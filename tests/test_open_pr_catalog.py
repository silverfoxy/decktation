"""The opt-in testing store lists current open PR builds without approvals."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('open_pr_catalog', ROOT / 'scripts/generate-pr-catalog.py')


def load():
    module = importlib.util.module_from_spec(SPEC)
    sys.modules[SPEC.name] = module
    SPEC.loader.exec_module(module)
    return module


def package(pages, number, run_id, sha, version=None, attempt=1):
    folder = pages / 'pulls' / str(number) / str(run_id) / str(attempt)
    folder.mkdir(parents=True)
    version = version or f'0.3.20-dev.pr-{number}.{sha[:7]}'
    with zipfile.ZipFile(folder / 'Decktation.zip', 'w') as z:
        z.writestr('decktation/plugin.json', json.dumps({'name': 'Decktation', 'version': version}))
    digest = hashlib.sha256((folder / 'Decktation.zip').read_bytes()).hexdigest()
    (folder / 'metadata.json').write_text(json.dumps({
        'channel': 'pull_request', 'number': number, 'run_id': run_id,
        'run_attempt': attempt, 'commit': sha, 'head_repository': 'contributor/decktation',
        'zip_url': f'https://decktation.com/pulls/{number}/{run_id}/{attempt}/Decktation.zip',
        'sha256': digest,
    }))
    return folder


def pr(number, sha, state='open', repo='contributor/decktation'):
    return {'number': number, 'state': state, 'head': {
        'sha': sha, 'repo': {'full_name': repo}}}


def catalog(root, pull_requests, heads=None):
    return load().build_catalog(root, ROOT / 'plugin.json', 'https://decktation.com',
                                pull_requests, heads or {})


def test_lists_open_fork_pr_without_approval_using_immutable_run_url(tmp_path):
    sha = 'a' * 40
    package(tmp_path, 81, 123, sha)
    result = catalog(tmp_path, [pr(81, sha)])
    versions = result[0]['versions']
    assert len(versions) == 1
    assert versions[0]['name'] == '0.3.20-dev.pr-81.aaaaaaa'
    assert versions[0]['artifact'] == 'https://decktation.com/pulls/81/123/1/Decktation.zip'
    assert 'PR #81' in result[0]['description']
    assert versions[0]['hash'] == hashlib.sha256((tmp_path / 'pulls/81/123/1/Decktation.zip').read_bytes()).hexdigest()


def test_changed_head_closed_pr_and_forged_repo_are_not_listed(tmp_path):
    sha = 'a' * 40
    package(tmp_path, 81, 123, sha)
    assert catalog(tmp_path, [pr(81, 'b' * 40)])[0]['versions'] == []
    assert catalog(tmp_path, [pr(81, sha, state='closed')])[0]['versions'] == []
    assert catalog(tmp_path, [pr(81, sha, repo='other/decktation')])[0]['versions'] == []


def test_tampered_package_and_metadata_are_omitted(tmp_path):
    sha = 'a' * 40
    folder = package(tmp_path, 81, 123, sha)
    with zipfile.ZipFile(folder / 'Decktation.zip', 'a') as z:
        z.writestr('decktation/evil.py', 'pass')
    assert catalog(tmp_path, [pr(81, sha)])[0]['versions'] == []


def test_newest_valid_run_for_current_head_is_selected(tmp_path):
    sha = 'a' * 40
    package(tmp_path, 81, 123, sha)
    package(tmp_path, 81, 124, sha)
    versions = catalog(tmp_path, [pr(81, sha)])[0]['versions']
    assert len(versions) == 1
    assert '/pulls/81/124/1/' in versions[0]['artifact']


def test_master_preselected_before_any_pr(tmp_path):
    sha = 'a' * 40
    package(tmp_path, 81, 123, sha)
    master = tmp_path / 'branches/master'
    master.mkdir(parents=True)
    with zipfile.ZipFile(master / 'Decktation.zip', 'w') as z:
        z.writestr('decktation/plugin.json', json.dumps({'name': 'Decktation', 'version': '0.3.20-dev.bbbbbbb'}))
    (master / 'metadata.json').write_text(json.dumps({
        'channel': 'branch', 'ref': 'master', 'commit': 'b' * 40,
        'zip_url': 'https://decktation.com/branches/master/Decktation.zip'}))
    result = catalog(tmp_path, [pr(81, sha)], {'master': 'b' * 40})
    assert [v['name'] for v in result[0]['versions']] == ['0.3.20-dev.bbbbbbb', '0.3.20-dev.pr-81.aaaaaaa']


def test_closed_pr_artifacts_are_pruned_but_open_prs_remain(tmp_path):
    sha = 'a' * 40
    old = package(tmp_path, 80, 123, sha)
    current = package(tmp_path, 81, 124, sha)
    load().prune_closed_prs(tmp_path, [pr(81, sha)])
    assert not old.exists()
    assert current.exists()


def test_workflow_has_separate_read_only_pr_build_and_trusted_publisher():
    build = (ROOT / '.github/workflows/build.yml').read_text()
    publish = (ROOT / '.github/workflows/publish.yml').read_text()
    assert 'contents: write' not in build
    assert "github.event.workflow_run.event == 'pull_request'" in publish
    assert 'head_repository.full_name == github.repository' not in publish.split('  publish-pr:', 1)[1].split('  reconcile-pages:', 1)[0]
    assert 'actions/download-artifact@v8' in publish
    assert 'ref: master' in publish
    assert 'pull_request_target:' in publish or 'schedule:' in publish
