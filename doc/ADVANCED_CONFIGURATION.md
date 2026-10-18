# Advanced configuration

Most settings can be changed in the Decktation panel. The source configuration files described here are useful when developing the plugin or preparing a custom build.

## Transcription settings

- **Model:** Base is fastest, Small is a balanced choice, and Medium is more accurate but slower. A model may download from Hugging Face the first time it is used.
- **Language:** Choose a transcription language, or leave **Lang** on **Auto** for automatic detection.
- **Spoken punctuation:** Off by default. Enable in **Advanced settings → Sending** to convert English punctuation commands with **Auto Detect** or **English** selected. Other selected languages leave the words unchanged. Say “hello comma how are you question mark” to produce `hello, how are you?`. Supported commands are comma, period/full stop, question mark, exclamation mark/point, colon, semicolon, and ellipsis. Commands ignore case; multiword commands also accept hyphens. Casual chat keeps explicitly spoken trailing periods and ellipses, while still removing Whisper's automatic trailing periods. Turn it off when dictating these words literally. Processing stays local and does not add another model. Standalone users can pass `--spoken-punctuation`.
- **Transcription sending:** Choose Send immediately, Review before sending, or Send after countdown. Review stays visible until you tap your recording binding to send or hold it for 0.6 seconds to cancel. Long messages and typing failures require review in the Decktation panel. Countdown waits 3–6 seconds and a press of the recording binding cancels it; opening QAM pauses it for explicit review. Existing Confirm settings migrate to countdown.
- **Type text as keystrokes:** Off by default under **Advanced settings → Sending**, between Transcription sending and Press Enter yourself. Uses the keyboard helper instead of clipboard paste for games that block paste (for example Old School RuneScape). This is slower and supports ASCII only; unsupported characters fail without submitting or falling back to paste. Key mapping assumes a US-style keyboard layout. The selected game preset still controls whether chat is opened and Enter is pressed; use Generic if the focused field is already open. This setting is independent of **Press Enter yourself**.
- **Press Enter yourself:** Types the message without submitting it. In review mode, the confirmation action is labeled Type into chat. Press Enter in the game to send.
- **Remember channel:** Reuses the last channel you spoke when the next message has no channel prefix.
- **Recording cue:** Selects a Steam toast, the in-game Gamescope overlay, or no recording indicator.

## Game presets

Decktation includes three presets defined in [`defaults/game_presets.json`](../defaults/game_presets.json):

| Preset | Behavior |
| --- | --- |
| **World of Warcraft** | For chat channels, opens chat, adds the selected channel command, and sends with Enter. |
| **Guild Wars 2** | For chat channels, opens chat, adds the selected channel command, and sends with Enter. |
| **Generic** | Enters text directly in the focused field without opening or sending game chat. |

In WoW or GW2, start a message with a spoken channel name to route it. For example, “party ready” selects party chat, and “guild: hello” selects guild chat. Prefix matching is case-insensitive; a space, colon, comma, or period can separate the channel from the message. The **type** channel enters the text without opening or sending game chat. Trigger words are configured in [`defaults/channel_languages.json`](../defaults/channel_languages.json).

Built-in WoW channels include `say`, `party`, `raid`, `guild`, `officer`, `yell`, `instance`, `whisper`, `reply`, `type`, and `alert` (raid warning). GW2 includes `say`, `map`, `party`, `squad` (also `raid`), `team`, `guild`, `guild one` through `guild six`, `whisper`, and `type`.

### Spoken slash commands

With **English** or **Auto Detect** selected, begin with **command**:

| Spoken text | Entered text |
| --- | --- |
| command gg | `/gg` |
| command ready | `/ready` |
| command whisper Thrall hello | `/whisper Thrall hello` |

The longer **command slash** prefix is also accepted, as is `command /gg` if
Whisper recognizes the slash itself. A command name must follow the prefix.
This prefix works independently of the **Spoken punctuation** setting. Bare
“slash gg” stays literal. Command names are lowercased; argument case is kept.
Whisper's automatic trailing sentence punctuation is removed. If Spoken
punctuation is enabled, punctuation commands in arguments still work, without
changing the slash command name.

Commands bypass `/s`, `/p`, and other preset channel prefixes and leave the
remembered chat channel unchanged. Game presets open and submit chat using their
normal keys; **Press Enter yourself** skips submission. Review and countdown
settings still apply, and review shows **Command** as the destination. Generic
only types into the focused field. Decktation sends the literal command name the
transcription recognized; it does not validate which commands the game supports.

### Add a custom channel

Add the game command to the preset’s `channels` map in `defaults/game_presets.json`, then add the spoken alias under the same channel key in `defaults/channel_languages.json` for each language you want to support. For example, add a WoW `/1` channel to the `"wow"` preset:

```json
"channels": {
  "say": "/s ",
  "party": "/p ",
  "one": "/1 "
}
```

```json
{
  "languages": {
    "en": {
      "channels": {
        "one": ["one", "channel one"]
      }
    }
  }
}
```

The channel key must match in both files. Rebuild and reinstall a custom package after changing the defaults.

### Add a game preset

Add another entry to `defaults/game_presets.json`. The `channels` keys must match the channel names used by the language configuration.

```json
"my_game": {
  "name": "My Game",
  "chat_open_key": "enter",
  "chat_send_key": "enter",
  "default_channel": "party",
  "channels": {
    "party": "/p ",
    "type": ""
  },
  "whisper_prompt": "Vocabulary relevant to My Game.",
  "chat_open_delay": 0,
  "chat_send_delay": 0
}
```

The chat keys can be `"enter"` or `null`. The optional chat delays are in seconds. `whisper_prompt` supplies game vocabulary to the speech recognizer.

## Controller buttons

The default push-to-talk combination is **L1 + R1**. Use **Input → Add Button** and the button dropdowns to choose one to five buttons. Available inputs include L1/R1, L2/R2, Steam Deck grips L4/R4/L5/R5, and A/B/X/Y.

Linux evdev gamepads provide their exposed buttons; Steam Deck raw HID input preserves the physical Deck controls and rear grips independently of Steam Input layouts. Original Steam Controllers expose L5/R5 grip input on wired or USB-receiver connections. A keyboard-and-mouse-only Steam Input layout may not expose gamepad buttons, and third-party paddles are not guaranteed to appear as separate inputs. Face-button names follow Xbox positions.

## Custom controller mappings

Create `controller_mappings.json` in the plugin settings directory, normally `/home/deck/homebrew/settings/decktation/`. Each key is a lowercase hexadecimal `bus:vendor:product` identifier, with four digits per component. For example, this maps X/Y for a Bluetooth Xbox controller (`045e:02fd`):

```json
{
  "0005:045e:02fd": {
    "0x133": "X",
    "0x134": "Y"
  }
}
```

Values may be `A`, `B`, `X`, `Y`, `L1`, `R1`, `L2`, or `R2`. Keys are Linux evdev button codes written as hexadecimal strings, not Steam button IDs. Unspecified codes keep their built-in mapping. These overrides apply to digital buttons; analog trigger axes are detected automatically. A controller must expose the standard A/B capabilities to be discovered.

Use the controller status panel and `Controller input` log entries to identify the device and raw codes. Mappings are read when a device opens, so restart Decktation or reconnect the controller after editing. USB and Bluetooth IDs may differ, and Steam’s virtual controller has its own mapping. Capture separate X and Y presses from the same device before changing a mapping that appears incorrect.

For the optional World of Warcraft addon and context converter, see the [WoW integration guide](WOW_INTEGRATION.md).
