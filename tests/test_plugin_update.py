import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import threading
import time
from unittest.mock import Mock
import zipfile

import pytest
import plugin_update as updater
from plugin_update import Version, PluginUpdater, UpdateError, parse_catalog, trusted_artifact, validate_zip

CURRENT = '0.3.18'
TARGET = '0.3.19'
URL = f'https://silverfoxy.github.io/decktation/releases/v{TARGET}/Decktation.zip'


def package(name='Decktation', version=TARGET, omit=(), extra=(), manifest=None):
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as archive:
        files = {'decktation/plugin.json': json.dumps({'name': name, 'version': version}) if manifest is None else manifest,
                 'decktation/main.py': 'import decky', 'decktation/dist/index.js': 'export default {}',
                 'decktation/bin/decktation_backend.py': '# backend',
                 'decktation/bin/python/numpy/plugin.json.example': 'legitimate extra file'}
        for path, value in files.items():
            if path not in omit:
                archive.writestr(path, value)
        for path, value in extra:
            archive.writestr(path, value)
    return result.getvalue()


def release(version=TARGET, data=None, **changes):
    result = {'name': version, 'hash': hashlib.sha256(data or package()).hexdigest(),
              'artifact': f'https://silverfoxy.github.io/decktation/releases/v{version}/Decktation.zip'}
    result.update(changes)
    return result


def catalog(*releases):
    return [{'name': 'Other', 'versions': [release('99.0.0')]}, {'name': 'Decktation', 'versions': list(releases)}]


class Response(io.BytesIO):
    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers or {}
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


def configured(monkeypatch, tmp_path, data=None, metadata=None, current=CURRENT):
    data = package() if data is None else data
    metadata = release(data=data) if metadata is None else metadata
    calls = []
    responses = []

    def network(url):
        calls.append(url)
        response = Response(json.dumps(catalog(metadata)).encode() if url == updater.CATALOG_URL else data)
        responses.append(response)
        return response

    monkeypatch.setattr(updater, 'open_url', network)
    return PluginUpdater(current, directory=tmp_path), calls, responses


@pytest.mark.parametrize('new,old', [
    ('0.3.19', '0.3.18'), ('0.3.10', '0.3.9'), ('1.0.0', '1.0.0-rc.1'),
    ('1.0.0-alpha.10', '1.0.0-alpha.2'), ('1.0.0-alpha.a', '1.0.0-alpha.9'),
    ('1.0.0-alpha.1', '1.0.0-alpha'), ('1.0.0-beta', '1.0.0-alpha'),
])
def test_semver_precedence(new, old):
    assert Version.parse(new) > Version.parse(old)


@pytest.mark.parametrize('value', ['', 'v1.0.0', '1.2', '01.2.3', '1.2.3-01', '1.2.3-',
                                         '1.2.3+', '1.2.3\n', None, 19, '١.2.3'])
def test_malformed_version(value):
    with pytest.raises(UpdateError):
        Version.parse(value)


def test_build_metadata_does_not_affect_precedence():
    assert Version.parse('1.2.3+one') == Version.parse('1.2.3+two') == Version.parse('1.2.3')


@pytest.mark.parametrize('current,available', [
    (CURRENT, True), (TARGET, False), ('0.3.20', False), ('0.3.20-dev.abcdef0', False),
    ('0.3.19-dev.abcdef0', True), ('0.3.19+abc', False),
])
def test_update_selection(monkeypatch, tmp_path, current, available):
    service, _, _ = configured(monkeypatch, tmp_path, current=current)
    assert service.check()['update_available'] is available


def test_catalog_selects_highest_stable(monkeypatch):
    data = catalog(release('0.3.9'), release('0.3.10'), release('0.3.21-dev.abcdef0'), release('0.3.19'))
    monkeypatch.setattr(updater, 'open_url', lambda _: Response(json.dumps(data).encode()))
    assert PluginUpdater('0.3.8').check()['version'] == TARGET
    assert set(parse_catalog(data)) == {'0.3.9', '0.3.10', TARGET}


