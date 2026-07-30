from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .util import canonical_json, stable_key


CRAFT_PACK_ROWS = 466
CRAFT_PACK_ID_MIN = 1
CRAFT_PACK_ID_MAX = 549
CRAFT_PACK_ID_DIGEST = (
    "1B656B7AD4D6484122AE7B8CC0E5AD32E258631FEBE5929AAEC48186E1B594E5"
)
CRAFT_PACK_ROW_DIGEST = (
    "F4B95735E70058B66437FD8843E992EE70A7C6B237633507EE21BA66ABAE9A01"
)
CRAFT_PACK_CACHED_ROWS_DIGEST = (
    "4647D3B4BF7FED5166952693CF21AC7CD0A0F41ED117BF698AEFEE23EAF61257"
)
CRAFT_PACK_START = 134_953_917
CRAFT_PACK_DONE = 134_956_247
CRAFT_PACK_CRAFT_ROWS = 11_951
CRAFT_PACK_CRAFT_ROW_DIGEST = (
    "EA259B17FC64AA5330550774CE67FD26DBA66FAC157085C0409E49CEC306AAFD"
)
CRAFT_PACK_CRAFT_CACHED_ROWS_DIGEST = (
    "9D8FEB31CBC450E0BBE05168AF2715AEA361BA2B33B1CD90F708FF0998E9E90B"
)
CRAFT_PACK_CRAFT_START = 134_798_548
CRAFT_PACK_CRAFT_DONE = 134_953_911
CRAFT_PACK_FRONTIER_RELATIONS = 11_523
CRAFT_PACK_FRONTIER_ENDPOINTS = 1_621
CRAFT_PACK_PRESENT_ENDPOINTS = 438
CRAFT_PACK_TOMBSTONES = 1_183
CRAFT_PACK_FRONTIER_DIGEST = (
    "EDB3FD79E706981D47B3B34B19F02E3952A0A541A9256054CA241DFAF98CB988"
)
CRAFT_PACK_PRESENT_DIGEST = (
    "D6539F3285F17E1581EFA2EE8B31E2F4F748B59632A1E30FA9075E8E8571D46E"
)
CRAFT_PACK_TOMBSTONE_DIGEST = (
    "84C0D71B45A2737CD92E61D8984679AF61CFDB2CE362EBDCE6169B48BA52DE4B"
)
PROVENANCE = "aa8-client-forensics:craft-pack-lifecycle"

QUERY_SPECS = {
    "craft_pack_crafts": {
        "sql": (
            "SELECT id, craft_pack_id, craft_id FROM craft_pack_crafts"
        ),
        "columns": ["id", "craft_pack_id", "craft_id"],
        "layout": ["68", "68", "68"],
        "rows": CRAFT_PACK_CRAFT_ROWS,
        "start": CRAFT_PACK_CRAFT_START,
        "done": CRAFT_PACK_CRAFT_DONE,
        "digest": CRAFT_PACK_CRAFT_ROW_DIGEST,
        "cached_rows_digest": CRAFT_PACK_CRAFT_CACHED_ROWS_DIGEST,
        "x64_loader": "39a82500",
        "x86_loader": "39dc2920",
        "consumer": "LoadCraftPackCraftDescs",
    },
    "craft_packs": {
        "sql": "SELECT id FROM craft_packs",
        "columns": ["id"],
        "layout": ["68"],
        "rows": CRAFT_PACK_ROWS,
        "start": CRAFT_PACK_START,
        "done": CRAFT_PACK_DONE,
        "digest": CRAFT_PACK_ROW_DIGEST,
        "cached_rows_digest": CRAFT_PACK_CACHED_ROWS_DIGEST,
        "x64_loader": "39a82740",
        "x86_loader": "39dc2ad0",
        "consumer": "LoadCraftPackDescs",
    },
}


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


def _craft_pack_id(entity_key: str) -> int | None:
    if not entity_key.startswith("craft_pack:"):
        return None
    try:
        return int(entity_key.split(":", 1)[1])
    except ValueError:
        return None


