# Transcription review validation

## Preview the UI

Open [the interactive local preview](preview/transcription-review/index.html) in
any browser. Select short, Unicode, long, manual-send, typing-failure, or countdown
examples. Press/release the simulated L4 button to send; hold it for 0.6 seconds
to cancel. This preview never records or injects text. Countdown is frozen for
inspection. The scene is illustrative; the card uses the live Cairo/Pango renderer.

Regenerate the preview on a machine with PyGObject, PyCairo, and Pango installed:

```sh
python scripts/preview_transcription_review.py
```

## Automated checks

```sh
pytest -q tests
npx tsc --noEmit
npm run build
```

Review coverage includes frozen final text/channel, manual-send labeling, stale
IDs, cancellation during transcription, duplicate/concurrent confirmation,
failed typing and persistence, controller tap/hold timing, presses begun before
preview readiness, fixed countdown deadlines, paused timer callbacks, QAM
approval/closing, stale renderer acknowledgments, Unicode wrapping, and long
text preventing quick confirmation. Renderer tests skip on hosts without Cairo
or PyGObject; they ran on this development host.

The interactive preview's JavaScript was also exercised through Node with a DOM
stub: tap sends, hold cancels, long text cannot send, and countdown press cancels.
That check does not establish browser rendering or Steam's controller navigation.

The frontend bundle committed with this feature was built successfully with the
production Rollup configuration and passed TypeScript checking using React 17
type declarations. The original development checkout's `dist` directory is
owned by `nobody`, so the fresh bundle was copied into an isolated worktree for
commit. The branch includes the updated `dist/index.js` and is ready for device
installation; a frontend rebuild is not required just to test the branch.

## Gaming Mode checks still required

1. Install a freshly built bundle and backend, then select Advanced → Sending →
   Review before sending. With QAM closed, record a short message. Wait at least
   ten seconds: text remains pending. Tap the configured binding: exactly one
   injection occurs and the card briefly acknowledges it.
2. Record again. Hold the binding for at least 0.6 seconds: the cancellation
   progress fills, the draft disappears, and releasing does not start recording.
   A fresh hold starts the next recording. Check whether the binding also
   triggers unwanted game actions, especially with multi-button chords.
3. Repeat with Recording cue set to Toast, Overlay, and None. Recording feedback
   follows that preference; the review card remains available in each case.
4. Dictate more than six wrapped lines. The card shows an excerpt and directs
   you to Decktation; tapping must not send it. Open QAM, focus the text, and use
   Up/Down to read it. At the scroll boundaries, navigation reaches the actions.
   Select Send: QAM closes, then typing targets the game. Cancel discards it.
5. Enable Press Enter yourself. The action says Type into chat. Confirmation
   types text without submitting it. Check channel parsing, remembered channels,
   accented text, CJK, handheld size, and docked resolution.
6. Select Send after countdown. Verify a 3–6 second countdown, immediate cancel
   on binding press, and conversion to persistent review when QAM opens.
7. Stop the overlay child or test without Gamescope. In explicit-review mode,
   text must stay pending and a toast must direct you to the panel. Approve there
   after reviewing the full text. Simulate a keyboard-helper failure: preserve
   the draft for explicit retry; check the game for partial input before retrying.
8. Disable/reload the plugin or change sending mode while a draft is pending.
   It must be discarded without typing. A binding held during transcription
   must be released and pressed afresh before it can confirm visible text.

These checks require a Deck running Gaming Mode and an active game. They have
not been performed as part of the local implementation.
