import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import PatchAa10SpanishUiLayout as patch
from ApplyAa10SpanishUiLayout import transaction


class SafetyTests(unittest.TestCase):
    def test_all_consumers_have_fixed_source_and_input_output_contracts(self):
        contracts = json.loads(patch.CONTRACTS.read_text())
        self.assertEqual(len(contracts["entries"]), 8)
        for entry in contracts["entries"]:
            self.assertTrue(entry["source_bytecode_equivalent"])
            self.assertIn(entry["patched_sha256"], entry["accepted_sha256"])
            self.assertTrue(all(len(h) == 64 for h in entry["accepted_sha256"]))

    def test_source_drift_and_unknown_consumer_rejected(self):
        with self.assertRaises(RuntimeError):
            patch.patch_source("store/common", "local width = 279\n" * 2)
        with self.assertRaises(ValueError):
            patch.patch_source("unknown", "")

    def test_transaction_rolls_back_including_partially_written_failing_entry(self):
        entries = [{"name": str(i), "before": "old", "after": "new"} for i in range(3)]
        disk = ["old"] * 3
        restored = []
        def write(entry):
            i = int(entry["name"])
            disk[i] = "new"
            if i == 1:
                raise RuntimeError("post-write verification failed")
        def restore(entry):
            i = int(entry["name"])
            restored.append(i)
            disk[i] = "old"
        with self.assertRaisesRegex(RuntimeError, "post-write"):
            transaction(entries, write, Mock(), restore)
        self.assertEqual(disk, ["old"] * 3)
        self.assertEqual(restored, [1, 0])

    def test_failed_final_verification_also_rolls_back(self):
        entry = {"before": "old", "after": "new"}
        restore = Mock()
        with self.assertRaises(RuntimeError):
            transaction([entry], Mock(), Mock(side_effect=RuntimeError("sentinel")), restore)
        restore.assert_called_once_with(entry)

    def test_idempotent_transaction_does_not_write_or_restore(self):
        write, verify, restore = Mock(), Mock(), Mock()
        transaction([{"before": "same", "after": "same"}], write, verify, restore)
        write.assert_not_called()
        restore.assert_not_called()
        verify.assert_called_once()

    def test_lua_chunk_rejects_wrong_abi_and_truncation(self):
        for data in (b"", b"not Lua", patch.v1.LUA_51_HEADER + b"\0" * 2):
            with self.assertRaises((RuntimeError, IndexError)):
                patch.semantic_chunk(data)


@unittest.skipUnless(os.environ.get("AA10_UI_EFFECTIVE") and os.environ.get("AA10_LUA51"),
                     "Requires extracted exact r575 inputs and Lua 5.1 interpreter")
class RetailSourceTests(unittest.TestCase):
    def setUp(self):
        self.effective = Path(os.environ["AA10_UI_EFFECTIVE"])
        self.lua = Path(os.environ["AA10_LUA51"])
        self.luac = Path(os.environ["AA10_LUAC51"])

    def source(self, name):
        return (self.effective / f"scripts/x2ui/{name}.lua").read_text(encoding="utf-8-sig")

    def execute(self, source):
        result = subprocess.run([str(self.lua), "-"], input=source.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))

    def test_exact_effective_bytecode_matches_sources_before_transformation(self):
        for entry in json.loads(patch.CONTRACTS.read_text())["entries"]:
            name = entry["name"]
            source = self.source(name)
            if name == "components/tooltip/tooltip":
                source = patch.v1.patch_tooltip_source(source)
            compiled = patch.compile_source(source, self.luac)
            effective = (self.effective / f"scriptsbin64/x2ui/{name}.alb").read_bytes()
            self.assertEqual(patch.semantic_chunk(compiled), patch.semantic_chunk(effective), name)

    def test_deterministic_build_and_reject_corrupted_effective_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = patch.build(self.effective, root / "one", self.luac)
            second = patch.build(self.effective, root / "two", self.luac)
            self.assertEqual([e["after"] for e in first], [e["after"] for e in second])
            for entry in first:
                self.assertEqual(Path(entry["replacement"]).stat().st_size, entry["size"])
            import shutil
            shutil.copytree(self.effective / "scriptsbin64", root / "corrupt/scriptsbin64")
            shutil.copytree(self.effective / "scripts", root / "corrupt/scripts")
            alb = root / "corrupt/scriptsbin64/x2ui/baselib/func_prefix_size.alb"
            data = bytearray(alb.read_bytes()); data[-1] ^= 1; alb.write_bytes(data)
            with self.assertRaisesRegex(RuntimeError, "Unknown effective ALB"):
                patch.build(root / "corrupt", root / "rejected", self.luac)

    def test_window_preset_api_and_icon_geometry(self):
        source = patch.patch_source("baselib/func_prefix_size", self.source("baselib/func_prefix_size"))
        self.execute(source + """
assert(F_PREFIX_SIZE:GetWindowWidth(WINDOW_WIDTH_350) == 430)
assert(F_PREFIX_SIZE:GetWindowWidth(WINDOW_WIDTH_680) == 800)
assert(F_PREFIX_SIZE:GetWindowWidth(WINDOW_WIDTH_900) == 900)
assert(F_PREFIX_SIZE:GetIconButtonSize(ICON_SIZE_42) == 42)
local combos = F_PREFIX_SIZE:GetWindowWidthForCombos()
for i, row in ipairs(combos) do assert(row.text == tostring(row.value)) end
""")

    def test_skill_cost_range_cast_and_cooldown_remain_separate_with_long_spanish_text(self):
        source = patch.patch_source("components/tooltip/tooltip", self.source("components/tooltip/tooltip"))
        section = source.split("    if tipSkillSimpleInfo ~= nil then\n", 1)[1].split("    if tipSkillTimeInfo ~= nil then", 1)[0]
        # Include its real surrounding if so the retail function is unmodified.
        section = "if tipSkillSimpleInfo ~= nil then\n" + section
        setup = r'''
tipSkillSimpleInfo = {SetHeight=function(self,h) self.height=h end}
tooltipLocale={forclyUseLeftSection=false}
FONT_SIZE={MIDDLE=16}; ALIGN_LEFT=1; ALIGN_RIGHT=2
space_normalFont=3; space_bigFont=6
tipText={mp="Maná",rangeSelf="Alcance: solo el lanzador",
GetRange=function(a,b) return "Alcance: "..a.."–"..b.." m" end,
GetTargetAreaRadius=function(r) return "Radio del área objetivo: "..r end}
FormatCastingTime=function() return "Canalización prolongada" end
FormatCooldownTime=function() return "28 s de tiempo de reutilización" end
SetSynergyIcon=function() return false end
local rows={}
local renderer={
AddLine=function(self,text) rows[#rows+1]=text; return #rows end,
AddAnotherSideLine=function() error("Two translated fields share a row") end,
GetHeightToLastLine=function() return #rows*20,#rows*20 end,
AttachUpperSpaceLine=function() end, AttachLowerSpaceLine=function() end}
'''
        checks = r'''
for _, data in ipairs({{mana=173}, {mana=0,minRange=0,maxRange=20,targetAreaRadius=8}}) do
 rows={}; tipSkillSimpleInfo:SetInfo(renderer,data)
 assert(rows[#rows] == "28 s de tiempo de reutilización")
 assert(tipSkillSimpleInfo.height > 0)
 local foundRange=false
 for _,text in ipairs(rows) do if string.find(text,"Alcance:",1,true) then foundRange=true end end
 assert(foundRange)
end
'''
        self.execute(setup + section + checks)


if __name__ == "__main__":
    unittest.main()
