#!/usr/bin/env python3
"""Execute every reconstruction_test_cases row in the Shadowplay V1 graph."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unittest
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_shadowplay_specialization_v1_runtime import (  # noqa: E402
    BLOCKED_SKILL_ID,
    canonical_json,
    columns,
    normalize,
    sha256_file,
    validate_graph,
)


PRESENTATION_TABLES = {
    "animation": "anims",
    "controller": "skill_controllers",
    "projectile": "projectiles",
    "aoe": "aoe_shapes",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("unittest_args", nargs="*")
    return parser.parse_args()


def open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def row_matches(
    runtime: sqlite3.Connection, table: str, source: dict[str, Any]
) -> tuple[bool, str]:
    if runtime.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is None:
        return False, f"runtime table {table} is missing"
    expected, _ = normalize(table, source)
    available = columns(runtime, table)
    names = [name for name in expected if name in available]
    actual = runtime.execute(
        f"SELECT {','.join(chr(34) + name.replace(chr(34), chr(34) * 2) + chr(34) for name in names)} "
        f"FROM \"{table}\" WHERE id=?",
        (int(source["id"]),),
    ).fetchone()
    if actual is None:
        return False, f"{table}.{source['id']} is missing"
    for index, name in enumerate(names):
        if actual[index] != expected[name]:
            return (
                False,
                f"{table}.{source['id']}.{name}: runtime={actual[index]!r} graph={expected[name]!r}",
            )
    return True, f"{table}.{source['id']} matches AA8"


class MatrixValidator:
    def __init__(self, graph_path: Path, catalog_path: Path, runtime_path: Path):
        self.contract = validate_graph(graph_path)
        self.graph = open_read_only(graph_path)
        self.runtime = open_read_only(runtime_path)
        self.catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.catalog_rows = {
            table: {int(row["id"]): row for row in rows}
            for table, rows in self.catalog["tables"].items()
        }
        self.catalog_status = {
            int(row["skill_id"]): row
            for row in self.catalog["skill_status"]
            if int(row["ability_id"]) == 8
        }
        self.skill_rows = {
            int(row["skill_id"]): json.loads(str(row["row_json"]))
            for row in self.graph.execute(
                "SELECT skill_id,row_json FROM specialization_skills WHERE root_member=1"
            )
        }

    def close(self) -> None:
        self.graph.close()
        self.runtime.close()

    def graph_rows(self, table: str, skill_id: int) -> list[sqlite3.Row]:
        column = "skill_id" if table == "reconstruction_test_cases" else "root_skill_id"
        return list(
            self.graph.execute(
                f"SELECT * FROM {table} WHERE {column}=? ORDER BY 1", (skill_id,)
            )
        )

    def runtime_skill(self, skill_id: int) -> sqlite3.Row:
        row = self.runtime.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
        if row is None:
            raise AssertionError(f"runtime skill {skill_id} is missing")
        return row

    def compare_skill_fields(self, skill_id: int, fields: tuple[str, ...]) -> str:
        source = self.skill_rows[skill_id]
        runtime = self.runtime_skill(skill_id)
        available = set(runtime.keys())
        checked = []
        for field in fields:
            if field not in source or field not in available:
                continue
            expected = normalize("skills", {"id": skill_id, field: source[field]})[0][field]
            actual = runtime[field]
            if actual != expected:
                raise AssertionError(
                    f"skills.{skill_id}.{field}: runtime={actual!r} graph={expected!r}"
                )
            checked.append(field)
        if not checked:
            raise AssertionError(f"No comparable fields for skill {skill_id}")
        return ",".join(checked)

    def validate_cost_cooldown(self, skill_id: int) -> str:
        fields = (
            "cost",
            "mana_cost",
            "mana_level_md",
            "consume_lp",
            "cooldown_time",
            "cooldown_tag_id",
            "second_cooldown_tag_id",
            "third_cooldown_tag_id",
            "ignore_global_cooldown",
            "default_gcd",
            "custom_gcd",
        )
        return "matched fields: " + self.compare_skill_fields(skill_id, fields)

    def validate_targeting(self, skill_id: int) -> str:
        fields = (
            "target_type_id",
            "target_selection_id",
            "target_relation_id",
            "min_range",
            "max_range",
            "valid_height",
            "target_valid_height",
            "target_area_count",
            "target_area_radius",
            "target_area_angle",
            "target_angle",
            "target_dead",
            "target_alive",
            "target_water",
            "target_only_water",
            "check_terrain",
            "check_obstacle",
        )
        return "matched fields: " + self.compare_skill_fields(skill_id, fields)

    def validate_cast_channel_toggle(self, skill_id: int) -> str:
        fields = (
            "casting_time",
            "casting_inc",
            "casting_useable",
            "casting_cancelable",
            "casting_delayable",
            "channeling_time",
            "channeling_tick",
            "channeling_cancelable",
            "channeling_buff_id",
            "channeling_target_buff_id",
            "toggle_buff_id",
            "effect_delay",
            "effect_repeat_count",
            "effect_repeat_tick",
        )
        return "matched fields: " + self.compare_skill_fields(skill_id, fields)

    def validate_effects(self, skill_id: int) -> str:
        steps = self.graph_rows("skill_effect_steps", skill_id)
        closure_ids = {
            int(value) for value in self.catalog_status[skill_id]["closure_skill_ids"]
        }
        actual_relations = {
            int(row["id"]): row
            for row in self.runtime.execute(
                "SELECT * FROM skill_effects WHERE skill_id IN (%s)"
                % ",".join("?" for _ in closure_ids),
                tuple(sorted(closure_ids)),
            )
        }
        for step in steps:
            relation = actual_relations.get(int(step["skill_effect_id"]))
            if relation is None:
                raise AssertionError(f"skill_effect {step['skill_effect_id']} is missing")
            if int(relation["effect_id"]) != int(step["effect_id"]):
                raise AssertionError(f"skill_effect {step['skill_effect_id']} effect mismatch")
            effect = self.runtime.execute(
                "SELECT actual_type FROM effects WHERE id=?", (int(step["effect_id"]),)
            ).fetchone()
            if effect is None or str(effect[0]) != str(step["effect_type"]):
                raise AssertionError(f"effect {step['effect_id']} concrete type mismatch")

        selected_ids = self.catalog["skill_table_ids"][str(skill_id)]
        checked = 0
        for table, ids in selected_ids.items():
            if table in ("skills", "passive_buffs"):
                continue
            if self.runtime.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone() is None:
                raise AssertionError(f"runtime table {table} is missing")
            for row_id in ids:
                source = self.catalog_rows[table][int(row_id)]
                ok, detail = row_matches(self.runtime, table, source)
                if not ok:
                    raise AssertionError(detail)
                checked += 1
        return f"{len(steps)} ordered effect steps and {checked} closure rows match"

    def validate_buff_lifecycle(self, skill_id: int) -> str:
        rows = self.graph_rows("buff_contracts", skill_id)
        for row in rows:
            source = json.loads(str(row["row_json"]))
            ok, detail = row_matches(self.runtime, "buffs", source)
            if not ok:
                raise AssertionError(detail)
        selected = self.catalog["skill_table_ids"][str(skill_id)]
        relation_count = 0
        for table in ("buff_tick_effects", "buff_triggers", "buff_unit_modifiers", "tagged_buffs"):
            for row_id in selected.get(table, []):
                ok, detail = row_matches(
                    self.runtime, table, self.catalog_rows[table][int(row_id)]
                )
                if not ok:
                    raise AssertionError(detail)
                relation_count += 1
        return f"{len(rows)} buff templates and {relation_count} lifecycle relations match"

    def validate_combos(self, skill_id: int) -> str:
        checked = 0
        for table in ("combo_conditions", "combo_outcomes"):
            for row in self.graph_rows(table, skill_id):
                source_table = str(row["source_table"])
                source = {"id": int(row["native_id"]), **json.loads(str(row["row_json"]))}
                ok, detail = row_matches(self.runtime, source_table, source)
                if not ok:
                    raise AssertionError(detail)
                checked += 1
        return f"{checked} native condition/outcome rows match"

    def validate_animation_projectile(self, skill_id: int) -> str:
        checked = 0
        for row in self.graph_rows("presentation_bindings", skill_id):
            kind = str(row["presentation_kind"])
            table = PRESENTATION_TABLES.get(kind)
            if table is None:
                continue
            raw_row = row["row_json"]
            if raw_row is None or not str(raw_row).strip():
                continue
            source = json.loads(str(raw_row))
            ok, detail = row_matches(self.runtime, table, source)
            if not ok:
                raise AssertionError(detail)
            checked += 1
        self.compare_skill_fields(
            skill_id,
            (
                "start_anim_id",
                "fire_anim_id",
                "twohand_fire_anim_id",
                "dual_wield_fire_anim_id",
                "projectile_id",
                "skill_controller_id",
                "skill_controller_at_end",
                "end_skill_controller",
                "use_anim_time",
            ),
        )
        return f"{checked} concrete animation/controller/projectile/AOE rows match"

    def validate_assets_localization(self, skill_id: int) -> str:
        bindings = self.graph_rows("presentation_bindings", skill_id)
        expected = {
            str(row["presentation_kind"]): int(row["native_id"])
            for row in bindings
            if str(row["presentation_kind"]) in ("fx", "icon")
        }
        source = self.skill_rows[skill_id]
        runtime = self.runtime_skill(skill_id)
        if "fx" in expected and expected["fx"] != int(source.get("fx_group_id") or 0):
            raise AssertionError("graph FX binding differs from the native skill row")
        if "icon" in expected and expected["icon"] != int(source.get("icon_id") or 0):
            raise AssertionError("graph icon binding differs from the native skill row")
        if int(runtime["fx_group_id"] or 0) != int(source.get("fx_group_id") or 0):
            raise AssertionError("runtime FX binding differs from graph")
        if int(runtime["icon_id"] or 0) != int(source.get("icon_id") or 0):
            raise AssertionError("runtime icon binding differs from graph")
        for field in ("name", "desc"):
            value = runtime[field]
            if isinstance(value, str) and value.startswith("<ref:"):
                raise AssertionError(f"runtime retained unresolved {field} reference")
        return "native icon/FX ids match; unresolved strings have no historical fallback"

    def validate_chained_skills(self, skill_id: int) -> str:
        closure = [int(value) for value in self.catalog_status[skill_id]["closure_skill_ids"]]
        if len(closure) <= 1:
            raise AssertionError(f"skill {skill_id} has no native chained-skill closure")
        statuses = [
            self.runtime.execute(
                "SELECT status FROM native_combat_skill_status WHERE skill_id=?", (value,)
            ).fetchone()
            for value in closure
        ]
        if any(row is None or row[0] != "enabled" for row in statuses):
            raise AssertionError(f"chained closure {closure} is not entirely enabled")
        return f"native chained closure enabled in order: {closure}"

    def validate_not_applicable(self, skill_id: int, area: str) -> str:
        if area == "chained_skills":
            closure = [int(value) for value in self.catalog_status[skill_id]["closure_skill_ids"]]
            if closure != [skill_id]:
                raise AssertionError(f"chained_skills is applicable: {closure}")
            return "catalog closure contains only the root skill"
        if area == "buff_lifecycle":
            if self.graph_rows("buff_contracts", skill_id):
                raise AssertionError("buff_lifecycle has graph rows")
            return "no buff_contracts rows exist"
        if area == "combos":
            if self.graph_rows("combo_conditions", skill_id) or self.graph_rows(
                "combo_outcomes", skill_id
            ):
                raise AssertionError("combos has graph rows")
            return "no native combo condition/outcome rows exist"
        if area == "effects":
            if self.graph_rows("skill_effect_steps", skill_id):
                raise AssertionError("effects has direct skill_effect_steps rows")
            return "no direct skill_effect_steps rows exist; plot outcomes are covered by combos"
        if area == "animation_projectile":
            concrete = [
                row
                for row in self.graph_rows("presentation_bindings", skill_id)
                if str(row["presentation_kind"]) in ("animation", "controller", "projectile")
            ]
            if concrete:
                raise AssertionError("animation_projectile has concrete native rows")
            return "no native animation, controller, or projectile rows exist"
        raise AssertionError(f"Unsupported not_applicable area {area}")

    def execute_case(self, row: sqlite3.Row) -> dict[str, Any]:
        skill_id = int(row["skill_id"])
        area = str(row["area"])
        expected = str(row["expected_state"])
        base = {
            "test_key": str(row["test_key"]),
            "skill_id": skill_id,
            "area": area,
            "expected_state": expected,
        }
        if expected == "not_applicable":
            detail = self.validate_not_applicable(skill_id, area)
            return {**base, "result": "not_applicable", "detail": detail}
        if skill_id == BLOCKED_SKILL_ID:
            status = self.runtime.execute(
                "SELECT status,reason FROM native_combat_skill_status WHERE skill_id=?",
                (skill_id,),
            ).fetchone()
            if status is None or status["status"] != "quarantined" or "BubbleEffect" not in str(status["reason"]):
                raise AssertionError("36594 is not quarantined by the BubbleEffect blocker")
            if self.runtime.execute(
                "SELECT COUNT(*) FROM skill_effects WHERE skill_id=?", (skill_id,)
            ).fetchone()[0]:
                raise AssertionError("36594 leaked executable skill_effect rows")
            return {
                **base,
                "result": "blocked_expected",
                "detail": "runtime execution withheld by the explicit AA8 BubbleEffect semantic blocker",
            }

        validators = {
            "cost_cooldown": self.validate_cost_cooldown,
            "targeting": self.validate_targeting,
            "cast_channel_toggle": self.validate_cast_channel_toggle,
            "effects": self.validate_effects,
            "buff_lifecycle": self.validate_buff_lifecycle,
            "combos": self.validate_combos,
            "animation_projectile": self.validate_animation_projectile,
            "assets_localization": self.validate_assets_localization,
            "chained_skills": self.validate_chained_skills,
        }
        detail = validators[area](skill_id)
        return {**base, "result": "passed", "detail": detail}

    def execute_all(self) -> list[dict[str, Any]]:
        results = []
        for row in self.graph.execute(
            "SELECT * FROM reconstruction_test_cases ORDER BY skill_id,area"
        ):
            try:
                results.append(self.execute_case(row))
            except Exception as exc:
                results.append(
                    {
                        "test_key": str(row["test_key"]),
                        "skill_id": int(row["skill_id"]),
                        "area": str(row["area"]),
                        "expected_state": str(row["expected_state"]),
                        "result": "failed",
                        "detail": str(exc),
                    }
                )
        return results


class ShadowplayReconstructionTests(unittest.TestCase):
    validator: MatrixValidator
    results: list[dict[str, Any]]

    def test_all_252_graph_cases_are_executed(self) -> None:
        self.assertEqual(252, len(self.results))
        for row in self.results:
            with self.subTest(skill_id=row["skill_id"], area=row["area"]):
                self.assertNotEqual("failed", row["result"], row["detail"])

    def test_result_accounting_is_exact(self) -> None:
        self.assertEqual(
            {"blocked_expected": 8, "not_applicable": 32, "passed": 212},
            dict(sorted(Counter(row["result"] for row in self.results).items())),
        )

    def test_six_passive_roots_and_native_tags_are_materialized(self) -> None:
        expected = {
            int(row["id"]): int(row["buff_id"])
            for row in self.validator.contract["passive_rows"]
        }
        actual = {
            int(row["id"]): int(row["buff_id"])
            for row in self.validator.runtime.execute(
                "SELECT id,buff_id FROM passive_buffs WHERE ability_id=8 ORDER BY id"
            )
        }
        self.assertEqual(expected, actual)
        for passive_id, buff_id in expected.items():
            self.assertIsNotNone(
                self.validator.runtime.execute(
                    "SELECT id FROM buffs WHERE id=?", (buff_id,)
                ).fetchone(),
                f"passive {passive_id} buff {buff_id}",
            )
            native_tags = [
                row
                for row in self.validator.catalog["tables"]["tagged_buffs"]
                if int(row["buff_id"]) == buff_id
            ]
            self.assertGreater(len(native_tags), 0)
            for source in native_tags:
                ok, detail = row_matches(
                    self.validator.runtime, "tagged_buffs", source
                )
                self.assertTrue(ok, detail)

    def test_wiki_only_skill_10082_is_not_a_native_root(self) -> None:
        self.assertNotIn(10082, self.validator.contract["root_skill_ids"])
        self.assertEqual(
            0,
            self.validator.runtime.execute(
                "SELECT COUNT(*) FROM native_combat_skill_status WHERE skill_id=10082"
            ).fetchone()[0],
        )

    def test_runtime_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.validator.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.validator.runtime.execute("PRAGMA integrity_check").fetchone()[0])


def main() -> int:
    args = parse_args()
    validator = MatrixValidator(args.graph, args.catalog, args.runtime)
    try:
        results = validator.execute_all()
        ShadowplayReconstructionTests.validator = validator
        ShadowplayReconstructionTests.results = results
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ShadowplayReconstructionTests)
        runner = unittest.TextTestRunner(verbosity=2)
        outcome = runner.run(suite)
        report = {
            "format_version": 1,
            "client_build": "Kakao 8.0.3.12 r558734",
            "authority": {
                "runtime_contract": "shadowplay-specialization-graph-v1.sqlite3",
                "wiki": "corroboration_only",
            },
            "sources": {
                "graph": {"path": str(args.graph.resolve()), "sha256": sha256_file(args.graph)},
                "catalog": {"path": str(args.catalog.resolve()), "sha256": sha256_file(args.catalog)},
                "runtime": {"path": str(args.runtime.resolve()), "sha256": sha256_file(args.runtime)},
            },
            "summary": {
                "total": len(results),
                "results": dict(sorted(Counter(row["result"] for row in results).items())),
                "unit_test_failures": len(outcome.failures),
                "unit_test_errors": len(outcome.errors),
            },
            "cases": results,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(canonical_json(report), encoding="utf-8")
        print(
            canonical_json(
                {
                    "report": str(args.report.resolve()),
                    "report_sha256": sha256_file(args.report),
                    "summary": report["summary"],
                }
            )
        )
        return 0 if outcome.wasSuccessful() else 1
    finally:
        validator.close()


if __name__ == "__main__":
    raise SystemExit(main())
