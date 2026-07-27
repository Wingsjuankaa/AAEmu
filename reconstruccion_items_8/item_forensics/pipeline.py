from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from . import CLIENT_BUILD, SCHEMA_VERSION, TOOL_NAME, TOOL_VERSION
from .cached_result import (
    CachedResultError,
    CachedResultReader,
    recover_calibrated_string_cache,
)
from .config import ForensicsConfig
from .db import create_database, finalize_database, set_metadata
from .families import (
    FAMILIES,
    X2GAME_ITEM_IMPL_EVIDENCE,
    X2GAME_ITEM_IMPL_NAMES,
    Family,
    family_for_impl,
    family_name,
)
from .native_catalogs import rebuild_native_catalogs
from .native_closure import generate_native_closure_audit
from .registry import (
    QuerySpec,
    attach_sql,
    columns_from_select,
    load_item_sql,
    load_legacy_specs,
    load_manifest_ranges,
    load_static_layout_registry,
    merge_ranges,
    registry_digest,
    serialize_spec,
    static_query_specs,
)
from .surfaces import scan_reviewed_surfaces
from .util import (
    canonical_json,
    columns,
    open_sqlite_read_only,
    quoted,
    sha256_bytes,
    sha256_file,
    table_names,
    write_text_atomic,
)


ITEM_REFERENCE_KIND = {
    "use_skill_id": "skill",
    "skill_id": "skill",
    "trigger_skill_id": "skill",
    "buff_id": "buff",
    "recharge_buff_id": "buff",
    "quest_id": "quest",
    "loot_quest_id": "quest",
    "quest_context_id": "quest",
    "npc_id": "npc",
    "doodad_id": "doodad",
    "craft_id": "craft",
    "item_id": "item",
    "source_item_id": "item",
    "target_item_id": "item",
    "reactive_item_id": "item",
    "reagent_item_id": "item",
    "result_item_id": "item",
}

REFERENCE_TABLES = {
    "skill": ("skills", "id"),
    "buff": ("buffs", "id"),
    "quest": ("quest_contexts", "id"),
    "npc": ("npcs", "id"),
    "doodad": ("doodad_templates", "id"),
    "craft": ("crafts", "id"),
    "item": ("items", "id"),
}

SOURCE_SUFFIXES = (
    "Manager.cs",
    "Service.cs",
    "Services.cs",
    "Packet.cs",
    "Template.cs",
)
ASCII_RUN = re.compile(rb"[\x20-\x7e]{8,}")
ITEM_DESC_TOKEN = re.compile(
    r"(?:\.\?A[UV])?([A-Za-z0-9_:$?@<>]*Item[A-Za-z0-9_]*Desc[A-Za-z0-9_:$?@<>]*)"
)


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _artifact(
    connection: sqlite3.Connection,
    role: str,
    path: Path,
    provenance: str,
    *,
    known_sha256: str | None = None,
    allow_missing: bool = False,
) -> int | None:
    if not path.is_file():
        if allow_missing:
            return None
        raise FileNotFoundError(path)
    digest = known_sha256 or sha256_file(path)
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO artifacts(role,path,bytes,sha256,provenance)
        VALUES (?,?,?,?,?)
        """,
        (role, path.resolve().as_posix(), path.stat().st_size, digest, provenance),
    )
    if cursor.lastrowid:
        return int(cursor.lastrowid)
    row = connection.execute(
        "SELECT artifact_id FROM artifacts WHERE role=? AND path=?",
        (role, path.resolve().as_posix()),
    ).fetchone()
    return int(row[0]) if row else None


def register_artifacts(
    connection: sqlite3.Connection,
    config: ForensicsConfig,
) -> dict[str, int]:
    result: dict[str, int] = {}
    for role, path, provenance in (
        ("client_compact", config.client_compact, "client_compact_8"),
        ("runtime_compact", config.runtime, "server_derived"),
    ):
        artifact_id = _artifact(connection, role, path, provenance)
        assert artifact_id is not None
        result[role] = artifact_id
    for path in sorted(config.streams_root.glob("game*"), key=lambda value: value.name):
        if not path.is_file():
            continue
        artifact_id = _artifact(
            connection,
            f"cached_stream:{path.name}",
            path,
            "game11_native" if path.name == "game11" else "native_client_cache",
        )
        assert artifact_id is not None
        result[f"stream:{path.name}"] = artifact_id
    for path in sorted(config.x2game, key=lambda value: value.as_posix().lower()):
        artifact_id = _artifact(
            connection,
            f"x2game:{path.parent.name}",
            path,
            "x2game_confirmed",
            allow_missing=True,
        )
        if artifact_id is not None:
            result[f"x2game:{path.parent.name}"] = artifact_id
    for role, path, provenance in (
        ("sql_manifest", config.sql_manifest, "x2game_confirmed"),
        ("surface_manifest", config.surface_manifest, "native_client_inventory"),
        ("gamepak_index", config.gamepak_index, "game_pak"),
    ):
        if path is None:
            continue
        artifact_id = _artifact(
            connection,
            role,
            path,
            provenance,
            allow_missing=True,
        )
        if artifact_id is not None:
            result[role] = artifact_id
    for role, path, provenance in (
        (
            "native_dependency_registry",
            Path(__file__).resolve().parent
            / "config"
            / "kakao-r558734-native-dependencies.json",
            "game11_native+x2game_confirmed",
        ),
        (
            "native_dependency_ghidra_tasks",
            Path(__file__).resolve().parent
            / "config"
            / "ghidra-native-dependency-tasks.tsv",
            "x2game_confirmed",
        ),
        (
            "native_dependency_ghidra_loaders",
            config.output_dir / "ghidra-native-dependency-loaders.txt",
            "x2game_confirmed",
        ),
        (
            "native_dependency_ghidra_layouts",
            config.output_dir / "ghidra-native-dependency-layouts.json",
            "x2game_confirmed",
        ),
        (
            "craft_sequence_ghidra_tasks",
            Path(__file__).resolve().parent
            / "config"
            / "ghidra-crafts-sequence-tasks.tsv",
            "x2game_confirmed",
        ),
        (
            "craft_sequence_ghidra_loaders_64",
            config.output_dir / "ghidra-crafts-sequence-loaders-64.txt",
            "x2game_confirmed",
        ),
        (
            "craft_sequence_ghidra_layouts_64",
            config.output_dir / "ghidra-crafts-sequence-layouts-64.json",
            "x2game_confirmed",
        ),
        (
            "craft_sequence_ghidra_loaders_32",
            config.output_dir / "ghidra-crafts-sequence-loaders-32.txt",
            "x2game_confirmed",
        ),
        (
            "craft_sequence_ghidra_layouts_32",
            config.output_dir / "ghidra-crafts-sequence-layouts-32.json",
            "x2game_confirmed",
        ),
        (
            "craft_sequence_function_context_64",
            config.output_dir / "ghidra-crafts-function-context-64.txt",
            "x2game_confirmed",
        ),
        (
            "craft_sequence_neighbor_strings_64",
            config.output_dir / "ghidra-crafts-neighbor-strings-64.txt",
            "x2game_confirmed",
        ),
        (
            "consumer_closure_ghidra_tasks",
            Path(__file__).resolve().parent
            / "config"
            / "ghidra-consumer-closure-tasks.tsv",
            "x2game_confirmed",
        ),
        (
            "consumer_closure_ghidra_loaders_64",
            config.output_dir / "ghidra-consumer-closure-loaders-64.txt",
            "x2game_confirmed",
        ),
        (
            "consumer_closure_ghidra_layouts_64",
            config.output_dir / "ghidra-consumer-closure-layouts-64.json",
            "x2game_confirmed",
        ),
        (
            "consumer_closure_ghidra_loaders_32",
            config.output_dir / "ghidra-consumer-closure-loaders-32.txt",
            "x2game_confirmed",
        ),
        (
            "consumer_closure_ghidra_layouts_32",
            config.output_dir / "ghidra-consumer-closure-layouts-32.json",
            "x2game_confirmed",
        ),
        (
            "all_sql_ghidra_tasks",
            config.output_dir / "ghidra-all-sql-tasks.tsv",
            "x2game_confirmed",
        ),
        (
            "all_sql_ghidra_loaders_64",
            config.output_dir / "ghidra-all-sql-loaders-64.txt",
            "x2game_confirmed",
        ),
        (
            "master_sql_call_sequence",
            config.output_dir / "ghidra-master-sql-call-sequence.json",
            "x2game_confirmed",
        ),
    ):
        artifact_id = _artifact(
            connection,
            role,
            path,
            provenance,
            allow_missing=True,
        )
        if artifact_id is not None:
            result[role] = artifact_id
    _register_gamepak_from_surface_manifest(connection, config.surface_manifest)
    return result


def _register_gamepak_from_surface_manifest(
    connection: sqlite3.Connection,
    manifest: Path | None,
) -> None:
    if manifest is None or not manifest.is_file():
        return
    try:
        document = json.loads(manifest.read_text(encoding="utf-8-sig"))
        gamepak = document.get("gamepak", {})
        path = Path(str(gamepak["path"]))
        bytes_count = int(gamepak.get("bytes", 0))
        digest = gamepak.get("sha256")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return
    connection.execute(
        """
        INSERT OR IGNORE INTO artifacts(role,path,bytes,sha256,provenance)
        VALUES ('game_pak',?,?,?,'game_pak')
        """,
        (path.as_posix(), bytes_count, digest),
    )


def scan_client(
    connection: sqlite3.Connection,
    config: ForensicsConfig,
) -> dict[str, Any]:
    client = open_sqlite_read_only(config.client_compact)
    try:
        available = table_names(client)
        if "items" not in available:
            raise RuntimeError("Client compact has no items table")
        item_columns = columns(client, "items")
        select_columns = [
            name
            for name in (
                "id",
                "impl_id",
                "name",
                "description",
                "category_id",
                "level",
                "use_skill_id",
                "buff_id",
                "craft_id",
                "loot_quest_id",
            )
            if name in item_columns
        ]
        rows = list(
            client.execute(
                "SELECT "
                + ",".join(quoted(name) for name in item_columns)
                + " FROM items ORDER BY id"
            )
        )
        positive_rows = [row for row in rows if int(row["id"]) > 0]
        anomalous_rows = [row for row in rows if int(row["id"]) <= 0]
        inserts = []
        for row in positive_rows:
            value = _row_dict(row)
            inserts.append(
                (
                    int(value["id"]),
                    int(value.get("impl_id") or 0),
                    value.get("name"),
                    value.get("description"),
                    value.get("category_id"),
                    value.get("level"),
                    value.get("use_skill_id"),
                    value.get("buff_id"),
                    value.get("craft_id"),
                    value.get("loot_quest_id"),
                    canonical_json(value),
                    "client_compact_8",
                )
            )
        connection.executemany(
            """
            INSERT INTO items(
                item_id,impl_id,name,description,category_id,level,use_skill_id,
                buff_id,craft_id,loot_quest_id,client_row_json,client_provenance
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            inserts,
        )
        for row in anomalous_rows:
            value = _row_dict(row)
            connection.execute(
                """
                INSERT INTO opaque_regions(
                    surface,locator,blocker_code,reason,searched_evidence_json
                ) VALUES (?,?,?,?,?)
                """,
                (
                    "client_compact.items",
                    str(value.get("id")),
                    "signed_or_nonpositive_item_id",
                    "The row is retained as an anomaly and is not coerced to uint.",
                    canonical_json(value),
                ),
            )
        impl_counts = Counter(int(row["impl_id"]) for row in positive_rows)
        set_metadata(
            connection,
            {
                "client_item_columns": canonical_json(select_columns),
                "client_item_positive_rows": len(positive_rows),
                "client_item_anomalies": len(anomalous_rows),
                "client_impl_counts": canonical_json(dict(sorted(impl_counts.items()))),
            },
        )
        connection.execute(
            """
            INSERT INTO validation_events(
                scope_kind,scope_id,check_name,status,evidence_json
            ) VALUES ('client','items','positive_item_inventory','ok',?)
            """,
            (
                canonical_json(
                    {
                        "positive_rows": len(positive_rows),
                        "nonpositive_rows": len(anomalous_rows),
                        "input_sha256": sha256_file(config.client_compact),
                    }
                ),
            ),
        )
        return {
            "positive_items": len(positive_rows),
            "nonpositive_anomalies": len(anomalous_rows),
            "impl_counts": dict(sorted(impl_counts.items())),
        }
    finally:
        client.close()


