from deck_hid import raw_button_states


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


def test_all_rear_grips_are_decoded():
    report = make_report()
    set_bit(report, 13, 1)  # L4
    set_bit(report, 13, 2)  # R4
    set_bit(report, 9, 7)   # L5
    set_bit(report, 10, 0)  # R5

    states = raw_button_states(report)

    assert all(states[name] for name in ("L4", "R4", "L5", "R5"))


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
