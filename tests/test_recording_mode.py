from recording_mode import RecordingGesture, ControllerEvents, EventCursor


def test_hold_mode_short_and_long_presses_stop_on_release():
    for duration in (0.02, 1):
        gesture = RecordingGesture('hold')
        assert gesture.feed('press', 1) == 'start'
        assert gesture.feed('release', 1 + duration) == 'stop'
        assert not gesture.recording


def test_tap_latches_then_second_press_stops_once():
    gesture = RecordingGesture('tap')
    assert gesture.feed('press', 1) == 'start'
    assert gesture.feed('release', 1.05) is None
    assert gesture.latched and gesture.recording
    assert gesture.feed('press', 4) == 'stop'
    assert gesture.feed('release', 4.1) is None
    assert not gesture.recording
    assert gesture.feed('press', 5) == 'start'


def test_hold_in_tap_mode_and_threshold_boundary():
    gesture = RecordingGesture('tap')
    assert gesture.feed('press', 1) == 'start'
    assert gesture.feed('release', 1.250) == 'stop'
    assert gesture.feed('press', 2) == 'start'
    assert gesture.feed('release', 3) == 'stop'


def test_release_and_repeat_without_start_do_nothing():
    gesture = RecordingGesture('tap')
    assert gesture.feed('release', 1) is None
    assert gesture.feed('press', 2) == 'start'
    assert gesture.feed('press', 2.01) is None
    assert gesture.feed('release', 2.1) is None


def test_disconnect_and_reset_clear_latched_recording():
    gesture = RecordingGesture('tap')
    gesture.feed('press', 1)
    gesture.feed('release', 1.1)
    assert gesture.feed('cancel', 2) == 'abort'
    assert not gesture.latched and not gesture.recording
    assert gesture.feed('release', 2.1) is None
    assert gesture.feed('press', 3) == 'start'
    gesture.reset()
    assert gesture.feed('release', 3.1) is None


def test_events_preserve_taps_between_backend_polls(tmp_path):
    path = tmp_path / 'events.json'
    writer = ControllerEvents(path)
    cursor = EventCursor()
    assert cursor.read(path) == []
    writer.append('press', 1)
    writer.append('release', 1.015)
    batch = cursor.read(path)
    assert [event['kind'] for event in batch] == ['press', 'release']
    assert batch[1]['time'] - batch[0]['time'] < 0.05
    assert cursor.read(path) == []


def test_event_restart_and_overflow_cancel(tmp_path):
    path = tmp_path / 'events.json'
    writer = ControllerEvents(path)
    cursor = EventCursor()
    cursor.read(path)
    writer = ControllerEvents(path)
    writer.append('press', 1)
    assert cursor.read(path)[0]['kind'] == 'cancel'
    for i in range(130):
        writer.append('press' if i % 2 == 0 else 'release', 2 + i)
    assert cursor.read(path)[0]['kind'] == 'cancel'


