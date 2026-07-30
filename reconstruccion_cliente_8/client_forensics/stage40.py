from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from . import TOOL_NAME, TOOL_VERSION
from .native_domains import (
    QUEST_DETAIL_LABELS,
    SCALAR_DOMAIN_SPECS,
    audit_quest_detail_parity,
    audit_scalar_domains,
    quest_detail_reference_counts,
)
from .quests import (
    QuestResult,
    act_detail_table,
    compare_quest_layouts,
    decode_effect_fire_details,
    decode_quest_core,
    quest_act_detail_counts,
    quest_loader_inventory,
    relation_target,
    table_entity_identity,
)
from .quest_text_kinds import audit_quest_text_kind_domains
from .quest_inline_semantics import audit_inline_quest_semantics
from .schema import open_read_only
from .util import canonical_json, entity_key, sha256_file, stable_key, typed_value
from .world_actors import unresolved_reference


STAGE = 40
STREAM_ARTIFACT = "stage40:stream-game11"
COMPACT_ARTIFACT = "stage40:client-compact"
X64_ARTIFACT = "stage40:ghidra-quest-loaders-x64"
X86_ARTIFACT = "stage40:ghidra-quest-loaders-x86"
CALL_SEQUENCE_ARTIFACT = "stage40:sql-call-sequence"
SQL_SURFACE_ARTIFACT = "stage40:sql-surface-manifest"
TASK_ARTIFACT = "stage40:quest-loader-tasks"
ENUM_X64_ARTIFACT = "stage40:ghidra-enum-consumers-x64"
ENUM_X86_ARTIFACT = "stage40:ghidra-enum-consumers-x86"
BUBBLE_CALLBACK_ARTIFACT = "stage40:ghidra-quest-bubble-callbacks-x64"
COMPONENT_STRUCT_ARTIFACT = "stage40:ghidra-quest-component-struct-x64"
SCALAR_API_X64_ARTIFACT = "stage40:ghidra-quest-scalar-api-x64"
SCALAR_CONSUMERS_X64_ARTIFACT = (
    "stage40:ghidra-quest-scalar-consumers-x64"
)
SCALAR_CONSUMERS_X86_ARTIFACT = (
    "stage40:ghidra-quest-scalar-consumers-x86"
)
COMPONENT_CONTEXT_X64_ARTIFACT = (
    "stage40:ghidra-component-accessor-context-x64"
)
COMPONENT_CONTEXT_X86_ARTIFACT = (
    "stage40:ghidra-component-accessor-context-x86"
)
COMPONENT_TEXT_VECTOR_X64_ARTIFACT = (
    "stage40:ghidra-component-text-vector-trace-x64"
)
COMPONENT_TEXT_VECTOR_X86_ARTIFACT = (
    "stage40:ghidra-component-text-vector-trace-x86"
)
COMPONENT_TEXT_DATA_X64_ARTIFACT = (
    "stage40:ghidra-component-text-data-x64"
)
COMPONENT_TEXT_DATA_X86_ARTIFACT = (
    "stage40:ghidra-component-text-data-x86"
)
UI_EVENT_CORE_X64_ARTIFACT = "stage40:ghidra-ui-event-core-x64"
UI_EVENT_CORE_X86_ARTIFACT = "stage40:ghidra-ui-event-core-x86"
COMPONENT_TEXT_SURFACE_ARTIFACT = (
    "stage40:component-text-surface-snapshot"
)
NPC_AI_FIELD_TRACE_X64_ARTIFACT = "stage40:ghidra-npc-ai-field-trace-x64"
NPC_AI_FIELD_TRACE_X86_ARTIFACT = "stage40:ghidra-npc-ai-field-trace-x86"
NPC_AI_HELPERS_X64_ARTIFACT = "stage40:ghidra-npc-ai-helpers-x64"
NPC_AI_HELPERS_X86_ARTIFACT = "stage40:ghidra-npc-ai-helpers-x86"
NPC_AI_RAW_VECTOR_X64_ARTIFACT = "stage40:ghidra-npc-ai-raw-vector-x64"
NPC_AI_RAW_VECTOR_X86_ARTIFACT = "stage40:ghidra-npc-ai-raw-vector-x86"
COMPONENT_COPY_X86_ARTIFACT = "stage40:ghidra-quest-component-copy-x86"
NPC_AI_BINDINGS_X64_ARTIFACT = "stage40:ghidra-npc-ai-bindings-x64"
NPC_AI_BINDINGS_X86_ARTIFACT = "stage40:ghidra-npc-ai-bindings-x86"
NPC_AI_STUBS_X64_ARTIFACT = "stage40:ghidra-npc-ai-stubs-x64"
NPC_AI_STUBS_X86_ARTIFACT = "stage40:ghidra-npc-ai-stubs-x86"
NPC_AI_SURFACE_ARTIFACT = "stage40:npc-ai-surface-snapshot"
CHAT_BUBBLE_LUA_ARTIFACT = "stage40:lua-chat-bubble"
QUEST_DIRECTING_LUA_ARTIFACT = "stage40:lua-quest-directing"
WIKI_KIND_MAP = {
    "achievements": "achievement",
    "buffs": "buff",
    "crafts": "craft",
    "doodads": "doodad",
    "items": "item",
    "npcs": "npc",
    "quests": "quest",
    "skills": "skill",
    "slaves": "slave",
    "titles": "title",
}


def _artifact(
    connection: sqlite3.Connection,
    *,
    key: str,
    role: str,
    path: Path,
    build: str,
    authority: str,
) -> str:
    digest = sha256_file(path)
    connection.execute(
        """
        INSERT INTO artifacts(
            artifact_key,source_stage,role,path,bytes,sha256,build,authority,
            state,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            key,
            STAGE,
            role,
            path.resolve().as_posix(),
            path.stat().st_size,
            digest,
            build,
            authority,
            "confirmed",
            TOOL_NAME,
            canonical_json({"immutable_input": True}),
        ),
    )
    return digest


def _entity(
    connection: sqlite3.Connection,
    *,
    kind: str,
    native_id: Any,
    subtype: str | None,
    lifecycle: str,
    state: str,
    authority: str = "client_native",
    provenance: str = TOOL_NAME,
    evidence: dict[str, Any] | None = None,
) -> str:
    key = entity_key(kind, native_id)
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
            STAGE,
            provenance,
            canonical_json(evidence or {}),
        ),
    )
    return key


def _property(
    connection: sqlite3.Connection,
    *,
    owner: str,
    namespace: str,
    name: str,
    value: Any,
    ordinal: int,
    locator: str,
    consumer: str | None,
    state: str,
    artifact: str = STREAM_ARTIFACT,
    authority: str = "client_native",
    evidence: dict[str, Any] | None = None,
) -> None:
    value_type, text, integer, real, boolean, json_value = typed_value(value)
    connection.execute(
        """
        INSERT OR IGNORE INTO entity_properties(
            property_key,entity_key,namespace,property_name,ordinal,value_type,
            value_text,value_integer,value_real,value_boolean,value_json,state,
            authority,source_artifact_key,locator,consumer,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
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
            canonical_json(evidence or {}),
        ),
    )


def _relation(
    connection: sqlite3.Connection,
    *,
    src: str,
    relation: str,
    dst: str,
    ordinal: int,
    locator: str,
    consumer: str | None,
    state: str,
    required: int = 0,
    evidence: dict[str, Any] | None = None,
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
            "client_native",
            STREAM_ARTIFACT,
            locator,
            consumer,
            TOOL_NAME,
            canonical_json(evidence or {"foreign_key_value_observed": True}),
        ),
    )


def _prior_entities(config: Any) -> dict[tuple[str, str], dict[str, str]]:
    result: dict[tuple[str, str], dict[str, str]] = {}
    for path in (config.stage_20, config.stage_30):
        connection = open_read_only(path)
        try:
            for row in connection.execute(
                """
                SELECT kind,native_id,state,lifecycle,authority
                FROM entities ORDER BY kind,native_id
                """
            ):
                result[(str(row["kind"]), str(row["native_id"]))] = {
                    "state": str(row["state"]),
                    "lifecycle": str(row["lifecycle"]),
                    "authority": str(row["authority"]),
                    "source": path.name,
                }
        finally:
            connection.close()
    return result


