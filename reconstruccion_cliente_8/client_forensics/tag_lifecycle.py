from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .config import ForensicsConfig
from .util import canonical_json, sha256_file, stable_key


TAG_SQL = "SELECT id, name FROM tags"
TAG_COLUMNS = ["id", "name"]
TAG_LAYOUT = ["68", "78"]
TAG_ROWS = 5_280
TAG_ID_MIN = 1
TAG_ID_MAX = 5_656
TAG_START = 5_374_123
TAG_DONE = 5_574_679
TAG_ROW_DIGEST = (
    "2451220D13CCC6C0D47E39D952BAA7CCDDC31E27EA314A7BE2BBE71150EFD029"
)
TAG_CACHED_ROWS_DIGEST = (
    "51F16FA8005976A43C62023F4768F669621901BE467D5F696CA2B10A2733B481"
)
TAG_ID_DIGEST = (
    "45D029E89528E0594D614D3F1231FD955ABFF9193044FA6D57DE8ACC75126795"
)
TAG_X64_LOADER = "FUN_39969130"
TAG_X86_LOADER = "FUN_39b43210"

TAG_RELATIONS = 95_008
TAG_RELATION_PAIRS = 94_881
TAG_ENDPOINTS = 4_795
TAG_PRESENT_ENDPOINTS = 4_784
TAG_TOMBSTONES = 11
TAG_TOMBSTONE_IDS = frozenset(
    {4, 152, 205, 522, 1273, 1389, 2949, 4902, 21423, 25007, 25041}
)
TAG_REFERENCE_DIGEST = (
    "B1E911D17FA1CA6A98C7DE443DA59E882FE7ED37FD523164182B9A78227B10FA"
)
TAG_PRESENT_REFERENCE_DIGEST = (
    "1A7B17AADC0DA74E30475F8D23CF3874708B3A11B34E1082202CD5C894BC7ECE"
)
TAG_TOMBSTONE_DIGEST = (
    "EDE0FAAC3E1D9C2E0FF990A3DE83F9D90B71AACC47CFD21E6B6BA03FC129DF46"
)
TAG_UNIVERSE_DIGEST = (
    "1A450AD9DA5706F401F61B13BE416222380D3B6B7A0CC3CDDF95D63433CE0891"
)
TAG_RELATION_PAIR_DIGEST = (
    "01776C15F42A84C02F63B8423813CF7E57D6C36ED2B74D1FF6798C235E47E1CC"
)

