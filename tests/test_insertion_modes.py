"""Experimental input mode selection and Gamescope send boundaries."""
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


def test_gamescope_mode_persists_and_rejects_unknown_choice(tmp_path, monkeypatch):
    config = tmp_path / "button_config.json"
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(config))
    service = SimpleNamespace(text_insertion_mode="paste", cancel_pending=lambda: None)
    monkeypatch.setattr(backend.Plugin, "voice_service", service)
    plugin = backend.Plugin()
    assert asyncio.run(plugin.set_text_insertion_mode("gamescope"))["success"]
    assert backend._read_button_config()["textInsertionMode"] == "gamescope"
    assert service.text_insertion_mode == "gamescope"
    assert not asyncio.run(plugin.set_text_insertion_mode("other"))["success"]
    assert backend._read_button_config()["textInsertionMode"] == "gamescope"


@patch("subprocess.run")
def test_gamescope_review_labels_manual_typing_and_result(mock_run):
    updates = []
    svc = WoWVoiceChat(preset=CHAT, lazy_load=True, review_mode=True,
                       text_insertion_mode="gamescope", pending_callback=updates.append)
    svc.send_to_wow_chat = MagicMock(return_value=True)
    svc.queue_transcription("hello")
    draft = svc.pending_snapshot()
    assert draft["action"] == "Type into chat"
    assert draft["manual"] is True
    assert svc.confirm_pending(draft["id"])
    assert updates[-1] == {"mode": "result", "message": "Typed into chat"}


@patch("subprocess.run")
def test_gamescope_types_complete_unicode_without_clipboard_or_auto_submit(mock_run, monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_PLUGIN_DIR", str(tmp_path))
    helper = tmp_path / "bin" / "gamescope-inject"
    helper.parent.mkdir()
    helper.write_bytes(b"fixture")
    helper.chmod(0o755)
    mock_run.return_value = MagicMock(returncode=0)
    svc = WoWVoiceChat(preset=CHAT, lazy_load=True, text_insertion_mode="gamescope")
    assert svc.send_to_wow_chat("Mañana Привет", channel="say")
    assert mock_run.call_args_list[0].args[0] == [str(helper), "--probe"]
    assert mock_run.call_args_list[1].args[0][1:] == ["key", "28:1", "28:0"]
    assert mock_run.call_count == 3
    assert mock_run.call_args_list[2].args[0] == [str(helper)]
    assert mock_run.call_args_list[2].kwargs["input"] == "/s Mañana Привет"


@patch("subprocess.run")
def test_gamescope_long_message_fails_before_chat_open(mock_run, monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_PLUGIN_DIR", str(tmp_path))
    helper = tmp_path / "bin" / "gamescope-inject"
    helper.parent.mkdir()
    helper.write_bytes(b"fixture")
    helper.chmod(0o755)
    svc = WoWVoiceChat(preset=CHAT, lazy_load=True, text_insertion_mode="gamescope")
    assert not svc.send_to_wow_chat("x" * 41, channel="say")
    mock_run.assert_not_called()


@patch("subprocess.run")
def test_missing_gamescope_helper_fails_before_opening_chat(mock_run, monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_PLUGIN_DIR", str(tmp_path))
    svc = WoWVoiceChat(preset=CHAT, lazy_load=True, text_insertion_mode="gamescope")
    assert not svc.send_to_wow_chat("hello", channel="say")
    mock_run.assert_not_called()


@patch("subprocess.run")
def test_gamescope_helper_error_never_submits_or_retries_via_paste(mock_run, monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_PLUGIN_DIR", str(tmp_path))
    helper = tmp_path / "bin" / "gamescope-inject"
    helper.parent.mkdir()
    helper.write_bytes(b"fixture")
    helper.chmod(0o755)
    mock_run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=0), MagicMock(returncode=1)]
    svc = WoWVoiceChat(preset=CHAT, lazy_load=True, text_insertion_mode="gamescope")
    assert not svc.send_to_wow_chat("hello", channel="say")
    assert mock_run.call_count == 3


@patch("subprocess.run")
def test_gamescope_mode_snapshot_survives_toggle_during_chat_open(mock_run, monkeypatch, tmp_path):
    monkeypatch.setenv("DECKY_PLUGIN_DIR", str(tmp_path))
    helper = tmp_path / "bin" / "gamescope-inject"
    helper.parent.mkdir()
    helper.write_bytes(b"fixture")
    helper.chmod(0o755)
    svc = WoWVoiceChat(preset=CHAT, lazy_load=True, text_insertion_mode="gamescope")
    def run(*args, **kwargs):
        if len(mock_run.call_args_list) == 2:
            svc.text_insertion_mode = "paste"
        return MagicMock(returncode=0)
    mock_run.side_effect = run
    assert svc.send_to_wow_chat("Привет", channel="say")
    assert mock_run.call_count == 3
    assert mock_run.call_args_list[2].kwargs["input"] == "/s Привет"
