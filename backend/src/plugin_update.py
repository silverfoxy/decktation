"""Stable update discovery and validation. Never modifies the installed plugin."""
from dataclasses import dataclass
from functools import total_ordering
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import stat
import ssl

import certifi
import tempfile
import threading
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, HTTPSHandler, Request
import zipfile

CATALOG_URL = "https://silverfoxy.github.io/decktation/store/plugins.json"
PLUGIN_NAME = "Decktation"
CACHE_SECONDS = 60 * 60
NETWORK_TIMEOUT = 30
DOWNLOAD_SECONDS = 10 * 60
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_CATALOG_BYTES = 2 * 1024 * 1024
MAX_UNPACKED_BYTES = 2 * 1024 * 1024 * 1024
TEMP_PREFIX = "decktation-update-"
STALE_SECONDS = 24 * 60 * 60
logger = logging.getLogger("decktation.updater")
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?")


class UpdateError(ValueError):
    """Detailed log-only failure; RPCs return fixed user-facing messages."""


@total_ordering
@dataclass(frozen=True, eq=False)
class Version:
    core: tuple
    prerelease: tuple = ()

    @classmethod
    def parse(cls, value):
        match = SEMVER.fullmatch(value) if isinstance(value, str) else None
        if not match:
            raise UpdateError("Invalid SemVer")
        pre = tuple(match.group(4).split(".")) if match.group(4) else ()
        if any(p.isdigit() and len(p) > 1 and p[0] == "0" for p in pre):
            raise UpdateError("Invalid numeric prerelease")
        return cls(tuple(int(p) for p in match.groups()[:3]), pre)

    def __eq__(self, other):
        return isinstance(other, Version) and (self.core, self.prerelease) == (other.core, other.prerelease)

    def __lt__(self, other):
        if self.core != other.core:
            return self.core < other.core
        if not self.prerelease or not other.prerelease:
            return bool(self.prerelease) and not other.prerelease
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            if left.isdigit() and right.isdigit():
                return int(left) < int(right)
            if left.isdigit() != right.isdigit():
                return left.isdigit()
            return left < right
        return len(self.prerelease) < len(other.prerelease)


def trusted_artifact(url, version):
    """Only exact version-matching project release artifacts are installable."""
    if not isinstance(url, str) or any(ord(c) < 33 for c in url):
        return False
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.port is not None or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            return False
        return ((parsed.netloc == "silverfoxy.github.io" and parsed.path ==
                 f"/decktation/releases/v{version}/Decktation.zip")
                or (parsed.netloc == "github.com" and parsed.path ==
                    f"/silverfoxy/decktation/releases/download/v{version}/decktation.zip"))
    except ValueError:
        return False


def parse_catalog(data):
    if not isinstance(data, list):
        raise UpdateError("Catalog must be a list")
    entries = [p for p in data if isinstance(p, dict) and p.get("name") == PLUGIN_NAME]
    if len(entries) != 1 or not isinstance(entries[0].get("versions"), list):
        raise UpdateError("Missing or ambiguous Decktation catalog entry")
    releases = {}
    ambiguous = set()
    for entry in entries[0]["versions"]:
        if not isinstance(entry, dict):
            continue
        try:
            version = entry.get("name")
            parsed = Version.parse(version)
            digest = entry.get("hash")
            artifact = entry.get("artifact")
            if (parsed.prerelease or not isinstance(digest, str)
                    or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)
                    or not trusted_artifact(artifact, version)):
                continue
            candidate = {"version": version, "hash": digest.lower(), "artifact": artifact}
            if version in releases and releases[version] != candidate:
                ambiguous.add(version)
            releases[version] = candidate
        except (UpdateError, ValueError):
            continue
    return {v: r for v, r in releases.items() if v not in ambiguous}


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise UpdateError("Update endpoint redirected unexpectedly")


class ArtifactRedirects(NoRedirects):
    """GitHub release assets redirect once to their dedicated HTTPS CDN."""
    def __init__(self, source):
        self.source = source

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        source = urlsplit(self.source)
        match = re.fullmatch(r"/silverfoxy/decktation/releases/download/v([^/]+)/decktation\.zip", source.path)
        target = urlsplit(newurl)
        # Only the validated original GitHub asset can introduce a CDN URL.
        # CDN URLs themselves are never accepted from catalog metadata.
        if (req.full_url == self.source and source.netloc == "github.com" and match
                and trusted_artifact(self.source, match.group(1))
                and target.scheme == "https" and target.netloc == "release-assets.githubusercontent.com"
                and not target.fragment and not target.username and not target.password
                and target.path.startswith("/github-production-release-asset/")
                and not any(ord(c) < 33 for c in newurl)):
            return HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url):
    return build_opener(ArtifactRedirects(url), HTTPSHandler(
        context=ssl.create_default_context(cafile=certifi.where()))).open(
        Request(url, headers={"User-Agent": "Decktation-updater", "Accept-Encoding": "identity"}),
        timeout=NETWORK_TIMEOUT,
    )


def cleanup_stale(directory="/tmp"):
    for path in Path(directory).glob(f"{TEMP_PREFIX}*.zip"):
        try:
            info = path.lstat()
            if (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and time.time() - info.st_mtime > STALE_SECONDS):
                path.unlink()
        except OSError:
            pass


