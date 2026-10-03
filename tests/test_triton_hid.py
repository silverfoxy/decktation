"""Protocol regression fixtures from SDL's published Triton wire format."""
import pytest

from deck_hid import triton_button_states, TRITON_BUTTON_MASKS


@pytest.mark.parametrize('report_id,length', [(0x42, 54), (0x45, 46), (0x47, 46)])
@pytest.mark.parametrize('name,mask', TRITON_BUTTON_MASKS.items())
def test_each_physical_button_and_release(report_id, length, name, mask):
    report = bytearray(length)
    report[0] = report_id
    report[2:6] = mask.to_bytes(4, 'little')
    assert {name for name, pressed in triton_button_states(report).items() if pressed} == {name}
    report[2:6] = bytes(4)
    assert not any(triton_button_states(report).values())


@pytest.mark.parametrize('name,offset', [('L2', 6), ('R2', 8)])
def test_half_pull_and_signed_trigger_range(name, offset):
    report = bytearray(54)
    report[0] = 0x42
    for value, expected in [(-1, False), (0, False), (16383, False), (16384, True), (32767, True)]:
        report[offset:offset + 2] = value.to_bytes(2, 'little', signed=True)
        assert triton_button_states(report)[name] == expected


@pytest.mark.parametrize('report', [b'', b'\x42', bytes([0x42]) + bytes(44),
                                    bytes([0x43]) + bytes(53), bytes([0x7b]) + bytes(53)])
def test_partial_and_non_state_reports_ignored(report):
    assert triton_button_states(report) is None


@pytest.mark.parametrize('report_id', [0x46, 0x79])
def test_wireless_disconnect_clears_grips(report_id):
    assert not any(triton_button_states(bytes([report_id, 1])).values())
    assert triton_button_states(bytes([report_id, 2])) is None


def test_grip_combo_is_independent_of_other_gamepad():
    from controller_listener import ComboTracker
    report = bytearray(54)
    report[0] = 0x42
    report[2:6] = (0x80 | 0x100).to_bytes(4, 'little')
    tracker = ComboTracker(['R4', 'R5'])
    assert tracker.update('puck', triton_button_states(report))
    assert tracker.update('xbox', {'A': True})
    assert not tracker.update('puck', triton_button_states(b'\x79\x01'))
