from binding_capture import BindingCapture


def ready():
    capture = BindingCapture('test', 20)
    capture.update({'deck': {'A': True}}, 0)
    assert capture.phase == 'release'
    capture.update({'deck': {}}, 1)
    assert capture.phase == 'listening'
    return capture


def test_capture_overlap_and_staggered_release():
    capture = ready()
    capture.update({'deck': {'L4': True}}, 2)
    capture.update({'deck': {'L4': True, 'View': True}}, 3)
    assert capture.buttons == ['L4', 'View']
    capture.update({'deck': {'View': True}}, 4)
    capture.update({'deck': {}}, 5)
    assert capture.phase == 'captured'
    assert capture.buttons == ['L4', 'View']


def test_new_press_during_release_is_not_added():
    capture = ready()
    capture.update({'deck': {'A': True, 'B': True}}, 2)
    capture.update({'deck': {'B': True}}, 3)
    capture.update({'deck': {'B': True, 'X': True}}, 4)
    capture.update({'deck': {}}, 5)
    assert capture.buttons == ['A', 'B']


def test_two_controllers_never_merge_and_wait_for_release():
    capture = ready()
    capture.update({'deck': {'L4': True}, 'xbox': {}}, 2)
    capture.update({'deck': {'L4': True}, 'xbox': {'View': True}}, 3)
    capture.update({'deck': {}, 'xbox': {'View': True}}, 4)
    assert capture.phase == 'holding'
    capture.update({'deck': {}, 'xbox': {}}, 5)
    assert capture.phase == 'captured'
    assert capture.buttons == ['L4']


def test_disconnect_cancels_instead_of_saving():
    capture = ready()
    capture.update({'deck': {'B': True}}, 2)
    capture.update({}, 3)
    assert capture.phase == 'cancelled'
    assert 'disconnected' in capture.error


def test_timeout_and_limit():
    capture = ready()
    capture.update({'deck': {}}, 20)
    assert capture.phase == 'cancelled'
    capture = ready()
    capture.update({'deck': {str(i): True for i in range(6)}}, 2)
    assert capture.phase == 'cancelled'


def test_rpc_save_clears_request_before_listener_restart(tmp_path, monkeypatch):
    import asyncio
    import importlib.util
    import sys
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    import audio_runtime
    from binding_capture import read_json, write_json
    repo = Path(__file__).parents[1]
    monkeypatch.setitem(sys.modules, 'decky', SimpleNamespace(
        logger=MagicMock(), DECKY_USER_HOME=str(tmp_path), DECKY_SETTINGS_DIR=str(tmp_path)))
    monkeypatch.setenv('DECKY_PLUGIN_DIR', str(repo))
    monkeypatch.setattr(audio_runtime, 'setup_audio_environment', lambda *args: None)
    spec = importlib.util.spec_from_file_location('capture_backend_test', repo / 'backend/src/decktation_backend.py')
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    backend.Plugin.voice_service = None
    backend.Plugin.listener_process = MagicMock()
    backend.Plugin.listener_process.poll.return_value = None
    backend.Plugin.stop_controller_listener = MagicMock()
    request_file = tmp_path / 'binding_capture_request.json'
    def restart():
        assert read_json(request_file)['cancelled'] is True
    backend.Plugin.start_controller_listener = restart
    started = asyncio.run(backend.Plugin.start_binding_capture(None))
    assert started['success']
    write_json(tmp_path / 'binding_capture_result.json', {
        'session': started['session'], 'phase': 'captured', 'buttons': ['L4', 'View']})
    result = asyncio.run(backend.Plugin.get_binding_capture(None, started['session']))
    assert result['phase'] == 'saved'
    assert backend._read_button_config()['buttons'] == ['L4', 'View']
    assert backend.Plugin.binding_session is None
    # Cancelling and stale polling cannot overwrite the saved configuration.
    assert not asyncio.run(backend.Plugin.get_binding_capture(None, started['session']))['success']
