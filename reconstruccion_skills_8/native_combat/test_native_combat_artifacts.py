#!/usr/bin/env python3
"""Structural regressions for the AA 8.0 native combat artefacts."""

from __future__ import annotations

import argparse
import json
import sqlite3
import unittest
from pathlib import Path


class NativeCombatArtifactTests(unittest.TestCase):
    catalog_path: Path
    runtime_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(cls.catalog_path.read_text(encoding="utf-8"))
        cls.runtime = sqlite3.connect(
            f"file:{cls.runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()

    def test_scope_contains_all_fourteen_player_abilities(self) -> None:
        self.assertEqual(list(range(1, 15)), [row["id"] for row in self.catalog["abilities"]])
        self.assertEqual(462, len(self.catalog["tables"]["skills"]))

    def test_no_historical_combat_provenance(self) -> None:
        serialized = json.dumps(self.catalog["provenance"], sort_keys=True)
        self.assertNotIn("historical_3_0", serialized)
        self.assertFalse(self.catalog["reference_resolution"]["historical_reference_used"])

    def test_native_string_cache_resolution(self) -> None:
        resolved = self.catalog["reference_resolution"]["effect_types"]
        self.assertEqual("DamageEffect", resolved["<ref:69865>"])
        self.assertEqual("HealEffect", resolved["<ref:69867>"])
        self.assertEqual("BuffEffect", resolved["<ref:75221>"])
        self.assertEqual("CombatResourceEffect", resolved["<ref:75256>"])

    def test_native_animation_string_cache_resolution(self) -> None:
        anim_range = self.catalog["sources"]["client_game_stream"]["native_ranges"]["anims"]
        self.assertEqual(18722, anim_range["string_cache"]["first_reference"])
        self.assertEqual("game11_native_self_references", anim_range["string_cache"]["source"])

        text_fields = (
            "hang_ub",
            "move_ub",
            "name",
            "relaxed_ub",
            "ride_ub",
            "swim_move_ub",
            "swim_ub",
        )
        for row in self.catalog["tables"]["anims"]:
            for field in text_fields:
                self.assertIsNotNone(row[field], f"anims.{row['id']}.{field}")
                self.assertFalse(str(row[field]).startswith("<ref:"))

        unresolved = self.runtime.execute(
            "SELECT COUNT(*) FROM anims WHERE name IS NULL OR name='' OR name LIKE '<ref:%'"
        ).fetchone()[0]
        self.assertEqual(0, unresolved)

    def test_x2game_confirmed_effect_ranges_are_recorded(self) -> None:
        ranges = self.catalog["sources"]["client_game_stream"]["native_ranges"]
        expected = {
            "bubble_effects": (0xDEBADB, 5811),
            "heal_effects": (0xB45F23, 916),
            "restore_mana_effects": (0xB5EFE9, 256),
            "spawn_effects": (0xD5AC76, 2447),
            "mana_burn_effects": (0xD9F951, 89),
            "kill_npc_without_corpse_effects": (0xDD0ECA, 1613),
            "reset_aoe_diminishing_effects": (0xE52AB1, 191),
            "extend_charge_effects": (0xE57331, 23),
        }
        for table, (start, rows) in expected.items():
            self.assertEqual(start, int(ranges[table]["start"]))
            self.assertEqual(rows, int(ranges[table]["rows"]))

    def test_unconfirmed_backend_semantics_stay_out_of_enabled_skills(self) -> None:
        pending = {
            row["primitive"]
            for row in self.catalog["coverage"]["effect_primitives"]
            if row["state"] != "native_implemented"
        }
        self.assertIn("BubbleEffect", pending)
        self.assertIn("ResetAoeDiminishingEffect", pending)
        self.assertIn("ExtendChargeEffect", pending)

        effects = {
            int(row["id"]): str(row["actual_type"])
            for row in self.catalog["tables"]["effects"]
        }
        for status in self.catalog["skill_status"]:
            if status["status"] != "enabled":
                continue
            relation_ids = self.catalog["skill_table_ids"][str(status["skill_id"])].get(
                "skill_effects", []
            )
            relations = {
                int(row["id"]): row
                for row in self.catalog["tables"]["skill_effects"]
                if int(row["id"]) in relation_ids
            }
            reached = {effects[int(row["effect_id"])] for row in relations.values()}
            plot_relation_ids = self.catalog["skill_table_ids"][str(status["skill_id"])].get(
                "plot_effects", []
            )
            reached.update(
                str(row["actual_type"])
                for row in self.catalog["tables"]["plot_effects"]
                if int(row["id"]) in plot_relation_ids
            )
            self.assertTrue(reached.isdisjoint(pending))

    def test_quarantine_is_scoped_to_each_skill(self) -> None:
        statuses_by_ability: dict[int, set[str]] = {}
        for row in self.catalog["skill_status"]:
            statuses_by_ability.setdefault(int(row["ability_id"]), set()).add(
                str(row["status"])
            )

        for ability in self.catalog["abilities"]:
            statuses = statuses_by_ability[int(ability["id"])]
            if ability["status"] == "partial":
                self.assertEqual({"enabled", "quarantined"}, statuses)
            elif ability["status"] == "enabled":
                self.assertEqual({"enabled"}, statuses)

        self.assertTrue(
            all("enabled" in statuses for statuses in statuses_by_ability.values())
        )

    def test_enabled_skill_does_not_chain_into_quarantine(self) -> None:
        status_by_skill = {
            int(row["skill_id"]): str(row["status"])
            for row in self.catalog["skill_status"]
        }
        for row in self.catalog["skill_status"]:
            if row["status"] != "enabled":
                continue
            chained_statuses = {
                status_by_skill[int(skill_id)]
                for skill_id in row["closure_skill_ids"]
            }
            self.assertEqual({"enabled"}, chained_statuses)

    def test_runtime_integrity(self) -> None:
        self.assertEqual("ok", self.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.runtime.execute("PRAGMA integrity_check").fetchone()[0])

    def test_runtime_plot_relations_have_no_orphans(self) -> None:
        checks = (
            ("plot_events", "plot_id", "plots"),
            ("plot_event_conditions", "event_id", "plot_events"),
            ("plot_event_conditions", "condition_id", "plot_conditions"),
            ("plot_aoe_conditions", "event_id", "plot_events"),
            ("plot_aoe_conditions", "condition_id", "plot_conditions"),
            ("plot_effects", "event_id", "plot_events"),
            ("plot_next_events", "event_id", "plot_events"),
            ("plot_next_events", "next_event_id", "plot_events"),
        )
        for child_table, child_column, parent_table in checks:
            count = self.runtime.execute(
                f"SELECT COUNT(*) FROM {child_table} child "
                f"LEFT JOIN {parent_table} parent ON parent.id=child.{child_column} "
                "WHERE parent.id IS NULL"
            ).fetchone()[0]
            self.assertEqual(0, count, f"{child_table}.{child_column}")

    def test_quarantined_skills_have_no_executable_relations(self) -> None:
        leaked = self.runtime.execute(
            """
            SELECT COUNT(*)
            FROM skill_effects se
            JOIN native_combat_skill_status ns ON ns.skill_id=se.skill_id
            WHERE ns.status='quarantined'
            """
        ).fetchone()[0]
        self.assertEqual(0, leaked)

    def test_triple_slash_native_aoe_graph(self) -> None:
        event = self.runtime.execute(
            """
            SELECT target_update_method_param1, target_update_method_param2,
                   target_update_method_param8, target_update_method_param9
            FROM plot_events WHERE id=20729
            """
        ).fetchone()
        self.assertEqual((10110, 20, 4, 111), event)
        self.assertEqual(
            19,
            self.runtime.execute(
                "SELECT COUNT(*) FROM plot_events WHERE plot_id=2541"
            ).fetchone()[0],
        )
        next_event = self.runtime.execute(
            "SELECT next_event_id, per_target FROM plot_next_events WHERE id=23962"
        ).fetchone()
        self.assertEqual((23026, 1), next_event)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    NativeCombatArtifactTests.catalog_path = args.catalog
    NativeCombatArtifactTests.runtime_path = args.runtime
    unittest.main(argv=[__file__, *remaining])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
