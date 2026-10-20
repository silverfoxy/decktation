"""Synthetic replay of InputPlumber's Legion Go S XInputDataReport layout.

These fixtures check our parser, not parallel HIDRAW access on a real Go S.
"""

import importlib
import json
import os
from types import SimpleNamespace

import pytest


def test_y1_y2_and_shoulder_buttons_decode_independently():
    from legion_go_s import button_states

    report = bytearray(32)
    report[1] = 0x11  # A and LB
    report[2] = 0x01  # Y1
    state = button_states(report)
    assert state['A'] and state['L1'] and state['L4']
    assert not state['R1'] and not state['R4']

    report[1] = 0x40  # RB only
    report[2] = 0x02  # Y2 only
    state = button_states(report)
    assert state['R1'] and state['R4']
    assert not state['L1'] and not state['L4'] and not state['A']
    assert button_states(bytes(31)) is None


@pytest.mark.parametrize('hid_id,interface,accepted', [
    ('0003:00001A86:0000E310', '06', True),
    ('0003:00001A86:0000E311', '06', True),
    ('0003:00001A86:0000E310', '02', False),
    ('0003:00001A86:0000E310', '05', False),
    ('0003:000028DE:00001205', '06', False),
    ('0006:00001A86:0000E310', '06', False),
])
def test_discovers_only_physical_gamepad_interface(monkeypatch, tmp_path, hid_id, interface, accepted):
    listener = importlib.import_module('controller_listener')
    usb_interface = tmp_path / 'usb' / '1-1:1.6'
    hid_device = usb_interface / '0003:1A86:E310.0001'
    hid_device.mkdir(parents=True)
    (usb_interface / 'bInterfaceNumber').write_text(interface + '\n')
    (hid_device / 'uevent').write_text(f'HID_ID={hid_id}\n')
    node = tmp_path / 'hidraw0'
    node.mkdir()
    (node / 'device').symlink_to(hid_device, target_is_directory=True)
    monkeypatch.setattr(listener.glob, 'glob', lambda pattern: ['/dev/hidraw0'])
    assert list(listener.find_hidraw(sysfs_root=str(tmp_path))) == (
        [('/dev/hidraw0', 'legion_go_s')] if accepted else [])


def test_reader_opens_read_only_and_yields_physical_paddle_states(monkeypatch):
    listener = importlib.import_module('controller_listener')
    opened = []
    closed = []
    reports = iter([bytes([0, 0x10, 0x01] + [0] * 29), bytes([0, 0x40, 0x02] + [0] * 29)])
    monkeypatch.setattr(listener.os, 'open', lambda path, flags: opened.append((path, flags)) or 42)
    monkeypatch.setattr(listener.os, 'read', lambda fd, length: next(reports))
    monkeypatch.setattr(listener.os, 'close', closed.append)
    gamepad = listener.HidGamepad('/dev/hidraw9', listener.PROFILES_BY_KIND['legion_go_s'])
    assert opened == [('/dev/hidraw9', os.O_RDONLY | os.O_NONBLOCK)]
    assert gamepad.profile.kind == 'legion_go_s'
    assert {'L1', 'R1', 'L4', 'R4'}.issubset(gamepad.supported_buttons)
    assert {name for name, pressed in next(gamepad.read_states()).items() if pressed} == {'L1', 'L4'}
    assert {name for name, pressed in next(gamepad.read_states()).items() if pressed} == {'R1', 'R4'}
    gamepad.close()
    assert closed == [42]


