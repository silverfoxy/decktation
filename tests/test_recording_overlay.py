import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock
import json

import decktation_backend
import recording_overlay_manager
from recording_overlay_manager import RecordingOverlay


def test_resolves_decky_user_home_owner_without_assuming_account_name(monkeypatch):
    monkeypatch.setattr(recording_overlay_manager.os, "geteuid", lambda: 0)
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


def test_rootless_overlay_uses_current_account_and_inherits_process_identity(monkeypatch):
    import os
    import subprocess
    user = SimpleNamespace(pw_uid=2345, pw_gid=2345, pw_dir='/home/gamer', pw_name='gamer')
    monkeypatch.setattr(recording_overlay_manager.os, 'geteuid', lambda: 2345)
    monkeypatch.setattr(recording_overlay_manager.pwd, 'getpwuid', lambda uid: user)
    overlay = RecordingOverlay('/plugin', MagicMock(), '/another/home', enabled=False)
    assert overlay.session_user is user
    assert overlay._process_identity() == {}
    subprocess.run(['/usr/bin/true'], check=True, **overlay._process_identity())


def test_root_overlay_still_drops_child_privileges(monkeypatch):
    overlay = RecordingOverlay('/plugin', MagicMock(), enabled=False)
    overlay.session_user = SimpleNamespace(pw_uid=2345, pw_gid=2345)
    monkeypatch.setattr(recording_overlay_manager.os, 'geteuid', lambda: 0)
    assert overlay._process_identity() == {'user': 2345, 'group': 2345, 'extra_groups': []}


def test_rootless_overlay_probe_and_launch_do_not_change_identity(tmp_path, monkeypatch):
    import os
    overlay = RecordingOverlay(tmp_path, MagicMock(), enabled=False)
    overlay.session_user = SimpleNamespace(pw_uid=os.geteuid(), pw_gid=os.getegid(),
                                          pw_dir=str(tmp_path), pw_name='gamer')
    monkeypatch.setattr(recording_overlay_manager.os, 'geteuid', lambda: overlay.session_user.pw_uid or 1000)
    monkeypatch.setattr(overlay, '_display_candidates', lambda: [':1'])
    probe = MagicMock(return_value=SimpleNamespace(returncode=0, stdout='GAMESCOPE_XWAYLAND_SERVER_ID = 0'))
    launch = MagicMock()
    monkeypatch.setattr(recording_overlay_manager.subprocess, 'run', probe)
    monkeypatch.setattr(recording_overlay_manager.subprocess, 'Popen', launch)
    monkeypatch.setattr(recording_overlay_manager.os, 'chown', MagicMock(side_effect=AssertionError('chown')))
    (tmp_path / 'bin').mkdir()
    (tmp_path / 'bin/recording_overlay.py').touch()
    overlay.display = overlay._find_display()
    overlay._show_ready('compact')
    for call in (probe.call_args, launch.call_args):
        assert not {'user', 'group', 'extra_groups'} & call.kwargs.keys()
    assert json.loads((overlay.directory / 'state').read_text()) == {'mode': 'compact'}
    import shutil
    shutil.rmtree(overlay.directory)