@pytest.mark.parametrize('data', [None, {}, [], [{'name': 'Other', 'versions': []}],
    [{'name': 'Decktation', 'versions': {}}], [{'name': 'Decktation', 'versions': None}],
    [{'name': 'Decktation', 'versions': []}] * 2])
def test_invalid_catalog(data):
    with pytest.raises(UpdateError):
        parse_catalog(data)


@pytest.mark.parametrize('changes', [{'artifact': None}, {'artifact': ''}, {'hash': None}, {'hash': 'abc'},
    {'hash': 'g' * 64}, {'name': 'malformed'}, {'artifact': 'https://example.com/x.zip'}])
def test_invalid_candidate_not_installable(changes):
    assert parse_catalog(catalog(release(**changes))) == {}


def test_ambiguous_release_is_rejected():
    assert parse_catalog(catalog(release(), release(hash='b' * 64))) == {}


@pytest.mark.parametrize('url', [
    'http://silverfoxy.github.io/decktation/releases/v0.3.19/Decktation.zip',
    'https://example.com/decktation/releases/v0.3.19/Decktation.zip',
    'https://github.com/another-user/decktation/releases/download/v0.3.19/decktation.zip',
    'https://github.com/silverfoxy/decktation/archive/master.zip',
    URL + '?trusted=silverfoxy.github.io', URL + '#trusted', URL.replace('v0.3.19', 'v0.3.20'),
    URL.replace('silverfoxy.github.io', 'silverfoxy.github.io.evil.com'),
    URL.replace('silverfoxy.github.io', 'evil@silverfoxy.github.io'),
    URL.replace('silverfoxy.github.io', 'silverfoxy.github.io:443'),
    URL.replace('Decktation.zip', 'decktation.zip'), URL.replace('/v0.3.19/', '/latest/'),
    URL.replace('/Decktation.zip', '/%44ecktation.zip'), 'https://[bad', '//silverfoxy.github.io/test',
    'https://evil.com/?url=' + URL, URL + '\n', None,
])
def test_untrusted_urls(url):
    assert not trusted_artifact(url, TARGET)


def test_exact_pages_url_trusted():
    assert trusted_artifact(URL, TARGET)


def test_failure_is_not_no_update(monkeypatch, tmp_path):
    service, _, _ = configured(monkeypatch, tmp_path)
    monkeypatch.setattr(updater, 'open_url', Mock(side_effect=OSError('offline')))
    result = service.check()
    assert result['success'] is False and 'update_available' not in result
    assert result['error'] == 'Could not check for updates.'


def test_invalid_current_fails_before_network(monkeypatch):
    network = Mock()
    monkeypatch.setattr(updater, 'open_url', network)
    assert PluginUpdater('unknown').check()['success'] is False
    network.assert_not_called()


def test_cache_and_force_refresh(monkeypatch, tmp_path):
    service, calls, _ = configured(monkeypatch, tmp_path)
    service.check(); service.check()
    assert len(calls) == 1
    service.check(True)
    assert len(calls) == 2
    service._cached_at -= updater.CACHE_SECONDS
    service.check()
    assert len(calls) == 3


def test_streaming_stage(monkeypatch, tmp_path):
    data = package(extra=[('decktation/payload.bin', b'x' * 150000)])
    service, calls, responses = configured(monkeypatch, tmp_path, data)
    result = service.stage(TARGET)
    path = Path(result['artifact'].removeprefix('file://'))
    assert path.read_bytes() == data
    assert result['hash'] == hashlib.sha256(data).hexdigest()
    assert path.stat().st_mode & 0o777 == 0o600
    assert calls == [updater.CATALOG_URL, URL]
    assert responses[-1].read_sizes and set(responses[-1].read_sizes) == {65536}


