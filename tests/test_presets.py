"""
Unit tests for game preset loading and switching.

Covers: constructor preset wiring, set_preset live switching,
game_presets.json structural validity, and user profile overrides.
"""

import json
import os
import pytest
from wow_voice_chat import WoWVoiceChat


PRESETS_FILE = os.path.join(os.path.dirname(__file__), "..", "defaults", "game_presets.json")


# ---------------------------------------------------------------------------
# game_presets.json structure
# ---------------------------------------------------------------------------

class TestPresetsFile:
    """Validate game_presets.json has the expected structure for all presets."""

    @pytest.fixture(scope="class")
    def presets(self):
        with open(PRESETS_FILE) as f:
            return json.load(f)

    REQUIRED_KEYS = {"name", "chat_open_key", "chat_send_key", "default_command", "commands", "whisper_prompt"}

    def test_file_is_valid_json(self, presets):
        assert isinstance(presets, dict)

    def test_required_presets_present(self, presets):
        assert "wow" in presets
        assert "guildwars2" in presets
        assert "generic" in presets

    @pytest.mark.parametrize("preset_id", ["wow", "guildwars2", "generic"])
    def test_required_keys(self, presets, preset_id):
        missing = self.REQUIRED_KEYS - presets[preset_id].keys()
        assert not missing, f"Preset '{preset_id}' missing keys: {missing}"

    def test_wow_default_command_in_commands(self, presets):
        wow = presets["wow"]
        assert wow["default_command"] in wow["commands"]

    def test_generic_default_command_in_commands(self, presets):
        generic = presets["generic"]
        assert generic["default_command"] in generic["commands"]

    def test_guildwars2_default_command_in_commands(self, presets):
        guildwars2 = presets["guildwars2"]
        assert guildwars2["default_command"] in guildwars2["commands"]

    def test_wow_has_enter_keys(self, presets):
        wow = presets["wow"]
        assert wow["chat_open_key"] == "enter"
        assert wow["chat_send_key"] == "enter"

    def test_guildwars2_has_enter_keys(self, presets):
        guildwars2 = presets["guildwars2"]
        assert guildwars2["chat_open_key"] == "enter"
        assert guildwars2["chat_send_key"] == "enter"

    def test_guildwars2_chat_commands(self, presets):
        commands = presets["guildwars2"]["commands"]
        assert commands["/s "] == "say"
        assert commands["/m "] == "map"
        assert commands["/p "] == "party"
        assert commands["/d "] == ["squad", "raid"]
        assert commands["/t "] == "team"
        assert commands["/g "] == "guild"
        assert commands["/g6 "] == ["guild six", "guild 6"]
        assert commands["/w "] == "whisper"

    def test_generic_has_null_keys(self, presets):
        generic = presets["generic"]
        assert generic["chat_open_key"] is None
        assert generic["chat_send_key"] is None

    def test_wow_has_context_file(self, presets):
        assert "context_file" in presets["wow"]

    def test_generic_has_no_context_file(self, presets):
        assert "context_file" not in presets["generic"]


# ---------------------------------------------------------------------------
# Constructor wiring from preset
# ---------------------------------------------------------------------------

class TestConstructorPreset:
    def test_wow_preset_sets_default_command(self):
        preset = {"default_command": "/s ", "commands": {"/s ": "say"}, "whisper_prompt": ""}
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        assert svc.default_command == "/s "

    def test_generic_preset_sets_default_command(self):
        preset = {"default_command": "", "commands": {"": "type"}, "whisper_prompt": ""}
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        assert svc.default_command == ""

    def test_preset_commands_used(self):
        commands = {"/s ": "say", "/p ": "party"}
        preset = {"default_command": "/s ", "commands": commands, "whisper_prompt": ""}
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        assert svc.commands == commands

    def test_no_preset_falls_back_to_wow_defaults(self):
        svc = WoWVoiceChat(lazy_load=True)
        # Should have WoW commands in fallback
        assert "/s " in svc.command_prefixes
        assert "/p " in svc.command_prefixes
        assert "/raid " in svc.command_prefixes

    def test_preset_stored_on_instance(self):
        preset = {"default_command": "", "commands": {"": "type"}, "whisper_prompt": "test"}
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        assert svc.preset is preset


# ---------------------------------------------------------------------------
# set_preset live switching
# ---------------------------------------------------------------------------

class TestSetPreset:
    def test_switch_updates_default_command(self):
        wow_preset = {"default_command": "/s ", "commands": {"/s ": "say", "": "type"}, "whisper_prompt": ""}
        generic_preset = {"default_command": "", "commands": {"": "type"}, "whisper_prompt": ""}

        svc = WoWVoiceChat(preset=wow_preset, lazy_load=True)
        assert svc.default_command == "/s "

        svc.set_preset(generic_preset)
        assert svc.default_command == ""

    def test_switch_updates_commands(self):
        wow_commands = {"/s ": "say", "/p ": "party", "": "type"}
        generic_commands = {"": "type"}

        wow_preset = {"default_command": "/s ", "commands": wow_commands, "whisper_prompt": ""}
        generic_preset = {"default_command": "", "commands": generic_commands, "whisper_prompt": ""}

        svc = WoWVoiceChat(preset=wow_preset, lazy_load=True)
        svc.set_preset(generic_preset)

        assert svc.commands == generic_commands
        assert "/p " not in svc.command_prefixes

    def test_switch_back_restores_commands(self):
        wow_preset = {"default_command": "/s ", "commands": {"/s ": "say", "/p ": "party", "": "type"}, "whisper_prompt": ""}
        generic_preset = {"default_command": "", "commands": {"": "type"}, "whisper_prompt": ""}

        svc = WoWVoiceChat(preset=wow_preset, lazy_load=True)
        svc.set_preset(generic_preset)
        svc.set_preset(wow_preset)

        assert svc.default_command == "/s "
        assert "/p " in svc.command_prefixes

    def test_switch_affects_command_parsing(self):
        wow_preset = {
            "default_command": "/s ",
            "commands": {"/s ": "say", "/p ": "party", "": "type"},
            "whisper_prompt": "",
        }
        generic_preset = {
            "default_command": "",
            "commands": {"": "type"},
            "whisper_prompt": "",
        }

        svc = WoWVoiceChat(preset=wow_preset, lazy_load=True)
        cmd, _ = svc.parse_channel_and_text("party hello")
        assert cmd == "/p "

        svc.set_preset(generic_preset)
        # "party" is no longer a trigger; falls back to default command ""
        cmd, text = svc.parse_channel_and_text("party hello")
        assert cmd == ""
        assert text == "party hello"
