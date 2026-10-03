# Haptic feedback development and Deck validation

This feature is off by default. It uses the Steam Deck's vendor HID rumble
command, so it does not need the Decktation panel to be mounted. It does not
control external gamepads.

Protocol reference: [Linux `hid-steam.c`](https://github.com/torvalds/linux/blob/master/drivers/hid/hid-steam.c),
specifically `steam_haptic_rumble()` and `steam_send_report_id()`.

## Hardware proof of concept

On the tested Steam Deck (Valve HID `28de:1205`, vendor interface `input2`),
the 0x8f trackpad pulse was felt with the QAM open and with WoW foregrounded,
but remained too subtle for gameplay even at +6 dB. The Deck's evdev devices
reported no force-feedback capability. The 0xeb rumble command was clear and
comfortable in WoW with the QAM closed at speed 45000: one 150 ms burst for
start and two 100 ms bursts for stop. Controller input continued working. The
integrated plugin was then tested on a v0.3.16 stable installation with the
v0.3.17 `audio_runtime.py` added: the QAM test transcribed without sending,
and physical push-to-talk worked in WoW with the QAM closed. Each transition
produced its expected cue once.

To repeat the standalone manual test, copy only the script to `/tmp`:

```sh
scp scripts/test_deck_rumble.py steamdeck:/tmp/decktation-rumble-test.py
ssh steamdeck 'python3 /tmp/decktation-rumble-test.py start'
ssh steamdeck 'python3 /tmp/decktation-rumble-test.py stop'
```

Run each command once while holding the Deck. The script sends a stop command
in `finally`. It does not alter the installed plugin or settings.

## Opt-in development deployment

The installed stable plugin and this checkout share the same Decky identity.
Do this only after explicitly choosing to replace the installed files for a
development test. The inspected Deck uses the system `plugin_loader.service`
and `/home/deck/homebrew/plugins/decktation`.

Back up the complete stable plugin and settings before copying anything:

```sh
ssh steamdeck 'tar -C /home/deck/homebrew -czf /home/deck/decktation-stable-backup.tar.gz plugins/decktation settings/decktation'
```

From the repository root, build the frontend and stage only the changed files:

```sh
npm run build
ssh steamdeck 'mkdir -p /tmp/decktation-dev'
scp backend/src/decktation_backend.py backend/src/wow_voice_chat.py backend/src/haptic_feedback.py dist/index.js steamdeck:/tmp/decktation-dev/
ssh -tt steamdeck 'sudo install -m 0644 /tmp/decktation-dev/decktation_backend.py /home/deck/homebrew/plugins/decktation/bin/decktation_backend.py && sudo install -m 0644 /tmp/decktation-dev/wow_voice_chat.py /home/deck/homebrew/plugins/decktation/bin/wow_voice_chat.py && sudo install -m 0644 /tmp/decktation-dev/haptic_feedback.py /home/deck/homebrew/plugins/decktation/bin/haptic_feedback.py && sudo install -m 0644 /tmp/decktation-dev/index.js /home/deck/homebrew/plugins/decktation/dist/index.js'
```

Check the installed `plugin.json` version first. The tested Deck had v0.3.16,
which lacks the v0.3.17 `audio_runtime.py` imported by the current backend.
For that older base, stage and install it before restarting Decky:

```sh
scp backend/src/audio_runtime.py steamdeck:/tmp/decktation-dev/audio_runtime.py
ssh -tt steamdeck 'sudo install -m 0644 /tmp/decktation-dev/audio_runtime.py /home/deck/homebrew/plugins/decktation/bin/audio_runtime.py'
```

Then restart Decky and inspect the newest
`/home/deck/homebrew/logs/decktation/*.log`:

```sh
ssh -tt steamdeck 'sudo systemctl restart plugin_loader.service'
```

After Decky returns, enable **Haptic feedback** in Decktation. Test both the
physical push-to-talk binding in WoW with QAM closed and **Test Recording
(3s)** in the QAM. Verify start and stop cues, no duplicate cues, normal
controller input, and no text sent by the test action. Turn the setting off
and repeat to confirm silence. Keep the setting off on unsupported hardware.

Restore stable files and settings from the backup:

```sh
ssh -tt steamdeck 'sudo tar -C /home/deck/homebrew -xzf /home/deck/decktation-stable-backup.tar.gz && sudo rm -f /home/deck/homebrew/plugins/decktation/bin/haptic_feedback.py'
```

When restoring this Deck's v0.3.16 backup, also remove the added
`audio_runtime.py` before restarting:

```sh
ssh -tt steamdeck 'sudo rm -f /home/deck/homebrew/plugins/decktation/bin/audio_runtime.py && sudo systemctl restart plugin_loader.service'
```

For a v0.3.17 backup, keep `audio_runtime.py` and restart Decky directly.

The repository's GitHub Actions build workflow produces and validates the
final Decky ZIP. This file-level workflow is only for local development.
