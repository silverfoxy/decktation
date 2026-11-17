import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock
import json

import decktation_backend
import recording_overlay_manager
from recording_overlay_manager import RecordingOverlay


def test_resolves_decky_user_home_owner_without_assuming_account_name(monkeypatch):
    user = SimpleNamespace(
        pw_uid=2345,
        pw_gid=2345,
        pw_dir="/home/gamer",
        pw_name="gamer",
    )
    monkeypatch.setattr(recording_overlay_manager.os, "stat", lambda _path: SimpleNamespace(st_uid=2345))
    monkeypatch.setattr(recording_overlay_manager.pwd, "getpwuid", lambda uid: user if uid == 2345 else None)

    overlay = RecordingOverlay("/plugin", MagicMock(), "/home/gamer", enabled=False)

    assert overlay.session_user is user
    assert overlay._env(":1")["XDG_RUNTIME_DIR"] == "/run/user/2345"


def test_show_schedules_discovery_without_running_probe_inline(monkeypatch):
    overlay = RecordingOverlay("/plugin", MagicMock(), enabled=False)
    overlay.enabled = True
    overlay.session_user = SimpleNamespace(pw_uid=1000, pw_gid=1000)
    scheduled = MagicMock()
    monkeypatch.setattr(overlay, "_start_display_discovery", scheduled)
    monkeypatch.setattr(overlay, "_find_display", MagicMock(side_effect=AssertionError("inline probe")))

    overlay.show("compact")

    scheduled.assert_called_once_with()
    assert overlay.desired_state == "compact"


def test_discovery_uses_latest_visible_state(monkeypatch):
    overlay = RecordingOverlay("/plugin", MagicMock(), enabled=False)
    overlay.enabled = True
    overlay.session_user = SimpleNamespace(pw_uid=1000, pw_gid=1000)
    overlay.desired_state = "transcribing"
    monkeypatch.setattr(overlay, "_find_display", lambda: ":1")
    show_ready = MagicMock()
    monkeypatch.setattr(overlay, "_show_ready", show_ready)

    overlay._discover_display()

    assert overlay.display == ":1"
    show_ready.assert_called_once_with("transcribing")


def test_hide_prevents_late_discovery_from_showing_stale_state(monkeypatch):
    overlay = RecordingOverlay("/plugin", MagicMock(), enabled=False)
    overlay.enabled = True
    overlay.session_user = SimpleNamespace(pw_uid=1000, pw_gid=1000)
    overlay.desired_state = "hidden"
    monkeypatch.setattr(overlay, "_find_display", lambda: ":1")
    show_ready = MagicMock()
    monkeypatch.setattr(overlay, "_show_ready", show_ready)

    overlay._discover_display()

    assert overlay.display == ":1"
    show_ready.assert_not_called()


def test_legacy_notification_setting_migrates_to_recording_cue(tmp_path, monkeypatch):
    config_file = tmp_path / "button_config.json"
    config_file.write_text(json.dumps({"showNotifications": False}))
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))

    config = decktation_backend._read_button_config()

    assert config["recordingIndicator"] == "none"


def test_overlay_mode_keeps_legacy_notifications_flag_compatible(tmp_path, monkeypatch):
    config_file = tmp_path / "button_config.json"
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))

    written = decktation_backend._write_button_config({"recordingIndicator": "overlay"})

    assert written["recordingIndicator"] == "overlay"
    assert written["showNotifications"] is True

def test_toast_recording_cue_migrates_to_overlay(tmp_path, monkeypatch):
    config_file = tmp_path / "button_config.json"
    config_file.write_text(json.dumps({"recordingIndicator": "toast", "showNotifications": True}))
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))

    assert decktation_backend.DEFAULT_BUTTON_CONFIG["recordingIndicator"] == "overlay"
    assert decktation_backend._read_button_config()["recordingIndicator"] == "overlay"
    assert decktation_backend._write_button_config({"recordingIndicator": "overlay"})["recordingIndicator"] == "overlay"

def test_old_toast_overrides_legacy_disabled_flag_and_persists_overlay(tmp_path, monkeypatch):
    config_file = tmp_path / "button_config.json"
    config_file.write_text(json.dumps({"recordingIndicator": "toast", "showNotifications": False}))
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))

    config = decktation_backend._read_button_config()
    assert config["recordingIndicator"] == "overlay"
    decktation_backend._write_button_config(config)
    saved = json.loads(config_file.read_text())
    assert saved["recordingIndicator"] == "overlay"
    assert saved["showNotifications"] is True

def test_legacy_enabled_notifications_migrate_to_overlay(tmp_path, monkeypatch):
    config_file = tmp_path / "button_config.json"
    config_file.write_text(json.dumps({"showNotifications": True}))
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))

    assert decktation_backend._read_button_config()["recordingIndicator"] == "overlay"

def test_explicit_none_remains_none(tmp_path, monkeypatch):
    config_file = tmp_path / "button_config.json"
    config_file.write_text(json.dumps({"recordingIndicator": "none", "showNotifications": True}))
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))

    assert decktation_backend._read_button_config()["recordingIndicator"] == "none"

def test_toast_recording_cue_is_rejected_by_rpc(tmp_path, monkeypatch):
    config_file = tmp_path / "button_config.json"
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))

    result = asyncio.run(decktation_backend.Plugin().set_recording_indicator("toast"))
    assert result["success"] is False
    assert "Unsupported recording indicator" in result["error"]


def test_model_size_rpc_reports_resident_vulkan_reload(tmp_path, monkeypatch):
    config_file = tmp_path / "button_config.json"
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))

    async def run_inline(function, *args):
        return function(*args)

    monkeypatch.setattr(decktation_backend.asyncio, "to_thread", run_inline)
    service = MagicMock()
    service.is_model_ready.return_value = True
    service.set_model_size.return_value = True
    monkeypatch.setattr(decktation_backend.Plugin, "voice_service", service)

    result = asyncio.run(decktation_backend.Plugin().set_model_size("small"))

    assert result == {"success": True, "modelSize": "small", "reloaded": True}
    service.set_model_size.assert_called_once_with("small")


def test_status_reports_active_whisper_cpp_device(monkeypatch):
    service = MagicMock()
    service.is_model_ready.return_value = True
    service.model_loading = False
    service.inference_device = "cpu"
    service.is_recording = False
    service.pending_text = None
    service.confirm_delay = 0
    monkeypatch.setattr(decktation_backend.Plugin, "voice_service", service)
    monkeypatch.setattr(decktation_backend.Plugin, "listener_process", None)

    result = asyncio.run(decktation_backend.Plugin().get_status())

    assert result["success"] is True, result
    assert result["model_ready"] is True
    assert result["inference_device"] == "cpu"
