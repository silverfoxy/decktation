"""
Unit tests for parse_channel_and_text with unified commands schema.

This is the most critical logic in the voice service: if parsing is wrong,
messages silently land in the wrong chat channel in-game.
"""

import pytest
from wow_voice_chat import WoWVoiceChat


WOW_PRESET = {
    "name": "World of Warcraft",
    "chat_open_key": "enter",
    "chat_send_key": "enter",
    "default_command": "/s ",
    "commands": {
        "/s ": "say",
        "/p ": ["party", "group"],
        "/raid ": "raid",
        "/g ": "guild",
        "/o ": "officer",
        "/y ": "yell",
        "/i ": "instance",
        "/1 ": "general",
        "/2 ": "trade",
        "/3 ": "local defense",
        "/w ": "whisper",
        "/": "slash",
        "": "type",
        "/rw ": "alert",
    },
    "whisper_prompt": "World of Warcraft gameplay.",
    "context_file": "wow_context.json",
    "casual_case": True,
}

GENERIC_PRESET = {
    "name": "Generic",
    "chat_open_key": None,
    "chat_send_key": None,
    "default_command": "",
    "commands": {"": "type"},
    "whisper_prompt": "",
    "casual_case": False,
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
        cmd, text = wow_svc.parse_channel_and_text("party let's go")
        assert cmd == "/p "
        assert text == "let's go"

    def test_colon_separator(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("party: pull boss")
        assert cmd == "/p "
        assert text == "pull boss"

    def test_comma_separator(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("party, I need mana")
        assert cmd == "/p "
        assert text == "i need mana"

    def test_period_separator(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("party. ready?")
        assert cmd == "/p "
        assert text == "ready?"

    def test_case_insensitive(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("Party: hello")
        assert cmd == "/p "
        assert text == "hello"

    def test_mixed_case(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("RAID pull now")
        assert cmd == "/raid "
        assert text == "pull now"

    def test_alias_group(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("group let's go")
        assert cmd == "/p "
        assert text == "let's go"

    def test_slash_command(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("slash dance")
        assert cmd == "/"
        assert text == "dance"


# ---------------------------------------------------------------------------
# WoW preset - all channels
# ---------------------------------------------------------------------------

class TestWoWChannels:
    @pytest.mark.parametrize("prefix,expected_cmd", [
        ("say", "/s "),
        ("party", "/p "),
        ("group", "/p "),
        ("raid", "/raid "),
        ("guild", "/g "),
        ("officer", "/o "),
        ("yell", "/y "),
        ("instance", "/i "),
        ("general", "/1 "),
        ("trade", "/2 "),
        ("local defense", "/3 "),
        ("whisper", "/w "),
        ("slash", "/"),
        ("type", ""),
        ("alert", "/rw "),
    ])
    def test_channel_prefix_recognized(self, wow_svc, prefix, expected_cmd):
        cmd, text = wow_svc.parse_channel_and_text(f"{prefix} hello")
        assert cmd == expected_cmd
        assert text == "hello"

    def test_message_preserved(self, wow_svc):
        _, text = wow_svc.parse_channel_and_text("raid: focus adds first please")
        assert text == "focus adds first please"

    def test_leading_whitespace_stripped(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("  party let's go")
        assert cmd == "/p "
        assert text == "let's go"

    def test_no_prefix_uses_default(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("hello everyone")
        assert cmd == "/s "
        assert text == "hello everyone"

    def test_partial_channel_name_not_matched(self, wow_svc):
        # "par" is not a valid channel; should fall through to default
        cmd, _ = wow_svc.parse_channel_and_text("par hello")
        assert cmd == "/s "

    def test_channel_name_alone_no_separator(self, wow_svc):
        # "party" with a trailing space is stripped to "party" (no separator) -> default command
        cmd, text = wow_svc.parse_channel_and_text("party ")
        assert cmd == "/s "
        assert text == "party"


# ---------------------------------------------------------------------------
# Generic preset - no channel prefixes
# ---------------------------------------------------------------------------

class TestGenericPreset:
    def test_default_command_is_empty(self, generic_svc):
        assert generic_svc.default_command == ""

    def test_no_channel_keywords(self, generic_svc):
        # "party" is not a command in the generic preset, treated as plain text
        cmd, text = generic_svc.parse_channel_and_text("party let's go")
        assert cmd == ""
        assert text == "party let's go"

    def test_plain_text_routed_to_type(self, generic_svc):
        cmd, text = generic_svc.parse_channel_and_text("hello world")
        assert cmd == ""
        assert text == "hello world"


class TestMultiLanguageCommands:
    def test_french_triggers_loaded_when_selected(self):
        preset = {
            "default_command": "/s ",
            "commands": {
                "/s ": {"en": ["say"], "fr": ["dis", "dire"]},
                "/p ": {"en": ["party"], "fr": ["groupe"]},
                "/y ": {"en": ["yell"], "fr": ["crie"]},
            },
        }
        svc_fr = WoWVoiceChat(preset=preset, transcription_language="fr", lazy_load=True)
        cmd, text = svc_fr.parse_channel_and_text("groupe on y va")
        assert cmd == "/p "
        assert text == "on y va"

        cmd, text = svc_fr.parse_channel_and_text("dis salut")
        assert cmd == "/s "
        assert text == "salut"


class TestCasualCase:
    def test_trailing_period_stripped_for_casual_chat(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("party haha.")
        assert cmd == "/p "
        assert text == "haha"

    def test_initial_letter_lowercased_for_casual_chat(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("party Thanks")
        assert cmd == "/p "
        assert text == "thanks"

    def test_exclamation_and_question_marks_preserved(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("party ready?")
        assert cmd == "/p "
        assert text == "ready?"

        cmd, text = wow_svc.parse_channel_and_text("party let's go!")
        assert cmd == "/p "
        assert text == "let's go!"

    def test_all_caps_acronyms_preserved(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("trade WTB silk cloth")
        assert cmd == "/2 "
        assert text == "WTB silk cloth"

    def test_slash_commands_formatted_casually(self, wow_svc):
        cmd, text = wow_svc.parse_channel_and_text("slash reload.")
        assert cmd == "/"
        assert text == "reload"

        cmd, text = wow_svc.parse_channel_and_text("slash Sit.")
        assert cmd == "/"
        assert text == "sit"

    def test_generic_preset_does_not_modify_casing(self, generic_svc):
        cmd, text = generic_svc.parse_channel_and_text("Hello World. I am here.")
        assert cmd == ""
        assert text == "Hello World. I am here."

