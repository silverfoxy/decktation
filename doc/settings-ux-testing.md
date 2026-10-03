# Settings UX (#20): Steam Deck test checklist

This branch starts from `feat/haptic-feedback`. Test it with that runtime installed. The UX change itself is frontend only (`src/index.tsx` and built `dist/index.js`).

## Smallest deployment for an approved Deck test

No backend file or saved setting needs replacing for this iteration. After the Deck owner approves this #20 deployment, run from the repository root:

```sh
ssh steamdeck 'cp /home/deck/homebrew/plugins/decktation/dist/index.js /home/deck/decktation-index-before-issue-20.js'
scp dist/index.js steamdeck:/tmp/decktation-issue-20-index.js
ssh -t steamdeck 'sudo install -m 0644 /tmp/decktation-issue-20-index.js /home/deck/homebrew/plugins/decktation/dist/index.js && sudo systemctl restart plugin_loader.service'
```

If the panel fails to open, restore the saved bundle:

```sh
ssh -t steamdeck 'sudo install -m 0644 /home/deck/decktation-index-before-issue-20.js /home/deck/homebrew/plugins/decktation/dist/index.js && sudo systemctl restart plugin_loader.service'
```

## Physical checklist

- **Main:** Open QAM using controls. Confirm it starts scrolled to the top; Enable matches saved settings; Game, Language, and binding are correct; Ready, loading, recording, and actionable error messages appear when relevant. Change Game. Open the single Language dropdown and navigate Auto Detect, Popular Steam languages, and Other languages with controls; choose a language and confirm it persists.
- **Test Dictation:** Select it with controls. Confirm recording feedback, an approximately three-second capture, then Transcribing and a timestamped result. Confirm no text is typed into WoW. Repeat. With haptics on, confirm the existing start and stop cues.
- **Advanced:** Enter and leave with controls; confirm each page starts at the top. Change Model and confirm loading. Edit the existing 1–5 button combination using the button choice page; Down moves to the next row while Right reaches the adjacent trash icon, which remains visible. Add Button must work. Toggle Toasts, Confirm, Manual, Remember channel, and Haptic feedback. Close and reopen QAM to confirm persistence.
- **Diagnostics:** Check controller readiness, live held-button preview, backend, keyboard helper, and model states. Toggle diagnostics sharing. Confirm backend and keyboard errors also appear on Main.
- **Navigation:** B returns from Diagnostics or Help to Advanced, and from Advanced to Main. Repeat entry and exit, then close and reopen QAM. Confirm focus remains usable and recording/status updates do not duplicate.

The test cannot be considered physically validated until the bundle has been installed on the Deck and these checks have been performed.

## Press-to-bind (#19)

Recording binding now lives on Main. Select **Change binding**, release the
activation button, hold one to five buttons together, then release to save.
Try **L4 + View**, a single **B**, D-pad, stick clicks, and trackpad clicks.
Confirm A/B/D-pad stay in capture instead of navigating the settings panel.
Cancel by touching **Cancel**, closing QAM, or waiting for the 20-second timeout;
the previous binding must remain unchanged. Test controller disconnection and
confirm buttons from two controllers are never combined. Dictation must stay
silent during capture and work immediately with the newly saved combination.
Reopen QAM and restart Decky to check persistence. Steam and Quick Access are
excluded. Expanded raw mappings follow Linux `drivers/hid/hid-steam.c`.

The test installer backs up replaced source files under
`/home/deck/decktation-press-bind-test/backup-*` and preserves runtime packages,
models, native helpers, and saved settings.

## Recording mode (#14)

On Main, open **Mode** under Recording binding. **Hold to record** remains the
default and sends on release, including short presses. **Tap to start/stop**
starts on press: a release within 250 ms keeps recording; the next press stops
and transcribes once. Holding for 250 ms or longer still stops on release.
Test a quick tap, several seconds of speech, and a second tap; then test a
held quick message using the same binding. Try a two-button combination and
release its buttons at slightly different times. Reopen QAM and restart Decky
to verify the selected mode persists. Verify pending-send cancellation still
cancels without starting another recording, and Test Dictation still shows
text without sending it. Mode changes and binding capture are unavailable
while recording. Disabling the plugin or disconnecting the controller cancels
hands-free recording without transcribing/sending it. Confirm normal haptic
start/stop feedback and no double-send after the second tap's release.

The recording-mode test installer stages at
`/home/deck/decktation-recording-mode-test`, backs up replaced source files,
and preserves saved settings, model data, and bundled runtime dependencies.
