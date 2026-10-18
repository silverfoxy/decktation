"""Verify the optional master build in the PR test catalog."""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

SHA_RE = re.compile(r'[0-9a-f]{40}\Z')
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('store_catalog', HERE / 'generate-store-catalog.py')
STORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STORE)


def verified_version(root, ref, commit, base_url):
    if ref != 'master' or not SHA_RE.fullmatch(commit):
        return None
    folder = Path(root) / 'branches/master'
    artifact = folder / 'Decktation.zip'
    metadata = folder / 'metadata.json'
    url = f'{base_url}/branches/master/Decktation.zip'
    if (not artifact.is_file() or not metadata.is_file() or artifact.is_symlink() or
            metadata.is_symlink() or folder.is_symlink()):
        return None
    try:
        data = json.loads(metadata.read_text(encoding='utf-8'))
        if (data.get('channel') != 'branch' or data.get('ref') != 'master' or
                data.get('commit') != commit or data.get('zip_url') != url):
            return None
        with zipfile.ZipFile(artifact) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if (len(members) > 10000 or len(names) != len(set(names)) or
                    sum(member.file_size for member in members) > 600 * 1024 * 1024 or
                    any(member.filename.startswith('/') or '..' in PurePosixPath(member.filename).parts or
                        member.file_size > 600 * 1024 * 1024 or
                        (member.external_attr >> 16) & 0o170000 == 0o120000 for member in members) or
                    archive.testzip() is not None):
                return None
            manifest = archive.getinfo('decktation/plugin.json')
            if manifest.file_size > 32768:
                return None
            plugin = json.loads(archive.read(manifest))
            version = plugin.get('version')
            if (plugin.get('name') != 'Decktation' or not isinstance(version, str) or
                    not STORE.SEMVER_RE.fullmatch(version) or
                    not version.endswith('.' + commit[:7])):
                return None
        with artifact.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        return {'name': version, 'hash': digest, 'artifact': url}
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError):
        return None


def read_current_refs(path):
    refs = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        sha, ref = line.split('\t')
        if not SHA_RE.fullmatch(sha) or not ref.startswith('refs/heads/'):
            raise ValueError('Invalid remote branch listing')
        refs[ref.removeprefix('refs/heads/')] = sha
    return refs
