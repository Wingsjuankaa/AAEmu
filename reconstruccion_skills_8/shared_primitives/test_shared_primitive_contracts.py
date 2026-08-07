from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path(__file__).resolve().parent / "generated" / "shared-primitives-v1.json"


class SharedPrimitiveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def test_all_eight_planned_primitives_are_present(self) -> None:
        self.assertEqual(
            set(self.contract["primitives"]),
            {
                "ResetAoeDiminishingEffect",
                "HealEffect",
                "RestoreManaEffect",
                "BubbleEffect",
                "ManaBurnEffect",
                "SpawnEffect",
                "KillNpcWithoutCorpseEffect",
                "ExtendChargeEffect",
            },
        )

    def test_catalog_fanout_is_frozen(self) -> None:
        expected = {
            "ResetAoeDiminishingEffect": 35,
            "HealEffect": 52,
            "RestoreManaEffect": 3,
            "BubbleEffect": 26,
            "ManaBurnEffect": 6,
            "SpawnEffect": 6,
            "KillNpcWithoutCorpseEffect": 3,
            "ExtendChargeEffect": 2,
        }
        self.assertEqual(
            {
                primitive: row["affected_skill_count"]
                for primitive, row in self.contract["primitives"].items()
            },
            expected,
        )

    def test_every_affected_root_reaches_the_declared_native_primitive(self) -> None:
        for primitive, row in self.contract["primitives"].items():
            with self.subTest(primitive=primitive):
                self.assertGreater(row["effect_reference_count"], 0)
                self.assertTrue(row["detail_rows"])
                self.assertTrue(
                    all(skill["references"] for skill in row["affected_skills"])
                )

    def test_stage15_dossiers_are_pinned_and_wiki_is_not_used(self) -> None:
        self.assertEqual(self.contract["authority"]["wiki"], "not_used")
        for primitive, row in self.contract["primitives"].items():
            with self.subTest(primitive=primitive):
                evidence = row["semantic_dossier"]
                self.assertEqual(len(evidence["sha256"]), 64)
                self.assertEqual(len(evidence["stage_15_sha256"]), 64)
                self.assertEqual(len(evidence["source_index_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
