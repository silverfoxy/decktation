"""The write-capable publisher must not execute code from candidate branches."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_candidate_builder_never_receives_write_token_or_publishes():
    workflow = (ROOT / '.github/workflows/build.yml').read_text()
    assert 'contents: write' not in workflow
    assert 'scripts/publish-pages.sh' not in workflow
    assert 'softprops/action-gh-release' not in workflow
    assert 'name: decktation.zip' in workflow
    assert 'archive: false' in workflow


def test_publisher_uses_default_branch_code_after_build_completion():
    workflow = (ROOT / '.github/workflows/publish.yml').read_text()
    assert 'workflow_run:' in workflow
    assert 'Build Decktation Plugin' in workflow
    assert 'github.event.workflow_run.event == \'push\'' in workflow
    assert 'head_repository.full_name == github.repository' in workflow
    assert 'ref: master' in workflow
    assert 'actions/download-artifact@v8' in workflow
    assert 'name: decktation.zip' in workflow
    assert workflow.count('skip-decompress: true') == 2
    assert 'scripts/publish-pages.sh' in workflow
    assert 'verify-current-ref.sh' in workflow
    assert 'concurrency:' in workflow
    assert 'cancel-in-progress: false' in workflow


def test_release_tag_requires_trusted_master_ancestry():
    workflow = (ROOT / '.github/workflows/publish.yml').read_text()
    assert 'compare/${SOURCE_SHA}...master' in workflow
    assert 'status' in workflow
    # GitHub compare BASE...HEAD reports ahead when master contains the tag.
    assert '"$status" = \'ahead\'' in workflow and '"$status" = \'identical\'' in workflow


def test_same_name_branch_and_tag_are_rejected_as_ambiguous():
    workflow = (ROOT / '.github/workflows/publish.yml').read_text()
    assert 'ambiguous' in workflow.lower()
    assert workflow.lower().index('ambiguous') < workflow.index('compare/${SOURCE_SHA}...master')


def test_failed_branch_build_reconciles_approved_catalog():
    workflow = (ROOT / '.github/workflows/publish.yml').read_text()
    assert 'reconcile-pages:' in workflow
    assert "workflow_run.conclusion != 'success'" in workflow
    assert 'needs.reconcile-pages.result' in workflow
    build = (ROOT / '.github/workflows/build.yml').read_text()
    assert 'paths-ignore:' not in build.split('  pull_request:')[0]


def test_publisher_rechecks_branch_head_after_push():
    script = (ROOT / 'scripts/publish-pages.sh').read_text()
    publish = script.split('publish_pages() (', 1)[1].split('\nfor attempt in 1 2 3;', 1)[0]
    assert publish.count('scripts/verify-current-ref.sh') >= 2
    assert publish.index('git push origin gh-pages') < publish.rindex('scripts/verify-current-ref.sh')
    assert 'refresh_testing_catalog' in publish


def test_publisher_rejects_stale_or_deleted_branches(tmp_path):
    import subprocess
    script = ROOT / 'scripts/verify-current-ref.sh'
    # A local bare Git remote exercises the same refs/heads lookup as GitHub.
    remote = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
    source = tmp_path / 'source'
    source.mkdir()
    subprocess.run(['git', 'init', str(source)], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(source), 'config', 'user.email', 'test@example.invalid'], check=True)
    subprocess.run(['git', '-C', str(source), 'config', 'user.name', 'Test'], check=True)
    (source / 'marker').write_text('first')
    subprocess.run(['git', '-C', str(source), 'add', 'marker'], check=True)
    subprocess.run(['git', '-C', str(source), 'commit', '-m', 'first'], check=True, capture_output=True)
    sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    subprocess.run(['git', '-C', str(source), 'push', str(remote), 'HEAD:refs/heads/feat/candidate'],
                   check=True, capture_output=True)
    assert subprocess.run(['bash', str(script), str(remote), 'branch', 'feat/candidate', sha],
                          capture_output=True).returncode == 0
    assert subprocess.run(['bash', str(script), str(remote), 'branch', 'feat/candidate', 'b' * 40],
                          capture_output=True).returncode != 0
    subprocess.run(['git', '--git-dir', str(remote), 'update-ref', '-d', 'refs/heads/feat/candidate'],
                   check=True, capture_output=True)
    assert subprocess.run(['bash', str(script), str(remote), 'branch', 'feat/candidate', sha],
                          capture_output=True).returncode != 0
