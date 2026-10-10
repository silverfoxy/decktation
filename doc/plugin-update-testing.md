# Direct plugin update testing

The updater checks `https://silverfoxy.github.io/decktation/store/plugins.json` and accepts stable, versioned Pages artifacts and exact project GitHub release ZIPs. It stages a ZIP in `/tmp`, verifies its SHA-256 and package structure, and requests Decky's native confirmation using `utilities/install_plugin` with install type `2`. It never extracts or replaces installed plugin files.

## Local checks

Run from the development checkout:

```sh
node scripts/release-version.mjs check
.venv/bin/pytest tests/ -v
node --test cloudflare/tests/*.test.js
pnpm run test:update
PYTHONPYCACHEPREFIX=/tmp/decktation-pycache .venv/bin/python -m py_compile main.py backend/src/*.py
pnpm build
```

On a Linux Docker build host with Decky CLI 0.0.7:

```sh
decky-cli plugin build -b -t /tmp/decktation-update-build -o build-output -s directory .
unzip -t build-output/decktation.zip
```

Assert that the ZIP includes `decktation/plugin.json`, `decktation/main.py`, `decktation/dist/index.js`, `decktation/bin/decktation_backend.py`, and `decktation/bin/plugin_update.py`. Check the existing bundled Python 3.11 dependencies, `whisper-server`, `ydotool`, `ydotoold`, `xclip`, and PortAudio as in the CI artifact checks. A frontend build or a synthetic test ZIP is not a validated installable package.

The Pages publishing test currently fails on case-insensitive macOS volumes when copying `decktation.zip` to `Decktation.zip`; use a case-sensitive Linux filesystem for that existing test. The full backend build targets Linux x86_64; an ARM Mac may require an x86_64 Docker build environment.

## Build an updater-enabled older test package

Pick the newest **stable release with a versioned Pages or project GitHub release ZIP** from the published catalog and record its version/hash. Do not use a branch, prerelease, `latest` alias, or GitHub source archive. Production manifests must stay at their actual version.

Create a temporary copy containing the current development changes (including the new updater module), with the directory itself named `decktation`:

```sh
TEST_ROOT="$(mktemp -d /tmp/decktation-updater-test.XXXXXX)"
TEST_COPY="$TEST_ROOT/decktation"
mkdir -p "$TEST_COPY"
rsync -a --exclude=.git --exclude=.venv --exclude=node_modules \
  --exclude=site --exclude=build-output --exclude=backend/out \
  --exclude=__pycache__ ./ "$TEST_COPY/"
cd "$TEST_COPY"
node scripts/release-version.mjs set 0.0.0
node scripts/release-version.mjs check
npm install
npm run build
decky-cli plugin build -b -t "$TEST_ROOT/build" -o "$TEST_ROOT/output" -s directory .
unzip -t "$TEST_ROOT/output/decktation.zip"
```

Verify that the ZIP manifest says `0.0.0` and that `bin/plugin_update.py` is present. Never commit this fake version or copy these manifests back into the production checkout. Keep the real updater-development ZIP available for reinstalling afterward.

## Steam Deck full flow

1. Record the installed Decky version. Back up settings outside the plugin directory (normally `~/homebrew/settings/decktation/`) and note the downloaded model/cache location and size (`$DECKY_USER_HOME/.cache/decktation/whisper.cpp/`, normally `/home/deck/.cache/decktation/whisper.cpp/`). Record enabled state, bindings, preset, language, model, sending mode, recording cue, haptics, and diagnostics preference.
2. Manually install the updater-enabled `0.0.0` test ZIP using Decky's ZIP installation flow. Open Check for updates from Advanced settings and confirm the Updates page reports the test version.
3. Open Decktation in Gaming Mode. Confirm it offers the selected published stable version and displays `0.0.0 → target`. Check again must refresh metadata without changing dictation settings.
4. Verify that recording, transcription, model loading/changing, test dictation, pending countdown/review drafts, and draft sending disable the action. Direct preparation RPC calls must also fail with the relevant busy reason.
5. While idle, press **Update to target**. Observe **Preparing update...**, followed by Decky's native update confirmation. There must be no custom second confirmation and no installation before accepting Decky's prompt.
6. Also close QAM during preparation once: no Loader request should follow while it remains closed. Disable networking after loading a model and use Check again; it must report a check failure while a real dictation still works.
7. Cancel once. The old instance should remain functional, with its Update button usable again after approximately eight seconds. Retry and accept the native confirmation while idle.
8. Confirm Decktation unloads and the published target installs/reloads without rebooting the Steam Deck. Check the installed manifest and displayed UI/version match the target.
9. Compare all recorded settings and the model/cache directory. Enable Decktation and perform a real dictation, including the configured sending mode.

**This test intentionally replaces the updater-development build with the published stable target.** That target may not contain the updater. Reinstall the real development ZIP if you want to continue testing development changes.

## Validation failures and known Decky bugs

Before the accepting test, run the mocked failure cases:

```sh
.venv/bin/pytest tests/test_plugin_update.py -v -k 'staging_failure or zip_rejects or bad_crc or partial_read'
pnpm run test:update
```

For a device-side development test, use a separate temporary test copy and a mock of `plugin_update.open_url`, never a configurable production feed. Supply a real test ZIP with (a) a mismatched metadata hash, (b) a corrupt ZIP whose metadata hash matches its bytes, and (c) a valid ZIP with a wrong plugin name or target version whose hash matches. Mock the canonical catalog and artifact responses; retain the normal preparation RPC and UI. The adapter must not be called on any preparation failure. Record installed-file hashes before/after; they must stay unchanged. Remove all mocks before the normal full-flow test.

- **#984 — Store telemetry:** Watch installation progress and Decky logs. **Incrementing download count** must not appear. The requested artifact must begin with `file:///tmp/decktation-update-`. Investigate any HTTPS handoff; the self-updater must never use that route.
- **#985 — deletion before Loader hash validation:** Wrong hash, corrupt ZIP, and wrong manifest must be rejected by Decktation before any native prompt. The current installation stays intact. Decky still receives the verified hash for its own second check.
- **#982 — watcher/extraction race:** Inspect Decky logs around unload, extraction, and startup. Record whether Decktation starts once or multiple times, including any partial-package import failures. Report the Loader limitation; do not patch its watcher from this plugin.
- **#976 — stale frontend:** Verify the displayed version and UI belong to the target. If closing/reopening QAM is required, record that behavior as a Loader limitation. Do not add Steam UI restart hacks.

Use the existing Decky/decktation logs under the Decky installation's logs directory. Look for updater catalog, staging, byte count, verified SHA, package validation, and staged-path messages. Network failures must produce only updater feedback, with normal dictation remaining usable.

## Lifecycle and limitations

The publisher may overwrite the current Pages catalog entry with a master prerelease and retain stable releases as GitHub asset URLs. Those exact `github.com/silverfoxy/decktation/releases/download/vVERSION/decktation.zip` paths are accepted; a single HTTPS redirect to GitHub’s dedicated `release-assets.githubusercontent.com` CDN is permitted only from that validated origin. CDN URLs are never accepted directly from metadata. All other redirects fail closed.

Metadata is cached in memory for one hour. This is a reuse window, not a polling interval; a full backend restart clears it. Check again forces refresh. There is no installer polling, silent installation, GitHub Releases API polling, or Cloudflare dependency.

Staged files are secure mode-0600 files retained for Decky's prompt. Owned regular staged files older than 24 hours are cleaned at later startup/preparation; canceling or closing QAM may leave a file until cleanup. Preparation is rejected if work is active, and is discarded if work starts during download. The native confirmation belongs to Loader: avoid starting dictation before accepting an outstanding prompt, since Decktation does not receive a reliable confirmation/cancellation callback.

Record automated results, actual ZIP validation, and physical results separately. Passing host tests does not validate real controller, Steam UI, Loader reload, or persistent-data survival.

## TLS and independent updater build

The updater uses the already packaged certifi CA bundle, with certificate and hostname verification enabled. Decky’s embedded Python may not locate the system CA bundle automatically. Never disable TLS verification to work around this.

This updater branch is based on upstream master and intentionally does not include the separate interface translation work. A main-page arrow icon opens the Updates page, also available through Check for updates at the end of Advanced settings, where preparation and Decky confirmation are requested.

## Hardware observation, 2026-10-10

The tester completed the native confirmation and installed published 0.3.18 from the updater-enabled 0.0.0 build. The installed manifest independently confirmed 0.3.18. Decky reopened the old Advanced panel until the tester exited and reopened Decktation, when the new UI appeared. This is consistent with upstream #976; the updater must not force Steam UI reloads. Two plugin log files appeared one second apart after replacement, so #982 remains a hardware investigation item rather than a confirmed single-start result.

When opening Updates from its main-page indicator, controller focus should land on the update action, keeping it visible, instead of jumping to the model selector below. The indicator uses a green arrow centered vertically beside its label.

## Stale-panel navigation and update discovery

The adapter now checks DeckyPluginLoader.deckyState.publicState().activePlugin.name after the native prompt request succeeds. If the active panel is Decktation, it calls closeActivePlugin() once. This clears Loader's stale active-plugin reference before replacement; the native prompt remains Decky's. Accepting or cancelling returns to the plugin list, where opening Decktation resolves the currently loaded plugin. If this optional Loader capability is absent or throws, installation continues; exit and reopen Decktation manually. No Steam reload, private state assignment, version polling or persistent navigation hooks are used.

Implementation reference: https://github.com/SteamDeckHomebrew/decky-loader/blob/main/frontend/src/components/DeckyState.tsx and upstream issue #976.

Test both acceptance and cancellation: the old panel must not reopen after the native prompt, other plugin panels must never be closed, and the new plugin must open normally from the list. The tester subsequently reported successful end-to-end operation with this mitigation; retain these checks for other Loader versions.

Advanced settings ends with Check for updates beside Diagnostics and Help. It opens a separate Updates page and forces metadata refresh. The main-page update indicator opens this same page. When no update exists, version and Up to date remain available there without taking space at the top of Advanced settings.

A one-time cached metadata check on frontend plugin startup controls a green dot on Decktation's microphone icon in Decky's plugin list, so the indicator can appear before opening the Decktation panel. It is a Decky-list indicator, not a global Steam taskbar badge. There is no repeating metadata polling or automatic installer. Check for updates refreshes the indicator too. Verify the dot appears for test 0.0.0 and disappears for an up-to-date review build.

The published stable target predates this updater: after testing 0.0.0 → published 0.3.18, manually reinstall the current review ZIP to test Check for updates and the new navigation in an up-to-date development build.

Hardware validation reported by the tester: the final update flow completed successfully, and after reinstalling the review build the Check for updates entry appeared in Advanced settings. Settings/model preservation and deliberate negative artifact fixtures should still be checked explicitly using the checklist above; do not infer them solely from successful installation.
