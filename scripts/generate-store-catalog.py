#!/usr/bin/env python3
"""Generate the static Decky custom-store catalog for Decktation."""

import argparse
from functools import cmp_to_key
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def read_json(path: Path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def validate_url(value: str):
    parsed_url = urlparse(value)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError(f"artifact URL must be absolute HTTPS: {value}")


def version_parts(value: str):
    match = SEMVER_RE.fullmatch(value)
    if not match:
        raise ValueError(f"invalid SemVer version: {value}")
    prerelease = match.group(4)
    return (
        tuple(int(part) for part in match.groups()[:3]),
        prerelease.split(".") if prerelease else None,
    )


def compare_versions(left, right):
    left_main, left_pre = version_parts(left["name"])
    right_main, right_pre = version_parts(right["name"])
    if left_main != right_main:
        return (left_main > right_main) - (left_main < right_main)
    if left_pre is None or right_pre is None:
        return (left_pre is None) - (right_pre is None)

    for left_part, right_part in zip(left_pre, right_pre):
        if left_part == right_part:
            continue
        left_numeric = left_part.isdigit()
        right_numeric = right_part.isdigit()
        if left_numeric and right_numeric:
            return (int(left_part) > int(right_part)) - (
                int(left_part) < int(right_part)
            )
        if left_numeric != right_numeric:
            return -1 if left_numeric else 1
        return (left_part > right_part) - (left_part < right_part)
    return (len(left_pre) > len(right_pre)) - (len(left_pre) < len(right_pre))


def github_release_versions(repository: str):
    request = Request(
        f"https://api.github.com/repos/{repository}/releases?per_page=100",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "decktation-store-catalog",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urlopen(request, timeout=30) as response:
            releases = json.load(response)
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"warning: unable to load historical GitHub releases: {error}", file=sys.stderr)
        return []

    versions = []
    for release in releases:
        tag = release.get("tag_name", "")
        name = tag[1:] if tag.startswith("v") else tag
        if not SEMVER_RE.fullmatch(name):
            continue
        asset = next(
            (
                candidate
                for candidate in release.get("assets", [])
                if candidate.get("name") == "decktation.zip"
            ),
            None,
        )
        digest = asset.get("digest", "") if asset else ""
        if not asset or not digest.startswith("sha256:"):
            continue
        artifact_url = asset["browser_download_url"]
        validate_url(artifact_url)
        versions.append(
            {
                "name": name,
                "hash": digest.removeprefix("sha256:"),
                "artifact": artifact_url,
            }
        )
    return versions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plugin-manifest", type=Path, default=Path("plugin.json")
    )
    parser.add_argument(
        "--package-manifest", type=Path, default=Path("package.json")
    )
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--github-repository",
        help="include installable historical versions from this GitHub repository",
    )
    args = parser.parse_args()

    plugin = read_json(args.plugin_manifest)
    package = read_json(args.package_manifest)
    if plugin["version"] != package["version"]:
        raise SystemExit(
            "plugin.json and package.json versions must match before publishing"
        )

    try:
        validate_url(args.artifact_url)
        version_parts(plugin["version"])
    except ValueError as error:
        raise SystemExit(str(error)) from error
    if not args.artifact.is_file():
        raise SystemExit(f"artifact does not exist: {args.artifact}")

    artifact_hash = hashlib.sha256(args.artifact.read_bytes()).hexdigest()
    publish = plugin["publish"]
    current_version = {
        "name": plugin["version"],
        "hash": artifact_hash,
        "artifact": args.artifact_url,
    }
    versions = [current_version]
    if args.github_repository:
        versions.extend(github_release_versions(args.github_repository))

    versions_by_name = {version["name"]: version for version in versions}
    versions_by_name[current_version["name"]] = current_version
    versions = sorted(
        versions_by_name.values(),
        key=cmp_to_key(compare_versions),
        reverse=True,
    )

    catalog = [
        {
            "id": 1,
            "name": plugin["name"],
            "author": plugin["author"],
            "description": publish["description"],
            "tags": publish["tags"],
            "image_url": publish["image"],
            "versions": versions,
        }
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        json.dump(catalog, destination, indent=2)
        destination.write("\n")


if __name__ == "__main__":
    main()
