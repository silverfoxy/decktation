# Browser + real Python controller integration

This is **layer 1**, not Steam/Decky or physical-controller validation. It mounts
`src/index.tsx` by invoking the production `definePlugin` callback, including the
real panel and `ControllerDebugClient`. It calls the real Python
`Plugin.start/get/stop/resume/upload_controller_debug` methods. A background replay
actor runs the production `controller_listener.ControllerDebug` producer and
exchanges protocol-v2 request/heartbeat/result JSON files with the real backend
owner in a fresh temporary directory. No successful capture RPC payload is
fabricated.

## Run

Requirements: Node 20+ and Python 3.11+, with pnpm 9.15.9 (the CI version).
The bridge itself uses only Python's standard library and the repository's backend
modules; no additional integration requirements file is needed. Existing backend
tests have their own requirements.

```sh
pnpm install --frozen-lockfile --ignore-scripts
pnpm exec playwright install --with-deps chromium
CI=true pnpm run test:integration
```

Override the Python executable or an already-installed Chromium when needed:

```sh
DECKTATION_TEST_PYTHON=/absolute/path/to/python3 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/absolute/path/to/chrome \
CI=true npm run test:integration
```

`CI=true` refuses to reuse an existing server. There are no automatic test retries.
Playwright limits discovery to `tests/integration/**/*.spec.ts`; existing Node
`frontend-*.test.cjs` tests are unchanged. Run the suite serially; one worker shares
one bridge, and the automatic fixture resets the backend module, owner, producer,
settings temporary directory, input replay, faults and side-effect counters before
**every** test. Do not override `--workers` or run two suites on the same ports.

For interactive inspection:

```sh
DECKTATION_TEST_PYTHON=python3 npm run dev:integration
# Open http://127.0.0.1:5179 in a browser.
```

The frontend listens only on `127.0.0.1:5179`; Python listens only on
`127.0.0.1:5180`. Stop with Ctrl-C. The Node supervisor closes Vite, terminates
Python, waits for its background thread and temporary-directory cleanup, and
escalates to SIGKILL only if shutdown fails. Do not expose either port publicly.

## Evidence and controls

The browser header permanently identifies replay-fixture evidence. Decky UI/SDK,
Steam navigation callback delivery, voice service/audio setup, external update
checks and telemetry are adapters. Native controller enumeration/event-reading,
Steam Input focus, kernel grabbing, physical button interception, microphone,
model inference and keyboard injection are **not** exercised. The background actor
is a thread in the Python bridge process, not the native listener's hardware
polling subprocess. It runs independently of browser polling and remains active
when the panel unmounts.

All controller lifecycle RPCs route through a fixed allowlist and the actual
backend implementation. The two unrelated UI-service adapters are explicitly
limited to `get_plugin_update` (no update/network discovery) and
`set_overlay_transcribing_label` (no native overlay). Microphone/text injection
attempts are counted and rejected by fail-closed voice boundaries. Telemetry is
replaced **before backend import**; explicit upload exercises the real backend
per-report consent/frozen-report path and records to memory with event IDs named
`local-fixture-event-*`. It never contacts Sentry.

The test-only `/api/control` endpoint is separate from `/api/rpc`. Allowed controls
are reset/inspect, bounded ACK/response delays, monotonic advance, pause/death,
busy voice state, bounded controller/HID press-release replay, and stale/malformed
**IPC-file** corruption. Replay accepts only `source: controller|hidraw`,
`button: A|L4`, and a boolean `pressed`. HID replay additionally allowlists
`Left Trackpad`, `Right Trackpad`, `D-pad Right`, and `D-pad Left` for simultaneous
long-label layout cases; these names are not accepted on the controller-key path.
Replay cannot choose a filesystem path or invoke
an arbitrary Python method. Both routes require a
random per-process 256-bit token, exact Origin when present, JSON content type,
and an at-most-8192-byte request. No CORS is enabled. The token is injected only
into the local test page. Tests also cover rejected authentication, origins,
oversized bodies and non-allowlisted operations.

The delayed-ACK automatic-finish test uses **real elapsed time** throughout its
3.5-second ACK delay and full 30-second capture. Another test advances only the
fixture's shared monotonic source to prove unmounted background completion.
Other flows use actual clocks for early Stop and bounded heartbeat/RPC errors.
Mock A/B/direction callbacks are cancelable events passed to production React
handlers; consuming them proves component wiring, **not native Steam behavior**.

## Compact debugger feedback regression slices

`debug-feedback.spec.ts` exercises the production panel and backend, not a copied
status component. Run one slice while bringing the stacked feature to GREEN:

```sh
CI=true pnpm exec playwright test --config tests/integration/playwright.config.ts \
  debug-feedback.spec.ts --grep 'live controller'
```

The scenarios cover:

- Capture copy under 400 characters in a 360×800 viewport, readable event/interface
  counts, Stop inside the viewport, and no horizontal panel overflow. This is a
  browser layout/copy budget, not an emulation of Decky's native CSS or focus.
