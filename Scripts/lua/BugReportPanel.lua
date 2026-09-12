-- Custom r575 reporting extension; native inventory functions remain unchanged.
Aa10BugReport = {}
local P = Aa10BugReport
local w, ready, pending, started, queue, cursor, sending
local nextSend = 0
local serial = math.random(1, 1000000)
local category, selected, page, pages, due, query, searchCategory, nonce = "quest", 0, 0, 1
local rows, controls = {}, {}
local host, view, historyDue, operation = nil, 1
local historyRows, historyPage, historyPages, historyCount, chunks = {}, 0, 1, 0, {}
local states = {new="Nuevo",investigating="En revisión",fixed="Corregido",needs_retest="Requiere prueba",closed="Cerrado",duplicate="Duplicado"}
local categories = {{"quest","Misión"},{"item","Objeto"},{"skill","Habilidad"},{"npc","NPC"},{"world","Mundo"},{"ui","Interfaz"},{"other","Otro"}}
local function HasEntity() return category == "quest" or category == "item" or category == "skill" or category == "npc" end
local function Hex(s) return (string.gsub(s,".",function(c) return string.format("%02x",string.byte(c)) end)) end
local function Unhex(s) return (string.gsub(s,"%x%x",function(c) return string.char(tonumber(c,16)) end)) end
local function ClearRows()
    for _,r in ipairs(rows) do r.id=nil; r:SetText(""); r:Enable(false) end
end
local function Enable()
    local idle = ready and not pending
    for _,c in ipairs(controls) do c:Enable(idle) end
    w.tabs:EnableTab(1,idle); w.tabs:EnableTab(2,idle)
    for _,r in ipairs(historyRows) do r:Enable(idle and r.id~=nil) end
    if w.historyPrevious then
        w.historyPrevious:Enable(idle and historyPage>0)
        w.historyNext:Enable(idle and historyPage+1<historyPages)
        w.refresh:Enable(idle)
    end

    w.search:Enable(ready and not sending and HasEntity())
    w.detail:Enable(ready and not sending)
    w.submit:Enable(idle and (not HasEntity() or selected > 0))
    w.previous:Enable(idle and not due and page > 0 and HasEntity())
    w.next:Enable(idle and not due and page+1 < pages and HasEntity())
    for _,r in ipairs(rows) do r:Enable(idle and not due and r.id ~= nil) end
