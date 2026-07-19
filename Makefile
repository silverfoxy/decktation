VERSION := $(shell node scripts/release-version.mjs print)
TAG := v$(VERSION)

.PHONY: version version-check version-set release-check release-tag

version:
	@node scripts/release-version.mjs print

version-check:
	@node scripts/release-version.mjs check

version-set:
	@test -n "$(VERSION)" || (echo "usage: make version-set VERSION=X.Y.Z" >&2; exit 1)
	@node scripts/release-version.mjs set "$(VERSION)"

release-check: version-check
	@set -eu; \
	if [ -x venv/bin/pytest ]; then venv/bin/pytest tests/ -q; \
	elif [ -x .venv/bin/pytest ]; then .venv/bin/pytest tests/ -q; \
	else python -m pytest tests/ -q; fi
	@python -m py_compile main.py wow_voice_chat.py controller_listener.py deck_hid.py

release-tag: release-check
	@set -eu; \
	test -z "$$(git status --porcelain)" || { \
		echo "error: commit or stash all changes before tagging" >&2; exit 1; \
	}; \
	! git rev-parse -q --verify "refs/tags/$(TAG)" >/dev/null || { \
		echo "error: tag $(TAG) already exists" >&2; exit 1; \
	}; \
	git tag -a "$(TAG)" -m "Release $(TAG)"; \
	echo "Created $(TAG). Push it with: git push origin $(TAG)"
