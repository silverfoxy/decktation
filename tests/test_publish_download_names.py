import json
import os
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[1]


def test_branch_publish_uses_manifest_name_and_migrates_existing_downloads(tmp_path):
    pages = tmp_path / 'pages'
    old = pages / 'branches' / 'old-branch'
    old.mkdir(parents=True)
    (old / 'decktation.zip').write_bytes(b'old branch')
    (old / 'metadata.json').write_text(json.dumps({'ref': 'old/branch'}))
    (pages / 'latest.zip').write_bytes(b'stable release')
    artifact = tmp_path / 'build.zip'
    artifact.write_bytes(b'new branch')
    # Execute the real publisher functions locally, excluding Git/network work.
    script = (REPO / 'scripts/publish-pages.sh').read_text().split('\nfor attempt in 1 2 3;')[0]
    script += '''
PAGES_DIR="$TEST_PAGES_DIR"
ZIP_SOURCE="$TEST_ARTIFACT"
CLEANUP_ONLY=false
REF_NAME=feat/transcription-review
REF_TYPE=branch
migrate_branch_dirs() { :; }
cleanup_deleted_branch_dirs() { :; }
render_pages_content
'''
    env = dict(os.environ, GITHUB_TOKEN='unused', GITHUB_REPOSITORY='silverfoxy/decktation',
               GITHUB_SHA='abc123', CLEANUP_ONLY='true',
               PAGES_BASE_URL='https://example.com', TEST_PAGES_DIR=str(pages),
               TEST_ARTIFACT=str(artifact))
    subprocess.run(['bash', '-c', script], cwd=REPO, env=env, check=True, capture_output=True)
    branch = pages / 'branches' / 'feat-transcription-review'
    assert (branch / 'Decktation.zip').read_bytes() == b'new branch'
    assert not (branch / 'decktation.zip').exists()
    metadata = json.loads((branch / 'metadata.json').read_text())
    assert metadata['zip_url'] == 'https://example.com/branches/feat-transcription-review/Decktation.zip'
    assert metadata['commit'] == 'abc123'
    assert 'Decktation.zip' in (branch / 'index.html').read_text()
    assert (old / 'Decktation.zip').read_bytes() == b'old branch'
    assert json.loads((old / 'metadata.json').read_text())['zip_url'].endswith('/Decktation.zip')
    assert not (pages / 'Decktation.zip').exists()
    assert not (pages / 'latest.zip').exists()
    assert not (old / 'decktation.zip').exists()
