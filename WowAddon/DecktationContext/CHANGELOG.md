# Decktation Context Addon - Changelog

## Version 1.1.0 (2026-02-07)

### Midnight Compatibility Update

**Added:**
- Full compatibility with WoW Midnight expansion (Interface 120000)
- Added `IconTexture` field to TOC for modern addon management
- Added `X-Category` and `X-Website` metadata fields

**Changed:**
- Updated Interface version from 110002 to 120000
- Replaced deprecated `GetRealZoneText()` with `C_Map.GetBestMapForUnit()` + `C_Map.GetMapInfo()`
- Replaced deprecated `GetSubZoneText()` with `GetMinimapZoneText()`
- Replaced `GetRaidRosterInfo()` with `UnitName("raidN")` for raid member enumeration
- Updated header comments to indicate Midnight compatibility

**Technical Details:**
- `GetZoneInfo()` helper function now uses modern C_Map API
- All zone lookups use map IDs instead of deprecated text functions
- Raid roster now iterates using UnitExists/UnitName pattern
- Maintains backward compatibility with The War Within (11.0+)

**Testing:**
- Tested zone detection with C_Map API
- Verified raid/party member tracking
- Confirmed SavedVariables export format unchanged

---

## Version 1.0.1 (Previous)

### Initial Release Features

**Core Functionality:**
- Automatic context tracking every 2 seconds
- Zone, subzone, boss, target tracking
- Party/raid member list
- Class and specialization detection
- SavedVariables export for JSON conversion

**Commands:**
- `/decktation` or `/dct` - Export context
- `/decktation errors` - Show error log
- `/decktation clearerrors` - Clear error log
- `/decktation help` - Show help

**Events:**
- PLAYER_LOGIN - Initialize addon
- PLAYER_ENTERING_WORLD - Update context
- ZONE_CHANGED* - Update zone info
- PLAYER_TARGET_CHANGED - Update target
- GROUP_ROSTER_UPDATE - Update party
- ENCOUNTER_START/END - Track bosses
- PLAYER_SPECIALIZATION_CHANGED - Update spec

**Data Exported:**
```lua
DecktationContextDB = {
    zone = "String",
    subzone = "String",
    boss = "String",
    target = "String",
    party = {"Player1", "Player2", ...},
    class = "CLASSTOKEN",
    spec = "SpecName",
    timestamp = number
}
```

---

## Upgrade Notes

### From 1.0.1 to 1.1.0

**No breaking changes** - SavedVariables format remains identical.

**What changed:**
- Internal API calls updated for Midnight
- TOC file updated to Interface 120000
- Zone detection now uses C_Map API

**What stayed the same:**
- All slash commands work identically
- SavedVariables structure unchanged
- JSON conversion scripts don't need updates
- All tracked data fields are the same

**Installation:**
- Simply replace the old addon folder with new version
- `/reload` in-game
- No configuration needed

### Backward Compatibility

The addon should still work on:
- WoW Midnight (12.0+) - Fully supported
- WoW The War Within (11.0+) - Fully supported
- Older expansions - May work but not officially supported

---

## Known Issues

None currently reported.

---

## Future Enhancements

Potential features for future versions:
- Mythic+ dungeon level tracking
- Delve difficulty tracking
- Covenant/Renown tracking (if applicable)
- Achievement progress for context
- More granular location data
- Custom keyword lists per zone

---

## API Migration Guide

For developers interested in the API changes:

### Zone Detection (Old vs New)

**Old (deprecated in Midnight):**
```lua
local zone = GetRealZoneText() or ""
local subzone = GetSubZoneText() or ""
```

**New (Midnight-compatible):**
```lua
local mapID = C_Map.GetBestMapForUnit("player")
local mapInfo = C_Map.GetMapInfo(mapID)
local zone = mapInfo and mapInfo.name or ""
local subzone = GetMinimapZoneText() or ""
```

### Raid Roster (Old vs New)

**Old (deprecated):**
```lua
for i = 1, GetNumGroupMembers() do
    local name = GetRaidRosterInfo(i)
    table.insert(party, name)
end
```

**New (modern API):**
```lua
for i = 1, GetNumGroupMembers() do
    local unitID = "raid" .. i
    if UnitExists(unitID) then
        local name = UnitName(unitID)
        if name and UnitIsPlayer(unitID) then
            table.insert(party, name)
        end
    end
end
```

### Benefits of New API

1. **Future-proof** - Won't be deprecated in upcoming expansions
2. **More accurate** - Better handling of cross-realm zones
3. **Consistent** - Uses same pattern as party member enumeration
4. **Map-aware** - Can extend to track map-specific data

---

## Credits

- Original addon: Decktation project
- Midnight update: 2026-02-07
- API migration based on Blizzard's addon development guidelines

---

## License

MIT License - Free to use and modify
