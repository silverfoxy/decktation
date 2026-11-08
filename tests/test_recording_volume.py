import json
import subprocess
from unittest.mock import Mock
from types import SimpleNamespace

from recording_volume import RecordingVolume


def volume(mode="quiet"):
    control = RecordingVolume(mode)
    control._run = Mock(side_effect=lambda *args: {
        ("get-default-sink",): "speakers\n",
        ("--format=json", "list", "sinks"): json.dumps([
            {"name": "speakers", "volume": {"left": {"value": 50000}, "right": {"value": 30000}}}
        ]),
    }.get(args, ""))
    return control


def test_quiet_restores_each_channel_and_original_device():
    control = volume()
    control.transition("started")
    control._run.assert_called_with("set-sink-volume", "speakers", "10000", "6000")
    control.transition("started")  # Duplicate starts must not snapshot attenuated volume.
    control.transition("stopped")
    control._run.assert_called_with("set-sink-volume", "speakers", "50000", "30000")
    count = control._run.call_count
    control.transition("finished")
    assert control._run.call_count == count


def test_mute_and_abort():
    control = volume("mute")
    control.transition("started")
    control._run.assert_called_with("set-sink-volume", "speakers", "0", "0")
    control.transition("aborted")
    control._run.assert_called_with("set-sink-volume", "speakers", "50000", "30000")


def test_off_does_not_touch_audio():
    control = volume("off")
    control.transition("started")
    control.transition("stopped")
    control._run.assert_not_called()


def test_changing_setting_restores_output():
    control = volume()
    control.transition("started")
    control.set_mode("off")
    control._run.assert_called_with("set-sink-volume", "speakers", "50000", "30000")


def test_missing_audio_tools_never_interrupt_recording():
    control = volume()
    control._run.side_effect = FileNotFoundError("pactl")
    control.transition("started")
    assert control._original is None


def test_failed_restore_is_retried_on_shutdown():
    control = volume()
    control.transition("started")
    run = control._run.side_effect
    control._run.side_effect = subprocess.TimeoutExpired("pactl", 2)
    control.transition("stopped")
    assert control._original is not None
    control._run.side_effect = run
    control.transition("shutdown")
    assert control._original is None


def test_voice_restores_before_transcription_and_after_stream_failure(monkeypatch):
    import pytest
    from wow_voice_chat import WoWVoiceChat
    import wow_voice_chat

    control = volume()
    voice = WoWVoiceChat(lazy_load=True, recording_state_callback=control.transition)
    stream = Mock()
    monkeypatch.setattr(voice, "_open_input_stream", lambda: stream)
    # Keep NumPy stubs local: Python 3.11 mock teardown can delete attributes
    # that an earlier test patched on the shared MagicMock.
    monkeypatch.setattr(wow_voice_chat, "np", SimpleNamespace(
        concatenate=lambda *a, **kw: [1],
    ))

    def transcribe(_):
        assert control._original is None
        return ""

    monkeypatch.setattr(voice, "transcribe_audio", transcribe)
    voice.start_recording()
    voice.audio_queue.put([1])
    voice.stop_recording(send=False)
    assert control._original is None

    voice.start_recording()
    stream.stop.side_effect = RuntimeError("device disconnected")
    with pytest.raises(RuntimeError):
        voice.stop_recording(send=False)
    assert control._original is None


def test_voice_abort_restores_volume(monkeypatch):
    from wow_voice_chat import WoWVoiceChat
    control = volume()
    voice = WoWVoiceChat(lazy_load=True, recording_state_callback=control.transition)
    monkeypatch.setattr(voice, "_open_input_stream", Mock(return_value=Mock()))
    voice.start_recording()
    assert control._original is not None
    voice.abort_recording()
    assert control._original is None
