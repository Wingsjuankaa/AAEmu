#!/usr/bin/env python3
"""Structural regressions for the complete AA8 Archery runtime V1."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


ABILITY_ID = 6
PASSIVE_IDS = (2, 7, 35, 255, 256, 300)
ANCESTRAL_PLOTS = (2927, 2928, 2941, 2942)
VISIBLE_BASE_SKILLS = (
    10694, 10708, 11368, 11933, 12133, 12759,
    13281, 14835, 15073, 15096, 16210, 23592,
)
ANCESTRAL_SUCCESSORS = (
    36468, 36469, 36470, 36471, 36472, 36473,
    39663, 39666, 41219, 41221, 42849, 42851,
)
INTERNAL_SKILLS = (
    12792, 12793, 12794, 14836, 14837, 38893,
    39664, 39665, 39667, 39668, 40580,
)
CLIENT_PROJECTILE_ANIMS = (1389, 1390, 1392, 1393, 1395, 1397, 1401, 1402, 1439)
CHARGE_SKILL_CONTRACTS = (
    (11368, 2, 8000),
    (13281, 5, 22000),
    (38893, 3, 16000),
    (42851, 3, 8000),
)
CHARGE_COOLDOWN_EFFECTS = ((41872, 16000), (55123, 22000))
ARCHERY_UNIT_REQUIREMENTS = (
    (10694, "Skill", 1, 30, 27, 0, 0),
    (11933, "Skill", 1, 29, 0, 0, 0),
    (12793, "Skill", 1, 29, 0, 0, 0),
    (12794, "Skill", 1, 29, 0, 0, 0),
    (13281, "Skill", 1, 29, 0, 0, 0),
    (14835, "Skill", 1, 29, 0, 0, 0),
    (14836, "Skill", 1, 29, 0, 0, 0),
    (14837, "Skill", 1, 29, 0, 0, 0),
    (15073, "Skill", 1, 29, 0, 0, 0),
    (15096, "Skill", 1, 29, 0, 0, 0),
    (16210, "Skill", 1, 29, 0, 0, 0),
    (23592, "Skill", 1, 29, 0, 0, 0),
)
ARCHERY_PLOT_UNIT_REQUIREMENTS = (
    (14753, "PlotCondition", 1, 26, 1, 30, 0),
)
OWNER_KEYED_RELATIONS = {
    "tagged_skills": (356, "C21FD1BE7FADC54B2847A3470A1D13752160A64A01DFC44307500F163299B068"),
    "skill_modifiers": (32, "3B9470E9E4A91AEDDABEC29EEE8AF9FC0CBD6752F85849393FB883B6BA4A65D8"),
    "skill_req_skills": (7, "D0631D6D0E1D91F112B64C247EE9A888E2AB6B868D81E82F35D44BD06A56BBFC"),
    "skill_visual_groups": (3, "9D41601FB7E332C87788736411C368D604CE56EDA58A0A240D3DAA4C38F095BE"),
}
PASSIVE_UNIT_MODIFIER_CONTRACTS = (
    (486, 10, 0, 80),
    (7564, 82, 0, 90),
)
PASSIVE_SKILL_MODIFIER_CONTRACTS = (
    (889, 0, 3750, 10, 1, 10),
)
PASSIVE_NATIVE_RELATIONS = {
    "archery_passive_buffs": (
        6,
        "C63FF2EC974C68D4C449FDEB5C8AF4FFBC7A45CD9C2D4C83562A8DF847B1FB7E",
    ),
    "archery_passive_tagged_buffs": (
        21,
        "404827C91918E3191F7A09B11E1E665D2BA62CDA6AA403197F8D9D78F9233D1A",
    ),
}
ARCHERY_PLOT_CONDITION_KINDS = (5, 6, 8, 9, 11, 12, 16, 18, 20)
ARCHERY_SOURCE_UPDATE_METHODS = (1, 3, 4)
ARCHERY_TARGET_UPDATE_METHODS = (1, 2, 4, 5, 6, 7)


class ArcheryRuntimeV1Tests(unittest.TestCase):
    runtime_path: Path
    manifest_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.runtime = sqlite3.connect(
            f"file:{cls.runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()

    def test_authority_and_crosswalk_boundary(self) -> None:
        self.assertEqual("AA8_client_native", self.manifest["authority"])
        self.assertEqual(
            "mandatory_gap_reduction_only_no_aa10_runtime_rows",
            self.manifest["crosswalk"]["policy"],
        )
        self.assertEqual(0, self.manifest["crosswalk"]["not_compared_rows"])
        evidence = self.runtime.execute(
            "SELECT ability_id,aa10_runtime_rows,selected_rows "
            "FROM aa8_archery_runtime_evidence WHERE version='archery-v1'"
        ).fetchone()
        self.assertEqual((ABILITY_ID, 0, 5022), evidence)
        self.assertEqual(8, self.manifest["crosswalk"]["conflict_rows"])
        conflict_details = self.manifest["crosswalk"]["conflict_details"]
        self.assertEqual(
            {"48364", "48367", "60051", "60055", "60059", "60071", "60076", "60082"},
            {row["aa8_id"] for row in conflict_details},
        )
        self.assertTrue(all(row["table"] == "plot_next_events" for row in conflict_details))
        self.assertTrue(all(row["runtime_authority"] == "AA8_client_native" for row in conflict_details))
        self.assertTrue(all(row["aa10_promoted"] is False for row in conflict_details))

    def test_every_native_archery_root_is_enabled(self) -> None:
        rows = self.runtime.execute(
            "SELECT skill_id,status FROM native_combat_skill_status "
            "WHERE ability_id=? ORDER BY skill_id",
            (ABILITY_ID,),
        ).fetchall()
        self.assertEqual(35, len(rows))
        self.assertTrue(all(status == "enabled" for _, status in rows))
        self.assertEqual(
            35,
            self.manifest["closure"]["downstream_audit"]["enabled"],
        )

    def test_all_six_passive_roots_are_materialized(self) -> None:
        actual = tuple(
            row[0]
            for row in self.runtime.execute(
                "SELECT id FROM passive_buffs WHERE ability_id=? ORDER BY id",
                (ABILITY_ID,),
            )
        )
        self.assertEqual(PASSIVE_IDS, actual)

    def test_passive_modifier_contracts_are_exact_and_not_synthesized(self) -> None:
        passive_buff_ids = (480, 486, 888, 7564, 7565, 889)
        marks = ",".join("?" for _ in passive_buff_ids)
        unit_rows = self.runtime.execute(
            "SELECT owner_id,unit_attribute_id,unit_modifier_type_id,value "
            "FROM unit_modifiers WHERE owner_type='Buff' "
            f"AND owner_id IN ({marks}) "
            "ORDER BY owner_id,unit_attribute_id,unit_modifier_type_id,value",
            passive_buff_ids,
        ).fetchall()
        skill_rows = self.runtime.execute(
            "SELECT owner_id,skill_id,tag_id,skill_attribute_id,"
            "unit_modifier_type_id,value FROM skill_modifiers "
            "WHERE owner_type='Buff' "
            f"AND owner_id IN ({marks}) "
            "ORDER BY owner_id,skill_id,tag_id,skill_attribute_id",
            passive_buff_ids,
        ).fetchall()

        self.assertEqual(PASSIVE_UNIT_MODIFIER_CONTRACTS, tuple(unit_rows))
        self.assertEqual(PASSIVE_SKILL_MODIFIER_CONTRACTS, tuple(skill_rows))

    def test_passive_buffs_and_tags_are_exact_aa8_native_relations(self) -> None:
        queries = {
            "archery_passive_buffs":
                "SELECT * FROM buffs WHERE id IN (480,486,888,889,7564,7565) "
                "ORDER BY id",
            "archery_passive_tagged_buffs":
                "SELECT * FROM tagged_buffs WHERE buff_id IN "
                "(480,486,888,889,7564,7565) ORDER BY buff_id,tag_id,id",
        }
        for name, query in queries.items():
            cursor = self.runtime.execute(query)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            payload = "\n".join(
                json.dumps(
                    dict(zip(columns, row)), ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"),
                )
                for row in rows
            ) + "\n"
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
            expected_rows, expected_digest = PASSIVE_NATIVE_RELATIONS[name]
            self.assertEqual(expected_rows, len(rows), name)
            self.assertEqual(expected_digest, digest, name)
            self.assertEqual(
                expected_digest,
                self.manifest["verification"]["owner_keyed_relations"][name]["sha256"],
            )

    def test_live_matrix_partitions_all_thirty_five_skill_rows(self) -> None:
        partitions = (
            set(VISIBLE_BASE_SKILLS),
            set(ANCESTRAL_SUCCESSORS),
            set(INTERNAL_SKILLS),
        )
        self.assertTrue(partitions[0].isdisjoint(partitions[1]))
        self.assertTrue(partitions[0].isdisjoint(partitions[2]))
        self.assertTrue(partitions[1].isdisjoint(partitions[2]))
        expected = set().union(*partitions)
        actual = {
            row[0]
            for row in self.runtime.execute(
                "SELECT id FROM skills WHERE ability_id=?", (ABILITY_ID,)
            )
        }
        self.assertEqual(expected, actual)
        self.assertEqual(12, len(VISIBLE_BASE_SKILLS))
        self.assertEqual(12, len(ANCESTRAL_SUCCESSORS))
        self.assertEqual(11, len(INTERNAL_SKILLS))

    def test_ancestral_plot_roots_are_materialized(self) -> None:
        actual = tuple(
            row[0]
            for row in self.runtime.execute(
                "SELECT id FROM plots WHERE id IN (2927,2928,2941,2942) ORDER BY id"
            )
        )
        self.assertEqual(ANCESTRAL_PLOTS, actual)
        for plot_id in ANCESTRAL_PLOTS:
            self.assertGreater(
                self.runtime.execute(
                    "SELECT COUNT(*) FROM plot_events WHERE plot_id=?", (plot_id,)
                ).fetchone()[0],
                0,
            )

    def test_concussive_arrow_mist_closes_damage_and_bubble_channels(self) -> None:
        skill = self.runtime.execute(
            "SELECT plot_id FROM skills WHERE id=36471"
        ).fetchone()
        self.assertEqual((2941,), skill)
        actual_types = {
            row[0]
            for row in self.runtime.execute(
                "SELECT DISTINCT pe.actual_type FROM plot_effects pe "
                "JOIN plot_events ev ON ev.id=pe.event_id WHERE ev.plot_id=2941"
            )
        }
        self.assertIn("DamageEffect", actual_types)
        self.assertIn("BubbleEffect", actual_types)
        bubble = self.runtime.execute(
            "SELECT kind_id FROM bubble_effects WHERE id=7542"
        ).fetchone()
        self.assertEqual((3,), bubble)

    def test_projectile_animation_ids_are_client_presentation_only(self) -> None:
        rows = self.runtime.execute(
            "SELECT DISTINCT se.value1,pne.add_anim_cs_time "
            "FROM special_effects se "
            "JOIN plot_effects pe ON pe.actual_type='SpecialEffect' AND pe.actual_id=se.id "
            "JOIN plot_next_events pne ON pne.next_event_id=pe.event_id "
            "WHERE se.special_effect_type_id=38 AND se.value1 IN "
            "(1389,1390,1392,1393,1395,1397,1401,1402,1439) "
            "ORDER BY se.value1"
        ).fetchall()
        self.assertEqual(CLIENT_PROJECTILE_ANIMS, tuple(row[0] for row in rows))
        self.assertTrue(all(row[1] == 0 for row in rows))

    def test_native_charge_contract_is_preserved(self) -> None:
        skills = self.runtime.execute(
            "SELECT id,charge_count,charge_cooldown_time FROM skills "
            "WHERE id IN (11368,13281,38893,42851) ORDER BY id"
        ).fetchall()
        self.assertEqual(CHARGE_SKILL_CONTRACTS, tuple(skills))

        effects = self.runtime.execute(
            "SELECT id,value1 FROM special_effects "
            "WHERE special_effect_type_id=158 AND id IN (41872,55123) ORDER BY id"
        ).fetchall()
        self.assertEqual(CHARGE_COOLDOWN_EFFECTS, tuple(effects))
        self.assertEqual(
            [list(row) for row in CHARGE_SKILL_CONTRACTS],
            self.manifest["verification"]["charge_skill_contracts"],
        )
        self.assertEqual(
            [list(row) for row in CHARGE_COOLDOWN_EFFECTS],
            self.manifest["verification"]["charge_cooldown_effects"],
        )

    def test_archery_unit_requirements_are_exact(self) -> None:
        rows = self.runtime.execute(
            "SELECT owner_id,owner_type,display_msg,kind_id,value1,value2,value3 "
            "FROM unit_reqs WHERE owner_type='Skill' AND owner_id IN "
            "(10694,11933,12793,12794,13281,14835,14836,14837,15073,15096,16210,23592) "
            "ORDER BY owner_id,kind_id,value1,value2,value3"
        ).fetchall()
        self.assertEqual(ARCHERY_UNIT_REQUIREMENTS, tuple(rows))
        self.assertEqual(
            [list(row) for row in ARCHERY_UNIT_REQUIREMENTS],
            self.manifest["verification"]["unit_requirements"],
        )

        plot_rows = self.runtime.execute(
            "SELECT owner_id,owner_type,display_msg,kind_id,value1,value2,value3 "
            "FROM unit_reqs WHERE owner_type='PlotCondition' AND owner_id=14753 "
            "ORDER BY owner_id,kind_id,value1,value2,value3"
        ).fetchall()
        self.assertEqual(ARCHERY_PLOT_UNIT_REQUIREMENTS, tuple(plot_rows))
        self.assertEqual(
            [list(row) for row in ARCHERY_PLOT_UNIT_REQUIREMENTS],
            self.manifest["verification"]["plot_unit_requirements"],
        )
        self.assertEqual(
            [14753],
            self.manifest["native_unit_requirements"]["selected_owner_ids"],
        )

    def test_owner_keyed_relations_are_not_lost_by_id_closure(self) -> None:
        skill_ids = tuple(
            row[0]
            for row in self.runtime.execute(
                "SELECT id FROM skills WHERE ability_id=? ORDER BY id", (ABILITY_ID,)
            )
        )
        placeholders = ",".join("?" for _ in skill_ids)
        queries = {
            "tagged_skills":
                f"SELECT * FROM tagged_skills WHERE skill_id IN ({placeholders}) "
                "ORDER BY skill_id,tag_id,id",
            "skill_modifiers":
                f"SELECT * FROM skill_modifiers WHERE skill_id IN ({placeholders}) "
                "ORDER BY skill_id,owner_type,owner_id,skill_attribute_id,unit_modifier_type_id,value",
            "skill_req_skills":
                f"SELECT * FROM skill_req_skills WHERE skill_id IN ({placeholders}) "
                "ORDER BY skill_id,skill_req_id",
            "skill_visual_groups":
                f"SELECT * FROM skill_visual_groups WHERE owner_type='Skill' "
                f"AND owner_id IN ({placeholders}) "
                "ORDER BY owner_id,level,fx_group_id,projectile_id",
        }
        for name, query in queries.items():
            columns = [description[0] for description in self.runtime.execute(query, skill_ids).description]
            rows = self.runtime.execute(query, skill_ids).fetchall()
            payload = "\n".join(
                json.dumps(dict(zip(columns, row)), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                for row in rows
            ) + "\n"
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
            expected_rows, expected_digest = OWNER_KEYED_RELATIONS[name]
            self.assertEqual(expected_rows, len(rows), name)
            self.assertEqual(expected_digest, digest, name)
            self.assertEqual(
                expected_digest,
                self.manifest["verification"]["owner_keyed_relations"][name]["sha256"],
            )

    def test_selected_buff_tags_are_unique_natural_relations(self) -> None:
        owner_ids = tuple(self.manifest["closure"]["tagged_buff_owner_ids"])
        self.assertGreater(len(owner_ids), 0)
        placeholders = ",".join("?" for _ in owner_ids)
        duplicates = self.runtime.execute(
            "SELECT buff_id,tag_id,COUNT(*) FROM tagged_buffs "
            f"WHERE buff_id IN ({placeholders}) "
            "GROUP BY buff_id,tag_id HAVING COUNT(*)<>1 "
            "ORDER BY buff_id,tag_id",
            owner_ids,
        ).fetchall()
        self.assertEqual([], duplicates)
        self.assertEqual(
            self.manifest["closure"]["tagged_buff_rows"],
            self.runtime.execute(
                f"SELECT COUNT(*) FROM tagged_buffs WHERE buff_id IN ({placeholders})",
                owner_ids,
            ).fetchone()[0],
        )

    def test_plot_relations_have_no_orphans(self) -> None:
        for child, column, parent in (
            ("plot_events", "plot_id", "plots"),
            ("plot_event_conditions", "event_id", "plot_events"),
            ("plot_event_conditions", "condition_id", "plot_conditions"),
            ("plot_aoe_conditions", "event_id", "plot_events"),
            ("plot_aoe_conditions", "condition_id", "plot_conditions"),
            ("plot_effects", "event_id", "plot_events"),
            ("plot_next_events", "event_id", "plot_events"),
            ("plot_next_events", "next_event_id", "plot_events"),
        ):
            count = self.runtime.execute(
                f"SELECT COUNT(*) FROM {child} child "
                f"LEFT JOIN {parent} parent ON parent.id=child.{column} "
                "WHERE parent.id IS NULL"
            ).fetchone()[0]
            self.assertEqual(0, count, f"{child}.{column}")

    def test_archery_plot_execution_domains_are_closed(self) -> None:
        plot_scope = (
            "SELECT DISTINCT plot_id FROM skills "
            "WHERE ability_id=? AND plot_id<>0"
        )
        condition_kinds = tuple(
            row[0]
            for row in self.runtime.execute(
                "SELECT DISTINCT condition.kind_id "
                "FROM plot_conditions condition "
                "JOIN plot_event_conditions link "
                "ON link.condition_id=condition.id "
                "JOIN plot_events event ON event.id=link.event_id "
                f"WHERE event.plot_id IN ({plot_scope}) "
                "ORDER BY condition.kind_id",
                (ABILITY_ID,),
            )
        )
        source_methods = tuple(
            row[0]
            for row in self.runtime.execute(
                "SELECT DISTINCT source_update_method_id FROM plot_events "
                f"WHERE plot_id IN ({plot_scope}) ORDER BY source_update_method_id",
                (ABILITY_ID,),
            )
        )
        target_methods = tuple(
            row[0]
            for row in self.runtime.execute(
                "SELECT DISTINCT target_update_method_id FROM plot_events "
                f"WHERE plot_id IN ({plot_scope}) ORDER BY target_update_method_id",
                (ABILITY_ID,),
            )
        )

        self.assertEqual(ARCHERY_PLOT_CONDITION_KINDS, condition_kinds)
        self.assertEqual(ARCHERY_SOURCE_UPDATE_METHODS, source_methods)
        self.assertEqual(ARCHERY_TARGET_UPDATE_METHODS, target_methods)

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.runtime.execute("PRAGMA integrity_check").fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    ArcheryRuntimeV1Tests.runtime_path = args.runtime
    ArcheryRuntimeV1Tests.manifest_path = args.manifest
    unittest.main(argv=[__file__, *remaining])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
