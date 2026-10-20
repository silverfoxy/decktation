# SDL 3 controller comparison experiment

This standalone tool compares SDL 3 with Decktation's existing HIDRAW and evdev
readers. It runs independently of Decky and the plugin panel. It never writes
Decktation's state, binding, preview, or controller-debug IPC files and never
starts recording, types text, or sends rumble. Shadow binding counts use the
existing `ComboTracker`, with each source kept separate.

Status: tested with synthetic SDL virtual controllers and native SDL 3.4.18 on
the development machine. Physical Steam Deck, Steam Controller, and Legion Go S
coverage and coexistence with Steam/InputPlumber are **unverified**. The
experiment is separate from the Legion Go S production fix in PR #86.

## Run from a source checkout

Requirements: Linux, Python 3.11+, and a compatible SDL 3.2+ shared library. There
is no Python SDL package dependency; the observer calls SDL through `ctypes`.
The prototype uses a system library or the explicit `--sdl-library` path. It does
not yet bundle SDL into the plugin. Copy the source checkout to the test device,
or run from a mounted checkout; the script needs `backend/src` beside `scripts`.
It also needs the same device permissions as the existing controller listener.
Opening failure records distinguish permissions from missing input.

First test the controller exposed by the OS/InputPlumber:

```sh
python3 scripts/compare_controller_inputs.py --seconds 60 --buttons L4+R4 \
  > /tmp/decktation-input-os.jsonl
```

Then compare SDL's HIDAPI device drivers in a fresh process:

```sh
python3 scripts/compare_controller_inputs.py --seconds 60 --buttons L4+R4 \
  --sdl-hidapi on > /tmp/decktation-input-hidapi.jsonl
```

Use `--sdl-library /absolute/path/to/libSDL3.so.0` if SDL cannot be found.
`--sdl-only` observes SDL without opening additional legacy readers; use it to
check whether concurrent legacy access changes the result. `--seconds 0` performs
one discovery/event pass. Ctrl+C ends capture and prints a summary.

HIDAPI defaults to **off**, with background-controller events enabled. Per-driver
HIDAPI environment overrides are disabled in this mode. With HIDAPI **on**, SDL
may send device configuration reports as part of initialization; observation of
buttons does not mean its drivers are strictly read-only. Check gameplay and
Steam Input behavior during that run. The tool takes no exclusive evdev grab and
does not initialize SDL video, keyboard, or the Steam API.

## Hardware protocol

Keep the plugin panel closed, launch a game, and repeat the same sequence in each
mode. First run with Decktation's PTT disabled so comparing a recording combo does
not itself start dictation. The comparison tool is never an action source; the
installed plugin continues to use its existing readers.

1. Start with all controls released. Press and release each face button, shoulder,
   trigger, stick click, D-pad direction, and rear button individually, five times.
2. Click each trackpad independently, then touch it without clicking. The observer
   does not equate touch contact with a click.
3. Press/release the chosen shadow binding five times; use both `L1+R1` and a rear
   button binding in separate runs. Check short taps and held inputs.
4. Confirm the game still receives its normal input and that opening/closing the
   panel, reconnecting a controller, and suspending/resuming do not stick buttons.
5. Repeat with the regular plugin active and, if wanted, PTT enabled. Count actual
   recording starts separately from the tool's shadow counts. This prototype
   cannot prove actual PTT behavior or automatic duplicate-device suppression.
6. Record SteamOS, SDL, InputPlumber, controller firmware/connection, active virtual
   target, and Steam Input layout alongside the local capture. In particular,
   test physical Deck/Steam Controller controls under both gamepad and keyboard
   Steam Input layouts.

## Read the evidence

Output is local JSON lines: `started`, `connected`, `transition`, `raw_button`,
`disconnected`, errors, and a final `summary`. It includes local device paths and
numeric identities for manual correlation, but no serials, keyboard typing,
audio, or transcripts. It is not part of diagnostic upload or telemetry. Inspect
it before sharing it manually.

Every source has its own summary:

- `supported_buttons`: controls advertised by that reader; this is not proof of
  receiving events.
- `presses` / `releases`: observed normalized transitions, by button.
- `raw_presses` / `raw_releases`: SDL joystick button-index observations, kept
  separate from normalized gamepad events. Seeing both for one press is expected;
  raw events never count as shadow actions.
- `combo_presses` / `combo_releases`: observed edges of the selected shadow binding
  on that source. A combo cannot span different sources.
- `held_buttons`: the final observed held controls, useful for spotting stuck state.
- `disconnects` and `connected`: device lifetime evidence. Disconnection clears
  held state without pretending an actual release event arrived.

`SDL Touchpad` is SDL's single generic touchpad click; it is deliberately not
renamed to both `Left Trackpad` and `Right Trackpad`. `SDL Misc*`, `SDL Guide`, and
raw button indices preserve additional evidence without assigning guessed
physical semantics. Touchpad count is metadata, not independent click support.
Triggers use the same half-pull threshold as Decktation's existing readers.

Match sources manually using paths and the hardware setup. A physical device and
its virtual target can have different IDs, while two physical controllers can
share IDs. SDL instance IDs also change after reconnect. This tool intentionally
does not merge them, claim an SDL identity is a physical identity, or add SDL to
production PTT. Simultaneous observations are evidence for choosing a future
source policy; they are not an automatic equivalence test.

A useful result is: five presses and five releases for each expected control,
five shadow combo starts/releases per relevant source, and uninterrupted game
input. Missing rear controls in a virtual target cannot be recovered merely by
naming SDL's paddle buttons. Before replacing the existing readers, also verify
packaging on SteamOS, full trackpad-click coverage, duplicate-source selection,
and recovery from disconnect/suspend with held inputs.

## Automated verification

```sh
.venv/bin/python -m pytest tests/test_sdl_comparison.py -q
```

The native checks compile `tests/sdl_virtual_gamepad.c` into a temporary shared
library and attach an **in-process SDL virtual gamepad**. They verify the ctypes
ABI against SDL headers, ordered paddle/trigger/face-button press and release
events, and hotplug. They do not create a kernel input device or establish
physical hardware behavior. These checks skip when SDL development files or a C
compiler are unavailable; pure Python summary and error-path checks still run.

References: [SDL gamepads](https://wiki.libsdl.org/SDL3/CategoryGamepad),
[background events](https://wiki.libsdl.org/SDL3/SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS),
[HIDAPI switch](https://wiki.libsdl.org/SDL3/SDL_HINT_JOYSTICK_HIDAPI),
[SDL event ABI](https://github.com/libsdl-org/SDL/blob/main/include/SDL3/SDL_events.h),
[InputPlumber Legion Go S profile](https://github.com/ShadowBlip/InputPlumber/blob/main/rootfs/usr/share/inputplumber/devices/50-legion_go_s.yaml).
