from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from collections import Counter
from typing import Any

from .schema import open_read_only
from .util import canonical_json, stable_key


PROVENANCE = "aa8-client-forensics:craft-identity-constraints"
CRAFTS_SQL = (
    "SELECT id, actability_limit, cast_delay, cost, craft_c_category_id, "
    "craft_d_category_id, orderable, products_pack_id, recommend_level, "
    "req_doodad_id, skill_id, title, use_only_actability, visible_order, "
    "wi_id FROM crafts WHERE enable = 't'"
)
CRAFTS_TOTAL_ROWS = 11_615
CRAFTS_ENABLED_ROWS = 9_369
CRAFTS_DISABLED_ROWS = 2_246
CRAFTS_OBSERVED_IDS = 12_071
CRAFTS_NON_ENABLED_OBSERVED_IDS = 2_702
CRAFTS_HISTORICAL_ROWS = 456
CRAFTS_ENABLED_ID_DIGEST = (
    "969EB678991F50D224896B5E3E3C32A0F0949366EA6AC27E0F8BCFBA6D52D61F"
)
CRAFTS_REFERENCE_ID_DIGEST = (
    "795E4314BF27E019C73C0A11688B96CC59AA41E455CC3DA7C15BE2E4F9C7491B"
)
CRAFTS_LOCALIZATION_ID_DIGEST = (
    "DAC965F348AEEFBF86B7C90ED798C4F23C83E6537315791D15AE545C0BA6B098"
)
CRAFTS_OBSERVED_ID_DIGEST = (
    "604B2DA86486A015FB37EFFC0C60E40D1AAAD8B27ECB77FBD556C0C6958C6396"
)
CRAFTS_NON_ENABLED_ID_DIGEST = (
    "AC318B420AF5AAFB409A63F0AFD6CFFC294C83157662347BBEFCC2F30AB222E5"
)


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


