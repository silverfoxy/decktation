# Decktation - Push-to-Talk Dictation for Steam Deck

Voice dictation plugin for Steam Deck using faster-whisper with context-aware transcription.

## Features

- **Push-to-Talk**: Hold button combo (default: L1+R1) to record
- **Configurable buttons**: Choose any two-button combination from the Steam Deck controller
- **Context-aware**: Optional context support for better accuracy with game-specific terms
- **Fast transcription**: Uses faster-whisper for efficient CPU-based speech recognition
- **Auto-type**: Automatically types transcribed text into active window via ydotool

## Installation

### Prerequisites

1. **Decky Loader** must be installed on your Steam Deck
2. **ydotoold service** must be running for keyboard simulation

### Setting up ydotoold

The plugin uses ydotool to simulate keyboard input. You need to set this up once:

```bash
cd /path/to/decktation
sudo ./setup_ydotoold.sh
```

This creates a systemd service that runs ydotoold with proper permissions.

### Easy Installation

**Option 1: Install from URL (GitHub)**

1. Open Decky Plugin Store
2. Settings → Install from URL
3. Enter: `https://github.com/silverfoxy/decktation`
4. Plugin installs automatically with all dependencies

**Option 2: Manual Installation**

1. Copy the plugin folder to Decky plugins directory:

   ```bash
   cp -r decktation ~/.local/share/decky/plugins/
   ```

2. Restart Decky Loader

3. **Dependencies install automatically on first run!**
   - When you first open the plugin, it will show "Installing dependencies..."
   - This takes ~30 seconds (downloads ~200MB)
   - Then shows "Loading Whisper model..."
   - Once ready, you can enable the plugin

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
- **Output**: Keyboard simulation via ydotool
- **Dependencies**: Auto-installed to `lib/` folder (~200MB total)
- **Architecture**: TypeScript frontend + Python backend + separate controller listener process

## Privacy

- All processing happens locally on your Steam Deck
- No data sent to external servers
- Whisper model downloads from HuggingFace (one-time)

## Future Milestones

### Improved Installation Process
**Goal:** Fully automated installation where possible

- Auto-detect Decky's Python version and use matching dependencies
- Remove hardcoded Python paths (use `sys.executable`)
- Create `install.sh` that runs automatically on plugin install
  - Auto-install Python dependencies to `lib/`
  - Auto-generate ydotoold setup script if needed
- Add UI indicators showing setup status
- One-click install + one optional command for ydotoold

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
