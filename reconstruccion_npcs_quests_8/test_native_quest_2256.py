#!/usr/bin/env python3
"""Regression tests for the AA8-native quest 2256 client-doodad closure."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
EXTRACTOR = DOMAIN / "extract_native_quest_2256.py"
BUILDER = DOMAIN / "build_native_quest_2256_runtime.py"
MANIFEST = (
    DOMAIN / "generated" / "native-quest-2256-client-doodad-v1-manifest.json"
)


class NativeQuest2256Tests(unittest.TestCase):
    def test_forensic_manifest_proves_object_not_npc_report(self) -> None:
        document = json.loads(MANIFEST.read_text(encoding="utf-8"))
        quest = document["deployable_quest_graph"][0]
        acts = {
            int(act["id"]): act
            for component in quest["components"]
            for act in component["acts"]
        }
        self.assertEqual(
            acts[63974]["detail"],
            {
                "id": 797,
                "doodad_id": 14074,
                "quest_act_obj_alias_id": 0,
                "use_alias": 0,
            },
        )
        self.assertEqual(
            acts[63975]["detail"],
            {
                "id": 165,
                "doodad_id": 14073,
                "quest_act_obj_alias_id": 6695,
                "use_alias": 1,
            },
        )
        proof = document["proof"]["client_doodad_14073"]
        self.assertEqual(proof["npc_proxy_model"], "npctype://10646")
        self.assertEqual(proof["use_target_highlight"], 1)
        self.assertEqual(
            document["deployment_gate"]["suppressed_adjacent_quest_ids"],
            [2257],
        )

    def test_extractor_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outputs = [Path(directory) / f"manifest-{index}.json" for index in range(2)]
            for output in outputs:
                subprocess.run(
                    [sys.executable, str(EXTRACTOR), "--output", str(output)],
                    cwd=DOMAIN.parent,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())

    def test_runtime_builder_replaces_only_quest_2256_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "runtime.sqlite3"
            build_manifest = Path(directory) / "runtime.json"
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
                        "FROM quest_acts "
                        "WHERE quest_component_id IN (10362,10364,10366) "
                        "ORDER BY id"
                    ).fetchall(),
                    [
                        (63974, "QuestActConAcceptDoodad", 797),
                        (63975, "QuestActConReportDoodad", 165),
                        (64096, "QuestActSupplyExp", 3926),
                        (65624, "QuestActSupplyItem", 8874),
                    ],
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT client_doodad,use_target_highlight "
                        "FROM doodad_almighties WHERE id=14073"
                    ).fetchone(),
                    (1, 1),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT model FROM doodad_func_groups WHERE id=41492"
                    ).fetchone(),
                    ("npctype://10646",),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM doodad_funcs "
                        "WHERE id IN (38376,38377)"
                    ).fetchone(),
                    (0,),
                )
                self.assertEqual(
                    connection.execute("PRAGMA quick_check").fetchone(),
                    ("ok",),
                )
            finally:
                connection.close()

    def test_builder_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hashes = []
            for index in range(2):
                output = Path(directory) / f"runtime-{index}.sqlite3"
                build_manifest = Path(directory) / f"runtime-{index}.json"
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
                digest = hashlib.sha256(output.read_bytes()).hexdigest()
                hashes.append(digest)
            self.assertEqual(hashes[0], hashes[1])


if __name__ == "__main__":
    unittest.main()
