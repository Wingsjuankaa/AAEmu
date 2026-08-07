from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from . import SCHEMA_VERSION, TOOL_NAME, TOOL_VERSION
from .config import ForensicsConfig
from .closure_frontier import LOOT_QUERIES, insert_loot_closure_frontier
from .item_grade_secondary import (
    ITEM_GRADE_SECONDARY_SPECS,
    audit_item_grade_secondary,
)
from .item_endpoint_lifecycle import (
    ITEMS_POSITIVE_IDS,
    reconcile_native_item_endpoints,
)
from .buff_endpoint_lifecycle import reconcile_native_buff_endpoints
from .craft_identity import (
    CRAFTS_ENABLED_ROWS,
    CRAFTS_NON_ENABLED_OBSERVED_IDS,
    CRAFTS_OBSERVED_IDS,
    native_craft_identity_constraints,
    reconcile_native_craft_endpoints,
)
from .craft_pack_lifecycle import (
    CRAFT_PACK_FRONTIER_RELATIONS,
    CRAFT_PACK_ROWS,
    CRAFT_PACK_TOMBSTONES,
    native_craft_pack_evidence,
    reconcile_craft_pack_query_registry,
    reconcile_native_craft_pack_endpoints,
)
from .item_guide_lifecycle import (
    ITEM_GUIDE_ELEM_ROWS,
    ITEM_GUIDE_ROWS,
    ITEM_GUIDE_TOMBSTONES,
    native_item_guide_evidence,
    reconcile_item_guide_query_registry,
    reconcile_native_item_guide_endpoints,
)
from .tag_lifecycle import (
    TAG_RELATIONS,
    TAG_ROWS,
    TAG_TOMBSTONES,
    native_tag_evidence,
    reconcile_native_tag_endpoints,
    reconcile_tag_query_registry,
    reconcile_tag_stage50_result,
)
from .npc_groups import (
    NPC_GROUP_REFERENCED_TOMBSTONES,
    NPC_GROUP_ROWS,
    materialize_native_npc_group_catalog,
    native_npc_group_identity_catalog,
    reconcile_native_npc_group_endpoints,
)
from .npc_endpoint_lifecycle import (
    NPCS_NATIVE_ROWS,
    NPCS_REFERENCED_TOMBSTONES,
    native_npc_identity_catalog,
    reconcile_native_npc_endpoints,
)
from .skill_endpoint_lifecycle import reconcile_native_skill_endpoints
from .skills import (
    BUFFS_NATIVE_ROWS,
    BUFFS_REFERENCED_TOMBSTONES,
    SKILLS_NATIVE_ROWS,
    SKILLS_REFERENCED_TOMBSTONES,
    native_buff_identity_catalog,
    native_skill_identity_catalog,
)
from .reporting import generate_static_viewer
from .schema import create_database, open_read_only, set_metadata, table_count
from .stage40 import populate_stage_40
from .stage50 import populate_stage_50
from .stage90 import populate_stage_90
from .assets60 import populate_stage_60
from .wiki70 import populate_stage_70
from .util import (
    atomic_text,
    canonical_json,
    canonicalize_json_text,
    entity_key,
    sha256_file,
    stable_key,
    tree_digest,
    typed_value,
)
from .world_actors import (
    ABSENT_APPEARANCE_SPECS,
    APPEARANCE_AUXILIARY_SPECS,
    APPEARANCE_SPECS,
    audit_absent_appearance_results,
    decode_appearance,
    decode_appearance_auxiliary,
    decode_catalog,
    decode_signed_modifier,
    face_profile_key_from_model_file,
    load_face_target_profiles,
    load_json,
    unresolved_reference,
)


SOURCE_ARTIFACT_KEY = "source:item-forensics-database"
SOURCE_MANIFEST_KEY = "source:item-forensics-manifest"
SOURCE_TOOL_KEY = "source:item-forensics-tool-tree"
ITEM_GRADE_ORDER_SQL = (
    "SELECT id FROM item_grades ORDER BY grade_order ASC"
)
ITEM_GRADE_DESCRIPTOR_SQL = (
    "SELECT id, color_argb, durability_value, grade_order, icon_id, name, "
    "refund_multiplier, stat_multiplier, upgrade_ratio, "
    "var_holdable_armor, var_holdable_dps, var_holdable_heal_dps, "
    "var_holdable_magic_dps, var_holdable_magic_resist, "
    "var_wearable_armor, var_wearable_magic_resistance FROM item_grades"
)


@dataclass(frozen=True)
class BuildContext:
    config: ForensicsConfig
    source_database_sha256: str
    source_manifest_sha256: str
    source_tool_sha256: str

    @classmethod
    def create(cls, config: ForensicsConfig) -> "BuildContext":
        config.validate()
        return cls(
            config=config,
            source_database_sha256=sha256_file(config.source_item_database),
            source_manifest_sha256=sha256_file(config.source_item_manifest),
            source_tool_sha256=tree_digest(config.source_item_tool_root),
        )


def _source(config: ForensicsConfig) -> sqlite3.Connection:
    return open_read_only(config.source_item_database)


