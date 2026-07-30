from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from collections import Counter, defaultdict
from typing import Any

from .util import canonical_json, stable_key


PROVENANCE = "aa8-client-forensics:npc-group-identity"
NPC_GROUP_SQL = (
    "SELECT id, aggro_rule_id, enable_respawn, name FROM npc_groups"
)
NPC_GROUP_HEADER = 100_623_898
NPC_GROUP_START = 100_623_904
NPC_GROUP_DONE = 100_630_755
NPC_GROUP_ROWS = 403
NPC_GROUP_STRIDE = 17
NPC_GROUP_ID_DIGEST = (
    "82812B3AECED5EF5F7240C82AC6C354A64CD31AF6D949A3F338BEB61830FBF27"
)
NPC_GROUP_RAW_DIGEST = (
    "447F1926776E994830A3C4660EDE4C174D70DB899DAE4C876F065AF51881EEF3"
)
NPC_GROUP_ROW_DIGEST = (
    "F21750016934B24632DA3DC52CDCBE42B998EF67849181607B4A96D715658398"
)
NPC_GROUP_REFERENCED_TOMBSTONES = 213


def _id_digest(values: set[int] | frozenset[int]) -> str:
    digest = hashlib.sha256()
    for value in sorted(values):
        digest.update(struct.pack("<I", value))
    return digest.hexdigest().upper()


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {"opaque_text": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def native_npc_group_identity_catalog(
    config: Any,
) -> tuple[tuple[dict[str, int], ...], frozenset[int], dict[str, Any]]:
    data = config.source_game11.read_bytes()
    if data[NPC_GROUP_HEADER : NPC_GROUP_HEADER + 2] != b"\x65\x64":
        raise RuntimeError("npc_groups structural header is absent")
    advertised = struct.unpack_from("<I", data, NPC_GROUP_HEADER + 2)[0]
    if advertised != NPC_GROUP_ROWS:
        raise RuntimeError(
            f"npc_groups advertised rows changed: {advertised}"
        )
    if data[NPC_GROUP_DONE : NPC_GROUP_DONE + 2] != b"\x65\x64":
        raise RuntimeError("npc_groups does not end at the next exact header")

    rows: list[dict[str, int]] = []
    cursor = NPC_GROUP_START
    while cursor < NPC_GROUP_DONE:
        if data[cursor] != 100:
            raise RuntimeError(
                f"npc_groups projection lost SQLITE_ROW at {cursor}"
            )
        values = struct.unpack_from("<iiii", data, cursor + 1)
        rows.append(
            {
                "id": values[0],
                "raw_field_1": values[1],
                "raw_field_2": values[2],
                "raw_field_3": values[3],
            }
        )
        cursor += NPC_GROUP_STRIDE
    if cursor != NPC_GROUP_DONE or len(rows) != NPC_GROUP_ROWS:
        raise RuntimeError("npc_groups projection boundary changed")

    ids = {row["id"] for row in rows}
    row_digest = hashlib.sha256()
    for row in rows:
        row_digest.update(
            (canonical_json(row) + "\n").encode("utf-8")
        )
    checks = {
        "positive_distinct_ids": len(ids) == NPC_GROUP_ROWS
        and min(ids) == 1
        and max(ids) == 482,
        "identity_digest": _id_digest(ids) == NPC_GROUP_ID_DIGEST,
        "raw_digest": (
            hashlib.sha256(
                data[NPC_GROUP_START:NPC_GROUP_DONE]
            ).hexdigest().upper()
            == NPC_GROUP_RAW_DIGEST
        ),
        "row_digest": (
            row_digest.hexdigest().upper() == NPC_GROUP_ROW_DIGEST
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"npc_groups catalog checks failed: {checks}")

    sql_manifest = json.loads(
        config.source_sql_surface_manifest.read_text(encoding="utf-8")
    )
    architecture: dict[str, Any] = {}
    for binary in sql_manifest["binaries"]:
        path = str(binary["path"])
        arch = "x86" if "/bin32/" in path else "x64"
        statements = [
            value
            for value in binary["statements"]
            if value.get("value") == NPC_GROUP_SQL
        ]
        if len(statements) != 1:
            raise RuntimeError(
                f"npc_groups SQL surface changed for {arch}"
            )
        architecture[arch] = {
            "binary": path,
            "binary_sha256": str(binary["sha256"]).upper(),
            "sql_offset": int(statements[0]["offset"]),
            "sql_sha256": str(statements[0]["sha256"]).upper(),
            "sql_surface_present": True,
        }

    loader_text = config.source_ghidra_sql_loaders_64.read_text(
        encoding="utf-8",
        errors="replace",
    )
    required_loader_tokens = (
        "TASK\tnpc_groups@dd0430",
        f"SQL\t{NPC_GROUP_SQL}",
        "FUNCTION_BEGIN\tFUN_3994d6c0\t3994d6c0",
    )
    if not all(token in loader_text for token in required_loader_tokens):
        raise RuntimeError("npc_groups x64 loader evidence changed")

    evidence = {
        "architecture": {
            **architecture,
            "x64_loader": "FUN_3994d6c0",
            "x64_sql_layout": ["68", "68", "38", "78"],
            "x86_loader_layout": "not_yet_recovered",
        },
        "boundary": {
            "advertised_rows": advertised,
            "call_index": 251,
            "header": NPC_GROUP_HEADER,
            "header_index": 216,
            "next_header": NPC_GROUP_DONE,
            "npc_anchor_call": 248,
            "npc_anchor_header_index": 213,
            "start": NPC_GROUP_START,
            "stride": NPC_GROUP_STRIDE,
        },
        "identity": {
            "digest": _id_digest(ids),
            "max": max(ids),
            "min": min(ids),
            "rows": len(rows),
        },
        "projection": {
            "layout": ["SQLITE_ROW", "int32", "int32", "int32", "int32"],
            "raw_digest": NPC_GROUP_RAW_DIGEST,
            "row_digest": NPC_GROUP_ROW_DIGEST,
            "secondary_field_semantics": "opaque",
            "sql_layout_mismatch_preserved": True,
        },
        "sql": NPC_GROUP_SQL,
        "unfiltered_positive_scope": True,
    }
    return tuple(rows), frozenset(ids), evidence


def materialize_native_npc_group_catalog(
    destination: sqlite3.Connection,
    *,
    rows: tuple[dict[str, int], ...],
    active_ids: frozenset[int],
    catalog_evidence: dict[str, Any],
    source_artifact_key: str,
) -> dict[str, Any]:
    query_key = "stage30:query:251:npc_groups"
    destination.execute(
        """
        INSERT INTO query_specs(
            query_key,source_query_spec_id,table_name,source_module,sql_text,
            columns_json,layout_json,stream_name,start_offset,expected_rows,
            anchor_json,loader_consumer,state,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            query_key,
            251,
            "npc_groups",
            "x2game.dll",
            NPC_GROUP_SQL,
            canonical_json(
                ["id", "aggro_rule_id", "enable_respawn", "name"]
            ),
            canonical_json(["68", "68", "38", "78"]),
            "game11",
            NPC_GROUP_START,
            NPC_GROUP_ROWS,
            canonical_json(
                {
                    "header": NPC_GROUP_HEADER,
                    "next_header": NPC_GROUP_DONE,
                }
            ),
            "x2game.dll FUN_3994d6c0",
            "confirmed",
            canonical_json(catalog_evidence),
        ),
    )
    destination.execute(
        """
        INSERT INTO cached_results(
            cached_result_key,source_cached_result_id,query_key,artifact_key,
            start_offset,end_offset,row_count,row_digest,raw_references_json,
            unresolved_references_json,resolution_evidence_json,state,error
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "stage30:cached:251:npc_groups",
            251,
            query_key,
            source_artifact_key,
            NPC_GROUP_START,
            NPC_GROUP_DONE,
            NPC_GROUP_ROWS,
            NPC_GROUP_ROW_DIGEST,
            "{}",
            "{}",
            canonical_json(catalog_evidence),
            "confirmed",
            None,
        ),
    )

    entity_rows: list[tuple[Any, ...]] = []
    native_rows: list[tuple[Any, ...]] = []
    properties: list[tuple[Any, ...]] = []
    coverage: list[tuple[Any, ...]] = []
    cached_rows: list[tuple[Any, ...]] = []
    for ordinal, row in enumerate(rows):
        npc_group_id = row["id"]
        key = f"npc_group:{npc_group_id}"
        row_evidence = {
            "catalog": catalog_evidence,
            "ordinal": ordinal,
            "secondary_fields_are_opaque": True,
        }
        entity_rows.append(
            (
                key,
                "npc_group",
                str(npc_group_id),
                "npc_groups",
                "present",
                "confirmed",
                "client_native",
                30,
                PROVENANCE,
                canonical_json(row_evidence),
            )
        )
        native_rows.append(
            (
                stable_key("stage30", "native-row", "npc_groups", npc_group_id),
                key,
                "npc_group",
                str(npc_group_id),
                "npc_groups_identity_projection",
                "confirmed",
                canonical_json(row),
                PROVENANCE,
                canonical_json(row_evidence),
            )
        )
        cached_rows.append((query_key, ordinal, canonical_json(row)))
        properties.append(
            (
                stable_key(
                    "property",
                    key,
                    "client.npc_groups.identity_projection",
                    "id",
                ),
                key,
                "client.npc_groups.identity_projection",
                "id",
                0,
                "integer",
                None,
                npc_group_id,
                None,
                None,
                None,
                "confirmed",
                "client_native",
                source_artifact_key,
                f"npc_groups[{npc_group_id}].id",
                "FUN_3994d6c0",
                canonical_json(row_evidence),
            )
        )
        for dimension in ("identity", "lifecycle"):
            coverage.append(
                (
                    stable_key(
                        "coverage",
                        "npc-group-catalog",
                        npc_group_id,
                        dimension,
                    ),
                    key,
                    dimension,
                    "confirmed",
                    "Positive ID exists in the complete unfiltered owner catalog.",
                    "client_native",
                    PROVENANCE,
                    canonical_json(row_evidence),
                )
            )

    destination.executemany(
        """
        INSERT INTO entities(
            entity_key,kind,native_id,subtype,lifecycle,state,authority,
            source_stage,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        entity_rows,
    )
    destination.executemany(
        """
        INSERT INTO native_rows(
            native_row_key,entity_key,entity_kind,native_id,source_table,state,
            row_json,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?)
        """,
        native_rows,
    )
    destination.executemany(
        """
        INSERT INTO cached_result_rows(query_key,row_index,row_json)
        VALUES(?,?,?)
        """,
        cached_rows,
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
    destination.execute(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "npc_groups_identity_projection",
            "npc_group",
            "id",
            "confirmed",
            len(rows),
            len(active_ids),
            PROVENANCE,
            canonical_json(catalog_evidence),
        ),
    )
    destination.execute(
        """
        INSERT INTO opaque_regions(
            opaque_key,surface,locator,blocker_code,reason,
            searched_evidence_json,source_stage,state
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "stage30:npc-groups-secondary-projection-fields",
            "npc_groups",
            f"game11:{NPC_GROUP_START}..{NPC_GROUP_DONE}",
            "npc_group_secondary_projection_semantics_unresolved",
            (
                "Identity and lifecycle are exact, but the three projected "
                "integers do not preserve the SQL column ABI and their "
                "post-loader semantics remain unassigned."
            ),
            canonical_json(catalog_evidence),
            30,
            "opaque",
        ),
    )
    summary = {
        "active_ids": len(active_ids),
        "identity_digest": _id_digest(active_ids),
        "rows": len(rows),
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
                30,
                "npc_group_identity_catalog_closed",
            ),
            "stage",
            "30",
            "npc_group_identity_catalog_closed",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary


def reconcile_native_npc_group_endpoints(
    destination: sqlite3.Connection,
    *,
    active_ids: frozenset[int],
    catalog_evidence: dict[str, Any],
    source_artifact_key: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    relation_rows = destination.execute(
        """
        SELECT r.relation_key,r.dst_entity_key,r.state,r.authority,
               r.evidence_json,d.native_id,d.evidence_json AS entity_evidence
        FROM relations r
        JOIN entities d ON d.entity_key=r.dst_entity_key
        WHERE d.kind='npc_group'
          AND CAST(d.native_id AS INTEGER)>0
          AND r.authority IN ('client_native','client_reference')
        ORDER BY r.relation_key
        """
    ).fetchall()
    endpoints: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in relation_rows:
        endpoints[int(row["native_id"])].append(row)
    classifications = {
        native_id: ("present" if native_id in active_ids else "tombstone")
        for native_id in sorted(endpoints)
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
                f"Stage 40 npc_group {key} changed: "
                f"{observed.get(key)} != {value}"
            )

    entity_updates: list[tuple[Any, ...]] = []
    relation_updates: list[tuple[Any, ...]] = []
    properties: list[tuple[Any, ...]] = []
    coverage: list[tuple[Any, ...]] = []
    endpoint_digest = hashlib.sha256()
    for native_id, classification in sorted(classifications.items()):
        key = f"npc_group:{native_id}"
        row = endpoints[native_id][0]
        evidence = {
            "catalog": catalog_evidence,
            "classification": classification,
            "native_relation_count": len(endpoints[native_id]),
            "prior_entity_evidence": _json_object(
                str(row["entity_evidence"])
            ),
        }
        entity_updates.append(
            (
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
                    "client.npc_groups.endpoint_lifecycle",
                    "classification",
                ),
                key,
                "client.npc_groups.endpoint_lifecycle",
                "classification",
                40,
                "text",
                classification,
                None,
                None,
                None,
                None,
                "confirmed" if classification == "present" else "tombstone",
                "client_native",
                source_artifact_key,
                f"npc_groups:endpoint:40:{native_id}",
                "FUN_3994d6c0",
                canonical_json(evidence),
            )
        )
        for dimension in ("identity", "lifecycle", "incoming_relations"):
            coverage.append(
                (
                    stable_key(
                        "coverage",
                        "npc-group-endpoint",
                        native_id,
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
                        "Endpoint reconciled against the complete unfiltered "
                        "npc_groups identity catalog."
                    ),
                    "client_native",
                    PROVENANCE,
                    canonical_json(evidence),
                )
            )
        endpoint_digest.update(
            f"{native_id}:{classification}:{len(endpoints[native_id])}\n".encode(
                "utf-8"
            )
        )
        for relation in endpoints[native_id]:
            relation_evidence = _json_object(str(relation["evidence_json"]))
            relation_evidence["npc_group_lifecycle_resolution"] = {
                "classification": classification,
                "policy": (
                    "Exact native edge is confirmed independently from "
                    "destination lifecycle."
                ),
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

    endpoint_keys = {f"npc_group:{value}" for value in endpoints}
    gap_rows = [
        row
        for row in destination.execute(
            """
            SELECT * FROM gaps
            WHERE blocker_code='referenced_endpoint_not_in_prior_stages'
            ORDER BY gap_key
            """
        )
        if str(row["entity_key"]) in endpoint_keys
    ]
    destination.executemany(
        """
        INSERT INTO source_records(
            source_record_key,source_table,source_pk,record_json,authority,
            provenance
        ) VALUES(?,?,?,?,?,?)
        """,
        [
            (
                stable_key(
                    "source-record",
                    "superseded-npc-group-gap",
                    str(row["gap_key"]),
                ),
                "superseded_npc_group_endpoint_gaps",
                str(row["gap_key"]),
                canonical_json(
                    {
                        **dict(row),
                        "superseded_by": "npc_groups_identity_projection",
                    }
                ),
                "client_native",
                PROVENANCE,
            )
            for row in gap_rows
        ],
    )
    destination.executemany(
        "DELETE FROM gaps WHERE gap_key=?",
        [(str(row["gap_key"]),) for row in gap_rows],
    )
    summary = {
        **observed,
        "endpoint_digest": endpoint_digest.hexdigest().upper(),
        "superseded_gaps": len(gap_rows),
    }
    destination.execute(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "npc_group_endpoint_lifecycle_stage_40",
            "npc_group",
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
                40,
                "npc_group_endpoint_lifecycle_closed",
            ),
            "stage",
            "40",
            "npc_group_endpoint_lifecycle_closed",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary
