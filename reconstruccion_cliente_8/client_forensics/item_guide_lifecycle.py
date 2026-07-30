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


ITEM_GUIDE_ROWS = 464
ITEM_GUIDE_ID_MIN = 492
ITEM_GUIDE_ID_MAX = 992
ITEM_GUIDE_ID_DIGEST = (
    "E85EEBD554E6B833345617CC370E6850EF47E617E91023D97038A7E766F64A0A"
)
ITEM_GUIDE_ROW_DIGEST = (
    "E18F9B990C49EA17957B4C282E1603994F01D69973B3F1D0F6297D054E49687A"
)
ITEM_GUIDE_CACHED_ROWS_DIGEST = (
    "7061D679512B4806D90389FD724E2CFBB8BABE6AC0F45E32982CE487826E9F7A"
)
ITEM_GUIDE_START = 74_766_590
ITEM_GUIDE_DONE = 74_792_156

ITEM_GUIDE_ELEM_ROWS = 4_459
ITEM_GUIDE_ELEM_ROW_DIGEST = (
    "FF243317895F8C32661E66EEB620743287B6A5BA11F9720F795D6CF5EB0C9802"
)
ITEM_GUIDE_ELEM_CACHED_ROWS_DIGEST = (
    "A42AB53E7824027662000EC847F3620AAEB71645122672CB11FE1DAB9E4413B0"
)
ITEM_GUIDE_ELEM_PAIR_DIGEST = (
    "208D6F0FFE2D65258374768B0E240B6B4852090BD668C0300583B2BD6FCCCE74"
)
ITEM_GUIDE_ELEM_START = 148_249_139
ITEM_GUIDE_ELEM_DONE = 148_329_401

ITEM_GUIDE_ENDPOINTS = 386
ITEM_GUIDE_PRESENT_ENDPOINTS = 383
ITEM_GUIDE_TOMBSTONES = 3
ITEM_GUIDE_TOMBSTONE_IDS = frozenset({488, 490, 491})
ITEM_GUIDE_REFERENCE_DIGEST = (
    "16A80DDB16F2571E5A942AA53729817F40C8E0766C1E388822AAD9B5C569A15C"
)
ITEM_GUIDE_PRESENT_REFERENCE_DIGEST = (
    "C0D74849F9E3B092381A76417AE7FCD5B2AB552DC3DCC3A4C7C3F94DE2E2D398"
)
ITEM_GUIDE_TOMBSTONE_DIGEST = (
    "D079B0F3FAF9186C7217266039EF2C322F044AE99FFC4A2D5968E1C406A8A365"
)
ITEM_GUIDE_UNIVERSE_DIGEST = (
    "A534EF760C6C733A3A5B7B69EA39C9F229A81446A915ECF51E39BCE96467D80E"
)

GHIDRA_X64_SHA256 = (
    "D13DF47D82E2C973532BEB595404C445CFB23B7D4362B6CA70B4B962B4A996FC"
)
GHIDRA_X86_SHA256 = (
    "77C789C6C8F761C5DD41FAAA0C03B381A84F2C2FCE97D39F02ED4EDD6ABE3940"
)
LOADER_TASKS_SHA256 = (
    "0C5784341E49560C21B46DAA786D7C2C5690F956A110DC7910EB84ED6D7AF1DC"
)
PROVENANCE = "aa8-client-forensics:item-guide-lifecycle"