def _canonical_state(value: Any) -> str:
    state = str(value or "unknown").strip().lower()
    if state.startswith("confirmed") or state in {"present", "enabled", "disabled"}:
        return "confirmed"
    if state in {"missing", "tombstone", "blocked", "unknown", "not_applicable", "opaque"}:
        return state
    if state in {"partial", "corroborated"}:
        return "corroborated"
    if state in {
        "native_result_absent",
        "layout_missing",
        "decode_failed",
        "unresolved_reference",
    }:
        return "blocked"
    if state in {"mode_excluded"}:
        return "not_applicable"
    return "unknown"


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {"opaque_text": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _row_payload(
    row: sqlite3.Row,
    *,
    json_columns: Iterable[str] = (),
) -> dict[str, Any]:
    payload = dict(row)
    for column in json_columns:
        if column in payload:
            payload[column] = _json_object(payload[column])
    return payload


def _artifact_key(source_artifact_id: int) -> str:
    return f"legacy:item-forensics:artifact:{source_artifact_id}"


def _query_key(source_query_spec_id: int) -> str:
    return f"legacy:item-forensics:query:{source_query_spec_id}"


def _copy_artifacts(
    destination: sqlite3.Connection,
    source: sqlite3.Connection,
    context: BuildContext,
    stage: int,
) -> int:
    rows = []
    for row in source.execute("SELECT * FROM artifacts ORDER BY artifact_id"):
        rows.append(
            (
                _artifact_key(int(row["artifact_id"])),
                stage,
                str(row["role"]),
                str(row["path"]),
                int(row["bytes"]),
                str(row["sha256"]).upper() if row["sha256"] else None,
                context.config.client_build,
                "client_native"
                if str(row["role"]) != "runtime_compact"
                else "server_observed",
                "confirmed" if row["sha256"] else "unknown",
                str(row["provenance"]),
                canonical_json({"source_artifact_id": int(row["artifact_id"])}),
            )
        )
    rows.extend(
        [
            (
                SOURCE_ARTIFACT_KEY,
                stage,
                "import_source_database",
                context.config.source_item_database.resolve().as_posix(),
                context.config.source_item_database.stat().st_size,
                context.source_database_sha256,
                context.config.client_build,
                "derived_forensic",
                "confirmed",
                "aa8_item_forensics_baseline",
                canonical_json({"immutable_import": True}),
            ),
            (
                SOURCE_MANIFEST_KEY,
                stage,
                "import_source_manifest",
                context.config.source_item_manifest.resolve().as_posix(),
                context.config.source_item_manifest.stat().st_size,
                context.source_manifest_sha256,
                context.config.client_build,
                "derived_forensic",
                "confirmed",
                "aa8_item_forensics_baseline",
                canonical_json({"immutable_import": True}),
            ),
            (
                SOURCE_TOOL_KEY,
                stage,
                "import_source_tool_tree",
                context.config.source_item_tool_root.resolve().as_posix(),
                0,
                context.source_tool_sha256,
                context.config.client_build,
                "derived_forensic",
                "corroborated",
                "current_item_forensics_source_bundle",
                canonical_json(
                    {
                        "digest_scope": ["*.py", "*.json"],
                        "baseline_database_records_tool_version": True,
                    }
                ),
            ),
        ]
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


def _insert_entity(
    connection: sqlite3.Connection,
    *,
    key: str,
    kind: str,
    native_id: Any,
    subtype: str | None,
    lifecycle: str,
    state: str,
    authority: str,
    stage: int,
    provenance: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO entities(
            entity_key,kind,native_id,subtype,lifecycle,state,authority,
            source_stage,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        (
            key,
            kind,
            str(native_id),
            subtype,
            lifecycle,
            state,
            authority,
            stage,
            provenance,
            canonical_json(evidence),
        ),
    )


def _property_tuple(
    *,
    owner: str,
    namespace: str,
    name: str,
    value: Any,
    locator: str,
    state: str = "confirmed",
    authority: str = "client_native",
    consumer: str | None = None,
    source_artifact_key: str = SOURCE_ARTIFACT_KEY,
    evidence: dict[str, Any] | None = None,
) -> tuple[Any, ...]:
    value_type, text, integer, real, boolean, json_value = typed_value(value)
    return (
        stable_key("property", owner, namespace, name, 0, locator),
        owner,
        namespace,
        name,
        0,
        value_type,
        text,
        integer,
        real,
        boolean,
        json_value,
        state,
        authority,
        source_artifact_key,
        locator,
        consumer,
        canonical_json(evidence or {}),
    )


PROPERTY_INSERT = """
INSERT OR IGNORE INTO entity_properties(
    property_key,entity_key,namespace,property_name,ordinal,value_type,
    value_text,value_integer,value_real,value_boolean,value_json,state,
    authority,source_artifact_key,locator,consumer,evidence_json
) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""


def _insert_source_record(
    connection: sqlite3.Connection,
    *,
    table: str,
    source_pk: str,
    payload: dict[str, Any],
    authority: str,
) -> None:
    connection.execute(
        """
        INSERT INTO source_records(
            source_record_key,source_table,source_pk,record_json,authority,provenance
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            f"legacy:item-forensics:{table}:{source_pk}",
            table,
            source_pk,
            canonical_json(payload),
            authority,
            "aa8-item-forensics",
        ),
    )


def _source_count(source: sqlite3.Connection, table: str) -> int:
    exists = source.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if exists is None:
        raise RuntimeError(f"Required source table is missing: {table}")
    return table_count(source, table)


def _record_counts(
    connection: sqlite3.Connection,
    source: sqlite3.Connection,
    mappings: dict[str, tuple[str, int]],
) -> None:
    for source_table, (destination_table, imported_count) in sorted(mappings.items()):
        expected = _source_count(source, source_table)
        if expected != imported_count:
            raise RuntimeError(
                f"Silent row loss in {source_table}: expected={expected} "
                f"imported={imported_count}"
            )
        set_metadata(
            connection,
            {
                f"source_count.{source_table}": expected,
                f"import_count.{destination_table}": imported_count,
            },
        )
        _add_validation(
            connection,
            scope_kind="source_table",
            scope_id=source_table,
            check_name="row_count_preserved",
            status="confirmed",
            evidence={
                "source_rows": expected,
                "destination_table": destination_table,
                "imported_rows": imported_count,
            },
        )


def _add_validation(
    connection: sqlite3.Connection,
    *,
    scope_kind: str,
    scope_id: str,
    check_name: str,
    status: str,
    evidence: dict[str, Any],
) -> None:
    key = stable_key("validation", scope_kind, scope_id, check_name)
    connection.execute(
        """
        INSERT OR REPLACE INTO validation_events(
            validation_key,scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            key,
            scope_kind,
            scope_id,
            check_name,
            status,
            canonical_json(evidence),
        ),
    )


def _initialize(
    connection: sqlite3.Connection,
    context: BuildContext,
    *,
    stage: int,
    classification: str,
) -> None:
    set_metadata(
        connection,
        {
            "authority": "client_forensics_only",
            "classification": classification,
            "client_build": context.config.client_build,
            "historical_3_0_gameplay_rows": 0,
            "schema_version": SCHEMA_VERSION,
            "source_item_database_sha256": context.source_database_sha256,
            "source_item_manifest_sha256": context.source_manifest_sha256,
            "source_item_tool_sha256": context.source_tool_sha256,
            "stage": stage,
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        },
    )


def _finalize(connection: sqlite3.Connection, scope_id: str) -> dict[str, str]:
    connection.commit()
    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    _add_validation(
        connection,
        scope_kind="database",
        scope_id=scope_id,
        check_name="quick_check",
        status="confirmed" if quick == "ok" else "blocked",
        evidence={"result": quick},
    )
    _add_validation(
        connection,
        scope_kind="database",
        scope_id=scope_id,
        check_name="integrity_check",
        status="confirmed" if integrity == "ok" else "blocked",
        evidence={"result": integrity},
    )
    connection.commit()
    connection.execute("VACUUM")
    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite validation failed: quick={quick} integrity={integrity}")
    return {"quick_check": quick, "integrity_check": integrity}


def _database_counts(path: Path) -> dict[str, int]:
    connection = open_read_only(path)
    try:
        tables = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        return {table: table_count(connection, table) for table in tables}
    finally:
        connection.close()


def _write_stage_manifest(
    context: BuildContext,
    *,
    stage: int,
    classification: str,
    database: Path,
    validation: dict[str, str],
) -> dict[str, Any]:
    manifest = {
        "authority": "client_forensics_only",
        "classification": classification,
        "client_build": context.config.client_build,
        "database": {
            "bytes": database.stat().st_size,
            "path": database.resolve().as_posix(),
            "sha256": sha256_file(database),
        },
        "determinism": {
            "immutable_after_build": True,
            "stable_ordering": True,
            "timestamps_in_reproducible_artifacts": False,
        },
        "input": {
            "item_database": {
                "path": context.config.source_item_database.resolve().as_posix(),
                "sha256": context.source_database_sha256,
            },
            "item_manifest": {
                "path": context.config.source_item_manifest.resolve().as_posix(),
                "sha256": context.source_manifest_sha256,
            },
            "item_tool_tree_sha256": context.source_tool_sha256,
        },
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "table_counts": _database_counts(database),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "validation": validation,
    }
    manifest_path = database.with_suffix(".manifest.json")
    atomic_text(manifest_path, canonical_json(manifest, pretty=True))
    manifest["manifest"] = {
        "path": manifest_path.resolve().as_posix(),
        "sha256": sha256_file(manifest_path),
    }
    return manifest


def _atomic_build(
    context: BuildContext,
    target: Path,
    *,
    stage: int,
    classification: str,
    populate: Callable[[sqlite3.Connection, sqlite3.Connection], None],
) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        prefix=f".{target.stem}.",
        suffix=".sqlite",
        dir=target.parent,
    )
    os.close(handle)
    temporary = Path(name)
    temporary.unlink(missing_ok=True)
    source = _source(context.config)
    connection: sqlite3.Connection | None = None
    try:
        connection = create_database(temporary)
        _initialize(
            connection,
            context,
            stage=stage,
            classification=classification,
        )
        populate(connection, source)
        validation = _finalize(connection, target.name)
        connection.close()
        connection = None
        source.close()
        temporary.replace(target)
        return _write_stage_manifest(
            context,
            stage=stage,
            classification=classification,
            database=target,
            validation=validation,
        )
    except Exception:
        if connection is not None:
            connection.close()
        source.close()
        temporary.unlink(missing_ok=True)
        raise


def build_stage_00(context: BuildContext) -> dict[str, Any]:
    def populate(destination: sqlite3.Connection, source: sqlite3.Connection) -> None:
        legacy_artifact_count = _copy_artifacts(destination, source, context, 0) - 3

        surface_count = 0
        property_rows: list[tuple[Any, ...]] = []
        for row in source.execute(
            "SELECT * FROM client_surfaces ORDER BY surface_id"
        ):
            source_id = int(row["surface_id"])
            key = entity_key("surface", source_id)
            evidence = canonicalize_json_text(row["evidence_json"])
            destination.execute(
                """
                INSERT INTO surfaces(
                    surface_key,source_stage,source_kind,locator,extension,
                    bytes,sha256,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    key,
                    0,
                    row["source_kind"],
                    row["path"],
                    row["extension"],
                    row["bytes"],
                    row["sha256"],
                    _canonical_state(row["status"]),
                    evidence,
                ),
            )
            _insert_entity(
                destination,
                key=key,
                kind="surface",
                native_id=source_id,
                subtype=str(row["source_kind"]),
                lifecycle="present",
                state=_canonical_state(row["status"]),
                authority="client_native",
                stage=0,
                provenance="client_surface_inventory",
                evidence={"path": row["path"]},
            )
            for name in ("source_kind", "path", "extension", "bytes", "sha256"):
                property_rows.append(
                    _property_tuple(
                        owner=key,
                        namespace="surface",
                        name=name,
                        value=row[name],
                        locator=f"client_surfaces:{source_id}:{name}",
                    )
                )
            if len(property_rows) >= 5000:
                destination.executemany(PROPERTY_INSERT, property_rows)
                property_rows.clear()
            surface_count += 1
        if property_rows:
            destination.executemany(PROPERTY_INSERT, property_rows)

        inventory_rows = [
            (
                row["source_kind"],
                row["extension"],
                row["file_count"],
                row["total_bytes"],
                canonicalize_json_text(row["evidence_json"]),
            )
            for row in source.execute(
                "SELECT * FROM surface_inventory ORDER BY source_kind,extension"
            )
        ]
        destination.executemany(
            """
            INSERT INTO surface_inventory(
                source_kind,extension,file_count,total_bytes,evidence_json
            ) VALUES(?,?,?,?,?)
            """,
            inventory_rows,
        )

        review_rows = [
            (
                f"legacy:item-forensics:review-manifest:{row['review_manifest_id']}",
                row["path"],
                row["sha256"],
                row["authority"] or "unknown",
                canonicalize_json_text(row["classification_json"]),
                canonicalize_json_text(row["summary_json"]),
            )
            for row in source.execute(
                "SELECT * FROM review_manifests ORDER BY review_manifest_id"
            )
        ]
        destination.executemany(
            """
            INSERT INTO review_manifests(
                review_manifest_key,path,sha256,authority,
                classification_json,summary_json
            ) VALUES(?,?,?,?,?,?)
            """,
            review_rows,
        )

        for row in source.execute("SELECT key,value FROM metadata ORDER BY key"):
            _insert_source_record(
                destination,
                table="metadata",
                source_pk=str(row["key"]),
                payload=dict(row),
                authority="derived_forensic",
            )

        legacy_validations = 0
        for row in source.execute(
            "SELECT * FROM validation_events ORDER BY validation_id"
        ):
            destination.execute(
                """
                INSERT INTO validation_events(
                    validation_key,scope_kind,scope_id,check_name,status,evidence_json
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    f"legacy:item-forensics:validation:{row['validation_id']}",
                    row["scope_kind"],
                    row["scope_id"],
                    row["check_name"],
                    _canonical_state(row["status"]),
                    canonicalize_json_text(row["evidence_json"]),
                ),
            )
            legacy_validations += 1

        _record_counts(
            destination,
            source,
            {
                "artifacts": ("artifacts:legacy", legacy_artifact_count),
                "client_surfaces": ("surfaces", surface_count),
                "surface_inventory": ("surface_inventory", len(inventory_rows)),
                "review_manifests": ("review_manifests", len(review_rows)),
                "metadata": ("source_records:metadata", _source_count(source, "metadata")),
                "validation_events": (
                    "validation_events:legacy",
                    legacy_validations,
                ),
            },
        )

    return _atomic_build(
        context,
        context.config.stage_00,
        stage=0,
        classification="stage_00_artifacts_and_surfaces",
        populate=populate,
    )


def build_stage_10(context: BuildContext) -> dict[str, Any]:
    def populate(destination: sqlite3.Connection, source: sqlite3.Connection) -> None:
        legacy_artifact_count = _copy_artifacts(destination, source, context, 10) - 3
        source_metadata = {
            str(row["key"]): str(row["value"])
            for row in source.execute("SELECT key,value FROM metadata ORDER BY key")
        }
        destination.executemany(
            """
            INSERT INTO decoders(
                decoder_key,name,version,sha256,status,inputs_json,
                assumptions_json,provenance
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            [
                (
                    "decoder:aa8-item-forensics",
                    source_metadata.get("tool_name", "aa8-item-forensics"),
                    source_metadata.get("tool_version", "unknown"),
                    context.source_tool_sha256,
                    "corroborated",
                    canonical_json(
                        {
                            "database_sha256": context.source_database_sha256,
                            "query_registry_digest": source_metadata.get(
                                "query_registry_digest"
                            ),
                        }
                    ),
                    canonical_json(
                        {
                            "source_bundle_is_current_workspace_state": True,
                            "database_metadata_is_authoritative_for_version": True,
                        }
                    ),
                    "legacy_item_forensics_import",
                ),
                (
                    f"decoder:{TOOL_NAME}",
                    TOOL_NAME,
                    TOOL_VERSION,
                    tree_digest(Path(__file__).resolve().parent),
                    "confirmed",
                    canonical_json(
                        {
                            "source_database_sha256": context.source_database_sha256
                        }
                    ),
                    canonical_json({"semantic_migration_only": True}),
                    "transversal_importer",
                ),
            ],
        )

        query_count = 0
        for row in source.execute("SELECT * FROM query_specs ORDER BY query_spec_id"):
            destination.execute(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    _query_key(int(row["query_spec_id"])),
                    row["query_spec_id"],
                    row["table_name"],
                    row["source_module"],
                    row["sql_text"],
                    canonicalize_json_text(row["columns_json"]),
                    canonicalize_json_text(row["layout_json"]),
                    row["stream_name"],
                    row["start_offset"],
                    row["expected_rows"],
                    canonicalize_json_text(row["anchor_json"]),
                    row["loader_consumer"],
                    _canonical_state(row["status"]),
                    canonicalize_json_text(row["evidence_json"]),
                ),
            )
            if row["loader_consumer"]:
                destination.execute(
                    """
                    INSERT INTO consumers(
                        consumer_key,scope_key,consumer_kind,name,module,locator,
                        architecture,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        f"legacy:item-forensics:query-consumer:{row['query_spec_id']}",
                        _query_key(int(row["query_spec_id"])),
                        "native_loader",
                        row["loader_consumer"],
                        row["source_module"],
                        row["loader_consumer"],
                        None,
                        _canonical_state(row["status"]),
                        canonical_json({"source_query_spec_id": row["query_spec_id"]}),
                    ),
                )
            query_count += 1

        result_count = 0
        for row in source.execute(
            "SELECT * FROM cached_results ORDER BY cached_result_id"
        ):
            artifact = (
                _artifact_key(int(row["artifact_id"]))
                if row["artifact_id"] is not None
                else None
            )
            destination.execute(
                """
                INSERT INTO cached_results(
                    cached_result_key,source_cached_result_id,query_key,
                    artifact_key,start_offset,end_offset,row_count,row_digest,
                    raw_references_json,unresolved_references_json,
                    resolution_evidence_json,state,error
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"legacy:item-forensics:cached-result:{row['cached_result_id']}",
                    row["cached_result_id"],
                    _query_key(int(row["query_spec_id"])),
                    artifact,
                    row["start_offset"],
                    row["end_offset"],
                    row["row_count"],
                    row["row_digest"],
                    canonicalize_json_text(row["raw_references_json"]),
                    canonicalize_json_text(row["unresolved_references_json"]),
                    canonicalize_json_text(row["resolution_evidence_json"]),
                    _canonical_state(row["status"]),
                    row["error"],
                ),
            )
            result_count += 1

        row_count = 0
        buffer: list[tuple[Any, ...]] = []
        for row in source.execute(
            """
            SELECT query_spec_id,row_index,row_json
            FROM cached_result_rows
            ORDER BY query_spec_id,row_index
            """
        ):
            buffer.append(
                (
                    _query_key(int(row["query_spec_id"])),
                    int(row["row_index"]),
                    row["row_json"],
                )
            )
            row_count += 1
            if len(buffer) >= 5000:
                destination.executemany(
                    "INSERT INTO cached_result_rows VALUES(?,?,?)",
                    buffer,
                )
                buffer.clear()
        if buffer:
            destination.executemany(
                "INSERT INTO cached_result_rows VALUES(?,?,?)",
                buffer,
            )

        catalog_rows = [
            (
                row["table_name"],
                row["entity_kind"],
                row["id_column"],
                _canonical_state(row["state"]),
                row["row_count"],
                row["distinct_ids"],
                row["provenance"],
                canonicalize_json_text(row["evidence_json"]),
            )
            for row in source.execute(
                "SELECT * FROM native_catalogs ORDER BY table_name"
            )
        ]
        destination.executemany(
            """
            INSERT INTO native_catalogs(
                table_name,entity_kind,id_column,state,row_count,distinct_ids,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            catalog_rows,
        )

        native_count = 0
        property_buffer: list[tuple[Any, ...]] = []
        for row in source.execute(
            """
            SELECT * FROM native_entities
            ORDER BY entity_kind,entity_id,source_table
            """
        ):
            kind = str(row["entity_kind"])
            native_id = str(row["entity_id"])
            key = entity_key(kind, native_id)
            locator = f"native_entities:{kind}:{native_id}:{row['source_table']}"
            _insert_entity(
                destination,
                key=key,
                kind=kind,
                native_id=native_id,
                subtype=str(row["source_table"]),
                lifecycle="present",
                state=_canonical_state(row["state"]),
                authority="client_native",
                stage=10,
                provenance=str(row["provenance"]),
                evidence={"source_table": row["source_table"]},
            )
            destination.execute(
                """
                INSERT INTO native_rows(
                    native_row_key,entity_key,entity_kind,native_id,source_table,
                    state,row_json,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"legacy:item-forensics:native:{kind}:{native_id}:{row['source_table']}",
                    key,
                    kind,
                    native_id,
                    row["source_table"],
                    _canonical_state(row["state"]),
                    row["row_json"],
                    row["provenance"],
                    canonicalize_json_text(row["evidence_json"]),
                ),
            )
            for name, value in sorted(_json_object(row["row_json"]).items()):
                property_buffer.append(
                    _property_tuple(
                        owner=key,
                        namespace=f"native.{row['source_table']}",
                        name=name,
                        value=value,
                        locator=f"{locator}:{name}",
                        state=_canonical_state(row["state"]),
                        evidence={"source_table": row["source_table"]},
                    )
                )
            if len(property_buffer) >= 5000:
                destination.executemany(PROPERTY_INSERT, property_buffer)
                property_buffer.clear()
            native_count += 1
        if property_buffer:
            destination.executemany(PROPERTY_INSERT, property_buffer)

        craft_pack_query_registry = reconcile_craft_pack_query_registry(
            destination,
            source,
        )
        item_guide_query_registry = reconcile_item_guide_query_registry(
            destination,
            source,
            context.config,
        )
        tag_query_registry = reconcile_tag_query_registry(
            destination,
            source,
            context.config,
        )
        item_grade_registry_rows = source.execute(
            """
            SELECT q.query_spec_id,cr.start_offset,cr.end_offset,cr.row_count,
                   cr.row_digest,cr.status
            FROM query_specs q
            JOIN cached_results cr ON cr.query_spec_id=q.query_spec_id
            WHERE q.table_name='item_grades' AND q.sql_text=?
            ORDER BY q.query_spec_id
            """,
            (ITEM_GRADE_DESCRIPTOR_SQL,),
        ).fetchall()
        if len(item_grade_registry_rows) != 1:
            raise RuntimeError(
                "Expected one Stage 10 item_grades descriptor result"
            )
        item_grade_registry = item_grade_registry_rows[0]
        item_grade_registry_checks = {
            "start": int(item_grade_registry["start_offset"]) == 0x46AF85D,
            "done": int(item_grade_registry["end_offset"]) == 0x46AFDF1,
            "rows": int(item_grade_registry["row_count"]) == 13,
            "digest": str(item_grade_registry["row_digest"]).upper()
            == "358D7DB348E81DDEE553DD49734F0463B008AF03EAEAFAF40AEBA87C22165669",
            "result": str(item_grade_registry["status"]).startswith(
                "confirmed"
            ),
        }
        if not all(item_grade_registry_checks.values()):
            raise RuntimeError(
                "Stage 10 item_grades registry evidence changed: "
                f"{item_grade_registry_checks}"
            )
        item_grade_query_key = _query_key(
            int(item_grade_registry["query_spec_id"])
        )
        destination.execute(
            """
            UPDATE query_specs SET state='confirmed'
            WHERE query_key=?
            """,
            (item_grade_query_key,),
        )
        item_grade_consumers_updated = destination.execute(
            """
            UPDATE consumers
            SET architecture='x86+x64',state='confirmed',
                evidence_json=?
            WHERE scope_key=?
            """,
            (
                canonical_json(
                    {
                        "native_result": {
                            "start": 0x46AF85D,
                            "done": 0x46AFDF1,
                            "rows": 13,
                            "digest": str(
                                item_grade_registry["row_digest"]
                            ).upper(),
                        },
                        "preserves_existing_stage20_closure": True,
                        "source_query_spec_id": int(
                            item_grade_registry["query_spec_id"]
                        ),
                        "x64_loader": "FUN_39a365c0",
                        "x86_loader": "FUN_39d2ec60",
                        "x86_x64_layout_parity": True,
                    }
                ),
                item_grade_query_key,
            ),
        ).rowcount
        if item_grade_consumers_updated != 1:
            raise RuntimeError(
                "Expected one Stage 10 item_grades registry consumer"
            )
        _add_validation(
            destination,
            scope_kind="stage",
            scope_id="10",
            check_name="item_grade_query_registry_preserved",
            status="confirmed",
            evidence=item_grade_registry_checks,
        )
        _record_counts(
            destination,
            source,
            {
                "artifacts": ("artifacts:legacy", legacy_artifact_count),
                "query_specs": ("query_specs", query_count),
                "cached_results": ("cached_results", result_count),
                "cached_result_rows": ("cached_result_rows", row_count),
                "native_catalogs": ("native_catalogs", len(catalog_rows)),
                "native_entities": ("native_rows", native_count),
            },
        )
        set_metadata(
            destination,
            {
                "stage10.craft_pack_query_registry": (
                    craft_pack_query_registry
                ),
                "stage10.item_guide_query_registry": (
                    item_guide_query_registry
                ),
                "stage10.tag_query_registry": tag_query_registry,
                "stage10.item_grade_query_registry_preserved": (
                    item_grade_registry_checks
                ),
            },
        )

    return _atomic_build(
        context,
        context.config.stage_10,
        stage=10,
        classification="stage_10_sql_cache_and_native_types",
        populate=populate,
    )


def _materialize_item_grade_secondary(
    destination: sqlite3.Connection,
    source: sqlite3.Connection,
    context: BuildContext,
) -> dict[str, Any]:
    audit = audit_item_grade_secondary(context.config)
    x64_artifact_key = "stage20:ghidra-item-grade-secondary-x64"
    x86_artifact_key = "stage20:ghidra-item-grade-secondary-x86"
    tasks_artifact_key = "stage20:item-grade-secondary-loader-tasks"
    destination.executemany(
        """
        INSERT INTO artifacts(
            artifact_key,source_stage,role,path,bytes,sha256,build,
            authority,state,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                x64_artifact_key,
                20,
                "ghidra_item_grade_secondary_loaders_x64",
                (
                    context.config.source_ghidra_item_grade_secondary_x64
                    .resolve()
                    .as_posix()
                ),
                (
                    context.config.source_ghidra_item_grade_secondary_x64
                    .stat()
                    .st_size
                ),
                sha256_file(
                    context.config.source_ghidra_item_grade_secondary_x64
                ),
                context.config.client_build,
                "client_native",
                "confirmed",
                "existing_ghidra_project_exact_sql_consumers",
                canonical_json(
                    {
                        "architecture": "x64",
                        "queries": [
                            spec.sql for spec in ITEM_GRADE_SECONDARY_SPECS
                        ],
                    }
                ),
            ),
            (
                x86_artifact_key,
                20,
                "ghidra_item_grade_secondary_loaders_x86",
                (
                    context.config.source_ghidra_item_grade_secondary_x86
                    .resolve()
                    .as_posix()
                ),
                (
                    context.config.source_ghidra_item_grade_secondary_x86
                    .stat()
                    .st_size
                ),
                sha256_file(
                    context.config.source_ghidra_item_grade_secondary_x86
                ),
                context.config.client_build,
                "client_native",
                "confirmed",
                "existing_ghidra_project_exact_sql_consumers",
                canonical_json(
                    {
                        "architecture": "x86",
                        "queries": [
                            spec.sql for spec in ITEM_GRADE_SECONDARY_SPECS
                        ],
                    }
                ),
            ),
            (
                tasks_artifact_key,
                20,
                "item_grade_secondary_loader_tasks",
                (
                    context.config.source_item_grade_secondary_loader_tasks
                    .resolve()
                    .as_posix()
                ),
                (
                    context.config.source_item_grade_secondary_loader_tasks
                    .stat()
                    .st_size
                ),
                sha256_file(
                    context.config.source_item_grade_secondary_loader_tasks
                ),
                context.config.client_build,
                "derived_forensic",
                "confirmed",
                "declarative_exact_sql_task_registry",
                canonical_json({"queries": len(ITEM_GRADE_SECONDARY_SPECS)}),
            ),
        ],
    )

    known_items = {
        int(row["item_id"])
        for row in source.execute("SELECT item_id FROM items ORDER BY item_id")
    }
    known_buffs = {
        int(row["entity_id"])
        for row in source.execute(
            """
            SELECT entity_id FROM native_entities
            WHERE entity_kind='buff' AND state='confirmed'
            ORDER BY entity_id
            """
        )
    }
    item_grade_rows = audit["results"]["item_grade_buffs"]["rows"]
    item_endpoints = {
        int(row["item_id"])
        for row in item_grade_rows
        if int(row["item_id"]) > 0
    }
    buff_endpoints = {
        int(row["buff_id"])
        for row in item_grade_rows
        if int(row["buff_id"]) > 0
    }
    skill_endpoints = {
        int(row["skill_id"])
        for row in audit["results"]["item_grade_skills"]["rows"]
    }
    for kind, values, known, subtype in (
        (
            "item",
            item_endpoints,
            known_items,
            "item_grade_buffs_item_endpoint",
        ),
        (
            "buff",
            buff_endpoints,
            known_buffs,
            "item_grade_buffs_buff_endpoint",
        ),
    ):
        for native_id in sorted(values):
            is_present = native_id in known
            _insert_entity(
                destination,
                key=entity_key(kind, native_id),
                kind=kind,
                native_id=native_id,
                subtype=subtype,
                lifecycle="present" if is_present else "tombstone",
                state="confirmed" if is_present else "tombstone",
                authority="client_native",
                stage=20,
                provenance=(
                    "complete_native_catalog"
                    if is_present
                    else "complete_native_catalog_negative_evidence"
                ),
                evidence={
                    "referenced_by": "item_grade_buffs",
                    "complete_catalog_member": is_present,
                },
            )
    for skill_id in sorted(skill_endpoints):
        _insert_entity(
            destination,
            key=entity_key("skill", skill_id),
            kind="skill",
            native_id=skill_id,
            subtype="item_grade_skills_skill_endpoint",
            lifecycle="referenced",
            state="unknown",
            authority="client_reference",
            stage=20,
            provenance="item_grade_skills.skill_id",
            evidence={"endpoint_materialized_for_graph_closure": True},
        )

    native_rows: list[tuple[Any, ...]] = []
    properties: list[tuple[Any, ...]] = []
    relations: list[tuple[Any, ...]] = []
    coverage_rows: list[tuple[Any, ...]] = []
    consumer_rows: list[tuple[Any, ...]] = []
    relation_counts: Counter[str] = Counter()
    source_result_ids: dict[str, int] = {}
    stream_artifact_key: str | None = None

    consumer_names = {
        "item_grade_buffs": "LoadItemGradeBuffDescs",
        "item_grade_skills": "LoadItemGradeSkillDescs",
        "item_grade_distributions": "LoadItemGradeDistributionDescs",
    }
    for spec in ITEM_GRADE_SECONDARY_SPECS:
        result = audit["results"][spec.table]
        source_queries = source.execute(
            """
            SELECT * FROM query_specs
            WHERE table_name=? AND sql_text=?
            ORDER BY query_spec_id
            """,
            (spec.table, spec.sql),
        ).fetchall()
        if len(source_queries) != 1:
            raise RuntimeError(
                f"Expected one historical query for {spec.table}"
            )
        source_query = source_queries[0]
        source_query_id = int(source_query["query_spec_id"])
        source_results = source.execute(
            """
            SELECT * FROM cached_results
            WHERE query_spec_id=?
            ORDER BY cached_result_id
            """,
            (source_query_id,),
        ).fetchall()
        if len(source_results) != 1:
            raise RuntimeError(
                f"Expected one historical cached result for {spec.table}"
            )
        source_result = source_results[0]
        candidate_stream_artifact = _artifact_key(
            int(source_result["artifact_id"])
        )
        if stream_artifact_key is None:
            stream_artifact_key = candidate_stream_artifact
        elif stream_artifact_key != candidate_stream_artifact:
            raise RuntimeError(
                "Secondary item-grade results do not share one native stream"
            )

        if spec.table == "item_grade_buffs":
            historical_columns = tuple(
                json.loads(str(source_query["columns_json"]))
            )
            historical_layout = tuple(
                json.loads(str(source_query["layout_json"]))
            )
            if (
                historical_columns == spec.columns
                or historical_layout == spec.layout
                or int(source_result["start_offset"]) == spec.start
            ):
                raise RuntimeError(
                    "Historical item_grade_buffs mismatch is no longer present"
                )
            destination.execute(
                """
                INSERT INTO source_records(
                    source_record_key,source_table,source_pk,record_json,
                    authority,provenance
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    "stage20:superseded-item-grade-buffs-association",
                    "superseded_cached_result_associations",
                    "item_grade_buffs",
                    canonical_json(
                        {
                            "source_query_spec_id": source_query_id,
                            "source_cached_result_id": int(
                                source_result["cached_result_id"]
                            ),
                            "sql_text": str(source_query["sql_text"]),
                            "stored_columns": list(historical_columns),
                            "stored_layout": list(historical_layout),
                            "start": int(source_result["start_offset"]),
                            "done": int(source_result["end_offset"]),
                            "rows": int(source_result["row_count"]),
                            "digest": str(
                                source_result["row_digest"]
                            ).upper(),
                            "superseded_by": {
                                "native_call_index": spec.call_index,
                                "structural_header_index": spec.header_index,
                                "start": spec.start,
                                "done": spec.done,
                                "rows": spec.rows,
                                "digest": spec.digest,
                            },
                            "reason": (
                                "Anchor-only association conflicts with the "
                                "native SQL execution sequence and both "
                                "five-column loaders."
                            ),
                        }
                    ),
                    "derived_forensic",
                    TOOL_NAME,
                ),
            )
            source_result_id = -20_138
        else:
            if (
                int(source_result["start_offset"]) != spec.start
                or int(source_result["end_offset"]) != spec.done
                or int(source_result["row_count"]) != spec.rows
                or str(source_result["row_digest"]).upper() != spec.digest
            ):
                raise RuntimeError(
                    f"Historical {spec.table} result changed"
                )
            source_result_id = int(source_result["cached_result_id"])
        source_result_ids[spec.table] = source_result_id

        query_key = f"stage20:{spec.table.replace('_', '-')}:query"
        result_key = f"stage20:{spec.table.replace('_', '-')}:result"
        evidence = {
            "native_call_index": spec.call_index,
            "structural_header_index": spec.header_index,
            "structural_header": spec.header,
            "x64_loader": spec.x64_loader,
            "x86_loader": spec.x86_loader,
            "x86_x64_layout_parity": True,
            "native_result": {
                "start": spec.start,
                "done": spec.done,
                "rows": spec.rows,
                "digest": spec.digest,
            },
        }
        if spec.table == "item_grade_buffs":
            evidence["supersedes_historical_anchor_association"] = True
        destination.execute(
            """
            INSERT INTO query_specs(
                query_key,source_query_spec_id,table_name,source_module,
                sql_text,columns_json,layout_json,stream_name,start_offset,
                expected_rows,anchor_json,loader_consumer,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                query_key,
                source_query_id,
                spec.table,
                "x2game.dll:native-sql-call-sequence",
                spec.sql,
                canonical_json(list(spec.columns)),
                canonical_json(list(spec.layout)),
                "game11",
                spec.start,
                spec.rows,
                canonical_json(
                    {
                        "header": spec.header,
                        "structural_header_index": spec.header_index,
                    }
                ),
                f"x64 {spec.x64_loader}; x86 {spec.x86_loader}",
                "confirmed",
                canonical_json(evidence),
            ),
        )
        destination.execute(
            """
            INSERT INTO cached_results(
                cached_result_key,source_cached_result_id,query_key,
                artifact_key,start_offset,end_offset,row_count,row_digest,
                raw_references_json,unresolved_references_json,
                resolution_evidence_json,state,error
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                result_key,
                source_result_id,
                query_key,
                stream_artifact_key,
                spec.start,
                spec.done,
                spec.rows,
                spec.digest,
                canonical_json([]),
                canonical_json([]),
                canonical_json(
                    {
                        "boundary_source": (
                            f"structural_header:{spec.header_index}"
                        ),
                        "primitive_layout": list(spec.layout),
                        "x86_x64_layout_parity": True,
                    }
                ),
                "confirmed",
                None,
            ),
        )
        destination.executemany(
            """
            INSERT INTO cached_result_rows(query_key,row_index,row_json)
            VALUES(?,?,?)
            """,
            [
                (query_key, index, canonical_json(row))
                for index, row in enumerate(result["rows"])
            ],
        )
        consumer_name = consumer_names[spec.table]
        consumer_rows.extend(
            [
                (
                    f"{query_key}:consumer-x64",
                    query_key,
                    "native_loader",
                    consumer_name,
                    "x2game.dll",
                    spec.x64_loader,
                    "x64",
                    "confirmed",
                    canonical_json(
                        {
                            "artifact_key": x64_artifact_key,
                            "columns": len(spec.columns),
                        }
                    ),
                ),
                (
                    f"{query_key}:consumer-x86",
                    query_key,
                    "native_loader",
                    consumer_name,
                    "x2game.dll",
                    spec.x86_loader,
                    "x86",
                    "confirmed",
                    canonical_json(
                        {
                            "artifact_key": x86_artifact_key,
                            "columns": len(spec.columns),
                        }
                    ),
                ),
            ]
        )

        for row_index, payload in enumerate(result["rows"]):
            native_id = int(payload["id"])
            owner = entity_key(spec.entity_kind, native_id)
            _insert_entity(
                destination,
                key=owner,
                kind=spec.entity_kind,
                native_id=native_id,
                subtype=spec.table,
                lifecycle="present",
                state="confirmed",
                authority="client_native",
                stage=20,
                provenance=f"{spec.table}_native_cached_result",
                evidence={
                    "query_key": query_key,
                    "row_index": row_index,
                    "x86_x64_loader_parity": True,
                },
            )
            native_rows.append(
                (
                    stable_key(
                        "stage20", "native-row", spec.table, native_id
                    ),
                    owner,
                    spec.entity_kind,
                    str(native_id),
                    spec.table,
                    "confirmed",
                    canonical_json(payload),
                    TOOL_NAME,
                    canonical_json(
                        {
                            "query_key": query_key,
                            "cached_result_key": result_key,
                            "row_index": row_index,
                        }
                    ),
                )
            )
            for name, value in sorted(payload.items()):
                properties.append(
                    _property_tuple(
                        owner=owner,
                        namespace=f"client.{spec.table}",
                        name=name,
                        value=value,
                        locator=f"{spec.table}[{native_id}].{name}",
                        consumer=consumer_name,
                        source_artifact_key=stream_artifact_key,
                        evidence={
                            "query_key": query_key,
                            "x64_loader": spec.x64_loader,
                            "x86_loader": spec.x86_loader,
                        },
                    )
                )
            for dimension, capability in (
                ("identity", "Native row ID materialized."),
                (
                    "schema",
                    "Exact primitive layout confirmed in x86 and x64.",
                ),
                ("properties", "Every cached field decoded."),
                (
                    "relations",
                    "Every nonzero typed reference classified.",
                ),
                ("lifecycle", "Present in the complete native result."),
            ):
                coverage_rows.append(
                    (
                        stable_key(
                            "stage20",
                            "item-grade-secondary-coverage",
                            spec.table,
                            native_id,
                            dimension,
                        ),
                        owner,
                        dimension,
                        "confirmed",
                        capability,
                        "client_native",
                        TOOL_NAME,
                        canonical_json({"query_key": query_key}),
                    )
                )

            def add_relation(
                relation: str,
                dst_kind: str,
                dst_id: int,
                *,
                state: str,
                ordinal: int = 0,
                required: int = 1,
                extra: dict[str, Any] | None = None,
            ) -> None:
                relations.append(
                    (
                        stable_key(
                            "stage20",
                            spec.table,
                            native_id,
                            relation,
                            dst_kind,
                            dst_id,
                            ordinal,
                        ),
                        owner,
                        relation,
                        entity_key(dst_kind, dst_id),
                        ordinal,
                        "one",
                        state,
                        required,
                        "client_native",
                        stream_artifact_key,
                        f"{spec.table}[{native_id}]",
                        consumer_name,
                        TOOL_NAME,
                        canonical_json(
                            {
                                "query_key": query_key,
                                "foreign_key_value_observed": True,
                                **(extra or {}),
                            }
                        ),
                    )
                )
                relation_counts[relation] += 1

            if spec.table == "item_grade_buffs":
                grade_id = int(payload["item_grade_id"])
                add_relation(
                    "applies_at_item_grade",
                    "item_grade",
                    grade_id,
                    state="confirmed",
                )
                item_id = int(payload["item_id"])
                buff_id = int(payload["buff_id"])
                if item_id > 0:
                    add_relation(
                        "applies_to_item",
                        "item",
                        item_id,
                        state=(
                            "confirmed"
                            if item_id in known_items
                            else "tombstone"
                        ),
                    )
                if buff_id > 0:
                    add_relation(
                        "grants_buff",
                        "buff",
                        buff_id,
                        state=(
                            "confirmed"
                            if buff_id in known_buffs
                            else "tombstone"
                        ),
                    )
            elif spec.table == "item_grade_skills":
                add_relation(
                    "applies_at_item_grade",
                    "item_grade",
                    int(payload["item_grade_id"]),
                    state="confirmed",
                )
                add_relation(
                    "applies_to_item",
                    "item",
                    int(payload["item_id"]),
                    state="confirmed",
                )
                add_relation(
                    "uses_skill",
                    "skill",
                    int(payload["skill_id"]),
                    state="unknown",
                )
            else:
                for grade_id in range(13):
                    weight = int(payload[f"weight_{grade_id}"])
                    if weight <= 0:
                        continue
                    add_relation(
                        "weights_item_grade",
                        "item_grade",
                        grade_id,
                        state="confirmed",
                        ordinal=grade_id,
                        required=0,
                        extra={"weight": weight},
                    )

        destination.execute(
            """
            INSERT INTO native_catalogs(
                table_name,entity_kind,id_column,state,row_count,distinct_ids,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                spec.table,
                spec.entity_kind,
                "id",
                "confirmed",
                spec.rows,
                spec.rows,
                TOOL_NAME,
                canonical_json(evidence),
            ),
        )

    assert stream_artifact_key is not None
    destination.executemany(
        """
        INSERT INTO consumers(
            consumer_key,scope_key,consumer_kind,name,module,locator,
            architecture,state,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?)
        """,
        consumer_rows,
    )
    destination.executemany(
        """
        INSERT INTO native_rows(
            native_row_key,entity_key,entity_kind,native_id,source_table,
            state,row_json,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?)
        """,
        native_rows,
    )
    destination.executemany(PROPERTY_INSERT, properties)
    destination.executemany(
        """
        INSERT INTO relations(
            relation_key,src_entity_key,relation,dst_entity_key,ordinal,
            cardinality,state,required,authority,source_artifact_key,
            locator,loader_or_consumer,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        relations,
    )
    destination.executemany(
        """
        INSERT INTO coverage(
            coverage_key,scope_key,dimension,state,capability,authority,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        coverage_rows,
    )
    summary = {
        "tables": len(ITEM_GRADE_SECONDARY_SPECS),
        "rows": len(native_rows),
        "properties": len(properties),
        "relations": len(relations),
        "coverage": len(coverage_rows),
        "consumers": len(consumer_rows),
        "relation_counts": dict(sorted(relation_counts.items())),
        "item_tombstones": len(item_endpoints.difference(known_items)),
        "buff_tombstones": len(buff_endpoints.difference(known_buffs)),
        "zero_endpoint_rows": audit[
            "item_grade_buff_zero_endpoint_rows"
        ],
        "positive_distribution_weights": audit[
            "item_grade_distribution_positive_weights"
        ],
        "source_result_ids": source_result_ids,
        "x86_x64_layout_parity": audit["x86_x64_layout_parity"],
    }
    set_metadata(
        destination,
        {
            "stage20.item_grade_secondary_rows": summary["rows"],
            "stage20.item_grade_secondary_relations": summary["relations"],
            "stage20.item_grade_buff_item_tombstones": summary[
                "item_tombstones"
            ],
            "stage20.item_grade_buff_buff_tombstones": summary[
                "buff_tombstones"
            ],
        },
    )
    _add_validation(
        destination,
        scope_kind="stage",
        scope_id="20",
        check_name="item_grade_secondary_catalogs_closed",
        status="confirmed",
        evidence=summary,
    )
    return summary


def build_stage_20(context: BuildContext) -> dict[str, Any]:
    def populate(destination: sqlite3.Connection, source: sqlite3.Connection) -> None:
        legacy_artifact_count = _copy_artifacts(destination, source, context, 20) - 3
        x86_loot_artifact_key = "stage20:ghidra-loot-loaders-x86"
        loot_tasks_artifact_key = "stage20:loot-loader-tasks"
        item_grade_order_x64_artifact_key = (
            "stage20:ghidra-item-grade-order-x64"
        )
        item_grade_order_x86_artifact_key = (
            "stage20:ghidra-item-grade-order-x86"
        )
        item_grade_descriptor_x64_artifact_key = (
            "stage20:ghidra-item-grade-descriptor-x64"
        )
        item_grade_descriptor_x86_artifact_key = (
            "stage20:ghidra-item-grade-descriptor-x86"
        )
        item_grade_tasks_artifact_key = "stage20:item-grade-loader-tasks"
        destination.executemany(
            """
            INSERT INTO artifacts(
                artifact_key,source_stage,role,path,bytes,sha256,build,
                authority,state,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    x86_loot_artifact_key,
                    20,
                    "ghidra_loot_loaders_x86",
                    (
                        context.config.source_ghidra_loot_loaders_x86
                        .resolve()
                        .as_posix()
                    ),
                    context.config.source_ghidra_loot_loaders_x86.stat().st_size,
                    sha256_file(context.config.source_ghidra_loot_loaders_x86),
                    context.config.client_build,
                    "client_native",
                    "confirmed",
                    "existing_ghidra_project_exact_sql_xrefs",
                    canonical_json(
                        {
                            "program": "x2game.dll",
                            "architecture": "x86",
                            "function": "FUN_39a07180",
                        }
                    ),
                ),
                (
                    loot_tasks_artifact_key,
                    20,
                    "loot_loader_tasks",
                    context.config.source_loot_loader_tasks.resolve().as_posix(),
                    context.config.source_loot_loader_tasks.stat().st_size,
                    sha256_file(context.config.source_loot_loader_tasks),
                    context.config.client_build,
                    "derived_forensic",
                    "confirmed",
                    "declarative_exact_sql_task_registry",
                    canonical_json({"queries": len(LOOT_QUERIES)}),
                ),
                (
                    item_grade_order_x64_artifact_key,
                    20,
                    "ghidra_item_grade_order_loader_x64",
                    (
                        context.config.source_ghidra_item_grade_order_x64
                        .resolve()
                        .as_posix()
                    ),
                    context.config.source_ghidra_item_grade_order_x64.stat().st_size,
                    sha256_file(
                        context.config.source_ghidra_item_grade_order_x64
                    ),
                    context.config.client_build,
                    "client_native",
                    "confirmed",
                    "existing_ghidra_project_exact_sql_consumer",
                    canonical_json(
                        {
                            "architecture": "x64",
                            "function": "FUN_39893a10",
                            "sql": ITEM_GRADE_ORDER_SQL,
                        }
                    ),
                ),
                (
                    item_grade_order_x86_artifact_key,
                    20,
                    "ghidra_item_grade_order_loader_x86",
                    (
                        context.config.source_ghidra_item_grade_order_x86
                        .resolve()
                        .as_posix()
                    ),
                    context.config.source_ghidra_item_grade_order_x86.stat().st_size,
                    sha256_file(
                        context.config.source_ghidra_item_grade_order_x86
                    ),
                    context.config.client_build,
                    "client_native",
                    "confirmed",
                    "existing_ghidra_project_exact_sql_consumer",
                    canonical_json(
                        {
                            "architecture": "x86",
                            "function": "FUN_39968900",
                            "sql": ITEM_GRADE_ORDER_SQL,
                        }
                    ),
                ),
                (
                    item_grade_descriptor_x64_artifact_key,
                    20,
                    "ghidra_item_grade_descriptor_loader_x64",
                    (
                        context.config.source_ghidra_item_grade_descriptor_x64
                        .resolve()
                        .as_posix()
                    ),
                    (
                        context.config.source_ghidra_item_grade_descriptor_x64
                        .stat()
                        .st_size
                    ),
                    sha256_file(
                        context.config.source_ghidra_item_grade_descriptor_x64
                    ),
                    context.config.client_build,
                    "client_native",
                    "confirmed",
                    "existing_ghidra_project_exact_sql_consumer",
                    canonical_json(
                        {
                            "architecture": "x64",
                            "function": "FUN_39a365c0",
                            "sql": ITEM_GRADE_DESCRIPTOR_SQL,
                        }
                    ),
                ),
                (
                    item_grade_descriptor_x86_artifact_key,
                    20,
                    "ghidra_item_grade_descriptor_loader_x86",
                    (
                        context.config.source_ghidra_item_grade_descriptor_x86
                        .resolve()
                        .as_posix()
                    ),
                    (
                        context.config.source_ghidra_item_grade_descriptor_x86
                        .stat()
                        .st_size
                    ),
                    sha256_file(
                        context.config.source_ghidra_item_grade_descriptor_x86
                    ),
                    context.config.client_build,
                    "client_native",
                    "confirmed",
                    "existing_ghidra_project_exact_sql_consumer",
                    canonical_json(
                        {
                            "architecture": "x86",
                            "function": "FUN_39d2ec60",
                            "sql": ITEM_GRADE_DESCRIPTOR_SQL,
                        }
                    ),
                ),
                (
                    item_grade_tasks_artifact_key,
                    20,
                    "item_grade_loader_tasks",
                    (
                        context.config.source_item_grade_loader_tasks
                        .resolve()
                        .as_posix()
                    ),
                    context.config.source_item_grade_loader_tasks.stat().st_size,
                    sha256_file(context.config.source_item_grade_loader_tasks),
                    context.config.client_build,
                    "derived_forensic",
                    "confirmed",
                    "declarative_exact_sql_task_registry",
                    canonical_json({"queries": 2}),
                ),
            ],
        )
        loot_loader_artifact = source.execute(
            """
            SELECT artifact_id FROM artifacts
            WHERE role='all_sql_ghidra_loaders_64'
            ORDER BY artifact_id
            """
        ).fetchone()
        if loot_loader_artifact is None:
            raise RuntimeError("Missing x64 all-SQL loader evidence")
        loot_frontier = insert_loot_closure_frontier(
            destination,
            context.config,
            x64_artifact_key=_artifact_key(
                int(loot_loader_artifact["artifact_id"])
            ),
            x86_artifact_key=x86_loot_artifact_key,
            tool_name=TOOL_NAME,
            tool_version=TOOL_VERSION,
        )

        descriptor_by_item = {
            int(row["item_id"]): dict(row)
            for row in source.execute("SELECT * FROM descriptors ORDER BY item_id")
        }
        lifecycle_by_item: dict[int, list[dict[str, Any]]] = {}
        for row in source.execute(
            """
            SELECT * FROM descriptor_lifecycle
            ORDER BY item_id,family,table_name
            """
        ):
            lifecycle_by_item.setdefault(int(row["item_id"]), []).append(dict(row))
        descriptor_tombstones = {
            item_id
            for item_id, rows in lifecycle_by_item.items()
            if any(
                str(row["lifecycle_state"]) == "tombstone"
                for row in rows
            )
        }

        item_count = 0
        property_buffer: list[tuple[Any, ...]] = []
        for row in source.execute("SELECT * FROM items ORDER BY item_id"):
            item_id = int(row["item_id"])
            key = entity_key("item", item_id)
            descriptor = descriptor_by_item.get(item_id)
            family = str(descriptor["family"]) if descriptor else None
            _insert_entity(
                destination,
                key=key,
                kind="item",
                native_id=item_id,
                subtype=family,
                lifecycle="present",
                state="confirmed",
                authority="client_native",
                stage=20,
                provenance=str(row["client_provenance"]),
                evidence={"source_table": "items", "positive_id": item_id > 0},
            )
            payload = _row_payload(row, json_columns=("client_row_json",))
            _insert_source_record(
                destination,
                table="items",
                source_pk=str(item_id),
                payload=payload,
                authority="client_native",
            )
            native_fields = _json_object(row["client_row_json"])
            for name in (
                "impl_id",
                "name",
                "description",
                "category_id",
                "level",
                "use_skill_id",
                "buff_id",
                "craft_id",
                "loot_quest_id",
            ):
                native_fields.setdefault(name, row[name])
            for name, value in sorted(native_fields.items()):
                property_buffer.append(
                    _property_tuple(
                        owner=key,
                        namespace="client.items",
                        name=name,
                        value=value,
                        locator=f"items:{item_id}:{name}",
                        evidence={"client_provenance": row["client_provenance"]},
                    )
                )
            if len(property_buffer) >= 5000:
                destination.executemany(PROPERTY_INSERT, property_buffer)
                property_buffer.clear()
            item_count += 1
        if property_buffer:
            destination.executemany(PROPERTY_INSERT, property_buffer)
            property_buffer.clear()

        # Native entity identities make this stage independently navigable.
        for row in source.execute(
            """
            SELECT entity_kind,entity_id,source_table,state,provenance
            FROM native_entities
            ORDER BY entity_kind,entity_id,source_table
            """
        ):
            _insert_entity(
                destination,
                key=entity_key(row["entity_kind"], row["entity_id"]),
                kind=str(row["entity_kind"]),
                native_id=row["entity_id"],
                subtype=str(row["source_table"]),
                lifecycle="present",
                state=_canonical_state(row["state"]),
                authority="client_native",
                stage=20,
                provenance=str(row["provenance"]),
                evidence={"identity_imported_from": "native_entities"},
            )

        item_grade_queries = source.execute(
            """
            SELECT * FROM query_specs
            WHERE table_name='item_grades' AND sql_text=?
            ORDER BY query_spec_id
            """,
            (ITEM_GRADE_DESCRIPTOR_SQL,),
        ).fetchall()
        if len(item_grade_queries) != 1:
            raise RuntimeError(
                "Expected one authoritative full item_grades descriptor query"
            )
        item_grade_query = item_grade_queries[0]
        item_grade_query_id = int(item_grade_query["query_spec_id"])
        item_grade_results = source.execute(
            """
            SELECT * FROM cached_results
            WHERE query_spec_id=?
            ORDER BY cached_result_id
            """,
            (item_grade_query_id,),
        ).fetchall()
        if len(item_grade_results) != 1:
            raise RuntimeError(
                "Expected one authoritative item_grades cached result"
            )
        item_grade_result = item_grade_results[0]
        if (
            int(item_grade_result["start_offset"]) != 0x46AF85D
            or int(item_grade_result["end_offset"]) != 0x46AFDF1
            or int(item_grade_result["row_count"]) != 13
            or str(item_grade_result["row_digest"]).upper()
            != "358D7DB348E81DDEE553DD49734F0463B008AF03EAEAFAF40AEBA87C22165669"
            or json.loads(
                str(item_grade_result["unresolved_references_json"])
            )
        ):
            raise RuntimeError(
                "The authoritative item_grades cached-result boundary changed"
            )

        item_grade_descriptor_query_key = (
            "stage20:item-grades:descriptor-query"
        )
        item_grade_descriptor_evidence = _json_object(
            item_grade_query["evidence_json"]
        )
        item_grade_descriptor_evidence.update(
            {
                "native_call_index": 144,
                "structural_header_index": 120,
                "structural_header": 0x46AF857,
                "x64_loader": "FUN_39a365c0",
                "x86_loader": "FUN_39d2ec60",
                "x86_x64_layout_parity": True,
                "supersedes_mismatched_order_query_association": True,
            }
        )
        destination.execute(
            """
            INSERT INTO query_specs(
                query_key,source_query_spec_id,table_name,source_module,
                sql_text,columns_json,layout_json,stream_name,start_offset,
                expected_rows,anchor_json,loader_consumer,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item_grade_descriptor_query_key,
                item_grade_query_id,
                "item_grades",
                item_grade_query["source_module"],
                ITEM_GRADE_DESCRIPTOR_SQL,
                canonicalize_json_text(item_grade_query["columns_json"]),
                canonicalize_json_text(item_grade_query["layout_json"]),
                item_grade_query["stream_name"],
                int(item_grade_result["start_offset"]),
                13,
                canonicalize_json_text(item_grade_query["anchor_json"]),
                "x64 FUN_39a365c0; x86 FUN_39d2ec60",
                "confirmed",
                canonical_json(item_grade_descriptor_evidence),
            ),
        )
        item_grade_order_query_key = "stage20:item-grades:order-query"
        destination.execute(
            """
            INSERT INTO query_specs(
                query_key,source_query_spec_id,table_name,source_module,
                sql_text,columns_json,layout_json,stream_name,start_offset,
                expected_rows,anchor_json,loader_consumer,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item_grade_order_query_key,
                -20_001,
                "item_grades",
                "x2game.dll:item_grade_order",
                ITEM_GRADE_ORDER_SQL,
                canonical_json(["id"]),
                canonical_json(["68"]),
                None,
                None,
                13,
                canonical_json({}),
                "x64 FUN_39893a10; x86 FUN_39968900",
                "confirmed",
                canonical_json(
                    {
                        "role": "ordered_identity_list",
                        "result_boundary": "not_observed_in_cached_streams",
                        "descriptor_catalog_cardinality": 13,
                        "x86_x64_layout_parity": True,
                        "does_not_authorize_descriptor_properties": True,
                    }
                ),
            ),
        )
        destination.execute(
            """
            INSERT INTO cached_results(
                cached_result_key,source_cached_result_id,query_key,
                artifact_key,start_offset,end_offset,row_count,row_digest,
                raw_references_json,unresolved_references_json,
                resolution_evidence_json,state,error
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "stage20:item-grades:descriptor-result",
                int(item_grade_result["cached_result_id"]),
                item_grade_descriptor_query_key,
                _artifact_key(int(item_grade_result["artifact_id"])),
                int(item_grade_result["start_offset"]),
                int(item_grade_result["end_offset"]),
                13,
                str(item_grade_result["row_digest"]).upper(),
                canonicalize_json_text(
                    item_grade_result["raw_references_json"]
                ),
                canonical_json([]),
                canonicalize_json_text(
                    item_grade_result["resolution_evidence_json"]
                ),
                "confirmed",
                None,
            ),
        )
        destination.executemany(
            """
            INSERT INTO consumers(
                consumer_key,scope_key,consumer_kind,name,module,locator,
                architecture,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    "stage20:item-grades:descriptor-consumer-x64",
                    item_grade_descriptor_query_key,
                    "native_loader",
                    "LoadItemGradeDescs",
                    "x2game.dll",
                    "FUN_39a365c0",
                    "x64",
                    "confirmed",
                    canonical_json(
                        {
                            "artifact_key": (
                                item_grade_descriptor_x64_artifact_key
                            ),
                            "columns": 16,
                        }
                    ),
                ),
                (
                    "stage20:item-grades:descriptor-consumer-x86",
                    item_grade_descriptor_query_key,
                    "native_loader",
                    "LoadItemGradeDescs",
                    "x2game.dll",
                    "FUN_39d2ec60",
                    "x86",
                    "confirmed",
                    canonical_json(
                        {
                            "artifact_key": (
                                item_grade_descriptor_x86_artifact_key
                            ),
                            "columns": 16,
                        }
                    ),
                ),
                (
                    "stage20:item-grades:order-consumer-x64",
                    item_grade_order_query_key,
                    "native_loader",
                    "LoadItemGradeOrder",
                    "x2game.dll",
                    "FUN_39893a10",
                    "x64",
                    "confirmed",
                    canonical_json(
                        {"artifact_key": item_grade_order_x64_artifact_key}
                    ),
                ),
                (
                    "stage20:item-grades:order-consumer-x86",
                    item_grade_order_query_key,
                    "native_loader",
                    "LoadItemGradeOrder",
                    "x2game.dll",
                    "FUN_39968900",
                    "x86",
                    "confirmed",
                    canonical_json(
                        {"artifact_key": item_grade_order_x86_artifact_key}
                    ),
                ),
            ],
        )

        compact_artifact = source.execute(
            """
            SELECT artifact_id FROM artifacts
            WHERE role='client_compact'
            ORDER BY artifact_id
            """
        ).fetchall()
        if len(compact_artifact) != 1:
            raise RuntimeError("Expected one client compact artifact")
        compact_artifact_key = _artifact_key(
            int(compact_artifact[0]["artifact_id"])
        )
        compact = open_read_only(context.config.source_client_compact)
        try:
            item_grade_localizations = compact.execute(
                """
                SELECT idx,text,locale FROM localized_texts
                WHERE tbl_name='item_grades' AND tbl_column_name='name'
                ORDER BY idx,locale,text
                """
            ).fetchall()
        finally:
            compact.close()
        if (
            len(item_grade_localizations) != 13
            or {int(row["idx"]) for row in item_grade_localizations}
            != set(range(13))
        ):
            raise RuntimeError(
                "Expected one native item_grade name for every ID 0..12"
            )
        localization_by_grade = {
            int(row["idx"]): dict(row)
            for row in item_grade_localizations
        }

        item_grade_rows = source.execute(
            """
            SELECT row_index,row_json FROM cached_result_rows
            WHERE query_spec_id=? ORDER BY row_index
            """,
            (item_grade_query_id,),
        ).fetchall()
        if len(item_grade_rows) != 13:
            raise RuntimeError(
                f"Expected 13 item_grade rows, got {len(item_grade_rows)}"
            )
        decoded_item_grades = [
            json.loads(str(row["row_json"])) for row in item_grade_rows
        ]
        if (
            {int(row["id"]) for row in decoded_item_grades} != set(range(13))
            or {int(row["grade_order"]) for row in decoded_item_grades}
            != set(range(13))
        ):
            raise RuntimeError(
                "item_grades no longer forms the complete ID/order domain 0..12"
            )

        item_grade_native_rows: list[tuple[Any, ...]] = []
        item_grade_properties: list[tuple[Any, ...]] = []
        item_grade_relations: list[tuple[Any, ...]] = []
        item_grade_coverage: list[tuple[Any, ...]] = []
        for cached_row, payload in zip(item_grade_rows, decoded_item_grades):
            grade_id = int(payload["id"])
            owner = entity_key("item_grade", grade_id)
            localization = localization_by_grade[grade_id]
            _insert_entity(
                destination,
                key=owner,
                kind="item_grade",
                native_id=grade_id,
                subtype=str(localization["text"]),
                lifecycle="present",
                state="confirmed",
                authority="client_native",
                stage=20,
                provenance="item_grades_descriptor_cache",
                evidence={
                    "source_query_spec_id": item_grade_query_id,
                    "row_index": int(cached_row["row_index"]),
                    "x86_x64_loader_parity": True,
                },
            )
            item_grade_native_rows.append(
                (
                    stable_key("stage20", "native-row", "item_grades", grade_id),
                    owner,
                    "item_grade",
                    str(grade_id),
                    "item_grades",
                    "confirmed",
                    canonical_json(payload),
                    TOOL_NAME,
                    canonical_json(
                        {
                            "query_key": item_grade_descriptor_query_key,
                            "row_index": int(cached_row["row_index"]),
                            "cached_result_key": (
                                "stage20:item-grades:descriptor-result"
                            ),
                        }
                    ),
                )
            )
            for name, value in sorted(payload.items()):
                item_grade_properties.append(
                    _property_tuple(
                        owner=owner,
                        namespace="client.item_grades",
                        name=name,
                        value=value,
                        locator=f"item_grades[{grade_id}].{name}",
                        consumer="LoadItemGradeDescs",
                        evidence={
                            "query_key": item_grade_descriptor_query_key,
                            "x64_loader": "FUN_39a365c0",
                            "x86_loader": "FUN_39d2ec60",
                        },
                    )
                )
            destination.execute(
                """
                INSERT INTO localizations(
                    localization_key,locale,text_value,entity_key,state,
                    source_artifact_key,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    stable_key(
                        "localization",
                        "item_grades",
                        "name",
                        grade_id,
                        localization["locale"],
                    ),
                    str(localization["locale"]),
                    str(localization["text"]),
                    owner,
                    "confirmed",
                    compact_artifact_key,
                    canonical_json(
                        {
                            "table": "item_grades",
                            "column": "name",
                            "idx": grade_id,
                            "cached_fallback_name": payload["name"],
                        }
                    ),
                ),
            )
            icon_id = int(payload["icon_id"])
            icon = entity_key("icon", icon_id)
            _insert_entity(
                destination,
                key=icon,
                kind="icon",
                native_id=icon_id,
                subtype=None,
                lifecycle="referenced",
                state="unknown",
                authority="client_reference",
                stage=20,
                provenance="item_grades.icon_id",
                evidence={"endpoint_materialized_for_graph_closure": True},
            )
            item_grade_relations.append(
                (
                    stable_key(
                        "stage20", "item-grade-icon", grade_id, icon_id
                    ),
                    owner,
                    "uses_icon",
                    icon,
                    0,
                    "one",
                    "unknown",
                    0,
                    "client_native",
                    SOURCE_ARTIFACT_KEY,
                    f"item_grades[{grade_id}].icon_id",
                    "LoadItemGradeDescs",
                    TOOL_NAME,
                    canonical_json(
                        {
                            "foreign_key_value_observed": True,
                            "query_key": item_grade_descriptor_query_key,
                            "visual_dependency": True,
                        }
                    ),
                )
            )
            for dimension, capability in (
                ("identity", "Native item_grade ID materialized."),
                ("schema", "Sixteen-field descriptor layout confirmed x86/x64."),
                ("properties", "All cached descriptor fields decoded."),
                ("lifecycle", "Present in the complete native catalog."),
                ("localization", "Native en_us name resolved from compact."),
            ):
                item_grade_coverage.append(
                    (
                        stable_key(
                            "stage20",
                            "item-grade-coverage",
                            grade_id,
                            dimension,
                        ),
                        owner,
                        dimension,
                        "confirmed",
                        capability,
                        "client_native",
                        TOOL_NAME,
                        canonical_json(
                            {"query_key": item_grade_descriptor_query_key}
                        ),
                    )
                )
        destination.executemany(
            """
            INSERT INTO cached_result_rows(query_key,row_index,row_json)
            VALUES(?,?,?)
            """,
            [
                (
                    item_grade_descriptor_query_key,
                    int(row["row_index"]),
                    canonicalize_json_text(row["row_json"]),
                )
                for row in item_grade_rows
            ],
        )
        destination.executemany(
            """
            INSERT INTO native_rows(
                native_row_key,entity_key,entity_kind,native_id,source_table,
                state,row_json,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            item_grade_native_rows,
        )
        destination.executemany(PROPERTY_INSERT, item_grade_properties)
        destination.executemany(
            """
            INSERT INTO relations(
                relation_key,src_entity_key,relation,dst_entity_key,ordinal,
                cardinality,state,required,authority,source_artifact_key,
                locator,loader_or_consumer,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            item_grade_relations,
        )
        destination.executemany(
            """
            INSERT INTO coverage(
                coverage_key,scope_key,dimension,state,capability,authority,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            item_grade_coverage,
        )
        destination.execute(
            """
            INSERT INTO native_catalogs(
                table_name,entity_kind,id_column,state,row_count,distinct_ids,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "item_grades",
                "item_grade",
                "id",
                "confirmed",
                13,
                13,
                TOOL_NAME,
                canonical_json(
                    {
                        "query_key": item_grade_descriptor_query_key,
                        "ordered_identity_query_key": item_grade_order_query_key,
                        "ids": list(range(13)),
                        "grade_orders": list(range(13)),
                        "header": 0x46AF857,
                        "start": 0x46AF85D,
                        "done": 0x46AFDF1,
                    }
                ),
            ),
        )

        item_grade_secondary = _materialize_item_grade_secondary(
            destination,
            source,
            context,
        )

        craft_query_rows = source.execute(
            """
            SELECT * FROM query_specs
            WHERE table_name='crafts'
              AND sql_text=?
            ORDER BY query_spec_id
            """,
            (
                "SELECT id, actability_limit, cast_delay, cost, "
                "craft_c_category_id, craft_d_category_id, orderable, "
                "products_pack_id, recommend_level, req_doodad_id, skill_id, "
                "title, use_only_actability, visible_order, wi_id "
                "FROM crafts WHERE enable = 't'",
            ),
        ).fetchall()
        if len(craft_query_rows) != 1:
            raise RuntimeError(
                "Expected one authoritative enabled-crafts query"
            )
        craft_query = craft_query_rows[0]
        craft_query_id = int(craft_query["query_spec_id"])
        craft_native_rows: list[tuple[Any, ...]] = []
        craft_properties: list[tuple[Any, ...]] = []
        craft_relations: list[tuple[Any, ...]] = []
        craft_wi_counts: Counter[int] = Counter()
        craft_row_count = 0
        for cached_row in source.execute(
            """
            SELECT row_index,row_json FROM cached_result_rows
            WHERE query_spec_id=? ORDER BY row_index
            """,
            (craft_query_id,),
        ):
            payload = json.loads(str(cached_row["row_json"]))
            craft_id = int(payload["id"])
            owner = entity_key("craft", craft_id)
            craft_native_rows.append(
                (
                    stable_key(
                        "stage20", "native-row", "crafts_enabled", craft_id
                    ),
                    owner,
                    "craft",
                    str(craft_id),
                    "crafts_enabled",
                    "confirmed",
                    canonical_json(payload),
                    TOOL_NAME,
                    canonical_json(
                        {
                            "source_query_spec_id": craft_query_id,
                            "row_index": int(cached_row["row_index"]),
                            "query_scope": "enable = 't'",
                        }
                    ),
                )
            )
            for name, value in sorted(payload.items()):
                craft_properties.append(
                    _property_tuple(
                        owner=owner,
                        namespace="client.crafts_enabled",
                        name=name,
                        value=value,
                        locator=f"crafts[{craft_id}].{name}",
                        state="confirmed",
                        evidence={
                            "source_query_spec_id": craft_query_id,
                            "query_scope": "enable = 't'",
                        },
                    )
                )
            wi_id = int(payload["wi_id"])
            if wi_id > 0:
                destination_key = entity_key("world_interaction", wi_id)
                _insert_entity(
                    destination,
                    key=destination_key,
                    kind="world_interaction",
                    native_id=wi_id,
                    subtype=None,
                    lifecycle="referenced",
                    state="unknown",
                    authority="client_native",
                    stage=20,
                    provenance="crafts_enabled.wi_id",
                    evidence={
                        "endpoint_materialized_for_graph_closure": True,
                    },
                )
                craft_relations.append(
                    (
                        stable_key(
                            "stage20",
                            "craft-world-interaction",
                            craft_id,
                            wi_id,
                        ),
                        owner,
                        "uses_world_interaction",
                        destination_key,
                        0,
                        "one",
                        "unknown",
                        1,
                        "client_native",
                        SOURCE_ARTIFACT_KEY,
                        f"crafts[{craft_id}].wi_id",
                        str(craft_query["loader_consumer"]),
                        TOOL_NAME,
                        canonical_json(
                            {
                                "foreign_key_value_observed": True,
                                "source_query_spec_id": craft_query_id,
                                "query_scope": "enable = 't'",
                            }
                        ),
                    )
                )
                craft_wi_counts[wi_id] += 1
            craft_row_count += 1
        if craft_row_count != 9_369:
            raise RuntimeError(
                f"Expected 9,369 enabled craft rows, got {craft_row_count}"
            )
        if sum(craft_wi_counts.values()) != 9_172 or len(craft_wi_counts) != 27:
            raise RuntimeError(
                "Enabled craft world_interaction reference inventory changed"
            )
        destination.executemany(
            """
            INSERT INTO native_rows(
                native_row_key,entity_key,entity_kind,native_id,source_table,
                state,row_json,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            craft_native_rows,
        )
        destination.executemany(PROPERTY_INSERT, craft_properties)
        destination.executemany(
            """
            INSERT INTO relations(
                relation_key,src_entity_key,relation,dst_entity_key,ordinal,
                cardinality,state,required,authority,source_artifact_key,
                locator,loader_or_consumer,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            craft_relations,
        )
        destination.execute(
            """
            INSERT INTO native_catalogs(
                table_name,entity_kind,id_column,state,row_count,distinct_ids,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "crafts_enabled",
                "craft",
                "id",
                "confirmed",
                craft_row_count,
                craft_row_count,
                TOOL_NAME,
                canonical_json(
                    {
                        "source_query_spec_id": craft_query_id,
                        "query_scope": "enable = 't'",
                        "world_interaction_references": sum(
                            craft_wi_counts.values()
                        ),
                        "world_interaction_ids": dict(
                            sorted(craft_wi_counts.items())
                        ),
                    }
                ),
            ),
        )

        descriptor_count = 0
        for item_id, row in sorted(descriptor_by_item.items()):
            descriptor_key = entity_key(
                "item_descriptor",
                f"{item_id}:{row['family']}",
            )
            source_state = _canonical_state(row["state"])
            lifecycle_rows = lifecycle_by_item.get(item_id, [])
            lifecycle = (
                str(lifecycle_rows[0]["lifecycle_state"])
                if lifecycle_rows
                else ("present" if source_state == "confirmed" else source_state)
            )
            state = (
                "tombstone"
                if source_state in {"missing", "unknown"}
                and lifecycle == "tombstone"
                else source_state
            )
            _insert_entity(
                destination,
                key=descriptor_key,
                kind="item_descriptor",
                native_id=f"{item_id}:{row['family']}",
                subtype=str(row["family"]),
                lifecycle=lifecycle,
                state=state,
                authority="client_native",
                stage=20,
                provenance=str(row["provenance"]),
                evidence={
                    "source_table": row["table_name"],
                    "item_id": item_id,
                    "source_descriptor_state": source_state,
                    "lifecycle_supersedes_absence": state == "tombstone",
                },
            )
            destination.execute(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,ordinal,
                    cardinality,state,required,authority,source_artifact_key,
                    locator,loader_or_consumer,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"derived:item-descriptor:{item_id}",
                    entity_key("item", item_id),
                    "has_descriptor",
                    descriptor_key,
                    0,
                    "zero_or_one",
                    state,
                    1,
                    "client_native",
                    SOURCE_ARTIFACT_KEY,
                    f"descriptors:{item_id}",
                    None,
                    str(row["provenance"]),
                    canonical_json({"projection": "descriptor_identity"}),
                ),
            )
            descriptor_payload = dict(row)
            descriptor_payload["descriptor_json"] = _json_object(
                descriptor_payload.get("descriptor_json")
            )
            descriptor_payload["evidence_json"] = _json_object(
                descriptor_payload.get("evidence_json")
            )
            _insert_source_record(
                destination,
                table="descriptors",
                source_pk=str(item_id),
                payload=descriptor_payload,
                authority="client_native",
            )
            descriptor_properties = _json_object(row["descriptor_json"])
            descriptor_properties.update(
                {
                    "family": row["family"],
                    "table_name": row["table_name"],
                    "row_key": row["row_key"],
                    "state": row["state"],
                }
            )
            destination.executemany(
                PROPERTY_INSERT,
                [
                    _property_tuple(
                        owner=descriptor_key,
                        namespace=f"descriptor.{row['family']}",
                        name=name,
                        value=value,
                        locator=f"descriptors:{item_id}:{name}",
                        state=state,
                        evidence={"item_id": item_id},
                    )
                    for name, value in sorted(descriptor_properties.items())
                ],
            )
            descriptor_count += 1

        lifecycle_count = 0
        for item_id, rows in sorted(lifecycle_by_item.items()):
            for ordinal, row in enumerate(rows):
                _insert_source_record(
                    destination,
                    table="descriptor_lifecycle",
                    source_pk=f"{item_id}:{row['family']}:{row['table_name']}:{ordinal}",
                    payload={
                        **row,
                        "evidence_json": _json_object(row.get("evidence_json")),
                    },
                    authority="client_native",
                )
                descriptor_key = entity_key(
                    "item_descriptor",
                    f"{item_id}:{row['family']}",
                )
                for name in (
                    "lifecycle_state",
                    "operational_state",
                    "target_kind",
                    "target_id",
                ):
                    destination.execute(
                        PROPERTY_INSERT,
                        _property_tuple(
                            owner=descriptor_key,
                            namespace="descriptor.lifecycle",
                            name=name,
                            value=row[name],
                            locator=(
                                f"descriptor_lifecycle:{item_id}:"
                                f"{row['family']}:{row['table_name']}:{name}"
                            ),
                            state=_canonical_state(row["lifecycle_state"]),
                            evidence={"source_table": row["table_name"]},
                        ),
                    )
                lifecycle_count += 1

        edge_count = 0
        relation_buffer: list[tuple[Any, ...]] = []
        for row in source.execute(
            "SELECT * FROM dependency_edges ORDER BY dependency_id"
        ):
            src = entity_key(row["src_kind"], row["src_id"])
            dst = entity_key(row["dst_kind"], row["dst_id"])
            state = _canonical_state(row["state"])
            _insert_entity(
                destination,
                key=src,
                kind=str(row["src_kind"]),
                native_id=row["src_id"],
                subtype=None,
                lifecycle="unknown",
                state="unknown",
                authority="client_reference",
                stage=20,
                provenance="dependency_endpoint",
                evidence={"direction": "source"},
            )
            _insert_entity(
                destination,
                key=dst,
                kind=str(row["dst_kind"]),
                native_id=row["dst_id"],
                subtype=None,
                lifecycle="unknown",
                state="missing" if state == "missing" else "unknown",
                authority="client_reference",
                stage=20,
                provenance="dependency_endpoint",
                evidence={"direction": "destination"},
            )
            relation_buffer.append(
                (
                    f"legacy:item-forensics:dependency:{row['dependency_id']}",
                    src,
                    row["relation"],
                    dst,
                    0,
                    None,
                    state,
                    int(row["required"]),
                    "client_native"
                    if state == "confirmed"
                    else "client_reference",
                    SOURCE_ARTIFACT_KEY,
                    f"dependency_edges:{row['dependency_id']}",
                    None,
                    row["provenance"],
                    canonical_json(
                        {
                            "source_dependency_id": row["dependency_id"],
                            "source_state": row["state"],
                            "evidence": _json_object(row["evidence_json"]),
                        }
                    ),
                )
            )
            edge_count += 1
            if len(relation_buffer) >= 5000:
                destination.executemany(
                    """
                    INSERT INTO relations(
                        relation_key,src_entity_key,relation,dst_entity_key,
                        ordinal,cardinality,state,required,authority,
                        source_artifact_key,locator,loader_or_consumer,
                        provenance,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    relation_buffer,
                )
                relation_buffer.clear()
        if relation_buffer:
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                relation_buffer,
            )

        surface_reference_count = 0
        relation_buffer.clear()
        for row in source.execute(
            "SELECT * FROM surface_references ORDER BY reference_id"
        ):
            surface_key = entity_key("surface", row["surface_id"])
            item_key = entity_key("item", row["item_id"])
            _insert_entity(
                destination,
                key=surface_key,
                kind="surface",
                native_id=row["surface_id"],
                subtype=None,
                lifecycle="unknown",
                state="unknown",
                authority="client_reference",
                stage=20,
                provenance="surface_reference_endpoint",
                evidence={},
            )
            _insert_entity(
                destination,
                key=item_key,
                kind="item",
                native_id=row["item_id"],
                subtype=None,
                lifecycle="unknown",
                state="unknown",
                authority="client_reference",
                stage=20,
                provenance="surface_reference_endpoint",
                evidence={},
            )
            relation_buffer.append(
                (
                    f"legacy:item-forensics:surface-reference:{row['reference_id']}",
                    surface_key,
                    f"mentions_item:{row['token_kind']}",
                    item_key,
                    0,
                    None,
                    _canonical_state(row["state"]),
                    0,
                    "client_reference",
                    SOURCE_ARTIFACT_KEY,
                    str(row["locator"]),
                    None,
                    str(row["provenance"]),
                    canonicalize_json_text(row["evidence_json"]),
                )
            )
            surface_reference_count += 1
            if len(relation_buffer) >= 5000:
                destination.executemany(
                    """
                    INSERT INTO relations(
                        relation_key,src_entity_key,relation,dst_entity_key,
                        ordinal,cardinality,state,required,authority,
                        source_artifact_key,locator,loader_or_consumer,
                        provenance,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    relation_buffer,
                )
                relation_buffer.clear()
        if relation_buffer:
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                relation_buffer,
            )

        gap_count = 0
        superseded_descriptor_gap_count = 0
        for row in source.execute("SELECT * FROM gaps ORDER BY gap_id"):
            gap_count += 1
            if (
                str(row["blocker_code"]) == "descriptor_missing"
                and int(row["item_id"]) in descriptor_tombstones
            ):
                _insert_source_record(
                    destination,
                    table="superseded_descriptor_gaps",
                    source_pk=str(row["gap_id"]),
                    payload={
                        **dict(row),
                        "superseded_by": "descriptor_lifecycle:tombstone",
                    },
                    authority="client_native",
                )
                superseded_descriptor_gap_count += 1
                continue
            _insert_entity(
                destination,
                key=entity_key("item", row["item_id"]),
                kind="item",
                native_id=row["item_id"],
                subtype=None,
                lifecycle="unknown",
                state="unknown",
                authority="server_observed",
                stage=20,
                provenance="gap_scope",
                evidence={},
            )
            destination.execute(
                """
                INSERT INTO gaps(
                    gap_key,entity_key,dimension,state,severity,blocker_code,
                    reason,required_evidence,provenance
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"legacy:item-forensics:gap:{row['gap_id']}",
                    entity_key("item", row["item_id"]),
                    row["dimension"],
                    _canonical_state(row["state"]),
                    row["severity"],
                    row["blocker_code"],
                    row["reason"],
                    row["required_evidence"],
                    "aa8-item-forensics",
                ),
            )

        capability_count = 0
        for row in source.execute(
            """
            SELECT * FROM server_capabilities
            ORDER BY item_id,dimension
            """
        ):
            _insert_entity(
                destination,
                key=entity_key("item", row["item_id"]),
                kind="item",
                native_id=row["item_id"],
                subtype=None,
                lifecycle="unknown",
                state="unknown",
                authority="server_observed",
                stage=20,
                provenance="server_capability_scope",
                evidence={},
            )
            item_id = int(row["item_id"])
            descriptor_tombstone = (
                str(row["dimension"]) == "descriptor"
                and item_id in descriptor_tombstones
            )
            projected_state = (
                "not_applicable"
                if descriptor_tombstone
                else _canonical_state(row["state"])
            )
            destination.execute(
                """
                INSERT INTO coverage(
                    coverage_key,scope_key,dimension,state,capability,authority,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    f"legacy:item-forensics:server-capability:"
                    f"{row['item_id']}:{row['dimension']}",
                    entity_key("item", row["item_id"]),
                    row["dimension"],
                    projected_state,
                    (
                        "Native descriptor absence is a classified tombstone."
                        if descriptor_tombstone
                        else row["capability"]
                    ),
                    (
                        "client_native"
                        if descriptor_tombstone
                        else "server_observed"
                    ),
                    (
                        "descriptor_lifecycle"
                        if descriptor_tombstone
                        else row["evidence_kind"]
                    ),
                    canonical_json(
                        {
                            "source_capability": _json_object(
                                row["evidence_json"]
                            ),
                            "source_state": row["state"],
                            "superseded_by_lifecycle": descriptor_tombstone,
                        }
                    ),
                ),
            )
            capability_count += 1

        runtime_count = 0
        for row in source.execute("SELECT * FROM runtime_coverage ORDER BY item_id"):
            _insert_entity(
                destination,
                key=entity_key("item", row["item_id"]),
                kind="item",
                native_id=row["item_id"],
                subtype=str(row["concrete_type"]),
                lifecycle="unknown",
                state="unknown",
                authority="server_observed",
                stage=20,
                provenance="runtime_coverage_scope",
                evidence={},
            )
            destination.execute(
                """
                INSERT INTO coverage(
                    coverage_key,scope_key,dimension,state,capability,authority,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    f"legacy:item-forensics:runtime-coverage:{row['item_id']}",
                    entity_key("item", row["item_id"]),
                    "legacy_runtime_projection",
                    "corroborated",
                    f"coverage:{row['coverage']}",
                    "server_observed",
                    row["provenance"],
                    canonical_json(
                        {
                            "concrete_type": row["concrete_type"],
                            "coverage": row["coverage"],
                            "missing_dependencies": row["missing_dependencies"],
                            "runtime_present": bool(row["runtime_present"]),
                        }
                    ),
                ),
            )
            runtime_count += 1

        hint_count = 0
        for row in source.execute("SELECT * FROM source_hints ORDER BY hint_id"):
            _insert_source_record(
                destination,
                table="source_hints",
                source_pk=str(row["hint_id"]),
                payload=dict(row),
                authority=(
                    "client_native" if int(row["authority"]) else "corroborative"
                ),
            )
            hint_count += 1

        opaque_count = 0
        for row in source.execute("SELECT * FROM opaque_regions ORDER BY opaque_id"):
            destination.execute(
                """
                INSERT INTO opaque_regions(
                    opaque_key,surface,locator,blocker_code,reason,
                    searched_evidence_json,source_stage,state
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    f"legacy:item-forensics:opaque:{row['opaque_id']}",
                    row["surface"],
                    row["locator"],
                    row["blocker_code"],
                    row["reason"],
                    canonicalize_json_text(row["searched_evidence_json"]),
                    20,
                    "opaque",
                ),
            )
            opaque_count += 1

        item_endpoint_lifecycle = reconcile_native_item_endpoints(
            destination,
            source,
            stage=20,
            source_artifact_key=SOURCE_ARTIFACT_KEY,
            expected={
                "relations": 66_924,
                "endpoints": 14_698,
                "present": 0,
                "tombstone": 14_698,
            },
        )
        active_skills, skill_catalog_evidence = (
            native_skill_identity_catalog(context.config)
        )
        skill_endpoint_lifecycle = reconcile_native_skill_endpoints(
            destination,
            active_ids=active_skills,
            catalog_evidence=skill_catalog_evidence,
            stage=20,
            source_artifact_key="legacy:item-forensics:artifact:6",
            expected={
                "relations": 14_208,
                "endpoints": 8_263,
                "present": 8_193,
                "tombstone": 70,
            },
        )
        active_buffs, buff_catalog_evidence = (
            native_buff_identity_catalog(context.config)
        )
        buff_endpoint_lifecycle = reconcile_native_buff_endpoints(
            destination,
            active_ids=active_buffs,
            catalog_evidence=buff_catalog_evidence,
            stage=20,
            source_artifact_key="legacy:item-forensics:artifact:6",
            expected={
                "relations": 41,
                "endpoints": 39,
                "present": 0,
                "tombstone": 39,
            },
        )
        (
            enabled_crafts,
            referenced_crafts,
            observed_crafts,
            craft_catalog_evidence,
        ) = native_craft_identity_constraints(context.config)
        craft_identity_constraints = reconcile_native_craft_endpoints(
            destination,
            enabled_ids=enabled_crafts,
            reference_ids=referenced_crafts,
            observed_ids=observed_crafts,
            catalog_evidence=craft_catalog_evidence,
            stage=20,
            source_artifact_key="legacy:item-forensics:artifact:6",
            materialize_observed_universe=True,
            expected={
                "entities": 12_071,
                "enabled": 9_369,
                "disabled_or_tombstone": 2_702,
                "relations": 62_978,
                "relation_endpoints": 11_946,
            },
        )
        active_craft_packs, craft_pack_catalog_evidence = (
            native_craft_pack_evidence(source)
        )
        craft_pack_endpoint_lifecycle = (
            reconcile_native_craft_pack_endpoints(
                destination,
                active_ids=active_craft_packs,
                catalog_evidence=craft_pack_catalog_evidence,
                stage=20,
                source_artifact_key="legacy:item-forensics:artifact:6",
                expected={
                    "relations": 11_523,
                    "endpoints": 1_621,
                    "present": 438,
                    "tombstone": 1_183,
                },
            )
        )
        active_item_guides, item_guide_catalog_evidence = (
            native_item_guide_evidence(source, context.config)
        )
        item_guide_endpoint_lifecycle = (
            reconcile_native_item_guide_endpoints(
                destination,
                active_ids=active_item_guides,
                catalog_evidence=item_guide_catalog_evidence,
                stage=20,
                source_artifact_key="legacy:item-forensics:artifact:6",
                expected={
                    "active": 464,
                    "active_without_incoming": 81,
                    "endpoints": 386,
                    "present_endpoints": 383,
                    "relations": 4_459,
                    "tombstones": 3,
                    "universe": 467,
                },
            )
        )
        active_npcs, npc_catalog_evidence = native_npc_identity_catalog(
            context.config
        )
        npc_endpoint_lifecycle = reconcile_native_npc_endpoints(
            destination,
            active_ids=active_npcs,
            catalog_evidence=npc_catalog_evidence,
            stage=20,
            source_artifact_key="legacy:item-forensics:artifact:6",
            expected={
                "relations": 340,
                "endpoints": 301,
                "present": 300,
                "tombstone": 1,
            },
        )

        _record_counts(
            destination,
            source,
            {
                "artifacts": ("artifacts:legacy", legacy_artifact_count),
                "items": ("source_records:items", item_count),
                "descriptors": ("source_records:descriptors", descriptor_count),
                "descriptor_lifecycle": (
                    "source_records:descriptor_lifecycle",
                    lifecycle_count,
                ),
                "dependency_edges": ("relations:dependency", edge_count),
                "surface_references": (
                    "relations:surface_reference",
                    surface_reference_count,
                ),
                "gaps": ("gaps", gap_count),
                "server_capabilities": ("coverage:server", capability_count),
                "runtime_coverage": ("coverage:runtime", runtime_count),
                "source_hints": ("source_records:source_hints", hint_count),
                "opaque_regions": ("opaque_regions", opaque_count),
            },
        )
        set_metadata(
            destination,
            {
                "stage20.descriptor_tombstones": len(descriptor_tombstones),
                "stage20.superseded_descriptor_gaps": (
                    superseded_descriptor_gap_count
                ),
                "stage20.loot_frontier_queries": loot_frontier["queries"],
                "stage20.crafts_enabled_rows": craft_row_count,
                "stage20.craft_world_interaction_references": sum(
                    craft_wi_counts.values()
                ),
                "stage20.craft_world_interaction_ids": len(craft_wi_counts),
                "stage20.item_grade_rows": len(decoded_item_grades),
                "stage20.item_grade_localizations": len(
                    item_grade_localizations
                ),
                "stage20.item_grade_icon_relations": len(
                    item_grade_relations
                ),
                "stage20.item_grade_secondary_tables": (
                    item_grade_secondary["tables"]
                ),
                "stage20.item_endpoint_lifecycle": (
                    item_endpoint_lifecycle
                ),
                "stage20.skill_endpoint_lifecycle": (
                    skill_endpoint_lifecycle
                ),
                "stage20.buff_endpoint_lifecycle": (
                    buff_endpoint_lifecycle
                ),
                "stage20.craft_identity_constraints": (
                    craft_identity_constraints
                ),
                "stage20.craft_pack_endpoint_lifecycle": (
                    craft_pack_endpoint_lifecycle
                ),
                "stage20.item_guide_endpoint_lifecycle": (
                    item_guide_endpoint_lifecycle
                ),
                "stage20.npc_endpoint_lifecycle": (
                    npc_endpoint_lifecycle
                ),
            },
        )
        _add_validation(
            destination,
            scope_kind="stage",
            scope_id="20",
            check_name="item_grade_native_catalog_closed",
            status="confirmed",
            evidence={
                "rows": len(decoded_item_grades),
                "ids": sorted(
                    int(row["id"]) for row in decoded_item_grades
                ),
                "grade_orders": sorted(
                    int(row["grade_order"]) for row in decoded_item_grades
                ),
                "localizations": len(item_grade_localizations),
                "icon_relations": len(item_grade_relations),
                "descriptor_query": ITEM_GRADE_DESCRIPTOR_SQL,
                "order_query": ITEM_GRADE_ORDER_SQL,
                "x64_descriptor_loader": "FUN_39a365c0",
                "x86_descriptor_loader": "FUN_39d2ec60",
                "x64_order_loader": "FUN_39893a10",
                "x86_order_loader": "FUN_39968900",
                "cached_result": {
                    "header": 0x46AF857,
                    "start": 0x46AF85D,
                    "done": 0x46AFDF1,
                    "digest": str(
                        item_grade_result["row_digest"]
                    ).upper(),
                },
            },
        )
        _add_validation(
            destination,
            scope_kind="stage",
            scope_id="20",
            check_name="enabled_craft_world_interaction_projection",
            status="confirmed",
            evidence={
                "rows": craft_row_count,
                "nonzero_references": sum(craft_wi_counts.values()),
                "distinct_world_interactions": len(craft_wi_counts),
                "counts": dict(sorted(craft_wi_counts.items())),
                "query_scope": "enable = 't'",
            },
        )
        _add_validation(
            destination,
            scope_kind="stage",
            scope_id="20",
            check_name="descriptor_absence_lifecycle_reconciled",
            status=(
                "confirmed"
                if superseded_descriptor_gap_count == len(descriptor_tombstones)
                else "blocked"
            ),
            evidence={
                "descriptor_tombstones": len(descriptor_tombstones),
                "superseded_descriptor_gaps": superseded_descriptor_gap_count,
            },
        )

        orphan_relations = int(
            destination.execute(
                """
                SELECT COUNT(*) FROM relations r
                LEFT JOIN entities s ON s.entity_key=r.src_entity_key
                LEFT JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE s.entity_key IS NULL OR d.entity_key IS NULL
                """
            ).fetchone()[0]
        )
        if orphan_relations:
            raise RuntimeError(f"Stage 20 has {orphan_relations} orphan relations")
        _add_validation(
            destination,
            scope_kind="stage",
            scope_id="20",
            check_name="zero_orphan_relations",
            status="confirmed",
            evidence={"orphan_relations": orphan_relations},
        )
    return _atomic_build(
        context,
        context.config.stage_20,
        stage=20,
        classification="stage_20_items_and_reachable_relations",
        populate=populate,
    )


WORLD_ACTOR_ARTIFACTS = {
    "stage30:game11": ("native_cached_stream", "source_game11", "client_native"),
    "stage30:client-compact": (
        "decrypted_client_compact",
        "source_client_compact",
        "client_native",
    ),
    "stage30:npc-catalog-manifest": (
        "native_decode_manifest",
        "source_npc_catalog_manifest",
        "derived_forensic",
    ),
    "stage30:character-data": (
        "native_character_rows",
        "source_character_data",
        "derived_forensic",
    ),
    "stage30:character-manifest": (
        "native_character_manifest",
        "source_character_manifest",
        "derived_forensic",
    ),
    "stage30:faction-data": (
        "native_faction_rows",
        "source_faction_data",
        "derived_forensic",
    ),
    "stage30:faction-manifest": (
        "native_faction_manifest",
        "source_faction_manifest",
        "derived_forensic",
    ),
    "stage30:spawner-layers": (
        "game_pak_spawner_evidence",
        "source_spawner_layers_manifest",
        "client_asset",
    ),
    "stage30:spawner-absence": (
        "negative_stream_evidence",
        "source_spawner_absence_manifest",
        "derived_forensic",
    ),
    "stage30:ghidra-sql-loaders-64": (
        "native_loader_decompilation",
        "source_ghidra_sql_loaders_64",
        "client_native",
    ),
    "stage30:ghidra-sql-call-sequence": (
        "native_sql_execution_sequence",
        "source_ghidra_sql_call_sequence",
        "client_native",
    ),
    "stage30:ghidra-custom-model-x64": (
        "custom_model_layout_x64",
        "source_ghidra_custom_model_x64",
        "client_native",
    ),
    "stage30:ghidra-custom-model-x86": (
        "custom_model_layout_x86",
        "source_ghidra_custom_model_x86",
        "client_native",
    ),
    "stage30:gamepak-index": (
        "game_pak_full_index",
        "source_gamepak_index",
        "client_asset",
    ),
}


NPC_RELATIONS = {
    "ai_file_id": ("uses_ai_file", "ai_file"),
    "base_skill_id": ("uses_base_skill", "skill"),
    "engage_combat_bgm_id": ("uses_combat_bgm", "sound"),
    "engage_combat_give_quest_id": ("grants_quest_on_combat", "quest"),
    "equip_cloths_id": ("uses_cloth_pack", "equip_pack_cloths"),
    "equip_weapons_id": ("uses_weapon_pack", "equip_pack_weapons"),
    "faction_id": ("belongs_to_faction", "system_faction"),
    "friendly_near_quest_id": ("references_friendly_quest", "quest"),
    "mate_equip_slot_pack_id": ("uses_mate_equip_slot_pack", "mate_equip_slot_pack"),
    "merchant_random_pack_id": ("uses_merchant_random_pack", "merchant_random_pack"),
    "model_id": ("uses_model", "model"),
    "npc_ai_client_param_id": ("uses_ai_client_param", "npc_ai_client_param"),
    "npc_ai_param_id": ("uses_ai_param", "npc_ai_param"),
    "npc_grade_id": ("has_grade", "npc_grade"),
    "npc_interaction_set_id": ("uses_interaction_set", "npc_interaction_set"),
    "npc_kind_id": ("has_kind", "npc_kind"),
    "npc_nickname_id": ("uses_nickname", "npc_nickname"),
    "npc_posture_set_id": ("uses_posture_set", "npc_posture_set"),
    "npc_strafe_param_id": ("uses_strafe_param", "npc_strafe_param"),
    "npc_template_id": ("uses_template", "npc_template"),
    "pet_item_id": ("created_from_item", "item"),
    "sound_pack_id": ("uses_sound_pack", "sound_pack"),
    "specialty_coin_id": ("uses_specialty_coin", "item"),
    "total_custom_id": ("uses_total_custom", "total_character_custom"),
    "weapon_element_id": ("uses_weapon_element", "weapon_element"),
}


CHARACTER_RELATIONS = {
    "default_custom_id": ("uses_default_custom", "total_character_custom"),
    "face_item_id": ("uses_face_item", "item"),
    "faction_id": ("belongs_to_faction", "system_faction"),
    "model_id": ("uses_model", "model"),
    "preview_cloth_pack_id": ("uses_preview_cloth_pack", "equip_pack_cloths"),
    "starting_zone_id": ("starts_in_zone", "zone"),
}


def _stage30_artifacts(
    destination: sqlite3.Connection,
    context: BuildContext,
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, (role, attribute, authority) in sorted(WORLD_ACTOR_ARTIFACTS.items()):
        path = Path(getattr(context.config, attribute))
        digest = sha256_file(path)
        hashes[key] = digest
        destination.execute(
            """
            INSERT INTO artifacts(
                artifact_key,source_stage,role,path,bytes,sha256,build,authority,
                state,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                key,
                30,
                role,
                path.resolve().as_posix(),
                path.stat().st_size,
                digest,
                context.config.client_build,
                authority,
                "confirmed",
                TOOL_NAME,
                canonical_json({"immutable_input": True}),
            ),
        )
    for stream_id in range(12):
        if stream_id == 11:
            continue
        path = context.config.source_cached_streams_dir / f"game{stream_id}"
        digest = sha256_file(path)
        key = f"stage30:stream:game{stream_id}"
        hashes[key] = digest
        destination.execute(
            """
            INSERT INTO artifacts(
                artifact_key,source_stage,role,path,bytes,sha256,build,authority,
                state,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                key,
                30,
                "native_cached_stream",
                path.resolve().as_posix(),
                path.stat().st_size,
                digest,
                context.config.client_build,
                "client_native",
                "confirmed",
                TOOL_NAME,
                canonical_json(
                    {
                        "immutable_input": True,
                        "included_for_negative_layout_audit": True,
                    }
                ),
            ),
        )
    face_profiles = load_face_target_profiles(
        context.config.source_gamepak_xml_root
    )
    for profile in face_profiles.values():
        path = context.config.source_gamepak_xml_root / profile.relative_path
        key = f"stage30:face-target-profile:{profile.code}"
        digest = sha256_file(path)
        hashes[key] = digest
        destination.execute(
            """
            INSERT INTO artifacts(
                artifact_key,source_stage,role,path,bytes,sha256,build,authority,
                state,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                key,
                30,
                "game_pak_face_target_profile",
                path.resolve().as_posix(),
                path.stat().st_size,
                digest,
                context.config.client_build,
                "client_asset",
                "confirmed",
                TOOL_NAME,
                canonical_json(
                    {
                        "profile_key": profile.profile_key,
                        "target_count": len(profile.targets),
                    }
                ),
            ),
        )
    for architecture, root in (
        ("x64", context.config.source_gamepak_lua64_root),
        ("x86", context.config.source_gamepak_lua32_root),
    ):
        path = root / "x2ui" / "customizing_new" / "modifier.lua"
        key = f"stage30:customizing-modifier-lua:{architecture}"
        digest = sha256_file(path)
        hashes[key] = digest
        destination.execute(
            """
            INSERT INTO artifacts(
                artifact_key,source_stage,role,path,bytes,sha256,build,authority,
                state,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                key,
                30,
                "customizing_modifier_ui_consumer",
                path.resolve().as_posix(),
                path.stat().st_size,
                digest,
                context.config.client_build,
                "client_script",
                "confirmed",
                TOOL_NAME,
                canonical_json(
                    {
                        "architecture": architecture,
                        "apis": [
                            "GetNumFaceTargets",
                            "GetFaceTargetIndex",
                            "GetFaceTargetName",
                            "GetFaceTargetMinValue",
                            "GetFaceTargetMaxValue",
                        ],
                    }
                ),
            ),
        )
    return hashes


def _stage30_property(
    connection: sqlite3.Connection,
    *,
    owner: str,
    namespace: str,
    name: str,
    value: Any,
    locator: str,
    artifact: str,
    state: str = "confirmed",
    authority: str = "client_native",
    consumer: str | None = None,
    ordinal: int = 0,
    evidence: dict[str, Any] | None = None,
) -> None:
    value_type, text, integer, real, boolean, json_value = typed_value(value)
    connection.execute(
        PROPERTY_INSERT,
        (
            stable_key("property", owner, namespace, name, ordinal, locator),
            owner,
            namespace,
            name,
            ordinal,
            value_type,
            text,
            integer,
            real,
            boolean,
            json_value,
            state,
            authority,
            artifact,
            locator,
            consumer,
            canonical_json({"decoded_field": True, **(evidence or {})}),
        ),
    )


def _stage30_relation(
    connection: sqlite3.Connection,
    *,
    src: str,
    relation: str,
    dst: str,
    locator: str,
    artifact: str,
    state: str = "confirmed",
    required: int = 0,
    authority: str = "client_native",
    consumer: str | None = None,
    ordinal: int = 0,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO relations(
            relation_key,src_entity_key,relation,dst_entity_key,ordinal,
            cardinality,state,required,authority,source_artifact_key,locator,
            loader_or_consumer,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            stable_key("relation", src, relation, dst, ordinal, locator),
            src,
            relation,
            dst,
            ordinal,
            "one",
            state,
            required,
            authority,
            artifact,
            locator,
            consumer,
            TOOL_NAME,
            canonical_json({"foreign_key_value_observed": True}),
        ),
    )


def _stage30_endpoint(
    connection: sqlite3.Connection,
    *,
    kind: str,
    native_id: Any,
    state: str = "unknown",
    authority: str = "client_native",
    provenance: str = "referenced_endpoint",
) -> str:
    key = entity_key(kind, native_id)
    _insert_entity(
        connection,
        key=key,
        kind=kind,
        native_id=native_id,
        subtype=None,
        lifecycle="referenced",
        state=state,
        authority=authority,
        stage=30,
        provenance=provenance,
        evidence={"endpoint_materialized_for_graph_closure": True},
    )
    return key


def build_stage_30(context: BuildContext) -> dict[str, Any]:
    """Decode the native world-actor frontier and preserve its open boundaries."""

    def populate(
        destination: sqlite3.Connection, source: sqlite3.Connection
    ) -> None:
        source_hashes = _stage30_artifacts(destination, context)
        catalog_manifest = load_json(context.config.source_npc_catalog_manifest)
        character_data = load_json(context.config.source_character_data)
        faction_data = load_json(context.config.source_faction_data)
        spawner_layers = load_json(context.config.source_spawner_layers_manifest)
        spawner_absence = load_json(context.config.source_spawner_absence_manifest)
        client_compact = open_read_only(context.config.source_client_compact)
        try:
            native_localizations = {
                (
                    str(row["tbl_name"]),
                    str(row["tbl_column_name"]),
                    int(row["idx"]),
                    str(row["locale"]),
                ): str(row["text"])
                for row in client_compact.execute(
                    """
                    SELECT tbl_name,tbl_column_name,idx,text,locale
                    FROM localized_texts
                    WHERE (tbl_name='npcs' AND tbl_column_name='name')
                       OR (
                           tbl_name='system_factions'
                           AND tbl_column_name IN (
                               'name','desc_when_use_create_expedition'
                           )
                       )
                    ORDER BY tbl_name,tbl_column_name,idx,locale
                    """
                )
            }
        finally:
            client_compact.close()
        decoded = decode_catalog(
            context.config.source_game11,
            context.config.source_npc_catalog_manifest,
        )
        appearance = decode_appearance(context.config.source_game11)
        appearance_auxiliary = decode_appearance_auxiliary(
            context.config.source_game11
        )
        face_profiles = load_face_target_profiles(
            context.config.source_gamepak_xml_root
        )
        appearance_absence = audit_absent_appearance_results(
            context.config.source_cached_streams_dir
        )
        unexpected_color_results = {
            table: result["exact_layout_matches"]
            for table, result in appearance_absence["tables"].items()
            if result["exact_layout_match_count"]
        }
        if unexpected_color_results:
            raise RuntimeError(
                "Unexpected appearance-color result candidates: "
                + canonical_json(unexpected_color_results)
            )

        destination.execute(
            """
            INSERT INTO decoders(
                decoder_key,name,version,sha256,status,inputs_json,
                assumptions_json,provenance
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "stage30:decoder:cached-result-primitives",
                "world_actor_cached_result_reader",
                TOOL_VERSION,
                tree_digest(Path(__file__).resolve().parent),
                "confirmed",
                canonical_json(
                    {
                        "artifact": "stage30:game11",
                        "tables": sorted(
                            (
                                *decoded,
                                *appearance,
                                *appearance_auxiliary,
                                *ABSENT_APPEARANCE_SPECS,
                            )
                        ),
                        "types": [
                            "38",
                            "40",
                            "60",
                            "68",
                            "70",
                            "78",
                            "blob:128",
                        ],
                    }
                ),
                canonical_json(
                    {
                        "strict_boundaries": True,
                        "unresolved_strings_remain_blocked": True,
                        "modifier_layout": {
                            "container_offset_x64": "CustomModel+0xA8",
                            "payload_type": "int8[128]",
                            "slot_zero_reserved": True,
                            "x64_evidence": "stage30:ghidra-custom-model-x64",
                            "x86_evidence": "stage30:ghidra-custom-model-x86",
                            "target_profiles": len(face_profiles),
                            "ui_consumers": [
                                "stage30:customizing-modifier-lua:x64",
                                "stage30:customizing-modifier-lua:x86",
                            ],
                        },
                    }
                ),
                TOOL_NAME,
            ),
        )
        attach_seed = {
            "columns": "owner_type owner_id anim_action_id attach_point_id".split(),
            "layout": "78 68 68 68".split(),
            "start": 0x3D6B679,
            "done": 0x3D6CABE,
            "rows": 287,
            "first_reference": 150126,
            "next_reference": 150128,
            "values": {150126: "VehicleModel", 150127: "ShipModel"},
            "loader": "x2game.dll FUN_39a46b50",
        }
        destination.execute(
            """
            INSERT INTO query_specs(
                query_key,source_query_spec_id,table_name,source_module,
                sql_text,columns_json,layout_json,stream_name,start_offset,
                expected_rows,anchor_json,loader_consumer,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "stage30:query:attach_anims_string_seed",
                -30401,
                "attach_anims",
                "x2game.dll",
                (
                    "SELECT owner_type,owner_id,anim_action_id,attach_point_id "
                    "FROM attach_anims"
                ),
                canonical_json(attach_seed["columns"]),
                canonical_json(attach_seed["layout"]),
                "game11",
                attach_seed["start"],
                attach_seed["rows"],
                canonical_json(
                    {
                        "done_offset": attach_seed["done"],
                        "first_reference": attach_seed["first_reference"],
                        "next_reference": attach_seed["next_reference"],
                    }
                ),
                attach_seed["loader"],
                "confirmed",
                canonical_json(
                    {
                        "purpose": "model subtype global string seed",
                        "values": attach_seed["values"],
                        "self_reference_validation": True,
                    }
                ),
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
                "stage30:cached:attach_anims_string_seed",
                -30401,
                "stage30:query:attach_anims_string_seed",
                "stage30:game11",
                attach_seed["start"],
                attach_seed["done"],
                attach_seed["rows"],
                None,
                canonical_json(
                    {
                        "first_reference": attach_seed["first_reference"],
                        "next_reference": attach_seed["next_reference"],
                    }
                ),
                canonical_json({}),
                canonical_json(
                    {
                        "values": attach_seed["values"],
                        "consumer": attach_seed["loader"],
                    }
                ),
                "confirmed",
                None,
            ),
        )

        decoded_row_count = 0
        property_count = 0
        relation_count = 0
        entity_counts: dict[str, int] = {}
        table_kinds = {
            "actor_models": "actor_model",
            "models": "model",
            "npcs": "npc",
        }
        for query_index, table in enumerate(sorted(decoded), start=1):
            result = decoded[table]
            spec = catalog_manifest["tables"][table]
            query_key = f"stage30:query:{table}"
            destination.execute(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    query_key,
                    -30000 - query_index,
                    table,
                    "x2game.dll",
                    "SELECT " + ",".join(spec["columns"]) + f" FROM {table}",
                    canonical_json(spec["columns"]),
                    canonical_json(spec["layout"]),
                    "game11",
                    result.start,
                    len(result.rows),
                    canonical_json({"done_offset": result.done, "done_byte": 101}),
                    spec["loader"],
                    (
                        "blocked"
                        if result.unresolved_references
                        else "confirmed"
                    ),
                    canonical_json(
                        {
                            "sql_address": spec["sql_address"],
                            "native_filter": spec.get("native_filter"),
                        }
                    ),
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
                    f"stage30:cached:{table}",
                    -30000 - query_index,
                    query_key,
                    "stage30:game11",
                    result.start,
                    result.done,
                    len(result.rows),
                    result.digest,
                    canonical_json(result.token_counts),
                    canonical_json(result.unresolved_references),
                    canonical_json(
                        {
                            "first_reference": spec["string_cache"]["first_reference"],
                            "strict_done_boundary": True,
                            **result.resolution_evidence,
                        }
                    ),
                    (
                        "blocked"
                        if result.unresolved_references
                        else "confirmed"
                    ),
                    (
                        f"{sum(result.unresolved_references.values())} unresolved "
                        "global string references"
                        if result.unresolved_references
                        else None
                    ),
                ),
            )
            kind = table_kinds[table]
            for row_index, row in enumerate(result.rows):
                native_id = int(row["id"])
                key = entity_key(kind, native_id)
                destination.execute(
                    "INSERT INTO cached_result_rows(query_key,row_index,row_json) "
                    "VALUES(?,?,?)",
                    (query_key, row_index, canonical_json(row)),
                )
                _insert_entity(
                    destination,
                    key=key,
                    kind=kind,
                    native_id=native_id,
                    subtype=(str(row.get("sub_type")) if table == "models" else None),
                    lifecycle="present",
                    state="confirmed",
                    authority="client_native",
                    stage=30,
                    provenance="game11_cached_result",
                    evidence={"table": table, "row_index": row_index},
                )
                destination.execute(
                    """
                    INSERT INTO native_rows(
                        native_row_key,entity_key,entity_kind,native_id,source_table,
                        state,row_json,provenance,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        stable_key("native-row", table, native_id),
                        key,
                        kind,
                        str(native_id),
                        table,
                        "confirmed",
                        canonical_json(row),
                        "game11_cached_result",
                        canonical_json({"query_key": query_key, "row_index": row_index}),
                    ),
                )
                for column, value in sorted(row.items()):
                    field_state = "blocked" if unresolved_reference(value) else "confirmed"
                    _stage30_property(
                        destination,
                        owner=key,
                        namespace=table,
                        name=column,
                        value=value,
                        locator=f"{table}[{native_id}].{column}",
                        artifact="stage30:game11",
                        state=field_state,
                        consumer=spec["loader"],
                    )
                    property_count += 1
                decoded_row_count += 1
            entity_counts[kind] = len(result.rows)
            destination.execute(
                """
                INSERT INTO native_catalogs(
                    table_name,entity_kind,id_column,state,row_count,distinct_ids,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    table,
                    kind,
                    "id",
                    "confirmed",
                    len(result.rows),
                    len({int(row["id"]) for row in result.rows}),
                    "game11_cached_result",
                    canonical_json({"canonical_rows_sha256": result.digest}),
                ),
            )
            _add_validation(
                destination,
                scope_kind="source_table",
                scope_id=table,
                check_name="row_count_preserved",
                status="confirmed",
                evidence={
                    "source_rows": len(result.rows),
                    "imported_rows": len(result.rows),
                },
            )

        appearance_kinds = {
            "face_decal_assets": "face_decal_asset",
            "custom_face_presets": "custom_face_preset",
            "total_character_customs": "total_character_custom",
        }
        for query_index, table in enumerate(sorted(appearance), start=201):
            result = appearance[table]
            spec = APPEARANCE_SPECS[table]
            query_key = f"stage30:query:{table}"
            sql_text = (
                "SELECT " + ",".join(spec["columns"]) + f" FROM {table}"
            )
            destination.execute(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    query_key,
                    -30000 - query_index,
                    table,
                    "x2game.dll",
                    sql_text,
                    canonical_json(spec["columns"]),
                    canonical_json(spec["layout"]),
                    "game11",
                    result.start,
                    len(result.rows),
                    canonical_json(
                        {
                            "done_offset": result.done,
                            "done_byte": 101,
                            "next_result_header": True,
                        }
                    ),
                    spec["loader"],
                    "confirmed",
                    canonical_json(
                        {
                            "sql_address": spec["sql_address"],
                            "ghidra_artifact": "stage30:ghidra-sql-loaders-64",
                            "blob_accessor": (
                                {
                                    "vtable_offset": "0x50",
                                    "length_prefix": "uint32_le",
                                    "payload_bytes": 128,
                                    "consumer_copy_bytes": "0x80",
                                }
                                if "blob:128" in spec["layout"]
                                else None
                            ),
                        }
                    ),
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
                    f"stage30:cached:{table}",
                    -30000 - query_index,
                    query_key,
                    "stage30:game11",
                    result.start,
                    result.done,
                    len(result.rows),
                    result.digest,
                    canonical_json(result.token_counts),
                    canonical_json({}),
                    canonical_json(
                        {
                            "first_string_reference": spec["first_string_reference"],
                            "next_string_reference": spec["next_string_reference"],
                            "strict_done_boundary": True,
                        }
                    ),
                    "confirmed",
                    None,
                ),
            )
            kind = appearance_kinds[table]
            for row_index, row in enumerate(result.rows):
                native_id = int(row["id"])
                key = entity_key(kind, native_id)
                destination.execute(
                    "INSERT INTO cached_result_rows(query_key,row_index,row_json) "
                    "VALUES(?,?,?)",
                    (query_key, row_index, canonical_json(row)),
                )
                _insert_entity(
                    destination,
                    key=key,
                    kind=kind,
                    native_id=native_id,
                    subtype=None,
                    lifecycle="present",
                    state="confirmed",
                    authority="client_native",
                    stage=30,
                    provenance="game11_cached_result",
                    evidence={"table": table, "row_index": row_index},
                )
                destination.execute(
                    """
                    INSERT INTO native_rows(
                        native_row_key,entity_key,entity_kind,native_id,source_table,
                        state,row_json,provenance,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        stable_key("native-row", table, native_id),
                        key,
                        kind,
                        str(native_id),
                        table,
                        "confirmed",
                        canonical_json(row),
                        "game11_cached_result",
                        canonical_json(
                            {"query_key": query_key, "row_index": row_index}
                        ),
                    ),
                )
                for column, value in sorted(row.items()):
                    _stage30_property(
                        destination,
                        owner=key,
                        namespace=table,
                        name=column,
                        value=value,
                        locator=f"{table}[{native_id}].{column}",
                        artifact="stage30:game11",
                        consumer=spec["loader"],
                    )
                    property_count += 1
                decoded_row_count += 1
            entity_counts[kind] = len(result.rows)
            destination.execute(
                """
                INSERT INTO native_catalogs(
                    table_name,entity_kind,id_column,state,row_count,distinct_ids,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    table,
                    kind,
                    "id",
                    "confirmed",
                    len(result.rows),
                    len({int(row["id"]) for row in result.rows}),
                    "game11_cached_result",
                    canonical_json(
                        {
                            "canonical_rows_sha256": result.digest,
                            "ghidra_loader": spec["loader"],
                        }
                    ),
                ),
            )
            _add_validation(
                destination,
                scope_kind="source_table",
                scope_id=table,
                check_name="row_count_preserved",
                status="confirmed",
                evidence={
                    "source_rows": len(result.rows),
                    "imported_rows": len(result.rows),
                },
            )

        auxiliary_kinds = {
            "body_diffuse_maps": "body_diffuse_map",
            "body_normal_maps": "body_normal_map",
            "face_diffuse_maps": "face_diffuse_map",
            "face_normal_maps": "face_normal_map",
            "face_eyelash_maps": "face_eyelash_map",
            "customizing_item_assets": "customizing_item_asset",
            "custom_hair_textures": "custom_hair_texture",
        }
        for query_index, table in enumerate(
            sorted(appearance_auxiliary), start=251
        ):
            result = appearance_auxiliary[table]
            spec = APPEARANCE_AUXILIARY_SPECS[table]
            query_key = f"stage30:query:{table}"
            id_column = (
                "item_id" if table == "customizing_item_assets" else "id"
            )
            destination.execute(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    query_key,
                    -30000 - query_index,
                    table,
                    "x2game.dll",
                    "SELECT " + ",".join(spec["columns"]) + f" FROM {table}",
                    canonical_json(spec["columns"]),
                    canonical_json(spec["layout"]),
                    "game11",
                    result.start,
                    len(result.rows),
                    canonical_json(
                        {
                            "header_offset": spec["header"],
                            "done_offset": result.done,
                            "done_byte": 101,
                        }
                    ),
                    spec["loader"],
                    "confirmed",
                    canonical_json(
                        {
                            "ghidra_artifact": "stage30:ghidra-sql-loaders-64",
                            "task": spec["task"],
                            "sql_call_sequence_artifact": (
                                "stage30:ghidra-sql-call-sequence"
                            ),
                            "empty_result_is_authoritative": not result.rows,
                        }
                    ),
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
                    f"stage30:cached:{table}",
                    -30000 - query_index,
                    query_key,
                    "stage30:game11",
                    result.start,
                    result.done,
                    len(result.rows),
                    result.digest,
                    canonical_json(result.token_counts),
                    canonical_json(result.unresolved_references),
                    canonical_json(
                        {
                            "strict_done_boundary": True,
                            "map_string_cache_bootstrap": (
                                {
                                    "table": "common_farms",
                                    "first_reference": 392878,
                                    "next_reference": 392923,
                                    "final_reference": 393140,
                                }
                                if table.endswith("_maps")
                                else None
                            ),
                            "first_string_reference": spec.get(
                                "first_string_reference"
                            ),
                            "next_string_reference": spec.get(
                                "next_string_reference"
                            ),
                        }
                    ),
                    "confirmed",
                    None,
                ),
            )
            kind = auxiliary_kinds[table]
            for row_index, row in enumerate(result.rows):
                native_id = int(row[id_column])
                key = entity_key(kind, native_id)
                destination.execute(
                    "INSERT INTO cached_result_rows(query_key,row_index,row_json) "
                    "VALUES(?,?,?)",
                    (query_key, row_index, canonical_json(row)),
                )
                _insert_entity(
                    destination,
                    key=key,
                    kind=kind,
                    native_id=native_id,
                    subtype=None,
                    lifecycle="present",
                    state="confirmed",
                    authority="client_native",
                    stage=30,
                    provenance="game11_cached_result",
                    evidence={"table": table, "row_index": row_index},
                )
                destination.execute(
                    """
                    INSERT INTO native_rows(
                        native_row_key,entity_key,entity_kind,native_id,source_table,
                        state,row_json,provenance,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        stable_key("native-row", table, native_id),
                        key,
                        kind,
                        str(native_id),
                        table,
                        "confirmed",
                        canonical_json(row),
                        "game11_cached_result",
                        canonical_json(
                            {"query_key": query_key, "row_index": row_index}
                        ),
                    ),
                )
                for column, value in sorted(row.items()):
                    _stage30_property(
                        destination,
                        owner=key,
                        namespace=table,
                        name=column,
                        value=value,
                        locator=f"{table}[{native_id}].{column}",
                        artifact="stage30:game11",
                        consumer=spec["loader"],
                    )
                    property_count += 1
                decoded_row_count += 1
            entity_counts[kind] = len(result.rows)
            destination.execute(
                """
                INSERT INTO native_catalogs(
                    table_name,entity_kind,id_column,state,row_count,distinct_ids,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    table,
                    kind,
                    id_column,
                    "confirmed",
                    len(result.rows),
                    len({int(row[id_column]) for row in result.rows}),
                    "game11_cached_result",
                    canonical_json(
                        {
                            "canonical_rows_sha256": result.digest,
                            "ghidra_loader": spec["loader"],
                            "native_empty": not result.rows,
                        }
                    ),
                ),
            )
            _add_validation(
                destination,
                scope_kind="source_table",
                scope_id=table,
                check_name="row_count_preserved",
                status="confirmed",
                evidence={
                    "source_rows": len(result.rows),
                    "imported_rows": len(result.rows),
                },
            )

        # Resolve every native face-decal path against the frozen game_pak index.
        requested_asset_paths = {
            str(row["asset_path"]).replace("\\", "/").lower().lstrip("/")
            for row in appearance["face_decal_assets"].rows
            if row.get("asset_path")
        }
        indexed_assets: dict[str, dict[str, str]] = {}
        with context.config.source_gamepak_index.open(
            "r", encoding="utf-8", newline=""
        ) as stream:
            for index_row in csv.DictReader(stream, delimiter=";"):
                normalized = str(index_row["name"]).lower().lstrip("/")
                if normalized.startswith("game/"):
                    normalized = normalized[5:]
                if normalized in requested_asset_paths:
                    indexed_assets[normalized] = index_row
        missing_asset_paths = requested_asset_paths - set(indexed_assets)
        if missing_asset_paths:
            raise RuntimeError(
                "Face decal assets missing from frozen game_pak index: "
                + ", ".join(sorted(missing_asset_paths)[:10])
            )

        for row in appearance["face_decal_assets"].rows:
            native_id = int(row["id"])
            src = entity_key("face_decal_asset", native_id)
            asset_path = row.get("asset_path")
            if asset_path:
                normalized = (
                    str(asset_path).replace("\\", "/").lower().lstrip("/")
                )
                index_row = indexed_assets[normalized]
                asset_id = stable_key("asset-path", normalized)
                dst = _stage30_endpoint(
                    destination,
                    kind="asset_file",
                    native_id=asset_id,
                    state="confirmed",
                    authority="client_asset",
                    provenance="gamepak_full_index",
                )
                destination.execute(
                    """
                    INSERT OR IGNORE INTO assets(
                        asset_key,path,asset_type,sha256,state,source_artifact_key,
                        evidence_json
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        asset_id,
                        str(index_row["name"]),
                        "face_decal_texture",
                        None,
                        "confirmed",
                        "stage30:gamepak-index",
                        canonical_json(
                            {
                                "md5": index_row["md5"],
                                "offset": int(index_row["offset"]),
                                "size": int(index_row["size"]),
                            }
                        ),
                    ),
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation="uses_asset",
                    dst=dst,
                    locator=f"face_decal_assets[{native_id}].asset_path",
                    artifact="stage30:gamepak-index",
                    authority="client_asset",
                    required=1,
                )
                relation_count += 1
            for column, relation, dst_kind in (
                ("category_id", "belongs_to_category", "face_decal_category"),
                ("icon_id", "uses_icon", "icon"),
                ("item_id", "references_item", "item"),
                ("model_id", "uses_model", "model"),
            ):
                target_id = int(row.get(column) or 0)
                if target_id <= 0:
                    continue
                dst = _stage30_endpoint(
                    destination, kind=dst_kind, native_id=target_id
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation=relation,
                    dst=dst,
                    locator=f"face_decal_assets[{native_id}].{column}",
                    artifact="stage30:game11",
                    consumer=APPEARANCE_SPECS["face_decal_assets"]["loader"],
                )
                relation_count += 1

        auxiliary_asset_paths: dict[str, str] = {}
        for table, result in appearance_auxiliary.items():
            spec = APPEARANCE_AUXILIARY_SPECS[table]
            for row in result.rows:
                for column in spec["asset_columns"]:
                    value = row.get(column)
                    if not value:
                        continue
                    normalized = (
                        str(value).replace("\\", "/").lower().lstrip("/")
                    )
                    auxiliary_asset_paths[normalized] = str(value)
        auxiliary_indexed_assets: dict[str, dict[str, str]] = {}
        with context.config.source_gamepak_index.open(
            "r", encoding="utf-8", newline=""
        ) as stream:
            for index_row in csv.DictReader(stream, delimiter=";"):
                normalized = str(index_row["name"]).lower().lstrip("/")
                if normalized.startswith("game/"):
                    normalized = normalized[5:]
                if normalized in auxiliary_asset_paths:
                    auxiliary_indexed_assets[normalized] = index_row
        missing_auxiliary_asset_paths = set(auxiliary_asset_paths).difference(
            auxiliary_indexed_assets
        )

        for table, result in appearance_auxiliary.items():
            spec = APPEARANCE_AUXILIARY_SPECS[table]
            kind = auxiliary_kinds[table]
            id_column = (
                "item_id" if table == "customizing_item_assets" else "id"
            )
            for row in result.rows:
                native_id = int(row[id_column])
                src = entity_key(kind, native_id)
                for column in spec["asset_columns"]:
                    value = row.get(column)
                    if not value:
                        continue
                    normalized = (
                        str(value).replace("\\", "/").lower().lstrip("/")
                    )
                    index_row = auxiliary_indexed_assets.get(normalized)
                    is_missing = index_row is None
                    asset_id = stable_key("asset-path", normalized)
                    dst = _stage30_endpoint(
                        destination,
                        kind="asset_file",
                        native_id=asset_id,
                        state="missing" if is_missing else "confirmed",
                        authority=(
                            "client_native" if is_missing else "client_asset"
                        ),
                        provenance=(
                            "gamepak_full_index_negative"
                            if is_missing
                            else "gamepak_full_index"
                        ),
                    )
                    destination.execute(
                        """
                        INSERT OR IGNORE INTO assets(
                            asset_key,path,asset_type,sha256,state,
                            source_artifact_key,evidence_json
                        ) VALUES(?,?,?,?,?,?,?)
                        """,
                        (
                            asset_id,
                            (
                                str(value)
                                if is_missing
                                else str(index_row["name"])
                            ),
                            "appearance_texture",
                            None,
                            "missing" if is_missing else "confirmed",
                            (
                                "stage30:game11"
                                if is_missing
                                else "stage30:gamepak-index"
                            ),
                            canonical_json(
                                (
                                    {
                                        "gamepak_index_match": False,
                                        "normalized_path": normalized,
                                    }
                                    if is_missing
                                    else {
                                        "md5": index_row["md5"],
                                        "offset": int(index_row["offset"]),
                                        "size": int(index_row["size"]),
                                    }
                                )
                            ),
                        ),
                    )
                    _stage30_relation(
                        destination,
                        src=src,
                        relation=f"uses_{column}",
                        dst=dst,
                        locator=f"{table}[{native_id}].{column}",
                        artifact=(
                            "stage30:game11"
                            if is_missing
                            else "stage30:gamepak-index"
                        ),
                        state="missing" if is_missing else "confirmed",
                        authority=(
                            "client_native" if is_missing else "client_asset"
                        ),
                        required=1,
                        consumer=spec["loader"],
                    )
                    relation_count += 1
                for column, relation, dst_kind in (
                    ("icon_id", "uses_icon", "icon"),
                    ("model_id", "uses_model", "model"),
                    ("category_id", "belongs_to_category", "customizing_category"),
                ):
                    target_id = int(row.get(column) or 0)
                    if target_id <= 0:
                        continue
                    dst = _stage30_endpoint(
                        destination, kind=dst_kind, native_id=target_id
                    )
                    _stage30_relation(
                        destination,
                        src=src,
                        relation=relation,
                        dst=dst,
                        locator=f"{table}[{native_id}].{column}",
                        artifact="stage30:game11",
                        consumer=spec["loader"],
                    )
                    relation_count += 1
                if table == "customizing_item_assets":
                    dst = _stage30_endpoint(
                        destination, kind="item", native_id=native_id
                    )
                    _stage30_relation(
                        destination,
                        src=src,
                        relation="customizes_item",
                        dst=dst,
                        locator=f"{table}[{native_id}].item_id",
                        artifact="stage30:game11",
                        required=1,
                        consumer=spec["loader"],
                    )
                    relation_count += 1

        # Join item_body_parts from the existing item evidence to the newly
        # decoded custom-hair texture catalog.
        hair_texture_ids = {
            int(row["id"])
            for row in appearance_auxiliary["custom_hair_textures"].rows
        }
        referenced_hair_texture_ids: set[int] = set()
        body_part_rows = source.execute(
            """
            SELECT r.row_json
            FROM cached_result_rows r
            JOIN query_specs q ON q.query_spec_id=r.query_spec_id
            WHERE q.table_name='item_body_parts'
            ORDER BY r.row_index
            """
        )
        for source_row in body_part_rows:
            row = json.loads(source_row["row_json"])
            item_id = int(row["item_id"])
            src = _stage30_endpoint(
                destination,
                kind="item",
                native_id=item_id,
                state="confirmed",
                authority="client_native",
                provenance="item_forensics_item_body_parts",
            )
            for texture_index, column in enumerate(
                (
                    "custom_texture_id",
                    "custom_texture_1_id",
                    "custom_texture_2_id",
                    "custom_texture_3_id",
                    "custom_texture_4_id",
                )
            ):
                target_id = int(row.get(column) or 0)
                if target_id <= 0:
                    continue
                referenced_hair_texture_ids.add(target_id)
                is_missing = target_id not in hair_texture_ids
                dst = _stage30_endpoint(
                    destination,
                    kind="custom_hair_texture",
                    native_id=target_id,
                    state="missing" if is_missing else "unknown",
                    provenance="item_body_parts_reference",
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation="uses_custom_hair_texture",
                    dst=dst,
                    ordinal=texture_index,
                    locator=f"item_body_parts[{item_id}].{column}",
                    artifact=SOURCE_ARTIFACT_KEY,
                    state="missing" if is_missing else "confirmed",
                    consumer=APPEARANCE_AUXILIARY_SPECS[
                        "custom_hair_textures"
                    ]["loader"],
                )
                relation_count += 1

        for row in appearance["custom_face_presets"].rows:
            native_id = int(row["id"])
            src = entity_key("custom_face_preset", native_id)
            for column, relation, dst_kind in (
                ("face_morph_type_id", "uses_face_morph_type", "face_morph_type"),
                ("icon_id", "uses_icon", "icon"),
                ("model_id", "uses_model", "model"),
            ):
                target_id = int(row.get(column) or 0)
                if target_id <= 0:
                    continue
                dst = _stage30_endpoint(
                    destination, kind=dst_kind, native_id=target_id
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation=relation,
                    dst=dst,
                    locator=f"custom_face_presets[{native_id}].{column}",
                    artifact="stage30:game11",
                    consumer=APPEARANCE_SPECS["custom_face_presets"]["loader"],
                )
                relation_count += 1

        face_decal_ids = {
            int(row["id"]) for row in appearance["face_decal_assets"].rows
        }
        customizing_item_asset_ids = {
            int(row["item_id"])
            for row in appearance_auxiliary["customizing_item_assets"].rows
        }
        custom_relation_specs = (
            ("body_normal_map_id", "uses_body_normal_map", "body_normal_map"),
            ("body_id", "uses_body_item", "item"),
            ("face_diffuse_map_id", "uses_face_diffuse_map", "face_diffuse_map"),
            ("face_eyelash_map_id", "uses_face_eyelash_map", "face_eyelash_map"),
            ("face_normal_map_id", "uses_face_normal_map", "face_normal_map"),
            ("face_id", "uses_face_item", "item"),
            ("hair_color_id", "uses_hair_color", "customizing_item_asset_color"),
            ("hair_id", "uses_hair_item", "item"),
            ("horn_color_id", "uses_horn_color", "customizing_item_asset_color"),
            ("horn_id", "uses_horn_item", "item"),
            ("icon_id", "uses_icon", "icon"),
            ("model_id", "uses_model", "model"),
            ("skin_color_id", "uses_skin_color", "skin_color"),
        )
        missing_decal_references: set[int] = set()
        missing_customizing_item_assets: set[int] = set()
        for row in appearance["total_character_customs"].rows:
            native_id = int(row["id"])
            src = entity_key("total_character_custom", native_id)
            for column, relation, dst_kind in custom_relation_specs:
                target_id = int(row.get(column) or 0)
                if target_id <= 0:
                    continue
                dst = _stage30_endpoint(
                    destination, kind=dst_kind, native_id=target_id
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation=relation,
                    dst=dst,
                    locator=f"total_character_customs[{native_id}].{column}",
                    artifact="stage30:game11",
                    consumer=APPEARANCE_SPECS["total_character_customs"]["loader"],
                )
                relation_count += 1
            for column, relation in (
                ("hair_id", "uses_hair_customizing_asset"),
                ("horn_id", "uses_horn_customizing_asset"),
            ):
                target_id = int(row.get(column) or 0)
                if target_id <= 0:
                    continue
                is_missing = target_id not in customizing_item_asset_ids
                if is_missing:
                    missing_customizing_item_assets.add(target_id)
                dst = _stage30_endpoint(
                    destination,
                    kind="customizing_item_asset",
                    native_id=target_id,
                    state="missing" if is_missing else "unknown",
                    provenance="total_character_customs_reference",
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation=relation,
                    dst=dst,
                    locator=f"total_character_customs[{native_id}].{column}",
                    artifact="stage30:game11",
                    state="missing" if is_missing else "confirmed",
                    consumer=APPEARANCE_SPECS[
                        "total_character_customs"
                    ]["loader"],
                )
                relation_count += 1
            for decal_index in range(6):
                column = f"face_fixed_decal_asset_{decal_index}_id"
                target_id = int(row.get(column) or 0)
                if target_id <= 0:
                    continue
                is_missing = target_id not in face_decal_ids
                if is_missing:
                    missing_decal_references.add(target_id)
                dst = _stage30_endpoint(
                    destination,
                    kind="face_decal_asset",
                    native_id=target_id,
                    state="missing" if is_missing else "unknown",
                    provenance="total_character_customs_reference",
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation="uses_fixed_face_decal",
                    dst=dst,
                    ordinal=decal_index,
                    locator=f"total_character_customs[{native_id}].{column}",
                    artifact="stage30:game11",
                    state="missing" if is_missing else "confirmed",
                    consumer=APPEARANCE_SPECS["total_character_customs"]["loader"],
                )
                relation_count += 1
            movable_id = int(row.get("face_movable_decal_asset_id") or 0)
            if movable_id > 0:
                is_missing = movable_id not in face_decal_ids
                if is_missing:
                    missing_decal_references.add(movable_id)
                dst = _stage30_endpoint(
                    destination,
                    kind="face_decal_asset",
                    native_id=movable_id,
                    state="missing" if is_missing else "unknown",
                    provenance="total_character_customs_reference",
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation="uses_movable_face_decal",
                    dst=dst,
                    locator=(
                        f"total_character_customs[{native_id}]"
                        ".face_movable_decal_asset_id"
                    ),
                    artifact="stage30:game11",
                    state="missing" if is_missing else "confirmed",
                    consumer=APPEARANCE_SPECS["total_character_customs"]["loader"],
                )
                relation_count += 1

        missing_map_relations = int(
            destination.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities e ON e.entity_key=r.dst_entity_key
                WHERE r.relation IN (
                    'uses_body_normal_map',
                    'uses_face_diffuse_map',
                    'uses_face_eyelash_map',
                    'uses_face_normal_map'
                )
                  AND e.state!='confirmed'
                """
            ).fetchone()[0]
        )
        if missing_map_relations:
            raise RuntimeError(
                f"Appearance map closure has {missing_map_relations} missing edge(s)"
            )
        _add_validation(
            destination,
            scope_kind="appearance",
            scope_id="map_catalogs",
            check_name="referenced_ids_close",
            status="confirmed",
            evidence={"missing_map_relations": missing_map_relations},
        )
        missing_hair_texture_ids = referenced_hair_texture_ids.difference(
            hair_texture_ids
        )
        if missing_hair_texture_ids:
            raise RuntimeError(
                "Missing custom-hair texture IDs: "
                + ",".join(str(value) for value in sorted(missing_hair_texture_ids))
            )
        _add_validation(
            destination,
            scope_kind="appearance",
            scope_id="custom_hair_textures",
            check_name="item_body_part_references_close",
            status="confirmed",
            evidence={
                "referenced_ids": len(referenced_hair_texture_ids),
                "missing_ids": [],
            },
        )
        _add_validation(
            destination,
            scope_kind="appearance",
            scope_id="color_catalogs",
            check_name="all_stream_exact_layout_audit",
            status="confirmed",
            evidence=appearance_absence,
        )
        _add_validation(
            destination,
            scope_kind="appearance",
            scope_id="texture_assets",
            check_name="frozen_gamepak_path_closure",
            status=(
                "blocked" if missing_auxiliary_asset_paths else "confirmed"
            ),
            evidence={
                "unique_paths": len(auxiliary_asset_paths),
                "matched_paths": len(auxiliary_indexed_assets),
                "missing_paths": sorted(missing_auxiliary_asset_paths),
            },
        )

        # Close each exact model subtype and actor model -> visual asset.
        for row in decoded["models"].rows:
            subtype = str(row.get("sub_type"))
            subtype_relation = {
                "ActorModel": ("uses_actor_model", "actor_model"),
                "VehicleModel": ("uses_vehicle_model", "vehicle_model"),
                "ShipModel": ("uses_ship_model", "ship_model"),
                "PrefabModel": ("uses_prefab_model", "prefab_model"),
            }.get(subtype)
            sub_id = int(row.get("sub_id") or 0)
            if subtype_relation is None or sub_id <= 0:
                continue
            relation, destination_kind = subtype_relation
            src = entity_key("model", row["id"])
            dst = _stage30_endpoint(
                destination,
                kind=destination_kind,
                native_id=sub_id,
            )
            _stage30_relation(
                destination,
                src=src,
                relation=relation,
                dst=dst,
                locator=f"models[{row['id']}].sub_id",
                artifact="stage30:game11",
                required=1,
                consumer=catalog_manifest["tables"]["models"]["loader"],
            )
            relation_count += 1
        for row in decoded["actor_models"].rows:
            model_file = row.get("model_file")
            if not model_file or unresolved_reference(model_file):
                continue
            src = entity_key("actor_model", row["id"])
            asset_id = stable_key("asset-path", str(model_file).lower())
            dst = _stage30_endpoint(
                destination,
                kind="asset_file",
                native_id=asset_id,
                state="corroborated",
                authority="client_asset",
                provenance="actor_models.model_file",
            )
            destination.execute(
                """
                INSERT OR IGNORE INTO assets(
                    asset_key,path,asset_type,sha256,state,source_artifact_key,
                    evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    asset_id,
                    str(model_file),
                    "character_model",
                    None,
                    "corroborated",
                    "stage30:game11",
                    canonical_json({"path_reference_confirmed": True}),
                ),
            )
            _stage30_relation(
                destination,
                src=src,
                relation="uses_asset",
                dst=dst,
                locator=f"actor_models[{row['id']}].model_file",
                artifact="stage30:game11",
                authority="client_asset",
            )
            relation_count += 1

        # The CustomModel payload is an index-native signed int8[128].  The
        # XML profiles name the indices exposed by the client customizer.  A
        # model reaches its profile only through its exact
        # model -> ActorModel -> model_file chain.
        profile_targets: dict[str, dict[int, dict[str, Any]]] = {}
        for profile_key, profile in face_profiles.items():
            profile_entity = entity_key("face_target_profile", profile_key)
            profile_artifact = (
                f"stage30:face-target-profile:{profile.code}"
            )
            _insert_entity(
                destination,
                key=profile_entity,
                kind="face_target_profile",
                native_id=profile_key,
                subtype=profile.race,
                lifecycle="present",
                state="confirmed",
                authority="client_asset",
                stage=30,
                provenance="game_pak_face_target_xml",
                evidence={
                    "relative_path": profile.relative_path,
                    "target_count": len(profile.targets),
                },
            )
            profile_row = {
                "profile_key": profile_key,
                "race": profile.race,
                "gender": profile.gender,
                "code": profile.code,
                "relative_path": profile.relative_path,
                "assets": list(profile.assets),
                "targets": list(profile.targets),
            }
            destination.execute(
                """
                INSERT INTO native_rows(
                    native_row_key,entity_key,entity_kind,native_id,source_table,
                    state,row_json,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("native-row", "face_target_profiles", profile_key),
                    profile_entity,
                    "face_target_profile",
                    profile_key,
                    "game_pak_face_target_profiles",
                    "confirmed",
                    canonical_json(profile_row),
                    "game_pak_face_target_xml",
                    canonical_json({"artifact": profile_artifact}),
                ),
            )
            for name, value in (
                ("race", profile.race),
                ("gender", profile.gender),
                ("code", profile.code),
                ("relative_path", profile.relative_path),
                ("assets", list(profile.assets)),
                ("target_count", len(profile.targets)),
            ):
                _stage30_property(
                    destination,
                    owner=profile_entity,
                    namespace="face_target_profile",
                    name=name,
                    value=value,
                    locator=f"{profile.relative_path}#{name}",
                    artifact=profile_artifact,
                    authority="client_asset",
                )
                property_count += 1
            targets_by_index: dict[int, dict[str, Any]] = {}
            for target in profile.targets:
                target_index = int(target["Idx"])
                targets_by_index[target_index] = target
                target_native_id = f"{profile_key}:{target_index}"
                target_entity = entity_key("face_target", target_native_id)
                _insert_entity(
                    destination,
                    key=target_entity,
                    kind="face_target",
                    native_id=target_native_id,
                    subtype=str(target.get("Category") or "none"),
                    lifecycle="present",
                    state="confirmed",
                    authority="client_asset",
                    stage=30,
                    provenance="game_pak_face_target_xml",
                    evidence={
                        "profile_key": profile_key,
                        "index": target_index,
                    },
                )
                for name, value in sorted(target.items()):
                    _stage30_property(
                        destination,
                        owner=target_entity,
                        namespace="face_target",
                        name=name,
                        value=value,
                        locator=(
                            f"{profile.relative_path}"
                            f"#Targets/Target[@Idx='{target_index}']/{name}"
                        ),
                        artifact=profile_artifact,
                        authority="client_asset",
                    )
                    property_count += 1
                _stage30_relation(
                    destination,
                    src=profile_entity,
                    relation="defines_face_target",
                    dst=target_entity,
                    ordinal=target_index,
                    locator=(
                        f"{profile.relative_path}"
                        f"#Targets/Target[@Idx='{target_index}']"
                    ),
                    artifact=profile_artifact,
                    authority="client_asset",
                    required=1,
                    consumer="X2Customizer face-target API",
                )
                relation_count += 1
            profile_targets[profile_key] = targets_by_index

        actor_profile_by_id: dict[int, str] = {}
        for row in decoded["actor_models"].rows:
            model_file = row.get("model_file")
            if not model_file or unresolved_reference(model_file):
                continue
            profile_key = face_profile_key_from_model_file(str(model_file))
            if profile_key in face_profiles:
                actor_id = int(row["id"])
                actor_profile_by_id[actor_id] = str(profile_key)
                _stage30_relation(
                    destination,
                    src=entity_key("actor_model", actor_id),
                    relation="uses_face_target_profile",
                    dst=entity_key("face_target_profile", profile_key),
                    locator=f"actor_models[{actor_id}].model_file",
                    artifact="stage30:game11",
                    authority="client_asset",
                    consumer="X2Customizer face-target API",
                )
                relation_count += 1

        model_profile_by_id: dict[int, str] = {}
        for row in decoded["models"].rows:
            if str(row.get("sub_type")) != "ActorModel":
                continue
            profile_key = actor_profile_by_id.get(int(row.get("sub_id") or 0))
            if profile_key is None:
                continue
            model_id = int(row["id"])
            model_profile_by_id[model_id] = profile_key
            _stage30_relation(
                destination,
                src=entity_key("model", model_id),
                relation="uses_face_target_profile",
                dst=entity_key("face_target_profile", profile_key),
                locator=f"models[{model_id}].sub_id",
                artifact="stage30:game11",
                consumer="X2Customizer face-target API",
            )
            relation_count += 1

        modifier_rows = [
            ("custom_face_presets", "custom_face_preset", row)
            for row in appearance["custom_face_presets"].rows
        ] + [
            ("total_character_customs", "total_character_custom", row)
            for row in appearance["total_character_customs"].rows
        ]
        unmapped_modifier_slots: Counter[tuple[str, int]] = Counter()
        reserved_slot_violations: list[dict[str, Any]] = []
        modifier_profile_rows = Counter()
        for table, kind, row in modifier_rows:
            native_id = int(row["id"])
            owner = entity_key(kind, native_id)
            model_id = int(row["model_id"])
            profile_key = model_profile_by_id.get(model_id)
            if profile_key is None:
                raise RuntimeError(
                    f"{table}[{native_id}] model {model_id} has no face profile"
                )
            modifier_profile_rows[profile_key] += 1
            profile_entity = entity_key("face_target_profile", profile_key)
            _stage30_relation(
                destination,
                src=owner,
                relation="uses_face_target_profile",
                dst=profile_entity,
                locator=f"{table}[{native_id}].model_id",
                artifact="stage30:game11",
                required=1,
                consumer="X2Customizer face-target API",
            )
            relation_count += 1
            values = decode_signed_modifier(row["modifier"])
            if values[0] != 0:
                reserved_slot_violations.append(
                    {"table": table, "id": native_id, "value": values[0]}
                )
            targets = profile_targets[profile_key]
            for slot, value in enumerate(values):
                target = targets.get(slot)
                if slot == 0:
                    name = "reserved_slot_000"
                    field_state = "confirmed"
                elif target is not None:
                    name = str(target["Name"])
                    field_state = "confirmed"
                elif value == 0:
                    name = f"unused_slot_{slot:03d}"
                    field_state = "not_applicable"
                else:
                    name = f"opaque_slot_{slot:03d}"
                    field_state = "blocked"
                    unmapped_modifier_slots[(profile_key, slot)] += 1
                _stage30_property(
                    destination,
                    owner=owner,
                    namespace="modifier_int8",
                    name=name,
                    value=value,
                    ordinal=slot,
                    locator=f"{table}[{native_id}].modifier[{slot}]",
                    artifact="stage30:game11",
                    state=field_state,
                    consumer="CustomModel serializer + X2Customizer face-target API",
                    evidence={
                        "payload_type": "int8[128]",
                        "byte_offset": slot,
                        "profile_key": profile_key,
                        "target": target,
                        "x64_layout": "stage30:ghidra-custom-model-x64",
                        "x86_layout": "stage30:ghidra-custom-model-x86",
                    },
                )
                property_count += 1
        if reserved_slot_violations:
            raise RuntimeError(
                "CustomModel reserved modifier slot 0 is non-zero: "
                + canonical_json(reserved_slot_violations[:10])
            )
        _add_validation(
            destination,
            scope_kind="appearance",
            scope_id="modifier_int8",
            check_name="layout_and_profile_projection",
            status="blocked" if unmapped_modifier_slots else "confirmed",
            evidence={
                "payload_type": "int8[128]",
                "rows": len(modifier_rows),
                "profile_rows": dict(sorted(modifier_profile_rows.items())),
                "reserved_slot_zero_violations": 0,
                "mapped_profile_slot_count": sum(
                    len(value) for value in profile_targets.values()
                ),
                "unmapped_nonzero_profile_slots": [
                    {
                        "profile_key": profile_key,
                        "slot": slot,
                        "occurrences": count,
                    }
                    for (profile_key, slot), count in sorted(
                        unmapped_modifier_slots.items()
                    )
                ],
            },
        )
        entity_counts["face_target_profile"] = len(face_profiles)
        entity_counts["face_target"] = sum(
            len(value) for value in profile_targets.values()
        )

        # Native character templates and their equipment packs provide appearance
        # endpoints shared by NPC model/customization analysis.
        character_tables = character_data["tables"]
        for table, kind in (
            ("equip_pack_cloths", "equip_pack_cloths"),
            ("equip_pack_weapons", "equip_pack_weapons"),
            ("characters", "character_template"),
        ):
            rows = character_tables[table]
            for row_index, row in enumerate(rows):
                native_id = int(row["id"])
                key = entity_key(kind, native_id)
                _insert_entity(
                    destination,
                    key=key,
                    kind=kind,
                    native_id=native_id,
                    subtype=None,
                    lifecycle="present",
                    state="confirmed",
                    authority="client_native",
                    stage=30,
                    provenance="native_character_creation_extract",
                    evidence={"table": table, "row_index": row_index},
                )
                destination.execute(
                    """
                    INSERT INTO native_rows(
                        native_row_key,entity_key,entity_kind,native_id,source_table,
                        state,row_json,provenance,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        stable_key("native-row", table, native_id),
                        key,
                        kind,
                        str(native_id),
                        table,
                        "confirmed",
                        canonical_json(row),
                        "native_character_creation_extract",
                        canonical_json({"row_index": row_index}),
                    ),
                )
                for column, value in sorted(row.items()):
                    _stage30_property(
                        destination,
                        owner=key,
                        namespace=table,
                        name=column,
                        value=value,
                        locator=f"{table}[{native_id}].{column}",
                        artifact="stage30:character-data",
                    )
                    property_count += 1
                if table == "characters":
                    for column, (relation, dst_kind) in CHARACTER_RELATIONS.items():
                        target_id = int(row.get(column) or 0)
                        if target_id <= 0:
                            continue
                        dst = _stage30_endpoint(
                            destination, kind=dst_kind, native_id=target_id
                        )
                        _stage30_relation(
                            destination,
                            src=key,
                            relation=relation,
                            dst=dst,
                            locator=f"characters[{native_id}].{column}",
                            artifact="stage30:character-data",
                        )
                        relation_count += 1
            entity_counts[kind] = len(rows)
            destination.execute(
                """
                INSERT INTO native_catalogs(
                    table_name,entity_kind,id_column,state,row_count,distinct_ids,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    table,
                    kind,
                    "id",
                    "confirmed",
                    len(rows),
                    len({int(row["id"]) for row in rows}),
                    "native_character_creation_extract",
                    canonical_json({"artifact": "stage30:character-data"}),
                ),
            )
            _add_validation(
                destination,
                scope_kind="source_table",
                scope_id=table,
                check_name="row_count_preserved",
                status="confirmed",
                evidence={"source_rows": len(rows), "imported_rows": len(rows)},
            )

        # Native system factions.
        faction_rows = faction_data["rows"]
        for row_index, row in enumerate(faction_rows):
            native_id = int(row["id"])
            key = entity_key("system_faction", native_id)
            _insert_entity(
                destination,
                key=key,
                kind="system_faction",
                native_id=native_id,
                subtype=None,
                lifecycle="present",
                state="confirmed",
                authority="client_native",
                stage=30,
                provenance="native_system_faction_extract",
                evidence={"row_index": row_index},
            )
            destination.execute(
                """
                INSERT INTO native_rows(
                    native_row_key,entity_key,entity_kind,native_id,source_table,
                    state,row_json,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("native-row", "system_factions", native_id),
                    key,
                    "system_faction",
                    str(native_id),
                    "system_factions",
                    "confirmed",
                    canonical_json(row),
                    "native_system_faction_extract",
                    canonical_json({"row_index": row_index}),
                ),
            )
            for column, value in sorted(row.items()):
                _stage30_property(
                    destination,
                    owner=key,
                    namespace="system_factions",
                    name=column,
                    value=value,
                    locator=f"system_factions[{native_id}].{column}",
                    artifact="stage30:faction-data",
                    state="blocked" if unresolved_reference(value) else "confirmed",
                )
                property_count += 1
            for localized_column in (
                "name",
                "desc_when_use_create_expedition",
            ):
                localized_value = native_localizations.get(
                    (
                        "system_factions",
                        localized_column,
                        native_id,
                        "en_us",
                    )
                )
                if localized_value is None:
                    continue
                localization_key = stable_key(
                    "localization",
                    key,
                    localized_column,
                    "en_us",
                )
                destination.execute(
                    """
                    INSERT INTO localizations(
                        localization_key,locale,text_value,entity_key,state,
                        source_artifact_key,evidence_json
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        localization_key,
                        "en_us",
                        localized_value,
                        key,
                        "confirmed",
                        "stage30:client-compact",
                        canonical_json(
                            {
                                "table": "system_factions",
                                "column": localized_column,
                                "idx": native_id,
                            }
                        ),
                    ),
                )
                _stage30_property(
                    destination,
                    owner=key,
                    namespace="localized_text",
                    name=localized_column,
                    value=localized_value,
                    locator=(
                        "localized_texts[system_factions,"
                        f"{localized_column},{native_id},en_us]"
                    ),
                    artifact="stage30:client-compact",
                    evidence={"locale": "en_us"},
                )
                property_count += 1
            mother_id = int(row.get("mother_id") or 0)
            if mother_id > 0:
                dst = _stage30_endpoint(
                    destination, kind="system_faction", native_id=mother_id
                )
                _stage30_relation(
                    destination,
                    src=key,
                    relation="has_mother_faction",
                    dst=dst,
                    locator=f"system_factions[{native_id}].mother_id",
                    artifact="stage30:faction-data",
                )
                relation_count += 1
        entity_counts["system_faction"] = len(faction_rows)
        destination.execute(
            """
            INSERT INTO native_catalogs(
                table_name,entity_kind,id_column,state,row_count,distinct_ids,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "system_factions",
                "system_faction",
                "id",
                "confirmed",
                len(faction_rows),
                len({int(row["id"]) for row in faction_rows}),
                "native_system_faction_extract",
                canonical_json({"artifact": "stage30:faction-data"}),
            ),
        )
        _add_validation(
            destination,
            scope_kind="source_table",
            scope_id="system_factions",
            check_name="row_count_preserved",
            status="confirmed",
            evidence={"source_rows": len(faction_rows), "imported_rows": len(faction_rows)},
        )

        # NPC dependency closure. Endpoints intentionally remain unknown until the
        # owning stage decodes the corresponding native table.
        for row in decoded["npcs"].rows:
            src = entity_key("npc", row["id"])
            npc_id = int(row["id"])
            localized_name = native_localizations.get(
                ("npcs", "name", npc_id, "en_us")
            )
            if localized_name is None:
                raise RuntimeError(
                    f"Client compact has no en_us NPC name for {npc_id}"
                )
            destination.execute(
                """
                INSERT INTO localizations(
                    localization_key,locale,text_value,entity_key,state,
                    source_artifact_key,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    stable_key("localization", src, "name", "en_us"),
                    "en_us",
                    localized_name,
                    src,
                    "confirmed",
                    "stage30:client-compact",
                    canonical_json(
                        {
                            "table": "npcs",
                            "column": "name",
                            "idx": npc_id,
                        }
                    ),
                ),
            )
            _stage30_property(
                destination,
                owner=src,
                namespace="localized_text",
                name="name",
                value=localized_name,
                locator=f"localized_texts[npcs,name,{npc_id},en_us]",
                artifact="stage30:client-compact",
                evidence={"locale": "en_us"},
            )
            property_count += 1
            for column, (relation, dst_kind) in NPC_RELATIONS.items():
                target_id = int(row.get(column) or 0)
                if target_id <= 0:
                    continue
                dst = _stage30_endpoint(
                    destination, kind=dst_kind, native_id=target_id
                )
                _stage30_relation(
                    destination,
                    src=src,
                    relation=relation,
                    dst=dst,
                    locator=f"npcs[{row['id']}].{column}",
                    artifact="stage30:game11",
                    required=column == "model_id",
                    consumer=catalog_manifest["tables"]["npcs"]["loader"],
                )
                relation_count += 1
        localized_npc_count = int(
            destination.execute(
                """
                SELECT COUNT(*) FROM localizations l
                JOIN entities e ON e.entity_key=l.entity_key
                WHERE e.kind='npc' AND l.locale='en_us'
                """
            ).fetchone()[0]
        )
        if localized_npc_count != len(decoded["npcs"].rows):
            raise RuntimeError(
                "NPC localization closure mismatch: "
                f"{localized_npc_count} != {len(decoded['npcs'].rows)}"
            )
        _add_validation(
            destination,
            scope_kind="npc",
            scope_id="all",
            check_name="en_us_localization_closure",
            status="confirmed",
            evidence={
                "npc_rows": len(decoded["npcs"].rows),
                "localized_names": localized_npc_count,
                "missing": 0,
            },
        )

        # Game-pak layer rows are placement evidence, not an active spawn catalog.
        spawner_rows = spawner_layers["spawners"]
        for row_index, row in enumerate(spawner_rows):
            spawner_id = int(row["object"]["spawnerId"])
            occurrence_id = f"{spawner_id}@{row['source']}#{row_index}"
            key = entity_key("spawner_evidence", occurrence_id)
            _insert_entity(
                destination,
                key=key,
                kind="spawner_evidence",
                native_id=occurrence_id,
                subtype=str(row["object"]["Type"]),
                lifecycle="observed_asset_layer",
                state="corroborated",
                authority="client_asset",
                stage=30,
                provenance="game_pak_layer",
                evidence={"spawner_id": spawner_id, "source": row["source"]},
            )
            destination.execute(
                """
                INSERT INTO native_rows(
                    native_row_key,entity_key,entity_kind,native_id,source_table,
                    state,row_json,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("native-row", "gamepak_spawner_layers", occurrence_id),
                    key,
                    "spawner_evidence",
                    occurrence_id,
                    "gamepak_spawner_layers",
                    "corroborated",
                    canonical_json(row),
                    "game_pak_layer",
                    canonical_json({"runtime_authority": False}),
                ),
            )
            for column in ("Pos", "Rotate", "Layer", "Type", "Name"):
                _stage30_property(
                    destination,
                    owner=key,
                    namespace="gamepak_spawner",
                    name=column.lower(),
                    value=row["object"].get(column),
                    locator=f"{row['source']}#{row_index}.{column}",
                    artifact="stage30:spawner-layers",
                    state="corroborated",
                    authority="client_asset",
                )
                property_count += 1
            if str(row["object"]["Type"]) == "NpcPointSpawner":
                npc_id = int(row["label_primary_id"])
                dst = _stage30_endpoint(
                    destination,
                    kind="npc",
                    native_id=npc_id,
                    state="confirmed",
                    authority="client_native",
                    provenance="native_npc_catalog",
                )
                _stage30_relation(
                    destination,
                    src=key,
                    relation="places_npc",
                    dst=dst,
                    locator=f"{row['source']}#{row_index}.label_primary_id",
                    artifact="stage30:spawner-layers",
                    state="corroborated",
                    authority="client_asset",
                )
                relation_count += 1
        entity_counts["spawner_evidence"] = len(spawner_rows)
        destination.execute(
            """
            INSERT INTO native_catalogs(
                table_name,entity_kind,id_column,state,row_count,distinct_ids,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "gamepak_spawner_layers",
                "spawner_evidence",
                "spawnerId+source+row",
                "corroborated",
                len(spawner_rows),
                len(
                    {
                        (
                            int(row["object"]["spawnerId"]),
                            str(row["source"]),
                            index,
                        )
                        for index, row in enumerate(spawner_rows)
                    }
                ),
                "game_pak_layer",
                canonical_json(spawner_layers["summary"]),
            ),
        )
        _add_validation(
            destination,
            scope_kind="source_table",
            scope_id="gamepak_spawner_layers",
            check_name="row_count_preserved",
            status="confirmed",
            evidence={"source_rows": len(spawner_rows), "imported_rows": len(spawner_rows)},
        )

        # Preserve exact negative evidence for the two native spawner tables.
        for index, table in enumerate(("npc_spawners", "npc_spawner_npcs"), start=1):
            spec = spawner_absence["layouts"][table]
            query_key = f"stage30:query:{table}"
            destination.execute(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    query_key,
                    -30100 - index,
                    table,
                    "x2game.dll",
                    "SELECT " + ",".join(spec["columns"]) + f" FROM {table}",
                    canonical_json(spec["columns"]),
                    canonical_json(spec["layout"]),
                    None,
                    None,
                    None,
                    canonical_json({}),
                    spec["loader"],
                    "blocked",
                    canonical_json(
                        {
                            "sql_address": spec["sql_address"],
                            "absence_audit": "stage30:spawner-absence",
                        }
                    ),
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
                    f"stage30:cached:{table}",
                    -30100 - index,
                    query_key,
                    "stage30:spawner-absence",
                    None,
                    None,
                    0,
                    None,
                    canonical_json({}),
                    canonical_json({}),
                    canonical_json(spawner_absence["result"]),
                    "blocked",
                    "native_result_absent from all non-empty decrypted client streams",
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
                    f"stage30:opaque:{table}",
                    table,
                    "game0,game2,game6,game7,game11",
                    "native_result_absent",
                    spawner_absence["result"]["conclusion"],
                    canonical_json(
                        {
                            "streams": spawner_absence["streams"],
                            "scope_limit": spawner_absence["result"]["scope_limit"],
                        }
                    ),
                    30,
                    "opaque",
                ),
            )

        # The color loaders and layouts are exact, but neither query emitted a
        # non-empty cached result in any decrypted game stream.
        for index, (table, spec) in enumerate(
            sorted(ABSENT_APPEARANCE_SPECS.items()), start=1
        ):
            query_key = f"stage30:query:{table}"
            audit = appearance_absence["tables"][table]
            destination.execute(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    query_key,
                    -30300 - index,
                    table,
                    "x2game.dll",
                    "SELECT " + ",".join(spec["columns"]) + f" FROM {table}",
                    canonical_json(spec["columns"]),
                    canonical_json(spec["layout"]),
                    None,
                    None,
                    None,
                    canonical_json({}),
                    spec["loader"],
                    "blocked",
                    canonical_json(
                        {
                            "task": spec["task"],
                            "call_index": spec["call_index"],
                            "ghidra_artifact": "stage30:ghidra-sql-loaders-64",
                            "call_sequence_artifact": (
                                "stage30:ghidra-sql-call-sequence"
                            ),
                            "execution_slot": appearance_absence[
                                "game11_execution_slot"
                            ],
                        }
                    ),
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
                    f"stage30:cached:{table}",
                    -30300 - index,
                    query_key,
                    "stage30:game11",
                    None,
                    None,
                    0,
                    None,
                    canonical_json({}),
                    canonical_json({}),
                    canonical_json(
                        {
                            "layout_audit": audit,
                            "streams": appearance_absence["streams"],
                            "execution_slot": appearance_absence[
                                "game11_execution_slot"
                            ],
                        }
                    ),
                    "blocked",
                    "native_result_absent from all decrypted client streams",
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
                    f"stage30:opaque:{table}",
                    table,
                    "game0...game11",
                    "native_result_absent",
                    "Exact x2game loader exists, but no non-empty result with "
                    "that layout exists in any decrypted stream.",
                    canonical_json(
                        {
                            "audit": audit,
                            "streams": appearance_absence["streams"],
                            "execution_slot": appearance_absence[
                                "game11_execution_slot"
                            ],
                            "guessing_forbidden": True,
                        }
                    ),
                    30,
                    "opaque",
                ),
            )
        destination.execute(
            """
            UPDATE entities
            SET state='blocked'
            WHERE kind IN ('customizing_item_asset_color','skin_color')
              AND state='unknown'
            """
        )

        stage_scope = _stage30_endpoint(
            destination,
            kind="forensic_stage",
            native_id=30,
            state="confirmed",
            authority="derived_forensic",
            provenance=TOOL_NAME,
        )
        coverage_rows = (
            (
                "native_actor_catalog",
                "confirmed",
                "actor_models, models and npcs decoded with exact row boundaries",
                "client_native",
                {
                    "actor_models": len(decoded["actor_models"].rows),
                    "models": len(decoded["models"].rows),
                    "npcs": len(decoded["npcs"].rows),
                },
            ),
            (
                "model_asset_links",
                "confirmed",
                "actor_models.model_file paths preserved and related",
                "client_native",
                {"asset_paths": destination.execute("SELECT COUNT(*) FROM assets").fetchone()[0]},
            ),
            (
                "npc_model_closure",
                "confirmed",
                "every positive NPC model_id closes against the decoded model catalog",
                "client_native",
                {
                    "unresolved_models": destination.execute(
                        "SELECT COUNT(*) FROM entities WHERE kind='model' AND state='unknown'"
                    ).fetchone()[0]
                },
            ),
            (
                "system_factions",
                "confirmed",
                "native faction rows imported; missing referenced parents remain endpoints",
                "client_native",
                {"rows": len(faction_rows)},
            ),
            (
                "string_cache",
                "blocked",
                "global references not reconstructed for all string-bearing results",
                "client_native",
                {
                    table: sum(result.unresolved_references.values())
                    for table, result in sorted(decoded.items())
                },
            ),
            (
                "model_subtype_dispatch",
                "confirmed",
                (
                    "all model sub_type values resolved, including VehicleModel "
                    "and ShipModel from the self-contained attach_anims string seed"
                ),
                "client_native",
                {
                    "blocked_subtypes": destination.execute(
                        """
                        SELECT COUNT(*) FROM entity_properties
                        WHERE namespace='models'
                          AND property_name='sub_type'
                          AND state='blocked'
                        """
                    ).fetchone()[0],
                    "attach_anims_seed": {
                        "start": attach_seed["start"],
                        "done": attach_seed["done"],
                        "values": attach_seed["values"],
                    },
                },
            ),
            (
                "npc_localized_names",
                "confirmed",
                "every decoded NPC ID has an authoritative en_us client localization",
                "client_native",
                {
                    "npc_rows": len(decoded["npcs"].rows),
                    "localized_names": destination.execute(
                        """
                        SELECT COUNT(*) FROM localizations l
                        JOIN entities e ON e.entity_key=l.entity_key
                        WHERE e.kind='npc' AND l.locale='en_us'
                        """
                    ).fetchone()[0],
                    "source": "stage30:client-compact",
                },
            ),
            (
                "npc_total_customs",
                "confirmed",
                "every NPC total_custom_id closes against decoded native rows",
                "client_native",
                {
                    "referenced_custom_ids": destination.execute(
                        "SELECT COUNT(DISTINCT dst_entity_key) FROM relations "
                        "WHERE relation='uses_total_custom'"
                    ).fetchone()[0],
                    "missing_custom_ids": destination.execute(
                        "SELECT COUNT(*) FROM entities WHERE "
                        "kind='total_character_custom' AND state!='confirmed'"
                    ).fetchone()[0],
                },
            ),
            (
                "appearance_native_catalogs",
                "confirmed",
                "face decals, face presets and total customs decoded at exact boundaries",
                "client_native",
                {
                    table: len(result.rows)
                    for table, result in sorted(appearance.items())
                },
            ),
            (
                "appearance_modifier_container",
                "confirmed",
                "uint32 length plus signed int8[128] payload confirmed for every modifier",
                "client_native",
                {
                    "custom_face_presets": len(
                        appearance["custom_face_presets"].rows
                    ),
                    "total_character_customs": len(
                        appearance["total_character_customs"].rows
                    ),
                },
            ),
            (
                "appearance_modifier_targets",
                "blocked" if unmapped_modifier_slots else "confirmed",
                (
                    "all modifier bytes projected through the exact "
                    "model/ActorModel/XML profile chain; only non-zero slots "
                    "without an XML Target remain blocked"
                ),
                "client_native+client_asset+client_script",
                {
                    "payload_type": "int8[128]",
                    "rows": len(modifier_rows),
                    "profiles": len(face_profiles),
                    "profile_targets": sum(
                        len(value) for value in profile_targets.values()
                    ),
                    "unmapped_nonzero_profile_slots": [
                        {
                            "profile_key": profile_key,
                            "slot": slot,
                            "occurrences": count,
                        }
                        for (profile_key, slot), count in sorted(
                            unmapped_modifier_slots.items()
                        )
                    ],
                    "consumer": "X2Customizer face-target API",
                },
            ),
            (
                "face_decal_assets",
                "confirmed",
                "every non-empty decal asset_path closes against the frozen game_pak index",
                "client_asset",
                {
                    "unique_paths": len(requested_asset_paths),
                    "matched_paths": len(indexed_assets),
                    "missing_paths": len(missing_asset_paths),
                },
            ),
            (
                "appearance_map_catalogs",
                "confirmed",
                "body/face diffuse, normal and eyelash maps decoded at exact boundaries",
                "client_native",
                {
                    table: len(appearance_auxiliary[table].rows)
                    for table in (
                        "body_diffuse_maps",
                        "body_normal_maps",
                        "face_diffuse_maps",
                        "face_normal_maps",
                        "face_eyelash_maps",
                    )
                },
            ),
            (
                "appearance_item_customization",
                "confirmed",
                "customizing item assets and custom hair textures decoded",
                "client_native",
                {
                    "customizing_item_assets": len(
                        appearance_auxiliary["customizing_item_assets"].rows
                    ),
                    "custom_hair_textures": len(
                        appearance_auxiliary["custom_hair_textures"].rows
                    ),
                    "referenced_hair_texture_ids": len(
                        referenced_hair_texture_ids
                    ),
                    "missing_hair_texture_ids": len(
                        referenced_hair_texture_ids.difference(hair_texture_ids)
                    ),
                },
            ),
            (
                "appearance_texture_assets",
                (
                    "blocked"
                    if missing_auxiliary_asset_paths
                    else "confirmed"
                ),
                "appearance texture paths checked against the frozen game_pak index",
                "client_asset",
                {
                    "unique_paths": len(auxiliary_asset_paths),
                    "matched_paths": len(auxiliary_indexed_assets),
                    "missing_paths": sorted(missing_auxiliary_asset_paths),
                },
            ),
            (
                "appearance_color_catalogs",
                "blocked",
                "color loaders are exact but native results are absent from every decrypted stream",
                "client_native",
                {
                    "tables": appearance_absence["tables"],
                    "execution_slot": appearance_absence[
                        "game11_execution_slot"
                    ],
                    "referenced_color_endpoints": destination.execute(
                        "SELECT COUNT(*) FROM entities WHERE kind IN "
                        "('customizing_item_asset_color','skin_color')"
                    ).fetchone()[0],
                },
            ),
            (
                "customizing_item_asset_closure",
                (
                    "blocked"
                    if missing_customizing_item_assets
                    else "confirmed"
                ),
                "hair and horn item IDs joined to native customizing-item rows",
                "client_native",
                {
                    "catalog_rows": len(customizing_item_asset_ids),
                    "missing_referenced_item_ids": sorted(
                        missing_customizing_item_assets
                    ),
                },
            ),
            (
                "native_spawner_tables",
                "blocked",
                "exact layouts known but native cached results absent in audited streams",
                "client_native",
                spawner_absence["result"],
            ),
            (
                "gamepak_spawner_placements",
                "corroborated",
                "layer placements preserved without treating them as active runtime rows",
                "client_asset",
                spawner_layers["summary"],
            ),
            (
                "spawner_world_mapping",
                "blocked",
                "root layer to world/zone mapping is unresolved",
                "client_asset",
                spawner_layers["activation_gap"],
            ),
        )
        for dimension, state, capability, authority, evidence in coverage_rows:
            destination.execute(
                """
                INSERT INTO coverage(
                    coverage_key,scope_key,dimension,state,capability,authority,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("coverage", stage_scope, dimension, authority),
                    stage_scope,
                    dimension,
                    state,
                    capability,
                    authority,
                    TOOL_NAME,
                    canonical_json(evidence),
                ),
            )
        gap_rows = (
            (
                "string_cache",
                4,
                "unresolved_global_string_references",
                (
                    "Raw cached fields still contain <ref:N>; NPC display names "
                    "are independently closed through localized_texts and every "
                    "model subtype is resolved."
                ),
                (
                    "Replay prior cached results in execution order to resolve "
                    "the remaining model names and non-localized NPC/faction fields."
                ),
            ),
            (
                "appearance_dependencies",
                5,
                "appearance_color_results_absent",
                "Skin colors and customizing item asset colors are referenced, "
                "but their exact native loaders emitted no cached result in "
                "the complete decrypted stream set.",
                "Locate an authoritative client mode or database that emits "
                "the Kakao r558734 color rows.",
            ),
            (
                "appearance_assets",
                3,
                "appearance_texture_path_missing",
                "Native appearance texture path(s) absent from the frozen "
                "game_pak index: "
                + ",".join(sorted(missing_auxiliary_asset_paths)),
                "Recover an authoritative alias/fallback consumer or a matching "
                "asset archive; do not rewrite the native row path.",
            ),
            (
                "appearance_item_assets",
                4,
                "referenced_customizing_item_asset_missing",
                "Total-character customs reference hair item(s) without a "
                "native customizing_item_assets row: "
                + ",".join(
                    str(value)
                    for value in sorted(missing_customizing_item_assets)
                ),
                "Classify the six item IDs as tombstones/fallbacks or recover "
                "their native customizing rows.",
            ),
            (
                "appearance_modifier_semantics",
                3,
                "modifier_target_slot_unmapped",
                (
                    "The payload type, signed values and XML-named target "
                    "indices are confirmed; "
                    f"{len(unmapped_modifier_slots)} profile/index pairs with "
                    "non-zero values have no Target in their profile XML."
                ),
                (
                    "Recover the removed/hidden target descriptors for: "
                    + ",".join(
                        f"{profile_key}[{slot}]"
                        for profile_key, slot in sorted(unmapped_modifier_slots)
                    )
                ),
            ),
            (
                "face_decals",
                4,
                "referenced_decal_row_missing",
                "Total-character customs reference absent face decal row(s): "
                + ",".join(str(value) for value in sorted(missing_decal_references)),
                "Classify each missing ID as tombstone or recover its native row from another authoritative source.",
            ),
            (
                "spawners",
                5,
                "native_result_absent",
                "npc_spawners and npc_spawner_npcs have exact layouts but no result chain in audited streams.",
                "Locate a native server-mode compact or another authoritative placement source.",
            ),
            (
                "world_mapping",
                5,
                "world_id_unresolved",
                "Game-pak layer placements are not tied to an authoritative world and active revision.",
                "Recover root-layer world ownership and layer activation metadata.",
            ),
        )
        for dimension, severity, code, reason, required_evidence in gap_rows:
            destination.execute(
                """
                INSERT INTO gaps(
                    gap_key,entity_key,dimension,state,severity,blocker_code,
                    reason,required_evidence,provenance
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("gap", stage_scope, dimension, code),
                    stage_scope,
                    dimension,
                    "blocked",
                    severity,
                    code,
                    reason,
                    required_evidence,
                    TOOL_NAME,
                ),
            )
        if unmapped_modifier_slots:
            destination.execute(
                """
                INSERT INTO opaque_regions(
                    opaque_key,surface,locator,blocker_code,reason,
                    searched_evidence_json,source_stage,state
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    "stage30:opaque:appearance-modifier-target-slots",
                    "appearance_modifier_target_slots",
                    ",".join(
                        f"{profile_key}[{slot}]"
                        for profile_key, slot in sorted(unmapped_modifier_slots)
                    ),
                    "modifier_target_slot_unmapped",
                    (
                        "Only the listed non-zero int8 slots lack an XML Target "
                        "name; all other payload bytes are structurally decoded."
                    ),
                    canonical_json(
                        {
                            "container_layout": (
                                "uint32_le length + signed int8[128]"
                            ),
                            "all_lengths_confirmed": 128,
                            "reserved_slot_zero_confirmed": True,
                            "x64_custom_model_offset": "0xA8",
                            "consumer_memcpy_bytes": "0x80",
                            "xml_profiles": {
                                key: len(value.targets)
                                for key, value in face_profiles.items()
                            },
                            "lua_api": [
                                "GetFaceTargetIndex",
                                "GetFaceTargetName",
                                "GetFaceTargetMinValue",
                                "GetFaceTargetMaxValue",
                            ],
                            "unmapped_nonzero_profile_slots": [
                                {
                                    "profile_key": profile_key,
                                    "slot": slot,
                                    "occurrences": count,
                                }
                                for (profile_key, slot), count in sorted(
                                    unmapped_modifier_slots.items()
                                )
                            ],
                            "guessing_historical_rows_forbidden": True,
                        }
                    ),
                    30,
                    "opaque",
                ),
            )

        for key, count in sorted(entity_counts.items()):
            set_metadata(destination, {f"stage30.entities.{key}": count})
        set_metadata(
            destination,
            {
                "stage30.decoded_rows": decoded_row_count,
                "stage30.properties": property_count,
                "stage30.relations": relation_count,
                "stage30.source_hashes": canonical_json(source_hashes),
                "stage30.spawner_rows": len(spawner_rows),
                "stage30.appearance_auxiliary_rows": sum(
                    len(result.rows)
                    for result in appearance_auxiliary.values()
                ),
                "stage30.appearance_color_absence": canonical_json(
                    appearance_absence
                ),
            },
        )
        orphan_relations = int(
            destination.execute(
                """
                SELECT COUNT(*) FROM relations r
                LEFT JOIN entities s ON s.entity_key=r.src_entity_key
                LEFT JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE s.entity_key IS NULL OR d.entity_key IS NULL
                """
            ).fetchone()[0]
        )
        if orphan_relations:
            raise RuntimeError(f"Stage 30 has {orphan_relations} orphan relations")
        _add_validation(
            destination,
            scope_kind="stage",
            scope_id="30",
            check_name="zero_orphan_relations",
            status="confirmed",
            evidence={"orphan_relations": orphan_relations},
        )
        (
            npc_group_rows,
            active_npc_groups,
            npc_group_catalog_evidence,
        ) = native_npc_group_identity_catalog(context.config)
        npc_group_catalog = materialize_native_npc_group_catalog(
            destination,
            rows=npc_group_rows,
            active_ids=active_npc_groups,
            catalog_evidence=npc_group_catalog_evidence,
            source_artifact_key="stage30:game11",
        )
        active_skills, skill_catalog_evidence = (
            native_skill_identity_catalog(context.config)
        )
        skill_endpoint_lifecycle = reconcile_native_skill_endpoints(
            destination,
            active_ids=active_skills,
            catalog_evidence=skill_catalog_evidence,
            stage=30,
            source_artifact_key="stage30:game11",
            expected={
                "relations": 18_213,
                "endpoints": 639,
                "present": 617,
                "tombstone": 22,
            },
        )
        set_metadata(
            destination,
            {
                "stage30.skill_endpoint_lifecycle": (
                    skill_endpoint_lifecycle
                ),
                "stage30.npc_group_identity_catalog": npc_group_catalog,
            },
        )

    return _atomic_build(
        context,
        context.config.stage_30,
        stage=30,
        classification="stage_30_world_actors_and_appearance_graph",
        populate=populate,
    )


def build_stage_40(context: BuildContext) -> dict[str, Any]:
    """Decode the native quest frontier and project its dependency graph."""

    def populate(
        destination: sqlite3.Connection,
        source: sqlite3.Connection,
    ) -> None:
        populate_stage_40(destination, source, context)
        item_endpoint_lifecycle = reconcile_native_item_endpoints(
            destination,
            source,
            stage=40,
            source_artifact_key=SOURCE_ARTIFACT_KEY,
            expected={
                "relations": 4_779,
                "endpoints": 2_293,
                "present": 3,
                "tombstone": 2_290,
            },
        )
        active_skills, skill_catalog_evidence = (
            native_skill_identity_catalog(context.config)
        )
        skill_endpoint_lifecycle = reconcile_native_skill_endpoints(
            destination,
            active_ids=active_skills,
            catalog_evidence=skill_catalog_evidence,
            stage=40,
            source_artifact_key="stage40:stream-game11",
            expected={
                "relations": 1_022,
                "endpoints": 173,
                "present": 169,
                "tombstone": 4,
            },
        )
        active_buffs, buff_catalog_evidence = (
            native_buff_identity_catalog(context.config)
        )
        buff_endpoint_lifecycle = reconcile_native_buff_endpoints(
            destination,
            active_ids=active_buffs,
            catalog_evidence=buff_catalog_evidence,
            stage=40,
            source_artifact_key="stage40:stream-game11",
            expected={
                "relations": 3,
                "endpoints": 3,
                "present": 0,
                "tombstone": 3,
            },
        )
        (
            enabled_crafts,
            referenced_crafts,
            observed_crafts,
            craft_catalog_evidence,
        ) = native_craft_identity_constraints(context.config)
        craft_identity_constraints = reconcile_native_craft_endpoints(
            destination,
            enabled_ids=enabled_crafts,
            reference_ids=referenced_crafts,
            observed_ids=observed_crafts,
            catalog_evidence=craft_catalog_evidence,
            stage=40,
            source_artifact_key="stage40:stream-game11",
            materialize_observed_universe=False,
            expected={
                "entities": 276,
                "enabled": 263,
                "disabled_or_tombstone": 13,
                "relations": 386,
                "relation_endpoints": 276,
            },
        )
        (
            _npc_group_rows,
            active_npc_groups,
            npc_group_catalog_evidence,
        ) = native_npc_group_identity_catalog(context.config)
        npc_group_endpoint_lifecycle = (
            reconcile_native_npc_group_endpoints(
                destination,
                active_ids=active_npc_groups,
                catalog_evidence=npc_group_catalog_evidence,
                source_artifact_key="stage40:stream-game11",
                expected={
                    "relations": 1_319,
                    "endpoints": 225,
                    "present": 12,
                    "tombstone": 213,
                },
            )
        )
        active_npcs, npc_catalog_evidence = native_npc_identity_catalog(
            context.config
        )
        npc_endpoint_lifecycle = reconcile_native_npc_endpoints(
            destination,
            active_ids=active_npcs,
            catalog_evidence=npc_catalog_evidence,
            stage=40,
            source_artifact_key="stage40:stream-game11",
            expected={
                "relations": 549,
                "endpoints": 123,
                "present": 0,
                "tombstone": 123,
            },
        )
        set_metadata(
            destination,
            {
                "stage40.item_endpoint_lifecycle": (
                    item_endpoint_lifecycle
                ),
                "stage40.skill_endpoint_lifecycle": (
                    skill_endpoint_lifecycle
                ),
                "stage40.buff_endpoint_lifecycle": (
                    buff_endpoint_lifecycle
                ),
                "stage40.craft_identity_constraints": (
                    craft_identity_constraints
                ),
                "stage40.npc_group_endpoint_lifecycle": (
                    npc_group_endpoint_lifecycle
                ),
                "stage40.npc_endpoint_lifecycle": (
                    npc_endpoint_lifecycle
                ),
            },
        )

    return _atomic_build(
        context,
        context.config.stage_40,
        stage=40,
        classification="stage_40_quests_and_dependency_graph",
        populate=populate,
    )


def build_stage_50(context: BuildContext) -> dict[str, Any]:
    """Decode skills, buffs, effects, plots, FX and their native graph."""

    def populate(
        destination: sqlite3.Connection,
        source: sqlite3.Connection,
    ) -> None:
        populate_stage_50(destination, source, context)
        tag_result_resolution = reconcile_tag_stage50_result(
            destination,
            source,
            context.config,
        )
        active_tags, tag_catalog_evidence = native_tag_evidence(
            source,
            context.config,
        )
        tag_endpoint_lifecycle = reconcile_native_tag_endpoints(
            destination,
            active_ids=active_tags,
            catalog_evidence=tag_catalog_evidence,
            stage=50,
            source_artifact_key="stage50:stream-game11",
            expected={
                "active": 5_280,
                "active_without_incoming": 496,
                "endpoints": 4_795,
                "present_endpoints": 4_784,
                "relation_pairs": 94_881,
                "relations": 95_008,
                "tombstones": 11,
                "universe": 5_291,
            },
        )
        item_endpoint_lifecycle = reconcile_native_item_endpoints(
            destination,
            source,
            stage=50,
            source_artifact_key=SOURCE_ARTIFACT_KEY,
            expected={
                "relations": 103,
                "endpoints": 102,
                "present": 0,
                "tombstone": 102,
            },
        )
        active_skills, skill_catalog_evidence = (
            native_skill_identity_catalog(context.config)
        )
        skill_endpoint_lifecycle = reconcile_native_skill_endpoints(
            destination,
            active_ids=active_skills,
            catalog_evidence=skill_catalog_evidence,
            stage=50,
            source_artifact_key="stage50:stream-game11",
            expected={
                "relations": 4_095,
                "endpoints": 1_507,
                "present": 0,
                "tombstone": 1_507,
            },
        )
        active_buffs, buff_catalog_evidence = (
            native_buff_identity_catalog(context.config)
        )
        buff_endpoint_lifecycle = reconcile_native_buff_endpoints(
            destination,
            active_ids=active_buffs,
            catalog_evidence=buff_catalog_evidence,
            stage=50,
            source_artifact_key="stage50:stream-game11",
            expected={
                "relations": 1_100,
                "endpoints": 384,
                "present": 0,
                "tombstone": 384,
            },
        )
        active_npcs, npc_catalog_evidence = native_npc_identity_catalog(
            context.config
        )
        npc_endpoint_lifecycle = reconcile_native_npc_endpoints(
            destination,
            active_ids=active_npcs,
            catalog_evidence=npc_catalog_evidence,
            stage=50,
            source_artifact_key="stage50:stream-game11",
            expected={
                "relations": 41,
                "endpoints": 39,
                "present": 0,
                "tombstone": 39,
            },
        )
        set_metadata(
            destination,
            {
                "stage50.item_endpoint_lifecycle": (
                    item_endpoint_lifecycle
                ),
                "stage50.skill_endpoint_lifecycle": (
                    skill_endpoint_lifecycle
                ),
                "stage50.buff_endpoint_lifecycle": (
                    buff_endpoint_lifecycle
                ),
                "stage50.npc_endpoint_lifecycle": (
                    npc_endpoint_lifecycle
                ),
                "stage50.tag_result_resolution": tag_result_resolution,
                "stage50.tag_endpoint_lifecycle": tag_endpoint_lifecycle,
            },
        )

    return _atomic_build(
        context,
        context.config.stage_50,
        stage=50,
        classification="stage_50_skills_buffs_effects_and_plots_graph",
        populate=populate,
    )


def build_stage_60(context: BuildContext) -> dict[str, Any]:
    """Build the complete client asset, UI and localization frontier."""

    def populate(
        destination: sqlite3.Connection,
        source: sqlite3.Connection,
    ) -> None:
        populate_stage_60(destination, source, context)

    return _atomic_build(
        context,
        context.config.stage_60,
        stage=60,
        classification="stage_60_assets_ui_localization_graph",
        populate=populate,
    )


def build_stage_70(context: BuildContext) -> dict[str, Any]:
    """Normalize the frozen compatible wiki as corroborative evidence."""

    def populate(
        destination: sqlite3.Connection,
        source: sqlite3.Connection,
    ) -> None:
        populate_stage_70(destination, source, context)

    return _atomic_build(
        context,
        context.config.stage_70,
        stage=70,
        classification="stage_70_external_wiki_corroboration_graph",
        populate=populate,
    )


def build_stage_90(context: BuildContext) -> dict[str, Any]:
    """Build the cross-stage coverage closure and prioritized work queue."""

    def populate(
        destination: sqlite3.Connection,
        source: sqlite3.Connection,
    ) -> None:
        populate_stage_90(destination, source, context)

    return _atomic_build(
        context,
        context.config.stage_90,
        stage=90,
        classification="stage_90_coverage_closure",
        populate=populate,
    )


CONSOLIDATED_COPY_ORDER = (
    "artifacts",
    "decoders",
    "surfaces",
    "surface_inventory",
    "review_manifests",
    "query_specs",
    "cached_results",
    "cached_result_rows",
    "native_catalogs",
    "native_rows",
    "entities",
    "entity_properties",
    "relations",
    "consumers",
    "assets",
    "localizations",
    "wiki_entities",
    "wiki_properties",
    "wiki_relations",
    "opaque_regions",
    "coverage",
    "gaps",
    "validation_events",
    "source_records",
    "blocker_roots",
    "blocker_impacts",
    "blocker_evidence",
    "work_queue",
)


def _import_native_code_evidence_links(
    connection: sqlite3.Connection,
    stage_15_alias: str,
) -> int:
    missing_consumers = int(
        connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {stage_15_alias}.code_evidence_links link
            LEFT JOIN main.consumers consumer
              ON consumer.consumer_key=json_extract(
                    link.evidence_json,
                    '$.consumer_key'
                 )
            WHERE consumer.consumer_key IS NULL
            """
        ).fetchone()[0]
    )
    if missing_consumers:
        raise RuntimeError(
            "Stage 15 native evidence links have missing consumers: "
            f"{missing_consumers}"
        )
    connection.execute(
        f"""
        INSERT INTO main.native_code_evidence_links(
            evidence_link_key,consumer_key,function_key,scope_key,relation,
            source_locator,state,source_stage,evidence_json
        )
        SELECT evidence_link_key,
               json_extract(evidence_json, '$.consumer_key'),
               function_key,
               scope_key,
               relation,
               source_locator,
               state,
               15,
               evidence_json
        FROM {stage_15_alias}.code_evidence_links
        ORDER BY evidence_link_key
        """
    )
    imported = int(
        connection.execute(
            "SELECT COUNT(*) FROM main.native_code_evidence_links"
        ).fetchone()[0]
    )
    expected = int(
        connection.execute(
            f"SELECT COUNT(*) FROM {stage_15_alias}.code_evidence_links"
        ).fetchone()[0]
    )
    if imported != expected:
        raise RuntimeError(
            "Stage 15 native evidence link row loss: "
            f"expected={expected} imported={imported}"
        )
    return imported


