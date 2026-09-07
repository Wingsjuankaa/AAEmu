import importlib.util
from pathlib import Path
import sys
import unittest


spec = importlib.util.spec_from_file_location(
    "patch",
    Path(__file__).parents[1] / "PatchAa10WesternUiLayout.py",
)
patch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = patch
spec.loader.exec_module(patch)


class WesternUiLayoutPatchTests(unittest.TestCase):
    def test_crafting_patch_is_scoped_and_exact(self):
        source = """            ApplyButtonSkin(button, BUTTON_STYLE.EQUIPMENT)

            local width = button:GetWidth() - 280
            ApplyButtonSkin(button, BUTTON_STYLE.DEFAULT)

            local width = button:GetWidth() - 100
    local windowWidth = GetLayoutSetCrafting()[\"windowWidth\"]
"""
        # These blank-line spaces are part of the exact retail source fixture.
        # Keep them explicit so whitespace cleanup cannot change the input.
        source = source.replace("\n\n", "\n" + " " * 12 + "\n")
        result = patch.patch_crafting_source(source)
        self.assertIn("button:SetWidth(window:GetWidth())", result)
        self.assertIn("button:SetWidth((window:GetWidth() - 4) / 2)", result)
        self.assertIn("local windowWidth = 900", result)
        self.assertIn("button:GetWidth() - 280", result)
        self.assertIn("button:GetWidth() - 100", result)

    def test_tooltip_patch_changes_only_equipment_item_paths(self):
        source = """    local tooltipWnd = tooltip.tooltipWindows[tipNum]
    tooltipWnd.minWindowWidth = 250
function PrepareTooltip(tipInfo, tipNum, equipped)
    local impl = tipInfo[\"item_impl\"]

    tooltip.tooltipWindows[tipNum].minWindowWidth = 250
"""
        result = patch.patch_tooltip_source(source)
        self.assertEqual(result.count("and 360 or 250"), 2)
        for item_impl in ("weapon", "armor", "mate_armor", "butler_armor", "accessory"):
            self.assertEqual(result.count(f'impl == "{item_impl}"'), 2)
        self.assertNotIn("minWindowWidth = 360\n", result)

    def test_ambiguous_or_already_patched_source_is_rejected(self):
        with self.assertRaises(RuntimeError):
            patch.patch_crafting_source("")
        with self.assertRaises(RuntimeError):
            patch.patch_tooltip_source("")

    def test_generated_contracts_keep_original_entry_sizes(self):
        self.assertEqual(patch.CRAFTING_VIEW.alb_size, 51_452)
        self.assertEqual(patch.TOOLTIP.alb_size, 266_870)
        self.assertEqual(len(patch.CRAFTING_VIEW.patched_sha256), 64)
        self.assertEqual(len(patch.TOOLTIP.patched_sha256), 64)


if __name__ == "__main__":
    unittest.main()
