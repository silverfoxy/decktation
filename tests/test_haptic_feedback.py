"""Recording cues stay optional and never require HID access in tests."""

from unittest.mock import MagicMock
import asyncio
import importlib.util
import json
import struct
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
    feedback._events.put_nowait(("started", {}, 0))
    feedback._events.put_nowait(("stopped", {}, 0))
    calls = 0
    def get(**_kwargs):
        nonlocal calls
        calls += 1
        if calls > 2:
            raise StopIteration
        return ["started", "stopped"][calls - 1], {}, 0
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

    source = {'path': '/dev/fake', 'kind': 'steam_deck'}
    feedback._play("started", source, 0)
    assert [call.args[1] for call in send.call_args_list] == [45000] * 3 + [0, 0]
    send.reset_mock()
    feedback._play("stopped", source, 0)
    assert [call.args[1] for call in send.call_args_list] == (
        [45000, 45000, 0, 45000, 45000, 0, 0]
    )

    send.reset_mock()
    send.side_effect = [OSError("failed"), None]
    with pytest.raises(OSError):
        feedback._play("started", source, 0)
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


def _source(kind, path='/dev/input/event7', **identity):
    return {'path': path, 'kind': kind,
            'identity': {'bus': identity.get('bus', 3),
                         'vendor_id': identity.get('vendor_id', 0x045e),
                         'product_id': identity.get('product_id', 1)},
            'time': haptic_feedback.time.time()}


def test_session_keeps_combo_controller_for_both_cues(tmp_path, monkeypatch):
    source_file = tmp_path / 'source.json'
    xbox = _source('evdev_gamepad')
    source_file.write_text(json.dumps(xbox))
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    monkeypatch.setattr(feedback, '_run', lambda: None)
    feedback.begin_session(str(source_file))
    feedback.emit('started')
    source_file.write_text(json.dumps(_source('steam_deck', '/dev/hidraw3')))
    feedback.emit('stopped')
    queued = [feedback._events.get_nowait() for _ in range(2)]
    assert [entry[0] for entry in queued] == ['started', 'stopped']
    assert all(entry[1] == xbox for entry in queued)
    assert feedback._session is None


def test_recent_controller_expires_and_disabled_events_do_not_queue(tmp_path, monkeypatch):
    source_file = tmp_path / 'recent.json'
    stale = _source('evdev_gamepad')
    stale['time'] -= 30
    source_file.write_text(json.dumps(stale))
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    feedback.begin_session(str(source_file), max_age=10)
    feedback.emit('started')
    assert feedback._events.empty()
    stale['time'] = haptic_feedback.time.time()
    source_file.write_text(json.dumps(stale))
    feedback.begin_session(str(source_file), max_age=10)
    feedback.set_enabled(False)
    feedback.emit('started')
    assert feedback._events.empty()


@pytest.mark.parametrize('kind,backend', [
    ('steam_deck', '_deck_pattern'),
    ('steam_controller_wired', '_legacy_pattern'),
    ('steam_controller_wireless', '_legacy_pattern'),
    ('steam_controller_2026_puck', '_triton_pattern'),
])
def test_valve_backend_is_bound_to_exact_discovered_path(monkeypatch, kind, backend):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    source = _source(kind, '/dev/hidraw4')
    monkeypatch.setattr(haptic_feedback, 'find_steam_hidraw',
                        lambda: iter([('/dev/hidraw4', kind), ('/dev/hidraw0', 'steam_deck')]))
    monkeypatch.setattr(haptic_feedback.os, 'open', lambda *args: 42)
    monkeypatch.setattr(haptic_feedback.os, 'close', lambda *args: None)
    deck = MagicMock()
    legacy = MagicMock()
    triton = MagicMock()
    monkeypatch.setattr(feedback, '_deck_pattern', deck)
    monkeypatch.setattr(feedback, '_legacy_pattern', legacy)
    monkeypatch.setattr(feedback, '_triton_pattern', triton)
    feedback._play('started', source, 0)
    {'_deck_pattern': deck, '_legacy_pattern': legacy,
     '_triton_pattern': triton}[backend].assert_called_once()
    source['path'] = '/dev/hidraw9'
    feedback._play('stopped', source, 0)
    assert deck.call_count + legacy.call_count + triton.call_count == 1


