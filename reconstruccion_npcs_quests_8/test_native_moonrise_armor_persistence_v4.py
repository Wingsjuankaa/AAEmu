#!/usr/bin/env python3
"""Regression tests for Moonrise armor crates and direct item persistence V4."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
ROOT = DOMAIN.parent
MANIFEST = (
    DOMAIN
    / "generated"
    / "native-moonrise-armor-persistence-v4-runtime-manifest.json"
)
PROVENANCE = "client_compact_8+game11_native+moonrise_armor_v4"


class NativeMoonriseArmorPersistenceV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.manifest["output"]["path"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_armor_box_skill_effect_closure_is_exact(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT id,skill_id,effect_id,consume_source_item,end_level "
                "FROM skill_effects WHERE id IN (59713,59715,59717) ORDER BY id"
            ).fetchall(),
            [
                (59713, 42225, 78589, 1, 255),
                (59715, 42227, 78591, 1, 255),
                (59717, 42229, 78593, 1, 255),
            ],
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id,actual_type,actual_id FROM effects "
                "WHERE id IN (78589,78591,78593) ORDER BY id"
            ).fetchall(),
            [
                (78589, "GainLootPackItemEffect", 4215),
                (78591, "GainLootPackItemEffect", 4217),
                (78593, "GainLootPackItemEffect", 4219),
            ],
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id,loot_pack_id FROM gain_loot_pack_item_effects "
                "WHERE id IN (4215,4217,4219) ORDER BY id"
            ).fetchall(),
            [(4215, 12950), (4217, 12952), (4219, 12954)],
        )

    def test_each_armor_box_grants_exactly_four_description_items(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT loot_pack_id,\"group\",item_id,min_amount,max_amount,always_drop "
                "FROM loots WHERE loot_pack_id IN (12950,12952,12954) "
                "ORDER BY loot_pack_id,\"group\""
            ).fetchall(),
            [
                (12950, 1, 48015, 1, 1, "t"),
                (12950, 2, 48016, 1, 1, "t"),
                (12950, 3, 48017, 1, 1, "t"),
                (12950, 4, 48019, 1, 1, "t"),
                (12952, 1, 48022, 1, 1, "t"),
                (12952, 2, 48023, 1, 1, "t"),
                (12952, 3, 48024, 1, 1, "t"),
                (12952, 4, 48026, 1, 1, "t"),
                (12954, 1, 48029, 1, 1, "t"),
                (12954, 2, 48030, 1, 1, "t"),
                (12954, 3, 48031, 1, 1, "t"),
                (12954, 4, 48033, 1, 1, "t"),
            ],
        )

    def test_sources_and_results_have_complete_native_coverage(self) -> None:
        identifiers = (
            47982, 47983, 47984,
            48015, 48016, 48017, 48019,
            48022, 48023, 48024, 48026,
            48029, 48030, 48031, 48033,
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
                "WHERE item_id IN (47982,47983,47984) ORDER BY item_id"
            ).fetchall(),
            [(47982, PROVENANCE), (47983, PROVENANCE), (47984, PROVENANCE)],
        )

    def test_rank_one_story_infusion_exchange_is_preserved(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT r.skill_id,r.item_id,r.amount,p.item_id,p.amount "
                "FROM skill_reagents r JOIN skill_products p ON p.skill_id=r.skill_id "
                "WHERE r.skill_id=43013"
            ).fetchall(),
            [(43013, 48507, 1, 48845, 1)],
        )

    def test_direct_character_save_persists_items_in_same_transaction(self) -> None:
        source = (
            ROOT / "AAEmu.Game" / "Models" / "Game" / "Char" / "Character.cs"
        ).read_text(encoding="utf-8")
        start = source.index("public bool SaveDirectlyToDatabase()")
        end = source.index("public bool SaveNewCharacterToDatabase", start)
        direct_save = source[start:end]
        item_save = direct_save.index("ItemManager.Instance.Save(sqlConnection, transaction);")
        character_save = direct_save.index("saved = Save(sqlConnection, transaction);")
        commit = direct_save.index("transaction.Commit();")
        self.assertLess(item_save, character_save)
        self.assertLess(character_save, commit)

    def test_previous_component_crate_and_quest_layers_are_preserved(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT loot_pack_id,item_id FROM loots "
                "WHERE loot_pack_id=12953 ORDER BY \"group\""
            ).fetchall(),
            [(12953, 48025), (12953, 48027), (12953, 48028)],
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT id FROM quest_acts WHERE quest_component_id=9962 ORDER BY id"
            ).fetchall(),
            [(40848,), (64100,), (65260,), (65261,), (65262,), (65323,), (65675,)],
        )

    def test_manifest_and_sqlite_integrity(self) -> None:
        self.assertTrue(self.manifest["determinism"]["identical"])
        self.assertEqual(self.manifest["scope"]["historical_3_0_rows"], 0)
        self.assertEqual(
            self.manifest["sources"]["wiki"]["authority"], "corroboration_only"
        )
        self.assertEqual(self.connection.execute("PRAGMA quick_check").fetchone()[0], "ok")
        self.assertEqual(
            self.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
        )


if __name__ == "__main__":
    unittest.main()