def _import_native_semantic_index(
    connection: sqlite3.Connection,
    config: ForensicsConfig,
) -> dict[str, int | str]:
    manifest = json.loads(
        config.source_native_semantic_manifest.read_text(encoding="utf-8")
    )
    expected_sha = str(manifest["database"]["sha256"]).upper()
    actual_sha = sha256_file(config.source_native_semantic_database).upper()
    if actual_sha != expected_sha:
        raise RuntimeError(
            "Native semantic index does not match its manifest: "
            f"expected={expected_sha} actual={actual_sha}"
        )
    stage_manifest = json.loads(
        config.source_native_code_manifest.read_text(encoding="utf-8")
    )
    expected_stage_sha = str(stage_manifest["database"]["sha256"]).upper()
    semantic_stage_sha = str(manifest["inputs"]["stage_15_sha256"]).upper()
    if semantic_stage_sha != expected_stage_sha:
        raise RuntimeError(
            "Native semantic index belongs to another Stage 15: "
            f"expected={expected_stage_sha} actual={semantic_stage_sha}"
        )
    connection.execute(
        "ATTACH DATABASE ? AS semantic_index",
        (config.source_native_semantic_database.resolve().as_posix(),),
    )
    try:
        projection = hashlib.sha256()
        for table in ("consumers", "query_specs", "blocker_roots"):
            columns = [
                str(row[1])
                for row in connection.execute(f"PRAGMA main.table_info({table})")
            ]
            projection.update((table + "\n").encode("utf-8"))
            for row in connection.execute(
                f'SELECT * FROM main."{table}" ORDER BY "{columns[0]}"'
            ):
                projection.update(
                    canonical_json(dict(zip(columns, tuple(row)))).encode("utf-8")
                )
                projection.update(b"\n")
        actual_projection_sha = projection.hexdigest().upper()
        semantic_projection_row = connection.execute(
            """
            SELECT value FROM semantic_index.metadata
            WHERE key='consolidated_source_projection_sha256'
            """
        ).fetchone()
        semantic_projection_sha = (
            str(semantic_projection_row[0]).upper()
            if semantic_projection_row is not None else ""
        )
        if actual_projection_sha != semantic_projection_sha:
            raise RuntimeError(
                "Native semantic index is stale for the consolidated source "
                f"projection: expected={actual_projection_sha} "
                f"actual={semantic_projection_sha}"
            )
        connection.execute(
            """
            INSERT INTO main.native_semantic_roots
            SELECT root_key,root_kind,scope_key,name,domain,backend_priority,
                   state,evidence_json
            FROM semantic_index.semantic_roots ORDER BY root_key
            """
        )
        connection.execute(
            """
            INSERT INTO main.native_semantic_function_states
            SELECT function_key,binary_key,module_name,architecture,domain,
                   category,impact_score,uncertainty_score,impact_tier,
                   primary_root_key,state,evidence_json
            FROM semantic_index.semantic_function_classifications
            ORDER BY function_key
            """
        )
        connection.execute(
            """
            INSERT INTO main.native_semantic_links
            SELECT link_key,root_key,function_key,relation,direction,depth,
                   impact_score,state
            FROM semantic_index.semantic_root_functions ORDER BY link_key
            """
        )
        connection.execute(
            """
            INSERT INTO main.native_semantic_opaque_states
            SELECT region_key,binary_key,start_rva,end_rva,classification,
                   impact_score,primary_function_key,primary_root_key,state
            FROM semantic_index.semantic_opaque_regions ORDER BY region_key
            """
        )
        connection.execute(
            """
            INSERT INTO main.native_semantic_work_queue
            SELECT queue_key,rank,wave,root_key,domain,impact_tier,impact_score,
                   uncertainty_score,closure_status,next_action
            FROM semantic_index.semantic_work_queue ORDER BY rank
            """
        )
        counts = {
            "roots": int(connection.execute("SELECT COUNT(*) FROM native_semantic_roots").fetchone()[0]),
            "functions": int(connection.execute("SELECT COUNT(*) FROM native_semantic_function_states").fetchone()[0]),
            "links": int(connection.execute("SELECT COUNT(*) FROM native_semantic_links").fetchone()[0]),
            "opaque_regions": int(connection.execute("SELECT COUNT(*) FROM native_semantic_opaque_states").fetchone()[0]),
            "queue": int(connection.execute("SELECT COUNT(*) FROM native_semantic_work_queue").fetchone()[0]),
        }
        connection.execute(
            """
            INSERT OR IGNORE INTO main.artifacts(
                artifact_key,source_stage,role,path,bytes,sha256,build,
                authority,state,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "native-semantic-index:v1", 80, "native_semantic_index",
                config.source_native_semantic_database.resolve().as_posix(),
                config.source_native_semantic_database.stat().st_size,
                actual_sha, config.client_build, "derived_forensic",
                "confirmed", TOOL_NAME,
                canonical_json({
                    "stage_15_sha256": semantic_stage_sha,
                    "pseudocode_copied": False,
                    "sidecar_is_full_path_authority": True,
                }),
            ),
        )
        connection.commit()
        return {**counts, "sha256": actual_sha}
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.execute("DETACH DATABASE semantic_index")


def consolidate(
    context: BuildContext,
    stage_manifests: list[dict[str, Any]] | None = None,
    *,
    include_stage_90: bool = True,
    include_native_semantic: bool = True,
) -> dict[str, Any]:
    stages = [
        (0, context.config.stage_00),
        (10, context.config.stage_10),
        (15, context.config.stage_15),
        (20, context.config.stage_20),
        (30, context.config.stage_30),
        (40, context.config.stage_40),
        (50, context.config.stage_50),
        (60, context.config.stage_60),
        (70, context.config.stage_70),
    ]
    if include_stage_90:
        stages.append((90, context.config.stage_90))
    for _, path in stages:
        if not path.is_file():
            raise FileNotFoundError(path)

    target = context.config.consolidated
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        prefix=f".{target.stem}.",
        suffix=".sqlite",
        dir=target.parent,
    )
    os.close(handle)
    temporary = Path(name)
    temporary.unlink(missing_ok=True)
    connection: sqlite3.Connection | None = None
    try:
        connection = create_database(temporary)
        _initialize(
            connection,
            context,
            stage=80,
            classification="stage_80_consolidated_transversal_graph",
        )
        connection.execute("PRAGMA foreign_keys = OFF")
        aliases: list[tuple[int, str, Path, int]] = []
        for index, (stage, path) in enumerate(stages):
            alias = f"stage_{index}"
            connection.execute(
                f"ATTACH DATABASE ? AS {alias}",
                (path.resolve().as_posix(),),
            )
            schema_version = int(
                connection.execute(f"PRAGMA {alias}.user_version").fetchone()[0]
            )
            aliases.append((stage, alias, path, schema_version))

        for table in CONSOLIDATED_COPY_ORDER:
            selected_aliases = aliases
            if table == "assets":
                selected_aliases = [
                    value for value in aliases if value[0] == 60
                ]
            elif table in {
                "wiki_entities",
                "wiki_properties",
                "wiki_relations",
            }:
                selected_aliases = [
                    value for value in aliases if value[0] == 70
                ]
            elif table in {
                "blocker_roots",
                "blocker_impacts",
                "blocker_evidence",
                "work_queue",
            }:
                selected_aliases = [
                    value for value in aliases if value[0] == 90
                ]
            for _, alias, _, _ in selected_aliases:
                conflict_mode = (
                    "OR REPLACE"
                    if table in {"entities", "entity_properties", "relations"}
                    else "OR IGNORE"
                )
                connection.execute(
                    f'INSERT {conflict_mode} INTO main."{table}" '
                    f'SELECT * FROM {alias}."{table}"'
                )

        stage15_alias = next(
            alias for stage, alias, _, _ in aliases if stage == 15
        )
        native_evidence_links = _import_native_code_evidence_links(
            connection,
            stage15_alias,
        )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="stage-15-native-code",
            check_name="native_code_evidence_links_preserved",
            status="confirmed",
            evidence={
                "external_function_identity": "binary_sha256+architecture+rva",
                "links": native_evidence_links,
                "pseudocode_copied": False,
                "source_stage": 15,
            },
        )

        stage20_alias = next(
            alias for stage, alias, _, _ in aliases if stage == 20
        )
        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage20_alias}.entities
            WHERE kind='item_grade'
            """
        )
        canonical_item_grades = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='item_grade'
                  AND source_stage=20
                  AND state='confirmed'
                  AND lifecycle='present'
                  AND subtype IS NOT NULL
                """
            ).fetchone()[0]
        )
        if canonical_item_grades != 13:
            raise RuntimeError(
                "Consolidated item_grade ownership is not closed in Stage 20"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="item_grade",
            check_name="item_grade_owner_stage_preserved",
            status="confirmed",
            evidence={
                "owner_stage": 20,
                "entities": canonical_item_grades,
                "later_reference_identities_do_not_replace_owner": True,
            },
        )

        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage20_alias}.entities
            WHERE kind='item'
              AND state IN ('confirmed','tombstone')
            """
        )
        canonical_active_items = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='item'
                  AND source_stage=20
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        item_owner_mismatches = int(
            connection.execute(
                f"""
                SELECT COUNT(*)
                FROM {stage20_alias}.entities s
                LEFT JOIN main.entities m ON m.entity_key=s.entity_key
                WHERE s.kind='item'
                  AND s.state IN ('confirmed','tombstone')
                  AND (
                      m.entity_key IS NULL
                      OR m.state<>s.state
                      OR m.lifecycle<>s.lifecycle
                      OR m.authority<>s.authority
                  )
                """
            ).fetchone()[0]
        )
        if canonical_active_items != ITEMS_POSITIVE_IDS:
            raise RuntimeError(
                "Consolidated positive item ownership is not closed in Stage 20"
            )
        if item_owner_mismatches:
            raise RuntimeError(
                f"Consolidated item owner mismatches={item_owner_mismatches}"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="item",
            check_name="item_owner_stage_preserved",
            status="confirmed",
            evidence={
                "active_items": canonical_active_items,
                "owner_mismatches": item_owner_mismatches,
                "owner_stage": 20,
                "strong_states": ["confirmed", "tombstone"],
            },
        )

        stage50_alias = next(
            alias for stage, alias, _, _ in aliases if stage == 50
        )
        for stage, alias, _, _ in aliases:
            if stage not in {20, 30, 40, 50}:
                continue
            connection.execute(
                f"""
                INSERT OR REPLACE INTO main.entities
                SELECT * FROM {alias}.entities
                WHERE kind='skill'
                  AND state='tombstone'
                """
            )
        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage50_alias}.entities
            WHERE kind='skill'
              AND state IN ('confirmed','tombstone')
            """
        )
        canonical_active_skills = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='skill'
                  AND source_stage=50
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        canonical_skill_tombstones = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='skill'
                  AND state='tombstone'
                  AND lifecycle='tombstone'
                """
            ).fetchone()[0]
        )
        skill_owner_mismatches = 0
        for stage, alias, _, _ in aliases:
            if stage not in {20, 30, 40, 50}:
                continue
            strong_filter = (
                "s.state IN ('confirmed','tombstone')"
                if stage == 50
                else "s.state='tombstone'"
            )
            skill_owner_mismatches += int(
                connection.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {alias}.entities s
                    LEFT JOIN main.entities m ON m.entity_key=s.entity_key
                    WHERE s.kind='skill'
                      AND {strong_filter}
                      AND (
                          m.entity_key IS NULL
                          OR m.state<>s.state
                          OR m.lifecycle<>s.lifecycle
                          OR m.authority<>s.authority
                      )
                    """
                ).fetchone()[0]
            )
        if canonical_active_skills != SKILLS_NATIVE_ROWS:
            raise RuntimeError(
                "Consolidated positive skill ownership is not closed in Stage 50"
            )
        if canonical_skill_tombstones != SKILLS_REFERENCED_TOMBSTONES:
            raise RuntimeError(
                "Consolidated referenced skill tombstones are not closed"
            )
        if skill_owner_mismatches:
            raise RuntimeError(
                f"Consolidated skill owner mismatches={skill_owner_mismatches}"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="skill",
            check_name="skill_owner_stage_preserved",
            status="confirmed",
            evidence={
                "active_skills": canonical_active_skills,
                "referenced_tombstones": canonical_skill_tombstones,
                "owner_mismatches": skill_owner_mismatches,
                "owner_stage": 50,
                "strong_states": ["confirmed", "tombstone"],
            },
        )

        for stage, alias, _, _ in aliases:
            if stage not in {20, 30, 40, 50}:
                continue
            connection.execute(
                f"""
                INSERT OR REPLACE INTO main.entities
                SELECT * FROM {alias}.entities
                WHERE kind='buff'
                  AND state='tombstone'
                """
            )
        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage50_alias}.entities
            WHERE kind='buff'
              AND state IN ('confirmed','tombstone')
            """
        )
        canonical_active_buffs = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='buff'
                  AND source_stage=50
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        canonical_buff_tombstones = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='buff'
                  AND state='tombstone'
                  AND lifecycle='tombstone'
                """
            ).fetchone()[0]
        )
        buff_owner_mismatches = 0
        for stage, alias, _, _ in aliases:
            if stage not in {20, 30, 40, 50}:
                continue
            strong_filter = (
                "s.state IN ('confirmed','tombstone')"
                if stage == 50
                else "s.state='tombstone'"
            )
            buff_owner_mismatches += int(
                connection.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {alias}.entities s
                    LEFT JOIN main.entities m ON m.entity_key=s.entity_key
                    WHERE s.kind='buff'
                      AND {strong_filter}
                      AND (
                          m.entity_key IS NULL
                          OR m.state<>s.state
                          OR m.lifecycle<>s.lifecycle
                          OR m.authority<>s.authority
                      )
                    """
                ).fetchone()[0]
            )
        if canonical_active_buffs != BUFFS_NATIVE_ROWS:
            raise RuntimeError(
                "Consolidated positive buff ownership is not closed in Stage 50"
            )
        if canonical_buff_tombstones != BUFFS_REFERENCED_TOMBSTONES:
            raise RuntimeError(
                "Consolidated referenced buff tombstones are not closed"
            )
        if buff_owner_mismatches:
            raise RuntimeError(
                f"Consolidated buff owner mismatches={buff_owner_mismatches}"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="buff",
            check_name="buff_owner_stage_preserved",
            status="confirmed",
            evidence={
                "active_buffs": canonical_active_buffs,
                "referenced_tombstones": canonical_buff_tombstones,
                "owner_mismatches": buff_owner_mismatches,
                "owner_stage": 50,
                "strong_states": ["confirmed", "tombstone"],
            },
        )

        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage50_alias}.entities
            WHERE kind='tag'
              AND state IN ('confirmed','tombstone')
            """
        )
        canonical_active_tags = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='tag'
                  AND source_stage=50
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        canonical_tag_tombstones = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='tag'
                  AND source_stage=50
                  AND state='tombstone'
                  AND lifecycle='tombstone'
                """
            ).fetchone()[0]
        )
        tag_relation_mismatches = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='tag'
                  AND r.relation='references_tag'
                  AND r.authority IN ('client_native','client_reference')
                  AND r.state<>'confirmed'
                """
            ).fetchone()[0]
        )
        tag_relation_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='tag'
                  AND r.relation='references_tag'
                  AND r.authority='client_native'
                  AND r.state='confirmed'
                """
            ).fetchone()[0]
        )
        if canonical_active_tags != TAG_ROWS:
            raise RuntimeError("Consolidated active tag ownership changed")
        if canonical_tag_tombstones != TAG_TOMBSTONES:
            raise RuntimeError(
                "Consolidated referenced tag tombstones changed"
            )
        if tag_relation_mismatches or tag_relation_count != TAG_RELATIONS:
            raise RuntimeError(
                "Consolidated exact tag relations are not closed"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="tag",
            check_name="tag_ownership_and_lifecycle_preserved",
            status="confirmed",
            evidence={
                "active": canonical_active_tags,
                "owner_stage": 50,
                "relation_mismatches": tag_relation_mismatches,
                "relations": tag_relation_count,
                "tombstones": canonical_tag_tombstones,
            },
        )

        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage20_alias}.entities
            WHERE kind='craft'
            """
        )
        canonical_crafts = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='craft' AND CAST(native_id AS INTEGER)>0
                """
            ).fetchone()[0]
        )
        canonical_enabled_crafts = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='craft'
                  AND CAST(native_id AS INTEGER)>0
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        canonical_unresolved_crafts = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='craft'
                  AND CAST(native_id AS INTEGER)>0
                  AND state='unknown'
                  AND lifecycle='disabled_or_tombstone'
                """
            ).fetchone()[0]
        )
        craft_relation_mismatches = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='craft'
                  AND CAST(d.native_id AS INTEGER)>0
                  AND r.authority IN ('client_native','client_reference')
                  AND r.state<>'confirmed'
                """
            ).fetchone()[0]
        )
        if canonical_crafts != CRAFTS_OBSERVED_IDS:
            raise RuntimeError(
                "Consolidated observed craft identity universe changed"
            )
        if canonical_enabled_crafts != CRAFTS_ENABLED_ROWS:
            raise RuntimeError(
                "Consolidated enabled craft ownership is not closed"
            )
        if canonical_unresolved_crafts != CRAFTS_NON_ENABLED_OBSERVED_IDS:
            raise RuntimeError(
                "Consolidated unresolved craft partition changed"
            )
        if craft_relation_mismatches:
            raise RuntimeError(
                "Consolidated exact native craft relations are not confirmed"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="craft",
            check_name="craft_identity_constraints_preserved",
            status="confirmed",
            evidence={
                "enabled": canonical_enabled_crafts,
                "observed_identities": canonical_crafts,
                "owner_stage": 20,
                "relation_mismatches": craft_relation_mismatches,
                "unresolved_disabled_or_tombstone": (
                    canonical_unresolved_crafts
                ),
            },
        )

        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage20_alias}.entities
            WHERE kind='craft_pack'
              AND state IN ('confirmed','tombstone')
            """
        )
        canonical_active_craft_packs = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='craft_pack'
                  AND source_stage=20
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        canonical_craft_pack_tombstones = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='craft_pack'
                  AND source_stage=20
                  AND state='tombstone'
                  AND lifecycle='tombstone'
                """
            ).fetchone()[0]
        )
        craft_pack_relation_mismatches = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='craft_pack'
                  AND r.relation='member_of_craft_pack'
                  AND r.authority IN ('client_native','client_reference')
                  AND r.state<>'confirmed'
                """
            ).fetchone()[0]
        )
        craft_pack_relation_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='craft_pack'
                  AND r.relation='member_of_craft_pack'
                  AND r.authority='client_native'
                  AND r.state='confirmed'
                """
            ).fetchone()[0]
        )
        if canonical_active_craft_packs != CRAFT_PACK_ROWS:
            raise RuntimeError(
                "Consolidated active craft_pack ownership changed"
            )
        if canonical_craft_pack_tombstones != CRAFT_PACK_TOMBSTONES:
            raise RuntimeError(
                "Consolidated referenced craft_pack tombstones changed"
            )
        if (
            craft_pack_relation_mismatches
            or craft_pack_relation_count != CRAFT_PACK_FRONTIER_RELATIONS
        ):
            raise RuntimeError(
                "Consolidated exact craft_pack relations are not closed"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="craft_pack",
            check_name="craft_pack_ownership_and_lifecycle_preserved",
            status="confirmed",
            evidence={
                "active": canonical_active_craft_packs,
                "owner_stage": 20,
                "relation_mismatches": craft_pack_relation_mismatches,
                "relations": craft_pack_relation_count,
                "tombstones": canonical_craft_pack_tombstones,
            },
        )

        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage20_alias}.entities
            WHERE kind='item_guide'
              AND state IN ('confirmed','tombstone')
            """
        )
        canonical_active_item_guides = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='item_guide'
                  AND source_stage=20
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        canonical_item_guide_tombstones = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='item_guide'
                  AND source_stage=20
                  AND state='tombstone'
                  AND lifecycle='tombstone'
                """
            ).fetchone()[0]
        )
        item_guide_relation_mismatches = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='item_guide'
                  AND r.relation='listed_in_item_guide'
                  AND r.authority IN ('client_native','client_reference')
                  AND r.state<>'confirmed'
                """
            ).fetchone()[0]
        )
        item_guide_relation_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='item_guide'
                  AND r.relation='listed_in_item_guide'
                  AND r.authority='client_native'
                  AND r.state='confirmed'
                """
            ).fetchone()[0]
        )
        if canonical_active_item_guides != ITEM_GUIDE_ROWS:
            raise RuntimeError(
                "Consolidated active item_guide ownership changed"
            )
        if canonical_item_guide_tombstones != ITEM_GUIDE_TOMBSTONES:
            raise RuntimeError(
                "Consolidated referenced item_guide tombstones changed"
            )
        if (
            item_guide_relation_mismatches
            or item_guide_relation_count != ITEM_GUIDE_ELEM_ROWS
        ):
            raise RuntimeError(
                "Consolidated exact item_guide relations are not closed"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="item_guide",
            check_name="item_guide_ownership_and_lifecycle_preserved",
            status="confirmed",
            evidence={
                "active": canonical_active_item_guides,
                "owner_stage": 20,
                "relation_mismatches": item_guide_relation_mismatches,
                "relations": item_guide_relation_count,
                "tombstones": canonical_item_guide_tombstones,
            },
        )

        stage30_alias = next(
            alias for stage, alias, _, _ in aliases if stage == 30
        )
        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage30_alias}.entities
            WHERE kind='npc_group'
              AND state='confirmed'
              AND lifecycle='present'
            """
        )
        stage40_alias = next(
            alias for stage, alias, _, _ in aliases if stage == 40
        )
        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage40_alias}.entities
            WHERE kind='npc_group'
              AND state='tombstone'
              AND lifecycle='tombstone'
            """
        )
        canonical_active_npc_groups = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='npc_group'
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        canonical_npc_group_tombstones = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='npc_group'
                  AND state='tombstone'
                  AND lifecycle='tombstone'
                """
            ).fetchone()[0]
        )
        npc_group_relation_mismatches = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='npc_group'
                  AND r.authority IN ('client_native','client_reference')
                  AND r.state<>'confirmed'
                """
            ).fetchone()[0]
        )
        if canonical_active_npc_groups != NPC_GROUP_ROWS:
            raise RuntimeError(
                "Consolidated active npc_group catalog changed"
            )
        if (
            canonical_npc_group_tombstones
            != NPC_GROUP_REFERENCED_TOMBSTONES
        ):
            raise RuntimeError(
                "Consolidated referenced npc_group tombstones changed"
            )
        if npc_group_relation_mismatches:
            raise RuntimeError(
                "Consolidated exact npc_group relations are not confirmed"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="npc_group",
            check_name="npc_group_ownership_preserved",
            status="confirmed",
            evidence={
                "active": canonical_active_npc_groups,
                "owner_stage": 30,
                "relation_mismatches": npc_group_relation_mismatches,
                "tombstones": canonical_npc_group_tombstones,
            },
        )

        connection.execute(
            f"""
            INSERT OR REPLACE INTO main.entities
            SELECT * FROM {stage30_alias}.entities
            WHERE kind='npc'
              AND state='confirmed'
              AND lifecycle='present'
            """
        )
        for stage, alias, _, _ in aliases:
            if stage not in {20, 40, 50}:
                continue
            connection.execute(
                f"""
                INSERT OR REPLACE INTO main.entities
                SELECT * FROM {alias}.entities
                WHERE kind='npc'
                  AND state='tombstone'
                  AND lifecycle='tombstone'
                """
            )
        canonical_active_npcs = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='npc'
                  AND source_stage=30
                  AND state='confirmed'
                  AND lifecycle='present'
                """
            ).fetchone()[0]
        )
        canonical_npc_tombstones = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM entities
                WHERE kind='npc'
                  AND state='tombstone'
                  AND lifecycle='tombstone'
                """
            ).fetchone()[0]
        )
        npc_relation_mismatches = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM relations r
                JOIN entities d ON d.entity_key=r.dst_entity_key
                WHERE d.kind='npc'
                  AND (
                      r.authority='client_native'
                      OR r.provenance IN (
                          'client_compact_8',
                          'game11_native',
                          'x2game_confirmed'
                      )
                  )
                  AND r.state<>'confirmed'
                """
            ).fetchone()[0]
        )
        if canonical_active_npcs != NPCS_NATIVE_ROWS:
            raise RuntimeError(
                "Consolidated active NPC ownership is not closed in Stage 30"
            )
        if canonical_npc_tombstones != NPCS_REFERENCED_TOMBSTONES:
            raise RuntimeError(
                "Consolidated referenced NPC tombstones changed"
            )
        if npc_relation_mismatches:
            raise RuntimeError(
                "Consolidated exact native NPC relations are not confirmed"
            )
        _add_validation(
            connection,
            scope_kind="consolidated",
            scope_id="npc",
            check_name="npc_ownership_and_lifecycle_preserved",
            status="confirmed",
            evidence={
                "active": canonical_active_npcs,
                "owner_stage": 30,
                "relation_mismatches": npc_relation_mismatches,
                "tombstones": canonical_npc_tombstones,
            },
        )

        connection.commit()
        native_manifest = json.loads(
            context.config.source_native_code_manifest.read_text(
                encoding="utf-8"
            )
        )
        if native_manifest.get("stage") != 15:
            raise RuntimeError("Native code manifest is not Stage 15")
        if native_manifest.get("client_build") != context.config.client_build:
            raise RuntimeError("Native code manifest belongs to another build")
        native_validation = native_manifest.get("validation", {})
        if (
            native_validation.get("quick_check") != "ok"
            or native_validation.get("integrity_check") != "ok"
            or int(native_validation.get("anticheat_engine_runs", -1)) != 0
        ):
            raise RuntimeError("Native code manifest is not validated")
        for stage, _, path, schema_version in aliases:
            digest = sha256_file(path)
            if stage == 15:
                expected_digest = str(
                    native_manifest.get("database", {}).get("sha256", "")
                ).upper()
                if digest.upper() != expected_digest:
                    raise RuntimeError(
                        "Stage 15 database SHA-256 does not match its manifest"
                    )
            lineage_artifact_key = (
                "stage:15" if stage == 15 else SOURCE_ARTIFACT_KEY
            )
            connection.execute(
                """
                INSERT INTO stage_lineage(
                    stage_id,database_name,database_sha256,schema_version,
                    source_artifact_key
                ) VALUES(?,?,?,?,?)
                """,
                (
                    stage,
                    path.name,
                    digest,
                    schema_version,
                    lineage_artifact_key,
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO artifacts(
                    artifact_key,source_stage,role,path,bytes,sha256,build,
                    authority,state,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"stage:{stage}",
                    80,
                    f"stage_database:{stage}",
                    path.name,
                    path.stat().st_size,
                    digest,
                    context.config.client_build,
                    "derived_forensic",
                    "confirmed",
                    TOOL_NAME,
                    canonical_json({"immutable_stage": True}),
                ),
            )

        connection.commit()
        for _, alias, _, _ in reversed(aliases):
            connection.execute(f"DETACH DATABASE {alias}")
        connection.execute("PRAGMA foreign_keys = ON")

        if include_native_semantic:
            semantic_import = _import_native_semantic_index(
                connection, context.config
            )
            _add_validation(
                connection,
                scope_kind="consolidated",
                scope_id="native-semantic-index-v1",
                check_name="native_semantic_index_preserved",
                status="confirmed",
                evidence={
                    **semantic_import,
                    "full_paths_remain_in_sidecar": True,
                    "pseudocode_copied": False,
                },
            )

        checks = {
            "orphan_properties": """
                SELECT COUNT(*) FROM entity_properties p
                LEFT JOIN entities e ON e.entity_key=p.entity_key
                WHERE e.entity_key IS NULL
            """,
            "orphan_relation_sources": """
                SELECT COUNT(*) FROM relations r
                LEFT JOIN entities e ON e.entity_key=r.src_entity_key
                WHERE e.entity_key IS NULL
            """,
            "orphan_relation_destinations": """
                SELECT COUNT(*) FROM relations r
                LEFT JOIN entities e ON e.entity_key=r.dst_entity_key
                WHERE e.entity_key IS NULL
            """,
            "orphan_cached_results": """
                SELECT COUNT(*) FROM cached_results r
                LEFT JOIN query_specs q ON q.query_key=r.query_key
                WHERE q.query_key IS NULL
            """,
            "orphan_cached_rows": """
                SELECT COUNT(*) FROM cached_result_rows r
                LEFT JOIN query_specs q ON q.query_key=r.query_key
                WHERE q.query_key IS NULL
            """,
            "orphan_wiki_properties": """
                SELECT COUNT(*) FROM wiki_properties p
                LEFT JOIN wiki_entities e
                  ON e.wiki_entity_key=p.wiki_entity_key
                WHERE e.wiki_entity_key IS NULL
            """,
            "orphan_wiki_relation_sources": """
                SELECT COUNT(*) FROM wiki_relations r
                LEFT JOIN wiki_entities e
                  ON e.wiki_entity_key=r.src_wiki_entity_key
                WHERE e.wiki_entity_key IS NULL
            """,
            "orphan_blocker_impacts": """
                SELECT COUNT(*) FROM blocker_impacts i
                LEFT JOIN blocker_roots r
                  ON r.blocker_root_key=i.blocker_root_key
                WHERE r.blocker_root_key IS NULL
            """,
            "orphan_blocker_evidence": """
                SELECT COUNT(*) FROM blocker_evidence e
                LEFT JOIN blocker_roots r
                  ON r.blocker_root_key=e.blocker_root_key
                WHERE r.blocker_root_key IS NULL
            """,
            "orphan_work_queue": """
                SELECT COUNT(*) FROM work_queue q
                LEFT JOIN blocker_roots r
                  ON r.blocker_root_key=q.blocker_root_key
                WHERE r.blocker_root_key IS NULL
            """,
            "orphan_native_code_evidence_consumers": """
                SELECT COUNT(*) FROM native_code_evidence_links link
                LEFT JOIN consumers consumer
                  ON consumer.consumer_key=link.consumer_key
                WHERE consumer.consumer_key IS NULL
            """,
            "orphan_native_semantic_function_roots": """
                SELECT COUNT(*) FROM native_semantic_function_states f
                LEFT JOIN native_semantic_roots r
                  ON r.root_key=f.primary_root_key
                WHERE f.primary_root_key IS NOT NULL AND r.root_key IS NULL
            """,
            "orphan_native_semantic_links": """
                SELECT COUNT(*) FROM native_semantic_links l
                LEFT JOIN native_semantic_roots r USING(root_key)
                WHERE r.root_key IS NULL
            """,
            "orphan_native_semantic_queue": """
                SELECT COUNT(*) FROM native_semantic_work_queue q
                LEFT JOIN native_semantic_roots r USING(root_key)
                WHERE r.root_key IS NULL
            """,
        }
        for check_name, sql in checks.items():
            count = int(connection.execute(sql).fetchone()[0])
            if count:
                raise RuntimeError(f"{check_name}={count}")
            _add_validation(
                connection,
                scope_kind="database",
                scope_id=target.name,
                check_name=check_name,
                status="confirmed",
                evidence={"count": count},
            )

        validation = _finalize(connection, target.name)
        connection.close()
        connection = None
        temporary.replace(target)
    except Exception:
        if connection is not None:
            connection.close()
        temporary.unlink(missing_ok=True)
        raise

    manifest = _write_stage_manifest(
        context,
        stage=80,
        classification="stage_80_consolidated_transversal_graph",
        database=target,
        validation=validation,
    )
    if stage_manifests is not None:
        manifest["stage_manifests"] = [
            {
                "stage": item["stage"],
                "database_sha256": item["database"]["sha256"],
                "manifest_sha256": item["manifest"]["sha256"],
            }
            for item in stage_manifests
        ]
    return manifest


def _write_exports(config: ForensicsConfig) -> dict[str, Any]:
    connection = open_read_only(config.consolidated)
    try:
        opaque = [
            dict(row)
            for row in connection.execute(
                """
                SELECT opaque_key,surface,locator,blocker_code,reason,
                       searched_evidence_json,source_stage,state
                FROM opaque_regions
                WHERE state IN ('blocked','missing','opaque','unknown')
                ORDER BY opaque_key
                """
            )
        ]
        for row in opaque:
            row["searched_evidence"] = _json_object(
                row.pop("searched_evidence_json")
            )
        opaque_path = config.output_dir / "opaque-regions.json"
        atomic_text(
            opaque_path,
            canonical_json(
                {
                    "classification": "opaque_regions_are_blockers",
                    "count": len(opaque),
                    "regions": opaque,
                },
                pretty=True,
            ),
        )

        coverage_rows = list(
            connection.execute(
                """
                SELECT authority,dimension,state,COUNT(*) AS row_count
                FROM coverage
                GROUP BY authority,dimension,state
                ORDER BY authority,dimension,state
                """
            )
        )
        coverage_path = config.output_dir / "coverage-summary.csv"
        handle, name = tempfile.mkstemp(
            prefix=".coverage-summary.",
            suffix=".csv",
            dir=config.output_dir,
        )
        os.close(handle)
        temporary = Path(name)
        try:
            with temporary.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(("authority", "dimension", "state", "row_count"))
                for row in coverage_rows:
                    writer.writerow(tuple(row))
            temporary.replace(coverage_path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    finally:
        connection.close()
    return {
        "coverage_summary": {
            "path": coverage_path.resolve().as_posix(),
            "sha256": sha256_file(coverage_path),
        },
        "opaque_regions": {
            "path": opaque_path.resolve().as_posix(),
            "sha256": sha256_file(opaque_path),
        },
    }


def finalize_outputs(
    config: ForensicsConfig,
    *,
    consolidated_manifest: dict[str, Any] | None = None,
    stage_manifests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if consolidated_manifest is None:
        path = config.consolidated.with_suffix(".manifest.json")
        if not path.is_file():
            raise FileNotFoundError(path)
        consolidated_manifest = json.loads(path.read_text(encoding="utf-8"))
    if stage_manifests is None:
        stage_manifests = []
        for database in (
            config.stage_00,
            config.stage_10,
            config.stage_15,
            config.stage_20,
            config.stage_30,
            config.stage_40,
            config.stage_50,
            config.stage_60,
            config.stage_70,
            config.stage_90,
        ):
            path = database.with_suffix(".manifest.json")
            if not path.is_file():
                raise FileNotFoundError(path)
            stage_manifests.append(json.loads(path.read_text(encoding="utf-8")))
    exports = _write_exports(config)
    exports.update(
        generate_static_viewer(config.consolidated, config.output_dir)
    )
    final_manifest = {
        "authority": "client_forensics_only",
        "classification": "aa8_client_transversal_knowledge_v1",
        "client_build": config.client_build,
        "consolidated": consolidated_manifest,
        "exports": exports,
        "historical_3_0_gameplay_rows": 0,
        "server_mutation": "forbidden",
        "stage_manifests": stage_manifests,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }
    atomic_text(config.manifest, canonical_json(final_manifest, pretty=True))
    return {
        "consolidated": {
            "path": config.consolidated,
            "sha256": consolidated_manifest["database"]["sha256"],
            "counts": consolidated_manifest["table_counts"],
        },
        "manifest": {
            "path": config.manifest,
            "sha256": sha256_file(config.manifest),
        },
        "stages": [
            {
                "stage": item["stage"],
                "path": Path(item["database"]["path"]),
                "sha256": item["database"]["sha256"],
            }
            for item in stage_manifests
        ],
    }


def run_all(config: ForensicsConfig) -> dict[str, Any]:
    context = BuildContext.create(config)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    stage_manifests = [
        build_stage_00(context),
        build_stage_10(context),
        json.loads(config.source_native_code_manifest.read_text(encoding="utf-8")),
        build_stage_20(context),
        build_stage_30(context),
        build_stage_40(context),
        build_stage_50(context),
        build_stage_60(context),
        build_stage_70(context),
    ]
    consolidate(
        context,
        stage_manifests,
        include_stage_90=False,
    )
    stage_manifests.append(build_stage_90(context))
    consolidated_manifest = consolidate(
        context,
        stage_manifests,
        include_stage_90=True,
    )
    return finalize_outputs(
        config,
        consolidated_manifest=consolidated_manifest,
        stage_manifests=stage_manifests,
    )
