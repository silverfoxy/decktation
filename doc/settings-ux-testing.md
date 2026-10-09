# Settings UX (#20): Steam Deck test checklist

This branch assumes the merged haptic-feedback runtime. The UX change itself is frontend only (`src/index.tsx` and built `dist/index.js`).

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
- **Advanced:** Enter and leave with controls; confirm each page starts at the top. Change Model and confirm loading. Edit the existing 1–5 button combination using the button choice page; Down moves to the next row while Right reaches the adjacent trash icon, which remains visible. Add Button must work. Change Recording cue and Transcription sending; toggle Press Enter yourself, Remember channel, and Haptic feedback. Close and reopen QAM to confirm persistence.
- **Diagnostics:** Check controller readiness, live held-button preview, backend, keyboard helper, and model states. Toggle diagnostics sharing. Confirm backend and keyboard errors also appear on Main.
- **Navigation:** B returns from Diagnostics or Help to Advanced, and from Advanced to Main. Repeat entry and exit, then close and reopen QAM. Confirm focus remains usable and recording/status updates do not duplicate.

The test cannot be considered physically validated until the bundle has been installed on the Deck and these checks have been performed.
