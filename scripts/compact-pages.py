#!/usr/bin/env python3
"""Keep bounded branch previews and PR metadata; remove release and PR ZIP copies."""

import argparse
import json
from pathlib import Path
import re
import shutil


def compact(root, repository, current_branch="", budget=512 * 1024 * 1024):
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
            for version in plugin["versions"]:
                if re.fullmatch(r"\d+\.\d+\.\d+", version["name"]):
                    version["artifact"] = f"{release_base}/download/v{version['name']}/decktation.zip"
        catalog.write_text(json.dumps(data, indent=2) + "\n")

    branches = []
    for metadata in (root / "branches").glob("*/metadata.json"):
        directory = metadata.parent
        old = directory / "decktation.zip"
        canonical = directory / "Decktation.zip"
        if old.exists():
            if not canonical.exists():
                old.rename(canonical)
            else:
                old.unlink()
        data = json.loads(metadata.read_text())
        protected = data["ref"] in ("master", current_branch)
        size = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
        branches.append((protected, data.get("generated_at", ""), directory, size))
    # Keep the newest immutable build for each PR. Older runs/attempts can
    # expire; the publisher regenerates the catalog from surviving files.
    for pr in (root / "pulls").glob("*"):
        builds = sorted(
            (metadata.parent for metadata in pr.glob("*/*/metadata.json")
             if metadata.parent.name.isdecimal() and metadata.parent.parent.name.isdecimal()),
            key=lambda directory: (int(directory.parent.name), int(directory.name)),
            reverse=True,
        )
        migrated = []
        for directory in builds:
            data = json.loads((directory / "metadata.json").read_text())
            if 'artifact_id' not in data:
                print(f"Retiring legacy Pages PR download: {directory.relative_to(root)}")
                shutil.rmtree(directory)
                continue
            for archive in directory.glob('*.zip'):
                archive.unlink()
            migrated.append(directory)
        builds = migrated
        for index, directory in enumerate(builds):
            size = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
            # Empty dates expire superseded PR builds before branch previews.
            branches.append((index == 0, "", directory, size))

    preview_dirs = [directory for _, _, directory, _ in branches]
    used = sum(p.stat().st_size for p in root.rglob("*")
               if p.is_file() and ".git" not in p.relative_to(root).parts
               and not any(directory in p.parents for directory in preview_dirs))
    required = used + sum(size for protected, _, _, size in branches if protected)
    if required > budget:
        raise ValueError("Current/master branch and latest PR downloads exceed the Pages budget")
    for protected, _, directory, size in sorted(branches, reverse=True):
        if used + size <= budget:
            used += size
        elif protected:
            raise ValueError("Current/master branch downloads exceed the Pages budget")
        else:
            print(f"Expiring preview: {directory.relative_to(root)}")
            shutil.rmtree(directory)
    print(f"Pages content: {used} bytes (budget {budget})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--current-branch", default="")
    args = parser.parse_args()
    compact(args.root, args.repository, args.current_branch)
