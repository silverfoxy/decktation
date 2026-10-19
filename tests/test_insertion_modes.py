"""Input mode selection and disabled Gamescope boundaries."""
import asyncio
import json
import shutil
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import decktation_backend as backend
from wow_voice_chat import WoWVoiceChat


GENERIC = {"chat_open_key": None, "chat_send_key": None, "default_channel": "type", "channels": {"type": ""}}
CHAT = {"chat_open_key": "enter", "chat_send_key": "enter", "default_channel": "say", "channels": {"say": "/s "}}


@pytest.fixture(autouse=True)
def bundled_ydotool(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/bin/true" if name == "ydotool" else None)


def test_modes_default_and_legacy_migration(tmp_path, monkeypatch):
    config = tmp_path / "button_config.json"
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(config))
    assert backend._read_button_config()["textInsertionMode"] == "paste"
    config.write_text(json.dumps({"typeAsKeys": True, "manualSend": True}))
    assert backend._read_button_config()["textInsertionMode"] == "ydotool"
    config.write_text(json.dumps({"textInsertionMode": ["gamescope"], "typeAsKeys": True, "manualSend": True}))
    assert backend._read_button_config()["textInsertionMode"] == "paste"
    assert backend._read_button_config()["typeAsKeys"] is False
    assert backend._read_button_config()["manualSend"] is True


def test_disabled_gamescope_resets_to_paste(tmp_path, monkeypatch):
    config = tmp_path / "button_config.json"
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(config))
    config.write_text(json.dumps({"textInsertionMode": "gamescope", "typeAsKeys": True}))
    saved = backend._read_button_config()
    assert saved["textInsertionMode"] == "paste"
    assert saved["typeAsKeys"] is False


def test_typing_persists_and_gamescope_is_rejected(tmp_path, monkeypatch):
    config = tmp_path / "button_config.json"
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(config))
    service = SimpleNamespace(text_insertion_mode="paste", cancel_pending=lambda: None)
    monkeypatch.setattr(backend.Plugin, "voice_service", service)
    plugin = backend.Plugin()
    assert asyncio.run(plugin.set_text_insertion_mode("ydotool"))["success"]
    assert service.text_insertion_mode == "ydotool"
    for mode in ("gamescope", "other"):
        assert not asyncio.run(plugin.set_text_insertion_mode(mode))["success"]
        assert backend._read_button_config()["textInsertionMode"] == "ydotool"
    with pytest.raises(ValueError):
        backend._write_button_config({"textInsertionMode": "gamescope"})


@patch("subprocess.run")
def test_disabled_gamescope_never_opens_chat_or_injects(mock_run):
    svc = WoWVoiceChat(preset=CHAT, lazy_load=True, text_insertion_mode="gamescope")
    assert not svc.send_to_wow_chat("hello", channel="say")
    mock_run.assert_not_called()
