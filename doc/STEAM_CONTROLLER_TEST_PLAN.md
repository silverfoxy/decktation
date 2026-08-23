# Steam Controller Validation Plan

Decktation currently treats the original Steam Controller as unsupported. Its
push-to-talk listener reads Valve raw HID reports, and the exact HID interface,
report format, and control mapping need validation on real hardware.

## What we need from a tester

- An original Steam Controller, connected either by USB or its wireless
  receiver.
- A Steam Deck running a current stable SteamOS build.
- Decktation installed from the test build and a microphone that works in Game
  Mode.
- Willingness to share command output and a short description of observed
  button behavior. Do not include account names, chat content, or recordings.

## Test matrix

Run the following once for each connection method available (wired and wireless
receiver). Record the SteamOS version, Steam Client build, controller firmware
version if shown, and Decktation version.

| Check | Steps | Pass condition |
| --- | --- | --- |
| Device discovery | Connect the controller before launching Decktation. Enable the plugin and inspect `/tmp/decktation.log`. | The listener identifies a Valve HID interface and does not repeatedly report that none was found. |
| Button preview | Open **Input** in the plugin and press A, B, X, Y, L1, R1, L2, R2, L5, and R5 individually. | Each available control appears in the **Button** preview on press. |
| Configured combo | Set a two-button combo, such as L1+R1. Hold it, then release it. Repeat with L2+R2 and L5+R5. | Recording starts only when the full combo is held and stops on release. Unsupported controls must not produce a false trigger. |
| End-to-end dictation | In the Generic preset, use the working combo and dictate a short neutral sentence into a text field. | The text is transcribed and typed once, with no stuck recording state. |
| Steam Input layouts | Repeat the configured-combo test with a standard Gamepad layout and a layout that maps the same controls to keyboard keys. | Physical-button detection remains consistent, or the difference is documented. |
| Reconnect | Disconnect and reconnect the controller, then retry the configured combo. | The listener recovers without restarting Decktation. |

## Collecting useful diagnostics

Immediately after a failure, capture the last 100 relevant log lines:

```bash
tail -n 100 /tmp/decktation.log
```

Also record whether the Input panel's button preview changed, whether the
recording toast appeared, and the exact configured combo. If the controller is
not discovered, include the output of:

```bash
ls -l /dev/hidraw*
grep -H -E 'HID_ID|HID_PHYS' /sys/class/hidraw/hidraw*/device/uevent
```

Avoid sharing unrelated system logs or personal game/chat data.

## Review and next decision

1. Compare results across wired and wireless connections and Steam Input
   layouts.
2. If discovery fails, update the supported HID interface matching and request
   a retest.
3. If discovery works but controls are wrong, capture raw report samples and
   correct the button/trigger mappings with unit tests.
4. Keep the unsupported notice until all matrix checks pass for at least one
   connection method and the fix is verified by the tester.
