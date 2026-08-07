#!/usr/bin/env python3
"""Build the exact AA8 Archery executable closure on top of Sorcery V23."""

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
ABILITY_ID = 6
PASSIVE_IDS = (2, 7, 35, 255, 256, 300)
PASSIVE_BUFF_IDS = (480, 486, 888, 7564, 7565, 889)
ANCESTRAL_PLOTS = (2927, 2928, 2941, 2942)
CONCUSSIVE_MIST = {
    "skill_id": 36471,
    "plot_id": 2941,
    "bubble_effect_id": 7542,
}
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
    "archery_passive_buffs": {
        "query": "SELECT * FROM buffs WHERE id IN (480,486,888,889,7564,7565) "
        "ORDER BY id",
        "rows": 6,
        "sha256": "C63FF2EC974C68D4C449FDEB5C8AF4FFBC7A45CD9C2D4C83562A8DF847B1FB7E",
        "consumer": "server_passive_buff_cache_and_native_hardcoded_dispatch",
    },
    "archery_passive_tagged_buffs": {
        "query": "SELECT * FROM tagged_buffs WHERE buff_id IN "
        "(480,486,888,889,7564,7565) ORDER BY buff_id,tag_id,id",
        "rows": 21,
        "sha256": "404827C91918E3191F7A09B11E1E665D2BA62CDA6AA403197F8D9D78F9233D1A",
        "consumer": "server_buff_tag_cache_and_native_passive_dispatch",
    },
    "tagged_skills": {
        "query": "SELECT * FROM tagged_skills WHERE skill_id IN "
        "(10694,10708,11368,11933,12133,12759,12792,12793,12794,13281,14835,14836,14837,"
        "15073,15096,16210,23592,36468,36469,36470,36471,36472,36473,38893,39663,39664,"
        "39665,39666,39667,39668,40580,41219,41221,42849,42851) "
        "ORDER BY skill_id,tag_id,id",
        "rows": 356,
        "sha256": "C21FD1BE7FADC54B2847A3470A1D13752160A64A01DFC44307500F163299B068",
        "consumer": "server_skill_tag_and_modifier_cache",
    },
    "skill_modifiers": {
        "query": "SELECT * FROM skill_modifiers WHERE skill_id IN "
        "(10694,10708,11368,11933,12133,12759,12792,12793,12794,13281,14835,14836,14837,"
        "15073,15096,16210,23592,36468,36469,36470,36471,36472,36473,38893,39663,39664,"
        "39665,39666,39667,39668,40580,41219,41221,42849,42851) "
        "ORDER BY skill_id,owner_type,owner_id,skill_attribute_id,unit_modifier_type_id,value",
        "rows": 32,
        "sha256": "3B9470E9E4A91AEDDABEC29EEE8AF9FC0CBD6752F85849393FB883B6BA4A65D8",
        "consumer": "server_skill_modifier_cache",
    },
    "skill_req_skills": {
        "query": "SELECT * FROM skill_req_skills WHERE skill_id IN "
        "(10694,10708,11368,11933,12133,12759,12792,12793,12794,13281,14835,14836,14837,"
        "15073,15096,16210,23592,36468,36469,36470,36471,36472,36473,38893,39663,39664,"
        "39665,39666,39667,39668,40580,41219,41221,42849,42851) "
        "ORDER BY skill_id,skill_req_id",
        "rows": 7,
        "sha256": "D0631D6D0E1D91F112B64C247EE9A888E2AB6B868D81E82F35D44BD06A56BBFC",
        "consumer": "client_learning_metadata",
    },
    "skill_visual_groups": {
        "query": "SELECT * FROM skill_visual_groups WHERE owner_type='Skill' AND owner_id IN "
        "(10694,10708,11368,11933,12133,12759,12792,12793,12794,13281,14835,14836,14837,"
        "15073,15096,16210,23592,36468,36469,36470,36471,36472,36473,38893,39663,39664,"
        "39665,39666,39667,39668,40580,41219,41221,42849,42851) "
        "ORDER BY owner_id,level,fx_group_id,projectile_id",
        "rows": 3,
        "sha256": "9D41601FB7E332C87788736411C368D604CE56EDA58A0A240D3DAA4C38F095BE",
        "consumer": "client_presentation",
    },
}
EXPECTED_HASHES = {
    "carrier": "B6E139D0E6953EE3F7BEAB015E770C9A7D5A270A45978E55016A0324B60CEBC0",
    "graph": "42F2369F8FDEDE622A8181CF0517412AC9D7A9A3A306DC52722E0D837279719C",
    "knowledge": "A3AB85F0F033407845651AD9277EFBBB4E772A1A8FCD20D973C2DCB5A3848559",
    "crosswalk": "44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71",
    "game11": "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--knowledge", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--game11", required=True, type=Path)
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
        if isinstance(payload, dict) and "id" in payload:
            candidates.append((len(payload), payload))
    if not candidates:
        raise RuntimeError(f"Missing exact AA8 row {expected_table}:{entity_key}")
    return max(candidates, key=lambda item: item[0])[1]


def collect_rows(
    graph: sqlite3.Connection, knowledge: sqlite3.Connection
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    selected: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
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
    passive_ids: list[int] = []
    passive_buff_ids: list[int] = []
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
            selected["passive_buffs"][int(payload["id"])] = payload
            passive_ids.append(int(payload["id"]))
            passive_buff_ids.append(int(payload["buff_id"]))

    if tuple(passive_ids) != PASSIVE_IDS:
        raise RuntimeError(f"Unexpected Archery passive roots: {passive_ids}")
    if tuple(passive_buff_ids) != PASSIVE_BUFF_IDS:
        raise RuntimeError(f"Unexpected Archery passive buff identities: {passive_buff_ids}")

    # specialization_roots identifies the passive wrapper and its buff_id, but
    # the graph does not currently emit the underlying buffs row.  Keeping the
    # carrier copy here is unsafe: older reconstruction passes contained
    # legacy descriptions and incomplete tag membership for these six buffs.
    # Materialize the exact AA8 native rows before resolving reverse relations.
    passive_buff_id_set = set(passive_buff_ids)
    for row in knowledge.execute(
        "SELECT row_json FROM native_rows WHERE source_table='buffs'"
    ):
        try:
            payload = json.loads(str(row["row_json"]))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or "id" not in payload:
            continue
        buff_id = int(payload["id"])
        if buff_id in passive_buff_id_set:
            selected["buffs"][buff_id] = payload

    missing_passive_buffs = passive_buff_id_set - set(selected["buffs"])
    if missing_passive_buffs:
        raise RuntimeError(
            f"Missing exact AA8 Archery passive buffs: {sorted(missing_passive_buffs)}"
        )

    downstream_states = {
        int(row["skill_id"]): str(row["observed_state"])
        for row in graph.execute(
            "SELECT skill_id,observed_state FROM downstream_implementation_audit "
            "ORDER BY skill_id"
        )
    }
    if set(downstream_states) != set(root_skill_ids):
        raise RuntimeError("Archery downstream audit does not cover every native skill root")
    non_enabled = {
        skill_id: state
        for skill_id, state in downstream_states.items()
        if state != "enabled"
    }
    if non_enabled:
        raise RuntimeError(f"Archery graph still contains quarantined roots: {non_enabled}")

    # The specialization graph closes executable effects but does not model
    # skill tags as child entities.  They are nevertheless executable input:
    # SkillModifiers and several native passive consumers select skills by
    # tag.  Materialize the exact AA8 rows for every Archery root instead of
    # retaining the duplicated/incomplete historical carrier surface.
    root_skill_id_set = set(root_skill_ids)
    tagged_skill_ids: set[int] = set()
    for row in knowledge.execute(
        "SELECT row_json FROM native_rows WHERE source_table='tagged_skills'"
    ):
        try:
            payload = json.loads(str(row["row_json"]))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or "id" not in payload:
            continue
        if int(payload.get("skill_id", 0)) not in root_skill_id_set:
            continue
        row_id = int(payload["id"])
        selected["tagged_skills"][row_id] = payload
        tagged_skill_ids.add(row_id)

    if not tagged_skill_ids:
        raise RuntimeError("AA8 Archery roots resolved zero tagged_skills rows")

    # tagged_buffs is a reverse lookup cache keyed by buff_id/tag_id, not a
    # conventional child closure rooted by its own id.  Re-resolve it from the
    # exact AA8 knowledge surface for every selected buff, including passives,
    # so deployment can replace the complete owner partition atomically.
    selected_buff_ids = set(selected["buffs"])
    tagged_buff_ids: set[int] = set()
    for row in knowledge.execute(
        "SELECT row_json FROM native_rows WHERE source_table='tagged_buffs'"
    ):
        try:
            payload = json.loads(str(row["row_json"]))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or "id" not in payload:
            continue
        if int(payload.get("buff_id", 0)) not in selected_buff_ids:
            continue
        row_id = int(payload["id"])
        selected["tagged_buffs"][row_id] = payload
        tagged_buff_ids.add(row_id)

    missing_passive_tag_owners = passive_buff_id_set - {
        int(payload["buff_id"])
        for payload in selected["tagged_buffs"].values()
    }
    if missing_passive_tag_owners:
        raise RuntimeError(
            "Missing exact AA8 tagged_buffs for Archery passive owners: "
            f"{sorted(missing_passive_tag_owners)}"
        )

    rows = {
        table: [by_id[row_id] for row_id in sorted(by_id)]
        for table, by_id in sorted(selected.items())
    }
    tagged_buff_owner_ids = sorted({
        int(row["buff_id"]) for row in rows.get("tagged_buffs", [])
    })
    return rows, {
        "ability_id": ABILITY_ID,
        "closure_entities": len(entity_keys),
        "closure_states": dict(sorted(state_counts.items())),
        "root_skill_ids": root_skill_ids,
        "passive_ids": passive_ids,
        "passive_buff_ids": passive_buff_ids,
        "tagged_skill_rows": len(tagged_skill_ids),
        "tagged_buff_native_rows": len(tagged_buff_ids),
        "tagged_buff_rows": len(rows.get("tagged_buffs", [])),
        "tagged_buff_owner_ids": tagged_buff_owner_ids,
        "downstream_audit": {
            "enabled": len(downstream_states),
            "non_enabled": non_enabled,
        },
        "rows_by_table": {table: len(values) for table, values in rows.items()},
    }


def crosswalk_audit(
    crosswalk: sqlite3.Connection, rows: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    by_classification: Counter[str] = Counter()
    by_table: dict[str, dict[str, int]] = {}
    compared = 0
    absent = 0
    conflicts = 0

    selected_ids = {
        table: {str(payload["id"]) for payload in values}
        for table, values in rows.items()
    }
    placeholders = ",".join("?" for _ in selected_ids)
    classifications_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    conflict_evidence_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    # row_comparisons has over 1.5 million rows and intentionally carries no
    # runtime index.  Scan it once for the selected logical tables instead of
    # issuing one full-table scan per AA8 row.
    for row in crosswalk.execute(
        f"SELECT table_name,aa8_id,classification,natural_key_json,"
        f"changed_property_columns_json,changed_relation_columns_json,balance_state "
        f"FROM row_comparisons "
        f"WHERE table_name IN ({placeholders}) AND aa8_id IS NOT NULL",
        tuple(sorted(selected_ids)),
    ):
        table = str(row["table_name"])
        row_id = str(row["aa8_id"])
        if row_id in selected_ids[table]:
            classifications_by_key[(table, row_id)].add(str(row["classification"]))
            if str(row["classification"]) == "conflict":
                conflict_evidence_by_key[(table, row_id)] = {
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

    for table, values in sorted(rows.items()):
        table_counts: Counter[str] = Counter()
        for payload in values:
            row_id = str(payload["id"])
            matches = classifications_by_key.get((table, row_id), set())
            if not matches:
                table_counts["not_compared"] += 1
                by_classification["not_compared"] += 1
                absent += 1
                continue
            classifications = sorted(matches)
            classification = "+".join(classifications)
            table_counts[classification] += 1
            by_classification[classification] += 1
            compared += 1
            if "conflict" in classifications:
                conflicts += 1
        by_table[table] = dict(sorted(table_counts.items()))

    return {
        "policy": "mandatory_gap_reduction_only_no_aa10_runtime_rows",
        "selected_aa8_rows": sum(len(values) for values in rows.values()),
        "compared_rows": compared,
        "not_compared_rows": absent,
        "conflict_rows": conflicts,
        "conflict_details": [
            conflict_evidence_by_key[key]
            for key in sorted(conflict_evidence_by_key)
        ],
        "classifications": dict(sorted(by_classification.items())),
        "tables": by_table,
    }


def row_exists(connection: sqlite3.Connection, table: str, row_id: int) -> bool:
    return (
        connection.execute(f'SELECT 1 FROM "{table}" WHERE id=?', (row_id,)).fetchone()
        is not None
    )


def owner_keyed_relation_audit(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    for name, contract in OWNER_KEYED_RELATIONS.items():
        rows = [dict(row) for row in connection.execute(str(contract["query"]))]
        payload = "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for row in rows
        ) + "\n"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
        if len(rows) != contract["rows"] or digest != contract["sha256"]:
            raise RuntimeError(
                f"Archery owner-keyed relation mismatch {name}: "
                f"rows={len(rows)} sha256={digest}"
            )
        report[name] = {
            "rows": len(rows),
            "sha256": digest,
            "consumer": contract["consumer"],
        }
    return report


def verify_runtime(
    connection: sqlite3.Connection, rows: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    missing: list[str] = []
    mismatched: list[str] = []
    for table, values in sorted(rows.items()):
        if table == "unit_reqs":
            continue
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
                if name not in runtime_columns:
                    continue
                if actual.get(name) != value:
                    mismatched.append(f"{table}:{row_id}:{name}")
                    break

    passive_rows = [
        int(row[0])
        for row in connection.execute(
            "SELECT id FROM passive_buffs WHERE ability_id=? ORDER BY id", (ABILITY_ID,)
        )
    ]
    if passive_rows != list(PASSIVE_IDS):
        raise RuntimeError(f"Archery passive runtime mismatch: {passive_rows}")
    for plot_id in ANCESTRAL_PLOTS:
        if not row_exists(connection, "plots", plot_id):
            missing.append(f"plots:{plot_id}")
    if not row_exists(connection, "bubble_effects", CONCUSSIVE_MIST["bubble_effect_id"]):
        missing.append(f"bubble_effects:{CONCUSSIVE_MIST['bubble_effect_id']}")
    charge_skills = tuple(
        tuple(row)
        for row in connection.execute(
            "SELECT id,charge_count,charge_cooldown_time FROM skills "
            "WHERE id IN (11368,13281,38893,42851) ORDER BY id"
        )
    )
    if charge_skills != CHARGE_SKILL_CONTRACTS:
        raise RuntimeError(f"Archery charge skill contract mismatch: {charge_skills}")
    charge_effects = tuple(
        tuple(row)
        for row in connection.execute(
            "SELECT id,value1 FROM special_effects "
            "WHERE special_effect_type_id=158 AND id IN (41872,55123) ORDER BY id"
        )
    )
    if charge_effects != CHARGE_COOLDOWN_EFFECTS:
        raise RuntimeError(f"Archery charge effect mismatch: {charge_effects}")
    unit_requirements = tuple(
        tuple(row)
        for row in connection.execute(
            "SELECT owner_id,owner_type,display_msg,kind_id,value1,value2,value3 "
            "FROM unit_reqs WHERE owner_type='Skill' AND owner_id IN "
            "(10694,11933,12793,12794,13281,14835,14836,14837,15073,15096,16210,23592) "
            "ORDER BY owner_id,kind_id,value1,value2,value3"
        )
    )
    if unit_requirements != ARCHERY_UNIT_REQUIREMENTS:
        raise RuntimeError(
            f"Archery unit requirement mismatch: {unit_requirements}"
        )
    plot_unit_requirements = tuple(
        tuple(row)
        for row in connection.execute(
            "SELECT owner_id,owner_type,display_msg,kind_id,value1,value2,value3 "
            "FROM unit_reqs WHERE owner_type='PlotCondition' AND owner_id=14753 "
            "ORDER BY owner_id,kind_id,value1,value2,value3"
        )
    )
    if plot_unit_requirements != ARCHERY_PLOT_UNIT_REQUIREMENTS:
        raise RuntimeError(
            f"Archery plot unit requirement mismatch: {plot_unit_requirements}"
        )
    owner_keyed_relations = owner_keyed_relation_audit(connection)
    non_enabled = int(
        connection.execute(
            "SELECT COUNT(*) FROM native_combat_skill_status "
            "WHERE ability_id=? AND status!='enabled'",
            (ABILITY_ID,),
        ).fetchone()[0]
    )
    if non_enabled:
        raise RuntimeError(f"Archery runtime retains {non_enabled} quarantined roots")
    if missing or mismatched:
        raise RuntimeError(
            f"Archery runtime verification failed: missing={missing[:20]} "
            f"mismatched={mismatched[:20]}"
        )
    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite integrity failed: quick={quick}, integrity={integrity}")
    return {
        "materialized_rows": sum(len(values) for values in rows.values()),
        "passive_roots": passive_rows,
        "ancestral_plots": list(ANCESTRAL_PLOTS),
        "concussive_mist_bubble_effect": CONCUSSIVE_MIST["bubble_effect_id"],
        "charge_skill_contracts": [list(row) for row in charge_skills],
        "charge_cooldown_effects": [list(row) for row in charge_effects],
        "unit_requirements": [list(row) for row in unit_requirements],
        "plot_unit_requirements": [list(row) for row in plot_unit_requirements],
        "owner_keyed_relations": owner_keyed_relations,
        "enabled_skill_roots": 35,
        "quick_check": quick,
        "integrity_check": integrity,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "carrier": validate_source(args.runtime_carrier, "carrier"),
        "graph": validate_source(args.graph, "graph"),
        "knowledge": validate_source(args.knowledge, "knowledge"),
        "crosswalk": validate_source(args.crosswalk, "crosswalk"),
        "game11": validate_source(args.game11, "game11"),
    }
    with ro(args.graph) as graph, ro(args.knowledge) as knowledge:
        rows, closure = collect_rows(graph, knowledge)
    native_unit_requirements, unit_req_provenance = extract_unit_requirements(args.game11)
    plot_condition_ids = {
        int(row["id"]) for row in rows.get("plot_conditions", [])
    }
    selected_plot_requirements = [
        row for row in native_unit_requirements
        if row["owner_type"] == "PlotCondition" and
           int(row["owner_id"]) in plot_condition_ids
    ]
    with ro(args.crosswalk) as crosswalk:
        crosswalk_report = crosswalk_audit(crosswalk, rows)
    # unit_reqs has no synthetic id column and therefore does not participate
    # in the id-keyed crosswalk audit above. These rows come directly from the
    # pinned AA8 game11 cached result, then enter the runtime closure here.
    rows.setdefault("unit_reqs", []).extend(selected_plot_requirements)

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
        tagged_skill_rows = rows.get("tagged_skills", [])
        tagged_skill_roots = sorted({int(row["skill_id"]) for row in tagged_skill_rows})
        if tagged_skill_roots:
            placeholders = ",".join("?" for _ in tagged_skill_roots)
            connection.execute(
                f"DELETE FROM tagged_skills WHERE skill_id IN ({placeholders})",
                tagged_skill_roots,
            )
        # tagged_buffs is another many-to-many cache boundary.  Historical
        # carrier rows commonly use a NULL synthetic id, so id-keyed upsert
        # cannot replace them and would double every natural (buff, tag) pair.
        # Replace the complete selected AA8 owner surface before inserting the
        # exact rows, just as for tagged_skills above.
        tagged_buff_rows = rows.get("tagged_buffs", [])
        tagged_buff_owners = sorted({int(row["buff_id"]) for row in tagged_buff_rows})
        if tagged_buff_owners:
            placeholders = ",".join("?" for _ in tagged_buff_owners)
            connection.execute(
                f"DELETE FROM tagged_buffs WHERE buff_id IN ({placeholders})",
                tagged_buff_owners,
            )
        changes = {
            table: upsert_rows(connection, table, values)
            for table, values in sorted(rows.items())
            if table != "unit_reqs"
        }
        unit_requirement_rows = rows.get("unit_reqs", [])
        for owner_type, owner_id in sorted({
            (str(row["owner_type"]), int(row["owner_id"]))
            for row in unit_requirement_rows
        }):
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
                for row in unit_requirement_rows
            ],
        )
        changes["unit_reqs"] = {
            "rows": len(unit_requirement_rows),
            "columns": list(unit_requirement_rows[0]) if unit_requirement_rows else [],
            "derived_fields": [],
            "historical_values_preserved": False,
        }
        connection.executemany(
            "UPDATE native_combat_skill_status SET status='enabled',reason='' "
            "WHERE ability_id=? AND skill_id=?",
            [(ABILITY_ID, skill_id) for skill_id in closure["root_skill_ids"]],
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS aa8_archery_runtime_evidence ("
            "version TEXT PRIMARY KEY, ability_id INTEGER NOT NULL, "
            "client_build TEXT NOT NULL, graph_sha256 TEXT NOT NULL, "
            "knowledge_sha256 TEXT NOT NULL, crosswalk_sha256 TEXT NOT NULL, "
            "aa10_runtime_rows INTEGER NOT NULL, selected_rows INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO aa8_archery_runtime_evidence VALUES(?,?,?,?,?,?,?,?)",
            (
                "archery-v1",
                ABILITY_ID,
                CLIENT_BUILD,
                EXPECTED_HASHES["graph"],
                EXPECTED_HASHES["knowledge"],
                EXPECTED_HASHES["crosswalk"],
                0,
                sum(len(values) for values in rows.values()),
            ),
        )
        connection.commit()
        verification = verify_runtime(connection, rows)
    finally:
        connection.close()
    temporary.replace(args.output)

    manifest = {
        "schema_version": 1,
        "runtime_version": "archery-v1",
        "client_build": CLIENT_BUILD,
        "authority": "AA8_client_native",
        "sources": sources,
        "closure": closure,
        "crosswalk": crosswalk_report,
        "native_unit_requirements": {
            "provenance": unit_req_provenance,
            "selected_plot_condition_rows": len(selected_plot_requirements),
            "selected_owner_ids": sorted(
                int(row["owner_id"]) for row in selected_plot_requirements
            ),
        },
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
        print(canonical(manifest), end="")
    else:
        print(manifest["output"]["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
