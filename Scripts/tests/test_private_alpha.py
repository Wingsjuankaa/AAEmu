from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import sys
import sqlite3
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import PatchAa10PrivateAlpha as patch
from ApplyAa10SpanishUiLayout import transaction

LUA = Path(os.environ.get('AA10_LUA51', 'E:/AAEmu/rama_10/localization/aa10-es-es/work/ui-layout-v2/lua-runtime/lua51.exe'))

MOCK = '''
widgets, sent = {}, {}
uiClock = 600000
X2Time={GetUiMsec=function() return uiClock end}
ALIGN_LEFT = 1
local function Widget(id)
    local w = { id=id, handlers={}, enabled=true, visible=true, text="" }
    widgets[id]=w
    w.style=setmetatable({}, {__index=function() return function() end end})
    function w:SetText(v) self.text=v; if self.handlers.OnTextChanged then self.handlers.OnTextChanged(self) end end
    function w:GetText() return self.text end
    function w:Enable(v) self.enabled=v end
    function w:Show(v) self.visible=v end
    function w:IsVisible() return self.visible end
    function w:SetHandler(k,v) self.handlers[k]=v end
    function w:CreateChildWidget(kind,name) local c=Widget(name); self[name]=c; return c end
    return setmetatable(w,{__index=function() return function() end end})
end
function CreateWindow(id) return Widget(id) end
function CreateIconButton(id) return Widget(id) end
W_CTRL={CreateEdit=function(id) return Widget(id) end}
X2Bag={ItemIdentifier=function() return selectedItem or 900001 end}
X2Chat={JoinUserChatChannel=function(self,name,password) assert(#name<=48 and password==""); sent[#sent+1]=name end}
X2Item={GetItemInfoByType=function(self,id) return {name="Item",itemType=id} end,Name=function(self,id) return "Item "..id end}
function Respond(kind,payload,sender,channel)
    local id=string.match(sent[#sent],"^aa10ap1:([0-9a-f]+):")
    widgets.aa10PrivateAlphaPanel.handlers.OnEvent(nil,"CHAT_MESSAGE",channel or -2,0,sender or "DAILY_MSG","AA10AP1:"..id..":"..kind..":"..payload)
end
function Click(id) local w=widgets[id]; if w.enabled then w.handlers.OnClick() end end
function Tick(ms) uiClock=uiClock+ms; widgets.aa10PrivateAlphaPanel.handlers.OnUpdate(nil,uiClock) end
'''


class PrivateAlphaPatchTests(unittest.TestCase):
    def test_honor_and_vocation_require_ack_validate_amount_and_never_repeat(self):
        self.lua('''
        Aa10PrivateAlpha.Open()
        assert(not widgets.gethonor.enabled and not widgets.getvocation.enabled)
        Respond("open","10000,5000,1000")
        for _, resource in ipairs({"honor", "vocation"}) do
            for _, invalid in ipairs({"0", "-1", "1.5", "100001", "abc"}) do
                widgets[resource]:SetText(invalid)
                local before=#sent; Click("get"..resource); assert(#sent==before)
            end
            widgets[resource]:SetText("100000"); Click("get"..resource)
            assert(string.find(sent[#sent],resource.."/100000",1,true))
            local before=#sent; Click("get"..resource); assert(#sent==before)
            Respond("ok","Entrega completada y guardada.")
            Tick(21000); assert(#sent==before)
        end
        Click("gethonor"); Respond("denied","Revocado")
        assert(not widgets.gethonor.enabled and not widgets.getvocation.enabled)
        ''')

    def test_native_layout_rejects_zero_padding_and_repairs_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'compact.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE items(id INTEGER PRIMARY KEY, name TEXT)')
                db.execute("INSERT INTO items VALUES(900001, 'Llave de alpha privada')")
                db.execute('PRAGMA schema_version=1007')
                db.commit()
                page_size = db.execute('PRAGMA page_size').fetchone()[0]
            # Exceed one freelist trunk, like the real 5303-page regression.
            size = path.stat().st_size + page_size * 5303
            with path.open('ab') as f:
                f.truncate(size)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(), ('ok',))
            with self.assertRaisesRegex(ValueError, 'Unregistered SQLite pages'):
                patch.verify_sqlite_layout(path, size, 1006)
            patch.preserve_sqlite_size(path, size, 1006)
            with self.assertRaisesRegex(ValueError, 'Native freelist leaf count too big'):
                patch.verify_sqlite_layout(path, size, 1006)
            patch.make_freelist_native_compatible(path)
            patch.verify_sqlite_layout(path, size, 1006)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT * FROM items').fetchall(), [(900001, 'Llave de alpha privada')])
                self.assertEqual(db.execute('PRAGMA freelist_count').fetchone()[0], 5303)
            before = patch.sha(path)
            patch.make_freelist_native_compatible(path)
            patch.verify_sqlite_layout(path, size, 1006)
            self.assertEqual(before, patch.sha(path))

    def lua(self, body):
        self.assertTrue(LUA.is_file(), 'Requires the pinned local Lua 5.1 runtime')
        source = MOCK + '\n' + patch.LUA.read_text(encoding='utf-8') + '\n' + body
        result = subprocess.run([str(LUA), '-'], input=source.encode('utf-8'), capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def test_open_requires_real_key_and_server_ack_and_ignores_forged_player_ack(self):
        self.lua('''
        selectedItem=1; assert(not Aa10PrivateAlpha.PreUse(1) and #sent==0)
        selectedItem=900001; assert(Aa10PrivateAlpha.PreUse(1) and #sent==1)
        assert(not widgets.getgold.enabled)
        Respond("open","10000,5000,1000","forged-player")
        assert(not widgets.getgold.enabled)
        Respond("open","10000,5000,1000","DAILY_MSG",0)
        assert(not widgets.getgold.enabled)
        Respond("open","10000,5000,1000","")
        assert(not widgets.getgold.enabled)
        Respond("open","10000,5000,1000")
        assert(widgets.getgold.enabled)
        Click("getgold"); assert(#sent==2 and not widgets.getgold.enabled)
        Click("getgold"); assert(#sent==2)
        Respond("denied","Revocado"); assert(not widgets.getgold.enabled)
        ''')

    def test_utf8_search_paging_item_grant_empty_result_and_no_automatic_retry(self):
        self.lua('''
        Aa10PrivateAlpha.Open(); Respond("open","10000,5000,1000")
        widgets.search:SetText("Infusión"); Click("find"); Tick(500)
        Respond("page","0/2/11/45338,45339")
        assert(widgets.alphaTake1.enabled and widgets.alphaTake2.enabled and not widgets.alphaTake3.enabled)
        widgets.count:SetText("0"); local before=#sent; Click("alphaTake1"); assert(#sent==before)
        widgets.count:SetText("5"); widgets.grade:SetText("13"); Click("alphaTake1"); assert(#sent==before)
        widgets.grade:SetText("4"); Click("alphaTake1")
        assert(string.find(sent[#sent],"item/45338/5/4",1,true))
        before=#sent; uiClock=uiClock+21000; widgets.aa10PrivateAlphaPanel.handlers.OnUpdate(nil,21000)
        assert(#sent==before and widgets.getgold.enabled)
        Click("find"); Tick(500); Respond("page","0/1/0/")
        assert(not widgets.alphaTake1.enabled)
        ''')

    def test_unknown_native_consumer_fails_closed(self):
        with self.assertRaises(ValueError): patch.modify_source('unknown source')

    def test_live_search_debounces_keeps_typing_and_discards_stale_page(self):
        self.lua('''
        Aa10PrivateAlpha.Open(); Respond("open","10000,5000,1000")
        widgets.search:SetText("D"); Tick(250)
        widgets.search:SetText("Dec"); Tick(499); assert(#sent==1)
        Tick(1); assert(#sent==2 and widgets.search.enabled)
        assert(string.find(sent[#sent],"search/0/446563",1,true))
        widgets.search:SetText("Jarrón"); Tick(600)
        assert(#sent==2 and not widgets.alphaTake1.enabled)
        Respond("page","0/1/1/98")
        assert(not widgets.alphaTake1.enabled)
        Tick(0); local before=#sent
        assert(string.find(sent[#sent],"4a617272c3b36e",1,true))
        Respond("page","0/5/49/98,99")
        assert(widgets.alphaTake1.enabled and widgets.next.enabled and not widgets.previous.enabled)
        Tick(2000); assert(#sent==before)
        widgets.search:SetText(""); Tick(500)
        assert(string.find(sent[#sent],"search/0/",1,true))
        Respond("page","0/5101/51010/3,5")
        assert(widgets.alphaTake1.enabled)
        ''')

    def test_live_search_cancel_on_world_exit_and_hidden_window_and_timeout(self):
        self.lua('''
        Aa10PrivateAlpha.Open(); Respond("open","10000,5000,1000")
        widgets.search:SetText("98"); widgets.aa10PrivateAlphaPanel:Show(false)
        Tick(600); assert(#sent==1)
        widgets.aa10PrivateAlphaPanel:Show(true); Tick(0); assert(#sent==2)
        Tick(20001); local before=#sent; Tick(21000); assert(#sent==before)
        assert(widgets.search.enabled)
        widgets.search:SetText("99")
        widgets.aa10PrivateAlphaPanel.handlers.OnEvent(nil,"ENTERED_LOADING")
        Tick(1000); assert(#sent==before and not widgets.search.enabled)
        ''')

    def test_large_update_argument_cannot_expire_a_fresh_request(self):
        self.lua('''
        Aa10PrivateAlpha.Open()
        uiClock=uiClock+16
        widgets.aa10PrivateAlphaPanel.handlers.OnUpdate(nil,600016)
        assert(string.find(widgets.note.text,"Esperando",1,true))
        Respond("open","10000,5000,1000")
        assert(widgets.getgold.enabled and widgets.find.enabled)
        Click("getgold"); local before=#sent
        uiClock=uiClock+19999
        widgets.aa10PrivateAlphaPanel.handlers.OnUpdate(nil,999999)
        assert(not widgets.getgold.enabled)
        uiClock=uiClock+2
        widgets.aa10PrivateAlphaPanel.handlers.OnUpdate(nil,1)
        assert(widgets.getgold.enabled and #sent==before)
        assert(string.find(widgets.note.text,"Sin respuesta",1,true))
        ''')

    def test_multi_entry_failure_rolls_back_attempted_writes_in_reverse_order(self):
        a = {'before': 'a', 'after': 'A'}; b = {'before': 'b', 'after': 'B'}
        seen = []
        def write(e):
            seen.append(e['after'])
            if e is b: raise RuntimeError('write failed')
        with self.assertRaises(RuntimeError): transaction([a,b], write, lambda: None, lambda e: seen.append(e['before']))
        self.assertEqual(seen, ['A','B','b','a'])


if __name__ == '__main__': unittest.main()
