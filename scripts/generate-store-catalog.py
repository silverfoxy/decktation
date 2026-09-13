#!/usr/bin/env python3
"""Generate the static Decky custom-store catalog for Decktation."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


def read_json(path: Path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


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
    args = parser.parse_args()

    plugin = read_json(args.plugin_manifest)
    package = read_json(args.package_manifest)
    if plugin["version"] != package["version"]:
        raise SystemExit(
            "plugin.json and package.json versions must match before publishing"
        )

    parsed_url = urlparse(args.artifact_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise SystemExit("artifact URL must be an absolute HTTPS URL")
    if not args.artifact.is_file():
        raise SystemExit(f"artifact does not exist: {args.artifact}")

    artifact_hash = hashlib.sha256(args.artifact.read_bytes()).hexdigest()
    publish = plugin["publish"]
    catalog = [
        {
            "id": 1,
            "name": plugin["name"],
            "author": plugin["author"],
            "description": publish["description"],
            "tags": publish["tags"],
            "image_url": publish["image"],
            "versions": [
                {
                    "name": plugin["version"],
                    "hash": artifact_hash,
                    "artifact": args.artifact_url,
                }
            ],
        }
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        json.dump(catalog, destination, indent=2)
        destination.write("\n")


if __name__ == "__main__":
    main()
