import json
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import PatchAa10SandboxAutoEntry as patch
import ApplyAa10SandboxAutoEntry as apply

EFFECTIVE = Path(os.environ.get("AA10_SANDBOX_EFFECTIVE", "E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/sandbox-intake-20261029/autoentry/effective"))
LUA = Path(os.environ.get("AA10_SANDBOX_LUA", "E:/AAEmu/rama_10/artifacts/sandbox/lua51/lua51.exe"))
LUAC = Path("E:/AAEmu-Research/work/lua-5.1.5-msvc/lua-5.1.5/src/luac51.exe")


class SafetyTests(unittest.TestCase):
    def test_reusing_full_hash_requires_same_physical_package_identity(self):
        patch.TEMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=patch.TEMP) as directory:
            root = Path(directory)
            pak = root / "package.bin"; pak.write_bytes(b"original")
            stat = pak.stat(); digest = hashlib.sha256(pak.read_bytes()).hexdigest().upper()
            marker = root / "marker.json"
            marker.write_text(json.dumps({"package_path": str(pak), "package_size": stat.st_size,
                "package_mtime_ns": stat.st_mtime_ns, "package_inode": stat.st_ino,
                "package_sha256": digest}))
            self.assertEqual(apply.verified_before_hash(pak, marker), digest)
            os.utime(pak, ns=(stat.st_atime_ns, stat.st_mtime_ns + 100))
            with self.assertRaisesRegex(RuntimeError, "no longer binds"):
                apply.verified_before_hash(pak, marker)

    def test_wibo_metadata_ignores_unrelated_non_utf8_names(self):
        from Aa10PakAppend import aes, aligned
        name = "game/scriptsbin64/x2ui/loginstage_new/connect/stage_server.alb"
        record = bytearray(336); record[:len(name)] = name.encode()
        struct.pack_into("<q", record, 320, 134262620298410395)
        unrelated = bytearray(336); unrelated[:4] = b"bad\xb2"
        records = aes(bytes(unrelated), True) + aes(bytes(record), True)
        header = bytearray(32); header[:8] = b"WIBO\0\0\0\0"
        struct.pack_into("<II", header, 8, 2, 0)
        payload = bytes(512) + records + bytes(aligned(len(records))-len(records)) + aes(bytes(header), True) + bytes(480)
        patch.TEMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=patch.TEMP) as directory:
            pak = Path(directory) / "package.bin"; pak.write_bytes(payload)
            self.assertEqual(apply.entry_modify_times(pak, [name]), {name: 134262620298410395})

    def test_exact_filetime_roundtrip_uses_integer_nanoseconds(self):
        patch.TEMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=patch.TEMP) as directory:
            target = Path(directory) / "timestamp.bin"
            target.write_bytes(b"metadata")
            filetime = 134262620298410395
            apply.set_modify_time(target, filetime)
            self.assertEqual(target.stat().st_mtime_ns, (filetime - 116444736000000000) * 100)

    def test_unknown_source_and_consumer_rejected(self):
        with self.assertRaises(RuntimeError):
            patch.patch_source("loginstage_new/connect/stage_server", "")
        with self.assertRaises(ValueError):
            patch.effective_source("other", "")

    def test_rejects_primary_client_and_c_output(self):
        with self.assertRaisesRegex(RuntimeError, "dedicated"):
            apply.preflight(apply.PRIMARY, False)
        with self.assertRaisesRegex(RuntimeError, "stay on E"):
            apply.require_e(Path("C:/sandbox"))

    def test_contracts_are_frozen_and_patch_is_opt_in(self):
        contracts = json.loads(patch.CONTRACTS.read_text())
        self.assertEqual(contracts["character"], "Sandbox")
        self.assertEqual(contracts["zone_key"], 379)
        for entry in contracts["entries"]:
            for key in ("source_sha256", "alb_sha256", "patched_sha256"):
                self.assertEqual(len(entry[key]), 64)
        self.assertIn('Console:GetAttribute("client_default_zone")', patch.GATE)


