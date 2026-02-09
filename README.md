# Decktation - Push-to-Talk Dictation for Steam Deck

Voice dictation plugin for Steam Deck using faster-whisper with context-aware transcription.

## Features

- **Push-to-Talk**: Hold button combo (default: L1+R1) to record
- **Configurable buttons**: Choose 1-5 button combinations from any Steam Deck controller buttons
- **Test Recording**: Built-in 3-second test with automatic transcription display
- **Context-aware**: Optional context support for better accuracy with game-specific terms
- **Fast transcription**: Uses faster-whisper for efficient CPU-based speech recognition
- **Auto-type**: Automatically types transcribed text into active window via ydotool
- **Toast notifications**: Optional notifications when recording starts/stops

## Installation

1. Download `decktation.zip` from [GitHub Releases](https://github.com/silverfoxy/decktation/releases)

2. Extract and install:
   ```bash
   unzip decktation.zip
   sudo cp -r decktation /home/deck/homebrew/plugins/
   ```

3. Setup keyboard simulation (one-time):
   ```bash
   sudo /home/deck/homebrew/plugins/decktation/setup_ydotoold.sh
   ```

4. Restart Decky or reload plugins from Decky settings

All dependencies are pre-bundled in the release

## Usage

1. Open Quick Access Menu (... button on Steam Deck)
2. Navigate to Decktation plugin
3. Enable the plugin (waits for Whisper model to load)
4. (Optional) Change the button combination in the plugin UI
5. In any app/game: hold **[button1]+[button2]** together to record, release to transcribe and type

## Button Configuration

The plugin uses a **two-button combo** for push-to-talk. You can configure both buttons from the plugin UI.

Available buttons:

- **L1, R1** (bumpers) - _Default combo_
- **L2, R2** (triggers)
- **A, B, X, Y** (face buttons)

**Default: L1+R1** (both bumpers pressed together)

## Use Cases

### Gaming

- **In-game chat**: Quickly dictate messages in MMOs, co-op games
- **Text input**: Type player names, search terms without keyboard
- **Accessibility**: Voice input for games requiring text

### General

- **Web browsing**: Fill forms, search, comment
- **Discord/messaging**: Send messages hands-free
- **Any text input**: Works in any active window

## Context Support (Optional)

For specialized vocabulary (game terms, technical jargon), you can provide context via JSON file:

Create: `~/.local/share/decky/plugins/decktation/context.json`

Example:

```json
{
  "zone": "Icecrown Citadel",
  "keywords": ["Lich King", "Sindragosa", "Arthas"],
  "vocabulary": ["paladin", "retribution", "holy"]
}
```

This helps the model correctly recognize domain-specific terms.

## Troubleshooting

### Plugin not showing up

- Check Decky Loader logs: `/tmp/decky-*.log`
- Ensure all Python dependencies are installed
- Restart Decky Loader

### Recording not working

- Ensure the plugin is enabled
- Check that Steam Deck mic is working (test in another app)
- Verify ydotoold is running: `pgrep ydotoold`
- Check logs: `/tmp/decktation.log`

### Button combo not detected

- Try a different button combination in the plugin UI
- Avoid L5/R5 as Steam may intercept these buttons
- Check `/tmp/decktation.log` for controller listener errors
- Verify controller listener is running: `pgrep -f controller_listener`

### Performance on Steam Deck

- Default `base` model is recommended (good balance)
- For faster: use `tiny` model (edit wow_voice_chat.py line 28)
- For accuracy: use `small` model (slower, needs more resources)

## Technical Details

- **Speech recognition**: faster-whisper (CTranslate2 backend)
- **Model**: base (150MB, ~2-4s transcription time)
- **Input**: Steam Deck microphone or connected headset
- **Controller input**: evdev (separate subprocess to avoid Steam interception)
- **Output**: Keyboard simulation via ydotool (bundled)
- **Dependencies**: Pre-bundled Python 3.11 libraries in `lib/` folder
- **Architecture**: TypeScript frontend + Python backend + separate controller listener process

## Privacy

- All processing happens locally on your Steam Deck
- No data sent to external servers
- Whisper model downloads from HuggingFace (one-time)

## Future Milestones

### Per-Game Configuration
**Goal:** Support different games with different chat systems

- Game profile system with built-in presets (WoW, FFXIV, Generic FPS, Direct Input)
- Auto-detect running game by process name
- Configurable per-game settings:
  - Chat activation key (Enter, T, Y, or none)
  - Channel prefix parsing (on/off)
  - Channel mappings (game-specific syntax)
  - Send key behavior
- Custom profile editor in UI
- Works seamlessly with any game, not just WoW

## Credits

Built with:

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Efficient Whisper implementation
- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) - Steam Deck plugin framework

## License

MIT
