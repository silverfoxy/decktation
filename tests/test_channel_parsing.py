"""
Unit tests for parse_channel_and_text.

This is the most critical logic in the voice service: if parsing is wrong,
messages silently land in the wrong chat channel in-game.
"""

import json
from pathlib import Path

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
        "reply": "/r ",
        "type": "",
        "alert": "/rw ",
        "channel_1": "/1 ",
        "channel_2": "/2 ",
        "channel_3": "/3 ",
        "channel_4": "/4 ",
        "channel_5": "/5 ",
    },
    "whisper_prompt": "World of Warcraft gameplay.",
    "context_file": "wow_context.json",
    "casual_case": True,
}

GENERIC_PRESET = {
    "name": "Generic",
    "chat_open_key": None,
    "chat_send_key": None,
    "default_channel": "type",
    "channels": {"type": ""},
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
        ("reply", "reply"),
        ("type", "type"),
        ("alert", "alert"),
        ("channel one", "channel_1"),
        ("channel two", "channel_2"),
        ("channel three", "channel_3"),
        ("channel four", "channel_4"),
        ("channel five", "channel_5"),
    ])
    def test_channel_prefix_recognized(self, wow_svc, prefix, expected_channel):
        ch, text = wow_svc.parse_channel_and_text(f"{prefix} hello")
        assert ch == expected_channel

    @pytest.mark.parametrize("prefix", ["reply", "Reply:", "REPLY,"])
    def test_reply_prefix_recognized_case_insensitively(self, wow_svc, prefix):
        ch, text = wow_svc.parse_channel_and_text(f"{prefix} on my way")
        assert ch == "reply"
        assert text == "on my way"

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

    @pytest.mark.parametrize("spoken,expected_channel,expected_command", [
        ("channel one hello", "channel_1", "/1 "),
        ("channel two: hello", "channel_2", "/2 "),
        ("channel 3, hello", "channel_3", "/3 "),
        ("CHANNEL FOUR hello", "channel_4", "/4 "),
        ("channel five hello", "channel_5", "/5 "),
    ])
    def test_numbered_channel_prefixes(self, wow_svc, spoken, expected_channel, expected_command):
        channel, text = wow_svc.parse_channel_and_text(spoken)
        assert channel == expected_channel
        assert text == "hello"
        assert wow_svc.channel_commands[channel] == expected_command

    def test_trade_as_message_is_not_a_channel_prefix(self, wow_svc):
        channel, text = wow_svc.parse_channel_and_text("trade me xyz")
        assert channel == "say"
        assert text == "trade me xyz"


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


class TestCasualCase:
    def test_trailing_period_stripped_for_casual_chat(self, wow_svc):
        channel, text = wow_svc.parse_channel_and_text("party haha.")
        assert channel == "party"
        assert text == "haha"

    def test_initial_letter_lowercased_for_casual_chat(self, wow_svc):
        channel, text = wow_svc.parse_channel_and_text("party Thanks")
        assert channel == "party"
        assert text == "thanks"

    def test_exclamation_and_question_marks_preserved(self, wow_svc):
        channel, text = wow_svc.parse_channel_and_text("party ready?")
        assert channel == "party"
        assert text == "ready?"

        channel, text = wow_svc.parse_channel_and_text("party let's go!")
        assert channel == "party"
        assert text == "let's go!"

    def test_all_caps_acronyms_preserved(self, wow_svc):
        channel, text = wow_svc.parse_channel_and_text("guild WTB silk cloth")
        assert channel == "guild"
        assert text == "WTB silk cloth"

    def test_every_standalone_i_is_capitalized(self, wow_svc):
        channel, text = wow_svc.parse_channel_and_text("reply i agree, i can do it.")
        assert channel == "reply"
        assert text == "I agree, I can do it"

    def test_i_inside_words_is_not_capitalized(self, wow_svc):
        channel, text = wow_svc.parse_channel_and_text("party i use an iPhone in raids.")
        assert channel == "party"
        assert text == "I use an iPhone in raids"

    def test_generic_preset_does_not_modify_casing(self, generic_svc):
        channel, text = generic_svc.parse_channel_and_text("Hello World. I am here.")
        assert channel == "type"
        assert text == "Hello World. I am here."


class TestNamedWoWChannels:
    @pytest.fixture
    def named_svc(self):
        path = Path(__file__).resolve().parents[1] / "defaults/game_presets.json"
        preset = json.loads(path.read_text())["wow"]
        return WoWVoiceChat(preset=preset, lazy_load=True)

    @pytest.mark.parametrize("phrase, channel, command", [
        ("general chat", "general_chat", "/1 "),
        ("trade chat", "trade_chat", "/2 "),
        ("local defense chat", "local_defense_chat", "/3 "),
        ("local defence chat", "local_defense_chat", "/3 "),
        ("services chat", "services_chat", "/4 "),
        ("trade services chat", "services_chat", "/4 "),
        ("looking for group chat", "looking_for_group_chat", "/5 "),
        ("lfg chat", "looking_for_group_chat", "/5 "),
    ])
    @pytest.mark.parametrize("separator", [" ", ": ", ", ", ". "])
    def test_named_prefixes_use_shipped_presets(self, named_svc, phrase, channel, command, separator):
        destination, text = named_svc.parse_channel_and_text(phrase.upper() + separator + "hello")
        assert (destination, text) == (channel, "hello")
        assert named_svc.channel_commands[destination] == command

    @pytest.mark.parametrize("message", [
        "trade me a potion", "general advice is welcome", "local defense needs help",
        "services are available", "looking for group tonight", "lfg tonight",
        "trade chatter is busy", "general chat", "trade chat",
    ])
    def test_ordinary_messages_and_trigger_without_message_stay_intact(self, named_svc, message):
        assert named_svc.parse_channel_and_text(message) == ("say", message)

    def test_named_channels_can_be_remapped_without_changing_numbered_routes(self, named_svc):
        preset = {**named_svc.preset, "channels": {**named_svc.channel_commands,
                  "services_chat": "/7 ", "looking_for_group_chat": "/4 "}}
        named_svc.set_preset(preset)
        for phrase, command in [("services chat", "/7 "), ("lfg chat", "/4 "), ("channel four", "/4 ")]:
            channel, text = named_svc.parse_channel_and_text(phrase + " hello")
            assert text == "hello"
            assert named_svc.channel_commands[channel] == command

    def test_wow_named_triggers_do_not_route_generic_or_guildwars2_messages(self, named_svc):
        path = Path(__file__).resolve().parents[1] / "defaults/game_presets.json"
        presets = json.loads(path.read_text())
        for game in ("generic", "guildwars2"):
            named_svc.set_preset(presets[game])
            channel, text = named_svc.parse_channel_and_text("trade chat hello")
            assert channel == presets[game]["default_channel"]
            assert text == "trade chat hello"
