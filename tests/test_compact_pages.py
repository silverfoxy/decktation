import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "compact_pages", Path(__file__).parents[1] / "scripts/compact-pages.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_metadata(directory, **data):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "metadata.json").write_text(json.dumps(data))


def test_release_migration_preserves_hashes_and_pins_latest_metadata(tmp_path):
    old_url = "https://decktation.com/releases/latest/Decktation.zip"
    release = tmp_path / "releases/latest"
    write_metadata(release, ref="v0.3.20", zip_url=old_url)
    (release / "index.html").write_text(f'<a href="{old_url}">{old_url}</a>')
    (release / "Decktation.zip").write_bytes(b"release")
    (tmp_path / "latest.zip").write_bytes(b"release")
    catalog = tmp_path / "store/plugins.json"
    catalog.parent.mkdir()
    catalog.write_text(json.dumps([{"versions": [
        {"name": "0.3.20", "hash": "abc", "artifact": old_url},
        {"name": "0.3.21-dev.123", "hash": "def", "artifact": "https://example.com/branch.zip"},
    ]}]))
    MODULE.compact(tmp_path, "silverfoxy/decktation")
    target = "https://github.com/silverfoxy/decktation/releases/download/v0.3.20/Decktation.zip"
    assert json.loads((release / "metadata.json").read_text())["zip_url"] == target
    assert (release / "index.html").read_text() == f'<a href="{target}">{target}</a>'
    assert not list(tmp_path.rglob("*.zip"))
    versions = json.loads(catalog.read_text())[0]["versions"]
    assert versions[0] == {"name": "0.3.20", "hash": "abc", "artifact": target.replace("/Decktation.zip", "/decktation.zip")}
    assert len(versions) == 1
    before = catalog.read_bytes()
    MODULE.compact(tmp_path, "silverfoxy/decktation")
    assert catalog.read_bytes() == before


def test_all_branch_previews_are_retired_and_only_metadata_remains(tmp_path):
    for name in ("master", "current", "old", "new"):
        directory = tmp_path / "branches" / name
        write_metadata(directory, ref=name)
        (directory / "Decktation.zip").write_bytes(b"x" * 100)
    MODULE.compact(tmp_path, "owner/repo", "current")
    assert not (tmp_path / "branches").exists()
    assert not list(tmp_path.rglob("*.zip"))


def test_pr_zips_are_removed_and_legacy_entries_retired(tmp_path):
    legacy = tmp_path / "pulls/104/100/1"
    current = tmp_path / "pulls/104/101/1"
    for directory in (legacy, current):
        write_metadata(directory, number=104, **({'artifact_id': 123} if directory == current else {}))
        (directory / "Decktation.zip").write_bytes(b"x" * 100)
    MODULE.compact(tmp_path, "owner/repo")
    assert not legacy.exists()
    assert (current / "metadata.json").exists()
    assert not list(tmp_path.rglob("*.zip"))
    MODULE.compact(tmp_path, "owner/repo")


def test_required_metadata_over_budget_fails_without_expiring_it(tmp_path):
    directory = tmp_path / "pulls/104/100/1"
    write_metadata(directory, number=104, artifact_id=123)
    with pytest.raises(ValueError, match="exceed"):
        MODULE.compact(tmp_path, "owner/repo", budget=1)
    assert (directory / "metadata.json").exists()


def test_latest_build_keeps_immutable_url_and_hash_during_compaction(tmp_path):
    catalog = tmp_path / 'store/plugins.json'
    catalog.parent.mkdir()
    latest = {'name': 'Latest', 'hash': 'a' * 64,
              'artifact': 'https://github.com/owner/repo/releases/download/master-sha/decktation.zip'}
    catalog.write_text(json.dumps([{'versions': [latest, {'name': '0.3.24', 'hash': 'b' * 64}]}]))
    MODULE.compact(tmp_path, 'owner/repo')
    assert json.loads(catalog.read_text())[0]['versions'][0] == latest
