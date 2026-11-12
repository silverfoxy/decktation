import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import decktation_backend as backend


@pytest.fixture
def setting(monkeypatch, tmp_path):
    monkeypatch.setattr(backend, 'BUTTON_CONFIG_FILE', str(tmp_path / 'buttons.json'))
    monkeypatch.setattr(backend.Plugin, 'voice_service', None)
    monkeypatch.setattr(backend.Plugin, 'binding_session', None)
    debug = SimpleNamespace(state='idle', uploading=False)
    monkeypatch.setattr(backend.Plugin, '_controller_debug', lambda: debug)
    restart = Mock(return_value=True)
    monkeypatch.setattr(backend.Plugin, 'start_controller_listener', restart)
    return debug, restart


def test_switch_preserves_binding_and_rolls_back_failure(setting):
    _, restart = setting
    config = backend._read_button_config()
    assert config['controllerBackend'] == 'legacy'
    config['buttons'] = ['L4']
    backend._write_button_config(config)
    assert asyncio.run(backend.Plugin.set_controller_backend(None, 'legacy'))['success']
    assert backend._read_button_config()['buttons'] == ['L4']
    assert backend._read_button_config()['controllerBackend'] == 'legacy'
    restart.side_effect = [False, True]
    assert not asyncio.run(backend.Plugin.set_controller_backend(None, 'sdl'))['success']
    assert backend._read_button_config()['controllerBackend'] == 'legacy'


def test_switch_rejects_active_capture_recording_and_invalid_input(setting, monkeypatch):
    debug, restart = setting
    debug.state = 'recording'
    assert not asyncio.run(backend.Plugin.set_controller_backend(None, 'legacy'))['success']
    debug.state = 'idle'
    monkeypatch.setattr(backend.Plugin, 'voice_service', SimpleNamespace(is_recording=True))
    assert not asyncio.run(backend.Plugin.set_controller_backend(None, 'legacy'))['success']
    for value in ('unknown', [], None):
        assert not asyncio.run(backend.Plugin.set_controller_backend(None, value))['success']
    restart.assert_not_called()


def test_old_sdl_default_migrates_once_and_explicit_opt_in_survives(setting):
    import json
    from pathlib import Path
    Path(backend.BUTTON_CONFIG_FILE).write_text(json.dumps({
        'controllerBackend': 'sdl', 'buttons': ['L4'], 'manualSend': True}))
    config = backend._read_button_config()
    assert config['controllerBackend'] == 'legacy'
    assert config['buttons'] == ['L4'] and config['manualSend'] is True
    assert asyncio.run(backend.Plugin.set_controller_backend(None, 'sdl'))['success']
    assert backend._read_button_config()['controllerBackend'] == 'sdl'
    assert backend._read_button_config()['controllerBackendOptIn'] is True
    # Any unrelated settings save must retain the deliberate choice.
    config = backend._read_button_config()
    config['manualSend'] = False
    backend._write_button_config(config)
    assert backend._read_button_config()['controllerBackend'] == 'sdl'


def test_failed_switch_restores_sdl_opt_in(setting):
    _, restart = setting
    assert asyncio.run(backend.Plugin.set_controller_backend(None, 'sdl'))['success']
    restart.side_effect = [False, True]
    assert not asyncio.run(backend.Plugin.set_controller_backend(None, 'legacy'))['success']
    config = backend._read_button_config()
    assert config['controllerBackend'] == 'sdl' and config['controllerBackendOptIn'] is True


@pytest.mark.parametrize('value', ['broken', None, [], 'sdl'])
def test_invalid_or_unconfirmed_backend_uses_legacy(setting, value):
    import json
    from pathlib import Path
    Path(backend.BUTTON_CONFIG_FILE).write_text(json.dumps({'controllerBackend': value}))
    assert backend._read_button_config()['controllerBackend'] == 'legacy'