def backend_for_test(tmp_path, monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    import audio_runtime
    repo = Path(__file__).parents[1]
    monkeypatch.setitem(sys.modules, 'decky', SimpleNamespace(
        logger=MagicMock(), DECKY_USER_HOME=str(tmp_path), DECKY_SETTINGS_DIR=str(tmp_path)))
    monkeypatch.setenv('DECKY_PLUGIN_DIR', str(repo))
    monkeypatch.setattr(audio_runtime, 'setup_audio_environment', lambda *args: None)
    spec = importlib.util.spec_from_file_location('recording_mode_backend_test', repo / 'backend/src/decktation_backend.py')
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    monkeypatch.setattr(backend.time, "monotonic", lambda: 0)
    plugin = backend.Plugin
    plugin.controller_enabled = True
    plugin.recording_input_since = 0
    plugin.recording_gesture = RecordingGesture('tap')
    plugin._start_dictation_trace = MagicMock()
    plugin._finish_dictation_trace = MagicMock()
    voice = MagicMock()
    voice.is_recording = False
    voice.pending_text = None
    voice.start_recording.side_effect = lambda: setattr(voice, 'is_recording', True)
    voice.stop_recording.side_effect = lambda: setattr(voice, 'is_recording', False)
    voice.abort_recording.side_effect = lambda: setattr(voice, 'is_recording', False)
    voice.cancel_pending.side_effect = lambda: setattr(voice, 'pending_text', None)
    plugin.voice_service = voice
    return backend, plugin, voice


def test_backend_tap_start_stop_and_disconnect(tmp_path, monkeypatch):
    _, plugin, voice = backend_for_test(tmp_path, monkeypatch)
    for kind, timestamp in [('press', 1), ('release', 1.1), ('press', 2), ('release', 2.1)]:
        plugin._handle_recording_event({'kind': kind, 'time': timestamp})
    voice.start_recording.assert_called_once()
    voice.stop_recording.assert_called_once()
    plugin._handle_recording_event({'kind': 'press', 'time': 3})
    plugin._handle_recording_event({'kind': 'release', 'time': 3.1})
    plugin._handle_recording_event({'kind': 'cancel', 'time': 4})
    voice.abort_recording.assert_called_once()
    assert not voice.is_recording


def test_pending_cancel_capture_and_disabled_do_not_start(tmp_path, monkeypatch):
    _, plugin, voice = backend_for_test(tmp_path, monkeypatch)
    voice.pending_text = 'pending'
    plugin._handle_recording_event({'kind': 'press', 'time': 1})
    plugin._handle_recording_event({'kind': 'release', 'time': 1.1})
    voice.cancel_pending.assert_called_once()
    voice.start_recording.assert_not_called()
    plugin.binding_session = 'capture'
    plugin.binding_deadline = float('inf')
    plugin._handle_recording_event({'kind': 'press', 'time': 2})
    plugin.binding_session = None
    plugin.controller_enabled = False
    plugin._handle_recording_event({'kind': 'press', 'time': 3})
    voice.start_recording.assert_not_called()


def test_mode_persistence_validation_and_recording_guard(tmp_path, monkeypatch):
    import asyncio
    backend, plugin, voice = backend_for_test(tmp_path, monkeypatch)
    assert backend._read_button_config()['recordingMode'] == 'hold'
    assert asyncio.run(plugin.set_recording_mode(None, 'tap'))['success']
    assert backend._read_button_config()['recordingMode'] == 'tap'
    assert plugin.recording_gesture.mode == 'tap'
    assert not asyncio.run(plugin.set_recording_mode(None, 'invalid'))['success']
    voice.is_recording = True
    assert not asyncio.run(plugin.set_recording_mode(None, 'hold'))['success']
    assert backend._read_button_config()['recordingMode'] == 'tap'


def test_audio_start_failure_resets_gesture(tmp_path, monkeypatch):
    import pytest
    _, plugin, voice = backend_for_test(tmp_path, monkeypatch)
    voice.start_recording.side_effect = OSError('microphone unavailable')
    with pytest.raises(OSError):
        plugin._handle_recording_event({'kind': 'press', 'time': 1})
    plugin._handle_recording_event({'kind': 'release', 'time': 1.1})
    assert not plugin.recording_gesture.recording
    voice.stop_recording.assert_not_called()


def test_gestures_during_transcription_are_not_replayed(tmp_path, monkeypatch):
    backend, plugin, voice = backend_for_test(tmp_path, monkeypatch)
    plugin._handle_recording_event({'kind': 'press', 'time': 1})
    plugin._handle_recording_event({'kind': 'release', 'time': 1.1})
    def transcribe():
        voice.is_recording = False
        monkeypatch.setattr(backend.time, 'monotonic', lambda: 4)
    voice.stop_recording.side_effect = transcribe
    plugin._handle_recording_event({'kind': 'press', 'time': 2})
    for kind, timestamp in [('release', 2.1), ('press', 3), ('release', 3.1)]:
        plugin._handle_recording_event({'kind': kind, 'time': timestamp})
    assert voice.start_recording.call_count == 1
    assert not voice.is_recording
    plugin._handle_recording_event({'kind': 'press', 'time': 5})
    assert voice.start_recording.call_count == 2
