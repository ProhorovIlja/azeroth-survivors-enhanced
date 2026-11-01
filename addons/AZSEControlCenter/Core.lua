-- AZSE Control Center | WoW 1.12 / Lua 5.0, no native hooks.
-- Working options use only the supported AZS_* HUD and stored level-up API.
-- The game's stock addon API does not expose damage, health, gold or unlock cheats.
local panel, headline, description, statusLine, launchButton
local tabs, rows, actionButtons = {}, {}, {}
local activeTab = 1
local addonPage = 1
local initialized = false
local elapsed = 0
local HUD = {
  {"clock", "Clock / Next boss"},
  {"bosses", "Boss / Guardian bars"},
  {"tally", "Kills / Gold panel"},
  {"build", "Spells and jewelry"},
  {"banners", "Event announcements"},
  {"loot", "Boss loot notifications"},
  {"meter", "Built-in damage meter"},
  {"levels", "Stored level-up control"},
}
local CATEGORIES = {"Dashboard", "Interface", "Level-ups", "Builds", "Mods", "Cheats", "Settings"}
local function say(msg)
  if DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.AddMessage then
    DEFAULT_CHAT_FRAME:AddMessage("|cffffd166AZSE|r " .. msg)
  end
end
local function saved()
  if type(AZSCC_DB) ~= "table" then AZSCC_DB = {} end
  if type(AZSCC_DB.uiScale) ~= "number" then AZSCC_DB.uiScale = 1 end
  if type(AZSCC_DB.buttonVisible) ~= "boolean" then AZSCC_DB.buttonVisible = true end
  if type(AZSCC_DB.advancedInfo) ~= "boolean" then AZSCC_DB.advancedInfo = false end
  return AZSCC_DB
end
local function phase()
  if type(AZS_GetPhase) == "function" then
    local value = AZS_GetPhase()
    return value or "not available"
  end
  return "game API unavailable"
end
local function runSummary()
  local p = phase()
  if p == "game API unavailable" then return "AZS API: unavailable; check client and reload" end
  local label = "Phase: " .. p
  if type(AZS_GetRunTime) == "function" then
    local t = AZS_GetRunTime()
    if type(t) == "number" then
      label = label .. " | time: " .. math.floor(t / 60) .. ":" .. string.format("%02d", math.mod(math.floor(t), 60))
    end
  end
  if type(AZS_RUN) == "table" then
    if AZS_RUN.k then label = label .. " | kills: " .. tostring(AZS_RUN.k) end
    if AZS_RUN.lvl then label = label .. " | level: " .. tostring(AZS_RUN.lvl) end
  end
  return label
end
local function textButton(parent, key, label, width, height, x, y, callback)
  local b = CreateFrame("Button", "AZSCC" .. key, parent, "UIPanelButtonTemplate")
  b:SetWidth(width); b:SetHeight(height)
  b:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
  b:SetText(label)
  b:SetScript("OnClick", callback)
  return b
end
local function display(tabTitle, message)
  headline:SetText(tabTitle)
  description:SetText(message)
end
local function hideActions()
  for i = 1, table.getn(rows) do
    rows[i]:Hide()
  end
  for i = 1, table.getn(actionButtons) do actionButtons[i]:Hide() end
end
local refresh
local function action(index, label, onClick)
  local b = actionButtons[index]
  if not b then
    local offset = index - 1
    local x = 150 + math.mod(offset, 2) * 220
    local y = -393 - math.floor(offset / 2) * 32
    b = textButton(panel, "Action" .. index, label, 210, 26, x, y, function()
      if type(actionButtons[index].AZSCCClick) == "function" then actionButtons[index].AZSCCClick() end
    end)
    actionButtons[index] = b
  end
  b.AZSCCClick = onClick
  b:SetText(label)
  b:Show()
end
local function row(index, label, onClick)
  local b = rows[index]
  if not b then
    b = textButton(panel, "Row" .. index, label, 425, 27, 150, -148 - (index - 1) * 30, function()
      if type(rows[index].AZSCCClick) == "function" then rows[index].AZSCCClick() end
    end)
    rows[index] = b
  end
  b.AZSCCClick = onClick
  b:SetText(label)
  b:Show()
end
local function hudShown(key)
  if type(AZS_IsHudShown) == "function" then return AZS_IsHudShown(key) end
  return nil
