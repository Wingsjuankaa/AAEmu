#!/usr/bin/env python3
"""Structural regressions for the AA8 Sorcery runtime reconstruction v4."""

from __future__ import annotations

import argparse
import json
import sqlite3
import unittest
from pathlib import Path


class SorcerySpecializationV2Tests(unittest.TestCase):
    runtime_path = Path(
        r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v4.sqlite3"
    )
    manifest_path = Path(__file__).resolve().parent / "generated" / "sorcery-specialization-v4.manifest.json"

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.runtime = sqlite3.connect(
            f"file:{cls.runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()

    def test_authority_boundary_is_explicit(self) -> None:
        self.assertEqual(
            "root_row_candidate_only", self.manifest["authority"]["aa10_crosswalk"]
        )
        self.assertEqual(
            "executable_closure_and_plot_contract",
            self.manifest["authority"]["aa8_native_sqlite"],
        )
        self.assertEqual(
            {"10151": "aa10_only", "10153": "aa10_only"},
            self.manifest["crosswalk"]["roots"],
        )
        for table in self.manifest["merge"].values():
            self.assertFalse(table["historical_values_preserved"])

    def test_runtime_roots_and_statuses(self) -> None:
        roots = self.runtime.execute(
            "SELECT id,ability_id,ability_level,plot_id,cooldown_time,casting_time,need_learn "
            "FROM skills WHERE id IN (10151,10153) ORDER BY id"
        ).fetchall()
        self.assertEqual(
            [(10151, 7, 25, 3096, 28000, 0, 1), (10153, 7, 10, None, 0, 1500, 1)],
            roots,
        )
        statuses = self.runtime.execute(
            "SELECT skill_id,status FROM native_combat_skill_status "
            "WHERE skill_id IN (10151,10153) ORDER BY skill_id"
        ).fetchall()
        self.assertEqual([(10151, "enabled"), (10153, "enabled")], statuses)

    def test_native_effect_closure_is_exact(self) -> None:
        effects = self.runtime.execute(
            "SELECT skill_id,id FROM skill_effects "
            "WHERE skill_id IN (10151,10153) ORDER BY skill_id,id"
        ).fetchall()
        self.assertEqual(
            [(10151, 271), (10151, 272), (10151, 44888),
             (10153, 53089), (10153, 65323)],
            effects,
        )
        extend = self.runtime.execute(
            "SELECT charge_buff_id,damage_type_id,dps_inc_multiplier,level_md,"
            "use_dps_charge,use_level_charge,use_percent_charge,use_current_health "
            "FROM extend_charge_effects WHERE id=1"
        ).fetchone()
        self.assertEqual((95, 2, 1.5, 3.0, 1, 1, 0, 0), extend)
        shield = self.runtime.execute(
            "SELECT cooldown_skill_id,cooldown_skill_time,duration,"
            "damage_absorption_type_id,init_min_charge,init_max_charge "
            "FROM buffs WHERE id=95"
        ).fetchone()
        self.assertEqual((10153, 30000, 40000, 2, 1, 10000), shield)

    def test_freezing_earth_plot_is_closed(self) -> None:
        self.assertEqual(
            8,
            self.runtime.execute(
                "SELECT COUNT(*) FROM plot_events WHERE plot_id=3096"
            ).fetchone()[0],
        )
        for child, column, parent in (
            ("plot_event_conditions", "event_id", "plot_events"),
            ("plot_aoe_conditions", "event_id", "plot_events"),
            ("plot_effects", "event_id", "plot_events"),
            ("plot_next_events", "event_id", "plot_events"),
            ("plot_next_events", "next_event_id", "plot_events"),
        ):
            missing = self.runtime.execute(
                f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p "
                f"ON p.id=c.{column} WHERE c.id IN ("
                f"SELECT id FROM {child} WHERE {column} IN "
                "(SELECT id FROM plot_events WHERE plot_id=3096)) AND p.id IS NULL"
            ).fetchone()[0]
            self.assertEqual(0, missing, f"{child}.{column}")

    def test_resource_data_and_protocol_are_native(self) -> None:
        resource = self.runtime.execute(
            "SELECT id,max,buff_id,recovery_cycle,resouece_send_type_id "
            "FROM combat_resources WHERE id=8"
        ).fetchone()
        group = self.runtime.execute(
            "SELECT id,ability_id,combat_resource_1_id,icon_id "
            "FROM combat_resource_groups WHERE id=7"
        ).fetchone()
        self.assertEqual((8, 60, 27177, 1000, 1), resource)
        self.assertEqual((7, 7, 8, 12847), group)
        metadata = dict(
            self.runtime.execute(
                "SELECT key,value FROM sorcery_reconstruction_v4_metadata"
            ).fetchall()
        )
        self.assertEqual(
            "implemented_exact_aa8_layout",
            metadata["combat_resource_protocol"],
        )

    def test_magic_circle_and_native_physics_closure_is_materialized(self) -> None:
        expected = {
            "physical_explosion_effects": (190,),
            "skill_controllers": (11660, 11661),
            "interaction_effects": (7406, 7407),
            "projectiles": (1126, 1131),
            "aoe_shapes": (16482, 16501),
            "doodad_almighties": (13406, 13407, 14623, 14666),
            "doodad_func_groups": (38626, 38627, 38628, 38629, 38630, 43090, 43245),
            "doodad_phase_funcs": (49136, 49137, 49339, 49340, 49913, 55165, 55330),
            "doodad_func_clouts": (4116, 4121),
            "doodad_func_timers": (16372, 16373),
            "doodad_func_finals": (5304, 5305, 5320),
        }
        for table, ids in expected.items():
            actual = tuple(
                row[0]
                for row in self.runtime.execute(
                    f'SELECT id FROM "{table}" WHERE id IN ('
                    + ",".join("?" for _ in ids)
                    + ") ORDER BY id",
                    ids,
                )
            )
            self.assertEqual(ids, actual, table)

        self.assertEqual(
            "structural_candidate_only_with_exact_aa8_endpoints",
            self.manifest["authority"]["aa10_magic_circle_links"],
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.runtime.execute("PRAGMA integrity_check").fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    SorcerySpecializationV2Tests.runtime_path = args.runtime
    SorcerySpecializationV2Tests.manifest_path = args.manifest
    unittest.main(argv=[__file__, *remaining])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
