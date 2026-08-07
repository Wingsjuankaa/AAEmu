#!/usr/bin/env python3
"""Regression tests for the readiness-gated Nuia story V2 compiler."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = DOMAIN / "generated" / "native-nuia-story-v2-runtime-manifest.json"
BUILDER = DOMAIN / "build_native_nuia_story_v2_runtime.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("native_nuia_story_v2_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {BUILDER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class NativeNuiaStoryV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_builder()
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.runtime = sqlite3.connect(
            f"file:{Path(cls.manifest['output']['path']).resolve().as_posix()}?mode=ro",
            uri=True,
        )
        cls.runtime.row_factory = sqlite3.Row
        cls.base = sqlite3.connect(
            f"file:{Path(cls.manifest['sources']['base']['path']).resolve().as_posix()}?mode=ro",
            uri=True,
        )
        cls.base.row_factory = sqlite3.Row
        cls.graph = sqlite3.connect(
            f"file:{Path(cls.manifest['sources']['graph']['path']).resolve().as_posix()}?mode=ro",
            uri=True,
        )
        cls.graph.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()
        cls.base.close()
        cls.graph.close()

    def test_forensic_inventory_is_complete_and_explicit(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(294, scope["quests"])
        self.assertEqual(1294, scope["components"])
        self.assertEqual(1354, scope["acts"])
        self.assertEqual(27, scope["act_types"])
        self.assertEqual(559, scope["endpoints"])
        self.assertEqual(428, scope["items"])
        self.assertEqual(
            294,
            self.runtime.execute(
                "SELECT COUNT(*) FROM aaemu_nuia_story_v2_quest_readiness"
            ).fetchone()[0],
        )
        self.assertEqual(
            294,
            self.runtime.execute(
                "SELECT SUM(CASE WHEN state IN "
                "('ready','blocked','pending_validation') THEN 1 ELSE 0 END) "
                "FROM aaemu_nuia_story_v2_quest_readiness"
            ).fetchone()[0],
        )

    def test_every_native_act_type_has_an_explicit_runtime_table(self) -> None:
        graph_types = {
            str(row[0])
            for row in self.graph.execute(
                "SELECT DISTINCT act_detail_type FROM story_quest_acts"
            )
        }
        self.assertEqual(graph_types, set(self.builder.DETAIL_TABLES))
        for detail_type, table in self.builder.DETAIL_TABLES.items():
            with self.subTest(detail_type=detail_type):
                self.assertIsNotNone(
                    self.runtime.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (table,),
                    ).fetchone()
                )

    def test_effect_fire_preserves_native_team_share_schema(self) -> None:
        columns = {
            str(row[1])
            for row in self.runtime.execute(
                "PRAGMA table_info(quest_act_obj_effect_fires)"
            )
        }
        self.assertIn("team_share", columns)
        materialization = self.runtime.execute(
            "SELECT authority,state,source_sha256 FROM "
            "aaemu_nuia_story_v2_materializations WHERE materialization_key=?",
            ("schema:quest_act_obj_effect_fires:team_share",),
        ).fetchone()
        self.assertEqual(
            (
                "AA8_client_native",
                "active",
                self.manifest["sources"]["graph"]["sha256"],
            ),
            tuple(materialization),
        )

    def test_every_objective_effect_has_its_exact_native_detail(self) -> None:
        stage50 = sqlite3.connect(
            f"file:{Path(self.manifest['sources']['stage50']['path']).resolve().as_posix()}?mode=ro",
            uri=True,
        )
        stage50.row_factory = sqlite3.Row
        try:
            effect_ids = sorted(
                {
                    int(json.loads(str(row[0]))["effect_id"])
                    for row in self.graph.execute(
                        "SELECT detail_row_json FROM story_quest_acts "
                        "WHERE act_detail_type='QuestActObjEffectFire'"
                    )
                }
            )
            self.assertTrue(effect_ids)
            for effect_id in effect_ids:
                with self.subTest(effect_id=effect_id):
                    native = stage50.execute(
                        "SELECT state,row_json FROM native_rows WHERE entity_key=?",
                        (f"effect:{effect_id}",),
                    ).fetchone()
                    self.assertEqual("confirmed", str(native["state"]))
                    native_effect = json.loads(str(native["row_json"]))
                    runtime_effect = self.runtime.execute(
                        "SELECT actual_type,actual_id FROM effects WHERE id=?",
                        (effect_id,),
                    ).fetchone()
                    self.assertEqual(
                        (
                            str(native_effect["actual_type"]),
                            int(native_effect["actual_id"]),
                        ),
                        (str(runtime_effect[0]), int(runtime_effect[1])),
                    )
                    detail_table = self.builder.actual_effect_table(
                        str(native_effect["actual_type"])
                    )
                    native_detail = stage50.execute(
                        "SELECT state,row_json FROM native_rows WHERE entity_key=?",
                        (
                            f"effect_detail:{detail_table}:"
                            f"{int(native_effect['actual_id'])}",
                        ),
                    ).fetchone()
                    self.assertEqual("confirmed", str(native_detail["state"]))
                    expected_detail = json.loads(str(native_detail["row_json"]))
                    runtime_detail = self.runtime.execute(
                        f'SELECT * FROM "{detail_table}" WHERE id=?',
                        (int(native_effect["actual_id"]),),
                    ).fetchone()
                    self.assertIsNotNone(runtime_detail)
                    for key, value in expected_detail.items():
                        self.assertEqual(value, runtime_detail[key])
            self.assertEqual(
                0,
                self.runtime.execute(
                    "SELECT COUNT(*) FROM aaemu_nuia_story_v2_blockers "
                    "WHERE blocker_kind IN "
                    "('missing_objective_effect','missing_objective_effect_detail')"
                ).fetchone()[0],
            )
        finally:
            stage50.close()

    def test_check_complete_component_targets_stay_inside_their_native_quest(self) -> None:
        rows = self.graph.execute(
            "SELECT quest_id,detail_row_json FROM story_quest_acts "
            "WHERE act_detail_type='QuestActCheckCompleteComponent'"
        ).fetchall()
        self.assertTrue(rows)
        for row in rows:
            target = int(json.loads(str(row["detail_row_json"]))["complete_component"])
            owner = self.graph.execute(
                "SELECT quest_id FROM story_quest_components WHERE component_id=?",
                (target,),
            ).fetchone()
            self.assertIsNotNone(owner)
            self.assertEqual(int(row["quest_id"]), int(owner[0]))
        self.assertEqual(
            0,
            self.runtime.execute(
                "SELECT COUNT(*) FROM aaemu_nuia_story_v2_blockers "
                "WHERE blocker_kind IN "
                "('missing_complete_component_target','external_complete_component_target')"
            ).fetchone()[0],
        )

    def test_story_cinemas_match_stage40_native_rows(self) -> None:
        stage40 = sqlite3.connect(
            f"file:{Path(self.manifest['sources']['stage40']['path']).resolve().as_posix()}?mode=ro",
            uri=True,
        )
        stage40.row_factory = sqlite3.Row
        try:
            for cinema_id in sorted(self.builder.story_cinema_ids(
                self.builder.load_graph(Path(self.manifest["sources"]["graph"]["path"])),
                31,
            )):
                native = stage40.execute(
                    "SELECT state,row_json FROM native_rows WHERE entity_key=?",
                    (f"cinema:{cinema_id}",),
                ).fetchone()
                self.assertEqual("confirmed", str(native["state"]))
                expected = json.loads(str(native["row_json"]))
                actual = self.runtime.execute(
                    "SELECT id,name,replay FROM cinemas WHERE id=?", (cinema_id,)
                ).fetchone()
                self.assertEqual(
                    (int(expected["id"]), str(expected["name"]), int(expected["replay"])),
                    (int(actual[0]), str(actual[1]), int(actual[2])),
                )
        finally:
            stage40.close()

    def test_v1_prefix_remains_byte_for_byte_equal_in_executable_tables(self) -> None:
        quest_ids = [
            int(row[0])
            for row in self.graph.execute(
                "SELECT quest_id FROM story_quests WHERE chapter_idx<=6 ORDER BY quest_id"
            )
        ]
        self.assertEqual(55, len(quest_ids))
        marks = ",".join("?" for _ in quest_ids)
        component_ids = [
            int(row[0])
            for row in self.graph.execute(
                f"SELECT component_id FROM story_quest_components "
                f"WHERE quest_id IN ({marks}) ORDER BY component_id",
                quest_ids,
            )
        ]
        component_marks = ",".join("?" for _ in component_ids)
        for table, query, params in (
            (
                "quest_contexts",
                f"SELECT * FROM quest_contexts WHERE id IN ({marks}) ORDER BY id",
                quest_ids,
            ),
            (
                "quest_components",
                f"SELECT * FROM quest_components WHERE id IN ({component_marks}) ORDER BY id",
                component_ids,
            ),
            (
                "quest_acts",
                f"SELECT * FROM quest_acts WHERE quest_component_id IN "
                f"({component_marks}) ORDER BY id",
                component_ids,
            ),
        ):
            with self.subTest(table=table):
                expected = [tuple(row) for row in self.base.execute(query, params)]
                actual = [tuple(row) for row in self.runtime.execute(query, params)]
                self.assertEqual(expected, actual)

    def test_only_the_contiguous_ready_prefix_is_enabled(self) -> None:
        enabled = [
            int(row[0])
            for row in self.runtime.execute(
                "SELECT quest_id FROM aaemu_nuia_story_v2_quest_readiness "
                "WHERE enabled=1 ORDER BY chapter_idx,quest_idx,quest_id"
            )
        ]
        self.assertEqual(86, len(enabled))
        block_a = [
            7115, 7119, 7123, 7125, 7127, 7128, 7129,
            7130, 7131, 7132, 7133, 7134, 7135, 7136,
            7137, 7138, 7139, 7140, 7141, 7142, 7143,
            7144, 7145, 7146, 7147, 7148, 7149, 7466,
        ]
        block_b_prefix = [6577, 6580, 6584]
        self.assertEqual(block_a + block_b_prefix, enabled[-31:])
        self.assertEqual(
            sorted(block_a + block_b_prefix),
            self.manifest["scope"]["post_v1_enabled_quest_ids"],
        )

    def test_block_b_prefix_and_first_stop_point_are_exact(self) -> None:
        prefix = self.runtime.execute(
            "SELECT quest_id,state,enabled,blocker_count FROM "
            "aaemu_nuia_story_v2_quest_readiness WHERE chapter_idx=12 "
            "ORDER BY quest_idx,quest_id"
        ).fetchall()
        self.assertEqual(
            [
                (6577, "ready", 1, 0),
                (6580, "ready", 1, 0),
                (6584, "ready", 1, 0),
            ],
            [tuple(row) for row in prefix[:3]],
        )
        self.assertEqual((6615, "blocked", 0, 6), tuple(prefix[3]))
        blockers = {
            (str(row[0]), str(row[1]), int(row[2]))
            for row in self.runtime.execute(
                "SELECT blocker_kind,entity_kind,entity_id FROM "
                "aaemu_nuia_story_v2_blockers WHERE quest_id=6615"
            )
        }
        self.assertEqual(
            {
                ("missing_npc_spawn_relation", "npc", 18455),
                ("missing_npc_spawn_relation", "npc", 18457),
                ("missing_npc_spawn_relation", "npc", 18459),
                ("missing_npc_spawn_relation", "npc", 18461),
                ("missing_npc_spawn_relation", "npc", 18463),
                ("missing_npc_spawn_relation", "npc", 18464),
            },
            blockers,
        )

    def test_block_b_tombstone_items_keep_native_roles_and_legacy_rows(self) -> None:
        for item_id in (8318, 16353, 16354, 16355):
            with self.subTest(item_id=item_id):
                coverage = self.runtime.execute(
                    "SELECT concrete_type,coverage,missing_dependencies,provenance "
                    "FROM aaemu_item_definition_coverage WHERE item_id=?",
                    (item_id,),
                ).fetchone()
                self.assertEqual("complete", str(coverage[1]))
                self.assertEqual("", str(coverage[2]))
                self.assertIn("legacy_3_0_minimal", str(coverage[3]))
                self.assertIsNotNone(
                    self.runtime.execute(
                        "SELECT 1 FROM items WHERE id=?", (item_id,)
                    ).fetchone()
                )
                materialization = self.runtime.execute(
                    "SELECT authority,evidence_json FROM "
                    "aaemu_nuia_story_v2_materializations "
                    "WHERE materialization_key=?",
                    (f"item:{item_id}:block-b-tombstone-legacy-minimum",),
                ).fetchone()
                self.assertEqual(
                    "AA8_native_relation_legacy_minimum", str(materialization[0])
                )
                evidence = json.loads(str(materialization[1]))
                self.assertTrue(evidence["quest_roles"])
                self.assertEqual("tombstone", evidence["stage20_state"])

    def test_block_b_monster_groups_preserve_every_native_member(self) -> None:
        stage40 = sqlite3.connect(
            f"file:{Path(self.manifest['sources']['stage40']['path']).resolve().as_posix()}?mode=ro",
            uri=True,
        )
        try:
            for group_id in self.builder.BLOCK_B_MONSTER_GROUPS:
                expected = [
                    tuple(row)
                    for row in stage40.execute(
                        "SELECT CAST(json_extract(row_json,'$.id') AS INTEGER),"
                        "CAST(json_extract(row_json,'$.npc_id') AS INTEGER),"
                        "CAST(json_extract(row_json,'$.quest_monster_group_id') AS INTEGER) "
                        "FROM native_rows WHERE source_table='quest_monster_npcs' "
                        "AND CAST(json_extract(row_json,'$.quest_monster_group_id') AS INTEGER)=? "
                        "ORDER BY CAST(json_extract(row_json,'$.id') AS INTEGER)",
                        (group_id,),
                    )
                ]
                actual = [
                    tuple(row)
                    for row in self.runtime.execute(
                        "SELECT id,npc_id,quest_monster_group_id FROM quest_monster_npcs "
                        "WHERE quest_monster_group_id=? ORDER BY id",
                        (group_id,),
                    )
                ]
                self.assertEqual(expected, actual)
        finally:
            stage40.close()

    def test_every_block_a_quest_is_ready_and_unblocked(self) -> None:
        rows = self.runtime.execute(
            "SELECT quest_id,state,enabled,blocker_count,recommended_stop_point "
            "FROM aaemu_nuia_story_v2_quest_readiness "
            "WHERE chapter_idx BETWEEN 7 AND 11 "
            "ORDER BY chapter_idx,quest_idx,quest_id"
        ).fetchall()
        self.assertEqual(28, len(rows))
        self.assertTrue(
            all(tuple(row)[1:] == ("ready", 1, 0, "none") for row in rows)
        )
        ids = [int(row[0]) for row in rows]
        marks = ",".join("?" for _ in ids)
        self.assertEqual(
            0,
            self.runtime.execute(
                f"SELECT COUNT(*) FROM aaemu_nuia_story_v2_blockers "
                f"WHERE quest_id IN ({marks})",
                ids,
            ).fetchone()[0],
        )

    def test_block_a_executable_rows_match_every_native_component_and_act(self) -> None:
        story = self.builder.load_graph(
            Path(self.manifest["sources"]["graph"]["path"])
        )
        block_a_ids = {
            int(row[0])
            for row in self.graph.execute(
                "SELECT quest_id FROM story_quests "
                "WHERE chapter_idx BETWEEN 7 AND 11"
            )
        }
        self.assertEqual(28, len(block_a_ids))
        for quest in story["quests"]:
            quest_id = int(quest["quest_id"])
            if quest_id not in block_a_ids:
                continue
            actual = self.runtime.execute(
                "SELECT * FROM quest_contexts WHERE id=?", (quest_id,)
            ).fetchone()
            self.assertIsNotNone(actual, quest_id)
            for key, value in quest["native_row"].items():
                self.assertEqual(value, actual[key], f"quest {quest_id}.{key}")

        components = [
            row for row in story["components"]
            if int(row["quest_context_id"]) in block_a_ids
        ]
        component_ids = {int(row["id"]) for row in components}
        for expected in components:
            component_id = int(expected["id"])
            actual = self.runtime.execute(
                "SELECT * FROM quest_components WHERE id=?", (component_id,)
            ).fetchone()
            self.assertIsNotNone(actual, component_id)
            for key, value in expected.items():
                self.assertEqual(value, actual[key], f"component {component_id}.{key}")

        acts = [
            row for row in story["acts"]
            if int(row["quest_component_id"]) in component_ids
        ]
        for expected in acts:
            act_id = int(expected["id"])
            actual = self.runtime.execute(
                "SELECT * FROM quest_acts WHERE id=?", (act_id,)
            ).fetchone()
            self.assertEqual(
                (
                    expected["act_detail_type"],
                    int(expected["act_detail_id"]),
                    int(expected["quest_component_id"]),
                ),
                (
                    str(actual["act_detail_type"]),
                    int(actual["act_detail_id"]),
                    int(actual["quest_component_id"]),
                ),
                act_id,
            )
            detail = story["act_meta"][act_id]["detail"]
            table = self.builder.DETAIL_TABLES[str(expected["act_detail_type"])]
            runtime_detail = self.runtime.execute(
                f'SELECT * FROM "{table}" WHERE id=?',
                (int(expected["act_detail_id"]),),
            ).fetchone()
            self.assertIsNotNone(runtime_detail, act_id)
            for key, value in detail.items():
                self.assertEqual(value, runtime_detail[key], f"act {act_id}.{key}")

    def test_blocked_post_v1_story_rows_are_quarantined(self) -> None:
        blocked = [
            int(row[0])
            for row in self.runtime.execute(
                "SELECT quest_id FROM aaemu_nuia_story_v2_quest_readiness "
                "WHERE chapter_idx>=7 AND enabled=0 ORDER BY quest_id"
            )
        ]
        marks = ",".join("?" for _ in blocked)
        self.assertEqual(
            0,
            self.runtime.execute(
                f"SELECT COUNT(*) FROM quest_contexts WHERE id IN ({marks})", blocked
            ).fetchone()[0],
        )
        self.assertEqual(
            0,
            self.runtime.execute(
                f"SELECT COUNT(*) FROM quest_components WHERE quest_context_id IN ({marks})",
                blocked,
            ).fetchone()[0],
        )

    def test_first_vertical_is_ready_and_has_no_hidden_blocker(self) -> None:
        readiness = self.runtime.execute(
            "SELECT state,enabled,blocker_count,recommended_stop_point "
            "FROM aaemu_nuia_story_v2_quest_readiness WHERE quest_id=7115"
        ).fetchone()
        self.assertEqual(("ready", 1, 0, "none"), tuple(readiness))
        self.assertEqual(
            0,
            self.runtime.execute(
                "SELECT COUNT(*) FROM aaemu_nuia_story_v2_blockers WHERE quest_id=7115"
            ).fetchone()[0],
        )

    def test_first_vertical_preserves_all_native_rows(self) -> None:
        story = self.builder.load_graph(
            Path(self.manifest["sources"]["graph"]["path"])
        )
        expected_quest = next(
            row["native_row"]
            for row in story["quests"]
            if int(row["quest_id"]) == 7115
        )
        actual_quest = self.runtime.execute(
            "SELECT * FROM quest_contexts WHERE id=7115"
        ).fetchone()
        for key, value in expected_quest.items():
            self.assertEqual(value, actual_quest[key], key)

        acts = self.graph.execute(
            "SELECT quest_act_id,act_detail_type,act_detail_id,detail_row_json "
            "FROM story_quest_acts WHERE quest_id=7115 ORDER BY quest_act_id"
        ).fetchall()
        self.assertEqual(8, len(acts))
        for act in acts:
            with self.subTest(quest_act_id=int(act[0])):
                self.assertIsNotNone(
                    self.runtime.execute(
                        "SELECT 1 FROM quest_acts WHERE id=? AND act_detail_type=? "
                        "AND act_detail_id=?",
                        (int(act[0]), str(act[1]), int(act[2])),
                    ).fetchone()
                )
                expected_detail = json.loads(str(act[3]))
                table = self.builder.DETAIL_TABLES[str(act[1])]
                actual_detail = self.runtime.execute(
                    f'SELECT * FROM "{table}" WHERE id=?', (int(act[2]),)
                ).fetchone()
                for key, value in expected_detail.items():
                    self.assertEqual(value, actual_detail[key], key)

    def test_first_vertical_item_skill_and_spawn_closure_is_materialized(self) -> None:
        self.assertEqual(
            (42069, 1),
            tuple(
                self.runtime.execute(
                    "SELECT use_skill_id,use_skill_as_reagent FROM items WHERE id=47879"
                ).fetchone()
            ),
        )
        self.assertEqual(
            (59478, 42069, 78235, 1),
            tuple(
                self.runtime.execute(
                    "SELECT id,skill_id,effect_id,consume_item_count "
                    "FROM skill_effects WHERE id=59478"
                ).fetchone()
            ),
        )
        self.assertEqual(
            ("SpecialEffect", 44393),
            tuple(
                self.runtime.execute(
                    "SELECT actual_type,actual_id FROM effects WHERE id=78235"
                ).fetchone()
            ),
        )
        self.assertEqual(
            (25, 999),
            tuple(
                self.runtime.execute(
                    "SELECT special_effect_type_id,value1 FROM special_effects WHERE id=44393"
                ).fetchone()
            ),
        )
        keys = {
            str(row[0])
            for row in self.runtime.execute(
                "SELECT materialization_key FROM aaemu_nuia_story_v2_materializations"
            )
        }
        self.assertTrue(
            {
                "item:47879:runtime-closure",
                "skill:42069:effect-application:59478",
                "effect:78235:special:44393",
                "special-effect:44393:return-point:999",
                "npc:15558:effective-spawn",
                "return-point:999:worldgate-proxy",
            }.issubset(keys)
        )

    def test_block_a_simple_items_preserve_type_and_graph_roles(self) -> None:
        for item_id, concrete_type in self.builder.BLOCK_A_SIMPLE_ITEMS.items():
            with self.subTest(item_id=item_id):
                coverage = self.runtime.execute(
                    "SELECT concrete_type,coverage,missing_dependencies "
                    "FROM aaemu_item_definition_coverage WHERE item_id=?",
                    (item_id,),
                ).fetchone()
                self.assertEqual((concrete_type, "complete", ""), tuple(coverage))
                materialization = self.runtime.execute(
                    "SELECT evidence_json FROM aaemu_nuia_story_v2_materializations "
                    "WHERE materialization_key=?",
                    (f"item:{item_id}:block-a-runtime-definition",),
                ).fetchone()
                evidence = json.loads(str(materialization[0]))
                graph_roles = [
                    {
                        "quest_id": int(row[0]),
                        "role": str(row[1]),
                        "count": int(row[2]),
                        "grade_id": int(row[3]),
                        "flags": json.loads(str(row[4])),
                    }
                    for row in self.graph.execute(
                        "SELECT quest_id,item_role,count,grade_id,flags_json "
                        "FROM story_quest_items WHERE item_id=? "
                        "ORDER BY quest_id,item_role",
                        (item_id,),
                    )
                ]
                self.assertEqual(graph_roles, evidence["quest_roles"])

    def test_block_a_client_doodad_closure_is_exact(self) -> None:
        ids = sorted(self.builder.BLOCK_A_CLIENT_DOODAD_IDS)
        marks = ",".join("?" for _ in ids)
        self.assertEqual(
            10,
            self.runtime.execute(
                f"SELECT COUNT(*) FROM doodad_almighties "
                f"WHERE id IN ({marks}) AND client_doodad=1",
                ids,
            ).fetchone()[0],
        )
        group_ids = [
            int(row[0])
            for row in self.runtime.execute(
                f"SELECT id FROM doodad_func_groups "
                f"WHERE doodad_almighty_id IN ({marks}) ORDER BY id",
                ids,
            )
        ]
        self.assertEqual(23, len(group_ids))
        group_marks = ",".join("?" for _ in group_ids)
        funcs = self.runtime.execute(
            f"SELECT actual_func_type,actual_func_id,func_skill_id "
            f"FROM doodad_funcs WHERE doodad_func_group_id IN ({group_marks}) "
            f"ORDER BY id",
            group_ids,
        ).fetchall()
        self.assertEqual(20, len(funcs))
        uses = {
            (int(row[1]), int(row[2]))
            for row in funcs
            if str(row[0]) == "DoodadFuncUse"
        }
        self.assertEqual({(10951, 29817), (10952, 29806)}, uses)
        quests = {
            (int(row[0]), int(row[1]))
            for row in self.runtime.execute(
                "SELECT quest_id,quest_kind_id FROM doodad_func_quests "
                f"WHERE id IN ({','.join('?' for _ in range(18))})",
                [int(row[1]) for row in funcs if str(row[0]) == "DoodadFuncQuest"],
            )
        }
        self.assertEqual(self.builder.BLOCK_A_CLIENT_DOODAD_QUESTS, quests)

    def test_block_a_doodad_use_skills_replace_legacy_effects_exactly(self) -> None:
        expected = {
            29806: [(59483, 78240, 37891, 1)],
            29817: [(59484, 78245, 37892, 1), (59567, 78373, 0, 1)],
        }
        for skill_id, applications in expected.items():
            with self.subTest(skill_id=skill_id):
                actual = [
                    tuple(map(int, row))
                    for row in self.runtime.execute(
                        "SELECT id,effect_id,consume_item_id,consume_item_count "
                        "FROM skill_effects WHERE skill_id=? ORDER BY id",
                        (skill_id,),
                    )
                ]
                self.assertEqual(applications, actual)
        self.assertEqual(
            ("InteractionEffect", 7897),
            tuple(
                self.runtime.execute(
                    "SELECT actual_type,actual_id FROM effects WHERE id=78240"
                ).fetchone()
            ),
        )
        self.assertEqual(
            ("InteractionEffect", 7898),
            tuple(
                self.runtime.execute(
                    "SELECT actual_type,actual_id FROM effects WHERE id=78245"
                ).fetchone()
            ),
        )
        self.assertEqual(
            ("BuffEffect", 30743),
            tuple(
                self.runtime.execute(
                    "SELECT actual_type,actual_id FROM effects WHERE id=78373"
                ).fetchone()
            ),
        )
        self.assertEqual(
            (16976, 100, 1),
            tuple(
                self.runtime.execute(
                    "SELECT buff_id,chance,stack FROM buff_effects WHERE id=30743"
                ).fetchone()
            ),
        )

    def test_block_a_npc_17903_is_native_and_reachable(self) -> None:
        npc = self.runtime.execute(
            "SELECT model_id,equip_cloths_id,npc_posture_set_id,npc_nickname_id,"
            "ai_file_id,sound_pack_id FROM npcs WHERE id=17903"
        ).fetchone()
        self.assertEqual((19, 1184, 150, 12, 15, 148), tuple(npc))
        columns = {
            str(row[1]) for row in self.runtime.execute("PRAGMA table_info(npcs)")
        }
        self.assertIn("npc_ai_client_param_id", columns)
        self.assertIn("weapon_element_level", columns)
        keys = {
            str(row[0])
            for row in self.runtime.execute(
                "SELECT materialization_key FROM aaemu_nuia_story_v2_materializations "
                "WHERE entity_id=17903"
            )
        }
        self.assertTrue(
            {"npc:17903:block-a-native-template", "npc:17903:effective-spawn"}
            .issubset(keys)
        )

    def test_block_a_return_item_49628_has_exact_native_closure(self) -> None:
        self.assertEqual(
            (38883, 1),
            tuple(
                self.runtime.execute(
                    "SELECT use_skill_id,use_skill_as_reagent FROM items WHERE id=49628"
                ).fetchone()
            ),
        )
        self.assertEqual(
            [(54281, 70355)],
            [
                tuple(map(int, row))
                for row in self.runtime.execute(
                    "SELECT id,effect_id FROM skill_effects "
                    "WHERE skill_id=38883 ORDER BY id"
                )
            ],
        )
        self.assertEqual(
            ("SpecialEffect", 35110),
            tuple(
                self.runtime.execute(
                    "SELECT actual_type,actual_id FROM effects WHERE id=70355"
                ).fetchone()
            ),
        )
        self.assertEqual(
            (25, 927),
            tuple(
                self.runtime.execute(
                    "SELECT special_effect_type_id,value1 "
                    "FROM special_effects WHERE id=35110"
                ).fetchone()
            ),
        )
        self.assertEqual(
            ("complete", ""),
            tuple(
                self.runtime.execute(
                    "SELECT coverage,missing_dependencies "
                    "FROM aaemu_item_definition_coverage WHERE item_id=49628"
                ).fetchone()
            ),
        )
        self.assertIsNotNone(
            self.runtime.execute(
                "SELECT 1 FROM aaemu_nuia_story_v2_materializations "
                "WHERE materialization_key='return-point:927:worldgate-proxy'"
            ).fetchone()
        )

    def test_post_v1_return_point_proxies_are_exact_and_audited(self) -> None:
        expected = {
            708: (15144, 200, 17233.918, 27511.28, 141.0),
            863: (17828, 258, 14434.6895, 26684.73, 134.25),
            998: (17823, 149, 16482.9, 28100.27, 105.262),
        }
        worldgates = self.builder.load_worldgate_ids(Path(self.manifest["sources"]["worldgates"]["path"]))
        for return_point_id, (npc_id, zone_id, x, y, z) in expected.items():
            with self.subTest(return_point_id=return_point_id):
                self.assertIn(return_point_id, worldgates)
                row = self.runtime.execute(
                    "SELECT evidence_json FROM aaemu_nuia_story_v2_materializations "
                    "WHERE materialization_key=?",
                    (f"return-point:{return_point_id}:worldgate-proxy",),
                ).fetchone()
                self.assertIsNotNone(row)
                evidence = json.loads(str(row[0]))
                self.assertEqual(npc_id, int(evidence["report_npc_id"]))
                self.assertEqual(zone_id, int(evidence["zone_id"]))
                self.assertAlmostEqual(x, float(evidence["x"]), places=4)
                self.assertAlmostEqual(y, float(evidence["y"]), places=4)
                self.assertAlmostEqual(z, float(evidence["z"]), places=4)

    def test_safe_story_buff_closures_preserve_native_rows_and_effects(self) -> None:
        expected_buffs = set(self.builder.POST_V1_SAFE_STORY_BUFF_ROOTS) | {26690}
        for buff_id in sorted(expected_buffs):
            with self.subTest(buff_id=buff_id):
                materialization = self.runtime.execute(
                    "SELECT state,evidence_json FROM aaemu_nuia_story_v2_materializations "
                    "WHERE materialization_key=?",
                    (f"buff:{buff_id}:post-v1-native-closure",),
                ).fetchone()
                self.assertIsNotNone(materialization)
                self.assertEqual("active", str(materialization[0]))
                evidence = json.loads(str(materialization[1]))
                self.assertIn(
                    evidence["native_row_state"], {"confirmed", "blocked"}
                )
                self.assertTrue(
                    all(
                        dependency["runtime_policy"]
                        == "client_presentation_nonblocking"
                        for dependency in evidence["presentation_dependencies"]
                    )
                )

        trigger_effects = {
            tuple(row)
            for row in self.runtime.execute(
                "SELECT buff_id,effect_id FROM buff_triggers "
                "WHERE buff_id IN (26178,26241) ORDER BY buff_id,effect_id"
            )
        }
        self.assertEqual({(26178, 83097), (26241, 83259), (26241, 83260)}, trigger_effects)
        self.assertEqual(
            (27, 48957, 0),
            tuple(
                self.runtime.execute(
                    "SELECT special_effect_type_id,value1,value2 FROM special_effects "
                    "WHERE id=48510"
                ).fetchone()
            ),
        )

    def test_transition_and_terminal_evidence_is_preserved(self) -> None:
        transitions = [
            tuple(row)
            for row in self.runtime.execute(
                "SELECT src_quest_id,dst_quest_id FROM "
                "aaemu_nuia_story_v2_transition_gates ORDER BY src_quest_id"
            )
        ]
        self.assertEqual(
            [(4411, 7115), (8558, 9009), (10303, 10361), (10369, 10646)],
            transitions,
        )
        terminal = self.manifest["terminal_audits"]
        self.assertEqual(4, len(terminal))
        self.assertTrue(
            all(
                int(row["quest_id"]) == 10682
                and row["state"] == "terminal_confirmed"
                for row in terminal
            )
        )

    def test_external_prerequisite_10159_stays_lateral(self) -> None:
        lateral = self.manifest["lateral_prerequisite_10159"]
        self.assertEqual(1, len(lateral))
        self.assertEqual(10039, int(lateral[0]["src_quest_id"]))
        self.assertEqual("external_native_prerequisite", lateral[0]["resolution_state"])
        self.assertNotIn(
            10159,
            [
                int(row[0])
                for row in self.graph.execute("SELECT quest_id FROM story_quests")
            ],
        )

    def test_two_independent_builds_are_identical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aaemu-nuia-v2-") as directory:
            directory = Path(directory)
            hashes = []
            for index in range(2):
                output = directory / f"runtime-{index}.sqlite3"
                manifest = directory / f"manifest-{index}.json"
                options = type(
                    "Options",
                    (),
                    {
                        "base_runtime": Path(self.manifest["sources"]["base"]["path"]),
                        "graph": Path(self.manifest["sources"]["graph"]["path"]),
                        "stage20": Path(self.manifest["sources"]["stage20"]["path"]),
                        "stage30": Path(self.manifest["sources"]["stage30"]["path"]),
                        "stage40": Path(self.manifest["sources"]["stage40"]["path"]),
                        "stage50": Path(self.manifest["sources"]["stage50"]["path"]),
                        "legacy_compact": Path(self.manifest["sources"]["legacy_compact"]["path"]),
                        "game11": Path(self.manifest["sources"]["game11"]["path"]),
                        "npc_spawns": Path(self.manifest["sources"]["npc_spawns"]["path"]),
                        "worldgates": Path(self.manifest["sources"]["worldgates"]["path"]),
                        "through_chapter": 31,
                        "output": output,
                        "manifest": manifest,
                    },
                )()
                document = self.builder.build(options)
                hashes.append(document["output"]["sha256"])
            self.assertEqual(hashes[0], hashes[1])
            self.assertEqual(self.manifest["output"]["sha256"], hashes[0])

    def test_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual(
            "ok", self.runtime.execute("PRAGMA integrity_check").fetchone()[0]
        )


if __name__ == "__main__":
    unittest.main()
