import pytest
from unittest.mock import MagicMock

import wow_voice_chat


def service():
    return wow_voice_chat.WoWVoiceChat(lazy_load=True)


@pytest.fixture(autouse=True)
def reset_audio_mock(monkeypatch):
    # A patched dynamic MagicMock attribute can remain deleted after teardown;
    # reset_mock() clears calls but does not restore that attribute. Isolate the
    # audio module so shutdown tests never inherit another test's missing API.
    monkeypatch.setattr(wow_voice_chat, "sd", MagicMock())
    wow_voice_chat.sd.default.device.__getitem__.return_value = 7
    wow_voice_chat.sd.query_devices.return_value = {
        "default_samplerate": 48000,
        "max_input_channels": 2,
    }
    wow_voice_chat.sd.check_input_settings.return_value = None


def test_stereo_audio_is_mixed_before_resampling(monkeypatch):
    voice = service()
    voice.whisper_sample_rate = 48000
    stereo = MagicMock()
    stereo.ndim = 2
    normalized = MagicMock()
    mixed = MagicMock()
    stereo.astype.return_value = normalized
    normalized.mean.return_value = mixed
    fake_numpy = MagicMock()
    fake_numpy.asarray.return_value = stereo
    fake_numpy.issubdtype.return_value = False
    fake_numpy.clip.return_value = mixed
    monkeypatch.setattr(wow_voice_chat, "np", fake_numpy)

    audio = voice._prepare_audio(stereo, 48000)

    normalized.mean.assert_called_once_with(axis=1)
    stereo.reshape.assert_not_called()
    assert audio is mixed


def test_capture_falls_back_to_stereo_when_mono_is_rejected(monkeypatch):
    voice = service()
    wow_voice_chat.sd.check_input_settings.side_effect = [RuntimeError("mono unsupported"), None]

    settings = voice._input_stream_settings()

    assert settings["device"] == 7
    assert settings["channels"] == 2
    assert voice.input_channels == 2


def test_recording_is_not_marked_active_when_stream_start_fails(monkeypatch):
    voice = service()
    stream = wow_voice_chat.sd.InputStream.return_value
    stream.start.side_effect = RuntimeError("cannot open")

    with pytest.raises(RuntimeError, match="cannot open"):
        voice.start_recording()

    assert voice.is_recording is False
    assert voice.recording_stream is None


def test_abort_recording_discards_audio_and_cancels_pending_send():
    voice = service()
    stream = MagicMock()
    timer = MagicMock()
    voice.is_recording = True
    voice.recording_stream = stream
    voice.pending_text = "do not send"
    voice._pending_timer = timer

    assert voice.abort_recording() is True

    assert voice.is_recording is False
    assert voice.recording_stream is None
    stream.abort.assert_called_once()
    stream.close.assert_called_once()
    assert voice.audio_queue.empty()
    assert voice.pending_text is None
    timer.cancel.assert_called_once()


def test_shutdown_closes_capture_before_terminating_portaudio(monkeypatch):
    voice = service()
    events = []
    stream = MagicMock()
    stream.abort.side_effect = lambda: events.append("abort")
    stream.close.side_effect = lambda: events.append("close")
    voice.recording_stream = stream
    voice.is_recording = True
    monkeypatch.setattr(wow_voice_chat.sd, "_terminate", lambda: events.append("terminate"))
    voice.shutdown()
    voice.start_recording()
    assert events == ["abort", "close", "terminate"]
    assert not voice.is_recording


def test_shutdown_does_not_terminate_portaudio_when_stream_close_fails():
    voice = service()
    voice.recording_stream = MagicMock()
    voice.recording_stream.close.side_effect = RuntimeError("close failed")
    with pytest.raises(RuntimeError, match="close failed"):
        voice.shutdown()
    wow_voice_chat.sd._terminate.assert_not_called()


def test_shutdown_prevents_model_load_and_text_injection():
    voice = service()
    voice.begin_shutdown()
    assert voice._load_model() is False
    voice.send_to_wow_chat("do not send")
    assert voice.pending_text is None


def test_shutdown_interrupts_inference_before_waiting_for_capture(monkeypatch):
    voice = service()
    worker = MagicMock()
    voice.whisper_worker = worker
    events = []
    worker.close.side_effect = lambda: events.append("worker")
    monkeypatch.setattr(voice, "abort_recording", lambda: events.append("capture"))
    monkeypatch.setattr(wow_voice_chat.sd, "_terminate", lambda: events.append("audio"))
    voice.shutdown()
    assert events == ["worker", "capture", "audio"]
    assert voice.whisper_worker is None
