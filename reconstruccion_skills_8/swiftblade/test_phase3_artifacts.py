#!/usr/bin/env python3
"""Portable structural regressions for the generated Phase 3 artifacts."""

from __future__ import annotations

import argparse
import json
import sqlite3
import unittest
from pathlib import Path


class Phase3ArtifactTests(unittest.TestCase):
    closure_path: Path
    compact_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.closure = json.loads(cls.closure_path.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(f"file:{cls.compact_path.as_posix()}?mode=ro", uri=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_swiftblade_catalogue_counts(self) -> None:
        tables = self.closure["tables"]
        self.assertEqual(46, len(tables["skills"]))
        self.assertEqual(12, sum(int(row["show"]) for row in tables["skills"]))
        self.assertEqual(6, len(tables["passive_buffs"]))
        self.assertEqual(140, len(tables["skill_effects"]))

    def test_no_unresolved_dependency(self) -> None:
        diagnostics = self.closure["diagnostics"]
        self.assertEqual([], diagnostics["unresolved_effect_dependencies"])
        self.assertEqual([], diagnostics["unresolved_plot_types"])
        self.assertEqual([], diagnostics["animation_ids_missing"])
        self.assertEqual([], diagnostics["aoe_shape_ids_missing"])
        self.assertGreater(len(diagnostics["aoe_shape_ids_requested"]), 0)

    def test_golden_skill_chains(self) -> None:
        expected = {
            40331: [("DamageEffect", 12250), ("SpecialEffect", 42648)],
            40337: [("DamageEffect", 12257)],
        }
        for skill_id, chain in expected.items():
            actual = self.connection.execute(
                """
                SELECT e.actual_type, e.actual_id
                FROM skill_effects se
                JOIN effects e ON e.id = se.effect_id
                WHERE se.skill_id = ?
                ORDER BY se.id
                """,
                (skill_id,),
            ).fetchall()
            self.assertEqual(chain, actual)
        sinister_count = self.connection.execute(
            "SELECT COUNT(*) FROM skill_effects WHERE skill_id=40339"
        ).fetchone()[0]
        self.assertEqual(9, sinister_count)

    def test_golden_swiftblade_aoe_shapes(self) -> None:
        expected = {
            15485: (1, 5.5, 0.0, 0.0),
            15575: (2, 1.0, 2.6, 3.5),
            15693: (1, 0.0, 0.0, 0.0),
        }
        for shape_id, values in expected.items():
            actual = self.connection.execute(
                "SELECT kind_id, value1, value2, value3 FROM aoe_shapes WHERE id=?",
                (shape_id,),
            ).fetchone()
            self.assertEqual(values, actual)

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--compact", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    Phase3ArtifactTests.closure_path = args.closure.resolve()
    Phase3ArtifactTests.compact_path = args.compact.resolve()
    unittest.main(argv=[__file__, *remaining])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
