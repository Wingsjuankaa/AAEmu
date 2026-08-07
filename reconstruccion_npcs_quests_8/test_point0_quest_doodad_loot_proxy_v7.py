#!/usr/bin/env python3
"""Regression tests for the bounded quest 2264 doodad-loot proxy."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = DOMAIN / "generated" / "point0-quest-doodad-loot-proxy-v7-runtime-manifest.json"


class Point0QuestDoodadLootProxyV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.manifest["output"]["path"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_native_objective_is_exact(self) -> None:
        self.assertEqual(
            (24967, 1, 1, 1, 1, 14310, 1, 0, 1522, 1),
            self.connection.execute(
                "SELECT item_id,count,cleanup,destroy_when_drop,drop_when_destroy,"
                "highlight_doodad_id,item_grade_id,use_grade,quest_act_obj_alias_id,use_alias "
                "FROM quest_act_obj_item_gathers WHERE id=1800"
            ).fetchone(),
        )

    def test_observed_doodad_loot_binding_is_preserved(self) -> None:
        self.assertEqual(
            (2482, 24967, 1, 1, 10000, 100000),
            self.connection.execute(
                "SELECT id,item_id,count_min,count_max,percent,remain_time "
                "FROM doodad_func_loot_items WHERE id=2482"
            ).fetchone(),
        )
        self.assertEqual(
            (9948, "DoodadFuncLootItem", 2482, 11012, 13898),
            self.connection.execute(
                "SELECT id,actual_func_type,actual_func_id,doodad_func_group_id,next_phase "
                "FROM doodad_funcs WHERE id=9948"
            ).fetchone(),
        )

    def test_proxy_only_enables_the_quest_token_contract(self) -> None:
        self.assertEqual(
            (24967, 64, 0, 2, 1, 0, 2264, 0, 0, 0, 1),
            self.connection.execute(
                "SELECT id,category_id,impl_id,bind_id,max_stack_size,sellable,"
                "loot_quest_id,use_skill_id,buff_id,craft_id,pickup_limit "
                "FROM items WHERE id=24967"
            ).fetchone(),
        )
        self.assertEqual(
            0,
            self.connection.execute(
                "SELECT COUNT(*) FROM item_open_papers WHERE item_id=24967"
            ).fetchone()[0],
        )

    def test_proxy_is_explicitly_server_derived(self) -> None:
        self.assertEqual(
            (
                "generic",
                "complete",
                "",
                "server_derived_accepted:quest2264_native_tombstone_doodad_loot_proxy:v1",
            ),
            self.connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=24967"
            ).fetchone(),
        )
        self.assertEqual("server_derived_accepted", self.manifest["classification"]["item_row"])
        self.assertEqual(0, self.manifest["scope"]["historical_3_0_rows"])
        self.assertEqual(0, self.manifest["scope"]["native_item_rows_claimed"])

    def test_reward_closure_is_already_complete(self) -> None:
        self.assertEqual(
            (34004, 5),
            self.connection.execute(
                "SELECT item_id,count FROM quest_act_supply_items WHERE id=8884"
            ).fetchone(),
        )
        self.assertEqual(
            (
                "generic",
                "complete",
                "",
                "client_compact_8+AA8_native_skill35239_full_closure+quest2264_runtime_audit:v1",
            ),
            self.connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=34004"
            ).fetchone(),
        )
        self.assertEqual(
            (34004, 0, 13, 1000, 35239),
            self.connection.execute(
                "SELECT id,impl_id,category_id,max_stack_size,use_skill_id "
                "FROM items WHERE id=34004"
            ).fetchone(),
        )
        self.assertEqual(
            (10, 10, 10),
            self.connection.execute(
                "SELECT COUNT(*),COUNT(DISTINCT e.actual_id),COUNT(DISTINCT b.buff_id) "
                "FROM skill_effects se JOIN effects e ON e.id=se.effect_id "
                "JOIN buff_effects b ON b.id=e.actual_id WHERE se.skill_id=35239"
            ).fetchone(),
        )

    def test_previous_tombstone_proxies_are_preserved(self) -> None:
        self.assertEqual(
            ("complete", "server_derived_accepted:quest2263_native_tombstone_proxy:v1"),
            self.connection.execute(
                "SELECT coverage,provenance FROM aaemu_item_definition_coverage WHERE item_id=24126"
            ).fetchone(),
        )
        self.assertEqual(
            ("complete", "server_derived_accepted:quest2261_native_tombstone_use_proxy:v1"),
            self.connection.execute(
                "SELECT coverage,provenance FROM aaemu_item_definition_coverage WHERE item_id=16293"
            ).fetchone(),
        )

    def test_gap_census_changes_only_for_item_24967(self) -> None:
        self.assertEqual(
            {"relations": 746, "quests": 654, "items": 553},
            self.manifest["direct_doodad_loot_gap_census"]["before"],
        )
        self.assertEqual(
            {"relations": 745, "quests": 653, "items": 552},
            self.manifest["direct_doodad_loot_gap_census"]["after"],
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