@pytest.mark.parametrize('failure', ['hash', 'size', 'network', 'partial', 'corrupt', 'identity'])
def test_staging_failure_cleans_file(monkeypatch, tmp_path, failure):
    data = b'corrupt' if failure == 'corrupt' else package(name='Other' if failure == 'identity' else 'Decktation')
    metadata = release(data=data, hash='0' * 64) if failure == 'hash' else release(data=data)
    service, _, _ = configured(monkeypatch, tmp_path, data, metadata)
    service.releases()
    if failure == 'size':
        monkeypatch.setattr(updater, 'MAX_ARTIFACT_BYTES', 5)
    if failure == 'network':
        monkeypatch.setattr(updater, 'open_url', Mock(side_effect=OSError('offline')))
    if failure == 'partial':
        monkeypatch.setattr(updater, 'open_url', lambda _: Response(data, {'Content-Length': str(len(data) + 10)}))
    with pytest.raises((UpdateError, OSError, zipfile.BadZipFile)):
        service.stage(TARGET)
    assert list(tmp_path.iterdir()) == []


def test_partial_read_exception_cleanup(monkeypatch, tmp_path):
    service, _, _ = configured(monkeypatch, tmp_path)
    service.releases()
    response = Response(package())
    response.read = Mock(side_effect=[b'partial', OSError('connection lost')])
    monkeypatch.setattr(updater, 'open_url', lambda _: response)
    with pytest.raises(OSError):
        service.stage(TARGET)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('options', [
    {'name': 'Other'}, {'version': CURRENT}, {'omit': ['decktation/plugin.json']},
    {'omit': ['decktation/main.py']}, {'omit': ['decktation/dist/index.js']},
    {'extra': [('decktation/plugin.json', '{}')]}, {'extra': [('decktation/other/plugin.json', '{}')]},
    {'extra': [('../escape', 'bad')]}, {'extra': [('/decktation/absolute', 'bad')]},
    {'extra': [('decktation/../escape', 'bad')]}, {'extra': [('other/file', 'bad')]},
    {'extra': [('decktation\\escape', 'bad')]},
])
def test_zip_rejects_unsafe_packages(tmp_path, options):
    path = tmp_path / 'test.zip'
    path.write_bytes(package(**options))
    with pytest.raises((UpdateError, ValueError)):
        validate_zip(path, TARGET)


def test_valid_package(tmp_path):
    path = tmp_path / 'test.zip'; path.write_bytes(package())
    validate_zip(path, TARGET)


def test_symlink_zip_rejected(tmp_path):
    path = tmp_path / 'test.zip'; path.write_bytes(package())
    with zipfile.ZipFile(path, 'a') as archive:
        link = zipfile.ZipInfo('decktation/link')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, '/etc/passwd')
    with pytest.raises(UpdateError):
        validate_zip(path, TARGET)


def test_cleanup_only_old_regular_files(tmp_path):
    stale = tmp_path / 'decktation-update-old.zip'; stale.write_bytes(b'old')
    fresh = tmp_path / 'decktation-update-fresh.zip'; fresh.write_bytes(b'fresh')
    other = tmp_path / 'unrelated.zip'; other.write_bytes(b'other')
    link = tmp_path / 'decktation-update-link.zip'; link.symlink_to(other)
    old = time.time() - updater.STALE_SECONDS - 10
    os.utime(stale, (old, old))
    updater.cleanup_stale(tmp_path)
    assert not stale.exists() and fresh.exists() and other.exists() and link.is_symlink()


def test_stage_version_only_security_boundary(monkeypatch, tmp_path):
    service, _, _ = configured(monkeypatch, tmp_path)
    for version in ['0.3.17', CURRENT, '1.0.0', 'https://evil.com/arbitrary.zip']:
        with pytest.raises(UpdateError):
            service.stage(version)
    with pytest.raises(TypeError):
        service.stage(TARGET, URL, 'a' * 64)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('state,reason', [('recording', 'dictation'), ('transcribing', 'dictation'),
    ('loading', 'model'), ('changing', 'model'), ('draft', 'dictation'), ('sending', 'dictation'), ('idle', None)])
