#!/usr/bin/env python3
"""Forensic and runtime regression tests for the AA8 quest 330 pilot."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
GENERATED = DOMAIN / "generated"
DATA = GENERATED / "native-quest-330-v3-data.json"
MANIFEST = GENERATED / "native-quest-330-v3-manifest.json"
EXTRACTOR = DOMAIN / "extract_native_quest_330.py"
BUILDER = DOMAIN / "build_native_quest_330_runtime.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest().upper()


class NativeQuest330Tests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))
        cls.base = Path(cls.manifest["sources"]["base_runtime"]["path"])

    def test_native_contract_is_closed(self) -> None:
        self.assertTrue(self.manifest["deployable"])
        self.assertEqual([], self.manifest["blockers"])
        self.assertEqual(
            {
                "aaemu_item_definition_coverage": 9,
                "item_armors": 4,
                "item_body_parts": 3,
                "items": 8,
                "quest_act_con_accept_npcs": 1,
                "quest_act_con_report_npcs": 1,
                "quest_act_supply_exps": 1,
                "quest_act_supply_items": 3,
                "quest_act_supply_selective_items": 2,
                "quest_acts": 8,
                "quest_components": 3,
                "quest_contexts": 1,
                "unit_reqs": 1,
            },
            self.manifest["table_counts"],
        )
        scope = self.manifest["scope"]
        self.assertEqual(3597, scope["accept_npc_id"])
        self.assertEqual(11541, scope["report_npc_id"])
        self.assertEqual(210, scope["custom_exp"])
        self.assertEqual(33, scope["generic_copper"])
        self.assertEqual(420, scope["generic_exp_suppressed_by_custom_exp"])
        self.assertEqual([18791, 23633, 47868, 47869, 51185], scope["reward_item_ids"])
        self.assertEqual(
            [2722, 16066, 18490, 19838, 24133, 25017, 25269],
            scope["appearance_item_ids"],
        )
        self.assertTrue(
            self.manifest["verified_existing_closure"][
                "next_quest_accept"
            ]["quest_id"]
            == 2531
        )

    def test_every_cached_result_has_a_loader_and_unique_ids(self) -> None:
        for table, source in self.manifest["source_ranges"].items():
            self.assertIn("loader", source, table)
            if "cached_result" not in source:
                continue
            result = source["cached_result"]
            if table == "unit_reqs":
                self.assertEqual(27407, result["row_count"])
                self.assertEqual(64, len(result["selected_rows_sha256"]))
                continue
            self.assertEqual(result["row_count"], result["unique_ids"], table)
            self.assertEqual(64, len(result["canonical_rows_sha256"]), table)
        self.assertEqual(
            set(
                [
                    "quest_act_con_accept_npcs",
                    "quest_act_con_report_npcs",
                    "quest_act_supply_exps",
                    "quest_act_supply_items",
                    "quest_act_supply_selective_items",
                    "quest_supplies",
                ]
            ),
            set(self.manifest["ghidra_loader_evidence"]),
        )

    def test_generation_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            subprocess.run(
                [sys.executable, str(EXTRACTOR), "--output", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                DATA.read_bytes(),
                (output / DATA.name).read_bytes(),
            )
            self.assertEqual(
                MANIFEST.read_bytes(),
                (output / MANIFEST.name).read_bytes(),
            )

    def test_builder_is_deterministic_and_runtime_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "quest330-a.sqlite3"
            second = Path(directory) / "quest330-b.sqlite3"
            common = [
                sys.executable,
                str(BUILDER),
                "--base-runtime",
                str(self.base),
                "--data",
                str(DATA),
                "--manifest",
                str(MANIFEST),
            ]
            subprocess.run(
                [*common, "--output", str(first)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [*common, "--output", str(second)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(sha256(first), sha256(second))

            connection = sqlite3.connect(first)
            try:
                context = connection.execute(
                    """
                    SELECT category_id, chapter_idx, detail_id, max_level,
                           quest_idx, race, zone_id, hide_chapter_index,
                           only_one_score_title
                    FROM quest_contexts WHERE id=330
                    """
                ).fetchone()
                self.assertEqual((3, 1, 2, 0, 1, 1, 125, 0, 0), context)
                self.assertEqual(
                    11541,
                    connection.execute(
                        "SELECT npc_id FROM quest_act_con_report_npcs WHERE id=329"
                    ).fetchone()[0],
                )
                self.assertEqual(
                    210,
                    connection.execute(
                        "SELECT exp FROM quest_act_supply_exps WHERE id=3922"
                    ).fetchone()[0],
                )
                self.assertEqual(
                    1,
                    connection.execute(
                        "SELECT COUNT(*) FROM items WHERE id=23633"
                    ).fetchone()[0],
                )
                self.assertEqual(
                    7,
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM items
                        WHERE id IN
                          (2722,16066,18490,19838,24133,25017,25269)
                        """
                    ).fetchone()[0],
                )
                self.assertEqual(
                    4,
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM item_armors
                        WHERE item_id IN (2722,16066,18490,25017)
                        """
                    ).fetchone()[0],
                )
                self.assertEqual(
                    9,
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM aaemu_item_definition_coverage
                        WHERE item_id IN
                          (23633,48541,2722,16066,18490,19838,
                           24133,25017,25269)
                          AND coverage='complete'
                          AND missing_dependencies=''
                        """
                    ).fetchone()[0],
                )
                self.assertEqual(
                    [(1, 56, 148, 0, 0)],
                    connection.execute(
                        """
                        SELECT display_msg,kind_id,value1,value2,value3
                        FROM unit_reqs
                        WHERE owner_type='QuestComponent' AND owner_id=1520
                        """
                    ).fetchall(),
                )
                self.assertEqual("ok", connection.execute("PRAGMA quick_check").fetchone()[0])
            finally:
                connection.close()

    def test_custom_exp_is_not_erased_by_later_reward_acts(self) -> None:
        source = (
            ROOT / "AAEmu.Game" / "Models" / "Game" / "Quests" / "Quest.cs"
        ).read_text(encoding="utf-8")
        method = source.split("private int GetCustomSupplies", 1)[1].split(
            "private void RemoveQuestItems", 1
        )[0]
        self.assertIn("return template.Exp;", method)
        self.assertIn("return template.Amount;", method)
        self.assertNotIn("value = 0", method)

    def test_login_synchronizes_aa8_quest_state(self) -> None:
        source = (
            ROOT
            / "AAEmu.Game"
            / "Core"
            / "Packets"
            / "C2G"
            / "CSSelectCharacterPacket.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("Connection.ActiveChar.Quests.Send();", source)
        self.assertIn("Connection.ActiveChar.Quests.SendCompleted();", source)
        self.assertNotIn("//Connection.ActiveChar.Quests.Send();", source)
        self.assertNotIn("//Connection.ActiveChar.Quests.SendCompleted();", source)

    def test_npc_customization_serializes_aa8_identity_and_all_decals(self) -> None:
        source = (
            ROOT
            / "AAEmu.Game"
            / "Core"
            / "Managers"
            / "UnitManagers"
            / "NpcManager.cs"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            2,
            source.count(
                ".SetCharacterIdentity(template.Race, template.Gender, tc.ModelId)"
            ),
        )
        for index in range(6):
            self.assertIn(
                f"Face.SetFixedDecalAsset({index}, tc.FaceFixedDecalAsset{index}Id",
                source,
            )
        self.assertIn(
            "SELECT model_id, face_item_id FROM characters WHERE face_item_id != 0",
            source,
        )
        self.assertEqual(2, source.count("SelectFaceBodyPart(") - 1)

    def test_quest_330_uses_the_native_aa8_start_requirement(self) -> None:
        self.assertEqual(
            [
                {
                    "owner_type": "QuestComponent",
                    "owner_id": 1520,
                    "display_msg": 1,
                    "kind_id": 56,
                    "value1": 148,
                    "value2": 0,
                    "value3": 0,
                }
            ],
            self.data["tables"]["unit_reqs"],
        )


if __name__ == "__main__":
    unittest.main()
