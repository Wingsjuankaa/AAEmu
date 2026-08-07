#!/usr/bin/env python3
"""Structural regression tests for the AA8 Shoot Rifle point-0 layer."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

DOMAIN = Path(__file__).resolve().parent
CATALOG = DOMAIN / "generated" / "native-basic-rifle-v1.json"
MANIFEST = DOMAIN / "generated" / "point0-rifle-stack-v1-runtime-manifest.json"


class ShootRifleRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.manifest["output"]["path"])

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_native_authority_and_closed_counts(self):
        self.assertFalse(self.catalog["historical_3_0_used"])
        self.assertEqual(16, self.catalog["table_counts"]["plot_events"])
        self.assertEqual(17, self.catalog["table_counts"]["plot_effects"])
        self.assertEqual([5796], self.catalog["diagnostics"]["reached_plot_ids"])
        self.assertFalse(self.catalog["diagnostics"]["unresolved_effect_dependencies"])
        self.assertFalse(self.catalog["diagnostics"]["unresolved_plot_types"])

    def test_skill_executes_native_plot_from_ranged_slot(self):
        row = self.connection.execute(
            "SELECT plot_only,plot_id,weapon_slot_for_autoattack_id,max_range,auto_fire,start_autoattack "
            "FROM skills WHERE id=46938"
        ).fetchone()
        self.assertEqual((1, 5796, 17, 15.0, 1, 1), row)

    def test_native_damage_animation_and_projectile_exist(self):
        damages = self.connection.execute(
            "SELECT id,dps_multiplier,use_ranged_weapon,weapon_slot_id FROM damage_effects "
            "WHERE id IN (14635,14638,14639) ORDER BY id"
        ).fetchall()
        self.assertEqual([(14635, 0.6, 1, 17), (14638, 0.6, 1, 17), (14639, 0.6, 1, 17)], damages)
        self.assertEqual(1, self.connection.execute("SELECT COUNT(*) FROM anims WHERE id=1074").fetchone()[0])
        self.assertEqual(1, self.connection.execute("SELECT COUNT(*) FROM projectiles WHERE id=1347").fetchone()[0])

    def test_sqlite_integrity(self):
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
