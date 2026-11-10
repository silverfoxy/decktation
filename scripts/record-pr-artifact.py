#!/usr/bin/env python3
"""Record a validated raw Actions artifact without copying its ZIP to Pages."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

SPEC = importlib.util.spec_from_file_location('pr_catalog', Path(__file__).with_name('generate-pr-catalog.py'))
CATALOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CATALOG)


def artifact_metadata(repository, run_id, sha, digest, size, token):
    matches = []
    page = 1
    while True:
        request = Request(
            f'https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100&page={page}',
            headers={'Accept': 'application/vnd.github+json', 'Authorization': f'Bearer {token}',
                     'User-Agent': 'decktation-pr-publisher'})
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)['artifacts']
        matches.extend(item for item in batch if item.get('name') == 'decktation.zip' and
                       not item.get('expired') and item.get('digest') == f'sha256:{digest}' and
                       item.get('size_in_bytes') == size and
                       item.get('workflow_run', {}).get('id') == run_id and
                       item.get('workflow_run', {}).get('head_sha') == sha)
        if len(batch) < 100:
            break
        page += 1
    if len(matches) != 1:
        raise ValueError('Expected one unexpired raw Actions artifact matching the verified ZIP')
    artifact = matches[0]
    if datetime.fromisoformat(artifact['expires_at'].replace('Z', '+00:00')) <= datetime.now(timezone.utc):
        raise ValueError('Actions artifact expired')
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    number, run, attempt = (int(os.environ[key]) for key in ('PR_NUMBER', 'PR_RUN_ID', 'PR_RUN_ATTEMPT'))
    sha, repository = os.environ['BUILD_SHA'], os.environ['GITHUB_REPOSITORY']
    if not 0 < args.artifact.stat().st_size <= 512 * 1024 * 1024:
        raise ValueError('PR artifact exceeds download size limit')
    head_repo, base = os.environ['PR_HEAD_REPO'], CATALOG.PR_ARTIFACT_BASE
    with args.artifact.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    data = {'channel': 'pull_request', 'number': number, 'run_id': run, 'run_attempt': attempt,
            'commit': sha, 'head_repository': head_repo, 'sha256': digest,
            'zip_url': f'{base}/pulls/{number}/{run}/{attempt}/Decktation.zip'}
    # Reuse the complete package validator before trusting metadata without ZIP bytes.
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        folder = root / 'pulls' / str(number) / str(run) / str(attempt)
        folder.mkdir(parents=True)
        shutil.copyfile(args.artifact, folder / 'Decktation.zip')
        (folder / 'metadata.json').write_text(json.dumps(data))
        version = CATALOG.verified_pr_version(root, number, run, attempt, sha, head_repo, base)
        if not version:
            raise ValueError('Invalid PR package')
    artifact = artifact_metadata(repository, run, sha, digest, args.artifact.stat().st_size,
                                 os.environ['GITHUB_TOKEN'])
    data.update(artifact_id=artifact['id'], expires_at=artifact['expires_at'],
                size_in_bytes=artifact['size_in_bytes'], version=version['name'])
    if args.output.exists():
        previous = json.loads(args.output.read_text())
        # Upgrade legacy metadata only if all previously pinned fields match.
        if any(data.get(key) != value for key, value in previous.items()):
            raise ValueError('Refusing to overwrite immutable PR artifact metadata')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
