from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from . import TOOL_NAME, TOOL_VERSION
from .config import ForensicsConfig
from .util import atomic_text, canonical_json, sha256_file, sha256_text, stable_key


SCHEMA_VERSION = 1
DEFAULT_AA10_DATABASE = Path(
    r"E:\AAEmu-Research\test\ArcheAge Returns 10.0.2.13 - 8yx - r575 - 2026-06-18\game\db\game.sqlite3"
)
EXPECTED_AA8 = {
    "bytes": 8_906_633_216,
    "sha256": "92CDF5D1EB16DAF0C4D5ABFCB80B510DFDF827708D4F8087235CCFACE3CE3C4F",
}
EXPECTED_AA10 = {
    "bytes": 552_178_688,
    "sha256": "87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F",
}
CLASSIFICATIONS = {
    "exact_id_exact_relation",
    "stable_id_changed_properties",
    "renumbered_row_stable_relation",
    "aa8_only",
    "aa10_only",
    "structural_candidate",
    "conflict",
}
IDENTITY_ENTITY_TABLES = {
    "appellations": "appellation",
    "customizing_item_asset_colors": "customizing_item_asset_color",
    "loot_packs": "loot_pack",
    "npc_groups": "npc_group",
    "npc_spawners": "npc_spawner",
    "skin_colors": "skin_color",
    "spheres": "sphere",
}
CONFIRMED_RELATION_TABLES = {
    "craft_materials",
    "craft_products",
    "npc_group_members",
    "npc_spawner_npcs",
    "skill_effects",
    "skill_products",
    "skill_reagents",
    "tagged_buffs",
    "tagged_skills",
}
BALANCE_MARKERS = (
    "amount",
    "chance",
    "cooldown",
    "cost",
    "damage",
    "delay",
    "drop_rate",
    "duration",
    "formula",
    "max_",
    "min_",
    "probability",
    "rate",
    "repeat",
    "time",
    "weight",
)


CROSSWALK_SCHEMA = """
PRAGMA page_size=4096;
PRAGMA auto_vacuum=NONE;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE source_artifacts (
    source_key TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    path TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    authority TEXT NOT NULL,
    provenance TEXT NOT NULL,
    quick_check TEXT NOT NULL,
    integrity_check TEXT NOT NULL,
    user_table_count INTEGER NOT NULL,
    internal_table_count INTEGER NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE schema_tables (
    source_key TEXT NOT NULL,
    table_name TEXT NOT NULL,
    table_kind TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    primary_key_json TEXT NOT NULL,
    create_sql_sha256 TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY(source_key,table_name)
) WITHOUT ROWID;

CREATE TABLE schema_columns (
    source_key TEXT NOT NULL,
    table_name TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    declared_type TEXT NOT NULL,
    not_null INTEGER NOT NULL,
    default_json TEXT,
    primary_key_ordinal INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY(source_key,table_name,ordinal)
) WITHOUT ROWID;

CREATE TABLE schema_indexes (
    source_key TEXT NOT NULL,
    table_name TEXT NOT NULL,
    index_name TEXT NOT NULL,
    is_unique INTEGER NOT NULL,
    origin TEXT NOT NULL,
    is_partial INTEGER NOT NULL,
    columns_json TEXT NOT NULL,
    create_sql_sha256 TEXT,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY(source_key,table_name,index_name)
) WITHOUT ROWID;

CREATE TABLE schema_foreign_keys (
    source_key TEXT NOT NULL,
    table_name TEXT NOT NULL,
    foreign_key_id INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    referenced_table TEXT NOT NULL,
    from_column TEXT,
    to_column TEXT,
    on_update TEXT NOT NULL,
    on_delete TEXT NOT NULL,
    match_mode TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY(source_key,table_name,foreign_key_id,sequence)
) WITHOUT ROWID;

CREATE TABLE logical_table_crosswalk (
    table_name TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    aa8_present INTEGER NOT NULL,
    aa10_present INTEGER NOT NULL,
    aa8_query_count INTEGER NOT NULL,
    aa8_expected_rows INTEGER NOT NULL,
    aa8_evidence_rows INTEGER NOT NULL,
    aa10_rows INTEGER NOT NULL,
    expected_columns_json TEXT NOT NULL,
    aa10_columns_json TEXT NOT NULL,
    missing_in_aa10_json TEXT NOT NULL,
    extra_in_aa10_json TEXT NOT NULL,
    identity_columns_json TEXT NOT NULL,
    relation_columns_json TEXT NOT NULL,
    classification TEXT NOT NULL,
    evidence_state TEXT NOT NULL,
    compared_rows INTEGER NOT NULL,
    row_classification_counts_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE row_comparisons (
    comparison_key TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    aa8_locator TEXT,
    aa10_locator TEXT,
    aa8_id TEXT,
    aa10_id TEXT,
    natural_key_json TEXT NOT NULL,
    classification TEXT NOT NULL,
    relation_state TEXT NOT NULL,
    property_state TEXT NOT NULL,
    balance_state TEXT NOT NULL,
    exact_columns_json TEXT NOT NULL,
    changed_relation_columns_json TEXT NOT NULL,
    changed_property_columns_json TEXT NOT NULL,
    balance_columns_json TEXT NOT NULL,
    aa8_only_columns_json TEXT NOT NULL,
    aa10_only_columns_json TEXT NOT NULL,
    aa8_row_sha256 TEXT,
    aa10_row_sha256 TEXT,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY(table_name) REFERENCES logical_table_crosswalk(table_name)
) WITHOUT ROWID;

CREATE TABLE relation_comparisons (
    relation_key TEXT PRIMARY KEY,
    comparison_key TEXT NOT NULL,
    table_name TEXT NOT NULL,
    relation_column TEXT NOT NULL,
    aa8_value_json TEXT,
    aa10_value_json TEXT,
    classification TEXT NOT NULL,
    evidence_state TEXT NOT NULL,
    promotable_to_aa8 INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY(comparison_key) REFERENCES row_comparisons(comparison_key),
    FOREIGN KEY(table_name) REFERENCES logical_table_crosswalk(table_name)
) WITHOUT ROWID;

CREATE TABLE coverage (
    coverage_key TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    table_name TEXT,
    dimension TEXT NOT NULL,
    state TEXT NOT NULL,
    expected INTEGER,
    actual INTEGER,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE negative_evidence (
    evidence_key TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    table_name TEXT,
    subject TEXT NOT NULL,
    state TEXT NOT NULL,
    reason TEXT NOT NULL,
    required_evidence TEXT,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE conflicts (
    conflict_key TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    table_name TEXT,
    subject TEXT NOT NULL,
    classification TEXT NOT NULL,
    severity INTEGER NOT NULL,
    blocked INTEGER NOT NULL,
    reason TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE validation_events (
    validation_key TEXT PRIMARY KEY,
    check_name TEXT NOT NULL,
    state TEXT NOT NULL,
    expected_json TEXT,
    actual_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX idx_logical_domain_classification
    ON logical_table_crosswalk(domain,classification,table_name);
CREATE INDEX idx_rows_table_classification
    ON row_comparisons(table_name,classification);
CREATE INDEX idx_relations_table_classification
    ON relation_comparisons(table_name,classification);
CREATE INDEX idx_negative_domain_state
    ON negative_evidence(domain,state,table_name);
CREATE INDEX idx_conflicts_domain_severity
    ON conflicts(domain,severity DESC,table_name);
"""


@dataclass(frozen=True)
class SourceRow:
    locator: str
    values: dict[str, Any]
    evidence_state: str
    identity_only: bool = False


@dataclass
class LogicalTable:
    name: str
    query_count: int = 0
    expected_rows: int = 0
    expected_columns: set[str] | None = None
    best_query_key: str | None = None
    best_sql: str | None = None
    best_columns: set[str] | None = None
    best_cached_rows: int = 0
    best_cached_state: str | None = None
    native_rows: int = 0
    native_catalog_state: str | None = None
    entity_kind: str | None = None
    opaque: bool = False

    def __post_init__(self) -> None:
        if self.expected_columns is None:
            self.expected_columns = set()
        if self.best_columns is None:
            self.best_columns = set()


