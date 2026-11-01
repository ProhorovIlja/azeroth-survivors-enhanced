-- AZS Enhanced Advisor: read-only Lua 1.12; in-game verification pending.
local position = 1
local selectedClass = nil
local frame, title, body, footer
local shown = {}

local function say(msg)
  if DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.AddMessage then
    DEFAULT_CHAT_FRAME:AddMessage("|cffffd066AZSE|r " .. msg)
  end
end

local function db()
  if type(AZSE_DB) ~= "table" then AZSE_DB = {} end
  if not AZSE_DB.class then AZSE_DB.class = "warlock" end
  return AZSE_DB
end

local function classKey()
  return selectedClass or db().class or "warlock"
end

local function refreshFiltered()
  shown = {}
  if type(AZSE_PRESETS) ~= "table" then return end
  for i = 1, table.getn(AZSE_PRESETS) do
    if AZSE_PRESETS[i].class == classKey() then
      table.insert(shown, AZSE_PRESETS[i])
    end
  end
  if position < 1 then position = table.getn(shown) end
  if position > table.getn(shown) or table.getn(shown) == 0 then position = 1 end
end

local function selected()
  refreshFiltered()
  local p = shown[position]
  if not p then return "No presets for " .. classKey(), "Use /azse class <class>", "Advisory only" end
  return p.name .. " [" .. p.spec .. "]",
    "Spells: " .. p.spells .. "\nPriorities: " .. p.passives .. "\n" .. p.note,
    "NOT VERIFIED | " .. p.baseline .. " | " .. position .. "/" .. table.getn(shown)
end

local function render()
  if not frame then return end
  local a, b, c = selected()
  title:SetText(a); body:SetText(b); footer:SetText(c)
end

local function printSelected()
  local a, b, c = selected()
  say(a); say(b); say(c)
end

local function panel()
  if frame then return end
  frame = CreateFrame("Frame", "AZSEAdvisorPanel", UIParent)
  frame:SetWidth(460); frame:SetHeight(190)
  frame:SetPoint("CENTER", UIParent, "CENTER", 0, 120)
  frame:SetFrameStrata("DIALOG")
  frame:EnableMouse(true); frame:SetMovable(true)
  frame:RegisterForDrag("LeftButton")
  frame:SetScript("OnDragStart", function() this:StartMoving() end)
  frame:SetScript("OnDragStop", function() this:StopMovingOrSizing() end)
  local background = frame:CreateTexture(nil, "BACKGROUND")
  background:SetAllPoints(frame); background:SetTexture(0.06, 0.07, 0.09, 0.93)
  title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  title:SetPoint("TOPLEFT", frame, "TOPLEFT", 16, -14)
  title:SetWidth(430); title:SetJustifyH("LEFT")
  body = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
  body:SetPoint("TOPLEFT", frame, "TOPLEFT", 16, -42)
  body:SetWidth(428); body:SetHeight(94)
  body:SetJustifyH("LEFT"); body:SetJustifyV("TOP")
  footer = frame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
  footer:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 16, 39)
  footer:SetWidth(425); footer:SetJustifyH("LEFT")
  local function addButton(id, label, x, callback)
    local b = CreateFrame("Button", id, frame, "UIPanelButtonTemplate")
    b:SetWidth(75); b:SetHeight(22)
    b:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", x, 9)
    b:SetText(label)
    b:SetScript("OnClick", callback)
  end
  addButton("AZSEPrev", "Previous", 14, function() position = position - 1; render() end)
  addButton("AZSENext", "Next", 97, function() position = position + 1; render() end)
  addButton("AZSEClose", "Close", 367, function() frame:Hide() end)
  frame:Hide()
end

local function command(message)
  message = string.lower(message or "")
  local _, _, verb, rest = string.find(message, "^(%S+)%s*(.-)%s*$")
  if not verb or verb == "" or verb == "toggle" then
    panel()
    if frame:IsShown() then frame:Hide() else render(); frame:Show() end
  elseif verb == "hide" then
    if frame then frame:Hide() end
  elseif verb == "list" then
    refreshFiltered()
    say("Presets for " .. classKey() .. ": " .. table.getn(shown))
    for i = 1, math.min(table.getn(shown), 20) do say(shown[i].id) end
  elseif verb == "class" then
    local accepted = {warrior=1,paladin=1,hunter=1,rogue=1,priest=1,shaman=1,mage=1,warlock=1,druid=1}
    if rest and accepted[rest] then
      selectedClass = rest; db().class = rest; position = 1; render(); say("Class: " .. rest)
    else
      say("Use /azse class warlock (or another class)")
    end
  elseif verb == "show" then
    for i = 1, table.getn(AZSE_PRESETS or {}) do
      if AZSE_PRESETS[i].id == rest then
        selectedClass = AZSE_PRESETS[i].class; db().class = selectedClass
        refreshFiltered()
        for j = 1, table.getn(shown) do
          if shown[j].id == rest then position = j; break end
        end
        render(); printSelected(); return
      end
    end
    say("Unknown preset: " .. rest)
  elseif verb == "next" or verb == "prev" then
    if verb == "next" then position = position + 1 else position = position - 1 end
    render(); printSelected()
  else
    say("Commands: /azse | list | class <class> | show <id> | next | prev | hide")
  end
end

SLASH_AZSE1 = "/azse"
SlashCmdList["AZSE"] = command
