import copy
import importlib.util
import io
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    'record_pr_artifact', Path(__file__).parents[1] / 'scripts/record-pr-artifact.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def artifact():
    return {'id': 987, 'name': 'decktation.zip', 'expired': False,
            'digest': 'sha256:' + 'b' * 64, 'size_in_bytes': 100,
            'expires_at': '2099-01-01T00:00:00Z',
            'workflow_run': {'id': 123, 'head_sha': 'a' * 40}}


def resolve(monkeypatch, items):
    def response(request, timeout):
        assert request.full_url.startswith('https://api.github.com/repos/silverfoxy/decktation/actions/runs/123/artifacts?')
        assert request.headers['Authorization'] == 'Bearer test-token'
        return io.BytesIO(json.dumps({'artifacts': items}).encode())
    monkeypatch.setattr(MODULE, 'urlopen', response)
    return MODULE.artifact_metadata('silverfoxy/decktation', 123, 'a' * 40, 'b' * 64, 100, 'test-token')


def test_raw_artifact_matches_run_sha_digest_size_and_expiration(monkeypatch):
    assert resolve(monkeypatch, [artifact()])['id'] == 987


@pytest.mark.parametrize('changes', [
    {'expired': True}, {'expires_at': '2000-01-01T00:00:00Z'},
    {'digest': 'sha256:wrong'}, {'size_in_bytes': 101}, {'name': 'other.zip'},
    {'workflow_run': {'id': 124, 'head_sha': 'a' * 40}},
    {'workflow_run': {'id': 123, 'head_sha': 'c' * 40}},
])
def test_wrong_or_expired_artifact_is_rejected(monkeypatch, changes):
    item = artifact()
    item.update(copy.deepcopy(changes))
    with pytest.raises(ValueError):
        resolve(monkeypatch, [item])


def test_ambiguous_artifacts_are_rejected(monkeypatch):
    with pytest.raises(ValueError, match='Expected one'):
        resolve(monkeypatch, [artifact(), artifact()])
