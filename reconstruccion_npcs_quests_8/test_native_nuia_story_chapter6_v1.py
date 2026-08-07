#!/usr/bin/env python3
"""Regression tests for the transversal Nuia story runtime through chapter 6."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = DOMAIN / "generated" / "native-nuia-story-chapter6-v1-runtime-manifest.json"


class NativeNuiaStoryChapter6V1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.runtime = sqlite3.connect(
            f"file:{Path(cls.manifest['output']['path']).resolve().as_posix()}?mode=ro",
            uri=True,
        )
        graph_path = Path(cls.manifest["sources"]["graph"]["path"])
        cls.graph = sqlite3.connect(
            f"file:{graph_path.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()
        cls.graph.close()

    def test_scope_is_the_exact_native_nuia_racial_category(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(55, scope["quest_contexts"])
        self.assertEqual(222, scope["quest_components"])
        self.assertEqual(344, scope["quest_acts"])
        self.assertEqual(18, scope["act_types"])
        self.assertEqual(list(range(7)), scope["chapters"])
        self.assertEqual(55, len(scope["quest_ids"]))

    def test_runtime_components_and_acts_match_the_frozen_graph(self) -> None:
        graph_components = self.graph.execute(
            "SELECT component_id,component_kind_id FROM story_quest_components "
            "ORDER BY component_id"
        ).fetchall()
        ids = [row[0] for row in graph_components]
        runtime_components = self.runtime.execute(
            "SELECT id,component_kind_id FROM quest_components WHERE id IN "
            f"({','.join('?' for _ in ids)}) ORDER BY id",
            ids,
        ).fetchall()
        self.assertEqual(graph_components, runtime_components)

        graph_acts = self.graph.execute(
            "SELECT quest_act_id,component_id,act_detail_type,act_detail_id "
            "FROM story_quest_acts ORDER BY quest_act_id"
        ).fetchall()
        act_ids = [row[0] for row in graph_acts]
        runtime_acts = self.runtime.execute(
            "SELECT id,quest_component_id,act_detail_type,act_detail_id "
            "FROM quest_acts WHERE id IN "
            f"({','.join('?' for _ in act_ids)}) ORDER BY id",
            act_ids,
        ).fetchall()
        self.assertEqual(graph_acts, runtime_acts)

    def test_all_story_item_dependencies_are_creatable(self) -> None:
        item_ids = self.manifest["scope"]["story_item_ids"]
        rows = self.runtime.execute(
            "SELECT i.id,c.coverage FROM items i "
            "JOIN aaemu_item_definition_coverage c ON c.item_id=i.id "
            f"WHERE i.id IN ({','.join('?' for _ in item_ids)}) ORDER BY i.id",
            item_ids,
        ).fetchall()
        self.assertEqual(61, len(rows))
        self.assertTrue(all(row[1] == "complete" for row in rows))

    def test_bounded_legacy_materializations_are_auditable(self) -> None:
        ids = self.manifest["scope"]["legacy_materialized_item_ids"]
        rows = self.runtime.execute(
            "SELECT item_id,authority,state FROM "
            "aaemu_nuia_story_chapter6_materializations ORDER BY item_id"
        ).fetchall()
        self.assertEqual(
            [(item_id, "legacy_3_0_corroborated", "active_bounded") for item_id in ids],
            rows,
        )
        self.assertEqual(
            (24087, 9, 1),
            self.runtime.execute(
                "SELECT item_id,slot_type_id,repairable FROM item_armors "
                "WHERE item_id=24087"
            ).fetchone(),
        )

    def test_native_phase_a_items_are_promoted_after_dependency_audit(self) -> None:
        ids = self.manifest["scope"]["native_promoted_item_ids"]
        rows = self.runtime.execute(
            "SELECT item_id,coverage,provenance FROM aaemu_item_definition_coverage "
            f"WHERE item_id IN ({','.join('?' for _ in ids)}) ORDER BY item_id",
            ids,
        ).fetchall()
        self.assertEqual(len(ids), len(rows))
        self.assertTrue(all(row[1] == "complete" for row in rows))
        self.assertTrue(all(row[2].startswith("client_compact_8+") for row in rows))

    def test_all_missing_logical_doodads_have_native_proxy_groups(self) -> None:
        ids = self.manifest["scope"]["client_doodad_ids"]
        doodads = self.runtime.execute(
            "SELECT id,client_doodad FROM doodad_almighties WHERE id IN "
            f"({','.join('?' for _ in ids)}) ORDER BY id",
            ids,
        ).fetchall()
        self.assertEqual([(item, 1) for item in ids], doodads)
        groups = self.runtime.execute(
            "SELECT doodad_almighty_id,model FROM doodad_func_groups WHERE "
            f"doodad_almighty_id IN ({','.join('?' for _ in ids)}) "
            "AND model LIKE 'npctype://%' ORDER BY doodad_almighty_id",
            ids,
        ).fetchall()
        self.assertEqual(ids, [row[0] for row in groups])

    def test_unproven_product_edges_remain_explicit(self) -> None:
        self.assertEqual(
            [2492, 4404],
            [row["quest_id"] for row in self.manifest["observation_required"]],
        )
        self.assertTrue(self.manifest["safety"]["opaque_product_edges_not_invented"])

    def test_previous_point0_repairs_remain_present(self) -> None:
        self.assertEqual(
            [(21604, "complete"), (24967, "complete")],
            self.runtime.execute(
                "SELECT item_id,coverage FROM aaemu_item_definition_coverage "
                "WHERE item_id IN (21604,24967) ORDER BY item_id"
            ).fetchall(),
        )
        self.assertEqual(
            37,
            self.runtime.execute(
                "SELECT COUNT(*) FROM merchant_goods WHERE merchant_pack_id=914119"
            ).fetchone()[0],
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.runtime.execute("PRAGMA integrity_check").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
