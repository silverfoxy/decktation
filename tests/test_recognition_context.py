import asyncio
import json
import os

import pytest
from recognition_context import read_context, merge_terms
from wow_voice_chat import WoWVoiceChat
import decktation_backend as backend


def write(path, **fields):
    path.write_text(json.dumps({"version": 1, "terms": ["Éowyn", "Azeroth"], **fields}))


@pytest.mark.parametrize("data,status", [
    ({"version": 2, "terms": []}, "invalid"),
    ({"version": True, "terms": []}, "invalid"),
    ({"version": 1, "terms": "bad"}, "invalid"),
    ({"version": 1, "terms": ["bad\nterm"]}, "invalid"),
    ({"version": 1, "terms": ["x"] * 101}, "invalid"),
    ({"version": 1, "terms": [], "expires_at": "2000-01-01T00:00:00Z"}, "expired"),
    ({"version": 1, "terms": [], "expires_at": "2099-01-01"}, "invalid"),
    ({"version": 1, "terms": [], "expires_at": "bad"}, "invalid"),
    ([], "invalid"),
    ({}, "invalid"),
])
def test_validation(tmp_path, data, status):
    path = tmp_path / "context.json"
    path.write_text(json.dumps(data))
    assert read_context(path) == ({}, status)


def test_missing_oversize_nonregular_and_bad_encoding(tmp_path):
    path = tmp_path / "context.json"
    assert read_context(path)[1] == "missing"
    path.write_bytes(b"x" * 65537)
    assert read_context(path)[1] == "invalid"
    path.write_bytes(b"\xff")
    assert read_context(path)[1] == "invalid"
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    assert read_context(fifo)[1] == "invalid"


def test_fresh_snapshot_and_profile_switch(tmp_path):
    path = tmp_path / "context.json"
    write(path)
    voice = WoWVoiceChat(lazy_load=True, context_file=str(tmp_path / "wow_context.json"),
                         preset={"context_file": "context.json", "hotwords": ["azeroth"]})
    assert voice.load_context()
    assert voice.build_prompt_from_context()[1] == "azeroth, Éowyn"
    path.write_text("broken")
    assert not voice.load_context()
    assert voice.build_prompt_from_context()[1] == "azeroth"
    write(path, terms=["New name"])
    assert voice.load_context()
    assert "New name" in voice.build_prompt_from_context()[1]
    voice.set_preset({"context_file": ""})
    assert not voice.load_context()
    assert voice.build_prompt_from_context()[1] is None


def test_budget_and_casefold():
    merged = merge_terms(["ÉOWYN"], ["éowyn", *[str(i) * 50 for i in range(100)]])
    assert merged.startswith("ÉOWYN, ")
    assert len(merged) <= 800
    assert "éowyn" not in merged


def test_legacy_snapshot(tmp_path):
    path = tmp_path / "context.json"
    path.write_text(json.dumps({"zone": "Azeroth", "boss": "Illidan", "target": "Akama"}))
    assert read_context(path) == ({"terms": ["Azeroth", "Illidan", "Akama"]}, "loaded")


def test_editor_roundtrip_and_status(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(backend.Plugin, "voice_service", None)
    plugin = backend.Plugin()
    settings = {"hotwords": [], "channels": {"type": ""}, "channel_triggers": {},
                "default_channel": "type", "context_file": str(tmp_path / "context.json")}
    write(tmp_path / "context.json")
    assert asyncio.run(plugin.save_profile_editor("generic", settings))["success"]
    assert asyncio.run(plugin.get_profile_editor("generic"))["profile"]["context_file"] == settings["context_file"]
    status = asyncio.run(plugin.get_recognition_context_status(settings["context_file"]))
    assert status == {"status": "loaded", "count": 2}
    settings["context_file"] = "bad\npath"
    assert not asyncio.run(plugin.save_profile_editor("generic", settings))["success"]


def test_converter_exports_generic_snapshot_atomically(tmp_path):
    from convert_wow_context import convert_context
    source = tmp_path / "saved.lua"
    source.write_text('DecktationContextDB = { ["zone"] = "Azeroth", ["target"] = "Akama", }')
    output = tmp_path / "context.json"
    assert convert_context(source, output)
    data = json.loads(output.read_text())
    assert data["version"] == 1
    assert data["terms"] == ["Azeroth", "Akama"]
    assert read_context(output)[1] == "loaded"
    assert not (tmp_path / "context.json.tmp").exists()


def test_generic_profile_does_not_read_legacy_default(tmp_path):
    path = tmp_path / "wow_context.json"
    write(path)
    voice = WoWVoiceChat(lazy_load=True, context_file=str(path), preset={"hotwords": []})
    assert not voice.load_context()
    assert voice.build_prompt_from_context()[1] is None
    standalone = WoWVoiceChat(lazy_load=True, context_file=str(path))
    assert standalone.load_context()
    assert standalone.build_prompt_from_context()[1] == "Éowyn, Azeroth"
