"""
Unit tests for send_to_wow_chat key behavior.

Verifies that:
- WoW channels press Enter to open chat and Enter to send
- WoW "type" channel skips both Enter presses
- Generic preset skips both Enter presses for all messages
"""

import pytest
import os
from unittest.mock import patch, call, MagicMock
from wow_voice_chat import WoWVoiceChat


# Linux keycode for Enter used by ydotool
ENTER_PRESS = "28:1"
ENTER_RELEASE = "28:0"


# Mock helper for ydotool path checks
def mock_path_exists(path):
    """Mock os.path.exists to return True for ydotool paths."""
    if "ydotool" in str(path):
        return True
    return os.path.exists.__wrapped__(path) if hasattr(os.path.exists, '__wrapped__') else False


WOW_PRESET = {
    "name": "World of Warcraft",
    "chat_open_key": "enter",
    "chat_send_key": "enter",
    "default_channel": "say",
    "channels": {"say": "/s ", "party": "/p ", "type": ""},
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

GUILDWARS2_PRESET = {
    "name": "Guild Wars 2",
    "chat_open_key": "enter",
    "chat_send_key": "enter",
    "default_channel": "say",
    "channels": {
        "say": "/s ",
        "map": "/m ",
        "party": "/p ",
        "squad": "/d ",
        "team": "/t ",
        "guild": "/g ",
        "guild_one": "/g1 ",
        "whisper": "/w ",
        "type": "",
    },
    "whisper_prompt": "Guild Wars 2 gameplay.",
}


def make_service(preset):
    return WoWVoiceChat(preset=preset, lazy_load=True)


def get_key_calls(mock_run):
    """Extract all ydotool 'key' subprocess.run calls."""
    return [c for c in mock_run.call_args_list if "key" in c.args[0]]


def get_type_calls(mock_run):
    """Extract all ydotool 'type' subprocess.run calls."""
    return [c for c in mock_run.call_args_list if "type" in c.args[0]]


# ---------------------------------------------------------------------------
# WoW preset - normal channels
# ---------------------------------------------------------------------------

class TestWoWSendBehavior:
    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_say_presses_enter_to_open(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("hello world", channel="say")

        key_calls = get_key_calls(mock_run)
        assert len(key_calls) == 2, "Expected 2 Enter keypresses: open + send"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_say_types_channel_prefix(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("hello world", channel="say")

        type_calls = get_type_calls(mock_run)
        assert len(type_calls) == 1
        typed_text = type_calls[0].args[0][-1]  # last arg to ydotool type is the text
        assert typed_text == "/s hello world"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_party_types_party_prefix(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("incoming", channel="party")

        type_calls = get_type_calls(mock_run)
        assert type_calls[0].args[0][-1] == "/p incoming"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_order_is_open_then_type_then_send(self, mock_run, mock_exists):
        """Enter (open), type message, Enter (send) — in that order."""
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("pull boss", channel="say")

        calls = mock_run.call_args_list
        actions = []
        for c in calls:
            cmd = c.args[0]
            if "key" in cmd:
                actions.append("enter")
            elif "type" in cmd:
                actions.append("type")

        assert actions == ["enter", "type", "enter"]


# ---------------------------------------------------------------------------
# Guild Wars 2 preset
# ---------------------------------------------------------------------------

class TestGuildWars2SendBehavior:
    @pytest.mark.parametrize(
        ("channel", "command"),
        [
            ("say", "/s "),
            ("map", "/m "),
            ("party", "/p "),
            ("squad", "/d "),
            ("team", "/t "),
            ("guild", "/g "),
            ("whisper", "/w "),
        ],
    )
    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_channel_opens_types_and_sends(self, mock_run, mock_exists, channel, command):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(GUILDWARS2_PRESET)
        svc.send_to_wow_chat("hello", channel=channel)

        calls = mock_run.call_args_list
        actions = ["enter" if "key" in c.args[0] else "type" for c in calls]
        assert actions == ["enter", "type", "enter"]
        assert get_type_calls(mock_run)[0].args[0][-1] == f"{command}hello"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_spoken_squad_prefix_uses_squad_chat(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(GUILDWARS2_PRESET)
        svc.send_to_wow_chat("squad stack on tag")

        assert get_type_calls(mock_run)[0].args[0][-1] == "/d stack on tag"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_long_guild_number_prefix_wins_over_guild(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(GUILDWARS2_PRESET)
        svc.send_to_wow_chat("guild one hello everyone")

        assert get_type_calls(mock_run)[0].args[0][-1] == "/g1 hello everyone"


# ---------------------------------------------------------------------------
# WoW preset - "type" channel (pure typing, no Enter)
# ---------------------------------------------------------------------------

class TestWoWTypeChannel:
    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_type_channel_no_enter_presses(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("hello", channel="type")

        key_calls = get_key_calls(mock_run)
        assert len(key_calls) == 0, "type channel must not press Enter"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_type_channel_no_prefix_in_text(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("hello world", channel="type")

        type_calls = get_type_calls(mock_run)
        typed = type_calls[0].args[0][-1]
        assert typed == "hello world"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_type_channel_strips_trailing_punctuation(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("hello world.", channel="type")

        type_calls = get_type_calls(mock_run)
        typed = type_calls[0].args[0][-1]
        assert typed == "hello world"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_type_via_parsed_prefix(self, mock_run, mock_exists):
        """'type hello' in WoW preset should route to type channel."""
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("type hello")  # let parser detect channel

        key_calls = get_key_calls(mock_run)
        assert len(key_calls) == 0


# ---------------------------------------------------------------------------
# Generic preset - no Enter presses at all
# ---------------------------------------------------------------------------

class TestGenericSendBehavior:
    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_no_enter_to_open(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(GENERIC_PRESET)
        svc.send_to_wow_chat("search for something", channel="type")

        key_calls = get_key_calls(mock_run)
        assert len(key_calls) == 0, "Generic preset must never press Enter"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_only_types_text(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(GENERIC_PRESET)
        svc.send_to_wow_chat("hello world", channel="type")

        calls = mock_run.call_args_list
        assert len(calls) == 1, "Only one subprocess call: the type command"
        assert "type" in calls[0].args[0]

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_plain_text_no_prefix(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(GENERIC_PRESET)
        svc.send_to_wow_chat("hello world")  # default channel = type

        type_calls = get_type_calls(mock_run)
        typed = type_calls[0].args[0][-1]
        assert typed == "hello world"


# ---------------------------------------------------------------------------
# Empty text short-circuits
# ---------------------------------------------------------------------------

class TestEmptyText:
    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_empty_text_no_subprocess_calls(self, mock_run, mock_exists):
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("")
        mock_run.assert_not_called()

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_none_channel_parsed_from_text(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.send_to_wow_chat("party let's go")  # channel parsed from text

        type_calls = get_type_calls(mock_run)
        typed = type_calls[0].args[0][-1]
        assert typed == "/p let's go"


# ---------------------------------------------------------------------------
# Manual send mode - opens chat and types, but doesn't send
# ---------------------------------------------------------------------------

class TestManualSendMode:
    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_manual_send_presses_enter_to_open(self, mock_run, mock_exists):
        """Manual send should still press Enter to open chat."""
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.manual_send = True
        svc.send_to_wow_chat("hello world", channel="say")

        key_calls = get_key_calls(mock_run)
        # Should have 1 Enter press (open) but not the second (send)
        assert len(key_calls) == 1, "Expected 1 Enter keypress: open only"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_manual_send_types_message(self, mock_run, mock_exists):
        """Manual send should type the message normally."""
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.manual_send = True
        svc.send_to_wow_chat("hello world", channel="say")

        type_calls = get_type_calls(mock_run)
        assert len(type_calls) == 1
        typed_text = type_calls[0].args[0][-1]
        assert typed_text == "/s hello world"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_manual_send_order_is_open_then_type(self, mock_run, mock_exists):
        """Manual send: Enter (open), type message, NO Enter (send)."""
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.manual_send = True
        svc.send_to_wow_chat("pull boss", channel="say")

        calls = mock_run.call_args_list
        actions = []
        for c in calls:
            cmd = c.args[0]
            if "key" in cmd:
                actions.append("enter")
            elif "type" in cmd:
                actions.append("type")

        assert actions == ["enter", "type"], "Should be: open, type (no send)"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_manual_send_works_with_all_channels(self, mock_run, mock_exists):
        """Manual send should work for party, raid, etc."""
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.manual_send = True
        svc.send_to_wow_chat("incoming", channel="party")

        key_calls = get_key_calls(mock_run)
        assert len(key_calls) == 1, "Party channel should also skip send Enter"

        type_calls = get_type_calls(mock_run)
        typed = type_calls[0].args[0][-1]
        assert typed == "/p incoming"

    @patch("os.path.exists", side_effect=mock_path_exists)
    @patch("subprocess.run")
    def test_manual_send_with_type_channel(self, mock_run, mock_exists):
        """Manual send + type channel = no Enter presses at all."""
        mock_run.return_value = MagicMock(returncode=0)
        svc = make_service(WOW_PRESET)
        svc.manual_send = True
        svc.send_to_wow_chat("hello", channel="type")

        key_calls = get_key_calls(mock_run)
        assert len(key_calls) == 0, "type channel never presses Enter, even with manual_send"
