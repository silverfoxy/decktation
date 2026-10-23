"""Model selection stays observable and cannot start dictation while it reloads."""

import asyncio
import importlib.util
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import audio_runtime

import decktation_backend as backend
import wow_voice_chat
from wow_voice_chat import WoWVoiceChat


@pytest.fixture
def backend_module(monkeypatch, tmp_path):
    repo = Path(__file__).parents[1]
    monkeypatch.setitem(sys.modules, "decky", SimpleNamespace(
        logger=MagicMock(), DECKY_USER_HOME=str(tmp_path), DECKY_SETTINGS_DIR=str(tmp_path)))
    monkeypatch.setenv("DECKY_PLUGIN_DIR", str(repo))
    monkeypatch.setattr(audio_runtime, "setup_audio_environment", lambda *args: None)
    spec = importlib.util.spec_from_file_location("download_backend_test", repo / "backend/src/decktation_backend.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.Plugin.recording_start_count = 0
    module.Plugin.controller_debug = None
    return module


def test_model_download_stage_is_reported_while_rpc_is_pending(monkeypatch, tmp_path):
    model = tmp_path / ".cache" / "decktation" / "whisper.cpp" / "ggml-medium.bin"
    monkeypatch.setenv("DECKY_USER_HOME", str(tmp_path))
    started, release = threading.Event(), threading.Event()

    def download(_url, destination, _cancel_event):
        started.set()
        assert release.wait(5)
        destination.write_bytes(b"model")

    monkeypatch.setattr("wow_voice_chat._download_vulkan_model", download)
    server = tmp_path / "whisper-server"
    server.touch()
    monkeypatch.setattr(wow_voice_chat, "_whisper_server_path", lambda: server)
    service = WoWVoiceChat(lazy_load=True, model_size="medium")
    plugin = backend.Plugin()
    monkeypatch.setattr(backend.Plugin, "voice_service", service)
    monkeypatch.setattr(backend.Plugin, "model_operations", 0)

    with ThreadPoolExecutor(max_workers=1) as pool:
        job = pool.submit(lambda: asyncio.run(plugin.load_model()))
        try:
            assert started.wait(5)
            status = asyncio.run(plugin.get_status())
            assert status["success"] is True
            assert status["model_loading"] is True
            assert status["model_stage"] == "downloading"
            assert status["model_size"] == "medium"
            assert not model.exists()
        finally:
            release.set()
        # The mocked worker cannot start; the observable stage must still reset.
        assert job.result(5)["success"] is False
    status = asyncio.run(plugin.get_status())
    assert status["model_loading"] is False
    assert status["model_stage"] == "idle"


def test_cancel_download_restores_previous_cached_model(monkeypatch, tmp_path):
    base = tmp_path / ".cache" / "decktation" / "whisper.cpp" / "ggml-base.bin"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"cached base")
    server = tmp_path / "whisper-server"
    server.touch()
    monkeypatch.setenv("DECKY_USER_HOME", str(tmp_path))
    monkeypatch.setattr(wow_voice_chat, "_whisper_server_path", lambda: server)
    monkeypatch.setattr(WoWVoiceChat, "_vulkan_available", lambda self: False)
    workers = []
    def worker(_server, model, _environment, use_gpu):
        result = MagicMock()
        result.model = model
        workers.append(result)
        return result
    monkeypatch.setattr(wow_voice_chat, "ResidentWhisper", worker)
    entered, release = threading.Event(), threading.Event()
    class SlowResponse:
        calls = 0
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def read(self, _size):
            self.calls += 1
            if self.calls > 1:
                return b""
            entered.set()
            assert release.wait(5)
            return b"download bytes"
    monkeypatch.setattr(wow_voice_chat.urllib.request, "urlopen", lambda *_a, **_kw: SlowResponse())
    config = tmp_path / "button_config.json"
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(config))
    backend.Plugin.voice_service = service = WoWVoiceChat(lazy_load=True, model_size="base")
    monkeypatch.setattr(backend.Plugin, "model_operations", 0)
    assert service._load_model() is True
    assert service.whisper_model == base
    with ThreadPoolExecutor(max_workers=1) as pool:
        job = pool.submit(lambda: asyncio.run(backend.Plugin().set_model_size("medium")))
        try:
            assert entered.wait(5)
            assert service.model_stage == "downloading"
            cancelled = asyncio.run(backend.Plugin().cancel_model_download())
            assert cancelled["success"] is True
        finally:
            release.set()
        result = job.result(5)
    assert result["cancelled"] is True
    assert backend._read_button_config()["modelSize"] == "base"
    assert service.model_size == "base"
    assert service.is_model_ready() and service.whisper_model == base
    assert len(workers) == 2
    assert not (base.parent / "ggml-medium.bin").exists()
    assert not (base.parent / "ggml-medium.download").exists()
    assert service.model_stage == "idle"