QUERY_SPECS: dict[str, dict[str, Any]] = {
    "item_guide_elems": {
        "sql": (
            "select item_guide_id, item_id, item_guide_a_category_id, "
            "item_guide_b_category_id, show_craft from item_guide_elems "
            "ORDER BY item_guide_id, visible_order"
        ),
        "columns": [
            "item_guide_id",
            "item_id",
            "item_guide_a_category_id",
            "item_guide_b_category_id",
            "show_craft",
        ],
        "layout": ["68", "68", "68", "68", "38"],
        "rows": ITEM_GUIDE_ELEM_ROWS,
        "start": ITEM_GUIDE_ELEM_START,
        "done": ITEM_GUIDE_ELEM_DONE,
        "digest": ITEM_GUIDE_ELEM_ROW_DIGEST,
        "cached_rows_digest": ITEM_GUIDE_ELEM_CACHED_ROWS_DIGEST,
        "x64_loader": "FUN_398f6750",
        "x86_loader": "FUN_39a06820",
        "consumer": "LoadItemGuideElemDescs",
    },
    "item_guides": {
        "sql": (
            "SELECT id, item_guide_impl_id, level, loot_main_category_id, "
            "loot_sub_category_id, name, show, show_order, way_to_loot, "
            "zone_key FROM item_guides"
        ),
        "columns": [
            "id",
            "item_guide_impl_id",
            "level",
            "loot_main_category_id",
            "loot_sub_category_id",
            "name",
            "show",
            "show_order",
            "way_to_loot",
            "zone_key",
        ],
        "layout": ["68", "68", "68", "68", "68", "78", "38", "68", "78", "68"],
        "rows": ITEM_GUIDE_ROWS,
        "start": ITEM_GUIDE_START,
        "done": ITEM_GUIDE_DONE,
        "digest": ITEM_GUIDE_ROW_DIGEST,
        "cached_rows_digest": ITEM_GUIDE_CACHED_ROWS_DIGEST,
        "x64_loader": "FUN_39a3b3f0",
        "x86_loader": "FUN_39d327f0",
        "consumer": "LoadItemGuideDescs",
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


def _guide_id(entity_key: str) -> int | None:
    if not entity_key.startswith("item_guide:"):
        return None
    try:
        return int(entity_key.split(":", 1)[1])
    except ValueError:
        return None


def _validate_ghidra(config: ForensicsConfig) -> dict[str, Any]:
    paths = {
        "x64": config.source_ghidra_item_guide_x64,
        "x86": config.source_ghidra_item_guide_x86,
        "tasks": config.source_item_guide_loader_tasks,
    }
    expected_hashes = {
        "x64": GHIDRA_X64_SHA256,
        "x86": GHIDRA_X86_SHA256,
        "tasks": LOADER_TASKS_SHA256,
    }
    digests = {name: sha256_file(path).upper() for name, path in paths.items()}
    if digests != expected_hashes:
        raise RuntimeError(
            f"item_guide Ghidra evidence changed: {digests}"
        )
    texts = {
        name: path.read_text(encoding="utf-8", errors="replace")
        for name, path in paths.items()
    }
    required = {
        "x64": [
            QUERY_SPECS["item_guides"]["sql"],
            QUERY_SPECS["item_guide_elems"]["sql"],
            "FUNCTION_BEGIN\tFUN_39a3b3f0",
            "FUNCTION_BEGIN\tFUN_398f6750",
            "LoadItemGuideDescs",
            "sqlite3_step",
        ],
        "x86": [
            QUERY_SPECS["item_guides"]["sql"],
            QUERY_SPECS["item_guide_elems"]["sql"],
            "FUNCTION_BEGIN\tFUN_39d327f0",
            "FUNCTION_BEGIN\tFUN_39a06820",
            "LoadItemGuideDescs",
            "sqlite3_step",
        ],
        "tasks": [
            QUERY_SPECS["item_guides"]["sql"],
            QUERY_SPECS["item_guide_elems"]["sql"],
        ],
    }
    missing = {
        name: [token for token in tokens if token not in texts[name]]
        for name, tokens in required.items()
    }
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    if missing:
        raise RuntimeError(f"item_guide Ghidra anchors changed: {missing}")
    return {
        "hashes": digests,
        "paths": {name: path.resolve().as_posix() for name, path in paths.items()},
        "x86_x64_layout_parity": True,
        "sqlite_done_guard_confirmed": True,
    }


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
    cached_digest = hashlib.sha256(
        canonical_json(rows).encode("utf-8")
    ).hexdigest().upper()
    checks = {
        "columns": json.loads(str(query["columns_json"])) == expected["columns"],
        "layout": json.loads(str(query["layout_json"])) == expected["layout"],
        "query_start": int(query["start_offset"]) == expected["start"],
        "expected_rows": int(query["expected_rows"]) == expected["rows"],
        "result_status": str(result["status"]).startswith("confirmed"),
        "result_start": int(result["start_offset"]) == expected["start"],
        "result_done": int(result["end_offset"]) == expected["done"],
        "result_rows": int(result["row_count"]) == expected["rows"],
        "decoded_rows": len(rows) == expected["rows"],
        "stored_digest": str(result["row_digest"]).upper() == expected["digest"],
        "cached_rows_digest": cached_digest == expected["cached_rows_digest"],
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
        "layout": str(registry_spec["layout"]).split() == expected["layout"],
        "x64_loader": str(registry_spec["loader"]).lower()
        == str(expected["x64_loader"]).lower().removeprefix("fun_"),
        "start": int(registry_spec["start"]) == expected["start"],
        "rows": int(registry_spec["rows"]) == expected["rows"],
        "status": str(registry_spec["status"]) == "confirmed_native_result",
    }
    if not all(registry_checks.values()):
        raise RuntimeError(
            f"Native {table} registry evidence changed: {registry_checks}"
        )
    return query, result, rows


def native_item_guide_evidence(
    source: sqlite3.Connection,
    config: ForensicsConfig,
) -> tuple[frozenset[int], dict[str, Any]]:
    query_data = {
        table: _source_query(source, table) for table in sorted(QUERY_SPECS)
    }
    guide_query, guide_result, guide_rows = query_data["item_guides"]
    elem_query, elem_result, elem_rows = query_data["item_guide_elems"]
    active_ids = frozenset(int(row["id"]) for row in guide_rows)
    referenced_ids = frozenset(
        int(row["item_guide_id"])
        for row in elem_rows
        if int(row["item_guide_id"]) > 0
    )
    present_ids = active_ids & referenced_ids
    tombstones = referenced_ids - active_ids
    universe = active_ids | referenced_ids
    pairs = {
        (int(row["item_id"]), int(row["item_guide_id"]))
        for row in elem_rows
        if int(row["item_id"]) > 0 and int(row["item_guide_id"]) > 0
    }
    pair_digest = hashlib.sha256(
        b"".join(struct.pack("<II", *pair) for pair in sorted(pairs))
    ).hexdigest().upper()
    checks = {
        "active_count": len(active_ids) == ITEM_GUIDE_ROWS,
        "active_min": min(active_ids) == ITEM_GUIDE_ID_MIN,
        "active_max": max(active_ids) == ITEM_GUIDE_ID_MAX,
        "active_digest": _id_digest(active_ids) == ITEM_GUIDE_ID_DIGEST,
        "relation_rows": len(elem_rows) == ITEM_GUIDE_ELEM_ROWS,
        "relation_pairs": len(pairs) == ITEM_GUIDE_ELEM_ROWS,
        "relation_pair_digest": pair_digest == ITEM_GUIDE_ELEM_PAIR_DIGEST,
        "endpoints": len(referenced_ids) == ITEM_GUIDE_ENDPOINTS,
        "endpoint_digest": _id_digest(referenced_ids)
        == ITEM_GUIDE_REFERENCE_DIGEST,
        "present_endpoints": len(present_ids) == ITEM_GUIDE_PRESENT_ENDPOINTS,
        "present_digest": _id_digest(present_ids)
        == ITEM_GUIDE_PRESENT_REFERENCE_DIGEST,
        "tombstones": tombstones == ITEM_GUIDE_TOMBSTONE_IDS,
        "tombstone_digest": _id_digest(tombstones)
        == ITEM_GUIDE_TOMBSTONE_DIGEST,
        "universe": len(universe) == ITEM_GUIDE_ROWS + ITEM_GUIDE_TOMBSTONES,
        "universe_digest": _id_digest(universe) == ITEM_GUIDE_UNIVERSE_DIGEST,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Native item_guide identity changed: {checks}")
    ghidra = _validate_ghidra(config)
    queries: dict[str, Any] = {}
    for table, (query, result, _rows) in query_data.items():
        expected = QUERY_SPECS[table]
        queries[table] = {
            "cached_rows_digest": expected["cached_rows_digest"],
            "columns": expected["columns"],
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
            "x64_loader": expected["x64_loader"],
            "x86_loader": expected["x86_loader"],
            "x86_x64_layout_parity": True,
        }
    return active_ids, {
        "active_identity_digest": _id_digest(active_ids),
        "authority": "Kakao 8.0.3.12 r558734 game11 + x2game.dll",
        "checks": checks,
        "frontier": {
            "active_without_incoming": len(active_ids - referenced_ids),
            "endpoint_digest": _id_digest(referenced_ids),
            "endpoints": len(referenced_ids),
            "pair_digest": pair_digest,
            "present_digest": _id_digest(present_ids),
            "present_endpoints": len(present_ids),
            "relations": len(pairs),
            "tombstone_digest": _id_digest(tombstones),
            "tombstone_ids": sorted(tombstones),
            "tombstones": len(tombstones),
            "universe": len(universe),
            "universe_digest": _id_digest(universe),
        },
        "ghidra": ghidra,
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


def reconcile_item_guide_query_registry(
    destination: sqlite3.Connection,
    source: sqlite3.Connection,
    config: ForensicsConfig,
) -> dict[str, Any]:
    active_ids, evidence = native_item_guide_evidence(source, config)
    artifact_specs = (
        (
            "stage10:ghidra-item-guide-x64",
            "ghidra_item_guide_loaders_x64",
            config.source_ghidra_item_guide_x64,
            GHIDRA_X64_SHA256,
        ),
        (
            "stage10:ghidra-item-guide-x86",
            "ghidra_item_guide_loaders_x86",
            config.source_ghidra_item_guide_x86,
            GHIDRA_X86_SHA256,
        ),
        (
            "stage10:item-guide-loader-tasks",
            "item_guide_loader_tasks",
            config.source_item_guide_loader_tasks,
            LOADER_TASKS_SHA256,
        ),
    )
    destination.executemany(
        """
        INSERT INTO artifacts(
            artifact_key,source_stage,role,path,bytes,sha256,build,authority,
            state,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                key,
                10,
                role,
                path.resolve().as_posix(),
                path.stat().st_size,
                digest,
                config.client_build,
                "client_native",
                "confirmed",
                PROVENANCE,
                canonical_json(
                    {"item_guide_loader_recovery": True, "architecture": role}
                ),
            )
            for key, role, path, digest in artifact_specs
        ],
    )
    for table in sorted(QUERY_SPECS):
        query_evidence = evidence["queries"][table]
        query_key = (
            f"legacy:item-forensics:query:{query_evidence['query_spec_id']}"
        )
        query_row = destination.execute(
            "SELECT evidence_json FROM query_specs WHERE query_key=?",
            (query_key,),
        ).fetchone()
        if query_row is None:
            raise RuntimeError(f"Imported query is absent: {query_key}")
        merged = _json_object(query_row["evidence_json"])
        merged["item_guide_registry_resolution"] = query_evidence
        destination.execute(
            """
            UPDATE query_specs
            SET state='confirmed',loader_consumer=?,evidence_json=?
            WHERE query_key=?
            """,
            (
                QUERY_SPECS[table]["consumer"],
                canonical_json(merged),
                query_key,
            ),
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
                f"Expected one imported consumer for {table}, got {len(consumers)}"
            )
        consumer_evidence = _json_object(consumers[0]["evidence_json"])
        consumer_evidence["item_guide_registry_resolution"] = {
            "architecture": "x64",
            **query_evidence,
        }
        destination.execute(
            """
            UPDATE consumers
            SET name=?,module='x2game.dll',locator=?,architecture='x64',
                state='confirmed',evidence_json=?
            WHERE consumer_key=?
            """,
            (
                QUERY_SPECS[table]["consumer"],
                query_evidence["x64_loader"],
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
                        "artifact_key": "stage10:ghidra-item-guide-x86",
                        "item_guide_registry_resolution": query_evidence,
                    }
                ),
            ),
        )
        destination.execute(
            """
            INSERT INTO source_records(
                source_record_key,source_table,source_pk,record_json,
                authority,provenance
            ) VALUES(?,?,?,?,?,?)
            """,
            (
                stable_key("source-record", "item-guide-query-registry", table),
                "item_guide_query_registry",
                table,
                canonical_json(query_evidence),
                "client_native",
                PROVENANCE,
            ),
        )
        catalog = destination.execute(
            """
            SELECT evidence_json FROM native_catalogs
            WHERE table_name=?
            """,
            (table,),
        ).fetchone()
        if catalog is None:
            raise RuntimeError(f"Imported {table} catalog is absent")
        catalog_evidence = _json_object(catalog["evidence_json"])
        catalog_evidence["query_registry_resolution"] = evidence
        destination.execute(
            """
            UPDATE native_catalogs
            SET state='confirmed',row_count=?,distinct_ids=?,provenance=?,
                evidence_json=?
            WHERE table_name=?
            """,
            (
                QUERY_SPECS[table]["rows"],
                (
                    ITEM_GUIDE_ROWS
                    if table == "item_guides"
                    else ITEM_GUIDE_ENDPOINTS
                ),
                PROVENANCE,
                canonical_json(catalog_evidence),
                table,
            ),
        )
    summary = {
        "active_ids": len(active_ids),
        "artifacts": len(artifact_specs),
        "inserted_x86_consumers": len(QUERY_SPECS),
        "query_tables": sorted(QUERY_SPECS),
        "updated_consumers": len(QUERY_SPECS),
        "updated_queries": len(QUERY_SPECS),
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
                "validation", "stage", 10, "item_guide_query_registry_reconciled"
            ),
            "stage",
            "10",
            "item_guide_query_registry_reconciled",
            "confirmed",
            canonical_json({**summary, "native_evidence": evidence}),
        ),
    )
    return summary


def reconcile_native_item_guide_endpoints(
    destination: sqlite3.Connection,
    *,
    active_ids: frozenset[int],
    catalog_evidence: dict[str, Any],
    stage: int,
    source_artifact_key: str,
    expected: dict[str, int],
) -> dict[str, Any]:
    relation_rows = destination.execute(
        """
        SELECT r.relation_key,r.src_entity_key,r.dst_entity_key,r.state,
               r.authority,r.evidence_json
        FROM relations r
        JOIN entities d ON d.entity_key=r.dst_entity_key
        WHERE d.kind='item_guide'
          AND r.relation='listed_in_item_guide'
          AND r.authority IN ('client_native','client_reference')
        ORDER BY r.relation_key
        """
    ).fetchall()
    endpoints: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in relation_rows:
        guide_id = _guide_id(str(row["dst_entity_key"]))
        if guide_id is not None and guide_id > 0:
            endpoints[guide_id].append(row)
    universe = active_ids | frozenset(endpoints)
    classifications = {
        guide_id: ("present" if guide_id in active_ids else "tombstone")
        for guide_id in sorted(universe)
    }
    counts = Counter(classifications.values())
    observed = {
        "active": counts["present"],
        "active_without_incoming": len(active_ids - frozenset(endpoints)),
        "endpoints": len(endpoints),
        "present_endpoints": len(frozenset(endpoints) & active_ids),
        "relations": len(relation_rows),
        "tombstones": counts["tombstone"],
        "universe": len(universe),
    }
    for name, value in expected.items():
        if observed.get(name) != value:
            raise RuntimeError(
                f"Stage {stage} item_guide {name} changed: "
                f"{observed.get(name)} != {value}"
            )
    entities = {
        str(row["entity_key"]): row
        for row in destination.execute(
            """
            SELECT entity_key,subtype,lifecycle,state,authority,source_stage,
                   provenance,evidence_json
            FROM entities WHERE kind='item_guide'
            """
        )
    }
    entity_updates: list[tuple[Any, ...]] = []
    relation_updates: list[tuple[Any, ...]] = []
    properties: list[tuple[Any, ...]] = []
    coverage: list[tuple[Any, ...]] = []
    records: list[tuple[Any, ...]] = []
    lifecycle_digest = hashlib.sha256()
    for guide_id, classification in sorted(classifications.items()):
        key = f"item_guide:{guide_id}"
        prior = entities.get(key)
        if prior is None:
            raise RuntimeError(f"Native item_guide universe endpoint absent: {key}")
        rows = endpoints.get(guide_id, [])
        evidence = {
            "catalog": catalog_evidence,
            "classification": classification,
            "guide_id": guide_id,
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
                "positive ID present in complete unfiltered item_guides result"
                if classification == "present"
                else (
                    "positive ID referenced by item_guide_elems and absent "
                    "from the complete unfiltered item_guides result"
                )
            ),
        }
        entity_updates.append(
            (
                (
                    "item_guides"
                    if classification == "present"
                    else "item_guide_elems_reference"
                ),
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
                    "client.item_guides.endpoint_lifecycle",
                    "classification",
                    stage,
                ),
                key,
                "client.item_guides.endpoint_lifecycle",
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
                f"item_guides-complete:endpoint:{stage}:{guide_id}",
                "LoadItemGuideDescs",
                canonical_json(evidence),
            )
        )
        for dimension in ("identity", "lifecycle", "incoming_relations"):
            if dimension == "incoming_relations" and not rows:
                coverage_state = "not_applicable"
                capability = (
                    "Native item_guide owner is complete and has no "
                    "item_guide_elems rows in this client."
                )
            elif classification == "tombstone" and dimension != "incoming_relations":
                coverage_state = "tombstone"
                capability = (
                    "Exact native references survive, but the owner identity "
                    "is absent from the complete item_guides result."
                )
            else:
                coverage_state = "confirmed"
                capability = (
                    "Native item_guide identity or exact incoming edges are "
                    "closed by complete cached results."
                )
            coverage.append(
                (
                    stable_key(
                        "coverage",
                        "item-guide-endpoint-lifecycle",
                        stage,
                        guide_id,
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
                    "item-guide-endpoint-lifecycle",
                    stage,
                    guide_id,
                ),
                f"item_guide_endpoint_lifecycle_stage_{stage}",
                str(guide_id),
                canonical_json(evidence),
                "client_native",
                PROVENANCE,
            )
        )
        lifecycle_digest.update(
            f"{guide_id}:{classification}:{len(rows)}\n".encode()
        )
        for relation in rows:
            relation_evidence = _json_object(relation["evidence_json"])
            relation_evidence["endpoint_lifecycle_resolution"] = {
                "catalog_identity_digest": catalog_evidence[
                    "active_identity_digest"
                ],
                "classification": classification,
                "guide_id": guide_id,
                "original_authority": str(relation["authority"]),
                "original_state": str(relation["state"]),
                "policy": (
                    "exact native edge remains confirmed independently from "
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
    }
    destination.execute(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            f"item_guide_endpoint_lifecycle_stage_{stage}",
            "item_guide",
            "id",
            "confirmed",
            observed["relations"],
            observed["universe"],
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
                "item_guide_endpoint_lifecycle_closed",
            ),
            "stage",
            str(stage),
            "item_guide_endpoint_lifecycle_closed",
            "confirmed",
            canonical_json(summary),
        ),
    )
    return summary
