from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .skills import _structural_headers
from .util import canonical_json, sha256_file, stable_key
from .world_actors import CachedResultReader


@dataclass(frozen=True)
class LootQuery:
    table: str
    sql: str
    columns: tuple[str, ...]
    layout: tuple[str, ...]


LOOT_QUERIES = (
    LootQuery(
        table="loot_packs",
        sql="SELECT id, war_drop FROM loot_packs",
        columns=("id", "war_drop"),
        layout=("68", "38"),
    ),
    LootQuery(
        table="loots",
        sql=(
            "SELECT loot_pack_id, loots.'group', item_id, grade_id, "
            "min_amount, max_amount, drop_rate, always_drop, msg_to_world, "
            "items.loot_quest_id FROM loots INNER JOIN items "
            "ON loots.item_id = items.id"
        ),
        columns=(
            "loot_pack_id",
            "group",
            "item_id",
            "grade_id",
            "min_amount",
            "max_amount",
            "drop_rate",
            "always_drop",
            "msg_to_world",
            "loot_quest_id",
        ),
        layout=("68", "68", "68", "68", "68", "68", "68", "38", "38", "68"),
    ),
)


def _exact_results(
    data: bytes,
    headers: list[tuple[int, int, int]],
    layout: tuple[str, ...],
) -> list[dict[str, int]]:
    matches: list[dict[str, int]] = []
    for index, (header, start, rows) in enumerate(headers[:-1]):
        if rows < 0 or rows > 2_000_000:
            continue
        cursor = start
        reader = CachedResultReader(data, first_string_reference=None)
        try:
            for _ in range(rows):
                _, cursor = reader.row(cursor, list(layout))
        except (IndexError, OverflowError, TypeError, ValueError):
            continue
        if cursor == headers[index + 1][0]:
            matches.append(
                {
                    "header": header,
                    "rows": rows,
                    "start": start,
                    "end": cursor,
                }
            )
    return matches


