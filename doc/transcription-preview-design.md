# Transcription review design

Status: implemented in source; automated checks and offline rendering verified.
Gaming Mode installation and in-game interaction checks remain pending.
See [validation and preview instructions](transcription-review-testing.md).

## Problem

The current Confirm setting provides a 3–6 second cancellation window, not an
explicit confirmation. Pending text is announced by a frontend toast, polled
once per second. The Gamescope overlay supports only recording, transcribing,
and hidden; recording completion hides it even when text is waiting. Preview
must have its own persistent state and must not depend on a recording cue.

## Recommended experience

Enable **Review before sending** to keep recognized text pending until the user
chooses an action. The small recording pill expands into a review card in the
same bottom-center position after transcription completes.

```text
┌──────────────────────────────────────────────────────┐
│ Review transcription                      Party chat │
│                                                      │
│ I'll be there in a minute.                            │
│                                                      │
│ Tap L4 to send             Hold L4 to cancel          │
└──────────────────────────────────────────────────────┘
```

Show the actual configured PTT binding, including chords, rather than the
literal abbreviation “PTT.” Show a destination only when the backend knows it;
do not infer a destination from the visible game. Preview the final text that
will be typed, after any recognized channel commands have been removed.

- **Tap the recording binding:** send on release, only if held less than 600 ms.
- **Hold the recording binding:** fill a visible cancellation progress cue;
  cancel at 600 ms, then show “Cancelled” briefly. Releasing afterward does
  nothing. A fresh press starts the next recording.
- **Wait:** keep the card visible. Never auto-send reviewed text.

The review card stays input-transparent and does not take game focus. Its
action hints describe controller gestures, not clickable buttons. Do not bind
ordinary A/B buttons globally. Existing passthrough behavior of the configured
recording binding remains a constraint: validation must establish whether its
tap/hold gestures also cause unwanted actions in the game.

Use an approximately 600 px wide card at the 1280×800 reference size, 22 px
body text, generous line spacing, a dark near-opaque background, and adaptive
height. Keep the existing bottom margin initially and validate chat overlap
in game. Wrap using Unicode-aware text layout. Show up to six lines; do not
shrink text to fit.

For longer text, show an excerpt and “Open Decktation to review all.” Disable
the quick-send gesture for that draft. The Decky panel contains the full
scrollable text and explicit Send/Cancel buttons. Cancellation remains
available through the recording binding. This avoids sending content that the
user cannot read on the card. The panel also provides an accessible alternative
for users who find tap/hold gestures difficult.

When **Manual** is enabled, label the action **Type into chat** instead of
**Send**, and explain “You press Enter to send.” Rename that setting to
**Press Enter yourself** so the two settings describe different decisions.
Only acknowledge successful typing; a failed injection keeps the draft visible
with a retry action. “Sent” means input injection completed, not that a game
or server acknowledged delivery.

## Settings and fallback

Keep **Recording cue: Toast / Overlay / None** independent of review. Enabling
review always requires a visible review surface, even with recording cue None.
Use the Gamescope card in Gaming Mode and mirror the pending draft in the Decky
panel. Suppress duplicate preview toasts while the card is available.

If the overlay is unavailable, keep the draft pending, issue a toast directing
the user to Decktation, and require Send/Cancel in the panel. A short-lived toast
must not be the only opportunity to review or approve text. Hide the overlay
before panel-driven typing and verify that game focus has returned; do not
inject into the Quick Access Menu. If that cannot be verified, defer typing
until QAM closes or the user confirms through the in-game binding.

Retain the old behavior as an explicitly named **Send after countdown** option
if compatibility is needed. Existing Confirm users should retain that option
on upgrade because changing the meaning of a PTT press from cancel to send
would be surprising. New review users receive a short gesture explanation.
Countdown mode should also show text in the overlay, with remaining time based
on the backend deadline rather than a fresh duration from each frontend poll.

## Implementation outline

1. Introduce one backend-owned pending draft with an ID, final text, destination,
   mode, and optional countdown deadline. Add ID-checked send/cancel actions.
   Resolve each draft once, even when controller, timer, and panel act together.
2. Route real recording and test-mode transcription through the same pending
   transition. Publish recording → transcribing → review → completed states;
   remove unconditional overlay hiding when a draft exists.
3. Extend the overlay state file to structured JSON with text and action hints.
   Use Pango for wrapping and Unicode rendering. Add renderer readiness/health
   reporting so fallback decisions reflect an actually available surface.
4. Interpret the configured binding as tap/hold only while a review draft is
   active. Require a fresh press after the card becomes ready; a press begun
   during transcription must not confirm a newly created draft.
5. Add the full draft and actions to the panel, and separate review notifications
   from the recording-cue preference. Cancel pending work when disabling the
   plugin, unloading, or changing sending mode. Changing mode never sends a
   pending draft implicitly.

## Acceptance checks

- With QAM closed, review stays visible over a game in every recording-cue mode.
- Waiting beyond six seconds does not send in explicit-review mode.
- Tap sends exactly once; hold cancels without recording or sending on release.
- Presses during transcription cannot approve text that was not yet visible.
- Long drafts require full-panel review; Unicode text remains readable.
- Manual mode types without Enter and accurately labels the action.
- Overlay startup/crash failure retains the draft and offers panel review.
- Panel confirmation never types into QAM; injection failure retains the draft.
- Countdown expiry and cancellation races resolve a draft only once.
- Verify handheld/docked sizing, configurable chords, and game button passthrough.