TAG_GHIDRA_HASHES = {
    "loaders_x64": (
        "ABFE61DE734B7524A119BED8C1D11CF7A0DAE754EE4F9F291AA6D0CC9567D89B"
    ),
    "loaders_x86": (
        "F6B162CB39F8A0E7D4122070DFC23AB0542D5786B0974590C55305DE590E3410"
    ),
    "layouts_x64": (
        "3905F9AC79E0B1020294AA717B11B638F5B55F2CA240F6460607981D02BE7C63"
    ),
    "layouts_x86": (
        "9C16B7856358824876D9D2B09BD16908C955089343C5B6D43BBA110992AB1B38"
    ),
    "tasks": (
        "DFAF2406998E74D18D1614B71C5E6DFC718E11BC60BA39B9C1959312066D8781"
    ),
}
PROVENANCE = "aa8-client-forensics:tag-lifecycle"


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {"opaque_text": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _id_digest(values: set[int] | frozenset[int]) -> str:
    return hashlib.sha256(
        b"".join(struct.pack("<I", value) for value in sorted(values))
    ).hexdigest().upper()


def _tag_id(entity_key: str) -> int | None:
    if not entity_key.startswith("tag:"):
        return None
    try:
        return int(entity_key.split(":", 1)[1])
    except ValueError:
        return None


def _ghidra_paths(config: ForensicsConfig) -> dict[str, Path]:
    return {
        "loaders_x64": config.source_ghidra_tag_loaders_x64,
        "loaders_x86": config.source_ghidra_tag_loaders_x86,
        "layouts_x64": config.source_ghidra_tag_layouts_x64,
        "layouts_x86": config.source_ghidra_tag_layouts_x86,
        "tasks": config.source_tag_loader_tasks,
    }


def _validate_ghidra(config: ForensicsConfig) -> dict[str, Any]:
    paths = _ghidra_paths(config)
    digests = {name: sha256_file(path).upper() for name, path in paths.items()}
    if digests != TAG_GHIDRA_HASHES:
        raise RuntimeError(f"tag Ghidra evidence changed: {digests}")
    for architecture, function in (
        ("x64", TAG_X64_LOADER),
        ("x86", TAG_X86_LOADER),
    ):
        layout_path = paths[f"layouts_{architecture}"]
        layouts = json.loads(layout_path.read_text(encoding="utf-8"))
        matches = [
            row
            for row in layouts
            if row.get("table_name") == "tags"
            and row.get("sql_text") == TAG_SQL
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected one {architecture} tag layout, got {len(matches)}"
            )
        row = matches[0]
        checks = {
            "blockers": row.get("blockers") == [],
            "columns": row.get("columns") == TAG_COLUMNS,
            "function": row.get("loader", {}).get("function") == function,
            "layout": row.get("layout") == TAG_LAYOUT,
            "status": row.get("status") == "confirmed_static",
        }
        if not all(checks.values()):
            raise RuntimeError(
                f"Native tag {architecture} layout changed: {checks}"
            )
        loader_text = paths[f"loaders_{architecture}"].read_text(
            encoding="utf-8",
            errors="replace",
        )
        required = (
            TAG_SQL,
            f"FUNCTION_BEGIN\t{function}",
            "LoadTagDescs",
            "sqlite3_step",
        )
        missing = [token for token in required if token not in loader_text]
        if missing:
            raise RuntimeError(
                f"Native tag {architecture} loader anchors changed: {missing}"
            )
    tasks = paths["tasks"].read_text(encoding="utf-8")
    if TAG_SQL not in tasks:
        raise RuntimeError("Native tag loader task is absent")
    return {
        "hashes": digests,
        "paths": {name: path.resolve().as_posix() for name, path in paths.items()},
        "sqlite_done_guard_confirmed": True,
        "x86_x64_layout_parity": True,
    }


def _source_tag_query(
    source: sqlite3.Connection,
) -> tuple[sqlite3.Row, sqlite3.Row, list[dict[str, Any]]]:
    queries = source.execute(
        """
        SELECT * FROM query_specs
        WHERE table_name='tags' AND sql_text=?
        ORDER BY query_spec_id
        """,
        (TAG_SQL,),
    ).fetchall()
    if len(queries) != 1:
        raise RuntimeError(f"Expected one native tags query, got {len(queries)}")
    query = queries[0]
    results = source.execute(
        """
        SELECT * FROM cached_results
        WHERE query_spec_id=?
        ORDER BY cached_result_id
        """,
        (int(query["query_spec_id"]),),
    ).fetchall()
    if len(results) != 1:
        raise RuntimeError(f"Expected one native tags result, got {len(results)}")
    result = results[0]
    rows = [
        json.loads(str(row["row_json"]))
        for row in source.execute(
            """
            SELECT row_json FROM cached_result_rows
            WHERE query_spec_id=?
            ORDER BY row_index
            """,
            (int(query["query_spec_id"]),),
        )
    ]
    checks = {
        "columns": json.loads(str(query["columns_json"])) == TAG_COLUMNS,
        "layout": json.loads(str(query["layout_json"])) == TAG_LAYOUT,
        "query_start": int(query["start_offset"]) == TAG_START,
        "expected_rows": int(query["expected_rows"]) == TAG_ROWS,
        "result_status": str(result["status"]) == "confirmed_consumer_resolved",
        "result_start": int(result["start_offset"]) == TAG_START,
        "result_done": int(result["end_offset"]) == TAG_DONE,
        "result_rows": int(result["row_count"]) == TAG_ROWS,
        "decoded_rows": len(rows) == TAG_ROWS,
        "stored_digest": str(result["row_digest"]).upper() == TAG_ROW_DIGEST,
        "cached_rows_digest": hashlib.sha256(
            canonical_json(rows).encode("utf-8")
        ).hexdigest().upper()
        == TAG_CACHED_ROWS_DIGEST,
        "unresolved_references": json.loads(
            str(result["unresolved_references_json"])
        )
        == [],
    }
    if not all(checks.values()):
        raise RuntimeError(f"Native tags result changed: {checks}")
    registry = json.loads(
        Path(str(query["source_module"])).read_text(encoding="utf-8")
    )
    spec = registry["tables"]["tags"]
    registry_checks = {
        "layout": str(spec["layout"]).split() == TAG_LAYOUT,
        "x64_loader": str(spec["loader"]).lower()
        == TAG_X64_LOADER.lower().removeprefix("fun_"),
        "x86_loader": str(spec["loader_32"]).lower()
        == TAG_X86_LOADER.lower().removeprefix("fun_"),
        "start": int(spec["start"]) == TAG_START,
        "rows": int(spec["rows"]) == TAG_ROWS,
        "status": str(spec["status"]) == "confirmed_native_result",
        "id_scope": spec["id_scope_authority"] is True,
    }
    if not all(registry_checks.values()):
        raise RuntimeError(f"Native tags registry changed: {registry_checks}")
    return query, result, rows


def native_tag_evidence(
    source: sqlite3.Connection,
    config: ForensicsConfig,
) -> tuple[frozenset[int], dict[str, Any]]:
    query, result, rows = _source_tag_query(source)
    active_ids = frozenset(int(row["id"]) for row in rows)
    checks = {
        "count": len(active_ids) == TAG_ROWS,
        "positive": all(value > 0 for value in active_ids),
        "min": min(active_ids) == TAG_ID_MIN,
        "max": max(active_ids) == TAG_ID_MAX,
        "digest": _id_digest(active_ids) == TAG_ID_DIGEST,
        "unique_rows": len(active_ids) == len(rows),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Native tag identity changed: {checks}")
    ghidra = _validate_ghidra(config)
    return active_ids, {
        "active_identity_digest": _id_digest(active_ids),
        "authority": "Kakao 8.0.3.12 r558734 game11 + compact + x2game.dll",
        "checks": checks,
        "ghidra": ghidra,
        "identity_field": {
            "column": "id",
            "layout_token": "68",
            "ordinal": 0,
            "primitive": "uint32",
        },
        "native_filter": None,
        "query": {
            "cached_rows_digest": TAG_CACHED_ROWS_DIGEST,
            "columns": TAG_COLUMNS,
            "done_offset": int(result["end_offset"]),
            "layout": TAG_LAYOUT,
            "query_spec_id": int(query["query_spec_id"]),
            "raw_references": json.loads(str(result["raw_references_json"])),
            "resolution_evidence": json.loads(
                str(result["resolution_evidence_json"])
            ),
            "result_id": int(result["cached_result_id"]),
            "row_count": int(result["row_count"]),
            "row_digest": str(result["row_digest"]).upper(),
            "source_module": str(query["source_module"]),
            "sql": TAG_SQL,
            "start_offset": int(result["start_offset"]),
            "stream_artifact_id": int(result["artifact_id"]),
            "x64_loader": TAG_X64_LOADER,
            "x86_loader": TAG_X86_LOADER,
            "x86_x64_layout_parity": True,
        },
        "rows": len(rows),
    }


def _insert_artifacts(
    destination: sqlite3.Connection,
    config: ForensicsConfig,
    *,
    stage: int,
) -> int:
    rows = []
    for name, path in sorted(_ghidra_paths(config).items()):
        rows.append(
            (
                f"stage{stage}:tag-{name.replace('_', '-')}",
                stage,
                f"tag_{name}",
                path.resolve().as_posix(),
                path.stat().st_size,
                TAG_GHIDRA_HASHES[name],
                config.client_build,
                (
                    "derived_forensic"
                    if name == "tasks"
                    else "client_native"
                ),
                "confirmed",
                PROVENANCE,
                canonical_json(
                    {
                        "scope": "tags",
                        "x86_x64_layout_parity": True,
                    }
                ),
            )
        )
    destination.executemany(
        """
        INSERT INTO artifacts(
            artifact_key,source_stage,role,path,bytes,sha256,build,authority,
            state,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    return len(rows)


def reconcile_tag_query_registry(
    destination: sqlite3.Connection,
    source: sqlite3.Connection,
    config: ForensicsConfig,
) -> dict[str, Any]:
    active_ids, evidence = native_tag_evidence(source, config)
    artifact_count = _insert_artifacts(destination, config, stage=10)
    query_key = f"legacy:item-forensics:query:{evidence['query']['query_spec_id']}"
    query = destination.execute(
        "SELECT evidence_json FROM query_specs WHERE query_key=?",
        (query_key,),
    ).fetchone()
    if query is None:
        raise RuntimeError("Imported tags query is absent")
    query_evidence = _json_object(query["evidence_json"])
    query_evidence["tag_registry_resolution"] = evidence
    destination.execute(
        """
        UPDATE query_specs
        SET state='confirmed',loader_consumer='LoadTagDescs',evidence_json=?
        WHERE query_key=?
        """,
        (canonical_json(query_evidence), query_key),
    )
    consumers = destination.execute(
        """
        SELECT consumer_key,evidence_json FROM consumers
        WHERE scope_key=?
        """,
        (query_key,),
    ).fetchall()
    if len(consumers) != 1:
        raise RuntimeError(
            f"Expected one imported tags consumer, got {len(consumers)}"
        )
    consumer_evidence = _json_object(consumers[0]["evidence_json"])
    consumer_evidence["tag_registry_resolution"] = {
        "architecture": "x64",
        **evidence["query"],
    }
    destination.execute(
        """
        UPDATE consumers
        SET name='LoadTagDescs',module='x2game.dll',locator=?,
            architecture='x64',state='confirmed',evidence_json=?
        WHERE consumer_key=?
        """,
        (
            TAG_X64_LOADER,
            canonical_json(consumer_evidence),
            str(consumers[0]["consumer_key"]),
        ),
    )
    destination.execute(
        """
        INSERT INTO consumers(
            consumer_key,scope_key,consumer_kind,name,module,locator,
            architecture,state,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            "stage10:tags:consumer:x86",
            query_key,
            "native_loader",
            "LoadTagDescs",
            "x2game.dll",
            TAG_X86_LOADER,
            "x86",
            "confirmed",
            canonical_json(
                {
                    "artifact_key": "stage10:tag-loaders-x86",
                    "tag_registry_resolution": evidence["query"],
                }
            ),
        ),
    )
    catalog = destination.execute(
        "SELECT evidence_json FROM native_catalogs WHERE table_name='tags'"
    ).fetchone()
    if catalog is None:
        raise RuntimeError("Imported tags catalog is absent")
    catalog_evidence = _json_object(catalog["evidence_json"])
    catalog_evidence["query_registry_resolution"] = evidence
    destination.execute(
        """
        UPDATE native_catalogs
        SET state='confirmed',row_count=?,distinct_ids=?,provenance=?,
            evidence_json=?
        WHERE table_name='tags'
        """,
        (
            len(active_ids),
            len(active_ids),
            PROVENANCE,
            canonical_json(catalog_evidence),
        ),
    )
    destination.execute(
        """
        INSERT INTO source_records(
            source_record_key,source_table,source_pk,record_json,authority,
            provenance
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            stable_key("source-record", "tag-query-registry", "tags"),
            "tag_query_registry",
            "tags",
            canonical_json(evidence),
            "client_native",
            PROVENANCE,
        ),
    )
    summary = {
        "active_ids": len(active_ids),
        "artifacts": artifact_count,
        "inserted_x86_consumers": 1,
        "updated_consumers": 1,
        "updated_queries": 1,
        "x86_x64_layout_parity": True,
    }
    destination.execute(
        """
        INSERT INTO validation_events(
            validation_key,scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            stable_key(
                "validation", "stage", 10, "tag_query_registry_reconciled"
            ),
            "stage",
            "10",
            "tag_query_registry_reconciled",
            "confirmed",
            canonical_json({**summary, "native_evidence": evidence}),
        ),
    )
    return summary


def reconcile_tag_stage50_result(
    destination: sqlite3.Connection,
    source: sqlite3.Connection,
    config: ForensicsConfig,
) -> dict[str, Any]:
    active_ids, evidence = native_tag_evidence(source, config)
    _query, source_result, rows = _source_tag_query(source)
    artifact_count = _insert_artifacts(destination, config, stage=50)
    query_rows = destination.execute(
        """
        SELECT * FROM query_specs
        WHERE table_name='tags' AND sql_text=?
        """,
        (TAG_SQL,),
    ).fetchall()
    if len(query_rows) != 1:
        raise RuntimeError(
            f"Expected one Stage 50 tags query, got {len(query_rows)}"
        )
    query = query_rows[0]
    query_key = str(query["query_key"])
    result_rows = destination.execute(
        "SELECT * FROM cached_results WHERE query_key=?",
        (query_key,),
    ).fetchall()
    if len(result_rows) != 1:
        raise RuntimeError(
            f"Expected one Stage 50 tags result, got {len(result_rows)}"
        )
    result = result_rows[0]
    before_checks = {
        "start": int(result["start_offset"]) == TAG_START,
        "done": int(result["end_offset"]) == TAG_DONE,
        "rows": int(result["row_count"]) == TAG_ROWS,
        "cached_rows": int(
            destination.execute(
                """
                SELECT COUNT(*) FROM cached_result_rows
                WHERE query_key=?
                """,
                (query_key,),
            ).fetchone()[0]
        )
        == TAG_ROWS,
        "native_rows": int(
            destination.execute(
                """
                SELECT COUNT(*) FROM native_rows
                WHERE source_table='tags'
                """
            ).fetchone()[0]
        )
        == TAG_ROWS,
        "name_properties": int(
            destination.execute(
                """
                SELECT COUNT(*) FROM entity_properties
                WHERE namespace='tags' AND property_name='name'
                """
            ).fetchone()[0]
        )
        == TAG_ROWS,
    }
    if not all(before_checks.values()):
        raise RuntimeError(f"Stage 50 tags surface changed: {before_checks}")

    destination.executemany(
        """
        UPDATE cached_result_rows SET row_json=?
        WHERE query_key=? AND row_index=?
        """,
        [
            (canonical_json(row), query_key, index)
            for index, row in enumerate(rows)
        ],
    )
    destination.execute(
        """
        UPDATE cached_results
        SET row_digest=?,raw_references_json=?,
            unresolved_references_json='[]',resolution_evidence_json=?,
            state='confirmed',error=NULL
        WHERE query_key=?
        """,
        (
            TAG_ROW_DIGEST,
            str(source_result["raw_references_json"]),
            str(source_result["resolution_evidence_json"]),
            query_key,
        ),
    )
    merged_query_evidence = _json_object(query["evidence_json"])
    merged_query_evidence["tag_result_resolution"] = evidence
    destination.execute(
        """
        UPDATE query_specs
        SET state='confirmed',loader_consumer='LoadTagDescs',
            evidence_json=?
        WHERE query_key=?
        """,
        (canonical_json(merged_query_evidence), query_key),
    )
    for row in rows:
        tag_id = int(row["id"])
        key = f"tag:{tag_id}"
        destination.execute(
            """
            UPDATE native_rows
            SET state='confirmed',row_json=?,provenance=?,evidence_json=?
            WHERE source_table='tags' AND entity_key=?
            """,
            (
                canonical_json(row),
                PROVENANCE,
                canonical_json(
                    {
                        "query_key": query_key,
                        "resolved_from": (
                            "authoritative item-forensics cached result + "
                            "client compact localization"
                        ),
                        "source_query_spec_id": evidence["query"][
                            "query_spec_id"
                        ],
                    }
                ),
                key,
            ),
        )
        destination.execute(
            """
            UPDATE entity_properties
            SET value_text=?,state='confirmed',authority='client_native',
                consumer='LoadTagDescs',evidence_json=?
            WHERE entity_key=? AND namespace='tags'
              AND property_name='name'
            """,
            (
                str(row["name"]),
                canonical_json(
                    {
                        "column_index": 1,
                        "layout": "78",
                        "resolution_evidence": evidence["query"][
                            "resolution_evidence"
                        ],
                    }
                ),
                key,
            ),
        )
    catalog = destination.execute(
        "SELECT evidence_json FROM native_catalogs WHERE table_name='tags'"
    ).fetchone()
    if catalog is None:
        raise RuntimeError("Stage 50 tags catalog is absent")
    catalog_evidence = _json_object(catalog["evidence_json"])
    catalog_evidence["tag_result_resolution"] = evidence
    destination.execute(
        """
        UPDATE native_catalogs
        SET state='confirmed',row_count=?,distinct_ids=?,provenance=?,
            evidence_json=?
        WHERE table_name='tags'
        """,
        (
            TAG_ROWS,
            TAG_ROWS,
            PROVENANCE,
            canonical_json(catalog_evidence),
        ),
    )
    opaque_rows = destination.execute(
        """
        SELECT opaque_key,searched_evidence_json FROM opaque_regions
        WHERE surface='tags'
          AND blocker_code='unresolved_string_cache_references'
        """
    ).fetchall()
    if len(opaque_rows) != 1:
        raise RuntimeError(
            f"Expected one superseded tags opaque row, got {len(opaque_rows)}"
        )
    opaque_evidence = _json_object(
        opaque_rows[0]["searched_evidence_json"]
    )
    opaque_evidence["resolution"] = evidence["query"]["resolution_evidence"]
    opaque_evidence["superseded_by"] = PROVENANCE
    destination.execute(
        """
        UPDATE opaque_regions
        SET blocker_code='superseded_string_cache_references_resolved',
            reason=?,searched_evidence_json=?,state='confirmed'
        WHERE opaque_key=?
        """,
        (
            (
                "All tag names were resolved by the authoritative cached "
                "result and client compact localization."
            ),
            canonical_json(opaque_evidence),
            str(opaque_rows[0]["opaque_key"]),
        ),
    )
    for architecture, loader in (("x64", TAG_X64_LOADER), ("x86", TAG_X86_LOADER)):
        destination.execute(
            """
            INSERT INTO consumers(
                consumer_key,scope_key,consumer_kind,name,module,locator,
                architecture,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                f"stage50:tags:consumer:{architecture}",
                query_key,
                "native_loader",
                "LoadTagDescs",
                "x2game.dll",
                loader,
                architecture,
                "confirmed",
                canonical_json(
                    {
                        "artifact_key": (
                            f"stage50:tag-loaders-{architecture}"
                        ),
                        "tag_result_resolution": evidence["query"],
                    }
                ),
            ),
        )
    summary = {
        "artifacts": artifact_count,
        "cached_rows_resolved": TAG_ROWS,
        "name_properties_confirmed": TAG_ROWS,
        "native_rows_confirmed": TAG_ROWS,
        "opaque_regions_superseded": 1,
        "raw_string_references_resolved": len(
            evidence["query"]["raw_references"]
        ),
        "x86_x64_layout_parity": True,
    }
    destination.execute(
        """
        INSERT INTO validation_events(
            validation_key,scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            stable_key(
                "validation", "stage", 50, "tag_cached_result_resolved"
            ),
            "stage",
            "50",
            "tag_cached_result_resolved",
            "confirmed",
            canonical_json({**summary, "native_evidence": evidence}),
        ),
    )
    return summary


def reconcile_native_tag_endpoints(
    destination: sqlite3.Connection,
    *,
    active_ids: frozenset[int],
    catalog_evidence: dict[str, Any],
    stage: int,
    source_artifact_key: str,
    expected: dict[str, int],
    strict_native_digests: bool = True,
) -> dict[str, Any]:
    relation_rows = destination.execute(
        """
        SELECT r.relation_key,r.src_entity_key,r.dst_entity_key,r.relation,
               r.state,r.authority,r.evidence_json
        FROM relations r
        JOIN entities d ON d.entity_key=r.dst_entity_key
        WHERE d.kind='tag'
          AND r.relation='references_tag'
          AND r.authority IN ('client_native','client_reference')
        ORDER BY r.relation_key
        """
    ).fetchall()
    endpoints: dict[int, list[sqlite3.Row]] = defaultdict(list)
    pairs: set[tuple[str, int, str]] = set()
    for row in relation_rows:
        tag_id = _tag_id(str(row["dst_entity_key"]))
        if tag_id is not None and tag_id > 0:
            endpoints[tag_id].append(row)
            pairs.add(
                (
                    str(row["src_entity_key"]),
                    tag_id,
                    str(row["relation"]),
                )
            )
    referenced_ids = frozenset(endpoints)
    present_ids = referenced_ids & active_ids
    tombstones = referenced_ids - active_ids
    universe = active_ids | referenced_ids
    pair_digest = hashlib.sha256(
        "\n".join(
            f"{source}|{tag_id}|{relation}"
            for source, tag_id, relation in sorted(pairs)
        ).encode("utf-8")
    ).hexdigest().upper()
    observed = {
        "active": len(active_ids),
        "active_without_incoming": len(active_ids - referenced_ids),
        "endpoints": len(referenced_ids),
        "present_endpoints": len(present_ids),
        "relation_pairs": len(pairs),
        "relations": len(relation_rows),
        "tombstones": len(tombstones),
        "universe": len(universe),
    }
    evidence_checks = {
        "reference_digest": _id_digest(referenced_ids) == TAG_REFERENCE_DIGEST,
        "present_digest": _id_digest(present_ids)
        == TAG_PRESENT_REFERENCE_DIGEST,
        "tombstone_ids": tombstones == TAG_TOMBSTONE_IDS,
        "tombstone_digest": _id_digest(tombstones)
        == TAG_TOMBSTONE_DIGEST,
        "universe_digest": _id_digest(universe) == TAG_UNIVERSE_DIGEST,
        "relation_pair_digest": pair_digest == TAG_RELATION_PAIR_DIGEST,
    }
    if strict_native_digests and not all(evidence_checks.values()):
        raise RuntimeError(f"Native tag frontier changed: {evidence_checks}")
    for name, value in expected.items():
        if observed.get(name) != value:
            raise RuntimeError(
                f"Stage {stage} tag {name} changed: "
                f"{observed.get(name)} != {value}"
            )
    classifications = {
        tag_id: ("present" if tag_id in active_ids else "tombstone")
        for tag_id in sorted(universe)
    }
    counts = Counter(classifications.values())
    if counts["present"] != len(active_ids) or counts["tombstone"] != len(
        tombstones
    ):
        raise RuntimeError("Native tag lifecycle partition changed")
    entities = {
        str(row["entity_key"]): row
        for row in destination.execute(
            """
            SELECT entity_key,subtype,lifecycle,state,authority,source_stage,
                   provenance,evidence_json
            FROM entities WHERE kind='tag'
            """
        )
    }
    entity_updates: list[tuple[Any, ...]] = []
    relation_updates: list[tuple[Any, ...]] = []
    properties: list[tuple[Any, ...]] = []
    coverage: list[tuple[Any, ...]] = []
    records: list[tuple[Any, ...]] = []
    lifecycle_digest = hashlib.sha256()
    frontier_evidence = {
        "active_identity_digest": catalog_evidence["active_identity_digest"],
        "active_without_incoming": observed["active_without_incoming"],
        "endpoint_digest": _id_digest(referenced_ids),
        "endpoints": observed["endpoints"],
        "pair_digest": pair_digest,
        "present_digest": _id_digest(present_ids),
        "present_endpoints": observed["present_endpoints"],
        "relations": observed["relations"],
        "tombstone_digest": _id_digest(tombstones),
        "tombstone_ids": sorted(tombstones),
        "tombstones": observed["tombstones"],
        "universe": observed["universe"],
        "universe_digest": _id_digest(universe),
    }
    for tag_id, classification in sorted(classifications.items()):
        key = f"tag:{tag_id}"
        prior = entities.get(key)
        if prior is None:
            raise RuntimeError(f"Native tag universe endpoint absent: {key}")
        rows = endpoints.get(tag_id, [])
        evidence = {
            "catalog": catalog_evidence,
            "classification": classification,
            "frontier": frontier_evidence,
            "native_relation_count": len(rows),
            "native_relation_keys_sha256": hashlib.sha256(
                "\n".join(str(row["relation_key"]) for row in rows).encode()
            ).hexdigest().upper(),
            "prior_observation": {
                "authority": str(prior["authority"]),
                "lifecycle": str(prior["lifecycle"]),
                "source_stage": int(prior["source_stage"]),
                "state": str(prior["state"]),
                "subtype": prior["subtype"],
            },
            "rule": (
                "positive ID present in complete unfiltered tags result"
                if classification == "present"
                else (
                    "positive ID referenced by native skill/buff/effect "
                    "relations and absent from complete tags result"
                )
            ),
            "tag_id": tag_id,
        }
        entity_updates.append(
            (
                "tags" if classification == "present" else "tag_reference",
                classification,
                "confirmed" if classification == "present" else "tombstone",
                "client_native",
                PROVENANCE,
                canonical_json(evidence),
                key,
            )
        )
        properties.append(
            (
                stable_key(
                    "property",
                    key,
                    "client.tags.endpoint_lifecycle",
                    "classification",
                    stage,
                ),
                key,
                "client.tags.endpoint_lifecycle",
                "classification",
                stage,
                "text",
                classification,
                None,
                None,
                None,
                None,
                "confirmed",
                "client_native",
                source_artifact_key,
                f"tags-complete:endpoint:{stage}:{tag_id}",
                "LoadTagDescs",
                canonical_json(evidence),
            )
        )
        for dimension in ("identity", "lifecycle", "incoming_relations"):
            if dimension == "incoming_relations" and not rows:
                coverage_state = "not_applicable"
                capability = (
                    "Native tag owner is complete and has no incoming "
                    "skill/buff/effect tag reference in this stage."
                )
            elif classification == "tombstone" and dimension != "incoming_relations":
                coverage_state = "tombstone"
                capability = (
                    "Exact native references survive, but tag identity is "
                    "absent from the complete native catalog."
                )
            else:
                coverage_state = "confirmed"
                capability = (
                    "Native tag identity or exact incoming relations are "
                    "closed by complete client results."
                )
            coverage.append(
                (
                    stable_key(
                        "coverage",
                        "tag-endpoint-lifecycle",
                        stage,
                        tag_id,
                        dimension,
                    ),
                    key,
                    dimension,
                    coverage_state,
                    capability,
                    "client_native",
                    PROVENANCE,
                    canonical_json(evidence),
                )
            )
        records.append(
            (
                stable_key(
                    "source-record",
                    "tag-endpoint-lifecycle",
                    stage,
                    tag_id,
                ),
                f"tag_endpoint_lifecycle_stage_{stage}",
                str(tag_id),
                canonical_json(evidence),
                "client_native",
                PROVENANCE,
            )
        )
        lifecycle_digest.update(
            f"{tag_id}:{classification}:{len(rows)}\n".encode()
        )
        for relation in rows:
            relation_evidence = _json_object(relation["evidence_json"])
            relation_evidence["endpoint_lifecycle_resolution"] = {
                "catalog_identity_digest": catalog_evidence[
                    "active_identity_digest"
                ],
                "classification": classification,
                "original_authority": str(relation["authority"]),
                "original_state": str(relation["state"]),
                "policy": (
                    "exact native edge remains confirmed independently from "
                    "destination lifecycle"
                ),
                "stage": stage,
                "tag_id": tag_id,
            }
            relation_updates.append(
                (
                    "confirmed",
                    "client_native",
                    canonical_json(relation_evidence),
                    str(relation["relation_key"]),
                )
            )
    destination.executemany(
        """
        UPDATE entities
        SET subtype=?,lifecycle=?,state=?,authority=?,provenance=?,
            evidence_json=?
        WHERE entity_key=?
        """,
        entity_updates,
    )
    destination.executemany(
        """
        UPDATE relations SET state=?,authority=?,evidence_json=?
        WHERE relation_key=?
        """,
        relation_updates,
    )
    destination.executemany(
        """
        INSERT INTO entity_properties(
            property_key,entity_key,namespace,property_name,ordinal,value_type,
            value_text,value_integer,value_real,value_boolean,value_json,state,
            authority,source_artifact_key,locator,consumer,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        properties,
    )
    destination.executemany(
        """
        INSERT INTO coverage(
            coverage_key,scope_key,dimension,state,capability,authority,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        coverage,
    )
    destination.executemany(
        """
        INSERT INTO source_records(
            source_record_key,source_table,source_pk,record_json,authority,
            provenance
        ) VALUES(?,?,?,?,?,?)
        """,
        records,
    )
    summary = {
        **observed,
        "lifecycle_digest": lifecycle_digest.hexdigest().upper(),
        "superseded_gaps": 0,
        "tombstone_ids": sorted(tombstones),
    }
    destination.execute(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            f"tag_endpoint_lifecycle_stage_{stage}",
            "tag",
            "id",
            "confirmed",
            observed["relations"],
            observed["universe"],
            PROVENANCE,
            canonical_json({**catalog_evidence, **frontier_evidence, **summary}),
        ),
    )
    destination.execute(
        """
        INSERT INTO validation_events(
            validation_key,scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            stable_key(
                "validation", "stage", stage, "tag_endpoint_lifecycle_closed"
            ),
            "stage",
            str(stage),
            "tag_endpoint_lifecycle_closed",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary
