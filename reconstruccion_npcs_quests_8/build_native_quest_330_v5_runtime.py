#!/usr/bin/env python3
"""Build quest 330 V5 with the complete AA8-native system-faction catalogue."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any


DOMAIN = Path(__file__).resolve().parent
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest330-v3.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest330-v5.sqlite3"
)
DEFAULT_DATA = DOMAIN / "generated" / "native-system-factions-v1-data.json"
DEFAULT_MANIFEST = DOMAIN / "generated" / "native-system-factions-v2-runtime-manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')}


def runtime_row(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["id"]),
        int(row["aggro_link"]),
        0,  # server-only legacy column; AA8 system_factions has no equivalent
        int(row["guard_help"]),
        "",  # server-only asset path; client resolves its own icon_id
        int(row["is_diplomacy_tgt"]),
        int(row["mother_id"]),
        str(row["name"]),
        int(row["owner_id"]),
        str(row["owner_name"]),
        int(row["owner_type_id"]),
        int(row["political_system_id"]),
        int(row["integration_faction"]),
    )


def verify(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_ids = {int(row["id"]) for row in rows}
    actual_ids = {int(row[0]) for row in connection.execute("SELECT id FROM system_factions")}
    if actual_ids != expected_ids:
        raise RuntimeError(
            f"native faction IDs differ: missing={sorted(expected_ids - actual_ids)}, "
            f"extra={sorted(actual_ids - expected_ids)}"
        )
    if len(actual_ids) != 114:
        raise RuntimeError(f"expected 114 native factions, found {len(actual_ids)}")

    chain = connection.execute(
        """
        SELECT child.id, child.mother_id, mother.id, mother.mother_id
        FROM system_factions child
        JOIN system_factions mother ON mother.id=child.mother_id
        WHERE child.id=101
        """
    ).fetchone()
    if chain != (101, 148, 148, 0):
        raise RuntimeError(f"quest 330 faction chain differs: {chain}")

    missing_mothers = connection.execute(
        """
        SELECT child.id, child.mother_id
        FROM system_factions child
        LEFT JOIN system_factions mother ON mother.id=child.mother_id
        WHERE child.mother_id != 0 AND mother.id IS NULL
        """
    ).fetchall()
    if missing_mothers:
        raise RuntimeError(f"native faction mother links are orphaned: {missing_mothers}")

    orphan_relations = connection.execute(
        """
        SELECT COUNT(*)
        FROM system_faction_relations relation
        LEFT JOIN system_factions first ON first.id=relation.faction1_id
        LEFT JOIN system_factions second ON second.id=relation.faction2_id
        WHERE first.id IS NULL OR second.id IS NULL
        """
    ).fetchone()[0]
    if orphan_relations:
        raise RuntimeError(f"system faction relations contain {orphan_relations} orphans")

    native_integration = {
        int(row[0])
        for row in connection.execute(
            "SELECT id FROM system_factions WHERE integration_faction=1"
        )
    }
    if native_integration != {204, 205, 206, 209}:
        raise RuntimeError(f"integration faction set differs: {sorted(native_integration)}")

    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite validation failed: {quick}/{integrity}")
    return {
        "system_factions": len(actual_ids),
        "quest_330_chain": [101, 148, 0],
        "integration_factions": sorted(native_integration),
        "system_faction_relation_orphans": orphan_relations,
        "quick_check": quick,
        "integrity_check": integrity,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    for path in (options.base_runtime, options.data):
        if not path.is_file():
            raise FileNotFoundError(path)
    data = json.loads(options.data.read_text(encoding="utf-8"))
    rows = data["rows"]
    if data.get("table") != "system_factions" or len(rows) != 114:
        raise RuntimeError("AA8 native system_factions bundle is incomplete")
    base_hash = sha256(options.base_runtime)

    options.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(options.base_runtime, options.output)
    connection = sqlite3.connect(options.output)
    try:
        with connection:
            if "integration_faction" not in table_columns(connection, "system_factions"):
                connection.execute(
                    "ALTER TABLE system_factions ADD COLUMN "
                    "integration_faction boolean NOT NULL DEFAULT 0"
                )
            connection.execute("DELETE FROM system_factions")
            connection.executemany(
                """
                INSERT INTO system_factions
                  (id, aggro_link, diplomacy_link_id, guard_help, icon_path,
                   is_diplomacy_tgt, mother_id, name, owner_id, owner_name,
                   owner_type_id, political_system_id, integration_faction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (runtime_row(row) for row in rows),
            )
            # Relation 901 is a historical server sentinel absent from AA8.
            # Keep only relations whose endpoints exist in the native catalogue.
            connection.execute(
                """
                DELETE FROM system_faction_relations
                WHERE faction1_id NOT IN (SELECT id FROM system_factions)
                   OR faction2_id NOT IN (SELECT id FROM system_factions)
                """
            )
        verification = verify(connection, rows)
        connection.execute("VACUUM")
        verification = verify(connection, rows)
    finally:
        connection.close()

    manifest = {
        "authority": data["authority"],
        "built": True,
        "deployable": True,
        "blockers": [],
        "sources": {
            "base_runtime": {
                "path": str(options.base_runtime.resolve()),
                "sha256": base_hash,
            },
            "native_system_factions": {
                "path": str(options.data.resolve()),
                "sha256": sha256(options.data),
                "game11_sha256": data["source"]["sha256"],
                "cached_result": data["cached_result"],
            },
        },
        "projection": {
            "classification": "game11_native",
            "native_rows": 114,
            "server_derived_columns": {
                "diplomacy_link_id": 0,
                "icon_path": "",
            },
            "removed_server_only_relation_sentinel": 901,
            "packet_fields_confirmed_by": "x2game.dll FUN_3999a730",
        },
        "output": {
            "path": str(options.output.resolve()),
            "sha256": sha256(options.output),
        },
        "verification": verification,
    }
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
