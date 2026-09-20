-- AA10 r575: isolated extension. Loaded after native module definitions;
-- widgets are created only by the HUD entry, after the UI library is ready.
Aa10GmPanel = {}
function Aa10GmPanel.Init()
    if Aa10GmPanel.started then return end
    Aa10GmPanel.started = true
    local root = CreateEmptyWindow("aa10GmRoot", "UIParent")
    root:SetUILayer("game"); root:SetExtent(42, 42)
    root:AddAnchor("BOTTOMRIGHT", "UIParent", -101, -46); root:Show(true)
    local shortcut = root:CreateChildWidget("button", "gmShortcut", 0, true)
    shortcut:SetExtent(42, 42); shortcut:AddAnchor("TOPLEFT", root, 0, 0)
    local function IconState(tint,offset)
        local image=shortcut:CreateImageDrawable("ui/custom/aaemu/gm_panel.dds","background")
        image:SetCoords(0,0,64,64);image:SetExtent(42,42)
        image:AddAnchor("CENTER",shortcut,offset,offset);image:SetColor(tint,tint,tint,1)
        return image
    end
    shortcut:SetNormalBackground(IconState(0.85,0));shortcut:SetHighlightBackground(IconState(1,0))
    shortcut:SetPushedBackground(IconState(0.65,1));shortcut:SetDisabledBackground(IconState(0.4,0))
    shortcut:Show(false)
    shortcut:SetHandler("OnEnter", function() SetVerticalTooltip("Panel GM", shortcut) end)
    shortcut:SetHandler("OnLeave", HideTooltip)
    local w, pending, started, inside, allowed, anchored, due
    local serial = math.random(1, 1000000)
    local entries, received, filtered, favorites, rows, controls = {}, {}, {}, {}, {}, {}
    local selected, confirm, page, category = nil, nil, 0, "all"
    local chunks, meta, detailPage, detailLines = {}, nil, 0, {}
    local categoryButtons = {}
    local categories = {{"all","Todos"},{"favorites","Favoritos"},{"combat","Combate y skills"},
        {"items","Objetos y kits"},{"progress","Progresión"},{"move","Movimiento"},
        {"world","Mundo y spawns"},{"housing","Viviendas"},{"guild","Gremios y asedios"},
        {"economy","Economía"},{"inspect","Inspección"},{"admin","Administración"},{"debug","Depuración"}}
    local function Hex(t) return (string.gsub(t, ".", function(c) return string.format("%02x", string.byte(c)) end)) end
    local function Unhex(t)
        if #t % 2 ~= 0 or string.find(t, "[^0-9a-fA-F]") then return nil end
        return (string.gsub(t, "..", function(c) return string.char(tonumber(c, 16)) end))
    end
    local function Clean(t) return string.gsub(string.gsub(t, "|c%x%x%x%x%x%x%x%x", ""), "|r", "") end
    local function Key(t)
        t = string.lower(t)
        for _, pair in ipairs({{"á","a"},{"é","e"},{"í","i"},{"ó","o"},{"ú","u"},{"Á","a"},{"É","e"},{"Í","i"},{"Ó","o"},{"Ú","u"},{"ñ","n"},{"Ñ","n"}}) do t=string.gsub(t,pair[1],pair[2]) end
        return t
    end
    local function Enable()
        shortcut:Show(allowed == true); shortcut:Enable(allowed == true and not pending)
        if not w then return end
        local ok = allowed and not pending
        for _, c in ipairs(controls) do c:Enable(ok) end
        for _, row in ipairs(rows) do row:Enable(ok and row.entry ~= nil) end
        w.execute:Enable(ok and selected ~= nil)
        w.favorite:Enable(ok and selected ~= nil)
        w.previous:Enable(ok and page > 0); w.next:Enable(ok and (page+1)*10 < #filtered)
        w.helpPrevious:Enable(ok and detailPage > 0)
        w.helpNext:Enable(ok and (detailPage+1)*10 < #detailLines)
        w.execute:SetText(confirm and "Confirmar" or "Ejecutar")
    end
    local function Request(payload)
        if pending then return false end
        local count=math.ceil(#payload/24)
        if count < 1 or count > 12 then if w then w.note:SetText("El comando es demasiado largo.") end; return false end
        serial=serial%2147483646+1; pending=string.format("%x",serial); started=X2Time:GetUiMsec()
        Enable()
        for i=1,count do X2Chat:JoinUserChatChannel(string.format("aa10gm1:%s:%d:%d:%s",pending,i,count,string.sub(payload,(i-1)*24+1,i*24)),"") end
        return true
    end
    local function RenderHelp()
        local text={}
        for i=detailPage*10+1,math.min(#detailLines,(detailPage+1)*10) do text[#text+1]=detailLines[i] end
        w.help:SetText(table.concat(text,"\n"))
        w.helpPage:SetText(string.format("Ayuda %d / %d",detailPage+1,math.max(1,math.ceil(#detailLines/10))))
        Enable()
    end
    local function Preview()
        confirm=nil
        if selected then w.preview:SetText("/"..selected.name..(w.args:GetText()=="" and "" or " "..w.args:GetText()))
        else w.preview:SetText("Selecciona un comando para ver su ayuda.") end
        Enable()
    end
    local function Filter()
        filtered={}; local query=Key(w.search:GetText())
        for _, entry in ipairs(entries) do
            if (category=="all" or category==entry.category or category=="favorites" and favorites[entry.name]) and
                string.find(Key(entry.name.." "..entry.description.." "..entry.aliases),query,1,true) then filtered[#filtered+1]=entry end
        end
        page=math.min(page,math.max(0,math.ceil(#filtered/10)-1))
        for i,row in ipairs(rows) do
            row.entry=filtered[page*10+i]
            local e=row.entry
            row:SetText(e and ((favorites[e.name] and "* " or "").."/"..e.name) or "")
        end
        for key,b in pairs(categoryButtons) do b:SetText((key==category and "> " or "")..b.caption) end
        w.pageLabel:SetText(string.format("%d comandos · %d / %d",#filtered,page+1,math.max(1,math.ceil(#filtered/10))))
        Enable()
    end
    local function Select(entry)
        selected=nil; confirm=nil; chunks={}; meta=nil; detailLines={}; detailPage=0
        w.title:SetText("/"..entry.name); w.summary:SetText(entry.description)
        w.args:SetText(""); w.help:SetText("Cargando ayuda..."); w.note:SetText("")
        Request("detail/"..entry.name)
    end
    local function Place(c,x,y,width,height) c:SetExtent(width,height); c:AddAnchor("TOPLEFT",w,x,y) end
    local function Label(id,text,x,y,width,height)
        local c=w:CreateChildWidget("textbox",id,0,true); Place(c,x,y,width,height or 24)
        c.style:SetAlign(ALIGN_LEFT); c.style:SetColorByKey("default"); c:SetText(text); return c
    end
    local function Button(id,text,x,y,width,callback)
        local c=w:CreateChildWidget("button",id,0,true); Place(c,x,y,width,28)
        c:SetText(text); c:SetStyle("text_default"); c:SetHandler("OnClick",callback)
        controls[#controls+1]=c; return c
    end
    local function Edit(id,x,y,width,max)
        local c=W_CTRL.CreateEdit(id,w); Place(c,x,y,width,28); c:SetMaxTextLength(max)
        c:SetText(""); controls[#controls+1]=c; return c
    end
    local function Run(text)
        if not allowed or pending then return end
        confirm=nil;w.preview:SetText("/"..text)
        w.note:SetText("Enviando comando..."); Request("run/"..Hex(text))
    end
    local function Create()
        w=CreateWindow("aa10GmPanel","UIParent"); w:Show(false); w:SetExtent(940,700)
        w:AddAnchor("CENTER","UIParent",0,0); w:SetTitle("Panel GM")
        Label("gmSearchLabel","Buscar comando, alias o función",25,57,290)
        Button("gmQuickNoCd","Sin CD",450,50,100,function() Run("ignoreskillcds true") end)
        Button("gmQuickHeal","Curar",560,50,100,function() Run("heal") end)
        Button("gmQuickDummy","Dummy",670,50,110,function() Run("spawn npc dummy") end)
        Button("gmQuickCd","CD normal",790,50,115,function() Run("ignoreskillcds false") end)
        w.search=Edit("gmSearch",25,83,365,70)
        w.search:SetHandler("OnTextChanged",function() page=0; Filter() end)
        Button("gmRefresh","Actualizar",402,83,115,function() received={}; selected=nil; confirm=nil; Request("list") end)
        Label("gmTarget","Se usa el objetivo seleccionado en el juego.",530,83,385,32)
        for i,cat in ipairs(categories) do
            local key,caption=cat[1],cat[2]
            local b=Button("gmCat"..key,caption,25,130+(i-1)*32,160,function() category=key;page=0;Filter() end)
            b.caption=caption;categoryButtons[key]=b
        end
        for i=1,10 do
            local row
            row=Button("gmRow"..i,"",200,130+(i-1)*38,225,function() if row.entry then Select(row.entry) end end)
            row:SetHandler("OnEnter",function() if row.entry then SetVerticalTooltip(row.entry.description,row) end end)
            row:SetHandler("OnLeave",HideTooltip); rows[i]=row
        end
        w.previous=Button("gmPrevious","Anterior",200,513,105,function() page=page-1;Filter() end)
        w.next=Button("gmNext","Siguiente",320,513,105,function() page=page+1;Filter() end)
        w.pageLabel=Label("gmPage","",200,549,225,36)
        w.title=Label("gmTitle","Elige un comando",450,128,455,28)
        w.summary=Label("gmSummary","Busca por función o explora las categorías.",450,161,455,48)
        w.help=Label("gmHelp","",450,217,455,214)
        w.helpPrevious=Button("gmHelpPrevious","Anterior",450,441,105,function() detailPage=detailPage-1;RenderHelp() end)
        w.helpNext=Button("gmHelpNext","Siguiente",800,441,105,function() detailPage=detailPage+1;RenderHelp() end)
        w.helpPage=Label("gmHelpPage","",574,447,210)
        Label("gmArgsLabel","Parámetros (sin /comando)",450,478,320)
        w.args=Edit("gmArgs",450,505,455,120); w.args:SetHandler("OnTextChanged",Preview)
        Button("gmTrue","true",450,541,65,function() w.args:SetText("true");Preview() end)
        Button("gmFalse","false",520,541,65,function() w.args:SetText("false");Preview() end)
        Button("gmExample","Ejemplo",590,541,100,function() if selected then w.args:SetText(selected.example);Preview() end end)
        w.favorite=Button("gmFavorite","Favorito",700,541,95,function()
            if selected then favorites[selected.name]=not favorites[selected.name];Filter() end
        end)
        w.execute=Button("gmExecute","Ejecutar",800,541,105,function()
            if not selected then return end
            if confirm then local id=confirm;confirm=nil;Request("confirm/"..id)
            else Run(selected.name..(w.args:GetText()=="" and "" or " "..w.args:GetText())) end
        end)
        w.preview=Label("gmPreview","Selecciona un comando para ver su ayuda.",25,591,880,32)
        w.note=Label("gmNote","",25,631,880,44)
        Filter(); Enable()
    end
    shortcut:SetHandler("OnClick",function()
        if not allowed or pending then return end
        if not w then Create() end
        w:Show(true);received={};selected=nil;confirm=nil;Request("list")
    end)
    root:SetHandler("OnUpdate",function()
        local now=X2Time:GetUiMsec()
        if not anchored and GetRightIconMenuFrame then
            local frame=GetRightIconMenuFrame()
            if frame then root:RemoveAllAnchors();root:AddAnchor("BOTTOMRIGHT",frame,"TOPRIGHT",-96,-4);anchored=true end
        end
        if pending and now-started>15000 then
            pending=nil;allowed=false;confirm=nil;Enable()
            if w then w.note:SetText("Sin respuesta. Comprueba el chat antes de repetir una acción.") end
        end
        if inside and due and now>=due and not pending then due=now+30000;Request("access") end
    end)
    root:SetHandler("OnEvent",function(self,event,channel,relation,name,message)
        if event=="ENTERED_WORLD" then inside=true;due=X2Time:GetUiMsec()+1500;return end
        if event=="LEFT_WORLD" or event=="ENTERED_LOADING" then
            inside,allowed,pending,due,confirm=false,false,nil,nil,nil;selected=nil
            entries,received,filtered,favorites={},{},{},{}
            if w then w:Show(false);w.args:SetText("");Filter() end;Enable();return
        end
        if not inside or channel~=-2 or name~="DAILY_MSG" or type(message)~="string" then return end
        local id,kind,payload=string.match(message,"^AA10GM1:([0-9a-f]+):([a-z]+):(.*)$")
        if not id or id~=pending then return end
        if kind=="entry" then
            local n,c,d,a=string.match(payload,"^([^/]+)/([^/]+)/([^/]*)/(.*)$")
            if n and Unhex(d) and Unhex(a) then received[#received+1]={name=n,category=c,description=Unhex(d),aliases=Unhex(a)} end;return
        elseif kind=="meta" then
            local n,r,e=string.match(payload,"^([^/]+)/([01])/(.*)$")
            if n and Unhex(e) then meta={name=n,risk=r=="1",example=Unhex(e)} end;return
        elseif kind=="chunk" then
            local n,t=string.match(payload,"^(%d+)/(.*)$"); n=tonumber(n)
            if n and n==#chunks+1 then chunks[n]=t end;return
        end
        pending=nil
        if kind=="access" then
            allowed=payload=="1"
            if not allowed and w then selected=nil;confirm=nil;w:Show(false) end
        elseif kind=="listed" then
            if #received==tonumber(payload) then entries=received;received={};Filter();w.note:SetText("Catálogo actualizado. Favoritos disponibles durante esta sesión.")
            else w.note:SetText("Catálogo incompleto. Pulsa Actualizar.") end
        elseif kind=="detail" then
            local text=Unhex(table.concat(chunks))
            if meta and #chunks==tonumber(payload) and text then
                selected=meta; detailLines={}
                -- Wrap on words; UTF-8 bytes are never sliced through a character.
                text=Clean(text)
                for line in string.gmatch(text.."\n","(.-)\n") do
                    local current=""
                    for word in string.gmatch(line,"%S+") do
                        if #current+#word>60 and #current>0 then detailLines[#detailLines+1]=current;current="" end
                        current=current..(#current>0 and " " or "")..word
                    end
                    detailLines[#detailLines+1]=current
                end
                RenderHelp();Preview();w.note:SetText(selected.risk and "Esta acción requiere confirmación antes de ejecutarse." or "Completa los parámetros y pulsa Ejecutar.")
            else w.note:SetText("Ayuda incompleta. Selecciona de nuevo el comando.") end
        elseif kind=="confirm" then confirm=payload;w.note:SetText("Confirma en 20 segundos. Revisa el comando y conserva el mismo objetivo.")
        elseif kind=="denied" then allowed=false;confirm=nil;selected=nil;w:Show(false)
        else confirm=nil;if w then w.note:SetText(payload) end end
        Enable()
    end)
    root:RegisterEvent("ENTERED_WORLD");root:RegisterEvent("LEFT_WORLD")
    root:RegisterEvent("ENTERED_LOADING");root:RegisterEvent("CHAT_MESSAGE")
end
