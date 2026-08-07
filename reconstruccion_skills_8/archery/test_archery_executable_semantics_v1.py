from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_archery_executable_semantics_v1.py")
SPEC = importlib.util.spec_from_file_location("archery_semantics_v1", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


class ArcheryExecutableSemanticsV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit.build_report(audit.shared.parse_args([]))

    def test_all_public_internal_roots_and_passives_are_in_scope(self) -> None:
        scope = self.report["scope"]
        self.assertEqual(24, scope["public_root_count"])
        self.assertEqual(11, scope["internal_root_count"])
        self.assertEqual(35, scope["audited_root_count"])
        self.assertEqual(35, len(self.report["roots"]))
        self.assertEqual(6, scope["passive_count"])

    def test_directed_executable_graph_has_no_static_blockers(self) -> None:
        summary = self.report["summary"]
        self.assertEqual(0, summary["blocked_root_count"])
        self.assertEqual([], summary["roots_with_blockers"])
        self.assertEqual([], summary["roots_with_missing_rows"])
        self.assertEqual([], summary["missing_or_blocking_specials"])
        self.assertEqual([], summary["roots_with_external_native_unknowns"])

    def test_only_reachable_archery_condition_families_are_claimed(self) -> None:
        actual = {
            name
            for row in self.report["roots"] + self.report["passives"]
            for name in row["condition_types"]
        }
        self.assertEqual(
            {
                "BuffTag", "CastingUseable", "CombatDiceResult", "Dead",
                "Range", "UnitReqs", "Variable", "Visible",
                "WeaponEquipStatus",
            },
            actual,
        )

    def test_all_reachable_buff_events_have_executable_consumers(self) -> None:
        self.assertEqual(
            {"Landing": 1, "RemoveOnMove": 1, "Started": 26, "Timeout": 1},
            self.report["summary"]["reachable_buff_trigger_events"],
        )

    def test_intensity_tail_is_deterministic_reset_cooldown(self) -> None:
        intensity = next(
            row for row in self.report["roots"] if row["skill_id"] == 10708
        )
        tail = intensity["nonzero_special_value5_7"]
        self.assertEqual(6, len(tail))
        self.assertTrue(all(row["type"] == "ResetCooldown" for row in tail))
        self.assertTrue(all(row["value7"] == 100 for row in tail))
        self.assertEqual(
            [10708], self.report["summary"]["roots_using_special_values_5_to_7"]
        )

    def test_concussive_mist_closes_bubble_controller_and_damage(self) -> None:
        mist = next(
            row for row in self.report["roots"] if row["skill_id"] == 36471
        )
        self.assertIn("BubbleEffect", mist["effect_types"])
        self.assertIn("DamageEffect", mist["effect_types"])
        self.assertIn("SkillController", mist["effect_types"])
        self.assertEqual([], mist["blockers"])

    def test_owner_keyed_skill_tags_are_closed_and_unique(self) -> None:
        contract = self.report["owner_keyed_relations"]["skill_tags"]
        self.assertEqual("server_skill_tag_and_modifier_cache", contract["consumer"])
        self.assertEqual(356, contract["tagged_skill_row_count"])
        self.assertEqual(356, contract["tagged_skill_pair_count"])
        self.assertEqual(35, len(contract["covered_root_ids"]))
        self.assertEqual([], contract["missing_root_ids"])
        self.assertEqual([], contract["duplicate_pairs"])
        self.assertEqual([], contract["blockers"])

    def test_marksman_native_modifier_has_24_tagged_consumers(self) -> None:
        contracts = self.report["owner_keyed_relations"]["skill_tags"][
            "passive_modifier_contracts"
        ]
        marksman = next(row for row in contracts if row["owner_buff_id"] == 889)
        self.assertEqual(300, marksman["passive_id"])
        self.assertEqual(3750, marksman["tag_id"])
        self.assertEqual(10, marksman["skill_attribute_id"])
        self.assertEqual(10, marksman["value"])
        self.assertEqual(24, marksman["consumer_count"])
        self.assertEqual([], self.report["summary"]["owner_keyed_relation_blockers"])

    def test_passive_buff_tags_are_closed_and_unique(self) -> None:
        contract = self.report["owner_keyed_relations"]["passive_buff_tags"]
        self.assertEqual(
            "server_buff_tag_cache_and_native_passive_dispatch",
            contract["consumer"],
        )
        self.assertEqual(6, contract["audited_passive_buff_count"])
        self.assertEqual(21, contract["tagged_buff_row_count"])
        self.assertEqual(21, contract["tagged_buff_pair_count"])
        self.assertEqual([480, 486, 888, 889, 7564, 7565], contract["covered_buff_ids"])
        self.assertEqual([], contract["missing_buff_ids"])
        self.assertEqual([], contract["duplicate_pairs"])
        self.assertEqual([], contract["blockers"])


if __name__ == "__main__":
    unittest.main()
