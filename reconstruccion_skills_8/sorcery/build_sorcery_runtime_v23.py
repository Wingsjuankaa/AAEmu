#!/usr/bin/env python3
"""Close AA8 Gods' Whip spatial sampling and Flame Barrier Mist damage data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reconstruccion_cliente_8.client_forensics.nuia_story_graph import (  # noqa: E402
    DOODAD_RESULT_SPECS,
    _decode_result,
)


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-honor-store-v1.sqlite3"
)
DEFAULT_STAGE50 = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\stage-50-skills.sqlite"
)
DEFAULT_CROSSWALK = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3"
)
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-sorcery-v23.sqlite3"
)
DEFAULT_MANIFEST = (
    Path(__file__).with_name("generated") / "sorcery-runtime-v23.manifest.json"
)

EXPECTED_BASE_SHA256 = (
    "C9D7E78196CC2563DB61498B566E9785A1850D2D869E4878E22287E6A79BC258"
)
EXPECTED_GAME11_SHA256 = (
    "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031"
)
EXPECTED_RELATION_ROWS = 768
EXPECTED_RELATION_SHA256 = (
    "47D2CFF5B1C7753445B58223DFAC000AC9EA2BFA7F2B1A841D5DA3DE39873C8E"
)

SOURCE_ROWS = {
    "effects": (76542, 76543),
    "buff_effects": (29874,),
    "buffs": (24585,),
    "buff_tick_effects": (4167,),
    "damage_effects": (12209,),
    "tagged_buffs": (61411, 61412, 61413, 61611),
}

QUERY_KEYS = {
    "effects": "stage50:query:103:effects",
    "buff_effects": "stage50:query:55:buff_effects",
    "buffs": "stage50:query:119:buffs",
    "buff_tick_effects": "stage50:query:116:buff_tick_effects",
    "damage_effects": "stage50:query:51:damage_effects",
    "tagged_buffs": "stage50:query:114:tagged_buffs",
}

RUNTIME_ALIASES = {
    "max_combat_resource": "max_high_ability_resource",
    "min_combat_resource": "min_high_ability_resource",
    "combat_resource_dps_md": "high_ability_resource_dps_md",
    "combat_resource_level_md": "high_ability_resource_level_md",
    "combat_resource_md": "high_ability_resource_md",
    "use_combat_resource": "use_high_ability_resource",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def one(
    connection: sqlite3.Connection,
    sql: str,
    args: tuple[Any, ...] = (),
) -> sqlite3.Row:
    value = connection.execute(sql, args).fetchone()
    if value is None:
        raise RuntimeError(f"Required row missing: {sql} {args}")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--stage50", type=Path, default=DEFAULT_STAGE50)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args(argv)


def load_stage50_rows(stage50: Path) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    with closing(sqlite3.connect(stage50)) as connection:
        connection.row_factory = sqlite3.Row
        for table, ids in SOURCE_ROWS.items():
            rows: list[dict[str, Any]] = []
            for row_id in ids:
                value = one(
                    connection,
                    "SELECT row_json FROM cached_result_rows "
                    "WHERE query_key=? AND json_extract(row_json,'$.id')=?",
                    (QUERY_KEYS[table], row_id),
                )
                decoded = json.loads(value["row_json"])
                if int(decoded["id"]) != row_id:
                    raise RuntimeError(f"AA8 Stage 50 identity mismatch: {table}:{row_id}")
                rows.append(decoded)
            selected[table] = rows
    return selected


def decode_native_clout_effects(game11: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, evidence = _decode_result(
        game11.read_bytes(),
        "doodad_func_clout_effects",
        dict(DOODAD_RESULT_SPECS["doodad_func_clout_effects"]),
    )
    if len(rows) != EXPECTED_RELATION_ROWS:
        raise RuntimeError("Unexpected AA8 doodad_func_clout_effects row count")
    if evidence["rows_sha256"] != EXPECTED_RELATION_SHA256:
        raise RuntimeError("Unexpected AA8 doodad_func_clout_effects row digest")
    target = [
        row for row in rows
        if int(row["doodad_func_clout_id"]) == 3792
    ]
    if target != [{"doodad_func_clout_id": 3792, "effect_id": 76542}]:
        raise RuntimeError(f"Unexpected Flame Barrier Mist native relation: {target}")
    return rows, evidence


def validate_crosswalk(crosswalk: Path) -> dict[str, Any]:
    exact = {
        ("effects", "76542"),
        ("effects", "76543"),
        ("buff_effects", "29874"),
        ("buffs", "24585"),
        ("buff_tick_effects", "4167"),
        ("damage_effects", "12209"),
    }
    observed: dict[str, Any] = {}
    with closing(sqlite3.connect(crosswalk)) as connection:
        connection.row_factory = sqlite3.Row
        for table, row_id in sorted(exact):
            row = one(
                connection,
                "SELECT classification,aa8_locator,aa8_row_sha256,evidence_json "
                "FROM row_comparisons WHERE table_name=? AND aa8_id=?",
                (table, row_id),
            )
            if row["classification"] not in {
                "exact_id_exact_relation",
                "stable_id_changed_properties",
            }:
                raise RuntimeError(
                    f"Crosswalk rejected AA8 closure {table}:{row_id}: "
                    f"{row['classification']}"
                )
            observed[f"{table}:{row_id}"] = dict(row)
        table = one(
            connection,
            "SELECT classification,evidence_state,evidence_json "
            "FROM logical_table_crosswalk "
            "WHERE table_name='doodad_func_clout_effects'",
        )
        observed["doodad_func_clout_effects"] = dict(table)
    return observed


def project_row(
    connection: sqlite3.Connection,
    table: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    target_columns = [
        str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")
    ]
    mapped = {RUNTIME_ALIASES.get(key, key): value for key, value in source.items()}
    return {column: mapped.get(column) for column in target_columns}


def insert_exact_row(
    connection: sqlite3.Connection,
    table: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    row_id = int(source["id"])
    existing = connection.execute(
        f"SELECT * FROM {table} WHERE id=?", (row_id,)
    ).fetchone()
    projected = project_row(connection, table, source)
    if existing is not None:
        if dict(existing) != projected:
            raise RuntimeError(f"Refusing to overwrite different runtime row {table}:{row_id}")
        return projected
    columns = list(projected)
    connection.execute(
        f"INSERT INTO {table}({','.join(columns)}) "
        f"VALUES({','.join('?' for _ in columns)})",
        tuple(projected[column] for column in columns),
    )
    return projected


def build(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.base, args.stage50, args.crosswalk, args.game11):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(args.base) != EXPECTED_BASE_SHA256:
        raise RuntimeError("The V23 base compact changed")
    if sha256_file(args.game11) != EXPECTED_GAME11_SHA256:
        raise RuntimeError("The AA8 game11 evidence changed")
    stage_rows = load_stage50_rows(args.stage50)
    _, relation_evidence = decode_native_clout_effects(args.game11)
    crosswalk_evidence = validate_crosswalk(args.crosswalk)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and not args.replace:
        raise FileExistsError(f"Use --replace for existing output: {args.output}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{args.output.name}.", suffix=".tmp", dir=args.output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(args.base, temporary)
        with closing(sqlite3.connect(temporary)) as connection:
            connection.row_factory = sqlite3.Row
            inserted: dict[str, list[dict[str, Any]]] = {}
            for table, rows in stage_rows.items():
                inserted[table] = [
                    insert_exact_row(connection, table, row) for row in rows
                ]
            relation = (3792, 76542)
            existing_relation = connection.execute(
                "SELECT doodad_func_clout_id,effect_id "
                "FROM doodad_func_clout_effects "
                "WHERE doodad_func_clout_id=? AND effect_id=?",
                relation,
            ).fetchone()
            if existing_relation is None:
                connection.execute(
                    "INSERT INTO doodad_func_clout_effects"
                    "(doodad_func_clout_id,effect_id) VALUES(?,?)",
                    relation,
                )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS sorcery_flame_barrier_v23_evidence("
                "evidence_key TEXT PRIMARY KEY,evidence_value TEXT NOT NULL)"
            )
            evidence_rows = {
                "client_build": CLIENT_BUILD,
                "native_relation": "clout:3792->effect:76542",
                "native_boundary": "game11:0x8AAEF32..0x8AB0A32",
                "native_rows": str(EXPECTED_RELATION_ROWS),
                "native_rows_sha256": EXPECTED_RELATION_SHA256,
                "damage_chain": (
                    "clout:3792->effect:76542->BuffEffect:29874->buff:24585"
                    "->tick_effect:76543->DamageEffect:12209"
                ),
                "authority": "exact_aa8_native_cached_results",
            }
            connection.executemany(
                "INSERT OR REPLACE INTO sorcery_flame_barrier_v23_evidence VALUES(?,?)",
                sorted(evidence_rows.items()),
            )
            connection.commit()
            quick = connection.execute("PRAGMA quick_check").fetchone()[0]
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            closure = {
                "relation": tuple(one(
                    connection,
                    "SELECT doodad_func_clout_id,effect_id "
                    "FROM doodad_func_clout_effects "
                    "WHERE doodad_func_clout_id=3792 AND effect_id=76542",
                )),
                "effect": tuple(one(
                    connection,
                    "SELECT actual_type,actual_id FROM effects WHERE id=76542",
                )),
                "buff_effect": tuple(one(
                    connection,
                    "SELECT buff_id,chance,stack FROM buff_effects WHERE id=29874",
                )),
                "buff": tuple(one(
                    connection,
                    "SELECT duration,tick FROM buffs WHERE id=24585",
                )),
                "tick_effect": tuple(one(
                    connection,
                    "SELECT buff_id,effect_id FROM buff_tick_effects WHERE id=4167",
                )),
                "damage_effect": tuple(one(
                    connection,
                    "SELECT damage_type_id,dps_inc_multiplier,level_md "
                    "FROM damage_effects WHERE id=12209",
                )),
            }
            expected_closure = {
                "relation": (3792, 76542),
                "effect": ("BuffEffect", 29874),
                "buff_effect": (24585, 100, 1),
                "buff": (4000, 1000),
                "tick_effect": (24585, 76543),
                "damage_effect": (2, 6.0, 7.0),
            }
            if closure != expected_closure or quick != "ok" or integrity != "ok":
                raise RuntimeError(
                    f"V23 runtime validation failed: {closure} {quick} {integrity}"
                )
        os.replace(temporary, args.output)
    finally:
        temporary.unlink(missing_ok=True)

    manifest = {
        "format_version": 23,
        "client_build": CLIENT_BUILD,
        "authority": {
            "runtime_rows": "exact AA8 Stage 50 cached results",
            "clout_effect_relation": "exact AA8 game11 cached result",
            "crosswalk": "mandatory gap-reduction and identity corroboration only",
            "aa10_balance_imported": False,
        },
        "sources": {
            "base": {"path": str(args.base), "sha256": EXPECTED_BASE_SHA256},
            "stage50": {"path": str(args.stage50), "sha256": sha256_file(args.stage50)},
            "crosswalk": {"path": str(args.crosswalk), "sha256": sha256_file(args.crosswalk)},
            "game11": {"path": str(args.game11), "sha256": EXPECTED_GAME11_SHA256},
        },
        "native_relation_evidence": relation_evidence,
        "crosswalk_evidence": crosswalk_evidence,
        "restored_rows": {
            table: [int(row["id"]) for row in rows]
            for table, rows in stage_rows.items()
        },
        "restored_relation": {
            "doodad_func_clout_id": 3792,
            "effect_id": 76542,
        },
        "gods_whip_code_fix": {
            "skill_id": 39674,
            "plot_id": 3778,
            "event_id": 33384,
            "policy": "sample radial distance across [0,p3], preserve V22 terrain correction",
        },
        "verification": {"quick_check": "ok", "integrity_check": "ok"},
        "output": {"path": str(args.output), "sha256": sha256_file(args.output)},
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    manifest = build(parse_args())
    print(canonical_json(manifest["output"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
