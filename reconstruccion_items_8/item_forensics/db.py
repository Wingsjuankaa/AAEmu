from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

from . import SCHEMA_VERSION


SCHEMA = """
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE artifacts (
    artifact_id INTEGER PRIMARY KEY,
    role TEXT NOT NULL,
    path TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    sha256 TEXT,
    provenance TEXT NOT NULL,
    UNIQUE(role, path)
);

CREATE TABLE query_specs (
    query_spec_id INTEGER PRIMARY KEY,
    table_name TEXT NOT NULL,
    source_module TEXT NOT NULL,
    sql_text TEXT,
    columns_json TEXT NOT NULL,
    layout_json TEXT NOT NULL,
    stream_name TEXT NOT NULL,
    start_offset INTEGER,
    expected_rows INTEGER,
    anchor_json TEXT,
    loader_consumer TEXT,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(table_name, source_module, stream_name, start_offset)
);

CREATE TABLE cached_results (
    cached_result_id INTEGER PRIMARY KEY,
    query_spec_id INTEGER NOT NULL REFERENCES query_specs(query_spec_id),
    artifact_id INTEGER REFERENCES artifacts(artifact_id),
    start_offset INTEGER,
    end_offset INTEGER,
    row_count INTEGER,
    row_digest TEXT,
    raw_references_json TEXT NOT NULL,
    unresolved_references_json TEXT NOT NULL,
    resolution_evidence_json TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    UNIQUE(query_spec_id)
);

CREATE TABLE cached_result_rows (
    query_spec_id INTEGER NOT NULL REFERENCES query_specs(query_spec_id),
    row_index INTEGER NOT NULL,
    row_json TEXT NOT NULL,
    PRIMARY KEY(query_spec_id, row_index)
) WITHOUT ROWID;

CREATE TABLE native_catalogs (
    table_name TEXT PRIMARY KEY,
    entity_kind TEXT NOT NULL,
    id_column TEXT NOT NULL,
    state TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    distinct_ids INTEGER NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE native_entities (
    entity_kind TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    source_table TEXT NOT NULL,
    state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY(entity_kind, entity_id, source_table)
) WITHOUT ROWID;

CREATE TABLE items (
    item_id INTEGER PRIMARY KEY,
    impl_id INTEGER NOT NULL,
    name TEXT,
    description TEXT,
    category_id INTEGER,
    level INTEGER,
    use_skill_id INTEGER,
    buff_id INTEGER,
    craft_id INTEGER,
    loot_quest_id INTEGER,
    client_row_json TEXT NOT NULL,
    client_provenance TEXT NOT NULL
);

CREATE TABLE descriptors (
    descriptor_id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    family TEXT NOT NULL,
    table_name TEXT,
    row_key TEXT,
    descriptor_json TEXT NOT NULL,
    state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(item_id, family, table_name, row_key)
);

CREATE TABLE dependency_edges (
    dependency_id INTEGER PRIMARY KEY,
    src_kind TEXT NOT NULL,
    src_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    dst_kind TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    required INTEGER NOT NULL CHECK(required IN (0, 1)),
    state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(src_kind, src_id, relation, dst_kind, dst_id)
);

CREATE TABLE runtime_coverage (
    item_id INTEGER PRIMARY KEY,
    concrete_type TEXT NOT NULL,
    coverage TEXT NOT NULL,
    missing_dependencies TEXT NOT NULL,
    provenance TEXT NOT NULL,
    runtime_present INTEGER NOT NULL CHECK(runtime_present IN (0, 1))
);

CREATE TABLE server_capabilities (
    item_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    state TEXT NOT NULL,
    capability TEXT NOT NULL,
    evidence_kind TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY(item_id, dimension)
) WITHOUT ROWID;

CREATE TABLE gaps (
    gap_id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    state TEXT NOT NULL,
    severity INTEGER NOT NULL,
    blocker_code TEXT NOT NULL,
    reason TEXT NOT NULL,
    required_evidence TEXT NOT NULL,
    UNIQUE(item_id, dimension, blocker_code)
);

CREATE TABLE opaque_regions (
    opaque_id INTEGER PRIMARY KEY,
    surface TEXT NOT NULL,
    locator TEXT NOT NULL,
    blocker_code TEXT NOT NULL,
    reason TEXT NOT NULL,
    searched_evidence_json TEXT NOT NULL,
    UNIQUE(surface, locator, blocker_code)
);

CREATE TABLE validation_events (
    validation_id INTEGER PRIMARY KEY,
    scope_kind TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(scope_kind, scope_id, check_name)
);

CREATE TABLE source_hints (
    hint_id INTEGER PRIMARY KEY,
    item_id INTEGER,
    family TEXT NOT NULL,
    hint_kind TEXT NOT NULL,
    locator TEXT NOT NULL,
    value TEXT NOT NULL,
    authority INTEGER NOT NULL CHECK(authority IN (0, 1)),
    UNIQUE(item_id, family, hint_kind, locator, value)
);

CREATE TABLE review_manifests (
    review_manifest_id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    authority TEXT,
    classification_json TEXT NOT NULL,
    summary_json TEXT NOT NULL
);

CREATE TABLE client_surfaces (
    surface_id INTEGER PRIMARY KEY,
    source_kind TEXT NOT NULL,
    path TEXT NOT NULL,
    extension TEXT NOT NULL,
    bytes INTEGER,
    sha256 TEXT,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(source_kind, path)
);

CREATE TABLE surface_inventory (
    source_kind TEXT NOT NULL,
    extension TEXT NOT NULL,
    file_count INTEGER NOT NULL,
    total_bytes INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY(source_kind, extension)
) WITHOUT ROWID;

CREATE TABLE surface_references (
    reference_id INTEGER PRIMARY KEY,
    surface_id INTEGER NOT NULL REFERENCES client_surfaces(surface_id),
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    token_kind TEXT NOT NULL,
    locator TEXT NOT NULL,
    state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(surface_id, item_id, token_kind, locator)
);

CREATE INDEX ix_items_impl ON items(impl_id);
CREATE INDEX ix_cached_result_rows_spec ON cached_result_rows(query_spec_id);
CREATE INDEX ix_native_entities_id ON native_entities(entity_kind, entity_id, state);
CREATE INDEX ix_descriptors_item ON descriptors(item_id);
CREATE INDEX ix_descriptors_family ON descriptors(family, state);
CREATE INDEX ix_dependencies_src ON dependency_edges(src_kind, src_id);
CREATE INDEX ix_dependencies_dst ON dependency_edges(dst_kind, dst_id);
CREATE INDEX ix_capabilities_state ON server_capabilities(dimension, state);
CREATE INDEX ix_gaps_item ON gaps(item_id, severity DESC);
CREATE INDEX ix_gaps_blocker ON gaps(blocker_code, severity DESC);
CREATE INDEX ix_client_surfaces_kind ON client_surfaces(source_kind, extension);
CREATE INDEX ix_surface_references_item ON surface_references(item_id, provenance);

CREATE VIEW item_summary AS
SELECT
    i.item_id,
    i.impl_id,
    i.name,
    COALESCE(
        NULLIF(rc.concrete_type, 'generic'),
        (SELECT d.family FROM descriptors d
         WHERE d.item_id=i.item_id
         ORDER BY CASE d.state WHEN 'confirmed' THEN 0 ELSE 1 END, d.family
         LIMIT 1),
        CASE WHEN i.impl_id=0 THEN 'generic' ELSE 'unmapped_impl_' || i.impl_id END
    ) AS family,
    COALESCE(rc.coverage, 'unknown') AS runtime_coverage,
    COALESCE(
        (SELECT MAX(g.severity) FROM gaps g WHERE g.item_id=i.item_id),
        0
    ) AS max_gap_severity,
    (SELECT COUNT(*) FROM gaps g WHERE g.item_id=i.item_id) AS gap_count,
    (SELECT COUNT(*) FROM dependency_edges e
     WHERE e.src_kind='item' AND e.src_id=CAST(i.item_id AS TEXT)) AS dependency_count
FROM items i
LEFT JOIN runtime_coverage rc ON rc.item_id=i.item_id;
"""


def create_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA page_size=4096")
    connection.execute("PRAGMA auto_vacuum=NONE")
    connection.executescript(SCHEMA)
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return connection


def open_database(path: Path, *, writable: bool = True) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"Forensics database not found: {path}")
    if writable:
        connection = sqlite3.connect(path)
    else:
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        connection.execute("PRAGMA query_only=ON")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version != SCHEMA_VERSION:
        connection.close()
        raise ValueError(
            f"Unsupported forensics schema {version}; expected {SCHEMA_VERSION}"
        )
    return connection


def set_metadata(connection: sqlite3.Connection, values: dict[str, Any]) -> None:
    connection.executemany(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)",
        ((key, str(value)) for key, value in sorted(values.items())),
    )


def insert_many(
    connection: sqlite3.Connection,
    statement: str,
    rows: Iterable[Iterable[Any]],
) -> None:
    connection.executemany(statement, rows)


def finalize_database(connection: sqlite3.Connection) -> tuple[str, str]:
    connection.commit()
    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(
            f"Forensics SQLite validation failed: quick={quick}, integrity={integrity}"
        )
    connection.execute("VACUUM")
    connection.commit()
    return quick, integrity
