"""Legion Go 60-byte HID input report (USB 17ef:6182/6183/6184/61eb, interface 2).

Layout and paddle names follow InputPlumber v0.78.0:
https://github.com/ShadowBlip/InputPlumber/blob/v0.78.0/src/drivers/lego/hid_report.rs
https://github.com/ShadowBlip/InputPlumber/blob/v0.78.0/src/input/source/hidraw/legion_go.rs
InputPlumber's go2_driver.rs uses the same XInputDataReport for product 61eb.
Only physical controls are decoded; no device configuration or grabbing is needed.
"""

REPORT_SIZE = 60
BUTTON_BITS = {
    'L3': (18, 0x20), 'R3': (18, 0x10),
    'D-pad Up': (18, 0x08), 'D-pad Down': (18, 0x04),
    'D-pad Left': (18, 0x02), 'D-pad Right': (18, 0x01),
    'A': (19, 0x80), 'B': (19, 0x40), 'X': (19, 0x20), 'Y': (19, 0x10),
    'L1': (19, 0x08), 'L2': (19, 0x04), 'R1': (19, 0x02), 'R2': (19, 0x01),
    'L4': (20, 0x80), 'L5': (20, 0x40),  # Y1/Y2
    'R4': (20, 0x20), 'R5': (20, 0x04),  # Y3/M3
    'View': (20, 0x02), 'Menu': (20, 0x01),
}


def button_states(report):
    """Ignore configuration replies; release controls outside gamepad modes."""
    if len(report) != REPORT_SIZE or report[0] != 0x04 or report[2] != 0x74:
        return None
    if report[9] not in (0, 1):  # XInput / DInput; FPS controls are mouse inputs.
        return dict.fromkeys(BUTTON_BITS, False)
    states = {name: bool(report[byte] & mask)
              for name, (byte, mask) in BUTTON_BITS.items()}
    states['L2'] |= report[22] >= 128
    states['R2'] |= report[23] >= 128
    return states
