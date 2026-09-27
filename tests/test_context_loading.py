"""
Unit tests for WoW context parsing and dynamic prompt/hotwords building.
"""

import os
import json
import pytest
from pathlib import Path
from convert_wow_context import parse_lua_table, extract_table
from wow_voice_chat import WoWVoiceChat


SAMPLE_LUA = """
DecktationContextDB = {
    ["timestamp"] = 1711540000,
    ["zone"] = "Duskwood",
    ["subzone"] = "Darkshire",
    ["boss"] = "Stitches",
    ["target"] = "Eliza",
    ["player"] = "Arthas",
    ["guild"] = "Knights of the Silver Hand",
    ["class"] = "Paladin",
    ["spec"] = "Retribution",
    ["party"] = {
        "Uther",
        "Jaina",
        "Muradin",
    },
    ["inventory"] = {
        "Pungent Skycheddar",
        "Silk Cloth",
        "Lesser Healing Potion",
    },
    ["quests"] = {
        "The Hermit",
        "Look To The Stars",
        "WANTED: Murkdeep",
    },
    ["spells"] = {
        "Holy Light",
        "Judgement",
        "Hammer of Justice",
    },
}
"""


class TestLuaParser:
    def test_extract_table_nested_braces(self):
        lua = 'DecktationContextDB = { ["foo"] = { "a", "b" }, ["bar"] = "baz" }'
        table = extract_table(lua, "DecktationContextDB")
        assert '["foo"]' in table
        assert '["bar"]' in table

    def test_parse_all_fields(self):
        ctx = parse_lua_table(SAMPLE_LUA)
        assert ctx["zone"] == "Duskwood"
        assert ctx["subzone"] == "Darkshire"
        assert ctx["boss"] == "Stitches"
        assert ctx["target"] == "Eliza"
        assert ctx["player"] == "Arthas"
        assert ctx["guild"] == "Knights of the Silver Hand"
        assert ctx["class"] == "Paladin"
        assert ctx["spec"] == "Retribution"
        assert ctx["party"] == ["Uther", "Jaina", "Muradin"]
        assert ctx["inventory"] == ["Pungent Skycheddar", "Silk Cloth", "Lesser Healing Potion"]
        assert ctx["quests"] == ["The Hermit", "Look To The Stars", "WANTED: Murkdeep"]
        assert ctx["spells"] == ["Holy Light", "Judgement", "Hammer of Justice"]
        assert ctx["timestamp"] == 1711540000

    def test_parse_empty_content(self):
        ctx = parse_lua_table("")
        assert ctx == {}

    def test_parse_partial_table(self):
        lua = 'DecktationContextDB = { ["zone"] = "Orgrimmar", ["party"] = { "Thrall" } }'
        ctx = parse_lua_table(lua)
        assert ctx["zone"] == "Orgrimmar"
        assert ctx["subzone"] == ""
        assert ctx["party"] == ["Thrall"]
        assert ctx["inventory"] == []
        assert ctx["quests"] == []
        assert ctx["spells"] == []


class TestPromptAndHotwordsBuilding:
    def test_build_prompt_with_full_context(self):
        preset = {
            "name": "World of Warcraft",
            "whisper_prompt": "say hello, party let's go",
            "hotwords": ["Orgrimmar", "Stormwind", "Hearthstone"],
            "context_file": "wow_context.json",
        }
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        svc.context = parse_lua_table(SAMPLE_LUA)

        prompt, hotwords = svc.build_prompt_from_context()

        # Check prompt contains locations, boss, target, party, quests
        assert "Zone: Duskwood (Darkshire)" in prompt
        assert "Boss: Stitches" in prompt
        assert "Target: Eliza" in prompt
        assert "Party: Uther, Jaina, Muradin" in prompt
        assert "Quests: The Hermit, Look To The Stars, WANTED: Murkdeep" in prompt

        # Check hotwords contains dynamic items + preset hotwords
        hotwords_list = [w.strip() for w in hotwords.split(",")]
        assert "Duskwood" in hotwords_list
        assert "Darkshire" in hotwords_list
        assert "Stitches" in hotwords_list
        assert "Eliza" in hotwords_list
        assert "Arthas" in hotwords_list
        assert "Knights of the Silver Hand" in hotwords_list
        assert "Uther" in hotwords_list
        assert "Pungent Skycheddar" in hotwords_list
        assert "Silk Cloth" in hotwords_list
        assert "Lesser Healing Potion" in hotwords_list
        assert "The Hermit" in hotwords_list
        assert "Look To The Stars" in hotwords_list
        assert "WANTED: Murkdeep" in hotwords_list
        assert "Holy Light" in hotwords_list
        assert "Hammer of Justice" in hotwords_list
        assert "Orgrimmar" in hotwords_list
        assert "Stormwind" in hotwords_list
        assert "Hearthstone" in hotwords_list

    def test_hotwords_deduplication(self):
        preset = {
            "name": "World of Warcraft",
            "whisper_prompt": "say hello",
            "hotwords": ["Duskwood", "Stitches", "Silk Cloth"],
            "context_file": "wow_context.json",
        }
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        svc.context = {
            "zone": "Duskwood",
            "boss": "Stitches",
            "inventory": ["Silk Cloth", "Silk Cloth"],
        }
        prompt, hotwords = svc.build_prompt_from_context()
        hotwords_list = [w.strip() for w in hotwords.split(",")]
        assert hotwords_list.count("Duskwood") == 1
        assert hotwords_list.count("Stitches") == 1
        assert hotwords_list.count("Silk Cloth") == 1

    def test_non_english_suppresses_prompt_and_hotwords(self):
        preset = {
            "name": "World of Warcraft",
            "whisper_prompt": "say hello",
            "hotwords": ["Orgrimmar"],
            "context_file": "wow_context.json",
        }
        svc = WoWVoiceChat(preset=preset, lazy_load=True, transcription_language="de")
        svc.context = {"zone": "Duskwood"}
        prompt, hotwords = svc.build_prompt_from_context()
        assert prompt is None
        assert hotwords is None

    def test_generic_preset_no_context_file(self):
        preset = {
            "name": "Generic",
            "whisper_prompt": "Type anything",
            "hotwords": ["Foo", "Bar"],
        }
        svc = WoWVoiceChat(preset=preset, lazy_load=True)
        svc.context = {"zone": "Ignored"}
        prompt, hotwords = svc.build_prompt_from_context()
        assert prompt == "Type anything"
        assert hotwords == "Foo, Bar"
