from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from typing import Any

from .util import canonical_json, stable_key


PROVENANCE = "aa8-client-forensics:buff-endpoint-lifecycle"


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {"opaque_text": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _buff_id(entity_key: str) -> int | None:
    if not entity_key.startswith("buff:"):
        return None
    try:
        return int(entity_key.split(":", 1)[1])
    except ValueError:
        return None


def reconcile_native_buff_endpoints(
    destination: sqlite3.Connection,
    *,
    active_ids: frozenset[int],
    catalog_evidence: dict[str, Any],
    stage: int,
    source_artifact_key: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    """Close exact native buff references against the unfiltered catalog."""

    relation_rows = destination.execute(
        """
        SELECT r.relation_key,r.src_entity_key,r.dst_entity_key,r.relation,
               r.state,r.authority,r.source_artifact_key,r.locator,
               r.loader_or_consumer,r.provenance,r.evidence_json,
               d.state AS destination_state
        FROM relations r
        JOIN entities d ON d.entity_key=r.dst_entity_key
        WHERE d.kind='buff'
          AND (
              d.state NOT IN ('confirmed','tombstone')
              OR r.state IN ('blocked','missing','opaque','tombstone','unknown')
          )
          AND (
              r.authority='client_native'
              OR r.provenance IN (
                  'client_compact_8','game11_native','x2game_confirmed'
              )
          )
        ORDER BY r.relation_key
        """
    ).fetchall()
    endpoints: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in relation_rows:
        buff_id = _buff_id(str(row["dst_entity_key"]))
        if buff_id is not None and buff_id > 0:
            endpoints[buff_id].append(row)

    classifications = {
        buff_id: ("present" if buff_id in active_ids else "tombstone")
        for buff_id in sorted(endpoints)
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
                f"Stage {stage} buff endpoint {key} changed: "
                f"{observed.get(key)} != {value}"
            )

    entity_rows = {
        str(row["entity_key"]): row
        for row in destination.execute(
            """
            SELECT entity_key,kind,native_id,subtype,lifecycle,state,authority,
                   source_stage,provenance,evidence_json
            FROM entities
            WHERE kind='buff'
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

    for buff_id, classification in sorted(classifications.items()):
        key = f"buff:{buff_id}"
        rows = endpoints[buff_id]
        row = entity_rows.get(key)
        if row is None:
            raise RuntimeError(f"Native relation endpoint is absent: {key}")
        endpoint_evidence = {
            "buff_id": buff_id,
            "catalog": catalog_evidence,
            "classification": classification,
            "native_relation_count": len(rows),
            "native_relation_keys_sha256": hashlib.sha256(
                "\n".join(
                    str(value["relation_key"]) for value in rows
                ).encode("utf-8")
            ).hexdigest().upper(),
            "prior_observation": {
                "authority": str(row["authority"]),
                "evidence": _json_object(row["evidence_json"]),
                "lifecycle": str(row["lifecycle"]),
                "provenance": str(row["provenance"]),
                "source_stage": int(row["source_stage"]),
                "state": str(row["state"]),
            },
            "rule": (
                "positive ID present in complete unfiltered buffs result"
                if classification == "present"
                else (
                    "positive ID referenced by an exact native edge and absent "
                    "from the complete unfiltered buffs result"
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
        locator = f"buffs-complete:endpoint:{stage}:{buff_id}"
        properties.append(
            (
                stable_key(
                    "property",
                    key,
                    "client.buffs.endpoint_lifecycle",
                    "classification",
                    stage,
                ),
                key,
                "client.buffs.endpoint_lifecycle",
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
                        "buff-endpoint-lifecycle",
                        stage,
                        buff_id,
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
                        "Positive buff identity exists in the complete native "
                        "catalog."
                        if classification == "present"
                        else (
                            "Exact native references survive, but the positive "
                            "buff identity is absent from the complete catalog."
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
                    "buff-endpoint-lifecycle",
                    stage,
                    buff_id,
                ),
                f"buff_endpoint_lifecycle_stage_{stage}",
                str(buff_id),
                canonical_json(endpoint_evidence),
                "client_native",
                PROVENANCE,
            )
        )
        endpoint_digest.update(
            f"{buff_id}:{classification}:{len(rows)}\n".encode("utf-8")
        )
        for relation in rows:
            relation_evidence = _json_object(relation["evidence_json"])
            relation_evidence["endpoint_lifecycle_resolution"] = {
                "buff_id": buff_id,
                "catalog_identity_digest": catalog_evidence["identity_digest"],
                "classification": classification,
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

    endpoint_keys = {f"buff:{value}" for value in classifications}
    gap_rows = [
        row
        for row in destination.execute(
            """
            SELECT * FROM gaps
            WHERE blocker_code IN (
                'referenced_endpoint_not_in_decoded_stages',
                'referenced_endpoint_not_in_prior_stages'
            )
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
                    "superseded-buff-endpoint-gap",
                    stage,
                    str(row["gap_key"]),
                ),
                "superseded_buff_endpoint_gaps",
                str(row["gap_key"]),
                canonical_json(
                    {
                        **dict(row),
                        "superseded_by": (
                            f"buff_endpoint_lifecycle_stage_{stage}"
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
            f"buff_endpoint_lifecycle_stage_{stage}",
            "buff",
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
                "buff_endpoint_lifecycle_closed",
            ),
            "stage",
            str(stage),
            "buff_endpoint_lifecycle_closed",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary
