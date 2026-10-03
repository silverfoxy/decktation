import importlib
import struct

import pytest

from gamepad_evdev import EvdevGamepad, KEY_BUTTONS, button_mapping, configured_button_mapping


def test_custom_mapping_is_scoped_and_duplicate_buttons_are_ored(monkeypatch, tmp_path):
    monkeypatch.setenv('DECKTATION_CONFIG_DIR', str(tmp_path))
    (tmp_path / 'controller_mappings.json').write_text(
        '{"0005:1234:5678": {"0x133": "X", "0x134": "Y", "0x135": "X"}}')
    identity = {'bus': 5, 'vendor_id': 0x1234, 'product_id': 0x5678}
    device = gamepad()
    device.key_buttons = configured_button_mapping(identity)
    device.feed(1, 0x133, 1)
    assert device.feed(0, 0, 0)['X']
    assert configured_button_mapping({**identity, 'bus': 3})[0x133] == 'Y'


@pytest.mark.parametrize('contents', ['{', '[]',
    '{"0005:1234:5678": {"0x133": "X", "0x134": "INVALID"}}'])
def test_invalid_custom_mapping_falls_back_atomically(monkeypatch, tmp_path, contents, capsys):
    monkeypatch.setenv('DECKTATION_CONFIG_DIR', str(tmp_path))
    (tmp_path / 'controller_mappings.json').write_text(contents)
    assert configured_button_mapping({'bus': 5, 'vendor_id': 0x1234, 'product_id': 0x5678}) == KEY_BUTTONS
    assert 'Ignoring controller mapping' in capsys.readouterr().out


@pytest.fixture
def listener(monkeypatch, tmp_path):
    monkeypatch.setenv('DECKTATION_CONFIG_DIR', str(tmp_path))
    return importlib.import_module('controller_listener')


def gamepad(axes=None, identity=None):
    device = EvdevGamepad.__new__(EvdevGamepad)
    device.key_buttons = button_mapping(identity or {})
    device.keys = set()
    device.axes = axes or {}
    device.values = {code: low for code, (_, low, _) in device.axes.items()}
    device.dropped = False
    device.resync_count = 0
    return device


@pytest.mark.parametrize('identity', [
    {'vendor_id': 0x045e, 'product_id': 0x02fd, 'bus': 5},
    {'vendor_id': 0x045e, 'product_id': 0x028e, 'bus': 3},
    {'vendor_id': 0x28de, 'product_id': 0x11ff, 'bus': 3},
])
def test_xbox_x_combo_uses_historical_key_codes(listener, identity):
    device = gamepad({2: ('L2', 0, 255), 5: ('R2', 0, 255)}, identity)
    tracker = listener.ComboTracker(['L2', 'R2', 'X'])
    device.feed(3, 2, 255)
    device.feed(3, 5, 255)
    device.feed(1, 0x134, 1)  # Physical Xbox Y must not trigger X.
    assert not tracker.update('pad', device.feed(0, 0, 0))
    device.feed(1, 0x134, 0)
    device.feed(1, 0x133, 1)  # Physical Xbox X.
    assert tracker.update('pad', device.feed(0, 0, 0))
    device.feed(1, 0x133, 0)
    assert not tracker.update('pad', device.feed(0, 0, 0))


@pytest.mark.parametrize('vendor', [0x054c, 0x057e, 0x28de, 0xffff])
def test_other_gamepads_keep_positional_mapping(vendor):
    device = gamepad(identity={'vendor_id': vendor})
    device.feed(1, 0x133, 1)
    states = device.feed(0, 0, 0)
    assert states['Y'] and not states['X']
    device.feed(1, 0x133, 0)
    device.feed(1, 0x134, 1)
    states = device.feed(0, 0, 0)
    assert states['X'] and not states['Y']


def test_combo_does_not_span_controllers_and_disconnect_releases(listener):
    tracker = listener.ComboTracker(['L1', 'R1'])
    assert not tracker.update('deck', {'L1': True})
    assert not tracker.update('xbox', {'R1': True})
    assert tracker.update('xbox', {'L1': True, 'R1': True})
    assert not tracker.remove('xbox')


def test_duplicate_sources_do_not_release_another_held_combo(listener):
    tracker = listener.ComboTracker(['A'])
    assert tracker.update('raw', {'A': True})
    assert tracker.update('evdev', {'A': True})
    assert tracker.update('raw', {'A': False})
    assert not tracker.remove('evdev')


def test_grip_combo_still_works_with_standard_button(listener):
    tracker = listener.ComboTracker(['L4', 'R1'])
    assert not tracker.update('xbox', {'R1': True})
    assert tracker.update('deck', {'L4': True, 'R1': True})
    assert not tracker.update('deck', {'L4': False, 'R1': True})


@pytest.mark.parametrize('code,name', KEY_BUTTONS.items())
def test_evdev_buttons_press_repeat_release(code, name):
    device = gamepad()
    for value in (1, 2, 0):
        assert device.feed(1, code, value) is None
        states = device.feed(0, 0, 0)
        assert {key for key, pressed in states.items() if pressed} == ({name} if value else set())


@pytest.mark.parametrize('low,high,below,pressed', [
    (0, 255, 127, 128), (0, 1023, 511, 512), (-32768, 32767, -1, 0),
])
def test_trigger_ranges_and_digital_or_analog(low, high, below, pressed):
    device = gamepad({2: ('L2', low, high)})
    device.feed(3, 2, below)
    assert not device.feed(0, 0, 0)['L2']
    device.feed(3, 2, pressed)
    assert device.feed(0, 0, 0)['L2']
    device.feed(1, 0x138, 1)
    device.feed(3, 2, low)
    assert device.feed(0, 0, 0)['L2']
    device.feed(1, 0x138, 0)
    assert not device.feed(0, 0, 0)['L2']


def test_dropped_events_are_discarded_until_resync(monkeypatch):
    device = gamepad()
    device.feed(1, 0x136, 1)
    device.feed(0, 3, 0)
    device.feed(1, 0x137, 1)
    assert 0x137 not in device.keys
    def resync():
        device.keys = set()
    monkeypatch.setattr(device, 'resync', resync)
    assert not any(device.feed(0, 0, 0).values())
    assert not device.dropped
    assert device.resync_count == 1