def _query_spec_status(spec: QuerySpec) -> str:
    if not spec.columns or not spec.layout:
        return "layout_missing"
    if len(spec.columns) != len(spec.layout):
        return "invalid_layout"
    if spec.start is None and spec.anchor_id is None:
        return "offset_and_anchor_missing"
    return "registered"


def _load_client_localizations(
    config: ForensicsConfig,
    table_names_to_load: set[str],
) -> dict[tuple[str, str, int], str]:
    client = open_sqlite_read_only(config.client_compact)
    try:
        if "localized_texts" not in table_names(client):
            return {}
        placeholders = ",".join("?" for _ in table_names_to_load)
        if not placeholders:
            return {}
        rows = client.execute(
            f"""
            SELECT tbl_name,tbl_column_name,idx,text
            FROM localized_texts
            WHERE locale='en_us' AND lower(tbl_name) IN ({placeholders})
            ORDER BY lower(tbl_name),lower(tbl_column_name),idx
            """,
            tuple(sorted(table_names_to_load)),
        )
        return {
            (
                str(row["tbl_name"]).lower(),
                str(row["tbl_column_name"]).lower(),
                int(row["idx"]),
            ): str(row["text"])
            for row in rows
            if row["text"] is not None
        }
    finally:
        client.close()


def _resolve_localized_consumers(
    rows: tuple[tuple[Any, ...], ...],
    spec: QuerySpec,
    localizations: dict[tuple[str, str, int], str],
) -> tuple[tuple[tuple[Any, ...], ...], tuple[int, ...], dict[str, Any]]:
    remaining: set[int] = set()
    localized_references: set[int] = set()
    localized_occurrences = 0
    resolved_rows: list[tuple[Any, ...]] = []
    key_index = (
        spec.columns.index("id")
        if "id" in spec.columns
        else spec.columns.index("item_id")
        if "item_id" in spec.columns
        else None
    )
    for row in rows:
        values = list(row)
        row_key = int(values[key_index]) if key_index is not None else None
        for index, value in enumerate(values):
            if (
                not isinstance(value, str)
                or not value.startswith("<ref:")
                or not value.endswith(">")
            ):
                continue
            reference = int(value[5:-1])
            localized = (
                localizations.get(
                    (
                        spec.table_name.lower(),
                        spec.columns[index].lower(),
                        row_key,
                    )
                )
                if row_key is not None
                else None
            )
            if localized is None:
                remaining.add(reference)
                continue
            values[index] = localized
            localized_references.add(reference)
            localized_occurrences += 1
        resolved_rows.append(tuple(values))
    return (
        tuple(resolved_rows),
        tuple(sorted(remaining)),
        {
            "localized_occurrences": localized_occurrences,
            "localized_references": sorted(localized_references),
            "source": "client_compact_8.localized_texts",
            "consumer": spec.loader_consumer or (spec.evidence or {}).get("loader"),
        },
    )


