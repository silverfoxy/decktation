from deck_hid import (
    STEAM_CONTROLLER_BUTTON_BITS,
    STEAM_DECK_BUTTON_BITS,
    raw_button_states,
)
from controller_listener import steam_controller_profile


def make_report():
    report = bytearray(64)
    report[0] = 1
    report[2] = 9
    return report


def set_bit(report, byte, bit):
    report[byte] |= 1 << bit


def set_u16(report, offset, value):
    report[offset:offset + 2] = value.to_bytes(2, "little")


def test_face_and_shoulder_buttons_are_decoded():
    report = make_report()
    set_bit(report, 8, 6)  # X
    set_bit(report, 8, 3)  # L1

    states = raw_button_states(report)

    assert states["X"] is True
    assert states["L1"] is True
    assert states["A"] is False
    assert states["R1"] is False


def test_each_digital_button_bit_maps_to_only_its_named_button():
    """One-hot reports catch swapped or overlapping button definitions."""
    for expected_name, (byte, bit) in STEAM_DECK_BUTTON_BITS.items():
        report = make_report()
        set_bit(report, byte, bit)

        states = raw_button_states(report)
        pressed = {name for name, is_pressed in states.items() if is_pressed}

        assert pressed == {expected_name}


def test_triggers_activate_at_half_pull_from_analog_values():
    report = make_report()
    set_u16(report, 44, 16384)
    set_u16(report, 46, 16383)

    states = raw_button_states(report)

    assert states["L2"] is True
    assert states["R2"] is False


def test_trigger_digital_click_is_also_accepted():
    report = make_report()
    set_bit(report, 8, 0)  # R2 fully pressed

    assert raw_button_states(report)["R2"] is True


def test_short_reports_are_ignored():
    assert raw_button_states(bytearray(47)) is None


def test_other_steam_hid_report_types_are_ignored():
    report = make_report()
    report[2] = 4  # Battery status report
    set_bit(report, 8, 6)

    assert raw_button_states(report) is None


def test_original_steam_controller_buttons_are_decoded():
    report = make_report()
    report[2] = 1
    set_bit(report, 8, 3)  # L1
    set_bit(report, 9, 7)  # left rear grip / frontend L5

    states = raw_button_states(report)

    assert states["L1"] is True
    assert states["L5"] is True
    assert states["R5"] is False
    assert "L4" not in states
    assert set(states) == set(STEAM_CONTROLLER_BUTTON_BITS)


def test_original_steam_controller_analog_triggers_activate_at_half_pull():
    report = make_report()
    report[2] = 1
    report[11] = 128
    report[12] = 127

    states = raw_button_states(report)

    assert states["L2"] is True
    assert states["R2"] is False


def test_known_valve_hid_ids_select_the_expected_raw_report_profile():
    assert steam_controller_profile("0003:000028DE:00001205") == {
        "controller_type": "steam_deck",
        "report_type": 9,
    }
    assert steam_controller_profile("0003:000028DE:00001102") == {
        "controller_type": "steam_controller_wired",
        "report_type": 1,
    }
    assert steam_controller_profile("0003:000028DE:00001142") == {
        "controller_type": "steam_controller_wireless",
        "report_type": 1,
    }
    assert steam_controller_profile("0003:000028DE:0000FFFF") is None
