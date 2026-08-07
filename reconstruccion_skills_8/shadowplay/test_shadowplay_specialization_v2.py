#!/usr/bin/env python3
"""Run the full V1 reconstruction matrix plus Shadowplay V2 regressions."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unittest
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_shadowplay_specialization_v1_runtime import canonical_json, sha256_file  # noqa: E402
from test_shadowplay_specialization_v1 import MatrixValidator, row_matches  # noqa: E402


MATERIALIZED_ROOTS = (10082, 10104, 10189)
EXPECTED_SKILL_EFFECTS = {
    10082: (2484, 2485, 2486, 22456, 22457, 22458, 31280, 31281),
    10104: (6101, 52542, 53731, 55322, 59336),
    10189: (1350, 34096, 34097, 34098),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--knowledge", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


class ShadowplayV2Tests(unittest.TestCase):
    validator: MatrixValidator
    knowledge: sqlite3.Connection
    results: list[dict]

    def test_all_original_reconstruction_cases_execute(self) -> None:
        self.assertEqual(252, len(self.results))
        for row in self.results:
            with self.subTest(skill_id=row["skill_id"], area=row["area"]):
                self.assertNotEqual("failed", row["result"], row["detail"])

    def test_original_result_accounting_is_exact(self) -> None:
        self.assertEqual(
            {"blocked_expected": 8, "not_applicable": 32, "passed": 212},
            dict(sorted(Counter(row["result"] for row in self.results).items())),
        )

    def test_live_requested_roots_are_learnable_shadowplay_skills(self) -> None:
        rows = list(self.validator.runtime.execute(
            "SELECT id,ability_id,skill_points,req_points,need_learn,show "
            "FROM skills WHERE id IN (10082,10104,10189) ORDER BY id"
        ))
        self.assertEqual(
            [
                (10082, 8, 1, 0, 1, 1),
                (10104, 8, 1, 0, 1, 1),
                (10189, 8, 1, 0, 1, 1),
            ],
            [tuple(row) for row in rows],
        )
        statuses = list(self.validator.runtime.execute(
            "SELECT skill_id,status FROM native_combat_skill_status "
            "WHERE skill_id IN (10082,10104,10189) ORDER BY skill_id"
        ))
        self.assertEqual([(10082, "enabled"), (10104, "enabled"), (10189, "enabled")], [tuple(r) for r in statuses])

    def test_live_requested_roots_use_exact_aa8_effect_applications(self) -> None:
        for skill_id, expected_ids in EXPECTED_SKILL_EFFECTS.items():
            actual_ids = tuple(row[0] for row in self.validator.runtime.execute(
                "SELECT id FROM skill_effects WHERE skill_id=? ORDER BY id", (skill_id,)
            ))
            self.assertEqual(expected_ids, actual_ids)
            for row_id in expected_ids:
                source_row = self.knowledge.execute(
                    "SELECT row_json FROM native_rows WHERE entity_key=? "
                    "AND source_table='skill_effects' AND state='confirmed'",
                    (f"skill_effect_application:{row_id}",),
                ).fetchone()
                self.assertIsNotNone(source_row)
                source = json.loads(str(source_row[0]))
                ok, detail = row_matches(self.validator.runtime, "skill_effects", source)
                self.assertTrue(ok, detail)

    def test_leech_reaches_aa8_buff_steal_primitive(self) -> None:
        count = self.validator.runtime.execute(
            "SELECT COUNT(*) FROM skill_effects se "
            "JOIN effects e ON e.id=se.effect_id "
            "JOIN special_effects s ON s.id=e.actual_id "
            "WHERE se.skill_id=10104 AND e.actual_type='SpecialEffect' "
            "AND s.special_effect_type_id=16"
        ).fetchone()[0]
        self.assertEqual(4, count)

    def test_poisoned_weapons_has_one_shot_server_bridge_and_native_payload(self) -> None:
        trigger = self.validator.runtime.execute(
            "SELECT buff_id,effect_id,event_id,source_agent_id,target_agent_id "
            "FROM buff_triggers WHERE id=88000001"
        ).fetchone()
        self.assertEqual((22266, 720, 1, 3, 2), tuple(trigger))
        bridge = self.validator.runtime.execute(
            "SELECT e.actual_type,e.actual_id,b.buff_id,b.chance,b.stack "
            "FROM effects e JOIN buff_effects b ON b.id=e.actual_id WHERE e.id=720"
        ).fetchone()
        self.assertEqual(("BuffEffect", 256, 196, 100, 1), tuple(bridge))
        payload = self.validator.runtime.execute(
            "SELECT b.duration,b.tick,t.effect_id,e.actual_type,e.actual_id "
            "FROM buffs b JOIN buff_tick_effects t ON t.buff_id=b.id "
            "JOIN effects e ON e.id=t.effect_id WHERE b.id=196 AND t.id=56"
        ).fetchone()
        self.assertEqual((6000, 1000, 791, "DamageEffect", 210), tuple(payload))
        tags = tuple(row[0] for row in self.validator.runtime.execute(
            "SELECT tag_id FROM tagged_buffs WHERE buff_id=196 ORDER BY tag_id"
        ))
        self.assertIn(14, tags)
        self.assertIn(2567, tags)
        self.assertEqual(0, self.validator.runtime.execute(
            "SELECT remove_on_attack_buff_trigger FROM buffs WHERE id=22266"
        ).fetchone()[0], "the native AA8 buff row must remain exact; one-shot consumption is backend-only")

    def test_passives_are_free_unlocks_gated_by_active_points(self) -> None:
        actual = [tuple(row) for row in self.validator.runtime.execute(
            "SELECT req_points,skill_points FROM passive_buffs "
            "WHERE ability_id=8 ORDER BY req_points"
        )]
        self.assertEqual([(3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0)], actual)

    def test_runtime_sqlite_integrity(self) -> None:
        self.assertEqual("ok", self.validator.runtime.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.validator.runtime.execute("PRAGMA integrity_check").fetchone()[0])


def main() -> int:
    args = parse_args()
    validator = MatrixValidator(args.graph, args.catalog, args.runtime)
    knowledge = ro(args.knowledge)
    try:
        results = validator.execute_all()
        ShadowplayV2Tests.validator = validator
        ShadowplayV2Tests.knowledge = knowledge
        ShadowplayV2Tests.results = results
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ShadowplayV2Tests)
        outcome = unittest.TextTestRunner(verbosity=2).run(suite)
        report = {
            "authority": {
                "aa8_sqlite": "runtime_contract",
                "live_packets_and_logs": "acceptance_evidence",
                "wiki": "corroboration_only",
            },
            "client_build": "Kakao 8.0.3.12 r558734",
            "format_version": 2,
            "original_reconstruction_cases": results,
            "sources": {
                "catalog": {"path": str(args.catalog.resolve()), "sha256": sha256_file(args.catalog)},
                "graph": {"path": str(args.graph.resolve()), "sha256": sha256_file(args.graph)},
                "knowledge": {"path": str(args.knowledge.resolve()), "sha256": sha256_file(args.knowledge)},
                "runtime": {"path": str(args.runtime.resolve()), "sha256": sha256_file(args.runtime)},
            },
            "summary": {
                "original_case_results": dict(sorted(Counter(row["result"] for row in results).items())),
                "original_cases": len(results),
                "unit_test_errors": len(outcome.errors),
                "unit_test_failures": len(outcome.failures),
                "v2_regression_tests": outcome.testsRun,
            },
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(canonical_json(report), encoding="utf-8")
        print(canonical_json({
            "report": str(args.report.resolve()),
            "report_sha256": sha256_file(args.report),
            "summary": report["summary"],
        }))
        return 0 if outcome.wasSuccessful() else 1
    finally:
        knowledge.close()
        validator.close()


if __name__ == "__main__":
    raise SystemExit(main())