def test_runtime_authoritative(monkeypatch, state, reason):
    from decktation_backend import Plugin
    service = Mock(is_recording=state == 'recording', is_transcribing=state == 'transcribing',
                   model_loading=state == 'loading', pending_text='text' if state == 'draft' else None)
    service.pending_snapshot.return_value = {'sending': state == 'sending'} if state in ('draft', 'sending') else None
    monkeypatch.setattr(Plugin, 'voice_service', service)
    monkeypatch.setattr(Plugin, 'model_operations', int(state == 'changing'))
    monkeypatch.setattr(Plugin, 'update_preparing', False)
    stage = Mock(return_value={'success': True, 'artifact': 'file:///tmp/decktation-update-test.zip'})
    monkeypatch.setattr(Plugin, 'updater', Mock(stage=stage))
    result = asyncio.run(Plugin().prepare_plugin_update(TARGET))
    if reason:
        assert not result['success'] and reason in result['error']
        stage.assert_not_called()
    else:
        assert result['success']; stage.assert_called_once_with(TARGET)


def test_busy_after_download_removes_staged_file(monkeypatch, tmp_path):
    from decktation_backend import Plugin
    service = Mock(is_recording=False, is_transcribing=False, model_loading=False, pending_text=None)
    service.pending_snapshot.return_value = None
    monkeypatch.setattr(Plugin, 'voice_service', service)
    monkeypatch.setattr(Plugin, 'model_operations', 0)
    monkeypatch.setattr(Plugin, 'update_preparing', False)
    path = tmp_path / 'decktation-update-test.zip'; path.write_bytes(b'zip')
    def stage(_):
        service.is_recording = True
        return {'success': True, 'artifact': path.as_uri()}
    monkeypatch.setattr(Plugin, 'updater', Mock(stage=stage))
    assert not asyncio.run(Plugin().prepare_plugin_update(TARGET))['success']
    assert not path.exists()


def test_network_worker_keeps_event_loop_responsive(monkeypatch):
    from decktation_backend import Plugin
    started, release_worker = threading.Event(), threading.Event()
    def check(_):
        started.set(); release_worker.wait(2)
        return {'success': True, 'update_available': False}
    monkeypatch.setattr(Plugin, 'updater', Mock(check=check))
    async def run():
        task = asyncio.create_task(Plugin().get_plugin_update())
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(.001)
        assert started.is_set() and not task.done()
        release_worker.set()
        assert (await task)['success']
    asyncio.run(run())

@pytest.mark.parametrize('extra', [[('decktation', 'file')], [('decktation/bin', 'file')],
    [('decktation//file', 'file')], [('decktation/./file', 'file')]])
def test_archive_directory_conflicts_and_paths(tmp_path, extra):
    path = tmp_path / 'test.zip'; path.write_bytes(package(extra=extra))
    with pytest.raises(UpdateError):
        validate_zip(path, TARGET)


def test_bad_crc_is_rejected(tmp_path):
    data = package(extra=[('decktation/data.bin', b'UNIQUE_PAYLOAD')])
    path = tmp_path / 'test.zip'; path.write_bytes(data.replace(b'UNIQUE_PAYLOAD', b'BROKEN_PAYLOAD'))
    with pytest.raises((UpdateError, zipfile.BadZipFile)):
        validate_zip(path, TARGET)


def test_redirect_fails_closed():
    with pytest.raises(UpdateError):
        updater.NoRedirects().redirect_request(None, None, 302, 'redirect', {}, 'http://evil.com')


def test_advertised_oversize_aborts_before_read(monkeypatch, tmp_path):
    service, _, _ = configured(monkeypatch, tmp_path)
    service.releases()
    response = Response(package(), {'Content-Length': str(updater.MAX_ARTIFACT_BYTES + 1)})
    monkeypatch.setattr(updater, 'open_url', lambda _: response)
    with pytest.raises(UpdateError):
        service.stage(TARGET)
    assert not response.read_sizes and not list(tmp_path.iterdir())


