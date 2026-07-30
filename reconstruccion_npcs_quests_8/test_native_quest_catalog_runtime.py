#!/usr/bin/env python3
"""Regression tests for the transversal native AA8 quest runtime."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
REPO = DOMAIN.parent
RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest-catalog-v2.sqlite3"
)
GRAPH = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics"
    r"\aa8-client-knowledge.sqlite"
)
MANIFEST = DOMAIN / "generated" / "native-quest-catalog-v2-runtime-manifest.json"
EXPECTED_OVERRIDES = {330, 2255, 2256, 2257, 2258, 2532}
EXPECTED_ACT_TYPES = {
    "QuestActConAcceptItem",
    "QuestActConAcceptDoodad",
    "QuestActConAcceptNpc",
    "QuestActConAutoComplete",
    "QuestActConReportDoodad",
    "QuestActConReportNpc",
    "QuestActObjInteraction",
    "QuestActObjItemGather",
    "QuestActObjItemUse",
    "QuestActObjMonsterGroupHunt",
    "QuestActObjMonsterHunt",
    "QuestActObjTalk",
    "QuestActSupplyCopper",
    "QuestActSupplyExp",
    "QuestActSupplyItem",
    "QuestActSupplySelectiveItem",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


class NativeQuestCatalogRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.runtime = sqlite3.connect(
            f"file:{RUNTIME.resolve().as_posix()}?mode=ro", uri=True
        )
        cls.graph = sqlite3.connect(
            f"file:{GRAPH.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()
        cls.graph.close()

    def test_manifest_binds_exact_inputs_and_output(self) -> None:
        self.assertEqual("native-quest-catalog-v2", self.manifest["phase"])
        self.assertEqual(sha256(RUNTIME), self.manifest["output"]["sha256"])
        self.assertEqual(sha256(GRAPH), self.manifest["sources"]["graph"]["sha256"])
        self.assertEqual(
            "C47AAF43F7BBA5F16D31CD30EBCB9B60A5103C07E13DE39D382DECFBBE82CD68",
            self.manifest["dossier"]["json_sha256"],
        )

    def test_scope_is_bounded_and_exhaustively_classified(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(7826, scope["native_quest_count"])
        self.assertEqual(555, scope["native_safe_count"])
        self.assertEqual(6, scope["validated_override_count"])
        self.assertEqual(7265, scope["quarantined_count"])
        self.assertEqual(561, scope["active_quest_count"])
        self.assertEqual(
            scope["native_quest_count"],
            scope["native_safe_count"]
            + scope["validated_override_count"]
            + scope["quarantined_count"],
        )
        self.assertEqual(EXPECTED_ACT_TYPES, set(scope["enabled_act_types"]))
        self.assertNotIn(
            "unsupported_act:QuestActConAcceptItem",
            scope["quarantine_reason_counts"],
        )
        self.assertEqual(
            4226,
            scope["quarantine_reason_counts"]["incomplete_item_definition"],
        )

    def test_active_contexts_equal_catalog_allow_list(self) -> None:
        active = {row[0] for row in self.runtime.execute("SELECT id FROM quest_contexts")}
        allowed = {
            row[0]
            for row in self.runtime.execute(
                "SELECT quest_id FROM aaemu_native_quest_runtime_catalog "
                "WHERE state IN ('native_safe','validated_override')"
            )
        }
        self.assertEqual(allowed, active)
        self.assertEqual(561, len(active))

    def test_validated_overrides_are_preserved(self) -> None:
        actual = {
            row[0]
            for row in self.runtime.execute(
                "SELECT quest_id FROM aaemu_native_quest_runtime_catalog "
                "WHERE state='validated_override'"
            )
        }
        self.assertEqual(EXPECTED_OVERRIDES, actual)
        for quest_id in EXPECTED_OVERRIDES:
            self.assertIsNotNone(
                self.runtime.execute(
                    "SELECT 1 FROM quest_contexts WHERE id=?", (quest_id,)
                ).fetchone()
            )

    def test_every_active_act_has_enabled_support_and_detail(self) -> None:
        unsupported = self.runtime.execute(
            """
            SELECT COUNT(*) FROM quest_acts a
            LEFT JOIN aaemu_native_quest_runtime_act_support s
              ON s.act_type=a.act_detail_type
            WHERE COALESCE(s.enabled,0)=0
            """
        ).fetchone()[0]
        self.assertEqual(0, unsupported)

        support = {
            row[0]: row[1]
            for row in self.runtime.execute(
                "SELECT act_type,detail_table "
                "FROM aaemu_native_quest_runtime_act_support WHERE enabled=1"
            )
        }
        self.assertEqual(EXPECTED_ACT_TYPES, set(support))
        for act_type, table in support.items():
            missing = self.runtime.execute(
                f"""
                SELECT COUNT(*) FROM quest_acts a
                LEFT JOIN {table} d ON d.id=a.act_detail_id
                WHERE a.act_detail_type=? AND d.id IS NULL
                """,
                (act_type,),
            ).fetchone()[0]
            self.assertEqual(0, missing, act_type)

    def test_native_safe_core_rows_equal_forensic_graph(self) -> None:
        safe_ids = {
            row[0]
            for row in self.runtime.execute(
                "SELECT quest_id FROM aaemu_native_quest_runtime_catalog "
                "WHERE state='native_safe'"
            )
        }
        graph_contexts = {}
        for native_id, row_json in self.graph.execute(
            "SELECT native_id,row_json FROM native_rows "
            "WHERE source_table='quest_contexts' AND state='confirmed'"
        ):
            quest_id = int(native_id)
            if quest_id in safe_ids:
                graph_contexts[quest_id] = json.loads(row_json)
        columns = [
            row[1] for row in self.runtime.execute("PRAGMA table_info(quest_contexts)")
        ]
        runtime_contexts = {
            row[0]: tuple(row)
            for row in self.runtime.execute(
                f"SELECT {','.join(columns)} FROM quest_contexts ORDER BY id"
            )
            if row[0] in safe_ids
        }
        expected = {
            quest_id: tuple(row[column] for column in columns)
            for quest_id, row in graph_contexts.items()
        }
        self.assertEqual(expected, runtime_contexts)

    def test_no_core_orphans_and_sqlite_is_healthy(self) -> None:
        self.assertEqual(
            0,
            self.runtime.execute(
                """
                SELECT COUNT(*) FROM quest_components c
                LEFT JOIN quest_contexts q ON q.id=c.quest_context_id
                WHERE q.id IS NULL
                """
            ).fetchone()[0],
        )
        self.assertEqual(
            0,
            self.runtime.execute(
                """
                SELECT COUNT(*) FROM quest_acts a
                LEFT JOIN quest_components c ON c.id=a.quest_component_id
                WHERE c.id IS NULL
                """
            ).fetchone()[0],
        )
        self.assertEqual("ok", self.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual(
            "ok", self.runtime.execute("PRAGMA integrity_check").fetchone()[0]
        )

    def test_server_reads_native_bounds_and_supported_generic_consumers(self) -> None:
        manager = (
            REPO / "AAEmu.Game" / "Core" / "Managers" / "QuestManager.cs"
        ).read_text(encoding="utf-8")
        quest = (
            REPO / "AAEmu.Game" / "Models" / "Game" / "Quests" / "Quest.cs"
        ).read_text(encoding="utf-8")
        character_quests = (
            REPO
            / "AAEmu.Game"
            / "Models"
            / "Game"
            / "Char"
            / "CharacterQuests.cs"
        ).read_text(encoding="utf-8")
        self.assertIn('reader.GetByte("min_level", 0)', manager)
        self.assertIn('reader.GetByte("max_level", 0)', manager)
        self.assertIn('reader.GetByte("race", byte.MaxValue)', manager)
        self.assertIn("case nameof(QuestActSupplyCopper)", quest)
        self.assertNotIn('"QuestActSupplyCoppers"', quest)
        self.assertIn("case nameof(QuestActConAcceptItem)", quest)
        self.assertIn(
            "template.Cleanup || template.DropWhenDestroy || template.DestroyWhenDrop",
            quest,
        )
        self.assertIn("[AA8QuestCatalog] Skipping active quest", character_quests)


if __name__ == "__main__":
    unittest.main()