def _resolve_calibrated_global_strings(
    payload: bytes,
    rows: tuple[tuple[Any, ...], ...],
    unresolved: tuple[int, ...],
    spec: QuerySpec,
    gamepak_index: Path | None,
) -> tuple[tuple[tuple[Any, ...], ...], tuple[int, ...], dict[str, Any]]:
    calibrations = (spec.evidence or {}).get("string_cache_calibrations")
    if not unresolved or not calibrations:
        return rows, unresolved, {
            "resolved_occurrences": 0,
            "resolved_references": [],
        }
    recovery = recover_calibrated_string_cache(
        payload,
        unresolved,
        calibrations,
    )
    resolved_occurrences = 0
    recovered_paths: set[str] = set()
    resolved_rows: list[tuple[Any, ...]] = []
    for row in rows:
        values = list(row)
        for index, value in enumerate(values):
            if (
                not isinstance(value, str)
                or not value.startswith("<ref:")
                or not value.endswith(">")
            ):
                continue
            reference = int(value[5:-1])
            recovered = recovery.values.get(reference)
            if recovered is None:
                continue
            values[index] = recovered
            resolved_occurrences += 1
            if spec.columns[index].lower() == "path" and recovered:
                recovered_paths.add(recovered)
        resolved_rows.append(tuple(values))
    remaining = tuple(
        sorted(set(unresolved).difference(recovery.values))
    )
    return (
        tuple(resolved_rows),
        remaining,
        {
            "resolved_occurrences": resolved_occurrences,
            "resolved_references": sorted(recovery.values),
            "value_digest": sha256_bytes(
                canonical_json(recovery.values).encode("utf-8")
            ),
            "candidate_index_delta": recovery.candidate_index_delta,
            "calibrations": list(recovery.calibration_evidence),
            "authority": "native cached-string signatures bracketed by "
            "confirmed cached-result reference bases",
            "gamepak_corroboration": _corroborate_gamepak_paths(
                recovered_paths,
                gamepak_index,
            ),
        },
    )


def _corroborate_gamepak_paths(
    paths: set[str],
    gamepak_index: Path | None,
) -> dict[str, Any]:
    if not paths or gamepak_index is None or not gamepak_index.is_file():
        return {
            "status": "not_available",
            "recovered_paths": len(paths),
        }
    expected = {
        "game/" + value.replace("\\", "/").lstrip("/").lower()
        for value in paths
    }
    found: set[str] = set()
    with gamepak_index.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            name = str(row.get("name") or "").lower()
            if name in expected:
                found.add(name)
    return {
        "status": "corroborated",
        "index": gamepak_index.resolve().as_posix(),
        "index_sha256": sha256_file(gamepak_index),
        "recovered_paths": len(expected),
        "exact_paths": len(found),
        "missing_paths": sorted(expected.difference(found)),
    }


def _classify_scoped_string_anomalies(
    rows: tuple[tuple[Any, ...], ...],
    unresolved: tuple[int, ...],
    spec: QuerySpec,
) -> tuple[tuple[int, ...], dict[str, Any]]:
    exclusions = (spec.evidence or {}).get("unresolved_scope_exclusions")
    if not unresolved or not exclusions:
        return unresolved, {
            "excluded_occurrences": 0,
            "excluded_references": [],
        }
    excluded_rows: set[int] = set()
    exclusion_evidence: list[dict[str, Any]] = []
    for rule in exclusions:
        column = str(rule["column"])
        operator = str(rule["operator"])
        if column not in spec.columns or operator != "<=0":
            raise CachedResultError(
                f"Unsupported unresolved-scope exclusion: {rule}"
            )
        column_index = spec.columns.index(column)
        matched = {
            row_index
            for row_index, row in enumerate(rows)
            if row[column_index] is not None
            and int(row[column_index]) <= 0
        }
        excluded_rows.update(matched)
        exclusion_evidence.append(
            {
                **dict(rule),
                "matched_rows": len(matched),
            }
        )
    occurrences: dict[int, list[tuple[int, int]]] = defaultdict(list)
    unresolved_set = set(unresolved)
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            if (
                isinstance(value, str)
                and value.startswith("<ref:")
                and value.endswith(">")
            ):
                reference = int(value[5:-1])
                if reference in unresolved_set:
                    occurrences[reference].append((row_index, column_index))
    excluded_references = {
        reference
        for reference, locations in occurrences.items()
        if locations and all(row_index in excluded_rows for row_index, _ in locations)
    }
    excluded_occurrences = sum(
        len(occurrences[reference])
        for reference in excluded_references
    )
    return (
        tuple(sorted(unresolved_set.difference(excluded_references))),
        {
            "excluded_occurrences": excluded_occurrences,
            "excluded_references": sorted(excluded_references),
            "rules": exclusion_evidence,
            "reason": "References occur only outside the declared positive "
            "inventory scope and remain preserved as anomalies.",
        },
    )


