import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_bug_reports import MOCK,LUA
from test_private_alpha import patch as panel
import PatchAa10AlphaShortcut as shortcut
import ApplyAa10SpanishUiLayout as tools

EXTRA='''
function CreateEmptyWindow(id) return CreateWindow(id) end
function SetVerticalTooltip(text) tooltip=text end
function HideTooltip() tooltip=nil end
function HudTick(ms) uiClock=uiClock+ms; widgets.aa10AlphaShortcut.handlers.OnUpdate() end
function HudEvent(event) widgets.aa10AlphaShortcut.handlers.OnEvent(nil,event) end
function AccessReply(value,sender,id)
    id=id or string.match(sent[#sent],"^aa10ap1:([0-9a-f]+):")
    widgets.aa10AlphaShortcut.handlers.OnEvent(nil,"CHAT_MESSAGE",-2,0,sender or "DAILY_MSG","AA10AP1:"..id..":access:"..value)
end
'''

class AlphaShortcutTests(unittest.TestCase):
    def lua(self,body):
        text=MOCK+EXTRA+panel.LUA.read_text(encoding='utf-8')+'\n'+shortcut.LUA.read_text(encoding='utf-8')+'\n'+body
        r=subprocess.run([str(LUA),'-'],input=text.encode(),capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'))

    def test_hidden_until_server_authorizes_and_opens_without_using_key(self):
        self.lua('''
        assert(not widgets.alphaShortcut.visible)
        HudEvent("ENTERED_WORLD"); HudTick(1499); assert(#sent==0)
        HudTick(1); assert(string.find(sent[1],":1:1:access",1,true))
        AccessReply("1","forged"); assert(not widgets.alphaShortcut.visible)
        AccessReply("1",nil,"ffffffff"); assert(not widgets.alphaShortcut.visible)
        AccessReply("1"); assert(widgets.alphaShortcut.visible)
        selectedItem=1; Click("alphaShortcut"); assert(string.find(sent[#sent],":open",1,true))
        assert(not widgets.getgold.enabled); Respond("open","10000,5000,1000"); assert(widgets.getgold.enabled)
        widgets.alphaShortcut.handlers.OnEnter(); assert(tooltip=="Alpha privada")
        AccessReply("0",nil,"0"); assert(not widgets.alphaShortcut.visible and not widgets.alphaShortcut.enabled)
        local before=#sent; Click("alphaShortcut"); assert(#sent==before)
        ''')

    def test_poll_is_read_only_loading_clears_access_and_timeout_hides_icon(self):
        self.lua('''
        HudEvent("ENTERED_WORLD"); HudTick(1500); AccessReply("1")
        HudTick(30000); local last=#sent; assert(last==2)
        assert(string.find(sent[last],":access",1,true)); HudTick(10001); assert(not widgets.alphaShortcut.visible)
        HudEvent("ENTERED_LOADING"); AccessReply("1",nil,"0"); HudTick(60000)
        assert(#sent==last and not widgets.alphaShortcut.visible)
        HudEvent("ENTERED_WORLD"); HudTick(1500); AccessReply("0"); assert(not widgets.alphaShortcut.visible)
        ''')

    def test_pinned_hud_builder_is_idempotent_and_rejects_drift(self):
        import tempfile,shutil
        evidence=tools.ROOT/'forensics/output/aa10-client-forensics/private-alpha-hud/effective'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);effective=root/'effective';shutil.copytree(evidence,effective)
            first=shortcut.build(effective,root/'one',tools.LUAC)[0]
            alb=effective/'scriptsbin64/x2ui/hud/shortcut.alb';shutil.copy2(first['replacement'],alb)
            second=shortcut.build(effective,root/'two',tools.LUAC)[0]
            self.assertEqual(second['before'],second['after'])
            alb.write_bytes(b'x'*alb.stat().st_size)
            with self.assertRaises(ValueError): shortcut.build(effective,root/'bad',tools.LUAC)

if __name__=='__main__': unittest.main()