def _source_query(
    source: sqlite3.Connection,
    table: str,
) -> tuple[sqlite3.Row, sqlite3.Row, list[dict[str, Any]]]:
    expected = QUERY_SPECS[table]
    query_rows = source.execute(
        """
        SELECT * FROM query_specs
        WHERE table_name=? AND sql_text=?
        ORDER BY query_spec_id
        """,
        (table, expected["sql"]),
    ).fetchall()
    if len(query_rows) != 1:
        raise RuntimeError(
            f"Expected one native {table} query, got {len(query_rows)}"
        )
    query = query_rows[0]
    result_rows = source.execute(
        """
        SELECT * FROM cached_results
        WHERE query_spec_id=?
        ORDER BY cached_result_id
        """,
        (int(query["query_spec_id"]),),
    ).fetchall()
    if len(result_rows) != 1:
        raise RuntimeError(
            f"Expected one native {table} result, got {len(result_rows)}"
        )
    result = result_rows[0]
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
    computed_digest = hashlib.sha256(
        canonical_json(rows).encode("utf-8")
    ).hexdigest().upper()
    checks = {
        "columns": json.loads(str(query["columns_json"]))
        == expected["columns"],
        "layout": json.loads(str(query["layout_json"]))
        == expected["layout"],
        "query_start": int(query["start_offset"]) == expected["start"],
        "expected_rows": int(query["expected_rows"]) == expected["rows"],
        "result_status": str(result["status"]) == "confirmed",
        "result_start": int(result["start_offset"]) == expected["start"],
        "result_done": int(result["end_offset"]) == expected["done"],
        "result_rows": int(result["row_count"]) == expected["rows"],
        "decoded_rows": len(rows) == expected["rows"],
        "stored_digest": str(result["row_digest"]).upper()
        == expected["digest"],
        "cached_rows_digest": (
            computed_digest == expected["cached_rows_digest"]
        ),
        "unresolved_references": json.loads(
            str(result["unresolved_references_json"])
        )
        == [],
    }
    if not all(checks.values()):
        raise RuntimeError(f"Native {table} evidence changed: {checks}")

    registry_path = Path(str(query["source_module"]))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_spec = registry["tables"][table]
    registry_checks = {
        "layout": str(registry_spec["layout"]).split()
        == expected["layout"],
        "x64_loader": str(registry_spec["loader"]).lower()
        == expected["x64_loader"],
        "x86_loader": str(registry_spec["loader_32"]).lower()
        == expected["x86_loader"],
        "start": int(registry_spec["start"]) == expected["start"],
        "rows": int(registry_spec["rows"]) == expected["rows"],
        "status": str(registry_spec["status"])
        == "confirmed_native_result",
    }
    if not all(registry_checks.values()):
        raise RuntimeError(
            f"Native {table} registry evidence changed: {registry_checks}"
        )
    return query, result, rows


