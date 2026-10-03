"""Decode Valve's raw 64-byte Steam controller state reports.

These offsets mirror the ``ID_CONTROLLER_STATE`` and
``ID_CONTROLLER_DECK_STATE`` mappings in Linux's ``drivers/hid/hid-steam.c``.
Reading these reports bypasses Steam Input's per-game virtual controller, so
the physical controls remain stable even when a layout emits keyboard and
mouse events instead of XInput events.
"""

# Physical digital button locations: button name -> (byte offset, bit offset).
STEAM_DECK_BUTTON_BITS = {
    "View": (9, 4),
    "Menu": (9, 6),
    "L3": (10, 6),
    "R3": (11, 2),
    "D-pad Up": (9, 0),
    "D-pad Right": (9, 1),
    "D-pad Left": (9, 2),
    "D-pad Down": (9, 3),
    "Left Trackpad": (10, 1),
    "Right Trackpad": (10, 2),
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
STEAM_CONTROLLER_REPORT_TYPE = 1

# The original Steam Controller uses the same bits for the controls it shares
# with the Deck.  It has two rear grips; Steam's frontend identifies those as
# L5/R5 (button IDs 32/33), so expose the raw grip bits under the same names.
STEAM_CONTROLLER_BUTTON_BITS = {
    name: location
    for name, location in STEAM_DECK_BUTTON_BITS.items()
    if name not in ("L4", "R4", "R3")
}
STEAM_CONTROLLER_TRIGGER_OFFSETS = {
    "L2": 11,
    "R2": 12,
}
STEAM_CONTROLLER_TRIGGER_THRESHOLD = 128

# Steam Controller (2026 / Triton). Wire layout and button masks are documented
# by SDL's steam/controller_structs.h and SDL_hidapi_steam_triton.c.
TRITON_BUTTON_MASKS = {
    'A': 0x1, 'B': 0x2, 'X': 0x4, 'Y': 0x8,
    'R4': 0x80, 'R5': 0x100, 'R1': 0x200,
    'L4': 0x20000, 'L5': 0x40000, 'L1': 0x80000,
    'R2': 0x800000, 'L2': 0x8000000,
}


def triton_button_states(report):
    """Decode USB/Puck, BLE and timestamped state; ignore other reports.

    All three formats share the sequence byte, 32-bit buttons and triggers.
    Accept extended packets, but require the complete 46-byte base state.
    Wireless disconnect reports release held controls even with the Puck present.
    """
    if len(report) >= 2 and report[0] in (0x46, 0x79):
        return {name: False for name in TRITON_BUTTON_MASKS} if report[1] == 1 else None
    if len(report) < 46 or report[0] not in (0x42, 0x45, 0x47):
        return None
    buttons = int.from_bytes(report[2:6], 'little')
    states = {name: bool(buttons & mask) for name, mask in TRITON_BUTTON_MASKS.items()}
    for name, offset in (('L2', 6), ('R2', 8)):
        states[name] |= int.from_bytes(report[offset:offset + 2], 'little', signed=True) >= 16384
    return states


def raw_button_states(report):
    """Return physical button states from a Valve controller report.

    Short reports are ignored because they may be feature/status reports from
    the same HID interface rather than a complete controller-state report.
    """
    if (
        len(report) != STEAM_DECK_REPORT_SIZE
        or report[0] != 1
        or report[1] != 0
    ):
        return None

    report_type = report[2]
    if report_type == STEAM_DECK_REPORT_TYPE:
        button_bits = STEAM_DECK_BUTTON_BITS
        trigger_offsets = STEAM_DECK_TRIGGER_OFFSETS
        trigger_threshold = STEAM_DECK_TRIGGER_THRESHOLD
    elif report_type == STEAM_CONTROLLER_REPORT_TYPE:
        button_bits = STEAM_CONTROLLER_BUTTON_BITS
        trigger_offsets = STEAM_CONTROLLER_TRIGGER_OFFSETS
        trigger_threshold = STEAM_CONTROLLER_TRIGGER_THRESHOLD
    else:
        return None

    states = {
        name: bool(report[byte] & (1 << bit))
        for name, (byte, bit) in button_bits.items()
    }

    for name, offset in trigger_offsets.items():
        if report_type == STEAM_DECK_REPORT_TYPE:
            analog_value = int.from_bytes(report[offset:offset + 2], "little")
        else:
            analog_value = report[offset]
        states[name] = states[name] or analog_value >= trigger_threshold

    return states
