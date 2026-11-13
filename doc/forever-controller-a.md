# Forever controller A investigation

## Plugin submission

The branch now uses the captured output for profiles with controller-A
submission. Recording start copies the listener snapshot, transcription carries
it to the draft, and review/countdown retains it independently of later input.
Manual-send and typing-only channels do not require a controller destination.

Before opening chat or typing, submission opens the selected event node and
checks its identity, device number, inode, sysfs path, and gamepad capabilities.
It holds that descriptor through insertion and sends a 100 ms BTN_SOUTH pulse
through it. A press always attempts a release. There is no ydotool A fallback.
The listener masks injected A events on the destination for a bounded interval
so the pulse cannot start another PTT recording. Physical input is independent.
Disconnected/replaced devices and ambiguous selections produce a reviewable
failure instead of silently selecting another controller. Errors after insertion
warn that text may already be in chat, so retrying can duplicate text.

Physical-to-virtual mapping among multiple outputs is not implemented: only a
direct source match or the single-compatible-output fallback is supported.
Panel/standalone recording without a PTT snapshot cannot auto-submit controller
A; choose manual submission or start recording with the PTT binding.
Device numbering is not persisted. No code can infer whether the focused game
accepts the selected controller; the tester validates the input path only.

## Identifying the push-to-talk source

`python3 scripts/inspect_ptt_controller.py` reads the last captured source and
discovers current Steam outputs without sending input. Run on the Deck host
(with sudo if input-device permissions require it), after activating PTT.
The updated listener also includes this resolution in the activation snapshot.
`same_device` identifies an output source directly. `single_candidate` is only
a fallback, not a proven association with the physical controller. `ambiguous`
leaves the target empty rather than guessing among several virtual pads.
`unavailable` means no readable compatible output was found. Discovery records
kernel device identity for later revalidation; it does not create persistent
physical-to-virtual pairings. Injecting A is still a separate manual probe.

On activation the listener selects a device whose own configured combo qualifies
(including the exact-binding delay). It atomically captures the path, reader
kind, bus/vendor/product identity, SDL session when applicable, and timestamp
in `/tmp/decktation_haptic_source.json` before publishing the pressed state.
It also logs `ptt_activated` with `activation_source`. This existing haptic
snapshot remains fixed during the held press; unrelated controller activity
does not rewrite it. A new activation replaces it. It is listener-session
state, not a persistent device identifier or a gamepad-slot mapping.

For a running build containing this change, hold the push-to-talk combo and read:

```sh
cat /tmp/decktation_haptic_source.json
```

For physical HID readers this identifies the physical input source; for a Steam
virtual evdev reader it identifies that output directly. Mapping a physical
source to one of several Steam virtual outputs remains separate work. A
downstream dictation job must copy the snapshot at recording start if it needs
to retain the identity beyond the next activation.

## Existing Steam controller probe

The separate-gamepad probe was observed in MultiPad Tester's XInput view as
player 2; A pulses did not affect the main controller. This confirms separate
routing in that test, not Forever's controller-selection policy.

`scripts/probe_steam_controller_a.py` instead writes input events to an existing
Steam virtual Xbox controller (vendor/product 28de:11ff). Linux evdev's
[write implementation](https://github.com/torvalds/linux/blob/master/drivers/input/evdev.c)
calls input_inject_event. The user verified that this probe's A pulses appear
on player 1 alongside the Deck's controls in MultiPad Tester under Proton.
Actual Forever chat submission remains unverified.

Stop the original probe. Discover current paths (they can change):

```sh
sudo python3 scripts/probe_steam_controller_a.py
sudo python3 scripts/probe_steam_controller_a.py --path /dev/input/eventN --send --startup-delay 30
```

Replace eventN with a discovered path. Focus MultiPad Tester's XInput view during
the delay. Five 100 ms A pulses follow, five seconds apart. Do not press or hold
physical A during the test. Verify the pulses appear on the same player entry
as the Deck's sticks. The probe does not grab input or create a new controller;
it validates the opened device identity and refuses a pulse if A is already held.
Physical and injected input can still race; this is a manual diagnostic only.
This manual probe is independent of the plugin submission implementation above.

Branch prototype: `scripts/probe_controller_a.py`. It does not change plugin
submission or settings. It creates a separate Xbox-layout uinput gamepad,
keeps it connected, and pulses BTN_SOUTH for 100 ms every five seconds after
a 15-second startup delay. Ctrl+C releases A and removes the device.

## Test outside WoW

On the Deck host, in a terminal:

```sh
sudo python3 scripts/probe_controller_a.py
```

Focus a controller tester before the startup delay ends. Repeated A presses
can activate focused UI controls, so stop the probe before returning to normal use.
If `/dev/uinput` is absent on the host, investigate the uinput kernel module first.

1. Find `Decktation A probe` in `sudo evtest`, select it, and confirm code 304
   has alternating values 1 and 0, each followed by SYN_REPORT.
2. For its event path, run
   `udevadm info --query=property --name=/dev/input/eventN`.
   Check `ID_INPUT_JOYSTICK=1`.
3. Check Steam's controller input test. Confirm the new device is recognized
   and A lights up with each pulse.
4. Launch a controller tester through Steam in Gaming Mode with the same
   Steam Input configuration as WoW. Verify A and the controller/player slot.
   A browser tester alone does not establish Proton delivery.
5. Only then test Forever chat. Record Steam Input enabled/disabled, controller
   order, client version, and whether physical A and virtual A both send.

An evtest pass establishes Linux event emission only. Steam recognition and a
tester launched through Steam establish additional routing layers. A separate
virtual gamepad may land in another player slot or be ignored by the game;
that is unresolved. Do not replace plugin submission until this is verified.

## Evidence and hypothesis

- [Player dictation workflow](https://www.reddit.com/r/SteamDeck/comments/1xqe5cv/if_youre_considering_it_wowforever_will_be_good/)
  explicitly finishes with “Hit A to send”.
- [Blizzard forum feedback](https://us.forums.blizzard.com/en/wow/t/wow-forever-controller-feedback-clearer-customization-chat-and-pccontroller-switching/2377667)
  distinguishes native controller chat from ConsolePort and requests clearer
  send/focus documentation.
- [Linux gamepad specification](https://kernel.org/doc/html/latest/input/gamepad.html)
  identifies BTN_SOUTH as the south face button.
- [uinput documentation](https://kernel.org/doc/html/latest/input/uinput.html)
  describes creating devices with explicit capabilities.

Hypothesis: Forever's controller compose UI requires controller confirmation,
and the existing ydotool device is not routed as the expected controller.
Neither the exact client behavior nor this routing diagnosis is yet proven.
The current plugin already emits code 304 for its controller-A send option;
changing only that code or its hold time does not test device classification.
