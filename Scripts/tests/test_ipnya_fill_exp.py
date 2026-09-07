import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import PatchAa10IpnyaFillExp as patch

FIXTURES = json.loads((Path(__file__).parent / 'fixtures/ipnya_fill_exp_r575.json').read_text(encoding='utf-8'))
LUA = Path(os.environ.get('AA10_LUA51', 'E:/AAEmu/rama_10/localization/aa10-es-es/work/ui-layout-v2/lua-runtime/lua51.exe'))


def literal(v):
    if isinstance(v, dict):
        return '{' + ','.join('[' + literal(k) + ']=' + literal(x) for k, x in v.items()) + '}'
    if isinstance(v, list):
        return '{' + ','.join(map(literal, v)) + '}'
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


@unittest.skipUnless(LUA.is_file(), 'Requires Lua 5.1 interpreter (AA10_LUA51)')
class IpnyaFillTests(unittest.TestCase):
    def lua(self, body):
        program = 'local B=(function()\n' + (patch.LUA / 'IpnyaFillExp.lua').read_text(encoding='utf-8') + '\nend)()\n'
        program += 'local fixtures=' + literal(FIXTURES) + '\n' + body
        result = subprocess.run([str(LUA), '-'], input=program.encode('utf-8'), capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def test_catalog_families_and_valid_recipe_batches(self):
        self.lua('''
        for _, f in ipairs(fixtures) do
            local info=f.recipes; info.curExp=0; info.totalExp=f.totalExp
            local options=B.Options(info, function() return 999 end)
            assert(#options>=4)
            for _, p in ipairs(options) do
                local exp, cost, stock=0,0,{}
                for i,r in ipairs(p.steps) do
                    assert(exp<info.totalExp, 'extra step after full EXP')
                    exp=exp+r.gainExp; cost=cost+r.currencyValue
                    for _,v in ipairs(r.itemList) do stock[v.item.itemType]=(stock[v.item.itemType] or 0)+v.count end
                end
                assert(exp==p.gainExp and cost==p.currencyValue)
                for _,v in ipairs(p.itemList) do assert(stock[v.item.itemType]==v.count) end
            end
        end
        ''')

    def test_uses_existing_exp_and_five_packs(self):
        self.lua('''
        local info=fixtures[4].recipes; info.curExp=400; info.totalExp=2400
        local p=B.Plan(info,function(id) return id==51594 and 20 or 0 end,'mixed')
        assert(p and p.gainExp==2000 and p.overflow==0 and #p.steps==4)
        assert(#p.itemList==1 and p.itemList[1].count==20)
        ''')

    def test_shared_stone_inventory_and_minimal_overflow(self):
        self.lua('''
        local info=fixtures[4].recipes; info.curExp=0; info.totalExp=300
        local bag=function(id) return (id==51594 or id==51602) and 2 or 0 end
        local p=B.Plan(info,bag,'mixed')
        assert(p and p.gainExp==350 and p.overflow==50)
        for _,v in ipairs(p.itemList) do assert(v.count<=2) end
        assert(B.Plan(info,function() return 0 end,'mixed')==nil)
        info.curExp=300; assert(B.Plan(info,bag,'mixed')==nil)
        info.curExp=0; info.totalExp=999999; assert(B.Plan(info,bag,'mixed')==nil)
        ''')

    def test_exact_optimum_against_independent_exhaustive_oracle(self):
        recipes = [r for r in FIXTURES[3]['recipes'] if all(v['count'] == 1 for v in r['itemList'])]
        rng = random.Random(575)
        cases = []
        for _ in range(65):
            stock = {51594: rng.randrange(9), 51595: rng.randrange(9), 51596: rng.randrange(9), 51602: rng.randrange(9)}
            need = rng.randrange(1, 1400)
            best = None
            for counts in itertools.product(range(9), repeat=4):
                used = {k: 0 for k in stock}
                exp = gold = nitems = 0
                for r, count in zip(recipes, counts):
                    exp += r['gainExp'] * count
                    gold += r['currencyValue'] * count
                    for item in r['itemList']:
                        used[item['item']['itemType']] += count
                        nitems += count
                if exp < need or any(used[k] > stock[k] for k in stock):
                    continue
                score = (exp, gold, nitems, sum(n // 5 + n % 5 for n in counts))
                if best is None or score < best:
                    best = score
            cases.append(dict(stock=stock, need=need, expected=list(best) if best else []))
        self.lua('local cases=' + literal(cases) + '''
        for _,c in ipairs(cases) do
            local info=fixtures[4].recipes; info.curExp=0; info.totalExp=c.need
            local p=B.Plan(info,function(id) return c.stock[id] end,'mixed')
            if #c.expected==0 then assert(not p) else
                assert(p and p.gainExp==c.expected[1] and p.currencyValue==c.expected[2])
                local items=0; for _,v in ipairs(p.itemList) do items=items+v.count end
                assert(items==c.expected[3] and #p.steps==c.expected[4])
            end
        end
        ''')

    def test_cross_language_quote_fixture_is_generated_by_current_planner(self):
        quotes=json.loads((Path(__file__).parent/'fixtures/ipnya_single_cast_quotes.json').read_text())
        self.lua('local quotes='+literal(quotes)+"""
        local index=0
        for i,f in ipairs(fixtures) do
            for _,exp in ipairs({0,math.floor(f.totalExp/2),f.totalExp-1}) do
                local info=f.recipes; info.curExp=exp; info.totalExp=f.totalExp
                for _,p in ipairs(B.Options(info,function() return 999 end)) do
                    index=index+1; local command=B.Request(p,f.slot+1,f.level)
                    assert(command==quotes[index].command and quotes[index].fixture==i-1)
                    for _,v in ipairs(p.itemList) do
                        assert(quotes[index].materials[tostring(v.item.itemType)]==v.count)
                    end
                end
            end
        end
        assert(index==#quotes)
        """)

    def test_single_cast_request_aggregates_and_watch_never_sends(self):
        self.lua("""
        local info=fixtures[4].recipes; info.curExp=0; info.totalExp=1100
        local p=B.Plan(info,function(id) return id==51594 and 11 or 0 end,'mixed')
        local command,id=B.Request(p,16,7)
        assert(id==1 and #command<=233 and command:find('1,15,7,0,1100,',1,true)==1)
        assert(not command:find(';',1,true))
        local q=B.Watch(p,7); local state={level=7,exp=0,totalExp=1100}
        for i=1,40 do assert(q:Tick(100,state,true,true)=='waiting') end
        state.exp=1100; assert(q:Tick(100,state,false,true)=='done')
        assert(q:Tick(999,state,false,true)=='stopped')
        """)

    def test_interruption_timeout_state_drift_close_and_level_change(self):
        self.lua("""
        local info=fixtures[4].recipes; info.curExp=0; info.totalExp=1100
        local p=B.Plan(info,function(id) return id==51594 and 11 or 0 end,'mixed')
        local function start() return B.Watch(p,7),{level=7,exp=0,totalExp=1100} end
        local q,s=start(); assert(q:Tick(10001,s,false,true)=='stopped')
        q,s=start(); q:Tick(100,s,true,true); assert(q:Tick(1501,s,false,true)=='stopped')
        q,s=start(); s.exp=45; assert(q:Tick(100,s,false,true)=='stopped')
        q,s=start(); assert(q:Tick(100,s,false,false)=='stopped')
        q,s=start(); s.level=8; assert(q:Tick(100,s,false,true)=='stopped')
        q,s=start(); s.totalExp=1200; assert(q:Tick(100,s,false,true)=='stopped')
        q,s=start(); assert(q:Tick(60001,s,true,true)=='stopped')
        """)

    def test_changed_stock_and_progress_invalidate_confirmation(self):
        self.lua('''
        local info=fixtures[4].recipes; info.curExp=0; info.totalExp=1000
        local p=B.Plan(info,function() return 100 end,'mixed')
        assert(p.signature==B.Plan(info,function() return 100 end,'mixed').signature)
        info.curExp=100
        assert(p.signature~=B.Plan(info,function() return 100 end,'mixed').signature)
        info.curExp=0
        local other=B.Plan(info,function(id) return id==51594 and 10 or 0 end,'mixed')
        assert(other and p.signature~=other.signature)
        ''')

    def test_ui_confirmation_cancel_and_no_silent_replan(self):
        ui = (patch.LUA / 'IpnyaFillExpUi.lua').read_text(encoding='utf-8')
        # Apply the same two lexical-scope bridges used by the actual builder.
        ui = ui.replace('        batchRunner = nil\n', '        batchRunner = nil\n        window.Aa10BatchRunning = false\n')
        ui = ui.replace('        local slot = selectedEquipSlot\n', '        window.Aa10BatchRunning = true\n        local slot = selectedEquipSlot\n')
        self.lua('''
        local Aa10IpnyaBatch=B
        local state={level=7, exp=0, totalExp=1100}
        local info=fixtures[4].recipes; info.curExp=0; info.totalExp=1100
        local sent, cancelled, working=0,0,false
        X2Chat={JoinUserChatChannel=function(self,command,password)
            assert(#command<=48 and password=="")
            if command:find('aa10ip3:',1,true)==1 then
                local index,total=command:match('^aa10ip3:%d+:(%d+):(%d+):')
                if index==total then sent=sent+1; working=true end
            elseif command:find('aa10ip3cancel:',1,true)==1 then cancelled=cancelled+1; working=false
            else error('unexpected transport frame') end
        end}
        X2Bag={GetCountInBag=function(self,id) return id==51594 and 11 or 0 end}
        X2EquipSlotReinforce={
            GetReinforceInfo=function() return state end,
            GetMaterialInfo=function() info.curExp=state.exp; return info end,
            IsWorkingAddExp=function() return working end,
            StartReinforceAddExp=function() error("single-cast option must not submit native single recipe") end,
            StopCasting=function() working=false end
        }
        W_MODULE={TYPES={TEXTBOX=1}, ATTRIBUTE={TEXT='text'},
            Create=function() return {SetData=function(self,d) self.data=d end} end}
        local function setup()
            local selectedEquipSlot=16
            local window={handlers={},visible=true,refresh=0}
            function window:SetHandler(k,v) self.handlers[k]=v end
            function window:ReleaseHandler(k) self.handlers[k]=nil end
            function window:IsVisible() return self.visible end
            function window:RegisterStack() end
            function window:ApplyAutoHeightByStack() end
            function window:ApplyOkButtonEnablement() end
            function window:SetEquipSlot() self.refresh=self.refresh+1 end
            local filter={Enable=function(self,v) self.enabled=v end}
            local levelupBtn={Enable=function() end}
            local function IsFullExp() return state.exp==state.totalExp end
        ''' + ui + '''
            batchSelected=B.Plan(info,function(id) return X2Bag:GetCountInBag(id) end,'mixed')
            return window, StartBatch, CancelBatch, filter
        end
        local w,start,cancel,f=setup()
        start(); start(); assert(w.Aa10BatchRunning and sent==1 and f.enabled==false)
        w.handlers.OnUpdate(w,250); assert(sent==1)
        for i=1,10 do w.handlers.OnUpdate(w,100) end
        assert(sent==1)
        w.handlers.OnHide(); assert(cancelled==1 and not w.Aa10BatchRunning and not w.handlers.OnUpdate)
        assert(f.enabled)
        w,start,cancel,f=setup(); state.exp=100
        start(); assert(sent==1 and w.refresh==1 and not w.handlers.OnUpdate)
        ''')


class BuilderTests(unittest.TestCase):
    def test_source_drift_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'exact source match'):
            patch.patch_source('function fake() end')

    def test_contract_pins_source_compiler_baseline_and_output(self):
        d = json.loads(patch.CONTRACTS.read_text())
        self.assertEqual(len(d['entries']), 1)
        e = d['entries'][0]
        self.assertEqual(e['size'], 36127)
        self.assertEqual(set(e['accepted_sha256']), {e['baseline_sha256'], e['previous_queue_sha256'], e['previous_console_sha256'], e['patched_sha256']})
        for h in [d['luac_sha256'], e['source_sha256'], *e['accepted_sha256']]:
            self.assertRegex(h, '^[A-F0-9]{64}$')

    @unittest.skipUnless(os.environ.get('AA10_IPNYA_EFFECTIVE'), 'Requires extracted exact r575 inputs')
    def test_determinism_wrong_input_and_idempotent_builder(self):
        import shutil
        root = Path(os.environ['AA10_IPNYA_EFFECTIVE'])
        luac = Path(os.environ['AA10_LUAC51'])
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            a = patch.build(root, temp/'a', luac)
            b = patch.build(root, temp/'b', luac)
            self.assertEqual(Path(a[0]['replacement']).read_bytes(), Path(b[0]['replacement']).read_bytes())
            clone = temp/'effective'
            shutil.copytree(root/'scripts', clone/'scripts')
            dest = clone/f"scriptsbin64/x2ui/{a[0]['name']}.alb"
            dest.parent.mkdir(parents=True)
            shutil.copyfile(a[0]['replacement'], dest)
            result = patch.build(clone, temp/'idempotent', luac)
            self.assertEqual(result[0]['before'], result[0]['after'])
            dest.write_bytes(b'corrupt')
            with self.assertRaisesRegex(RuntimeError, 'Unknown effective'):
                patch.build(clone, temp/'bad', luac)