def test_capabilities_choose_trigger_axes_and_initial_state(monkeypatch):
    def bitmap(codes, size):
        data = bytearray(size)
        for code in codes:
            data[code // 8] |= 1 << (code % 8)
        return data
    def ioctl(fd, number, size):
        assert fd == 123
        if number == 0x02:
            return struct.pack('4H', 5, 0x045e, 0x0b13, 1)
        if number == 0x21:
            return bitmap([0x130, 0x131, 0x136], size)
        if number == 0x23:
            # Bluetooth Xbox exposes right-stick Z/RZ alongside GAS/BRAKE.
            return bitmap([0, 1, 0x02, 0x05, 0x0a, 0x09], size)
        if number == 0x18:
            return bitmap([0x136], size)
        return struct.pack('6i', 200, 0, 255, 0, 0, 0)
    monkeypatch.setattr('gamepad_evdev.os.open', lambda *args: 123)
    monkeypatch.setattr('gamepad_evdev.ioctl_read', ioctl)
    device = EvdevGamepad('/dev/input/event42')
    assert device.axes == {0x0a: ('L2', 0, 255), 0x09: ('R2', 0, 255)}
    assert device.states()['L1']
    assert device.states()['L2']
    assert device.states()['R2']
    assert device.identity['vendor_id'] == 0x045e
    assert device.supported_buttons == {'A', 'B', 'L1', 'L2', 'R2'}


def test_non_gamepads_are_rejected_and_closed(monkeypatch):
    closed = []
    monkeypatch.setattr('gamepad_evdev.os.open', lambda *args: 123)
    monkeypatch.setattr('gamepad_evdev.os.close', closed.append)
    monkeypatch.setattr('gamepad_evdev.ioctl_read', lambda fd, number, size: bytes(size))
    with pytest.raises(ValueError, match='not a gamepad'):
        EvdevGamepad('/dev/input/event42')
    assert closed == [123]


def test_keyboard_helper_with_gamepad_key_bits_is_rejected(monkeypatch):
    def ioctl(fd, number, size):
        data = bytearray(size)
        if number == 0x21:
            for code in (0x130, 0x131):
                data[code // 8] |= 1 << (code % 8)
        return data
    closed = []
    monkeypatch.setattr('gamepad_evdev.os.open', lambda *args: 123)
    monkeypatch.setattr('gamepad_evdev.os.close', closed.append)
    monkeypatch.setattr('gamepad_evdev.ioctl_read', ioctl)
    with pytest.raises(ValueError, match='not a gamepad'):
        EvdevGamepad('/dev/input/event25')
    assert closed == [123]


def test_custom_grips_can_be_mapped_without_assuming_vendor_codes(monkeypatch, tmp_path):
    monkeypatch.setenv('DECKTATION_CONFIG_DIR', str(tmp_path))
    (tmp_path / 'controller_mappings.json').write_text('{"0003:1234:5678": {"0x2c0": "R4"}}')
    device = gamepad()
    device.key_buttons = configured_button_mapping({'bus': 3, 'vendor_id': 0x1234, 'product_id': 0x5678})
    device.feed(1, 0x2c0, 1)
    assert device.feed(0, 0, 0)['R4']
    device.feed(1, 0x2c0, 0)
    assert not device.feed(0, 0, 0)['R4']


@pytest.mark.parametrize('product,suffix,expected', [
    (0x1205, '/input2', 'steam_deck'),
    (0x1142, '/input1', 'steam_controller_wireless'),
    (0x1304, '/input2', 'steam_controller_2026_puck'),
    (0x1304, '/input5', 'steam_controller_2026_puck'),
    (0x1304, '/input6', None),
    (0x1305, '/input3', 'steam_controller_2026_receiver'),
    (0x1302, '/input1', 'steam_controller_2026_wired'),
    (0x1303, '', 'steam_controller_2026_bluetooth'),
    (0x9999, '/input2', None),
])
def test_valve_discovery_selects_controller_slots(listener, monkeypatch, product, suffix, expected):
    import io
    bus = 5 if product == 0x1303 else 3
    monkeypatch.setattr(listener.glob, 'glob', lambda pattern: ['/dev/hidraw0'])
    monkeypatch.setattr('builtins.open', lambda *args: io.StringIO(
        f'HID_ID={bus:04X}:000028DE:{product:08X}\nHID_PHYS=usb-test{suffix}\n'))
    assert list(listener.find_steam_hidraw()) == ([('/dev/hidraw0', expected)] if expected else [])


def test_live_preview_shows_triggers_and_clears_on_release(listener, monkeypatch, tmp_path):
    preview = tmp_path / 'preview'
    monkeypatch.setattr(listener, 'PREVIEW_FILE', str(preview))
    listener.write_button_preview({'L2': True, 'R2': True, 'X': True})
    assert preview.read_text() == 'L2+R2+X'
    listener.write_button_preview({'L2': True, 'R2': False, 'X': False})
    assert preview.read_text() == 'L2'
    listener.write_button_preview({'L2': False})
    assert preview.read_text() == 'None'


def test_raw_reader_ignores_status_and_detects_grips(listener, monkeypatch):
    report = bytearray(64)
    report[0] = 1
    report[2] = 9
    report[13] = 2
    monkeypatch.setattr(listener.os, 'open', lambda *args: 123)
    monkeypatch.setattr(listener.os, 'read', lambda *args: report)
    device = listener.RawGamepad('/dev/hidraw0')
    assert list(device.read_states())[0]['L4']
    report[2] = 4
    assert list(device.read_states()) == []
    report[2] = 3
    report[4] = 1
    assert not any(list(device.read_states())[0].values())


def test_listener_hotplug_evdev_while_raw_is_idle_and_disconnect(listener, monkeypatch, tmp_path, capsys):
    """An idle Deck must not block a newly attached Xbox or its release."""
    from types import SimpleNamespace

    for name in ('STATE_FILE', 'PID_FILE', 'PREVIEW_FILE', 'CONTROLLER_TYPE_FILE', 'STATUS_FILE',
                 'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE'):
        monkeypatch.setattr(listener, name, str(tmp_path / name))
    monkeypatch.setattr(listener, 'load_button_config', lambda: ['L1', 'R1'])
    monkeypatch.setattr(listener, 'find_steam_hidraw', lambda: iter([('/dev/hidraw0', 'steam_deck')]))
    scans = []
    def discover(pattern):
        scans.append(pattern)
        return [] if len(scans) == 1 else ['/dev/input/event0']
    monkeypatch.setattr(listener.glob, 'glob', discover)
    ticks = iter(range(0, 100, 3))
    monkeypatch.setattr(listener.time, 'monotonic', lambda: next(ticks))

    class Raw:
        fd = 10
        closed = False
        def __init__(self, path):
            pass
        def close(self):
            self.closed = True
    class Pad(Raw):
        fd = 11
        reads = 0
        identity = {'vendor_id': 0x045e, 'product_id': 0x0b13, 'bus': 5}
        supported_buttons = {'L1', 'R1'}
        def states(self):
            return {'L1': False, 'R1': False}
        def read_states(self):
            self.reads += 1
            if self.reads == 1:
                yield {'L1': True, 'R1': True}
            else:
                raise OSError('unplugged')
    monkeypatch.setattr(listener, 'RawGamepad', Raw)
    monkeypatch.setattr(listener, 'EvdevGamepad', Pad)

    class Selector:
        calls = 0
        registered = {}
        def register(self, fd, events, path):
            self.registered[fd] = path
        def unregister(self, fd):
            del self.registered[fd]
        def select(self, timeout):
            self.calls += 1
            state = (tmp_path / 'STATE_FILE').read_text()
            if self.calls == 1:
                assert state == '0'
                assert 11 not in self.registered
                return []
            if self.calls in (2, 3):
                assert state == ('0' if self.calls == 2 else '1')
                if self.calls == 3:
                    import json
                    captured = json.loads((tmp_path / 'HAPTIC_SOURCE_FILE').read_text())
                    assert captured['path'] == '/dev/input/event0'
                    assert captured['identity']['vendor_id'] == 0x045e
                return [(SimpleNamespace(data=self.registered[11]), 1)]
            assert state == '0'
            raise KeyboardInterrupt
        def close(self):
            pass
    monkeypatch.setattr(listener.selectors, 'DefaultSelector', Selector)
    listener.main()
    assert not (tmp_path / 'STATE_FILE').exists()
    import json
    events = [json.loads(line[len(listener.DIAGNOSTIC_PREFIX):])
              for line in capsys.readouterr().out.splitlines()
              if line.startswith(listener.DIAGNOSTIC_PREFIX)]
    active = next(event for event in events if event['event'] == 'active_changed')
    assert active['current_controller']['controller_type'] == 'xbox'
    assert active['current_controller']['connection'] == 'bluetooth'
    assert active['current_controller']['combo_supported'] is True
    assert active['source_count'] == 2
    assert any(event['event'] == 'first_input' for event in events)
    disconnected = next(event for event in events if event['event'] == 'disconnected')
    assert disconnected['current_controller'] == {}
    assert disconnected['affected_controller']['vendor_id'] == 0x045e


def test_triton_puck_reports_buttons_and_disconnect(listener, monkeypatch):
    packets = []
    state = bytearray(64)
    state[0] = 0x42
    struct.pack_into('<I', state, 2, listener.TRITON_BUTTON_BITS['L1'] |
                     listener.TRITON_BUTTON_BITS['R1'])
    packets.extend((bytes(state), b'\x79\x01'))
    monkeypatch.setattr(listener.os, 'open', lambda *args: 42)
    monkeypatch.setattr(listener.os, 'read', lambda *args: packets.pop(0))
    device = listener.TritonGamepad('/dev/hidraw4')
    assert list(device.read_states())[0]['L1']
    assert list(device.read_states())[0]['R1'] is False
    details = listener.controller_details(device, 'steam_controller_2026_puck')
    assert details['product_id'] == 0x1304
    assert {'L1', 'R1'}.issubset(details['supported_buttons'])
