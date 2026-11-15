"""Source-based HID fixtures; hardware coexistence still needs validation."""
import os

import pytest

from controller_profiles import PROFILES_BY_KIND
from legion_go import button_states


def report():
    data = bytearray(60)
    data[:3] = b'\x04\x3c\x74'
    return data


def test_buttons_paddles_and_analog_triggers():
    data = report()
    data[18] = 0x28  # Left stick click and D-pad up.
    data[19] = 0x8a  # A, LB, RB.
    data[20] = 0xa4  # Y1, Y3, M3.
    data[22] = 128
    data[23] = 127
    states = button_states(data)
    assert {name for name, down in states.items() if down} == {
        'L3', 'D-pad Up', 'A', 'L1', 'R1', 'L4', 'R4', 'R5', 'L2'}
    data[19] = 0x01  # Digital RT also counts below the analog threshold.
    assert button_states(data)['R2']
    assert not any(button_states(report()).values())


def test_configuration_replies_and_short_reports_are_ignored():
    assert button_states(bytes(59)) is None
    data = report()
    data[2] = 0x10
    assert button_states(data) is None
    data = report()
    data[0] = 0x01
    assert button_states(data) is None


def test_fps_mode_releases_held_controls():
    data = report()
    data[19] = 0xff
    data[22] = 255
    data[9] = 2
    assert not any(button_states(data).values())


@pytest.mark.parametrize('product,interface,accepted', [
    (0x6182, '02', True), (0x6183, '02', True), (0x6184, '02', True),
    (0x61eb, '02', True), (0x61eb, '00', False),
    (0x6182, '00', False), (0x6185, '02', False),
])
def test_profile_selects_go_gamepad_interface(tmp_path, product, interface, accepted):
    device = tmp_path / 'hid'
    device.mkdir()
    (tmp_path / 'bInterfaceNumber').write_text(interface)
    profile = PROFILES_BY_KIND['legion_go']
    assert profile.matches({'HID_ID': f'0003:000017EF:{product:08X}'}, str(device)) is accepted
    assert profile.access == os.O_RDONLY


@pytest.mark.parametrize('product', [0x6182, 0x61eb])
def test_hid_reader_delivers_recording_press_and_release(monkeypatch, tmp_path, product):
    import selectors
    import controller_listener as listener

    monkeypatch.setenv('DECKTATION_CONTROLLER_BACKEND', 'legacy')
    monkeypatch.setattr(listener, 'CONFIG_DIR', str(tmp_path))
    for name in ('STATE_FILE', 'PID_FILE', 'PREVIEW_FILE', 'CONTROLLER_TYPE_FILE',
                 'STATUS_FILE', 'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE'):
        monkeypatch.setattr(listener, name, str(tmp_path / name))
    monkeypatch.setattr(listener, 'load_button_config', lambda: ['L1', 'R1'])
    monkeypatch.setattr(listener, 'find_hidraw',
                        lambda: iter([('/dev/hidraw9', 'legion_go')]))
    monkeypatch.setattr(listener.glob, 'glob', lambda pattern: [])
    # Output discovery is separate from input support; this controller test
    # deliberately provides no rumble or chat-submission target.
    monkeypatch.setattr(listener, 'discover_outputs', lambda: [])
    reader, writer = os.pipe()
    held = report()
    held[19] = 0x0a  # Both shoulders, using the upstream HID bit layout.
    os.write(writer, held)

    class PipeGo(listener.HidGamepad):
        def __init__(self, path, profile):
            self.profile = profile
            self.fd = reader
            self.identity = {'bus': 3, 'vendor_id': 0x17ef, 'product_id': product}
            self.supported_buttons = set(profile.buttons)

    monkeypatch.setattr(listener, 'HidGamepad', PipeGo)

    class Selector(selectors.DefaultSelector):
        calls = 0

        def select(self, timeout=None):
            self.calls += 1
            if self.calls == 2:
                assert (tmp_path / 'STATE_FILE').read_text() == '1'
                assert (tmp_path / 'CONTROLLER_TYPE_FILE').read_text() == 'legion_go'
                os.write(writer, report())
            elif self.calls == 3:
                assert (tmp_path / 'STATE_FILE').read_text() == '0'
                raise KeyboardInterrupt
            return super().select(timeout)

    monkeypatch.setattr(listener.selectors, 'DefaultSelector', Selector)
    try:
        listener.main()
    finally:
        os.close(writer)
