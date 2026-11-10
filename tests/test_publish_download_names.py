import json
import os
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[1]


def record_pr_metadata(tmp_path, monkeypatch, number=94):
    import importlib.util
    import sys
    import zipfile
    spec = importlib.util.spec_from_file_location('record_pr', REPO / 'scripts/record-pr-artifact.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    artifact = tmp_path / 'candidate.zip'
    with zipfile.ZipFile(artifact, 'w') as archive:
        archive.writestr('decktation/plugin.json', json.dumps({
            'name': 'Decktation', 'version': f'0.3.22-dev.pr-{number}.bbbbbbb'}))
    output = tmp_path / f'pages/pulls/{number}/123/1/metadata.json'
    for key, value in dict(GITHUB_TOKEN='unused', GITHUB_REPOSITORY='silverfoxy/decktation',
                           PAGES_BASE_URL='https://decktation.com', PR_NUMBER=str(number),
                           PR_RUN_ID='123', PR_RUN_ATTEMPT='1', PR_HEAD_REPO='contributor/decktation',
                           GITHUB_SHA='a' * 40, BUILD_SHA='b' * 40).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(module, 'artifact_metadata', lambda *args: {
        'id': 987, 'expires_at': '2099-01-01T00:00:00Z', 'size_in_bytes': artifact.stat().st_size})
    monkeypatch.setattr(sys, 'argv', ['record-pr-artifact.py', '--artifact', str(artifact), '--output', str(output)])
    module.main()
    return output, artifact


def test_publisher_uses_build_sha_instead_of_workflow_run_master_sha(tmp_path, monkeypatch):
    output, _ = record_pr_metadata(tmp_path, monkeypatch)
    assert json.loads(output.read_text())['commit'] == 'b' * 40
    workflow = (REPO / '.github/workflows/publish.yml').read_text()
    assert workflow.count('BUILD_SHA: ${{ github.event.workflow_run.head_sha }}') == 2
    assert 'GITHUB_SHA:' not in workflow


def test_trusted_publisher_uploads_one_canonical_release_asset(tmp_path):
    workflow = (REPO / '.github/workflows/publish.yml').read_text()
    step = workflow.split('- name: Name the public release download', 1)[1].split('- name:', 1)[0]
    command = step.split('run: ', 1)[1].strip()
    output = tmp_path / 'build-output'
    output.mkdir()
    (output / 'decktation.zip').write_bytes(b'installable plugin')
    subprocess.run(['bash', '-c', command], cwd=tmp_path, check=True)
    assert (output / 'Decktation.zip').read_bytes() == b'installable plugin'
    assert (output / 'decktation.zip').read_bytes() == b'installable plugin'
    upload = workflow.split('- name: Upload release archive', 1)[1].split('  publish-pr:', 1)[0]
    assert 'build-output/Decktation.zip' in upload
    assert 'build-output/decktation.zip' not in upload
    assert 'files: build-output/Decktation.zip' in upload


def test_publisher_refreshes_testing_catalog_after_branch_package_is_written():
    script = (REPO / 'scripts/publish-pages.sh').read_text()
    assert 'git -C "$WORKSPACE_DIR" fetch origin master' in script
    assert 'scripts/generate-pr-catalog.py' in script
    assert '--repository "$GITHUB_REPOSITORY"' in script
    assert script.index('render_pages_content\n  refresh_testing_catalog\n  if publish_pages') > 0


def test_tag_stable_catalog_reads_release_manifests_not_current_master():
    script = (REPO / 'scripts/publish-pages.sh').read_text()
    assert 'git -C "$WORKSPACE_DIR" show "$BUILD_SHA:plugin.json"' in script
    assert 'git -C "$WORKSPACE_DIR" show "$BUILD_SHA:package.json"' in script


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


def test_pr_metadata_is_written_without_copying_zip_to_pages(tmp_path, monkeypatch):
    output, artifact = record_pr_metadata(tmp_path, monkeypatch, number=81)
    assert not list((tmp_path / 'pages').rglob('*.zip'))
    data = json.loads(output.read_text())
    assert data['zip_url'] == 'https://decktation.com/pulls/81/123/1/Decktation.zip'
    assert data['run_attempt'] == 1
    assert data['artifact_id'] == 987
    assert data['sha256'] == __import__('hashlib').sha256(artifact.read_bytes()).hexdigest()
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
