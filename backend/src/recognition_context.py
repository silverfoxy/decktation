"""Bounded, application-independent recognition vocabulary snapshots."""
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

MAX_BYTES = 65536
MAX_TERMS = 100
MAX_CHARACTERS = 800


def read_context(path, base_dir=None):
    """Return (snapshot, status); failures never retain a previous snapshot."""
    if not path:
        return {}, "disabled"
    try:
        resolved = Path(path).expanduser()
        if base_dir is not None and not resolved.is_absolute():
            resolved = Path(base_dir) / resolved
        fd = os.open(resolved, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                return {}, "invalid"
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return {}, "invalid"
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}, "invalid"
        # Legacy WoW snapshots remain supported at this compatibility boundary.
        if "version" not in data and "terms" not in data:
            if not any(key in data for key in ("zone", "boss", "target")):
                return {}, "invalid"
            terms = [data.get(key, "") for key in ("zone", "boss", "target")]
        else:
            if type(data.get("version")) is not int or data["version"] != 1:
                return {}, "invalid"
            terms = data.get("terms")
            if not isinstance(terms, list) or len(terms) > MAX_TERMS:
                return {}, "invalid"
            for key in ("source", "updated_at", "expires_at"):
                if key in data and not isinstance(data[key], str):
                    return {}, "invalid"
            if "expires_at" in data:
                expiry = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
                if expiry.tzinfo is None:
                    return {}, "invalid"
                if expiry <= datetime.now(timezone.utc):
                    return {}, "expired"
        if any(not isinstance(term, str) or len(term) > 100
               or any(ord(c) < 32 or ord(c) == 127 for c in term) for term in terms):
            return {}, "invalid"
        return {"terms": [term.strip() for term in terms if term.strip()]}, "loaded"
    except FileNotFoundError:
        return {}, "missing"
    except (OSError, ValueError, TypeError, OverflowError, RuntimeError, RecursionError):
        return {}, "invalid"


def merge_terms(manual, external):
    """Manual vocabulary wins; preserve producer priority within a small prompt."""
    result, seen, size = [], set(), 0
    for term in [*manual, *external]:
        term = term.strip()
        key = term.casefold()
        cost = len(term) + (2 if result else 0)
        if not term or key in seen or len(result) >= MAX_TERMS:
            continue
        if size + cost > MAX_CHARACTERS:
            continue
        seen.add(key)
        result.append(term)
        size += cost
    return ", ".join(result) or None