def test_time_limit_cleans_up(monkeypatch, tmp_path):
    service, _, _ = configured(monkeypatch, tmp_path)
    service.releases()
    monkeypatch.setattr(updater, 'DOWNLOAD_SECONDS', -1)
    with pytest.raises(UpdateError):
        service.stage(TARGET)
    assert not list(tmp_path.iterdir())


def test_catalog_limit_is_failure(monkeypatch):
    monkeypatch.setattr(updater, 'MAX_CATALOG_BYTES', 10)
    monkeypatch.setattr(updater, 'open_url', lambda _: Response(b'x' * 11))
    result = PluginUpdater(CURRENT).check()
    assert not result['success'] and 'update_available' not in result


def test_runtime_rejects_parallel_preparation_and_arbitrary_rpc_arguments(monkeypatch):
    from decktation_backend import Plugin
    monkeypatch.setattr(Plugin, 'voice_service', None)
    monkeypatch.setattr(Plugin, 'model_operations', 0)
    monkeypatch.setattr(Plugin, 'update_preparing', True)
    stage = Mock()
    monkeypatch.setattr(Plugin, 'updater', Mock(stage=stage))
    assert not asyncio.run(Plugin().prepare_plugin_update(TARGET))['success']
    stage.assert_not_called()
    with pytest.raises(TypeError):
        Plugin().prepare_plugin_update(TARGET, URL, 'a' * 64)


@pytest.mark.parametrize('fails', [False, True])
def test_transcription_state_covers_test_path_and_clears(monkeypatch, tmp_path, fails):
    from wow_voice_chat import WoWVoiceChat
    service = WoWVoiceChat.__new__(WoWVoiceChat)
    service.recording_lock = threading.Lock()
    service._pending_lock = threading.RLock()
    service._draft_generation = 0
    service.is_recording = True
    service.is_transcribing = False
    service.test_mode = True
    audio = tmp_path / 'audio.wav'; audio.write_bytes(b'audio')
    service.test_audio_file = str(audio)
    service._recording_transition = Mock()
    service._report_diagnostic = Mock()
    def transcribe(_):
        assert service.is_transcribing and not service.is_recording
        if fails:
            raise ValueError('test error')
        return 'test result'
    service.transcribe_audio = transcribe
    service.stop_recording(send=False)
    assert not service.is_transcribing and not service.is_recording


def test_transcription_state_clears_when_stream_close_raises():
    from wow_voice_chat import WoWVoiceChat
    service = WoWVoiceChat.__new__(WoWVoiceChat)
    service.recording_lock = threading.Lock(); service._pending_lock = threading.RLock()
    service._draft_generation = 0
    service.is_recording = True; service.is_transcribing = False; service.test_mode = False
    service.recording_stream = Mock()
    service.recording_stream.stop.side_effect = RuntimeError('audio error')
    with pytest.raises(RuntimeError):
        service.stop_recording(False)
    assert not service.is_transcribing


def test_exact_github_release_asset_trusted(monkeypatch):
    url = 'https://github.com/silverfoxy/decktation/releases/download/v0.3.19/decktation.zip'
    assert trusted_artifact(url, TARGET)
    assert not trusted_artifact(url.replace('v0.3.19', 'v0.3.18'), TARGET)
    assert not trusted_artifact(url.replace('decktation.zip', 'Decktation.zip'), TARGET)
    data = catalog(release(artifact=url))
    monkeypatch.setattr(updater, 'open_url', lambda _: Response(json.dumps(data).encode()))
    assert PluginUpdater(CURRENT).check()['version'] == TARGET


