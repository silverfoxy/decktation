# World of Warcraft Integration Guide

**Compatible with WoW Midnight (12.0+) and The War Within (11.0+)**

This guide explains how to set up Decktation with World of Warcraft for context-aware voice transcription.

## Overview

The WoW integration consists of three components:

1. **WoW Addon** (`WowAddon/DecktationContext/`) - Tracks in-game context
2. **Conversion Script** (`convert_wow_context.py`) - Converts SavedVariables to JSON
3. **Voice Service** (`wow_voice_chat.py`) - Uses context for better transcription

## How It Works

```
┌─────────────────┐
│   WoW Addon     │  Tracks zone, boss, party, etc.
│  (In-game Lua)  │  Saves to SavedVariables
└────────┬────────┘
         │
         │ DecktationContext.lua
         ▼
┌─────────────────┐
│ Conversion      │  Parses Lua → JSON
│    Script       │  convert_wow_context.py
└────────┬────────┘
         │
         │ wow_context.json
         ▼
┌─────────────────┐
│  Voice Service  │  Uses context in transcription
│ wow_voice_chat  │  Better accuracy for WoW terms
└─────────────────┘
```

## Complete Setup

### Step 1: Install the WoW Addon

**Option A: Manual Copy**

```bash
# Find your WoW installation
# On Steam Deck with Proton, it's usually here:
WOW_DIR=~/.local/share/Steam/steamapps/compatdata/<appid>/pfx/drive_c/Program Files (x86)/World of Warcraft

# Copy the addon
cp -r WowAddon/DecktationContext "$WOW_DIR/_retail_/Interface/AddOns/"
```

**Option B: Via Windows File Manager**

If you have WoW installed on Windows or through Proton:

1. Navigate to: `World of Warcraft/_retail_/Interface/AddOns/`
2. Copy the `DecktationContext` folder there
3. Restart WoW

### Step 2: Verify Addon is Working

1. Launch World of Warcraft
2. At character selection, click "AddOns"
3. Ensure "Decktation Context" is listed and checked
4. Log in to a character
5. Type `/decktation` - you should see context output

### Step 3: Set Up Context Conversion

**Find Your SavedVariables Location**

The addon saves to:
```
WTF/Account/<ACCOUNT_NAME>/SavedVariables/DecktationContext.lua
```

On Steam Deck:
```bash
# Find it automatically
find ~/.local/share/Steam/steamapps/compatdata -name "DecktationContext.lua" 2>/dev/null
```

**Run Conversion Script**

```bash
# Auto-detect and convert once
python convert_wow_context.py

# Or specify manually
python convert_wow_context.py --input "/path/to/DecktationContext.lua" --output wow_context.json

# Watch mode (recommended for live use)
python convert_wow_context.py --watch
```

### Step 4: Use with Voice Service

Now you can use the voice service with WoW context:

```bash
# Run once (5 second recording)
python wow_voice_chat.py --context wow_context.json --mode once

# Continuous mode
python wow_voice_chat.py --context wow_context.json --mode continuous

# Push-to-talk mode
python wow_voice_chat.py --context wow_context.json --mode push-to-talk --ptt-key '`'

# Daemon mode (for Decky integration)
python wow_voice_chat.py --context wow_context.json --mode daemon
```

## Recommended Workflow

### For Steam Deck Gaming

**Terminal 1: Run context converter in watch mode**
```bash
cd /home/deck/Documents/personal/decktation
python convert_wow_context.py --watch
```

**Terminal 2: Run voice service**
```bash
cd /home/deck/Documents/personal/decktation
python wow_voice_chat.py --mode daemon
```

The converter will automatically update `wow_context.json` whenever you zone, target enemies, or join/leave party.

### For Desktop Use

If you're running WoW on desktop and want voice transcription:

1. Install the addon in WoW
2. Run converter in watch mode
3. Run voice service in push-to-talk mode
4. Hold `` ` `` key to record voice, release to transcribe and send to chat

## Context Data Explained

The addon tracks and exports:

| Field | Description | Example |
|-------|-------------|---------|
| `zone` | Current zone | "Icecrown Citadel" |
| `subzone` | Specific area | "The Frozen Throne" |
| `boss` | Boss encounter or elite target | "The Lich King" |
| `target` | Current target | "Scourge Minion" |
| `party` | Party/raid members | ["Tank", "Healer", "DPS1"] |
| `class` | Your class | "PALADIN" |
| `spec` | Your spec | "Retribution" |

### How Context Improves Transcription

Without context:
- "Let's pull the Litch King" (wrong spelling)
- "I'm playing a power din" (misheard)
- "Meet at ice crown" (wrong spelling)

With context:
- "Let's pull the Lich King" ✓
- "I'm playing a paladin" ✓
- "Meet at Icecrown" ✓

The voice recognition model uses this context to:
1. Build an initial prompt with WoW vocabulary
2. Prioritize current zone/boss names as "hotwords"
3. Understand specialized terminology

