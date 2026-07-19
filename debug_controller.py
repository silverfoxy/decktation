#!/usr/bin/env python3
"""Print physical Steam Deck button transitions from raw HID reports."""

import time

from controller_listener import find_steam_deck_hidraw
from deck_hid import STEAM_DECK_BUTTON_BITS, raw_button_states


def main():
    previous = {name: False for name in STEAM_DECK_BUTTON_BITS}

    while True:
        path = find_steam_deck_hidraw()
        if not path:
            print("Steam Deck raw HID interface not found; retrying...", flush=True)
            time.sleep(2)
            continue

        print(f"Listening on {path}; press Ctrl+C to stop", flush=True)
        try:
            with open(path, "r+b", buffering=0) as device:
                while True:
                    report = device.read(64)
                    if not report:
                        raise OSError("empty HID report")
                    states = raw_button_states(report)
                    if states is None:
                        continue
                    for name, pressed in states.items():
                        if pressed != previous[name]:
                            previous[name] = pressed
                            state = "pressed" if pressed else "released"
                            print(f"{name}: {state}", flush=True)
        except OSError as error:
            print(f"Raw HID disconnected: {error}; retrying...", flush=True)
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
