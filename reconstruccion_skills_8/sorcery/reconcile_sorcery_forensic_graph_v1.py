"""Reconcile the independent AA8 Sorcery graph with the active V9 runtime.

This is deliberately a comparison artifact.  It never promotes a runtime or
AA10 row into native AA8 evidence; instead it makes every mismatch between the
forensic graph and the executable closure explicit and terminal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DEFAULT_GRAPH = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\sorcery-specialization-graph-v1.sqlite3"
)
DEFAULT_AUDIT = HERE / "generated" / "sorcery-executable-semantics-audit-v3.json"
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v9.sqlite3"
)
DEFAULT_CROSSWALK = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3"
)
DEFAULT_OUTPUT = HERE / "generated" / "sorcery-forensic-runtime-reconciliation-v1.json"

TOMBSTONE_PARENT_CANDIDATES = {10151, 10153}
CROSS_ABILITY_CHILDREN = {15317}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.graph, args.audit, args.runtime, args.crosswalk):
        if not path.is_file():
            raise FileNotFoundError(path)

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    audit_roots = {int(row["skill_id"]): row for row in audit["roots"]}
    audit_records = audit["roots"] + audit["passives"]
    audit_skill_ids = {
        int(value)
        for record in audit_records
        for value in record["closure_ids"].get("skills", [])
    }

    graph = read_only(args.graph)
    runtime = read_only(args.runtime)
    crosswalk = read_only(args.crosswalk)
    try:
        graph_roots = {
            int(row[0])
            for row in graph.execute(
                "SELECT native_id FROM specialization_roots "
                "WHERE root_kind='skill' ORDER BY native_id"
            )
        }
        graph_states = dict(
            graph.execute(
                "SELECT observed_state,COUNT(*) FROM downstream_implementation_audit "
                "GROUP BY observed_state ORDER BY observed_state"
            )
        )
        candidate_membership = {
            int(row["skill_id"]): dict(row)
            for row in graph.execute(
                "SELECT skill_id,root_member,lifecycle,membership_state,native_state "
                "FROM specialization_skills WHERE skill_id IN (10151,10153) "
                "ORDER BY skill_id"
            )
        }
        runtime_rows = {
            int(row["id"]): dict(row)
            for row in runtime.execute(
                "SELECT id,ability_id,show,plot_id FROM skills "
                "WHERE id IN (10151,10153,15317) ORDER BY id"
            )
        }
        crosswalk_rows = {
            int(row["aa10_id"]): dict(row)
            for row in crosswalk.execute(
                "SELECT aa8_id,aa10_id,classification,relation_state,property_state,"
                "balance_state,aa8_locator,aa10_locator FROM row_comparisons "
                "WHERE table_name='skills' AND aa10_id IN ('10151','10153') "
                "ORDER BY CAST(aa10_id AS INTEGER)"
            )
        }
    finally:
        graph.close()
        runtime.close()
        crosswalk.close()

    missing_native = sorted(graph_roots - audit_skill_ids)
    audit_extras = sorted(audit_skill_ids - graph_roots)
    expected_extras = sorted(TOMBSTONE_PARENT_CANDIDATES | CROSS_ABILITY_CHILDREN)
    if missing_native:
        raise RuntimeError(f"Native Sorcery graph roots omitted by runtime audit: {missing_native}")
    if audit_extras != expected_extras:
        raise RuntimeError(
            f"Unexpected executable skills outside native Sorcery roots: {audit_extras}"
        )
    if graph_states != {"enabled": len(graph_roots)}:
        raise RuntimeError(f"Sorcery graph contains non-enabled downstream states: {graph_states}")

    classifications: list[dict[str, Any]] = []
    for skill_id in sorted(graph_roots):
        root = audit_roots.get(skill_id)
        classifications.append(
            {
                "skill_id": skill_id,
                "classification": "exact_aa8_native_sorcery",
                "entrypoint_kind": root["root_kind"] if root else "reachable_dependency",
                "authority": "aa8_client_native",
                "runtime_state": "enabled",
            }
        )
    for skill_id in sorted(TOMBSTONE_PARENT_CANDIDATES):
        membership = candidate_membership.get(skill_id)
        row = runtime_rows.get(skill_id)
        crosswalk_row = crosswalk_rows.get(skill_id)
        if not membership or membership["root_member"] != 0:
            raise RuntimeError(f"Tombstone candidate {skill_id} was promoted into native roots")
        if not row or int(row["ability_id"] or 0) != 7:
            raise RuntimeError(f"Tombstone candidate {skill_id} is absent from V9 runtime")
        if not crosswalk_row or crosswalk_row["classification"] != "aa10_only":
            raise RuntimeError(f"Unexpected crosswalk class for tombstone candidate {skill_id}")
        classifications.append(
            {
                "skill_id": skill_id,
                "classification": "runtime_confirmed_tombstone_parent_candidate",
                "entrypoint_kind": audit_roots[skill_id]["root_kind"],
                "authority": "observed_aa8_protocol_plus_aa10_candidate_not_native_aa8_row",
                "forensic_membership": membership,
                "runtime_row": row,
                "crosswalk": crosswalk_row,
                "promotion_allowed": False,
            }
        )
    for skill_id in sorted(CROSS_ABILITY_CHILDREN):
        row = runtime_rows.get(skill_id)
        parents = sorted(
            int(record["skill_id"])
            for record in audit["roots"]
            if skill_id in {int(value) for value in record["closure_ids"].get("skills", [])}
        )
        if not row or int(row["ability_id"] or 0) != 0 or not parents:
            raise RuntimeError(f"Cross-ability child {skill_id} is not executable evidence")
        classifications.append(
            {
                "skill_id": skill_id,
                "classification": "exact_aa8_cross_ability_reachable_child",
                "entrypoint_kind": "reachable_dependency",
                "authority": "aa8_runtime_native_child_row_and_directed_closure",
                "runtime_row": row,
                "reachable_from_roots": parents,
            }
        )

    return {
        "format_version": 1,
        "client_build": "Kakao 8.0.3.12 r558734",
        "authority_rule": {
            "aa8_native_graph": "primary_identity_relation_and_property_authority",
            "aa8_runtime": "executable_closure_and_observed_protocol_authority",
            "aa10_crosswalk": "gap_reduction_only_no_automatic_promotion",
        },
        "sources": {
            key: {"path": str(path.resolve()), "sha256": sha256_file(path)}
            for key, path in (
                ("forensic_graph", args.graph),
                ("executable_audit", args.audit),
                ("runtime_v9", args.runtime),
                ("aa10_crosswalk", args.crosswalk),
            )
        },
        "coverage": {
            "native_sorcery_graph_roots": len(graph_roots),
            "audited_entrypoints": len(audit["roots"]),
            "audited_public_entrypoints": audit["scope"]["public_root_count"],
            "audited_internal_entrypoints": audit["scope"]["internal_root_count"],
            "executable_skill_closure": len(audit_skill_ids),
            "passives": len(audit["passives"]),
            "native_roots_missing_from_executable_audit": missing_native,
            "executable_rows_outside_native_sorcery_roots": audit_extras,
            "downstream_states": graph_states,
            "blocked_entrypoints": audit["summary"]["roots_with_blockers"],
            "missing_rows": audit["summary"]["roots_with_missing_rows"],
            "classification_count": len(classifications),
            "unclassified_executable_skills": sorted(
                audit_skill_ids - {row["skill_id"] for row in classifications}
            ),
        },
        "classifications": sorted(classifications, key=lambda row: row["skill_id"]),
        "terminal_conclusion": (
            "All 40 native AA8 Sorcery skill roots are covered by the executable audit; "
            "the only three extra executable IDs are two non-promotable tombstone parent "
            "candidates and one exact AA8 cross-ability child."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    if report["coverage"]["unclassified_executable_skills"]:
        raise RuntimeError("Executable Sorcery closure contains unclassified skill IDs")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(report), encoding="utf-8")
    print(canonical({
        "output": str(args.output.resolve()),
        "sha256": sha256_file(args.output),
        "coverage": report["coverage"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