def _endpoint(
    connection: sqlite3.Connection,
    *,
    kind: str,
    native_id: int,
    prior: dict[tuple[str, str], dict[str, str]],
    quest_ids: set[int],
) -> tuple[str, str]:
    key = entity_key(kind, native_id)
    current = connection.execute(
        "SELECT state FROM entities WHERE entity_key=?",
        (key,),
    ).fetchone()
    if current is not None:
        return key, str(current["state"])
    if kind == "quest" and native_id in quest_ids:
        return key, "confirmed"
    known = prior.get((kind, str(native_id)))
    if known is not None:
        return (
            _entity(
                connection,
                kind=kind,
                native_id=native_id,
                subtype=None,
                lifecycle=known["lifecycle"],
                state=known["state"],
                authority=known["authority"],
                provenance="prior_forensic_stage",
                evidence={"confirmed_by": known["source"]},
            ),
            known["state"],
        )
    return (
        _entity(
            connection,
            kind=kind,
            native_id=native_id,
            subtype=None,
            lifecycle="referenced",
            state="unknown",
            evidence={"endpoint_materialized_for_graph_closure": True},
        ),
        "unknown",
    )


def _materialize_native_domains(
    connection: sqlite3.Connection,
    *,
    scalar_audits: dict[str, dict[str, Any]],
    quest_detail_audit: dict[str, Any],
    quest_detail_counts: Counter[int],
) -> int:
    property_count = 0
    for native_id, label in sorted(QUEST_DETAIL_LABELS.items()):
        owner = _entity(
            connection,
            kind="quest_detail",
            native_id=native_id,
            subtype="inline_scalar_enum",
            lifecycle="present",
            state="confirmed",
            evidence={
                "domain_type": "inline_scalar_enum",
                "semantic_label": label,
                "semantic_label_state": "confirmed",
                "x64_consumer": quest_detail_audit["x64_consumer"],
                "x86_consumer": quest_detail_audit["x86_consumer"],
                "architecture_parity": True,
                "invalid_sentinel": quest_detail_audit["invalid_sentinel"],
            },
        )
        for name, value in (
            ("enum_value", native_id),
            ("semantic_label", label),
            ("observed_reference_count", quest_detail_counts.get(native_id, 0)),
        ):
            _property(
                connection,
                owner=owner,
                namespace="native_enum",
                name=name,
                value=value,
                ordinal=0,
                locator=f"quest_detail[{native_id}].{name}",
                consumer=str(quest_detail_audit["x64_consumer"]),
                state="confirmed",
                artifact=ENUM_X64_ARTIFACT,
                evidence={"x86_x64_parity": True},
            )
            property_count += 1

    for kind, audit in sorted(scalar_audits.items()):
        for native_id in audit["ids"]:
            label = audit.get("labels", {}).get(native_id)
            candidate = audit.get("semantic_candidates", {}).get(native_id)
            owner = _entity(
                connection,
                kind=kind,
                native_id=native_id,
                subtype="inline_scalar_enum",
                lifecycle="present",
                state="confirmed",
                evidence={
                    "domain_type": audit["domain_type"],
                    "source_table": audit["source_table"],
                    "source_column": audit["source_column"],
                    "loader_x64": audit["loader_x64"],
                    "owner_query_absent": audit["owner_query_absent"],
                    "semantic_label_state": audit["semantic_label_state"],
                    "semantic_label": label,
                    "semantic_candidate": candidate,
                },
            )
            for name, value in (
                ("enum_value", native_id),
                (
                    "observed_reference_count",
                    int(audit["counts"][str(native_id)]),
                ),
                ("source_column", audit["source_column"]),
            ):
                _property(
                    connection,
                    owner=owner,
                    namespace="native_enum",
                    name=name,
                    value=value,
                    ordinal=0,
                    locator=f"{kind}[{native_id}].{name}",
                    consumer=str(audit["loader_x64"]),
                    state="confirmed",
                    artifact=X64_ARTIFACT,
                    evidence={
                        "inline_domain_membership_confirmed": True,
                        "semantic_label_state": audit["semantic_label_state"],
                    },
                )
                property_count += 1
            if label is not None:
                label_consumer = (
                    audit.get("consumers", {})
                    .get(native_id, {})
                    .get("x64", audit["loader_x64"])
                )
                if isinstance(label_consumer, list):
                    label_consumer = label_consumer[0]
                _property(
                    connection,
                    owner=owner,
                    namespace="native_enum",
                    name="semantic_label",
                    value=label,
                    ordinal=0,
                    locator=f"{kind}[{native_id}].semantic_label",
                    consumer=str(label_consumer),
                    state="confirmed",
                    artifact=(
                        (
                            COMPONENT_TEXT_DATA_X64_ARTIFACT
                            if native_id == 5
                            else (
                                UI_EVENT_CORE_X64_ARTIFACT
                                if native_id == 6
                                else NPC_AI_HELPERS_X64_ARTIFACT
                            )
                        )
                        if kind == "quest_component_text_kind"
                        else ENUM_X64_ARTIFACT
                    ),
                    evidence={
                        "architecture_parity": audit.get(
                            "architecture_parity", False
                        ),
                        "semantic_label_state": audit[
                            "semantic_label_state"
                        ],
                    },
                )
                property_count += 1
            if candidate is not None:
                _property(
                    connection,
                    owner=owner,
                    namespace="native_enum",
                    name="semantic_candidate",
                    value=candidate,
                    ordinal=0,
                    locator=f"{kind}[{native_id}].semantic_candidate",
                    consumer=None,
                    state="corroborated",
                    artifact=X64_ARTIFACT,
                    evidence=audit.get("correlations", {}).get(
                        str(native_id), {}
                    ),
                )
                property_count += 1
            for name, specification in sorted(
                audit.get("domain_properties", {}).items()
            ):
                domain_artifact = X64_ARTIFACT
                if kind == "npc_ai":
                    domain_artifact = (
                        NPC_AI_STUBS_X64_ARTIFACT
                        if name in {
                            "behavior_authority",
                            "client_behavior_implementation",
                        }
                        else NPC_AI_FIELD_TRACE_X64_ARTIFACT
                    )
                elif kind == "quest_component_text_kind":
                    domain_artifact = COMPONENT_TEXT_VECTOR_X64_ARTIFACT
                _property(
                    connection,
                    owner=owner,
                    namespace="native_enum",
                    name=name,
                    value=specification["value"],
                    ordinal=0,
                    locator=f"{kind}[{native_id}].{name}",
                    consumer=None,
                    state=str(specification["state"]),
                    artifact=domain_artifact,
                    evidence={
                        "architecture_parity": audit.get(
                            "architecture_parity", False
                        ),
                        "client_consumer_state": audit.get(
                            "client_consumer_state"
                        ),
                        "behavior_authority_state": audit.get(
                            "behavior_authority_state"
                        ),
                    },
                )
                property_count += 1
            for name, specification in sorted(
                audit.get("value_properties", {})
                .get(native_id, {})
                .items()
            ):
                _property(
                    connection,
                    owner=owner,
                    namespace="native_enum",
                    name=name,
                    value=specification["value"],
                    ordinal=0,
                    locator=f"{kind}[{native_id}].{name}",
                    consumer=None,
                    state=str(specification["state"]),
                    artifact=(
                        COMPONENT_TEXT_VECTOR_X64_ARTIFACT
                        if kind == "quest_component_text_kind"
                        else X64_ARTIFACT
                    ),
                    evidence={
                        "architecture_parity": audit.get(
                            "architecture_parity", False
                        ),
                        "row_population_lifecycle": True,
                    },
                )
                property_count += 1

            consumer = audit.get("consumers", {}).get(native_id)
            if consumer is not None:
                consumer_artifacts = (
                    (
                        "x64",
                        (
                            NPC_AI_HELPERS_X64_ARTIFACT
                            if kind == "quest_component_text_kind"
                            else ENUM_X64_ARTIFACT
                        ),
                    ),
                    (
                        "x86",
                        (
                            NPC_AI_HELPERS_X86_ARTIFACT
                            if kind == "quest_component_text_kind"
                            else ENUM_X86_ARTIFACT
                        ),
                    ),
                )
                for architecture, artifact in consumer_artifacts:
                    functions = consumer[architecture]
                    if not isinstance(functions, list):
                        functions = [functions]
                    for ordinal, function_name in enumerate(functions):
                        connection.execute(
                            """
                            INSERT INTO consumers(
                                consumer_key,scope_key,consumer_kind,name,
                                module,locator,architecture,state,evidence_json
                            ) VALUES(?,?,?,?,?,?,?,?,?)
                            """,
                            (
                                stable_key(
                                    "stage40",
                                    kind,
                                    native_id,
                                    architecture,
                                    function_name,
                                    ordinal,
                                ),
                                owner,
                                "native_enum_consumer",
                                str(consumer.get("api", function_name)),
                                "x2game.dll",
                                str(function_name),
                                architecture,
                                "confirmed",
                                canonical_json(
                                    {
                                        "artifact": artifact,
                                        "native_id": native_id,
                                        "semantic_label": label,
                                    }
                                ),
                            ),
                        )
    return property_count


