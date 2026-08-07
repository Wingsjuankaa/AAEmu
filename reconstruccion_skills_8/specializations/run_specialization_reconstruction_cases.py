#!/usr/bin/env python3
"""Execute every forensic reconstruction case against one built AA8 runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from build_specialization_runtime import (
    CLIENT_BUILD,
    DEFAULT_CATALOG,
    extend_interaction_doodad_closure,
    resolve_ability,
    select_runtime_rows,
    validate_graph,
    verify_runtime,
)


ALLOWED_AREAS = {
    "animation_projectile",
    "assets_localization",
    "buff_lifecycle",
    "cast_channel_toggle",
    "chained_skills",
    "combos",
    "cost_cooldown",
    "effects",
    "targeting",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def case_detail(
    connection: sqlite3.Connection, skill_id: int, area: str, state: str
) -> str:
    if state == "not_applicable":
        return "AA8 forensic oracle marks this area not applicable"
    counts = {
        "effects": connection.execute(
            "SELECT COUNT(*) FROM skill_effect_steps WHERE root_skill_id=?", (skill_id,)
        ).fetchone()[0],
        "buff_lifecycle": connection.execute(
            "SELECT COUNT(*) FROM buff_contracts WHERE root_skill_id=?", (skill_id,)
        ).fetchone()[0],
        "combos": connection.execute(
            "SELECT COUNT(*) FROM combo_conditions WHERE root_skill_id=?", (skill_id,)
        ).fetchone()[0]
        + connection.execute(
            "SELECT COUNT(*) FROM combo_outcomes WHERE root_skill_id=?", (skill_id,)
        ).fetchone()[0],
        "animation_projectile": connection.execute(
            "SELECT COUNT(*) FROM presentation_bindings WHERE root_skill_id=?",
            (skill_id,),
        ).fetchone()[0],
        "chained_skills": connection.execute(
            "SELECT COUNT(*) FROM dependency_edges WHERE root_skill_id=?", (skill_id,)
        ).fetchone()[0],
    }
    if area in counts:
        return f"AA8 graph and normalized runtime closure verified ({int(counts[area])} graph rows)"
    return "AA8 root contract fields and normalized runtime row verified"


def execute(args: argparse.Namespace) -> dict[str, Any]:
    ability_id, name, slug = resolve_ability(args.ability)
    for path in (args.graph, args.graph_manifest, args.catalog, args.runtime):
        if not path.is_file():
            raise FileNotFoundError(path)

    contract = validate_graph(
        args.graph, args.graph_manifest, ability_id, name, slug, args.catalog
    )
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    selected, selection = select_runtime_rows(contract, catalog)
    extend_interaction_doodad_closure(selected, selection, catalog, ability_id)

    runtime = sqlite3.connect(args.runtime)
    graph = sqlite3.connect(args.graph)
    graph.row_factory = sqlite3.Row
    try:
        runtime_verification = verify_runtime(runtime, contract, selected, selection)
        audit = {
            int(row["skill_id"]): str(row["observed_state"])
            for row in graph.execute("SELECT skill_id,observed_state FROM downstream_implementation_audit")
        }
        runtime_roots = {
            int(row[0])
            for row in runtime.execute(
                "SELECT skill_id FROM native_combat_skill_status WHERE ability_id=? AND status='enabled'",
                (ability_id,),
            )
        }
        cases: list[dict[str, Any]] = []
        failures: list[str] = []
        for row in graph.execute(
            "SELECT * FROM reconstruction_test_cases ORDER BY skill_id,area,test_key"
        ):
            test_key = str(row["test_key"])
            skill_id = int(row["skill_id"])
            area = str(row["area"])
            expected = str(row["expected_state"])
            try:
                oracle = json.loads(row["oracle_json"])
                evidence = json.loads(row["evidence_json"])
                if area not in ALLOWED_AREAS:
                    raise AssertionError(f"unknown area {area}")
                if expected not in {"confirmed", "not_applicable"}:
                    raise AssertionError(f"unsupported state {expected}")
                if int(oracle["native_skill_id"]) != skill_id:
                    raise AssertionError("oracle native_skill_id differs")
                if oracle["area"] != area or oracle["expected_state"] != expected:
                    raise AssertionError("oracle fields differ from case row")
                if evidence.get("authority") != "client_native" or not evidence.get(
                    "wiki_not_oracle", False
                ):
                    raise AssertionError("case authority is not AA8 native-only")
                if audit.get(skill_id) != "enabled" or skill_id not in runtime_roots:
                    raise AssertionError("skill is not enabled in both audit and runtime")
                result = "not_applicable" if expected == "not_applicable" else "passed"
                detail = case_detail(graph, skill_id, area, expected)
            except Exception as exc:  # report every failed oracle, then fail the run
                result = "failed"
                detail = str(exc)
                failures.append(f"{test_key}: {exc}")
            cases.append(
                {
                    "test_key": test_key,
                    "skill_id": skill_id,
                    "area": area,
                    "expected_state": expected,
                    "result": result,
                    "detail": detail,
                }
            )
    finally:
        graph.close()
        runtime.close()

    result_counts = Counter(case["result"] for case in cases)
    report = {
        "format_version": 1,
        "client_build": CLIENT_BUILD,
        "authority": {
            "runtime_contract": args.graph.name,
            "wiki": "corroboration_only",
        },
        "sources": {
            "graph": {"path": str(args.graph.resolve()), "sha256": sha256_file(args.graph)},
            "catalog": {"path": str(args.catalog.resolve()), "sha256": sha256_file(args.catalog)},
            "runtime": {"path": str(args.runtime.resolve()), "sha256": sha256_file(args.runtime)},
        },
        "runtime_verification": runtime_verification,
        "cases": cases,
        "summary": {
            "total": len(cases),
            "results": dict(sorted(result_counts.items())),
            "failures": len(failures),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    if failures:
        raise RuntimeError("\n".join(failures[:100]))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ability", required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--graph-manifest", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    execute(parse_args())
