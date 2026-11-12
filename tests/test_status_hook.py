import json
import subprocess
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import decktation_backend as backend
import status_hook
from status_hook import StatusHook
from wow_voice_chat import WoWVoiceChat


def test_config_off_by_default_and_preserved(tmp_path, monkeypatch):
    path = tmp_path / "button_config.json"
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(path))
    assert backend._read_button_config()["statusHookCommand"] == ""
    path.write_text(json.dumps({"statusHookCommand": "/usr/bin/true"}))
    assert backend._write_button_config(backend._read_button_config())["statusHookCommand"] == "/usr/bin/true"


def test_worker_preserves_order_and_survives_failure(monkeypatch):
    hook = StatusHook()
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    seen = []

    def run(command, event, home):
        seen.append(event)
        if event == "record_start":
            entered.set()
            assert release.wait(2)
            raise RuntimeError("broken command")
        if event == "transcription_done":
            finished.set()

    monkeypatch.setattr(hook, "_run", run)
    hook.submit("command", "record_start")
    assert entered.wait(2)
    try:
        hook.submit("command", "record_stop")
        hook.submit("command", "transcription_done")
        assert seen == ["record_start"]
    finally:
        release.set()
    assert finished.wait(2)
    assert seen == ["record_start", "record_stop", "transcription_done"]


def process_setup(monkeypatch, uid=1000):
    monkeypatch.setattr(status_hook, "_session_account", lambda env: SimpleNamespace(
        pw_uid=uid, pw_gid=100, pw_name="gamer", pw_dir="/home/gamer"))
    monkeypatch.setattr(status_hook.os, "geteuid", lambda: 0)
    process = MagicMock(pid=1234)
    process.wait.return_value = 0
    popen = MagicMock()
    popen.return_value.__enter__.return_value = process
    monkeypatch.setattr(status_hook.subprocess, "Popen", popen)
    return process, popen


def test_hook_drops_root_and_privileged_environment(monkeypatch):
    _, popen = process_setup(monkeypatch)
    monkeypatch.setenv("SECRET_TOKEN", "private")
    StatusHook()._run('/home/gamer/hook "two words"', "record_abort", "/home/gamer")
    args, kwargs = popen.call_args
    assert args[0] == ["/home/gamer/hook", "two words"]
    assert (kwargs["user"], kwargs["group"], kwargs["extra_groups"]) == (1000, 100, [])
    assert kwargs["env"]["DECKTATION_EVENT"] == "record_abort"
    assert kwargs["env"]["HOME"] == "/home/gamer"
    assert "SECRET_TOKEN" not in kwargs["env"]


def test_unresolved_or_root_account_never_launches(monkeypatch):
    _, popen = process_setup(monkeypatch, uid=0)
    with pytest.raises(RuntimeError):
        StatusHook()._run("command", "record_start", None)
    popen.assert_not_called()


def test_timeout_kills_group_and_reaps_process(monkeypatch):
    process, _ = process_setup(monkeypatch)
    process.wait.side_effect = [subprocess.TimeoutExpired("hook", 3), 0]
    kill = MagicMock()
    monkeypatch.setattr(status_hook.os, "killpg", kill)
    StatusHook()._run("command", "record_stop", "/home/gamer")
    kill.assert_called_once_with(1234, status_hook.signal.SIGKILL)
    assert process.wait.call_count == 2


def test_service_events_cover_abort_completion_and_errors(monkeypatch):
    events = []
    monkeypatch.setattr(backend, "_status_hook", events.append)
    monkeypatch.setattr(backend.Plugin, "recording_volume", None)
    monkeypatch.setattr(backend.Plugin, "haptic_feedback", None)
    voice = WoWVoiceChat(lazy_load=True, recording_state_callback=backend.Plugin._recording_transition)
    stream = MagicMock()
    monkeypatch.setattr(voice, "_open_input_stream", lambda: stream)
    voice.start_recording()
    voice.start_recording()  # No duplicate notification for an idempotent call.
    voice.abort_recording()
    voice.abort_recording()
    assert events == ["record_start", "record_abort"]
    events.clear()
    voice.start_recording()
    voice.stop_recording(send=False)  # Empty capture still completes.
    voice.stop_recording(send=False)
    assert events == ["record_start", "record_stop", "transcription_done"]
    events.clear()
    voice.start_recording()
    stream.stop.side_effect = RuntimeError("device failed")
    with pytest.raises(RuntimeError):
        voice.stop_recording()
    assert events == ["record_start", "record_stop", "error"]


@pytest.mark.parametrize("action", ["disable", "shutdown"])
def test_disable_and_shutdown_emit_abort(action, tmp_path, monkeypatch):
    import asyncio
    events = []
    monkeypatch.setattr(backend, "_status_hook", events.append)
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(backend.Plugin, "recording_volume", None)
    monkeypatch.setattr(backend.Plugin, "recording_overlay", None)
    monkeypatch.setattr(backend.Plugin, "haptic_feedback", None)
    monkeypatch.setattr(backend.Plugin, "enable_transition_lock", asyncio.Lock())
    monkeypatch.setattr(backend.Plugin, "_set_controller_enabled", MagicMock())
    monkeypatch.setattr(backend.Plugin, "_finish_dictation_trace", MagicMock())
    voice = WoWVoiceChat(lazy_load=True, recording_state_callback=backend.Plugin._recording_transition)
    monkeypatch.setattr(voice, "_open_input_stream", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(voice, "unload_model", MagicMock())
    monkeypatch.setattr(backend.Plugin, "voice_service", voice)
    voice.start_recording()
    if action == "disable":
        async def disable():
            await asyncio.wait_for(backend.Plugin().set_enabled(False), timeout=3)
        asyncio.run(disable())
    else:
        asyncio.run(backend.Plugin()._shutdown_voice_service())
    assert events == ["record_start", "record_abort"]


def test_transcription_failure_emits_error(monkeypatch):
    import wow_voice_chat
    events = []
    voice = WoWVoiceChat(lazy_load=True, recording_state_callback=events.append)
    monkeypatch.setattr(voice, "_open_input_stream", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(wow_voice_chat, "np", SimpleNamespace(concatenate=lambda *a, **kw: [1]))
    monkeypatch.setattr(voice, "transcribe_audio", MagicMock(side_effect=RuntimeError("inference failed")))
    voice.start_recording()
    voice.audio_queue.put([1])
    with pytest.raises(RuntimeError):
        voice.stop_recording()
    assert events == ["started", "stopped", "error"]
