#!/usr/bin/env python3
"""Build the complete AA8 Battlerage runtime on top of Archery V5.

AA8 remains the runtime authority.  The current specialization graph supplies
the 37 playable/ancestral roots and the deterministic native closure supplies
the three automatic and two obsolete internal skills absent from the staged
projection.  The AA10 database is audited only as a relationship crosswalk;
no AA10 row is promoted into the runtime.
"""

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
SHARED_PRIMITIVES = ROOT / "reconstruccion_skills_8" / "shared_primitives"
sys.path.insert(0, str(NATIVE_COMBAT))
sys.path.insert(0, str(SHARED_PRIMITIVES))

from build_native_combat_runtime import normalize, sha256_file, upsert_rows  # noqa: E402
from extract_native_unit_requirements import extract_unit_requirements  # noqa: E402


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
RUNTIME_VERSION = "battlerage-v2"
ABILITY_ID = 1
PLAYABLE_ROOT_IDS = (
    10377, 10455, 10644, 11918, 12026, 12028, 12034, 12786, 12787,
    12788, 13282, 13315, 16185, 18131, 18132, 18134, 18308, 18757,
    23587, 32040, 32049, 36401, 36402, 36403, 36404, 36405, 36406,
    36446, 36447, 36448, 36449, 39661, 39662, 41217, 41218, 43188,
    43189,
)
AUTOMATIC_SKILL_IDS = (34119, 34120, 34124)
OBSOLETE_INTERNAL_SKILL_IDS = (10385, 11854)
ALL_SKILL_IDS = tuple(sorted(
    PLAYABLE_ROOT_IDS + AUTOMATIC_SKILL_IDS + OBSOLETE_INTERNAL_SKILL_IDS
))
PASSIVE_IDS = (29, 32, 92, 244, 245, 295)
PASSIVE_BUFF_IDS = (811, 2610, 2621, 7544, 7542, 831)
PASSIVE_ID_TO_BUFF = {
    29: 811,
    32: 2610,
    92: 2621,
    244: 7544,
    245: 7542,
    295: 831,
}
EXPECTED_HASHES = {
    "carrier": "4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2",
    "graph": "54736AFC8CDC453C84FFA4C8337C76894FA86D78155E714B1B121B5B640589B5",
    "knowledge": "A3AB85F0F033407845651AD9277EFBBB4E772A1A8FCD20D973C2DCB5A3848559",
    "crosswalk": "44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71",
    "aa10_candidate": "87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F",
    "game11": "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
    "native_closure": "9B29046271D67802F9D3986AFFFB54640DC1292544FFB34B0A2AD7AEB44D10A8",
    "skill_modifiers": "CEC0A999BF9DD9E27A84DFD761CA92E7655196D4E2EEFC3F77BE0D90C10AC955",
}
EXPECTED_TAGGED_SKILLS_ROWS = 299
EXPECTED_TAGGED_BUFFS_ROWS = 287
EXPECTED_NATIVE_SKILL_MODIFIER_ROWS = 1571


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--knowledge", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--aa10-candidate", required=True, type=Path)
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--native-closure", required=True, type=Path)
    parser.add_argument("--skill-modifiers", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def compact_row_digest(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def validate_source(path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    expected = EXPECTED_HASHES[role]
    if actual != expected:
        raise RuntimeError(f"Unexpected {role} SHA-256 for {path}: {actual}")
    return {"path": str(path.resolve()), "sha256": actual}


def exact_native_row(
    knowledge: sqlite3.Connection, entity_key: str, expected_table: str
) -> dict[str, Any]:
    candidates: list[tuple[int, dict[str, Any]]] = []
    for row in knowledge.execute(
        "SELECT source_table,row_json FROM native_rows WHERE entity_key=?",
        (entity_key,),
    ):
        if str(row["source_table"]) != expected_table:
            continue
        try:
            payload = json.loads(str(row["row_json"]))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("id") is not None:
            candidates.append((len(payload), payload))
    if not candidates:
        raise RuntimeError(f"Missing exact AA8 row {expected_table}:{entity_key}")
    return max(candidates, key=lambda item: item[0])[1]


def load_native_closure(path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    tables = manifest.get("tables")
    if not isinstance(tables, dict):
        raise RuntimeError("Battlerage native closure has no tables object")
    if sorted(int(row["id"]) for row in tables.get("skills", [])) != list(ALL_SKILL_IDS):
        raise RuntimeError("Battlerage native closure does not contain the exact 42-skill set")
    if len(tables.get("passive_buffs", [])) != len(PASSIVE_IDS):
        raise RuntimeError("Battlerage native closure does not contain six passives")
    return tables, {
        "authority": "AA8_game11_native_closure",
        "runtime_carrier_role": "supplement_identity_source_only_not_runtime_base",
        "table_counts": {name: len(rows) for name, rows in sorted(tables.items())},
        "diagnostics": manifest.get("diagnostics", {}),
    }


def collect_rows(
    graph: sqlite3.Connection,
    knowledge: sqlite3.Connection,
    closure_tables: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    selected: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    # Start with the deterministic AA8 native closure.  Current staged rows
    # overlay it below so the old Phase 4 compact never acts as runtime carrier.
    for table, values in sorted(closure_tables.items()):
        if table == "tagged_buffs":
            continue
        for payload in values:
            if payload.get("id") is None:
                raise RuntimeError(f"Native closure row lacks id: {table}")
            selected[table][int(payload["id"])] = payload

    state_counts: Counter[str] = Counter()
    entity_keys: set[str] = set()
    for row in graph.execute(
        "SELECT DISTINCT entity_key,source_table,state FROM dependency_closure "
        "WHERE source_table IS NOT NULL ORDER BY source_table,entity_key"
    ):
        table = str(row["source_table"])
        entity_key = str(row["entity_key"])
        payload = exact_native_row(knowledge, entity_key, table)
        selected[table][int(payload["id"])] = payload
        state_counts[str(row["state"])] += 1
        entity_keys.add(entity_key)

    root_skill_ids: list[int] = []
    passive_map: dict[int, int] = {}
    for row in graph.execute(
        "SELECT root_kind,native_id,row_json FROM specialization_roots "
        "WHERE ability_id=? ORDER BY root_kind,native_id",
        (ABILITY_ID,),
    ):
        payload = json.loads(str(row["row_json"]))
        if str(row["root_kind"]) == "skill":
            selected["skills"][int(payload["id"])] = payload
            root_skill_ids.append(int(payload["id"]))
        elif str(row["root_kind"]) == "passive_buff":
            passive_id = int(payload["id"])
            selected["passive_buffs"][passive_id] = payload
            passive_map[passive_id] = int(payload["buff_id"])

    if tuple(root_skill_ids) != PLAYABLE_ROOT_IDS:
        raise RuntimeError(f"Unexpected Battlerage playable roots: {root_skill_ids}")
    if passive_map != PASSIVE_ID_TO_BUFF:
        raise RuntimeError(f"Unexpected Battlerage passive identities: {passive_map}")

    downstream = {
        int(row["skill_id"]): str(row["observed_state"])
        for row in graph.execute(
            "SELECT skill_id,observed_state FROM downstream_implementation_audit "
            "ORDER BY skill_id"
        )
    }
    if set(downstream) != set(PLAYABLE_ROOT_IDS):
        raise RuntimeError("Battlerage downstream audit does not cover all playable roots")
    non_enabled = {key: value for key, value in downstream.items() if value != "enabled"}
    if non_enabled:
        raise RuntimeError(f"Battlerage graph retains quarantined roots: {non_enabled}")

    # Reverse owner-keyed caches are reconstructed from exact AA8 knowledge.
    all_skill_ids = set(ALL_SKILL_IDS)
    tagged_skills: dict[int, dict[str, Any]] = {}
    for row in knowledge.execute(
        "SELECT row_json FROM native_rows WHERE source_table='tagged_skills'"
    ):
        try:
            payload = json.loads(str(row["row_json"]))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or payload.get("id") is None:
            continue
        if int(payload.get("skill_id") or 0) in all_skill_ids:
            tagged_skills[int(payload["id"])] = payload
    if len(tagged_skills) != EXPECTED_TAGGED_SKILLS_ROWS:
        raise RuntimeError(f"Unexpected AA8 tagged_skills rows: {len(tagged_skills)}")
    selected["tagged_skills"] = tagged_skills

    selected_buff_ids = set(selected["buffs"])
    tagged_buffs: dict[int, dict[str, Any]] = {}
    for row in knowledge.execute(
        "SELECT row_json FROM native_rows WHERE source_table='tagged_buffs'"
    ):
        try:
            payload = json.loads(str(row["row_json"]))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or payload.get("id") is None:
            continue
        if int(payload.get("buff_id") or 0) in selected_buff_ids:
            tagged_buffs[int(payload["id"])] = payload
    closure_tagged = {
        int(row["id"]): row for row in closure_tables.get("tagged_buffs", [])
    }
    if tagged_buffs != closure_tagged:
        raise RuntimeError("Current AA8 tagged_buffs differ from deterministic native closure")
    if len(tagged_buffs) != EXPECTED_TAGGED_BUFFS_ROWS:
        raise RuntimeError(f"Unexpected AA8 tagged_buffs rows: {len(tagged_buffs)}")
    selected["tagged_buffs"] = tagged_buffs

    rows = {
        table: [by_id[row_id] for row_id in sorted(by_id)]
        for table, by_id in sorted(selected.items())
    }
    if sorted(int(row["id"]) for row in rows["skills"]) != list(ALL_SKILL_IDS):
        raise RuntimeError("Merged Battlerage closure does not contain exact skill identities")
    return rows, {
        "ability_id": ABILITY_ID,
        "closure_entities": len(entity_keys),
        "closure_states": dict(sorted(state_counts.items())),
        "root_skill_ids": root_skill_ids,
        "automatic_skill_ids": list(AUTOMATIC_SKILL_IDS),
        "obsolete_internal_skill_ids": list(OBSOLETE_INTERNAL_SKILL_IDS),
        "passive_id_to_buff": {str(key): value for key, value in sorted(passive_map.items())},
        "tagged_skill_rows": len(tagged_skills),
        "tagged_buff_rows": len(tagged_buffs),
        "downstream_audit": {"enabled": len(downstream), "non_enabled": non_enabled},
        "rows_by_table": {table: len(values) for table, values in rows.items()},
    }


def crosswalk_audit(
    crosswalk: sqlite3.Connection, rows: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    selected_ids = {
        table: {str(payload["id"]) for payload in values}
        for table, values in rows.items()
        if values and values[0].get("id") is not None
    }
    placeholders = ",".join("?" for _ in selected_ids)
    classifications_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    conflict_details: dict[tuple[str, str], dict[str, Any]] = {}
    for row in crosswalk.execute(
        f"SELECT table_name,aa8_id,classification,natural_key_json,"
        f"changed_property_columns_json,changed_relation_columns_json,balance_state "
        f"FROM row_comparisons WHERE table_name IN ({placeholders}) "
        f"AND aa8_id IS NOT NULL",
        tuple(sorted(selected_ids)),
    ):
        table = str(row["table_name"])
        row_id = str(row["aa8_id"])
        if row_id not in selected_ids[table]:
            continue
        classification = str(row["classification"])
        classifications_by_key[(table, row_id)].add(classification)
        if classification == "conflict":
            conflict_details[(table, row_id)] = {
                "table": table,
                "aa8_id": row_id,
                "natural_key": json.loads(str(row["natural_key_json"] or "{}")),
                "changed_properties": json.loads(
                    str(row["changed_property_columns_json"] or "[]")
                ),
                "changed_relations": json.loads(
                    str(row["changed_relation_columns_json"] or "[]")
                ),
                "balance_state": str(row["balance_state"]),
                "runtime_authority": "AA8_client_native",
                "aa10_promoted": False,
            }

    totals: Counter[str] = Counter()
    by_table: dict[str, dict[str, int]] = {}
    for table, values in sorted(rows.items()):
        table_counts: Counter[str] = Counter()
        for payload in values:
            row_id = str(payload["id"])
            matches = sorted(classifications_by_key.get((table, row_id), set()))
            classification = "+".join(matches) if matches else "not_compared"
            table_counts[classification] += 1
            totals[classification] += 1
        by_table[table] = dict(sorted(table_counts.items()))
    return {
        "policy": "mandatory_gap_reduction_only_no_aa10_runtime_rows",
        "selected_aa8_rows": sum(len(values) for values in rows.values()),
        "classifications": dict(sorted(totals.items())),
        "conflict_rows": sum(value for key, value in totals.items() if "conflict" in key),
        "conflict_details": [conflict_details[key] for key in sorted(conflict_details)],
        "tables": by_table,
    }


def audit_aa10_internal_candidates(
    path: Path, tagged_skills: list[dict[str, Any]]
) -> dict[str, Any]:
    ids = OBSOLETE_INTERNAL_SKILL_IDS + AUTOMATIC_SKILL_IDS
    placeholders = ",".join("?" for _ in ids)
    with ro(path) as connection:
        skill_rows = [
            dict(row) for row in connection.execute(
                f"SELECT id,ability_id,show,auto_learn,skill_points FROM skills "
                f"WHERE id IN ({placeholders}) ORDER BY id", ids
            )
        ]
        tag_rows = [
            dict(row) for row in connection.execute(
                f"SELECT id,tag_id,skill_id FROM tagged_skills "
                f"WHERE skill_id IN ({placeholders}) ORDER BY id", ids
            )
        ]
        visual_rows = [
            dict(row) for row in connection.execute(
                f"SELECT owner_id,owner_type,level,fx_group_id,projectile_id "
                f"FROM skill_visual_groups WHERE owner_id IN ({placeholders}) "
                f"AND owner_type='Skill' ORDER BY owner_id,level,fx_group_id", ids
            )
        ]
    if [int(row["id"]) for row in skill_rows] != list(OBSOLETE_INTERNAL_SKILL_IDS):
        raise RuntimeError(f"Unexpected AA10 Battlerage internal skills: {skill_rows}")
    aa8_tags = sorted(
        {
            (int(row["id"]), int(row["tag_id"]), int(row["skill_id"]))
            for row in tagged_skills
            if int(row["skill_id"]) in ids
        }
    )
    aa10_tags = sorted(
        (int(row["id"]), int(row["tag_id"]), int(row["skill_id"]))
        for row in tag_rows
    )
    if aa10_tags != aa8_tags:
        raise RuntimeError("AA10 Battlerage internal tag crosswalk does not match AA8")
    return {
        "authority": "crosswalk_10_r575_candidate",
        "runtime_rows": 0,
        "skills_present": [int(row["id"]) for row in skill_rows],
        "skills_absent": list(AUTOMATIC_SKILL_IDS),
        "stable_tagged_skill_relations": len(aa10_tags),
        "skill_visual_candidates": visual_rows,
        "accepted_fields": ["identity", "tag_relation", "presentation_relation"],
        "rejected_fields": ["balance", "timing", "formula", "protocol", "content_exclusive_10x"],
    }


def validate_skill_modifiers(
    path: Path, carrier: sqlite3.Connection
) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    rows = manifest.get("rows", [])
    if len(rows) != EXPECTED_NATIVE_SKILL_MODIFIER_ROWS:
        raise RuntimeError(f"Unexpected native skill_modifiers rows: {len(rows)}")
    native_rows = sorted(
        (tuple(row.get(column) for column in manifest["columns"]) for row in rows),
        key=lambda row: tuple("" if value is None else str(value) for value in row),
    )
    carrier_rows = sorted(
        (tuple(row) for row in carrier.execute(
            "SELECT owner_type,owner_id,dynamic_value,skill_attribute_id,skill_id,"
            "synergy,tag_id,target_buff_id,target_tag_id,unit_modifier_type_id,value "
            "FROM skill_modifiers"
        )),
        key=lambda row: tuple("" if value is None else str(value) for value in row),
    )
    if carrier_rows != native_rows:
        raise RuntimeError("Archery V5 carrier skill_modifiers differ from AA8 game11")
    forbidden_legacy = [
        row for row in carrier.execute(
            "SELECT * FROM skill_modifiers WHERE owner_type='Buff' AND owner_id=811"
        )
    ]
    if forbidden_legacy:
        raise RuntimeError("Carrier unexpectedly contains legacy owner 811 skill modifiers")
    weapon_mastery = [
        dict(row) for row in carrier.execute(
            "SELECT * FROM skill_modifiers WHERE owner_type='Buff' AND owner_id=831"
        )
    ]
    if len(weapon_mastery) != 1:
        raise RuntimeError(f"Unexpected Weapon Mastery modifiers: {weapon_mastery}")
    return {
        "authority": "AA8_game11_cached_result",
        "rows": len(native_rows),
        "sha256": compact_row_digest([dict(zip(manifest["columns"], row)) for row in native_rows]),
        "weapon_mastery_rows": weapon_mastery,
        "legacy_owner_811_rows_rejected": 16,
        "runtime_mutation": False,
    }


def materialize_unit_requirements(
    game11: Path,
    rows: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    native_rows, provenance = extract_unit_requirements(game11)
    plot_condition_ids = {int(row["id"]) for row in rows.get("plot_conditions", [])}
    selected = [
        row for row in native_rows
        if (
            str(row["owner_type"]) == "Skill"
            and int(row["owner_id"]) in set(ALL_SKILL_IDS)
        ) or (
            str(row["owner_type"]) == "PlotCondition"
            and int(row["owner_id"]) in plot_condition_ids
        )
    ]
    selected.sort(key=lambda row: (
        str(row["owner_type"]), int(row["owner_id"]), int(row["kind_id"]),
        int(row["value1"]), int(row["value2"]), int(row["value3"]),
    ))
    skill_rows = [row for row in selected if row["owner_type"] == "Skill"]
    if len(skill_rows) != 21:
        raise RuntimeError(f"Unexpected Battlerage skill unit requirements: {skill_rows}")
    return selected, {
        "provenance": provenance,
        "selected_rows": len(selected),
        "selected_skill_rows": len(skill_rows),
        "selected_plot_condition_rows": len(selected) - len(skill_rows),
    }


def replace_owner_partition(
    connection: sqlite3.Connection,
    table: str,
    owner_column: str,
    rows: list[dict[str, Any]],
) -> None:
    owners = sorted({int(row[owner_column]) for row in rows})
    if not owners:
        return
    placeholders = ",".join("?" for _ in owners)
    connection.execute(
        f'DELETE FROM "{table}" WHERE "{owner_column}" IN ({placeholders})', owners
    )


def upsert_heterogeneous_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Upsert native rows without assuming every provenance has one schema.

    Current staged rows and game11-only supplemental rows can legitimately
    expose different column sets.  Grouping by the exact source column set
    prevents absent fields from being materialized as guessed zeroes while
    still writing every field that AA8 actually recovered.
    """
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        normalized, _ = normalize(table, row)
        groups[tuple(normalized)].append(row)
    reports = [
        upsert_rows(connection, table, group)
        for _, group in sorted(groups.items(), key=lambda item: item[0])
    ]
    return {
        "rows": sum(int(report["rows"]) for report in reports),
        "columns": sorted({
            column for report in reports for column in report.get("columns", [])
        }),
        "derived_fields": [
            field for report in reports for field in report.get("derived_fields", [])
        ],
        "schema_groups": len(reports),
        "historical_values_preserved": False,
    }


def verify_runtime(
    connection: sqlite3.Connection,
    rows: dict[str, list[dict[str, Any]]],
    unit_requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    missing: list[str] = []
    mismatched: list[str] = []
    for table, values in sorted(rows.items()):
        runtime_columns = {
            str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')
        }
        for source in values:
            row_id = int(source["id"])
            runtime = connection.execute(
                f'SELECT * FROM "{table}" WHERE id=?', (row_id,)
            ).fetchone()
            if runtime is None:
                missing.append(f"{table}:{row_id}")
                continue
            expected, _ = normalize(table, source)
            actual = dict(runtime)
            for name, value in expected.items():
                if name in runtime_columns and actual.get(name) != value:
                    mismatched.append(f"{table}:{row_id}:{name}")
                    break
    skills = [
        tuple(row) for row in connection.execute(
            "SELECT id,show,skill_points,auto_learn FROM skills WHERE ability_id=? "
            "ORDER BY id", (ABILITY_ID,)
        )
    ]
    if [int(row[0]) for row in skills] != list(ALL_SKILL_IDS):
        raise RuntimeError(f"Battlerage runtime skill identities mismatch: {skills}")
    visible_learnable = [row for row in skills if int(row[1]) and int(row[2]) > 0]
    automatic = [row for row in skills if int(row[0]) in AUTOMATIC_SKILL_IDS]
    hidden = [row for row in skills if int(row[0]) in OBSOLETE_INTERNAL_SKILL_IDS]
    if len(visible_learnable) != 12:
        raise RuntimeError(f"Battlerage visible learnable skills={len(visible_learnable)}")
    if len(automatic) != 3 or any(int(row[1]) != 1 or int(row[2]) != 0 for row in automatic):
        raise RuntimeError(f"Battlerage automatic skill contract mismatch: {automatic}")
    if len(hidden) != 2 or any(int(row[1]) != 0 for row in hidden):
        raise RuntimeError(f"Battlerage hidden skill contract mismatch: {hidden}")

    passives = [
        (int(row[0]), int(row[1])) for row in connection.execute(
            "SELECT id,buff_id FROM passive_buffs WHERE ability_id=? ORDER BY id",
            (ABILITY_ID,),
        )
    ]
    if passives != sorted(PASSIVE_ID_TO_BUFF.items()):
        raise RuntimeError(f"Battlerage passive runtime mismatch: {passives}")

    status = [
        (int(row[0]), str(row[1])) for row in connection.execute(
            "SELECT skill_id,status FROM native_combat_skill_status "
            "WHERE ability_id=? ORDER BY skill_id", (ABILITY_ID,)
        )
    ]
    if status != [(skill_id, "enabled") for skill_id in PLAYABLE_ROOT_IDS]:
        raise RuntimeError(f"Battlerage status mismatch: {status}")

    tagged_skill_count = int(connection.execute(
        f"SELECT COUNT(*) FROM tagged_skills WHERE skill_id IN "
        f"({','.join('?' for _ in ALL_SKILL_IDS)})", ALL_SKILL_IDS
    ).fetchone()[0])
    if tagged_skill_count != EXPECTED_TAGGED_SKILLS_ROWS:
        raise RuntimeError(f"Battlerage tagged_skills rows={tagged_skill_count}")
    duplicate_skill_tags = int(connection.execute(
        f"SELECT COUNT(*) FROM (SELECT skill_id,tag_id,COUNT(*) n FROM tagged_skills "
        f"WHERE skill_id IN ({','.join('?' for _ in ALL_SKILL_IDS)}) "
        f"GROUP BY skill_id,tag_id HAVING n>1)", ALL_SKILL_IDS
    ).fetchone()[0])
    if duplicate_skill_tags:
        raise RuntimeError(f"Battlerage duplicate skill tags={duplicate_skill_tags}")

    selected_buff_ids = sorted({int(row["buff_id"]) for row in rows["tagged_buffs"]})
    duplicate_buff_tags = int(connection.execute(
        f"SELECT COUNT(*) FROM (SELECT buff_id,tag_id,COUNT(*) n FROM tagged_buffs "
        f"WHERE buff_id IN ({','.join('?' for _ in selected_buff_ids)}) "
        f"GROUP BY buff_id,tag_id HAVING n>1)", selected_buff_ids
    ).fetchone()[0])
    if duplicate_buff_tags:
        raise RuntimeError(f"Battlerage duplicate buff tags={duplicate_buff_tags}")

    actual_requirements = [
        dict(row) for row in connection.execute(
            "SELECT owner_type,owner_id,display_msg,kind_id,value1,value2,value3 "
            "FROM unit_reqs WHERE (owner_type,owner_id) IN ("
            + ",".join("(?,?)" for _ in {
                (str(row["owner_type"]), int(row["owner_id"]))
                for row in unit_requirements
            }) + ") ORDER BY owner_type,owner_id,kind_id,value1,value2,value3",
            tuple(value for pair in sorted({
                (str(row["owner_type"]), int(row["owner_id"]))
                for row in unit_requirements
            }) for value in pair),
        )
    ]
    if actual_requirements != unit_requirements:
        raise RuntimeError("Battlerage unit requirements differ after materialization")

    evidence = connection.execute(
        "SELECT aa10_runtime_rows FROM aa8_battlerage_runtime_evidence WHERE version=?",
        (RUNTIME_VERSION,),
    ).fetchone()
    if evidence is None or int(evidence[0]) != 0:
        raise RuntimeError("Battlerage runtime evidence does not prove zero AA10 rows")
    if missing or mismatched:
        raise RuntimeError(
            f"Battlerage runtime verification failed: missing={missing[:20]} "
            f"mismatched={mismatched[:20]}"
        )
    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite integrity failed: quick={quick}, integrity={integrity}")
    return {
        "materialized_rows": sum(len(values) for values in rows.values()),
        "skills": len(skills),
        "visible_learnable": len(visible_learnable),
        "automatic_skills": [int(row[0]) for row in automatic],
        "obsolete_internal_skills": [int(row[0]) for row in hidden],
        "passives": passives,
        "enabled_playable_roots": len(status),
        "tagged_skill_rows": tagged_skill_count,
        "unit_requirement_rows": len(unit_requirements),
        "quick_check": quick,
        "integrity_check": integrity,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "carrier": validate_source(args.runtime_carrier, "carrier"),
        "graph": validate_source(args.graph, "graph"),
        "knowledge": validate_source(args.knowledge, "knowledge"),
        "crosswalk": validate_source(args.crosswalk, "crosswalk"),
        "aa10_candidate": validate_source(args.aa10_candidate, "aa10_candidate"),
        "game11": validate_source(args.game11, "game11"),
        "native_closure": validate_source(args.native_closure, "native_closure"),
        "skill_modifiers": validate_source(args.skill_modifiers, "skill_modifiers"),
    }
    closure_tables, native_closure_report = load_native_closure(args.native_closure)
    with ro(args.graph) as graph, ro(args.knowledge) as knowledge:
        rows, closure = collect_rows(graph, knowledge, closure_tables)
    with ro(args.crosswalk) as crosswalk:
        crosswalk_report = crosswalk_audit(crosswalk, rows)
    aa10_report = audit_aa10_internal_candidates(
        args.aa10_candidate, rows["tagged_skills"]
    )
    unit_requirements, unit_req_report = materialize_unit_requirements(
        args.game11, rows
    )
    with ro(args.runtime_carrier) as carrier:
        skill_modifier_report = validate_skill_modifiers(args.skill_modifiers, carrier)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(args.runtime_carrier, temporary)
    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN IMMEDIATE")
        replace_owner_partition(connection, "tagged_skills", "skill_id", rows["tagged_skills"])
        replace_owner_partition(connection, "tagged_buffs", "buff_id", rows["tagged_buffs"])
        changes = {
            table: upsert_heterogeneous_rows(connection, table, values)
            for table, values in sorted(rows.items())
        }
        unit_owner_pairs = sorted({
            (str(row["owner_type"]), int(row["owner_id"]))
            for row in unit_requirements
        })
        for owner_type, owner_id in unit_owner_pairs:
            connection.execute(
                "DELETE FROM unit_reqs WHERE owner_type=? AND owner_id=?",
                (owner_type, owner_id),
            )
        connection.executemany(
            "INSERT INTO unit_reqs "
            "(owner_type,owner_id,display_msg,kind_id,value1,value2,value3) "
            "VALUES(?,?,?,?,?,?,?)",
            [
                (
                    row["owner_type"], row["owner_id"], row["display_msg"],
                    row["kind_id"], row["value1"], row["value2"], row["value3"],
                )
                for row in unit_requirements
            ],
        )
        changes["unit_reqs"] = {
            "rows": len(unit_requirements),
            "columns": [
                "owner_type", "owner_id", "display_msg", "kind_id",
                "value1", "value2", "value3",
            ],
            "derived_fields": [],
            "historical_values_preserved": False,
        }
        connection.executemany(
            "UPDATE native_combat_skill_status SET status='enabled',reason='' "
            "WHERE ability_id=? AND skill_id=?",
            [(ABILITY_ID, skill_id) for skill_id in PLAYABLE_ROOT_IDS],
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS aa8_battlerage_runtime_evidence ("
            "version TEXT PRIMARY KEY, ability_id INTEGER NOT NULL, "
            "client_build TEXT NOT NULL, graph_sha256 TEXT NOT NULL, "
            "knowledge_sha256 TEXT NOT NULL, crosswalk_sha256 TEXT NOT NULL, "
            "native_closure_sha256 TEXT NOT NULL, aa10_runtime_rows INTEGER NOT NULL, "
            "selected_rows INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO aa8_battlerage_runtime_evidence "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                RUNTIME_VERSION, ABILITY_ID, CLIENT_BUILD,
                EXPECTED_HASHES["graph"], EXPECTED_HASHES["knowledge"],
                EXPECTED_HASHES["crosswalk"], EXPECTED_HASHES["native_closure"],
                0, sum(len(values) for values in rows.values()),
            ),
        )
        connection.commit()
        verification = verify_runtime(connection, rows, unit_requirements)
    finally:
        connection.close()
    temporary.replace(args.output)

    manifest = {
        "schema_version": 1,
        "runtime_version": RUNTIME_VERSION,
        "client_build": CLIENT_BUILD,
        "authority": "AA8_client_native",
        "sources": sources,
        "native_closure": native_closure_report,
        "closure": closure,
        "crosswalk": crosswalk_report,
        "aa10_internal_gap_reduction": aa10_report,
        "native_skill_modifiers": skill_modifier_report,
        "native_unit_requirements": unit_req_report,
        "changes": changes,
        "verification": verification,
        "output": {
            "path": str(args.output.resolve()),
            "bytes": args.output.stat().st_size,
            "sha256": sha256_file(args.output),
        },
    }
    args.manifest.write_text(canonical(manifest), encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    args = parse_args()
    manifest = build(args)
    if args.verify:
        print(canonical({
            "output": manifest["output"],
            "verification": manifest["verification"],
            "crosswalk_classifications": manifest["crosswalk"]["classifications"],
        }), end="")
    else:
        print(manifest["output"]["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
