# Controller haptic feedback: selection and test plan

The single **Haptic feedback** setting remains off by default. The controller
listener writes the source that completes the recording button combination
before it writes the pressed state. The backend captures that source at recording
start and uses the same source for the stop cue, even if another controller sends
input. Test Recording uses only a controller active within the last ten seconds.
When the identity is absent or stale, feedback is silent.

Exactly one backend is selected for the captured source:

| Input source | Output | Current evidence |
| --- | --- | --- |
| Steam Deck vendor HID | Valve `0xEB` rumble, 150 ms start / 2 × 100 ms stop | Physically confirmed on Steam Deck in WoW with QAM closed |
| Original Steam Controller wired (`28de:1102`) or receiver (`28de:1142`) | Legacy Valve `0x8F` pulse on both sides, one 15 ms start / two 15 ms stop | Mocked tests; physical test pending |
| 2026 Steam Controller Puck (`28de:1304`) | Native `0x80` HID rumble on the exact controller slot | Raw L1/R1 reports, one 150 ms probe, and integrated start/stop cues physically confirmed in WoW with QAM closed |
| Linux evdev gamepad with `EV_FF` and `FF_RUMBLE` | One 150 ms start / two 100 ms stop effects | Mocked tests; physical test pending |
| Steam Input virtual gamepad with `FF_RUMBLE` on the same input event node | Same evdev effect, routed by Steam Input | One 150 ms probe physically confirmed on a 2026 Steam Controller; integrated trigger still depends on Steam Input's button mapping |
| Virtual without force feedback, unidentifiable, or ambiguous output | No output | Safe no-op tested |

The evdev backend first checks force-feedback on the exact input event node.
This also supports a Steam Input virtual gamepad when that node itself accepts
`FF_RUMBLE`; Steam handles routing to its corresponding physical controller.
For physical devices with a separate output node, it matches only within the
same kernel HID/input parent and with the same bus, vendor and product
identity. It refuses ambiguous matches. It does not map a Steam controller
index to a guessed device or send an external controller's cue to the Deck.
A disconnected device is rediscovered at the next
cue or next recording session. Local logs name the input family, selected
backend, or reason for no feedback; they omit controller serial numbers.

The original Steam Controller protocol follows the [Linux `hid-steam.c`
legacy pulse format](https://github.com/torvalds/linux/blob/master/drivers/hid/hid-steam.c).
The 2026 Puck uses a distinct state report and [native `0x80` output
report](https://github.com/benashby/steam-puck-bridge/blob/main/src/steam-puck-bridge.c).
Its physical slot is preferred when raw buttons are received; a Steam Input
virtual pad can also use `FF_RUMBLE` when the input and output share its exact
event node. The legacy command is never sent to the Puck. Linux force feedback uses the [kernel input FF
ABI](https://docs.kernel.org/input/ff.html). SteamClient exposes haptic APIs,
but the required evdev-to-Steam-controller index mapping and delivery while WoW
is foregrounded with QAM closed are unverified, so this version does not call
those APIs.

## Standalone hardware probes

The probe requires an exact input path. Without `--play` it only checks identity
and capabilities. With `--play`, it sends one bounded start cue and leaves the
installed plugin untouched. Run it only after confirming the device path.

```sh
python3 scripts/test_controller_haptic.py --backend steam-controller --path /dev/hidrawN
python3 scripts/test_controller_haptic.py --backend steam-controller --path /dev/hidrawN --play
python3 scripts/test_controller_haptic.py --backend steam-controller-2026 --path /dev/hidrawN
python3 scripts/test_controller_haptic.py --backend steam-controller-2026 --path /dev/hidrawN --play
python3 scripts/test_controller_haptic.py --backend evdev --path /dev/input/eventN
python3 scripts/test_controller_haptic.py --backend evdev --path /dev/input/eventN --play
```

## Integrated Steam Deck check

After backing up the installed plugin and staging a matching build, explicitly
install the development files and restart Decky. In Gaming Mode, enable Haptic
feedback and check:

1. Hold the Deck and run Test Recording. Confirm one start cue, a distinct
   two-burst stop cue, transcription, and no text sent.
2. Close the QAM, foreground WoW, and use the physical dictation binding.
   Confirm one cue at each transition and normal controls.
3. With an external controller, use its own dictation binding. Confirm cues on
   that controller only, including stop after unrelated Deck input.
4. Disconnect during a recording and confirm the stop cue is silent and
   dictation still completes. Reconnect and confirm the next recording works.
5. Disable Haptic feedback and confirm transcription still works silently.

On the tested 2026 Steam Controller, the physical L1+R1 binding triggered
dictation, the start cue occurred once, and the two-burst stop cue occurred
once on that controller. Transcription and controls worked in WoW with the QAM
closed. Tapping a Deck button during the recording did not move the stop cue to
the Deck. The log selected `steam_controller_2026: triton-hid-rumble` for both
transitions. A virtual-pad `FF_RUMBLE` probe also reached the Controller, but
L1+R1 did not activate dictation via that virtual input under the tested WoW
layout; the raw Puck path is required for this layout. Switching Haptic feedback
off made the next Controller dictation silent while transcription still worked.
With the Controller still connected, the physical Deck binding produced its
start and stop cues only on the Deck; transcription and both sets of controls
remained normal. The log selected `steam_deck: deck-hid-rumble` for both cues.
Unplugging and reconnecting the Puck between recordings was also tested: the
listener rediscovered its slot without a Decktation restart, and the next
recording again transcribed with both cues on the Controller.

The previously tested Deck cue was comfortable at speed 45000. Earlier trackpad
pulses and low-strength Deck rumble were too subtle during WoW; the existing
Deck pattern is preserved. External-controller success remains pending physical
confirmation until the corresponding probe and integrated test are performed.
