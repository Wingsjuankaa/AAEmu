#!/usr/bin/env python3
"""Promote the Sorcery doodad closure from AA10 candidates to direct AA8 evidence."""

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

from reconstruccion_cliente_8.client_forensics.nuia_story_graph import (  # noqa: E402
    DOODAD_RESULT_SPECS,
    _decode_result,
)


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v5.sqlite3"
)
DEFAULT_BASE_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v5.manifest.json"
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v6.sqlite3"
)
DEFAULT_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v6.manifest.json"
EXPECTED_HASHES = {
    "base": "FFD3864120ABC39D2CB5B0D62FED73602D2055F6D0A750401045785258659E30",
    "base_manifest": "D588B26508F870D7FF32B80550F6107CAD30F1590D7B8F7D59DFCD63B0AA09F8",
    "game11": "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
}
TARGET_IDS = {
    "doodad_func_groups": (38626, 38627, 38628, 38629, 38630, 43090, 43245),
    "doodad_phase_funcs": (49136, 49137, 49339, 49340, 49913, 55165, 55330),
    "doodad_func_clouts": (4116, 4121),
    "doodad_func_timers": (16372, 16373),
    "doodad_func_finals": (5304, 5305, 5320),
}
BOOLEAN_FIELDS = {
    "doodad_func_groups": {"is_msg_to_world", "is_msg_to_zone", "use_ui_msg"},
    "doodad_func_clouts": {
        "check_no_target_tag_src",
        "check_projectile_high_priority",
        "check_target_tag_src",
        "show_to_friendly_only",
        "target_parent",
        "use_origin_source",
    },
    "doodad_func_timers": {
        "keep_requester",
        "reset_first_interaction",
        "show_end_time",
        "show_tip",
    },
    "doodad_func_finals": {"respawn", "show_end_time", "show_tip"},
}
NULLABLE_ZERO_FIELDS = {
    "doodad_func_groups": {"msg_to_faction_id", "sound_id"},
    "doodad_func_clouts": {"fx_group_id", "target_buff_tag_id"},
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def runtime_value(table: str, field: str, value: Any) -> Any:
    if field in BOOLEAN_FIELDS.get(table, set()):
        return "t" if int(value or 0) else "f"
    if field in NULLABLE_ZERO_FIELDS.get(table, set()) and int(value or 0) == 0:
        return None
    return value


def decode_scope(game11: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    payload = game11.read_bytes()
    selected: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, Any] = {}
    for table, ids in TARGET_IDS.items():
        spec = dict(DOODAD_RESULT_SPECS[table])
        rows, decoder = _decode_result(payload, table, spec)
        wanted = set(ids)
        selected[table] = [row for row in rows if int(row["id"]) in wanted]
        found = {int(row["id"]) for row in selected[table]}
        if found != wanted:
            raise RuntimeError(f"AA8 {table} closure mismatch: {sorted(found)}")
        evidence[table] = decoder
    return selected, evidence


def compare_runtime(
    connection: sqlite3.Connection,
    selected: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    output: list[dict[str, Any]] = []
    counts = {"exact_fields": 0, "reference_resolved_fields": 0, "schema_defaults": 0}
    for table in TARGET_IDS:
        available = [
            str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')
        ]
        for raw in selected[table]:
            current_row = connection.execute(
                f'SELECT * FROM "{table}" WHERE id=?', (int(raw["id"]),)
            ).fetchone()
            if current_row is None:
                raise RuntimeError(f"Runtime row missing: {table}.{raw['id']}")
            current = dict(current_row)
            fields: dict[str, str] = {}
            for field, value in raw.items():
                if field not in available:
                    raise RuntimeError(f"Runtime column missing: {table}.{field}")
                if isinstance(value, str) and value.startswith("<ref:"):
                    if current[field] in (None, ""):
                        raise RuntimeError(
                            f"Unresolved AA8 reference has no bounded value: {table}.{raw['id']}.{field}"
                        )
                    fields[field] = "exact_aa8_reference_identity_resolved_by_stable_aa10_row"
                    counts["reference_resolved_fields"] += 1
                    continue
                expected = runtime_value(table, field, value)
                if current[field] != expected:
                    raise RuntimeError(
                        f"AA8 runtime mismatch {table}.{raw['id']}.{field}: "
                        f"{current[field]!r} != {expected!r}"
                    )
                fields[field] = "exact_aa8_native"
                counts["exact_fields"] += 1
            for field in sorted(set(available).difference(raw)):
                if field == "comment" and current[field] == "":
                    fields[field] = "runtime_schema_default"
                    counts["schema_defaults"] += 1
                else:
                    raise RuntimeError(
                        f"Unclassified runtime-only field {table}.{raw['id']}.{field}"
                    )
            output.append(
                {
                    "table": table,
                    "row_id": int(raw["id"]),
                    "classification": (
                        "aa8_native_with_bounded_string_reference_resolution"
                        if any("reference" in state for state in fields.values())
                        else "aa8_native_exact"
                    ),
                    "fields": fields,
                    "native_row": raw,
                    "runtime_row": current,
                }
            )
    return output, counts


def build(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.base, args.base_manifest, args.game11):
        if not path.is_file():
            raise FileNotFoundError(path)
    sources = {
        "base": verify_hash(args.base, EXPECTED_HASHES["base"]),
        "base_manifest": verify_hash(
            args.base_manifest, EXPECTED_HASHES["base_manifest"]
        ),
        "game11": verify_hash(args.game11, EXPECTED_HASHES["game11"]),
    }
    selected, decoder_evidence = decode_scope(args.game11)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.base, args.output)
    connection = sqlite3.connect(args.output)
    connection.row_factory = sqlite3.Row
    try:
        rows, counts = compare_runtime(connection, selected)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS sorcery_doodad_aa8_v6_evidence("
            "table_name TEXT NOT NULL,row_id INTEGER NOT NULL,classification TEXT NOT NULL,"
            "field_states_json TEXT NOT NULL,native_row_json TEXT NOT NULL,"
            "runtime_row_json TEXT NOT NULL,PRIMARY KEY(table_name,row_id)) WITHOUT ROWID"
        )
        connection.execute("DELETE FROM sorcery_doodad_aa8_v6_evidence")
        connection.executemany(
            "INSERT INTO sorcery_doodad_aa8_v6_evidence VALUES(?,?,?,?,?,?)",
            [
                (
                    row["table"],
                    row["row_id"],
                    row["classification"],
                    json.dumps(row["fields"], ensure_ascii=False, sort_keys=True),
                    json.dumps(row["native_row"], ensure_ascii=False, sort_keys=True),
                    json.dumps(row["runtime_row"], ensure_ascii=False, sort_keys=True),
                )
                for row in rows
            ],
        )
        metadata = {
            "sorcery_doodad_authority": "aa8_game11_native_direct",
            "sorcery_doodad_structural_candidates": "promoted_from_aa10_candidate_to_aa8_native",
            "sorcery_doodad_reference_resolution": "aa8_reference_identity_plus_stable_aa10_literal",
        }
        for key, value in metadata.items():
            connection.execute(
                "INSERT INTO sorcery_reconstruction_v4_metadata(key,value,provenance) "
                "VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,"
                "provenance=excluded.provenance",
                (key, value, "aa8_sorcery_v6"),
            )
        connection.commit()
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        connection.close()
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite verification failed: {quick}/{integrity}")

    manifest = {
        "format_version": 6,
        "client_build": CLIENT_BUILD,
        "sources": {
            "base": {"path": str(args.base.resolve()), "sha256": sources["base"]},
            "base_manifest": {
                "path": str(args.base_manifest.resolve()),
                "sha256": sources["base_manifest"],
            },
            "game11": {"path": str(args.game11.resolve()), "sha256": sources["game11"]},
        },
        "authority": {
            "doodad_rows": "aa8_game11_native_direct",
            "unresolved_string_literals": "stable_aa10_row_crosswalk_only",
            "balance_protocol_and_behavior": "unchanged_from_v5",
        },
        "scope": {
            "tables": {table: list(ids) for table, ids in TARGET_IDS.items()},
            "rows": len(rows),
            "field_counts": counts,
        },
        "decoder_evidence": decoder_evidence,
        "rows": rows,
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