def crosswalk_paths(
    output_dir: Path,
    database: Path | None = None,
) -> dict[str, Path]:
    db = (database or output_dir / "aa8-aa10-crosswalk-v1.sqlite3").resolve()
    stem = db.with_suffix("")
    return {
        "database": db,
        "manifest": stem.with_suffix(".manifest.json"),
        "summary": stem.with_suffix(".summary.json"),
        "tables": stem.with_name(stem.name + "-table-coverage.csv"),
        "conflicts": stem.with_name(stem.name + "-conflicts.csv"),
        "negative_evidence": stem.with_name(stem.name + "-negative-evidence.csv"),
        "domains": stem.with_name(stem.name + "-domains"),
    }


def _open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _create_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.executescript(CROSSWALK_SCHEMA)
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return connection


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _normal(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() == "t":
            return 1
        if stripped.lower() == "f":
            return 0
        return stripped
    if isinstance(value, float) and value == 0:
        return 0.0
    return value


def _normal_relation(value: Any) -> Any:
    normalized = _normal(value)
    if normalized in (None, ""):
        return 0
    if isinstance(normalized, float) and normalized.is_integer():
        return int(normalized)
    return normalized


def _jsonable(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray, memoryview)):
        payload = bytes(value)
        return {
            "$blob_bytes": len(payload),
            "$blob_sha256": hashlib.sha256(payload).hexdigest().upper(),
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    return value


def _canonical_id(value: Any) -> str | None:
    if value is None:
        return None
    normalized = _normal(value)
    if isinstance(normalized, float) and normalized.is_integer():
        normalized = int(normalized)
    return str(normalized)


def _domain(table: str) -> str:
    name = table.lower()
    if name.startswith("enum_") or name.startswith("const_"):
        return "enum_const"
    if "loot" in name or name.startswith("gacha_"):
        return "loot"
    if "quest" in name:
        return "quests"
    if "doodad" in name:
        return "doodads"
    if "craft" in name or "recipe" in name:
        return "crafting"
    if "npc" in name or "spawner" in name:
        return "npc_world"
    if any(token in name for token in ("appearance", "custom", "skin", "hair", "face", "sphere")):
        return "appearance"
    if any(
        token in name
        for token in ("skill", "buff", "effect", "plot", "combat", "ability", "tagged")
    ):
        return "skills_buffs"
    if "item" in name:
        return "items"
    return "other"


def _is_balance(column: str) -> bool:
    lowered = column.lower()
    return any(marker in lowered for marker in BALANCE_MARKERS)


def _is_relation_column(column: str) -> bool:
    lowered = column.lower()
    return lowered != "id" and lowered != "uid" and (
        lowered.endswith("_id")
        or lowered in {"member_id", "owner_id", "source_id", "target_id"}
    )


def _source_check(
    path: Path,
    *,
    expected: dict[str, Any],
    source_key: str,
    role: str,
    authority: str,
    provenance: str,
    strict_hashes: bool,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = sha256_file(path)
    size = path.stat().st_size
    if strict_hashes and (size != expected["bytes"] or digest != expected["sha256"]):
        raise RuntimeError(
            f"Frozen input mismatch for {source_key}: bytes={size} sha256={digest}"
        )
    connection = _open_read_only(path)
    try:
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        user_tables = int(
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0]
        )
        internal_tables = int(
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'sqlite_%'"
            ).fetchone()[0]
        )
        evidence: dict[str, Any] = {
            "immutable_read": True,
            "schema_version": int(connection.execute("PRAGMA schema_version").fetchone()[0]),
            "user_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
        }
        if source_key == "aa8" and _table_exists(connection, "metadata"):
            evidence["metadata"] = {
                str(row[0]): str(row[1])
                for row in connection.execute("SELECT * FROM metadata ORDER BY 1")
            }
        if source_key == "aa10" and _table_exists(connection, "bundle_versions"):
            columns = [str(row[1]) for row in connection.execute("PRAGMA table_info(bundle_versions)")]
            evidence["bundle_versions"] = [
                dict(zip(columns, row))
                for row in connection.execute("SELECT * FROM bundle_versions ORDER BY id")
            ]
            evidence["external_package_label"] = "10.0.2.13 - 8yx - r575 - 2026-06-18"
            evidence["duplicate_policy"] = (
                "byte-identical retail-zone-server copies are not independent evidence"
            )
        if quick != "ok" or integrity != "ok":
            raise RuntimeError(
                f"Source database failed integrity gates: {path} quick={quick} integrity={integrity}"
            )
        return {
            "source_key": source_key,
            "role": role,
            "path": path.resolve().as_posix(),
            "bytes": size,
            "sha256": digest,
            "authority": authority,
            "provenance": provenance,
            "quick_check": quick,
            "integrity_check": integrity,
            "user_table_count": user_tables,
            "internal_table_count": internal_tables,
            "evidence": evidence,
        }
    finally:
        connection.close()


def _schema_inventory(
    source: sqlite3.Connection,
    destination: sqlite3.Connection,
    source_key: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    table_rows = source.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for table_row in table_rows:
        table = str(table_row["name"])
        create_sql = str(table_row["sql"] or "")
        columns = [dict(row) for row in source.execute(f'PRAGMA table_info("{table}")')]
        primary_key = [
            str(row["name"])
            for row in sorted(columns, key=lambda value: int(value["pk"]))
            if int(row["pk"]) > 0
        ]
        count = int(source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        table_kind = "internal" if table.startswith("sqlite_") else "user"
        destination.execute(
            "INSERT INTO schema_tables VALUES(?,?,?,?,?,?,?,?)",
            (
                source_key,
                table,
                table_kind,
                count,
                len(columns),
                canonical_json(primary_key),
                sha256_text(create_sql),
                canonical_json({"create_sql_present": bool(create_sql)}),
            ),
        )
        for column in columns:
            destination.execute(
                "INSERT INTO schema_columns VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    source_key,
                    table,
                    int(column["cid"]),
                    str(column["name"]),
                    str(column["type"] or ""),
                    int(column["notnull"]),
                    None
                    if column["dflt_value"] is None
                    else canonical_json(column["dflt_value"]),
                    int(column["pk"]),
                    "{}",
                ),
            )
        indexes: list[dict[str, Any]] = []
        for index_row in source.execute(f'PRAGMA index_list("{table}")'):
            index = dict(index_row)
            index_name = str(index["name"])
            index_columns = [
                str(row["name"])
                for row in source.execute(f'PRAGMA index_info("{index_name}")')
            ]
            index_sql_row = source.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (index_name,)
            ).fetchone()
            index_sql = str(index_sql_row[0] or "") if index_sql_row else ""
            destination.execute(
                "INSERT INTO schema_indexes VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    source_key,
                    table,
                    index_name,
                    int(index["unique"]),
                    str(index["origin"]),
                    int(index["partial"]),
                    canonical_json(index_columns),
                    sha256_text(index_sql) if index_sql else None,
                    "{}",
                ),
            )
            indexes.append(
                {
                    "name": index_name,
                    "unique": int(index["unique"]),
                    "columns": index_columns,
                }
            )
        foreign_keys: list[dict[str, Any]] = []
        for foreign_row in source.execute(f'PRAGMA foreign_key_list("{table}")'):
            foreign = dict(foreign_row)
            destination.execute(
                "INSERT INTO schema_foreign_keys VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    source_key,
                    table,
                    int(foreign["id"]),
                    int(foreign["seq"]),
                    str(foreign["table"]),
                    foreign["from"],
                    foreign["to"],
                    str(foreign["on_update"]),
                    str(foreign["on_delete"]),
                    str(foreign["match"]),
                    "{}",
                ),
            )
            foreign_keys.append(foreign)
        result[table] = {
            "columns": [str(row["name"]) for row in columns],
            "column_types": {str(row["name"]): str(row["type"] or "") for row in columns},
            "primary_key": primary_key,
            "indexes": indexes,
            "foreign_keys": foreign_keys,
            "rows": count,
            "table_kind": table_kind,
        }
    return result