def test_listener_uses_go_s_hid_buttons_for_combo_and_status(monkeypatch, tmp_path, capsys):
    listener = importlib.import_module('controller_listener')
    monkeypatch.setattr(listener, 'CONFIG_DIR', str(tmp_path))
    for name in ('STATE_FILE', 'PID_FILE', 'PREVIEW_FILE', 'CONTROLLER_TYPE_FILE',
                 'STATUS_FILE', 'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE'):
        monkeypatch.setattr(listener, name, str(tmp_path / name))
    monkeypatch.setattr(listener, 'load_button_config', lambda: ['L4', 'R4'])
    monkeypatch.setattr(listener, 'find_hidraw',
                        lambda: iter([('/dev/hidraw9', 'legion_go_s')]))
    monkeypatch.setattr(listener.glob, 'glob', lambda pattern: [])

    class GoS:
        fd = 42
        identity = {'bus': 3, 'vendor_id': 0x1a86, 'product_id': 0xe310}
        supported_buttons = {'L1', 'R1', 'L4', 'R4'}
        def __init__(self, path, product_id=None):
            assert (path, product_id) == ('/dev/hidraw9', None)
        def read_states(self):
            yield {'L1': False, 'R1': False, 'L4': True, 'R4': True}
        def close(self):
            pass
    monkeypatch.setattr(listener, 'HidGamepad', lambda path, profile: GoS(path))

    class Selector:
        calls = 0
        def register(self, fd, mask, path):
            assert (fd, path) == (42, '/dev/hidraw9')
        def select(self, timeout):
            self.calls += 1
            if self.calls == 1:
                assert (tmp_path / 'STATE_FILE').read_text() == '0'
                return [(SimpleNamespace(data='/dev/hidraw9'), 1)]
            assert (tmp_path / 'STATE_FILE').read_text() == '1'
            assert json.loads((tmp_path / 'HAPTIC_SOURCE_FILE').read_text())['kind'] == 'legion_go_s'
            raise KeyboardInterrupt
        def close(self):
            pass
    monkeypatch.setattr(listener.selectors, 'DefaultSelector', Selector)
    listener.main()
    events = [json.loads(line[len(listener.DIAGNOSTIC_PREFIX):])
              for line in capsys.readouterr().out.splitlines()
              if line.startswith(listener.DIAGNOSTIC_PREFIX)]
    first = next(item for item in events if item['event'] == 'first_input')
    assert first['affected_controller']['combo_supported'] is True
    assert first['affected_controller']['supported_buttons'] == ['L1', 'L4', 'R1', 'R4']
    assert next(item for item in events if item['event'] == 'active_changed')['current_controller']['controller_type'] == 'legion_go_s'


def test_real_selector_delivers_a_legion_report_to_the_combo(monkeypatch, tmp_path):
    import selectors
    listener = importlib.import_module('controller_listener')
    monkeypatch.setattr(listener, 'CONFIG_DIR', str(tmp_path))
    for name in ('STATE_FILE', 'PID_FILE', 'PREVIEW_FILE', 'CONTROLLER_TYPE_FILE',
                 'STATUS_FILE', 'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE'):
        monkeypatch.setattr(listener, name, str(tmp_path / name))
    monkeypatch.setattr(listener, 'load_button_config', lambda: ['L4', 'R4'])
    monkeypatch.setattr(listener, 'find_hidraw',
                        lambda: iter([('/dev/hidraw9', 'legion_go_s')]))
    monkeypatch.setattr(listener.glob, 'glob', lambda pattern: [])
    reader, writer = os.pipe()
    report = bytearray(32)
    report[2] = 0x03  # Both physical rear buttons.
    os.write(writer, report)

    class PipeGoS(listener.HidGamepad):
        def __init__(self, path, profile):
            self.profile = profile
            self.fd = reader
            self.identity = {'bus': 3, 'vendor_id': 0x1a86, 'product_id': 0xe310}
            self.supported_buttons = {'L4', 'R4'}
    monkeypatch.setattr(listener, 'HidGamepad', PipeGoS)
    class Selector(selectors.DefaultSelector):
        calls = 0
        def select(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                return super().select(timeout)
            assert (tmp_path / 'STATE_FILE').read_text() == '1'
            raise KeyboardInterrupt
    monkeypatch.setattr(listener.selectors, 'DefaultSelector', Selector)
    try:
        listener.main()
    finally:
        os.close(writer)
    assert not (tmp_path / 'STATE_FILE').exists()


def test_diagnostic_report_retains_legion_hid_source_and_paddles():
    from controller_debug_report import InputReport, sanitize_report

    report = InputReport('synthetic', 0.0, ['L4', 'R4'])
    report.device('/dev/hidraw9', 'hidraw', {
        'input_backend': 'hidraw', 'controller_type': 'legion_go_s',
        'bindings_accepted': True, 'diagnostic_observed': True,
        'bus': 3, 'vendor_id': 0x1a86, 'product_id': 0xe310})
    report.initial('/dev/hidraw9', None, (), 0.0)
    report.event('/dev/hidraw9', 'hid', 0.1, button='L4', pressed=True)
    result = sanitize_report(report.snapshot(1.0))
    assert result['devices'][0]['controller_type'] == 'legion_go_s'
    assert result['events'][0]['button'] == 'L4'
