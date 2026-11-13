from functools import cmp_to_key
import importlib.util
from pathlib import Path
import io
import json


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "generate-store-catalog.py"
SPEC = importlib.util.spec_from_file_location("generate_store_catalog", SCRIPT_PATH)
CATALOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CATALOG)


def test_versions_sort_newest_first_with_prereleases_before_previous_release():
    versions = [
        {"name": "0.3.15"},
        {"name": "0.3.16-dev.abcdef0"},
        {"name": "0.3.14"},
        {"name": "0.3.16"},
    ]

    ordered = sorted(
        versions,
        key=cmp_to_key(CATALOG.compare_versions),
        reverse=True,
    )

    assert [version["name"] for version in ordered] == [
        "0.3.16",
        "0.3.16-dev.abcdef0",
        "0.3.15",
        "0.3.14",
    ]


def test_numeric_prerelease_identifiers_use_numeric_ordering():
    left = {"name": "1.0.0-dev.10"}
    right = {"name": "1.0.0-dev.2"}

    assert CATALOG.compare_versions(left, right) > 0


def test_capitalized_release_asset_keeps_url_compatible_with_installed_updaters(monkeypatch):
    response = [{"tag_name": "v0.3.20", "assets": [{
        "name": "Decktation.zip", "digest": "sha256:abc",
        "browser_download_url": "https://github.com/silverfoxy/decktation/releases/download/v0.3.20/Decktation.zip",
    }]}]
    monkeypatch.setattr(CATALOG, "urlopen", lambda *a, **kw: io.BytesIO(json.dumps(response).encode()))
    assert CATALOG.github_release_versions("silverfoxy/decktation") == [{
        "name": "0.3.20", "hash": "abc",
        "artifact": "https://github.com/silverfoxy/decktation/releases/download/v0.3.20/decktation.zip",
    }]


def test_latest_is_first_and_survives_a_later_release(tmp_path, monkeypatch):
    import hashlib
    import sys
    plugin = {"name": "Decktation", "author": "Author", "version": "0.3.24",
              "publish": {"description": "Dictation", "tags": [], "image": "image"}}
    manifest = tmp_path / 'plugin.json'
    manifest.write_text(json.dumps(plugin))
    package = tmp_path / 'package.json'
    package.write_text(json.dumps({"version": "0.3.24"}))
    artifact = tmp_path / 'Decktation.zip'
    artifact.write_bytes(b'master build')
    latest_path, output = tmp_path / 'latest.json', tmp_path / 'plugins.json'
    stable = {"name": "0.3.24", "hash": "a" * 64,
              "artifact": "https://example.com/v0.3.24/decktation.zip"}
    monkeypatch.setattr(CATALOG, 'github_release_versions', lambda _: [stable])
    args = ['catalog', '--plugin-manifest', str(manifest), '--package-manifest', str(package),
            '--artifact', str(artifact), '--artifact-url', 'https://example.com/master-sha/decktation.zip',
            '--github-repository', 'owner/repo', '--output', str(output),
            '--latest-metadata', str(latest_path)]
    monkeypatch.setattr(sys, 'argv', args + ['--publish-latest'])
    CATALOG.main()
    latest = {"name": "Latest", "hash": hashlib.sha256(artifact.read_bytes()).hexdigest(),
              "artifact": 'https://example.com/master-sha/decktation.zip'}
    assert json.loads(output.read_text())[0]['versions'] == [latest, stable]
    artifact.write_bytes(b'release build')
    args[args.index('--artifact-url') + 1] = stable['artifact']
    monkeypatch.setattr(sys, 'argv', args)
    CATALOG.main()
    versions = json.loads(output.read_text())[0]['versions']
    assert versions[0] == latest
    assert versions[1]['name'] == '0.3.24'
    assert versions[1]['hash'] == hashlib.sha256(b'release build').hexdigest()


def test_master_prereleases_do_not_hide_older_numbered_releases(monkeypatch):
    pages = []
    def response(request, **kwargs):
        pages.append(request.full_url)
        batch = ([{'tag_name': 'master-' + str(i)} for i in range(100)]
                 if len(pages) == 1 else [{'tag_name': 'v0.3.24', 'assets': [{
                     'name': 'Decktation.zip', 'digest': 'sha256:abc',
                     'browser_download_url': 'https://github.com/owner/repo/releases/download/v0.3.24/Decktation.zip'}]}])
        return io.BytesIO(json.dumps(batch).encode())
    monkeypatch.setattr(CATALOG, 'urlopen', response)
    assert CATALOG.github_release_versions('owner/repo')[0]['name'] == '0.3.24'
    assert pages[-1].endswith('page=2')
