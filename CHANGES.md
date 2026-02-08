# Changes - Button Configuration System

**Date:** 2026-02-07

## Summary

Updated the Decktation plugin to use L1+R1 (bumpers) as the default button combo instead of L5, and added a full button configuration system allowing users to customize their push-to-talk buttons.

## Key Changes

### 1. UI Updates (src/index.tsx)

**Before:**
- Displayed "Hold L5 to record"
- No button configuration options
- Hard-coded L5 references in help text

**After:**
- Displays "Hold L1+R1 to record" (or current configured combo)
- Added two dropdown menus for Button 1 and Button 2 configuration
- 10 button options available: L1, R1, L2, R2, L5, R5, A, B, X, Y
- Dynamic display of current button combo throughout UI
- Help text updates based on selected combo

**New Features:**
- `BUTTON_OPTIONS` array with all available buttons
- `button1` and `button2` state management
- Dropdowns call `set_button_config` RPC when changed
- Loads config on component mount via `get_button_config` RPC

### 2. Backend Configuration (main.py)

**New RPC Methods:**

```python
async def get_button_config(self):
    """Get current button configuration from button_config.json"""
    # Returns: {"success": True, "config": {"button1": "L1", "button2": "R1"}}

async def set_button_config(self, button1: str, button2: str):
    """Save button config and restart controller listener"""
    # Writes to button_config.json
    # Restarts controller listener with new config
```

**Updated Logic:**
- Controller listener restarts when config changes
- Default config: L1+R1 if no config file exists
- Updated log messages to say "Button combo" instead of "L5"

### 3. Controller Listener (controller_listener.py)

**Before:**
- Hard-coded L1+R1 button codes
- Static button detection

**After:**
- Reads `button_config.json` on startup
- `BUTTON_CODES` dictionary maps button names to evdev codes
- `load_button_config()` function loads user configuration
- Dynamic button detection based on config
- Logs show actual button combo being used

**Supported Buttons:**

```python
BUTTON_CODES = {
    "L1": 310,   # BTN_TL (left bumper)
    "R1": 311,   # BTN_TR (right bumper)
    "L2": 312,   # BTN_TL2 (left trigger)
    "R2": 313,   # BTN_TR2 (right trigger)
    "L5": 314,   # BTN_SELECT (left back grip)
    "R5": 315,   # BTN_START (right back grip)
    "A": 304,    # BTN_SOUTH
    "B": 305,    # BTN_EAST
    "X": 307,    # BTN_NORTH
    "Y": 308,    # BTN_WEST
}
```

### 4. Documentation Updates

**README.md:**
- Updated features list to highlight configurable buttons
- Added ydotoold setup instructions
- Expanded button configuration section explaining why L1+R1 is default
- Added troubleshooting for button detection issues
- Updated technical details with evdev architecture

**CLAUDE.md:**
- Updated architecture description with button configuration flow
- Added `button_config.json` to configuration section
- Updated data flow diagram
- Added new RPC methods to backend description
- Listed all available buttons

**STATUS.md:**
- Added "Latest Updates" section with full changelog
- Documented button configuration system implementation
- Explained architectural decisions
- Updated next steps

**New Files:**
- `INSTALLATION.md` - Comprehensive installation and setup guide
- `CHANGES.md` - This file, documenting all changes

### 5. Built Frontend

**dist/index.js:**
- Rebuilt from TypeScript source with all UI changes
- Includes button configuration dropdowns
- Updated display text

## Configuration File Format

**button_config.json:**

```json
{
  "button1": "L1",
  "button2": "R1"
}
```

This file is created when the user first changes button configuration from the UI.

## Default Behavior

If no `button_config.json` exists:
- Backend returns default: `{"button1": "L1", "button2": "R1"}`
- Controller listener uses L1+R1
- UI displays L1+R1 in all text

## Migration Path

Users upgrading from previous versions:
1. No action required - defaults to L1+R1
2. If they prefer different buttons, select from dropdowns
3. Configuration persists across plugin reloads
4. Restart controller listener when config changes

## Why L1+R1?

**Previous approach (L5):**
- L5 back grips are intercepted by Steam on many configurations
- Not accessible via evdev on all Steam Deck models
- Unreliable for production use

**New default (L1+R1):**
- Both bumpers reliably detected via evdev
- Not intercepted by Steam
- Easy to press simultaneously while gaming
- Doesn't conflict with most game controls
- Users can still choose L5+R5 if it works on their device

## Testing Checklist

- [ ] UI displays current button combo correctly
- [ ] Dropdowns show all 10 button options
- [ ] Changing button 1 updates config and restarts listener
- [ ] Changing button 2 updates config and restarts listener
- [ ] button_config.json is created/updated correctly
- [ ] Controller listener reads config on startup
- [ ] L1+R1 combo triggers recording
- [ ] Other button combos work when configured
- [ ] Config persists across plugin reload
- [ ] Logs show correct button combo names

## Future Enhancements

Potential improvements for future versions:

1. **Single-button mode** - Allow single button press (not combo)
2. **Triple-button combos** - Support 3+ buttons
3. **Visual button tester** - Show which buttons are currently pressed
4. **Preset combos** - Quick selection of common combinations
5. **Per-game configs** - Different buttons for different games
6. **Haptic feedback** - Controller vibration when recording starts/stops

## Breaking Changes

None. The plugin remains backward compatible:
- Default behavior changes from L5 to L1+R1
- Users can configure back to L5+R5 if preferred
- No API changes for existing integrations

## Files Modified

1. `src/index.tsx` - UI with button configuration
2. `main.py` - RPC methods for config management
3. `controller_listener.py` - Dynamic button detection
4. `README.md` - Updated documentation
5. `CLAUDE.md` - Updated technical docs
6. `STATUS.md` - Changelog and status
7. `dist/index.js` - Rebuilt frontend

## Files Created

1. `INSTALLATION.md` - Complete installation guide
2. `CHANGES.md` - This changelog
3. `button_config.json` - Created on first config change (not in repo)

## Technical Notes

**evdev button codes:**
- Linux input subsystem event codes
- Xbox 360 controller emulation on Steam Deck
- Codes may vary on other devices/controllers

**Configuration persistence:**
- JSON file in plugin directory
- Survives plugin reload/restart
- Does not survive plugin reinstallation

**Controller listener restart:**
- Old process killed via PID file
- New process spawned with fresh config
- State file reset to "0" (not pressed)
- Takes ~0.5s to restart

## Known Issues

1. **L5/R5 detection** - May not work on all Steam Deck configurations due to Steam interception
2. **Button codes** - Assumes Xbox 360 pad emulation; may need adjustment for other controllers
3. **No validation** - Selecting same button for both positions is allowed (won't work as combo)

## Recommendations

**For most users:**
- Use default L1+R1 combo
- Reliable, easy to press, good ergonomics

**If L1/R1 used by game:**
- Try L2+R2 (triggers)
- Try A+B (face buttons)
- Check game settings to rebind conflicting controls

**Avoid combinations:**
- L5+R5 (Steam intercepts)
- Same button for both positions
- D-Pad buttons (not implemented)