def _materialize_quest_text_kind_domains(
    connection: sqlite3.Connection,
    *,
    audits: dict[str, dict[str, Any]],
) -> int:
    property_count = 0
    for kind, audit in sorted(audits.items()):
        dormant_values = set(audit.get("dormant_values", []))
        for native_id in audit["ids"]:
            label = str(audit["labels"][native_id])
            dormant = native_id in dormant_values
            consumer = audit["consumers"].get(native_id)
            owner = _entity(
                connection,
                kind=kind,
                native_id=native_id,
                subtype="inline_scalar_enum",
                lifecycle=("dormant_fixture" if dormant else "present"),
                state="confirmed",
                evidence={
                    "architecture_parity": audit["architecture_parity"],
                    "domain_type": audit["domain_type"],
                    "loader_x64": audit["loader_x64"],
                    "loader_x86": audit["loader_x86"],
                    "owner_query_absent": audit["owner_query_absent"],
                    "semantic_label": label,
                    "semantic_label_state": (
                        "native_fixture_literal"
                        if dormant
                        else "confirmed"
                    ),
                    "source_column": audit["source_column"],
                    "source_table": audit["source_table"],
                },
            )
            properties = (
                ("enum_value", native_id, "confirmed"),
                ("semantic_label", label, "corroborated" if dormant else "confirmed"),
                (
                    "observed_reference_count",
                    int(audit["counts"][str(native_id)]),
                    "confirmed",
                ),
                ("source_column", audit["source_column"], "confirmed"),
                (
                    "consumer_state",
                    "not_applicable" if dormant else "confirmed",
                    "confirmed",
                ),
            )
            for name, value, state in properties:
                _property(
                    connection,
                    owner=owner,
                    namespace="native_enum",
                    name=name,
                    value=value,
                    ordinal=0,
                    locator=f"{kind}[{native_id}].{name}",
                    consumer=(
                        None if consumer is None else str(consumer["x64"])
                    ),
                    state=state,
                    artifact=(
                        STREAM_ARTIFACT
                        if dormant and name == "semantic_label"
                        else SCALAR_CONSUMERS_X64_ARTIFACT
                    ),
                    evidence={
                        "architecture_parity": True,
                        "dormant_fixture": dormant,
                    },
                )
                property_count += 1

            if consumer is not None:
                for architecture, artifact in (
                    ("x64", SCALAR_CONSUMERS_X64_ARTIFACT),
                    ("x86", SCALAR_CONSUMERS_X86_ARTIFACT),
                ):
                    function_name = str(consumer[architecture])
                    connection.execute(
                        """
                        INSERT INTO consumers(
                            consumer_key,scope_key,consumer_kind,name,module,
                            locator,architecture,state,evidence_json
                        ) VALUES(?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            stable_key(
                                "stage40",
                                "quest-text-kind-consumer",
                                owner,
                                architecture,
                            ),
                            owner,
                            "native_scalar_accessor",
                            str(consumer["api"]),
                            "x2game.dll",
                            function_name,
                            architecture,
                            "confirmed",
                            canonical_json(
                                {
                                    "artifact_key": artifact,
                                    "enum_value": native_id,
                                    "semantic_label": label,
                                }
                            ),
                        ),
                    )

            for dimension, state in (
                ("identity", "confirmed"),
                ("schema_layout", "confirmed"),
                ("properties", "confirmed"),
                ("relations", "confirmed"),
                ("consumer", "not_applicable" if dormant else "confirmed"),
                ("lifecycle", "confirmed"),
            ):
                connection.execute(
                    """
                    INSERT INTO coverage(
                        coverage_key,scope_key,dimension,state,capability,
                        authority,provenance,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        stable_key("coverage", owner, dimension),
                        owner,
                        dimension,
                        state,
                        label,
                        "client_native",
                        TOOL_NAME,
                        canonical_json(
                            {
                                "architecture_parity": True,
                                "dormant_fixture": dormant,
                            }
                        ),
                    ),
                )
    return property_count


def _insert_query(
    connection: sqlite3.Connection,
    *,
    result: QuestResult,
    source_id: int,
) -> str:
    query_key = f"stage40:query:{result.spec.call_index}:{result.spec.table}"
    connection.execute(
        """
        INSERT INTO query_specs(
            query_key,source_query_spec_id,table_name,source_module,sql_text,
            columns_json,layout_json,stream_name,start_offset,expected_rows,
            anchor_json,loader_consumer,state,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            query_key,
            source_id,
            result.spec.table,
            X64_ARTIFACT,
            result.spec.sql,
            canonical_json(result.spec.columns),
            canonical_json(result.spec.layout),
            "game11",
            result.start,
            len(result.rows),
            canonical_json(
                {
                    "header": result.header,
                    "done": result.done,
                    "advertised_rows": result.advertised_rows,
                }
            ),
            f"x2game.dll {result.spec.loader}",
            "confirmed",
            canonical_json(
                {
                    "call_index": result.spec.call_index,
                    "loader_address_x64": result.spec.loader_address,
                    "header_mapping": (
                        "mapped_call_index - 53 for the contiguous quest block"
                        if result.spec.call_index >= 480
                        else "exact structural match and act-detail closure"
                    ),
                }
            ),
        ),
    )
    connection.execute(
        """
        INSERT INTO cached_results(
            cached_result_key,source_cached_result_id,query_key,artifact_key,
            start_offset,end_offset,row_count,row_digest,raw_references_json,
            unresolved_references_json,resolution_evidence_json,state,error
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            f"stage40:cached:{result.spec.call_index}:{result.spec.table}",
            source_id,
            query_key,
            STREAM_ARTIFACT,
            result.start,
            result.done,
            len(result.rows),
            result.digest,
            canonical_json(result.token_counts),
            canonical_json(result.unresolved_references),
            canonical_json(
                {
                    **result.resolution_evidence,
                    "quest_act_string_seed": (
                        {
                            "first_reference": 320614,
                            "next_reference": 320699,
                            "resolved": result.token_counts.get(
                                "resolved_reference", 0
                            ),
                        }
                        if result.spec.table == "quest_acts"
                        else None
                    )
                }
            ),
            (
                "confirmed"
                if not result.unresolved_references
                else "blocked"
            ),
            (
                None
                if not result.unresolved_references
                else "non-gameplay cached string references remain unresolved"
            ),
        ),
    )
    connection.executemany(
        """
        INSERT INTO cached_result_rows(query_key,row_index,row_json)
        VALUES(?,?,?)
        """,
        [
            (query_key, index, canonical_json(row))
            for index, row in enumerate(result.rows)
        ],
    )
    return query_key


def _localized_identity(table: str, native_id: int) -> tuple[str, str]:
    return table_entity_identity(table, native_id)


