# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Decktation is a push-to-talk dictation plugin for Steam Deck that enables voice-to-text input for gaming. It uses OpenAI's Whisper model (via faster-whisper) with context-aware transcription optimized for World of Warcraft gameplay. All processing is done locally on the device.

## Build Commands

```bash
npm install           # Install Node dependencies
npm run build         # Compile TypeScript to dist/index.js
npm run watch         # Watch mode for development
```

Python dependencies are installed via `install_deps.sh` using the venv pip, which installs faster-whisper, sounddevice, numpy, and evdev-binary to the `lib/` folder.

## Testing

```bash
python test_voice.py           # Test transcription
python test_xdotool.py         # Test keyboard simulation
python test_context_benefit.py # Test context improvement
./test_wow_integration.sh      # Full WoW addon integration test
```

## Architecture

The system has five main components:

1. **Frontend Plugin** (`src/index.tsx`) - React/TypeScript Decky Loader plugin UI. Provides toggle to enable dictation, button configuration dropdowns, status display, and manual test button. Note: Steam's frontend input APIs only work when Steam UI is active, so controller input is handled by the backend.

2. **Backend Plugin** (`main.py`) - Python Decky plugin backend. Uses static methods and class variables (Decky quirk). Spawns the controller listener subprocess and polls for button state. Provides RPC methods for button configuration (`get_button_config`, `set_button_config`).

3. **Controller Listener** (`controller_listener.py`) - Separate Python process using evdev to detect configurable button combo on the Xbox 360 pad device. Reads configuration from `button_config.json` (default: L1+R1). Writes button state to `/tmp/decktation_l5`. Required because Steam intercepts some controller inputs and Decky has evdev import issues.

4. **Voice Service** (`wow_voice_chat.py`) - Core audio processing. Records audio via sounddevice, transcribes with faster-whisper (base model, int8, CPU), parses chat channel prefixes, types output via ydotool.

5. **WoW Addon** (`WowAddon/DecktationContext/`) - Lua addon that exports game state (zone, target, party members, class/spec) to SavedVariables every 2 seconds. The `convert_wow_context.py` script watches and converts this to `wow_context.json` for the voice service.

### Data Flow
```
User selects buttons in UI → set_button_config RPC → button_config.json
    ↓
Button Combo (evdev) → controller_listener.py reads config
    ↓
Button state → /tmp/decktation_l5
    ↓
main.py polls file → WoWVoiceChat.start_recording()
    ↓
Audio Capture → Whisper Transcription
    ↓
Parse Channel (party, raid, say, etc.)
    ↓
ydotool Types Text → Game Chat
```

### Chat Channel Detection
Voice input like "party, hello everyone" or "raid: pull boss" is parsed to extract channel prefix (`/p`, `/raid`) and message text. Supports separators: colon, comma, period, or space. Channels: `/s`, `/p`, `/raid`, `/g`, `/o`, `/y`, `/i`, `/w`.

## Key Files

- `src/index.tsx` - Plugin UI with button configuration dropdowns, status polling, manual test button
- `main.py` - Plugin lifecycle, spawns controller listener, polls button state, RPC endpoints for config
- `controller_listener.py` - Standalone evdev process for configurable button combo detection
- `button_config.json` - User's button configuration (created on first config change)
- `wow_voice_chat.py` - Whisper model, audio recording, transcription, ydotool output
- `convert_wow_context.py` - Lua SavedVariables parser with `--watch` mode
- `WowAddon/DecktationContext/DecktationContext.lua` - WoW addon for game context

## Configuration

- Whisper model: `WhisperModel("base", device="cpu", compute_type="int8")`
- Context file: `wow_context.json` (auto-generated from WoW SavedVariables)
- Button config: `button_config.json` (default: `{"button1": "L1", "button2": "R1"}`)
- Push-to-talk: Configurable two-button combo via UI (default: L1+R1)
- Available buttons: L1, R1, L2, R2, L5, R5, A, B, X, Y
- Logs: `/tmp/decktation.log`

## Platform Notes

- Designed for Steam Deck Linux environment (Gaming Mode)
- Uses **ydotool** for keyboard simulation (requires ydotoold service running)
- Setup ydotoold: `sudo /path/to/setup_ydotoold.sh` (creates systemd service with proper socket permissions)
- Steam Deck controller appears as "Microsoft X-Box 360 pad 0" to evdev
- L5/R5 back grips are intercepted by Steam and not exposed via evdev
- WoW runs via Proton; addon SavedVariables at `~/.steam/steam/steamapps/compatdata/*/pfx/drive_c/Program Files (x86)/World of Warcraft/_retail_/WTF/Account/<ACCOUNT>/SavedVariables/`
- Plugin installs to `~/homebrew/plugins/decktation/`

## Known Issues

- Steam's `RegisterForControllerStateChanges` API doesn't exist on all Steam Deck versions; using evdev subprocess instead
- Decky's Python environment has issues importing evdev directly (circular import), hence the separate subprocess approach
- Plugin class methods must use `@staticmethod` and `Plugin.xxx` instead of `self.xxx` due to Decky loader quirk