def decode_cache(
    connection: sqlite3.Connection,
    config: ForensicsConfig,
    artifacts: dict[str, int],
    *,
    deep: bool,
) -> dict[str, Any]:
    connection.execute("DELETE FROM cached_results")
    connection.execute("DELETE FROM cached_result_rows")
    connection.execute("DELETE FROM query_specs")
    connection.execute(
        """
        DELETE FROM opaque_regions
        WHERE surface LIKE 'game%' OR surface='extractor_registry'
        """
    )
    specs, import_failures = load_legacy_specs(config.legacy_item_root)
    ranges = load_manifest_ranges(config.legacy_item_root)
    specs = merge_ranges(specs, ranges)
    sql_by_table = load_item_sql(config.sql_manifest)
    specs = attach_sql(specs, sql_by_table)
    registry_root = Path(__file__).resolve().parent / "config"
    static_registry = load_static_layout_registry(
        registry_root / "kakao-r558734-static-layouts.json"
    )
    dependency_registry = load_static_layout_registry(
        registry_root / "kakao-r558734-native-dependencies.json"
    )
    overlap = set(static_registry).intersection(dependency_registry)
    if overlap:
        raise RuntimeError(
            "Duplicate static native registry table(s): "
            + ", ".join(sorted(overlap))
        )
    static_registry.update(dependency_registry)
    existing_tables = {
        spec.table_name.removesuffix("_short").lower()
        for spec in specs
    }
    specs.extend(
        static_query_specs(
            static_registry,
            sql_by_table,
            existing_tables,
        )
    )
    specs.sort(key=lambda spec: spec.stable_key())
    localizations = _load_client_localizations(
        config,
        {spec.table_name.lower() for spec in specs},
    )
    set_metadata(
        connection,
        {
            "query_registry_digest": registry_digest(specs),
            "query_registry_specs": len(specs),
            "embedded_item_sql_tables": len(sql_by_table),
            "static_layout_registry_tables": len(static_registry),
        },
    )
    for failure in import_failures:
        connection.execute(
            """
            INSERT OR IGNORE INTO opaque_regions(
                surface,locator,blocker_code,reason,searched_evidence_json
            ) VALUES ('extractor_registry',?,'extractor_import_failed',?,?)
            """,
            (
                failure["module"],
                failure["error"],
                canonical_json(failure),
            ),
        )

    stream_payloads: dict[str, bytes] = {}
    decoded_counts: Counter[str] = Counter()
    for spec in specs:
        status = _query_spec_status(spec)
        cursor = connection.execute(
            """
            INSERT INTO query_specs(
                table_name,source_module,sql_text,columns_json,layout_json,
                stream_name,start_offset,expected_rows,anchor_json,
                loader_consumer,status,evidence_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                spec.table_name,
                spec.source_module,
                spec.sql_text,
                canonical_json(list(spec.columns)),
                canonical_json(list(spec.layout)),
                spec.stream_name,
                spec.start,
                spec.expected_rows,
                canonical_json(
                    {"id": spec.anchor_id, "values": spec.anchor_values or {}}
                ),
                spec.loader_consumer,
                status,
                canonical_json(spec.evidence or {}),
            ),
        )
        query_spec_id = int(cursor.lastrowid)
        artifact_id = artifacts.get(f"stream:{spec.stream_name}")
        if status != "registered":
            _record_pending_result(
                connection,
                query_spec_id,
                artifact_id,
                status,
                "Specification does not contain a usable layout and locator.",
                spec,
            )
            decoded_counts[status] += 1
            continue
        stream_path = config.streams_root / spec.stream_name
        if not stream_path.is_file() or stream_path.stat().st_size == 0:
            _record_pending_result(
                connection,
                query_spec_id,
                artifact_id,
                "stream_missing",
                f"Missing or empty cached stream: {stream_path}",
                spec,
            )
            decoded_counts["stream_missing"] += 1
            continue
        payload = stream_payloads.setdefault(spec.stream_name, stream_path.read_bytes())
        reader = CachedResultReader(payload)
        first_reference = (spec.evidence or {}).get("first_string_reference")
        if first_reference is not None:
            reader.seed_string_cache(next_reference=int(first_reference))
        try:
            start = spec.start
            if start is None:
                if not deep:
                    raise CachedResultError(
                        "No reused manifest range; deep anchor search disabled"
                    )
                assert spec.anchor_id is not None
                start = reader.locate(
                    spec.columns,
                    spec.layout,
                    spec.anchor_id,
                    spec.anchor_values or {},
                )
            decoded = reader.read_result(
                start,
                spec.layout,
                expected_rows=spec.expected_rows,
                allow_adjacent_result=(
                    (spec.evidence or {}).get("termination")
                    == "adjacent_result"
                ),
            )
            semantic_rows, unresolved, localization_evidence = (
                _resolve_localized_consumers(
                    decoded.rows,
                    spec,
                    localizations,
                )
            )
            semantic_rows, unresolved, global_cache_evidence = (
                _resolve_calibrated_global_strings(
                    payload,
                    semantic_rows,
                    unresolved,
                    spec,
                    config.gamepak_index,
                )
            )
            unresolved, scope_anomaly_evidence = (
                _classify_scoped_string_anomalies(
                    semantic_rows,
                    unresolved,
                    spec,
                )
            )
            row_digest = sha256_bytes(
                canonical_json(semantic_rows).encode("utf-8")
            )
            if unresolved and (spec.evidence or {}).get("id_scope_authority"):
                result_status = "confirmed_id_scope_with_opaque_text"
            elif unresolved:
                result_status = "blocked_unresolved_string_references"
            elif scope_anomaly_evidence["excluded_occurrences"]:
                result_status = "confirmed_positive_scope_with_anomaly"
            elif global_cache_evidence["resolved_occurrences"]:
                result_status = "confirmed_global_cache_resolved"
            elif localization_evidence["localized_occurrences"]:
                result_status = "confirmed_consumer_resolved"
            else:
                result_status = "confirmed"
            resolution_evidence = {
                "captured_strings": decoded.strings_captured,
                "forward_references": list(
                    decoded.resolved_forward_references
                ),
                "localization": localization_evidence,
                "global_string_cache": global_cache_evidence,
                "scope_anomalies": scope_anomaly_evidence,
            }
            connection.execute(
                """
                INSERT INTO cached_results(
                    query_spec_id,artifact_id,start_offset,end_offset,row_count,
                    row_digest,raw_references_json,unresolved_references_json,
                    resolution_evidence_json,status,error
                ) VALUES (?,?,?,?,?,?,?,?,?,?,NULL)
                """,
                (
                    query_spec_id,
                    artifact_id,
                    decoded.start,
                    decoded.end,
                    len(decoded.rows),
                    row_digest,
                    canonical_json(list(decoded.raw_references)),
                    canonical_json(list(unresolved)),
                    canonical_json(resolution_evidence),
                    result_status,
                ),
            )
            connection.executemany(
                """
                INSERT INTO cached_result_rows(
                    query_spec_id,row_index,row_json
                ) VALUES (?,?,?)
                """,
                (
                    (
                        query_spec_id,
                        row_index,
                        canonical_json(dict(zip(spec.columns, row))),
                    )
                    for row_index, row in enumerate(semantic_rows)
                ),
            )
            decoded_counts[result_status] += 1
            if unresolved:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO opaque_regions(
                        surface,locator,blocker_code,reason,searched_evidence_json
                    ) VALUES (?,?,?,?,?)
                    """,
                    (
                        spec.stream_name,
                        f"0x{decoded.start:X}-0x{decoded.end:X}",
                        "unresolved_string_cache_references",
                        (
                            "Non-ID cached strings remain opaque; the numeric entity "
                            "catalog is independently confirmed by its x2game layout, "
                            "native range and row-count boundary."
                            if (spec.evidence or {}).get("id_scope_authority")
                            else "Cached strings could not be resolved from native "
                            "execution order."
                        ),
                        canonical_json(
                            {
                                "table": spec.table_name,
                                "references": list(unresolved),
                                "raw_references": list(decoded.raw_references),
                                "resolution": resolution_evidence,
                                "spec": serialize_spec(spec),
                            }
                        ),
                    ),
                )
        except (CachedResultError, IndexError, ValueError) as exc:
            _record_pending_result(
                connection,
                query_spec_id,
                artifact_id,
                "decode_failed",
                f"{type(exc).__name__}: {exc}",
                spec,
            )
            decoded_counts["decode_failed"] += 1

    known_tables = {
        spec.table_name.removesuffix("_short").lower()
        for spec in specs
    }
    for table, statements in sorted(sql_by_table.items()):
        if table in known_tables:
            continue
        statement = statements[0]
        static_entry = static_registry.get(table)
        native_absent = (
            static_entry is not None
            and static_entry.get("status")
            == "confirmed_layout_result_absent"
        )
        sql_text = str(statement["sql"])
        columns = (
            list(columns_from_select(sql_text))
            if native_absent
            else []
        )
        layout = (
            str(static_entry["layout"]).split()
            if native_absent and static_entry is not None
            else []
        )
        spec_status = (
            "native_result_absent"
            if native_absent
            else "layout_missing"
        )
        evidence = dict(statement)
        if static_entry is not None:
            evidence["static_layout"] = {
                key: value
                for key, value in static_entry.items()
                if key != "evidence"
            }
            evidence.update(static_entry.get("evidence") or {})
        absence_verification: dict[str, Any] | None = None
        if (
            native_absent
            and static_entry is not None
            and static_entry.get("result_absence_evidence")
        ):
            absence_verification = _verify_structural_result_absence(
                config,
                tuple(columns),
                tuple(layout),
                stream_payloads,
                dict(
                    static_entry.get("result_absence_evidence", {}).get(
                        "validators",
                        {},
                    )
                ),
            )
            evidence["result_absence_verification"] = absence_verification
            if absence_verification["semantic_matches"]:
                native_absent = False
        cursor = connection.execute(
            """
            INSERT INTO query_specs(
                table_name,source_module,sql_text,columns_json,layout_json,
                stream_name,start_offset,expected_rows,anchor_json,
                loader_consumer,status,evidence_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                table,
                (
                    str(
                        (static_entry.get("evidence") or {}).get(
                            "registry_path",
                            "item_forensics/config/static-layouts.json",
                        )
                    )
                    if native_absent
                    else "client-sql-surfaces-v1-manifest.json"
                ),
                sql_text,
                canonical_json(columns),
                canonical_json(layout),
                (
                    str(static_entry["stream"])
                    if native_absent and static_entry is not None
                    else "unknown"
                ),
                None,
                None,
                "{}",
                (
                    f"x2game.dll FUN_{static_entry['loader']}"
                    if native_absent and static_entry is not None
                    else None
                ),
                (
                    "blocked_unexpected_structural_result_match"
                    if absence_verification
                    and absence_verification["semantic_matches"]
                    else spec_status
                ),
                canonical_json(evidence),
            ),
        )
        query_spec_id = int(cursor.lastrowid)
        if absence_verification and absence_verification["semantic_matches"]:
            spec_status = "blocked_unexpected_structural_result_match"
        _record_pending_result(
            connection,
            query_spec_id,
            None,
            spec_status,
            (
                "Loader layout is confirmed, but its guarded table produced "
                "no native cached result in this client build."
                if native_absent
                else (
                    "A result with the same structural layout was found; exact "
                    "table identity must be proven before the cached result can "
                    "be assigned."
                    if spec_status == "blocked_unexpected_structural_result_match"
                    else "Embedded SQL is known, but its cached layout/result "
                    "range is not decoded."
                )
            ),
            None,
        )
        decoded_counts[spec_status] += 1
    set_metadata(
        connection,
        {"cached_result_status_counts": canonical_json(dict(sorted(decoded_counts.items())))},
    )
    return {
        "registry_specs": len(specs),
        "sql_item_tables": len(sql_by_table),
        "import_failures": len(import_failures),
        "result_statuses": dict(sorted(decoded_counts.items())),
    }


def _verify_structural_result_absence(
    config: ForensicsConfig,
    columns: tuple[str, ...],
    layout: tuple[str, ...],
    payload_cache: dict[str, bytes],
    validators: dict[str, Any] | None = None,
) -> dict[str, Any]:
    streams: dict[str, int] = {}
    matches: list[dict[str, Any]] = []
    for path in sorted(config.streams_root.glob("game*"), key=lambda value: value.name):
        if not path.is_file() or path.stat().st_size == 0:
            continue
        payload = payload_cache.setdefault(path.name, path.read_bytes())
        headers = CachedResultReader(payload).result_headers()
        streams[path.name] = len(headers)
        for header in headers:
            if header.row_count == 0:
                continue
            try:
                decoded = CachedResultReader(payload).read_result(
                    header.start,
                    layout,
                    expected_rows=header.row_count,
                )
            except (CachedResultError, IndexError, ValueError):
                continue
            matches.append(
                {
                    "stream": path.name,
                    "header": header.header,
                    "start": header.start,
                    "end": decoded.end,
                    "rows": header.row_count,
                    "semantic_match": _rows_match_absence_validators(
                        columns,
                        decoded.rows,
                        validators or {},
                    ),
                }
            )
    semantic_matches = [
        match for match in matches if bool(match["semantic_match"])
    ]
    return {
        "method": (
            "Every self-describing native cached-result header was decoded "
            "against the exact x2game-confirmed layout."
        ),
        "layout": list(layout),
        "columns": list(columns),
        "validators": validators or {},
        "stream_header_counts": streams,
        "structural_matches": matches,
        "semantic_matches": semantic_matches,
    }


def _rows_match_absence_validators(
    columns: tuple[str, ...],
    rows: tuple[tuple[Any, ...], ...],
    validators: dict[str, Any],
) -> bool:
    if not rows:
        return False
    mappings = [dict(zip(columns, row)) for row in rows]
    id_column = str(validators.get("id_column", ""))
    if id_column:
        try:
            ids = [int(row[id_column]) for row in mappings]
        except (KeyError, TypeError, ValueError):
            return False
        if any(value <= 0 for value in ids) or len(ids) != len(set(ids)):
            return False
    for column in validators.get("boolean_columns", []):
        if any(row.get(str(column)) not in (0, 1) for row in mappings):
            return False
    for column in validators.get("nonnegative_columns", []):
        try:
            if any(int(row[str(column)]) < 0 for row in mappings):
                return False
        except (KeyError, TypeError, ValueError):
            return False
    return True


def _record_pending_result(
    connection: sqlite3.Connection,
    query_spec_id: int,
    artifact_id: int | None,
    status: str,
    error: str,
    spec: QuerySpec | None,
) -> None:
    connection.execute(
        """
        INSERT INTO cached_results(
            query_spec_id,artifact_id,start_offset,end_offset,row_count,row_digest,
            raw_references_json,unresolved_references_json,
            resolution_evidence_json,status,error
        ) VALUES (?,?,NULL,NULL,NULL,NULL,'[]','[]','{}',?,?)
        """,
        (query_spec_id, artifact_id, status, error),
    )
    if spec is not None:
        connection.execute(
            """
            INSERT OR IGNORE INTO opaque_regions(
                surface,locator,blocker_code,reason,searched_evidence_json
            ) VALUES (?,?,?,?,?)
            """,
            (
                spec.stream_name,
                f"query:{spec.table_name}",
                status,
                error,
                canonical_json(serialize_spec(spec)),
            ),
        )


def _runtime_row(
    runtime: sqlite3.Connection,
    table: str,
    item_id: int,
) -> dict[str, Any] | None:
    available_columns = columns(runtime, table)
    if "item_id" in available_columns:
        key = "item_id"
    elif table == "items" and "id" in available_columns:
        key = "id"
    else:
        return None
    row = runtime.execute(
        f"SELECT * FROM {quoted(table)} WHERE {quoted(key)}=? ORDER BY rowid LIMIT 1",
        (item_id,),
    ).fetchone()
    return _row_dict(row) if row else None


def _runtime_coverage(
    connection: sqlite3.Connection,
    runtime: sqlite3.Connection,
    runtime_tables: set[str],
    client_ids: set[int],
) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    runtime_item_ids = (
        {int(row[0]) for row in runtime.execute("SELECT id FROM items WHERE id>0")}
        if "items" in runtime_tables
        else set()
    )
    if "aaemu_item_definition_coverage" in runtime_tables:
        for row in runtime.execute(
            "SELECT * FROM aaemu_item_definition_coverage ORDER BY item_id"
        ):
            value = _row_dict(row)
            item_id = int(value["item_id"])
            result[item_id] = value
            connection.execute(
                """
                INSERT INTO runtime_coverage(
                    item_id,concrete_type,coverage,missing_dependencies,
                    provenance,runtime_present
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    item_id,
                    str(value.get("concrete_type", "unknown")),
                    str(value.get("coverage", "unknown")),
                    str(value.get("missing_dependencies", "")),
                    str(value.get("provenance", "")),
                    int(item_id in runtime_item_ids),
                ),
            )
    for item_id in sorted(client_ids - set(result)):
        connection.execute(
            """
            INSERT INTO runtime_coverage(
                item_id,concrete_type,coverage,missing_dependencies,
                provenance,runtime_present
            ) VALUES (?,?,'unknown','coverage_row_missing','',?)
            """,
            (item_id, "unknown", int(item_id in runtime_item_ids)),
        )
        result[item_id] = {
            "item_id": item_id,
            "concrete_type": "unknown",
            "coverage": "unknown",
            "missing_dependencies": "coverage_row_missing",
            "provenance": "",
        }
    runtime_only = sorted(runtime_item_ids - client_ids)
    if runtime_only:
        connection.execute(
            """
            INSERT OR IGNORE INTO opaque_regions(
                surface,locator,blocker_code,reason,searched_evidence_json
            ) VALUES ('runtime.items','runtime_only','server_only_items',
                      'Runtime rows are absent from the positive AA8 client item catalogue.',?)
            """,
            (canonical_json(runtime_only),),
        )
    return result


