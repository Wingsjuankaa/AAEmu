#!/usr/bin/env python3
"""Artifact regressions for the two final Sorcery ancestral closures."""

from __future__ import annotations

import argparse
import sqlite3
import unittest
from pathlib import Path


class SorceryAncestralClosureV23Tests(unittest.TestCase):
    runtime_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = sqlite3.connect(
            f"file:{cls.runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()

    def test_gods_whip_wave_reaches_six_native_damage_branches(self) -> None:
        self.assertEqual(
            (3778,),
            self.runtime.execute(
                "SELECT plot_id FROM skills WHERE id=39674"
            ).fetchone(),
        )
        self.assertEqual(
            (7, 14281, 0, 4000),
            self.runtime.execute(
                "SELECT target_update_method_id,target_update_method_param1,"
                "target_update_method_param2,target_update_method_param3 "
                "FROM plot_events WHERE id=33384 AND plot_id=3778"
            ).fetchone(),
        )
        self.assertEqual(
            (33388, 2000),
            self.runtime.execute(
                "SELECT next_event_id,delay FROM plot_next_events "
                "WHERE event_id=33384"
            ).fetchone(),
        )
        self.assertEqual(
            (5, 14282, 20, 0),
            self.runtime.execute(
                "SELECT target_update_method_id,target_update_method_param1,"
                "target_update_method_param2,target_update_method_param3 "
                "FROM plot_events WHERE id=33388 AND plot_id=3778"
            ).fetchone(),
        )
        damage_events = tuple(
            self.runtime.execute(
                "SELECT pne.next_event_id,pe.actual_id FROM plot_next_events pne "
                "JOIN plot_effects pe ON pe.event_id=pne.next_event_id "
                "WHERE pne.event_id=33388 AND pe.actual_type='DamageEffect' "
                "ORDER BY pne.position"
            ).fetchall()
        )
        self.assertEqual(
            (
                (33387, 11690),
                (36316, 12133),
                (36317, 12134),
                (36318, 12135),
                (36319, 12136),
                (36320, 12137),
            ),
            damage_events,
        )

    def test_flame_barrier_mist_closes_clout_to_periodic_damage(self) -> None:
        self.assertEqual(
            (4049,),
            self.runtime.execute(
                "SELECT plot_id FROM skills WHERE id=41478"
            ).fetchone(),
        )
        self.assertEqual(
            (76542,),
            self.runtime.execute(
                "SELECT effect_id FROM doodad_func_clout_effects "
                "WHERE doodad_func_clout_id=3792"
            ).fetchone(),
        )
        self.assertEqual(
            ("BuffEffect", 29874),
            self.runtime.execute(
                "SELECT actual_type,actual_id FROM effects WHERE id=76542"
            ).fetchone(),
        )
        self.assertEqual(
            (24585, 100, 1),
            self.runtime.execute(
                "SELECT buff_id,chance,stack FROM buff_effects WHERE id=29874"
            ).fetchone(),
        )
        self.assertEqual(
            (4000, 1000),
            self.runtime.execute(
                "SELECT duration,tick FROM buffs WHERE id=24585"
            ).fetchone(),
        )
        self.assertEqual(
            (24585, 76543),
            self.runtime.execute(
                "SELECT buff_id,effect_id FROM buff_tick_effects WHERE id=4167"
            ).fetchone(),
        )
        self.assertEqual(
            ("DamageEffect", 12209),
            self.runtime.execute(
                "SELECT actual_type,actual_id FROM effects WHERE id=76543"
            ).fetchone(),
        )
        self.assertEqual(
            (2, 6.0, 7.0, 104, 1.41),
            self.runtime.execute(
                "SELECT damage_type_id,dps_inc_multiplier,level_md,"
                "target_buff_tag_id,target_buff_bonus_mul "
                "FROM damage_effects WHERE id=12209"
            ).fetchone(),
        )

    def test_v23_native_evidence_survives_composite_runtime(self) -> None:
        evidence = dict(
            self.runtime.execute(
                "SELECT evidence_key,evidence_value "
                "FROM sorcery_flame_barrier_v23_evidence"
            ).fetchall()
        )
        self.assertEqual("exact_aa8_native_cached_results", evidence["authority"])
        self.assertEqual("clout:3792->effect:76542", evidence["native_relation"])
        self.assertEqual(
            "clout:3792->effect:76542->BuffEffect:29874->buff:24585"
            "->tick_effect:76543->DamageEffect:12209",
            evidence["damage_chain"],
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual(
            "ok", self.runtime.execute("PRAGMA integrity_check").fetchone()[0]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    SorceryAncestralClosureV23Tests.runtime_path = args.runtime
    unittest.main(argv=[__file__, *remaining])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
