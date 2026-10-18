# Integration and installed-device testing

This environment adds two distinct checks around Decktation's existing unit and
IPC tests. They are intentionally reported separately: a browser pass is not a
native Steam focus pass, and a device-runner fixture pass is not a physical
controller pass.

## Browser + real Python backend

See [Browser integration](INTEGRATION_BROWSER.md) for the harness architecture,
local setup, fault controls, and runnable scenarios.

The browser lane mounts the production React panel, adapts the Decky boundary,
and drives actual Python controller diagnostics through temporary listener IPC.
Audio devices, text entry, and remote telemetry must remain isolated from test
execution. Successful lifecycle responses come from the real backend, not an
independently fabricated set of browser fixtures.

The standard entry point is:

```sh
npm run test:integration
```

The tests exercise startup/acknowledgment, visible countdown, intercepted input,
early Stop, final report review, panel reopening, and failure/recovery paths.
Their Decky navigation adapter verifies browser wiring, not the native Steam
navigation tree. Failure evidence belongs under `test-results/` and
`playwright-report/`, not in the plugin payload.

## Installed Steam/Decky smoke runner

See [On-device testing](ON_DEVICE_TESTING.md) for exact commands, prerequisites,
mutation-approval flags, artifact verification, transport tests, and the manual
physical-controller checklist.

Use a dedicated authorized device and the exact CI-built plugin ZIP. Compare the
installed frontend and backend contents with the artifact before exercising the
UI. Installed bytes alone do not prove CEF is executing the new bundle; record
runtime identity evidence and explicitly report ambiguity rather than promoting
it to a passing result.

Keep SSH host-key verification enabled and tunnel debugger access to loopback.
The tooling must not enable remote debugging, install packages, deploy a plugin,
or dispatch input without an explicit action/approval. System-reserved Steam and
Quick Access buttons are outside the plugin's interception guarantee.

A native smoke should inspect Steam's actual gamepad focus, not infer it from DOM
order or `document.activeElement`. Synthetic CDP input is useful evidence but
remains distinct from a physical Steam Deck/Legion Go controller test.

## CI and release policy

`.github/workflows/integration.yml` runs on pull requests and relevant branch
pushes, including stacked PRs:

- **Chromium and real Python RPC integration**: installs Chromium, runs existing
  regressions and the browser/backend scenarios, and retains failure evidence.
- **Device runner safety and transport fixtures (not hardware)**: validates the
  device tooling using local artifact/transport fixtures. It does not connect to
  a personal Steam Deck from a public runner.

A device smoke is a separately authorized developer operation. Changes to input,
focus, or capture lifecycle should record an installed-device result before a
release is called hardware-verified. Missing device access must be reported as
**not run**, not silently treated as a pass. Never retry a race repeatedly until
one lucky run passes and discard the original failure evidence.

## Scope and dependencies

This infrastructure is a separate, stacked change based on the controller
capture implementation in PR #74. The test PR's base is that feature branch so
its diff excludes the diagnostic feature itself. Retarget/rebase onto `master`
after that dependency merges.

The kernel/uinput environment is not part of this change. Replayed input in the
browser lane does not emulate actual device discovery, hardware firmware, or
Valve raw-HID delivery. Keep the existing real-selector/IPC regressions and
physical-controller validation alongside this environment.

## Design references

Patterns were informed by `madrigal-eschat/decky-toy-haptics`'s Vite/Playwright
harness and `beallio/Decky-Metadata`'s on-device verification runbook and native
focus probes. This environment does not ship those plugins or claim that a
mocked Decky UI is a complete Steam emulator.