def test_redirect_only_from_original_github_asset_to_release_cdn():
    from urllib.request import Request
    source = 'https://github.com/silverfoxy/decktation/releases/download/v0.3.19/decktation.zip'
    cdn = 'https://release-assets.githubusercontent.com/github-production-release-asset/123/id?signature=example'
    handler = updater.ArtifactRedirects(source)
    result = handler.redirect_request(Request(source), None, 302, 'redirect', {}, cdn)
    assert result.full_url == cdn
    for request_url, destination in [(source, 'http://release-assets.githubusercontent.com/test'),
        (source, 'https://evil.com/test'), (source, cdn.replace('githubusercontent.com', 'githubusercontent.com.evil.com')),
        (source, cdn.replace('release-assets.', 'user@release-assets.')), (cdn, cdn),
        (updater.CATALOG_URL, cdn), (source, cdn.replace('/github-production-release-asset/', '/arbitrary/'))]:
        with pytest.raises(UpdateError):
            handler.redirect_request(Request(request_url), None, 302, 'redirect', {}, destination)
    with pytest.raises(UpdateError):
        updater.ArtifactRedirects(URL).redirect_request(Request(URL), None, 302, 'redirect', {}, cdn)
    assert not trusted_artifact(cdn, TARGET)


@pytest.mark.parametrize('manifest', ['not JSON', 'null', '[]', '{}', '{"name": "Decktation"}',
    '{"name": "Decktation", "version": 19}'])
def test_malformed_manifest_rejected(tmp_path, manifest):
    path = tmp_path / 'test.zip'; path.write_bytes(package(manifest=manifest))
    with pytest.raises((UpdateError, ValueError)):
        validate_zip(path, TARGET)


def test_unpacked_size_limit(tmp_path, monkeypatch):
    path = tmp_path / 'test.zip'; path.write_bytes(package())
    monkeypatch.setattr(updater, 'MAX_UNPACKED_BYTES', 10)
    with pytest.raises(UpdateError):
        validate_zip(path, TARGET)


def test_failed_force_refresh_does_not_report_cached_no_update(monkeypatch, tmp_path):
    service, _, _ = configured(monkeypatch, tmp_path, current=TARGET)
    assert service.check()['update_available'] is False
    monkeypatch.setattr(updater, 'open_url', Mock(side_effect=OSError('offline')))
    result = service.check(True)
    assert not result['success'] and 'update_available' not in result


def test_unexpected_busy_state_error_fails_closed(monkeypatch):
    from decktation_backend import Plugin
    service = Mock(is_recording=False, is_transcribing=False, model_loading=False, pending_text=None)
    service.pending_snapshot.side_effect = RuntimeError('status unavailable')
    monkeypatch.setattr(Plugin, 'voice_service', service)
    monkeypatch.setattr(Plugin, 'model_operations', 0)
    monkeypatch.setattr(Plugin, 'update_preparing', False)
    stage = Mock()
    monkeypatch.setattr(Plugin, 'updater', Mock(stage=stage))
    result = asyncio.run(Plugin().prepare_plugin_update(TARGET))
    assert not result['success'] and 'status unavailable' not in result['error']
    stage.assert_not_called()
    assert not Plugin.update_preparing


@pytest.mark.parametrize('encoding', ['utf-16', 'utf-8-sig'])
def test_manifest_must_be_readable_by_deckys_utf8_json_loader(tmp_path, encoding):
    manifest = json.dumps({'name': 'Decktation', 'version': TARGET}).encode(encoding)
    path = tmp_path / 'test.zip'; path.write_bytes(package(manifest=manifest))
    with pytest.raises(ValueError):
        validate_zip(path, TARGET)


def test_https_uses_bundled_ca_and_keeps_certificate_validation(monkeypatch):
    import ssl
    captured = []
    context = ssl.create_default_context(cafile=updater.certifi.where())
    factory = Mock(return_value=context)
    opener = Mock()
    monkeypatch.setattr(updater.ssl, 'create_default_context', factory)
    monkeypatch.setattr(updater, 'build_opener', lambda *handlers: captured.extend(handlers) or opener)
    updater.open_url(updater.CATALOG_URL)
    factory.assert_called_once_with(cafile=updater.certifi.where())
    https = next(h for h in captured if isinstance(h, updater.HTTPSHandler))
    assert https._context is context
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    opener.open.assert_called_once()