end
local function toggleHud(key)
  if type(AZS_SetHudShown) ~= "function" or type(AZS_IsHudShown) ~= "function" then
    say("HUD API unavailable in this client")
    return
  end
  local current = AZS_IsHudShown(key)
  AZS_SetHudShown(key, not current)
  refresh()
end
local function storing()
  if type(AZS_IsStoringLevels) == "function" then return AZS_IsStoringLevels() end
  return nil
end
local function levelLabel()
  local s = storing()
  if s == nil then return "Store levels: not supported in this client" end
  return "Store level-ups: " .. (s and "ON" or "OFF")
end
local function quickHud(allShown)
  if type(AZS_SetHudShown) ~= "function" then say("HUD API unavailable"); return end
  for i = 1, table.getn(HUD) do
    AZS_SetHudShown(HUD[i][1], allShown)
  end
  refresh()
end
local function getAddonInfoSafe(index)
  if type(GetAddOnInfo) ~= "function" then return nil, nil, nil end
  local ok, name, title, info = pcall(GetAddOnInfo, index)
  if ok then return name, title, info end
  return nil, nil, nil
end
local function getAddonEnabledSafe(index)
  if type(GetAddOnEnableState) ~= "function" then return nil end
  local ok, value = pcall(GetAddOnEnableState, nil, index)
  if ok and type(value) == "number" then return value > 0 end
  return nil
end
local function addonCount()
  if type(GetNumAddOns) ~= "function" then return nil end
  local ok, value = pcall(GetNumAddOns)
  if ok and type(value) == "number" then return value end
  return nil
end
local function toggleAddon(index, name)
  if name == "AZSEControlCenter" then
    say("Cannot disable the active control panel from inside itself")
    return
  end
  local enabled = getAddonEnabledSafe(index)
  if enabled == nil or type(EnableAddOn) ~= "function" or type(DisableAddOn) ~= "function" then
    say("AddOn management unavailable; use Options > AddOns")
    return
  end
  local func = enabled and DisableAddOn or EnableAddOn
  local ok = pcall(func, index)
  if ok then
    if type(SaveAddOns) == "function" then pcall(SaveAddOns) end
    say("Changed " .. tostring(name) .. "; restart/reload game to apply")
  else
    say("AddOn change rejected; use Options > AddOns")
  end
  refresh()
end
local function meterSummary()
  if type(AZS_GetMeter) ~= "function" then return "Damage meter API unavailable" end
  local lines, total, dps = AZS_GetMeter()
  local info = "Damage: " .. math.floor(tonumber(total) or 0) .. " | DPS: " .. math.floor(tonumber(dps) or 0)
  if type(lines) == "table" and lines[1] then info = info .. " | Top: " .. tostring(lines[1].name or "?") end
  return info
end
local function makeMiniButton()
  launchButton = CreateFrame("Button", "AZSCCLauncher", UIParent, "UIPanelButtonTemplate")
  launchButton:SetWidth(44); launchButton:SetHeight(28)
  launchButton:SetPoint("CENTER", UIParent, "CENTER", 360, -155)
  launchButton:SetFrameStrata("HIGH")
  launchButton:SetText("AZSE")
  launchButton:SetMovable(true); launchButton:EnableMouse(true)
  launchButton:RegisterForDrag("LeftButton")
  launchButton:SetScript("OnDragStart", function() this:StartMoving() end)
  launchButton:SetScript("OnDragStop", function() this:StopMovingOrSizing() end)
  launchButton:SetScript("OnClick", function()
    if panel:IsShown() then panel:Hide() else refresh(); panel:Show() end
  end)
  if not saved().buttonVisible then launchButton:Hide() end
