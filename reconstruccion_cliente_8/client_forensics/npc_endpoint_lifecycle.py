from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import ForensicsConfig
from .util import canonical_json, stable_key
from .world_actors import decode_catalog, load_json


NPCS_NATIVE_ROWS = 18_217
NPCS_ID_MIN = 1
NPCS_ID_MAX = 21_626
NPCS_ID_DIGEST = (
    "3A27FDCFD378AF49036ACAD53F2421623A4A4F07F97C7320CF9391DA8DB00417"
)
NPCS_ROW_DIGEST = (
    "963767D30141EBC0CF87F1284D39E4754B2EEF005F4DB982C56B6E87BB27D704"
)
NPCS_REFERENCED_TOMBSTONES = 163
NPCS_FRONTIER_ENDPOINTS = 463
NPCS_FRONTIER_RELATIONS = 932
PROVENANCE = "aa8-client-forensics:npc-endpoint-lifecycle"


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {"opaque_text": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _npc_id(entity_key: str) -> int | None:
    if not entity_key.startswith("npc:"):
        return None
    try:
        return int(entity_key.split(":", 1)[1])
    except ValueError:
        return None


@lru_cache(maxsize=2)
def _native_npc_identity_catalog(
    game11_path: str,
    manifest_path: str,
) -> tuple[frozenset[int], dict[str, Any]]:
    manifest = load_json(Path(manifest_path))
    spec = manifest["tables"]["npcs"]
    if spec.get("native_filter") is not None:
        raise RuntimeError("The native npcs identity query is no longer unfiltered")

    decoded = decode_catalog(Path(game11_path), Path(manifest_path))["npcs"]
    ids = [int(row["id"]) for row in decoded.rows]
    active_ids = frozenset(value for value in ids if value > 0)
    identity_digest = hashlib.sha256(
        b"".join(struct.pack("<I", value) for value in sorted(active_ids))
    ).hexdigest().upper()
    cached = spec["cached_result"]
    checks = {
        "row_count": len(ids) == NPCS_NATIVE_ROWS,
        "positive_unique_ids": len(active_ids) == NPCS_NATIVE_ROWS,
        "id_min": min(active_ids) == NPCS_ID_MIN,
        "id_max": max(active_ids) == NPCS_ID_MAX,
        "identity_digest": identity_digest == NPCS_ID_DIGEST,
        "row_digest": decoded.digest == NPCS_ROW_DIGEST,
        "manifest_row_digest": (
            str(cached["canonical_rows_sha256"]).upper() == NPCS_ROW_DIGEST
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Native npcs identity catalog changed: {checks}")

    columns = [str(value) for value in spec["columns"]]
    sql = f"SELECT {','.join(columns)} FROM npcs"
    evidence = {
        "authority": str(spec["authority"]),
        "checks": checks,
        "done_offset": int(str(cached["done_hex"]), 16),
        "identity_digest": identity_digest,
        "identity_field": {
            "column": "id",
            "layout_token": str(spec["layout"][0]),
            "ordinal": 0,
            "string_cache_independent": True,
        },
        "loader": str(spec["loader"]),
        "native_filter": None,
        "positive_ids": len(active_ids),
        "row_digest": decoded.digest,
        "rows": len(ids),
        "source_game11": str(game11_path),
        "source_manifest": str(manifest_path),
        "sql": sql,
        "sql_address": str(spec["sql_address"]),
        "start_offset": int(str(cached["start_hex"]), 16),
        "unresolved_string_reference_ids": len(
            decoded.unresolved_references
        ),
        "unresolved_string_references": sum(
            decoded.unresolved_references.values()
        ),
    }
    return active_ids, evidence


def native_npc_identity_catalog(
    config: ForensicsConfig,
) -> tuple[frozenset[int], dict[str, Any]]:
    """Return the exact positive NPC identity set and its native evidence."""

    active_ids, evidence = _native_npc_identity_catalog(
        config.source_game11.resolve().as_posix(),
        config.source_npc_catalog_manifest.resolve().as_posix(),
    )
    return active_ids, dict(evidence)


def reconcile_native_npc_endpoints(
    destination: sqlite3.Connection,
    *,
    active_ids: frozenset[int],
    catalog_evidence: dict[str, Any],
    stage: int,
    source_artifact_key: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    """Close exact native NPC references against the unfiltered catalog."""

    relation_rows = destination.execute(
        """
        SELECT r.relation_key,r.src_entity_key,r.dst_entity_key,r.relation,
               r.state,r.authority,r.source_artifact_key,r.locator,
               r.loader_or_consumer,r.provenance,r.evidence_json,
               d.state AS destination_state
        FROM relations r
        JOIN entities d ON d.entity_key=r.dst_entity_key
        WHERE d.kind='npc'
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
        npc_id = _npc_id(str(row["dst_entity_key"]))
        if npc_id is not None and npc_id > 0:
            endpoints[npc_id].append(row)

    classifications = {
        npc_id: ("present" if npc_id in active_ids else "tombstone")
        for npc_id in sorted(endpoints)
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
                f"Stage {stage} NPC endpoint {key} changed: "
                f"{observed.get(key)} != {value}"
            )

    entity_rows = {
        str(row["entity_key"]): row
        for row in destination.execute(
            """
            SELECT entity_key,kind,native_id,subtype,lifecycle,state,authority,
                   source_stage,provenance,evidence_json
            FROM entities
            WHERE kind='npc'
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

    for npc_id, classification in sorted(classifications.items()):
        key = f"npc:{npc_id}"
        rows = endpoints[npc_id]
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
            "npc_id": npc_id,
            "prior_observation": {
                "authority": str(row["authority"]),
                "evidence": _json_object(row["evidence_json"]),
                "lifecycle": str(row["lifecycle"]),
                "provenance": str(row["provenance"]),
                "source_stage": int(row["source_stage"]),
                "state": str(row["state"]),
            },
            "rule": (
                "positive ID present in complete unfiltered npcs result"
                if classification == "present"
                else (
                    "positive ID referenced by an exact native edge and absent "
                    "from the complete unfiltered npcs result"
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
        locator = f"npcs-complete:endpoint:{stage}:{npc_id}"
        properties.append(
            (
                stable_key(
                    "property",
                    key,
                    "client.npcs.endpoint_lifecycle",
                    "classification",
                    stage,
                ),
                key,
                "client.npcs.endpoint_lifecycle",
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
                str(catalog_evidence["loader"]),
                canonical_json(endpoint_evidence),
            )
        )
        for dimension in ("identity", "lifecycle", "incoming_relations"):
            coverage.append(
                (
                    stable_key(
                        "coverage",
                        "npc-endpoint-lifecycle",
                        stage,
                        npc_id,
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
                        "Positive NPC identity exists in the complete native "
                        "catalog."
                        if classification == "present"
                        else (
                            "Exact native references survive, but the positive "
                            "NPC identity is absent from the complete catalog."
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
                    "npc-endpoint-lifecycle",
                    stage,
                    npc_id,
                ),
                f"npc_endpoint_lifecycle_stage_{stage}",
                str(npc_id),
                canonical_json(endpoint_evidence),
                "client_native",
                PROVENANCE,
            )
        )
        endpoint_digest.update(
            f"{npc_id}:{classification}:{len(rows)}\n".encode("utf-8")
        )
        for relation in rows:
            relation_evidence = _json_object(relation["evidence_json"])
            relation_evidence["endpoint_lifecycle_resolution"] = {
                "catalog_identity_digest": catalog_evidence["identity_digest"],
                "classification": classification,
                "npc_id": npc_id,
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

    endpoint_keys = {f"npc:{value}" for value in classifications}
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
                    "superseded-npc-endpoint-gap",
                    stage,
                    str(row["gap_key"]),
                ),
                "superseded_npc_endpoint_gaps",
                str(row["gap_key"]),
                canonical_json(
                    {
                        **dict(row),
                        "superseded_by": (
                            f"npc_endpoint_lifecycle_stage_{stage}"
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
            f"npc_endpoint_lifecycle_stage_{stage}",
            "npc",
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
                "npc_endpoint_lifecycle_closed",
            ),
            "stage",
            str(stage),
            "npc_endpoint_lifecycle_closed",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary
