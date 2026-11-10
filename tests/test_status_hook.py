import json
from unittest.mock import MagicMock

import decktation_backend


def _config(tmp_path, monkeypatch, **values):
    config_file = tmp_path / "button_config.json"
    config_file.write_text(json.dumps(values))
    monkeypatch.setattr(decktation_backend, "BUTTON_CONFIG_FILE", str(config_file))


def test_status_hook_is_off_by_default(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch)
    popen = MagicMock()
    monkeypatch.setattr(decktation_backend.subprocess, "Popen", popen)

    decktation_backend._status_hook("record_start")

    popen.assert_not_called()


def test_status_hook_runs_command_with_event(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch, statusHookCommand="/home/deck/bin/on-dictation --verbose")
    popen = MagicMock()
    monkeypatch.setattr(decktation_backend.subprocess, "Popen", popen)

    decktation_backend._status_hook("record_stop")

    popen.assert_called_once()
    args, kwargs = popen.call_args
    assert args[0] == ["/home/deck/bin/on-dictation", "--verbose"]
    assert kwargs["env"]["DECKTATION_EVENT"] == "record_stop"
    assert kwargs["start_new_session"] is True


def test_status_hook_failure_never_breaks_dictation(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch, statusHookCommand="/missing/command")
    monkeypatch.setattr(
        decktation_backend.subprocess, "Popen", MagicMock(side_effect=FileNotFoundError("missing"))
    )

    decktation_backend._status_hook("error")  # must not raise


def test_status_hook_command_survives_config_writes(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch, statusHookCommand="/usr/bin/true")

    written = decktation_backend._write_button_config(decktation_backend._read_button_config())

    assert written["statusHookCommand"] == "/usr/bin/true"
