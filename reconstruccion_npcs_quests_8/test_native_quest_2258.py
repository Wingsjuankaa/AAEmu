#!/usr/bin/env python3
"""Regression tests for the AA8-native quest 2258 V5 runtime."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = (
    DOMAIN
    / "generated"
    / "native-quest-2258-urgent-message-v1-runtime-manifest.json"
)


class NativeQuest2258Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.manifest["output"]["path"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_native_graph_is_exact(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT category_id,chapter_idx,quest_idx,race,level "
                "FROM quest_contexts WHERE id=2258"
            ).fetchone(),
            (3, 2, 1, 1, 5),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id,component_kind_id FROM quest_components "
                "WHERE quest_context_id=2258 ORDER BY id"
            ).fetchall(),
            [(9951, 2), (9952, 3), (9953, 6), (9954, 8), (9999, 4)],
        )

    def test_delivery_item_closes_supply_and_objective(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,count,grade_id FROM quest_act_supply_items "
                "WHERE id=1339"
            ).fetchone(),
            (16288, 1, 0),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,count FROM quest_act_obj_item_gathers WHERE id=935"
            ).fetchone(),
            (16288, 1),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT category_id,impl_id,auto_complete,loot_multi,"
                "loot_quest_id,max_stack_size,use_skill_id "
                "FROM items WHERE id=16288"
            ).fetchone(),
            (64, 0, 1, 1, 2258, 10, 0),
        )

    def test_delivery_item_is_promoted_only_as_generic(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=16288"
            ).fetchone(),
            (
                "generic",
                "complete",
                "",
                "game11_native_items:quest2258_delivery_item",
            ),
        )

    def test_accept_and_report_npcs_are_native_targets(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT npc_id FROM quest_act_con_accept_npcs WHERE id=1854"
            ).fetchone(),
            (3630,),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT npc_id FROM quest_act_con_report_npcs WHERE id=2090"
            ).fetchone(),
            (3611,),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT model_id,equip_cloths_id,equip_weapons_id,total_custom_id "
                "FROM npcs WHERE id=3611"
            ).fetchone(),
            (10, 1064, 144, 422),
        )

    def test_reward_dependencies_remain_complete(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,coverage FROM aaemu_item_definition_coverage "
                "WHERE item_id IN (18791,23633) ORDER BY item_id"
            ).fetchall(),
            [(18791, "complete"), (23633, "complete")],
        )

    def test_manifest_records_web_as_corroboration_only(self) -> None:
        corroboration = self.manifest["sources"]["visible_behavior_corroboration"]
        self.assertEqual(corroboration["authority"], "corroboration_only")
        self.assertEqual(
            corroboration["url"],
            "https://wiki.archerage.to/na-en/db/quests/2258",
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual(
            self.connection.execute("PRAGMA quick_check").fetchone()[0],
            "ok",
        )
        self.assertEqual(
            self.connection.execute("PRAGMA integrity_check").fetchone()[0],
            "ok",
        )


if __name__ == "__main__":
    unittest.main()
