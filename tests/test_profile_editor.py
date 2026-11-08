import asyncio
import json
from unittest.mock import MagicMock

import pytest
import decktation_backend as backend
from wow_voice_chat import WoWVoiceChat


@pytest.fixture
def editor(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(backend.Plugin, "voice_service", None)
    return backend.Plugin()


def profile():
    return {"hotwords": ["Azeroth"], "channels": {"party": "/p ", "type": ""},
            "channel_triggers": {"team": "party"}, "default_channel": "party"}


def test_editor_persists_and_preserves_other_settings(editor, tmp_path):
    (tmp_path / "custom_presets.json").write_text(json.dumps({
        "wow": {"casual_case": False}, "generic": {"hotwords": ["Other"]}}))
    assert asyncio.run(editor.save_profile_editor("wow", profile()))["success"]
    loaded = asyncio.run(editor.get_profile_editor("wow"))["profile"]
    assert loaded["hotwords"] == ["Azeroth"]
    assert loaded["channel_triggers"] == {"team": "party"}
    presets = backend._load_game_presets()
    assert presets["wow"]["casual_case"] is False
    assert presets["generic"]["hotwords"] == ["Other"]


@pytest.mark.parametrize("field, value", [
    ("channels", {"party": "/p\n/quit"}),
    ("hotwords", ["bad\tword"]),
    ("channel_triggers", {"team": "missing"}),
    ("default_channel", "missing"),
])
def test_editor_rejects_invalid_settings_without_writing(editor, tmp_path, field, value):
    settings = profile()
    settings[field] = value
    assert not asyncio.run(editor.save_profile_editor("wow", settings))["success"]
    assert not (tmp_path / "profiles.json").exists()


def test_custom_trigger_and_vocabulary_apply_after_switching_profiles():
    voice = WoWVoiceChat(lazy_load=True, preset=profile(), review_mode=True)
    assert voice._parse_channel_and_text("team hello")[:2] == ("party", "hello")
    assert voice.build_prompt_from_context()[1] == "Azeroth"
    voice.set_preset({"channels": {"type": ""}, "default_channel": "type"})
    assert voice._parse_channel_and_text("team hello")[:2] == ("type", "team hello")


def test_save_applies_to_running_service_and_blocks_pending_drafts(editor, monkeypatch):
    voice = WoWVoiceChat(lazy_load=True, preset=profile(), review_mode=True)
    monkeypatch.setattr(backend.Plugin, "voice_service", voice)
    monkeypatch.setattr(backend.Plugin, "active_preset", "wow")
    voice.set_preset = MagicMock(wraps=voice.set_preset)
    assert asyncio.run(editor.save_profile_editor("wow", profile()))["success"]
    voice.set_preset.assert_called_once()
    voice.queue_transcription("team hello")
    assert not asyncio.run(editor.save_profile_editor("wow", profile()))["success"]
    assert voice.pending_snapshot()["text"] == "hello"


def test_create_profile_preserves_overrides_and_can_be_edited_and_activated(editor, tmp_path):
    (tmp_path / "custom_presets.json").write_text(json.dumps({"wow": {"casual_case": False}}))
    created = asyncio.run(editor.create_profile("My Game"))
    assert created == {"success": True, "id": "my_game", "name": "My Game"}
    assert backend._load_game_presets()["wow"]["casual_case"] is False
    assert asyncio.run(editor.get_profile_editor("my_game"))["profile"]["channels"] == {"type": ""}
    assert asyncio.run(editor.save_profile_editor("my_game", profile()))["success"]
    assert asyncio.run(editor.set_active_preset("my_game"))["success"]
    assert asyncio.run(editor.get_active_preset())["game"] == "my_game"
    assert asyncio.run(editor.get_presets())["presets"][-1] == {"id": "my_game", "name": "My Game"}


@pytest.mark.parametrize("name", ["", "   ", "wow", "World\nGame", "a" * 61, "../"])
def test_create_rejects_invalid_or_existing_names(editor, tmp_path, name):
    assert not asyncio.run(editor.create_profile(name))["success"]
    assert not (tmp_path / "profiles.json").exists()
