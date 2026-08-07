#!/usr/bin/env python3
"""Regression tests for the AA8 initial quest SupplyItem closure V2."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = DOMAIN / "generated" / "native-quest-supply-closure-v2-runtime-manifest.json"
PROVENANCE = "game11_native_items:quest_initial_supply_generic_v2"


class NativeQuestSupplyClosureV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.manifest["output"]["path"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_quest_2260_native_graph_is_exact(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT category_id,chapter_idx,quest_idx,race,level,zone_id "
                "FROM quest_contexts WHERE id=2260"
            ).fetchone(),
            (3, 2, 3, 1, 5, 124),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id,component_kind_id FROM quest_components "
                "WHERE quest_context_id=2260 ORDER BY id"
            ).fetchall(),
            [(9959, 2), (9960, 3), (9961, 6), (9962, 8), (10002, 4)],
        )

    def test_quest_2260_delivery_item_closes_supply_and_objective(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,count,grade_id FROM quest_act_supply_items WHERE id=1334"
            ).fetchone(),
            (16260, 1, 0),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,count FROM quest_act_obj_item_gathers WHERE id=938"
            ).fetchone(),
            (16260, 1),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT category_id,impl_id,auto_complete,loot_multi,loot_quest_id,"
                "max_stack_size,use_skill_id FROM items WHERE id=16260"
            ).fetchone(),
            (64, 0, 1, 1, 2260, 1, 0),
        )

    def test_transversal_generic_coverage_contains_both_observed_letters(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id IN (16259,16260) "
                "ORDER BY item_id"
            ).fetchall(),
            [
                (16259, "generic", "complete", "", PROVENANCE),
                (16260, "generic", "complete", "", PROVENANCE),
            ],
        )

    def test_transversal_replacement_never_duplicates_native_item_ids(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT id,COUNT(*) FROM items WHERE id IN (16259,16260) "
                "GROUP BY id ORDER BY id"
            ).fetchall(),
            [(16259, 1), (16260, 1)],
        )

    def test_accept_and_report_npcs_are_native(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT id,npc_id FROM quest_act_con_accept_npcs WHERE id=1856"
            ).fetchone(),
            (1856, 10582),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id,npc_id FROM quest_act_con_report_npcs WHERE id=2092"
            ).fetchone(),
            (2092, 10583),
        )

    def test_known_fixed_quest_and_point0_rifle_layers_are_preserved(self) -> None:
        self.assertEqual(
            self.connection.execute("SELECT id FROM items WHERE id=16259").fetchone(),
            (16259,),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT plot_only,plot_id,projectile_id,weapon_slot_for_autoattack_id "
                "FROM skills WHERE id=46938"
            ).fetchone(),
            (1, 5796, 9, 17),
        )
        self.assertGreater(
            self.connection.execute(
                "SELECT COUNT(*) FROM native_character_creation_action_slots "
                "WHERE action_type=2"
            ).fetchone()[0],
            0,
        )

    def test_reward_items_needed_after_report_remain_available(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,coverage FROM aaemu_item_definition_coverage "
                "WHERE item_id IN (23633,48507) ORDER BY item_id"
            ).fetchall(),
            [(23633, "complete"), (48507, "complete")],
        )

    def test_unverified_supply_items_remain_fail_closed(self) -> None:
        audit = self.manifest["scope"]
        self.assertEqual(audit["audit_before"]["incomplete_acts"], 1000)
        self.assertEqual(audit["audit_after"]["incomplete_acts"], 999)
        self.assertEqual(audit["audit_before"]["incomplete_distinct_items"], 961)
        self.assertEqual(audit["audit_after"]["incomplete_distinct_items"], 960)

    def test_wiki_is_corroboration_only(self) -> None:
        quest = self.manifest["sources"]["quests"]["2260"]
        self.assertEqual(quest["wiki_authority"], "corroboration_only")
        self.assertEqual(quest["wiki"], "https://wiki.archerage.to/na-en/db/quests/2260")

    def test_sqlite_integrity(self) -> None:
        self.assertEqual(self.connection.execute("PRAGMA quick_check").fetchone()[0], "ok")
        self.assertEqual(self.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
