from __future__ import annotations

import sqlite3


NATIVE_SEMANTIC_SCHEMA_VERSION = 1

FUNCTION_CATEGORIES = {
    "critical_root",
    "critical_reachable",
    "support_reachable",
    "candidate_signal",
    "unlinked",
    "external_or_not_backend_relevant",
}

OPAQUE_CLASSIFICATIONS = {
    "critical_blocker",
    "reachable_context",
    "unlinked_no_demonstrated_impact",
}

CLOSURE_STATES = {
    "pending_review",
    "understood",
    "blocked_by_indirect_dispatch",
    "blocked_by_opaque_region",
    "blocked_by_missing_native_data",
    "external_dependency",
    "not_backend_relevant",
}


NATIVE_SEMANTIC_SQL = """
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE semantic_roots (
    root_key TEXT PRIMARY KEY,
    root_kind TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    backend_priority INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE semantic_root_functions (
    link_key TEXT PRIMARY KEY,
    root_key TEXT NOT NULL,
    function_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    direction TEXT NOT NULL,
    depth INTEGER NOT NULL,
    impact_score INTEGER NOT NULL,
    state TEXT NOT NULL,
    path_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (root_key) REFERENCES semantic_roots(root_key)
);

CREATE TABLE semantic_function_classifications (
    function_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    module_name TEXT NOT NULL,
    architecture TEXT NOT NULL,
    domain TEXT NOT NULL,
    category TEXT NOT NULL,
    impact_score INTEGER NOT NULL,
    uncertainty_score INTEGER NOT NULL,
    impact_tier TEXT NOT NULL,
    fanin INTEGER NOT NULL,
    fanout INTEGER NOT NULL,
    primary_root_key TEXT,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (primary_root_key) REFERENCES semantic_roots(root_key)
);

CREATE TABLE semantic_function_reasons (
    reason_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    root_key TEXT,
    reason_code TEXT NOT NULL,
    score_axis TEXT NOT NULL,
    score_delta INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (root_key) REFERENCES semantic_roots(root_key)
);

CREATE TABLE semantic_closures (
    root_key TEXT PRIMARY KEY,
    outbound_functions INTEGER NOT NULL,
    inbound_functions INTEGER NOT NULL,
    total_functions INTEGER NOT NULL,
    max_outbound_depth INTEGER NOT NULL,
    max_inbound_depth INTEGER NOT NULL,
    truncated INTEGER NOT NULL,
    truncation_reason TEXT,
    closure_status TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (root_key) REFERENCES semantic_roots(root_key)
);

CREATE TABLE semantic_consumer_classification (
    consumer_key TEXT PRIMARY KEY,
    scope_key TEXT NOT NULL,
    locator TEXT,
    architecture TEXT,
    match_count INTEGER NOT NULL,
    classification TEXT NOT NULL,
    state TEXT NOT NULL,
    function_keys_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE semantic_query_classification (
    query_key TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    normalized_sql_sha256 TEXT,
    match_count INTEGER NOT NULL,
    classification TEXT NOT NULL,
    state TEXT NOT NULL,
    function_keys_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE semantic_indirect_sites (
    site_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    callsite_rva INTEGER NOT NULL,
    instruction_text TEXT NOT NULL,
    pattern TEXT NOT NULL,
    target_hint TEXT,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE semantic_opaque_regions (
    region_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    start_rva INTEGER NOT NULL,
    end_rva INTEGER NOT NULL,
    classification TEXT NOT NULL,
    impact_score INTEGER NOT NULL,
    primary_function_key TEXT,
    primary_root_key TEXT,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (primary_root_key) REFERENCES semantic_roots(root_key)
);

CREATE TABLE semantic_work_queue (
    queue_key TEXT PRIMARY KEY,
    rank INTEGER NOT NULL UNIQUE,
    wave INTEGER NOT NULL,
    root_key TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    impact_tier TEXT NOT NULL,
    impact_score INTEGER NOT NULL,
    backend_priority INTEGER NOT NULL,
    uncertainty_score INTEGER NOT NULL,
    closure_size INTEGER NOT NULL,
    closure_status TEXT NOT NULL,
    next_action TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (root_key) REFERENCES semantic_roots(root_key)
);

CREATE TABLE validation_events (
    validation_key TEXT PRIMARY KEY,
    check_name TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    expected_json TEXT NOT NULL,
    actual_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE INDEX idx_semantic_roots_domain ON semantic_roots(domain, backend_priority);
CREATE INDEX idx_semantic_root_functions_function ON semantic_root_functions(function_key);
CREATE INDEX idx_semantic_root_functions_root_depth ON semantic_root_functions(root_key, direction, depth);
CREATE INDEX idx_semantic_function_category ON semantic_function_classifications(category, impact_tier);
CREATE INDEX idx_semantic_function_domain ON semantic_function_classifications(domain, impact_score DESC);
CREATE INDEX idx_semantic_function_uncertainty ON semantic_function_classifications(uncertainty_score DESC);
CREATE INDEX idx_semantic_reasons_function ON semantic_function_reasons(function_key, reason_code);
CREATE INDEX idx_semantic_indirect_function ON semantic_indirect_sites(function_key);
CREATE INDEX idx_semantic_opaque_classification ON semantic_opaque_regions(classification, impact_score DESC);
CREATE INDEX idx_semantic_queue_wave ON semantic_work_queue(wave, rank);
"""


def create_native_semantic_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(NATIVE_SEMANTIC_SQL)
    connection.execute(f"PRAGMA user_version = {NATIVE_SEMANTIC_SCHEMA_VERSION}")