def _source_inventory(repo_root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    source_root = repo_root / "AAEmu.Game"
    for path in sorted(source_root.rglob("*.cs")):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        lowered = text.lower()
        relative = path.relative_to(repo_root).as_posix()
        for family in FAMILIES.values():
            for table in family.descriptor_tables:
                if table.lower() in lowered:
                    result[family.name].append(relative)
                    break
    return {
        key: sorted(set(values))
        for key, values in sorted(result.items())
    }


def _x2game_item_desc_hints(
    connection: sqlite3.Connection,
    binaries: Iterable[Path],
) -> list[str]:
    values: set[str] = set()
    for path in sorted(binaries, key=lambda value: value.as_posix().lower()):
        if not path.is_file():
            continue
        data = path.read_bytes()
        for run in ASCII_RUN.finditer(data):
            text = run.group().decode("ascii", errors="replace")
            if "Item" not in text or "Desc" not in text:
                continue
            for match in ITEM_DESC_TOKEN.finditer(text):
                value = match.group(1)
                if len(value) > 300:
                    continue
                values.add(value)
                connection.execute(
                    """
                    INSERT OR IGNORE INTO source_hints(
                        item_id,family,hint_kind,locator,value,authority
                    ) VALUES (NULL,'unclassified','x2game_item_desc_rtti',?,?,0)
                    """,
                    (
                        f"{path.resolve().as_posix()}@0x{run.start():X}",
                        value,
                    ),
                )
    return sorted(values)


def _descriptor_state(
    item_id: int,
    impl_id: int,
    family: Family | None,
    coverage: dict[str, Any],
    descriptor_row: dict[str, Any] | None,
    descriptor_native: bool = False,
) -> tuple[str, str]:
    runtime_state = str(coverage.get("coverage", "unknown"))
    provenance = str(coverage.get("provenance", ""))
    if impl_id == 0:
        if runtime_state in ("complete", "phase_a_candidate"):
            return "confirmed", provenance or "client_compact_8"
        return "unknown", "client_compact_8"
    if family is None:
        return "blocked", "x2game_mapping_unresolved"
    if not family.descriptor_tables:
        return "confirmed", family.confidence
    if descriptor_row is None:
        return "missing", family.confidence
    if descriptor_native:
        return "confirmed", family.confidence
    if runtime_state == "complete":
        return "confirmed", provenance or family.confidence
    if runtime_state == "phase_a_candidate" and (
        "game11_native" in provenance
        or "client_compact_8+game11_native" in provenance
        or family.confidence.startswith("game11_native")
    ):
        return "confirmed", provenance or family.confidence
    return "unknown", "runtime_reference+x2game_type_hint"


def _native_cached_rows_by_table(
    connection: sqlite3.Connection,
) -> dict[str, dict[int, dict[str, Any]]]:
    result: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    rows = connection.execute(
        """
        SELECT q.table_name,rr.row_json
        FROM query_specs q
        JOIN cached_results cr ON cr.query_spec_id=q.query_spec_id
        JOIN cached_result_rows rr ON rr.query_spec_id=q.query_spec_id
        WHERE cr.status LIKE 'confirmed%'
        ORDER BY q.table_name,rr.row_index
        """
    )
    for row in rows:
        value = json.loads(str(row["row_json"]))
        item_id = value.get("item_id")
        if item_id is None:
            continue
        result[str(row["table_name"])][int(item_id)] = value
    return result


def _reference_state(
    connection: sqlite3.Connection,
    runtime: sqlite3.Connection,
    runtime_tables: set[str],
    kind: str,
    target_id: int,
) -> str:
    table_key = REFERENCE_TABLES.get(kind)
    if target_id == 0:
        return "not_applicable"
    if kind == "item":
        native_item = connection.execute(
            "SELECT 1 FROM items WHERE item_id=? LIMIT 1",
            (target_id,),
        ).fetchone()
        if native_item:
            return "confirmed"
    native_entity = connection.execute(
        """
        SELECT 1 FROM native_entities
        WHERE entity_kind=? AND entity_id=? AND state='confirmed'
        LIMIT 1
        """,
        (kind, target_id),
    ).fetchone()
    if native_entity:
        return "confirmed"
    if table_key is None:
        return "unknown"
    table, column = table_key
    if table not in runtime_tables:
        return "missing"
    row = runtime.execute(
        f"SELECT 1 FROM {quoted(table)} WHERE {quoted(column)}=? LIMIT 1",
        (target_id,),
    ).fetchone()
    return "confirmed" if row else "missing"


def _add_dependency(
    connection: sqlite3.Connection,
    runtime: sqlite3.Connection,
    runtime_tables: set[str],
    item_id: int,
    column: str,
    target: Any,
    provenance: str,
    evidence: dict[str, Any],
) -> None:
    if target in (None, "", 0, "0"):
        return
    try:
        target_id = int(target)
    except (TypeError, ValueError):
        return
    kind = ITEM_REFERENCE_KIND.get(column)
    if kind is None:
        if column.endswith("_item_id"):
            kind = "item"
        elif column.endswith("_skill_id"):
            kind = "skill"
        elif column.endswith("_buff_id"):
            kind = "buff"
        elif column.endswith("_npc_id"):
            kind = "npc"
        elif column.endswith("_doodad_id"):
            kind = "doodad"
        elif column.endswith("_quest_id"):
            kind = "quest"
        elif column.endswith("_craft_id"):
            kind = "craft"
        else:
            return
    state = _reference_state(
        connection,
        runtime,
        runtime_tables,
        kind,
        target_id,
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO dependency_edges(
            src_kind,src_id,relation,dst_kind,dst_id,required,state,
            provenance,evidence_json
        ) VALUES ('item',?,?,?,?,1,?,?,?)
        """,
        (
            str(item_id),
            column,
            kind,
            str(target_id),
            state,
            provenance,
            canonical_json(evidence),
        ),
    )


def _add_capability(
    connection: sqlite3.Connection,
    item_id: int,
    dimension: str,
    state: str,
    capability: str,
    evidence_kind: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO server_capabilities(
            item_id,dimension,state,capability,evidence_kind,evidence_json
        ) VALUES (?,?,?,?,?,?)
        """,
        (
            item_id,
            dimension,
            state,
            capability,
            evidence_kind,
            canonical_json(evidence),
        ),
    )
    if state in ("confirmed", "not_applicable"):
        return
    severity = {"unknown": 1, "missing": 3, "blocked": 4}.get(state, 2)
    required = {
        "descriptor": "Native descriptor row and x2game loader layout.",
        "dependency_closure": "All required native rows and exact ID relations.",
        "backend": "Executable AAEmu model/loader/handler evidence.",
        "protocol": "AA8 serializer/handler layout or observed byte trace.",
        "persistence": "Atomic mutation, database mapping and relog proof.",
        "validation": "Repeated in-game action, relog and observer validation.",
    }.get(dimension, "Native AA8 evidence.")
    connection.execute(
        """
        INSERT OR IGNORE INTO gaps(
            item_id,dimension,state,severity,blocker_code,reason,required_evidence
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            item_id,
            dimension,
            state,
            severity,
            f"{dimension}_{state}",
            capability,
            required,
        ),
    )


def audit_server(
    connection: sqlite3.Connection,
    config: ForensicsConfig,
) -> dict[str, Any]:
    connection.execute("DELETE FROM gaps")
    connection.execute("DELETE FROM server_capabilities")
    connection.execute("DELETE FROM dependency_edges")
    connection.execute("DELETE FROM descriptors")
    connection.execute("DELETE FROM runtime_coverage")
    connection.execute("DELETE FROM source_hints")
    connection.execute(
        """
        DELETE FROM opaque_regions
        WHERE surface IN ('runtime.items','x2game.item_factory')
        """
    )
    connection.execute(
        """
        DELETE FROM validation_events
        WHERE (scope_kind='server' AND scope_id='runtime')
           OR (scope_kind='client' AND scope_id='item_impl')
        """
    )
    native_catalog_summary = rebuild_native_catalogs(connection)
    runtime = open_sqlite_read_only(config.runtime)
    try:
        runtime_tables = table_names(runtime)
        item_rows = list(
            connection.execute(
                "SELECT * FROM items ORDER BY item_id"
            )
        )
        client_ids = {int(row["item_id"]) for row in item_rows}
        coverage_by_id = _runtime_coverage(
            connection,
            runtime,
            runtime_tables,
            client_ids,
        )
        source_inventory = _source_inventory(config.repo_root)
        item_desc_hints = _x2game_item_desc_hints(connection, config.x2game)
        native_cached_rows = _native_cached_rows_by_table(connection)
        for family, paths in source_inventory.items():
            for path in paths:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO source_hints(
                        item_id,family,hint_kind,locator,value,authority
                    ) VALUES (NULL,?,'server_loader_source',?,? ,0)
                    """,
                    (family, path, "descriptor table name referenced"),
                )

        impl_counts: Counter[int] = Counter()
        descriptor_states: Counter[str] = Counter()
        capability_states: Counter[str] = Counter()
        for item in item_rows:
            item_id = int(item["item_id"])
            impl_id = int(item["impl_id"])
            impl_counts[impl_id] += 1
            family = family_for_impl(impl_id)
            coverage = coverage_by_id.get(item_id, {})
            descriptor_rows: list[
                tuple[str | None, dict[str, Any] | None, bool]
            ] = []
            if impl_id == 0:
                descriptor_rows.append((None, {"impl_id": 0}, True))
            elif family is not None:
                if family.descriptor_tables:
                    for table in family.descriptor_tables:
                        native_row = native_cached_rows.get(table, {}).get(item_id)
                        runtime_row = (
                            _runtime_row(runtime, table, item_id)
                            if table in runtime_tables
                            else None
                        )
                        descriptor_rows.append(
                            (
                                table,
                                native_row if native_row is not None else runtime_row,
                                native_row is not None,
                            )
                        )
                else:
                    descriptor_rows.append(
                        (
                            None,
                            {
                                "impl_id": impl_id,
                                "item_impl": X2GAME_ITEM_IMPL_NAMES[impl_id],
                                "tableless": True,
                            },
                            True,
                        )
                    )
            else:
                descriptor_rows.append((None, None, False))

            best_state = "blocked"
            for table, descriptor_row, descriptor_native in descriptor_rows:
                state, provenance = _descriptor_state(
                    item_id,
                    impl_id,
                    family,
                    coverage,
                    descriptor_row,
                    descriptor_native,
                )
                order = {"confirmed": 0, "unknown": 1, "missing": 2, "blocked": 3}
                if order.get(state, 4) < order.get(best_state, 4):
                    best_state = state
                connection.execute(
                    """
                    INSERT OR IGNORE INTO descriptors(
                        item_id,family,table_name,row_key,descriptor_json,state,
                        provenance,evidence_json
                    ) VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        item_id,
                        family.name if family else family_name(impl_id),
                        table,
                        str(item_id),
                        canonical_json(descriptor_row or {}),
                        state,
                        provenance,
                        canonical_json(
                            {
                                "runtime_coverage": coverage,
                                "descriptor_native_cached_result": descriptor_native,
                                "mapping_confidence": (
                                    family.confidence if family else "unresolved"
                                ),
                                "item_impl_mapping": (
                                    {
                                        "function": X2GAME_ITEM_IMPL_EVIDENCE,
                                        "impl_id": impl_id,
                                        "name": X2GAME_ITEM_IMPL_NAMES.get(impl_id),
                                    }
                                    if family else None
                                ),
                            }
                        ),
                    ),
                )
                descriptor_states[state] += 1
                if descriptor_row:
                    for column, target in sorted(descriptor_row.items()):
                        if column == "item_id":
                            continue
                        _add_dependency(
                            connection,
                            runtime,
                            runtime_tables,
                            item_id,
                            column,
                            target,
                            provenance,
                            {"table": table, "row_key": item_id},
                        )

            client_value = json.loads(str(item["client_row_json"]))
            for column in (
                "use_skill_id",
                "buff_id",
                "craft_id",
                "loot_quest_id",
                "proc_recharge_restrict_item_id",
                "use_skill_recharge_restrict_item_id",
            ):
                if column in client_value:
                    _add_dependency(
                        connection,
                        runtime,
                        runtime_tables,
                        item_id,
                        column,
                        client_value.get(column),
                        "client_compact_8",
                        {"table": "items", "item_id": item_id},
                    )

            runtime_state = str(coverage.get("coverage", "unknown"))
            has_source_hint = (
                impl_id == 0
                or bool(family and source_inventory.get(family.name))
            )
            dependency_rows = list(
                connection.execute(
                    """
                    SELECT state,COUNT(*) AS count FROM dependency_edges
                    WHERE src_kind='item' AND src_id=?
                    GROUP BY state
                    """,
                    (str(item_id),),
                )
            )
            dependency_counts = {
                str(row["state"]): int(row["count"])
                for row in dependency_rows
            }
            dependency_state = (
                "missing"
                if dependency_counts.get("missing", 0)
                else "confirmed"
                if runtime_state == "complete"
                else "unknown"
            )
            backend_state = (
                "confirmed"
                if runtime_state == "complete" and has_source_hint
                else "unknown"
                if has_source_hint
                else "missing"
            )
            no_action = (
                int(client_value.get("use_skill_id") or 0) == 0
                and impl_id == 0
            )
            protocol_state = (
                "not_applicable"
                if no_action
                else "confirmed"
                if (
                    runtime_state == "complete"
                    and family is not None
                    and family.protocol_known
                )
                else "unknown"
            )
            persistence_state = (
                "not_applicable"
                if no_action
                else "confirmed"
                if runtime_state == "complete" and backend_state == "confirmed"
                else "unknown"
            )
            validation_state = (
                "confirmed" if runtime_state == "complete" else "unknown"
            )
            dimensions = (
                ("catalog", "confirmed", "Positive AA8 client item row exists.", "client_row"),
                (
                    "descriptor",
                    best_state,
                    (
                        "Concrete descriptor is client-native and represented."
                        if best_state == "confirmed"
                        else "Concrete descriptor is not fully proven from AA8-native evidence."
                    ),
                    "native_or_runtime_descriptor",
                ),
                (
                    "dependency_closure",
                    dependency_state,
                    "Required ID relations must resolve in the active AA8 runtime.",
                    "graph_audit",
                ),
                (
                    "backend",
                    backend_state,
                    "AAEmu must load and execute the family without generic fallback.",
                    "runtime_coverage_and_source_hint",
                ),
                (
                    "protocol",
                    protocol_state,
                    "AA8 request/result/ItemTask layout must be confirmed.",
                    "protocol_registry",
                ),
                (
                    "persistence",
                    persistence_state,
                    "Mutations must be atomic and survive relog.",
                    "runtime_and_manual_evidence",
                ),
                (
                    "validation",
                    validation_state,
                    "Repeated action, relog and observer acceptance are required.",
                    "runtime_coverage",
                ),
            )
            for dimension, state, capability, evidence_kind in dimensions:
                _add_capability(
                    connection,
                    item_id,
                    dimension,
                    state,
                    capability,
                    evidence_kind,
                    {
                        "runtime_coverage": runtime_state,
                        "runtime_provenance": coverage.get("provenance", ""),
                        "family": family.name if family else family_name(impl_id),
                        "dependency_states": dependency_counts,
                        "server_source_hints": (
                            source_inventory.get(family.name, [])
                            if family else []
                        ),
                    },
                )
                capability_states[f"{dimension}:{state}"] += 1

        unmapped = {
            impl_id: count
            for impl_id, count in sorted(impl_counts.items())
            if impl_id not in FAMILIES
        }
        for impl_id, count in unmapped.items():
            connection.execute(
                """
                INSERT OR IGNORE INTO opaque_regions(
                    surface,locator,blocker_code,reason,searched_evidence_json
                ) VALUES ('x2game.item_factory',?,'impl_mapping_unresolved',
                          'No exact AA8 impl_id to Item*Desc mapping is registered.',?)
                """,
                (
                    str(impl_id),
                    canonical_json(
                        {
                            "client_item_count": count,
                            "item_desc_rtti_hints": item_desc_hints,
                            "required": (
                                "x2game factory/RTTI/vtable plus matching native loader"
                            ),
                        }
                    ),
                ),
            )
        set_metadata(
            connection,
            {
                "runtime_coverage_counts": canonical_json(
                    dict(
                        connection.execute(
                            """
                            SELECT coverage,COUNT(*) FROM runtime_coverage
                            GROUP BY coverage ORDER BY coverage
                            """
                        ).fetchall()
                    )
                ),
                "descriptor_state_counts": canonical_json(
                    dict(sorted(descriptor_states.items()))
                ),
                "capability_state_counts": canonical_json(
                    dict(sorted(capability_states.items()))
                ),
                "unmapped_impl_counts": canonical_json(unmapped),
                "x2game_item_desc_rtti_hints": canonical_json(item_desc_hints),
            },
        )
        connection.execute(
            """
            INSERT INTO validation_events(
                scope_kind,scope_id,check_name,status,evidence_json
            ) VALUES ('server','runtime','all_client_items_present',?,?)
            """,
            (
                "ok"
                if not [
                    row
                    for row in connection.execute(
                        "SELECT item_id FROM runtime_coverage WHERE runtime_present=0"
                    )
                ]
                else "failed",
                canonical_json(
                    {
                        "missing": [
                            int(row[0])
                            for row in connection.execute(
                                """
                                SELECT item_id FROM runtime_coverage
                                WHERE runtime_present=0 ORDER BY item_id
                                """
                            )
                        ]
                    }
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO validation_events(
                scope_kind,scope_id,check_name,status,evidence_json
            ) VALUES ('client','item_impl','all_impl_ids_mapped',?,?)
            """,
            (
                "ok" if not unmapped else "blocked",
                canonical_json(unmapped),
            ),
        )
        return {
            "runtime_tables": len(runtime_tables),
            "coverage_rows": len(coverage_by_id),
            "unmapped_impl": unmapped,
            "descriptor_states": dict(sorted(descriptor_states.items())),
            "capability_states": dict(sorted(capability_states.items())),
            "native_catalogs": native_catalog_summary,
            "x2game_item_desc_rtti_hints": len(item_desc_hints),
        }
    finally:
        runtime.close()


def _manifest_counts(connection: sqlite3.Connection) -> dict[str, Any]:
    scalar_tables = (
        "artifacts",
        "query_specs",
        "cached_results",
        "cached_result_rows",
        "native_catalogs",
        "native_entities",
        "items",
        "descriptors",
        "dependency_edges",
        "runtime_coverage",
        "server_capabilities",
        "gaps",
        "opaque_regions",
        "validation_events",
        "source_hints",
        "review_manifests",
        "client_surfaces",
        "surface_inventory",
        "surface_references",
    )
    result: dict[str, Any] = {}
    for table in scalar_tables:
        result[table] = int(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        )
    result["runtime_coverage"] = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            """
            SELECT coverage,COUNT(*) FROM runtime_coverage
            GROUP BY coverage ORDER BY coverage
            """
        )
    }
    result["gap_states"] = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT state,COUNT(*) FROM gaps GROUP BY state ORDER BY state"
        )
    }
    result["impl_ids"] = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT impl_id,COUNT(*) FROM items GROUP BY impl_id ORDER BY impl_id"
        )
    }
    return result