def test_triton_output_report_and_explicit_stop(monkeypatch):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    writes = []
    monkeypatch.setattr(haptic_feedback.os, 'write', lambda fd, report: writes.append(report))
    monkeypatch.setattr(haptic_feedback.time, 'sleep', lambda _: None)
    feedback._triton_pattern(42, 'started', 0)
    assert len(writes) == 5
    assert all(len(report) == 10 and report[0] == 0x80 for report in writes)
    assert all(struct.unpack_from('<H', report, 4)[0] == 45000 for report in writes[:3])
    assert writes[-1] == bytes([0x80] + [0] * 9)


def test_legacy_pulse_report_and_two_burst_pattern(monkeypatch):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    sent = []
    monkeypatch.setattr(haptic_feedback.fcntl, 'ioctl',
                        lambda fd, request, report: sent.append(bytes(report)))
    monkeypatch.setattr(haptic_feedback.time, 'sleep', lambda _: None)
    feedback._legacy_pattern(42, 'stopped', 0)
    assert len(sent) == 2
    assert all(report[:4] == b'\x00\x8f\x08\x02' for report in sent)
    assert all(struct.unpack_from('<H', report, 4)[0] == 15000 for report in sent)
    assert all(struct.unpack_from('<H', report, 8)[0] == 1 for report in sent)


@pytest.mark.parametrize('vendor,family', [(0x045e, 'xbox'), (0x054c, 'playstation'),
                                           (0x1234, 'generic')])
def test_evdev_family_selects_only_matching_ff_interface(monkeypatch, vendor, family):
    source = _source('evdev_gamepad', vendor_id=vendor)
    monkeypatch.setattr(haptic_feedback.glob, 'glob',
                        lambda pattern: ['/dev/input/event7', '/dev/input/event8', '/dev/input/event9'])
    monkeypatch.setattr(haptic_feedback, '_physical_parent',
                        lambda path: '/same' if path.endswith(('7', '8')) else '/other')
    monkeypatch.setattr(haptic_feedback.os, 'open', lambda *args: int(args[0][-1]))
    monkeypatch.setattr(haptic_feedback.os, 'close', lambda *args: None)
    monkeypatch.setattr(haptic_feedback, '_identity', lambda fd: source['identity'])
    monkeypatch.setattr(haptic_feedback, '_ff_capable', lambda fd: fd == 8)
    assert haptic_feedback._ff_path(source) == ('/dev/input/event8', None)


def test_virtual_and_unsupported_controller_never_fall_back_to_deck(monkeypatch):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    deck = MagicMock()
    monkeypatch.setattr(feedback, '_deck_pattern', deck)
    source = _source('evdev_gamepad', bus=6, vendor_id=0x28de, product_id=0x11ff)
    feedback._play('started', source, 0)
    deck.assert_not_called()
    assert haptic_feedback._ff_path(source)[0] is None


def test_evdev_effect_stops_and_erases_on_failure(monkeypatch):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    calls = []
    monkeypatch.setattr(haptic_feedback.os, 'open', lambda *args: 42)
    monkeypatch.setattr(haptic_feedback.os, 'close', lambda fd: calls.append(('close', fd)))
    monkeypatch.setattr(haptic_feedback, '_ff_capable', lambda fd: True)
    monkeypatch.setattr(haptic_feedback, '_identity', lambda fd: {'bus': 3})
    def ioctl(fd, request, arg):
        if request == haptic_feedback.EVIOCSFF:
            arg.id = 3
        calls.append(('ioctl', request))
    monkeypatch.setattr(haptic_feedback.fcntl, 'ioctl', ioctl)
    def write(fd, event):
        calls.append(('write', haptic_feedback.EVENT.unpack(event)[-1]))
        if haptic_feedback.EVENT.unpack(event)[-1] == 1:
            raise OSError('disconnected')
    monkeypatch.setattr(haptic_feedback.os, 'write', write)
    with pytest.raises(OSError):
        feedback._evdev_pattern('/dev/input/event7', 'started', 0, {'bus': 3})
    assert ('write', 0) in calls
    assert ('ioctl', haptic_feedback.EVIOCRMFF) in calls
    assert ('close', 42) in calls