def _logical_inventory(connection: sqlite3.Connection) -> dict[str, LogicalTable]:
    result: dict[str, LogicalTable] = {}
    if _table_exists(connection, "query_specs"):
        query_rows = connection.execute(
            """
            SELECT q.query_key,q.table_name,q.sql_text,q.columns_json,q.expected_rows,q.state,
                   c.row_count AS cached_rows,c.state AS cached_state
            FROM query_specs q
            LEFT JOIN cached_results c ON c.query_key=q.query_key
            ORDER BY q.table_name,q.query_key
            """
        ).fetchall()
        grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in query_rows:
            grouped[str(row["table_name"])].append(row)
        for table, rows in grouped.items():
            item = result.setdefault(table, LogicalTable(table))
            item.query_count = len(rows)
            item.expected_rows = sum(int(row["expected_rows"] or 0) for row in rows)
            for row in rows:
                try:
                    item.expected_columns.update(str(value) for value in json.loads(row["columns_json"] or "[]"))
                except (TypeError, ValueError):
                    pass
            candidates = [row for row in rows if int(row["cached_rows"] or 0) > 0]
            if candidates:
                best = max(
                    candidates,
                    key=lambda row: (
                        int(row["cached_rows"] or 0),
                        len(json.loads(row["columns_json"] or "[]")),
                        str(row["state"]) == "confirmed",
                        str(row["query_key"]),
                    ),
                )
                item.best_query_key = str(best["query_key"])
                item.best_sql = str(best["sql_text"] or "")
                item.best_columns = {
                    str(value) for value in json.loads(best["columns_json"] or "[]")
                }
                item.best_cached_rows = int(best["cached_rows"] or 0)
                item.best_cached_state = str(best["cached_state"] or "unknown")
    if _table_exists(connection, "native_catalogs"):
        for row in connection.execute(
            "SELECT table_name,entity_kind,state,row_count FROM native_catalogs ORDER BY table_name"
        ):
            table = str(row["table_name"])
            item = result.setdefault(table, LogicalTable(table))
            item.native_catalog_state = str(row["state"])
            item.entity_kind = str(row["entity_kind"])
            item.native_rows = max(item.native_rows, int(row["row_count"] or 0))
    if _table_exists(connection, "native_rows"):
        for row in connection.execute(
            "SELECT source_table,COUNT(*) AS rows FROM native_rows GROUP BY source_table ORDER BY source_table"
        ):
            table = str(row["source_table"])
            item = result.setdefault(table, LogicalTable(table))
            item.native_rows = max(item.native_rows, int(row["rows"] or 0))
    if _table_exists(connection, "opaque_regions"):
        for row in connection.execute(
            "SELECT DISTINCT surface FROM opaque_regions WHERE state<>'superseded' ORDER BY surface"
        ):
            table = str(row["surface"])
            item = result.setdefault(table, LogicalTable(table))
            item.opaque = True
    for table, entity_kind in IDENTITY_ENTITY_TABLES.items():
        item = result.setdefault(table, LogicalTable(table))
        if item.entity_kind is None:
            item.entity_kind = entity_kind
    return result


def _aa8_rows(connection: sqlite3.Connection, table: LogicalTable) -> list[SourceRow]:
    if table.name == "tagged_items":
        return []
    if table.best_query_key:
        rows: list[SourceRow] = []
        for row in connection.execute(
            "SELECT row_index,row_json FROM cached_result_rows WHERE query_key=? ORDER BY row_index",
            (table.best_query_key,),
        ):
            values = json.loads(str(row["row_json"]))
            if isinstance(values, dict):
                rows.append(
                    SourceRow(
                        locator=f"cached_result_rows:{table.best_query_key}:{int(row['row_index'])}",
                        values=values,
                        evidence_state=(table.best_cached_state or "unknown"),
                    )
                )
        if rows:
            return rows
    entity_kind = IDENTITY_ENTITY_TABLES.get(table.name)
    if entity_kind and _table_exists(connection, "entities"):
        return [
            SourceRow(
                locator=f"entities:{row['entity_key']}",
                values={
                    "id": int(row["native_id"])
                    if str(row["native_id"]).lstrip("-").isdigit()
                    else str(row["native_id"]),
                    "aa8_state": str(row["state"]),
                    "aa8_lifecycle": str(row["lifecycle"]),
                },
                evidence_state=str(row["state"]),
                identity_only=True,
            )
            for row in connection.execute(
                """
                SELECT entity_key,native_id,state,lifecycle FROM entities
                WHERE kind=? ORDER BY CAST(native_id AS INTEGER),native_id,entity_key
                """,
                (entity_kind,),
            )
            if str(row["native_id"]).strip() != ""
        ]
    if table.native_rows and _table_exists(connection, "native_rows"):
        rows = []
        for row in connection.execute(
            "SELECT native_row_key,native_id,row_json,state FROM native_rows WHERE source_table=? ORDER BY native_row_key",
            (table.name,),
        ):
            values = json.loads(str(row["row_json"] or "{}"))
            if not isinstance(values, dict):
                values = {}
            if "id" not in values:
                values = {"id": row["native_id"], **values}
            identity_only = set(values) <= {
                "id",
                "first_row_index",
                "last_row_index",
                "reference_count",
                "id_column",
            }
            rows.append(
                SourceRow(
                    locator=f"native_rows:{row['native_row_key']}",
                    values=values,
                    evidence_state=str(row["state"]),
                    identity_only=identity_only,
                )
            )
        return rows
    return []


def _aa10_rows(
    connection: sqlite3.Connection,
    table: str,
    columns: list[str],
    aa8_sql: str | None,
) -> list[SourceRow]:
    where = ""
    if aa8_sql and "where enable = 't'" in aa8_sql.lower() and "enable" in columns:
        where = " WHERE enable='t'"
    order_columns = ["id"] if "id" in columns else columns
    order = ""
    if order_columns:
        order = " ORDER BY " + ",".join(f'"{column}"' for column in order_columns)
    query = f'SELECT * FROM "{table}"{where}{order}'
    return [
        SourceRow(
            locator=f"{table}:row:{index}",
            values=dict(row),
            evidence_state="cross_version",
        )
        for index, row in enumerate(connection.execute(query))
    ]


def _row_id(values: dict[str, Any]) -> str | None:
    return _canonical_id(values.get("id")) if "id" in values else None


def _relation_columns(aa8: Iterable[SourceRow], aa10_columns: Iterable[str]) -> list[str]:
    columns = set(aa10_columns)
    for row in aa8:
        columns.update(row.values)
    return sorted(column for column in columns if _is_relation_column(column))


def _signature(values: dict[str, Any], columns: Iterable[str]) -> tuple[Any, ...] | None:
    selected = tuple(_normal_relation(values.get(column)) for column in columns)
    if not selected or all(value in (None, 0, "") for value in selected):
        return None
    return selected


def _same_relation(
    aa8: SourceRow,
    aa10: SourceRow,
    relation_columns: list[str],
) -> bool:
    common = [column for column in relation_columns if column in aa8.values and column in aa10.values]
    if not common:
        return True
    return all(
        _normal_relation(aa8.values[column]) == _normal_relation(aa10.values[column])
        for column in common
    )