def native_craft_pack_evidence(
    source: sqlite3.Connection,
) -> tuple[frozenset[int], dict[str, Any]]:
    """Audit the complete owner result and its membership references."""

    query_data: dict[
        str, tuple[sqlite3.Row, sqlite3.Row, list[dict[str, Any]]]
    ] = {
        table: _source_query(source, table)
        for table in sorted(QUERY_SPECS)
    }
    pack_query, pack_result, pack_rows = query_data["craft_packs"]
    link_query, link_result, link_rows = query_data["craft_pack_crafts"]

    active_ids = frozenset(int(row["id"]) for row in pack_rows)
    referenced_ids = frozenset(
        int(row["craft_pack_id"])
        for row in link_rows
        if int(row["craft_pack_id"]) > 0
    )
    present_ids = referenced_ids & active_ids
    tombstones = referenced_ids - active_ids
    unique_pairs = {
        (int(row["craft_id"]), int(row["craft_pack_id"]))
        for row in link_rows
        if int(row["craft_id"]) > 0 and int(row["craft_pack_id"]) > 0
    }
    checks = {
        "active_count": len(active_ids) == CRAFT_PACK_ROWS,
        "active_positive": min(active_ids) == CRAFT_PACK_ID_MIN,
        "active_max": max(active_ids) == CRAFT_PACK_ID_MAX,
        "active_digest": _id_digest(active_ids) == CRAFT_PACK_ID_DIGEST,
        "frontier_relations": (
            len(unique_pairs) == CRAFT_PACK_FRONTIER_RELATIONS
        ),
        "frontier_endpoints": (
            len(referenced_ids) == CRAFT_PACK_FRONTIER_ENDPOINTS
        ),
        "frontier_digest": (
            _id_digest(referenced_ids) == CRAFT_PACK_FRONTIER_DIGEST
        ),
        "present_endpoints": (
            len(present_ids) == CRAFT_PACK_PRESENT_ENDPOINTS
        ),
        "present_digest": (
            _id_digest(present_ids) == CRAFT_PACK_PRESENT_DIGEST
        ),
        "tombstones": len(tombstones) == CRAFT_PACK_TOMBSTONES,
        "tombstone_digest": (
            _id_digest(tombstones) == CRAFT_PACK_TOMBSTONE_DIGEST
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Native craft_pack identity changed: {checks}")

    queries: dict[str, Any] = {}
    for table, (query, result, _rows) in query_data.items():
        expected = QUERY_SPECS[table]
        queries[table] = {
            "columns": expected["columns"],
            "cached_rows_digest": expected["cached_rows_digest"],
            "done_offset": int(result["end_offset"]),
            "layout": expected["layout"],
            "query_spec_id": int(query["query_spec_id"]),
            "result_id": int(result["cached_result_id"]),
            "row_count": int(result["row_count"]),
            "row_digest": str(result["row_digest"]).upper(),
            "source_module": str(query["source_module"]),
            "sql": str(query["sql_text"]),
            "start_offset": int(result["start_offset"]),
            "stream_artifact_id": int(result["artifact_id"]),
            "x64_loader": f"FUN_{expected['x64_loader']}",
            "x86_loader": f"FUN_{expected['x86_loader']}",
            "x86_x64_layout_parity": True,
        }
    evidence = {
        "active_identity_digest": _id_digest(active_ids),
        "authority": "Kakao 8.0.3.12 r558734 game11 + x2game.dll",
        "checks": checks,
        "frontier": {
            "endpoint_digest": _id_digest(referenced_ids),
            "endpoints": len(referenced_ids),
            "present_digest": _id_digest(present_ids),
            "present_endpoints": len(present_ids),
            "relation_rows": len(link_rows),
            "relations_unique": len(unique_pairs),
            "tombstone_digest": _id_digest(tombstones),
            "tombstones": len(tombstones),
        },
        "identity_field": {
            "column": "id",
            "layout_token": "68",
            "ordinal": 0,
            "primitive": "uint32",
        },
        "native_filter": None,
        "queries": queries,
        "rows": len(active_ids),
    }
    return active_ids, evidence


def reconcile_craft_pack_query_registry(
    destination: sqlite3.Connection,
    source: sqlite3.Connection,
) -> dict[str, Any]:
    """Promote the two proven queries and both architecture consumers."""

    active_ids, evidence = native_craft_pack_evidence(source)
    updated_queries = 0
    updated_consumers = 0
    inserted_consumers = 0
    for table in sorted(QUERY_SPECS):
        query_evidence = evidence["queries"][table]
        query_key = (
            f"legacy:item-forensics:query:{query_evidence['query_spec_id']}"
        )
        row = destination.execute(
            "SELECT evidence_json FROM query_specs WHERE query_key=?",
            (query_key,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Imported query is absent: {query_key}")
        merged = _json_object(row["evidence_json"])
        merged["craft_pack_registry_resolution"] = query_evidence
        cursor = destination.execute(
            """
            UPDATE query_specs SET state=?,evidence_json=?
            WHERE query_key=?
            """,
            ("confirmed", canonical_json(merged), query_key),
        )
        updated_queries += cursor.rowcount

        consumer_rows = destination.execute(
            "SELECT consumer_key,evidence_json FROM consumers WHERE scope_key=?",
            (query_key,),
        ).fetchall()
        if len(consumer_rows) != 1:
            raise RuntimeError(
                f"Expected one imported consumer for {table}, "
                f"got {len(consumer_rows)}"
            )
        consumer_evidence = _json_object(
            consumer_rows[0]["evidence_json"]
        )
        consumer_evidence["craft_pack_registry_resolution"] = {
            "architecture": "x64",
            **query_evidence,
        }
        destination.execute(
            """
            UPDATE consumers
            SET name=?,module=?,locator=?,architecture=?,state=?,
                evidence_json=?
            WHERE consumer_key=?
            """,
            (
                QUERY_SPECS[table]["consumer"],
                "x2game.dll",
                query_evidence["x64_loader"],
                "x64",
                "confirmed",
                canonical_json(consumer_evidence),
                str(consumer_rows[0]["consumer_key"]),
            ),
        )
        updated_consumers += 1
        destination.execute(
            """
            INSERT INTO consumers(
                consumer_key,scope_key,consumer_kind,name,module,locator,
                architecture,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                f"stage10:{table}:consumer:x86",
                query_key,
                "native_loader",
                QUERY_SPECS[table]["consumer"],
                "x2game.dll",
                query_evidence["x86_loader"],
                "x86",
                "confirmed",
                canonical_json(
                    {
                        "architecture": "x86",
                        "craft_pack_registry_resolution": query_evidence,
                    }
                ),
            ),
        )
        inserted_consumers += 1
        destination.execute(
            """
            INSERT INTO source_records(
                source_record_key,source_table,source_pk,record_json,
                authority,provenance
            ) VALUES(?,?,?,?,?,?)
            """,
            (
                stable_key(
                    "source-record",
                    "craft-pack-query-registry",
                    table,
                ),
                "craft_pack_query_registry",
                table,
                canonical_json(query_evidence),
                "client_native",
                PROVENANCE,
            ),
        )

    catalog = destination.execute(
        "SELECT evidence_json FROM native_catalogs WHERE table_name='craft_packs'"
    ).fetchone()
    if catalog is None:
        raise RuntimeError("Imported craft_packs catalog is absent")
    catalog_evidence = _json_object(catalog["evidence_json"])
    catalog_evidence["query_registry_resolution"] = evidence
    destination.execute(
        """
        UPDATE native_catalogs
        SET state='confirmed',row_count=?,distinct_ids=?,provenance=?,
            evidence_json=?
        WHERE table_name='craft_packs'
        """,
        (
            len(active_ids),
            len(active_ids),
            PROVENANCE,
            canonical_json(catalog_evidence),
        ),
    )
    summary = {
        "active_ids": len(active_ids),
        "inserted_x86_consumers": inserted_consumers,
        "query_tables": sorted(QUERY_SPECS),
        "updated_consumers": updated_consumers,
        "updated_queries": updated_queries,
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
                "validation",
                "stage",
                10,
                "craft_pack_query_registry_reconciled",
            ),
            "stage",
            "10",
            "craft_pack_query_registry_reconciled",
            "confirmed",
            canonical_json({**summary, "native_evidence": evidence}),
        ),
    )
    return summary


def reconcile_native_craft_pack_endpoints(
    destination: sqlite3.Connection,
    *,
    active_ids: frozenset[int],
    catalog_evidence: dict[str, Any],
    stage: int,
    source_artifact_key: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    """Close all exact native incoming craft_pack relations."""

    relation_rows = destination.execute(
        """
        SELECT r.relation_key,r.src_entity_key,r.dst_entity_key,r.relation,
               r.state,r.authority,r.source_artifact_key,r.locator,
               r.loader_or_consumer,r.provenance,r.evidence_json
        FROM relations r
        JOIN entities d ON d.entity_key=r.dst_entity_key
        WHERE d.kind='craft_pack'
          AND r.relation='member_of_craft_pack'
          AND (
              r.authority IN ('client_native','client_reference')
              OR r.provenance IN ('game11_native','x2game_confirmed')
          )
        ORDER BY r.relation_key
        """
    ).fetchall()
    endpoints: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in relation_rows:
        craft_pack_id = _craft_pack_id(str(row["dst_entity_key"]))
        if craft_pack_id is not None and craft_pack_id > 0:
            endpoints[craft_pack_id].append(row)

    classifications = {
        pack_id: ("present" if pack_id in active_ids else "tombstone")
        for pack_id in sorted(endpoints)
    }
    counts = Counter(classifications.values())
    observed = {
        "relations": len(relation_rows),
        "endpoints": len(endpoints),
        "present": counts["present"],
        "tombstone": counts["tombstone"],
    }
    for key, value in expected.items():
        if observed.get(key) != value:
            raise RuntimeError(
                f"Stage {stage} craft_pack endpoint {key} changed: "
                f"{observed.get(key)} != {value}"
            )

    entity_rows = {
        str(row["entity_key"]): row
        for row in destination.execute(
            """
            SELECT entity_key,kind,native_id,subtype,lifecycle,state,authority,
                   source_stage,provenance,evidence_json
            FROM entities
            WHERE kind='craft_pack'
            ORDER BY entity_key
            """
        )
    }
    entity_updates: list[tuple[Any, ...]] = []
    relation_updates: list[tuple[Any, ...]] = []
    properties: list[tuple[Any, ...]] = []
    coverage: list[tuple[Any, ...]] = []
    records: list[tuple[Any, ...]] = []
    endpoint_digest = hashlib.sha256()

    for pack_id, classification in sorted(classifications.items()):
        key = f"craft_pack:{pack_id}"
        rows = endpoints[pack_id]
        row = entity_rows.get(key)
        if row is None:
            raise RuntimeError(f"Native relation endpoint is absent: {key}")
        endpoint_evidence = {
            "catalog": catalog_evidence,
            "classification": classification,
            "native_relation_count": len(rows),
            "native_relation_keys_sha256": hashlib.sha256(
                "\n".join(
                    str(value["relation_key"]) for value in rows
                ).encode("utf-8")
            ).hexdigest().upper(),
            "pack_id": pack_id,
            "prior_observation": {
                "authority": str(row["authority"]),
                "evidence": _json_object(row["evidence_json"]),
                "lifecycle": str(row["lifecycle"]),
                "provenance": str(row["provenance"]),
                "source_stage": int(row["source_stage"]),
                "state": str(row["state"]),
            },
            "rule": (
                "positive ID present in complete unfiltered craft_packs result"
                if classification == "present"
                else (
                    "positive ID referenced by craft_pack_crafts and absent "
                    "from the complete unfiltered craft_packs result"
                )
            ),
        }
        entity_updates.append(
            (
                classification,
                "confirmed" if classification == "present" else "tombstone",
                "client_native",
                PROVENANCE,
                canonical_json(endpoint_evidence),
                key,
            )
        )
        locator = f"craft_packs-complete:endpoint:{stage}:{pack_id}"
        properties.append(
            (
                stable_key(
                    "property",
                    key,
                    "client.craft_packs.endpoint_lifecycle",
                    "classification",
                    stage,
                ),
                key,
                "client.craft_packs.endpoint_lifecycle",
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
                locator,
                "LoadCraftPackDescs",
                canonical_json(endpoint_evidence),
            )
        )
        for dimension in ("identity", "lifecycle", "incoming_relations"):
            coverage.append(
                (
                    stable_key(
                        "coverage",
                        "craft-pack-endpoint-lifecycle",
                        stage,
                        pack_id,
                        dimension,
                    ),
                    key,
                    dimension,
                    (
                        "confirmed"
                        if classification == "present"
                        or dimension == "incoming_relations"
                        else "tombstone"
                    ),
                    (
                        "Positive craft_pack identity exists in the complete "
                        "native catalog."
                        if classification == "present"
                        else (
                            "Exact native references survive, but the positive "
                            "craft_pack identity is absent from the complete "
                            "native catalog."
                        )
                    ),
                    "client_native",
                    PROVENANCE,
                    canonical_json(endpoint_evidence),
                )
            )
        records.append(
            (
                stable_key(
                    "source-record",
                    "craft-pack-endpoint-lifecycle",
                    stage,
                    pack_id,
                ),
                f"craft_pack_endpoint_lifecycle_stage_{stage}",
                str(pack_id),
                canonical_json(endpoint_evidence),
                "client_native",
                PROVENANCE,
            )
        )
        endpoint_digest.update(
            f"{pack_id}:{classification}:{len(rows)}\n".encode("utf-8")
        )
        for relation in rows:
            relation_evidence = _json_object(relation["evidence_json"])
            relation_evidence["endpoint_lifecycle_resolution"] = {
                "catalog_identity_digest": catalog_evidence[
                    "active_identity_digest"
                ],
                "classification": classification,
                "pack_id": pack_id,
                "original_authority": str(relation["authority"]),
                "original_state": str(relation["state"]),
                "policy": (
                    "the exact native edge is confirmed independently from "
                    "the destination lifecycle"
                ),
                "stage": stage,
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
        SET lifecycle=?,state=?,authority=?,provenance=?,evidence_json=?
        WHERE entity_key=?
        """,
        entity_updates,
    )
    destination.executemany(
        """
        UPDATE relations
        SET state=?,authority=?,evidence_json=?
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
        "endpoint_digest": endpoint_digest.hexdigest().upper(),
        "superseded_gaps": 0,
    }
    destination.execute(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            f"craft_pack_endpoint_lifecycle_stage_{stage}",
            "craft_pack",
            "id",
            "confirmed",
            observed["relations"],
            observed["endpoints"],
            PROVENANCE,
            canonical_json({**catalog_evidence, **summary}),
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
                "validation",
                "stage",
                stage,
                "craft_pack_endpoint_lifecycle_closed",
            ),
            "stage",
            str(stage),
            "craft_pack_endpoint_lifecycle_closed",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary
