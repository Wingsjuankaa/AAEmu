#!/usr/bin/env python3
"""Restore the exact AA8 Freezing Earth area shape over Sorcery runtime v9."""

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
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v9.sqlite3"
)
DEFAULT_STAGE60 = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\stage-60-assets.sqlite"
)
DEFAULT_CROSSWALK = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3"
)
DEFAULT_AA10 = Path(
    r"E:\AAEmu-Research\test\ArcheAge Returns 10.0.2.13 - 8yx - r575 - 2026-06-18"
    r"\game\db\game.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v10.sqlite3"
)
DEFAULT_MANIFEST = (
    Path(__file__).with_name("generated") / "sorcery-specialization-v10.manifest.json"
)

EXPECTED_HASHES = {
    "base": "33C0268086CCF7E6914B33CCF75B3BF935F6481CE18C9006E18B76446085C6CF",
    "stage60": "423E8872C8AAAEFA46ABB0E04FB299A17F56722ECDCDF97C2888F7AC9061AB02",
    "crosswalk": "44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71",
    "aa10": "87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F",
}

AA8_SHAPE = {
    "adjust_angle": 0,
    "area_target_kind_id": 0,
    "calc_distance": 0,
    "id": 11815,
    "kind_id": 1,
    "value1": 8.7,
    "value2": 0.0,
    "value3": 0.0,
}
RUNTIME_SHAPE = {
    "id": 11815,
    "adjust_angle": 0,
    "calc_distance": 0,
    "kind_id": 1,
    "target_update_method_id": 0,
    "value1": 8.7,
    "value2": 0.0,
    "value3": 0.0,
}
EXPECTED_EXACT_COLUMNS = [
    "adjust_angle", "area_target_kind_id", "calc_distance", "kind_id",
    "value1", "value2", "value3",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def one(connection: sqlite3.Connection, sql: str, args: tuple[Any, ...] = ()) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    value = connection.execute(sql, args).fetchone()
    if value is None:
        raise RuntimeError(f"Required row missing: {sql} {args}")
    return dict(value)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--stage60", type=Path, default=DEFAULT_STAGE60)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--aa10", type=Path, default=DEFAULT_AA10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def _normalized_aa10(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (1 if value == "t" else 0 if value == "f" else value)
        for key, value in row.items()
    }


def validate_sources(args: argparse.Namespace) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, expected in EXPECTED_HASHES.items():
        path = getattr(args, name)
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"Unexpected SHA-256 for {path}: {actual} != {expected}")
        hashes[name] = actual

    with closing(sqlite3.connect(args.base)) as connection:
        if connection.execute("SELECT count(*) FROM aoe_shapes WHERE id=11815").fetchone()[0]:
            raise RuntimeError("Runtime v9 unexpectedly already contains aoe_shapes:11815")
        event = one(
            connection,
            "SELECT plot_id,target_update_method_id,target_update_method_param1 "
            "FROM plot_events WHERE id=25977",
        )
        if event != {
            "plot_id": 3096,
            "target_update_method_id": 5,
            "target_update_method_param1": 11815,
        }:
            raise RuntimeError(f"Freezing Earth plot carrier changed: {event}")

    with closing(sqlite3.connect(args.stage60)) as connection:
        cached = json.loads(one(
            connection,
            "SELECT row_json FROM cached_result_rows WHERE query_key=? AND row_index=?",
            ("stage60:query:6:aoe_shapes", 9856),
        )["row_json"])
        if cached != AA8_SHAPE:
            raise RuntimeError(f"Unexpected AA8 native aoe_shapes:11815 row: {cached}")

    with closing(sqlite3.connect(args.crosswalk)) as connection:
        comparison = one(
            connection,
            "SELECT classification,relation_state,property_state,balance_state,"
            "exact_columns_json,changed_relation_columns_json,changed_property_columns_json,"
            "balance_columns_json,aa8_row_sha256 "
            "FROM row_comparisons WHERE table_name='aoe_shapes' AND aa8_id='11815'",
        )
        expected = {
            "classification": "exact_id_exact_relation",
            "relation_state": "stable",
            "property_state": "exact",
            "balance_state": "exact_or_absent",
            "exact_columns_json": json.dumps(EXPECTED_EXACT_COLUMNS, separators=(",", ":")),
            "changed_relation_columns_json": "[]",
            "changed_property_columns_json": "[]",
            "balance_columns_json": "[]",
            "aa8_row_sha256": "44BC30CE2F95E949DA5DCF52BB16E639DB5AEDF6BFEDE1DB4C84BEE4A4BCE5D2",
        }
        if comparison != expected:
            raise RuntimeError(f"Unexpected crosswalk classification: {comparison}")

    with closing(sqlite3.connect(args.aa10)) as connection:
        aa10 = _normalized_aa10(one(connection, "SELECT * FROM aoe_shapes WHERE id=11815"))
        if aa10 != AA8_SHAPE:
            raise RuntimeError(f"AA10 exact corroboration differs from AA8: {aa10}")
    return hashes


def build(args: argparse.Namespace) -> dict[str, Any]:
    hashes = validate_sources(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.base, args.output)

    with closing(sqlite3.connect(args.output)) as connection:
        columns = list(RUNTIME_SHAPE)
        connection.execute(
            f"INSERT INTO aoe_shapes({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
            tuple(RUNTIME_SHAPE[column] for column in columns),
        )
        connection.execute(
            "CREATE TABLE sorcery_aoe_shape_v10_evidence("
            "evidence_key TEXT PRIMARY KEY,evidence_value TEXT NOT NULL)"
        )
        evidence = {
            "aa8_native_locator": "stage60:query:6:aoe_shapes row_index=9856",
            "aa8_row_sha256": "44BC30CE2F95E949DA5DCF52BB16E639DB5AEDF6BFEDE1DB4C84BEE4A4BCE5D2",
            "crosswalk": "exact_id_exact_relation;stable;exact;exact_or_absent",
            "freezing_earth_chain": "skill10151->plot3096->event25977->aoe_shape11815",
            "shape_contract": "sphere;radius=8.7;adjust_angle=0;calc_distance=0;area_target_kind_id=0",
        }
        connection.executemany(
            "INSERT INTO sorcery_aoe_shape_v10_evidence VALUES(?,?)",
            sorted(evidence.items()),
        )
        connection.commit()
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        inserted = one(connection, "SELECT * FROM aoe_shapes WHERE id=11815")
        if inserted != RUNTIME_SHAPE or quick != "ok" or integrity != "ok":
            raise RuntimeError("Runtime v10 validation failed")

    manifest = {
        "format_version": 10,
        "client_build": "Kakao 8.0.3.12 r558734",
        "authority": {
            "shape": "exact AA8 native cached row",
            "crosswalk": "mandatory exact relationship/property corroboration",
            "aa10": "exact normalized row corroboration only",
        },
        "sources": {
            name: {"path": str(getattr(args, name)), "sha256": value}
            for name, value in hashes.items()
        },
        "restored_aa8_shape": AA8_SHAPE,
        "runtime_projection": RUNTIME_SHAPE,
        "closure": ["skill:10151", "plot:3096", "plot_event:25977", "aoe_shapes:11815"],
        "verification": {"quick_check": quick, "integrity_check": integrity},
        "output": {"path": str(args.output), "sha256": sha256_file(args.output)},
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    print(json.dumps(build(parse_args()), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