- Send/submit control before the full report preview in both DOM and visual order.
- Explicit local upload showing **Report submitted** and its event ID, without
  queue/delivery-disclaimer wording. The text is a UI requirement; telemetry stays
  local and no remote-delivery claim is tested.
- Live L4 press/release from both `ControllerDebug.key` and
  `ControllerDebug.transition(..., 'hid', ...)`, through real producer IPC and
  `get_controller_debug`, into visible button/source/count feedback. Source aliases
  reflect deterministic enumeration: accepted `source_1`, rejected `source_2`, and
  replay HID `source_3`. No successful RPC JSON is fabricated.
- No in-progress full report, cleared terminal live state after Stop while held,
  immutable reviewed/uploaded reports, and ignored late key/HID observations.
- Reviewed `duration_ms` bounded to 0–30000, a nonempty `stop_reason`, and
  `initial_state`/`truncation` evidence alongside host version/OS/kernel/architecture
  and controller capabilities/transitions. Enum values and inner enrichment shapes
  intentionally remain the backend schema tests' responsibility.
- Rejection of arbitrary sources, keyboard names and nonboolean replay values.

The optional shared live contract is:

```ts
live_input?: {
  pressed: { source: string; button: string }[];
  last_event: {
    at_ms: number; source: string; kind: string;
    button?: string; code?: number; pressed: boolean;
  } | null;
}
```

Only recording may expose live transitions. Non-recording status may omit
`live_input` or return empty `pressed`/null `last_event`. The tests assume anonymous
`source_N` labels and allow small English label changes; they do not require new
production test IDs or expose native input paths. Browser coverage is English;
locale completeness remains in the frontend localization suite.

### Verification

The original missing-feature baseline failed compact-copy, send-order, submission
feedback, capture-outcome, and live-input assertions before the updated production
feature was applied. With the updated feature, the full serial Chromium suite
passes **29 tests**, retries disabled, under Node 22.14.0 and Python 3.11.2 using
Playwright 1.58.2 Chromium. The full Python suite passes **757 tests, 1 skipped**;
the frontend suite passes **42 tests**. These are browser/backend and fixture
results, not hardware evidence.

Failure traces/screenshots/logs stay local and ignored. Native/physical Steam
Deck or Legion Go controller checks and installed-device smoke remain **UNRUN**.

### Stable narrow-QAM layout regression

`capture-layout.spec.ts` runs at **320×600** and **360×640**, starting from a
Diagnostics page scrolled down to Start. It compares actual Chromium bounding
boxes for status, stats and Stop through starting, no-input recording, a single
held control, five simultaneous controls (including trackpads/D-pad), release,
countdown/counter changes and stopping. Held input has its own fixed-height scroll
region; timestamp prose does not grow the card.

Four completion cases cover Stop and automatic completion at both sizes. They
require Send and Back to be fully inside the viewport without scrolling, a
bounded visible JSON preview whose scrolling does not move either action,
ordinary cancel/Back navigation, dismissal for only the current session, a fresh
capture with no stale held source, and zero unsolicited upload. The existing RPC
timeout case also starts with a visible held source, requires it to disappear on
error, and retains its reconnect assertions.

```sh
node node_modules/@playwright/test/cli.js test \
  --config tests/integration/playwright.config.ts --reporter=line \
  tests/integration/capture-layout.spec.ts
```

The original active view failed with Stop moving **133 px** at 320 px width
(**76 px** at 360 px). After the capture-card fix that slice passed. The next
vertical slice reproduced Send below the viewport after both Stop and automatic
completion: its lower edge was **1190 px** in the 600 px viewport and **1100 px**
in the 640 px viewport. Dedicated review made all six narrow-layout cases pass.
Screenshots are viewport-only real browser/backend fixtures, not native Steam
screenshots. `LAYOUT_STAGE=before` prefixes baseline captures when reproducing
against the previous source.

The exact read-only installed-device probe now scopes Start/Stop and Send/Back
controls, including ready review after explicit submission. Its browser scenario
keeps the full ready-phase assertion and verifies the review controls instead of
accepting an invisible probe. The complete browser/backend suite passes **29 tests**
with retries disabled. Native focus restoration and physical held-confirm behavior
at completion remain **UNRUN**.

## Reports

- `playwright-report/index.html`: complete HTML report.
- `test-results/`: per-failure Chromium screenshot, trace and error context.
- On failure the automatic fixture attaches browser console/page errors, backend
  logs and a backend inspection/history/counter snapshot to the Playwright report.
- `tests/integration/.artifacts/backend.log`: most recent bridge run (gitignored).

The suite covers immediate Starting feedback before RPC delivery, delayed ACK,
full-duration countdown/finish, real producer metadata/device events, duplicate
activation, mocked navigation suppression, mouse/touch Stop and terminal drain,
unmount/remount, dead listener, stalled heartbeat, missing ACK, RPC timeout and
retry, stale/malformed producer snapshots, busy recording/transcription,
per-report upload consent and bridge safety. Every test asserts zero microphone
and typing calls, no unexpected upload and no background-actor/page errors.

Everything here lives under `tests/integration` and test-only devDependencies.
No production frontend/backend import points to this directory; the plugin build
continues to use its existing Rollup entry point, not this Vite server.
