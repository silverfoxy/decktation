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
    assert versions[1]["artifact"] == "https://example.com/branch.zip"
    before = catalog.read_bytes()
    MODULE.compact(tmp_path, "silverfoxy/decktation")
    assert catalog.read_bytes() == before


def test_branch_budget_keeps_master_current_and_newest_then_expires_oldest(tmp_path):
    for name, timestamp in [("master", "1"), ("current", "0"), ("old", "2"), ("new", "3")]:
        directory = tmp_path / "branches" / name
        write_metadata(directory, ref=name, generated_at=timestamp)
        (directory / "decktation.zip").write_bytes(b"x" * 100)
        (directory / "Decktation.zip").write_bytes(b"x" * 100)
    branch = tmp_path / "branches"
    one_size = 100 + (branch / "master/metadata.json").stat().st_size
    MODULE.compact(tmp_path, "owner/repo", "current", budget=one_size * 3 + 10)
    assert sorted(p.name for p in branch.iterdir()) == ["current", "master", "new"]
    assert not list(branch.rglob("decktation.zip"))
    with pytest.raises(ValueError, match="exceed"):
        MODULE.compact(tmp_path, "owner/repo", "current", budget=1)