end
refresh = function()
  if not panel then return end
  hideActions()
  statusLine:SetText(runSummary())
  local tab = CATEGORIES[activeTab]
  if tab == "Dashboard" then
    display("AZSE Control Center | Dashboard",
      "This menu runs INSIDE Azeroth Survivors. Safe run telemetry and real game settings are available now.\n" ..
      meterSummary() .. "\n\n" ..
      "Experimental build suggestions and cheat functions are separate from verified game controls.\n" ..
      "Original game version: Windows 0.137.0 (runtime compatibility NOT verified).")
    action(1, "Show stock HUD", function() quickHud(true) end)
    action(2, "Hide stock HUD", function() quickHud(false) end)
    action(3, "Refresh status", function() refresh() end)
  elseif tab == "Interface" then
    display("Interface | Real HUD toggles",
      "These buttons use AZS_SetHudShown() and affect the game's OWN HUD.\n" ..
      "Other installed addons may still draw separate overlapping panels.")
    for i = 1, table.getn(HUD) do
      local data = HUD[i]
      local v = hudShown(data[1])
      local s = v == nil and "UNKNOWN" or (v and "ON" or "OFF")
      row(i, "[" .. s .. "]  " .. data[2], function() toggleHud(data[1]) end)
    end
    action(1, "Show ALL HUD parts", function() quickHud(true) end)
    action(2, "Hide ALL HUD parts", function() quickHud(false) end)
  elseif tab == "Level-ups" then
    local count = nil
    if type(AZS_GetStoredLevels) == "function" then count = AZS_GetStoredLevels() end
    display("Run | Level-up queue",
      "Toggle how the game offers NEW level-ups.\n" ..
      "Stored cards: " .. tostring(count or 0) .. "\n" ..
      "This does NOT create levels, items, gold or talent points.\n" ..
      "Actions require the game's supported API and an active run.")
    row(1, levelLabel(), function()
      local old = storing()
      if old == nil or type(AZS_SetStoringLevels) ~= "function" then
        say("Storing API unavailable")
      else AZS_SetStoringLevels(not old) end
      refresh()
    end)
    row(2, "Open stored level-up cards", function()
      if type(AZS_OpenStoredLevels) == "function" then AZS_OpenStoredLevels() else say("No stored-level API") end
      refresh()
    end)
  elseif tab == "Builds" then
    display("Builds | Research", "Your client contains both historical and newer Demonology labels.\n" ..
      "Do not import an older 51-point allocation blindly into 0.137.0.\n" ..
      "No verified tree graph or automatic talent allocation is available yet.\n" ..
      "Use /azse to open the separate read-only advisor, if installed.")
    row(1, "Show actual current run phase", function() say(runSummary()) end)
    row(2, "Show damage summary", function() say(meterSummary()) end)
  elseif tab == "Mods" then
    local count = addonCount()
    if count == nil then
      display("Mods | Existing AddOns", "This client does not expose the stock addon manager API.\n" ..
        "Open the game's Options > AddOns menu to enable/disable mods.\n" ..
        "Install or uninstall packages only while the game is closed.")
    else
      display("Mods | Installed addons", "Found " .. count .. " AddOns. Click to toggle for NEXT launch.\n" ..
        "If a function is unavailable, this menu stays read-only.\n" ..
        "Only addons already installed by the player are listed.\n" ..
        "No ZIP download, installation or DLL injection occurs here.")
      local pages = math.max(1, math.ceil(count / 6))
      if addonPage > pages then addonPage = pages end
      for slot = 1, 6 do
        local index = (addonPage - 1) * 6 + slot
        if index <= count then
          local name, title = getAddonInfoSafe(index)
          if name then
            local enabled = getAddonEnabledSafe(index)
            local state = enabled == nil and "?" or (enabled and "ON" or "OFF")
            local displayName = tostring(title or name)
            if string.len(displayName) > 36 then displayName = string.sub(displayName, 1, 35) .. "..." end
            row(slot, "[" .. state .. "] " .. displayName, function() toggleAddon(index, name) end)
          end
        end
      end
      action(1, "Previous page", function() addonPage = math.max(1, addonPage - 1); refresh() end)
      action(2, "Next page " .. addonPage .. "/" .. pages, function() addonPage = math.min(pages, addonPage + 1); refresh() end)
    end
  elseif tab == "Cheats" then
    display("Cheats | Native module required", "God Mode, one-hit kill, gold, rerolls, levels and permanent unlocks\n" ..
      "cannot be changed through the documented WoW 1.12 Lua addon API.\n\n" ..
      "STATUS: NOT CONNECTED. No effects are simulated by this screen.\n" ..
      "Old external trainers target 0.119/0.127, NOT your 0.137.0.\n" ..
      "Single-player save editing currently requires a separately backed-up save.")
    row(1, "[Unavailable] God Mode / infinite health", function() say("Not available through Lua addon API. No cheat applied.") end)
    row(2, "[Unavailable] One-hit kill / damage multiplier", function() say("No native cheat backend connected.") end)
    row(3, "[Unavailable] Gold / XP / rerolls", function() say("No resource-edit API; no values changed.") end)
    row(4, "[Unavailable] Unlock everything", function() say("Use a backed-up save export in an isolated single-player test.") end)
    row(5, "[Unavailable] Change game speed", function() say("Requires separately tested speed addon / native component.") end)
  elseif tab == "Settings" then
    display("Settings | AZSE menu itself",
      "Only this panel's preferences are stored in AZSCC_DB.\n" ..
      "HUD controls are the game's own saved settings.\n" ..
      "Drag the AZSE button or this window with the left mouse button.\n" ..
      "Slash command: /azcc or /azmenu.")
    row(1, "AZSE launcher: " .. (saved().buttonVisible and "VISIBLE" or "HIDDEN"), function()
      local data = saved(); data.buttonVisible = not data.buttonVisible
      if data.buttonVisible then launchButton:Show() else launchButton:Hide() end
      refresh()
    end)
    row(2, "Menu scale: " .. tostring(saved().uiScale), function()
      local v = saved().uiScale + 0.1
      if v > 1.21 then v = 0.8 end
      saved().uiScale = math.floor(v * 10 + 0.5) / 10
      panel:SetScale(saved().uiScale)
      refresh()
    end)
    row(3, "Reset AZSE panel preferences", function()
      AZSCC_DB = {uiScale = 1, buttonVisible = true}
      panel:SetScale(1); launchButton:Show()
      refresh()
    end)
  end
