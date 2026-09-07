    local batchRunner, batchSelected = nil, nil
    local batchNote = W_MODULE:Create("aa10BatchNote", window, W_MODULE.TYPES.TEXTBOX, {
        [W_MODULE.ATTRIBUTE.TEXT] = "Las opciones Completar EXP calculan los materiales de tu bolso."
    })
    window:RegisterStack(batchNote)
    local function BatchNote(text)
        batchNote:SetData({ [W_MODULE.ATTRIBUTE.TEXT] = text })
        window:ApplyAutoHeightByStack()
    end
    local function BagCount(id) return X2Bag:GetCountInBag(id) end
    local function StopBatch(message)
        batchRunner = nil
        window:ReleaseHandler("OnUpdate")
        filter:Enable(true)
        levelupBtn:Enable(selectedEquipSlot ~= nil and IsFullExp())
        if message then BatchNote(message) end
        window:ApplyOkButtonEnablement()
    end
    local function CancelBatch()
        local q = batchRunner
        if q then Aa10IpnyaBatch.Cancel(q.requestId) end
        StopBatch(q and "Operación cancelada. Revisa el estado de la ranura." or nil)
        if q and X2EquipSlotReinforce:IsWorkingAddExp() then X2EquipSlotReinforce:StopCasting() end
    end
    local function StartBatch()
        if not batchSelected or batchRunner then return end
        local info = X2EquipSlotReinforce:GetMaterialInfo(selectedEquipSlot,
            X2EquipSlotReinforce:GetReinforceInfo(selectedEquipSlot).level)
        local fresh = info and Aa10IpnyaBatch.Plan(info, BagCount, batchSelected.mode)
        if not fresh or fresh.signature ~= batchSelected.signature then
            window:SetEquipSlot(selectedEquipSlot)
            BatchNote("Cambió la EXP o el inventario. Revisa la selección antes de confirmar.")
            return
        end
        local level = X2EquipSlotReinforce:GetReinforceInfo(selectedEquipSlot).level
        local command, requestId = Aa10IpnyaBatch.Request(fresh, selectedEquipSlot, level)
        if not command then BatchNote("No se pudo preparar la operación."); return end
        batchRunner = Aa10IpnyaBatch.Watch(fresh, level)
        batchRunner.requestId = requestId
        local slot = selectedEquipSlot
        filter:Enable(false)
        levelupBtn:Enable(false)
        window:ApplyOkButtonEnablement()
        BatchNote("Completando EXP en 1 casteo. Pago con oro. Cancelar interrumpe la operación.")
        window:SetHandler("OnUpdate", function(self, dt)
            local q = batchRunner
            if not q then return end
            local action = q:Tick(dt, X2EquipSlotReinforce:GetReinforceInfo(slot),
                X2EquipSlotReinforce:IsWorkingAddExp(), window:IsVisible() and selectedEquipSlot == slot)
            if action == "done" then
                StopBatch()
                window:SetEquipSlot(slot)
                BatchNote("EXP completa. Ya puedes subir el nivel con la runa correspondiente.")
            elseif action == "stopped" then
                -- Invalidate a delayed request before unlocking; never fall back to a single recipe.
                Aa10IpnyaBatch.Cancel(q.requestId)
                StopBatch()
                window:SetEquipSlot(slot)
                BatchNote("La operación no se completó. Revisa el estado, los materiales y el oro.")
            end
        end)
        Aa10IpnyaBatch.Send(command, requestId)
    end
    window:SetHandler("OnHide", CancelBatch)
    window.Aa10CancelBatch = CancelBatch
