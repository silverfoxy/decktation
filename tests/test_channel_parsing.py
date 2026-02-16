"""
Unit tests for parse_channel_and_text.

This is the most critical logic in the voice service: if parsing is wrong,
messages silently land in the wrong chat channel in-game.
"""

import pytest
from wow_voice_chat import WoWVoiceChat


WOW_PRESET = {
    "name": "World of Warcraft",
    "chat_open_key": "enter",
    "chat_send_key": "enter",
    "default_channel": "say",
    "channels": {
        "say": "/s ",
        "party": "/p ",
        "raid": "/raid ",
        "guild": "/g ",
        "officer": "/o ",
        "yell": "/y ",
        "instance": "/i ",
        "whisper": "/w ",
        "type": "",
    },
    "whisper_prompt": "World of Warcraft gameplay.",
    "context_file": "wow_context.json",
}

GENERIC_PRESET = {
    "name": "Generic",
    "chat_open_key": None,
    "chat_send_key": None,
    "default_channel": "type",
    "channels": {"type": ""},
    "whisper_prompt": "",
}


@pytest.fixture
def wow_svc():
    return WoWVoiceChat(preset=WOW_PRESET, lazy_load=True)


@pytest.fixture
def generic_svc():
    return WoWVoiceChat(preset=GENERIC_PRESET, lazy_load=True)


# ---------------------------------------------------------------------------
# WoW preset - separator variants
# ---------------------------------------------------------------------------

class TestWoWChannelSeparators:
    """All four separator styles should work for each channel."""

    def test_space_separator(self, wow_svc):
        ch, text = wow_svc.parse_channel_and_text("party let's go")
        assert ch == "party"
        assert text == "let's go"

    def test_colon_separator(self, wow_svc):
        ch, text = wow_svc.parse_channel_and_text("party: pull boss")
        assert ch == "party"
        assert text == "pull boss"

    def test_comma_separator(self, wow_svc):
        ch, text = wow_svc.parse_channel_and_text("party, I need mana")
        assert ch == "party"
        assert text == "I need mana"

    def test_period_separator(self, wow_svc):
        ch, text = wow_svc.parse_channel_and_text("party. ready?")
        assert ch == "party"
        assert text == "ready?"

    def test_case_insensitive(self, wow_svc):
        ch, text = wow_svc.parse_channel_and_text("Party: hello")
        assert ch == "party"
        assert text == "hello"

    def test_mixed_case(self, wow_svc):
        ch, text = wow_svc.parse_channel_and_text("RAID pull now")
        assert ch == "raid"
        assert text == "pull now"


# ---------------------------------------------------------------------------
# WoW preset - all channels
# ---------------------------------------------------------------------------

class TestWoWChannels:
    @pytest.mark.parametrize("prefix,expected_channel", [
        ("say", "say"),
        ("party", "party"),
        ("raid", "raid"),
        ("guild", "guild"),
        ("officer", "officer"),
        ("yell", "yell"),
        ("instance", "instance"),
        ("whisper", "whisper"),
        ("type", "type"),
    ])
    def test_channel_prefix_recognized(self, wow_svc, prefix, expected_channel):
        ch, text = wow_svc.parse_channel_and_text(f"{prefix} hello")
        assert ch == expected_channel

    def test_message_preserved(self, wow_svc):
        _, text = wow_svc.parse_channel_and_text("raid: focus adds first please")
        assert text == "focus adds first please"

    def test_leading_whitespace_stripped(self, wow_svc):
        # parse_channel_and_text strips the input, so leading whitespace is ignored
        ch, text = wow_svc.parse_channel_and_text("  party let's go")
        assert ch == "party"
        assert text == "let's go"

    def test_no_prefix_uses_default(self, wow_svc):
        ch, text = wow_svc.parse_channel_and_text("hello everyone")
        assert ch == "say"
        assert text == "hello everyone"

    def test_partial_channel_name_not_matched(self, wow_svc):
        # "par" is not a valid channel; should fall through to default
        ch, _ = wow_svc.parse_channel_and_text("par hello")
        assert ch == "say"

    def test_channel_name_alone_no_separator(self, wow_svc):
        # "party" with a trailing space is stripped to "party" (no separator) → default channel
        ch, text = wow_svc.parse_channel_and_text("party ")
        assert ch == "say"
        assert text == "party"


# ---------------------------------------------------------------------------
# Generic preset - no channel prefixes
# ---------------------------------------------------------------------------

class TestGenericPreset:
    def test_default_channel_is_type(self, generic_svc):
        assert generic_svc.default_channel == "type"

    def test_no_channel_keywords(self, generic_svc):
        # "party" is not a channel in the generic preset, treated as plain text
        ch, text = generic_svc.parse_channel_and_text("party let's go")
        assert ch == "type"
        assert text == "party let's go"

    def test_plain_text_routed_to_type(self, generic_svc):
        ch, text = generic_svc.parse_channel_and_text("hello world")
        assert ch == "type"
        assert text == "hello world"
