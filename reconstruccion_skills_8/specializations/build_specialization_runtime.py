#!/usr/bin/env python3
"""Build one AA8 specialization slice from its forensic graph and native catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / "reconstruccion_skills_8"
NATIVE_COMBAT = ROOT / "reconstruccion_skills_8" / "native_combat"
SWIFTBLADE_ROOT = SKILLS_ROOT / "swiftblade"
CLIENT_FORENSICS_CONFIG = (
    ROOT / "reconstruccion_cliente_8" / "config" / "kakao-r558734.json"
)
DEFAULT_CATALOG = (
    NATIVE_COMBAT / "generated" / "native-combat-catalog-v1.json"
)
DEFAULT_ENV = ROOT / ".env"
CLIENT_BUILD = "Kakao 8.0.3.12 r558734"

sys.path.insert(0, str(NATIVE_COMBAT))
sys.path.insert(0, str(SKILLS_ROOT))
sys.path.insert(0, str(SWIFTBLADE_ROOT))
sys.path.insert(0, str(ROOT))
from build_native_combat_runtime import columns, normalize, sha256_file, upsert_rows  # noqa: E402
from extract_battlerage_manifest import extract_client_relationships  # noqa: E402
from extract_swiftblade_phase3 import build_closure, extract_native_tables  # noqa: E402
from reconstruccion_cliente_8.client_forensics.nuia_story_graph import (  # noqa: E402
    DOODAD_RESULT_SPECS,
    _decode_result,
)


ABILITIES = {
    1: ("Battlerage", "battlerage"),
    2: ("Witchcraft", "witchcraft"),
    3: ("Defense", "defense"),
    4: ("Auramancy", "auramancy"),
    5: ("Occultism", "occultism"),
    6: ("Archery", "archery"),
    7: ("Sorcery", "sorcery"),
    8: ("Shadowplay", "shadowplay"),
    9: ("Songcraft", "songcraft"),
    10: ("Vitalism", "vitalism"),
    11: ("Malediction", "malediction"),
    12: ("Swiftblade", "swiftblade"),
    13: ("Gunslinger", "gunslinger"),
    14: ("Spelldance", "spelldance"),
}

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


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def compact_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def resolve_ability(value: str | int) -> tuple[int, str, str]:
    text = str(value).strip().lower()
    if text.isdigit() and int(text) in ABILITIES:
        ability_id = int(text)
    else:
        matches = [
            ability_id
            for ability_id, (name, slug) in ABILITIES.items()
            if text in {name.lower(), slug}
        ]
        if len(matches) != 1:
            raise ValueError(f"Unknown AA8 specialization: {value}")
        ability_id = matches[0]
    name, slug = ABILITIES[ability_id]
    return ability_id, name, slug


def env_value(path: Path, key: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    raise RuntimeError(f"{key} is absent from {path}")


def configured_output_dir() -> Path:
    raw = json.loads(CLIENT_FORENSICS_CONFIG.read_text(encoding="utf-8"))
    value = Path(str(raw["output_dir"]))
    if value.is_absolute():
        return value.resolve()
    return (CLIENT_FORENSICS_CONFIG.parent / value).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ability", required=True)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--runtime-carrier", type=Path)
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--graph-manifest", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--determinism-output", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def rows_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(compact_json(rows)).hexdigest().upper()


def graph_rows(
    graph: sqlite3.Connection,
    table: str,
    ability_id: int,
    root_skill_ids: list[int],
) -> list[dict[str, Any]]:
    primary_key = GRAPH_TABLES[table]
    placeholders = ",".join("?" for _ in root_skill_ids)
    if table == "specialization_roots":
        sql = f"SELECT * FROM {table} WHERE ability_id=? ORDER BY {primary_key}"
        args: tuple[Any, ...] = (ability_id,)
    elif table == "specialization_skills":
        sql = (
            f"SELECT * FROM {table} WHERE root_member=1 "
            f"AND skill_id IN ({placeholders}) ORDER BY {primary_key}"
        )
        args = tuple(root_skill_ids)
    elif table in {
        "skill_runtime_contracts",
        "reconstruction_test_cases",
        "downstream_implementation_audit",
    }:
        sql = f"SELECT * FROM {table} WHERE skill_id IN ({placeholders}) ORDER BY {primary_key}"
        args = tuple(root_skill_ids)
    else:
        sql = f"SELECT * FROM {table} WHERE root_skill_id IN ({placeholders}) ORDER BY {primary_key}"
        args = tuple(root_skill_ids)
    return [dict(row) for row in graph.execute(sql, args)]


def validate_graph(
    graph_path: Path,
    manifest_path: Path,
    ability_id: int,
    expected_name: str,
    expected_slug: str,
    catalog_path: Path,
) -> dict[str, Any]:
    for path in (graph_path, manifest_path, catalog_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    graph_sha = sha256_file(graph_path)
    graph_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared_graph_sha = str(graph_manifest["outputs"]["database"]["sha256"])
    if graph_sha != declared_graph_sha:
        raise RuntimeError(
            f"Graph SHA-256 differs from its manifest: {graph_sha} != {declared_graph_sha}"
        )
    declared_catalog_sha = str(graph_manifest["inputs"]["catalog"]["sha256"])
    catalog_sha = sha256_file(catalog_path)
    if catalog_sha != declared_catalog_sha:
        raise RuntimeError(
            "The graph and runtime catalog do not belong to the same extraction: "
            f"{declared_catalog_sha} != {catalog_sha}"
        )

    graph = open_read_only(graph_path)
    try:
        metadata = {
            str(row["key"]): json.loads(str(row["value_json"]))
            for row in graph.execute("SELECT key,value_json FROM metadata")
        }
        expected_specialization = {
            "ability_id": ability_id,
            "name": expected_name,
            "slug": expected_slug,
        }
        if metadata.get("client_build") != CLIENT_BUILD:
            raise RuntimeError(f"Unexpected client build: {metadata.get('client_build')}")
        if metadata.get("specialization") != expected_specialization:
            raise RuntimeError(
                f"Graph specialization mismatch: {metadata.get('specialization')}"
            )

        failed_events = graph.execute(
            "SELECT COUNT(*) FROM validation_events WHERE state<>'confirmed'"
        ).fetchone()[0]
        audit_queue = graph.execute("SELECT COUNT(*) FROM audit_queue").fetchone()[0]
        if failed_events or audit_queue:
            raise RuntimeError(
                f"Graph is not closed: failed_events={failed_events}, audit_queue={audit_queue}"
            )

        root_skill_ids = [
            int(row[0])
            for row in graph.execute(
                "SELECT skill_id FROM specialization_skills "
                "WHERE root_member=1 ORDER BY skill_id"
            )
        ]
        if not root_skill_ids or len(root_skill_ids) != len(set(root_skill_ids)):
            raise RuntimeError("The graph has no unique skill-root set")
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
                "WHERE root_kind='passive_buff' AND ability_id=? ORDER BY native_id",
                (ability_id,),
            )
        ]
        if len(passive_rows) != 6:
            raise RuntimeError(
                f"Ability {ability_id} must have six native passive rows, found {len(passive_rows)}"
            )
        if any(int(row.get("skill_points", -1)) != 0 for row in passive_rows):
            raise RuntimeError("AA8 passives must preserve native skill_points=0")

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
        if set(audit) != set(root_skill_ids):
            raise RuntimeError("The graph audit does not cover every root exactly once")

        test_states = {
            str(row[0]): int(row[1])
            for row in graph.execute(
                "SELECT expected_state,COUNT(*) FROM reconstruction_test_cases "
                "GROUP BY expected_state ORDER BY expected_state"
            )
        }
        if sum(test_states.values()) != len(root_skill_ids) * 9:
            raise RuntimeError(
                f"Expected nine reconstruction cases per root, found {test_states}"
            )

        consumed = {}
        for table in GRAPH_TABLES:
            rows = graph_rows(graph, table, ability_id, root_skill_ids)
            consumed[table] = {
                "primary_key": GRAPH_TABLES[table],
                "row_count": len(rows),
                "canonical_rows_sha256": rows_digest(rows),
            }
        return {
            "ability_id": ability_id,
            "name": expected_name,
            "slug": expected_slug,
            "graph_sha256": graph_sha,
            "graph_manifest_sha256": sha256_file(manifest_path),
            "root_skill_ids": root_skill_ids,
            "visible_skill_ids": visible_skill_ids,
            "passive_rows": passive_rows,
            "audit": audit,
            "test_states": test_states,
            "consumed_graph_rows": consumed,
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
    ability_id = int(contract["ability_id"])
    root_ids = set(int(value) for value in contract["root_skill_ids"])
    statuses = {
        int(row["skill_id"]): row
        for row in catalog["skill_status"]
        if int(row["ability_id"]) == ability_id
    }
    if set(statuses) != root_ids:
        raise RuntimeError(
            f"Catalog and graph disagree on ability {ability_id} roots: "
            f"catalog_only={sorted(set(statuses)-root_ids)}, "
            f"graph_only={sorted(root_ids-set(statuses))}"
        )

    selected_ids: dict[str, set[int]] = defaultdict(set)
    quarantined: list[int] = []
    enabled: list[int] = []
    for skill_id in sorted(root_ids):
        expected = str(contract["audit"][skill_id]["status"])
        actual = str(statuses[skill_id]["status"])
        if actual != expected:
            raise RuntimeError(
                f"Skill {skill_id}: catalog={actual}, graph={expected}"
            )
        selected_ids["skills"].add(skill_id)
        if actual == "quarantined":
            quarantined.append(skill_id)
            continue
        if actual != "enabled":
            raise RuntimeError(f"Unsupported runtime state {actual} for skill {skill_id}")
        enabled.append(skill_id)
        for table, ids in catalog["skill_table_ids"][str(skill_id)].items():
            selected_ids[table].update(int(value) for value in ids)

    indexed = catalog_index(catalog)
    passive_by_id = indexed.get("passive_buffs", {})
    passive_ids = {int(row["id"]) for row in contract["passive_rows"]}
    if not passive_ids.issubset(passive_by_id):
        raise RuntimeError(
            f"Catalog is missing passive ids {sorted(passive_ids-set(passive_by_id))}"
        )
    passive_buff_ids = {int(passive_by_id[value]["buff_id"]) for value in passive_ids}
    selected_ids["passive_buffs"].update(passive_ids)
    selected_ids["buffs"].update(passive_buff_ids)
    selected_ids["tagged_buffs"].update(
        int(row["id"])
        for row in catalog["tables"].get("tagged_buffs", [])
        if int(row["buff_id"]) in passive_buff_ids
    )

    selected: dict[str, list[dict[str, Any]]] = {}
    for table, ids in sorted(selected_ids.items()):
        missing = ids.difference(indexed.get(table, {}))
        if missing:
            raise RuntimeError(f"Catalog table {table} is missing ids {sorted(missing)}")
        selected[table] = [indexed[table][row_id] for row_id in sorted(ids)]

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
        raise RuntimeError(f"Enabled slice reaches pending primitives: {pending}")

    return selected, {
        "enabled_skill_ids": enabled,
        "quarantined_skill_ids": quarantined,
        "passive_ids": sorted(passive_ids),
        "passive_buff_ids": sorted(passive_buff_ids),
        "selected_table_ids": {
            table: sorted(ids) for table, ids in sorted(selected_ids.items())
        },
        "root_status": {
            str(skill_id): {
                "status": str(statuses[skill_id]["status"]),
                "reason": str(statuses[skill_id]["reason"]),
            }
            for skill_id in sorted(statuses)
        },
    }


def extend_interaction_doodad_closure(
    selected: dict[str, list[dict[str, Any]]],
    selection: dict[str, Any],
    catalog: dict[str, Any],
    ability_id: int,
) -> dict[str, Any]:
    """Add AA8 doodad roots/phases reached by native InteractionEffect rows.

    Doodad descriptors live in the native game11 cached stream, not in the
    decrypted client compact. This keeps the specialization builder generic:
    any selected InteractionEffect with a doodad_id receives the same native
    presentation closure without a skill-specific allow-list.
    """
    doodad_ids = {
        int(row.get("doodad_id") or 0)
        for row in selected.get("interaction_effects", [])
        if int(row.get("doodad_id") or 0) > 0
    }
    if not doodad_ids:
        return {
            "doodad_ids": [],
            "group_ids": [],
            "func_ids": [],
            "source": None,
        }

    source = Path(catalog["sources"]["client_game_stream"]["path"]).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = source.read_bytes()
    decoded: dict[str, list[dict[str, Any]]] = {}
    decoder_evidence: dict[str, Any] = {}
    for table in (
        "doodad_almighties",
        "doodad_func_groups",
        "doodad_funcs",
        "doodad_phase_funcs",
        "doodad_func_clouts",
        "doodad_func_timers",
        "doodad_func_finals",
    ):
        decoded[table], decoder_evidence[table] = _decode_result(
            payload, table, DOODAD_RESULT_SPECS[table]
        )

    all_roots = [
        row for row in decoded["doodad_almighties"]
        if int(row["id"]) in doodad_ids
    ]
    found_ids = {int(row["id"]) for row in all_roots}
    missing_ids = doodad_ids.difference(found_ids)
    if missing_ids:
        raise RuntimeError(
            f"Native interaction doodads are missing from game11: {sorted(missing_ids)}"
        )

    all_groups = [
        row for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) in doodad_ids
    ]
    all_group_ids = {int(row["id"]) for row in all_groups}
    pending_funcs = [
        row for row in decoded["doodad_funcs"]
        if int(row["doodad_func_group_id"]) in all_group_ids
    ]
    interactive_group_ids = {
        int(row["doodad_func_group_id"]) for row in pending_funcs
    }
    all_phase_funcs = [
        row for row in decoded["doodad_phase_funcs"]
        if int(row["doodad_func_group_id"]) in all_group_ids
    ]
    unsupported_phase_group_ids = {
        int(row["doodad_func_group_id"])
        for row in all_phase_funcs
        if str(row["actual_func_type"])
        not in {"DoodadFuncClout", "DoodadFuncTimer", "DoodadFuncFinal"}
    }
    functional_group_ids = interactive_group_ids | unsupported_phase_group_ids
    functional_doodad_ids = {
        int(row["doodad_almighty_id"]) for row in all_groups
        if int(row["id"]) in functional_group_ids
    }

    # Skill-created presentation doodads with no server functions are a closed
    # native slice. Doodads that reach a DoodadFunc remain isolated until their
    # concrete function descriptor is decoded; importing a partial functional
    # doodad would create a silent runtime fallback.
    materialized_doodad_ids = doodad_ids.difference(functional_doodad_ids)
    roots = [
        row for row in all_roots
        if int(row["id"]) in materialized_doodad_ids
    ]
    groups = [
        row for row in all_groups
        if int(row["doodad_almighty_id"]) in materialized_doodad_ids
    ]
    group_ids = {int(row["id"]) for row in groups}
    funcs: list[dict[str, Any]] = []
    phase_funcs = [
        row for row in all_phase_funcs
        if int(row["doodad_func_group_id"]) in group_ids
    ]
    clout_ids = {
        int(row["actual_func_id"])
        for row in phase_funcs
        if str(row["actual_func_type"]) == "DoodadFuncClout"
    }
    clouts = [
        row for row in decoded["doodad_func_clouts"]
        if int(row["id"]) in clout_ids
    ]
    missing_clout_ids = clout_ids.difference(int(row["id"]) for row in clouts)
    if missing_clout_ids:
        raise RuntimeError(
            f"Native doodad clout descriptors are missing: {sorted(missing_clout_ids)}"
        )
    timer_ids = {
        int(row["actual_func_id"])
        for row in phase_funcs
        if str(row["actual_func_type"]) == "DoodadFuncTimer"
    }
    timers = [
        row for row in decoded["doodad_func_timers"]
        if int(row["id"]) in timer_ids
    ]
    missing_timer_ids = timer_ids.difference(int(row["id"]) for row in timers)
    if missing_timer_ids:
        raise RuntimeError(
            f"Native doodad timer descriptors are missing: {sorted(missing_timer_ids)}"
        )
    final_ids = {
        int(row["actual_func_id"])
        for row in phase_funcs
        if str(row["actual_func_type"]) == "DoodadFuncFinal"
    }
    finals = [
        row for row in decoded["doodad_func_finals"]
        if int(row["id"]) in final_ids
    ]
    missing_final_ids = final_ids.difference(int(row["id"]) for row in finals)
    if missing_final_ids:
        raise RuntimeError(
            f"Native doodad final descriptors are missing: {sorted(missing_final_ids)}"
        )

    native_buff_closure: dict[str, list[dict[str, Any]]] = {}
    native_buff_diagnostics: dict[str, Any] = {}
    if clouts:
        relationships = extract_client_relationships(source)
        native, _ = extract_native_tables(source)
        client_compact = Path(catalog["sources"]["client_compact"]["path"]).resolve()
        if not client_compact.is_file():
            raise FileNotFoundError(client_compact)
        client = open_read_only(client_compact)
        try:
            reference_resolution = catalog["reference_resolution"]
            native_buff_closure, native_buff_diagnostics = build_closure(
                client,
                None,
                relationships,
                native,
                ability_id=ability_id,
                effect_type_map_override=reference_resolution["effect_types"],
                plot_type_map_override=reference_resolution["plot_types"],
                reference_evidence_override=reference_resolution["evidence"],
                root_skill_ids=set(),
                root_buff_ids={
                    int(row["buff_id"])
                    for row in clouts
                    if int(row.get("buff_id") or 0) > 0
                },
                include_ability_passives=False,
            )
        finally:
            client.close()

        blocking_diagnostics = {
            key: native_buff_diagnostics.get(key)
            for key in (
                "unresolved_effect_dependencies",
                "unresolved_plot_types",
                "animation_ids_missing",
                "controller_ids_missing",
                "projectile_ids_missing",
                "aoe_shape_ids_missing",
            )
            if native_buff_diagnostics.get(key)
        }
        if blocking_diagnostics:
            raise RuntimeError(
                f"Native doodad clout buff closure is incomplete: {blocking_diagnostics}"
            )

        shape_by_id = {
            int(row["id"]): row for row in native.get("aoe_shapes", [])
        }
        shape_ids = {
            int(row["aoe_shape_id"])
            for row in clouts
            if int(row.get("aoe_shape_id") or 0) > 0
        }
        missing_shape_ids = shape_ids.difference(shape_by_id)
        if missing_shape_ids:
            raise RuntimeError(
                f"Native doodad clout shapes are missing: {sorted(missing_shape_ids)}"
            )
        native_buff_closure.setdefault("aoe_shapes", []).extend(
            shape_by_id[shape_id] for shape_id in sorted(shape_ids)
        )

    def merge_rows(table: str, rows: list[dict[str, Any]]) -> None:
        merged = {int(row["id"]): row for row in selected.get(table, [])}
        for row in rows:
            row_id = int(row["id"])
            previous = merged.get(row_id)
            if previous is not None and previous != row:
                raise RuntimeError(f"Conflicting selected row {table}.{row_id}")
            merged[row_id] = row
        selected[table] = [merged[row_id] for row_id in sorted(merged)]
        selection["selected_table_ids"][table] = sorted(merged)

    for table, rows in (
        ("doodad_almighties", roots),
        ("doodad_func_groups", groups),
        ("doodad_funcs", funcs),
        ("doodad_phase_funcs", phase_funcs),
        ("doodad_func_clouts", clouts),
        ("doodad_func_timers", timers),
        ("doodad_func_finals", finals),
    ):
        merge_rows(table, rows)
    for table, rows in native_buff_closure.items():
        merge_rows(table, rows)

    return {
        "doodad_ids": sorted(doodad_ids),
        "materialized_doodad_ids": sorted(materialized_doodad_ids),
        "functional_doodad_ids_pending": sorted(functional_doodad_ids),
        "group_ids": sorted(group_ids),
        "func_ids": sorted(int(row["id"]) for row in funcs),
        "func_ids_pending": sorted(int(row["id"]) for row in pending_funcs),
        "phase_func_ids": sorted(int(row["id"]) for row in phase_funcs),
        "clout_ids": sorted(clout_ids),
        "timer_ids": sorted(timer_ids),
        "final_ids": sorted(final_ids),
        "unsupported_phase_group_ids": sorted(unsupported_phase_group_ids),
        "native_buff_closure": {
            table: sorted(int(row["id"]) for row in rows)
            for table, rows in sorted(native_buff_closure.items())
        },
        "native_buff_diagnostics": native_buff_diagnostics,
        "source": {"path": str(source), "sha256": sha256_file(source)},
        "decoder_evidence": decoder_evidence,
    }


def normalized_row_matches(
    connection: sqlite3.Connection, table: str, source: dict[str, Any]
) -> bool:
    expected, _ = normalize(table, source)
    available = columns(connection, table)
    names = [name for name in expected if name in available]
    quoted = ",".join('"' + name.replace('"', '""') + '"' for name in names)
    actual = connection.execute(
        f'SELECT {quoted} FROM "{table}" WHERE id=?', (int(source["id"]),)
    ).fetchone()
    return actual is not None and tuple(actual) == tuple(expected[name] for name in names)


def verify_runtime(
    connection: sqlite3.Connection,
    contract: dict[str, Any],
    selected: dict[str, list[dict[str, Any]]],
    selection: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    for table, rows in selected.items():
        for row in rows:
            if not normalized_row_matches(connection, table, row):
                errors.append(f"{table}.{row['id']} differs from selected AA8 row")

    roots = [int(value) for value in contract["root_skill_ids"]]
    placeholders = ",".join("?" for _ in roots)
    actual_roots = [
        int(row[0])
        for row in connection.execute(
            f"SELECT id FROM skills WHERE id IN ({placeholders}) ORDER BY id", tuple(roots)
        )
    ]
    if actual_roots != roots:
        errors.append(f"Runtime root membership differs: {actual_roots}")

    expected_status_counts: dict[str, int] = defaultdict(int)
    for row in selection["root_status"].values():
        expected_status_counts[str(row["status"])] += 1
    actual_status_counts = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            f"SELECT status,COUNT(*) FROM native_combat_skill_status "
            f"WHERE skill_id IN ({placeholders}) GROUP BY status ORDER BY status",
            tuple(roots),
        )
    }
    if actual_status_counts != dict(expected_status_counts):
        errors.append(
            f"Status counts differ: {actual_status_counts} != {dict(expected_status_counts)}"
        )

    quarantined = [int(value) for value in selection["quarantined_skill_ids"]]
    quarantined_effects = 0
    if quarantined:
        qmarks = ",".join("?" for _ in quarantined)
        quarantined_effects = int(
            connection.execute(
                f"SELECT COUNT(*) FROM skill_effects WHERE skill_id IN ({qmarks})",
                tuple(quarantined),
            ).fetchone()[0]
        )
        if quarantined_effects:
            errors.append(f"Quarantined roots retain {quarantined_effects} skill_effect rows")

    passive_ids = [int(value) for value in selection["passive_ids"]]
    qmarks = ",".join("?" for _ in passive_ids)
    actual_passives = [
        tuple(row)
        for row in connection.execute(
            f"SELECT id,req_points,skill_points FROM passive_buffs "
            f"WHERE id IN ({qmarks}) ORDER BY id",
            tuple(passive_ids),
        )
    ]
    if len(actual_passives) != 6 or any(int(row[2]) != 0 for row in actual_passives):
        errors.append(f"Passive point policy differs: {actual_passives}")

    missing_passive_buffs = int(
        connection.execute(
            "SELECT COUNT(*) FROM passive_buffs p LEFT JOIN buffs b ON b.id=p.buff_id "
            "WHERE p.ability_id=? AND b.id IS NULL",
            (int(contract["ability_id"]),),
        ).fetchone()[0]
    )
    if missing_passive_buffs:
        errors.append(f"Passives with missing buff templates: {missing_passive_buffs}")

    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite checks failed: quick={quick}, integrity={integrity}")
    if errors:
        raise RuntimeError("\n".join(errors[:100]))
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "enabled_roots": len(selection["enabled_skill_ids"]),
        "quarantined_roots": len(quarantined),
        "quarantined_skill_effect_rows": quarantined_effects,
        "visible_native_roots": len(contract["visible_skill_ids"]),
        "passive_roots": len(actual_passives),
        "passive_policy": "skill_points_zero_req_points_native_gate",
    }


def build_once(
    carrier: Path,
    output: Path,
    contract: dict[str, Any],
    selected: dict[str, list[dict[str, Any]]],
    selection: dict[str, Any],
    *,
    verify: bool,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    if output.resolve() == carrier.resolve():
        raise ValueError("Output must not replace COMPACT_DB/runtime carrier")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(carrier, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        quarantined = [int(value) for value in selection["quarantined_skill_ids"]]
        pruned = 0
        if quarantined:
            qmarks = ",".join("?" for _ in quarantined)
            cursor = connection.execute(
                f"DELETE FROM skill_effects WHERE skill_id IN ({qmarks})",
                tuple(quarantined),
            )
            pruned = max(int(cursor.rowcount), 0)
        merge = {
            table: upsert_rows(connection, table, rows)
            for table, rows in sorted(selected.items())
        }
        ability_id = int(contract["ability_id"])
        provenance = f"aa8_specialization_graph_v1:{contract['slug']}"
        connection.executemany(
            "INSERT INTO native_combat_skill_status(skill_id,ability_id,status,reason,provenance) "
            "VALUES(?,?,?,?,?) ON CONFLICT(skill_id) DO UPDATE SET "
            "ability_id=excluded.ability_id,status=excluded.status,reason=excluded.reason,"
            "provenance=excluded.provenance",
            [
                (
                    skill_id,
                    ability_id,
                    contract["audit"][skill_id]["status"],
                    contract["audit"][skill_id]["reason"],
                    provenance,
                )
                for skill_id in contract["root_skill_ids"]
            ],
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS specialization_reconstruction_metadata("
            "ability_id INTEGER NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL,"
            "provenance TEXT NOT NULL,PRIMARY KEY(ability_id,key))"
        )
        metadata = {
            "client_build": CLIENT_BUILD,
            "graph_sha256": contract["graph_sha256"],
            "root_skill_count": str(len(contract["root_skill_ids"])),
            "visible_native_root_count": str(len(contract["visible_skill_ids"])),
            "passive_count": str(len(contract["passive_rows"])),
            "wiki_authority": "corroboration_only",
        }
        connection.executemany(
            "INSERT INTO specialization_reconstruction_metadata"
            "(ability_id,key,value,provenance) VALUES(?,?,?,?) "
            "ON CONFLICT(ability_id,key) DO UPDATE SET "
            "value=excluded.value,provenance=excluded.provenance",
            [
                (ability_id, key, value, provenance)
                for key, value in sorted(metadata.items())
            ],
        )
        connection.commit()
        verification = (
            verify_runtime(connection, contract, selected, selection) if verify else None
        )
        connection.execute("VACUUM")
        connection.close()
    except Exception:
        connection.close()
        output.unlink(missing_ok=True)
        raise
    return merge, verification, {"quarantined_skill_effect_rows_pruned": pruned}


def resolve_inputs(args: argparse.Namespace) -> tuple[int, str, str, Path, Path, Path]:
    ability_id, name, slug = resolve_ability(args.ability)
    carrier = (
        args.runtime_carrier
        if args.runtime_carrier is not None
        else Path(env_value(args.env_file, "COMPACT_DB"))
    ).resolve()
    graph = (
        args.graph
        if args.graph is not None
        else configured_output_dir() / f"{slug}-specialization-graph-v1.sqlite3"
    ).resolve()
    graph_manifest = (
        args.graph_manifest
        if args.graph_manifest is not None
        else graph.with_name(graph.name.removesuffix(".sqlite3") + ".manifest.json")
    ).resolve()
    return ability_id, name, slug, carrier, graph, graph_manifest


def build(args: argparse.Namespace) -> dict[str, Any]:
    ability_id, name, slug, carrier, graph, graph_manifest = resolve_inputs(args)
    for path in (carrier, graph, graph_manifest, args.catalog):
        if not path.is_file():
            raise FileNotFoundError(path)
    contract = validate_graph(
        graph, graph_manifest, ability_id, name, slug, args.catalog
    )
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if "historical_3_0" in json.dumps(catalog.get("provenance", {})):
        raise RuntimeError("Historical combat provenance is forbidden")
    selected, selection = select_runtime_rows(contract, catalog)
    interaction_doodads = extend_interaction_doodad_closure(
        selected, selection, catalog, ability_id
    )

    output = args.output.resolve()
    merge, verification, mutations = build_once(
        carrier, output, contract, selected, selection, verify=args.verify
    )
    determinism = None
    if args.determinism_output is not None:
        second = args.determinism_output.resolve()
        if second in {carrier, output}:
            raise ValueError("Determinism output must be distinct from carrier and output")
        _, second_verification, _ = build_once(
            carrier, second, contract, selected, selection, verify=args.verify
        )
        first_sha = sha256_file(output)
        second_sha = sha256_file(second)
        if first_sha != second_sha:
            raise RuntimeError(
                f"Runtime builds are not deterministic: {first_sha} != {second_sha}"
            )
        determinism = {
            "status": "confirmed",
            "first": {"path": str(output), "sha256": first_sha},
            "second": {"path": str(second), "sha256": second_sha},
            "second_verification": second_verification,
        }

    manifest = {
        "format_version": 1,
        "client_build": CLIENT_BUILD,
        "ability": {"id": ability_id, "name": name, "slug": slug},
        "authority": {
            "aa8_sqlite_graph": "runtime_contract",
            "wiki": "corroboration_only",
            "historical_gameplay_rows": False,
        },
        "sources": {
            "runtime_carrier": {
                "path": str(carrier),
                "sha256": sha256_file(carrier),
                "resolution": f"COMPACT_DB from {args.env_file.resolve()}"
                if args.runtime_carrier is None
                else "explicit argument",
            },
            "graph": {"path": str(graph), "sha256": contract["graph_sha256"]},
            "graph_manifest": {
                "path": str(graph_manifest),
                "sha256": contract["graph_manifest_sha256"],
            },
            "native_combat_catalog": {
                "path": str(args.catalog.resolve()),
                "sha256": sha256_file(args.catalog),
            },
        },
        "consumed_graph_rows": contract["consumed_graph_rows"],
        "selection": selection,
        "interaction_doodad_closure": interaction_doodads,
        "merge": merge,
        "mutations": mutations,
        "reconstruction_test_contract": {
            "total": sum(contract["test_states"].values()),
            "states": contract["test_states"],
        },
        "verification": verification,
        "determinism": determinism,
        "output": {"path": str(output), "sha256": sha256_file(output)},
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(canonical_json(manifest), encoding="utf-8")
    result = {
        "ability": manifest["ability"],
        "output": manifest["output"],
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256_file(args.manifest),
        "selected_rows": {
            table: len(rows) for table, rows in sorted(selected.items())
        },
        "verification": verification,
        "determinism": determinism,
    }
    print(canonical_json(result))
    return manifest


def main() -> int:
    build(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
