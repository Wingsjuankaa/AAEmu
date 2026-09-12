import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_private_alpha import MOCK, LUA
import PatchAa10BugReports as patch
import PatchAa10SpanishUiLayout as codec
import ApplyAa10SpanishUiLayout as apply
from Aa10LuaExtension import Reader, encode, append_extension
MOCK=MOCK.replace('function w:GetText()', '''function w:CreateImageDrawable(path,layer) local d=Widget(self.id..path); return d end
    function w:SetNormalBackground(d) self.normal=d end
    function w:SetHighlightBackground(d) self.highlight=d end
    function w:SetPushedBackground(d) self.pushed=d end
    function w:SetDisabledBackground(d) self.disabled=d end
    function w:SetMaxTextLength(n) self.maxTextLength=n end
    function w:SetReadOnly(v) self.readOnly=v end
    function w:GetText()''')
MOCK=MOCK.replace('return setmetatable(w,{__index=function() return function() end end})',
    'return setmetatable(w,{__index=function(_,k) if string.match(k,"^[A-Z]") then return function() end end end})')

EXTRA='''
W_TAB={}
function W_TAB.CreateTab(id,parent)
    local t=Widget(id); t.window={Widget(id.."one"),Widget(id.."two")}
    function t:AddTabs(titles) self.titles=titles end
    function t:EnableTab(index,on) self[index]=on end
    function t:SelectTab(index) if self[index] and self.OnTabChangedProc then self:OnTabChangedProc(index) end end
    return t
end
function SetVerticalTooltip(text,widget) tooltipText=text end
function HideTooltip() tooltipText=nil end
function CreateEmptyWindow(id) return CreateWindow(id) end
W_CTRL.CreateMultiLineEdit=W_CTRL.CreateEdit
function Flush()
    for i=1,300 do uiClock=uiClock+16; widgets.aa10BugShortcut.handlers.OnUpdate() end
end
function TickBug(ms) uiClock=uiClock+ms; widgets.aa10BugShortcut.handlers.OnUpdate() end
function BugResponse(kind,payload,sender)
    local id=string.match(sent[#sent],"^aa10br1:([0-9a-f]+):")
    widgets.aa10BugShortcut.handlers.OnEvent(nil,"CHAT_MESSAGE",-2,0,sender or "DAILY_MSG","AA10BR1:"..id..":"..kind..":"..payload)
end
function Payload()
    local id=string.match(sent[#sent],"^aa10br1:([0-9a-f]+):")
    local text=""
    for _,s in ipairs(sent) do
        local r,part=string.match(s,"^aa10br1:([0-9a-f]+):%d+:%d+:(.*)$")
        if r==id then text=text..part end
    end
    return text
end
'''
class BugReportsTests(unittest.TestCase):
    def test_history_tabs_paging_detail_and_draft_survive(self):
        self.lua('''
        Aa10BugReport.Open(); Flush(); BugResponse("open","ready")
        widgets.bugDetail:SetText("Mi borrador sin enviar")
        widgets.bugTabs:SelectTab(2); Flush(); assert(Payload()=="mine/0")
        BugResponse("history","0/2/5"); BugResponse("entry","3/new/2026-09-11 23:39/quest/10029/476c61646965")
        assert(not widgets.bugHistory1.enabled)
        BugResponse("listed","1"); assert(widgets.bugHistory1.enabled and widgets.bugHistoryNext.enabled)
        assert(not widgets.bugHistoryPrevious.enabled)
        local before=#sent; Click("bugHistory1"); TickBug(399); assert(#sent==before)
        TickBug(1); Flush(); assert(Payload()=="read/3")
        BugResponse("report","3/new/2026-09-11 23:39/quest/10029/476c61646965")
        BugResponse("chunk","1/5445535420"); BugResponse("chunk","2/4445204552524f52"); BugResponse("read","2")
        assert(widgets.bugHistoryDetail:GetText()=="TEST DE ERROR")
        assert(widgets.bugHistoryDetail.readOnly and widgets.bugHistoryDetail.maxTextLength==600)
        widgets.bugTabs:SelectTab(1); assert(widgets.bugDetail:GetText()=="Mi borrador sin enviar")
        widgets.bugTabs:SelectTab(2); Flush(); BugResponse("history","0/1/0"); BugResponse("listed","0")
        assert(not widgets.bugHistory1.enabled and not widgets.bugHistoryNext.enabled)
        assert(string.find(widgets.bugNote:GetText(),"Todavía",1,true))
        ''')

    def test_history_timeout_missing_chunk_and_loading_cancel(self):
        self.lua('''
        Aa10BugReport.Open(); Flush(); BugResponse("open","ready")
        widgets.bugTabs:SelectTab(2); Flush()
        BugResponse("history","0/1/1"); BugResponse("entry","3/new/2026-09-11 23:39/quest/10029/476c61646965"); BugResponse("listed","1")
        Click("bugHistory1"); Flush(); BugResponse("chunk","2/626164"); BugResponse("read","2")
        assert(widgets.bugHistoryDetail:GetText()=="")
        Click("bugHistoryRefresh"); Flush(); TickBug(30001); local before=#sent; Flush(); assert(#sent==before)
        widgets.aa10BugShortcut.handlers.OnEvent(nil,"ENTERED_LOADING")
        before=#sent; Flush(); assert(#sent==before and not widgets.aa10BugReportPanel.visible)
        assert(widgets.bugHistory1:GetText()=="" and widgets.bugHistoryDetail:GetText()=="")
        ''')
    def test_icon_has_four_states_tooltip_and_opens_report_form(self):
        self.lua('''
        local b=widgets.bugShortcut
        assert(b:GetText()=="" and b.normal and b.highlight and b.pushed and b.disabled)
        b.handlers.OnEnter(); assert(tooltipText=="Reportar un error")
        b.handlers.OnLeave(); assert(tooltipText==nil)
        Click("bugShortcut"); assert(widgets.aa10BugReportPanel.visible)
        Flush(); assert(Payload()=="open")
        ''')
    def test_generated_catalog_contains_spanish_and_actual_english(self):
        path=apply.ROOT/'forensics/output/aa10-client-forensics/bug-reports/bug_report_catalog.json'
        rows=json.loads(path.read_text(encoding='utf-8'))
        vase=next(r for r in rows if r['Category']=='item' and r['Id']==98)
        self.assertEqual(vase['Name'],'Jarrón decorativo')
        self.assertEqual(vase['English'],'Decorative Vase')
        self.assertEqual(len({(r['Category'],r['Id']) for r in rows}),len(rows))
        self.assertLessEqual(max(len(r['Name']) for r in rows),1024)

    def lua(self,body):
        source=MOCK+EXTRA+patch.LUA.read_text(encoding='utf-8')+'\n'+body
        r=subprocess.run([str(LUA),'-'],input=source.encode('utf-8'),capture_output=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr.decode('utf-8',errors='replace'))

    def test_search_select_submit_ack_and_invalid_detail(self):
        self.lua('''
        Click("bugShortcut"); assert(not widgets.bugSubmit.enabled)
        Flush(); assert(Payload()=="open")
        BugResponse("open","ready","forged"); assert(not widgets.bugSearch.enabled)
        BugResponse("open","ready")
        widgets.bugSearch:SetText("98"); Flush(); assert(Payload()=="search/quest/0/3938")
        BugResponse("page","0/1/1/98,4d6973696f6e")
        Click("bugResult1"); assert(widgets.bugSubmit.enabled)
        widgets.bugDetail:SetText("short"); local before=#sent; Click("bugSubmit"); Flush(); assert(#sent==before)
        widgets.bugDetail:SetText("La misión no avanza al hablar.")
        Click("bugSubmit"); assert(not widgets.bugSubmit.enabled and not widgets.bugDetail.enabled)
        Flush(); assert(string.find(Payload(),"submit/quest/98/",1,true))
        before=#sent; Click("bugSubmit"); Flush(); assert(#sent==before)
        BugResponse("saved","42"); assert(widgets.bugDetail:GetText()=="")
        assert(string.find(widgets.bugNote:GetText(),"#42",1,true))
        ''')

    def test_timeout_manual_retry_retains_nonce_and_does_not_autosend(self):
        self.lua('''
        Aa10BugReport.Open(); Flush(); BugResponse("open","ready")
        Click("bugCategoryworld"); widgets.bugDetail:SetText("Me quedo atascado al caminar aquí.")
        Click("bugSubmit"); Flush(); local original=Payload(); local before=#sent
        TickBug(30001); Flush(); assert(#sent==before and widgets.bugDetail:GetText()~="")
        Click("bugSubmit"); Flush(); assert(Payload()==original)
        BugResponse("error","Error simulado"); assert(widgets.bugDetail:GetText()~="")
        widgets.bugDetail:SetText("Otro problema al caminar por la zona.")
        Click("bugSubmit"); Flush(); assert(Payload()~=original)
        ''')

    def test_stale_search_and_loading_cancel(self):
        self.lua('''
        Aa10BugReport.Open(); Flush(); BugResponse("open","ready")
        widgets.bugSearch:SetText("Mission"); Flush()
        widgets.bugSearch:SetText("Otra"); BugResponse("page","0/1/1/98,4d6973696f6e")
        assert(not widgets.bugResult1.enabled and not widgets.bugSubmit.enabled)
        widgets.aa10BugShortcut.handlers.OnEvent(nil,"ENTERED_LOADING")
        local before=#sent; Flush(); assert(#sent==before and not widgets.aa10BugReportPanel.visible)
        ''')

    def test_append_preserves_native_semantics_and_executes_both_closures(self):
        native=codec.compile_source('local n=4; function original() return n+3 end; baseline=original()',apply.LUAC)
        extension=codec.compile_source('extensionResult=original()*2',apply.LUAC)
        data=append_extension(native,extension)
        root=Reader(data).function(); root['children'].pop();root['code']=root['code'][:-12]+root['code'][-4:]
        root['flags']=root['flags'][:3]+bytes([root['flags'][3]-1])
        self.assertEqual(codec.semantic_chunk(native),codec.semantic_chunk(native[:12]+encode(root)))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.lua'; b=bytearray(data);b[11]=0;p.write_bytes(b)
            r=subprocess.run([str(LUA),'-'],input=('dofile([['+str(p)+']]); assert(baseline==7 and extensionResult==14)').encode(),capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_pinned_build_and_second_build_are_identical(self):
        evidence=apply.ROOT/'forensics/output/aa10-client-forensics/bug-reports'
        import shutil
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);effective=root/'effective'
            alb=effective/'scriptsbin64/x2ui/inventory/sort_inventory.alb';alb.parent.mkdir(parents=True)
            shutil.copy2(evidence/'candidates/inventory/sort_inventory.alb',alb)
            lua=effective/'scripts/x2ui/inventory/sort_inventory.lua';lua.parent.mkdir(parents=True)
            shutil.copy2(evidence/'effective/scripts/x2ui/inventory/sort_inventory.lua',lua)
            first=patch.build(effective,root/'first',apply.LUAC)[0]
            shutil.copy2(first['replacement'],alb)
            second=patch.build(effective,root/'second',apply.LUAC)[0]
            self.assertEqual(second['before'],second['after'])
            self.assertEqual(first['after'],second['after'])
            alb.write_bytes(b'x'*alb.stat().st_size)
            with self.assertRaises(ValueError): patch.build(effective,root/'bad',apply.LUAC)

if __name__=='__main__': unittest.main()
