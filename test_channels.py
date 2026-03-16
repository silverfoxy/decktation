#!/usr/bin/env python3
"""Test multi-language channel detection"""

import sys
import json
from pathlib import Path

# Test just the parsing logic without loading the full module
# Load the language config and implement parse_channel_and_text

config_file = Path(__file__).parent / "channel_languages.json"
if not config_file.exists():
    print("Error: channel_languages.json not found")
    sys.exit(1)

with open(config_file) as f:
    config = json.load(f)

# Build trigger lookup
channel_triggers = {}
enabled_languages = config.get("enabled_languages", ["en"])
languages = config.get("languages", {})

for lang_code in enabled_languages:
    if lang_code not in languages:
        continue
    lang_data = languages[lang_code]
    channels = lang_data.get("channels", {})
    for channel_name, triggers in channels.items():
        for trigger in triggers:
            channel_triggers[trigger.lower()] = channel_name

channel_commands = config.get("channel_commands", {})
default_channel = config.get("default_channel", "say")

def parse_channel_and_text(text):
    """Parse channel prefix from text using multi-language triggers"""
    text = text.strip()
    text_lower = text.lower()

    for trigger, channel_name in channel_triggers.items():
        prefixes = [
            f"{trigger}:",
            f"{trigger},",
            f"{trigger}.",
            f"{trigger} ",
        ]
        for prefix in prefixes:
            if text_lower.startswith(prefix):
                message = text[len(prefix):].strip()
                return channel_name, message

    return default_channel, text

# Test cases: (input, expected_channel, expected_message)
test_cases = [
    # English
    ("party let's go", "party", "let's go"),
    ("raid pull boss", "raid", "pull boss"),
    ("guild hello everyone", "guild", "hello everyone"),
    ("say hi there", "say", "hi there"),
    ("type test message", "type", "test message"),
    ("yell help!", "yell", "help!"),

    # French
    ("groupe allons-y", "party", "allons-y"),
    ("raid attaquez le boss", "raid", "attaquez le boss"),
    ("guilde bonjour tout le monde", "guild", "bonjour tout le monde"),
    ("dis salut", "say", "salut"),
    ("tape message de test", "type", "message de test"),
    ("crie à l'aide!", "yell", "à l'aide!"),

    # With separators
    ("party: need healer", "party", "need healer"),
    ("groupe, on y va", "party", "on y va"),
    ("raid. ready check", "raid", "ready check"),

    # Mixed/no prefix
    ("hello world", "say", "hello world"),
    ("bonjour", "say", "bonjour"),
]

print("Testing multi-language channel detection:")
print("=" * 60)

passed = 0
failed = 0

for input_text, expected_channel, expected_message in test_cases:
    channel, message = parse_channel_and_text(input_text)

    if channel == expected_channel and message == expected_message:
        print(f"✓ '{input_text}'")
        print(f"  → {channel}: '{message}'")
        passed += 1
    else:
        print(f"✗ '{input_text}'")
        print(f"  Expected: {expected_channel}: '{expected_message}'")
        print(f"  Got:      {channel}: '{message}'")
        failed += 1

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed")

# Show loaded triggers
print("\nLoaded channel triggers:")
for trigger, channel in sorted(channel_triggers.items()):
    cmd = channel_commands.get(channel, "")
    print(f"  '{trigger}' → {channel} ({cmd!r})")
