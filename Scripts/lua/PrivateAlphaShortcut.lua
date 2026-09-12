-- Independent HUD extension; alpha grants still require server entitlement.
local root=CreateEmptyWindow("aa10AlphaShortcut","UIParent")
root:SetUILayer("game"); root:SetExtent(42,42)
root:AddAnchor("BOTTOMRIGHT","UIParent",-53,-46)
local button=root:CreateChildWidget("button","alphaShortcut",0,true)
button:SetExtent(42,42); button:AddAnchor("TOPLEFT",root,0,0)
local function IconState(tint,offset)
    local image=button:CreateImageDrawable("ui/custom/aaemu/private_alpha.dds","background")
    image:SetCoords(0,0,64,64); image:SetExtent(42,42)
    image:AddAnchor("CENTER",button,offset,offset); image:SetColor(tint,tint,tint,1)
    return image
end
button:SetNormalBackground(IconState(0.85,0))
button:SetHighlightBackground(IconState(1,0))
button:SetPushedBackground(IconState(0.65,1))
button:SetDisabledBackground(IconState(0.4,0))
button:SetHandler("OnEnter",function() SetVerticalTooltip("Alpha privada",button) end)
button:SetHandler("OnLeave",HideTooltip)
local allowed,inside,anchored=false,false,false
local due,request,started
local serial=math.random(1,1000000)
local function Access(value)
    allowed=value; button:Show(value); button:Enable(value)
    if not value then HideTooltip() end
end
button:SetHandler("OnClick",function()
    if allowed and Aa10PrivateAlpha then Aa10PrivateAlpha.Open() end
end)
Access(false); root:Show(true) -- Empty root remains active so its timer can check access.
root:SetHandler("OnUpdate",function()
    local now=X2Time:GetUiMsec()
    if not anchored and GetRightIconMenuFrame then
        local frame=GetRightIconMenuFrame()
        if frame then root:RemoveAllAnchors(); root:AddAnchor("BOTTOMRIGHT",frame,"TOPRIGHT",-48,-4); anchored=true end
    end
    if request and now-started>10000 then request=nil; Access(false) end
    if inside and due and now>=due and not request then
        serial=serial%2147483646+1; request=string.format("%x",serial); started=now; due=now+30000
        X2Chat:JoinUserChatChannel("aa10ap1:"..request..":1:1:access","")
    end
end)
root:SetHandler("OnEvent",function(self,event,channel,relation,name,message)
    if event=="ENTERED_WORLD" then inside=true; due=X2Time:GetUiMsec()+1500; return end
    if event=="ENTERED_LOADING" or event=="LEFT_WORLD" then
        inside,due,request=false,nil,nil; Access(false); return
    end
    if channel~=-2 or name~="DAILY_MSG" or type(message)~="string" then return end
    local id,kind,payload=string.match(message,"^AA10AP1:([0-9a-f]+):([a-z]+):(.*)$")
    if not inside then return end
    if kind=="access" and (id==request or id=="0") then
        request=nil; Access(payload=="1")
    elseif kind=="denied" then Access(false) end
end)
root:RegisterEvent("ENTERED_WORLD"); root:RegisterEvent("ENTERED_LOADING")
root:RegisterEvent("LEFT_WORLD"); root:RegisterEvent("CHAT_MESSAGE")