def test_cancel_never_acknowledges_after_final_download_check(monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_USER_HOME", str(tmp_path))
    class PausedStageService(WoWVoiceChat):
        @property
        def model_stage(self):
            return self._stage

        @model_stage.setter
        def model_stage(self, value):
            if value == "loading" and getattr(self, "pause_transition", False):
                self.transition_started.set()
                assert self.transition_release.wait(5)
                self.pause_transition = False
            self._stage = value

    service = PausedStageService(lazy_load=True, model_size="medium")
    service.transition_started = threading.Event()
    service.transition_release = threading.Event()
    def downloaded(_url, destination, _cancel_event):
        destination.write_bytes(b"complete model")
        service.pause_transition = True
    monkeypatch.setattr(wow_voice_chat, "_download_vulkan_model", downloaded)
    with ThreadPoolExecutor(max_workers=2) as pool:
        loading = pool.submit(service._ensure_whisper_model)
        try:
            assert service.transition_started.wait(5)
            attempted = threading.Event()
            cancelling = pool.submit(lambda: (attempted.set(), service.cancel_model_download())[1])
            assert attempted.wait(5)
            # The final check and transition must be atomic with cancel's decision.
            with pytest.raises(FutureTimeout):
                cancelling.result(0.1)
        finally:
            service.transition_release.set()
        assert cancelling.result(5) is False
        assert loading.result(5).read_bytes() == b"complete model"


def test_switch_after_cancelled_initial_download_loads_cached_smaller_model(monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_USER_HOME", str(tmp_path))
    cache = tmp_path / ".cache" / "decktation" / "whisper.cpp"
    cache.mkdir(parents=True)
    (cache / "ggml-base.bin").write_bytes(b"cached")
    server = tmp_path / "whisper-server"
    server.touch()
    monkeypatch.setattr(wow_voice_chat, "_whisper_server_path", lambda: server)
    monkeypatch.setattr(WoWVoiceChat, "_vulkan_available", lambda self: False)
    monkeypatch.setattr(wow_voice_chat, "ResidentWhisper", lambda *_args, **_kwargs: MagicMock())
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(tmp_path / "button_config.json"))
    monkeypatch.setattr(backend.Plugin, "model_operations", 0)
    monkeypatch.setattr(backend.Plugin, "controller_enabled", True)
    service = WoWVoiceChat(lazy_load=True, model_size="medium")
    monkeypatch.setattr(backend.Plugin, "voice_service", service)
    backend._write_button_config({"modelSize": "medium"})
    result = asyncio.run(backend.Plugin().set_model_size("base"))
    assert result["success"] is True
    assert service.is_model_ready()
    assert service.whisper_model == cache / "ggml-base.bin"


def test_model_stage_clears_when_download_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_USER_HOME", str(tmp_path))
    def broken(_url, _destination, _cancel_event):
        raise OSError("network unavailable")
    monkeypatch.setattr("wow_voice_chat._download_vulkan_model", broken)
    server = tmp_path / "whisper-server"
    server.touch()
    monkeypatch.setattr(wow_voice_chat, "_whisper_server_path", lambda: server)
    service = WoWVoiceChat(lazy_load=True, model_size="medium")
    assert service._load_model() is False
    assert service.model_stage == "idle"
    assert service.model_loading is False


def test_controller_ptt_does_not_start_or_queue_when_model_operation_active(backend_module, monkeypatch, tmp_path):
    plugin = backend_module.Plugin
    state = tmp_path / "ptt_state"
    state.write_text("1")
    monkeypatch.setattr(backend_module, "STATE_FILE", str(state))
    plugin.poll_running = plugin.controller_enabled = True
    plugin.model_operations = 1
    voice = plugin.voice_service = MagicMock()
    voice.model_loading = True
    voice.is_recording = False
    voice.pending_snapshot.return_value = None
    voice.pending_text = None
    monkeypatch.setattr(backend_module.time, "sleep", lambda _: setattr(plugin, "poll_running", False))
    plugin.poll_button_state()
    voice.start_recording.assert_not_called()
    assert plugin.recording_start_count == 0


def test_controller_release_stops_existing_recording_even_if_model_becomes_busy(backend_module, monkeypatch, tmp_path):
    plugin = backend_module.Plugin
    state = tmp_path / "ptt_state"
    state.write_text("1")
    monkeypatch.setattr(backend_module, "STATE_FILE", str(state))
    plugin.poll_running = plugin.controller_enabled = True
    plugin.model_operations = 0
    voice = plugin.voice_service = MagicMock()
    voice.model_loading = False
    voice.is_recording = False
    voice.pending_snapshot.return_value = None
    voice.pending_text = None
    voice.start_recording.side_effect = lambda: setattr(voice, "is_recording", True)
    voice.stop_recording.side_effect = lambda: setattr(voice, "is_recording", False)
    ticks = 0
    def tick(_delay):
        nonlocal ticks
        ticks += 1
        if ticks == 1:
            assert voice.is_recording
            plugin.model_operations = 1
            state.write_text("0")
        else:
            plugin.poll_running = False
    monkeypatch.setattr(backend_module.time, "sleep", tick)
    plugin.poll_button_state()
    voice.stop_recording.assert_called_once_with()
    assert not voice.is_recording


def test_rpc_rejects_recording_during_model_operation(monkeypatch):
    service = MagicMock()
    service.is_recording = False
    service.model_loading = True
    monkeypatch.setattr(backend.Plugin, "voice_service", service)
    monkeypatch.setattr(backend.Plugin, "model_operations", 1)
    result = asyncio.run(backend.Plugin().start_recording())
    assert result["success"] is False
    service.start_recording.assert_not_called()


def test_model_switch_rejects_active_recording_without_losing_release(monkeypatch):
    service = MagicMock()
    service.is_recording = True
    service.is_transcribing = False
    monkeypatch.setattr(backend.Plugin, "voice_service", service)
    monkeypatch.setattr(backend.Plugin, "model_operations", 0)
    result = asyncio.run(backend.Plugin().set_model_size("medium"))
    assert result["success"] is False
    assert backend.Plugin.model_operations == 0
    service.set_model_size.assert_not_called()


def test_model_load_rejects_active_recording(monkeypatch):
    service = MagicMock()
    service.is_recording = True
    service.is_transcribing = False
    monkeypatch.setattr(backend.Plugin, "voice_service", service)
    monkeypatch.setattr(backend.Plugin, "model_operations", 0)
    result = asyncio.run(backend.Plugin().load_model())
    assert result["success"] is False
    assert backend.Plugin.model_operations == 0
    service._load_model.assert_not_called()
