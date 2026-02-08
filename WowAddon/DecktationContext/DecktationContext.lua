--[[
    Decktation Context - WoW Context Exporter
    Tracks game state and exports to SavedVariables for voice transcription

    Compatible with WoW Midnight (12.0+) and The War Within (11.0+)
    Uses modern C_Map API and updated group functions
]]

local AddonName, Addon = ...

-- Saved variables
DecktationContextDB = DecktationContextDB or {}
DecktationErrorLog = DecktationErrorLog or {}

-- Local context cache
local Context = {
    zone = "",
    subzone = "",
    boss = "",
    target = "",
    party = {},
    class = "",
    spec = "",
    lastUpdate = 0
}

-- Error logging
local function LogError(message, errorDetail)
    local errorEntry = {
        timestamp = date("%Y-%m-%d %H:%M:%S"),
        message = tostring(message),
        detail = tostring(errorDetail or "")
    }

    -- Keep only last 20 errors
    table.insert(DecktationErrorLog, 1, errorEntry)
    if #DecktationErrorLog > 20 then
        table.remove(DecktationErrorLog)
    end

    -- Also print to chat
    print("|cffff0000Decktation Error:|r " .. message)
    if errorDetail then
        print("  Details: " .. tostring(errorDetail))
    end
end

-- Update interval (seconds)
local UPDATE_INTERVAL = 2

-- Initialize addon
local function Initialize()
    print("|cff00ff00Decktation Context|r: Loaded! Use /decktation to export context.")

    -- Update context immediately (includes class detection)
    UpdateContext()
    SaveContext()
end

-- Get zone information using modern C_Map API (Midnight-compatible)
local function GetZoneInfo()
    local mapID = C_Map.GetBestMapForUnit("player")
    if not mapID then
        return "", ""
    end

    local mapInfo = C_Map.GetMapInfo(mapID)
    local zone = mapInfo and mapInfo.name or ""

    -- Get subzone from minimap text (still works in Midnight)
    local subzone = GetMinimapZoneText() or ""

    return zone, subzone
end

-- Update current context
function UpdateContext()
    -- Wrap in pcall to prevent crashes
    local success, err = pcall(function()
        -- Zone information (using modern API)
        Context.zone, Context.subzone = GetZoneInfo()

        -- Target information
        if UnitExists("target") then
            local targetName = UnitName("target") or ""
            local targetClass = UnitClassification("target") or ""

            -- If it's a boss or rare, it's important
            if targetClass == "worldboss" or targetClass == "rareelite" or targetClass == "rare" or targetClass == "elite" then
                Context.boss = targetName
            else
                Context.boss = ""
            end

            Context.target = targetName
        else
            Context.target = ""
            -- Keep boss for a bit even if not targeted
        end

        -- Party/Raid members - clear first to avoid stale data
        Context.party = {}

        if IsInRaid() then
            local numMembers = GetNumGroupMembers() or 0
            for i = 1, numMembers do
                -- Use UnitName for modern API compatibility
                local unitID = "raid" .. i
                if UnitExists(unitID) then
                    local name = UnitName(unitID)
                    if name and name ~= "" and UnitIsPlayer(unitID) then
                        table.insert(Context.party, name)
                    end
                end
            end
        elseif IsInGroup() then
            -- Add player first
            local playerName = UnitName("player")
            if playerName and playerName ~= "" then
                table.insert(Context.party, playerName)
            end

            -- Add party members
            local numMembers = GetNumSubgroupMembers() or 0
            for i = 1, numMembers do
                local unitID = "party" .. i
                if UnitExists(unitID) then
                    local name = UnitName(unitID)
                    -- Only add real players, not NPCs
                    if name and name ~= "" and UnitIsPlayer(unitID) then
                        table.insert(Context.party, name)
                    end
                end
            end
        else
            -- Solo - just add player
            local playerName = UnitName("player")
            if playerName and playerName ~= "" then
                table.insert(Context.party, playerName)
            end
        end

        -- Get player class (English token, e.g., "SHAMAN")
        local localizedClass, classToken = UnitClass("player")
        Context.class = classToken or ""

        -- Get specialization
        local specIndex = GetSpecialization()
        if specIndex then
            local _, specName = GetSpecializationInfo(specIndex)
            Context.spec = specName or ""
        else
            Context.spec = ""
        end

        Context.lastUpdate = time()
    end)

    if not success then
        LogError("Failed to update context", err)
    end
end

-- Save context to SavedVariables
function SaveContext()
    DecktationContextDB = {
        zone = Context.zone,
        subzone = Context.subzone,
        boss = Context.boss,
        target = Context.target,
        party = Context.party,
        class = Context.class,
        spec = Context.spec,
        timestamp = time()
    }
end

