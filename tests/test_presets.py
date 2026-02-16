"""
Unit tests for game preset loading and switching.

Covers: constructor preset wiring, set_preset live switching,
and game_presets.json structural validity.
"""

import json
import os
import pytest
from wow_voice_chat import WoWVoiceChat


PRESETS_FILE = os.path.join(os.path.dirname(__file__), "..", "game_presets.json")


# ---------------------------------------------------------------------------
# game_presets.json structure
# ---------------------------------------------------------------------------

class TestPresetsFile:
    """Validate game_presets.json has the expected structure for all presets."""

    @pytest.fixture(scope="class")
    def presets(self):
        with open(PRESETS_FILE) as f:
            return json.load(f)

    REQUIRED_KEYS = {"name", "chat_open_key", "chat_send_key", "default_channel", "channels", "whisper_prompt"}

    def test_file_is_valid_json(self, presets):
        assert isinstance(presets, dict)

    def test_required_presets_present(self, presets):
        assert "wow" in presets
        assert "generic" in presets

    @pytest.mark.parametrize("preset_id", ["wow", "generic"])
    def test_required_keys(self, presets, preset_id):
        missing = self.REQUIRED_KEYS - presets[preset_id].keys()
        assert not missing, f"Preset '{preset_id}' missing keys: {missing}"

    def test_wow_default_channel_in_channels(self, presets):
        wow = presets["wow"]
        assert wow["default_channel"] in wow["channels"]

    def test_generic_default_channel_in_channels(self, presets):
        generic = presets["generic"]
        assert generic["default_channel"] in generic["channels"]

    def test_wow_has_enter_keys(self, presets):
        wow = presets["wow"]
        assert wow["chat_open_key"] == "enter"
        assert wow["chat_send_key"] == "enter"

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
    def test_wow_preset_sets_default_channel(self):
        preset = {"default_channel": "say", "channels": {"say": "/s "}, "whisper_prompt": ""}
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        assert svc.default_channel == "say"

    def test_generic_preset_sets_default_channel(self):
        preset = {"default_channel": "type", "channels": {"type": ""}, "whisper_prompt": ""}
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        assert svc.default_channel == "type"

    def test_preset_channel_commands_used(self):
        channels = {"say": "/s ", "party": "/p "}
        preset = {"default_channel": "say", "channels": channels, "whisper_prompt": ""}
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        assert svc.channel_commands == channels

    def test_no_preset_falls_back_to_wow_defaults(self):
        svc = WoWVoiceChat(lazy_load=True)
        # Should have WoW channels in fallback
        assert "say" in svc.channel_commands
        assert "party" in svc.channel_commands
        assert "raid" in svc.channel_commands

    def test_preset_stored_on_instance(self):
        preset = {"default_channel": "type", "channels": {"type": ""}, "whisper_prompt": "test"}
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        assert svc.preset is preset


# ---------------------------------------------------------------------------
# set_preset live switching
# ---------------------------------------------------------------------------

class TestSetPreset:
    def test_switch_updates_default_channel(self):
        wow_preset = {"default_channel": "say", "channels": {"say": "/s ", "type": ""}, "whisper_prompt": ""}
        generic_preset = {"default_channel": "type", "channels": {"type": ""}, "whisper_prompt": ""}

        svc = WoWVoiceChat(preset=wow_preset, lazy_load=True)
        assert svc.default_channel == "say"

        svc.set_preset(generic_preset)
        assert svc.default_channel == "type"

    def test_switch_updates_channel_commands(self):
        wow_channels = {"say": "/s ", "party": "/p ", "type": ""}
        generic_channels = {"type": ""}

        wow_preset = {"default_channel": "say", "channels": wow_channels, "whisper_prompt": ""}
        generic_preset = {"default_channel": "type", "channels": generic_channels, "whisper_prompt": ""}

        svc = WoWVoiceChat(preset=wow_preset, lazy_load=True)
        svc.set_preset(generic_preset)

        assert svc.channel_commands == generic_channels
        assert "party" not in svc.channel_commands

    def test_switch_back_restores_channels(self):
        wow_preset = {"default_channel": "say", "channels": {"say": "/s ", "party": "/p ", "type": ""}, "whisper_prompt": ""}
        generic_preset = {"default_channel": "type", "channels": {"type": ""}, "whisper_prompt": ""}

        svc = WoWVoiceChat(preset=wow_preset, lazy_load=True)
        svc.set_preset(generic_preset)
        svc.set_preset(wow_preset)

        assert svc.default_channel == "say"
        assert "party" in svc.channel_commands

    def test_switch_affects_channel_parsing(self):
        wow_preset = {
            "default_channel": "say",
            "channels": {"say": "/s ", "party": "/p ", "type": ""},
            "whisper_prompt": "",
        }
        generic_preset = {
            "default_channel": "type",
            "channels": {"type": ""},
            "whisper_prompt": "",
        }

        svc = WoWVoiceChat(preset=wow_preset, lazy_load=True)
        ch, _ = svc.parse_channel_and_text("party hello")
        assert ch == "party"

        svc.set_preset(generic_preset)
        # "party" is no longer a channel; falls back to default "type"
        ch, text = svc.parse_channel_and_text("party hello")
        assert ch == "type"
        assert text == "party hello"
