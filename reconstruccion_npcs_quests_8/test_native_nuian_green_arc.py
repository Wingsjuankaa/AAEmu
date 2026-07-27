#!/usr/bin/env python3
"""Regression tests for the first AA8-native Nuian green quest arc."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
EXTRACTOR = DOMAIN / "extract_native_nuian_green_arc.py"
BUILDER = DOMAIN / "build_native_nuian_green_arc_runtime.py"
MANIFEST = DOMAIN / "generated" / "native-nuian-green-arc-v1-manifest.json"


def load_manifest(path: Path = MANIFEST):
    return json.loads(path.read_text(encoding="utf-8"))


class NativeNuianGreenArcTests(unittest.TestCase):
    def test_native_arc_selection_is_stable(self) -> None:
        manifest = load_manifest()
        self.assertEqual(
            manifest["selection"]["quest_ids"],
            [2255, 2262, 2264, 2265, 2266, 2531, 2532],
        )
        self.assertEqual(
            manifest["selection"]["counts"],
            {
                "quest_contexts": 7,
                "quest_components": 25,
                "quest_acts": 40,
            },
        )

    def test_quest_2532_reports_to_native_doodad_not_marian(self) -> None:
        proof = load_manifest()["runtime_comparison"]["quest_2532_proof"]
        native_ready = [
            row
            for row in proof["native_acts"]
            if int(row["quest_component_id"]) == 10966
        ]
        self.assertEqual(
            native_ready,
            [{
                "id": 63971,
                "act_detail_type": "QuestActConReportDoodad",
                "act_detail_id": 163,
                "quest_component_id": 10966,
            }],
        )
        runtime_ready = [
            row
            for row in proof["runtime_acts"]
            if int(row["quest_component_id"]) == 10966
        ]
        self.assertEqual(
            runtime_ready,
            [{
                "id": 15465,
                "act_detail_type": "QuestActConReportNpc",
                "act_detail_id": 2301,
                "quest_component_id": 10966,
            }],
        )

    def test_native_report_doodad_detail_163_targets_14074(self) -> None:
        manifest = load_manifest()
        quest = next(
            row
            for row in manifest["native_quest_graph"]
            if int(row["context"]["id"]) == 2532
        )
        ready = next(
            row for row in quest["components"] if int(row["id"]) == 10966
        )
        self.assertEqual(len(ready["acts"]), 1)
        self.assertEqual(
            ready["acts"][0]["detail"],
            {
                "id": 163,
                "doodad_id": 14074,
                "quest_act_obj_alias_id": 0,
                "use_alias": 0,
            },
        )

    def test_14074_is_marians_native_client_doodad_proxy(self) -> None:
        proof = load_manifest()["marian_client_doodad_proof"]
        self.assertEqual(proof["doodad_id"], 14074)
        self.assertEqual(proof["client_doodad"], 1)
        self.assertEqual(proof["npc_proxy_model"], "npctype://10581")
        self.assertEqual(
            proof["quest_func"],
            {"id": 1508, "quest_kind_id": 2, "quest_id": 2532},
        )

    def test_deployment_gate_exposes_real_closure_blockers(self) -> None:
        manifest = load_manifest()
        gate = manifest["deployment_gate"]
        closure = manifest["runtime_comparison"]["dependency_closure"]
        self.assertFalse(gate["deployable"])
        self.assertEqual(
            closure["missing_doodad_template_ids"],
            [14074, 14134],
        )
        self.assertEqual(
            gate["schema_gaps"]["quest_act_obj_item_gathers"],
            ["item_grade_id", "use_grade"],
        )
        self.assertIn("client_doodad", gate["schema_gaps"]["doodad_almighties"])
        item_closure = manifest["runtime_comparison"]["item_closure"]
        self.assertEqual(
            item_closure["runtime"]["missing_ids"],
            [16280, 21604, 24967],
        )
        self.assertEqual(
            item_closure["aa8_client_compact"]["missing_ids"],
            [47982, 47983, 47984],
        )
        self.assertEqual(item_closure["unresolved_ids"], [])

    def test_extractor_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            for output in (first, second):
                subprocess.run(
                    [sys.executable, str(EXTRACTOR), "--output", str(output)],
                    cwd=DOMAIN.parent,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_runtime_builder_closes_the_native_2532_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "runtime.sqlite3"
            build_manifest = Path(directory) / "build.json"
            subprocess.run(
                [
                    sys.executable,
                    str(BUILDER),
                    "--output",
                    str(output),
                    "--build-manifest",
                    str(build_manifest),
                ],
                cwd=DOMAIN.parent,
                check=True,
                capture_output=True,
                text=True,
            )
            connection = sqlite3.connect(output)
            try:
                self.assertEqual(
                    connection.execute(
                        "SELECT id,act_detail_type,act_detail_id "
                        "FROM quest_acts WHERE quest_component_id=10966"
                    ).fetchall(),
                    [(63971, "QuestActConReportDoodad", 163)],
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT client_doodad FROM doodad_almighties "
                        "WHERE id=14074"
                    ).fetchone(),
                    (1,),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT quest_kind_id,quest_id FROM doodad_func_quests "
                        "WHERE id=1508"
                    ).fetchone(),
                    (2, 2532),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM items "
                        "WHERE id IN (16280,21604,24967)"
                    ).fetchone(),
                    (3,),
                )
                gather_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(quest_act_obj_item_gathers)"
                    )
                }
                self.assertTrue(
                    {"item_grade_id", "use_grade"} <= gather_columns
                )
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