end
local function Request(payload, isSubmit)
    if pending then return end
    operation=string.match(payload,"^([^/]+)")
    serial = serial % 2147483646 + 1
    pending, started, sending = string.format("%x",serial), X2Time:GetUiMsec(), isSubmit
    local count = math.ceil(#payload/20)
    queue, cursor = {}, 1
    for i=1,count do queue[i]=string.format("aa10br1:%s:%d:%d:%s",pending,i,count,string.sub(payload,(i-1)*20+1,i*20)) end
    w.note:SetText(isSubmit and "Enviando reporte..." or "Consultando...")
    Enable()
end
local function Search(p)
    query, searchCategory = w.search:GetText(), category
    if #query > 96 then w.note:SetText("Usa un nombre más corto o el ID."); return end
    Request("search/"..category.."/"..p.."/"..Hex(query))
end
local function Place(c,x,y,width,height)
    if host==w.tabs.window[1] and y<580 then y=y+40 end
    c:SetExtent(width,height); c:AddAnchor("TOPLEFT",w,x,y)
    return c
end
local function Label(id,text,x,y,width,height)
    local c=Place(host:CreateChildWidget("textbox",id,0,true),x,y,width,height or 24)
    c.style:SetAlign(ALIGN_LEFT); c.style:SetColorByKey("default"); c:SetText(text)
    return c
end
local function Button(id,text,x,y,width,callback)
    local c=Place(host:CreateChildWidget("button",id,0,true),x,y,width,28)
    c:SetText(text); c:SetStyle("text_default"); c:SetExtent(width,28); c:SetHandler("OnClick",callback)
    controls[#controls+1]=c; return c
end
local function ClearHistory()
    historyCount=0
    for _,r in ipairs(historyRows) do r.id=nil; r:SetText(""); r.meta:SetText("") end
    w.historyDetail:SetText(""); w.historySelected:SetText("Selecciona un reporte para leer su detalle.")
end
local function Mine(p)
    ClearHistory()
    Request("mine/"..p)
end
local function Summary(payload)
    local id,status,date,cat,entity,title=string.match(payload,"^(%d+)/([a-z_]+)/([^/]+)/([a-z]+)/(%d+)/(.*)$")
    if not id then return end
    local label=cat
    for _,v in ipairs(categories) do if v[1]==cat then label=v[2] end end
    title=Unhex(title)
    return id,"#"..id.." · "..label..(title~="" and " · "..title.." ["..entity.."]" or ""),date.." UTC · "..(states[status] or status)
end
local function Create()
    w=CreateWindow("aa10BugReportPanel","UIParent")
    w:Show(false); w:SetExtent(700,690); w:AddAnchor("CENTER","UIParent",0,0)
    w:SetTitle("Reportar un error")
    w.tabs=W_TAB.CreateTab("bugTabs",w)
    w.tabs:AddTabs({"Nuevo reporte","Mis reportes"})
    host=w.tabs.window[1]
    for i,v in ipairs(categories) do
        local key,title=v[1],v[2]
        Button("bugCategory"..key,title,25+(i-1)*93,65,89,function()
            category,selected,nonce=key,0,nil
            ClearRows(); w.selected:SetText("Categoría: "..title)
            w.search:SetText(""); due=HasEntity() and X2Time:GetUiMsec()+500 or nil
            w.help:SetText(HasEntity() and "Busca y selecciona el elemento afectado." or "Describe el problema en el detalle.")
            Enable()
        end)
    end
    w.help=Label("bugHelp","Busca y selecciona la misión afectada.",25,108,650)
    w.search=Place(W_CTRL.CreateEdit("bugSearch",host),25,138,650,28)
    w.search:SetMaxTextLength(96); w.search:SetText("")
    w.search:SetHandler("OnTextChanged",function()
        selected,nonce=0,nil; ClearRows(); due=X2Time:GetUiMsec()+500
        w.selected:SetText("Selecciona un resultado. Búsqueda ES/EN o ID."); Enable()
    end)
    w.search:SetHandler("OnEnterPressed",function() due=X2Time:GetUiMsec() end)
    for i=1,4 do
        local r
        r=Button("bugResult"..i,"",25,180+(i-1)*34,650,function()
            selected,nonce=r.id,nil; w.selected:SetText("Seleccionado: "..r.title.." ("..selected..")"); Enable()
        end)
        r.style:SetEllipsis(true)
        r.id=nil; rows[i]=r
    end
    w.previous=Button("bugPrevious","Anterior",25,321,100,function() Search(page-1) end)
    w.next=Button("bugNext","Siguiente",575,321,100,function() Search(page+1) end)
    w.page=Label("bugPage","",150,325,410)
    w.selected=Label("bugSelected","Categoría: Misión",25,360,650,36)
    w.selected.style:SetEllipsis(true)
    Label("bugDetailLabel","¿Qué hiciste, qué ocurrió y qué esperabas?",25,404,650)
    w.detail=Place(W_CTRL.CreateMultiLineEdit("bugDetail",host),25,433,650,100)
    w.detail:SetMaxTextLength(600); w.detail:SetText("")
    w.detail:SetHandler("OnTextChanged",function() nonce=nil end)
    Label("bugContext","Guardamos personaje, fecha y ubicación. No incluyas contraseñas.",25,581,650,26)
    w.submit=Button("bugSubmit","Enviar reporte",490,618,185,function()
        local detail=w.detail:GetText()
        local _,letters=string.gsub(detail,"[^\128-\191]","")
        if #detail < 10 or #detail > 2400 or letters > 600 then w.note:SetText("Escribe entre 10 y 600 caracteres."); return end
        if not nonce then nonce=string.format("%x-%x-%x",math.random(1,2147483646),X2Time:GetUiMsec(),serial) end
        due=nil
        Request("submit/"..category.."/"..selected.."/"..nonce.."/"..Hex(detail),true)
    end)
    host=w.tabs.window[2]
    Label("bugHistoryHelp","Reportes de este personaje, del más reciente al más antiguo.",25,105,650)
    for i=1,4 do
        local r
        r=Button("bugHistory"..i,"",25,142+(i-1)*62,650,function()
            chunks={}; w.historyDetail:SetText(""); Request("read/"..r.id)
        end)
        r.style:SetEllipsis(true)
        r.meta=Label("bugHistoryMeta"..i,"",25,172+(i-1)*62,650)
        r.id=nil; historyRows[i]=r
    end
    w.historyPrevious=Button("bugHistoryPrevious","Anterior",25,405,100,function() Mine(historyPage-1) end)
    w.historyNext=Button("bugHistoryNext","Siguiente",575,405,100,function() Mine(historyPage+1) end)
    w.historyPage=Label("bugHistoryPage","",140,409,420)
    w.historySelected=Label("bugHistorySelected","Selecciona un reporte para leer su detalle.",25,448,650,38)
    w.historySelected.style:SetEllipsis(true)
    w.historyDetail=Place(W_CTRL.CreateMultiLineEdit("bugHistoryDetail",host),25,490,650,110)
    w.historyDetail:SetMaxTextLength(600)
    w.historyDetail:SetReadOnly(true)
    w.refresh=Button("bugHistoryRefresh","Actualizar",490,618,185,function() Mine(historyPage) end)
    function w.tabs:OnTabChangedProc(index)
        view=index
        if index==2 then due=nil; historyDue=X2Time:GetUiMsec()+400
        else historyDue=nil; w.note:SetText("Completa el detalle y pulsa Enviar.") end
    end
    host=w
    w.note=Label("bugNote","",25,614,450,62)
    Enable()
end
function P.Open()
    if not w then Create() end
    w:Show(true)
    if not pending then ready=false; Request("open") end
end
local root=CreateEmptyWindow("aa10BugShortcut","UIParent")
root:SetUILayer("game"); root:SetExtent(42,42)
root:AddAnchor("BOTTOMRIGHT","UIParent",-5,-46)
local button=root:CreateChildWidget("button","bugShortcut",0,true)
button:SetExtent(42,42); button:AddAnchor("TOPLEFT",root,0,0)
local function IconState(tint,offset)
    local image=button:CreateImageDrawable("ui/custom/aaemu/bug_report.dds","background")
    image:SetCoords(0,0,64,64); image:SetExtent(42,42)
    image:AddAnchor("CENTER",button,offset,offset); image:SetColor(tint,tint,tint,1)
    return image
end
button:SetNormalBackground(IconState(0.85,0))
button:SetHighlightBackground(IconState(1,0))
button:SetPushedBackground(IconState(0.65,1))
button:SetDisabledBackground(IconState(0.4,0))
button:SetHandler("OnEnter",function() SetVerticalTooltip("Reportar un error",button) end)
button:SetHandler("OnLeave",HideTooltip)
button:SetHandler("OnClick",P.Open)
root:Show(true)
local anchored=false
root:SetHandler("OnUpdate",function()
    if not anchored and GetRightIconMenuFrame then
        local frame=GetRightIconMenuFrame()
        if frame then root:RemoveAllAnchors(); root:AddAnchor("BOTTOMRIGHT",frame,"TOPRIGHT",0,-4); anchored=true end
    end
    if not w then return end
    local now=X2Time:GetUiMsec()
    if pending and queue and now>=nextSend then
        for i=1,2 do
            if cursor <= #queue then X2Chat:JoinUserChatChannel(queue[cursor],""); cursor=cursor+1 end
        end
        if cursor > #queue then queue=nil end
    end
    if pending and now-started > 30000 then
        pending,queue,sending=nil,nil,nil; Enable()
        w.note:SetText("Sin confirmación. Conservamos el texto; reintentar no duplica el reporte.")
    end
    if historyDue and ready and not pending and w:IsVisible() and view==2 and now>=historyDue and now-started>=400 then
        historyDue=nil; Mine(0)
    end
    if due and view==1 and ready and not pending and w:IsVisible() and HasEntity() and now>=due and now-started>=400 then
        due=nil; Search(0)
    end
end)
root:SetHandler("OnEvent",function(self,event,channel,relation,name,message)
    if event=="ENTERED_LOADING" then
        ready,pending,queue,sending,due,historyDue=false,nil,nil,nil,nil,nil
        if w then ClearHistory(); chunks={}; w:Show(false); Enable() end
        return
    end
    if not w or channel~=-2 or name~="DAILY_MSG" or type(message)~="string" then return end
    local id,kind,payload=string.match(message,"^AA10BR1:([0-9a-f]+):([a-z]+):(.*)$")
    if not id or id~=pending then return end
    if operation=="mine" and kind=="history" then
        local p,n,total=string.match(payload,"^(%d+)/(%d+)/(%d+)$")
        if p then historyPage,historyPages=tonumber(p),tonumber(n); w.historyPage:SetText(total.." reportes · Página "..(historyPage+1).." de "..n) end
        return
    elseif operation=="mine" and kind=="entry" then
        local reportId,title,meta=Summary(payload)
        if reportId and historyCount<4 then
            historyCount=historyCount+1; local r=historyRows[historyCount]
            r.id=reportId; r:SetText(title); r.meta:SetText(meta)
        end
        return
    elseif operation=="read" and kind=="report" then
        local reportId,title,meta=Summary(payload)
        if reportId then w.historySelected:SetText(title.." · "..meta) end
        return
    elseif operation=="read" and kind=="chunk" then
        local i,data=string.match(payload,"^(%d+)/(%x+)$")
        if i and tonumber(i)==#chunks+1 and #chunks<20 and #data<=240 then chunks[#chunks+1]=data end
        return
    end
    pending,queue,sending=nil,nil,nil; nextSend=X2Time:GetUiMsec()+400
    if kind=="listed" then
        w.note:SetText(tonumber(payload)~=historyCount and "Lista incompleta. Pulsa Actualizar." or historyCount==0 and "Todavía no has enviado reportes." or "Revisa el detalle antes de enviar un reporte similar.")
    elseif kind=="read" then
        if tonumber(payload)==#chunks then w.historyDetail:SetText(Unhex(table.concat(chunks))); w.note:SetText("Detalle del reporte enviado. Sólo lectura.")
        else w.note:SetText("Detalle incompleto. Selecciona otra vez el reporte.") end
    elseif kind=="open" then ready=true; if view==2 then historyDue=X2Time:GetUiMsec()+400 end; w.note:SetText("Completa el detalle y pulsa Enviar.")
    elseif kind=="saved" then
        w.detail:SetText(""); nonce=nil
        w.note:SetText("Reporte #"..payload.." guardado. Gracias.")
    elseif kind=="page" then
        if due or searchCategory~=category or query~=w.search:GetText() then Enable(); return end
        local p,n,total,data=string.match(payload,"^(%d+)/(%d+)/(%d+)/(.*)$")
        if not p then Enable(); return end
        page,pages=tonumber(p),tonumber(n); ClearRows()
        w.page:SetText(total.." resultados · Página "..(page+1).." de "..pages)
        local i=0
        for itemId,title in string.gmatch(data,"(%d+),(%x+)") do
            i=i+1; if i>4 then break end
            rows[i].id,rows[i].title=tonumber(itemId),Unhex(title)
            rows[i]:SetText(rows[i].title.."  ["..itemId.."]")
        end
        w.note:SetText(tonumber(total)==0 and "Sin resultados. Prueba otro nombre o el ID." or "Selecciona un resultado.")
    else w.note:SetText(payload) end
    Enable()
end)
root:RegisterEvent("CHAT_MESSAGE"); root:RegisterEvent("ENTERED_LOADING")
