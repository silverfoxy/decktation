"""Prepare the pinned, minimal Linux runtime used independently of Decky.

Build-time only. No downloads, pip, or system installation happen on the Deck.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

VERSION = '3.11.17'
BUILD = '20261013'
URL = ('https://github.com/astral-sh/python-build-standalone/releases/download/'
       + BUILD + '/cpython-' + VERSION + '%2B' + BUILD
       + '-x86_64-unknown-linux-gnu-install_only.tar.gz')
SHA256 = '846bf682e2b67393f2affa5e5c0994e446abc3a7cc5bb699890c36346823644c'


def prepare(archive, destination):
    archive, destination = Path(archive), Path(destination)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Private Python archive checksum mismatch')
    if destination.exists():
        raise ValueError('Runtime destination already exists')
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        with tarfile.open(archive) as tar:
            # The archive is checksum-pinned; still reject traversal entries.
            for entry in tar.getmembers():
                if entry.name.startswith('/') or '..' in Path(entry.name).parts:
                    raise ValueError('Unsafe runtime archive entry')
                if entry.issym() or entry.islnk():
                    target = (root / entry.name).parent / entry.linkname if entry.issym() else root / entry.linkname
                    if root.resolve() not in target.resolve().parents:
                        raise ValueError('Unsafe runtime archive link')
                if entry.isdev() or entry.isfifo():
                    raise ValueError('Unexpected special runtime archive entry')
            tar.extractall(root)
        source = root / 'python'
        (destination / 'bin').mkdir(parents=True)
        (destination / 'lib').mkdir()
        shutil.copy2(source / 'bin/python3.11', destination / 'bin/python3.11')
        stdlib = destination / 'lib/python3.11'
        shutil.copytree(source / 'lib/python3.11', stdlib, ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '*.pyo', 'site-packages', 'ensurepip',
            'idlelib', 'tkinter', 'turtledemo', 'test', 'tests', 'config-3.11-*',
        ))
        # This build's executable is self-contained (no libpython DT_NEEDED).
        # Retain stdlib native modules, but not the optional Tk GUI extension.
        for item in (stdlib / 'lib-dynload').glob('_tkinter*'):
            item.unlink()
        for native in [destination / 'bin/python3.11', *(stdlib / 'lib-dynload').glob('*.so')]:
            subprocess.run(['strip', '--strip-unneeded', str(native)], check=True)
        (destination / 'runtime.json').write_text(json.dumps({
            'python': VERSION, 'build': BUILD, 'source': URL, 'sha256': SHA256,
        }, indent=2) + '\n')
        # Keep Python's own full license; component licenses are also packaged.
        shutil.copy2(stdlib / 'LICENSE.txt', destination / 'LICENSE.txt')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination')
    parser.add_argument('--archive')
    args = parser.parse_args()
    if args.archive:
        prepare(args.archive, args.destination)
    else:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'python.tar.gz'
            urllib.request.urlretrieve(URL, archive)
            prepare(archive, args.destination)


if __name__ == '__main__':
    main()