def _import_wiki_evidence(
    connection: sqlite3.Connection,
    *,
    config: Any,
    input_hashes: dict[str, str],
    prior: set[str],
) -> dict[str, int]:
    tool_parent = str(config.source_item_tool_root.parent)
    if tool_parent not in sys.path:
        sys.path.insert(0, tool_parent)
    from item_forensics.wiki import parse_wiki_page

    html_files = sorted(
        config.source_quest_wiki_cache.glob("*.html"),
        key=lambda path: int(path.stem),
    )
    if not html_files:
        raise RuntimeError("The frozen Stage 40 quest wiki snapshot is empty")
    counts = Counter()
    for html_path in html_files:
        quest_id = int(html_path.stem)
        meta_path = html_path.with_suffix(".meta.json")
        if not meta_path.is_file():
            raise RuntimeError(f"Missing wiki metadata for quest {quest_id}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for suffix, path in (("html", html_path), ("meta", meta_path)):
            artifact_key = f"stage40:wiki:quest:{quest_id}:{suffix}"
            input_hashes[artifact_key] = _artifact(
                connection,
                key=artifact_key,
                role=f"wiki_visible_quest_{suffix}",
                path=path,
                build=config.client_build,
                authority="wiki_visible",
            )
        payload = html_path.read_bytes()
        page = parse_wiki_page(
            payload,
            entity_kind="quests",
            entity_id=quest_id,
            locale=str(meta["locale"]),
        )
        if sha256_file(html_path) != str(meta["content_sha256"]):
            raise RuntimeError(f"Wiki payload hash mismatch for quest {quest_id}")
        owner = entity_key("quest", quest_id)
        native_exists = (
            connection.execute(
                "SELECT 1 FROM entities WHERE entity_key=?", (owner,)
            ).fetchone()
            is not None
        )
        comparison = (
            "corroborated_native_identity" if native_exists else "wiki_only"
        )
        wiki_key = f"wiki:na-en:quest:{quest_id}"
        connection.execute(
            """
            INSERT INTO wiki_entities(
                wiki_entity_key,entity_key,url,status_code,response_sha256,
                state,comparison_state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                wiki_key,
                owner,
                str(meta["url"]),
                int(meta["status_code"]),
                str(meta["content_sha256"]),
                page.parse_state,
                comparison,
                canonical_json(
                    {
                        "authority": "wiki_visible",
                        "parser_version": meta["parser_version"],
                        "text_digest": page.text_digest,
                    }
                ),
            ),
        )
        properties = {
            "page_type": page.page_type,
            "name": page.name,
            "category": page.category,
            "grade": page.grade,
            "level": page.level,
            "map_links": list(page.map_links),
        }
        for ordinal, (name, value) in enumerate(properties.items()):
            if value is None:
                continue
            connection.execute(
                """
                INSERT INTO wiki_properties(
                    wiki_property_key,wiki_entity_key,property_name,value_json,
                    comparison_state,evidence_json
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    stable_key("wiki-property", wiki_key, name, ordinal),
                    wiki_key,
                    name,
                    canonical_json(value),
                    "visible_only",
                    canonical_json({"authority": "wiki_visible"}),
                ),
            )
            counts["properties"] += 1
        for ordinal, link in enumerate(page.links):
            destination_kind = WIKI_KIND_MAP.get(link.kind, link.kind.rstrip("s"))
            destination = entity_key(destination_kind, link.entity_id)
            destination_known = (
                destination in prior
                or connection.execute(
                    "SELECT 1 FROM entities WHERE entity_key=?",
                    (destination,),
                ).fetchone()
                is not None
            )
            connection.execute(
                """
                INSERT INTO wiki_relations(
                    wiki_relation_key,src_wiki_entity_key,relation,dst_kind,
                    dst_id,comparison_state,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    stable_key(
                        "wiki-relation",
                        wiki_key,
                        link.relation_hint,
                        link.kind,
                        link.entity_id,
                        ordinal,
                    ),
                    wiki_key,
                    link.relation_hint,
                    destination_kind,
                    link.entity_id,
                    (
                        "destination_present_in_native_graph"
                        if destination_known
                        else "wiki_destination_not_yet_in_graph"
                    ),
                    canonical_json(
                        {
                            "authority": "wiki_visible",
                            "href": link.href,
                            "label": link.label,
                            "context": list(link.context),
                        }
                    ),
                ),
            )
            counts["relations"] += 1
        if native_exists:
            connection.execute(
                """
                UPDATE coverage
                SET state='confirmed',authority='wiki_visible',
                    provenance=?,evidence_json=?
                WHERE scope_key=? AND dimension='wiki'
                """,
                (
                    TOOL_NAME,
                    canonical_json(
                        {
                            "wiki_entity_key": wiki_key,
                            "comparison_state": comparison,
                        }
                    ),
                    owner,
                ),
            )
        counts["entities"] += 1
    return dict(counts)


def populate_stage_40(
    connection: sqlite3.Connection,
    source: sqlite3.Connection,
    context: Any,
) -> None:
    del source
    config = context.config
    input_hashes = {
        STREAM_ARTIFACT: _artifact(
            connection,
            key=STREAM_ARTIFACT,
            role="native_cached_stream",
            path=config.source_game11,
            build=config.client_build,
            authority="client_native",
        ),
        COMPACT_ARTIFACT: _artifact(
            connection,
            key=COMPACT_ARTIFACT,
            role="decrypted_client_compact",
            path=config.source_client_compact,
            build=config.client_build,
            authority="client_native",
        ),
        X64_ARTIFACT: _artifact(
            connection,
            key=X64_ARTIFACT,
            role="quest_loader_decompilation_x64",
            path=config.source_ghidra_sql_loaders_64,
            build=config.client_build,
            authority="client_native",
        ),
        X86_ARTIFACT: _artifact(
            connection,
            key=X86_ARTIFACT,
            role="quest_loader_decompilation_x86",
            path=config.source_ghidra_quest_loaders_x86,
            build=config.client_build,
            authority="client_native",
        ),
        CALL_SEQUENCE_ARTIFACT: _artifact(
            connection,
            key=CALL_SEQUENCE_ARTIFACT,
            role="native_sql_execution_sequence",
            path=config.source_ghidra_sql_call_sequence,
            build=config.client_build,
            authority="client_native",
        ),
        SQL_SURFACE_ARTIFACT: _artifact(
            connection,
            key=SQL_SURFACE_ARTIFACT,
            role="embedded_sql_inventory_x86_x64",
            path=config.source_sql_surface_manifest,
            build=config.client_build,
            authority="client_native",
        ),
        TASK_ARTIFACT: _artifact(
            connection,
            key=TASK_ARTIFACT,
            role="quest_loader_task_registry",
            path=config.source_quest_loader_tasks,
            build=config.client_build,
            authority="derived_forensic",
        ),
        ENUM_X64_ARTIFACT: _artifact(
            connection,
            key=ENUM_X64_ARTIFACT,
            role="native_enum_consumers_x64",
            path=config.source_ghidra_enum_consumers_x64,
            build=config.client_build,
            authority="client_native",
        ),
        ENUM_X86_ARTIFACT: _artifact(
            connection,
            key=ENUM_X86_ARTIFACT,
            role="native_enum_consumers_x86",
            path=config.source_ghidra_enum_consumers_x86,
            build=config.client_build,
            authority="client_native",
        ),
        BUBBLE_CALLBACK_ARTIFACT: _artifact(
            connection,
            key=BUBBLE_CALLBACK_ARTIFACT,
            role="quest_bubble_callbacks_x64",
            path=config.source_ghidra_quest_bubble_callbacks_x64,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_STRUCT_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_STRUCT_ARTIFACT,
            role="quest_component_struct_copy_x64",
            path=config.source_ghidra_quest_component_struct_x64,
            build=config.client_build,
            authority="client_native",
        ),
        SCALAR_API_X64_ARTIFACT: _artifact(
            connection,
            key=SCALAR_API_X64_ARTIFACT,
            role="quest_scalar_api_bindings_x64",
            path=config.source_ghidra_quest_scalar_api_x64,
            build=config.client_build,
            authority="client_native",
        ),
        SCALAR_CONSUMERS_X64_ARTIFACT: _artifact(
            connection,
            key=SCALAR_CONSUMERS_X64_ARTIFACT,
            role="quest_scalar_consumers_x64",
            path=config.source_ghidra_quest_scalar_consumers_x64,
            build=config.client_build,
            authority="client_native",
        ),
        SCALAR_CONSUMERS_X86_ARTIFACT: _artifact(
            connection,
            key=SCALAR_CONSUMERS_X86_ARTIFACT,
            role="quest_scalar_consumers_x86",
            path=config.source_ghidra_quest_scalar_consumers_x86,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_CONTEXT_X64_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_CONTEXT_X64_ARTIFACT,
            role="component_accessor_context_x64",
            path=config.source_ghidra_component_accessor_context_x64,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_CONTEXT_X86_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_CONTEXT_X86_ARTIFACT,
            role="component_accessor_context_x86",
            path=config.source_ghidra_component_accessor_context_x86,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_TEXT_VECTOR_X64_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_TEXT_VECTOR_X64_ARTIFACT,
            role="component_text_vector_trace_x64",
            path=config.source_ghidra_component_text_vector_trace_x64,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_TEXT_VECTOR_X86_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_TEXT_VECTOR_X86_ARTIFACT,
            role="component_text_vector_trace_x86",
            path=config.source_ghidra_component_text_vector_trace_x86,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_TEXT_DATA_X64_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_TEXT_DATA_X64_ARTIFACT,
            role="component_text_data_x64",
            path=config.source_ghidra_component_text_data_x64,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_TEXT_DATA_X86_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_TEXT_DATA_X86_ARTIFACT,
            role="component_text_data_x86",
            path=config.source_ghidra_component_text_data_x86,
            build=config.client_build,
            authority="client_native",
        ),
        UI_EVENT_CORE_X64_ARTIFACT: _artifact(
            connection,
            key=UI_EVENT_CORE_X64_ARTIFACT,
            role="ui_event_dispatch_core_x64",
            path=config.source_ghidra_ui_event_core_x64,
            build=config.client_build,
            authority="client_native",
        ),
        UI_EVENT_CORE_X86_ARTIFACT: _artifact(
            connection,
            key=UI_EVENT_CORE_X86_ARTIFACT,
            role="ui_event_dispatch_core_x86",
            path=config.source_ghidra_ui_event_core_x86,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_TEXT_SURFACE_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_TEXT_SURFACE_ARTIFACT,
            role="component_text_client_surface_snapshot",
            path=config.source_component_text_surface_snapshot,
            build=config.client_build,
            authority="derived_forensic",
        ),
        NPC_AI_FIELD_TRACE_X64_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_FIELD_TRACE_X64_ARTIFACT,
            role="npc_ai_field_trace_x64",
            path=config.source_ghidra_npc_ai_field_trace_x64,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_FIELD_TRACE_X86_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_FIELD_TRACE_X86_ARTIFACT,
            role="npc_ai_field_trace_x86",
            path=config.source_ghidra_npc_ai_field_trace_x86,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_HELPERS_X64_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_HELPERS_X64_ARTIFACT,
            role="npc_ai_forwarded_helpers_x64",
            path=config.source_ghidra_npc_ai_forwarded_helpers_x64,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_HELPERS_X86_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_HELPERS_X86_ARTIFACT,
            role="npc_ai_forwarded_helpers_x86",
            path=config.source_ghidra_npc_ai_forwarded_helpers_x86,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_RAW_VECTOR_X64_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_RAW_VECTOR_X64_ARTIFACT,
            role="npc_ai_raw_vector_x64",
            path=config.source_ghidra_npc_ai_raw_vector_x64,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_RAW_VECTOR_X86_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_RAW_VECTOR_X86_ARTIFACT,
            role="npc_ai_raw_vector_x86",
            path=config.source_ghidra_npc_ai_raw_vector_x86,
            build=config.client_build,
            authority="client_native",
        ),
        COMPONENT_COPY_X86_ARTIFACT: _artifact(
            connection,
            key=COMPONENT_COPY_X86_ARTIFACT,
            role="quest_component_struct_copy_x86",
            path=config.source_ghidra_quest_component_copy_x86,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_BINDINGS_X64_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_BINDINGS_X64_ARTIFACT,
            role="npc_ai_lua_bindings_x64",
            path=config.source_ghidra_npc_ai_lua_bindings_x64,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_BINDINGS_X86_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_BINDINGS_X86_ARTIFACT,
            role="npc_ai_lua_bindings_x86",
            path=config.source_ghidra_npc_ai_lua_bindings_x86,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_STUBS_X64_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_STUBS_X64_ARTIFACT,
            role="npc_ai_script_stubs_x64",
            path=config.source_ghidra_npc_ai_script_stubs_x64,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_STUBS_X86_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_STUBS_X86_ARTIFACT,
            role="npc_ai_script_stubs_x86",
            path=config.source_ghidra_npc_ai_script_stubs_x86,
            build=config.client_build,
            authority="client_native",
        ),
        NPC_AI_SURFACE_ARTIFACT: _artifact(
            connection,
            key=NPC_AI_SURFACE_ARTIFACT,
            role="npc_ai_client_surface_snapshot",
            path=config.source_npc_ai_surface_snapshot,
            build=config.client_build,
            authority="derived_forensic",
        ),
        CHAT_BUBBLE_LUA_ARTIFACT: _artifact(
            connection,
            key=CHAT_BUBBLE_LUA_ARTIFACT,
            role="chat_bubble_lua_consumer",
            path=(
                config.source_gamepak_lua64_root
                / "x2ui"
                / "chat"
                / "chatbubble.lua"
            ),
            build=config.client_build,
            authority="client_native",
        ),
        QUEST_DIRECTING_LUA_ARTIFACT: _artifact(
            connection,
            key=QUEST_DIRECTING_LUA_ARTIFACT,
            role="quest_directing_lua_consumer",
            path=(
                config.source_gamepak_lua64_root
                / "x2ui"
                / "questcontext"
                / "quest_context_directing.lua"
            ),
            build=config.client_build,
            authority="client_native",
        ),
    }

    architecture_evidence = compare_quest_layouts(
        config.source_ghidra_sql_loaders_64,
        config.source_ghidra_quest_loaders_x86,
        config.source_ghidra_sql_call_sequence,
    )
    connection.execute(
        """
        INSERT INTO decoders(
            decoder_key,name,version,sha256,status,inputs_json,
            assumptions_json,provenance
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "stage40:decoder:quest-cache",
            "AA8 quest cached-result decoder",
            TOOL_VERSION,
            None,
            "confirmed",
            canonical_json(input_hashes),
            canonical_json(
                {
                    "primitive_abi": ["38", "60", "68", "78"],
                    "core_call_range": [480, 604],
                    "header_delta": 53,
                    "architecture_evidence": architecture_evidence,
                }
            ),
            TOOL_NAME,
        ),
    )

    decoded = decode_quest_core(
        config.source_game11,
        config.source_ghidra_sql_loaders_64,
        config.source_ghidra_sql_call_sequence,
    )
    effect_fires = decode_effect_fire_details(
        config.source_game11,
        config.source_ghidra_sql_loaders_64,
    )
    decoded[effect_fires.spec.table] = effect_fires
    closure = quest_act_detail_counts(decoded, effect_fires)
    if closure["missing"]:
        raise RuntimeError(f"Quest act detail closure failed: {closure['missing']}")

    x64_inventory = quest_loader_inventory(config.source_ghidra_sql_loaders_64)
    if len(x64_inventory) != 156:
        raise RuntimeError(
            f"Expected 156 quest-related SQL surfaces, got {len(x64_inventory)}"
        )
    if Counter(value["state"] for value in x64_inventory) != {
        "confirmed_static": 154,
        "blocked": 2,
    }:
        raise RuntimeError("Quest SQL layout inventory changed")
    native_sql_tables = {str(value["table"]) for value in x64_inventory}
    scalar_audits = audit_scalar_domains(
        decoded,
        native_sql_tables=native_sql_tables,
    )
    inline_semantics = audit_inline_quest_semantics(
        decoded,
        enum_x64_path=config.source_ghidra_enum_consumers_x64,
        enum_x86_path=config.source_ghidra_enum_consumers_x86,
        component_context_x64_path=(
            config.source_ghidra_component_accessor_context_x64
        ),
        component_context_x86_path=(
            config.source_ghidra_component_accessor_context_x86
        ),
        component_copy_x64_path=(
            config.source_ghidra_quest_component_struct_x64
        ),
        component_copy_x86_path=(
            config.source_ghidra_quest_component_copy_x86
        ),
        npc_ai_field_trace_x64_path=(
            config.source_ghidra_npc_ai_field_trace_x64
        ),
        npc_ai_field_trace_x86_path=(
            config.source_ghidra_npc_ai_field_trace_x86
        ),
        npc_ai_forwarded_helpers_x64_path=(
            config.source_ghidra_npc_ai_forwarded_helpers_x64
        ),
        npc_ai_forwarded_helpers_x86_path=(
            config.source_ghidra_npc_ai_forwarded_helpers_x86
        ),
        npc_ai_raw_vector_x64_path=(
            config.source_ghidra_npc_ai_raw_vector_x64
        ),
        npc_ai_raw_vector_x86_path=(
            config.source_ghidra_npc_ai_raw_vector_x86
        ),
        npc_ai_lua_bindings_x64_path=(
            config.source_ghidra_npc_ai_lua_bindings_x64
        ),
        npc_ai_lua_bindings_x86_path=(
            config.source_ghidra_npc_ai_lua_bindings_x86
        ),
        npc_ai_script_stubs_x64_path=(
            config.source_ghidra_npc_ai_script_stubs_x64
        ),
        npc_ai_script_stubs_x86_path=(
            config.source_ghidra_npc_ai_script_stubs_x86
        ),
        npc_ai_surface_snapshot_path=(
            config.source_npc_ai_surface_snapshot
        ),
        component_text_vector_trace_x64_path=(
            config.source_ghidra_component_text_vector_trace_x64
        ),
        component_text_vector_trace_x86_path=(
            config.source_ghidra_component_text_vector_trace_x86
        ),
        component_text_data_x64_path=(
            config.source_ghidra_component_text_data_x64
        ),
        component_text_data_x86_path=(
            config.source_ghidra_component_text_data_x86
        ),
        ui_event_core_x64_path=config.source_ghidra_ui_event_core_x64,
        ui_event_core_x86_path=config.source_ghidra_ui_event_core_x86,
        component_text_surface_snapshot_path=(
            config.source_component_text_surface_snapshot
        ),
        lua64_root=config.source_gamepak_lua64_root,
    )
    for kind, semantics in inline_semantics.items():
        scalar_audits[kind].update(semantics)
    quest_text_kind_audits = audit_quest_text_kind_domains(
        decoded,
        native_sql_tables=native_sql_tables,
        api_x64_path=config.source_ghidra_quest_scalar_api_x64,
        consumers_x64_path=config.source_ghidra_quest_scalar_consumers_x64,
        consumers_x86_path=config.source_ghidra_quest_scalar_consumers_x86,
    )
    quest_detail_audit = audit_quest_detail_parity(
        config.source_ghidra_enum_consumers_x64,
        config.source_ghidra_enum_consumers_x86,
    )
    detail_reference_counts = quest_detail_reference_counts(decoded)

    call_sequence = json.loads(
        config.source_ghidra_sql_call_sequence.read_text(encoding="utf-8")
    )
    call_by_sql = {
        str(task["sql"]): int(call["mapped_call_index"])
        for call in call_sequence
        for task in call["tasks"]
    }
    decoded_sql = {result.spec.sql for result in decoded.values()}
    peripheral = [value for value in x64_inventory if value["sql"] not in decoded_sql]
    for ordinal, value in enumerate(peripheral):
        query_key = stable_key("stage40", "surface-query", value["sql"])
        call_index = call_by_sql.get(value["sql"])
        connection.execute(
            """
            INSERT INTO query_specs(
                query_key,source_query_spec_id,table_name,source_module,sql_text,
                columns_json,layout_json,stream_name,start_offset,expected_rows,
                anchor_json,loader_consumer,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                query_key,
                500_000 + ordinal,
                value["table"],
                X64_ARTIFACT,
                value["sql"],
                canonical_json(value["columns"]),
                canonical_json(value["layout"]),
                None,
                None,
                None,
                canonical_json({}),
                (
                    f"x2game.dll {value['loader']}"
                    if value["loader"]
                    else None
                ),
                (
                    "confirmed"
                    if value["state"] == "confirmed_static"
                    else "blocked"
                ),
                canonical_json(
                    {
                        "call_index": call_index,
                        "layout_state": value["state"],
                        "result_boundary": "not_yet_mapped",
                    }
                ),
            ),
        )

    prior = _prior_entities(config)
    quest_ids = {
        int(row["id"]) for row in decoded["quest_contexts"].rows
    }
    row_counts: dict[str, int] = {}
    property_count = _materialize_native_domains(
        connection,
        scalar_audits=scalar_audits,
        quest_detail_audit=quest_detail_audit,
        quest_detail_counts=detail_reference_counts,
    )
    property_count += _materialize_quest_text_kind_domains(
        connection,
        audits=quest_text_kind_audits,
    )
    relation_count = 0
    unknown_endpoints: set[str] = set()

    for table, result in sorted(decoded.items()):
        for row_index, row in enumerate(result.rows):
            if "id" not in row:
                raise RuntimeError(f"{table} has no native id column")
            native_id = int(row["id"])
            kind, identity = table_entity_identity(table, native_id)
            _entity(
                connection,
                kind=kind,
                native_id=identity,
                subtype=(table if kind == "quest_act_detail" else None),
                lifecycle="present",
                state="confirmed",
                evidence={
                    "source_table": table,
                    "row_index": row_index,
                    "identity_prepass": True,
                },
            )

    for source_id, (table, result) in enumerate(
        sorted(decoded.items()), start=400_000
    ):
        query_key = _insert_query(
            connection,
            result=result,
            source_id=source_id,
        )
        ids = []
        for row_index, row in enumerate(result.rows):
            if "id" not in row:
                raise RuntimeError(f"{table} has no native id column")
            native_id = int(row["id"])
            ids.append(native_id)
            kind, identity = table_entity_identity(table, native_id)
            owner = entity_key(kind, identity)
            connection.execute(
                """
                INSERT INTO native_rows(
                    native_row_key,entity_key,entity_kind,native_id,source_table,
                    state,row_json,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("stage40", "native-row", table, native_id),
                    owner,
                    kind,
                    str(identity),
                    table,
                    "confirmed",
                    canonical_json(row),
                    TOOL_NAME,
                    canonical_json(
                        {
                            "query_key": query_key,
                            "row_index": row_index,
                        }
                    ),
                ),
            )
            for column_index, (column, value) in enumerate(row.items()):
                locator = f"{table}[{native_id}].{column}"
                _property(
                    connection,
                    owner=owner,
                    namespace=table,
                    name=column,
                    value=value,
                    ordinal=0,
                    locator=locator,
                    consumer=result.spec.loader,
                    state=(
                        "blocked"
                        if unresolved_reference(value)
                        else "confirmed"
                    ),
                    evidence={
                        "column_index": column_index,
                        "layout": result.spec.layout[column_index],
                    },
                )
                property_count += 1

                target = relation_target(table, column)
                if (
                    target is None
                    or isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0
                ):
                    continue
                relation, destination_kind = target
                destination, destination_state = _endpoint(
                    connection,
                    kind=destination_kind,
                    native_id=value,
                    prior=prior,
                    quest_ids=quest_ids,
                )
                _relation(
                    connection,
                    src=owner,
                    relation=relation,
                    dst=destination,
                    ordinal=column_index,
                    locator=locator,
                    consumer=result.spec.loader,
                    state=(
                        "confirmed"
                        if destination_state == "confirmed"
                        else "unknown"
                    ),
                    required=1,
                )
                relation_count += 1
                if destination_state != "confirmed":
                    unknown_endpoints.add(destination)

            if table == "quest_acts":
                detail_table = act_detail_table(str(row["act_detail_type"]))
                detail_kind, detail_id = table_entity_identity(
                    detail_table, int(row["act_detail_id"])
                )
                detail_key = entity_key(detail_kind, detail_id)
                _relation(
                    connection,
                    src=owner,
                    relation="uses_act_detail",
                    dst=detail_key,
                    ordinal=0,
                    locator=f"quest_acts[{native_id}].act_detail",
                    consumer=result.spec.loader,
                    state="confirmed",
                    required=1,
                    evidence={
                        "actual_type": row["act_detail_type"],
                        "detail_table": detail_table,
                    },
                )
                relation_count += 1
            elif table == "quest_contexts":
                detail_id = int(row.get("detail_id") or 0)
                if detail_id > 0:
                    destination, destination_state = _endpoint(
                        connection,
                        kind="quest_detail",
                        native_id=detail_id,
                        prior=prior,
                        quest_ids=quest_ids,
                    )
                    _relation(
                        connection,
                        src=owner,
                        relation="uses_quest_detail",
                        dst=destination,
                        ordinal=0,
                        locator=f"quest_contexts[{native_id}].detail_id",
                        consumer=str(quest_detail_audit["x64_consumer"]),
                        state=destination_state,
                        required=0,
                        evidence={
                            "inline_scalar_enum": True,
                            "semantic_label": QUEST_DETAIL_LABELS[detail_id],
                            "x86_x64_switch_parity": True,
                        },
                    )
                    relation_count += 1

        connection.execute(
            """
            INSERT INTO native_catalogs(
                table_name,entity_kind,id_column,state,row_count,distinct_ids,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                table,
                (
                    table_entity_identity(table, 0)[0]
                    if table != "quest_contexts"
                    else "quest"
                ),
                "id",
                "confirmed",
                len(result.rows),
                len(set(ids)),
                TOOL_NAME,
                canonical_json(
                    {
                        "query_key": query_key,
                        "native_empty": len(result.rows) == 0,
                        "advertised_rows": result.advertised_rows,
                    }
                ),
            ),
        )
        row_counts[table] = len(result.rows)

    localization_count = 0
    localization_only_quests = 0
    compact = sqlite3.connect(
        f"file:{config.source_client_compact.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    compact.row_factory = sqlite3.Row
    try:
        localized_rows = compact.execute(
            """
            SELECT tbl_name,tbl_column_name,idx,text,locale
            FROM localized_texts
            WHERE lower(tbl_name) LIKE '%quest%'
               OR lower(tbl_column_name) LIKE '%quest%'
            ORDER BY tbl_name,tbl_column_name,idx,locale,text
            """
        ).fetchall()
    finally:
        compact.close()
    if len(localized_rows) != 74_980:
        raise RuntimeError(
            f"Expected 74,980 quest localization rows, got {len(localized_rows)}"
        )
    localized_quest_ids = {
        int(row["idx"])
        for row in localized_rows
        if str(row["tbl_name"]) == "quest_contexts"
        and str(row["tbl_column_name"]) == "name"
    }
    localization_only_quest_ids = localized_quest_ids - quest_ids
    if len(localization_only_quest_ids) != 969:
        raise RuntimeError(
            "Quest localization-only ID set changed: "
            f"{len(localization_only_quest_ids)}"
        )
    for row in localized_rows:
        table = str(row["tbl_name"])
        column = str(row["tbl_column_name"])
        native_id = int(row["idx"])
        kind, identity = _localized_identity(table, native_id)
        owner = entity_key(kind, identity)
        exists = connection.execute(
            "SELECT 1 FROM entities WHERE entity_key=?",
            (owner,),
        ).fetchone()
        if table == "quest_contexts" and native_id in localization_only_quest_ids:
            if exists is None:
                owner = _entity(
                    connection,
                    kind=kind,
                    native_id=identity,
                    subtype=None,
                    lifecycle="tombstone",
                    state="tombstone",
                    evidence={
                        "localized_text_without_decoded_native_row": True,
                        "source_table": table,
                    },
                )
            else:
                connection.execute(
                    """
                    UPDATE entities
                    SET lifecycle='tombstone',state='tombstone',
                        authority='client_native',source_stage=?,
                        provenance=?,evidence_json=?
                    WHERE entity_key=?
                    """,
                    (
                        STAGE,
                        TOOL_NAME,
                        canonical_json(
                            {
                                "localized_text_without_decoded_native_row": True,
                                "may_have_incoming_native_references": True,
                                "source_table": table,
                            }
                        ),
                        owner,
                    ),
                )
            localization_only_quests += 1
            exists = (1,)
        if exists is None:
            lifecycle = (
                "tombstone"
                if table == "quest_contexts"
                else "localization_only"
            )
            state = "tombstone" if lifecycle == "tombstone" else "unknown"
            owner = _entity(
                connection,
                kind=kind,
                native_id=identity,
                subtype=None,
                lifecycle=lifecycle,
                state=state,
                evidence={
                    "localized_text_without_decoded_native_row": True,
                    "source_table": table,
                },
            )
        localization_key = stable_key(
            "localization",
            table,
            column,
            native_id,
            row["locale"],
        )
        connection.execute(
            """
            INSERT INTO localizations(
                localization_key,locale,text_value,entity_key,state,
                source_artifact_key,evidence_json
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (
                localization_key,
                str(row["locale"]),
                str(row["text"]),
                owner,
                "confirmed",
                COMPACT_ARTIFACT,
                canonical_json(
                    {
                        "table": table,
                        "column": column,
                        "idx": native_id,
                    }
                ),
            ),
        )
        localization_count += 1

    for quest_id in sorted(
        int(row[0])
        for row in connection.execute(
            "SELECT native_id FROM entities WHERE kind='quest'"
        )
        if str(row[0]).isdigit()
    ):
        owner = entity_key("quest", quest_id)
        entity_row = connection.execute(
            "SELECT state,lifecycle FROM entities WHERE entity_key=?",
            (owner,),
        ).fetchone()
        localization_rows = int(
            connection.execute(
                "SELECT COUNT(*) FROM localizations WHERE entity_key=?",
                (owner,),
            ).fetchone()[0]
        )
        dimensions = {
            "identity": "confirmed",
            "schema_layout": (
                "confirmed"
                if entity_row["lifecycle"] == "present"
                else "not_applicable"
            ),
            "properties": (
                "confirmed"
                if entity_row["lifecycle"] == "present"
                else "not_applicable"
            ),
            "relations": (
                "confirmed"
                if entity_row["lifecycle"] == "present"
                else "not_applicable"
            ),
            "localization": (
                "confirmed" if localization_rows else "missing"
            ),
            "lifecycle": (
                "confirmed"
                if entity_row["lifecycle"] == "present"
                else "tombstone"
            ),
            "wiki": "unknown",
        }
        for dimension, state in dimensions.items():
            connection.execute(
                """
                INSERT INTO coverage(
                    coverage_key,scope_key,dimension,state,capability,
                    authority,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("coverage", owner, dimension),
                    owner,
                    dimension,
                    state,
                    None,
                    "client_native",
                    TOOL_NAME,
                    canonical_json(
                        {"localization_rows": localization_rows}
                    ),
                ),
            )

    for ordinal, value in enumerate(x64_inventory):
        scope = f"quest-query:{stable_key(value['sql'])}"
        connection.execute(
            """
            INSERT INTO coverage(
                coverage_key,scope_key,dimension,state,capability,authority,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("coverage", scope, "layout"),
                scope,
                "schema_layout",
                (
                    "confirmed"
                    if value["state"] == "confirmed_static"
                    else "blocked"
                ),
                value["table"],
                "client_native",
                TOOL_NAME,
                canonical_json({"inventory_ordinal": ordinal}),
            ),
        )

    wiki_counts = _import_wiki_evidence(
        connection,
        config=config,
        input_hashes=input_hashes,
        prior=prior,
    )

    blocked_layouts = [
        value for value in x64_inventory if value["state"] == "blocked"
    ]
    for value in blocked_layouts:
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("stage40", "opaque-layout", value["sql"]),
                value["table"],
                value["task"],
                "quest_loader_layout_blocked",
                "The SQL is present but the static accessor layout is incomplete.",
                canonical_json(
                    {
                        "x64_loader_dump": input_hashes[X64_ARTIFACT],
                        "sql": value["sql"],
                    }
                ),
                STAGE,
                "opaque",
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
            "stage40:opaque:peripheral-quest-results",
            "quest_related_sql_surfaces",
            "outside_calls_480_604",
            "cached_result_boundary_not_yet_mapped",
            (
                "Quest-bearing queries outside the contiguous quest core retain "
                "confirmed SQL/layout evidence but are not yet assigned to exact "
                "cached-result boundaries."
            ),
            canonical_json(
                {
                    "surface_count": len(peripheral),
                    "confirmed_layouts": sum(
                        value["state"] == "confirmed_static"
                        for value in peripheral
                    ),
                    "blocked_layouts": sum(
                        value["state"] == "blocked" for value in peripheral
                    ),
                    "queries": [
                        {
                            "table": value["table"],
                            "call_index": call_by_sql.get(value["sql"]),
                            "state": value["state"],
                        }
                        for value in peripheral
                    ],
                }
            ),
            STAGE,
            "opaque",
        ),
    )

    for kind, audit in sorted(scalar_audits.items()):
        unresolved_ids = audit.get("unresolved_semantic_ids", audit["ids"])
        if not unresolved_ids:
            continue
        searched_artifacts = [
            X64_ARTIFACT,
            X86_ARTIFACT,
            ENUM_X64_ARTIFACT,
            ENUM_X86_ARTIFACT,
            BUBBLE_CALLBACK_ARTIFACT,
            COMPONENT_STRUCT_ARTIFACT,
            COMPONENT_CONTEXT_X64_ARTIFACT,
            COMPONENT_CONTEXT_X86_ARTIFACT,
            CHAT_BUBBLE_LUA_ARTIFACT,
            QUEST_DIRECTING_LUA_ARTIFACT,
        ]
        blocker_code = "native_enum_semantic_labels_not_yet_recovered"
        reason = (
            "The native IDs, field layout, membership and graph edges "
            "are confirmed. Human-readable meanings remain unassigned "
            "until a native switch, accessor or UI consumer proves them."
        )
        if kind == "npc_ai":
            searched_artifacts.extend(
                [
                    NPC_AI_FIELD_TRACE_X64_ARTIFACT,
                    NPC_AI_FIELD_TRACE_X86_ARTIFACT,
                    NPC_AI_HELPERS_X64_ARTIFACT,
                    NPC_AI_HELPERS_X86_ARTIFACT,
                    NPC_AI_RAW_VECTOR_X64_ARTIFACT,
                    NPC_AI_RAW_VECTOR_X86_ARTIFACT,
                    COMPONENT_COPY_X86_ARTIFACT,
                    NPC_AI_BINDINGS_X64_ARTIFACT,
                    NPC_AI_BINDINGS_X86_ARTIFACT,
                    NPC_AI_STUBS_X64_ARTIFACT,
                    NPC_AI_STUBS_X86_ARTIFACT,
                    NPC_AI_SURFACE_ARTIFACT,
                ]
            )
            blocker_code = "client_explicitly_unsupported_behavior"
            reason = (
                "The client loads and preserves npc_ai_id, but no direct, "
                "forwarded-helper or raw-vector behavior read exists in "
                "either architecture. Its related ScriptBindUnit entry "
                "points are explicit client stubs, so semantic labels need "
                "server/protocol authority and cannot be invented here."
            )
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                f"stage40:opaque:{kind}:semantic-labels",
                f"{kind}.semantic_labels",
                f"{audit['source_table']}.{audit['source_column']}",
                blocker_code,
                reason,
                canonical_json(
                    {
                        "ids": unresolved_ids,
                        "counts": audit["counts"],
                        "loader_x64": audit["loader_x64"],
                        "owner_query_absent": audit["owner_query_absent"],
                        "searched_artifacts": searched_artifacts,
                        "semantic_candidates": audit.get(
                            "semantic_candidates", {}
                        ),
                        "negative_consumer_evidence": audit.get(
                            "negative_consumer_evidence", {}
                        ),
                    }
                ),
                STAGE,
                "opaque",
            ),
        )
    unresolved_by_table = {
        table: sum(result.unresolved_references.values())
        for table, result in decoded.items()
        if result.unresolved_references
    }
    if unresolved_by_table:
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "stage40:opaque:quest-string-cache",
                "quest_cached_strings",
                "calls_480_604_except_quest_acts",
                "unresolved_string_cache_references",
                (
                    "Numeric graph closure and localized text are independently "
                    "confirmed; remaining non-localized cached strings retain raw "
                    "refs."
                ),
                canonical_json(
                    {
                        "tables": unresolved_by_table,
                        "occurrences": sum(unresolved_by_table.values()),
                        "quest_acts_resolved": True,
                    }
                ),
                STAGE,
                "opaque",
            ),
        )

    for endpoint in sorted(unknown_endpoints):
        current_state = connection.execute(
            "SELECT state FROM entities WHERE entity_key=?",
            (endpoint,),
        ).fetchone()
        if (
            current_state is not None
            and str(current_state["state"]) in {"confirmed", "tombstone"}
        ):
            continue
        connection.execute(
            """
            INSERT OR IGNORE INTO gaps(
                gap_key,entity_key,dimension,state,severity,blocker_code,reason,
                required_evidence,provenance
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("stage40", "gap", endpoint),
                endpoint,
                "dependency_closure",
                "unknown",
                2,
                "referenced_endpoint_not_in_prior_stages",
                "A native quest row references an endpoint not yet decoded.",
                "Decode the authoritative table in its owning forensic stage.",
                TOOL_NAME,
            ),
        )

    wi_reference_rows = connection.execute(
        """
        SELECT COUNT(*) AS row_count,
               COUNT(DISTINCT dst_entity_key) AS distinct_ids
        FROM relations
        WHERE relation='references_world_interaction'
        """
    ).fetchone()
    wi_reference_count = int(wi_reference_rows["row_count"])
    wi_reference_ids = int(wi_reference_rows["distinct_ids"])
    wi_invalid_references = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM relations
            WHERE relation='references_world_interaction'
              AND dst_entity_key='world_interaction:95'
            """
        ).fetchone()[0]
    )
    checks = {
        "quest_core_queries": len(decoded) - 1,
        "quest_core_rows": sum(
            len(result.rows)
            for table, result in decoded.items()
            if table != "quest_act_obj_effect_fires"
        ),
        "quest_act_detail_rows": closure["act_rows"],
        "quest_act_detail_types": closure["detail_types"],
        "quest_act_detail_missing": len(closure["missing"]),
        "quest_localizations": localization_count,
        "localization_only_quests": localization_only_quests,
        "unknown_endpoints": len(unknown_endpoints),
        "native_scalar_domain_members": (
            len(QUEST_DETAIL_LABELS)
            + sum(len(audit["ids"]) for audit in scalar_audits.values())
        ),
        "native_scalar_domain_references": (
            sum(detail_reference_counts.values())
            + sum(audit["references"] for audit in scalar_audits.values())
        ),
        "semantic_enum_domains_opaque": sum(
            1
            for spec in SCALAR_DOMAIN_SPECS.values()
            if spec["semantic_state"] == "unknown"
        ),
        "wiki_quest_entities": wiki_counts.get("entities", 0),
        "wiki_quest_properties": wiki_counts.get("properties", 0),
        "wiki_quest_relations": wiki_counts.get("relations", 0),
        "world_interaction_references": wi_reference_count,
        "world_interaction_ids": wi_reference_ids,
        "world_interaction_invalid_references": wi_invalid_references,
    }
    if checks["quest_core_queries"] != 125:
        raise RuntimeError(f"Quest core query count changed: {checks}")
    if checks["quest_core_rows"] != 180_730:
        raise RuntimeError(f"Quest core row count changed: {checks}")
    if checks["quest_act_detail_missing"] != 0:
        raise RuntimeError(f"Quest detail closure changed: {checks}")
    if localization_only_quests != 969:
        raise RuntimeError(
            f"Expected 969 localization-only quests, got {localization_only_quests}"
        )
    if (
        wi_reference_count != 668
        or wi_reference_ids != 6
        or wi_invalid_references != 0
    ):
        raise RuntimeError(
            "Quest world_interaction reference inventory changed: "
            f"{wi_reference_count}/{wi_reference_ids}/"
            f"{wi_invalid_references}"
        )
    orphan_relations = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM relations r
            LEFT JOIN entities s ON s.entity_key=r.src_entity_key
            LEFT JOIN entities d ON d.entity_key=r.dst_entity_key
            WHERE s.entity_key IS NULL OR d.entity_key IS NULL
            """
        ).fetchone()[0]
    )
    if orphan_relations:
        raise RuntimeError(f"Stage 40 has {orphan_relations} orphan relations")
    validation_rows = {
        "x86_x64_layout_parity": architecture_evidence,
        "quest_act_detail_closure": closure,
        "quest_localization_inventory": {
            "rows": localization_count,
            "localization_only_quests": localization_only_quests,
        },
        "quest_wiki_corroboration": wiki_counts,
        "native_scalar_domains": {
            "quest_detail": {
                **quest_detail_audit,
                "counts": {
                    str(key): value
                    for key, value in sorted(detail_reference_counts.items())
                },
            },
            **scalar_audits,
            **quest_text_kind_audits,
        },
        "quest_world_interaction_references": {
            "rows": wi_reference_count,
            "distinct_ids": wi_reference_ids,
            "invalid_id_95_references": wi_invalid_references,
            "source_table": "quest_act_obj_interactions",
            "column": "wi_id",
            "owning_stage": 50,
        },
        "zero_orphan_relations": {"count": orphan_relations},
    }
    for name, evidence in validation_rows.items():
        connection.execute(
            """
            INSERT INTO validation_events(
                validation_key,scope_kind,scope_id,check_name,status,evidence_json
            ) VALUES(?,?,?,?,?,?)
            """,
            (
                stable_key("validation", "stage", "40", name),
                "stage",
                "40",
                name,
                "confirmed",
                canonical_json(evidence),
            ),
        )

    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        ("stage40.input_hashes", canonical_json(input_hashes)),
    )
    for key, value in sorted(checks.items()):
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
            (f"stage40.{key}", str(value)),
        )
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        ("stage40.native_row_counts", canonical_json(row_counts)),
    )
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        ("stage40.properties", str(property_count)),
    )
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        ("stage40.relations", str(relation_count)),
    )
