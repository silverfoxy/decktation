# AGENTS.md

This file gives coding agents and other contributors current repository guidance.

## Project overview

Decktation is a Decky Loader plugin for controller push-to-talk dictation on Steam Deck. The TypeScript/React panel is in `src/`; the Python plugin backend and voice service are in `backend/src/`. The backend uses a bundled resident `whisper-server` (Vulkan when available, CPU fallback), captures audio locally, recognizes optional spoken chat-channel prefixes, and types text into the focused app.

The optional WoW addon is in `WowAddon/DecktationContext/`. It writes game context to WoW SavedVariables. WoW does not save each in-memory update immediately, so context read from that file can be stale during a play session. See [`doc/WOW_INTEGRATION.md`](doc/WOW_INTEGRATION.md).

## Release changelog

When preparing a release, update `CHANGELOG.md` as part of the release commit. Record all user-facing changes since the previous release under the new version and date, and keep the `Unreleased` section for changes intended for a later release. Check the commits since the previous release so user-facing changes are not missed.

## Website release notes and tutorials

- The website reads release notes directly from the root `CHANGELOG.md`. Do not
  maintain a separate copy under `site/`. Every documented version generates
  `/changelog/<version>/`; `Unreleased` generates `/changelog/unreleased/`.
- For each release, move the shipped changes into a new version/date section in
  `CHANGELOG.md` as part of the release commit. Include all user-facing changes
  since the previous tag, and leave future work under `Unreleased`.
- Review `site/src/data/tutorials.ts` and `site/src/pages/walkthrough.astro` for
  examples or availability notes affected by the release. Update the walkthrough
  when a feature ships or its controls/settings change; distinguish stable
  features from test-build features.
- Run `npm --prefix site run build`, `npm --prefix site test`, and
  `npm --prefix cloudflare test`. Check the new release's generated page and
  sitemap entry. Website deployment is triggered by `CHANGELOG.md` changes on
  `master`; verify that workflow and the published release-note URL after merge.
- Website popups are exported from the app's shared Cairo/Pango renderer in
  `backend/src/overlay_render.py`. After changing that renderer or the export
  script, run `/usr/bin/python3 scripts/export_website_overlays.py` and commit
  both `site/public/assets/app-overlays/sprite.svg` and `manifest.json`. Requires
  system PyCairo, PyGObject, and Pango. Website tests reject stale exports.
- Upload only the canonical `Decktation.zip` GitHub release asset. GitHub asset
  names are case-insensitive, so uploading a second `decktation.zip` alias collides
  with it; both URL spellings resolve to the same asset.
- Stable releases are announced by the trusted publisher using the tagged
  changelog notes and the `DISCORD_RELEASE_WEBHOOK_URL` repository secret. Verify
  the announcement after publishing; use the **Announce release on Discord**
  workflow to retry or announce a release that already exists. Preserve the
  hidden Discord message marker in release bodies to prevent duplicate posts.
  See `doc/DISCORD_RELEASES.md` for setup and recovery.
- Keep the tutorial's native recording, transcribing, review, and result visuals
  in sync with the app; regenerate them rather than drawing a separate imitation.

## Build and test

Build the frontend with Node and the repository's root package manifest:

```bash
npm install
npm run build
```

This generates `dist/index.js`, which is included in the Decky package. Run `npm run watch` for frontend development. The `npm test` script is a placeholder; use `npm run test:update` for the frontend update tests.

Set up and run the Python test suite with:

```bash
make test-setup
make test
```

The Python tests use mocks for audio and Decky-specific APIs and do not require a Steam Deck. `make release-check` runs the Python suite, release-version validation, and selected Python compile checks. CI also runs the Cloudflare Worker tests and builds and validates the installable Decky archive; see [`.github/workflows/build.yml`](.github/workflows/build.yml).

Website tasks use the separate Astro project in `site/` and Cloudflare Worker in `cloudflare/`. Their build and test commands are in [`site/README.md`](site/README.md) and the Worker package scripts.

## Source layout

- `main.py` is the small Decky Loader entry point. It imports `Plugin` from the packaged backend.
- `backend/src/decktation_backend.py` implements plugin lifecycle and RPC methods.
- `backend/src/wow_voice_chat.py` captures and transcribes speech, manages pending drafts, and sends text to the active app.
- `backend/src/controller_listener.py`, `deck_hid.py`, and `gamepad_evdev.py` read controller inputs in a separate process.
- `backend/src/resident_whisper.py` manages the local Whisper server. `backend/src/audio_runtime.py` and `clipboard_injection.py` handle audio setup and text insertion.
- `backend/src/telemetry.py` implements opt-in, scrubbed Sentry diagnostics. Sharing is disabled by default.
- `backend/entrypoint.sh` assembles the runtime files and binaries that Decky packages under the plugin's `bin/` directory. `backend/Dockerfile` pins and builds the native tools and runtime dependencies.
- `defaults/` contains the game preset and chat-language configuration bundled with the plugin.
- `scripts/` contains release, catalog, Pages publishing, and manual controller/haptic tools. `tests/manual/` contains hardware-dependent probes; these are not part of the automated pytest suite.

The Decky build workflow is the source of truth for the installable archive. It uses the Decky CLI and validates that the bundled Python runtime, Whisper server, audio libraries, and helper binaries are present.

## Runtime behavior and configuration

The frontend calls the Python backend through Decky RPC. The backend starts the controller listener, polls its state, and starts or stops recording on the configured physical button combo. The plugin bundles and manages its own `ydotoold`; it does not require a separately installed system service.

The default push-to-talk binding is L1 + R1. Users can configure one to five supported controls in the plugin. Persistent settings are read and written through Decky's settings directory; controller state and other temporary coordination files live in `/tmp`.

The voice service supports the standalone modes `once`, `continuous`, and `daemon`. Controller push-to-talk is provided by the Decky plugin; standalone keyboard push-to-talk is not supported. For standalone use, the CLI lives at `backend/src/wow_voice_chat.py`.

The default standalone channel is `say`. A spoken channel prefix can select a different destination for a message, and `--channel` selects the default. WoW context may improve game-term recognition, but it does not select a channel. The standalone CLI does not support `--channel auto`.

Whisper models (`base`, `small`, or `medium`) are stored in the user's Decktation cache and run locally. Optional Sentry diagnostics send data only after the user enables **Diagnostics → Share**. Consult [`doc/PRIVACY_AND_PERMISSIONS.md`](doc/PRIVACY_AND_PERMISSIONS.md) before changing what telemetry records.

## Development notes

- Keep substantive Python backend modules in `backend/src/`; `main.py` remains the Decky entry point.
- Keep the compiled frontend bundle `dist/index.js` in sync when changing frontend source, as required by the plugin build.
- Do not assume WoW SavedVariables reflect live in-memory addon state. The current converter reads snapshots from disk.
- Controller behavior depends on physical input reports and may require hardware for manual validation. Automated tests should continue to run without hardware.
- Follow the existing tests and CI checks when changing packaging, native runtime dependencies, plugin RPCs, or release behavior.
