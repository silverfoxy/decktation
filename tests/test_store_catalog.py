from functools import cmp_to_key
import importlib.util
from pathlib import Path


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
