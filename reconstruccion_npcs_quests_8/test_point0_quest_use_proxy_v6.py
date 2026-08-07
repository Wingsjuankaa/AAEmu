#!/usr/bin/env python3
"""Regression tests for the bounded quest 2261 use-item closure."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = DOMAIN / "generated" / "point0-quest-use-proxy-v6-runtime-manifest.json"


class Point0QuestUseProxyV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.manifest["output"]["path"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_native_supply_and_item_use_graph_is_exact(self) -> None:
        self.assertEqual(
            (16293, 1, 0, 1, 1, 1, 1, 0),
            self.connection.execute(
                "SELECT item_id,count,grade_id,cleanup,destroy_when_drop,"
                "drop_when_destroy,show_action_bar,try_equip "
                "FROM quest_act_supply_items WHERE id=2273"
            ).fetchone(),
        )
        self.assertEqual(
            (16293, 1, 6578, 1),
            self.connection.execute(
                "SELECT item_id,count,quest_act_obj_alias_id,use_alias "
                "FROM quest_act_obj_item_uses WHERE id=598"
            ).fetchone(),
        )

    def test_missing_native_reward_rows_are_restored(self) -> None:
        self.assertEqual(
            [(64103, "QuestActSupplyExp", 3933, 9970), (65631, "QuestActSupplyItem", 8881, 9970)],
            self.connection.execute(
                "SELECT id,act_detail_type,act_detail_id,quest_component_id "
                "FROM quest_acts WHERE id IN (64103,65631) ORDER BY id"
            ).fetchall(),
        )
        self.assertEqual(
            (4500,),
            self.connection.execute("SELECT exp FROM quest_act_supply_exps WHERE id=3933").fetchone(),
        )
        self.assertEqual(
            (18791, 5),
            self.connection.execute("SELECT item_id,count FROM quest_act_supply_items WHERE id=8881").fetchone(),
        )

    def test_proxy_only_enables_the_proven_quest_skill_contract(self) -> None:
        self.assertEqual(
            (16293, 64, 0, 2, 1, 0, 2261, 13886, 0, 0),
            self.connection.execute(
                "SELECT id,category_id,impl_id,bind_id,max_stack_size,sellable,"
                "loot_quest_id,use_skill_id,buff_id,craft_id FROM items WHERE id=16293"
            ).fetchone(),
        )

    def test_proxy_is_explicitly_server_derived(self) -> None:
        self.assertEqual(
            ("generic", "complete", "", "server_derived_accepted:quest2261_native_tombstone_use_proxy:v1"),
            self.connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=16293"
            ).fetchone(),
        )
        self.assertEqual("server_derived_accepted", self.manifest["classification"]["item_row"])
        self.assertEqual(0, self.manifest["scope"]["historical_3_0_rows"])
        self.assertEqual(0, self.manifest["scope"]["native_item_rows_claimed"])

    def test_native_skill_plot_dependencies_remain_closed(self) -> None:
        self.assertEqual(
            (13886, 383, 4, 2, 119, 0.0, 20.0, 10000),
            self.connection.execute(
                "SELECT id,plot_id,target_type_id,target_selection_id,target_unit_param,"
                "min_range,max_range,cooldown_time FROM skills WHERE id=13886"
            ).fetchone(),
        )
        self.assertEqual(8, self.connection.execute("SELECT COUNT(*) FROM plot_events WHERE plot_id=383").fetchone()[0])
        self.assertEqual(
            14,
            self.connection.execute(
                "SELECT COUNT(*) FROM plot_effects f JOIN plot_events e ON e.id=f.event_id WHERE e.plot_id=383"
            ).fetchone()[0],
        )

    def test_initial_supply_gap_changes_only_for_item_16293(self) -> None:
        self.assertEqual(
            {"acts": 1003, "distinct_items": 964, "incomplete_acts": 999, "incomplete_distinct_items": 960},
            self.manifest["initial_supply_audit"]["before"],
        )
        self.assertEqual(
            {"acts": 1003, "distinct_items": 964, "incomplete_acts": 998, "incomplete_distinct_items": 959},
            self.manifest["initial_supply_audit"]["after"],
        )

    def test_previous_quest_loot_proxy_is_preserved(self) -> None:
        self.assertEqual(
            ("complete", "server_derived_accepted:quest2263_native_tombstone_proxy:v1"),
            self.connection.execute(
                "SELECT coverage,provenance FROM aaemu_item_definition_coverage WHERE item_id=24126"
            ).fetchone(),
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
