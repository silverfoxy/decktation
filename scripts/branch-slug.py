"""Map Git branch names to shareable ASCII download paths."""

import hashlib
import re
import sys


def branch_slug(ref):
    slug = re.sub(r"[^A-Za-z0-9-]+", "-", ref).strip("-") or "branch"
    # Preserve readable paths for ordinary slash-separated branch names.
    # Other punctuation/Unicode gets a stable suffix to avoid losing identity.
    if re.search(r"[^A-Za-z0-9/-]", ref):
        slug += "-" + hashlib.sha256(ref.encode()).hexdigest()[:10]
    return slug


if __name__ == "__main__":
    print(branch_slug(sys.argv[1]))
