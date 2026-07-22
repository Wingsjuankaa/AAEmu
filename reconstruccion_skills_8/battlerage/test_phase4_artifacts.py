#!/usr/bin/env python3
"""Portable structural regressions for Battlerage Phase 4 artifacts."""

from __future__ import annotations

import argparse
import json
import sqlite3
import unittest
from pathlib import Path


class Phase4BattlerageArtifactTests(unittest.TestCase):
    closure_path: Path
    compact_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.closure = json.loads(cls.closure_path.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(
            f"file:{cls.compact_path.as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_catalogue_counts(self) -> None:
        tables = self.closure["tables"]
        self.assertEqual(42, len(tables["skills"]))
        self.assertEqual(
            12,
            sum(
                int(row["show"]) and int(row.get("skill_points") or 0) > 0
                for row in tables["skills"]
            ),
        )
        self.assertEqual(6, len(tables["passive_buffs"]))
        self.assertEqual(115, len(tables["skill_effects"]))

    def test_no_playable_unresolved_dependency(self) -> None:
        diagnostics = self.closure["diagnostics"]
        self.assertEqual([], diagnostics["unresolved_effect_dependencies"])
        self.assertEqual([], diagnostics["unresolved_plot_types"])
        self.assertEqual([], diagnostics["animation_ids_missing"])
        self.assertEqual([], diagnostics["projectile_ids_missing"])
        self.assertEqual([], diagnostics["aoe_shape_ids_missing"])
        self.assertEqual([604], diagnostics["controller_ids_missing"])

    def test_triple_slash_native_chains(self) -> None:
        expected = {
            18132: [("DamageEffect", 3220), ("BuffEffect", 6548), ("SpecialEffect", 6515), ("DamageEffect", 9373)],
            18134: [("DamageEffect", 3221), ("SpecialEffect", 6628), ("DamageEffect", 9374)],
            18131: [("DamageEffect", 3218), ("SpecialEffect", 6629), ("BuffEffect", 6708), ("SpecialEffect", 15810), ("BuffEffect", 24379)],
            36401: [("DamageEffect", 9584), ("BuffEffect", 22833), ("SpecialEffect", 28540), ("DamageEffect", 9585)],
            36402: [("DamageEffect", 9586), ("SpecialEffect", 28541), ("DamageEffect", 9587)],
            36403: [("DamageEffect", 9588), ("BuffEffect", 22835), ("DamageEffect", 9908)],
            36404: [("DamageEffect", 9589), ("SpecialEffect", 28544), ("DamageEffect", 9590)],
            36405: [("DamageEffect", 9591), ("SpecialEffect", 28545), ("DamageEffect", 9592)],
            36406: [("DamageEffect", 9593), ("BuffEffect", 22838)],
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

    def test_triple_slash_plots_are_complete(self) -> None:
        for plot_id in (2541, 2855, 2856, 2857):
            count = self.connection.execute(
                "SELECT COUNT(*) FROM plot_events WHERE plot_id=?", (plot_id,)
            ).fetchone()[0]
            self.assertGreater(count, 0)

    def test_historical_relation_was_pruned(self) -> None:
        self.assertIsNone(
            self.connection.execute(
                "SELECT 1 FROM skill_effects WHERE id=16562 AND skill_id=18132"
            ).fetchone()
        )
        self.assertIsNotNone(
            self.connection.execute(
                "SELECT 1 FROM skill_effects WHERE id=52413 AND skill_id=18131"
            ).fetchone()
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual(
            "ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0]
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--compact", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    Phase4BattlerageArtifactTests.closure_path = args.closure.resolve()
    Phase4BattlerageArtifactTests.compact_path = args.compact.resolve()
    unittest.main(argv=[__file__, *remaining])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
