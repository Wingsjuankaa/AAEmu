#!/usr/bin/env python3
"""Restore the confirmed AA8 Insulating Lens absorption trigger over runtime v8."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v8.sqlite3"
)
DEFAULT_STAGE50 = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\stage-50-skills.sqlite"
)
DEFAULT_CROSSWALK = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3"
)
DEFAULT_AA10 = Path(
    r"E:\AAEmu-Research\test\ArcheAge Returns 10.0.2.13 - 8yx - r575 - 2026-06-18"
    r"\game\db\game.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v9.sqlite3"
)
DEFAULT_MANIFEST = (
    Path(__file__).with_name("generated") / "sorcery-specialization-v9.manifest.json"
)

EXPECTED_HASHES = {
    "base": "F441B45D72009D6B649EA3FD5B02BB831FFA2FA360C253D97789CBAA1DB16067",
    "stage50": "B15853F5E1D24FC9FAF77C9F4F1697262F32525E6CCDE4EC96D943DD938E9E07",
    "crosswalk": "44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71",
    "aa10": "87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F",
}

TRIGGER = {
    "id": 9738,
    "buff_id": 95,
    "check_no_tag_src_in_owner": 0,
    "check_no_tag_src_in_source": 0,
    "check_no_tag_src_in_target": 0,
    "check_tag_src_in_owner": 0,
    "check_tag_src_in_source": 0,
    "check_tag_src_in_target": 0,
    "delay_time": 0,
    "effect_id": 67353,
    "event_id": 29,
    "or_unit_reqs": 0,
    "owner_buff_tag_id": 0,
    "owner_no_buff_tag_id": 0,
    "source_agent_id": 0,
    "source_buff_tag_id": 0,
    "source_no_buff_tag_id": 0,
    "target_agent_id": 0,
    "target_buff_tag_id": 0,
    "target_no_buff_tag_id": 0,
    "use_collision_impact": 0,
    "use_damage_amount": 0,
    "use_stack_count": 0,
}

EFFECT = {"id": 67353, "actual_type": "SpecialEffect", "actual_id": 31561}
SPECIAL = {
    "id": 31561,
    "special_effect_type_id": 33,
    "value1": 37837,
    "value2": 0,
    "value3": 0,
    "value4": 0,
    "value5": 0,
    "value6": 0,
    "value7": 0,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def row(connection: sqlite3.Connection, sql: str, args: tuple[Any, ...] = ()) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    value = connection.execute(sql, args).fetchone()
    if value is None:
        raise RuntimeError(f"Required row missing: {sql} {args}")
    return dict(value)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--stage50", type=Path, default=DEFAULT_STAGE50)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--aa10", type=Path, default=DEFAULT_AA10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def validate_sources(args: argparse.Namespace) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, expected in EXPECTED_HASHES.items():
        path = getattr(args, name)
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"Unexpected SHA-256 for {path}: {actual} != {expected}")
        hashes[name] = actual

    with closing(sqlite3.connect(args.base)) as connection:
        if connection.execute("SELECT count(*) FROM buff_triggers WHERE id=9738").fetchone()[0]:
            raise RuntimeError("Runtime v8 unexpectedly already contains trigger 9738")
        if connection.execute("SELECT count(*) FROM effects WHERE id=67353").fetchone()[0]:
            raise RuntimeError("Runtime v8 unexpectedly already contains effect 67353")
        if connection.execute("SELECT count(*) FROM special_effects WHERE id=31561").fetchone()[0]:
            raise RuntimeError("Runtime v8 unexpectedly already contains special effect 31561")
        if connection.execute("SELECT count(*) FROM skills WHERE id=37837").fetchone()[0] != 1:
            raise RuntimeError("AA8 Ice Shield skill 37837 missing")
        if connection.execute("SELECT count(*) FROM buffs WHERE id=94 AND root=1").fetchone()[0] != 1:
            raise RuntimeError("AA8 Ice Shard root buff 94 missing")

    with closing(sqlite3.connect(args.stage50)) as connection:
        cached = json.loads(row(
            connection,
            "SELECT row_json FROM cached_result_rows WHERE query_key=? AND row_index=?",
            ("stage50:query:115:buff_triggers", 5272),
        )["row_json"])
        if cached != TRIGGER:
            raise RuntimeError(f"Unexpected AA8 native trigger row: {cached}")
        cached_effect = json.loads(row(
            connection,
            "SELECT row_json FROM cached_result_rows WHERE query_key=? AND row_index=?",
            ("stage50:query:103:effects", 41494),
        )["row_json"])
        cached_special = json.loads(row(
            connection,
            "SELECT row_json FROM cached_result_rows WHERE query_key=? AND row_index=?",
            ("stage50:query:59:special_effects", 19281),
        )["row_json"])
        if cached_effect != EFFECT or cached_special != SPECIAL:
            raise RuntimeError("AA8 native trigger dependencies changed")

    with closing(sqlite3.connect(args.crosswalk)) as connection:
        comparison = row(
            connection,
            "SELECT classification,relation_state,property_state,balance_state,aa8_row_sha256 "
            "FROM row_comparisons WHERE table_name='buff_triggers' AND aa8_id='9738'",
        )
        expected = {
            "classification": "stable_id_changed_properties",
            "relation_state": "stable",
            "property_state": "changed",
            "balance_state": "exact_or_absent",
            "aa8_row_sha256": "9B744BBE82AA260FFDCA6D3BB409F362B6DD4FC9967C883B29B7765D7339EB33",
        }
        if comparison != expected:
            raise RuntimeError(f"Unexpected crosswalk classification: {comparison}")
        for table, native_id in (("effects", "67353"), ("special_effects", "31561")):
            dependency = row(
                connection,
                "SELECT classification,relation_state,property_state,balance_state "
                "FROM row_comparisons WHERE table_name=? AND aa8_id=?",
                (table, native_id),
            )
            if dependency != {
                "classification": "exact_id_exact_relation",
                "relation_state": "stable",
                "property_state": "exact",
                "balance_state": "exact_or_absent",
            }:
                raise RuntimeError(f"Unexpected crosswalk dependency {table}:{native_id}: {dependency}")

    with closing(sqlite3.connect(args.aa10)) as connection:
        aa10 = row(connection, "SELECT * FROM buff_triggers WHERE id=9738")
        for key, value in TRIGGER.items():
            normalized = 1 if aa10[key] == "t" else 0 if aa10[key] == "f" else aa10[key]
            if normalized != value:
                raise RuntimeError(f"AA10 trigger mismatch at {key}: {normalized} != {value}")
        if aa10.get("enable") != "t":
            raise RuntimeError("AA10 stable trigger is not enabled")
        if row(connection, "SELECT * FROM effects WHERE id=67353") != EFFECT:
            raise RuntimeError("AA10 effect 67353 differs from AA8")
        if row(connection, "SELECT * FROM special_effects WHERE id=31561") != SPECIAL:
            raise RuntimeError("AA10 special effect 31561 differs from AA8")

    return hashes


def build(args: argparse.Namespace) -> dict[str, Any]:
    hashes = validate_sources(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.base, args.output)

    with closing(sqlite3.connect(args.output)) as connection:
        special_columns = list(SPECIAL)
        connection.execute(
            f"INSERT INTO special_effects({','.join(special_columns)}) "
            f"VALUES({','.join('?' for _ in special_columns)})",
            tuple(SPECIAL[column] for column in special_columns),
        )
        effect_columns = list(EFFECT)
        connection.execute(
            f"INSERT INTO effects({','.join(effect_columns)}) "
            f"VALUES({','.join('?' for _ in effect_columns)})",
            tuple(EFFECT[column] for column in effect_columns),
        )
        columns = list(TRIGGER)
        connection.execute(
            f"INSERT INTO buff_triggers({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
            tuple(TRIGGER[column] for column in columns),
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS sorcery_absorption_v9_evidence("
            "evidence_key TEXT PRIMARY KEY,evidence_value TEXT NOT NULL)"
        )
        evidence = {
            "aa8_native_query": "stage50:query:115:buff_triggers row_index=5272",
            "aa8_trigger": "9738:buff95:absorption29:effect67353",
            "effect_chain": "67353->SpecialEffect31561->SkillUse37837->BuffEffect67349->buff94",
            "aa8_native_effect": "stage50:query:103:effects row_index=41494",
            "aa8_native_special": "stage50:query:59:special_effects row_index=19281",
            "crosswalk": "stable_id_changed_properties;relation_state=stable",
            "aa10_difference": "only enable column absent from AA8 projection",
            "cooldown_contract": "buff95 cooldown_skill_id=10153 cooldown_skill_time=30000",
        }
        connection.executemany(
            "INSERT OR REPLACE INTO sorcery_absorption_v9_evidence VALUES(?,?)",
            sorted(evidence.items()),
        )
        connection.commit()
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        inserted = row(connection, "SELECT * FROM buff_triggers WHERE id=9738")
        inserted_effect = row(connection, "SELECT * FROM effects WHERE id=67353")
        inserted_special = row(connection, "SELECT * FROM special_effects WHERE id=31561")
        if (inserted != TRIGGER or inserted_effect != EFFECT
                or inserted_special != SPECIAL or quick != "ok" or integrity != "ok"):
            raise RuntimeError("Runtime v9 validation failed")

    manifest = {
        "format_version": 9,
        "client_build": "Kakao 8.0.3.12 r558734",
        "authority": {
            "trigger": "exact AA8 native cached row",
            "crosswalk": "stable corroboration only",
            "aa10": "schema/enable corroboration only",
        },
        "sources": {
            name: {"path": str(getattr(args, name)), "sha256": value}
            for name, value in hashes.items()
        },
        "restored_trigger": TRIGGER,
        "restored_effect": EFFECT,
        "restored_special_effect": SPECIAL,
        "closure": [
            "buff:95", "buff_trigger:9738", "effect:67353", "special_effect:31561",
            "skill:37837", "effect:67349", "buff:94",
        ],
        "verification": {"quick_check": quick, "integrity_check": integrity},
        "output": {"path": str(args.output), "sha256": sha256_file(args.output)},
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    manifest = build(parse_args())
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
