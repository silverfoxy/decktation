# Gaming Mode recording indicator

The **Recording cue** setting selects the short Steam toast, a Gamescope overlay,
or no recording cue. Transcription review remains available in all three modes and uses its own
persistent overlay card, independent of the recording cue. If the card cannot
start, a toast directs the user to the full draft in Decktation. Existing `showNotifications` preferences migrate to **Toast** when
enabled and **None** when disabled.

The backend starts a separate `/usr/bin/python3` process as the `deck` user on the
first recording. It finds Gamescope's main Xwayland display through
`GAMESCOPE_XWAYLAND_SERVER_ID = 0`, sets `GAMESCOPE_EXTERNAL_OVERLAY = 1` on an
RGBA GTK 3 window, and gives that window an empty input region. The window never
requests focus. The full-display surface is transparent; only a 368 × 80 pixel
pill is drawn near the bottom center. Nine bars animate at 20 frames per second.
A JSON state file switches the indicator between recording, transcribing,
review, countdown, a brief result, and hidden without relaunching it. Review
uses shared Cairo/Pango drawing for readable Unicode text; the child reports
which draft was rendered and whether all text fits. Quick confirmation requires
a fresh, readable renderer acknowledgment. The child also reads Gamescope's
`GAMESCOPE_FOCUSED_APP` through Xlib so controller confirmation can check game
input focus without relying on a hidden browser window. Steam-menu focus blocks
confirmation; unavailable native focus falls back to verified frontend state.
Acknowledgments use atomic replacement in a child-owned directory, while the
backend state file stays owned by the plugin process. The card explains a blocked
confirmation instead of advertising a tap action that cannot run.

The focus-property interpretation follows
[Gamescope's input-focus publication](https://github.com/ValveSoftware/gamescope/blob/master/src/steamcompmgr.cpp). The full panel provides scrollable
text and Send/Cancel actions; sending closes QAM and waits for the frontend to
observe it closed before typing. Disabling the setting hides it; unloading the plugin
stops the child and removes its temporary state directory. If the plugin process
exits unexpectedly, the child detects its missing parent and exits. Overlay
errors are logged and do not stop recording or transcription.

Runtime dependencies are the SteamOS system Python, PyGObject/GTK 3, PyCairo, Pango/PangoCairo,
`xprop`, and Gamescope's external overlay support. No microphone or network
access is used by the indicator. `DECKTATION_OVERLAY_DISPLAY` may override
automatic Xwayland selection for development.

## Validation

- Standalone visual prototype displayed over WoW in Gaming Mode with QAM closed.
  The first small window appeared at the top left; a transparent full-display
  window placed the pill at the bottom center.
- The Deck owner confirmed the doubled translucent pill looked good and WoW
  chat, accented dictation, and controller input continued normally.
- A standalone run of the integrated manager on the Deck exercised recording,
  transcribing, hiding, and process cleanup. The integrated plugin still needs
  an in-game installation test before this behavior is considered released.

The design uses proportions studied in [Handy's recording overlay](https://github.com/cjpais/Handy/blob/main/src/overlay/RecordingOverlay.css).
The Gamescope property approach was studied in [OverLaid's backend](https://github.com/TheLogicMaster/OverLaid/blob/main/backend/main.cpp).
No source code from either project was copied.
