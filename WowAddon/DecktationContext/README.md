# Decktation Context - WoW Addon

This addon tracks your in-game context (zone, boss, party members, etc.) and exports it to help improve voice transcription accuracy for the Decktation plugin.

## Features

- **Automatic context tracking**: Monitors zone, subzone, boss, target, and party members
- **Real-time updates**: Updates every 2 seconds and on relevant events
- **SavedVariables export**: Saves context data that can be converted to JSON
- **Chat commands**: Export context manually with `/decktation`
- **Event-driven**: Responds to zone changes, target changes, encounters, etc.

## Installation

### Method 1: Manual Installation

1. Copy the `DecktationContext` folder to your WoW AddOns directory:
   - **Retail**: `World of Warcraft/_retail_/Interface/AddOns/`
   - **Classic**: `World of Warcraft/_classic_/Interface/AddOns/`

2. Restart WoW or type `/reload` in-game

3. The addon will automatically start tracking context

### Method 2: Via Steam Deck

If playing WoW through Proton on Steam Deck:

```bash
# Find your WoW installation
COMPATDATA_DIR=~/.local/share/Steam/steamapps/compatdata

# Common app IDs for WoW (adjust if needed)
# Battle.net: various app IDs depending on how you added it

# Example path (adjust based on your installation):
WOW_ADDONS="$COMPATDATA_DIR/<appid>/pfx/drive_c/Program Files (x86)/World of Warcraft/_retail_/Interface/AddOns"

# Copy addon
cp -r DecktationContext "$WOW_ADDONS/"
```

## Usage

### In-Game Commands

- `/decktation` or `/dct` - Export current context to chat
- `/decktation help` - Show help message

### Automatic Operation

The addon works automatically once loaded:
- Updates context every 2 seconds
- Saves to SavedVariables on events (zone change, target change, etc.)
- Tracks boss encounters automatically
- Updates party/raid roster changes

### Integration with Decktation Plugin

The addon saves data to:
```
WTF/Account/<YourAccount>/SavedVariables/DecktationContext.lua
```

To use with the Decktation voice plugin:

1. Install this addon in WoW
2. Log in and play (context updates automatically)
3. Run the conversion script to generate JSON:

```bash
# Auto-detect and convert
python convert_wow_context.py

# Or specify the file manually
python convert_wow_context.py --input "/path/to/WTF/Account/ACCOUNT/SavedVariables/DecktationContext.lua"

# Watch mode (auto-converts on changes)
python convert_wow_context.py --watch
```

## What Context is Tracked?

The addon tracks:

- **Zone**: Current zone (e.g., "Icecrown Citadel")
- **Subzone**: Current subzone (e.g., "The Frozen Throne")
- **Boss**: Current boss encounter or elite target
- **Target**: Current target name
- **Party**: List of party/raid member names
- **Class**: Your character class
- **Spec**: Your current specialization

This context helps the voice recognition system better understand WoW-specific terminology when you're dictating in chat.

## Example Context Output

When you type `/decktation`, you'll see:

```
Decktation Context Exported:
  Zone: Icecrown Citadel
  Subzone: The Frozen Throne
  Boss: The Lich King
  Target: The Lich King
  Player1, Player2, Player3, Player4, Player5
  Class: PALADIN
  Spec: Retribution
JSON: {"zone":"Icecrown Citadel","subzone":"The Frozen Throne",...}
```

## Troubleshooting

### Addon not loading
- Check that the folder structure is correct: `AddOns/DecktationContext/DecktationContext.toc`
- Type `/reload` in-game
- Check AddOns list at character selection screen

### No context being saved
- Make sure the addon is enabled in the AddOns menu
- Log out or `/reload` to force SavedVariables to write
- Check the SavedVariables folder exists

### Context not updating in Decktation
- Run the `convert_wow_context.py` script to generate JSON
- Use `--watch` mode for automatic updates
- Make sure the output JSON file is in the correct location for the Decktation plugin

## Performance

The addon is very lightweight:
- Minimal CPU usage (updates every 2 seconds)
- Small memory footprint
- Only tracks essential data
- No UI elements (runs in background)

## Privacy

All context data stays local:
- Saved only to your WoW SavedVariables
- No network communication
- No data sent to external servers

## Compatibility

- **WoW Midnight**: Yes (Interface 120000 - Midnight expansion)
- **WoW The War Within**: Yes (Interface 110002+)
- **WoW Classic**: Should work (may need Interface version update in .toc)
- **Steam Deck**: Yes (designed for Steam Deck + Decktation)
- **Other Addons**: No known conflicts

## Development

The addon uses standard WoW API (updated for Midnight):
- `C_Map.GetBestMapForUnit()` - Current map ID
- `C_Map.GetMapInfo()` - Zone information (replaces deprecated GetRealZoneText)
- `GetMinimapZoneText()` - Current subzone
- `UnitName()` - Target/party names
- `IsInRaid()`, `IsInGroup()` - Party detection
- `GetSpecialization()`, `GetSpecializationInfo()` - Character spec
- Various events (ZONE_CHANGED, ENCOUNTER_START, etc.)

**API Changes in v1.1.0:**
- Replaced `GetRealZoneText()` with `C_Map` API (Midnight-compatible)
- Replaced `GetRaidRosterInfo()` with `UnitName("raidN")` for modern API
- Added backward compatibility for The War Within

## License

MIT - Feel free to modify and distribute

## Support

For issues or questions:
- Check the main Decktation project documentation
- Ensure WoW addon is loaded (`/decktation` should work)
- Verify SavedVariables file is being created
- Test the conversion script separately
