"""Recording cues stay optional and never require HID access in tests."""

from unittest.mock import MagicMock
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import haptic_feedback
import audio_runtime
import wow_voice_chat
from wow_voice_chat import WoWVoiceChat


def test_default_disabled_and_missing_hardware(monkeypatch):
    feedback = haptic_feedback.HapticFeedback()
    play = MagicMock()
    monkeypatch.setattr(feedback, "_play", play)
    feedback.emit("started")
    assert feedback._events.empty()
    play.assert_not_called()

    monkeypatch.setattr(haptic_feedback, "find_steam_hidraw", lambda: iter(()))
    feedback._play("started")  # Unsupported hardware is a no-op.


def test_single_worker_plays_distinct_patterns_and_survives_failure(monkeypatch):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    play = MagicMock(side_effect=[OSError("unavailable"), None])
    monkeypatch.setattr(feedback, "_play", play)
    monkeypatch.setattr(haptic_feedback.time, "sleep", lambda _: None)
    # Run queued events synchronously, stopping once both are consumed.
    feedback._events.put_nowait("started")
    feedback._events.put_nowait("stopped")
    calls = 0
    def get(**_kwargs):
        nonlocal calls
        calls += 1
        if calls > 2:
            raise StopIteration
        return ["started", "stopped"][calls - 1]
    monkeypatch.setattr(feedback._events, "get", get)
    with pytest.raises(StopIteration):
        feedback._run()
    assert play.call_count == 2


def test_rumble_patterns_are_bounded_and_always_stopped(monkeypatch):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    monkeypatch.setattr(haptic_feedback, "find_steam_hidraw",
                        lambda: iter([("/dev/fake", "steam_deck")]))
    monkeypatch.setattr(haptic_feedback.os, "open", lambda *args: 42)
    monkeypatch.setattr(haptic_feedback.os, "close", lambda fd: None)
    monkeypatch.setattr(haptic_feedback.time, "sleep", lambda _: None)
    send = MagicMock()
    monkeypatch.setattr(feedback, "_send_rumble", send)

    feedback._play("started")
    assert [call.args[1] for call in send.call_args_list] == [45000] * 3 + [0, 0]
    send.reset_mock()
    feedback._play("stopped")
    assert [call.args[1] for call in send.call_args_list] == (
        [45000, 45000, 0, 45000, 45000, 0, 0]
    )

    send.reset_mock()
    send.side_effect = [OSError("failed"), None]
    with pytest.raises(OSError):
        feedback._play("started")
    assert [call.args[1] for call in send.call_args_list] == [45000, 0]


def test_recording_transitions_emit_once_and_before_processing(monkeypatch):
    events = []
    voice = WoWVoiceChat(lazy_load=True, recording_state_callback=events.append)
    stream = MagicMock()
    monkeypatch.setattr(voice, "_open_input_stream", lambda: stream)

    voice.start_recording()
    voice.start_recording()
    assert events == ["started"]

    voice.audio_queue.put([1])
    monkeypatch.setattr(wow_voice_chat.np, "concatenate", lambda *args, **kwargs: [1])
    monkeypatch.setattr(voice, "transcribe_audio", lambda _: events.append("transcribing"))
    voice.stop_recording(send=False)
    voice.stop_recording(send=False)
    assert events == ["started", "stopped", "transcribing"]
    stream.stop.assert_called_once()


def test_test_mode_uses_same_transitions_without_sending():
    events = []
    voice = WoWVoiceChat(lazy_load=True, test_mode=True,
                         recording_state_callback=events.append)
    voice.start_recording()
    voice.stop_recording(send=False)
    assert events == ["started", "stopped"]


def test_failed_start_and_feedback_errors_do_not_affect_recording(monkeypatch):
    events = []
    voice = WoWVoiceChat(lazy_load=True, recording_state_callback=events.append)
    stream = MagicMock()
    stream.start.side_effect = OSError("microphone unavailable")
    monkeypatch.setattr(voice, "_open_input_stream", lambda: stream)
    with pytest.raises(OSError):
        voice.start_recording()
    assert events == []

    voice.recording_state_callback = MagicMock(side_effect=RuntimeError("haptic error"))
    stream.start.side_effect = None
    voice.start_recording()
    voice.stop_recording(send=False)
    assert voice.is_recording is False


def test_preference_defaults_off_and_persists(tmp_path, monkeypatch):
    repo = Path(__file__).parents[1]
    decky = SimpleNamespace(
        logger=MagicMock(), DECKY_USER_HOME=str(tmp_path),
        DECKY_SETTINGS_DIR=str(tmp_path),
    )
    monkeypatch.setitem(sys.modules, "decky", decky)
    monkeypatch.setenv("DECKY_PLUGIN_DIR", str(repo))
    monkeypatch.setattr(audio_runtime, "setup_audio_environment", lambda *args: None)
    spec = importlib.util.spec_from_file_location(
        "decktation_backend_haptic_test", repo / "backend/src/decktation_backend.py"
    )
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)

    assert backend._read_button_config()["hapticFeedback"] is False
    backend.Plugin.haptic_feedback = haptic_feedback.HapticFeedback()
    assert asyncio.run(backend.Plugin().set_haptic_feedback(True))["success"]
    assert backend._read_button_config()["hapticFeedback"] is True
    assert backend.Plugin.haptic_feedback.enabled is True
    assert json.loads((tmp_path / "button_config.json").read_text())["hapticFeedback"] is True
    assert asyncio.run(backend.Plugin().set_haptic_feedback(False))["success"]
    assert backend._read_button_config()["hapticFeedback"] is False
