#!/usr/bin/env python3
"""Build an AA8-native runtime for the first Nuian green quest arc.

The base runtime is never modified.  The builder consumes the forensic
manifest, migrates only the schemas required by the selected native rows,
replaces the historical quest graph atomically, and validates the complete
quest/doodad/item closure before publishing the generated compact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any


DOMAIN = Path(__file__).resolve().parent
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-nuian-green-arc-v1-manifest.json"
)
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest330-v5.sqlite3"
)
DEFAULT_CLIENT_COMPACT = Path(r"D:\Proyectos\AAemu\client_kakao\compact.sqlite3")
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v1.sqlite3"
)
DEFAULT_BUILD_MANIFEST = (
    DOMAIN / "generated" / "native-nuian-green-arc-v1-runtime-manifest.json"
)


def load_extractor():
    path = DOMAIN / "extract_native_nuian_green_arc.py"
    spec = importlib.util.spec_from_file_location("green_arc_extractor", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    ]


def sqlite_type(layout: str) -> str:
    return {
        "38": "INTEGER",
        "68": "INTEGER",
        "40": "INTEGER",
        "70": "INTEGER",
        "60": "REAL",
        "78": "TEXT",
    }[layout]


def ensure_columns(
    connection: sqlite3.Connection,
    table: str,
    columns: list[str],
    layout: list[str],
) -> list[str]:
    existing = set(table_columns(connection, table))
    added: list[str] = []
    for column, field_type in zip(columns, layout):
        if column in existing:
            continue
        connection.execute(
            f'ALTER TABLE "{table}" ADD COLUMN "{column}" '
            f"{sqlite_type(field_type)}"
        )
        default_value: Any = "" if field_type == "78" else 0
        connection.execute(
            f'UPDATE "{table}" SET "{column}"=? WHERE "{column}" IS NULL',
            (default_value,),
        )
        added.append(column)
    return added


def existing_row(
    connection: sqlite3.Connection, table: str, row_id: int
) -> dict[str, Any] | None:
    connection.row_factory = sqlite3.Row
    row = connection.execute(
        f'SELECT * FROM "{table}" WHERE id=?', (row_id,)
    ).fetchone()
    return dict(row) if row else None


def sanitize_unresolved_strings(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sanitized: list[dict[str, Any]] = []
    fallbacks: list[dict[str, Any]] = []
    for original in rows:
        row = dict(original)
        previous = existing_row(connection, table, int(row["id"]))
        for column, value in list(row.items()):
            if not (
                isinstance(value, str)
                and value.startswith("<ref:")
                and value.endswith(">")
            ):
                continue
            replacement = (
                previous.get(column)
                if previous is not None and previous.get(column) is not None
                else ""
            )
            row[column] = replacement
            fallbacks.append(
                {
                    "table": table,
                    "id": int(row["id"]),
                    "column": column,
                    "native_reference": value,
                    "runtime_value": replacement,
                    "reason": (
                        "The game11 cached row references a string interned by "
                        "an earlier result. The server does not consume this "
                        "field for the selected quest behavior."
                    ),
                }
            )
        sanitized.append(row)
    return sanitized, fallbacks


def replace_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    columns = list(rows[0])
    placeholders = ",".join("?" for _ in columns)
    quoted = ",".join(f'"{column}"' for column in columns)
    sql = (
        f'INSERT OR REPLACE INTO "{table}" ({quoted}) '
        f"VALUES ({placeholders})"
    )
    connection.executemany(
        sql,
        [[row[column] for column in columns] for row in rows],
    )


def flatten_quest_graph(manifest: dict[str, Any]):
    contexts: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    acts: list[dict[str, Any]] = []
    concrete_by_type: dict[str, dict[int, dict[str, Any]]] = {}
    for quest in manifest["native_quest_graph"]:
        contexts.append(dict(quest["context"]))
        for component_with_acts in quest["components"]:
            component = {
                key: value
                for key, value in component_with_acts.items()
                if key != "acts"
            }
            components.append(component)
            for act_with_detail in component_with_acts["acts"]:
                detail = dict(act_with_detail["detail"])
                act = {
                    key: value
                    for key, value in act_with_detail.items()
                    if key != "detail"
                }
                acts.append(act)
                concrete_by_type.setdefault(
                    str(act["act_detail_type"]), {}
                )[int(detail["id"])] = detail
    return contexts, components, acts, concrete_by_type


def copy_quest_items(
    runtime: sqlite3.Connection,
    client_path: Path,
    item_ids: set[int],
) -> list[int]:
    client = sqlite3.connect(
        f"file:{client_path.resolve().as_posix()}?mode=ro", uri=True
    )
    client.row_factory = sqlite3.Row
    try:
        source_rows = {
            int(row["id"]): dict(row)
            for row in client.execute(
                "SELECT * FROM items WHERE id IN "
                f"({','.join('?' for _ in item_ids)})",
                sorted(item_ids),
            )
        }
    finally:
        client.close()
    if set(source_rows) != item_ids:
        raise RuntimeError(
            f"AA8 client compact is missing items {sorted(item_ids - set(source_rows))}"
        )

    runtime_columns = table_columns(runtime, "items")
    defaults: dict[str, Any] = {
        column: 0 for column in runtime_columns
    }
    defaults.update({"name": "", "description": ""})
    rows: list[dict[str, Any]] = []
    for item_id in sorted(item_ids):
        source = source_rows[item_id]
        row = dict(defaults)
        for column in runtime_columns:
            if column in source:
                row[column] = source[column]
        rows.append(row)
    replace_rows(runtime, "items", rows)
    return sorted(item_ids)


def validate_runtime(
    connection: sqlite3.Connection,
    quest_ids: set[int],
    component_ids: set[int],
    expected_act_ids: set[int],
    item_ids: set[int],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["integrity_check"] = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]
    checks["quest_contexts"] = connection.execute(
        "SELECT COUNT(*) FROM quest_contexts WHERE id IN "
        f"({','.join('?' for _ in quest_ids)})",
        sorted(quest_ids),
    ).fetchone()[0]
    checks["quest_components"] = connection.execute(
        "SELECT COUNT(*) FROM quest_components WHERE quest_context_id IN "
        f"({','.join('?' for _ in quest_ids)})",
        sorted(quest_ids),
    ).fetchone()[0]
    actual_acts = {
        int(row[0])
        for row in connection.execute(
            "SELECT id FROM quest_acts WHERE quest_component_id IN "
            f"({','.join('?' for _ in component_ids)})",
            sorted(component_ids),
        )
    }
    checks["quest_act_ids_match"] = actual_acts == expected_act_ids
    checks["quest_2532_ready_acts"] = [
        tuple(row)
        for row in connection.execute(
            "SELECT id,act_detail_type,act_detail_id,quest_component_id "
            "FROM quest_acts WHERE quest_component_id=10966 ORDER BY id"
        )
    ]
    checks["marian_client_doodad"] = connection.execute(
        "SELECT client_doodad FROM doodad_almighties WHERE id=14074"
    ).fetchone()[0]
    checks["marian_proxy_group"] = connection.execute(
        "SELECT COUNT(*) FROM doodad_func_groups "
        "WHERE doodad_almighty_id=14074 AND model='npctype://10581'"
    ).fetchone()[0]
    checks["quest_2532_doodad_func"] = connection.execute(
        "SELECT COUNT(*) FROM doodad_func_quests "
        "WHERE id=1508 AND quest_kind_id=2 AND quest_id=2532"
    ).fetchone()[0]
    present_items = {
        int(row[0])
        for row in connection.execute(
            "SELECT id FROM items WHERE id IN "
            f"({','.join('?' for _ in item_ids)})",
            sorted(item_ids),
        )
    }
    checks["quest_items_match"] = present_items == item_ids
    expected_ready = [(63971, "QuestActConReportDoodad", 163, 10966)]
    if (
        checks["integrity_check"] != "ok"
        or checks["quest_contexts"] != 7
        or checks["quest_components"] != 25
        or not checks["quest_act_ids_match"]
        or checks["quest_2532_ready_acts"] != expected_ready
        or checks["marian_client_doodad"] != 1
        or checks["marian_proxy_group"] != 1
        or checks["quest_2532_doodad_func"] != 1
        or not checks["quest_items_match"]
    ):
        raise RuntimeError(f"generated runtime validation failed: {checks}")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument(
        "--client-compact", type=Path, default=DEFAULT_CLIENT_COMPACT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--build-manifest", type=Path, default=DEFAULT_BUILD_MANIFEST
    )
    options = parser.parse_args()
    for path in (
        options.manifest,
        options.base_runtime,
        options.client_compact,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
    expected_base_hash = manifest["sources"]["runtime_comparison_only"]["sha256"]
    if sha256(options.base_runtime) != expected_base_hash:
        raise RuntimeError("base runtime differs from the audited manifest")
    expected_client_hash = manifest["sources"]["aa8_client_compact"]["sha256"]
    if sha256(options.client_compact) != expected_client_hash:
        raise RuntimeError("AA8 client compact differs from the audited manifest")

    extractor = load_extractor()
    contexts, components, acts, concrete_by_type = flatten_quest_graph(manifest)
    table_by_type = {
        spec["type"]: table
        for table, spec in extractor.CONCRETE_SPECS.items()
    }
    concrete = {
        table_by_type[detail_type]: list(rows.values())
        for detail_type, rows in concrete_by_type.items()
    }
    doodads = manifest["native_doodad_closure"]

    quest_ids = {int(row["id"]) for row in contexts}
    component_ids = {int(row["id"]) for row in components}
    act_ids = {int(row["id"]) for row in acts}
    item_ids = {
        int(row["item_id"])
        for rows in concrete.values()
        for row in rows
        if "item_id" in row and int(row["item_id"]) > 0
    }
    missing_runtime_items = set(
        manifest["runtime_comparison"]["item_closure"]["runtime"]["missing_ids"]
    )

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.build_manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    schema_additions: dict[str, list[str]] = {}
    string_fallbacks: list[dict[str, Any]] = []
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")

        for table, spec in extractor.CONCRETE_SPECS.items():
            added = ensure_columns(
                connection, table, list(spec["columns"]), list(spec["layout"])
            )
            if added:
                schema_additions[table] = added
        for table, spec in extractor.DOODAD_SPECS.items():
            added = ensure_columns(
                connection, table, list(spec["columns"]), list(spec["layout"])
            )
            if added:
                schema_additions[table] = added

        contexts, fallbacks = sanitize_unresolved_strings(
            connection, "quest_contexts", contexts
        )
        string_fallbacks.extend(fallbacks)
        connection.execute(
            "DELETE FROM quest_acts WHERE quest_component_id IN "
            f"({','.join('?' for _ in component_ids)})",
            sorted(component_ids),
        )
        replace_rows(connection, "quest_contexts", contexts)
        replace_rows(connection, "quest_components", components)
        replace_rows(connection, "quest_acts", acts)

        for table, rows in concrete.items():
            clean, fallbacks = sanitize_unresolved_strings(
                connection, table, rows
            )
            string_fallbacks.extend(fallbacks)
            replace_rows(connection, table, clean)

        for table in (
            "doodad_almighties",
            "doodad_func_groups",
            "doodad_funcs",
            "doodad_func_quests",
        ):
            clean, fallbacks = sanitize_unresolved_strings(
                connection, table, list(doodads[table])
            )
            string_fallbacks.extend(fallbacks)
            replace_rows(connection, table, clean)

        copied_items = copy_quest_items(
            connection, options.client_compact, missing_runtime_items
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aaemu_native_quest_reconstruction (
                phase TEXT PRIMARY KEY,
                authority TEXT NOT NULL,
                source_manifest_sha256 TEXT NOT NULL,
                quest_ids TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "VALUES (?, ?, ?, ?)",
            (
                "native-nuian-green-arc-v1",
                manifest["authority"],
                sha256(options.manifest),
                ",".join(map(str, sorted(quest_ids))),
            ),
        )
        checks = validate_runtime(
            connection, quest_ids, component_ids, act_ids, item_ids
        )
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()

    os.replace(temporary, options.output)
    build_manifest = {
        "format_version": 1,
        "phase": "native-nuian-green-arc-v1-runtime",
        "authority": manifest["authority"],
        "sources": {
            "forensic_manifest": {
                "path": str(options.manifest),
                "sha256": sha256(options.manifest),
            },
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": sha256(options.base_runtime),
            },
            "aa8_client_compact": {
                "path": str(options.client_compact),
                "sha256": sha256(options.client_compact),
            },
        },
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
        "scope": {
            "quest_ids": sorted(quest_ids),
            "quest_contexts": len(contexts),
            "quest_components": len(components),
            "quest_acts": len(acts),
            "copied_client_quest_item_ids": copied_items,
        },
        "schema_additions": schema_additions,
        "unresolved_string_fallbacks": string_fallbacks,
        "validation": checks,
        "deployment": {
            "deployed": False,
            "reason": (
                "Generated and validated offline. Live deployment requires a "
                "controlled restart and an in-game marker/interaction probe."
            ),
        },
    }
    options.build_manifest.write_text(
        json.dumps(build_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {options.output} ({options.output.stat().st_size} bytes, "
        f"sha256={build_manifest['output']['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
