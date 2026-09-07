#!/usr/bin/env python3
"""Build the custom r575 Ipnya fill-EXP UI from exact effective source/ALB."""
import argparse
import json
from pathlib import Path

import PatchAa10SpanishUiLayout as codec

v1 = codec.v1
CONTRACTS = Path(__file__).with_name("Aa10IpnyaFillExp.contracts.json")
LUA = Path(__file__).with_name("lua")


def patch_source(source):
    replace = v1.replace_once
    source = replace(source, 'local selectedMaterialType = nil',
                     'local selectedMaterialType = nil\n' + (LUA / 'IpnyaFillExpUi.lua').read_text(encoding='utf-8'), 'batch UI')
    source = replace(source, 'window:SetWidth(F_PREFIX_SIZE:GetWindowWidth(WINDOW_WIDTH_430))',
                     'window:SetWidth(F_PREFIX_SIZE:GetWindowWidth(WINDOW_WIDTH_510))', 'batch labels width')
    source = replace(source, 'return materialSatisfy and not IsFullExp()',
                     'return materialSatisfy and not IsFullExp() and not window.Aa10BatchRunning', 'batch disablement')
    source = replace(source, '            X2EquipSlotReinforce:StartReinforceAddExp(selectedEquipSlot, selectedMaterialType)',
                     '            if batchSelected then StartBatch(); return end\n'
                     '            X2EquipSlotReinforce:StartReinforceAddExp(selectedEquipSlot, selectedMaterialType)', 'confirm batch')
    source = replace(source, '            if X2EquipSlotReinforce:IsWorkingAddExp() then',
                     '            if batchRunner then CancelBatch(); return end\n'
                     '            if X2EquipSlotReinforce:IsWorkingAddExp() then', 'cancel batch')
    source = replace(source, '        local datas = {}\n        for i = 1, #materialInfo do',
                     '        local options = Aa10IpnyaBatch.Options(materialInfo, BagCount)\n'
                     '        for _, option in ipairs(options) do materialInfo[#materialInfo + 1] = option end\n'
                     '        if filterSelectedIndex > #materialInfo then filterSelectedIndex = 1 end\n'
                     '        local datas = {}\n        for i = 1, #materialInfo do', 'dynamic options')
    source = replace(source, '        local itemList = curMaterialInfo.itemList',
                     '        batchSelected = curMaterialInfo.batchPlan\n'
                     '        if batchSelected then\n'
                     '            BatchNote(string.format("1 casteo. Pago con oro. Excedente: %d EXP. Cancelar interrumpe la operación.", batchSelected.overflow))\n'
                     '        else\n'
                     '            BatchNote("Uso individual. Completar EXP permite combinar los materiales disponibles.")\n'
                     '        end\n'
                     '        local itemList = curMaterialInfo.itemList', 'preview totals')
    source = replace(source, '    function window:SetEquipSlot(equipSlot)\n',
                     '    function window:SetEquipSlot(equipSlot)\n'
                     '        if batchRunner then\n'
                     '            if selectedEquipSlot == equipSlot then\n'
                     '                FillSlot(equipSlot, X2EquipSlotReinforce:GetReinforceInfo(equipSlot))\n'
                     '                levelupBtn:Enable(false)\n'
                     '                return\n'
                     '            end\n'
                     '            CancelBatch()\n'
                     '        end\n', 'prevent in-flight replan')
    source = replace(source, '        ["EQUIP_SLOT_REINFORCE_MSG_LEVEL_UP"] = function(equipSlot)',
                     '        ["BAG_UPDATE"] = function()\n'
                     '            if window:IsVisible() and selectedEquipSlot and not batchRunner then window:SetEquipSlot(selectedEquipSlot) end\n'
                     '        end,\n'
                     '        ["EQUIP_SLOT_REINFORCE_MSG_LEVEL_UP"] = function(equipSlot)', 'inventory refresh')
    # The Satisfy function occurs before the runner local declaration.
    source = replace(source, '        batchRunner = nil\n',
                     '        batchRunner = nil\n        window.Aa10BatchRunning = false\n', 'clear running')
    source = replace(source, '        local slot = selectedEquipSlot\n',
                     '        window.Aa10BatchRunning = true\n        local slot = selectedEquipSlot\n', 'set running')
    helper = (LUA / 'IpnyaFillExp.lua').read_text(encoding='utf-8')
    return 'local Aa10IpnyaBatch = (function()\n' + helper + '\nend)()\n' + source


def build(effective, output, luac):
    contracts = json.loads(CONTRACTS.read_text(encoding='utf-8'))
    v1.require_exact(luac, contracts['luac_sha256'])
    results = []
    for entry in contracts['entries']:
        name = entry['name']
        source_path = effective / f'scripts/x2ui/{name}.lua'
        alb_path = effective / f'scriptsbin64/x2ui/{name}.alb'
        v1.require_exact(source_path, entry['source_sha256'])
        before = v1.sha256(alb_path)
        if before not in entry['accepted_sha256'] or alb_path.stat().st_size != entry['size']:
            raise RuntimeError('Unknown effective Ipnya ALB')
        source = source_path.read_text(encoding='utf-8-sig')
        if before == entry['baseline_sha256'] and codec.semantic_chunk(codec.compile_source(source, luac)) != codec.semantic_chunk(alb_path.read_bytes()):
            raise RuntimeError('Source/retail bytecode mismatch')
        compiled = codec.compile_source(patch_source(source), luac)
        if len(compiled) > entry['size']:
            raise RuntimeError(f'Ipnya ALB exceeds fixed capacity: {len(compiled)}/{entry["size"]}')
        replacement = output / f'{name}.alb'
        replacement.parent.mkdir(parents=True, exist_ok=True)
        replacement.write_bytes(compiled + b'\0' * (entry['size'] - len(compiled)))
        v1.require_exact(replacement, entry['patched_sha256'], entry['size'])
        results.append(dict(name=name, before=before, after=entry['patched_sha256'],
                            size=entry['size'], replacement=str(replacement)))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--effective', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--luac', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.effective, args.output, args.luac), indent=2))
