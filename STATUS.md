# Decktation Plugin Status

**Date:** 2026-02-07

## Issue

Previous installation caused 100% CPU utilization, crashed SteamOS, and required recovery mode to disable.

## Root Cause Analysis

The Whisper model (~150MB) was loaded synchronously in the plugin's `_main()` async method during Decky initialization. This blocked Decky's event loop and caused the CPU spike.

Standalone testing confirmed the voice service works correctly outside of Decky:
```bash
python wow_voice_chat.py --mode once --duration 3  # Works fine
```

## Fix Applied

Implemented **lazy model loading** so the Whisper model only loads when the user explicitly enables dictation, not on plugin startup.

### Changes Made

**wow_voice_chat.py:**
- Added `lazy_load=False` parameter to `__init__`
- Added `_load_model()` method for deferred loading
- Added `is_model_ready()` method to check model state
- `transcribe_audio()` now ensures model is loaded before use

**main.py:**
- Service initialized with `lazy_load=True`
- Added `load_model()` RPC method
- `get_status()` now returns `model_ready` and `model_loading` states

**src/index.tsx:**
- Toggle calls `load_model()` when enabling dictation for the first time
- Shows "Loading Whisper model..." during model load
- Recording buttons disabled until model is ready

## Testing Instructions

1. Install the plugin:
   ```bash
   mkdir -p ~/.local/share/decky/plugins/decktation
   cp -r /home/deck/Documents/personal/decktation/* ~/.local/share/decky/plugins/decktation/
   ```

2. Monitor logs:
   ```bash
   tail -f /tmp/decktation.log
   ```

3. Monitor CPU:
   ```bash
   watch -n 1 'top -b -n 1 | head -15'
   ```

4. Restart Decky and open the plugin in Game Mode

5. Plugin should load quickly (no model loading yet)

6. Toggle "Enable Dictation" to trigger model loading

## Rollback

If issues occur, remove the plugin from Desktop mode:
```bash
rm -rf ~/.local/share/decky/plugins/decktation
```

## Latest Updates (2026-02-07)

### WoW Addon - Midnight Compatibility (v1.1.0)

Updated the WoW addon for compatibility with Midnight expansion:

**Changes:**
- Interface version updated from 110002 to 120000
- Replaced deprecated `GetRealZoneText()` with `C_Map.GetBestMapForUnit()` + `C_Map.GetMapInfo()`
- Replaced deprecated `GetSubZoneText()` with `GetMinimapZoneText()`
- Replaced `GetRaidRosterInfo()` with modern `UnitName("raidN")` API
- Added IconTexture and metadata fields to TOC file
- Created comprehensive CHANGELOG.md for the addon

**Backward Compatibility:**
- Maintains full compatibility with The War Within (11.0+)
- SavedVariables format unchanged - no migration needed
- All existing JSON conversion scripts work without changes

### Button Configuration System

Added configurable button combo system:

**Changes:**
- UI now shows current button combo (e.g., "L1+R1")
- Added dropdown selectors for Button 1 and Button 2
- Backend RPC methods: `get_button_config`, `set_button_config`
- Configuration stored in `button_config.json`
- Controller listener dynamically reads config and supports all button combinations
- Updated all documentation to reflect L1+R1 default (instead of L5)

**Available buttons:**
- L1, R1 (bumpers) - **Default combo**
- L2, R2 (triggers)
- L5, R5 (back grips - may not work)
- A, B, X, Y (face buttons)

**Why L1+R1 default?**
- L5/R5 are often intercepted by Steam
- L1+R1 is reliable and easy to press while gaming
- Users can customize to their preference

### Architecture Updates

**controller_listener.py:**
- Now reads `button_config.json` on startup
- Button codes mapped via `BUTTON_CODES` dictionary
- Supports all Steam Deck controller buttons
- Logs active button combo on startup

**main.py:**
- New RPC endpoints for button configuration
- Restarts controller listener when config changes
- Default config: L1+R1 if no config file exists

**src/index.tsx:**
- Button configuration UI with two dropdowns
- Displays current combo in multiple places
- Loads config on component mount
- Saves config changes immediately

## Next Steps

- [ ] Test plugin installation in Decky
- [ ] Verify model loading works when enabling dictation
- [ ] Test push-to-talk functionality with L1+R1
- [ ] Test button configuration changes
- [ ] Consider adding a loading timeout/cancel option
- [ ] Consider adding visual/haptic feedback when recording starts
