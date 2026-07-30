from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from typing import Any

from .util import canonical_json, stable_key


ITEMS_SQL_SUFFIX = " FROM items"
ITEMS_NATIVE_ROWS = 21_420
ITEMS_POSITIVE_IDS = 21_419
NATIVE_RELATION_PROVENANCE = {
    "client_compact_8",
    "game11_native",
    "x2game_confirmed",
}
ENDPOINT_GAP_CODES = {
    "referenced_endpoint_not_in_decoded_stages",
    "referenced_endpoint_not_in_prior_stages",
}
PROVENANCE = "aa8-client-forensics:item-endpoint-lifecycle"


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {"opaque_text": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _item_id(entity_key: str) -> int | None:
    if not entity_key.startswith("item:"):
        return None
    try:
        return int(entity_key.split(":", 1)[1])
    except ValueError:
        return None


def _native_item_catalog(source: sqlite3.Connection) -> tuple[set[int], dict[str, Any]]:
    queries = source.execute(
        """
        SELECT * FROM query_specs
        WHERE table_name='items'
        ORDER BY query_spec_id
        """
    ).fetchall()
    unfiltered = [
        row
        for row in queries
        if str(row["sql_text"]).strip().endswith(ITEMS_SQL_SUFFIX)
        and " where " not in str(row["sql_text"]).lower()
    ]
    if len(unfiltered) != 1:
        raise RuntimeError(
            f"Expected one unfiltered native items query, got {len(unfiltered)}"
        )
    query = unfiltered[0]
    results = source.execute(
        """
        SELECT * FROM cached_results
        WHERE query_spec_id=?
        ORDER BY cached_result_id
        """,
        (int(query["query_spec_id"]),),
    ).fetchall()
    if (
        len(results) != 1
        or int(results[0]["row_count"]) != ITEMS_NATIVE_ROWS
        or results[0]["error"] is not None
        or not str(results[0]["status"]).startswith("confirmed")
    ):
        raise RuntimeError("The complete native items result is not authoritative")
    active_ids = {
        int(row["item_id"])
        for row in source.execute("SELECT item_id FROM items ORDER BY item_id")
    }
    if (
        len(active_ids) != ITEMS_POSITIVE_IDS
        or any(value <= 0 for value in active_ids)
    ):
        raise RuntimeError("The positive native item catalog changed")
    return active_ids, {
        "cached_result_id": int(results[0]["cached_result_id"]),
        "end_offset": int(results[0]["end_offset"]),
        "native_rows": int(results[0]["row_count"]),
        "positive_ids": len(active_ids),
        "query_spec_id": int(query["query_spec_id"]),
        "row_digest": str(results[0]["row_digest"]),
        "sql": str(query["sql_text"]),
        "start_offset": int(results[0]["start_offset"]),
        "status": str(results[0]["status"]),
        "unfiltered_positive_scope": True,
    }


def reconcile_native_item_endpoints(
    destination: sqlite3.Connection,
    source: sqlite3.Connection,
    *,
    stage: int,
    source_artifact_key: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    """Close typed item references against the complete native item catalog.

    A positive ID present in the unfiltered `items` result is `present`. A
    positive ID referenced by an exact native relation but absent from that
    result is a `tombstone`: the reference survives, but no physical item row
    is loaded by this client build.
    """

    active_ids, catalog_evidence = _native_item_catalog(source)
    relation_rows = destination.execute(
        """
        SELECT relation_key,src_entity_key,dst_entity_key,relation,state,
               authority,source_artifact_key,locator,loader_or_consumer,
               provenance,evidence_json
        FROM relations
        WHERE dst_entity_key LIKE 'item:%'
          AND state IN ('blocked','missing','opaque','unknown')
          AND (
              authority='client_native'
              OR provenance IN (
                  'client_compact_8','game11_native','x2game_confirmed'
              )
          )
        ORDER BY relation_key
        """
    ).fetchall()
    endpoints: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in relation_rows:
        item_id = _item_id(str(row["dst_entity_key"]))
        if item_id is None or item_id <= 0:
            continue
        endpoints[item_id].append(row)

    classifications = {
        item_id: ("present" if item_id in active_ids else "tombstone")
        for item_id in sorted(endpoints)
    }
    counts = Counter(classifications.values())
    observed = {
        "relations": sum(len(rows) for rows in endpoints.values()),
        "endpoints": len(endpoints),
        "present": counts["present"],
        "tombstone": counts["tombstone"],
    }
    for key, value in expected.items():
        if observed.get(key) != value:
            raise RuntimeError(
                f"Stage {stage} item endpoint {key} changed: "
                f"{observed.get(key)} != {value}"
            )

    entity_rows = {
        str(row["entity_key"]): row
        for row in destination.execute(
            """
            SELECT entity_key,kind,native_id,subtype,lifecycle,state,authority,
                   source_stage,provenance,evidence_json
            FROM entities
            WHERE kind='item'
            ORDER BY entity_key
            """
        )
    }
    relation_updates: list[tuple[str, str, str]] = []
    entity_updates: list[tuple[str, str, str, str, str]] = []
    properties: list[tuple[Any, ...]] = []
    coverage: list[tuple[Any, ...]] = []
    records: list[tuple[Any, ...]] = []
    endpoint_digest = hashlib.sha256()

    for item_id, classification in sorted(classifications.items()):
        key = f"item:{item_id}"
        rows = endpoints[item_id]
        row = entity_rows.get(key)
        if row is None:
            raise RuntimeError(f"Native relation endpoint is absent: {key}")
        prior_observation = {
            "authority": str(row["authority"]),
            "evidence": _json_object(row["evidence_json"]),
            "lifecycle": str(row["lifecycle"]),
            "provenance": str(row["provenance"]),
            "source_stage": int(row["source_stage"]),
            "state": str(row["state"]),
        }
        endpoint_evidence = {
            "catalog": catalog_evidence,
            "classification": classification,
            "item_id": item_id,
            "native_relation_count": len(rows),
            "native_relation_keys_sha256": hashlib.sha256(
                "\n".join(
                    str(value["relation_key"]) for value in rows
                ).encode("utf-8")
            ).hexdigest().upper(),
            "prior_observation": prior_observation,
            "rule": (
                "positive ID present in complete unfiltered items result"
                if classification == "present"
                else (
                    "positive ID referenced by a typed native edge and absent "
                    "from the complete unfiltered items result"
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
        locator = f"items-complete:endpoint:{stage}:{item_id}"
        properties.append(
            (
                stable_key(
                    "property",
                    key,
                    "client.items.endpoint_lifecycle",
                    "classification",
                    stage,
                ),
                key,
                "client.items.endpoint_lifecycle",
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
                str(catalog_evidence["sql"]),
                canonical_json(endpoint_evidence),
            )
        )
        for dimension in ("identity", "lifecycle", "incoming_relations"):
            coverage.append(
                (
                    stable_key(
                        "coverage",
                        "item-endpoint-lifecycle",
                        stage,
                        item_id,
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
                        "Positive item identity exists in the complete native "
                        "catalog."
                        if classification == "present"
                        else (
                            "Typed native references survive, but the positive "
                            "item identity is absent from the complete catalog."
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
                    "item-endpoint-lifecycle",
                    stage,
                    item_id,
                ),
                f"item_endpoint_lifecycle_stage_{stage}",
                str(item_id),
                canonical_json(endpoint_evidence),
                "client_native",
                PROVENANCE,
            )
        )
        endpoint_digest.update(
            f"{item_id}:{classification}:{len(rows)}\n".encode("utf-8")
        )
        for relation in rows:
            relation_evidence = _json_object(relation["evidence_json"])
            relation_evidence["endpoint_lifecycle_resolution"] = {
                "catalog_query_spec_id": catalog_evidence["query_spec_id"],
                "classification": classification,
                "item_id": item_id,
                "original_authority": str(relation["authority"]),
                "original_state": str(relation["state"]),
                "policy": (
                    "the typed native edge is confirmed independently from "
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

    endpoint_keys = {f"item:{value}" for value in classifications}
    gap_rows = [
        row
        for row in destination.execute(
            """
            SELECT * FROM gaps
            WHERE blocker_code IN (
                'referenced_endpoint_not_in_decoded_stages',
                'referenced_endpoint_not_in_prior_stages'
            )
              AND provenance='aa8-client-forensics'
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
                    "superseded-item-endpoint-gap",
                    stage,
                    str(row["gap_key"]),
                ),
                "superseded_item_endpoint_gaps",
                str(row["gap_key"]),
                canonical_json(
                    {
                        **dict(row),
                        "superseded_by": (
                            f"item_endpoint_lifecycle_stage_{stage}"
                        ),
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
    destination.execute(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            f"item_endpoint_lifecycle_stage_{stage}",
            "item",
            "id",
            "confirmed",
            observed["relations"],
            observed["endpoints"],
            PROVENANCE,
            canonical_json(
                {
                    **catalog_evidence,
                    **observed,
                    "endpoint_digest": endpoint_digest.hexdigest().upper(),
                    "superseded_gaps": len(gap_rows),
                }
            ),
        ),
    )
    summary = {
        **observed,
        "endpoint_digest": endpoint_digest.hexdigest().upper(),
        "superseded_gaps": len(gap_rows),
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
                stage,
                "item_endpoint_lifecycle_closed",
            ),
            "stage",
            str(stage),
            "item_endpoint_lifecycle_closed",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary
