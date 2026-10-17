# Installed Steam / Decky verification (layer 3)

**Status:** tooling and local transport fixtures are automation-tested. An actual Steam Deck / Steam / Decky run is **UNRUN** until an authorized operator supplies a target and performs this checklist. No device was used to develop this runner. Browser + real Python integration is a separate layer and does not establish native focus or physical-controller behavior.

## Safety and prerequisites

- Use a dedicated authorized test device. Install the **exact CI-built ZIP** manually through Decky's normal ZIP installer. Keep that original ZIP locally; do not rebuild it for the device test. The runner does not deploy anything.
- Python 3.9+ and OpenSSH on the operator machine; no extra Python packages. The target needs `sha256sum` and existing authorized SSH access. Establish and verify its SSH host key separately. The runner enforces `BatchMode=yes` and `StrictHostKeyChecking=yes`; it never accepts unknown keys or handles passwords.
- The operator must configure existing Steam CEF debugging **on target loopback only**, using their device's supported procedure. This tool does not enable debugging, edit Steam settings, start services, install packages, restart Decky or hard-reload any renderer. Do not expose a debugging port publicly. Check the actual configured remote port; `8080` is just the CLI default, not a claim about your device.
- Set the plugin UI to English before the run. Open **Decktation → Advanced settings → Diagnostics** yourself, and put native gamepad focus on the debugger's Start control. The runner deliberately does not navigate Steam, launch a game, open settings, or select the first CDP page.
- Use an exact target title and type from your authorized CEF target listing. `SP` below is an example, **not** an assumed Steam title. Missing, duplicate or unsupported targets fail closed. The remote websocket must advertise a loopback hostname.
- `--host` is mandatory. Hostnames/IPv4 or `user@hostname` are accepted; IPv6 SSH destination syntax and custom SSH CLI options are deliberately not supported (use a reviewed SSH config alias). All remote file paths are shell-quoted; no `shell=True` is used.

## Commands

Run from the repository root. Replace example host, target title, ZIP path and ports with your authorized values:

```sh
# Read-only: compare installed critical bytes with the original CI ZIP.
python3 scripts/deck/runner.py verify-artifact \
  --host deck@deck-test --artifact ./artifacts/Decktation-ci.zip \
  --target-title SP --output ./device-evidence/verify

# Read-only native UI probe; creates and closes only its own loopback SSH tunnel.
python3 scripts/deck/runner.py preflight \
  --host deck@deck-test --artifact ./artifacts/Decktation-ci.zip \
  --target-title SP --target-type page --remote-port 8080 --local-port 19222 \
  --output ./device-evidence/preflight

# Read-only UI state plus screenshot; operator must already show Diagnostics.
python3 scripts/deck/runner.py capture \
  --host deck@deck-test --artifact ./artifacts/Decktation-ci.zip \
  --target-title SP --output ./device-evidence/capture

# MUTATING: explicit synthetic input consent, and explicit acceptance that the
# current production UI cannot establish active frontend/backend byte identity.
python3 scripts/deck/runner.py smoke \
  --host deck@deck-test --artifact ./artifacts/Decktation-ci.zip \
  --target-title SP --allow-input --allow-unverified-runtime \
  --phase-timeout 8 --overall-timeout 60 --output ./device-evidence/smoke
```

Optional `--installed-root /absolute/plugin/path` overrides `/home/deck/homebrew/plugins/decktation`. That default is a path convention, not evidence of an installation. Ports are bound to `127.0.0.1` on both sides of `ssh -L`; occupied local ports are rejected. Tunnel failure does not trigger changes to the target.

### Exit codes and identity limitations

- `0`: **verify-artifact only** proved the seven installed critical-file hashes match the exact ZIP. It does not prove those bytes are executing.
- `1`: a check failed, transport was unavailable, a phase timed out, or consent was missing. Inspect `result.json` and any timeline/screenshots.
- `2`: native UI evidence was collected, but **active runtime identity is inconclusive**. Even a completed smoke flow remains exit 2. This is not a verified-device pass.

The verifier records the whole ZIP's SHA-256 and hashes for `package.json`, `dist/index.js`, `main.py`, `bin/decktation_backend.py`, `bin/controller_listener.py`, `bin/controller_debug_report.py`, and `bin/controller_debug_session.py`. It requires `PROTOCOL = 2` in the packaged session module, rejects traversal/noncanonical paths, duplicate entries, symlinks, missing critical entries and critical sources larger than 16 MiB. It never extracts the ZIP or reads bundled Python dependency contents. Installed source hashes are obtained read-only via `sha256sum`, not inferred from the copy path or version.

`source_sha_hint` comes only from a `g<hex>` development version in packaged `package.json`; otherwise it is null. It is a **hint**, not proof of source provenance. ZIP filename and Git branch are not used as identity. Matching installed bytes does not invalidate a stale CEF renderer or old backend process. The current Diagnostics DOM exposes no trustworthy active frontend byte hash or active backend `get_status.plugin_version`; the probe therefore reports both identities **inconclusive**, never invents a runtime SHA, and refuses input unless `--allow-unverified-runtime` is also supplied. A production/test-only runtime identity hook is future work before a verified native-build verdict can be emitted.

## What smoke does (and does not prove)

1. Verify installed critical bytes against the supplied ZIP before any CDP input.
2. Require visible scoped Diagnostics, idle/ready state and actual visible Steam `.gpfocus` evidence in the debugger region. DOM order and `document.activeElement` are not focus oracles; no `.focus()` is used.
3. Save baseline state and screenshot, activate Start with a **synthetic CDP mouse click**, and wait for recording plus a 1–30 second countdown.
4. Send paired keyDown/keyUp for Escape, ArrowDown and Enter. These are **synthetic CDP keyboard approximations for B, D-pad Down and A**, not injected physical controller events or proof Steam dispatches native gamepad events identically. After each pair, require the same visible recording screen and native debugger focus evidence; unexpected Stop/navigation fails.
5. Stop via a **synthetic CDP mouse click** on the touch/mouse-only Stop control, wait for ready, and save screenshot evidence. Every wait has a phase deadline (default 8 s, maximum 15 s); the CDP interaction has an overall deadline (default 60 s, maximum 120 s). Transport operations are also bounded.
6. Close only the runner-owned websocket and SSH process in `finally`. It does not terminate any Steam window, restore unrelated state, or automatically stop an unfinished capture after failure. If input failed after Start, let the existing 30-second capture finish and reopen Diagnostics manually.

A missing `.gpfocus` fails the input flow rather than silently substituting DOM focus. A completed synthetic trace does **not** prove raw controller event counts should increase. The fixture tests verify runner ordering and checks, not Steam behavior.

## Evidence and privacy

Use a **new output directory per run**. `result.json` includes artifact hashes, bounded probe state and a verdict. `timeline.json` includes only known UI phase, countdown/event count, known control labels/coordinates and native focus rectangles. Console/exception events are bounded to 100 method names; their arguments, exception messages, URLs and stack/home paths are discarded. No settings, audio, transcript, typing, backend logs or raw controller report are fetched; no report is uploaded and Sentry consent is never changed.

Screenshots (`baseline.png`, `recording.png`, `ready.png`, `capture.png`, or best-effort `failure.png`) show the current viewport and **can contain private Steam UI or report metadata**. Prepare a clean test account/screen and review/redact images before sharing. Do not upload the entire evidence directory without review. Failures before a usable scoped CDP connection may have only `result.json`; transport failures cannot guarantee a screenshot.

## Mandatory physical/manual acceptance checklist — UNRUN until recorded

Record artifact SHA-256, installed hash result, SteamOS/Steam/Decky versions (manually), active-runtime identity limitation, operator/date and screenshots/video. Mark each result pass/fail/unrun separately:

- Fresh entry and native focus: physically activate Start with A and release; Start must not become Stop after rerender. Countdown begins only after listener readiness.
- Press/release A, B, D-pad and every back paddle independently during capture. Navigation remains captured, no dictation/typing/audio action occurs, and expected controller events are visible in the sanitized report.
- Touch/mouse Stop works; controller activation must not trigger that touch-only control. Report reaches ready; inspect counts and protocol without uploading.
- Open **Steam** and **Quick Access** system menus during capture (reserved buttons may still open them), return to the plugin, verify same session/countdown and native focus. These system-menu actions are never automated here.
- Let 30 seconds expire; close/reopen Diagnostics while capturing; reopen after ready; repeat Start across rerenders. Check reconnect, producer acknowledgment, report completion and focus recovery.
- Repeat after a manual Decky/plugin reload and, if relevant, reboot. A copied frontend or matching package version is insufficient active-build proof.

## Local verification only

```sh
python3 -m pip install -r requirements-test.txt
python3 -m pytest -q \
  tests/test_deck_artifact.py tests/test_deck_transport.py tests/test_deck_smoke.py
```

The tests exercise real localhost HTTP/WebSocket frames, exact target selection, a separate CLI process and local fake-SSH forwarding process, input ordering/consent, transport timeout/socket/tunnel cleanup, unsafe ZIPs and installed hash mismatches. The fake SSH process is **not SSH authorization/encryption testing**, and its fixture state is **not Steam/Decky or real backend behavior**. No device action is needed to run these tests.
