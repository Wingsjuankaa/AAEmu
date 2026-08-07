#!/usr/bin/env python3
"""Regression tests for quest 2260 rewards and Moonrise crate closure V3."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = (
    DOMAIN / "generated" / "native-quest-reward-explorer-closure-v3-runtime-manifest.json"
)
PROVENANCE = "client_compact_8+game11_native+quest2260_reward_explorer_v3"


class NativeQuestRewardExplorerClosureV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.manifest["output"]["path"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_reward_component_contains_complete_native_act_set(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT id,act_detail_type,act_detail_id FROM quest_acts "
                "WHERE quest_component_id=9962 ORDER BY id"
            ).fetchall(),
            [
                (40848, "QuestActSupplyItem", 4815),
                (64100, "QuestActSupplyExp", 3930),
                (65260, "QuestActSupplySelectiveItem", 3655),
                (65261, "QuestActSupplySelectiveItem", 3656),
                (65262, "QuestActSupplySelectiveItem", 3657),
                (65323, "QuestActSupplyItem", 8711),
                (65675, "QuestActSupplyCopper", 3823),
            ],
        )

    def test_visible_base_rewards_match_native_rows(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT exp FROM quest_act_supply_exps WHERE id=3930"
            ).fetchone(),
            (2800,),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT amount FROM quest_act_supply_coppers WHERE id=3823"
            ).fetchone(),
            (2500,),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,count,grade_id FROM quest_act_supply_items "
                "WHERE id IN (4815,8711) ORDER BY id"
            ).fetchall(),
            [(23633, 1, 0), (48507, 2, 0)],
        )

    def test_three_selective_rewards_are_one_based_and_exact(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT id,item_id,count,grade_id FROM quest_act_supply_selective_items "
                "WHERE id IN (3655,3656,3657) ORDER BY id"
            ).fetchall(),
            [(3655, 47985, 1, 0), (3656, 47986, 1, 0), (3657, 47987, 1, 0)],
        )

    def test_moonrise_box_skill_effect_closure_is_complete(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT id,skill_id,effect_id,consume_source_item,end_level "
                "FROM skill_effects WHERE id IN (59714,59716,59718) ORDER BY id"
            ).fetchall(),
            [
                (59714, 42226, 78590, 1, 255),
                (59716, 42228, 78592, 1, 255),
                (59718, 42230, 78594, 1, 255),
            ],
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id,actual_type,actual_id FROM effects "
                "WHERE id IN (78590,78592,78594) ORDER BY id"
            ).fetchall(),
            [
                (78590, "GainLootPackItemEffect", 4216),
                (78592, "GainLootPackItemEffect", 4218),
                (78594, "GainLootPackItemEffect", 4220),
            ],
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id,loot_pack_id FROM gain_loot_pack_item_effects "
                "WHERE id IN (4216,4218,4220) ORDER BY id"
            ).fetchall(),
            [(4216, 12951), (4218, 12953), (4220, 12955)],
        )

    def test_each_box_grants_its_three_description_items(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT loot_pack_id,\"group\",item_id,min_amount,max_amount,always_drop "
                "FROM loots WHERE loot_pack_id IN (12951,12953,12955) "
                "ORDER BY loot_pack_id,\"group\""
            ).fetchall(),
            [
                (12951, 1, 48018, 1, 1, "t"),
                (12951, 2, 48020, 1, 1, "t"),
                (12951, 3, 48021, 1, 1, "t"),
                (12953, 1, 48025, 1, 1, "t"),
                (12953, 2, 48027, 1, 1, "t"),
                (12953, 3, 48028, 1, 1, "t"),
                (12955, 1, 48032, 1, 1, "t"),
                (12955, 2, 48034, 1, 1, "t"),
                (12955, 3, 48035, 1, 1, "t"),
            ],
        )

    def test_source_boxes_and_all_results_are_complete(self) -> None:
        identifiers = (
            47985, 47986, 47987,
            48018, 48020, 48021,
            48025, 48027, 48028,
            48032, 48034, 48035,
        )
        rows = self.connection.execute(
            "SELECT item_id,coverage,missing_dependencies FROM aaemu_item_definition_coverage "
            f"WHERE item_id IN ({','.join('?' for _ in identifiers)}) ORDER BY item_id",
            identifiers,
        ).fetchall()
        self.assertEqual(len(rows), len(identifiers))
        self.assertTrue(all(row[1:] == ("complete", "") for row in rows))
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,provenance FROM aaemu_item_definition_coverage "
                "WHERE item_id IN (47985,47986,47987) ORDER BY item_id"
            ).fetchall(),
            [(47985, PROVENANCE), (47986, PROVENANCE), (47987, PROVENANCE)],
        )

    def test_no_loot_dependency_is_orphaned(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM loots l LEFT JOIN items i ON i.id=l.item_id "
                "LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=l.item_id "
                "WHERE l.loot_pack_id IN (12951,12953,12955) "
                "AND (i.id IS NULL OR c.coverage!='complete')"
            ).fetchone(),
            (0,),
        )

    def test_previous_point0_and_initial_supply_layers_are_preserved(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT id FROM items WHERE id IN (16259,16260) ORDER BY id"
            ).fetchall(),
            [(16259,), (16260,)],
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT plot_only,plot_id,projectile_id,weapon_slot_for_autoattack_id "
                "FROM skills WHERE id=46938"
            ).fetchone(),
            (1, 5796, 9, 17),
        )

    def test_manifest_records_native_sources_and_no_3_0(self) -> None:
        self.assertTrue(self.manifest["determinism"]["identical"])
        self.assertEqual(self.manifest["scope"]["historical_3_0_rows"], 0)
        self.assertEqual(
            self.manifest["sources"]["wiki"]["authority"],
            "corroboration_only",
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual(self.connection.execute("PRAGMA quick_check").fetchone()[0], "ok")
        self.assertEqual(self.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