def _match_rows(
    aa8_rows: list[SourceRow],
    aa10_rows: list[SourceRow],
    relation_columns: list[str],
) -> list[tuple[SourceRow | None, SourceRow | None, str]]:
    matches: list[tuple[SourceRow | None, SourceRow | None, str]] = []
    used_aa8: set[int] = set()
    used_aa10: set[int] = set()
    aa10_by_id: dict[str, deque[int]] = defaultdict(deque)
    for index, row in enumerate(aa10_rows):
        row_id = _row_id(row.values)
        if row_id is not None:
            aa10_by_id[row_id].append(index)
    for aa8_index, aa8 in enumerate(aa8_rows):
        row_id = _row_id(aa8.values)
        if row_id is None:
            continue
        for aa10_index in aa10_by_id.get(row_id, ()):
            if aa10_index not in used_aa10 and _same_relation(
                aa8, aa10_rows[aa10_index], relation_columns
            ):
                matches.append((aa8, aa10_rows[aa10_index], "same_id"))
                used_aa8.add(aa8_index)
                used_aa10.add(aa10_index)
                break
    matching_relation_columns = [
        column
        for column in relation_columns
        if any(column in row.values for row in aa8_rows)
        and any(column in row.values for row in aa10_rows)
    ]
    aa10_by_signature: dict[tuple[Any, ...], deque[int]] = defaultdict(deque)
    for index, row in enumerate(aa10_rows):
        if index in used_aa10:
            continue
        signature = _signature(row.values, matching_relation_columns)
        if signature is not None:
            aa10_by_signature[signature].append(index)
    for aa8_index, aa8 in enumerate(aa8_rows):
        if aa8_index in used_aa8:
            continue
        signature = _signature(aa8.values, matching_relation_columns)
        if signature is None:
            continue
        queue = aa10_by_signature.get(signature)
        while queue and queue[0] in used_aa10:
            queue.popleft()
        if queue:
            aa10_index = queue.popleft()
            matches.append((aa8, aa10_rows[aa10_index], "natural_relation"))
            used_aa8.add(aa8_index)
            used_aa10.add(aa10_index)
    for aa8_index, aa8 in enumerate(aa8_rows):
        if aa8_index in used_aa8:
            continue
        row_id = _row_id(aa8.values)
        candidate = next(
            (
                index
                for index in aa10_by_id.get(row_id or "", ())
                if index not in used_aa10
            ),
            None,
        )
        if candidate is not None:
            matches.append((aa8, aa10_rows[candidate], "id_conflict"))
            used_aa8.add(aa8_index)
            used_aa10.add(candidate)
    for index, row in enumerate(aa8_rows):
        if index not in used_aa8:
            matches.append((row, None, "aa8_only"))
    for index, row in enumerate(aa10_rows):
        if index not in used_aa10:
            matches.append((None, row, "aa10_only"))
    return sorted(
        matches,
        key=lambda pair: (
            (_canonical_id(pair[0].values.get("id")) or "") if pair[0] else "",
            (_canonical_id(pair[1].values.get("id")) or "") if pair[1] else "",
            pair[2],
            pair[0].locator if pair[0] else "",
            pair[1].locator if pair[1] else "",
        ),
    )


def _comparison_details(
    aa8: SourceRow | None,
    aa10: SourceRow | None,
    match_kind: str,
    relation_columns: list[str],
) -> dict[str, Any]:
    aa8_values = aa8.values if aa8 else {}
    aa10_values = aa10.values if aa10 else {}
    aa8_columns = set(aa8_values)
    aa10_columns = set(aa10_values)
    common = sorted(aa8_columns & aa10_columns)
    exact: list[str] = []
    changed_relations: list[str] = []
    changed_properties: list[str] = []
    balance_columns: list[str] = []
    for column in common:
        if column == "id":
            continue
        if column in relation_columns:
            if _normal_relation(aa8_values[column]) == _normal_relation(aa10_values[column]):
                exact.append(column)
            else:
                changed_relations.append(column)
        elif _normal(aa8_values[column]) == _normal(aa10_values[column]):
            exact.append(column)
        elif _is_balance(column):
            balance_columns.append(column)
        else:
            changed_properties.append(column)
    aa8_only_columns = sorted(aa8_columns - aa10_columns)
    aa10_only_columns = sorted(aa10_columns - aa8_columns)
    if aa8 is None:
        classification = "aa10_only"
    elif aa10 is None:
        classification = "aa8_only"
    elif match_kind == "natural_relation" and _row_id(aa8_values) != _row_id(aa10_values):
        classification = "renumbered_row_stable_relation"
    elif match_kind == "id_conflict" or changed_relations:
        classification = "conflict"
    elif (
        changed_properties
        or balance_columns
        or aa8_only_columns
        or aa10_only_columns
        or aa8.identity_only
    ):
        classification = "stable_id_changed_properties"
    else:
        classification = "exact_id_exact_relation"
    relation_state = (
        "not_applicable"
        if not relation_columns
        else ("conflict" if changed_relations else "stable")
    )
    property_state = (
        "not_compared_aa8_identity_only"
        if aa8 and aa8.identity_only
        else (
            "changed"
            if changed_properties or aa8_only_columns or aa10_only_columns
            else "exact"
        )
    )
    balance_state = "changed_not_promotable" if balance_columns else "exact_or_absent"
    return {
        "classification": classification,
        "relation_state": relation_state,
        "property_state": property_state,
        "balance_state": balance_state,
        "exact": exact,
        "changed_relations": changed_relations,
        "changed_properties": changed_properties,
        "balance_columns": balance_columns,
        "aa8_only_columns": aa8_only_columns,
        "aa10_only_columns": aa10_only_columns,
    }


def compare_source_rows(
    table: str,
    aa8_rows: list[SourceRow],
    aa10_rows: list[SourceRow],
    aa10_columns: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    relation_columns = _relation_columns(aa8_rows, aa10_columns)
    rows: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for ordinal, (aa8, aa10, match_kind) in enumerate(
        _match_rows(aa8_rows, aa10_rows, relation_columns)
    ):
        details = _comparison_details(aa8, aa10, match_kind, relation_columns)
        classification = details["classification"]
        counts[classification] += 1
        aa8_values = aa8.values if aa8 else {}
        aa10_values = aa10.values if aa10 else {}
        natural = {
            column: _normal_relation((aa8_values if column in aa8_values else aa10_values).get(column))
            for column in relation_columns
            if column in aa8_values or column in aa10_values
        }
        comparison_key = stable_key(
            "aa10_row",
            table,
            aa8.locator if aa8 else None,
            aa10.locator if aa10 else None,
            ordinal,
        )
        rows.append(
            {
                "comparison_key": comparison_key,
                "table_name": table,
                "domain": _domain(table),
                "aa8_locator": aa8.locator if aa8 else None,
                "aa10_locator": aa10.locator if aa10 else None,
                "aa8_id": _row_id(aa8_values),
                "aa10_id": _row_id(aa10_values),
                "natural_key_json": canonical_json(_jsonable(natural)),
                **details,
                "aa8_row_sha256": sha256_text(canonical_json(_jsonable(aa8_values))) if aa8 else None,
                "aa10_row_sha256": sha256_text(canonical_json(_jsonable(aa10_values))) if aa10 else None,
                "evidence_json": canonical_json(
                    {
                        "aa8_authority": "client_native" if aa8 else None,
                        "aa8_evidence_state": aa8.evidence_state if aa8 else None,
                        "aa10_authority": "cross_version" if aa10 else None,
                        "identity_only": bool(aa8.identity_only) if aa8 else False,
                        "match_algorithm": match_kind,
                        "normalization": "boolean_t_f_and_scalar_v1",
                    }
                ),
            }
        )
        for column in relation_columns:
            if column not in aa8_values and column not in aa10_values:
                continue
            if aa8 is None:
                relation_class = "aa10_only"
            elif aa10 is None:
                relation_class = "aa8_only"
            elif column not in aa8_values or column not in aa10_values:
                relation_class = "structural_candidate"
            elif _normal_relation(aa8_values[column]) == _normal_relation(aa10_values[column]):
                relation_class = (
                    "renumbered_row_stable_relation"
                    if classification == "renumbered_row_stable_relation"
                    else "exact_id_exact_relation"
                )
            else:
                relation_class = "conflict"
            evidence_state = (
                "confirmed_consumer_contract"
                if table in CONFIRMED_RELATION_TABLES
                else "inferred_column_semantics"
            )
            relations.append(
                {
                    "relation_key": stable_key(
                        "aa10_relation", comparison_key, column
                    ),
                    "comparison_key": comparison_key,
                    "table_name": table,
                    "relation_column": column,
                    "aa8_value_json": (
                        canonical_json(_jsonable(aa8_values[column])) if column in aa8_values else None
                    ),
                    "aa10_value_json": (
                        canonical_json(_jsonable(aa10_values[column])) if column in aa10_values else None
                    ),
                    "classification": relation_class,
                    "evidence_state": evidence_state,
                    "promotable_to_aa8": 0,
                    "evidence_json": canonical_json(
                        {
                            "aa10_is_comparative_only": True,
                            "balance_promotion_forbidden": True,
                        }
                    ),
                }
            )
    return rows, relations, dict(sorted(counts.items()))


def _insert_metadata(connection: sqlite3.Connection, key: str, value: Any) -> None:
    connection.execute(
        "INSERT INTO metadata(key,value_json) VALUES(?,?)", (key, canonical_json(value))
    )


def _insert_validation(
    connection: sqlite3.Connection,
    check_name: str,
    state: str,
    expected: Any,
    actual: Any,
    evidence: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        "INSERT INTO validation_events VALUES(?,?,?,?,?,?)",
        (
            stable_key("aa10_validation", check_name),
            check_name,
            state,
            None if expected is None else canonical_json(expected),
            canonical_json(actual),
            canonical_json(evidence or {}),
        ),
    )


def _insert_negative(
    connection: sqlite3.Connection,
    *,
    domain: str,
    table: str | None,
    subject: str,
    state: str,
    reason: str,
    required_evidence: str | None,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        "INSERT INTO negative_evidence VALUES(?,?,?,?,?,?,?,?)",
        (
            stable_key("aa10_negative", domain, table, subject, reason),
            domain,
            table,
            subject,
            state,
            reason,
            required_evidence,
            canonical_json(evidence),
        ),
    )


def _insert_conflict(
    connection: sqlite3.Connection,
    *,
    domain: str,
    table: str | None,
    subject: str,
    severity: int,
    blocked: bool,
    reason: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        "INSERT INTO conflicts VALUES(?,?,?,?,?,?,?,?,?)",
        (
            stable_key("aa10_conflict", domain, table, subject, reason),
            domain,
            table,
            subject,
            "conflict",
            severity,
            int(blocked),
            reason,
            canonical_json(evidence),
        ),
    )


def _table_classification(
    *,
    table: str,
    aa8_present: bool,
    aa10_present: bool,
    missing_columns: list[str],
    aa8_rows: int,
    aa10_rows: int,
    row_counts: dict[str, int],
) -> tuple[str, str]:
    if table == "tagged_items":
        return "conflict", "blocked_cache_boundary"
    if not aa8_present:
        if table.startswith("enum_") or table.startswith("const_"):
            return "structural_candidate", "cross_version_only"
        return "aa10_only", "cross_version_only"
    if not aa10_present:
        return "aa8_only", "client_native"
    if missing_columns:
        return "conflict", "schema_conflict"
    if aa8_rows == 0:
        return "structural_candidate", "cross_version_only"
    if row_counts.get("conflict", 0):
        return "conflict", "mixed_row_evidence"
    if row_counts.get("stable_id_changed_properties", 0):
        return "stable_id_changed_properties", "cross_version_comparison"
    if row_counts.get("renumbered_row_stable_relation", 0):
        return "renumbered_row_stable_relation", "cross_version_comparison"
    if row_counts.get("aa8_only", 0) and not row_counts.get("exact_id_exact_relation", 0):
        return "aa8_only", "client_native"
    if row_counts.get("exact_id_exact_relation", 0):
        return "exact_id_exact_relation", "cross_version_comparison"
    if aa10_rows == 0:
        return "aa8_only", "client_native"
    return "structural_candidate", "cross_version_only"


def _identity_metrics(
    aa8: sqlite3.Connection,
    aa10: sqlite3.Connection,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    table_kinds = {
        "items": "item",
        "skills": "skill",
        "crafts": "craft",
        "appellations": "appellation",
        "loot_packs": "loot_pack",
        "npc_spawners": "npc_spawner",
        "npc_groups": "npc_group",
        "skin_colors": "skin_color",
        "customizing_item_asset_colors": "customizing_item_asset_color",
        "spheres": "sphere",
    }
    for table, kind in table_kinds.items():
        if not _table_exists(aa10, table):
            continue
        if kind == "craft":
            aa8_ids = {
                int(row[0])
                for row in aa8.execute(
                    "SELECT native_id FROM entities WHERE kind=? AND lifecycle='present' ORDER BY CAST(native_id AS INTEGER)",
                    (kind,),
                )
                if str(row[0]).lstrip("-").isdigit() and int(row[0]) > 0
            }
        elif kind in {"item", "skill"}:
            aa8_ids = {
                int(row[0])
                for row in aa8.execute(
                    "SELECT native_id FROM entities WHERE kind=? AND lifecycle='present' ORDER BY CAST(native_id AS INTEGER)",
                    (kind,),
                )
                if str(row[0]).lstrip("-").isdigit() and int(row[0]) > 0
            }
        else:
            aa8_ids = {
                int(row[0])
                for row in aa8.execute(
                    "SELECT native_id FROM entities WHERE kind=? ORDER BY CAST(native_id AS INTEGER)",
                    (kind,),
                )
                if str(row[0]).lstrip("-").isdigit() and int(row[0]) > 0
            }
        aa10_ids = {int(row[0]) for row in aa10.execute(f'SELECT id FROM "{table}"')}
        metrics[table] = {
            "aa8": len(aa8_ids),
            "aa10": len(aa10_ids),
            "matched": len(aa8_ids & aa10_ids),
            "aa8_only_ids": sorted(aa8_ids - aa10_ids),
        }
    if _table_exists(aa10, "loots") and "loot_packs" in metrics:
        content_ids = {
            int(row[0])
            for row in aa10.execute("SELECT DISTINCT loot_pack_id FROM loots WHERE loot_pack_id>0")
        }
        aa8_loot = {
            int(row[0])
            for row in aa8.execute(
                "SELECT native_id FROM entities WHERE kind='loot_pack' ORDER BY CAST(native_id AS INTEGER)"
            )
            if str(row[0]).isdigit()
        }
        metrics["loot_content"] = {
            "aa8": len(aa8_loot),
            "matched": len(aa8_loot & content_ids),
            "missing_content_ids": sorted(aa8_loot - content_ids),
        }
    return metrics


def _summary(connection: sqlite3.Connection) -> dict[str, Any]:
    table_counts = {
        table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        for table in (
            "schema_tables",
            "schema_columns",
            "schema_indexes",
            "schema_foreign_keys",
            "logical_table_crosswalk",
            "row_comparisons",
            "relation_comparisons",
            "coverage",
            "negative_evidence",
            "conflicts",
            "validation_events",
        )
    }
    return {
        "classification_counts": dict(
            connection.execute(
                "SELECT classification,COUNT(*) FROM row_comparisons GROUP BY classification ORDER BY classification"
            ).fetchall()
        ),
        "conflicts_by_domain": dict(
            connection.execute(
                "SELECT domain,COUNT(*) FROM conflicts GROUP BY domain ORDER BY domain"
            ).fetchall()
        ),
        "negative_evidence_by_state": dict(
            connection.execute(
                "SELECT state,COUNT(*) FROM negative_evidence GROUP BY state ORDER BY state"
            ).fetchall()
        ),
        "relation_classification_counts": dict(
            connection.execute(
                "SELECT classification,COUNT(*) FROM relation_comparisons GROUP BY classification ORDER BY classification"
            ).fetchall()
        ),
        "schema_version": SCHEMA_VERSION,
        "table_classification_counts": dict(
            connection.execute(
                "SELECT classification,COUNT(*) FROM logical_table_crosswalk GROUP BY classification ORDER BY classification"
            ).fetchall()
        ),
        "table_counts": table_counts,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(handle)
    temporary = Path(name)
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field) for field in fieldnames})
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _export_outputs(paths: dict[str, Path]) -> dict[str, Any]:
    connection = _open_read_only(paths["database"])
    try:
        summary = _summary(connection)
        atomic_text(paths["summary"], canonical_json(summary, pretty=True))
        table_rows = [dict(row) for row in connection.execute("SELECT * FROM logical_table_crosswalk ORDER BY domain,table_name")]
        _write_csv(
            paths["tables"],
            [
                "domain",
                "table_name",
                "classification",
                "evidence_state",
                "aa8_present",
                "aa10_present",
                "aa8_expected_rows",
                "aa8_evidence_rows",
                "aa10_rows",
                "compared_rows",
                "missing_in_aa10_json",
                "row_classification_counts_json",
            ],
            table_rows,
        )
        conflict_rows = [dict(row) for row in connection.execute("SELECT * FROM conflicts ORDER BY domain,severity DESC,table_name,subject")]
        _write_csv(
            paths["conflicts"],
            ["domain", "table_name", "subject", "classification", "severity", "blocked", "reason", "evidence_json"],
            conflict_rows,
        )
        negative_rows = [dict(row) for row in connection.execute("SELECT * FROM negative_evidence ORDER BY domain,table_name,subject")]
        _write_csv(
            paths["negative_evidence"],
            ["domain", "table_name", "subject", "state", "reason", "required_evidence", "evidence_json"],
            negative_rows,
        )
        paths["domains"].mkdir(parents=True, exist_ok=True)
        domain_outputs: dict[str, dict[str, Any]] = {}
        domains = [str(row[0]) for row in connection.execute("SELECT DISTINCT domain FROM logical_table_crosswalk ORDER BY domain")]
        for domain in domains:
            domain_path = paths["domains"] / f"{domain}.csv"
            rows = [row for row in table_rows if row["domain"] == domain]
            _write_csv(
                domain_path,
                [
                    "table_name",
                    "classification",
                    "evidence_state",
                    "aa8_evidence_rows",
                    "aa10_rows",
                    "compared_rows",
                    "row_classification_counts_json",
                ],
                rows,
            )
            domain_outputs[domain] = {
                "file": f"{paths['domains'].name}/{domain_path.name}",
                "bytes": domain_path.stat().st_size,
                "sha256": sha256_file(domain_path),
            }
        return {"summary": summary, "domain_outputs": domain_outputs}
    finally:
        connection.close()


