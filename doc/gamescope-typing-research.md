# Experimental Gamescope typing: on-device test protocol

Gamescope text insertion is disabled after the on-device failures recorded below.
**Advanced → Sending → Text insertion** offers **Paste** (default) and
**Type (only English keyboard)**. Type requires an English (US) keyboard layout
and ASCII text; ydotool remains its internal engine. Saved Gamescope selections
reset to Paste, and the backend rejects new Gamescope selections.

## Pending: test the Gamescope keymap patch

Before re-enabling Gamescope typing, test a Gamescope build containing the
keymap compatibility/serialization fix discussed in issue #2311. Repeat both
direct scripts below with ASCII and Unicode in a plain X11 field and the original
game. Require the visible text to match exactly; helper exit status is insufficient.
Record the patched Gamescope version/commit and results. The patch has not yet
been tested on this device. Keep the helper and scripts for this research;
the historical plugin comparison steps below apply only to an experimental build
that explicitly re-enables Gamescope insertion.

## Why this is experimental

Gamescope's [private input-method protocol](https://github.com/ValveSoftware/gamescope/blob/74a06ff517ed9fc1307227406bd53ae847be3a91/protocol/gamescope-input-method.xml) takes an entire UTF-8 `set_string`, then `commit` with the latest `done` serial. The bundled helper is built from pinned protocol XML plus `backend/src/gamescope_inject.c` in the SteamOS-like Decky build image; it reads the literal transcription through stdin. The shipped [Gamescope implementation](https://github.com/ValveSoftware/gamescope/blob/74a06ff517ed9fc1307227406bd53ae847be3a91/src/ime.cpp) synthesizes key events with a temporary map; unlike the protocol description, the inspected implementation does not enforce exclusive input-method ownership or acknowledge delivery to a game. Consequently the helper's zero exit only means the Wayland requests completed a roundtrip, **not** that the game displayed text. The helper keeps its IME resource alive for 150 ms after commit to avoid destroying Gamescope's temporary keymap before its 100 ms reset window; this still cannot prove game delivery. [Gamescope issue #2311](https://github.com/ValveSoftware/gamescope/issues/2311) documents non-ASCII output appearing as digits on one Xwayland setup; the current source has a workaround but SteamOS installations were not verified. Gamescope typing therefore never presses Enter, regardless of the saved manual-send toggle. Its capability probe detects a missing socket/seat/protocol before opening chat, but cannot confirm focused-game delivery or IME exclusivity. This test backend accepts at most **40 Unicode characters** (including any preset channel prefix) to stay below Gamescope's 47 temporary keycode slots. It does not silently fall back to paste or ydotool.

## Installing a test build

Install the **ZIP built by this branch's GitHub Actions build workflow**, not the source ZIP or the PR #79 artifact; verify the installed version/commit matches the test branch. Its ZIP must contain `decktation/bin/gamescope-inject`. Record SteamOS and Gamescope versions and the active game. Back up your settings if using an update build. Do not test with sensitive text or in a chat that automatically posts on typing.

## On-Deck comparison

### Direct test result: 2026-10-19

SteamOS 3.8.28 (build 20260922.1), Gamescope package 3.16.23.6-1,
Xwayland 24.1.10-1.2. The installed helper completed its probe and commit
successfully. Wayland tracing showed the literal request
`set_string("Hi 907! | ñ é Ж 中")`; the user observed `1234567890-=qwert`
in the target field. These are exactly the first 17 entries of Gamescope's
`allow_keycodes`, interpreted under the ordinary US layout. This reproduces
incorrect mapping independently of transcription and plugin insertion routing.
The target application was not recorded.

The installed `/usr/bin/gamescope` contains the old generated compatibility
section (`xkb_compatibility "(unnamed)" { include "complete" };`), without the
`interpret Any+AnyOfOrNone(all)` workaround present in the pinned upstream source.
This supports the keymap serialization failure described in issue #2311 as a
likely explanation. It does not establish whether Xwayland rejected the map or
the target application ignored it; capturing the live Xwayland map or comparing
with an ordinary X11 text field would distinguish those cases.

Follow-up: `scripts/test_gamescope_x11.py --display :1` opened a plain Tk X11
entry in Gamescope. After the user clicked Run test, the script focused the
entry, committed the same sample and read the entry back automatically. Result:
`actual="1234567890-=qwert"`, `matches=false`, `helper_exit=0`.
The same failure therefore affects ordinary X11 text input, independently of the
original game. The exact keymap serialization mechanism remains unverified, but
the failure is reproducible in the Gamescope/Xwayland input path.

Repeat this comparison with `/usr/bin/python3 scripts/test_gamescope_x11.py
--display :1` (system Python supplies Tk). Click Run test in the resulting
window; it captures the entry's contents and closes 12 seconds after the result.

To bypass transcription, presets and chat-open keys, run the direct helper test
from this checkout while Gaming Mode is running:

```sh
python3 scripts/test_gamescope_typing.py --case ascii --trace
python3 scripts/test_gamescope_typing.py --case unicode --trace
```

Each invocation probes the compositor, prints the expected text, then waits 15
seconds for you to focus an empty game text field. Run the commands separately
and manually clear the field between tests. The script never clears text or
presses Enter. `--case mixed` combines ASCII and Unicode in one short sample;
`--probe` checks capability without typing. Protocol tracing includes the sample
so you can compare `set_string` with the visible result. Correct protocol text
with incorrect visible characters isolates the failure downstream of the plugin's
transcription and insertion routing, but does not by itself identify the cause.

1. In Gaming Mode, select **Generic** and focus a harmless editable field. Select Gamescope typing, dictate English (`test 123`), Spanish (`mañana ¿sí?`), and Russian (`Привет`). Compare the **visible characters**, not a success toast. If the field is blank or characters are wrong, record exactly what it shows. Manually clear between runs.
2. In a game that blocks paste (OSRS is the motivating report), focus chat and keep the message **unsent**. Use Generic if chat is already open, or a custom preset with the correct game chat-open key and no WoW `/s ` prefix. Compare the same English phrase under ydotool typing and Gamescope typing; check dropped, rearranged or duplicated characters. Only press Enter yourself after inspecting the text. A screenshot of the unsent draft helps.
3. Compare after reopening the game, with a non-US keyboard layout and after using Steam's on-screen keyboard. Include the exact SteamOS/Gamescope versions in the report, whether the helper is present/executable, selected preset, insertion choice, expected text, observed text and any error. If Gamescope fails, switch back to Paste or ydotool explicitly; do not retry into an uncleared text field.
4. Test Gamescope unavailable (e.g. Desktop Mode) and a failed helper execution; it should refuse insertion rather than open chat or submit. No automated fixture, subprocess return code or VM can verify the OSRS acceptance criterion.

Only after on-device results demonstrate reliable input should we decide whether to replace the ydotool typing implementation. Keep issue #76 open until the actual game behavior is verified.
