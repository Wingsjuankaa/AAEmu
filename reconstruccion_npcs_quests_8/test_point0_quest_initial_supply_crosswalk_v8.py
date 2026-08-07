#!/usr/bin/env python3
"""Regression tests for the crosswalk-backed quest 2265 SupplyItem closure."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = (
    DOMAIN / "generated" / "point0-quest-initial-supply-crosswalk-v8-runtime-manifest.json"
)


class Point0QuestInitialSupplyCrosswalkV8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(
            f"file:{cls.manifest['output']['path']}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_native_quest_2265_contract_is_exact(self) -> None:
        self.assertEqual(
            [(9987, 2), (9988, 3), (9989, 6), (9991, 8)],
            self.connection.execute(
                "SELECT id,component_kind_id FROM quest_components "
                "WHERE quest_context_id=2265 ORDER BY id"
            ).fetchall(),
        )
        self.assertEqual(
            (21604, 1, 1, 1, 1, 1, 0),
            self.connection.execute(
                "SELECT item_id,count,cleanup,destroy_when_drop,drop_when_destroy,"
                "show_action_bar,try_equip FROM quest_act_supply_items WHERE id=1336"
            ).fetchone(),
        )
        self.assertEqual(
            (6700, 23633, 1, 34000, 5),
            (
                self.connection.execute(
                    "SELECT exp FROM quest_act_supply_exps WHERE id=3937"
                ).fetchone()[0],
                *self.connection.execute(
                    "SELECT item_id,count FROM quest_act_supply_items WHERE id=4819"
                ).fetchone(),
                *self.connection.execute(
                    "SELECT item_id,count FROM quest_act_supply_items WHERE id=8885"
                ).fetchone(),
            ),
        )

    def test_only_crosswalk_safe_candidate_was_promoted(self) -> None:
        policy = self.manifest["transversal_policy"]
        self.assertEqual(1, policy["selected_before"])
        self.assertEqual(0, policy["selected_after"])
        self.assertEqual(
            [{"quest_id": 2265, "item_id": 21604}],
            policy["selected_quest_items"],
        )
        self.assertEqual(
            {"relations": 1174, "quests": 1083, "items": 1111},
            self.manifest["initial_supply_gap_census"]["before"],
        )
        self.assertEqual(
            {"relations": 1173, "quests": 1082, "items": 1110},
            self.manifest["initial_supply_gap_census"]["after"],
        )

    def test_item_21604_is_bounded_corroborated_legacy(self) -> None:
        self.assertEqual(
            (21604, 64, 0, 1, 2, 1, 0, 0, 2265, 0, 0, 0, -1, 0),
            self.connection.execute(
                "SELECT id,category_id,impl_id,level,bind_id,max_stack_size,sellable,"
                "gradable,loot_quest_id,use_skill_id,buff_id,craft_id,fixed_grade,pickup_limit "
                "FROM items WHERE id=21604"
            ).fetchone(),
        )
        self.assertEqual(
            (
                "generic",
                "complete",
                "",
                "legacy_3_0_corroborated:AA8_quest2265_crosswalk_match:v1",
            ),
            self.connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=21604"
            ).fetchone(),
        )
        self.assertEqual(0, self.manifest["scope"]["legacy_rows_imported"])
        self.assertEqual(0, self.manifest["scope"]["legacy_field_overrides"])
        self.assertEqual(9, self.manifest["scope"]["legacy_schema_padding_fields"])

    def test_materialization_audit_row_is_explicit(self) -> None:
        self.assertEqual(
            (
                2265,
                9988,
                14179,
                1336,
                21604,
                "quest_item_comparison:b734129ee9a70e13c907e0814c64fe9d",
                "legacy_3_0_corroborated",
                "active_bounded",
            ),
            self.connection.execute(
                "SELECT quest_id,component_id,quest_act_id,act_detail_id,item_id,"
                "comparison_key,authority,state "
                "FROM aaemu_quest_initial_supply_crosswalk_materializations "
                "WHERE item_id=21604"
            ).fetchone(),
        )

    def test_reward_item_34000_has_full_native_closure(self) -> None:
        self.assertEqual(
            (
                "generic",
                "complete",
                "",
                "client_compact_8+AA8_native_skill35238_full_closure+quest2265_runtime_audit:v1",
            ),
            self.connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=34000"
            ).fetchone(),
        )
        self.assertEqual(
            (34000, 0, 13, 1000, 35238),
            self.connection.execute(
                "SELECT id,impl_id,category_id,max_stack_size,use_skill_id "
                "FROM items WHERE id=34000"
            ).fetchone(),
        )
        self.assertEqual(
            (10, 10, 10, 5000, 5000),
            self.connection.execute(
                "SELECT COUNT(*),COUNT(DISTINCT e.actual_id),COUNT(DISTINCT be.buff_id),"
                "MIN(b.duration),MAX(b.duration) FROM skill_effects se "
                "JOIN effects e ON e.id=se.effect_id "
                "JOIN buff_effects be ON be.id=e.actual_id "
                "JOIN buffs b ON b.id=be.buff_id WHERE se.skill_id=35238"
            ).fetchone(),
        )

    def test_previous_quest_and_merchant_closures_are_preserved(self) -> None:
        self.assertEqual(
            "complete",
            self.connection.execute(
                "SELECT coverage FROM aaemu_item_definition_coverage WHERE item_id=24967"
            ).fetchone()[0],
        )
        self.assertEqual(
            37,
            self.connection.execute(
                "SELECT COUNT(*) FROM merchant_goods WHERE merchant_pack_id=914119"
            ).fetchone()[0],
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
