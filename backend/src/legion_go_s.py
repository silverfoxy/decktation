"""Lenovo Legion Go S 32-byte XInput HID report (USB 1a86:e310/e311, interface 6).

Bit positions follow InputPlumber's XInputDataReport in
src/drivers/legion_go_s/hid_report.rs. Only physical controls are decoded;
there is no keyboard input, report payload logging, or device grabbing.
"""

REPORT_SIZE = 32
# name -> (byte, mask). Y1/Y2 are the two physical rear buttons.
BUTTON_BITS = {
    'A': (1, 0x01), 'B': (1, 0x02), 'X': (1, 0x04), 'Y': (1, 0x08),
    'L1': (1, 0x10), 'R1': (1, 0x40),
    'L2': (1, 0x20), 'R2': (1, 0x80),
    'L4': (2, 0x01), 'R4': (2, 0x02),
    'View': (2, 0x40), 'Menu': (2, 0x80),
    'L3': (0, 0x04), 'R3': (0, 0x08),
    'D-pad Up': (0, 0x10), 'D-pad Down': (0, 0x20),
    'D-pad Left': (0, 0x40), 'D-pad Right': (0, 0x80),
}


def button_states(report):
    """Return mapped buttons, or None for non-controller/short HID reports."""
    if len(report) != REPORT_SIZE:
        return None
    states = {name: bool(report[byte] & mask)
              for name, (byte, mask) in BUTTON_BITS.items()}
    # Analog triggers can be pressed without the digital full-pull bit.
    states['L2'] |= report[12] >= 128
    states['R2'] |= report[13] >= 128
    return states