def audit_loot_native_result(config: Any) -> dict[str, Any]:
    x86_text = config.source_ghidra_loot_loaders_x86.read_text(
        encoding="utf-8"
    )
    tasks = [
        line.split("\t", 1)
        for line in config.source_loot_loader_tasks.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    expected_tasks = [[query.table, query.sql] for query in LOOT_QUERIES]
    if tasks != expected_tasks:
        raise ValueError("Loot loader task registry does not match LOOT_QUERIES")
    required_x86_markers = [
        "LANGUAGE\tx86:LE:32:default",
        "FUNCTION_BEGIN\tFUN_39a07180\t39a07180",
        *[f"SQL\t{query.sql}" for query in LOOT_QUERIES],
    ]
    missing_markers = [
        marker for marker in required_x86_markers if marker not in x86_text
    ]
    if missing_markers or x86_text.count("STRING_MATCHES\t1") != len(LOOT_QUERIES):
        raise ValueError(
            "Incomplete x86 loot loader evidence: "
            + canonical_json(
                {
                    "missing_markers": missing_markers,
                    "exact_string_match_records": x86_text.count(
                        "STRING_MATCHES\t1"
                    ),
                }
            )
        )

    streams: list[dict[str, Any]] = []
    consecutive_candidates: list[dict[str, Any]] = []
    layout_candidates: dict[str, list[dict[str, Any]]] = {
        query.table: [] for query in LOOT_QUERIES
    }
    root = Path(config.source_cached_streams_dir)
    for index in range(12):
        path = root / f"game{index}"
        if not path.is_file():
            streams.append(
                {"stream": path.name, "present": False, "bytes": None}
            )
            continue
        data = path.read_bytes()
        headers = _structural_headers(data)
        streams.append(
            {
                "stream": path.name,
                "present": True,
                "bytes": len(data),
                "structural_headers": len(headers),
            }
        )
        stream_candidates: dict[str, list[dict[str, int]]] = {}
        for query in LOOT_QUERIES:
            stream_candidates[query.table] = _exact_results(
                data, headers, query.layout
            )
            for match in stream_candidates[query.table]:
                layout_candidates[query.table].append(
                    {"stream": path.name, **match}
                )
        loot_by_header = {
            int(value["header"]): value
            for value in stream_candidates["loots"]
        }
        for pack in stream_candidates["loot_packs"]:
            loot = loot_by_header.get(int(pack["end"]))
            if loot is not None:
                consecutive_candidates.append(
                    {
                        "stream": path.name,
                        "loot_packs": pack,
                        "loots": loot,
                    }
                )

    compact = sqlite3.connect(
        f"file:{config.source_client_compact.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    try:
        compact_tables = {
            str(row[0])
            for row in compact.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        compact.close()

    sequence = json.loads(
        config.source_ghidra_sql_call_sequence.read_text(encoding="utf-8")
    )
    sequence_text = canonical_json(sequence).lower()
    sequence_hits = {
        query.table: query.sql.lower() in sequence_text
        for query in LOOT_QUERIES
    }
    return {
        "classification": "native_result_absent_from_available_client_cache",
        "compact_tables": {
            query.table: query.table in compact_tables
            for query in LOOT_QUERIES
        },
        "execution_sequence_hits": sequence_hits,
        "consecutive_layout_candidates": consecutive_candidates,
        "unanchored_layout_candidates": layout_candidates,
        "streams": streams,
        "x64_loader": "FUN_398f70e0",
        "x86_loader": "FUN_39a07180",
        "x86_layout_parity": True,
        "x86_loader_sha256": sha256_file(
            config.source_ghidra_loot_loaders_x86
        ),
        "loader_tasks_sha256": sha256_file(config.source_loot_loader_tasks),
    }


def insert_loot_closure_frontier(
    connection: sqlite3.Connection,
    config: Any,
    *,
    x64_artifact_key: str,
    x86_artifact_key: str,
    tool_name: str,
    tool_version: str,
) -> dict[str, int]:
    audit = audit_loot_native_result(config)
    connection.execute(
        """
        INSERT INTO decoders(
            decoder_key,name,version,sha256,status,inputs_json,
            assumptions_json,provenance
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "stage20:loot-native-result-audit",
            "AA8 loot pack loader and cached-result absence audit",
            tool_version,
            None,
            "blocked",
            canonical_json(audit),
            canonical_json(
                {
                    "rows_are_not_inferred": True,
                    "runtime_compact_is_not_authority": True,
                    "wiki_is_not_authority": True,
                    "x86_x64_layout_parity": True,
                }
            ),
            tool_name,
        ),
    )
    for ordinal, query in enumerate(LOOT_QUERIES, start=1):
        query_key = f"stage20:closure:{query.table}"
        candidates = audit["unanchored_layout_candidates"][query.table]
        connection.execute(
            """
            INSERT INTO query_specs(
                query_key,source_query_spec_id,table_name,source_module,
                sql_text,columns_json,layout_json,stream_name,start_offset,
                expected_rows,anchor_json,loader_consumer,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                query_key,
                950_000 + ordinal,
                query.table,
                x64_artifact_key,
                query.sql,
                canonical_json(query.columns),
                canonical_json(query.layout),
                None,
                None,
                None,
                canonical_json(
                    {
                        "unanchored_layout_candidates": candidates,
                        "native_result": "absent",
                    }
                ),
                "x2game.dll x64 FUN_398f70e0; x86 FUN_39a07180",
                "blocked",
                canonical_json(
                    {
                        "loader_x64": "FUN_398f70e0",
                        "loader_x86": "FUN_39a07180",
                        "layout_parity": True,
                        "audit": audit,
                    }
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO consumers(
                consumer_key,scope_key,consumer_kind,name,module,locator,
                architecture,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("consumer", query_key, "FUN_398f70e0"),
                query_key,
                "native_loader",
                "FUN_398f70e0",
                "x2game.dll",
                query.sql,
                "x64",
                "confirmed",
                canonical_json(
                    {
                        "columns": query.columns,
                        "layout": query.layout,
                        "source_artifact": x64_artifact_key,
                    }
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO consumers(
                consumer_key,scope_key,consumer_kind,name,module,locator,
                architecture,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("consumer", query_key, "FUN_39a07180"),
                query_key,
                "native_loader",
                "FUN_39a07180",
                "x2game.dll",
                query.sql,
                "x86",
                "confirmed",
                canonical_json(
                    {
                        "columns": query.columns,
                        "layout": query.layout,
                        "source_artifact": x86_artifact_key,
                        "layout_parity_with_x64": True,
                    }
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("stage20", "loot-native-result", query.table),
                f"native_query.{query.table}",
                query_key,
                "native_result_absent",
                (
                    "The AA8 x86/x64 loaders and exact primitive layout are "
                    "confirmed, but no authoritative row result was found in "
                    "the client compact or cached streams."
                ),
                canonical_json(audit),
                20,
                "opaque",
            ),
        )
    return {
        "queries": len(LOOT_QUERIES),
        "opaque_regions": len(LOOT_QUERIES),
        "x64_consumers": len(LOOT_QUERIES),
        "x86_consumers": len(LOOT_QUERIES),
    }
