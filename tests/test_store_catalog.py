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
