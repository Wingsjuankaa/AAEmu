#!/usr/bin/env python3
"""Materialize AA8-native heir skill data on top of Sorcery runtime v6."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SORCERY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from reconstruccion_cliente_8.client_forensics.world_actors import CachedResultReader  # noqa: E402


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v6.sqlite3"
)
DEFAULT_BASE_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v6.manifest.json"
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v7.sqlite3"
)
DEFAULT_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v7.manifest.json"
EXPECTED_HASHES = {
    "base": "FD9B16F571628B869B1B0356ECFB5A432904063F94E3BB33392673471198B133",
    "base_manifest": "6DB3328CFE5420226B4A726ED7875B9704CDCF63BC4E321BB558261E699FC495",
    "game11": "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
}

HEIR_RESULT_SPECS = {
    "heir_levels": {
        "loader_x64": "FUN_3993b660",
        "sql": (
            "SELECT id, level, req_item_count, req_item_id, req_total_exp, step "
            "FROM heir_levels"
        ),
        "columns": (
            "id",
            "level",
            "req_item_count",
            "req_item_id",
            "req_total_exp",
            "step",
        ),
        "layout": ("68", "68", "68", "68", "70", "68"),
        "start": 113_965_013,
        "done": 113_967_072,
        "rows": 71,
        "first_string_reference": None,
        "next_string_reference": None,
    },
    "heir_skill_details": {
        "loader_x64": "FUN_399d1530",
        "sql": (
            "SELECT id, active_item_id, desc, heir_skill_id, pos, "
            "skill_active_type_id, skill_id FROM heir_skill_details"
        ),
        "columns": (
            "id",
            "active_item_id",
            "desc",
            "heir_skill_id",
            "pos",
            "skill_active_type_id",
            "skill_id",
        ),
        "layout": ("68", "68", "78", "68", "68", "68", "68"),
        "start": 143_882_320,
        "done": 143_887_105,
        "rows": 159,
        "first_string_reference": 406_799,
        "next_string_reference": 406_802,
    },
    "heir_skills": {
        "loader_x64": "FUN_399d1850",
        "sql": "SELECT id, skill_id, step FROM heir_skills WHERE enable = 't'",
        "columns": ("id", "skill_id", "step"),
        "layout": ("68", "68", "68"),
        "start": 143_887_111,
        "done": 143_888_125,
        "rows": 78,
        "first_string_reference": None,
        "next_string_reference": None,
    },
}

SORCERY_HEIR_SKILLS = {
    19: (10752, 1, ((36474, 1), (36475, 8))),
    20: (11967, 2, ((36476, 1), (36477, 5))),
    21: (10664, 3, ((36478, 5), (36479, 8))),
    40: (23593, 4, ((39669, 8), (39674, 5))),
    52: (14774, 5, ((41222, 5), (41223, 6))),
    58: (12796, 6, ((43068, 3), (43185, 1))),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def verify_hash(path: Path, expected: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Unexpected SHA-256 for {path}: {actual} != {expected}")
    return actual


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def decode_heir_results(game11: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    payload = game11.read_bytes()
    decoded: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, Any] = {}
    for table, spec in HEIR_RESULT_SPECS.items():
        reader = CachedResultReader(payload, spec["first_string_reference"])
        cursor = int(spec["start"])
        rows: list[dict[str, Any]] = []
        for row_index in range(int(spec["rows"])):
            values, cursor = reader.row(cursor, list(spec["layout"]))
            rows.append(dict(zip(spec["columns"], values, strict=True)))
        if cursor != int(spec["done"]) or payload[cursor] != 101:
            raise RuntimeError(f"Unexpected {table} SQLITE_DONE boundary: {cursor}")
        if reader.unresolved:
            raise RuntimeError(f"Unresolved {table} string references: {reader.unresolved}")
        if reader.next_reference != spec["next_string_reference"]:
            raise RuntimeError(f"Unexpected {table} string cache endpoint")
        decoded[table] = rows
        evidence[table] = {
            "loader_x64": spec["loader_x64"],
            "sql": spec["sql"],
            "columns": list(spec["columns"]),
            "layout": list(spec["layout"]),
            "start": spec["start"],
            "done": spec["done"],
            "rows": len(rows),
            "first_string_reference": spec["first_string_reference"],
            "next_string_reference": reader.next_reference,
            "tokens": dict(sorted(reader.tokens.items())),
            "row_sha256": hashlib.sha256(
                json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest().upper(),
        }
    return decoded, evidence


def validate_sorcery_mapping(decoded: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    skills = {int(row["id"]): row for row in decoded["heir_skills"]}
    details: dict[int, list[dict[str, Any]]] = {}
    for row in decoded["heir_skill_details"]:
        details.setdefault(int(row["heir_skill_id"]), []).append(row)
    result: list[dict[str, Any]] = []
    for heir_id, (base_skill_id, step, successors) in SORCERY_HEIR_SKILLS.items():
        actual_skill = skills.get(heir_id)
        if actual_skill != {"id": heir_id, "skill_id": base_skill_id, "step": step}:
            raise RuntimeError(f"AA8 Sorcery heir skill mismatch: {heir_id}: {actual_skill}")
        actual_successors = sorted(
            (int(row["skill_id"]), int(row["pos"])) for row in details.get(heir_id, [])
        )
        if actual_successors != sorted(successors):
            raise RuntimeError(
                f"AA8 Sorcery successor mismatch: {heir_id}: {actual_successors}"
            )
        result.append(
            {
                "heir_skill_id": heir_id,
                "base_skill_id": base_skill_id,
                "step": step,
                "successors": [
                    {
                        "skill_id": int(row["skill_id"]),
                        "pos": int(row["pos"]),
                        "skill_active_type_id": int(row["skill_active_type_id"]),
                        "active_item_id": int(row["active_item_id"]),
                    }
                    for row in sorted(details[heir_id], key=lambda value: int(value["skill_id"]))
                ],
            }
        )
    return result


def materialize(connection: sqlite3.Connection, decoded: dict[str, list[dict[str, Any]]]) -> None:
    connection.execute("DROP TABLE IF EXISTS heir_levels")
    connection.execute("DROP TABLE IF EXISTS heir_skill_details")
    connection.execute("DROP TABLE IF EXISTS heir_skills")
    connection.execute(
        "CREATE TABLE heir_levels("
        "id INTEGER PRIMARY KEY NOT NULL,level INTEGER DEFAULT 0 NOT NULL,"
        "req_item_count INTEGER DEFAULT 0 NOT NULL,req_item_id INTEGER DEFAULT 0 NOT NULL,"
        "req_total_exp INTEGER DEFAULT 0 NOT NULL,step INTEGER DEFAULT 0 NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE heir_skills("
        "id INTEGER PRIMARY KEY NOT NULL,skill_id INTEGER DEFAULT 0 NOT NULL,"
        "step INTEGER DEFAULT 0 NOT NULL,enable BOOLEAN DEFAULT 't' NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE heir_skill_details("
        "id INTEGER PRIMARY KEY NOT NULL,heir_skill_id INTEGER NOT NULL,"
        "skill_id INTEGER DEFAULT 0 NOT NULL,pos INTEGER DEFAULT 0 NOT NULL,"
        "skill_active_type_id INTEGER DEFAULT 2 NOT NULL,desc TEXT DEFAULT '',"
        "active_item_id INTEGER DEFAULT 0 NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO heir_levels("
        "id,level,req_item_count,req_item_id,req_total_exp,step"
        ") VALUES(?,?,?,?,?,?)",
        [
            tuple(row[column] for column in HEIR_RESULT_SPECS["heir_levels"]["columns"])
            for row in decoded["heir_levels"]
        ],
    )
    connection.executemany(
        "INSERT INTO heir_skills(id,skill_id,step,enable) VALUES(?,?,?,'t')",
        [(row["id"], row["skill_id"], row["step"]) for row in decoded["heir_skills"]],
    )
    connection.executemany(
        "INSERT INTO heir_skill_details("
        "id,active_item_id,desc,heir_skill_id,pos,skill_active_type_id,skill_id"
        ") VALUES(?,?,?,?,?,?,?)",
        [
            tuple(row[column] for column in HEIR_RESULT_SPECS["heir_skill_details"]["columns"])
            for row in decoded["heir_skill_details"]
        ],
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.base, args.base_manifest, args.game11):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hashes = {
        "base": verify_hash(args.base, EXPECTED_HASHES["base"]),
        "base_manifest": verify_hash(args.base_manifest, EXPECTED_HASHES["base_manifest"]),
        "game11": verify_hash(args.game11, EXPECTED_HASHES["game11"]),
    }
    decoded, decoder_evidence = decode_heir_results(args.game11)
    sorcery_mapping = validate_sorcery_mapping(decoded)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.base, args.output)
    connection = sqlite3.connect(args.output)
    try:
        materialize(connection, decoded)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS sorcery_heir_aa8_v7_evidence("
            "table_name TEXT NOT NULL,row_id INTEGER NOT NULL,row_json TEXT NOT NULL,"
            "PRIMARY KEY(table_name,row_id)) WITHOUT ROWID"
        )
        connection.execute("DELETE FROM sorcery_heir_aa8_v7_evidence")
        for table in ("heir_levels", "heir_skill_details", "heir_skills"):
            connection.executemany(
                "INSERT INTO sorcery_heir_aa8_v7_evidence VALUES(?,?,?)",
                [
                    (table, int(row["id"]), json.dumps(row, ensure_ascii=False, sort_keys=True))
                    for row in decoded[table]
                ],
            )
        connection.commit()
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        counts = {
            table: int(connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
            for table in ("heir_levels", "heir_skill_details", "heir_skills")
        }
    finally:
        connection.close()
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite verification failed: {quick}/{integrity}")
    manifest = {
        "format_version": 7,
        "client_build": CLIENT_BUILD,
        "sources": {
            "base": {"path": str(args.base.resolve()), "sha256": source_hashes["base"]},
            "base_manifest": {
                "path": str(args.base_manifest.resolve()),
                "sha256": source_hashes["base_manifest"],
            },
            "game11": {"path": str(args.game11.resolve()), "sha256": source_hashes["game11"]},
        },
        "authority": {
            "heir_skill_rows": "aa8_game11_native_direct",
            "aa10_crosswalk_role": "candidate_and_independent_identity_confirmation_only",
            "protocol_and_behavior": "not_inferred_from_data_tables",
        },
        "scope": {
            "table_counts": counts,
            "sorcery_heir_families": len(sorcery_mapping),
            "sorcery_successor_skills": sum(len(row["successors"]) for row in sorcery_mapping),
        },
        "decoder_evidence": decoder_evidence,
        "sorcery_mapping": sorcery_mapping,
        "verification": {"quick_check": quick, "integrity_check": integrity},
        "output": {"path": str(args.output.resolve()), "sha256": sha256_file(args.output)},
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(canonical_json(manifest), encoding="utf-8")
    return manifest


def main() -> int:
    manifest = build(parse_args())
    print(canonical_json({"output": manifest["output"], "scope": manifest["scope"]}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
