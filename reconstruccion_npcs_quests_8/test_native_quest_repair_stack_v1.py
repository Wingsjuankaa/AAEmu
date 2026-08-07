#!/usr/bin/env python3
"""Regression tests for the first transversal AA8 quest repair stack."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = (
    DOMAIN
    / "generated"
    / "native-quest-repair-stack-v1-runtime-manifest.json"
)


class NativeQuestRepairStackV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.manifest["output"]["path"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_native_quest_2259_graph_is_exact(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT category_id,chapter_idx,quest_idx,race,level "
                "FROM quest_contexts WHERE id=2259"
            ).fetchone(),
            (3, 2, 2, 1, 5),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id,component_kind_id FROM quest_components "
                "WHERE quest_context_id=2259 ORDER BY id"
            ).fetchall(),
            [(9955, 2), (9956, 3), (9957, 6), (9958, 4), (10001, 8)],
        )

    def test_delivery_item_closes_supply_and_objective(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,count,grade_id FROM quest_act_supply_items "
                "WHERE id=2233"
            ).fetchone(),
            (16259, 1, 0),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,count FROM quest_act_obj_item_gathers "
                "WHERE id=1012"
            ).fetchone(),
            (16259, 1),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT category_id,impl_id,auto_complete,loot_multi,"
                "loot_quest_id,max_stack_size,use_skill_id "
                "FROM items WHERE id=16259"
            ).fetchone(),
            (64, 0, 1, 1, 2259, 1, 0),
        )

    def test_item_is_promoted_only_as_native_generic(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=16259"
            ).fetchone(),
            (
                "generic",
                "complete",
                "",
                "game11_native_items:quest2259_delivery_item",
            ),
        )

    def test_accept_report_and_reward_dependencies_are_closed(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT npc_id FROM quest_act_con_accept_npcs WHERE id=1855"
            ).fetchone(),
            (3611,),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT npc_id FROM quest_act_con_report_npcs WHERE id=2091"
            ).fetchone(),
            (10582,),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,coverage FROM aaemu_item_definition_coverage "
                "WHERE item_id=18792"
            ).fetchone(),
            (18792, "complete"),
        )

    def test_manifest_keeps_wiki_as_corroboration_only(self) -> None:
        corroboration = self.manifest["sources"]["visible_behavior_corroboration"]
        self.assertEqual(corroboration["authority"], "corroboration_only")
        self.assertEqual(
            corroboration["url"],
            "https://wiki.archerage.to/na-en/db/quests/2259",
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