@unittest.skipUnless(EFFECTIVE.exists() and LUA.exists() and LUAC.exists(), "Exact r575 extracts and Lua compiler/interpreter required")
class RetailTests(unittest.TestCase):
    def execute(self, source):
        result = subprocess.run([str(LUA), "-"], input=source.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def source(self, name):
        return (EFFECTIVE / f"scripts/x2ui/{name}.lua").read_text(encoding="utf-8-sig")

    def character_fixture(self):
        name = "loginstage_new/character_select/character_select"
        source = patch.patch_source(name, patch.effective_source(name, self.source(name)))
        # Execute the real patched retail SelectCharacter and TryToEnterGame,
        # rather than a test-only reconstruction of their validation logic.
        native = source.split("local function TryToEnterGame", 1)[1].split("function startBtn:OnClick()", 1)[0]
        return patch.GATE + '''
local dev, zone, realm, visible, queue, preselect = false, -1, "AA10 Sandbox", true, 0, false
local names, last, calls, showCalls = {"Other", "Sandbox"}, 1, {}, 0
local blocked, deleted, rename, transfer = false, false, false, false
X2Debug={GetDevMode=function() return dev end}
Console={GetAttribute=function() return zone end}
X2World={IsPreSelectCharacterPeriod=function() return preselect end,
 GetCurrentWorldName=function() return realm end}
X2Player={GetFeatureSet=function() return {forbidTransferChar=true} end}
background={IsVisible=function() return visible end, Enable=function() end}
UIParent={Log=function() end}
F_SOUND={PlayUISound=function() end}
X2LoginCharacter={
 GetWorldQueuePosition=function() return queue end,
 GetNumLoginCharacters=function() return #names end,
 GetLoginCharacterName=function(self,index) return names[index] end,
 GetLastPlayedCharacterIndex=function() return last end,
 IsInEnableStartingLocation=function() return not blocked end,
 IsDeleteRequestedCharacter=function() return deleted end,
 IsForceNameChangedCharacter=function() return rename end,
 IsTransferRequestedCharacter=function() return transfer end,
 CheckPremiumUserServer=function() return true end,
 CanShowClientDrivenSkipDialog=function() return false end,
 SelectCharacter=function(self,index,skip) table.insert(calls,{index=index,skip=skip}) end
}
function GetRemainCreatableCharacterCount() return 0 end
function ShowCharacter(index) last=index; showCalls=showCalls+1 end
''' + "local function TryToEnterGame" + native + patch.character_controller()

    def test_exact_name_preview_then_single_native_selection(self):
        self.execute(self.character_fixture() + '''
Aa10SandboxStep(499); assert(#calls==0 and showCalls==0)
Aa10SandboxStep(1); assert(last==2 and showCalls==1 and #calls==0)
Aa10SandboxStep(500); assert(#calls==1 and calls[1].index==2 and calls[1].skip==true)
Aa10SandboxStep(5000); assert(#calls==1 and showCalls==1)
''')

    def test_wrong_realm_wrong_character_and_hidden_do_nothing(self):
        self.execute(self.character_fixture() + '''
realm=nil; Aa10SandboxStep(500); assert(#calls==0 and showCalls==0)
realm="Ordinary World"; Aa10SandboxStep(500); assert(#calls==0 and showCalls==0)
realm="AA10 Sandbox"; names={"Other"}; Aa10SandboxStep(500); assert(#calls==0 and showCalls==0)
names={"Other","Sandbox"}; visible=false; Aa10SandboxStep(500); assert(#calls==0 and showCalls==0)
''')

    def test_queue_native_restrictions_and_preselection_are_respected(self):
        self.execute(self.character_fixture() + '''
last=2
queue=1; Aa10SandboxStep(500); assert(#calls==0)
queue=0; preselect=true; Aa10SandboxStep(500); assert(#calls==0)
preselect=false; blocked=true; Aa10SandboxStep(500); assert(#calls==0)
blocked=false; deleted=true; Aa10SandboxStep(500); assert(#calls==0)
deleted=false; rename=true; Aa10SandboxStep(500); assert(#calls==0)
rename=false; transfer=true; Aa10SandboxStep(500); assert(#calls==0)
transfer=false; Aa10SandboxStep(500); assert(#calls==1)
''')

    def test_other_characters_keep_normal_prologue_flag(self):
        self.execute(self.character_fixture() + '''
SelectCharacter(1); assert(#calls==1 and calls[1].skip==false)
calls={}; last=2; realm="Ordinary World"; SelectCharacter(2)
assert(#calls==1 and calls[1].skip==false)
''')

    def test_world_selection_waits_for_exact_shard_and_runs_once(self):
        self.execute(patch.GATE + '''
local dev, zone, requested = false, -1, {}
X2Debug={GetDevMode=function() return dev end}
Console={GetAttribute=function() return zone end}
UIParent={Log=function() end}
local worldListWnd={SelectByDataKey=function() end}
local wnd={SelectServer=function(self,id) table.insert(requested,id) end,
 SetHandler=function() end}
''' + patch.world_controller() + '''
Aa10SandboxTryWorld({{id=2,name="AA10 Sandbox"}}); assert(#requested==0)
Aa10SandboxTryWorld({{id=1,name="Ordinary World"}}); assert(#requested==0)
Aa10SandboxTryWorld({{id=1}}); assert(#requested==0)
Aa10SandboxTryWorld({{id=2},{id=1,name="AA10 Sandbox"}}); assert(#requested==1 and requested[1]==1)
Aa10SandboxTryWorld({{id=1,name="AA10 Sandbox"}}); assert(#requested==1)
''')

    def widget_fixture(self):
        return r'''
local widgets, logs, worldInfos, requests = {}, {}, {}, {}
local realm="AA10 Sandbox"
local function widget(name)
 local w={visible=false,handlers={},name=name}
 w.style=setmetatable({}, {__index=function() return function() end end})
 local methods={
  Show=function(self,show)
   local changed=self.visible~=show; self.visible=show
   local handler=self.handlers[show and "OnShow" or "OnHide"]
   if changed and handler then handler(self) end
  end,
  IsVisible=function(self) return self.visible end,
  SetHandler=function(self,event,handler) self.handlers[event]=handler end,
  CreateChildWidget=function(self,kind,id) return widget(id) end,
  CreateDrawable=function() return widget("drawable") end,
  GetOffset=function() return 0,0 end,
  GetExtent=function() return 100,20 end,
  GetTextHeight=function() return 20 end
 }
 setmetatable(w,{__index=function(self,key) return methods[key] or function() end end})
 widgets[name]=w; return w
end
UIParent=widget("UIParent")
UIParent.Log=function(self,text) table.insert(logs,text) end
CreateEmptyWindow=widget
CreateWorldListWnd=widget
CreateAuthMessageWindow=widget
CreateWorldQueueWindow=widget
CreateAccountInfoWnd=widget
CreateCharacterInfoWnd=widget
CreateCharacterListWnd=widget
CreateMenuWnd=widget
CreateCharacterSelectQueueWindow=widget
X2Debug={GetDevMode=function() return false end}
Console={GetAttribute=function() return "-1" end}
X2Util={GetVersionInfo=function() return "r575" end}
X2World={GetCharactersDefaultLimitPerWorld=function() return 6 end,
 GetCharactersDefaultLimitPerAccount=function() return 6 end,
 GetCharacterExpandableLimit=function() return 0 end,
 GetCurrentWorldName=function() return realm end,
 IsPreSelectCharacterPeriod=function() return false end,
 EnterWorld=function(self,world,zone) table.insert(requests,{world=world,zone=zone});return true end}
X2Player={GetFeatureSet=function() return {forbidTransferChar=true} end}
local lastIndex=1
X2LoginCharacter={GetLastPlayedWorldInfo=function() return nil end,
 GetNumLoginCharacters=function() return 2 end,
 GetWorldQueuePosition=function() return 0 end,
 GetLastPlayedCharacterIndex=function() return lastIndex end,
 GetLoginCharacterName=function(self,index) return index==2 and "Sandbox" or "Other" end,
 IsInEnableStartingLocation=function() return true end,
 IsDeleteRequestedCharacter=function() return false end,
 IsForceNameChangedCharacter=function() return false end,
 IsTransferRequestedCharacter=function() return false end,
 CheckPremiumUserServer=function() return true end,
 CanShowClientDrivenSkipDialog=function() return false end,
 ShowSelectedCharacter=function(self,index) lastIndex=index end,
 SelectCharacter=function(self,index,skip) table.insert(requests,{index=index,skip=skip}) end}
F_SOUND={PlayUISound=function() end}
FONT_SIZE={MIDDLE=16,LARGE=20};FONT_PATH={SUB="font"}
TEXTURE_PATH={SERVER_SELECT="server"}
characterSelectLocale={showReturnServer=false}
locale={server={max_character_count_warning=function() return "count" end}}
function GetWorldListInfos() return worldInfos end
function SortWorldListIndices() return {},{} end
function RegistUIEvent() end
function GetUIText() return "text" end
function GetCommonText() return "text" end
function GetRemainCreatableCharacterCount() return 0 end
'''

    def test_actual_world_window_handlers_poll_late_data_with_release_devmode_false(self):
        name = "loginstage_new/connect/stage_server"
        source = patch.patch_source(name, patch.effective_source(name, self.source(name)))
        self.execute(self.widget_fixture() + source + r'''
local wnd=CreateServerWnd("serverWnd")
wnd:Show(true)
assert(#requests==0)
worldInfos={{id=1,name="Ordinary World"}}
wnd.handlers.OnUpdate(wnd,250);assert(#requests==0)
worldInfos={{id=1,name="AA10 Sandbox"}}
assert(type(wnd.handlers.OnUpdate)=="function")
wnd.handlers.OnUpdate(wnd,249);assert(#requests==0)
wnd.handlers.OnUpdate(wnd,1);assert(#requests==1)
assert(requests[1].world==1 and requests[1].zone==379)
wnd.handlers.OnUpdate(wnd,1000);assert(#requests==1)
assert(string.find(logs[1], '"dev_mode":false', 1, true))
assert(string.find(logs[1], '"marker":-1', 1, true))
assert(string.find(logs[#logs], '"event":"world_request"', 1, true))
''')

    def test_manual_world_entry_keeps_native_zone_default(self):
        name = "loginstage_new/connect/stage_server"
        source = patch.patch_source(name, patch.effective_source(name, self.source(name)))
        self.execute(self.widget_fixture() + source + r'''
local wnd=CreateServerWnd("serverWnd")
worldInfos={{id=1,name="Ordinary World"}}
wnd:Show(true)
wnd.handlers.OnUpdate(wnd,500);assert(#requests==0)
wnd:SelectServer(1)
assert(#requests==1 and requests[1].world==1 and requests[1].zone==-1)
''')

    def test_actual_character_window_onupdate_dispatches_native_selection_with_release_gate(self):
        name = "loginstage_new/character_select/character_select"
        source = patch.patch_source(name, patch.effective_source(name, self.source(name)))
        self.execute(self.widget_fixture() + source + r'''
local wnd=widgets.background
realm="Ordinary World"
wnd.handlers.OnUpdate(wnd,500);assert(#requests==0)
realm="AA10 Sandbox"
assert(type(wnd.handlers.OnUpdate)=="function")
wnd.handlers.OnUpdate(wnd,500);assert(#requests==0)
wnd.handlers.OnUpdate(wnd,500);assert(#requests==1)
assert(requests[1].index==2 and requests[1].skip==true)
wnd.handlers.OnUpdate(wnd,1000);assert(#requests==1)
assert(string.find(logs[1], '"dev_mode":false', 1, true))
assert(string.find(logs[1], '"marker":-1', 1, true))
assert(string.find(logs[#logs], '"event":"character_request"', 1, true))
''')

    def test_two_identical_builds_and_corruption_rejected(self):
        patch.TEMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=patch.TEMP) as directory:
            root = Path(directory)
            first = patch.build(EFFECTIVE, root / "first", LUAC)
            second = patch.build(EFFECTIVE, root / "second", LUAC)
            self.assertEqual([e["after"] for e in first], [e["after"] for e in second])
            corrupt = root / "corrupt"
            for e in json.loads(patch.CONTRACTS.read_text())["entries"]:
                for prefix, suffix in (("scripts", "lua"), ("scriptsbin64", "alb")):
                    rel = f"{prefix}/x2ui/{e['name']}.{suffix}"
                    target = corrupt / rel; target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(EFFECTIVE / rel, target)
            bad = corrupt / "scriptsbin64/x2ui/loginstage_new/connect/stage_server.alb"
            data = bytearray(bad.read_bytes()); data[-1] ^= 1; bad.write_bytes(data)
            with self.assertRaisesRegex(RuntimeError, "Unknown effective"):
                patch.build(corrupt, root / "rejected", LUAC)
            # Installing the exact outputs a second time is recognized by hash.
            for e in first:
                shutil.copyfile(e["replacement"], corrupt / f"scriptsbin64/x2ui/{e['name']}.alb")
            repeated = patch.build(corrupt, root / "repeated", LUAC)
            self.assertTrue(all(e["before"] == e["after"] for e in repeated))


if __name__ == "__main__":
    unittest.main()
