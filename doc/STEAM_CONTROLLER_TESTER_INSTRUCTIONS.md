# Steam Controller Test Instructions

Thanks for helping test Steam Controller support in Decktation.

## Install the test build

On your Steam Deck, open **Decky Settings** → **Install Plugin from URL** and
enter:

```text
https://silverfoxy.github.io/decktation/branches/steam-controller/decktation.zip
```

This URL is available after the `steam-controller` branch has been pushed and
its GitHub Pages build has completed.

Restart or reload Decktation after it installs. Connect your original Steam
Controller (USB or wireless receiver), then open the Decktation panel and
enable the plugin.

## Test it

1. In Desktop Mode, open a terminal and run:

   ```bash
   tail -f /tmp/decktation.log
   ```

2. When you see **"Press any controller button now"**, press A, L1, R1, L2,
   and both rear grips a few times.
3. In the Decktation **Input** section, set a combo such as L1+R1, then hold
   and release it. Confirm that recording starts and stops.

## Send back

Please send:

- Whether the controller was connected by USB or the wireless receiver.
- Whether the Input panel showed button presses and whether L1+R1 worked.
- The log lines beginning with `Probing Valve HID candidate`, `Selected raw
  Valve controller interface`, `Skipped HID candidate`, or `Raw HID candidate`.

Do not include voice recordings, dictated text, account names, or unrelated
system logs.
