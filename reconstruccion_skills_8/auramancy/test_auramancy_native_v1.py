#!/usr/bin/env python3
"""Structural and regression gates for the AA8 Auramancy V2 runtime."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unittest
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("unittest_args", nargs="*")
    return parser.parse_args()


class AuramancyNativeV1Tests(unittest.TestCase):
    runtime_path: Path
    manifest_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = sqlite3.connect(
            f"file:{cls.runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )
        cls.runtime.row_factory = sqlite3.Row
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()

    def test_all_roots_and_passives_are_enabled(self) -> None:
        verification = self.manifest["verification"]
        self.assertEqual(25, verification["root_count"])
        self.assertEqual(12, verification["visible_root_count"])
        self.assertEqual(25, verification["enabled_root_count"])
        self.assertEqual(0, verification["quarantined_root_count"])
        self.assertEqual(6, verification["passive_count"])
        self.assertEqual(12, verification["learnable_visible_root_count"])
        self.assertEqual(
            [],
            list(self.runtime.execute(
                "SELECT skill_id,status FROM native_combat_skill_status "
                "WHERE ability_id=4 AND status!='enabled'"
            )),
        )

    def test_all_visible_skills_remain_learnable(self) -> None:
        expected = [
            10152, 10710, 10714, 11380, 11424, 11429,
            11869, 11989, 11991, 16486, 18222, 23589,
        ]
        rows = [tuple(row) for row in self.runtime.execute(
            "SELECT id,need_learn FROM skills WHERE ability_id=4 AND show=1 ORDER BY id"
        )]
        self.assertEqual([(skill_id, 1) for skill_id in expected], rows)

    def test_teleportation_is_bounded_parent_plus_exact_aa8_closure(self) -> None:
        self.assertEqual(
            (10152, 4, 20, 35000, 3786, 264, 271, 1, 0),
            tuple(self.runtime.execute(
                "SELECT id,ability_id,ability_level,cooldown_time,cooldown_tag_id,"
                "fire_anim_id,fx_group_id,ignore_global_cooldown,default_gcd "
                "FROM skills WHERE id=10152"
            ).fetchone()),
        )
        self.assertEqual(
            [(273, 235), (20536, 26043)],
            [tuple(row) for row in self.runtime.execute(
                "SELECT id,effect_id FROM skill_effects WHERE skill_id=10152 ORDER BY id"
            )],
        )
        self.assertEqual(
            (11, 15, 0, 0, 0),
            tuple(self.runtime.execute(
                "SELECT special_effect_type_id,value1,value2,value3,value4 "
                "FROM special_effects WHERE id=27"
            ).fetchone()),
        )
        self.assertEqual(
            (10, 1, 1, 0),
            tuple(self.runtime.execute(
                "SELECT buff_tag_id,cure_count,dispel_count,stack "
                "FROM dispel_effects WHERE id=631"
            ).fetchone()),
        )
        self.assertEqual(
            "Teleportation",
            self.runtime.execute(
                "SELECT en_us FROM localized_texts WHERE tbl_name='skills' "
                "AND tbl_column_name='name' AND idx=10152"
            ).fetchone()[0],
        )
        self.assertEqual(
            "exact AA8 native rows",
            self.manifest["authority"]["teleportation_closure"],
        )

    def test_conversion_shield_subset_is_data_driven(self) -> None:
        rows = [tuple(row) for row in self.runtime.execute(
            "SELECT b.id,t.event_id,t.use_damage_amount,h.fixed_min,h.fixed_max,"
            "h.use_fixed_heal,h.percent "
            "FROM buffs b JOIN buff_triggers t ON t.buff_id=b.id "
            "JOIN effects e ON e.id=t.effect_id AND e.actual_type='HealEffect' "
            "JOIN heal_effects h ON h.id=e.actual_id "
            "WHERE b.id IN (745,854,855,856,857,21416,21375,28209) "
            "AND t.event_id=9 ORDER BY b.id"
        )]
        self.assertEqual(8, len(rows))
        self.assertTrue(all(row[1] == 9 and row[2] == 1 for row in rows))
        self.assertTrue(all(row[3] == row[4] and row[5] == 1 and row[6] == 1 for row in rows))
        self.assertEqual(
            {170, 190, 210, 230, 250, 333},
            {row[3] for row in rows},
        )

    def test_native_passive_progression_is_preserved(self) -> None:
        self.assertEqual(
            [
                (13, 498, 8, 0),
                (21, 621, 5, 0),
                (98, 2784, 6, 0),
                (251, 7554, 7, 0),
                (252, 7553, 4, 0),
                (298, 927, 3, 0),
            ],
            [tuple(row) for row in self.runtime.execute(
                "SELECT id,buff_id,req_points,skill_points FROM passive_buffs "
                "WHERE ability_id=4 ORDER BY id"
            )],
        )

    def test_closed_trees_remain_present_without_status_regression(self) -> None:
        expected = {
            10752: 7,   # Sorcery Flamebolt
            14835: 6,   # Archery Endless Arrows
            11918: 1,   # Battlerage Charge
            10481: 8,   # Shadowplay Poisoned Weapons
        }
        for skill_id, ability_id in expected.items():
            row = self.runtime.execute(
                "SELECT s.ability_id,n.status FROM skills s "
                "LEFT JOIN native_combat_skill_status n ON n.skill_id=s.id "
                "WHERE s.id=?", (skill_id,)
            ).fetchone()
            self.assertIsNotNone(row, skill_id)
            self.assertEqual(ability_id, row[0], skill_id)
            if row[1] is not None:
                self.assertEqual("enabled", row[1], skill_id)

    def test_sqlite_and_determinism_gates(self) -> None:
        self.assertEqual("ok", self.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.runtime.execute("PRAGMA integrity_check").fetchone()[0])
        self.assertEqual("confirmed", self.manifest["determinism"]["status"])
        self.assertEqual(
            self.manifest["determinism"]["first"]["sha256"],
            self.manifest["determinism"]["second"]["sha256"],
        )


if __name__ == "__main__":
    args = parse_args()
    AuramancyNativeV1Tests.runtime_path = args.runtime.resolve()
    AuramancyNativeV1Tests.manifest_path = args.manifest.resolve()
    unittest.main(argv=[sys.argv[0], *args.unittest_args])
