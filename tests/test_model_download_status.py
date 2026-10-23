"""Model selection stays observable and cannot start dictation while it reloads."""

import asyncio
import importlib.util
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
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

    def download(_url, destination):
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


def test_model_stage_clears_when_download_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_USER_HOME", str(tmp_path))
    def broken(_url, _destination):
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
