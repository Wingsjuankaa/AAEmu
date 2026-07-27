#!/usr/bin/env python3
"""Regression checks for the AA8 native NPC/quest forensic catalogue."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXTRACTOR = ROOT / "extract_native_npc_quest_catalog.py"
COMMITTED = ROOT / "generated" / "native-npc-quest-catalog-v1-manifest.json"


class NativeNpcQuestCatalogTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        if not COMMITTED.is_file():
            raise AssertionError(f"Missing generated manifest: {COMMITTED}")
        cls.manifest = json.loads(COMMITTED.read_text(encoding="utf-8"))

    def test_native_row_contract(self) -> None:
        expected = {
            "actor_models": 1598,
            "models": 2907,
            "npcs": 18217,
            "quest_acts": 42446,
            "quest_components": 32191,
            "quest_contexts": 7826,
        }
        actual = {
            name: table["cached_result"]["row_count"]
            for name, table in self.manifest["tables"].items()
        }
        self.assertEqual(expected, actual)
        for table in self.manifest["tables"].values():
            result = table["cached_result"]
            self.assertEqual(result["row_count"], result["unique_ids"])

    def test_proven_relations_and_deployment_gate(self) -> None:
        closure = self.manifest["native_closure"]
        self.assertEqual([], closure["npc_to_model"]["missing_model_ids"])
        self.assertEqual(
            [], closure["model_to_actor_model"]["missing_actor_model_ids"]
        )
        self.assertEqual(
            [], closure["quest_component_to_act"]["dangling_act_ids"]
        )
        self.assertEqual(85, closure["quest_act_types"]["resolved_type_count"])
        self.assertFalse(self.manifest["deployable"])
        self.assertGreaterEqual(len(self.manifest["blockers"]), 6)

    def test_all_native_quest_act_sql_is_inventoried(self) -> None:
        inventory = self.manifest["quest_act_loader_sql_inventory"]["entries"]
        self.assertEqual(97, len(inventory))
        self.assertEqual(97, len({entry["file_offset_hex"] for entry in inventory}))
        self.assertIn("quest_acts", {entry["table"] for entry in inventory})
        audit = self.manifest["server_consumer_audit"]["quest_manager"]
        self.assertEqual(96, audit["native_concrete_table_count"])
        self.assertGreater(len(audit["native_tables_not_loaded"]), 0)

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

    def test_spawner_rows_are_not_claimed_from_client_streams(self) -> None:
        path = (
            ROOT
            / "generated"
            / "native-spawner-stream-audit-v1-manifest.json"
        )
        audit = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(0, audit["result"]["candidate_chains"])
        self.assertEqual(0, audit["result"]["rows_recovered"])


if __name__ == "__main__":
    unittest.main()
