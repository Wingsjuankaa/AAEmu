#!/usr/bin/env python3
"""Regression checks for AA8 game_pak NPC spawner layer evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXTRACTOR = ROOT / "extract_gamepak_npc_spawner_layers.py"
COMMITTED = (
    ROOT / "generated" / "gamepak-native-npc-spawner-layers-v1-manifest.json"
)


class GamePakNpcSpawnerLayerTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        if not COMMITTED.is_file():
            raise AssertionError(f"Missing generated manifest: {COMMITTED}")
        cls.manifest = json.loads(COMMITTED.read_text(encoding="utf-8"))

    def test_complete_layer_contract(self) -> None:
        summary = self.manifest["summary"]
        self.assertEqual(45, self.manifest["sources"]["gamepak_global_review"]["layer_file_count"])
        self.assertEqual([], self.manifest["sources"]["gamepak_global_review"]["parse_failures"])
        self.assertEqual(157, summary["spawner_rows"])
        self.assertEqual(126, summary["unique_spawner_ids"])
        self.assertEqual(13, summary["files_with_spawners"])
        self.assertEqual(
            {"NpcAreaSpawner": 8, "NpcPointSpawner": 149},
            summary["rows_by_type"],
        )

    def test_point_spawners_close_against_native_npcs_and_models(self) -> None:
        closure = self.manifest["native_closure"]
        self.assertEqual(42, closure["point_spawner_unique_primary_ids"])
        self.assertEqual(
            42, closure["point_spawner_primary_ids_resolved_as_native_npcs"]
        )
        self.assertEqual([], closure["point_spawner_primary_ids_missing_from_native_npcs"])
        self.assertEqual(19, closure["point_spawner_unique_model_ids"])
        self.assertEqual(0, closure["area_spawner_primary_ids_resolved_as_native_npcs"])

    def test_deployment_gate_remains_closed(self) -> None:
        self.assertFalse(self.manifest["deployable"])
        gap = self.manifest["activation_gap"]
        self.assertEqual("unresolved", gap["world_id_per_root_layer"])
        self.assertEqual("unresolved", gap["active_layer_revision"])
        self.assertEqual(5, gap["zero_positions_require_resolution"])

    def test_generation_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "manifest.json"
            subprocess.run(
                [sys.executable, str(EXTRACTOR), "--output", str(output)],
                check=True,
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                COMMITTED.read_bytes(),
                output.read_bytes(),
                "Regeneration changed the committed manifest",
            )


if __name__ == "__main__":
    unittest.main()
