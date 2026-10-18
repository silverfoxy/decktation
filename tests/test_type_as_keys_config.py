import asyncio
import json
from types import SimpleNamespace

import decktation_backend as backend


def test_type_as_keys_defaults_and_persists_without_losing_other_settings(tmp_path, monkeypatch):
    config = tmp_path / "button_config.json"
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(config))
    assert backend._read_button_config()["typeAsKeys"] is False
    config.write_text(json.dumps({"manualSend": True, "game": "generic"}))
    service = SimpleNamespace(type_as_keys=False, cancel_pending=lambda: None)
    monkeypatch.setattr(backend.Plugin, "voice_service", service)
    plugin = backend.Plugin()
    assert asyncio.run(plugin.set_type_as_keys(True))["success"]
    assert json.loads(config.read_text())["manualSend"] is True
    assert backend._read_button_config()["typeAsKeys"] is True
    assert service.type_as_keys is True
    assert asyncio.run(plugin.set_type_as_keys(False))["success"]
    assert service.type_as_keys is False
    assert backend._read_button_config()["typeAsKeys"] is False


def test_type_as_keys_rejects_non_boolean_values(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "BUTTON_CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(backend.Plugin, "voice_service", None)
    plugin = backend.Plugin()
    assert not asyncio.run(plugin.set_type_as_keys("false"))["success"]
    assert backend._read_button_config()["typeAsKeys"] is False