end
local function showPanel()
  if not initialized then return end
  if panel:IsShown() then panel:Hide() else refresh(); panel:Show() end
end
local function create()
  if initialized then return end
  panel = CreateFrame("Frame", "AZSCCPanel", UIParent)
  panel:SetWidth(600); panel:SetHeight(465)
  panel:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
  panel:SetFrameStrata("DIALOG")
  panel:SetMovable(true); panel:EnableMouse(true)
  panel:RegisterForDrag("LeftButton")
  panel:SetScript("OnDragStart", function() this:StartMoving() end)
  panel:SetScript("OnDragStop", function() this:StopMovingOrSizing() end)
  local bg = panel:CreateTexture(nil, "BACKGROUND")
  bg:SetAllPoints(panel); bg:SetTexture(0.045, 0.07, 0.12, 0.98)
  local border = panel:CreateTexture(nil, "BORDER")
  border:SetPoint("TOPLEFT", panel, "TOPLEFT", 4, -4)
  border:SetWidth(592); border:SetHeight(33)
  border:SetTexture(0.17, 0.13, 0.05, 0.94)
  headline = panel:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
  headline:SetPoint("TOPLEFT", panel, "TOPLEFT", 16, -14)
  headline:SetWidth(500); headline:SetJustifyH("LEFT")
  local close = textButton(panel, "Close", "X", 34, 25, 551, -8, function() panel:Hide() end)
  description = panel:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
  description:SetPoint("TOPLEFT", panel, "TOPLEFT", 153, -55)
  description:SetWidth(423); description:SetHeight(90)
  description:SetJustifyH("LEFT"); description:SetJustifyV("TOP")
  statusLine = panel:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
  statusLine:SetPoint("BOTTOMLEFT", panel, "BOTTOMLEFT", 15, 12)
  statusLine:SetWidth(570); statusLine:SetJustifyH("LEFT")
  for i = 1, table.getn(CATEGORIES) do
    local index = i
    local tab = textButton(panel, "Tab" .. i, CATEGORIES[i], 132, 37, 10, -60 - (i - 1) * 43, function()
      activeTab = index
      refresh()
    end)
    tabs[i] = tab
  end
  panel:SetScale(saved().uiScale)
  panel:Hide()
  initialized = true
  makeMiniButton()
end
local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("VARIABLES_LOADED")
eventFrame:SetScript("OnEvent", function()
  if event == "VARIABLES_LOADED" then create() end
end)
eventFrame:SetScript("OnUpdate", function()
  elapsed = elapsed + (arg1 or 0)
  if elapsed > 2 then
    elapsed = 0
    if panel and panel:IsShown() and statusLine then statusLine:SetText(runSummary()) end
  end
end)
local function slash(msg)
  local value = string.lower(msg or "")
  if value == "reset" then
    quickHud(true); say("Restored stock HUD parts")
  elseif value == "help" then
    say("/azcc or /azmenu: in-game panel; /azcc reset: show stock HUD; /azcc help")
  else
    if not initialized then create() end
    showPanel()
  end
end
SLASH_AZSCC1 = "/azcc"
SLASH_AZSCC2 = "/azmenu"
SlashCmdList["AZSCC"] = slash
