#!/usr/bin/env python3
"""Keep Pages metadata only; all plugin ZIPs live in Releases or Actions."""

import argparse
import json
from pathlib import Path
import re
import shutil


def compact(root, repository, current_branch="", budget=8 * 1024 * 1024):
    release_base = f"https://github.com/{repository}/releases"
    for metadata in (root / "releases").glob("*/metadata.json"):
        data = json.loads(metadata.read_text())
        tag = data["ref"]
        if not re.fullmatch(r"v[0-9A-Za-z.+-]+", tag):
            raise ValueError(f"Invalid release tag: {tag}")
        target = f"{release_base}/download/{tag}/Decktation.zip"
        data["zip_url"] = target
        metadata.write_text(json.dumps(data, indent=2) + "\n")
        page = metadata.with_name("index.html")
        if page.exists():
            page.write_text(re.sub(
                r'https://[^\s<>"\x27]+/releases/[^/\s<>"\x27]+/(?:decktation|Decktation)\.zip',
                lambda _: target, page.read_text()))
        for archive in metadata.parent.glob("*.zip"):
            archive.unlink()
    for name in ("latest.zip", "Decktation.zip", "decktation.zip"):
        (root / name).unlink(missing_ok=True)

    catalog = root / "store/plugins.json"
    if catalog.exists():
        data = json.loads(catalog.read_text())
        for plugin in data:
            plugin["versions"] = [version for version in plugin["versions"]
                                  if version["name"] == "Latest" or
                                  re.fullmatch(r"\d+\.\d+\.\d+", version["name"])]
            for version in plugin["versions"]:
                if version["name"] == "Latest":
                    continue
                version["artifact"] = f"{release_base}/download/v{version['name']}/decktation.zip"
        catalog.write_text(json.dumps(data, indent=2) + "\n")

    # Branch previews are no longer published. Stable ZIPs live in Releases;
    # only PR Actions artifact metadata belongs in the testing catalog.
    if (root / "branches").exists():
        shutil.rmtree(root / "branches")
    for metadata in (root / "pulls").glob("*/*/*/metadata.json"):
        if 'artifact_id' not in json.loads(metadata.read_text()):
            shutil.rmtree(metadata.parent)
    for directory in (root / "branches", root / "pulls"):
        for archive in directory.rglob("*.zip"):
            archive.unlink()
    used = sum(p.stat().st_size for p in root.rglob("*")
               if p.is_file() and ".git" not in p.relative_to(root).parts)
    if used > budget:
        raise ValueError("Pages metadata exceeds the budget")
    print(f"Pages metadata: {used} bytes (budget {budget}); no plugin ZIP copies")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--current-branch", default="")
    args = parser.parse_args()
    compact(args.root, args.repository, args.current_branch)
