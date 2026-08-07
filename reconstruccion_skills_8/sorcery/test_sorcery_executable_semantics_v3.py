from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_sorcery_executable_semantics_v3.py")
SPEC = importlib.util.spec_from_file_location("sorcery_semantics_v3", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


class SorceryExecutableSemanticsV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit.build_report(audit.parse_args([]))

    def test_all_public_internal_roots_and_passives_are_in_scope(self) -> None:
        self.assertEqual(24, self.report["scope"]["public_root_count"])
        self.assertEqual(6, self.report["scope"]["internal_root_count"])
        self.assertEqual(30, self.report["scope"]["audited_root_count"])
        self.assertEqual(30, len(self.report["roots"]))
        self.assertEqual(6, self.report["scope"]["passive_count"])
        self.assertEqual(6, len(self.report["passives"]))

    def test_internal_entrypoints_are_explicitly_classified(self) -> None:
        kinds = {row["skill_id"]: row["root_kind"] for row in self.report["roots"]}
        self.assertEqual(
            {12789: "login_stage", 12790: "login_stage", 12791: "login_stage"},
            {value: kinds[value] for value in (12789, 12790, 12791)},
        )
        self.assertEqual(
            {42012: "contextual", 43464: "contextual", 43465: "contextual"},
            {value: kinds[value] for value in (42012, 43464, 43465)},
        )

    def test_directed_executable_graph_has_no_static_blockers(self) -> None:
        summary = self.report["summary"]
        self.assertEqual(0, summary["blocked_root_count"])
        self.assertEqual([], summary["roots_with_blockers"])
        self.assertEqual([], summary["roots_with_missing_rows"])
        self.assertEqual([], summary["missing_or_blocking_specials"])

    def test_only_the_six_reachable_condition_families_are_claimed(self) -> None:
        actual = {
            name
            for row in self.report["roots"] + self.report["passives"]
            for name in row["condition_types"]
        }
        self.assertEqual(
            {"ABLevel", "BuffTag", "CombatDiceResult", "Dead", "Range", "Visible"},
            actual,
        )

    def test_extend_charge_and_high_ability_migration_are_reachable(self) -> None:
        effects = {
            name
            for row in self.report["roots"]
            for name in row["effect_types"]
        }
        self.assertIn("ExtendChargeEffect", effects)
        self.assertIn("HighAbilityResourceEffect", effects)
        self.assertTrue(self.report["crosswalk_resource_migration_details"])

    def test_insulating_lens_absorption_break_closure_is_reachable(self) -> None:
        lens = next(row for row in self.report["roots"] if row["skill_id"] == 10153)
        self.assertIn(9738, lens["closure_ids"]["buff_triggers"])
        self.assertIn(67353, lens["closure_ids"]["effects"])
        self.assertIn(31561, lens["closure_ids"]["special_effects"])
        self.assertIn(37837, lens["closure_ids"]["skills"])
        self.assertIn(94, lens["closure_ids"]["buffs"])
        self.assertEqual(1, lens["special_types"]["SkillUse"])

    def test_plot_area_shapes_are_executable_dependencies(self) -> None:
        freezing_earth = next(
            row for row in self.report["roots"] if row["skill_id"] == 10151
        )
        self.assertIn(11815, freezing_earth["closure_ids"]["aoe_shapes"])
        self.assertIn(
            {
                "source": "plot_events:25977",
                "relation": "area_shape",
                "target": "aoe_shapes:11815",
            },
            freezing_earth["edges"],
        )

    def test_reachable_buff_triggers_are_counted_once_across_shared_closures(self) -> None:
        self.assertEqual(
            {"Absorption": 1, "Started": 18, "Timeout": 4},
            self.report["summary"]["reachable_buff_trigger_events"],
        )

    def test_fire_wall_mist_preserves_the_only_nonzero_skill_use_value4(self) -> None:
        mist = next(row for row in self.report["roots"] if row["skill_id"] == 41223)
        self.assertEqual(
            [{
                "id": 42478,
                "child_skill_id": 41478,
                "delay": 0,
                "chance": 0,
                "value4": 1,
                "state": "preserved_not_consumed_by_supplied_r575_binaries",
            }],
            mist["nonzero_skill_use_value4"],
        )
        self.assertEqual(
            ["SkillUse.value4:present_but_not_consumed_by_supplied_r575_binaries"],
            mist["external_native_unknowns"],
        )
        self.assertEqual([41223], self.report["summary"]["roots_with_external_native_unknowns"])


if __name__ == "__main__":
    unittest.main()
