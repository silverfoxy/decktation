import base64
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('discord_release', ROOT / 'scripts/announce-discord-release.py')
discord = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discord)
REPO = 'silverfoxy/decktation'
TAG = 'v0.3.22'
WEBHOOK = 'https://discord.com/api/webhooks/123456/secret-token'
NOTES = '## [Unreleased]\nFuture work\n## [0.3.22] - 2026-11-08\n### Added\n- New feature\n## [0.3.21]\nOlder notes\n'


@pytest.fixture
def release(monkeypatch):
    value = {'id': 42, 'tag_name': TAG, 'body': 'Existing release body', 'draft': False,
             'prerelease': False, 'html_url': f'https://github.com/{REPO}/releases/tag/{TAG}',
             'assets': [{'name': 'Decktation.zip', 'state': 'uploaded', 'size': 1024,
                         'browser_download_url': f'https://github.com/{REPO}/releases/download/{TAG}/Decktation.zip'}]}
    patches = []

    def api(method, path, data=None):
        if method == 'PATCH':
            patches.append(data)
            value.update(data)
            return value
        if '/contents/' in path:
            assert path.endswith('?ref=' + TAG)
            return {'content': base64.b64encode(NOTES.encode()).decode()}
        return value

    monkeypatch.setattr(discord, 'github', Mock(side_effect=api))
    monkeypatch.setenv('DISCORD_RELEASE_WEBHOOK_URL', WEBHOOK)
    monkeypatch.setattr(discord, 'send', Mock(return_value='123456789'))
    return value, patches


def test_announcement_uses_tagged_notes_and_uploaded_archive_and_deduplicates(release):
    value, patches = release
    assert discord.announce(REPO, TAG) == '123456789'
    message = discord.send.call_args.args[1]
    assert 'New feature' in message['embeds'][0]['description']
    assert 'Future work' not in message['embeds'][0]['description']
    assert 'Older notes' not in message['embeds'][0]['description']
    assert value['assets'][0]['browser_download_url'] in message['embeds'][0]['fields'][0]['value']
    assert message['allowed_mentions'] == {'parse': []}
    assert patches[0]['body'].startswith('Existing release body')
    assert '<!-- decktation-discord-message:123456789 -->' in patches[0]['body']
    discord.announce(REPO, TAG)
    assert discord.send.call_count == 1


def test_publisher_rerun_restores_marker_without_posting_again(release):
    _, patches = release
    discord.announce(REPO, TAG, previous_id='987654321')
    discord.send.assert_not_called()
    assert patches[0]['body'].endswith('<!-- decktation-discord-message:987654321 -->')


@pytest.mark.parametrize('field', ['draft', 'prerelease'])
def test_unpublished_release_types_are_rejected(release, field):
    release[0][field] = True
    with pytest.raises(discord.AnnouncementError):
        discord.announce(REPO, TAG)
    discord.send.assert_not_called()


def test_release_without_installable_archive_cannot_be_announced(release):
    release[0]['assets'] = []
    with pytest.raises(discord.AnnouncementError):
        discord.announce(REPO, TAG)
    discord.send.assert_not_called()


def test_unconfigured_secret_skips_delivery_without_changing_release(release, monkeypatch):
    monkeypatch.delenv('DISCORD_RELEASE_WEBHOOK_URL')
    assert discord.announce(REPO, TAG) is None
    discord.send.assert_not_called()
    assert release[1] == []


def test_stable_tag_and_changelog_version_are_required(release):
    with pytest.raises(discord.AnnouncementError):
        discord.announce(REPO, 'v0.3.23-dev')
    with pytest.raises(discord.AnnouncementError):
        discord.release_notes(NOTES, 'v0.3.23')
    discord.send.assert_not_called()


def test_discord_payload_fits_embed_limit_with_unicode():
    message = discord.payload(TAG, '🎮' * 10000, 'https://example.com/release', 'https://example.com/download')
    description = message['embeds'][0]['description']
    assert len(description.encode('utf-16-le')) // 2 <= 4096
    assert description.endswith(f'/changelog/{TAG[1:]}/)')


def test_webhook_delivery_waits_for_a_saved_message(monkeypatch):
    send = discord.send
    requests = []

    def respond(request, **kwargs):
        requests.append(request)
        return io.StringIO('{"id":"123456789"}')

    monkeypatch.setattr(discord, 'urlopen', respond)
    assert send(WEBHOOK + '?thread_id=456', {'allowed_mentions': {'parse': []}}) == '123456789'
    assert 'wait=true' in requests[0].full_url
    assert 'thread_id=456' in requests[0].full_url
    assert requests[0].method == 'POST'
    assert json.loads(requests[0].data)['allowed_mentions'] == {'parse': []}
    with pytest.raises(discord.AnnouncementError):
        send('https://example.com/webhook', {})


@pytest.mark.parametrize('error', [HTTPError(WEBHOOK, 401, 'invalid', None, None), URLError(WEBHOOK)])
def test_failures_do_not_print_webhook_secrets(monkeypatch, capsys, error):
    monkeypatch.setenv('GITHUB_REPOSITORY', REPO)
    monkeypatch.setenv('RELEASE_TAG', TAG)
    monkeypatch.setattr(discord.sys, 'argv', ['announce-discord-release.py'])
    monkeypatch.setattr(discord, 'github', Mock(side_effect=error))
    assert discord.main() == 1
    output = capsys.readouterr()
    assert 'secret-token' not in output.err + output.out


def test_capture_handles_new_and_existing_releases(monkeypatch):
    monkeypatch.setattr(discord, 'github', Mock(return_value={'body': '<!-- decktation-discord-message:123 -->'}))
    assert discord.capture(REPO, TAG) == '123'
    discord.github.side_effect = HTTPError('https://api.github.com/release', 404, '', None, None)
    assert discord.capture(REPO, TAG) == ''


def test_publisher_announces_only_after_release_upload_and_preserves_marker():
    workflow = (ROOT / '.github/workflows/publish.yml').read_text()
    capture = workflow.index('id: discord-state')
    upload = workflow.index('name: Upload release archive')
    announce = workflow.index('name: Announce the published release on Discord')
    assert capture < upload < announce < workflow.index('  publish-pr:')
    step = workflow[announce:workflow.index('  publish-pr:')]
    assert "steps.source-ref.outputs.current == 'true'" in step
    assert "steps.source-ref.outputs.ref_type == 'tag'" in step
    assert 'secrets.DISCORD_RELEASE_WEBHOOK_URL' in step
    assert 'steps.discord-state.outputs.message_id' in step
