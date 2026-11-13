"""Private per-user IPC paths, isolated from older root-owned plugin files."""
import os
from pathlib import Path
import stat
import tempfile


def ipc_path(name):
    if not name or Path(name).name != name:
        raise ValueError('IPC name must be a filename')
    directory = Path(tempfile.gettempdir()) / f'decktation-{os.geteuid()}'
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
            stat.S_IMODE(info.st_mode) != 0o700):
        raise PermissionError(f'Unsafe Decktation runtime directory: {directory}')
    return str(directory / name)
