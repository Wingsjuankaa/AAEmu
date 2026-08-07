from __future__ import annotations

import sqlite3


NATIVE_CODE_SCHEMA_VERSION = 2

NATIVE_CODE_STATES = {
    "confirmed",
    "corroborated",
    "candidate",
    "ambiguous",
    "opaque",
    "timeout",
    "failed",
    "unsupported",
    "not_scheduled",
}

NATIVE_CODE_SQL = """
CREATE TABLE code_binaries (
    binary_key TEXT PRIMARY KEY,
    module_name TEXT NOT NULL,
    architecture TEXT NOT NULL,
    classification TEXT NOT NULL,
    source_path TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    machine INTEGER NOT NULL,
    image_base INTEGER NOT NULL,
    entry_rva INTEGER NOT NULL,
    image_size INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    linker_version TEXT NOT NULL,
    signed INTEGER NOT NULL,
    pdb_path TEXT,
    pdb_guid TEXT,
    pdb_age INTEGER,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE (sha256, architecture)
);

CREATE TABLE code_sections (
    section_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    name TEXT NOT NULL,
    rva INTEGER NOT NULL,
    virtual_size INTEGER NOT NULL,
    raw_offset INTEGER NOT NULL,
    raw_size INTEGER NOT NULL,
    characteristics INTEGER NOT NULL,
    executable INTEGER NOT NULL,
    entropy REAL NOT NULL,
    sha256 TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key)
);

CREATE TABLE code_regions (
    region_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    section_key TEXT NOT NULL,
    function_key TEXT,
    start_rva INTEGER NOT NULL,
    end_rva INTEGER NOT NULL,
    region_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key),
    FOREIGN KEY (section_key) REFERENCES code_sections(section_key),
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_imports (
    import_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    library_name TEXT NOT NULL,
    symbol_name TEXT,
    ordinal INTEGER,
    iat_rva INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key)
);

CREATE TABLE code_exports (
    export_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    symbol_name TEXT,
    ordinal INTEGER NOT NULL,
    rva INTEGER NOT NULL,
    forwarded_to TEXT,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key)
);

CREATE TABLE code_functions (
    function_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    entry_rva INTEGER NOT NULL,
    end_rva INTEGER,
    size INTEGER,
    byte_sha256 TEXT,
    mnemonic_sha256 TEXT,
    discovery_engine TEXT NOT NULL,
    function_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE (binary_key, entry_rva),
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key)
);

CREATE TABLE code_names (
    name_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    name TEXT NOT NULL,
    namespace TEXT,
    source_kind TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    primary_name INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_instructions (
    instruction_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    rva INTEGER NOT NULL,
    mnemonic TEXT NOT NULL,
    instruction_text TEXT NOT NULL,
    bytes_hex TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(function_key, rva),
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_basic_blocks (
    block_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    start_rva INTEGER NOT NULL,
    end_rva INTEGER NOT NULL,
    instruction_count INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_calls (
    call_key TEXT PRIMARY KEY,
    caller_function_key TEXT NOT NULL,
    callee_function_key TEXT,
    callsite_rva INTEGER NOT NULL,
    target_rva INTEGER,
    target_name TEXT,
    call_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (caller_function_key) REFERENCES code_functions(function_key),
    FOREIGN KEY (callee_function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_data_references (
    reference_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    from_rva INTEGER NOT NULL,
    to_rva INTEGER NOT NULL,
    reference_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_strings (
    string_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    rva INTEGER NOT NULL,
    encoding TEXT NOT NULL,
    value TEXT NOT NULL,
    value_sha256 TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE (binary_key, rva, encoding),
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key)
);

CREATE TABLE code_function_strings (
    function_key TEXT NOT NULL,
    string_key TEXT NOT NULL,
    reference_rva INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY (function_key, string_key, reference_rva),
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key),
    FOREIGN KEY (string_key) REFERENCES code_strings(string_key)
);

CREATE TABLE code_types (
    type_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    type_name TEXT NOT NULL,
    type_kind TEXT NOT NULL,
    size INTEGER,
    source_kind TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key)
);

CREATE TABLE code_type_fields (
    field_key TEXT PRIMARY KEY,
    type_key TEXT NOT NULL,
    offset INTEGER NOT NULL,
    field_name TEXT,
    field_type TEXT,
    size INTEGER,
    source_locator TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (type_key) REFERENCES code_types(type_key)
);

CREATE TABLE code_vtables (
    vtable_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    type_key TEXT,
    rva INTEGER NOT NULL,
    slot_count INTEGER NOT NULL,
    source_locator TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key),
    FOREIGN KEY (type_key) REFERENCES code_types(type_key)
);

CREATE TABLE code_vtable_slots (
    slot_key TEXT PRIMARY KEY,
    vtable_key TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    target_function_key TEXT,
    target_rva INTEGER,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (vtable_key) REFERENCES code_vtables(vtable_key),
    FOREIGN KEY (target_function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_engine_runs (
    run_key TEXT PRIMARY KEY,
    binary_key TEXT NOT NULL,
    engine_id TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    engine_sha256 TEXT,
    scope TEXT NOT NULL,
    input_manifest_sha256 TEXT NOT NULL,
    output_path TEXT NOT NULL,
    output_sha256 TEXT,
    timeout_seconds INTEGER NOT NULL,
    exit_code INTEGER,
    status TEXT NOT NULL,
    error TEXT,
    evidence_json TEXT NOT NULL,
    UNIQUE (binary_key, engine_id, engine_version, scope),
    FOREIGN KEY (binary_key) REFERENCES code_binaries(binary_key)
);

CREATE TABLE code_decompilations (
    decompilation_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    run_key TEXT NOT NULL,
    engine_id TEXT NOT NULL,
    prototype TEXT,
    calling_convention TEXT,
    pseudocode TEXT,
    pseudocode_sha256 TEXT,
    duration_ms INTEGER,
    status TEXT NOT NULL,
    error TEXT,
    evidence_json TEXT NOT NULL,
    UNIQUE (function_key, run_key),
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key),
    FOREIGN KEY (run_key) REFERENCES code_engine_runs(run_key)
);

CREATE TABLE code_equivalences (
    equivalence_key TEXT PRIMARY KEY,
    left_function_key TEXT NOT NULL,
    right_function_key TEXT NOT NULL,
    method TEXT NOT NULL,
    rank_score REAL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (left_function_key) REFERENCES code_functions(function_key),
    FOREIGN KEY (right_function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_evidence_links (
    evidence_link_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_dynamic_runs (
    dynamic_run_key TEXT PRIMARY KEY,
    scenario TEXT NOT NULL,
    tool_id TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    trace_path TEXT NOT NULL,
    trace_sha256 TEXT NOT NULL,
    network_scope TEXT NOT NULL,
    anticheat_state TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE code_dynamic_coverage (
    coverage_key TEXT PRIMARY KEY,
    dynamic_run_key TEXT NOT NULL,
    function_key TEXT NOT NULL,
    hit_count INTEGER NOT NULL,
    first_observed_rva INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (dynamic_run_key) REFERENCES code_dynamic_runs(dynamic_run_key),
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_review_queue (
    review_key TEXT PRIMARY KEY,
    function_key TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    priority INTEGER NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key)
);

CREATE TABLE code_review_groups (
    review_group_key TEXT PRIMARY KEY,
    engine_id TEXT NOT NULL,
    run_key TEXT,
    reason_code TEXT NOT NULL,
    affected_functions INTEGER NOT NULL,
    priority INTEGER NOT NULL,
    state TEXT NOT NULL,
    error_signature TEXT,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (run_key) REFERENCES code_engine_runs(run_key)
);

CREATE TABLE code_review_decisions (
    decision_key TEXT PRIMARY KEY,
    decision_kind TEXT NOT NULL,
    function_key TEXT,
    related_function_key TEXT,
    state TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY (function_key) REFERENCES code_functions(function_key),
    FOREIGN KEY (related_function_key) REFERENCES code_functions(function_key)
);

CREATE VIRTUAL TABLE code_search USING fts5(
    function_key UNINDEXED,
    module_name,
    architecture,
    primary_name,
    strings,
    instructions,
    pseudocode,
    tokenize='unicode61'
);

CREATE INDEX idx_code_binaries_module
    ON code_binaries(module_name, architecture);
CREATE INDEX idx_code_sections_binary
    ON code_sections(binary_key, rva);
CREATE INDEX idx_code_regions_binary
    ON code_regions(binary_key, start_rva, end_rva);
CREATE INDEX idx_code_imports_binary
    ON code_imports(binary_key, library_name);
CREATE INDEX idx_code_exports_binary
    ON code_exports(binary_key, rva);
CREATE INDEX idx_code_functions_binary
    ON code_functions(binary_key, entry_rva);
CREATE INDEX idx_code_functions_rva
    ON code_functions(entry_rva, binary_key);
CREATE INDEX idx_code_names_function
    ON code_names(function_key, primary_name DESC);
CREATE INDEX idx_code_instructions_function
    ON code_instructions(function_key, rva);
CREATE INDEX idx_code_calls_caller
    ON code_calls(caller_function_key, callsite_rva);
CREATE INDEX idx_code_calls_callee
    ON code_calls(callee_function_key);
CREATE INDEX idx_code_refs_function
    ON code_data_references(function_key, from_rva);
CREATE INDEX idx_code_function_strings_function
    ON code_function_strings(function_key);
CREATE INDEX idx_code_decompilations_function
    ON code_decompilations(function_key, engine_id);
CREATE INDEX idx_code_vtables_rva
    ON code_vtables(rva, binary_key);
CREATE INDEX idx_code_vtable_slots_target
    ON code_vtable_slots(target_function_key, vtable_key);
CREATE INDEX idx_code_equivalences_left
    ON code_equivalences(left_function_key, state);
CREATE INDEX idx_code_equivalences_right
    ON code_equivalences(right_function_key, state);
CREATE INDEX idx_code_evidence_scope
    ON code_evidence_links(scope_key, relation);
CREATE INDEX idx_code_evidence_function
    ON code_evidence_links(function_key);
CREATE INDEX idx_code_review_priority
    ON code_review_queue(state, priority DESC);
CREATE INDEX idx_code_review_groups_priority
    ON code_review_groups(state, priority DESC);
CREATE INDEX idx_code_review_decisions_function
    ON code_review_decisions(function_key, related_function_key, decision_kind);
"""


def create_native_code_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(NATIVE_CODE_SQL)
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        ("native_code_schema_version", str(NATIVE_CODE_SCHEMA_VERSION)),
    )
