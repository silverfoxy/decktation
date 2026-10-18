#!/usr/bin/env python3
"""Build an opt-in catalog of current open PR artifacts, including forks.

Never execute a candidate's files here. PR ZIPs are immutable by run ID;
only trusted default-branch publisher code writes the catalog.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from urllib.request import Request, urlopen
import zipfile

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('master_build_helpers', HERE / 'verify-master-build.py')
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)
STORE = HELPERS.STORE
SHA_RE = HELPERS.SHA_RE


def fetch_open_prs(repository, token):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    results = []
    page = 1
    while True:
        request = Request(f'https://api.github.com/repos/{repository}/pulls?state=open&per_page=100&page={page}',
                          headers={'Accept': 'application/vnd.github+json',
                                   'Authorization': f'Bearer {token}',
                                   'User-Agent': 'decktation-pr-catalog'})
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError('GitHub did not return a PR list')
        results.extend(batch)
        if len(batch) < 100:
            return results
        page += 1


def prune_closed_prs(pages_root, pull_requests):
    """Remove closed PR artifacts only after an authoritative full API listing."""
    if not isinstance(pull_requests, list):
        raise ValueError('Open PR list is required for pruning')
    open_numbers = {pr['number'] for pr in pull_requests if pr.get('state') == 'open' and
                    type(pr.get('number')) is int and pr['number'] > 0}
    root = Path(pages_root) / 'pulls'
    if root.is_symlink() or not root.is_dir():
        return
    for directory in root.iterdir():
        if (directory.name.isdecimal() and directory.is_dir() and
                not directory.is_symlink() and int(directory.name) not in open_numbers):
            shutil.rmtree(directory)


def verified_pr_version(root, number, run_id, attempt, sha, repository, base_url):
    folder = root / 'pulls' / str(number) / str(run_id) / str(attempt)
    artifact = folder / 'Decktation.zip'
    metadata = folder / 'metadata.json'
    if (not artifact.is_file() or not metadata.is_file() or artifact.is_symlink() or
            metadata.is_symlink() or folder.is_symlink() or folder.parent.is_symlink()):
        return None
    expected_url = f'{base_url}/pulls/{number}/{run_id}/{attempt}/Decktation.zip'
    try:
        data = json.loads(metadata.read_text(encoding='utf-8'))
        if (data.get('channel') != 'pull_request' or data.get('number') != number or
                data.get('run_id') != run_id or data.get('run_attempt') != attempt or
                data.get('commit') != sha or
                data.get('head_repository') != repository or data.get('zip_url') != expected_url):
            return None
        with zipfile.ZipFile(artifact) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if (len(members) > 10000 or len(names) != len(set(names)) or
                    sum(member.file_size for member in members) > 600 * 1024 * 1024 or
                    any(member.filename.startswith('/') or
                        '..' in PurePosixPath(member.filename).parts or
                        member.file_size > 600 * 1024 * 1024 or
                        (member.external_attr >> 16) & 0o170000 == 0o120000
                        for member in members) or archive.testzip() is not None):
                return None
            manifest = archive.getinfo('decktation/plugin.json')
            if manifest.file_size > 32768:
                return None
            plugin = json.loads(archive.read(manifest))
            version = plugin.get('version')
            if (plugin.get('name') != 'Decktation' or not isinstance(version, str) or
                    not STORE.SEMVER_RE.fullmatch(version) or
                    not version.endswith(f'.pr-{number}.{sha[:7]}')):
                return None
        with artifact.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if data.get('sha256') != digest:
            return None
        return {'name': version, 'hash': digest, 'artifact': expected_url}
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError):
        return None


def build_catalog(pages_root, plugin_manifest, base_url, pull_requests, current_heads):
    STORE.validate_url(base_url)
    base_url = base_url.rstrip('/')
    root = Path(pages_root).resolve()
    plugin = json.loads(Path(plugin_manifest).read_text(encoding='utf-8'))
    versions, labels = [], []
    master = current_heads.get('master')
    if isinstance(master, str) and SHA_RE.fullmatch(master):
        version = HELPERS.verified_version(root, 'master', master, base_url)
        if version:
            versions.append(version)  # Decky preselects the first version.
    if not isinstance(pull_requests, list):
        raise ValueError('Open PR list is required')
    for pr in sorted(pull_requests, key=lambda item: item.get('number', 0)):
        number = pr.get('number')
        head = pr.get('head') or {}
        sha = head.get('sha')
        repo = (head.get('repo') or {}).get('full_name')
        if (pr.get('state') != 'open' or type(number) is not int or number <= 0 or
                not isinstance(sha, str) or not SHA_RE.fullmatch(sha) or
                not isinstance(repo, str)):
            continue
        directory = root / 'pulls' / str(number)
        if not directory.is_dir() or directory.is_symlink():
            continue
        for run in sorted(directory.iterdir(), key=lambda path: int(path.name) if path.name.isdecimal() else -1, reverse=True):
            if not run.name.isdecimal() or run.is_symlink() or not run.is_dir():
                continue
            for attempt in sorted(run.iterdir(), key=lambda path: int(path.name) if path.name.isdecimal() else -1, reverse=True):
                if not attempt.name.isdecimal() or attempt.is_symlink() or not attempt.is_dir():
                    continue
                version = verified_pr_version(root, number, int(run.name), int(attempt.name), sha, repo, base_url)
                if version:
                    versions.append(version)
                    labels.append(f'PR #{number} ({sha[:7]})')
                    break
            else:
                continue
            break
    publish = plugin['publish']
    return [{'id': 1, 'name': plugin['name'], 'author': plugin['author'],
             'description': publish['description'] + ' UNREVIEWED experimental code: ' + ', '.join(labels),
             'tags': publish['tags'], 'image_url': publish['image'], 'versions': versions}]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages-root', required=True, type=Path)
    parser.add_argument('--plugin-manifest', required=True, type=Path)
    parser.add_argument('--current-refs', required=True, type=Path)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    pull_requests = fetch_open_prs(args.repository, os.environ['GITHUB_TOKEN'])
    prune_closed_prs(args.pages_root, pull_requests)
    catalog = build_catalog(args.pages_root, args.plugin_manifest, args.base_url,
                            pull_requests, HELPERS.read_current_refs(args.current_refs))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
