# SDL controller test build

This branch experiments with SDL 3.4.18 as the controller reader (#87). SDL is
bundled with the plugin; testers do not need to install packages. It is the
default in this build. The existing reader remains available under **Advanced
settings → Diagnostics → Controller input (test build) → Legacy (evdev / HID)**.
Only the selected reader supplies inputs, so duplicate backend triggers are
avoided. Switching restarts the listener. A failed start restores the previous
selection and reports an error; there is no silent fallback to legacy.

SDL supplies standard face buttons, D-pad, shoulders, stick clicks, View/Menu,
half-pull triggers, supported paddles mapped to L4/R4/L5/R5, and the standard
touchpad click mapped to Right Trackpad. Guide/Steam/QAM and other miscellaneous
buttons are not bindable. A separate Left Trackpad click is not represented by
SDL's standard mapping. Existing bindings are preserved; recapture them if the
selected controller does not expose the required controls. Rumble cues are not
implemented for SDL sources in this experiment; use the visual recording cue.

SDL is initialized without video or audio and with background input enabled.
Some SDL HID drivers configure devices on opening. Coexistence with Steam and
normal game controls must be tested; library support does not prove that the
required controls are accessible during gameplay or while Decky is open.

## Tester steps

Record the handheld model, SteamOS version, controller connection (attached,
detached, USB, Bluetooth), game, and Steam Input layout. Prioritize original
Legion Go, Legion Go 2, Legion Go S, Steam Deck LCD/OLED, and external controllers.

1. Select **SDL 3 (experimental)** in Diagnostics. Start a controller capture.
   Press and release A/B/X/Y, D-pad directions, L1/R1, L2/R2, stick clicks,
   View/Menu, and each rear button individually. Try the desired combination.
   Check that held buttons clear when released. Touch Stop or wait 30 seconds.
2. Review and export the report, or explicitly send it to Sentry. Report the
   event ID and which physical controls you pressed but could not see.
3. Capture a binding, then close Decky and test actual push-to-talk in a game.
   Confirm recording starts and stops, ordinary game controls still work, and
   each combination causes only one recording. Repeat on the Steam home screen.
4. Start another capture and close the panel during its recording window. Press
   the same controls in the game, wait 30 seconds, then reopen Diagnostics and
   review the completed report. Closing the panel does not end capture. This
   distinguishes input access with the panel open from access during gameplay.
5. Repeat with **Legacy (evdev / HID)** under identical conditions. Keep reports
   labeled with the selected reader and panel/game state. Do not switch during
   a recording, pending draft, binding capture, or diagnostic capture.
6. Test controller reconnect and sleep/resume. Confirm controls are released
   after a disconnect and push-to-talk works again after reconnect/resume.

Keep the runtime log from this same session. SDL startup logs its numeric
version; controller reports include `input_backend: sdl`, numeric gamepad type,
connection state, IDs, and supported controls. No controller names, paths,
serials, raw HID payloads, or keyboard typing are added to uploaded reports.
The SDL capture describes SDL-visible gamepads, not every raw HID interface.

If SDL input fails or affects normal controls, select Legacy and report the
comparison. If necessary reinstall the stable build. Hardware compatibility
and passive in-game access remain experimental.

## Development checks

`tests/test_gamepad_sdl.py` uses SDL virtual gamepads to exercise the actual C
ABI, button/trigger events, rapid press/release pairs, reconnection, and scrubbed
reports without controller hardware. It skips when SDL is unavailable locally;
CI builds the pinned dependency and sets `DECKTATION_TEST_SDL_LIBRARY`, making
library-load errors fail the tests. The Decky builder also initializes the
bundled library with the shipped Python interpreter before producing an archive.

For a source-tree listener run, set `DECKTATION_CONTROLLER_BACKEND=sdl` (otherwise
the standalone listener defaults to legacy). Installed builds load the bundled
`bin/lib/libSDL3.so.0`; source-tree runs use the system SDL3 library.
