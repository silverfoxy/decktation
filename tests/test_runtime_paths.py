import os
from pathlib import Path

import pytest
import runtime_paths


def test_ipc_paths_are_private_shared_and_separate_from_legacy_files(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_paths.tempfile, 'gettempdir', lambda: str(tmp_path))
    path = Path(runtime_paths.ipc_path('decktation_l5'))
    assert path.parent.name == f'decktation-{os.geteuid()}'
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert runtime_paths.ipc_path('decktation_l5') == str(path)
    assert Path(runtime_paths.ipc_path('decktation-ydotool.sock')).parent == path.parent


@pytest.mark.parametrize('kind', ['symlink', 'public'])
def test_unsafe_existing_runtime_directory_is_rejected(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(runtime_paths.tempfile, 'gettempdir', lambda: str(tmp_path))
    directory = tmp_path / f'decktation-{os.geteuid()}'
    if kind == 'symlink':
        directory.symlink_to(tmp_path, target_is_directory=True)
    else:
        directory.mkdir(mode=0o755)
    with pytest.raises(PermissionError):
        runtime_paths.ipc_path('state')


def test_all_input_processes_share_the_same_runtime_directory():
    import controller_listener, controller_output, decktation_backend, gamepad_sdl
    assert controller_listener.STATE_FILE == decktation_backend.STATE_FILE
    assert controller_listener.HAPTIC_SOURCE_FILE == decktation_backend.HAPTIC_SOURCE_FILE
    assert Path(controller_output.INJECTION_FILE).parent == Path(gamepad_sdl.HAPTIC_REQUEST_FILE).parent
    assert Path(decktation_backend.YDOTOOL_SOCKET).parent == Path(controller_listener.STATE_FILE).parent
