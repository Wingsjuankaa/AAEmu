"""Build opt-in AA10 r575 sandbox entry using the retail client UI consumers.

The two ALBs retain their fixed sizes. Exact source/compiler/ALB contracts and
semantic parity with the effective, previously patched consumers fail closed.
The dedicated, runner-bound copy opts in. World id 1 plus the exact realm name
AA10 Sandbox gate native world entry; character automation also requires that realm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import PatchAa10SpanishUiLayout as lua

ROOT = Path("E:/AAEmu/rama_10")
TEMP = ROOT / "artifacts/sandbox/temp"
CONTRACTS = Path(__file__).with_name("Aa10SandboxAutoEntry.contracts.json")
CHARACTER = "Sandbox"
WORLD = 1
ZONE = 379
GATE = '''local function Aa10SandboxEnabled()
    return X2World:GetCurrentWorldName() == "AA10 Sandbox"
end
local function Aa10SandboxLog(event, fields)
    UIParent:Log('AA10_SANDBOX {"event":"' .. event .. '",' .. fields .. '}')
end
local function Aa10SandboxModule(stage)
    local marker = tonumber(Console:GetAttribute("client_default_zone"))
    Aa10SandboxLog("module_loaded", '"stage":"' .. stage .. '","marker":' ..
        (marker and tostring(marker) or "null") .. ',"dev_mode":' .. tostring(X2Debug:GetDevMode()))
end
'''


def once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise RuntimeError(f"Expected one exact sandbox source anchor: {old!r}")
    return source.replace(old, new, 1)


def effective_source(name: str, source: str) -> str:
    """Recover the two existing retail ALB deltas; never undo them by using Lua blindly."""
    if name == "loginstage_new/connect/stage_server":
        return once(source, 'returnToLogin:AddAnchor("TOPLEFT", wnd, 0, 50)',
                    'returnToLogin:AddAnchor("TOPLEFT", wnd, 0, 100)')
    if name == "loginstage_new/character_select/character_select":
        old = '''if characterSelectLocale.showReturnServer then
    serverBtn:Show(true)
    reviewBtn:AddAnchor("LEFT", serverBtn, "RIGHT", 15, 0)
    AdjustBtnLongestTextWidth({serverBtn, reviewBtn})
else
    serverBtn:Show(false)
    reviewBtn:AddAnchor("BOTTOMLEFT", background, 40, -40)
end'''
        replacement = ('if X2Debug:GetDevMode() then\n' +
                       '\n'.join('    ' + line for line in old.splitlines()) +
                       '\nelse\n    serverBtn:Show(false)\n'
                       '    reviewBtn:AddAnchor("BOTTOMLEFT", background, 40, -40)\nend')
        return once(source, old, replacement)
    raise ValueError(f"Unknown sandbox consumer: {name}")


def world_controller() -> str:
    return '''    local aa10SandboxWorldRequested = false
    local aa10SandboxWorldElapsed = 0
    local aa10SandboxWorldEmptyLogged = false
    local function Aa10SandboxTryWorld(worldInfos)
        if aa10SandboxWorldRequested then return end
        if #worldInfos == 0 and not aa10SandboxWorldEmptyLogged then
            Aa10SandboxLog("world_wait", '"reason":"empty_list"')
            aa10SandboxWorldEmptyLogged = true
        end
        for i = 1, #worldInfos do
            if tonumber(worldInfos[i].id) == 1 and worldInfos[i].name == "AA10 Sandbox" then
                aa10SandboxWorldRequested = true
                worldListWnd:SelectByDataKey(worldInfos[i].id)
                Aa10SandboxLog("world_request", '"world":1,"zone":379')
                wnd:SelectServer(worldInfos[i].id)
                return
            end
        end
    end
    function wnd:Aa10SandboxOnUpdate(dt)
        if aa10SandboxWorldRequested or not wnd:IsVisible() then return end
        aa10SandboxWorldElapsed = aa10SandboxWorldElapsed + dt
        if aa10SandboxWorldElapsed < 250 then return end
        aa10SandboxWorldElapsed = 0
        Aa10SandboxTryWorld(wnd:UpdateList())
    end
    wnd:SetHandler("OnUpdate", wnd.Aa10SandboxOnUpdate)
'''


def character_controller() -> str:
    return '''local aa10SandboxEntry = { elapsed = 0, sent = false, status = "" }
local function Aa10SandboxCharacterStatus(status)
    if aa10SandboxEntry.status == status then return end
    aa10SandboxEntry.status = status
    Aa10SandboxLog("character_wait", '"reason":"' .. status .. '"')
end
local function Aa10SandboxStep(dt)
    if aa10SandboxEntry.sent or not Aa10SandboxEnabled() then return end
    aa10SandboxEntry.elapsed = aa10SandboxEntry.elapsed + dt
    if aa10SandboxEntry.elapsed < 500 then return end
    aa10SandboxEntry.elapsed = 0
    if not background:IsVisible() then return end
    if X2World:IsPreSelectCharacterPeriod() then Aa10SandboxCharacterStatus("preselect_period"); return end
    if X2LoginCharacter:GetWorldQueuePosition() > 0 then Aa10SandboxCharacterStatus("queue"); return end
    for index = 1, X2LoginCharacter:GetNumLoginCharacters() do
        if X2LoginCharacter:GetLoginCharacterName(index) == "Sandbox" then
            if not X2LoginCharacter:IsInEnableStartingLocation(index) or
               X2LoginCharacter:IsDeleteRequestedCharacter(index) or
               X2LoginCharacter:IsForceNameChangedCharacter(index) or
               (X2LoginCharacter:IsTransferRequestedCharacter(index) and X2Player:GetFeatureSet().forbidTransferChar) then
                Aa10SandboxCharacterStatus("native_restriction"); return
            end
            if X2LoginCharacter:GetLastPlayedCharacterIndex() ~= index then
                Aa10SandboxCharacterStatus("preview")
                ShowCharacter(index, true)
                return
            end
            aa10SandboxEntry.sent = true
            Aa10SandboxLog("character_request", '"character":"Sandbox","index":' .. tostring(index))
            SelectCharacter(index)
            return
        end
    end
    Aa10SandboxCharacterStatus("missing_character")
end
'''


def patch_source(name: str, source: str) -> str:
    if name == "loginstage_new/connect/stage_server":
        source = once(source, '    function wnd:OnShow()\n',
                      world_controller() + '\n    function wnd:OnShow()\n')
        source = once(source, '        tipLabel:SetHeight(tipLabel:GetTextHeight())',
                      '        tipLabel:SetHeight(tipLabel:GetTextHeight())\n'
                      '        Aa10SandboxTryWorld(worldInfos)')
        source = once(source, '    end\n\n    function wnd:ReAnchorOnScale()',
                      '        Aa10SandboxTryWorld(worldInfos)\n    end\n\n'
                      '    function wnd:ReAnchorOnScale()')
        # Only the exact-name/id automatic request supplies the fixed native zone.
        # The ordinary manual consumer keeps its native CVar/dev-combo behavior.
        source = once(source, '        if zoneId == nil then',
                      '        if aa10SandboxWorldRequested and tonumber(worldIndex) == 1 then zoneId = 379 end\n'
                      '        if zoneId == nil then')
    elif name == "loginstage_new/character_select/character_select":
        source = once(source, '                if X2LoginCharacter:CanShowClientDrivenSkipDialog(index) then',
                      '                if Aa10SandboxEnabled() and X2LoginCharacter:GetLoginCharacterName(index) == "Sandbox" then\n'
                      '                    TryToEnterGame(index, true)\n'
                      '                elseif X2LoginCharacter:CanShowClientDrivenSkipDialog(index) then')
        source = once(source, 'local freshTime = 0\n', character_controller() + '\nlocal freshTime = 0\n')
        source = once(source, 'function background:OnUpdate(dt)\n',
                      'function background:OnUpdate(dt)\n    Aa10SandboxStep(dt)\n')
    else:
        raise ValueError(f"Unknown sandbox consumer: {name}")
    return GATE + 'Aa10SandboxModule("' + name + '")\n' + source


def compile_source(source: str, luac: Path) -> bytes:
    TEMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="autoentry-", dir=TEMP) as directory:
        root = Path(directory)
        source_path, output = root / "source.lua", root / "compiled.alb"
        source_path.write_text(source, encoding="utf-8", newline="\n")
        subprocess.run([str(luac), "-s", "-o", str(output), str(source_path)], check=True)
        data = bytearray(output.read_bytes())
        if data[:12] != lua.v1.LUA_51_HEADER:
            raise RuntimeError("Unexpected compiler ABI")
        data[11] = 8
        lua.semantic_chunk(bytes(data))
        return bytes(data)


def build(effective: Path, output: Path, luac: Path):
    contracts = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    lua.v1.require_exact(luac, contracts["luac_sha256"])
    results = []
    for entry in contracts["entries"]:
        name = entry["name"]
        source_path = effective / f"scripts/x2ui/{name}.lua"
        input_path = effective / f"scriptsbin64/x2ui/{name}.alb"
        lua.v1.require_exact(source_path, entry["source_sha256"])
        baseline = effective_source(name, source_path.read_text(encoding="utf-8-sig"))
        compiled = compile_source(patch_source(name, baseline), luac)
        if len(compiled) > entry["size"]:
            raise RuntimeError(f"Sandbox ALB exceeds entry capacity: {name}")
        replacement = compiled + bytes(entry["size"] - len(compiled))
        after = hashlib.sha256(replacement).hexdigest().upper()
        if after != entry["patched_sha256"]:
            raise RuntimeError(f"Non-reproducible sandbox output: {name}: {after}")
        before = lua.v1.sha256(input_path)
        accepted = [entry["alb_sha256"], *entry.get("previous_patched_sha256", []), after]
        if input_path.stat().st_size != entry["size"] or before not in accepted:
            raise RuntimeError(f"Unknown effective sandbox ALB: {name}: {before}")
        if before == entry["alb_sha256"] and lua.semantic_chunk(compile_source(baseline, luac)) != lua.semantic_chunk(input_path.read_bytes()):
            raise RuntimeError(f"Effective source/ALB semantic mismatch: {name}")
        target = output / f"{name}.alb"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(replacement)
        results.append({"name": name, "before": before, "after": after,
                        "size": entry["size"], "replacement": str(target),
                        "source_bytecode_equivalent": True})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--effective", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--luac", type=Path, default=Path("E:/AAEmu-Research/work/lua-5.1.5-msvc/lua-5.1.5/src/luac51.exe"))
    args = parser.parse_args()
    print(json.dumps(build(args.effective, args.output, args.luac), indent=2))


if __name__ == "__main__":
    main()
