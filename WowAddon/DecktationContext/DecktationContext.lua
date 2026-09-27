--[[
    Decktation Context - WoW Context Exporter
    Tracks game state and exports to SavedVariables for voice transcription

    Compatible with WoW Midnight, The War Within, Classic Era, and WoW Forever
    Uses modern C_Map/C_Container/C_QuestLog APIs with robust Classic fallbacks
]]

local AddonName, Addon = ...

-- Saved variables
DecktationContextDB = DecktationContextDB or {}
DecktationErrorLog = DecktationErrorLog or {}

-- Local context cache
local Context = {
    player = "",
    guild = "",
    zone = "",
    subzone = "",
    boss = "",
    target = "",
    party = {},
    class = "",
    spec = "",
    inventory = {},
    quests = {},
    spells = {},
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

-- Get zone information using modern C_Map API with fallback to Classic APIs
local function GetZoneInfo()
    local zone = ""
    local subzone = ""

    -- Try modern C_Map API first (Retail / Midnight / TWW)
    if C_Map and C_Map.GetBestMapForUnit and C_Map.GetMapInfo then
        local mapID = C_Map.GetBestMapForUnit("player")
        if mapID then
            local mapInfo = C_Map.GetMapInfo(mapID)
            if mapInfo and mapInfo.name and mapInfo.name ~= "" then
                zone = mapInfo.name
            end
        end
    end

    -- Fallback to Classic / legacy zone APIs if C_Map returned nil or empty
    if not zone or zone == "" then
        if GetRealZoneText then
            zone = GetRealZoneText() or ""
        end
        if (not zone or zone == "") and GetZoneText then
            zone = GetZoneText() or ""
        end
    end

    -- Get subzone from minimap or subzone text
    if GetMinimapZoneText then
        subzone = GetMinimapZoneText() or ""
    end
    if (not subzone or subzone == "") and GetSubZoneText then
        subzone = GetSubZoneText() or ""
    end

    return zone or "", subzone or ""
end

-- Get specialization (Retail) or talent tree with most points (Classic)
local function GetPlayerSpec()
    if GetSpecialization then
        local specIndex = GetSpecialization()
        if specIndex then
            local _, specName = GetSpecializationInfo(specIndex)
            return specName or ""
        end
    elseif GetNumTalentTabs and GetTalentTabInfo then
        local maxPoints = 0
        local activeSpec = ""
        for tabIndex = 1, GetNumTalentTabs() do
            local name, _, pointsSpent = GetTalentTabInfo(tabIndex)
            if pointsSpent and pointsSpent > maxPoints then
                maxPoints = pointsSpent
                activeSpec = name or ""
            end
        end
        return activeSpec
    end
    return ""
end

-- Get inventory item names from all bags
local function GetInventoryItems()
    local items = {}
    local seen = {}
    local numBags = NUM_BAG_SLOTS or 4

    for bag = 0, numBags do
        local numSlots = 0
        if C_Container and C_Container.GetContainerNumSlots then
            numSlots = C_Container.GetContainerNumSlots(bag) or 0
        elseif GetContainerNumSlots then
            numSlots = GetContainerNumSlots(bag) or 0
        end

        for slot = 1, numSlots do
            local itemLink = nil
            if C_Container and C_Container.GetContainerItemLink then
                itemLink = C_Container.GetContainerItemLink(bag, slot)
            elseif GetContainerItemLink then
                itemLink = GetContainerItemLink(bag, slot)
            end

            if itemLink then
                local itemName = itemLink:match("%[(.-)%]")
                if itemName and itemName ~= "" and not seen[itemName] then
                    seen[itemName] = true
                    table.insert(items, itemName)
                end
            end
        end
    end
    return items
end

-- Get active quest titles from quest log
local function GetActiveQuests()
    local quests = {}
    local seen = {}

    if C_QuestLog and C_QuestLog.GetNumQuestLogEntries and C_QuestLog.GetInfo then
        local numEntries = C_QuestLog.GetNumQuestLogEntries() or 0
        for i = 1, numEntries do
            local info = C_QuestLog.GetInfo(i)
            if info and not info.isHeader and info.title and info.title ~= "" and not seen[info.title] then
                seen[info.title] = true
                table.insert(quests, info.title)
            end
        end
    elseif GetNumQuestLogEntries and GetQuestLogTitle then
        local numEntries = GetNumQuestLogEntries() or 0
        for i = 1, numEntries do
            local title, level, suggestedGroup, isHeader = GetQuestLogTitle(i)
            if title and not isHeader and title ~= "" and not seen[title] then
                seen[title] = true
                table.insert(quests, title)
            end
        end
    end
    return quests
end

-- Get player class abilities / spells
local function GetPlayerSpells()
    local spells = {}
    local seen = {}

    if C_SpellBook and C_SpellBook.GetSpellBookItemName and C_SpellBook.GetNumSpellBookSkillLines and C_SpellBook.GetSpellBookSkillLineInfo then
        local numTabs = C_SpellBook.GetNumSpellBookSkillLines() or 0
        for tab = 1, numTabs do
            local skillLineInfo = C_SpellBook.GetSpellBookSkillLineInfo(tab)
            if skillLineInfo then
                local offset = skillLineInfo.itemIndexOffset or 0
                local numSlots = skillLineInfo.numSpellBookItems or 0
                for i = 1, numSlots do
                    local bank = (Enum and Enum.SpellBookSpellBank and Enum.SpellBookSpellBank.Player) or 0
                    local spellName = C_SpellBook.GetSpellBookItemName(offset + i, bank)
                    if spellName and spellName ~= "" and not seen[spellName] then
                        seen[spellName] = true
                        table.insert(spells, spellName)
                    end
                end
            end
        end
    elseif GetNumSpellTabs and GetSpellTabInfo and GetSpellBookItemName then
        local numTabs = GetNumSpellTabs() or 0
        for tab = 1, numTabs do
            local name, texture, offset, numSlotSpells = GetSpellTabInfo(tab)
            if offset and numSlotSpells then
                for i = 1, numSlotSpells do
                    local spellName = GetSpellBookItemName(offset + i, BOOKTYPE_SPELL or "spell")
                    if spellName and spellName ~= "" and not seen[spellName] then
                        seen[spellName] = true
                        table.insert(spells, spellName)
                    end
                end
            end
        end
    end
    return spells
end

-- Update current context
function UpdateContext()
    local success, err = pcall(function()
        -- Character and Guild info
        local playerName = UnitName("player") or ""
        Context.player = playerName
        if GetGuildInfo then
            local guildName = GetGuildInfo("player")
            Context.guild = guildName or ""
        else
            Context.guild = ""
        end

        -- Zone information
        Context.zone, Context.subzone = GetZoneInfo()

        -- Target information
        if UnitExists("target") then
            local targetName = UnitName("target") or ""
            local targetClass = UnitClassification("target") or ""

            if targetClass == "worldboss" or targetClass == "rareelite" or targetClass == "rare" or targetClass == "elite" then
                Context.boss = targetName
            else
                Context.boss = ""
            end

            Context.target = targetName
        else
            Context.target = ""
        end

        -- Party/Raid members
        Context.party = {}
        if IsInRaid() then
            local numMembers = GetNumGroupMembers() or 0
            for i = 1, numMembers do
                local unitID = "raid" .. i
                if UnitExists(unitID) then
                    local name = UnitName(unitID)
                    if name and name ~= "" and UnitIsPlayer(unitID) then
                        table.insert(Context.party, name)
                    end
                end
            end
        elseif IsInGroup() then
            if playerName ~= "" then
                table.insert(Context.party, playerName)
            end
            local numMembers = GetNumSubgroupMembers() or 0
            for i = 1, numMembers do
                local unitID = "party" .. i
                if UnitExists(unitID) then
                    local name = UnitName(unitID)
                    if name and name ~= "" and UnitIsPlayer(unitID) then
                        table.insert(Context.party, name)
                    end
                end
            end
        else
            if playerName ~= "" then
                table.insert(Context.party, playerName)
            end
        end

        -- Class and Specialization
        local localizedClass, classToken = UnitClass("player")
        Context.class = classToken or ""
        Context.spec = GetPlayerSpec()

        -- Inventory items, Quests, and Spells
        Context.inventory = GetInventoryItems()
        Context.quests = GetActiveQuests()
        Context.spells = GetPlayerSpells()

        Context.lastUpdate = time()
    end)

    if not success then
        LogError("Failed to update context", err)
    end
end

-- Save context to SavedVariables
function SaveContext()
    DecktationContextDB = {
        player = Context.player,
        guild = Context.guild,
        zone = Context.zone,
        subzone = Context.subzone,
        boss = Context.boss,
        target = Context.target,
        party = Context.party,
        class = Context.class,
        spec = Context.spec,
        inventory = Context.inventory,
        quests = Context.quests,
        spells = Context.spells,
        timestamp = time()
    }
end

-- Export context to chat (for debugging)
local function ExportToChat()
    UpdateContext()
    SaveContext()

    local function safePrint(label, value)
        print("  " .. label .. ": " .. tostring(value or ""))
    end

    print("|cff00ff00Decktation Context Exported:|r")
    safePrint("Player", Context.player)
    if Context.guild and Context.guild ~= "" then
        safePrint("Guild", Context.guild)
    end
    safePrint("Zone", Context.zone)
    safePrint("Subzone", Context.subzone)
    safePrint("Boss", Context.boss)
    safePrint("Target", Context.target)

    local partyStr = ""
    if Context.party and #Context.party > 0 then
        partyStr = table.concat(Context.party, ", ")
    end
    safePrint("Party", partyStr)

    safePrint("Class", Context.class)
    safePrint("Spec", Context.spec)
    safePrint("Inventory Items", #Context.inventory)
    safePrint("Active Quests", #Context.quests)
    safePrint("Known Spells", #Context.spells)
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

-- Initialize addon
local function Initialize()
    print("|cff00ff00Decktation Context|r: Loaded! Use /decktation to export context.")
    UpdateContext()
    SaveContext()
end

-- Slash command handler
SLASH_DECKTATION1 = "/decktation"
SLASH_DECKTATION2 = "/dct"
SlashCmdList["DECKTATION"] = function(msg)
    pcall(function()
        local cmd = (msg or ""):match("^%s*(.-)%s*$"):lower()

        if cmd == "" or cmd == "export" then
            ExportToChat()
        elseif cmd == "errors" or cmd == "log" then
            ShowErrorLog()
        elseif cmd == "clearerrors" or cmd == "clearlog" then
            ClearErrorLog()
        elseif cmd == "help" then
            print("|cff00ff00Decktation Context Commands:|r")
            print("  /decktation or /dct - Export current context")
            print("  /decktation errors - Show error log")
            print("  /decktation clearerrors - Clear error log")
            print("  /decktation help - Show this help")
        else
            print("|cffff0000Unknown command. Use /decktation help for commands.|r")
        end
    end)
end

-- Update frame (periodic in-memory refresh)
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
EventFrame:RegisterEvent("PLAYER_TALENT_UPDATE")
EventFrame:RegisterEvent("CHARACTER_POINTS_CHANGED")
EventFrame:RegisterEvent("BAG_UPDATE_DELAYED")
EventFrame:RegisterEvent("QUEST_LOG_UPDATE")
EventFrame:RegisterEvent("QUEST_ACCEPTED")
EventFrame:RegisterEvent("QUEST_REMOVED")
EventFrame:RegisterEvent("SPELLS_CHANGED")
EventFrame:RegisterEvent("PLAYER_GUILD_UPDATE")
EventFrame:RegisterEvent("PLAYER_LOGOUT")

EventFrame:SetScript("OnEvent", function(self, event, ...)
    pcall(function()
        if event == "PLAYER_LOGIN" then
            Initialize()
        elseif event == "ENCOUNTER_START" then
            local encounterID, encounterName = ...
            Context.boss = encounterName or ""
            SaveContext()
        elseif event == "ENCOUNTER_END" then
            Context.boss = ""
            SaveContext()
        else
            UpdateContext()
            SaveContext()
        end
    end)
end)
