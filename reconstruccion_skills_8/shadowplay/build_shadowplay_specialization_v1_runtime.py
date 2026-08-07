#!/usr/bin/env python3
"""Materialize the AA8 Shadowplay contract without enabling blocked skill 36594."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NATIVE_COMBAT = ROOT / "reconstruccion_skills_8" / "native_combat"
sys.path.insert(0, str(NATIVE_COMBAT))

from build_native_combat_runtime import columns, normalize, sha256_file, upsert_rows  # noqa: E402


EXPECTED_GRAPH_SHA256 = "40B7BD4F82B0BA86A1E9FEB8CF6A436B94983634284D01C651FAB5C7C7358AE7"
EXPECTED_CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
BLOCKED_SKILL_ID = 36594
GRAPH_TABLES = {
    "specialization_roots": "root_key",
    "specialization_skills": "skill_id",
    "skill_runtime_contracts": "skill_id",
    "skill_effect_steps": "step_key",
    "buff_contracts": "contract_key",
    "combo_conditions": "condition_key",
    "combo_outcomes": "outcome_key",
    "presentation_bindings": "binding_key",
    "dependency_closure": "closure_key",
    "dependency_edges": "edge_key",
    "reconstruction_test_cases": "test_key",
    "downstream_implementation_audit": "audit_key",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def compact_canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def rows_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(compact_canonical(rows)).hexdigest().upper()


def graph_rows(
    graph: sqlite3.Connection,
    table: str,
    root_skill_ids: list[int],
) -> list[dict[str, Any]]:
    primary_key = GRAPH_TABLES[table]
    placeholders = ",".join("?" for _ in root_skill_ids)
    if table == "specialization_roots":
        sql = f"SELECT * FROM {table} WHERE ability_id=8 ORDER BY {primary_key}"
        args: tuple[Any, ...] = ()
    elif table == "specialization_skills":
        sql = (
            f"SELECT * FROM {table} WHERE root_member=1 "
            f"AND skill_id IN ({placeholders}) ORDER BY {primary_key}"
        )
        args = tuple(root_skill_ids)
    elif table in ("skill_runtime_contracts", "reconstruction_test_cases", "downstream_implementation_audit"):
        column = "skill_id"
        sql = f"SELECT * FROM {table} WHERE {column} IN ({placeholders}) ORDER BY {primary_key}"
        args = tuple(root_skill_ids)
    else:
        sql = f"SELECT * FROM {table} WHERE root_skill_id IN ({placeholders}) ORDER BY {primary_key}"
        args = tuple(root_skill_ids)
    return [dict(row) for row in graph.execute(sql, args)]


def validate_graph(graph_path: Path) -> dict[str, Any]:
    graph_sha = sha256_file(graph_path)
    if graph_sha != EXPECTED_GRAPH_SHA256:
        raise RuntimeError(f"Unexpected Shadowplay graph SHA-256: {graph_sha}")

    graph = open_read_only(graph_path)
    try:
        metadata = {
            str(row["key"]): json.loads(str(row["value_json"]))
            for row in graph.execute("SELECT key,value_json FROM metadata")
        }
        if metadata.get("client_build") != EXPECTED_CLIENT_BUILD:
            raise RuntimeError(f"Unexpected client build: {metadata.get('client_build')}")
        if metadata.get("specialization") != {
            "ability_id": 8,
            "name": "Shadowplay",
            "slug": "shadowplay",
        }:
            raise RuntimeError("The graph is not the Shadowplay ability_id=8 contract")

        root_skill_ids = [
            int(row[0])
            for row in graph.execute(
                "SELECT skill_id FROM specialization_skills "
                "WHERE root_member=1 ORDER BY skill_id"
            )
        ]
        visible_skill_ids = [
            int(row[0])
            for row in graph.execute(
                "SELECT skill_id FROM specialization_skills "
                "WHERE root_member=1 AND visible=1 ORDER BY skill_id"
            )
        ]
        passive_rows = [
            json.loads(str(row[0]))
            for row in graph.execute(
                "SELECT row_json FROM specialization_roots "
                "WHERE root_kind='passive_buff' AND ability_id=8 ORDER BY native_id"
            )
        ]
        audit = {
            int(row["skill_id"]): {
                "status": str(row["observed_state"]),
                "reason": str(row["reason"] or ""),
            }
            for row in graph.execute(
                "SELECT skill_id,observed_state,reason "
                "FROM downstream_implementation_audit ORDER BY skill_id"
            )
        }
        if len(root_skill_ids) != 28 or len(set(root_skill_ids)) != 28:
            raise RuntimeError(f"Expected 28 Shadowplay roots, found {len(root_skill_ids)}")
        if len(visible_skill_ids) != 9:
            raise RuntimeError(f"Expected 9 visible Shadowplay roots, found {len(visible_skill_ids)}")
        if len(passive_rows) != 6:
            raise RuntimeError(f"Expected 6 Shadowplay passives, found {len(passive_rows)}")
        if 10082 in root_skill_ids:
            raise RuntimeError("Wiki-only skill 10082 must never become a native root")
        if audit.get(BLOCKED_SKILL_ID, {}).get("status") != "quarantined":
            raise RuntimeError("Skill 36594 must remain explicitly quarantined")
        if [skill_id for skill_id, row in audit.items() if row["status"] == "quarantined"] != [BLOCKED_SKILL_ID]:
            raise RuntimeError("Shadowplay must have exactly one quarantined root: 36594")

        test_states = dict(
            graph.execute(
                "SELECT expected_state,COUNT(*) FROM reconstruction_test_cases "
                "GROUP BY expected_state ORDER BY expected_state"
            )
        )
        if test_states != {"confirmed": 220, "not_applicable": 32}:
            raise RuntimeError(f"Unexpected reconstruction test matrix: {test_states}")

        consumed = {}
        for table in GRAPH_TABLES:
            rows = graph_rows(graph, table, root_skill_ids)
            consumed[table] = {
                "primary_key": GRAPH_TABLES[table],
                "row_count": len(rows),
                "canonical_rows_sha256": rows_digest(rows),
            }

        per_skill = []
        for skill_id in root_skill_ids:
            table_contract = {}
            for table in (
                "skill_runtime_contracts",
                "skill_effect_steps",
                "buff_contracts",
                "combo_conditions",
                "combo_outcomes",
                "presentation_bindings",
                "dependency_closure",
                "dependency_edges",
                "reconstruction_test_cases",
            ):
                rows = graph_rows(graph, table, [skill_id])
                table_contract[table] = {
                    "row_count": len(rows),
                    "canonical_rows_sha256": rows_digest(rows),
                }
            per_skill.append(
                {
                    "skill_id": skill_id,
                    "runtime_status": audit[skill_id]["status"],
                    "graph_rows": table_contract,
                }
            )
        return {
            "graph_sha256": graph_sha,
            "root_skill_ids": root_skill_ids,
            "visible_skill_ids": visible_skill_ids,
            "passive_rows": passive_rows,
            "audit": audit,
            "test_states": test_states,
            "consumed_graph_rows": consumed,
            "per_skill_contracts": per_skill,
        }
    finally:
        graph.close()


def catalog_index(catalog: dict[str, Any]) -> dict[str, dict[int, dict[str, Any]]]:
    return {
        table: {int(row["id"]): row for row in rows}
        for table, rows in catalog["tables"].items()
    }


def select_runtime_rows(
    contract: dict[str, Any], catalog: dict[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    root_ids = set(contract["root_skill_ids"])
    statuses = {
        int(row["skill_id"]): row
        for row in catalog["skill_status"]
        if int(row["ability_id"]) == 8
    }
    if set(statuses) != root_ids:
        raise RuntimeError("Native catalog and graph disagree on Shadowplay root membership")

    selected_ids: dict[str, set[int]] = defaultdict(set)
    for skill_id in sorted(root_ids):
        expected = contract["audit"][skill_id]["status"]
        actual = str(statuses[skill_id]["status"])
        if actual != expected:
            raise RuntimeError(
                f"Skill {skill_id} catalog status {actual} differs from graph audit {expected}"
            )
        selected_ids["skills"].add(skill_id)
        if expected != "enabled":
            continue
        for table, ids in catalog["skill_table_ids"][str(skill_id)].items():
            selected_ids[table].update(int(value) for value in ids)

    passive_by_id = {
        int(row["id"]): row for row in catalog["tables"]["passive_buffs"]
    }
    passive_ids = {int(row["id"]) for row in contract["passive_rows"]}
    if not passive_ids.issubset(passive_by_id):
        raise RuntimeError("The catalog is missing a Shadowplay passive root")
    passive_buff_ids = {int(passive_by_id[value]["buff_id"]) for value in passive_ids}
    selected_ids["passive_buffs"].update(passive_ids)
    selected_ids["buffs"].update(passive_buff_ids)
    selected_ids["tagged_buffs"].update(
        int(row["id"])
        for row in catalog["tables"]["tagged_buffs"]
        if int(row["buff_id"]) in passive_buff_ids
    )

    indexed = catalog_index(catalog)
    selected: dict[str, list[dict[str, Any]]] = {}
    for table, ids in sorted(selected_ids.items()):
        missing = ids.difference(indexed.get(table, {}))
        if missing:
            raise RuntimeError(f"Catalog table {table} is missing ids {sorted(missing)}")
        selected[table] = [indexed[table][row_id] for row_id in sorted(ids)]

    if selected.get("bubble_effects"):
        raise RuntimeError("BubbleEffect must not enter the executable Shadowplay slice")
    if any(int(row["skill_id"]) == BLOCKED_SKILL_ID for row in selected.get("skill_effects", [])):
        raise RuntimeError("Quarantined skill 36594 leaked executable skill_effect rows")

    primitive_state = {
        str(row["primitive"]): str(row["state"])
        for row in catalog["coverage"]["effect_primitives"]
    }
    pending = sorted(
        {
            str(row["actual_type"])
            for row in selected.get("effects", [])
            if primitive_state.get(str(row["actual_type"])) != "native_implemented"
        }
    )
    if pending:
        raise RuntimeError(f"Enabled Shadowplay slice reaches pending primitives: {pending}")

    return selected, {
        "root_status": {
            str(skill_id): {
                "status": str(statuses[skill_id]["status"]),
                "closure_skill_ids": [int(value) for value in statuses[skill_id]["closure_skill_ids"]],
                "reason": str(statuses[skill_id]["reason"]),
            }
            for skill_id in sorted(statuses)
        },
        "passive_ids": sorted(passive_ids),
        "passive_buff_ids": sorted(passive_buff_ids),
        "selected_table_ids": {
            table: sorted(ids) for table, ids in sorted(selected_ids.items())
        },
    }


def normalized_row_matches(
    connection: sqlite3.Connection,
    table: str,
    source: dict[str, Any],
) -> bool:
    expected, _ = normalize(table, source)
    available = columns(connection, table)
    names = [name for name in expected if name in available]
    actual = connection.execute(
        f"SELECT {','.join(chr(34) + name.replace(chr(34), chr(34) * 2) + chr(34) for name in names)} "
        f"FROM \"{table}\" WHERE id=?",
        (int(source["id"]),),
    ).fetchone()
    return actual is not None and tuple(actual) == tuple(expected[name] for name in names)


def validate_runtime(
    connection: sqlite3.Connection,
    contract: dict[str, Any],
    selected: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    errors: list[str] = []
    for table, rows in selected.items():
        for row in rows:
            if not normalized_row_matches(connection, table, row):
                errors.append(f"{table}.{row['id']} differs from the selected AA8 row")

    roots = contract["root_skill_ids"]
    placeholders = ",".join("?" for _ in roots)
    status_counts = dict(
        connection.execute(
            f"SELECT status,COUNT(*) FROM native_combat_skill_status "
            f"WHERE skill_id IN ({placeholders}) GROUP BY status ORDER BY status",
            tuple(roots),
        )
    )
    if status_counts != {"enabled": 27, "quarantined": 1}:
        errors.append(f"Unexpected Shadowplay status counts: {status_counts}")
    if connection.execute(
        "SELECT COUNT(*) FROM skill_effects WHERE skill_id=?", (BLOCKED_SKILL_ID,)
    ).fetchone()[0]:
        errors.append("Quarantined skill 36594 has executable skill_effect rows")

    passive_ids = sorted(int(row["id"]) for row in contract["passive_rows"])
    passive_placeholders = ",".join("?" for _ in passive_ids)
    actual_passives = [
        int(row[0])
        for row in connection.execute(
            f"SELECT id FROM passive_buffs WHERE id IN ({passive_placeholders}) ORDER BY id",
            tuple(passive_ids),
        )
    ]
    if actual_passives != passive_ids:
        errors.append(f"Shadowplay passive rows differ: {actual_passives}")

    missing_passive_buffs = connection.execute(
        "SELECT COUNT(*) FROM passive_buffs p LEFT JOIN buffs b ON b.id=p.buff_id "
        "WHERE p.ability_id=8 AND b.id IS NULL"
    ).fetchone()[0]
    if missing_passive_buffs:
        errors.append(f"Shadowplay passives with missing buff template: {missing_passive_buffs}")

    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite checks failed: quick={quick}, integrity={integrity}")
    if errors:
        raise RuntimeError("\n".join(errors[:100]))
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "root_status_counts": status_counts,
        "visible_roots": len(contract["visible_skill_ids"]),
        "passive_roots": len(actual_passives),
        "quarantined_skill_id": BLOCKED_SKILL_ID,
        "wiki_skill_10082_materialized": False,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.runtime_carrier, args.graph, args.catalog):
        if not path.is_file():
            raise FileNotFoundError(path)
    output = args.output.resolve()
    if output == args.runtime_carrier.resolve():
        raise ValueError("The output must not replace the runtime carrier")

    contract = validate_graph(args.graph)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if "historical_3_0" in json.dumps(catalog.get("provenance", {})):
        raise RuntimeError("Historical combat provenance is forbidden")
    selected, selection = select_runtime_rows(contract, catalog)

    output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.runtime_carrier, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        merge = {
            table: upsert_rows(connection, table, rows)
            for table, rows in sorted(selected.items())
        }
        connection.executemany(
            "INSERT INTO native_combat_skill_status(skill_id,ability_id,status,reason,provenance) "
            "VALUES(?,8,?,?,?) ON CONFLICT(skill_id) DO UPDATE SET "
            "ability_id=excluded.ability_id,status=excluded.status,reason=excluded.reason,"
            "provenance=excluded.provenance",
            [
                (
                    skill_id,
                    contract["audit"][skill_id]["status"],
                    contract["audit"][skill_id]["reason"],
                    "aa8_shadowplay_graph_v1",
                )
                for skill_id in contract["root_skill_ids"]
            ],
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS shadowplay_reconstruction_metadata("
            "key TEXT PRIMARY KEY,value TEXT NOT NULL,provenance TEXT NOT NULL)"
        )
        metadata = {
            "client_build": EXPECTED_CLIENT_BUILD,
            "graph_sha256": contract["graph_sha256"],
            "root_skill_count": "28",
            "visible_skill_count": "9",
            "passive_count": "6",
            "blocked_skill_id": str(BLOCKED_SKILL_ID),
            "wiki_skill_10082_policy": "corroborative_only_not_materialized",
        }
        connection.executemany(
            "INSERT INTO shadowplay_reconstruction_metadata(key,value,provenance) "
            "VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET "
            "value=excluded.value,provenance=excluded.provenance",
            [(key, value, "aa8_shadowplay_graph_v1") for key, value in sorted(metadata.items())],
        )
        connection.commit()
        verification = validate_runtime(connection, contract, selected) if args.verify else None
        connection.execute("VACUUM")
    except Exception:
        connection.close()
        output.unlink(missing_ok=True)
        raise
    finally:
        if connection:
            connection.close()

    manifest = {
        "format_version": 1,
        "client_build": EXPECTED_CLIENT_BUILD,
        "authority": {
            "runtime_contract": "shadowplay-specialization-graph-v1.sqlite3",
            "wiki": "corroboration_only",
            "historical_gameplay_rows": False,
        },
        "sources": {
            "runtime_carrier": {
                "path": str(args.runtime_carrier.resolve()),
                "sha256": sha256_file(args.runtime_carrier),
            },
            "shadowplay_graph": {
                "path": str(args.graph.resolve()),
                "sha256": contract["graph_sha256"],
            },
            "native_combat_catalog": {
                "path": str(args.catalog.resolve()),
                "sha256": sha256_file(args.catalog),
            },
        },
        "consumed_graph_rows": contract["consumed_graph_rows"],
        "skill_contracts": contract["per_skill_contracts"],
        "selection": selection,
        "merge": merge,
        "reconstruction_test_contract": {
            "total": sum(contract["test_states"].values()),
            "states": contract["test_states"],
        },
        "verification": verification,
        "output": {"path": str(output), "sha256": sha256_file(output)},
    }
    args.manifest.write_text(canonical_json(manifest), encoding="utf-8")
    print(
        canonical_json(
            {
                "output": str(output),
                "output_sha256": manifest["output"]["sha256"],
                "manifest": str(args.manifest.resolve()),
                "manifest_sha256": sha256_file(args.manifest),
                "selected_rows": {
                    table: len(rows) for table, rows in sorted(selected.items())
                },
                "verification": verification,
            }
        )
    )
    return manifest


def main() -> int:
    build(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
