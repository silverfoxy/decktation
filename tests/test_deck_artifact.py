"""Exact ZIP checks; no Steam device required."""
import importlib.util
import json
from pathlib import Path
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]

def runner():
    path = ROOT / 'scripts/deck/runner.py'
    assert path.exists(), 'installed-device runner is missing'
    spec = importlib.util.spec_from_file_location('deck_runner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def artifact(tmp_path):
    files = {'package.json': json.dumps({'version': '1.0.0-dev.gabc1234'}).encode(),
             'dist/index.js': b'frontend', 'main.py': b'backend',
             'bin/decktation_backend.py': b'backend', 'bin/controller_listener.py': b'listener',
             'bin/controller_debug_report.py': b'report',
             'bin/controller_debug_session.py': b'PROTOCOL = 2\n'}
    path = tmp_path / 'ci.zip'
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in files.items():
            z.writestr('decktation/' + name, data)
    return path, files


def test_exact_artifact_hashes(tmp_path):
    r = runner()
    path, files = artifact(tmp_path)
    manifest = r.inspect_artifact(path)
    assert manifest['protocol'] == 2
    assert manifest['source_sha_hint'] == 'abc1234'
    assert r.compare_installed(manifest, manifest['files'])['installed_bytes_match']
    wrong = dict(manifest['files'], **{'main.py': '0' * 64})
    with pytest.raises(ValueError, match='mismatch'):
        r.compare_installed(manifest, wrong)
    assert set(manifest['files']) == set(files)


@pytest.mark.parametrize('bad', ['../escape', '/absolute', 'decktation/../escape', 'decktation/link'])
def test_unsafe_zip_rejected(tmp_path, bad):
    r = runner()
    path, _ = artifact(tmp_path)
    with zipfile.ZipFile(path, 'a') as z:
        info = zipfile.ZipInfo(bad)
        if bad.endswith('link'):
            info.external_attr = 0o120777 << 16
        z.writestr(info, 'bad')
    with pytest.raises(ValueError):
        r.inspect_artifact(path)


@pytest.mark.parametrize('kind', ['duplicate', 'oversized', 'protocol', 'missing'])
def test_bad_required_sources(tmp_path, kind):
    r = runner()
    _, files = artifact(tmp_path)
    path = tmp_path / 'bad.zip'
    if kind == 'protocol':
        files['bin/controller_debug_session.py'] = b'PROTOCOL = 1\n'
    if kind == 'missing':
        del files['main.py']
    if kind == 'oversized':
        files['main.py'] = b'x' * (r.MAX_SOURCE + 1)
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr('decktation/' + name, data)
        if kind == 'duplicate':
            with pytest.warns(UserWarning):
                z.writestr('decktation/main.py', 'bad')
    with pytest.raises(ValueError):
        r.inspect_artifact(path)
