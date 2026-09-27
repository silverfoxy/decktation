import json
import time
from pathlib import Path
from unittest.mock import patch
from convert_wow_context import parse_lua_table, find_savedvariables_file
from wow_voice_chat import WoWVoiceChat


def test_parse_lua_table_standard():
    lua = """
DecktationContextDB = {
    ["timestamp"] = 1790447559,
    ["boss"] = "Onyxia",
    ["spec"] = "Arms",
    ["zone"] = "Darkshore",
    ["subzone"] = "Bashal'Aran",
    ["class"] = "WARRIOR",
    ["party"] = {
        "Tyden",
        "Korg",
    },
    ["target"] = "Greymist Coastrunner",
}
"""
    parsed = parse_lua_table(lua)
    assert parsed["timestamp"] == 1790447559
    assert parsed["boss"] == "Onyxia"
    assert parsed["spec"] == "Arms"
    assert parsed["zone"] == "Darkshore"
    assert parsed["subzone"] == "Bashal'Aran"
    assert parsed["class"] == "WARRIOR"
    assert parsed["party"] == ["Tyden", "Korg"]
    assert parsed["target"] == "Greymist Coastrunner"


def test_parse_lua_table_empty_or_invalid():
    assert parse_lua_table("") == {}
    assert parse_lua_table("random text without table") == {}


def test_find_savedvariables_file_direct_file(tmp_path):
    lua_file = tmp_path / "DecktationContext.lua"
    lua_file.write_text('DecktationContextDB = { ["zone"] = "Durotar" }')
    found = find_savedvariables_file(wow_path=str(lua_file))
    assert found == lua_file


def test_find_savedvariables_file_wow_path_dir(tmp_path):
    account_dir = tmp_path / "_classic_beta_" / "WTF" / "Account" / "12345#1" / "SavedVariables"
    account_dir.mkdir(parents=True)
    lua_file = account_dir / "DecktationContext.lua"
    lua_file.write_text('DecktationContextDB = { ["zone"] = "Durotar" }')

    found = find_savedvariables_file(wow_path=str(tmp_path))
    assert found == lua_file


def test_find_savedvariables_file_picks_most_recent(tmp_path):
    acc1 = tmp_path / "WTF" / "Account" / "1" / "SavedVariables"
    acc2 = tmp_path / "WTF" / "Account" / "2" / "SavedVariables"
    acc1.mkdir(parents=True)
    acc2.mkdir(parents=True)

    lua1 = acc1 / "DecktationContext.lua"
    lua2 = acc2 / "DecktationContext.lua"

    lua1.write_text('DecktationContextDB = { ["zone"] = "Old" }')
    lua2.write_text('DecktationContextDB = { ["zone"] = "New" }')

    # Ensure lua2 has newer mtime
    lua1.touch()
    time.sleep(0.02)
    lua2.touch()

    found = find_savedvariables_file(wow_path=str(tmp_path))
    assert found == lua2


def test_find_savedvariables_file_discovered_in_home(tmp_path):
    mock_home = tmp_path / "fakehome"
    wow_saved = mock_home / "Games" / "battlenet" / "drive_c" / "Program Files (x86)" / "World of Warcraft" / "_classic_" / "WTF" / "Account" / "123" / "SavedVariables" / "DecktationContext.lua"
    wow_saved.parent.mkdir(parents=True)
    wow_saved.write_text('DecktationContextDB = { ["zone"] = "Barrens" }')

    with patch("convert_wow_context.get_candidate_home_dirs", return_value=[mock_home]):
        found = find_savedvariables_file()
        assert found == wow_saved


def test_wow_voice_chat_load_context_from_savedvariables(tmp_path):
    lua_file = tmp_path / "DecktationContext.lua"
    lua_file.write_text("""
DecktationContextDB = {
    ["zone"] = "Elwynn Forest",
    ["subzone"] = "Goldshire",
    ["boss"] = "Hogger",
    ["target"] = "Hogger",
    ["class"] = "PALADIN",
    ["party"] = { "Arthur" },
}
""")
    json_cache = tmp_path / "wow_context.json"

    with patch("wow_voice_chat.find_savedvariables_file", return_value=lua_file):
        service = WoWVoiceChat(context_file=str(json_cache), lazy_load=True)
        loaded = service.load_context()
        assert loaded is True
        assert service.context["zone"] == "Elwynn Forest"
        assert service.context["subzone"] == "Goldshire"
        assert service.context["boss"] == "Hogger"
        assert service.context["party"] == ["Arthur"]

        # Also verify it cached to json_cache
        assert json_cache.exists()
        cached = json.loads(json_cache.read_text())
        assert cached["zone"] == "Elwynn Forest"


def test_wow_voice_chat_fallback_to_json(tmp_path):
    json_cache = tmp_path / "wow_context.json"
    json_cache.write_text(json.dumps({"zone": "Ironforge", "subzone": "Commons"}))

    with patch("wow_voice_chat.find_savedvariables_file", return_value=None):
        service = WoWVoiceChat(context_file=str(json_cache), lazy_load=True)
        loaded = service.load_context()
        assert loaded is True
        assert service.context["zone"] == "Ironforge"
        assert service.context["subzone"] == "Commons"


def test_build_prompt_from_context():
    service = WoWVoiceChat(
        lazy_load=True,
        preset={
            "whisper_prompt": "base prompt words.",
            "context_file": "wow_context.json"
        }
    )
    service.context = {
        "zone": "Duskwood",
        "subzone": "Darkshire",
        "boss": "Mor'Ladim",
        "target": "Mor'Ladim",
        "party": ["Hero1", "Hero2"]
    }

    prompt, _ = service.build_prompt_from_context()
    assert "base prompt words." in prompt
    assert "Currently in Duskwood at Darkshire fighting Mor'Ladim with party members Hero1, Hero2." in prompt