def validate_zip(path, version):
    required = {"decktation/plugin.json", "decktation/main.py", "decktation/dist/index.js",
                "decktation/bin/decktation_backend.py"}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if not entries or len(entries) > 50000 or len(names) != len(set(names)):
            raise UpdateError("Empty or ambiguous ZIP")
        total = 0
        files = {entry.filename for entry in entries if not entry.is_dir()}
        for entry in entries:
            name = entry.filename
            parts = name.rstrip("/").split("/")
            if (entry.orig_filename != name or "\\" in name or parts[0] != "decktation"
                    or any(part in ("", ".", "..") for part in parts)
                    or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1):
                raise UpdateError("Unsafe ZIP entry")
            mode = stat.S_IFMT(entry.external_attr >> 16)
            if (len(parts) == 1 and not entry.is_dir()) or mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise UpdateError("Invalid ZIP file type")
            if any("/".join(parts[:i]) in files for i in range(1, len(parts))):
                raise UpdateError("ZIP file conflicts with package directory")
            total += entry.file_size
            if total > MAX_UNPACKED_BYTES:
                raise UpdateError("ZIP expands beyond size limit")
        manifests = [name for name in names if name.rstrip("/").split("/")[-1] == "plugin.json"]
        if manifests != ["decktation/plugin.json"] or not required.issubset(names):
            raise UpdateError("Missing or ambiguous plugin structure")
        if any(archive.getinfo(name).is_dir() or archive.getinfo(name).file_size == 0 for name in required):
            raise UpdateError("Empty required plugin file")
        if archive.getinfo("decktation/plugin.json").file_size > 64 * 1024:
            raise UpdateError("Manifest too large")
        manifest = json.loads(archive.read("decktation/plugin.json").decode("utf-8"))
        if (not isinstance(manifest, dict) or manifest.get("name") != PLUGIN_NAME
                or manifest.get("version") != version):
            raise UpdateError("Plugin identity/version mismatch")
        if archive.testzip() is not None:
            raise UpdateError("ZIP integrity check failed")
    logger.info("updater: ZIP/manifest validated")


class PluginUpdater:
    def __init__(self, current, log=None, directory="/tmp"):
        self.current = current
        self.log = log or logger
        self.directory = directory
        self._cached = None
        self._cached_at = 0
        self._lock = threading.Lock()

    def releases(self, force=False):
        with self._lock:
            if not force and self._cached is not None and time.monotonic() - self._cached_at < CACHE_SECONDS:
                return self._cached
            self.log.info("updater: checking catalog")
            with open_url(CATALOG_URL) as response:
                raw = response.read(MAX_CATALOG_BYTES + 1)
            if len(raw) > MAX_CATALOG_BYTES:
                raise UpdateError("Catalog too large")
            releases = parse_catalog(json.loads(raw))
            self._cached, self._cached_at = releases, time.monotonic()
            return releases

    def check(self, force=False):
        try:
            current = Version.parse(self.current)
            releases = self.releases(force)
            latest = max(releases.values(), key=lambda r: Version.parse(r["version"]), default=None)
            if latest:
                self.log.info("updater: latest stable %s", latest["version"])
            result = {"success": True, "current": self.current, "update_available": False}
            if latest and Version.parse(latest["version"]) > current:
                result.update(latest, update_available=True)
            else:
                self.log.info("updater: no update available")
            return result
        except Exception as error:
            self.log.warning("updater: check failed: %s", error)
            return {"success": False, "current": self.current, "error": "Could not check for updates."}

    def stage(self, version):
        current = Version.parse(self.current)
        release = self.releases().get(version)
        if not release or Version.parse(version) <= current:
            raise UpdateError("Requested release is not an available update")
        # Revalidate even cached metadata at the security boundary.
        if not trusted_artifact(release["artifact"], version) or not re.fullmatch(r"[0-9a-f]{64}", release["hash"]):
            raise UpdateError("Invalid release metadata")
        cleanup_stale(self.directory)
        fd, filename = tempfile.mkstemp(prefix=TEMP_PREFIX, suffix=".zip", dir=self.directory)
        path = Path(filename)
        try:
            self.log.info("updater: staging %s", version)
            digest = hashlib.sha256()
            count = 0
            deadline = time.monotonic() + DOWNLOAD_SECONDS
            with os.fdopen(fd, "wb") as output, open_url(release["artifact"]) as response:
                length = response.headers.get("Content-Length")
                if length is not None and (int(length) < 0 or int(length) > MAX_ARTIFACT_BYTES):
                    raise UpdateError("Artifact exceeds size limit")
                while True:
                    if time.monotonic() > deadline:
                        raise UpdateError("Download exceeded time limit")
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > MAX_ARTIFACT_BYTES:
                        raise UpdateError("Artifact exceeds size limit")
                    output.write(chunk)
                    digest.update(chunk)
                if length is not None and count != int(length):
                    raise UpdateError("Incomplete download")
            self.log.info("updater: downloaded %s bytes", count)
            if digest.hexdigest() != release["hash"]:
                raise UpdateError("SHA-256 mismatch")
            self.log.info("updater: SHA-256 verified")
            validate_zip(path, version)
            self.log.info("updater: staged at %s", path)
            return {"success": True, "version": version, "hash": release["hash"], "artifact": path.as_uri()}
        except BaseException:
            path.unlink(missing_ok=True)
            raise
