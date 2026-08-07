#!/usr/bin/env python3
"""Patch Shadowplay V1 from AA8 SQLite plus exact live-client observations."""

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
sys.path.insert(0, str(NATIVE_COMBAT))

from build_native_combat_runtime import columns, normalize, sha256_file, upsert_rows  # noqa: E402


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
EXPECTED_V1_SHA256 = "647E0A65A447595CA547F352E9867869D0650C22B33F1B1207B113D1E34A3029"
EXPECTED_LEGACY_SHA256 = "9FB1838113820D4F5BAC93BB7E79A3E51613CF7B2828B28545B59F506B4F4397"
EXPECTED_KNOWLEDGE_SHA256 = "92CDF5D1EB16DAF0C4D5ABFCB80B510DFDF827708D4F8087235CCFACE3CE3C4F"
DOSSIER_HASHES = {
    10082: "9A641DF00571E413AD49F606BD888EE5EE7C6727954FFBDC5BB3EE26EA50909F",
    10104: "AE5DEF418465D6A8594681B30CC6B2960041ABC16EF543590E1536E776444EAC",
    10189: "6C839F21A5C176982F91CCC99CF2AC3DB054EE82B6F618BDF45B629B3348FD76",
}
MATERIALIZED_ROOTS = (10082, 10104, 10189)
POISON_NATIVE_KEYS = (
    "buff:196",
    "buff:22266",
    "buff_tick_effect:56",
    "effect:791",
    "effect_detail:damage_effects:210",
    "tagged_buff:16",
    "tagged_buff:55119",
    "tagged_buff:56446",
    "tagged_buff:56469",
)
EXECUTABLE_TABLES = {
    "skill_effects",
    "effects",
    "buff_effects",
    "special_effects",
    "damage_effects",
    "buffs",
    "buff_tick_effects",
    "buff_triggers",
    "buff_unit_modifiers",
    "buff_modifiers",
    "unit_modifiers",
    "tagged_buffs",
}
POISON_TRIGGER_ID = 88000001


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--knowledge", required=True, type=Path)
    parser.add_argument("--legacy-scaffold", required=True, type=Path)
    parser.add_argument("--dossier-dir", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
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


def validate_sources(args: argparse.Namespace) -> dict[str, Any]:
    expected = {
        args.runtime_carrier: EXPECTED_V1_SHA256,
        args.legacy_scaffold: EXPECTED_LEGACY_SHA256,
        args.knowledge: EXPECTED_KNOWLEDGE_SHA256,
    }
    sources: dict[str, Any] = {}
    for path, expected_hash in expected.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        if actual != expected_hash:
            raise RuntimeError(f"Unexpected source SHA-256 for {path}: {actual}")
        sources[path.name] = {"path": str(path.resolve()), "sha256": actual}
    if not args.observations.is_file():
        raise FileNotFoundError(args.observations)
    observations = json.loads(args.observations.read_text(encoding="utf-8"))
    observed_learns = sorted(
        int(row["skill_id"])
        for row in observations["observations"]
        if row["kind"] == "learn_request"
    )
    if observed_learns != list(MATERIALIZED_ROOTS):
        raise RuntimeError(f"Unexpected observed learn requests: {observed_learns}")
    sources[args.observations.name] = {
        "path": str(args.observations.resolve()),
        "sha256": sha256_file(args.observations),
    }
    return sources


def dossier_entity_keys(args: argparse.Namespace) -> tuple[set[str], dict[str, Any]]:
    keys: set[str] = set()
    evidence: dict[str, Any] = {}
    for skill_id, expected_hash in DOSSIER_HASHES.items():
        path = args.dossier_dir / f"skill-{skill_id}.json"
        actual = sha256_file(path)
        if actual != expected_hash:
            raise RuntimeError(f"Unexpected dossier SHA-256 for skill {skill_id}: {actual}")
        dossier = json.loads(path.read_text(encoding="utf-8"))
        if dossier["root"]["entity_key"] != f"skill:{skill_id}":
            raise RuntimeError(f"Dossier root mismatch for {skill_id}")
        for node in dossier["graph"]["nodes"]:
            if node.get("path_importance") in ("required", "contextual"):
                keys.add(str(node["entity_key"]))
        evidence[str(skill_id)] = {
            "path": str(path.resolve()),
            "sha256": actual,
            "forensic_state": dossier["readiness"]["forensic"]["state"],
            "reconstruction_state": dossier["readiness"]["reconstruction"]["state"],
        }
    return keys, evidence


def exact_native_row(
    knowledge: sqlite3.Connection, entity_key: str
) -> tuple[str, dict[str, Any]] | None:
    candidates = []
    for row in knowledge.execute(
        "SELECT source_table,state,row_json,provenance FROM native_rows WHERE entity_key=?",
        (entity_key,),
    ):
        try:
            payload = json.loads(str(row["row_json"]))
        except json.JSONDecodeError:
            continue
        table = str(row["source_table"])
        if table not in EXECUTABLE_TABLES or "id" not in payload:
            continue
        candidates.append((len(payload), table, payload))
    if not candidates:
        return None
    _, table, payload = max(candidates, key=lambda value: value[0])
    return table, payload


def select_native_rows(
    knowledge: sqlite3.Connection, keys: set[str]
) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for key in sorted(keys.union(POISON_NATIVE_KEYS)):
        result = exact_native_row(knowledge, key)
        if result is None:
            continue
        table, payload = result
        selected[table][int(payload["id"])] = payload
    result = {
        table: [rows[row_id] for row_id in sorted(rows)]
        for table, rows in sorted(selected.items())
    }
    for skill_id in MATERIALIZED_ROOTS:
        if not any(
            int(row.get("skill_id", 0)) == skill_id
            for row in result.get("skill_effects", [])
        ):
            raise RuntimeError(f"Dossier did not yield AA8 skill_effects for {skill_id}")
    return result


def full_legacy_root(
    runtime: sqlite3.Connection, source: sqlite3.Row, ability_id: int
) -> dict[str, Any]:
    result = dict(source)
    result["ability_id"] = ability_id
    for name, sql_type in columns(runtime, "skills").items():
        if name in result:
            continue
        result[name] = None if "TEXT" in sql_type.upper() else 0
    result["need_learn"] = 1
    result["skill_points"] = 1
    result["req_points"] = 0
    return result


def poison_trigger() -> dict[str, Any]:
    return {
        "id": POISON_TRIGGER_ID,
        "buff_id": 22266,
        "check_no_tag_src_in_owner": 0,
        "check_no_tag_src_in_source": 0,
        "check_no_tag_src_in_target": 0,
        "check_tag_src_in_owner": 0,
        "check_tag_src_in_source": 0,
        "check_tag_src_in_target": 0,
        "delay_time": 0,
        "effect_id": 720,
        "event_id": 1,
        "owner_buff_tag_id": 0,
        "owner_no_buff_tag_id": 0,
        "source_agent_id": 3,
        "source_buff_tag_id": 0,
        "source_no_buff_tag_id": 0,
        "target_agent_id": 2,
        "target_buff_tag_id": 0,
        "target_no_buff_tag_id": 0,
        "use_collision_impact": 0,
        "use_damage_amount": 0,
        "use_stack_count": 0,
        "or_unit_reqs": 0,
    }


def verify_runtime(
    connection: sqlite3.Connection,
    native: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    errors = []
    for table, rows in native.items():
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
    roots = list(
        connection.execute(
            "SELECT id,ability_id,skill_points,req_points,need_learn FROM skills "
            "WHERE id IN (10082,10104,10189) ORDER BY id"
        )
    )
    if [tuple(row) for row in roots] != [
        (10082, 8, 1, 0, 1),
        (10104, 8, 1, 0, 1),
        (10189, 8, 1, 0, 1),
    ]:
        errors.append(f"Materialized root contract mismatch: {[tuple(row) for row in roots]}")
    trigger = connection.execute(
        "SELECT buff_id,effect_id,event_id,source_agent_id,target_agent_id "
        "FROM buff_triggers WHERE id=?", (POISON_TRIGGER_ID,)
    ).fetchone()
    if trigger is None or tuple(trigger) != (22266, 720, 1, 3, 2):
        errors.append("Poisoned Weapons trigger bridge mismatch")
    if connection.execute(
        "SELECT remove_on_attack_buff_trigger FROM buffs WHERE id=22266"
    ).fetchone()[0] != 0:
        errors.append("AA8 buff 22266 was altered instead of preserving its native row")
    passives = list(connection.execute(
        "SELECT req_points,skill_points FROM passive_buffs WHERE ability_id=8 ORDER BY req_points"
    ))
    if [tuple(row) for row in passives] != [(3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0)]:
        errors.append(f"Passive accounting differs from AA8: {[tuple(row) for row in passives]}")
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite integrity failed: {quick}/{integrity}")
    if errors:
        raise RuntimeError("\n".join(errors))
    return {
        "integrity_check": integrity,
        "materialized_roots": list(MATERIALIZED_ROOTS),
        "passive_policy": "skill_points_zero_req_points_gate",
        "poison_bridge": {
            "trigger_id": POISON_TRIGGER_ID,
            "self_buff_id": 22266,
            "target_buff_id": 196,
        },
        "quick_check": quick,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    sources = validate_sources(args)
    keys, dossiers = dossier_entity_keys(args)
    knowledge = ro(args.knowledge)
    legacy = ro(args.legacy_scaffold)
    try:
        native = select_native_rows(knowledge, keys)
        legacy_roots = []
        for skill_id in MATERIALIZED_ROOTS:
            row = legacy.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
            if row is None:
                raise RuntimeError(f"Legacy scaffold root {skill_id} is absent")
            legacy_roots.append(row)
        bridge_effect = dict(legacy.execute("SELECT * FROM effects WHERE id=720").fetchone())
        bridge_detail = dict(legacy.execute("SELECT * FROM buff_effects WHERE id=256").fetchone())
    finally:
        knowledge.close()
        legacy.close()

    output = args.output.resolve()
    if output == args.runtime_carrier.resolve():
        raise ValueError("Output must not replace the V1 carrier")
    output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.runtime_carrier, output)
    connection = sqlite3.connect(output)
    try:
        connection.row_factory = sqlite3.Row
        roots = [full_legacy_root(connection, row, 8) for row in legacy_roots]
        merge = {"skills": upsert_rows(connection, "skills", roots)}
        for table, rows in native.items():
            merge[table] = upsert_rows(connection, table, rows)
        merge["legacy_bridge_effect"] = upsert_rows(connection, "effects", [bridge_effect])
        merge["legacy_bridge_detail"] = upsert_rows(connection, "buff_effects", [bridge_detail])
        merge["poison_trigger"] = upsert_rows(connection, "buff_triggers", [poison_trigger()])
        connection.executemany(
            "INSERT INTO native_combat_skill_status(skill_id,ability_id,status,reason,provenance) "
            "VALUES(?,8,'enabled',?,?) ON CONFLICT(skill_id) DO UPDATE SET "
            "ability_id=excluded.ability_id,status=excluded.status,reason=excluded.reason,"
            "provenance=excluded.provenance",
            [
                (
                    skill_id,
                    "AA8 live client requested exact skill ID; root lifecycle omitted; "
                    "minimal same-ID legacy scaffold with AA8-native executable closure",
                    "aa8_shadowplay_v2_live_packet_plus_native_dossier",
                )
                for skill_id in MATERIALIZED_ROOTS
            ],
        )
        connection.execute(
            "UPDATE native_combat_skill_status SET reason=?,provenance=? WHERE skill_id=10481",
            (
                "AA8 self buff plus exact native Poison payload; minimal server-only trigger bridge",
                "aa8_shadowplay_v2_poison_trigger_bridge",
            ),
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS shadowplay_reconstruction_v2_metadata("
            "key TEXT PRIMARY KEY,value TEXT NOT NULL,provenance TEXT NOT NULL)"
        )
        metadata = {
            "client_build": CLIENT_BUILD,
            "materialized_missing_roots": "10082,10104,10189",
            "passive_point_policy": "free_unlocks_gated_by_req_points",
            "poison_payload": "22266->trigger:88000001->effect:720->buff:196->tick:56->effect:791",
            "wiki_authority": "corroboration_only",
        }
        connection.executemany(
            "INSERT INTO shadowplay_reconstruction_v2_metadata(key,value,provenance) "
            "VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,"
            "provenance=excluded.provenance",
            [(key, value, "aa8_shadowplay_v2") for key, value in sorted(metadata.items())],
        )
        connection.commit()
        verification = verify_runtime(connection, native) if args.verify else None
        connection.execute("VACUUM")
    except Exception:
        connection.close()
        output.unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    manifest = {
        "authority": {
            "aa8_sqlite": "runtime_contract",
            "live_packets_and_logs": "acceptance_evidence",
            "legacy": "minimal_same_id_root_and_server_only_trigger_scaffold",
            "wiki": "corroboration_only",
        },
        "client_build": CLIENT_BUILD,
        "dossiers": dossiers,
        "format_version": 2,
        "merge": merge,
        "native_table_ids": {
            table: [int(row["id"]) for row in rows]
            for table, rows in sorted(native.items())
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