def native_craft_identity_constraints(
    config: Any,
) -> tuple[frozenset[int], frozenset[int], frozenset[int], dict[str, Any]]:
    """Recover every exact craft set while preserving the unresolved partition.

    The client caches the exact enabled identities and an unfiltered physical
    row count, but it does not cache the identity column for disabled rows.
    Native references and localizations expose a larger historical universe.
    Consequently the sizes of the disabled and historical partitions are exact,
    while assignment of individual non-enabled IDs is underdetermined.
    """

    source = open_read_only(config.source_item_database)
    compact = open_read_only(config.source_client_compact)
    try:
        query_rows = source.execute(
            """
            SELECT * FROM query_specs
            WHERE table_name='crafts' AND sql_text=?
            ORDER BY query_spec_id
            """,
            (CRAFTS_SQL,),
        ).fetchall()
        if len(query_rows) != 1:
            raise RuntimeError("Expected one filtered native crafts query")
        query = query_rows[0]
        query_id = int(query["query_spec_id"])
        query_evidence = _json_object(str(query["evidence_json"]))
        enabled_ids = {
            int(json.loads(str(row["row_json"]))["id"])
            for row in source.execute(
                """
                SELECT row_json FROM cached_result_rows
                WHERE query_spec_id=? ORDER BY row_index
                """,
                (query_id,),
            )
        }
        reference_ids = {
            int(row["dst_id"])
            for row in source.execute(
                """
                SELECT DISTINCT dst_id FROM dependency_edges
                WHERE dst_kind='craft' AND CAST(dst_id AS INTEGER)>0
                ORDER BY CAST(dst_id AS INTEGER)
                """
            )
        }
        localization_ids = {
            int(row["idx"])
            for row in compact.execute(
                """
                SELECT DISTINCT idx FROM localized_texts
                WHERE tbl_name='crafts'
                  AND tbl_column_name='title'
                  AND idx>0
                ORDER BY idx
                """
            )
        }
    finally:
        compact.close()
        source.close()

    observed_ids = enabled_ids | reference_ids | localization_ids
    non_enabled_ids = observed_ids - enabled_ids
    checks = {
        "enabled_rows": (len(enabled_ids), CRAFTS_ENABLED_ROWS),
        "observed_ids": (len(observed_ids), CRAFTS_OBSERVED_IDS),
        "non_enabled_observed_ids": (
            len(non_enabled_ids),
            CRAFTS_NON_ENABLED_OBSERVED_IDS,
        ),
        "enabled_id_digest": (
            _id_digest(enabled_ids),
            CRAFTS_ENABLED_ID_DIGEST,
        ),
        "reference_id_digest": (
            _id_digest(reference_ids),
            CRAFTS_REFERENCE_ID_DIGEST,
        ),
        "localization_id_digest": (
            _id_digest(localization_ids),
            CRAFTS_LOCALIZATION_ID_DIGEST,
        ),
        "observed_id_digest": (
            _id_digest(observed_ids),
            CRAFTS_OBSERVED_ID_DIGEST,
        ),
        "non_enabled_id_digest": (
            _id_digest(non_enabled_ids),
            CRAFTS_NON_ENABLED_ID_DIGEST,
        ),
        "guard_rows": (
            int(query_evidence.get("header_rows", -1)),
            CRAFTS_TOTAL_ROWS,
        ),
        "filtered_rows": (
            int(query_evidence.get("filtered_rows", -1)),
            CRAFTS_ENABLED_ROWS,
        ),
    }
    changed = {
        name: {"observed": actual, "expected": expected}
        for name, (actual, expected) in checks.items()
        if actual != expected
    }
    if changed:
        raise RuntimeError(f"Native craft identity constraints changed: {changed}")

    if (
        CRAFTS_TOTAL_ROWS - CRAFTS_ENABLED_ROWS != CRAFTS_DISABLED_ROWS
        or len(observed_ids) - CRAFTS_TOTAL_ROWS != CRAFTS_HISTORICAL_ROWS
    ):
        raise RuntimeError("Craft partition arithmetic is inconsistent")

    evidence = {
        "architecture": {
            "x64_loader": "FUN_39a818b0",
            "x86_loader": "FUN_39dc1ff0",
            "layout_validated_both": True,
        },
        "authority": "client_native",
        "enabled": {
            "ids": len(enabled_ids),
            "identity_digest": _id_digest(enabled_ids),
            "query_spec_id": query_id,
            "sql": CRAFTS_SQL,
        },
        "guard": {
            "header_offset": int(query_evidence["header_offset"]),
            "physical_rows": CRAFTS_TOTAL_ROWS,
            "sql": str(query_evidence["guard_sql"]),
        },
        "localizations": {
            "ids": len(localization_ids),
            "identity_digest": _id_digest(localization_ids),
            "scope": "localized_texts(crafts.title)",
        },
        "native_references": {
            "ids": len(reference_ids),
            "identity_digest": _id_digest(reference_ids),
            "scope": "dependency_edges.dst_kind=craft",
        },
        "observed_universe": {
            "ids": len(observed_ids),
            "identity_digest": _id_digest(observed_ids),
            "non_enabled_ids": len(non_enabled_ids),
            "non_enabled_identity_digest": _id_digest(non_enabled_ids),
        },
        "partition": {
            "current_disabled_rows": CRAFTS_DISABLED_ROWS,
            "enabled_rows": CRAFTS_ENABLED_ROWS,
            "historical_or_tombstone_identities": CRAFTS_HISTORICAL_ROWS,
            "physical_rows": CRAFTS_TOTAL_ROWS,
            "status": "identity_assignment_underdetermined",
        },
        "result": {
            "end_offset": int(query_evidence["termination_offset"]),
            "filtered_rows": CRAFTS_ENABLED_ROWS,
            "start_offset": int(query_evidence["start_offset"])
            if "start_offset" in query_evidence
            else int(query["start_offset"]),
            "stream": str(query["stream_name"]),
        },
        "rule": (
            "Only the 9,369 filtered identities are individually present. "
            "Exactly 2,246 of the 2,702 observed non-enabled identities are "
            "current disabled rows and exactly 456 are historical, but the "
            "cached client surface does not expose their individual partition."
        ),
    }
    return (
        frozenset(enabled_ids),
        frozenset(reference_ids),
        frozenset(observed_ids),
        evidence,
    )


def reconcile_native_craft_endpoints(
    destination: sqlite3.Connection,
    *,
    enabled_ids: frozenset[int],
    reference_ids: frozenset[int],
    observed_ids: frozenset[int],
    catalog_evidence: dict[str, Any],
    stage: int,
    source_artifact_key: str,
    materialize_observed_universe: bool,
    expected: dict[str, int],
) -> dict[str, Any]:
    """Confirm exact edges and represent the non-enabled partition honestly."""

    if materialize_observed_universe:
        existing = {
            int(row["native_id"])
            for row in destination.execute(
                "SELECT native_id FROM entities WHERE kind='craft'"
            )
            if int(row["native_id"]) > 0
        }
        destination.executemany(
            """
            INSERT INTO entities(
                entity_key,kind,native_id,subtype,lifecycle,state,authority,
                source_stage,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    f"craft:{craft_id}",
                    "craft",
                    str(craft_id),
                    "observed_identity",
                    "unknown",
                    "unknown",
                    "corroborative",
                    stage,
                    PROVENANCE,
                    canonical_json(
                        {
                            "craft_id": craft_id,
                            "materialized_from_observed_union": True,
                        }
                    ),
                )
                for craft_id in sorted(observed_ids - existing)
            ],
        )

    entity_rows = [
        row
        for row in destination.execute(
            """
            SELECT entity_key,native_id,subtype,lifecycle,state,authority,
                   source_stage,provenance,evidence_json
            FROM entities WHERE kind='craft'
            ORDER BY CAST(native_id AS INTEGER),entity_key
            """
        )
        if int(row["native_id"]) > 0
    ]
    stage_ids = {int(row["native_id"]) for row in entity_rows}
    if materialize_observed_universe and stage_ids != set(observed_ids):
        raise RuntimeError("Stage 20 craft universe was not materialized exactly")

    relation_rows = [
        row
        for row in destination.execute(
            """
            SELECT r.relation_key,r.dst_entity_key,r.state,r.authority,
                   r.provenance,r.evidence_json
            FROM relations r
            JOIN entities d ON d.entity_key=r.dst_entity_key
            WHERE d.kind='craft'
              AND CAST(d.native_id AS INTEGER)>0
              AND r.authority IN ('client_native','client_reference')
            ORDER BY r.relation_key
            """
        )
    ]
    relation_endpoint_ids = {
        int(row["dst_entity_key"].split(":", 1)[1]) for row in relation_rows
    }
    counts = Counter(
        "enabled" if craft_id in enabled_ids else "disabled_or_tombstone"
        for craft_id in stage_ids
    )
    observed = {
        "entities": len(stage_ids),
        "enabled": counts["enabled"],
        "disabled_or_tombstone": counts["disabled_or_tombstone"],
        "relations": len(relation_rows),
        "relation_endpoints": len(relation_endpoint_ids),
    }
    for key, value in expected.items():
        if observed.get(key) != value:
            raise RuntimeError(
                f"Stage {stage} craft endpoint {key} changed: "
                f"{observed.get(key)} != {value}"
            )

    entity_updates: list[tuple[Any, ...]] = []
    properties: list[tuple[Any, ...]] = []
    coverage: list[tuple[Any, ...]] = []
    records: list[tuple[Any, ...]] = []
    endpoint_digest = hashlib.sha256()
    for row in entity_rows:
        craft_id = int(row["native_id"])
        classification = (
            "enabled" if craft_id in enabled_ids else "disabled_or_tombstone"
        )
        prior = {
            "authority": str(row["authority"]),
            "evidence": _json_object(str(row["evidence_json"])),
            "lifecycle": str(row["lifecycle"]),
            "provenance": str(row["provenance"]),
            "source_stage": int(row["source_stage"]),
            "state": str(row["state"]),
        }
        endpoint_evidence = {
            "catalog": catalog_evidence,
            "classification": classification,
            "craft_id": craft_id,
            "has_native_reference": craft_id in reference_ids,
            "prior_observation": prior,
        }
        entity_updates.append(
            (
                "present" if classification == "enabled" else classification,
                "confirmed" if classification == "enabled" else "unknown",
                "client_native",
                PROVENANCE,
                canonical_json(endpoint_evidence),
                str(row["entity_key"]),
            )
        )
        properties.append(
            (
                stable_key(
                    "property",
                    row["entity_key"],
                    "client.crafts.identity_constraints",
                    "classification",
                    stage,
                ),
                str(row["entity_key"]),
                "client.crafts.identity_constraints",
                "classification",
                stage,
                "text",
                classification,
                None,
                None,
                None,
                None,
                "confirmed" if classification == "enabled" else "unknown",
                "client_native",
                source_artifact_key,
                f"crafts:identity-constraint:{stage}:{craft_id}",
                CRAFTS_SQL,
                canonical_json(endpoint_evidence),
            )
        )
        for dimension in ("identity", "lifecycle", "incoming_relations"):
            if dimension == "incoming_relations":
                state = (
                    "confirmed"
                    if craft_id in relation_endpoint_ids
                    else "not_applicable"
                )
            else:
                state = (
                    "confirmed" if classification == "enabled" else "unknown"
                )
            coverage.append(
                (
                    stable_key(
                        "coverage",
                        "craft-identity-constraints",
                        stage,
                        craft_id,
                        dimension,
                    ),
                    str(row["entity_key"]),
                    dimension,
                    state,
                    (
                        "Exact enabled identity from filtered native result."
                        if classification == "enabled"
                        else (
                            "Identity is observed, but individual membership "
                            "in disabled versus historical partition is not "
                            "exposed by the cached client result."
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
                    "craft-identity-constraints",
                    stage,
                    craft_id,
                ),
                f"craft_identity_constraints_stage_{stage}",
                str(craft_id),
                canonical_json(endpoint_evidence),
                "client_native",
                PROVENANCE,
            )
        )
        endpoint_digest.update(
            f"{craft_id}:{classification}\n".encode("utf-8")
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

    relation_updates: list[tuple[Any, ...]] = []
    for relation in relation_rows:
        evidence = _json_object(str(relation["evidence_json"]))
        evidence["craft_identity_constraint_resolution"] = {
            "policy": (
                "Exact native edge is confirmed independently from unresolved "
                "disabled-versus-historical destination lifecycle."
            ),
            "stage": stage,
        }
        relation_updates.append(
            (
                "confirmed",
                "client_native",
                canonical_json(evidence),
                str(relation["relation_key"]),
            )
        )
    destination.executemany(
        """
        UPDATE relations SET state=?,authority=?,evidence_json=?
        WHERE relation_key=?
        """,
        relation_updates,
    )

    endpoint_keys = {f"craft:{value}" for value in stage_ids}
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
                    "superseded-craft-endpoint-gap",
                    stage,
                    str(row["gap_key"]),
                ),
                "superseded_craft_endpoint_gaps",
                str(row["gap_key"]),
                canonical_json(
                    {
                        **dict(row),
                        "superseded_by": (
                            f"craft_identity_constraints_stage_{stage}"
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

    if materialize_observed_universe:
        destination.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "stage20:craft-disabled-historical-identity-partition",
                "crafts",
                "game11:134099279..134777928",
                "craft_identity_partition_underdetermined",
                (
                    "The client exposes 11,615 physical rows and 9,369 enabled "
                    "identities, but not the 2,246 disabled identities. The "
                    "observed non-enabled universe contains 2,702 IDs, leaving "
                    "an exact but individually unresolved 2,246/456 split."
                ),
                canonical_json(catalog_evidence),
                stage,
                "opaque",
            ),
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
            f"craft_identity_constraints_stage_{stage}",
            "craft",
            "id",
            "unknown",
            len(stage_ids),
            len(stage_ids),
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
                "craft_identity_constraints_materialized",
            ),
            "stage",
            str(stage),
            "craft_identity_constraints_materialized",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary
