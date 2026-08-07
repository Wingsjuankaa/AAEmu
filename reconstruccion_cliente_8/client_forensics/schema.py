from __future__ import annotations

import sqlite3
from pathlib import Path

from . import SCHEMA_VERSION


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE stage_lineage (
    stage_id INTEGER PRIMARY KEY,
    database_name TEXT NOT NULL,
    database_sha256 TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    source_artifact_key TEXT NOT NULL
);

CREATE TABLE artifacts (
    artifact_key TEXT PRIMARY KEY,
    source_stage INTEGER NOT NULL,
    role TEXT NOT NULL,
    path TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    sha256 TEXT,
    build TEXT,
    authority TEXT NOT NULL,
    state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE decoders (
    decoder_key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    sha256 TEXT,
    status TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    assumptions_json TEXT NOT NULL,
    provenance TEXT NOT NULL
);

CREATE TABLE surfaces (
    surface_key TEXT PRIMARY KEY,
    source_stage INTEGER NOT NULL,
    source_kind TEXT NOT NULL,
    locator TEXT NOT NULL,
    extension TEXT,
    bytes INTEGER,
    sha256 TEXT,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE surface_inventory (
    source_kind TEXT NOT NULL,
    extension TEXT NOT NULL,
    file_count INTEGER NOT NULL,
    total_bytes INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY (source_kind, extension)
);

CREATE TABLE review_manifests (
    review_manifest_key TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    authority TEXT NOT NULL,
    classification_json TEXT NOT NULL,
    summary_json TEXT NOT NULL
);

CREATE TABLE query_specs (
    query_key TEXT PRIMARY KEY,
    source_query_spec_id INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    source_module TEXT NOT NULL,
    sql_text TEXT,
    columns_json TEXT NOT NULL,
    layout_json TEXT NOT NULL,
    stream_name TEXT,
    start_offset INTEGER,
    expected_rows INTEGER,
    anchor_json TEXT NOT NULL,
    loader_consumer TEXT,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE cached_results (
    cached_result_key TEXT PRIMARY KEY,
    source_cached_result_id INTEGER NOT NULL,
    query_key TEXT NOT NULL,
    artifact_key TEXT,
    start_offset INTEGER,
    end_offset INTEGER,
    row_count INTEGER,
    row_digest TEXT,
    raw_references_json TEXT NOT NULL,
    unresolved_references_json TEXT NOT NULL,
    resolution_evidence_json TEXT NOT NULL,
    state TEXT NOT NULL,
    error TEXT,
    FOREIGN KEY (query_key) REFERENCES query_specs(query_key),
    FOREIGN KEY (artifact_key) REFERENCES artifacts(artifact_key)
);

CREATE TABLE cached_result_rows (
    query_key TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    row_json TEXT NOT NULL,
    PRIMARY KEY (query_key, row_index),
    FOREIGN KEY (query_key) REFERENCES query_specs(query_key)
);

CREATE TABLE native_catalogs (
    table_name TEXT PRIMARY KEY,
    entity_kind TEXT NOT NULL,
    id_column TEXT NOT NULL,
    state TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    distinct_ids INTEGER NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE native_rows (
    native_row_key TEXT PRIMARY KEY,
    entity_key TEXT NOT NULL,
    entity_kind TEXT NOT NULL,
    native_id TEXT NOT NULL,
    source_table TEXT NOT NULL,
    state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE entities (
    entity_key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    native_id TEXT NOT NULL,
    subtype TEXT,
    lifecycle TEXT NOT NULL,
    state TEXT NOT NULL,
    authority TEXT NOT NULL,
    source_stage INTEGER NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE (kind, native_id)
);

CREATE TABLE entity_properties (
    property_key TEXT PRIMARY KEY,
    entity_key TEXT NOT NULL,
    namespace TEXT NOT NULL,
    property_name TEXT NOT NULL,
    ordinal INTEGER NOT NULL DEFAULT 0,
    value_type TEXT NOT NULL,
    value_text TEXT,
    value_integer INTEGER,
    value_real REAL,
    value_boolean INTEGER,
    value_json TEXT,
    state TEXT NOT NULL,
    authority TEXT NOT NULL,
    source_artifact_key TEXT,
    locator TEXT NOT NULL,
    consumer TEXT,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (entity_key) REFERENCES entities(entity_key)
);

CREATE TABLE relations (
    relation_key TEXT PRIMARY KEY,
    src_entity_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    dst_entity_key TEXT NOT NULL,
    ordinal INTEGER NOT NULL DEFAULT 0,
    cardinality TEXT,
    state TEXT NOT NULL,
    required INTEGER NOT NULL,
    authority TEXT NOT NULL,
    source_artifact_key TEXT,
    locator TEXT NOT NULL,
    loader_or_consumer TEXT,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (src_entity_key) REFERENCES entities(entity_key),
    FOREIGN KEY (dst_entity_key) REFERENCES entities(entity_key)
);

CREATE TABLE consumers (
    consumer_key TEXT PRIMARY KEY,
    scope_key TEXT NOT NULL,
    consumer_kind TEXT NOT NULL,
    name TEXT NOT NULL,
    module TEXT,
    locator TEXT,
    architecture TEXT,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE assets (
    asset_key TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    sha256 TEXT,
    state TEXT NOT NULL,
    source_artifact_key TEXT,
    evidence_json TEXT NOT NULL
);

CREATE TABLE localizations (
    localization_key TEXT PRIMARY KEY,
    locale TEXT NOT NULL,
    text_value TEXT NOT NULL,
    entity_key TEXT,
    state TEXT NOT NULL,
    source_artifact_key TEXT,
    evidence_json TEXT NOT NULL
);

CREATE TABLE wiki_entities (
    wiki_entity_key TEXT PRIMARY KEY,
    entity_key TEXT NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_sha256 TEXT,
    state TEXT NOT NULL,
    comparison_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE wiki_properties (
    wiki_property_key TEXT PRIMARY KEY,
    wiki_entity_key TEXT NOT NULL,
    property_name TEXT NOT NULL,
    value_json TEXT NOT NULL,
    comparison_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE wiki_relations (
    wiki_relation_key TEXT PRIMARY KEY,
    src_wiki_entity_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    dst_kind TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    comparison_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE opaque_regions (
    opaque_key TEXT PRIMARY KEY,
    surface TEXT NOT NULL,
    locator TEXT NOT NULL,
    blocker_code TEXT NOT NULL,
    reason TEXT NOT NULL,
    searched_evidence_json TEXT NOT NULL,
    source_stage INTEGER NOT NULL,
    state TEXT NOT NULL
);

CREATE TABLE coverage (
    coverage_key TEXT PRIMARY KEY,
    scope_key TEXT NOT NULL,
    dimension TEXT NOT NULL,
    state TEXT NOT NULL,
    capability TEXT,
    authority TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE gaps (
    gap_key TEXT PRIMARY KEY,
    entity_key TEXT NOT NULL,
    dimension TEXT NOT NULL,
    state TEXT NOT NULL,
    severity INTEGER NOT NULL,
    blocker_code TEXT NOT NULL,
    reason TEXT NOT NULL,
    required_evidence TEXT NOT NULL,
    provenance TEXT NOT NULL
);

CREATE TABLE blocker_roots (
    blocker_root_key TEXT PRIMARY KEY,
    root_code TEXT NOT NULL,
    category TEXT NOT NULL,
    scope_kind TEXT NOT NULL,
    scope_value TEXT NOT NULL,
    owner_stage INTEGER NOT NULL,
    state TEXT NOT NULL,
    disposition TEXT NOT NULL,
    authority TEXT NOT NULL,
    max_severity INTEGER NOT NULL,
    gap_count INTEGER NOT NULL,
    opaque_count INTEGER NOT NULL,
    coverage_count INTEGER NOT NULL,
    query_count INTEGER NOT NULL,
    consumer_count INTEGER NOT NULL,
    relation_count INTEGER NOT NULL,
    entity_count INTEGER NOT NULL,
    incoming_fanout INTEGER NOT NULL,
    outgoing_fanout INTEGER NOT NULL,
    effort_score INTEGER NOT NULL,
    fanout_score INTEGER NOT NULL,
    priority_score INTEGER NOT NULL,
    required_evidence_json TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE blocker_impacts (
    blocker_impact_key TEXT PRIMARY KEY,
    blocker_root_key TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    entity_key TEXT,
    state TEXT NOT NULL,
    impact_count INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (blocker_root_key) REFERENCES blocker_roots(blocker_root_key)
);

CREATE TABLE blocker_evidence (
    blocker_evidence_key TEXT PRIMARY KEY,
    blocker_root_key TEXT NOT NULL,
    evidence_kind TEXT NOT NULL,
    source_key TEXT NOT NULL,
    source_stage INTEGER,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (blocker_root_key) REFERENCES blocker_roots(blocker_root_key)
);

CREATE TABLE work_queue (
    work_queue_key TEXT PRIMARY KEY,
    rank INTEGER NOT NULL UNIQUE,
    blocker_root_key TEXT NOT NULL UNIQUE,
    lane TEXT NOT NULL,
    owner_stage INTEGER NOT NULL,
    status TEXT NOT NULL,
    priority_score INTEGER NOT NULL,
    effort_score INTEGER NOT NULL,
    fanout_score INTEGER NOT NULL,
    next_action TEXT NOT NULL,
    acceptance_json TEXT NOT NULL,
    rationale_json TEXT NOT NULL,
    FOREIGN KEY (blocker_root_key) REFERENCES blocker_roots(blocker_root_key)
);

CREATE TABLE validation_events (
    validation_key TEXT PRIMARY KEY,
    scope_kind TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE source_records (
    source_record_key TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_pk TEXT NOT NULL,
    record_json TEXT NOT NULL,
    authority TEXT NOT NULL,
    provenance TEXT NOT NULL
);

CREATE TABLE native_code_evidence_links (
    evidence_link_key TEXT PRIMARY KEY,
    consumer_key TEXT NOT NULL,
    function_key TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    state TEXT NOT NULL,
    source_stage INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (consumer_key) REFERENCES consumers(consumer_key)
);

CREATE TABLE native_semantic_roots (
    root_key TEXT PRIMARY KEY,
    root_kind TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    backend_priority INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE native_semantic_function_states (
    function_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    module_name TEXT NOT NULL,
    architecture TEXT NOT NULL,
    domain TEXT NOT NULL,
    category TEXT NOT NULL,
    impact_score INTEGER NOT NULL,
    uncertainty_score INTEGER NOT NULL,
    impact_tier TEXT NOT NULL,
    primary_root_key TEXT,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (primary_root_key) REFERENCES native_semantic_roots(root_key)
);

CREATE TABLE native_semantic_links (
    link_key TEXT PRIMARY KEY,
    root_key TEXT NOT NULL,
    function_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    direction TEXT NOT NULL,
    depth INTEGER NOT NULL,
    impact_score INTEGER NOT NULL,
    state TEXT NOT NULL,
    FOREIGN KEY (root_key) REFERENCES native_semantic_roots(root_key)
);

CREATE TABLE native_semantic_opaque_states (
    region_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    start_rva INTEGER NOT NULL,
    end_rva INTEGER NOT NULL,
    classification TEXT NOT NULL,
    impact_score INTEGER NOT NULL,
    primary_function_key TEXT,
    primary_root_key TEXT,
    state TEXT NOT NULL,
    FOREIGN KEY (primary_root_key) REFERENCES native_semantic_roots(root_key)
);

CREATE TABLE native_semantic_work_queue (
    queue_key TEXT PRIMARY KEY,
    rank INTEGER NOT NULL UNIQUE,
    wave INTEGER NOT NULL,
    root_key TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    impact_tier TEXT NOT NULL,
    impact_score INTEGER NOT NULL,
    uncertainty_score INTEGER NOT NULL,
    closure_status TEXT NOT NULL,
    next_action TEXT NOT NULL,
    FOREIGN KEY (root_key) REFERENCES native_semantic_roots(root_key)
);

CREATE INDEX idx_artifacts_role ON artifacts(role);
CREATE INDEX idx_surfaces_kind ON surfaces(source_kind, extension);
CREATE INDEX idx_queries_table ON query_specs(table_name);
CREATE INDEX idx_native_rows_entity ON native_rows(entity_key);
CREATE INDEX idx_entities_kind_id ON entities(kind, native_id);
CREATE INDEX idx_properties_entity ON entity_properties(entity_key, namespace, property_name);
CREATE INDEX idx_relations_src ON relations(src_entity_key, relation);
CREATE INDEX idx_relations_dst ON relations(dst_entity_key, relation);
CREATE INDEX idx_relations_state ON relations(state);
CREATE INDEX idx_coverage_scope ON coverage(scope_key, dimension);
CREATE INDEX idx_gaps_entity ON gaps(entity_key, severity);
CREATE INDEX idx_blocker_roots_priority
    ON blocker_roots(disposition, priority_score DESC, blocker_root_key);
CREATE INDEX idx_blocker_impacts_root
    ON blocker_impacts(blocker_root_key, subject_kind, subject_key);
CREATE INDEX idx_blocker_impacts_entity
    ON blocker_impacts(entity_key, blocker_root_key);
CREATE INDEX idx_blocker_evidence_root
    ON blocker_evidence(blocker_root_key, evidence_kind);
CREATE INDEX idx_work_queue_lane
    ON work_queue(lane, rank);
CREATE INDEX idx_source_records_table ON source_records(source_table);
CREATE INDEX idx_native_code_evidence_consumer
    ON native_code_evidence_links(consumer_key);
CREATE INDEX idx_native_code_evidence_function
    ON native_code_evidence_links(function_key);
CREATE INDEX idx_native_code_evidence_scope
    ON native_code_evidence_links(scope_key, relation);
CREATE INDEX idx_native_semantic_root_domain
    ON native_semantic_roots(domain, backend_priority DESC);
CREATE INDEX idx_native_semantic_function_category
    ON native_semantic_function_states(category, impact_tier);
CREATE INDEX idx_native_semantic_function_domain
    ON native_semantic_function_states(domain, impact_score DESC);
CREATE INDEX idx_native_semantic_links_function
    ON native_semantic_links(function_key, impact_score DESC);
CREATE INDEX idx_native_semantic_opaque_classification
    ON native_semantic_opaque_states(classification, impact_score DESC);
CREATE INDEX idx_native_semantic_queue_wave
    ON native_semantic_work_queue(wave, rank);
"""


def create_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA page_size = 4096")
    connection.execute("PRAGMA journal_mode = DELETE")
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA application_id = 0x41413846")
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.executescript(SCHEMA_SQL)
    return connection


def open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def set_metadata(connection: sqlite3.Connection, values: dict[str, object]) -> None:
    connection.executemany(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        sorted((str(key), str(value)) for key, value in values.items()),
    )


def table_count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