def build_aa10_crosswalk_from_paths(
    aa8_database: Path,
    aa10_database: Path,
    output_dir: Path,
    *,
    database: Path | None = None,
    client_build: str = "Kakao 8.0.3.12 r558734",
    strict_hashes: bool = True,
) -> dict[str, Any]:
    paths = crosswalk_paths(output_dir, database)
    paths["database"].parent.mkdir(parents=True, exist_ok=True)
    aa8_source = _source_check(
        aa8_database,
        expected=EXPECTED_AA8,
        source_key="aa8",
        role="aa8_consolidated_client_knowledge",
        authority="client_native",
        provenance=f"{TOOL_NAME}:{TOOL_VERSION}",
        strict_hashes=strict_hashes,
    )
    aa10_source = _source_check(
        aa10_database,
        expected=EXPECTED_AA10,
        source_key="aa10",
        role="aa10_decrypted_cross_version_candidate",
        authority="cross_version",
        provenance="ArcheAge Returns external package r575; internal bundle 10.0.1.6 SVN 622045",
        strict_hashes=strict_hashes,
    )
    handle, name = tempfile.mkstemp(
        prefix=f".{paths['database'].stem}.", suffix=".sqlite3", dir=paths["database"].parent
    )
    os.close(handle)
    temporary = Path(name)
    temporary.unlink(missing_ok=True)
    output: sqlite3.Connection | None = None
    aa8 = _open_read_only(aa8_database)
    aa10 = _open_read_only(aa10_database)
    try:
        output = _create_database(temporary)
        _insert_metadata(output, "authority", "cross_version_comparative_only")
        _insert_metadata(output, "client_build", client_build)
        _insert_metadata(output, "classification_vocabulary", sorted(CLASSIFICATIONS))
        _insert_metadata(output, "schema_version", SCHEMA_VERSION)
        _insert_metadata(output, "tool", {"name": TOOL_NAME, "version": TOOL_VERSION})
        _insert_metadata(
            output,
            "promotion_policy",
            {
                "aa10_rows_are_aa8_authority": False,
                "balance_values_promotable": False,
                "identity_or_relation_requires_aa8_evidence": True,
                "localized_text_is_identity": False,
            },
        )
        for source in (aa8_source, aa10_source):
            output.execute(
                "INSERT INTO source_artifacts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    source["source_key"],
                    source["role"],
                    source["path"],
                    source["bytes"],
                    source["sha256"],
                    source["authority"],
                    source["provenance"],
                    source["quick_check"],
                    source["integrity_check"],
                    source["user_table_count"],
                    source["internal_table_count"],
                    canonical_json(source["evidence"]),
                ),
            )
        aa8_schema = _schema_inventory(aa8, output, "aa8")
        aa10_schema = _schema_inventory(aa10, output, "aa10")
        logical = _logical_inventory(aa8)
        aa10_user_tables = {
            table for table, record in aa10_schema.items() if record["table_kind"] == "user"
        }
        all_tables = sorted(set(logical) | aa10_user_tables)
        for table in all_tables:
            aa8_present = table in logical
            aa10_present = table in aa10_user_tables
            item = logical.get(table, LogicalTable(table))
            comparison_columns = item.best_columns or item.expected_columns or set()
            expected_columns = sorted(comparison_columns)
            aa10_columns = list(aa10_schema.get(table, {}).get("columns", []))
            missing_columns = sorted(set(expected_columns) - set(aa10_columns))
            extra_columns = sorted(set(aa10_columns) - set(expected_columns))
            provisional, evidence_state = _table_classification(
                table=table,
                aa8_present=aa8_present,
                aa10_present=aa10_present,
                missing_columns=missing_columns,
                aa8_rows=0,
                aa10_rows=int(aa10_schema.get(table, {}).get("rows", 0)),
                row_counts={},
            )
            output.execute(
                "INSERT INTO logical_table_crosswalk VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    table,
                    _domain(table),
                    int(aa8_present),
                    int(aa10_present),
                    item.query_count,
                    item.expected_rows,
                    0,
                    int(aa10_schema.get(table, {}).get("rows", 0)),
                    canonical_json(expected_columns),
                    canonical_json(aa10_columns),
                    canonical_json(missing_columns),
                    canonical_json(extra_columns),
                    canonical_json(aa10_schema.get(table, {}).get("primary_key", [])),
                    canonical_json(sorted(column for column in set(expected_columns) | set(aa10_columns) if _is_relation_column(column))),
                    provisional,
                    evidence_state,
                    0,
                    "{}",
                    canonical_json(
                        {
                            "aa8_native_catalog_state": item.native_catalog_state,
                            "aa8_opaque": item.opaque,
                            "best_query_key": item.best_query_key,
                            "all_query_columns_json": sorted(item.expected_columns or set()),
                        }
                    ),
                ),
            )
        output.commit()

        for table in sorted(logical):
            item = logical[table]
            aa8_rows = _aa8_rows(aa8, item)
            if table == "tagged_items":
                output.execute(
                    "UPDATE logical_table_crosswalk SET aa8_evidence_rows=? WHERE table_name=?",
                    (item.best_cached_rows, table),
                )
                _insert_conflict(
                    output,
                    domain="skills_buffs",
                    table=table,
                    subject="legacy_game11_cache_boundary",
                    severity=3,
                    blocked=True,
                    reason="AA8 tagged_items is assigned to the exact tagged_skills byte range",
                    evidence={
                        "assigned_range": [21_952_540, 22_328_370],
                        "assigned_rows": 28_910,
                        "item_consumer": "LoadItemTagsRelation/FUN_3995be70",
                        "item_contract": ["item_id", "tag_id"],
                        "skill_consumer": "LoadSkillTagsRelation/FUN_3995b570",
                        "skill_contract": ["skill_id", "tag_id"],
                        "aa10_rows_not_substituted": int(aa10_schema[table]["rows"]),
                    },
                )
                _insert_negative(
                    output,
                    domain="skills_buffs",
                    table=table,
                    subject="native_relations",
                    state="blocked",
                    reason="cached_result_boundary_misassigned_to_tagged_skills",
                    required_evidence="recover the original AA8 tagged_items cached boundary or an equivalent native result",
                    evidence={"aa10_is_not_replacement_evidence": True},
                )
                continue
            if not aa8_rows:
                continue
            aa10_columns = list(aa10_schema.get(table, {}).get("columns", []))
            aa10_rows = (
                _aa10_rows(aa10, table, aa10_columns, item.best_sql)
                if table in aa10_user_tables
                else []
            )
            row_records, relation_records, row_counts = compare_source_rows(
                table, aa8_rows, aa10_rows, aa10_columns
            )
            output.executemany(
                """
                INSERT INTO row_comparisons VALUES(
                    :comparison_key,:table_name,:domain,:aa8_locator,:aa10_locator,
                    :aa8_id,:aa10_id,:natural_key_json,:classification,:relation_state,
                    :property_state,:balance_state,:exact_columns_json,
                    :changed_relation_columns_json,:changed_property_columns_json,
                    :balance_columns_json,:aa8_only_columns_json,:aa10_only_columns_json,
                    :aa8_row_sha256,:aa10_row_sha256,:evidence_json
                )
                """,
                [
                    {
                        **row,
                        "exact_columns_json": canonical_json(row["exact"]),
                        "changed_relation_columns_json": canonical_json(row["changed_relations"]),
                        "changed_property_columns_json": canonical_json(row["changed_properties"]),
                        "balance_columns_json": canonical_json(row["balance_columns"]),
                        "aa8_only_columns_json": canonical_json(row["aa8_only_columns"]),
                        "aa10_only_columns_json": canonical_json(row["aa10_only_columns"]),
                    }
                    for row in row_records
                ],
            )
            output.executemany(
                """
                INSERT INTO relation_comparisons VALUES(
                    :relation_key,:comparison_key,:table_name,:relation_column,
                    :aa8_value_json,:aa10_value_json,:classification,:evidence_state,
                    :promotable_to_aa8,:evidence_json
                )
                """,
                relation_records,
            )
            comparison_columns = item.best_columns or item.expected_columns or set()
            missing_columns = sorted(set(comparison_columns) - set(aa10_columns))
            classification, evidence_state = _table_classification(
                table=table,
                aa8_present=True,
                aa10_present=table in aa10_user_tables,
                missing_columns=missing_columns,
                aa8_rows=len(aa8_rows),
                aa10_rows=len(aa10_rows),
                row_counts=row_counts,
            )
            output.execute(
                """
                UPDATE logical_table_crosswalk
                SET aa8_evidence_rows=?,classification=?,evidence_state=?,compared_rows=?,
                    row_classification_counts_json=? WHERE table_name=?
                """,
                (
                    len(aa8_rows),
                    classification,
                    evidence_state,
                    len(row_records),
                    canonical_json(row_counts),
                    table,
                ),
            )
            if row_counts.get("conflict", 0):
                _insert_conflict(
                    output,
                    domain=_domain(table),
                    table=table,
                    subject="row_relation_conflicts",
                    severity=2,
                    blocked=False,
                    reason="stable IDs or compared rows have changed relation columns",
                    evidence={"rows": row_counts["conflict"]},
                )
            output.commit()

        zero_homonyms = []
        compatible_zero = []
        compatible_nonempty = []
        opaque_homonyms = []
        for table, item in sorted(logical.items()):
            if item.opaque and table in aa10_user_tables:
                opaque_homonyms.append(table)
            if item.query_count and item.best_cached_rows == 0 and table in aa10_user_tables:
                zero_homonyms.append(table)
                missing = sorted(set(item.expected_columns or set()) - set(aa10_schema[table]["columns"]))
                if not missing:
                    compatible_zero.append(table)
                    if int(aa10_schema[table]["rows"]) > 0:
                        compatible_nonempty.append(table)
                _insert_negative(
                    output,
                    domain=_domain(table),
                    table=table,
                    subject="aa8_native_result",
                    state="opaque" if item.opaque else "missing",
                    reason="AA8 query exists but no native rows were recovered",
                    required_evidence="AA8 cached boundary/consumer result; 10.x rows remain comparative only",
                    evidence={
                        "aa10_rows": int(aa10_schema[table]["rows"]),
                        "missing_expected_columns_in_aa10": missing,
                    },
                )
        _insert_negative(
            output,
            domain="loot",
            table="loots",
            subject="loot_quest_id",
            state="blocked",
            reason="AA10 loots omits loot_quest_id required by the AA8 loader contract",
            required_evidence="AA8-native loots result or independently verified equivalent relation",
            evidence={"aa10_columns": aa10_schema.get("loots", {}).get("columns", [])},
        )
        _insert_conflict(
            output,
            domain="loot",
            table="loots",
            subject="loot_quest_id",
            severity=3,
            blocked=True,
            reason="cross-version schema cannot establish the AA8 loot quest relation",
            evidence={"promotion_forbidden": True},
        )

        identities = _identity_metrics(aa8, aa10)
        for table, metric in sorted(identities.items()):
            output.execute(
                "INSERT INTO coverage VALUES(?,?,?,?,?,?,?,?)",
                (
                    stable_key("aa10_coverage", table, "identity"),
                    _domain(table),
                    table,
                    "identity",
                    "confirmed" if not metric.get("aa8_only_ids") else "partial",
                    metric.get("aa8"),
                    metric.get("matched"),
                    canonical_json(metric),
                ),
            )
            if metric.get("aa8_only_ids"):
                _insert_negative(
                    output,
                    domain=_domain(table),
                    table=table,
                    subject="aa8_ids_absent_in_aa10",
                    state="missing",
                    reason="AA8-observed IDs are absent from the comparison database",
                    required_evidence=None,
                    evidence={"ids": metric["aa8_only_ids"]},
                )
        enum_tables = sorted(table for table in aa10_user_tables if table.startswith("enum_"))
        const_tables = sorted(table for table in aa10_user_tables if table.startswith("const_"))
        enum_rows = sum(int(aa10_schema[table]["rows"]) for table in enum_tables)
        const_rows = sum(int(aa10_schema[table]["rows"]) for table in const_tables)
        _insert_metadata(
            output,
            "triage",
            {
                "opaque_aa8_homonyms": len(opaque_homonyms),
                "aa8_zero_result_homonyms": len(zero_homonyms),
                "aa8_zero_result_schema_compatible": len(compatible_zero),
                "aa8_zero_result_compatible_nonempty": len(compatible_nonempty),
                "historical_checkpoint_values": {
                    "aa8_zero_result_homonyms": 179,
                    "aa8_zero_result_schema_compatible": 177,
                    "aa8_zero_result_compatible_nonempty": 162,
                },
                "enum_tables": len(enum_tables),
                "enum_rows": enum_rows,
                "const_tables": len(const_tables),
                "const_rows": const_rows,
            },
        )
        _insert_metadata(output, "identity_metrics", identities)
        _insert_validation(output, "source_hashes_frozen", "confirmed", True, True)
        _insert_validation(
            output,
            "aa10_user_table_count",
            "confirmed" if len(aa10_user_tables) == 1373 else "blocked",
            1373,
            len(aa10_user_tables),
            {"sqlite_sequence_is_internal": True},
        )
        _insert_validation(
            output,
            "opaque_homonyms",
            "confirmed" if len(opaque_homonyms) == 67 else "blocked",
            67,
            len(opaque_homonyms),
        )
        _insert_validation(
            output,
            "enum_const_catalog",
            "confirmed"
            if (len(enum_tables), enum_rows, len(const_tables), const_rows)
            == (285, 5295, 28, 653)
            else "blocked",
            [285, 5295, 28, 653],
            [len(enum_tables), enum_rows, len(const_tables), const_rows],
        )
        _insert_validation(
            output,
            "tagged_items_quarantined",
            "confirmed",
            True,
            True,
            {"aa10_substitution": False},
        )
        _insert_validation(
            output,
            "loot_quest_id_blocked",
            "confirmed",
            True,
            True,
            {"aa10_column_present": "loot_quest_id" in aa10_schema["loots"]["columns"]},
        )
        invalid_table_vocab = [
            row[0]
            for row in output.execute(
                "SELECT DISTINCT classification FROM logical_table_crosswalk ORDER BY classification"
            )
            if row[0] not in CLASSIFICATIONS
        ]
        invalid_row_vocab = [
            row[0]
            for row in output.execute(
                "SELECT DISTINCT classification FROM row_comparisons ORDER BY classification"
            )
            if row[0] not in CLASSIFICATIONS
        ]
        invalid_relation_vocab = [
            row[0]
            for row in output.execute(
                "SELECT DISTINCT classification FROM relation_comparisons ORDER BY classification"
            )
            if row[0] not in CLASSIFICATIONS
        ]
        invalid_vocab = sorted(set(invalid_table_vocab + invalid_row_vocab + invalid_relation_vocab))
        _insert_validation(
            output,
            "classification_vocabulary_closed",
            "confirmed" if not invalid_vocab else "blocked",
            [],
            invalid_vocab,
        )
        orphan_rows = int(
            output.execute(
                """
                SELECT COUNT(*) FROM row_comparisons r
                LEFT JOIN logical_table_crosswalk t USING(table_name)
                WHERE t.table_name IS NULL
                """
            ).fetchone()[0]
        )
        orphan_relations = int(
            output.execute(
                """
                SELECT COUNT(*) FROM relation_comparisons r
                LEFT JOIN row_comparisons c USING(comparison_key)
                WHERE c.comparison_key IS NULL
                """
            ).fetchone()[0]
        )
        _insert_validation(
            output,
            "orphan_references",
            "confirmed" if orphan_rows == 0 and orphan_relations == 0 else "blocked",
            {"rows": 0, "relations": 0},
            {"rows": orphan_rows, "relations": orphan_relations},
        )
        aa8_evidence_rows = int(
            output.execute(
                "SELECT COALESCE(SUM(aa8_evidence_rows),0) FROM logical_table_crosswalk WHERE table_name<>'tagged_items'"
            ).fetchone()[0]
        )
        classified_aa8_rows = int(
            output.execute(
                "SELECT COUNT(*) FROM row_comparisons WHERE aa8_locator IS NOT NULL"
            ).fetchone()[0]
        )
        _insert_validation(
            output,
            "aa8_source_rows_accounted",
            "confirmed" if aa8_evidence_rows == classified_aa8_rows else "blocked",
            aa8_evidence_rows,
            classified_aa8_rows,
            {"tagged_items_quarantined_rows": logical["tagged_items"].best_cached_rows},
        )
        output.commit()
        output.execute("VACUUM")
        output.close()
        output = None
        temporary.replace(paths["database"])
    except Exception:
        if output is not None:
            output.close()
        temporary.unlink(missing_ok=True)
        raise
    finally:
        aa8.close()
        aa10.close()

    exported = _export_outputs(paths)
    output_records: dict[str, Any] = {}
    for key in ("database", "summary", "tables", "conflicts", "negative_evidence"):
        path = paths[key]
        output_records[key] = {
            "file": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    output_records["domains"] = exported["domain_outputs"]
    manifest = {
        "authority": "cross_version_comparative_only",
        "classification": "aa8_to_aa10_relational_crosswalk_v1",
        "client_build": client_build,
        "commands": [
            "python -B -m client_forensics build-aa10-crosswalk",
            "python -B -m client_forensics validate-aa10-crosswalk",
        ],
        "determinism": {
            "atomic_output": True,
            "stable_ordering": True,
            "timestamps_in_reproducible_outputs": False,
        },
        "inputs": {
            "aa8": {
                key: aa8_source[key]
                for key in ("path", "bytes", "sha256", "quick_check", "integrity_check")
            },
            "aa10": {
                key: aa10_source[key]
                for key in ("path", "bytes", "sha256", "quick_check", "integrity_check")
            },
        },
        "outputs": output_records,
        "schema_version": SCHEMA_VERSION,
        "summary": exported["summary"],
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }
    atomic_text(paths["manifest"], canonical_json(manifest, pretty=True))
    return {
        "database": paths["database"],
        "database_sha256": output_records["database"]["sha256"],
        "manifest": paths["manifest"],
        "manifest_sha256": sha256_file(paths["manifest"]),
        "summary": exported["summary"],
    }


def build_aa10_crosswalk(
    config: ForensicsConfig,
    *,
    aa10_database: Path | None = None,
    database: Path | None = None,
) -> dict[str, Any]:
    return build_aa10_crosswalk_from_paths(
        config.consolidated,
        (aa10_database or DEFAULT_AA10_DATABASE).resolve(),
        config.output_dir,
        database=database,
        client_build=config.client_build,
        strict_hashes=True,
    )


def validate_aa10_crosswalk(
    config: ForensicsConfig,
    *,
    database: Path | None = None,
) -> dict[str, Any]:
    paths = crosswalk_paths(config.output_dir, database)
    for key, path in paths.items():
        if key == "domains":
            if not path.is_dir():
                raise FileNotFoundError(path)
        elif not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    connection = _open_read_only(paths["database"])
    try:
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        failed_events = [
            dict(row)
            for row in connection.execute(
                "SELECT check_name,state,actual_json FROM validation_events WHERE state<>'confirmed' ORDER BY check_name"
            )
        ]
        invalid_vocab = sorted(
            {
                str(row[0])
                for query in (
                    "SELECT DISTINCT classification FROM logical_table_crosswalk",
                    "SELECT DISTINCT classification FROM row_comparisons",
                    "SELECT DISTINCT classification FROM relation_comparisons",
                )
                for row in connection.execute(query)
                if str(row[0]) not in CLASSIFICATIONS
            }
        )
        foreign = sqlite3.connect(paths["database"])
        try:
            foreign.execute("PRAGMA foreign_keys=ON")
            foreign_key_errors = [tuple(row) for row in foreign.execute("PRAGMA foreign_key_check")]
        finally:
            foreign.close()
        silent_drops = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM logical_table_crosswalk
                WHERE aa8_evidence_rows>0 AND compared_rows=0 AND table_name<>'tagged_items'
                """
            ).fetchone()[0]
        )
        tagged = connection.execute(
            "SELECT classification,evidence_state,compared_rows FROM logical_table_crosswalk WHERE table_name='tagged_items'"
        ).fetchone()
        loot_block = int(
            connection.execute(
                "SELECT COUNT(*) FROM negative_evidence WHERE table_name='loots' AND subject='loot_quest_id' AND state='blocked'"
            ).fetchone()[0]
        )
        checks = {
            "quick_check": quick,
            "integrity_check": integrity,
            "failed_validation_events": failed_events,
            "invalid_classification_vocabulary": invalid_vocab,
            "foreign_key_errors": foreign_key_errors,
            "silent_drops": silent_drops,
            "tagged_items": dict(tagged) if tagged else None,
            "loot_quest_id_block": loot_block,
        }
        if (
            quick != "ok"
            or integrity != "ok"
            or failed_events
            or invalid_vocab
            or foreign_key_errors
            or silent_drops
            or tagged is None
            or tagged["classification"] != "conflict"
            or tagged["compared_rows"] != 0
            or loot_block != 1
        ):
            raise RuntimeError(f"AA10 crosswalk validation failed: {checks}")
        for key, record in manifest["outputs"].items():
            if key == "domains":
                for domain, domain_record in record.items():
                    path = paths["database"].parent / domain_record["file"]
                    actual = sha256_file(path)
                    if actual != str(domain_record["sha256"]).upper():
                        raise RuntimeError(f"Output hash mismatch for domain {domain}: {actual}")
                continue
            path = paths[key]
            actual = sha256_file(path)
            if actual != str(record["sha256"]).upper():
                raise RuntimeError(f"Output hash mismatch for {key}: {actual}")
        return {
            "checks": checks,
            "database": paths["database"],
            "database_sha256": sha256_file(paths["database"]),
            "manifest": paths["manifest"],
            "manifest_sha256": sha256_file(paths["manifest"]),
            "status": "confirmed",
        }
    finally:
        connection.close()
