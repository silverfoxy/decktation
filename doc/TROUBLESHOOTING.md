# Troubleshooting

## Find the plugin logs

Decktation writes timestamped logs through Decky. The usual directory is:

```text
/home/deck/homebrew/logs/decktation/
```

Open the newest log for the current session. For example, in Desktop Mode:

```bash
ls -lt /home/deck/homebrew/logs/decktation/*.log
```

Controller-listener output is forwarded into the plugin log. Decktation no longer creates `/tmp/decktation.log`.

## Plugin does not become ready

- Wait for **Initializing service...** to finish.
- If the panel says **Keyboard helper unavailable**, reload the plugin. If it persists, reinstall using a packaged ZIP from the [installation guide](INSTALLATION.md).
- Check the latest Decktation log for backend or model-loading errors.
- The first use of a selected Whisper model downloads its files from Hugging Face; connect the Deck to the internet until the download completes.

## Test recording does not transcribe

Enable Decktation and wait for **Ready**, then select **Test Recording (3s)** and speak clearly while it records. Check that the Steam Deck microphone or connected headset works in another app. The test displays its transcription in the panel and does not type it into the focused app.

## Microphone crackles, pops, or cuts out

A Steam Deck LCD user reported popping in Steam's microphone test and poor Decktation transcription. Disabling Steam's voice-processing options removed the popping and improved transcription for that user. This is a community-reported workaround, not an independently verified fix or a confirmed defect affecting every LCD Deck. Its effect on Decktation's system audio input has not been established.

1. On the Deck, open **Steam → Power → Switch to Desktop**.
2. In the desktop Steam client, open **Friends & Chat**, then the **gear icon → Voice**. Depending on your Steam client version, Voice may also be available under **Steam → Settings → Voice**.
3. Check **Voice Input Device** and select the microphone you intend to use. Choose **Start Microphone Test**, speak, and listen for popping, crackling, or missing words. Stop the test afterward.
4. Note your current settings, then expand **Show Advanced Settings** if the options below are hidden. Try turning off all three voice-processing options:
   - **Noise Cancellation**
   - **Echo Cancellation**
   - **Automatic Volume/Gain Control** (automatic gain control; wording may vary)
5. Run **Start Microphone Test** again using the same microphone and phrase, then stop the test. If the audio improves, you can re-enable the options one at a time and repeat the test to identify which setting helps.
6. Return to **Gaming Mode**, enable Decktation, wait for **Ready**, and repeat the plugin's three-second dictation test. Check the resulting transcription before trying it in a game.

Restore your previous settings if this does not help. Disabling processing can increase background noise or speaker echo and can affect Steam voice chat. Clear playback in Steam does not guarantee that Decktation is receiving the same audio; if Steam sounds clear but dictation still fails, check the system's default recording device and the plugin logs.

When reporting a persistent problem, include your Deck model (LCD or OLED), SteamOS and Steam client versions, whether you use the built-in microphone or a headset, and whether the improvement survives returning to Gaming Mode and rebooting.

## Push-to-talk is not detected

- Open the plugin panel and check **Input**. **Receiving input** confirms decoded
  controller reports have arrived; held buttons should appear as you press them.
  **No controller found** means no supported input device was opened;
  **Waiting for input** means devices were opened but no decoded report arrived.
- Steam Deck and both generations of Steam Controller use physical HID reports,
  including the new Controller's Puck, so detection does not rely on Steam Input
  producing a virtual gamepad event. Other Linux gamepads use evdev; their
  controls must be exposed by the driver. Rear grips require distinct driver
  codes and a per-device mapping if they are not supported directly.
- Confirm the configured combination is held on one controller; buttons from different devices cannot be combined.
- Try a different combination, reconnect the controller, and check the latest log for controller-listener errors.
- Some Steam Input keyboard-and-mouse layouts do not expose gamepad controls. Third-party paddles may not appear as distinct buttons.
- If only one controller maps its buttons incorrectly, see [custom controller mappings](ADVANCED_CONFIGURATION.md#custom-controller-mappings).

## Transcription is slow or inaccurate

- If the microphone audio crackles, pops, or cuts out, try the [microphone troubleshooting steps](#microphone-crackles-pops-or-cuts-out) before changing models.
- Speak clearly and reduce background noise.
- Set **Lang** to the language you are speaking, or leave it on **Auto**.
- Base is fastest, Small is a balanced choice, and Medium is more accurate but slower.
- The WoW addon can add its latest saved context, but it does not reliably stream target or group changes during a session. See the [WoW context guide](WOW_INTEGRATION.md) for the limitation and upstream discussion.

## Text is missing or goes to the wrong place

- Put focus in the intended text field before using push-to-talk.
- For GeForce NOW clipboard paste, enable **Clipboard** in both the main GeForce NOW settings and its overlay settings; enabling it only in the overlay is not enough.
- Use **Generic** to enter text directly in the focused field. WoW and GW2 presets open their in-game chat and add a channel command.
- If **Manual** is on, Decktation enters the message and waits for you to press Enter.
- Check the panel for **Keyboard helper unavailable** and inspect the latest plugin log for `ydotoold` errors. Reload or reinstall the packaged plugin if the helper did not start.
- Use **Confirm** if you want a brief chance to cancel a game message before it is sent.
