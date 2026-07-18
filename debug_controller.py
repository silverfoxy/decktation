#!/usr/bin/env python3
"""Debug controller detection"""
import sys
import evdev

print("Available input devices:")
for path in evdev.list_devices():
    try:
        device = evdev.InputDevice(path)
        name_lower = device.name.lower()
        print(f"\n{path}: {device.name}")
        print(f"  Name (lowercase): {name_lower}")

        caps = device.capabilities()
        print(f"  Capabilities: {list(caps.keys())}")

        # Check for EV_KEY (key/button events)
        if 1 in caps:
            key_codes = caps[1]
            gamepad_buttons = [code for code in [304, 305, 307, 308, 310, 311] if code in key_codes]
            print(f"  Has EV_KEY: Yes ({len(key_codes)} codes)")
            print(f"  Gamepad buttons (304,305,307,308,310,311): {gamepad_buttons}")

            # Check name matching
            keywords = ["x-box 360", "xbox 360", "gamepad", "steam deck controller", "valve"]
            matching_keywords = [kw for kw in keywords if kw in name_lower]
            print(f"  Matching keywords: {matching_keywords}")

            has_gamepad_buttons = len(gamepad_buttons) > 0
            has_keyword_match = len(matching_keywords) > 0

            if has_gamepad_buttons and has_keyword_match:
                print(f"  *** WOULD SELECT THIS DEVICE ***")
        else:
            print(f"  Has EV_KEY: No")

    except Exception as e:
        print(f"Error reading {path}: {e}")