def build_manifest(
    database: Path,
    connection: sqlite3.Connection,
    config: ForensicsConfig,
    validation: dict[str, str],
) -> dict[str, Any]:
    artifacts = [
        {
            "role": row["role"],
            "path": row["path"],
            "bytes": int(row["bytes"]),
            "sha256": row["sha256"],
            "provenance": row["provenance"],
        }
        for row in connection.execute(
            "SELECT role,path,bytes,sha256,provenance FROM artifacts ORDER BY role,path"
        )
    ]
    opaque_by_code = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            """
            SELECT blocker_code,COUNT(*) FROM opaque_regions
            GROUP BY blocker_code ORDER BY blocker_code
            """
        )
    }
    return {
        "authority": {
            "client": CLIENT_BUILD,
            "historical_3_0_gameplay_rows": 0,
            "order": [
                "client_compact_8",
                "native_cached_result_streams",
                "x2game_confirmed",
                "observed_protocol",
                "reviewed_dll_lua_xml_surfaces",
                "game_pak",
            ],
        },
        "artifacts": artifacts,
        "classification": "native_item_forensics_inventory",
        "counts": _manifest_counts(connection),
        "database": {
            "path": database.resolve().as_posix(),
            "sha256": sha256_file(database),
        },
        "determinism": {
            "timestamps_in_reproducible_artifacts": False,
            "stable_ordering": True,
        },
        "opaque_evidence": opaque_by_code,
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "validation": validation,
    }


def artifact_map(connection: sqlite3.Connection) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in connection.execute(
        "SELECT artifact_id,role,path FROM artifacts ORDER BY artifact_id"
    ):
        role = str(row["role"])
        if role.startswith("cached_stream:"):
            result[f"stream:{role.split(':', 1)[1]}"] = int(row["artifact_id"])
        result.setdefault(role, int(row["artifact_id"]))
    return result


def run_pipeline(
    config: ForensicsConfig,
    *,
    deep: bool = True,
) -> dict[str, Any]:
    config.validate()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".aa8-item-forensics.",
        suffix=".sqlite",
        dir=config.output_dir,
    )
    os.close(handle)
    Path(temporary_name).unlink(missing_ok=True)
    try:
        connection = create_database(Path(temporary_name))
        set_metadata(
            connection,
            {
                "client_build": config.client_build,
                "schema_version": SCHEMA_VERSION,
                "tool_name": TOOL_NAME,
                "tool_version": TOOL_VERSION,
                "historical_3_0_gameplay_rows": 0,
            },
        )
        artifacts = register_artifacts(connection, config)
        scan_summary = scan_client(connection, config)
        surface_summary = scan_reviewed_surfaces(connection, config)
        decode_summary = decode_cache(
            connection,
            config,
            artifacts,
            deep=deep,
        )
        audit_summary = audit_server(connection, config)
        quick, integrity = finalize_database(connection)
        connection.close()
        temporary = Path(temporary_name)
        temporary.replace(config.database)
        read_only = open_sqlite_read_only(config.database)
        try:
            manifest = build_manifest(
                config.database,
                read_only,
                config,
                {"quick_check": quick, "integrity_check": integrity},
            )
        finally:
            read_only.close()
        closure = generate_native_closure_audit(config)
        manifest["native_closure"] = {
            "json": config.native_closure_report.resolve().as_posix(),
            "json_sha256": closure["json_sha256"],
            "csv": config.native_closure_csv.resolve().as_posix(),
            "csv_sha256": closure["csv_sha256"],
            "summary": {
                "unresolved_descriptors": closure["unresolved_descriptors"],
                "closure_states": closure["closure_states"],
                "consumer_roles": closure["consumer_roles"],
            },
        }
        write_text_atomic(config.manifest, canonical_json(manifest, pretty=True))
        return {
            "scan": scan_summary,
            "surfaces": surface_summary,
            "decode": decode_summary,
            "audit": audit_summary,
            "database": config.database,
            "manifest": config.manifest,
            "database_sha256": manifest["database"]["sha256"],
            "native_closure": closure,
        }
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
