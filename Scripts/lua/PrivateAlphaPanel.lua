-- Custom r575 extension. PreUse opens it; every operation is authorized by Game.
Aa10PrivateAlpha = {}
local P = Aa10PrivateAlpha
local w, pending, started, ready = nil, nil, 0, false
local serial = math.random(1, 1000000)
local page, pages, query = 0, 1, ""
local rows, controls = {}, {}
local keyType = 900001
local due

local function ClearRows()
    for _, row in ipairs(rows) do
        row.itemType = nil; row.name:SetText(""); row.icon:Show(false); row.take:Enable(false)
    end
end

local function Hex(text)
    return (string.gsub(text, ".", function(c) return string.format("%02x", string.byte(c)) end))
end
local function EnableControls()
    local enabled = ready and not pending
    for _, control in ipairs(controls) do control:Enable(enabled) end
    w.search:Enable(ready)
    enabled = enabled and not due
    for _, row in ipairs(rows) do row.take:Enable(enabled and row.itemType ~= nil) end
    w.previous:Enable(enabled and page > 0)
    w.next:Enable(enabled and page + 1 < pages)
end
local function Request(payload)
    if pending then return end
    serial = serial % 2147483646 + 1
    local id = string.format("%x", serial)
    local count = math.ceil(#payload / 24)
    if count < 1 or count > 12 then w.note:SetText("Solicitud demasiado larga."); return end
    pending, started = id, X2Time:GetUiMsec()
    EnableControls()
    w.note:SetText("Esperando...")
    for i = 1, count do
        X2Chat:JoinUserChatChannel(string.format("aa10ap1:%s:%d:%d:%s", id, i, count,
            string.sub(payload, (i - 1) * 24 + 1, i * 24)), "")
    end
end
local function Search(targetPage)
    if #query > 96 then w.note:SetText("Máximo: 96 bytes."); return end
    Request("search/" .. tostring(targetPage) .. "/" .. Hex(query))
end
local function Place(c, x, y, width, height)
    c:SetExtent(width, height); c:AddAnchor("TOPLEFT", w, x, y)
end
local function Label(id, text, x, y, width, height)
    local c = w:CreateChildWidget("textbox", id, 0, true)
    Place(c, x, y, width, height or 24)
    c.style:SetAlign(ALIGN_LEFT); c.style:SetColorByKey("default"); c:SetText(text)
    return c
end
local function Edit(id, value, x, y, width, digits)
    local c = W_CTRL.CreateEdit(id, w)
    Place(c, x, y, width, 26)
    if digits then c:SetDigit(true) end
    c:SetMaxTextLength(digits and 7 or 96); c:SetText(value)
    if digits then controls[#controls + 1] = c end
    return c
end
local function Button(id, text, x, y, width, callback)
    local c = w:CreateChildWidget("button", id, 0, true)
    c:SetText(text); c:SetStyle("text_default"); Place(c, x, y, width, 28)
    c:SetHandler("OnClick", callback)
    controls[#controls + 1] = c
    return c
end
local function Integer(edit, limit)
    local n = tonumber(edit:GetText())
    if not n or n < 1 or n ~= math.floor(n) or n > limit then
        w.note:SetText("Cantidad: 1–" .. tostring(limit) .. ".")
        return nil
    end
    return n
end
local function Resource(id, label, limit, x, y)
    Label(id .. "Label", label, x, y + 6, 62)
    w[id] = Edit(id, id == "labor" and "5000" or "1000", x + 62, y + 1, 92, true)
    Button("get" .. id, "Obtener " .. label, x + 162, y, 140, function()
        local n = Integer(w[id], w[limit]); if n then Request(id .. "/" .. n) end
    end)
end
local function Create()
    w = CreateWindow("aa10PrivateAlphaPanel", "UIParent")
    w:Show(false); w:SetExtent(760, 720); w:AddAnchor("CENTER", "UIParent", 0, 0)
    w:SetTitle("Alpha privada")
    w.maxGold, w.maxLabor, w.maxItems, w.maxPoints = 10000, 5000, 1000, 100000
    Resource("gold", "oro", "maxGold", 25, 81)
    Resource("labor", "labor", "maxLabor", 343, 81)
    Resource("honor", "honor", "maxPoints", 25, 121)
    Resource("vocation", "vocación", "maxPoints", 343, 121)
    Label("s", "Nombre / ID", 25, 167, 110)
    w.search = Edit("search", "", 137, 162, 350, false)
    local function NewSearch() due = X2Time:GetUiMsec(); ClearRows(); EnableControls() end
    Button("find", "Buscar", 500, 161, 105, NewSearch)
    w.search:SetHandler("OnEnterPressed", NewSearch)
    w.search:SetHandler("OnTextChanged", function()
        due = X2Time:GetUiMsec() + 500; ClearRows(); EnableControls()
        w.result:SetText("Buscando...")
    end)
    Label("c", "Cantidad", 25, 206, 85)
    w.count = Edit("count", "1", 112, 200, 80, true)
    Label("g", "Grado (0–12)", 218, 206, 110)
    w.grade = Edit("grade", "0", 335, 200, 65, true)
    Label("h", "Grado fijo: se conserva.", 415, 206, 320)
    w.result = Label("result", "Nombre ES/EN o ID. Búsqueda automática.", 25, 241, 710)
    for i = 1, 10 do
        local row = {}
        rows[i] = row
        local y = 274 + (i - 1) * 34
        row.icon = CreateIconButton("alphaIcon" .. i, w)
        Place(row.icon, 25, y, 32, 32)
        row.name = Label("alphaName" .. i, "", 66, y + 1, 532, 34)
        row.name.style:SetEllipsis(true)
        row.take = Button("alphaTake" .. i, "Obtener", 615, y, 110, function()
            if not row.itemType then return end
            local count = Integer(w.count, w.maxItems)
            local grade = tonumber(w.grade:GetText())
            if not grade or grade < 0 or grade > 12 or grade ~= math.floor(grade) then
                w.note:SetText("Grado: entero de 0 a 12."); return
            end
            if count then Request(string.format("item/%d/%d/%d", row.itemType, count, grade)) end
        end)
        row.icon:Show(false); row.take:Enable(false)
    end
    w.previous = Button("previous", "Anterior", 25, 623, 105, function() Search(page - 1) end)
    w.next = Button("next", "Siguiente", 615, 623, 110, function() Search(page + 1) end)
    w.pageLabel = Label("pageLabel", "", 245, 628, 300)
    w.note = Label("note", "", 25, 663, 710, 44)
    w:SetHandler("OnUpdate", function(self)
        local now = X2Time:GetUiMsec()
        if pending then
            if now - started > 20000 then
                pending = nil; EnableControls()
                w.note:SetText("Sin respuesta. Revisa el inventario.")
            end
        end
        if due and ready and not pending and w:IsVisible() and now >= due and now - started >= 400 then
            due = nil; query = w.search:GetText(); Search(0)
        end
    end)
    w:SetHandler("OnEvent", function(self, event, channel, relation, name, message)
        if event == "LEFT_WORLD" or event == "ENTERED_LOADING" then
            ready, pending, due = false, nil, nil; w:Show(false); EnableControls(); return
        end
        -- r575 maps system channel -2 to the native sender DAILY_MSG.
        if channel ~= -2 or name ~= "DAILY_MSG" or type(message) ~= "string" then return end
        local id, kind, payload = string.match(message, "^AA10AP1:([0-9a-f]+):([a-z]+):(.*)$")
        if not id or id ~= pending then return end
        pending = nil
        if kind == "open" then
            local gold, labor, count = string.match(payload, "^(%d+),(%d+),(%d+)$")
            if not gold then ready = false; EnableControls(); return end
            w.maxGold, w.maxLabor, w.maxItems = tonumber(gold), tonumber(labor), tonumber(count)
            ready = true; w.note:SetText("Acceso autorizado.")
        elseif kind == "page" then
            if due or query ~= w.search:GetText() then EnableControls(); return end
            local p, n, total, ids = string.match(payload, "^(%d+)/(%d+)/(%d+)/(.*)$")
            if not p then return end
            page, pages = tonumber(p), tonumber(n)
            w.result:SetText(total .. " resultados.")
            w.pageLabel:SetText(string.format("Página %d de %d", page + 1, pages))
            ClearRows()
            local index = 0
            for value in string.gmatch(ids, "%d+") do
                index = index + 1
                if index > 10 then break end
                local row, itemType = rows[index], tonumber(value)
                local info = X2Item:GetItemInfoByType(itemType)
                row.itemType = itemType
                local title = X2Item:Name(itemType)
                row.name:SetText(string.format("%s\nID %d", title or "Objeto del catálogo", itemType))
                if info then row.icon:SetInfo(info); row.icon:Show(true) end
            end
            w.note:SetText(tonumber(total) == 0 and "Sin resultados." or "Requiere ranuras libres.")
        elseif kind == "denied" then
            ready, due = false, nil; w.note:SetText(payload)
        else w.note:SetText(payload) end
        EnableControls()
    end)
    w:RegisterEvent("CHAT_MESSAGE"); w:RegisterEvent("ENTERED_LOADING")
    EnableControls()
end

function P.Open()
    if not w then Create() end
    w:Show(true)
    if not pending then ready = false; Request("open") end
end

function P.PreUse(realSlot)
    local itemType = X2Bag:ItemIdentifier(realSlot)
    if itemType ~= keyType then return false end
    P.Open()
    return true
end