def test_steam_virtual_pad_uses_only_its_own_ff_node(monkeypatch):
    source = _source('evdev_gamepad', '/dev/input/event25',
                     bus=3, vendor_id=0x28de, product_id=0x11ff)
    monkeypatch.setattr(haptic_feedback.os, 'open', lambda *args: 25)
    monkeypatch.setattr(haptic_feedback.os, 'close', lambda *args: None)
    monkeypatch.setattr(haptic_feedback, '_identity', lambda fd: source['identity'])
    monkeypatch.setattr(haptic_feedback, '_ff_capable', lambda fd: True)
    monkeypatch.setattr(haptic_feedback.glob, 'glob',
                        lambda pattern: (_ for _ in ()).throw(AssertionError('must not scan siblings')))
    assert haptic_feedback._ff_path(source) == ('/dev/input/event25', None)
    monkeypatch.setattr(haptic_feedback, '_ff_capable', lambda fd: False)
    assert haptic_feedback._ff_path(source)[0] is None


def test_ff_capability_queries_event_and_force_feedback_bitmaps(monkeypatch):
    queries = []
    def read(fd, number, size):
        queries.append((number, size))
        data = bytearray(size)
        code = haptic_feedback.EV_FF if number == 0x20 else haptic_feedback.FF_RUMBLE
        data[code // 8] |= 1 << (code % 8)
        return data
    monkeypatch.setattr(haptic_feedback, 'ioctl_read', read)
    assert haptic_feedback._ff_capable(42)
    assert queries == [(0x20, 8), (0x20 + haptic_feedback.EV_FF, 16)]


def test_switching_controllers_changes_next_session_only(tmp_path, monkeypatch):
    source_file = tmp_path / 'source.json'
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    monkeypatch.setattr(feedback, '_run', lambda: None)
    deck = _source('steam_deck', '/dev/hidraw0')
    controller = _source('steam_controller_2026_puck', '/dev/hidraw3')
    source_file.write_text(json.dumps(deck))
    feedback.begin_session(str(source_file))
    feedback.emit('started')
    source_file.write_text(json.dumps(controller))
    feedback.emit('stopped')
    feedback.begin_session(str(source_file))
    feedback.emit('started')
    sources = [feedback._events.get_nowait()[1]['kind'] for _ in range(3)]
    assert sources == ['steam_deck', 'steam_deck', 'steam_controller_2026_puck']


def test_disconnected_controller_does_not_fall_back_to_other_valve_device(monkeypatch):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    monkeypatch.setattr(haptic_feedback, 'find_steam_hidraw',
                        lambda: iter([('/dev/hidraw0', 'steam_deck')]))
    opened = MagicMock()
    monkeypatch.setattr(haptic_feedback.os, 'open', opened)
    feedback._play('stopped', _source('steam_controller_2026_puck', '/dev/hidraw3'), 0)
    opened.assert_not_called()


def test_evdev_diagnostics_identify_family_without_serial():
    assert haptic_feedback._evdev_label(_source('evdev_gamepad', vendor_id=0x045e)) == 'xbox'
    assert haptic_feedback._evdev_label(_source('evdev_gamepad', vendor_id=0x054c)) == 'playstation'
    assert haptic_feedback._evdev_label(_source('evdev_gamepad', vendor_id=0x1234)) == 'generic-gamepad'
    assert haptic_feedback._evdev_label(_source('evdev_gamepad', vendor_id=0x28de,
                                                product_id=0x11ff)) == 'steam-input-virtual'


def test_evdev_identity_is_rechecked_after_open(monkeypatch):
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    monkeypatch.setattr(haptic_feedback.os, 'open', lambda *args: 42)
    closed = []
    monkeypatch.setattr(haptic_feedback.os, 'close', closed.append)
    monkeypatch.setattr(haptic_feedback, '_identity', lambda fd: {'vendor_id': 2})
    write = MagicMock()
    monkeypatch.setattr(haptic_feedback.os, 'write', write)
    feedback._evdev_pattern('/dev/input/event7', 'started', 0, {'vendor_id': 1})
    write.assert_not_called()
    assert closed == [42]


def test_puck_kind_is_accepted_for_haptic_session(tmp_path):
    source = _source('steam_controller_2026_puck', '/dev/hidraw4',
                     vendor_id=0x28de, product_id=0x1304)
    file = tmp_path / 'source.json'
    file.write_text(json.dumps(source))
    feedback = haptic_feedback.HapticFeedback(enabled=True)
    feedback.begin_session(str(file))
    assert feedback._session == source
