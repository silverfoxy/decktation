"""Decode the Steam Deck's raw 64-byte controller state report.

These offsets mirror the ``ID_CONTROLLER_DECK_STATE`` mapping in Linux's
``drivers/hid/hid-steam.c``.  Reading this report bypasses Steam Input's
per-game virtual controller, so the physical controls remain stable even when
a layout emits keyboard and mouse events instead of XInput events.
"""

# Physical digital button locations: button name -> (byte offset, bit offset).
STEAM_DECK_BUTTON_BITS = {
    "R2": (8, 0),
    "L2": (8, 1),
    "R1": (8, 2),
    "L1": (8, 3),
    "Y": (8, 4),
    "B": (8, 5),
    "X": (8, 6),
    "A": (8, 7),
    "L5": (9, 7),
    "R5": (10, 0),
    "L4": (13, 1),
    "R4": (13, 2),
}

# The Deck also reports uncalibrated 16-bit analog trigger values.  Preserve
# Decktation's previous half-pull behavior instead of requiring the digital
# "fully pressed" bit above.
STEAM_DECK_TRIGGER_OFFSETS = {
    "L2": 44,
    "R2": 46,
}
STEAM_DECK_TRIGGER_THRESHOLD = 16384
STEAM_DECK_REPORT_SIZE = 64
STEAM_DECK_REPORT_TYPE = 9


def raw_button_states(report):
    """Return physical button states from a Steam Deck controller report.

    Short reports are ignored because they may be feature/status reports from
    the same HID interface rather than a complete controller-state report.
    """
    if (
        len(report) != STEAM_DECK_REPORT_SIZE
        or report[0] != 1
        or report[1] != 0
        or report[2] != STEAM_DECK_REPORT_TYPE
    ):
        return None

    states = {
        name: bool(report[byte] & (1 << bit))
        for name, (byte, bit) in STEAM_DECK_BUTTON_BITS.items()
    }

    for name, offset in STEAM_DECK_TRIGGER_OFFSETS.items():
        analog_value = int.from_bytes(report[offset:offset + 2], "little")
        states[name] = (
            states[name] or analog_value >= STEAM_DECK_TRIGGER_THRESHOLD
        )

    return states
