import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_bug_reports import MOCK, LUA
import ApplyAa10SpanishUiLayout as tools
import PatchAa10GmPanel as patch

EXTRA = r'''
function CreateEmptyWindow(id) return CreateWindow(id) end
function SetVerticalTooltip(t,w) tooltip=t end
function HideTooltip() tooltip=nil end
function Tick(ms) uiClock=uiClock+ms; widgets.aa10GmRoot.handlers.OnUpdate() end
function Event(event) widgets.aa10GmRoot.handlers.OnEvent(nil,event) end
function Hex(t) return (string.gsub(t,".",function(c) return string.format("%02x",string.byte(c)) end)) end
function Reply(kind,payload,sender,id)
 id=id or string.match(sent[#sent],"^aa10gm1:([0-9a-f]+):")
 widgets.aa10GmRoot.handlers.OnEvent(nil,"CHAT_MESSAGE",-2,0,sender or "DAILY_MSG","AA10GM1:"..id..":"..kind..":"..payload)
end
function Payload()
 local id=string.match(sent[#sent],"^aa10gm1:([0-9a-f]+):");local text=""
 for _,s in ipairs(sent) do local r,p=string.match(s,"^aa10gm1:([0-9a-f]+):%d+:%d+:(.*)$");if r==id then text=text..p end end
 return text
end
function Open()
 Event("ENTERED_WORLD");Tick(1500);Reply("access","1");Click("gmShortcut")
 Reply("entry","ignoreskillcds/combat/"..Hex("Sin reutilización").."/"..Hex("ignorecd"))
 Reply("entry","scripts/admin/"..Hex("Apagar servidor").."/"..Hex("scripts"))
 Reply("listed","2")
end
function Detail(name)
 Reply("meta",name.."/0/"..Hex("true"))
 Reply("chunk","1/"..Hex("Descripción\nUso del servidor"));Reply("detail","1")
end
'''

class GmPanelTests(unittest.TestCase):
    def lua(self, body):
        source = MOCK + EXTRA + (tools.REPO/'Scripts/lua/GmPanel.lua').read_text(encoding='utf-8')
        source += '\n' + (tools.REPO/'Scripts/lua/GmPanelShortcut.lua').read_text(encoding='utf-8') + '\n' + body
        result = subprocess.run([str(LUA), '-'], input=source.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def test_hud_requires_matching_server_authorization(self):
        self.lua('''
        assert(not widgets.gmShortcut.visible)
        assert(widgets.gmShortcut.normal and widgets.gmShortcut.highlight and widgets.gmShortcut.pushed and widgets.gmShortcut.disabled)
        Event("ENTERED_WORLD");Tick(1500)
        Reply("access","1","forged");assert(not widgets.gmShortcut.visible)
        Reply("access","1",nil,"ffffff");assert(not widgets.gmShortcut.visible)
        Reply("access","1");assert(widgets.gmShortcut.visible)
        Event("ENTERED_LOADING");assert(not widgets.gmShortcut.visible)
        ''')

    def test_search_alias_categories_help_favorites_and_dispatch(self):
        self.lua('''
        Open();assert(widgets.gmRow1:GetText()=="/ignoreskillcds")
        widgets.gmSearch:SetText("ignorecd");widgets.gmSearch.handlers.OnTextChanged()
        assert(widgets.gmRow1.enabled and not widgets.gmRow2.enabled)
        Click("gmRow1");assert(Payload()=="detail/ignoreskillcds");assert(not widgets.gmExecute.enabled)
        Detail("ignoreskillcds");Click("gmTrue");Click("gmFavorite")
        Click("gmCatfavorites");assert(widgets.gmRow1:GetText()=="* /ignoreskillcds")
        Click("gmExecute");assert(Payload()=="run/"..Hex("ignoreskillcds true"))
        Reply("done","Enviado");assert(widgets.gmExecute.enabled)
        Click("gmQuickDummy");assert(Payload()=="run/"..Hex("spawn npc dummy"))
        Reply("done","Enviado");Event("LEFT_WORLD");assert(not widgets.aa10GmPanel.visible)
        ''')

    def test_confirmation_changes_timeout_and_incomplete_detail_fail_closed(self):
        self.lua('''
        Open();Click("gmRow2");Detail("scripts")
        widgets.gmArgs:SetText("shutdown");widgets.gmArgs.handlers.OnTextChanged()
        Click("gmExecute");Reply("confirm","17")
        assert(widgets.gmExecute:GetText()=="Confirmar")
        widgets.gmArgs:SetText("save");widgets.gmArgs.handlers.OnTextChanged()
        assert(widgets.gmExecute:GetText()=="Ejecutar")
        Click("gmExecute");Reply("confirm","18");Click("gmExecute");assert(Payload()=="confirm/18")
        Tick(15001);assert(not widgets.gmExecute.enabled)
        ''')

    def test_chunk_loss_does_not_enable_execution(self):
        self.lua('''Open();Click("gmRow1");Reply("meta","ignoreskillcds/0/")
        Reply("chunk","2/"..Hex("Lost"));Reply("detail","2");assert(not widgets.gmExecute.enabled)''')

    def test_pinned_builder_preserves_previous_extensions_and_rejects_drift(self):
        effective = tools.ROOT/'artifacts/gm-panel-20260920/effective'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); shutil.copytree(effective, root/'effective')
            first = patch.build(root/'effective', root/'one', tools.LUAC)
            for result in first:
                target = root/'effective/scriptsbin64/x2ui'/f"{result['name']}.alb"
                shutil.copyfile(result['replacement'], target)
            second = patch.build(root/'effective', root/'two', tools.LUAC)
            self.assertTrue(all(r['before'] == r['after'] for r in second))
            target.write_bytes(b'x'*target.stat().st_size)
            with self.assertRaises(ValueError): patch.build(root/'effective', root/'bad', tools.LUAC)

if __name__ == '__main__': unittest.main()
