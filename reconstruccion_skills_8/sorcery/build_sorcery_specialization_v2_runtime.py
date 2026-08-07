#!/usr/bin/env python3
"""Reconstruct the two AA8 Sorcery roots omitted from the native skills result."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NATIVE_COMBAT = ROOT / "reconstruccion_skills_8" / "native_combat"
NATIVE_CATALOG = NATIVE_COMBAT / "generated" / "native-combat-catalog-v1.json"
sys.path.insert(0, str(NATIVE_COMBAT))

from build_native_combat_runtime import columns, normalize, sha256_file, upsert_rows  # noqa: E402


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
ROOT_IDS = (10151, 10153)
EXPECTED_SKILL_EFFECTS = {
    10151: (271, 272, 44888),
    10153: (53089, 65323),
}
# These rows are reachable from the complete AA8 Sorcery graph but were absent
# from the carrier produced by the earlier visible-root closure.  They are not
# AA10 balance imports: every row is a confirmed native AA8 row in the
# consolidated knowledge database.
REQUIRED_SORCERY_DAMAGE_EFFECTS = (
    9679,
    9680,
    9843,
    9860,
    9875,
    11361,
    11689,
    11690,
    12133,
    12134,
    12135,
    12136,
    12137,
    12937,
)
REQUIRED_NATIVE_CLOSURE = {
    "physical_explosion_effects": {
        190: "effect_detail:physical_explosion_effects:190",
    },
    "skill_controllers": {
        11660: "skill_controller:11660",
        11661: "skill_controller:11661",
    },
    "interaction_effects": {
        7406: "effect_detail:interaction_effects:7406",
        7407: "effect_detail:interaction_effects:7407",
    },
    "projectiles": {
        1126: "projectile:1126",
        1131: "projectile:1131",
    },
    "aoe_shapes": {
        16482: "aoe_shape:16482",
        16501: "aoe_shape:16501",
    },
}
CACHED_AA8_DOODADS = (13406, 13407, 14623, 14666)
AA10_STRUCTURAL_CANDIDATES = {
    "doodad_func_groups": (38626, 38627, 38628, 38629, 38630, 43090, 43245),
    "doodad_phase_funcs": (49136, 49137, 49339, 49340, 49913, 55165, 55330),
    "doodad_func_clouts": (4116, 4121),
    "doodad_func_timers": (16372, 16373),
    "doodad_func_finals": (5304, 5305, 5320),
}
PROMOTED_SORCERY_SKILLS = (11939, 36477, 36478, 39674)
EXPECTED_HASHES = {
    "carrier": "780D08ECD6A3FB8294EC7B9305C6ADC9AFF558D951F83FF96FE928D48DD0195F",
    "knowledge": "92CDF5D1EB16DAF0C4D5ABFCB80B510DFDF827708D4F8087235CCFACE3CE3C4F",
    "crosswalk": "44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71",
    "aa10": "87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F",
    "evidence": "6E830D449939C420FA7F7A30104DB80AF433CC921B08D071BBD3646482C9092D",
    "catalog": "9849E3CF5C52702CC0CEB71B9DBBFB343E29880924DA4AFF13C3C5F33B2DD027",
}
DOSSIER_HASHES = {
    10151: "6DFB8EEDF555D6A9C82F8A4A84AD9BEF99B554953C21D6B4C0AB002FBB96E85F",
    10153: "56E6FAED6468F5AA092EE97011EFC20E2C59329FEF87B6776ECC0C228080C4AC",
}
EXECUTABLE_TABLES = {
    "aoe_shapes",
    "buff_effects",
    "buffs",
    "combat_resource_effects",
    "damage_effects",
    "effects",
    "extend_charge_effects",
    "interaction_effects",
    "physical_explosion_effects",
    "plot_aoe_conditions",
    "plot_conditions",
    "plot_effects",
    "plot_event_conditions",
    "plot_events",
    "plot_next_events",
    "plots",
    "skill_effects",
    "skill_controllers",
    "special_effects",
    "projectiles",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--knowledge", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--aa10", required=True, type=Path)
    parser.add_argument("--dossier-dir", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def validate_source(path: Path, expected: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Unexpected source SHA-256 for {path}: {actual}")
    return {"path": str(path.resolve()), "sha256": actual}


def dossier_keys(path: Path, skill_id: int) -> tuple[set[str], dict[str, Any]]:
    expected = DOSSIER_HASHES[skill_id]
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Unexpected dossier SHA-256 for {skill_id}: {actual}")
    dossier = json.loads(path.read_text(encoding="utf-8"))
    if dossier["root"]["entity_key"] != f"skill:{skill_id}":
        raise RuntimeError(f"Dossier root mismatch for {skill_id}")
    keys = {
        str(node["entity_key"])
        for node in dossier["graph"]["nodes"]
        if node.get("path_importance") in ("required", "contextual")
    }
    return keys, {
        "path": str(path.resolve()),
        "sha256": actual,
        "static_root_state": next(
            node["state"]
            for node in dossier["graph"]["nodes"]
            if node["entity_key"] == f"skill:{skill_id}"
        ),
    }


def exact_native_row(
    knowledge: sqlite3.Connection, entity_key: str
) -> tuple[str, dict[str, Any]] | None:
    candidates = []
    for row in knowledge.execute(
        "SELECT source_table,state,row_json FROM native_rows WHERE entity_key=?",
        (entity_key,),
    ):
        try:
            payload = json.loads(str(row["row_json"]))
        except json.JSONDecodeError:
            continue
        table = str(row["source_table"])
        if table not in EXECUTABLE_TABLES or "id" not in payload:
            continue
        candidates.append((len(payload), table, payload, str(row["state"])))
    if not candidates:
        return None
    _, table, payload, _ = max(candidates, key=lambda value: value[0])
    return table, payload


def plot_3096_keys(knowledge: sqlite3.Connection) -> set[str]:
    keys = {"plot:3096"}
    event_keys = {
        str(row["src_entity_key"])
        for row in knowledge.execute(
            "SELECT src_entity_key FROM relations WHERE dst_entity_key='plot:3096' "
            "AND relation='references_plot'"
        )
    }
    keys.update(event_keys)
    for event_key in sorted(event_keys):
        keys.update(
            str(row["src_entity_key"])
            for row in knowledge.execute(
                "SELECT src_entity_key FROM relations WHERE dst_entity_key=? "
                "AND relation='references_plot_event'",
                (event_key,),
            )
        )

    frontier = set(keys)
    for _ in range(6):
        next_keys = set()
        for key in sorted(frontier):
            next_keys.update(
                str(row["dst_entity_key"])
                for row in knowledge.execute(
                    "SELECT dst_entity_key FROM relations WHERE src_entity_key=? "
                    "AND state IN ('confirmed','tombstone')",
                    (key,),
                )
            )
        next_keys.difference_update(keys)
        if not next_keys:
            break
        keys.update(next_keys)
        frontier = next_keys
    return keys


def native_rows(
    knowledge: sqlite3.Connection, keys: set[str]
) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for key in sorted(keys):
        result = exact_native_row(knowledge, key)
        if result is None:
            continue
        table, payload = result
        selected[table][int(payload["id"])] = payload
    rows = {
        table: [by_id[row_id] for row_id in sorted(by_id)]
        for table, by_id in sorted(selected.items())
    }
    for skill_id, expected in EXPECTED_SKILL_EFFECTS.items():
        actual = tuple(
            int(row["id"])
            for row in rows.get("skill_effects", [])
            if int(row.get("skill_id", 0)) == skill_id
        )
        if actual != expected:
            raise RuntimeError(f"AA8 effect closure mismatch for {skill_id}: {actual}")
    return rows


def extend_selected_rows(
    selected: dict[str, list[dict[str, Any]]],
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    by_id = {int(row["id"]): row for row in selected.get(table, [])}
    by_id.update({int(row["id"]): row for row in rows})
    selected[table] = [by_id[row_id] for row_id in sorted(by_id)]


def materialize_required_aa8_closure(
    knowledge: sqlite3.Connection,
    selected: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    evidence: dict[str, Any] = {"native_rows": {}, "cached_doodads": {}}
    for expected_table, keys in REQUIRED_NATIVE_CLOSURE.items():
        rows = []
        for expected_id, entity_key in sorted(keys.items()):
            result = exact_native_row(knowledge, entity_key)
            if result is None:
                raise RuntimeError(f"Missing required AA8 native row {entity_key}")
            table, payload = result
            if table != expected_table or int(payload["id"]) != expected_id:
                raise RuntimeError(
                    f"AA8 native row mismatch for {entity_key}: {table}.{payload.get('id')}"
                )
            rows.append(payload)
        extend_selected_rows(selected, expected_table, rows)
        evidence["native_rows"][expected_table] = sorted(keys)

    cached_rows = {}
    for row in knowledge.execute(
        "SELECT row_index,row_json FROM cached_result_rows "
        "WHERE query_key='legacy:item-forensics:query:15' ORDER BY row_index"
    ):
        payload = json.loads(str(row["row_json"]))
        row_id = int(payload.get("id", 0))
        if row_id in CACHED_AA8_DOODADS:
            cached_rows[row_id] = payload
            evidence["cached_doodads"][str(row_id)] = {
                "query_key": "legacy:item-forensics:query:15",
                "row_index": int(row["row_index"]),
                "name": payload.get("name"),
            }
    if tuple(sorted(cached_rows)) != CACHED_AA8_DOODADS:
        raise RuntimeError(f"Missing AA8 cached doodads: {sorted(cached_rows)}")
    expected_names = {
        13406: "Wave Gods' Whip",
        13407: "Wave Gods' Whip",
        14623: "Magic Circle",
        14666: "Magic Circle",
    }
    for row_id, expected_name in expected_names.items():
        if str(cached_rows[row_id].get("name")) != expected_name:
            raise RuntimeError(
                f"AA8 cached Sorcery doodad identity changed for {row_id}"
            )
    extend_selected_rows(
        selected,
        "doodad_almighties",
        [cached_rows[row_id] for row_id in CACHED_AA8_DOODADS],
    )
    return evidence


def aa10_structural_candidate_rows(
    aa10: sqlite3.Connection,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    expected = {
        "doodad_func_groups": {
            38626: {"doodad_almighty_id": 13406, "doodad_func_group_kind_id": 1},
            38627: {"doodad_almighty_id": 13406, "doodad_func_group_kind_id": 2},
            38628: {"doodad_almighty_id": 13406, "doodad_func_group_kind_id": 2},
            38629: {"doodad_almighty_id": 13406, "doodad_func_group_kind_id": 2},
            38630: {"doodad_almighty_id": 13407, "doodad_func_group_kind_id": 1},
            43090: {"doodad_almighty_id": 14623, "doodad_func_group_kind_id": 1},
            43245: {"doodad_almighty_id": 14666, "doodad_func_group_kind_id": 1},
        },
        "doodad_phase_funcs": {
            49136: {
                "doodad_func_group_id": 38626,
                "actual_func_type": "DoodadFuncTimer",
                "actual_func_id": 16372,
            },
            49137: {
                "doodad_func_group_id": 38627,
                "actual_func_type": "DoodadFuncTimer",
                "actual_func_id": 16373,
            },
            49339: {
                "doodad_func_group_id": 38630,
                "actual_func_type": "DoodadFuncFinal",
                "actual_func_id": 5304,
            },
            49340: {
                "doodad_func_group_id": 38629,
                "actual_func_type": "DoodadFuncFinal",
                "actual_func_id": 5305,
            },
            49913: {
                "doodad_func_group_id": 38628,
                "actual_func_type": "DoodadFuncFinal",
                "actual_func_id": 5320,
            },
            55165: {
                "doodad_func_group_id": 43090,
                "actual_func_type": "DoodadFuncClout",
                "actual_func_id": 4116,
            },
            55330: {
                "doodad_func_group_id": 43245,
                "actual_func_type": "DoodadFuncClout",
                "actual_func_id": 4121,
            },
        },
        "doodad_func_clouts": {
            4116: {
                "duration": 20000,
                "tick": 0,
                "target_relation_id": 1,
                "buff_id": 25646,
                "projectile_id": 1126,
                "aoe_shape_id": 16482,
                "target_no_buff_tag_id": 805,
                "use_origin_source": "t",
                "check_target_tag_src": "f",
            },
            4121: {
                "duration": 20000,
                "tick": 0,
                "target_relation_id": 3,
                "buff_id": 25647,
                "projectile_id": 1131,
                "aoe_shape_id": 16501,
                "target_buff_tag_id": 4482,
                "target_no_buff_tag_id": 805,
                "use_origin_source": "t",
                "check_target_tag_src": "t",
            },
        },
        "doodad_func_timers": {
            16372: {"delay": 1000, "next_phase": 38627},
            16373: {"delay": 1000, "next_phase": 38628},
        },
        "doodad_func_finals": {
            5304: {"after": 5000, "respawn": "f"},
            5305: {"after": 1000, "respawn": "f"},
            5320: {"after": 1000, "respawn": "f"},
        },
    }
    selected: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, Any] = {}
    for table, ids in AA10_STRUCTURAL_CANDIDATES.items():
        rows = []
        for row_id in ids:
            row = aa10.execute(f'SELECT * FROM "{table}" WHERE id=?', (row_id,)).fetchone()
            if row is None:
                raise RuntimeError(f"Missing AA10 structural candidate {table}.{row_id}")
            payload = dict(row)
            for name, value in expected[table][row_id].items():
                if payload.get(name) != value:
                    raise RuntimeError(
                        f"AA10 structural gate mismatch {table}.{row_id}.{name}: "
                        f"{payload.get(name)!r} != {value!r}"
                    )
            rows.append(payload)
        selected[table] = rows
        evidence[table] = {
            "ids": list(ids),
            "classification": "aa10_structural_candidate_anchored_by_aa8_identity_closure",
            "automatic_balance_authority": False,
        }
    return selected, evidence


def promoted_catalog_rows(
    catalog: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    table_maps = {
        table: {int(row["id"]): row for row in rows}
        for table, rows in catalog["tables"].items()
        if rows and isinstance(rows[0], dict) and "id" in rows[0]
    }
    selected: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    evidence: dict[str, Any] = {}
    for skill_id in PROMOTED_SORCERY_SKILLS:
        table_ids = catalog["skill_table_ids"].get(str(skill_id))
        if not table_ids:
            raise RuntimeError(f"Native catalog lacks promoted Sorcery skill {skill_id}")
        counts = {}
        for table, ids in sorted(table_ids.items()):
            if not ids or table == "passive_buffs":
                continue
            if table not in table_maps:
                raise RuntimeError(f"Native catalog lacks table payload {table}")
            for row_id in ids:
                row = table_maps[table].get(int(row_id))
                if row is None:
                    raise RuntimeError(
                        f"Native catalog lacks {table}.{row_id} for promoted skill {skill_id}"
                    )
                selected[table][int(row_id)] = row
            counts[table] = len(ids)
        evidence[str(skill_id)] = {
            "former_blocker": "ResetAoeDiminishingEffect backend no-op",
            "resolution": "handler_implemented_and_full_aa8_catalog_closure_restored",
            "table_counts": counts,
        }
    return (
        {
            table: [rows[row_id] for row_id in sorted(rows)]
            for table, rows in sorted(selected.items())
        },
        evidence,
    )


def validate_crosswalk(connection: sqlite3.Connection) -> dict[str, Any]:
    root_rows = list(connection.execute(
        "SELECT aa10_id,classification FROM row_comparisons "
        "WHERE table_name='skills' AND aa10_id IN ('10151','10153') ORDER BY aa10_id"
    ))
    if [tuple(row) for row in root_rows] != [("10151", "aa10_only"), ("10153", "aa10_only")]:
        raise RuntimeError(f"Unexpected root crosswalk states: {[tuple(row) for row in root_rows]}")

    exact_effects = (233, 234, 56762, 68337, 87343)
    qmarks = ",".join("?" for _ in exact_effects)
    effect_rows = list(connection.execute(
        f"SELECT aa8_id,classification FROM row_comparisons WHERE table_name='effects' "
        f"AND aa8_id IN ({qmarks}) ORDER BY CAST(aa8_id AS INTEGER)",
        tuple(str(value) for value in exact_effects),
    ))
    if any(str(row["classification"]) != "exact_id_exact_relation" for row in effect_rows):
        raise RuntimeError("The root effect descriptors are not exact in the AA8->AA10 crosswalk")
    closure_rows: dict[str, dict[str, str]] = {}
    for table, ids in REQUIRED_NATIVE_CLOSURE.items():
        table_rows = {}
        for row_id in sorted(ids):
            row = connection.execute(
                "SELECT classification FROM row_comparisons "
                "WHERE table_name=? AND aa8_id=? AND aa10_id=?",
                (table, str(row_id), str(row_id)),
            ).fetchone()
            if row is None:
                raise RuntimeError(f"Missing crosswalk row for {table}.{row_id}")
            classification = str(row["classification"])
            if table != "projectiles" and classification != "exact_id_exact_relation":
                raise RuntimeError(
                    f"Unexpected crosswalk classification for {table}.{row_id}: {classification}"
                )
            if table == "projectiles" and classification not in (
                "exact_id_exact_relation", "stable_id_changed_properties"
            ):
                raise RuntimeError(
                    f"Unstable projectile identity for {table}.{row_id}: {classification}"
                )
            table_rows[str(row_id)] = classification
        closure_rows[table] = table_rows
    return {
        "roots": {str(row["aa10_id"]): str(row["classification"]) for row in root_rows},
        "effect_descriptors": {
            str(row["aa8_id"]): str(row["classification"]) for row in effect_rows
        },
        "required_sorcery_closure": closure_rows,
    }


def aa10_roots(connection: sqlite3.Connection, runtime: sqlite3.Connection) -> list[dict[str, Any]]:
    available = columns(runtime, "skills")
    roots = []
    for skill_id in ROOT_IDS:
        row = connection.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
        if row is None:
            raise RuntimeError(f"AA10 candidate root {skill_id} is absent")
        source = dict(row)
        result: dict[str, Any] = {}
        for name, sql_type in available.items():
            if name in source:
                value = source[name]
                if value == "t":
                    value = 1
                elif value == "f":
                    value = 0
                result[name] = value
            elif name == "need_learn":
                result[name] = 1
            else:
                result[name] = None if "TEXT" in sql_type.upper() else 0
        roots.append(result)
    return roots


def verify_native_rows(
    connection: sqlite3.Connection,
    selected: dict[str, list[dict[str, Any]]],
) -> list[str]:
    errors = []
    for table, rows in selected.items():
        available = columns(connection, table)
        for source in rows:
            expected, _ = normalize(table, source)
            names = [name for name in expected if name in available]
            actual = connection.execute(
                f'SELECT {",".join(chr(34)+name+chr(34) for name in names)} '
                f'FROM "{table}" WHERE id=?',
                (int(source["id"]),),
            ).fetchone()
            if actual is None or tuple(actual) != tuple(expected[name] for name in names):
                errors.append(f"{table}.{source['id']} differs from AA8 native row")
    return errors


def verify_runtime(
    connection: sqlite3.Connection,
    selected: dict[str, list[dict[str, Any]]],
    structural_candidates: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    errors = verify_native_rows(connection, selected)
    roots = [tuple(row) for row in connection.execute(
        "SELECT id,ability_id,ability_level,plot_id,cooldown_time,casting_time,need_learn "
        "FROM skills WHERE id IN (10151,10153) ORDER BY id"
    )]
    expected_roots = [
        (10151, 7, 25, 3096, 28000, 0, 1),
        (10153, 7, 10, None, 0, 1500, 1),
    ]
    if roots != expected_roots:
        errors.append(f"Root candidate contract mismatch: {roots}")
    for skill_id, expected in EXPECTED_SKILL_EFFECTS.items():
        actual = tuple(row[0] for row in connection.execute(
            "SELECT id FROM skill_effects WHERE skill_id=? ORDER BY id", (skill_id,)
        ))
        if actual != expected:
            errors.append(f"Skill {skill_id} effect set mismatch: {actual}")
    materialized_damage = tuple(
        int(row[0])
        for row in connection.execute(
            "SELECT id FROM damage_effects WHERE id IN ("
            + ",".join("?" for _ in REQUIRED_SORCERY_DAMAGE_EFFECTS)
            + ") ORDER BY id",
            REQUIRED_SORCERY_DAMAGE_EFFECTS,
        )
    )
    if materialized_damage != REQUIRED_SORCERY_DAMAGE_EFFECTS:
        errors.append(
            "Sorcery native damage closure mismatch: "
            f"{materialized_damage}"
        )
    required_materialized = {}
    for table, ids in {
        **{name: tuple(values) for name, values in (
            (table, rows.keys()) for table, rows in REQUIRED_NATIVE_CLOSURE.items()
        )},
        "doodad_almighties": CACHED_AA8_DOODADS,
        **AA10_STRUCTURAL_CANDIDATES,
    }.items():
        actual = tuple(
            int(row[0])
            for row in connection.execute(
                f'SELECT id FROM "{table}" WHERE id IN ('
                + ",".join("?" for _ in ids)
                + ") ORDER BY id",
                tuple(ids),
            )
        )
        expected = tuple(sorted(ids))
        if actual != expected:
            errors.append(f"Sorcery closure mismatch for {table}: {actual} != {expected}")
        required_materialized[table] = list(actual)
    shield = connection.execute(
        "SELECT cooldown_skill_id,cooldown_skill_time,duration,damage_absorption_type_id,"
        "init_min_charge,init_max_charge FROM buffs WHERE id=95"
    ).fetchone()
    if shield is None or tuple(shield) != (10153, 30000, 40000, 2, 1, 10000):
        errors.append(f"AA8 shield buff contract mismatch: {tuple(shield) if shield else None}")
    extend = connection.execute(
        "SELECT charge_buff_id,damage_type_id,dps_inc_multiplier,level_md,use_dps_charge,"
        "use_level_charge,use_percent_charge,use_current_health FROM extend_charge_effects WHERE id=1"
    ).fetchone()
    if extend is None or tuple(extend) != (95, 2, 1.5, 3.0, 1, 1, 0, 0):
        errors.append(f"AA8 ExtendCharge contract mismatch: {tuple(extend) if extend else None}")
    statuses = [tuple(row) for row in connection.execute(
        "SELECT skill_id,status FROM native_combat_skill_status "
        "WHERE skill_id IN (10151,10153,11939,36477,36478,39674) ORDER BY skill_id"
    )]
    expected_statuses = [
        (10151, "enabled"),
        (10153, "enabled"),
        (11939, "enabled"),
        (36477, "enabled"),
        (36478, "enabled"),
        (39674, "enabled"),
    ]
    if statuses != expected_statuses:
        errors.append(f"Runtime statuses mismatch: {statuses}")
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite integrity failed: {quick}/{integrity}")
    if errors:
        raise RuntimeError("\n".join(errors))
    return {
        "integrity_check": integrity,
        "quick_check": quick,
        "root_contracts": roots,
        "skill_effects": {str(key): list(value) for key, value in EXPECTED_SKILL_EFFECTS.items()},
        "sorcery_damage_effects": list(materialized_damage),
        "required_sorcery_closure": required_materialized,
        "structural_candidate_tables": sorted(structural_candidates),
        "enabled_reconstructed_skills": [row[0] for row in statuses],
        "shield_buff": list(shield),
        "extend_charge": list(extend),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "runtime_carrier": validate_source(args.runtime_carrier, EXPECTED_HASHES["carrier"]),
        "knowledge": validate_source(args.knowledge, EXPECTED_HASHES["knowledge"]),
        "crosswalk": validate_source(args.crosswalk, EXPECTED_HASHES["crosswalk"]),
        "aa10": validate_source(args.aa10, EXPECTED_HASHES["aa10"]),
        "evidence": validate_source(args.evidence, EXPECTED_HASHES["evidence"]),
        "catalog": validate_source(NATIVE_CATALOG, EXPECTED_HASHES["catalog"]),
    }
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    catalog = json.loads(NATIVE_CATALOG.read_text(encoding="utf-8"))
    observed = sorted(
        int(row["skill_id"])
        for row in evidence["observations"]
        if row["kind"] == "learn_request"
    )
    if observed != list(ROOT_IDS):
        raise RuntimeError(f"Unexpected live learn observations: {observed}")

    dossier_evidence = {}
    keys = set()
    for skill_id in ROOT_IDS:
        selected_keys, dossier = dossier_keys(
            args.dossier_dir / f"skill-{skill_id}.json", skill_id
        )
        keys.update(selected_keys)
        dossier_evidence[str(skill_id)] = dossier

    knowledge = ro(args.knowledge)
    crosswalk = ro(args.crosswalk)
    aa10 = ro(args.aa10)
    try:
        keys.update(plot_3096_keys(knowledge))
        keys.update(
            f"effect_detail:damage_effects:{effect_id}"
            for effect_id in REQUIRED_SORCERY_DAMAGE_EFFECTS
        )
        selected = native_rows(knowledge, keys)
        aa8_closure_evidence = materialize_required_aa8_closure(knowledge, selected)
        promoted_rows, promoted_evidence = promoted_catalog_rows(catalog)
        for table, rows in promoted_rows.items():
            extend_selected_rows(selected, table, rows)
        structural_candidates, structural_candidate_evidence = (
            aa10_structural_candidate_rows(aa10)
        )
        crosswalk_evidence = validate_crosswalk(crosswalk)
    finally:
        crosswalk.close()

    output = args.output.resolve()
    if output == args.runtime_carrier.resolve():
        raise ValueError("Output must not replace its runtime carrier")
    output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.runtime_carrier, output)
    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        roots = aa10_roots(aa10, connection)
        merge = {"skills": upsert_rows(connection, "skills", roots)}
        for table, rows in selected.items():
            merge[table] = upsert_rows(connection, table, rows)
        for table, rows in structural_candidates.items():
            merge[table] = upsert_rows(connection, table, rows)
        for table, rows in evidence["resource_native_stream"]["rows"].items():
            merge[table] = upsert_rows(connection, table, rows)
        connection.executemany(
            "INSERT INTO native_combat_skill_status(skill_id,ability_id,status,reason,provenance) "
            "VALUES(?,7,'enabled',?,?) ON CONFLICT(skill_id) DO UPDATE SET "
            "ability_id=excluded.ability_id,status=excluded.status,reason=excluded.reason,"
            "provenance=excluded.provenance",
            [
                (
                    skill_id,
                    "AA8 live client requested the omitted root; AA10 supplies only the root row, "
                    "while the executable closure is exact AA8 native data",
                    "aa8_sorcery_v4_live_packet_plus_aa10_root_crosswalk_plus_aa8_closure",
                )
                for skill_id in ROOT_IDS
            ],
        )
        connection.executemany(
            "INSERT INTO native_combat_skill_status(skill_id,ability_id,status,reason,provenance) "
            "VALUES(?,7,'enabled',?,?) ON CONFLICT(skill_id) DO UPDATE SET "
            "ability_id=excluded.ability_id,status=excluded.status,reason=excluded.reason,"
            "provenance=excluded.provenance",
            [
                (
                    skill_id,
                    "Former ResetAoeDiminishingEffect no-op is implemented; full AA8 native "
                    "executable closure restored",
                    "aa8_sorcery_v4_promoted_after_backend_semantics_reconstruction",
                )
                for skill_id in PROMOTED_SORCERY_SKILLS
            ],
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS sorcery_reconstruction_v4_metadata("
            "key TEXT PRIMARY KEY,value TEXT NOT NULL,provenance TEXT NOT NULL)"
        )
        metadata = {
            "client_build": CLIENT_BUILD,
            "root_authority": "runtime_confirmed_identity; aa10_candidate_properties",
            "native_closure_authority": "aa8_client_native",
            "materialized_roots": "10151,10153",
            "materialized_damage_closure": ",".join(
                str(effect_id) for effect_id in REQUIRED_SORCERY_DAMAGE_EFFECTS
            ),
            "forced_movement_contract": "aa8_millimetres_plus_elevation_degrees",
            "physical_explosion_contract": "cryengine_constant_pressure_inside_radius",
            "sorcery_native_doodads": "13406,13407,14623,14666",
            "magic_circle_native_rows": "14623,14666;1126,1131;16482,16501;25646,25647",
            "wave_gods_whip_native_rows": "13406,13407;7406,7407;11660,11661;190",
            "sorcery_doodad_structural_candidates": (
                "groups:38626,38627,38628,38629,38630,43090,43245;"
                "phases:49136,49137,49339,49340,49913,55165,55330;"
                "clouts:4116,4121;timers:16372,16373;finals:5304,5305,5320"
            ),
            "promoted_native_skills": ",".join(str(value) for value in PROMOTED_SORCERY_SKILLS),
            "plot_3096": "aa8_client_native",
            "combat_resource_protocol": "implemented_exact_aa8_layout",
        }
        connection.executemany(
            "INSERT INTO sorcery_reconstruction_v4_metadata(key,value,provenance) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,provenance=excluded.provenance",
            [(key, value, "aa8_sorcery_v4") for key, value in sorted(metadata.items())],
        )
        connection.commit()
        verification = verify_runtime(
            connection, selected, structural_candidates
        ) if args.verify else None
        connection.execute("VACUUM")
    except Exception:
        connection.close()
        output.unlink(missing_ok=True)
        raise
    finally:
        if connection:
            connection.close()
        knowledge.close()
        aa10.close()

    manifest = {
        "authority": {
            "aa8_runtime_packets": "root_identity_and_client_reachability",
            "aa8_native_sqlite": "executable_closure_and_plot_contract",
            "aa10_crosswalk": "root_row_candidate_only",
            "balance_promotion": "manual_candidate_gate_required",
            "aa10_magic_circle_links": "structural_candidate_only_with_exact_aa8_endpoints",
        },
        "client_build": CLIENT_BUILD,
        "crosswalk": crosswalk_evidence,
        "dossiers": dossier_evidence,
        "format_version": 4,
        "aa8_closure_evidence": aa8_closure_evidence,
        "promoted_aa8_catalog_closures": promoted_evidence,
        "aa10_structural_candidates": structural_candidate_evidence,
        "merge": merge,
        "native_table_ids": {
            table: [int(row["id"]) for row in rows]
            for table, rows in sorted(selected.items())
        },
        "output": {"path": str(output), "sha256": sha256_file(output)},
        "sources": sources,
        "verification": verification,
    }
    args.manifest.write_text(canonical(manifest), encoding="utf-8")
    print(canonical({
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256_file(args.manifest),
        "output": str(output),
        "output_sha256": manifest["output"]["sha256"],
        "verification": verification,
    }))
    return manifest


if __name__ == "__main__":
    build(parse_args())