-- Export context to chat (for debugging)
local function ExportToChat()
    UpdateContext()
    SaveContext()

    -- Safe print with nil checks
    local function safePrint(label, value)
        print("  " .. label .. ": " .. tostring(value or ""))
    end

    print("|cff00ff00Decktation Context Exported:|r")
    safePrint("Zone", Context.zone)
    safePrint("Subzone", Context.subzone)
    safePrint("Boss", Context.boss)
    safePrint("Target", Context.target)

    -- Safe party list
    local partyStr = ""
    if Context.party and #Context.party > 0 then
        partyStr = table.concat(Context.party, ", ")
    end
    safePrint("Party", partyStr)

    safePrint("Class", Context.class)
    safePrint("Spec", Context.spec)

    -- Also print JSON format for easy copy (with error handling)
    local success, json = pcall(function()
        local partyJSON = ""
        if Context.party and #Context.party > 0 then
            partyJSON = '"' .. table.concat(Context.party, '","') .. '"'
        end

        return string.format(
            '{"zone":"%s","subzone":"%s","boss":"%s","target":"%s","party":[%s],"class":"%s","spec":"%s"}',
            tostring(Context.zone or ""),
            tostring(Context.subzone or ""),
            tostring(Context.boss or ""),
            tostring(Context.target or ""),
            partyJSON,
            tostring(Context.class or ""),
            tostring(Context.spec or "")
        )
    end)

    if success then
        print("JSON: " .. json)
    else
        print("|cffff0000Error generating JSON|r")
    end
end

-- Show error log
local function ShowErrorLog()
    if not DecktationErrorLog or #DecktationErrorLog == 0 then
        print("|cff00ff00Decktation:|r No errors logged")
        return
    end

    print("|cff00ff00Decktation Error Log:|r (" .. #DecktationErrorLog .. " errors)")
    for i, error in ipairs(DecktationErrorLog) do
        print(string.format("  [%s] %s", error.timestamp or "unknown", error.message or ""))
        if error.detail and error.detail ~= "" then
            print("    " .. error.detail)
        end
        if i >= 10 then
            print("  ... (showing first 10 of " .. #DecktationErrorLog .. " errors)")
            break
        end
    end
end

-- Clear error log
local function ClearErrorLog()
    DecktationErrorLog = {}
    print("|cff00ff00Decktation:|r Error log cleared")
end

-- Slash command handler
SLASH_DECKTATION1 = "/decktation"
SLASH_DECKTATION2 = "/dct"
SlashCmdList["DECKTATION"] = function(msg)
    msg = msg:lower():trim()

    if msg == "" or msg == "export" then
        ExportToChat()
    elseif msg == "errors" or msg == "log" then
        ShowErrorLog()
    elseif msg == "clearerrors" or msg == "clearlog" then
        ClearErrorLog()
    elseif msg == "help" then
        print("|cff00ff00Decktation Context Commands:|r")
        print("  /decktation or /dct - Export current context")
        print("  /decktation errors - Show error log")
        print("  /decktation clearerrors - Clear error log")
        print("  /decktation help - Show this help")
    else
        print("|cffff0000Unknown command. Use /decktation help for commands.|r")
    end
end

-- Update frame
local UpdateFrame = CreateFrame("Frame")
UpdateFrame:SetScript("OnUpdate", function(self, elapsed)
    self.timeSinceLastUpdate = (self.timeSinceLastUpdate or 0) + elapsed

    if self.timeSinceLastUpdate >= UPDATE_INTERVAL then
        UpdateContext()
        SaveContext()
        self.timeSinceLastUpdate = 0
    end
end)

-- Event handlers
local EventFrame = CreateFrame("Frame")

EventFrame:RegisterEvent("PLAYER_LOGIN")
EventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
EventFrame:RegisterEvent("ZONE_CHANGED")
EventFrame:RegisterEvent("ZONE_CHANGED_NEW_AREA")
EventFrame:RegisterEvent("PLAYER_TARGET_CHANGED")
EventFrame:RegisterEvent("GROUP_ROSTER_UPDATE")
EventFrame:RegisterEvent("ENCOUNTER_START")
EventFrame:RegisterEvent("ENCOUNTER_END")
EventFrame:RegisterEvent("PLAYER_SPECIALIZATION_CHANGED")

EventFrame:SetScript("OnEvent", function(self, event, ...)
    if event == "PLAYER_LOGIN" then
        Initialize()
    elseif event == "PLAYER_ENTERING_WORLD" then
        UpdateContext()
        SaveContext()
    elseif event == "ZONE_CHANGED" or event == "ZONE_CHANGED_NEW_AREA" then
        UpdateContext()
        SaveContext()
    elseif event == "PLAYER_TARGET_CHANGED" then
        UpdateContext()
        SaveContext()
    elseif event == "GROUP_ROSTER_UPDATE" then
        UpdateContext()
        SaveContext()
    elseif event == "ENCOUNTER_START" then
        local encounterID, encounterName = ...
        Context.boss = encounterName or ""
        SaveContext()
    elseif event == "ENCOUNTER_END" then
        Context.boss = ""
        SaveContext()
    elseif event == "PLAYER_SPECIALIZATION_CHANGED" then
        local specIndex = GetSpecialization()
        if specIndex then
            local _, specName = GetSpecializationInfo(specIndex)
            Context.spec = specName or ""
        end
        SaveContext()
    end
end)

-- Force save on logout
EventFrame:RegisterEvent("PLAYER_LOGOUT")
EventFrame:SetScript("OnEvent", function(self, event)
    if event == "PLAYER_LOGOUT" then
        SaveContext()
    end
end)
