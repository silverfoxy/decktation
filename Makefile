VERSION := $(shell node scripts/release-version.mjs print)
TAG := v$(VERSION)
PYTHON ?= python3.11
TEST_PYTHON ?= .venv/bin/python

.PHONY: test-setup test python-version-check version version-check version-set release-check release-tag

test-setup:
	$(PYTHON) -m venv .venv
	$(TEST_PYTHON) -m pip install -r requirements-test.txt

python-version-check:
	@$(TEST_PYTHON) -c 'import sys; assert sys.version_info[:2] == (3, 11), "Backend tests require Python 3.11; recreate .venv with make test-setup PYTHON=python3.11"'

test: python-version-check
	$(TEST_PYTHON) -m pytest tests/ -q

version:
	@node scripts/release-version.mjs print

version-check:
	@node scripts/release-version.mjs check

version-set:
	@test -n "$(VERSION)" || (echo "usage: make version-set VERSION=X.Y.Z" >&2; exit 1)
	@node scripts/release-version.mjs set "$(VERSION)"

release-check: version-check test
	@$(TEST_PYTHON) -m py_compile main.py backend/src/audio_runtime.py backend/src/decktation_backend.py backend/src/wow_voice_chat.py backend/src/controller_listener.py backend/src/deck_hid.py backend/src/telemetry.py

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
