import json
import os
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[1]


def test_publisher_refreshes_testing_catalog_after_branch_package_is_written():
    script = (REPO / 'scripts/publish-pages.sh').read_text()
    assert 'git -C "$WORKSPACE_DIR" fetch origin master' in script
    assert 'scripts/generate-pr-catalog.py' in script
    assert '--repository "$GITHUB_REPOSITORY"' in script
    assert script.index('render_pages_content\n  refresh_testing_catalog\n  if publish_pages') > 0


def test_tag_stable_catalog_reads_release_manifests_not_current_master():
    script = (REPO / 'scripts/publish-pages.sh').read_text()
    assert 'git -C "$WORKSPACE_DIR" show "$GITHUB_SHA:plugin.json"' in script
    assert 'git -C "$WORKSPACE_DIR" show "$GITHUB_SHA:package.json"' in script


def test_published_branch_names_are_html_escaped(tmp_path):
    branch = tmp_path / 'branches' / 'hostile'
    branch.mkdir(parents=True)
    (branch / 'metadata.json').write_text(json.dumps({'ref': '<svg/onload=alert(1)>'}))
    script = (REPO / 'scripts/publish-pages.sh').read_text().split('\nfor attempt in 1 2 3;')[0]
    script += '''
PAGES_DIR="$TEST_PAGES_DIR"
render_index_list "$PAGES_DIR/branches" "Branches" "https://decktation.com"
write_download_page "$TEST_PAGE" "Decktation branch build: <svg/onload=alert(1)>" "https://example.com/zip" "https://example.com/metadata"
'''
    env = dict(os.environ, GITHUB_TOKEN='unused', GITHUB_REPOSITORY='silverfoxy/decktation',
               CLEANUP_ONLY='true', PAGES_BASE_URL='https://decktation.com',
               TEST_PAGES_DIR=str(tmp_path), TEST_PAGE=str(tmp_path / 'page.html'))
    result = subprocess.run(['bash', '-c', script], cwd=REPO, env=env,
                            check=True, capture_output=True, text=True)
    assert '<svg' not in result.stdout + (tmp_path / 'page.html').read_text()
    assert '&lt;svg' in result.stdout + (tmp_path / 'page.html').read_text()


def test_older_tag_cannot_roll_back_latest_release(tmp_path):
    latest = tmp_path / 'releases/latest'
    latest.mkdir(parents=True)
    (latest / 'metadata.json').write_text(json.dumps({
        'ref': 'v0.3.20', 'commit': 'a' * 40, 'channel': 'release-latest'}))
    script = (REPO / 'scripts/publish-pages.sh').read_text().split('\nfor attempt in 1 2 3;')[0]
    script += '\nPAGES_DIR="$TEST_PAGES_DIR"\nassert_release_is_not_older\n'
    env = dict(os.environ, GITHUB_TOKEN='unused', GITHUB_REPOSITORY='silverfoxy/decktation',
               CLEANUP_ONLY='true', PAGES_BASE_URL='https://decktation.com',
               TEST_PAGES_DIR=str(tmp_path), REF_TYPE='tag', RELEASE_TAG='v0.3.19', GITHUB_SHA='b' * 40)
    result = subprocess.run(['bash', '-c', script], cwd=REPO, env=env, capture_output=True)
    assert result.returncode != 0
    assert b'older release' in result.stderr.lower()


def test_pr_package_is_written_under_immutable_run_id(tmp_path):
    pages = tmp_path / 'pages'
    artifact = tmp_path / 'candidate.zip'
    artifact.write_bytes(b'candidate bytes')
    script = (REPO / 'scripts/publish-pages.sh').read_text().split('\nfor attempt in 1 2 3;')[0]
    script += '\nPAGES_DIR="$TEST_PAGES_DIR"\nZIP_SOURCE="$TEST_ARTIFACT"\nrender_pr_content\n'
    env = dict(os.environ, GITHUB_TOKEN='unused', GITHUB_REPOSITORY='silverfoxy/decktation',
               CLEANUP_ONLY='true', PAGES_BASE_URL='https://decktation.com',
               TEST_PAGES_DIR=str(pages), TEST_ARTIFACT=str(artifact), PR_NUMBER='81',
               PR_RUN_ID='123', PR_RUN_ATTEMPT='1', PR_HEAD_REPO='contributor/decktation', GITHUB_SHA='a' * 40)
    subprocess.run(['bash', '-c', script], cwd=REPO, env=env, check=True, capture_output=True)
    folder = pages / 'pulls/81/123/1'
    assert (folder / 'Decktation.zip').read_bytes() == b'candidate bytes'
    data = json.loads((folder / 'metadata.json').read_text())
    assert data['zip_url'] == 'https://decktation.com/pulls/81/123/1/Decktation.zip'
    assert data['run_attempt'] == 1
    assert data['sha256'] == __import__('hashlib').sha256(b'candidate bytes').hexdigest()
    assert data['head_repository'] == 'contributor/decktation'


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
    assert (branch / 'decktation.zip').read_bytes() == b'new branch'
    metadata = json.loads((branch / 'metadata.json').read_text())
    assert metadata['zip_url'] == 'https://example.com/branches/feat-transcription-review/Decktation.zip'
    assert metadata['commit'] == 'abc123'
    assert 'Decktation.zip' in (branch / 'index.html').read_text()
    assert (old / 'Decktation.zip').read_bytes() == b'old branch'
    assert json.loads((old / 'metadata.json').read_text())['zip_url'].endswith('/Decktation.zip')
    assert (pages / 'Decktation.zip').read_bytes() == b'stable release'
