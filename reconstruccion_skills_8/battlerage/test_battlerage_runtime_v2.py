#!/usr/bin/env python3
"""Independent structural regressions for the AA8 Battlerage V5 runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


COMPACT_SHA256 = "BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58"
CLOSURE_SHA256 = "9B29046271D67802F9D3986AFFFB54640DC1292544FFB34B0A2AD7AEB44D10A8"
PLAYABLE_ROOT_IDS = (
    10377, 10455, 10644, 11918, 12026, 12028, 12034, 12786, 12787,
    12788, 13282, 13315, 16185, 18131, 18132, 18134, 18308, 18757,
    23587, 32040, 32049, 36401, 36402, 36403, 36404, 36405, 36406,
    36446, 36447, 36448, 36449, 39661, 39662, 41217, 41218, 43188,
    43189,
)
AUTOMATIC_SKILL_IDS = (34119, 34120, 34124)
OBSOLETE_INTERNAL_SKILL_IDS = (10385, 11854)
ALL_SKILL_IDS = tuple(sorted(
    PLAYABLE_ROOT_IDS + AUTOMATIC_SKILL_IDS + OBSOLETE_INTERNAL_SKILL_IDS
))
PASSIVES = ((29, 811), (32, 2610), (92, 2621), (244, 7544),
            (245, 7542), (295, 831))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


class BattlerageRuntimeV5Tests(unittest.TestCase):
    compact_path: Path
    closure_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.closure = json.loads(cls.closure_path.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(
            f"file:{cls.compact_path.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_pinned_artifact_hashes(self) -> None:
        self.assertEqual(COMPACT_SHA256, sha256(self.compact_path))
        self.assertEqual(CLOSURE_SHA256, sha256(self.closure_path))

    def test_complete_skill_identity_partition(self) -> None:
        rows = self.connection.execute(
            "SELECT id,show,skill_points,auto_learn FROM skills "
            "WHERE ability_id=1 ORDER BY id"
        ).fetchall()
        self.assertEqual(ALL_SKILL_IDS, tuple(int(row[0]) for row in rows))
        self.assertEqual(
            12,
            sum(int(row[1]) == 1 and int(row[2]) > 0 for row in rows),
        )
        automatic = [row for row in rows if int(row[0]) in AUTOMATIC_SKILL_IDS]
        self.assertEqual(3, len(automatic))
        self.assertTrue(all(int(row[1]) == 1 and int(row[2]) == 0 for row in automatic))
        hidden = [row for row in rows if int(row[0]) in OBSOLETE_INTERNAL_SKILL_IDS]
        self.assertEqual(2, len(hidden))
        self.assertTrue(all(int(row[1]) == 0 for row in hidden))

    def test_passive_identity_contract(self) -> None:
        actual = tuple(self.connection.execute(
            "SELECT id,buff_id FROM passive_buffs WHERE ability_id=1 ORDER BY id"
        ))
        self.assertEqual(PASSIVES, actual)

    def test_behind_enemy_lines_reduces_charge_per_distinct_target(self) -> None:
        actual = self.connection.execute(
            "SELECT source_skill_id,target_skill_id,target_skill_tag_id,"
            "flat_milliseconds,percent,per_distinct_target "
            "FROM skill_hit_cooldown_reductions WHERE id=39661001"
        ).fetchone()
        self.assertEqual((39661, 11918, 0, 2000, 0, 1), actual)

    def test_native_closure_counts_and_dependencies(self) -> None:
        tables = self.closure["tables"]
        self.assertEqual(42, len(tables["skills"]))
        self.assertEqual(6, len(tables["passive_buffs"]))
        self.assertEqual(115, len(tables["skill_effects"]))
        self.assertEqual(18, len(tables["plots"]))
        self.assertEqual(64, len(tables["buffs"]))
        diagnostics = self.closure["diagnostics"]
        for name in (
            "unresolved_effect_dependencies", "unresolved_plot_types",
            "animation_ids_missing", "projectile_ids_missing",
            "aoe_shape_ids_missing",
        ):
            self.assertEqual([], diagnostics[name], name)
        # Controller 604 belongs only to obsolete hidden skill 11854.
        self.assertEqual([604], diagnostics["controller_ids_missing"])

    def test_all_playable_roots_are_enabled_and_executable(self) -> None:
        status = tuple(self.connection.execute(
            "SELECT skill_id,status FROM native_combat_skill_status "
            "WHERE ability_id=1 ORDER BY skill_id"
        ))
        self.assertEqual(
            tuple((skill_id, "enabled") for skill_id in PLAYABLE_ROOT_IDS), status
        )
        for skill_id in PLAYABLE_ROOT_IDS:
            effect_count, plot_id = self.connection.execute(
                "SELECT (SELECT COUNT(*) FROM skill_effects WHERE skill_id=s.id),"
                "s.plot_id FROM skills s WHERE s.id=?", (skill_id,)
            ).fetchone()
            self.assertTrue(effect_count > 0 or int(plot_id or 0) > 0, skill_id)

    def test_exact_skill_relationship_partitions(self) -> None:
        placeholders = ",".join("?" for _ in ALL_SKILL_IDS)
        tagged_skills = self.connection.execute(
            f"SELECT COUNT(*) FROM tagged_skills WHERE skill_id IN ({placeholders})",
            ALL_SKILL_IDS,
        ).fetchone()[0]
        self.assertEqual(299, tagged_skills)
        duplicate_tags = self.connection.execute(
            f"SELECT COUNT(*) FROM (SELECT skill_id,tag_id,COUNT(*) n "
            f"FROM tagged_skills WHERE skill_id IN ({placeholders}) "
            "GROUP BY skill_id,tag_id HAVING n>1)", ALL_SKILL_IDS,
        ).fetchone()[0]
        self.assertEqual(0, duplicate_tags)
        self.assertEqual(287, len(self.closure["tables"]["tagged_buffs"]))

    def test_exact_native_skill_modifiers(self) -> None:
        self.assertEqual(
            1571,
            self.connection.execute("SELECT COUNT(*) FROM skill_modifiers").fetchone()[0],
        )
        self.assertEqual(
            0,
            self.connection.execute(
                "SELECT COUNT(*) FROM skill_modifiers "
                "WHERE owner_type='Buff' AND owner_id=811"
            ).fetchone()[0],
        )
        self.assertEqual(
            1,
            self.connection.execute(
                "SELECT COUNT(*) FROM skill_modifiers "
                "WHERE owner_type='Buff' AND owner_id=831"
            ).fetchone()[0],
        )

    def test_runtime_contains_no_promoted_aa10_rows(self) -> None:
        row = self.connection.execute(
            "SELECT graph_sha256,crosswalk_sha256,native_closure_sha256,"
            "aa10_runtime_rows FROM aa8_battlerage_runtime_evidence "
            "WHERE version='battlerage-v5'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual("54736AFC8CDC453C84FFA4C8337C76894FA86D78155E714B1B121B5B640589B5", row[0])
        self.assertEqual("44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71", row[1])
        self.assertEqual(CLOSURE_SHA256, row[2])
        self.assertEqual(0, int(row[3]))

    def test_hammer_toss_uses_native_plot_presentation_only(self) -> None:
        columns = {
            str(row[1]) for row in self.connection.execute("PRAGMA table_info(skills)")
        }
        self.assertNotIn("server_plot_only_fire_presentation", columns)
        self.assertEqual(
            (1, 440, 308),
            self.connection.execute(
                "SELECT plot_only,plot_id,projectile_id FROM skills WHERE id=18757"
            ).fetchone(),
        )

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--compact", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    BattlerageRuntimeV5Tests.closure_path = args.closure.resolve()
    BattlerageRuntimeV5Tests.compact_path = args.compact.resolve()
    unittest.main(argv=[__file__, *remaining])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