## Automation Options

### Option 1: Systemd Service (Linux)

Create `/etc/systemd/user/wow-context-converter.service`:

```ini
[Unit]
Description=WoW Context Converter for Decktation
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/deck/Documents/personal/decktation
ExecStart=/usr/bin/python convert_wow_context.py --watch
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable it:
```bash
systemctl --user enable wow-context-converter
systemctl --user start wow-context-converter
```

### Option 2: Cron Job

Run every 2 minutes:
```bash
crontab -e
```

Add:
```
*/2 * * * * cd /home/deck/Documents/personal/decktation && python convert_wow_context.py
```

### Option 3: Game Launch Script

Create a script that launches with WoW:
```bash
#!/bin/bash
# wow_launch.sh

# Start context converter in background
python /home/deck/Documents/personal/decktation/convert_wow_context.py --watch &
CONVERTER_PID=$!

# Start voice service in daemon mode
python /home/deck/Documents/personal/decktation/wow_voice_chat.py --mode daemon &
VOICE_PID=$!

# Wait for WoW to close
wait

# Cleanup
kill $CONVERTER_PID $VOICE_PID 2>/dev/null
```

## Troubleshooting

### Addon not saving data

**Problem**: SavedVariables file not created or empty

**Solutions**:
- Log out (not just /reload) - SavedVariables write on logout
- Check addon is enabled in AddOns menu
- Type `/decktation` to verify addon is loaded

### Conversion script can't find SavedVariables

**Problem**: "Could not find DecktationContext.lua"

**Solutions**:
```bash
# Find it manually
find ~ -name "DecktationContext.lua" 2>/dev/null

# Then use --input flag
python convert_wow_context.py --input "/full/path/to/DecktationContext.lua"
```

### Context not improving transcription

**Problem**: Voice recognition still getting WoW terms wrong

**Solutions**:
- Check `wow_context.json` is being updated (look at timestamp)
- Verify voice service is loading the context file (check console output)
- Make sure you're in an area with recognizable names
- Try with more explicit context (during a boss fight, in a well-known zone)

### Performance issues

**Problem**: Game stuttering or high CPU usage

**Solutions**:
- The addon updates every 2 seconds - this is very light
- Converter in watch mode checks file every 2 seconds - also light
- If needed, increase check interval in convert_wow_context.py (line near `time.sleep(2)`)

## Advanced Configuration

### Custom Context File Location

If you want to use a different context file location:

```bash
# Converter
python convert_wow_context.py --output /custom/path/wow_context.json

# Voice service
python wow_voice_chat.py --context /custom/path/wow_context.json
```

### Multiple WoW Accounts

If you play multiple characters:

```bash
# Convert for specific account
python convert_wow_context.py --input "WTF/Account/ACCOUNT1/SavedVariables/DecktationContext.lua"
```

Or modify the addon to include character name in the SavedVariables.

### Custom Vocabulary

You can extend the context by manually editing `wow_context.json`:

```json
{
  "zone": "Icecrown Citadel",
  "subzone": "The Frozen Throne",
  "boss": "The Lich King",
  "target": "",
  "party": ["Tankadin", "Holypriest"],
  "class": "PALADIN",
  "spec": "Retribution",
  "custom_terms": ["Ashbringer", "Divine Storm", "Avenging Wrath"]
}
```

## Testing

### Test the Addon

In WoW, type:
```
/decktation
```

You should see output like:
```
Decktation Context Exported:
  Zone: Durotar
  Subzone: Valley of Trials
  ...
```

### Test the Converter

```bash
python convert_wow_context.py
cat wow_context.json
```

Should show valid JSON with your current context.

### Test Voice Service

```bash
# Record a test
python wow_voice_chat.py --mode once --duration 3

# Say something like: "Let's go to Icecrown and fight the Lich King"
```

Check if WoW-specific terms are transcribed correctly.

## Performance Tips

1. **Run converter in watch mode** - Most efficient for real-time updates
2. **Don't spam /reload** - SavedVariables write automatically on events
3. **Use daemon mode** - Best for Decky plugin integration
4. **Monitor logs** - Check `/tmp/decktation.log` for issues

## Privacy & Security

- All processing is local (no network calls)
- Context data stays on your machine
- No sensitive data is collected (only public game state)
- SavedVariables are standard WoW addon storage

## What's Next?

Once you have this working:

1. Integrate with Decky plugin for Steam Deck UI
2. Add custom keybinds in game for push-to-talk
3. Create macros that combine voice commands with game actions
4. Share your context improvements with the community

## Support

If you run into issues:

1. Check addon is loaded: `/decktation`
2. Verify SavedVariables file exists and has data
3. Test converter script independently
4. Check voice service can read wow_context.json
5. Review logs in `/tmp/decktation.log`

For more help, see the main README.md and individual component documentation.
