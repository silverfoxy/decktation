#!/usr/bin/env python3
"""Manual test for preset command detection"""

import json
from pathlib import Path

presets_file = Path(__file__).parents[2] / "defaults" / "game_presets.json"
if not presets_file.exists():
    print("Error: game_presets.json not found")
    raise SystemExit(1)

with open(presets_file) as f:
    presets = json.load(f)

wow_preset = presets.get("wow", {})
commands = wow_preset.get("commands", {})
default_command = wow_preset.get("default_command", "/s ")

command_triggers = {}
for cmd_prefix, definition in commands.items():
    if isinstance(definition, str):
        command_triggers[definition.lower()] = cmd_prefix
    elif isinstance(definition, list):
        for word in definition:
            command_triggers[str(word).lower()] = cmd_prefix


def parse_channel_and_text(text):
    text = text.strip()
    text_lower = text.lower()

    for trigger, cmd_prefix in sorted(command_triggers.items(), key=lambda x: len(x[0]), reverse=True):
        prefixes = [f"{trigger}:", f"{trigger},", f"{trigger}.", f"{trigger} "]
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                return cmd_prefix, text[len(prefix):].strip()

    return default_command, text


if __name__ == "__main__":
    test_cases = [
        ("party let's go", "/p ", "let's go"),
        ("group let's go", "/p ", "let's go"),
        ("slash dance", "/", "dance"),
        ("raid pull boss", "/raid ", "pull boss"),
        ("guild hello everyone", "/g ", "hello everyone"),
        ("say hi there", "/s ", "hi there"),
        ("type test message", "", "test message"),
        ("yell help!", "/y ", "help!"),
        ("hello world", "/s ", "hello world"),
    ]

    passed = 0
    failed = 0
    for input_text, expected_cmd, expected_message in test_cases:
        cmd, message = parse_channel_and_text(input_text)
        if cmd == expected_cmd and message == expected_message:
            print(f"✓ '{input_text}' -> {cmd!r}: '{message}'")
            passed += 1
        else:
            print(f"✗ '{input_text}' (Expected: {expected_cmd!r} '{expected_message}', got: {cmd!r} '{message}')")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
