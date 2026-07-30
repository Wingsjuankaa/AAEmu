from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from . import TOOL_NAME, TOOL_VERSION
from .schema import open_read_only
from .skills import (
    EFFECT_ABSENT_CALLS,
    FX_ABSENT_CALLS,
    SkillQuery,
    SkillResult,
    compare_skill_layouts,
    load_stage50_results,
    skill_query_inventory,
)
from .util import canonical_json, entity_key, sha256_file, stable_key, typed_value
from .world_actors import unresolved_reference
from .world_interactions import (
    WORLD_INTERACTION_INVALID_ID,
    audit_world_interactions,
)


STAGE = 50
STREAM_ARTIFACT = "stage50:stream-game11"
COMPACT_ARTIFACT = "stage50:client-compact"
X64_ARTIFACT = "stage50:ghidra-skill-loaders-x64"
X86_ARTIFACT = "stage50:ghidra-skill-loaders-x86"
CALL_SEQUENCE_ARTIFACT = "stage50:sql-call-sequence"
TASK_ARTIFACT = "stage50:skill-loader-tasks"
WI_X86_LOADER_ARTIFACT = "stage50:ghidra-world-interaction-loader-x86"
WI_ENUM_X64_ARTIFACT = "stage50:ghidra-world-interaction-enum-x64"
WI_ENUM_X86_ARTIFACT = "stage50:ghidra-world-interaction-enum-x86"
WI_TASK_ARTIFACT = "stage50:world-interaction-loader-tasks"

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

TABLE_KIND = {
    "skills": "skill",
    "levels": "skill_level",
    "passive_buffs": "passive_buff",
    "buffs": "buff",
    "effects": "effect",
    "skill_effects": "skill_effect_application",
    "skill_modifiers": "skill_modifier",
    "skill_controllers": "skill_controller",
    "skill_synergy_icons": "skill_synergy_icon",
    "skill_synergy_buff_tags": "skill_synergy_buff_tag",
    "skill_alert_conditions": "skill_alert_condition",
    "tooltip_skill_effects": "tooltip_skill_effect",
    "tagged_skills": "tagged_skill",
    "buff_tick_effects": "buff_tick_effect",
    "buff_triggers": "buff_trigger",
    "buff_unit_modifiers": "buff_unit_modifier",
    "buff_passive_buffs": "buff_passive_buff",
    "buff_visual_changes": "buff_visual_change",
    "buff_swap_skills": "buff_swap_skill",
    "tagged_buffs": "tagged_buff",
    "plots": "plot",
    "plot_events": "plot_event",
    "plot_conditions": "plot_condition",
    "plot_aoe_conditions": "plot_aoe_condition",
    "plot_event_conditions": "plot_event_condition",
    "plot_effects": "plot_effect",
    "plot_next_events": "plot_next_event",
    "anims": "anim",
    "anim_actions": "anim_action",
    "anim_rules": "anim_rule",
    "aoe_shapes": "aoe_shape",
    "skill_controllers": "skill_controller",
    "projectiles": "projectile",
    "fx_groups": "fx_group",
    "fx_items": "fx_item",
    "fx_particles": "fx_particle",
    "fx_sounds": "fx_sound",
    "sounds": "sound",
    "sound_packs": "sound_pack",
    "sound_pack_items": "sound_pack_item",
    "tags": "tag",
}

EXACT_TARGETS = {
    "skill_id": "skill",
    "new_skill_id": "skill",
    "origin_skill_id": "skill",
    "end_skill_id": "skill",
    "precedence_skill_id": "skill",
    "deactive_skill_id": "skill",
    "buff_id": "buff",
    "passive_buff_id": "buff",
    "charged_buff_id": "buff",
    "target_charged_buff_id": "buff",
    "channeling_buff_id": "buff",
    "channeling_target_buff_id": "buff",
    "toggle_buff_id": "buff",
    "transform_buff_id": "buff",
    "link_buff_id": "buff",
    "require_buff_id": "buff",
    "aura_slave_buff_id": "buff",
    "crowd_buff_id": "buff",
    "effect_id": "effect",
    "quest_id": "quest",
    "item_id": "item",
    "consume_item_id": "item",
    "npc_id": "npc",
    "enter_portal_npc_id": "npc",
    "exit_portal_npc_id": "npc",
    "doodad_id": "doodad",
    "channeling_doodad_id": "doodad",
    "backpack_doodad_id": "doodad",
    "plot_id": "plot",
    "event_id": "plot_event",
    "next_event_id": "plot_event",
    "condition_id": "plot_condition",
    "anim_id": "anim",
    "start_anim_id": "anim",
    "end_anim_id": "anim",
    "fire_anim_id": "anim",
    "tick_anim_id": "anim",
    "fx_group_id": "fx_group",
    "sound_id": "sound",
    "sound_pack_id": "sound_pack",
    "projectile_id": "projectile",
    "skill_controller_id": "skill_controller",
    "model_id": "model",
    "base_model_id": "model",
    "mutated_model_id": "model",
    "faction_id": "faction",
    "ability_id": "ability",
    "combat_resource_id": "combat_resource",
    "icon_id": "icon",
    "spawner_id": "npc_spawner",
    "loot_pack_id": "loot_pack",
    "gimmick_id": "gimmick",
    "wi_id": "world_interaction",
    "tag_id": "tag",
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


def _identity(
    table: str, row: dict[str, Any], row_index: int
) -> tuple[str, str]:
    if table == "skill_modifiers":
        identity = ":".join(
            str(row.get(name, 0))
            for name in (
                "owner_type",
                "owner_id",
                "skill_id",
                "skill_attribute_id",
                "tag_id",
                "target_buff_id",
            )
        )
        return "skill_modifier", f"{identity}:{row_index}"
    native_id = row.get("id")
    if native_id is None:
        return f"{table.rstrip('s')}_row", str(row_index)
    if table.endswith("_effects") and table not in {
        "effects",
        "skill_effects",
        "buff_tick_effects",
        "plot_effects",
        "tooltip_skill_effects",
    }:
        return "effect_detail", f"{table}:{native_id}"
    return TABLE_KIND.get(table, table.rstrip("s")), str(native_id)


def _entity_tuple(
    *,
    kind: str,
    native_id: str,
    subtype: str | None,
    lifecycle: str,
    state: str,
    authority: str = "client_native",
    provenance: str = TOOL_NAME,
    evidence: dict[str, Any] | None = None,
) -> tuple[Any, ...]:
    return (
        entity_key(kind, native_id),
        kind,
        native_id,
        subtype,
        lifecycle,
        state,
        authority,
        STAGE,
        provenance,
        canonical_json(evidence or {}),
    )


def _insert_entities(
    connection: sqlite3.Connection, rows: list[tuple[Any, ...]]
) -> None:
    connection.executemany(
        """
        INSERT OR IGNORE INTO entities(
            entity_key,kind,native_id,subtype,lifecycle,state,authority,
            source_stage,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )


def _prior_entities(config: Any) -> dict[tuple[str, str], dict[str, str]]:
    result: dict[tuple[str, str], dict[str, str]] = {}
    for path in (
        config.stage_20,
        config.stage_30,
        config.stage_40,
    ):
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


def _target_kind(column: str) -> str | None:
    if column in EXACT_TARGETS:
        return EXACT_TARGETS[column]
    if column.endswith("_buff_tag_id") or column.endswith("_skill_tag_id"):
        return "tag"
    if column.endswith("_tag_id"):
        return "tag"
    if column.endswith("_skill_id"):
        return "skill"
    if column.endswith("_buff_id"):
        return "buff"
    if column.endswith("_effect_id"):
        return "effect"
    if column.endswith("_item_id"):
        return "item"
    if column.endswith("_npc_id"):
        return "npc"
    if column.endswith("_doodad_id"):
        return "doodad"
    if column.endswith("_anim_id"):
        return "anim"
    if column.endswith("_model_id"):
        return "model"
    if column.endswith("_sound_id"):
        return "sound"
    return None


def _snake_effect_table(actual_type: str) -> str:
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", actual_type).lower()
    if snake == "skill_controller":
        return "skill_controllers"
    return snake + "s"


def _property_tuple(
    *,
    owner: str,
    namespace: str,
    name: str,
    value: Any,
    locator: str,
    consumer: str | None,
    state: str,
    artifact: str = STREAM_ARTIFACT,
    authority: str = "client_native",
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
        artifact,
        locator,
        consumer,
        canonical_json(evidence or {}),
    )


def _relation_tuple(
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
) -> tuple[Any, ...]:
    return (
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
    )


def _endpoint(
    connection: sqlite3.Connection,
    *,
    kind: str,
    native_id: Any,
    prior: dict[tuple[str, str], dict[str, str]],
    pending: dict[str, tuple[Any, ...]],
    cache: dict[str, str],
) -> tuple[str, str]:
    value = str(native_id)
    key = entity_key(kind, value)
    if key in cache:
        return key, cache[key]
    row = connection.execute(
        "SELECT state FROM entities WHERE entity_key=?", (key,)
    ).fetchone()
    if row is not None:
        cache[key] = str(row["state"])
        return key, cache[key]
    if key in pending:
        cache[key] = str(pending[key][5])
        return key, cache[key]
    known = prior.get((kind, value))
    if known is not None:
        pending[key] = _entity_tuple(
            kind=kind,
            native_id=value,
            subtype=None,
            lifecycle=known["lifecycle"],
            state=known["state"],
            authority=known["authority"],
            provenance="prior_forensic_stage",
            evidence={"confirmed_by": known["source"]},
        )
        cache[key] = known["state"]
        return key, known["state"]
    pending[key] = _entity_tuple(
        kind=kind,
        native_id=value,
        subtype=None,
        lifecycle="referenced",
        state="unknown",
        evidence={"endpoint_materialized_for_graph_closure": True},
    )
    cache[key] = "unknown"
    return key, "unknown"


def _insert_query_spec(
    connection: sqlite3.Connection,
    *,
    query: SkillQuery,
    result: SkillResult | None,
    source_id: int,
) -> str:
    query_key = f"stage50:query:{query.call_index}:{query.table}"
    state = (
        "confirmed"
        if result is not None and not result.unresolved_references
        else "blocked"
        if query.architecture_state == "blocked"
        else "confirmed"
    )
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
            query.table,
            X64_ARTIFACT,
            query.sql,
            canonical_json(query.columns),
            canonical_json(query.layout),
            "game11" if result is not None else None,
            result.start if result is not None else None,
            len(result.rows) if result is not None else None,
            canonical_json(
                {
                    "end": result.end if result is not None else None,
                    "advertised_rows": (
                        result.advertised_rows if result is not None else None
                    ),
                    "boundary_source": (
                        result.boundary_source if result is not None else None
                    ),
                }
            ),
            (
                f"x2game.dll {query.loader}"
                if query.loader is not None
                else None
            ),
            state,
            canonical_json(
                {
                    "call_index": query.call_index,
                    "architecture_state": query.architecture_state,
                    "loader_address": query.loader_address,
                    "cached_result_state": (
                        "decoded" if result is not None else "not_decoded"
                    ),
                }
            ),
        ),
    )
    if result is None:
        return query_key
    connection.execute(
        """
        INSERT INTO cached_results(
            cached_result_key,source_cached_result_id,query_key,artifact_key,
            start_offset,end_offset,row_count,row_digest,raw_references_json,
            unresolved_references_json,resolution_evidence_json,state,error
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            f"stage50:cached:{query.call_index}:{query.table}",
            source_id,
            query_key,
            STREAM_ARTIFACT,
            result.start,
            result.end,
            len(result.rows),
            result.digest,
            canonical_json({}),
            canonical_json(result.unresolved_references),
            canonical_json(
                {
                    "boundary_source": result.boundary_source,
                    "string_cache_resolution": (
                        "complete"
                        if not result.unresolved_references
                        else "partial"
                    ),
                }
            ),
            "confirmed" if not result.unresolved_references else "blocked",
            (
                None
                if not result.unresolved_references
                else "cached string references remain unresolved"
            ),
        ),
    )
    connection.executemany(
        """
        INSERT INTO cached_result_rows(query_key,row_index,row_json)
        VALUES(?,?,?)
        """,
        (
            (query_key, index, canonical_json(row))
            for index, row in enumerate(result.rows)
        ),
    )
    return query_key


def _materialize_world_interactions(
    connection: sqlite3.Connection,
    *,
    audit: dict[str, Any],
    query_key: str,
) -> dict[str, int]:
    labels = dict(audit["labels"])
    detail_ids = set(audit["detail_ids"])
    result = audit["result"]
    if WORLD_INTERACTION_INVALID_ID in labels:
        raise RuntimeError("Invalid world_interaction ID 95 entered the enum")

    entities = [
        _entity_tuple(
            kind="world_interaction",
            native_id=native_id,
            subtype="native_scalar_enum",
            lifecycle="present",
            state="confirmed",
            evidence={
                "semantic_label": label,
                "x64_switch": audit["x64_switch"]["function"],
                "x86_switch": audit["x86_switch"]["function"],
                "x86_x64_switch_parity": True,
                "invalid_default_excludes": WORLD_INTERACTION_INVALID_ID,
            },
        )
        for native_id, label in sorted(labels.items())
    ]
    _insert_entities(connection, entities)

    properties: list[tuple[Any, ...]] = []
    for native_id, label in sorted(labels.items()):
        owner = entity_key("world_interaction", native_id)
        for name, value in (
            ("enum_value", native_id),
            ("semantic_label", label),
            ("has_wi_detail", native_id in detail_ids),
        ):
            properties.append(
                _property_tuple(
                    owner=owner,
                    namespace="world_interaction.enum",
                    name=name,
                    value=value,
                    locator=(
                        f"{audit['x64_switch']['function']}:case:{native_id}"
                    ),
                    consumer=audit["x64_switch"]["function"],
                    state="confirmed",
                    artifact=WI_ENUM_X64_ARTIFACT,
                    evidence={
                        "x86_consumer": audit["x86_switch"]["function"],
                        "x86_x64_switch_parity": True,
                    },
                )
            )

    native_rows: list[tuple[Any, ...]] = []
    for row_index, row in enumerate(result.rows):
        native_id = int(row["wi_id"])
        owner = entity_key("world_interaction", native_id)
        native_rows.append(
            (
                stable_key("stage50", "native-row", "wi_details", native_id),
                owner,
                "world_interaction",
                str(native_id),
                "wi_details",
                "confirmed",
                canonical_json(row),
                TOOL_NAME,
                canonical_json(
                    {"query_key": query_key, "row_index": row_index}
                ),
            )
        )
        for column_index, column in enumerate(
            ("apply_expert", "distance_sqrt", "lp"), start=1
        ):
            properties.append(
                _property_tuple(
                    owner=owner,
                    namespace="wi_details",
                    name=column,
                    value=row[column],
                    locator=f"wi_details[{native_id}].{column}",
                    consumer=result.spec.loader,
                    state="confirmed",
                    evidence={
                        "column_index": column_index,
                        "layout": result.spec.layout[column_index],
                        "optional_enum_metadata": True,
                    },
                )
            )

    connection.executemany(
        """
        INSERT INTO native_rows(
            native_row_key,entity_key,entity_kind,native_id,source_table,
            state,row_json,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?)
        """,
        native_rows,
    )
    connection.executemany(
        """
        INSERT INTO entity_properties(
            property_key,entity_key,namespace,property_name,ordinal,
            value_type,value_text,value_integer,value_real,value_boolean,
            value_json,state,authority,source_artifact_key,locator,
            consumer,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        properties,
    )
    connection.executemany(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        [
            (
                "world_interaction_enum",
                "world_interaction",
                "enum_value",
                "confirmed",
                len(labels),
                len(labels),
                TOOL_NAME,
                canonical_json(
                    {
                        "authority": "x2game.dll native switch",
                        "x64_function": audit["x64_switch"]["function"],
                        "x86_function": audit["x86_switch"]["function"],
                        "invalid_default_excludes": WORLD_INTERACTION_INVALID_ID,
                    }
                ),
            ),
            (
                "wi_details",
                "world_interaction",
                "wi_id",
                "confirmed",
                len(result.rows),
                len(detail_ids),
                TOOL_NAME,
                canonical_json(
                    {
                        "query_key": query_key,
                        "optional_enum_metadata": True,
                        "absence_is_not_tombstone": True,
                    }
                ),
            ),
        ],
    )

    coverage: list[tuple[Any, ...]] = []
    for native_id in sorted(labels):
        owner = entity_key("world_interaction", native_id)
        dimensions = {
            "identity": "confirmed",
            "schema_layout": (
                "confirmed" if native_id in detail_ids else "not_applicable"
            ),
            "properties": "confirmed",
            "relations": "unknown",
            "localization": "not_applicable",
            "lifecycle": "confirmed",
            "wiki": "unknown",
        }
        for dimension, state in dimensions.items():
            coverage.append(
                (
                    stable_key("coverage", owner, dimension),
                    owner,
                    dimension,
                    state,
                    None,
                    "client_native",
                    TOOL_NAME,
                    canonical_json(
                        {
                            "native_scalar_enum": True,
                            "has_wi_detail": native_id in detail_ids,
                        }
                    ),
                )
            )
    connection.executemany(
        """
        INSERT INTO coverage(
            coverage_key,scope_key,dimension,state,capability,authority,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        coverage,
    )
    return {
        "enum_members": len(labels),
        "detail_rows": len(result.rows),
        "properties": len(properties),
        "coverage_rows": len(coverage),
    }


def _localized_identity(table: str, native_id: int) -> tuple[str, str]:
    if table == "skills":
        return "skill", str(native_id)
    if table == "buffs":
        return "buff", str(native_id)
    if table.endswith("_effects"):
        return "effect_detail", f"{table}:{native_id}"
    if table == "skill_synergy_icons":
        return "skill_synergy_icon", str(native_id)
    return "localized_record", f"{table}:{native_id}"


def _import_wiki(
    connection: sqlite3.Connection,
    *,
    config: Any,
    input_hashes: dict[str, str],
    prior_keys: set[str],
) -> dict[str, int]:
    tool_parent = str(config.source_item_tool_root.parent)
    if tool_parent not in sys.path:
        sys.path.insert(0, tool_parent)
    from item_forensics.wiki import parse_wiki_page

    html_files = sorted(
        config.source_skill_wiki_cache.glob("*.html"),
        key=lambda path: int(path.stem),
    )
    if not html_files:
        raise RuntimeError("The frozen Stage 50 skill wiki snapshot is empty")
    counts = Counter()
    for html_path in html_files:
        skill_id = int(html_path.stem)
        meta_path = html_path.with_suffix(".meta.json")
        if not meta_path.is_file():
            raise RuntimeError(f"Missing wiki metadata for skill {skill_id}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for suffix, path in (("html", html_path), ("meta", meta_path)):
            key = f"stage50:wiki:skill:{skill_id}:{suffix}"
            input_hashes[key] = _artifact(
                connection,
                key=key,
                role=f"wiki_visible_skill_{suffix}",
                path=path,
                build=config.client_build,
                authority="wiki_visible",
            )
        if sha256_file(html_path) != str(meta["content_sha256"]):
            raise RuntimeError(f"Wiki payload hash mismatch for skill {skill_id}")
        page = parse_wiki_page(
            html_path.read_bytes(),
            entity_kind="skills",
            entity_id=skill_id,
            locale=str(meta["locale"]),
        )
        owner = entity_key("skill", skill_id)
        native_exists = connection.execute(
            "SELECT 1 FROM entities WHERE entity_key=?", (owner,)
        ).fetchone() is not None
        wiki_key = f"wiki:na-en:skill:{skill_id}"
        comparison = (
            "corroborated_native_identity" if native_exists else "wiki_only"
        )
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
        for ordinal, (name, value) in enumerate(
            {
                "page_type": page.page_type,
                "name": page.name,
                "category": page.category,
                "grade": page.grade,
                "level": page.level,
                "map_links": list(page.map_links),
            }.items()
        ):
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
            destination_kind = WIKI_KIND_MAP.get(
                link.kind, link.kind.rstrip("s")
            )
            destination = entity_key(destination_kind, link.entity_id)
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
                        if destination in prior_keys
                        or connection.execute(
                            "SELECT 1 FROM entities WHERE entity_key=?",
                            (destination,),
                        ).fetchone()
                        is not None
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
                UPDATE coverage SET state='confirmed',authority='wiki_visible',
                    evidence_json=?
                WHERE scope_key=? AND dimension='wiki'
                """,
                (
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


def populate_stage_50(
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
            role="skill_loader_decompilation_x64",
            path=config.source_ghidra_sql_loaders_64,
            build=config.client_build,
            authority="client_native",
        ),
        X86_ARTIFACT: _artifact(
            connection,
            key=X86_ARTIFACT,
            role="skill_loader_decompilation_x86",
            path=config.source_ghidra_skill_loaders_x86,
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
        TASK_ARTIFACT: _artifact(
            connection,
            key=TASK_ARTIFACT,
            role="skill_loader_task_registry",
            path=config.source_skill_loader_tasks,
            build=config.client_build,
            authority="derived_forensic",
        ),
        WI_X86_LOADER_ARTIFACT: _artifact(
            connection,
            key=WI_X86_LOADER_ARTIFACT,
            role="world_interaction_loader_decompilation_x86",
            path=config.source_ghidra_world_interaction_loader_x86,
            build=config.client_build,
            authority="client_native",
        ),
        WI_ENUM_X64_ARTIFACT: _artifact(
            connection,
            key=WI_ENUM_X64_ARTIFACT,
            role="world_interaction_enum_decompilation_x64",
            path=config.source_ghidra_world_interaction_enum_x64,
            build=config.client_build,
            authority="client_native",
        ),
        WI_ENUM_X86_ARTIFACT: _artifact(
            connection,
            key=WI_ENUM_X86_ARTIFACT,
            role="world_interaction_enum_decompilation_x86",
            path=config.source_ghidra_world_interaction_enum_x86,
            build=config.client_build,
            authority="client_native",
        ),
        WI_TASK_ARTIFACT: _artifact(
            connection,
            key=WI_TASK_ARTIFACT,
            role="world_interaction_loader_task_registry",
            path=config.source_world_interaction_loader_tasks,
            build=config.client_build,
            authority="derived_forensic",
        ),
    }
    inventory = skill_query_inventory(
        config.source_ghidra_sql_loaders_64,
        config.source_ghidra_skill_loaders_x86,
        config.source_ghidra_sql_call_sequence,
        config.source_skill_loader_tasks,
    )
    architecture = compare_skill_layouts(inventory)
    results, diagnostics = load_stage50_results(config, inventory)
    world_interactions = audit_world_interactions(config)
    connection.execute(
        """
        INSERT INTO decoders(
            decoder_key,name,version,sha256,status,inputs_json,
            assumptions_json,provenance
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "stage50:decoder:skill-buff-effect-cache",
            "AA8 skills, buffs, effects, plots and FX cached-result decoder",
            TOOL_VERSION,
            None,
            "confirmed",
            canonical_json(input_hashes),
            canonical_json(
                {
                    "primitive_abi": ["38", "40", "60", "68", "70", "78"],
                    "architecture_evidence": architecture,
                    "physical_layout_exception": {
                        "npc_spawner_despawn_effects": ["68", "38"]
                    },
                    "effect_string_map": diagnostics["effect_string_map"],
                    "plot_string_map": diagnostics["plot_string_map"],
                    "projection_policy": (
                        "native_rows preserve every field; entity_properties "
                        "projects text, polymorphic discriminators and IDs"
                    ),
                    "world_interaction": {
                        "enum_members": len(world_interactions["labels"]),
                        "invalid_default_excludes": (
                            WORLD_INTERACTION_INVALID_ID
                        ),
                        "wi_detail_rows": len(
                            world_interactions["result"].rows
                        ),
                        "x86_x64_switch_parity": True,
                        "x86_x64_loader_layout_parity": True,
                    },
                }
            ),
            TOOL_NAME,
        ),
    )

    query_keys: dict[str, str] = {}
    for source_id, query in enumerate(inventory, start=500_000):
        candidate = results.get(query.table)
        result = (
            candidate
            if candidate is not None
            and candidate.spec.call_index == query.call_index
            else None
        )
        query_key = _insert_query_spec(
            connection,
            query=query,
            result=result,
            source_id=source_id,
        )
        if result is not None:
            query_keys[query.table] = query_key
    wi_query_key = _insert_query_spec(
        connection,
        query=world_interactions["spec"],
        result=world_interactions["result"],
        source_id=500_611,
    )
    query_keys["wi_details"] = wi_query_key
    wi_counts = _materialize_world_interactions(
        connection,
        audit=world_interactions,
        query_key=wi_query_key,
    )

    prior = _prior_entities(config)
    decoded_plot_event_ids = {
        int(row["id"])
        for row in results["plot_events"].rows
        if isinstance(row.get("id"), int)
        and not isinstance(row.get("id"), bool)
    }
    plot_event_references: Counter[int] = Counter()
    plot_event_reference_sources: Counter[str] = Counter()
    for source_table, result in sorted(results.items()):
        for row in result.rows:
            for column, value in row.items():
                if (
                    _target_kind(column) == "plot_event"
                    and isinstance(value, int)
                    and not isinstance(value, bool)
                    and value > 0
                    and value not in decoded_plot_event_ids
                ):
                    plot_event_references[value] += 1
                    plot_event_reference_sources[
                        f"{source_table}.{column}"
                    ] += 1
    expected_plot_event_tombstones = Counter(
        {
            4: 431,
            5: 126,
            6: 3_804,
            7: 19,
            8: 20,
            9: 29,
            10: 154,
            11: 168,
            15: 8,
            19: 1,
            20: 15,
            21: 177,
            22: 9,
            31: 2,
        }
    )
    if plot_event_references != expected_plot_event_tombstones:
        raise RuntimeError(
            "Referenced plot_event tombstone set changed: "
            f"{dict(sorted(plot_event_references.items()))}"
        )
    if plot_event_reference_sources != Counter(
        {"buff_triggers.event_id": 4_963}
    ):
        raise RuntimeError(
            "plot_event tombstone reference sources changed: "
            f"{dict(plot_event_reference_sources)}"
        )

    identity_rows: dict[str, tuple[Any, ...]] = {}
    for table, result in sorted(results.items()):
        for row_index, row in enumerate(result.rows):
            kind, native_id = _identity(table, row, row_index)
            key = entity_key(kind, native_id)
            identity_rows[key] = _entity_tuple(
                kind=kind,
                native_id=native_id,
                subtype=(
                    table
                    if kind
                    in {
                        "effect_detail",
                        "skill_modifier",
                        "localized_record",
                    }
                    else None
                ),
                lifecycle="present",
                state="confirmed",
                evidence={
                    "source_table": table,
                    "row_index": row_index,
                    "identity_prepass": True,
                },
            )
        _insert_entities(connection, list(identity_rows.values()))
        identity_rows.clear()
    _insert_entities(
        connection,
        [
            _entity_tuple(
                kind="plot_event",
                native_id=native_id,
                subtype=None,
                lifecycle="tombstone",
                state="tombstone",
                evidence={
                    "authoritative_table": "plot_events",
                    "absence_in_unfiltered_native_result": True,
                    "native_result_rows": len(results["plot_events"].rows),
                    "query_call_index": results[
                        "plot_events"
                    ].spec.call_index,
                    "incoming_reference_count": reference_count,
                    "incoming_reference_sources": dict(
                        sorted(plot_event_reference_sources.items())
                    ),
                },
            )
            for native_id, reference_count in sorted(
                plot_event_references.items()
            )
        ],
    )

    property_count = wi_counts["properties"]
    relation_count = 0
    unknown_endpoints: set[str] = set()
    endpoint_cache: dict[str, str] = {}
    unclassified_id_columns: Counter[str] = Counter()
    effect_tombstones: Counter[str] = Counter()
    decoded_effect_ids = {
        table: {
            int(row["id"])
            for row in result.rows
            if isinstance(row.get("id"), int)
            and not isinstance(row.get("id"), bool)
        }
        for table, result in results.items()
        if table.endswith("_effects")
        and table not in {
            "effects",
            "skill_effects",
            "buff_tick_effects",
            "plot_effects",
            "tooltip_skill_effects",
        }
    }
    native_counts: dict[str, int] = {
        "world_interaction_enum": wi_counts["enum_members"],
        "wi_details": wi_counts["detail_rows"],
    }
    for table, result in sorted(results.items()):
        query_key = query_keys[table]
        native_rows: list[tuple[Any, ...]] = []
        properties: list[tuple[Any, ...]] = []
        relations: list[tuple[Any, ...]] = []
        pending_entities: dict[str, tuple[Any, ...]] = {}
        ids: list[str] = []
        for row_index, row in enumerate(result.rows):
            kind, native_id = _identity(table, row, row_index)
            owner = entity_key(kind, native_id)
            ids.append(native_id)
            native_rows.append(
                (
                    stable_key(
                        "stage50", "native-row", table, native_id, row_index
                    ),
                    owner,
                    kind,
                    native_id,
                    table,
                    (
                        "blocked"
                        if any(unresolved_reference(v) for v in row.values())
                        else "confirmed"
                    ),
                    canonical_json(row),
                    TOOL_NAME,
                    canonical_json(
                        {"query_key": query_key, "row_index": row_index}
                    ),
                )
            )
            for column_index, (column, value) in enumerate(row.items()):
                locator = f"{table}[{native_id}].{column}"
                target_kind = _target_kind(column)
                should_project = (
                    column != "id"
                    and (
                        isinstance(value, str)
                        and value != ""
                        or column in {"actual_type", "owner_type"}
                    )
                )
                if should_project:
                    properties.append(
                        _property_tuple(
                            owner=owner,
                            namespace=table,
                            name=column,
                            value=value,
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
                                "projection_policy": (
                                    "nonempty_text_or_polymorphic_discriminator"
                                ),
                            },
                        )
                    )
                if (
                    target_kind is None
                    or column in {"actual_id", "owner_id"}
                    or isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0
                ):
                    if (
                        target_kind is None
                        and column != "id"
                        and column.endswith("_id")
                        and isinstance(value, int)
                        and not isinstance(value, bool)
                        and value > 0
                    ):
                        unclassified_id_columns[f"{table}.{column}"] += 1
                    continue
                destination, destination_state = _endpoint(
                    connection,
                    kind=target_kind,
                    native_id=value,
                    prior=prior,
                    pending=pending_entities,
                    cache=endpoint_cache,
                )
                relations.append(
                    _relation_tuple(
                        src=owner,
                        relation=f"references_{target_kind}",
                        dst=destination,
                        ordinal=column_index,
                        locator=locator,
                        consumer=result.spec.loader,
                        state=(
                            "confirmed"
                            if destination_state in {"confirmed", "tombstone"}
                            else "unknown"
                        ),
                        required=1,
                    )
                )
                if destination_state not in {"confirmed", "tombstone"}:
                    unknown_endpoints.add(destination)

            if table in {"effects", "plot_effects"}:
                actual_type = str(row["actual_type"])
                actual_id = int(row["actual_id"])
                detail_table = _snake_effect_table(actual_type)
                destination_kind = (
                    "skill_controller"
                    if actual_type == "SkillController"
                    else "effect_detail"
                )
                destination_id = (
                    str(actual_id)
                    if destination_kind == "skill_controller"
                    else f"{detail_table}:{actual_id}"
                )
                destination_key = entity_key(
                    destination_kind,
                    destination_id,
                )
                if (
                    destination_kind == "effect_detail"
                    and detail_table in decoded_effect_ids
                    and actual_id not in decoded_effect_ids[detail_table]
                    and destination_key not in pending_entities
                    and connection.execute(
                        "SELECT 1 FROM entities WHERE entity_key=?",
                        (destination_key,),
                    ).fetchone()
                    is None
                ):
                    pending_entities[destination_key] = _entity_tuple(
                        kind="effect_detail",
                        native_id=destination_id,
                        subtype=detail_table,
                        lifecycle="tombstone",
                        state="tombstone",
                        evidence={
                            "referenced_by": owner,
                            "actual_type": actual_type,
                            "actual_id": actual_id,
                            "authoritative_table": detail_table,
                            "native_result_rows": len(results[detail_table].rows),
                            "absence_in_unfiltered_native_result": True,
                            "query_call_index": (
                                results[detail_table].spec.call_index
                            ),
                        },
                    )
                    endpoint_cache[destination_key] = "tombstone"
                    effect_tombstones[detail_table] += 1
                destination, destination_state = _endpoint(
                    connection,
                    kind=destination_kind,
                    native_id=destination_id,
                    prior=prior,
                    pending=pending_entities,
                    cache=endpoint_cache,
                )
                relations.append(
                    _relation_tuple(
                        src=owner,
                        relation="uses_concrete_effect",
                        dst=destination,
                        ordinal=0,
                        locator=f"{table}[{native_id}].actual",
                        consumer=result.spec.loader,
                        state=(
                            "confirmed"
                            if destination_state == "confirmed"
                            else "tombstone"
                            if destination_state == "tombstone"
                            else "unknown"
                        ),
                        required=1,
                        evidence={
                            "actual_type": actual_type,
                            "actual_id": actual_id,
                            "detail_table": detail_table,
                        },
                    )
                )
                if destination_state not in {"confirmed", "tombstone"}:
                    unknown_endpoints.add(destination)

        _insert_entities(connection, list(pending_entities.values()))
        connection.executemany(
            """
            INSERT INTO native_rows(
                native_row_key,entity_key,entity_kind,native_id,source_table,
                state,row_json,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            native_rows,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO entity_properties(
                property_key,entity_key,namespace,property_name,ordinal,
                value_type,value_text,value_integer,value_real,value_boolean,
                value_json,state,authority,source_artifact_key,locator,
                consumer,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            properties,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO relations(
                relation_key,src_entity_key,relation,dst_entity_key,ordinal,
                cardinality,state,required,authority,source_artifact_key,
                locator,loader_or_consumer,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            relations,
        )
        connection.execute(
            """
            INSERT INTO native_catalogs(
                table_name,entity_kind,id_column,state,row_count,distinct_ids,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                table,
                TABLE_KIND.get(table, _identity(table, {}, 0)[0]),
                "composite" if table == "skill_modifiers" else "id",
                (
                    "blocked"
                    if result.unresolved_references
                    else "confirmed"
                ),
                len(result.rows),
                len(set(ids)),
                TOOL_NAME,
                canonical_json(
                    {
                        "query_key": query_key,
                        "native_empty": len(result.rows) == 0,
                        "advertised_rows": result.advertised_rows,
                        "unresolved_references": result.unresolved_references,
                    }
                ),
            ),
        )
        property_count += len(properties)
        relation_count += len(relations)
        native_counts[table] = len(result.rows)

    localized_query = """
        SELECT tbl_name,tbl_column_name,idx,text,locale
        FROM localized_texts
        WHERE lower(tbl_name) LIKE '%skill%'
           OR lower(tbl_name) LIKE '%buff%'
           OR lower(tbl_name) LIKE '%effect%'
           OR lower(tbl_name) LIKE '%plot%'
           OR lower(tbl_column_name) LIKE '%skill%'
           OR lower(tbl_column_name) LIKE '%buff%'
           OR lower(tbl_column_name) LIKE '%effect%'
           OR lower(tbl_column_name) LIKE '%plot%'
        ORDER BY tbl_name,tbl_column_name,idx,locale,text
    """
    compact = sqlite3.connect(
        f"file:{config.source_client_compact.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    compact.row_factory = sqlite3.Row
    try:
        localized_rows = compact.execute(localized_query).fetchall()
    finally:
        compact.close()
    if len(localized_rows) != 176_235:
        raise RuntimeError(
            f"Expected 176,235 Stage 50 localization rows, got "
            f"{len(localized_rows)}"
        )
    localization_entities: dict[str, tuple[Any, ...]] = {}
    localization_values: list[tuple[Any, ...]] = []
    for row in localized_rows:
        table = str(row["tbl_name"])
        column = str(row["tbl_column_name"])
        native_id = int(row["idx"])
        kind, identity = _localized_identity(table, native_id)
        owner = entity_key(kind, identity)
        if connection.execute(
            "SELECT 1 FROM entities WHERE entity_key=?", (owner,)
        ).fetchone() is None:
            localization_entities[owner] = _entity_tuple(
                kind=kind,
                native_id=identity,
                subtype=table,
                lifecycle="localization_only",
                state="unknown",
                evidence={
                    "localized_text_without_decoded_native_row": True,
                    "source_table": table,
                },
            )
        localization_values.append(
            (
                stable_key(
                    "localization",
                    table,
                    column,
                    native_id,
                    row["locale"],
                    row["text"],
                ),
                str(row["locale"]),
                str(row["text"]),
                owner,
                "confirmed",
                COMPACT_ARTIFACT,
                canonical_json(
                    {"table": table, "column": column, "idx": native_id}
                ),
            )
        )
    _insert_entities(connection, list(localization_entities.values()))
    connection.executemany(
        """
        INSERT INTO localizations(
            localization_key,locale,text_value,entity_key,state,
            source_artifact_key,evidence_json
        ) VALUES(?,?,?,?,?,?,?)
        """,
        localization_values,
    )

    coverage_rows: list[tuple[Any, ...]] = []
    localizations_by_entity = {
        str(row["entity_key"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT entity_key,COUNT(*) AS row_count
            FROM localizations GROUP BY entity_key
            """
        )
    }
    relations_by_entity = {
        str(row["src_entity_key"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT src_entity_key,COUNT(*) AS row_count
            FROM relations GROUP BY src_entity_key
            """
        )
    }
    skill_rows = connection.execute(
        """
        SELECT entity_key,state,lifecycle FROM entities
        WHERE kind='skill' ORDER BY CAST(native_id AS INTEGER),native_id
        """
    ).fetchall()
    for row in skill_rows:
        owner = str(row["entity_key"])
        lifecycle = str(row["lifecycle"])
        localization_count = localizations_by_entity.get(owner, 0)
        relation_rows = relations_by_entity.get(owner, 0)
        dimensions = {
            "identity": "confirmed",
            "schema_layout": (
                "confirmed" if lifecycle == "present" else "not_applicable"
            ),
            "properties": (
                "confirmed" if lifecycle == "present" else "not_applicable"
            ),
            "relations": (
                "confirmed" if lifecycle == "present" else "not_applicable"
            ),
            "localization": (
                "confirmed" if localization_count else "missing"
            ),
            "lifecycle": (
                "confirmed" if lifecycle == "present" else "unknown"
            ),
            "wiki": "unknown",
        }
        for dimension, state in dimensions.items():
            coverage_rows.append(
                (
                    stable_key("coverage", owner, dimension),
                    owner,
                    dimension,
                    state,
                    None,
                    "client_native",
                    TOOL_NAME,
                    canonical_json(
                        {
                            "localization_rows": localization_count,
                            "outgoing_relations": relation_rows,
                        }
                    ),
                )
            )
    connection.executemany(
        """
        INSERT INTO coverage(
            coverage_key,scope_key,dimension,state,capability,authority,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        coverage_rows,
    )

    decoded_calls = {result.spec.call_index for result in results.values()}
    absent_calls = EFFECT_ABSENT_CALLS | FX_ABSENT_CALLS
    for query in inventory:
        if query.call_index in decoded_calls:
            continue
        native_absent = query.call_index in absent_calls
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key(
                    "stage50", "opaque-query", query.call_index, query.sql
                ),
                query.table,
                f"sql_call:{query.call_index}",
                (
                    "native_result_absent"
                    if native_absent
                    else "cached_result_boundary_not_yet_mapped"
                ),
                (
                    "The loader and SQL are confirmed, but this execution has "
                    "no native cached-result payload."
                    if native_absent
                    else "The loader layout is confirmed but its exact cached "
                    "result boundary has not yet been decoded."
                ),
                canonical_json(
                    {
                        "sql": query.sql,
                        "architecture_state": query.architecture_state,
                        "x64_loader_hash": input_hashes[X64_ARTIFACT],
                        "x86_loader_hash": input_hashes[X86_ARTIFACT],
                    }
                ),
                STAGE,
                "opaque",
            ),
        )

    unresolved_tables = {
        table: result.unresolved_references
        for table, result in results.items()
        if result.unresolved_references
    }
    for table, references in sorted(unresolved_tables.items()):
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("stage50", "string-cache", table),
                table,
                query_keys[table],
                "unresolved_string_cache_references",
                (
                    "Numeric rows and graph edges are decoded, but one or more "
                    "cached string references still lack their earlier insertion."
                ),
                canonical_json(
                    {
                        "references": references,
                        "occurrences": sum(references.values()),
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
            "stage50:opaque:unclassified-id-semantics",
            "positive_id_fields",
            "native_rows.row_json",
            "foreign_key_consumer_not_yet_confirmed",
            (
                "Positive *_id values are preserved exactly, but are not "
                "projected as graph edges until their destination table and "
                "consumer semantics are confirmed."
            ),
            canonical_json(
                {
                    "occurrences": sum(unclassified_id_columns.values()),
                    "columns": dict(sorted(unclassified_id_columns.items())),
                }
            ),
            STAGE,
            "opaque",
        ),
    )

    for endpoint in sorted(unknown_endpoints):
        row = connection.execute(
            "SELECT state FROM entities WHERE entity_key=?", (endpoint,)
        ).fetchone()
        if row is not None and str(row["state"]) in {"confirmed", "tombstone"}:
            continue
        connection.execute(
            """
            INSERT OR IGNORE INTO gaps(
                gap_key,entity_key,dimension,state,severity,blocker_code,reason,
                required_evidence,provenance
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("stage50", "gap", endpoint),
                endpoint,
                "dependency_closure",
                "unknown",
                2,
                "referenced_endpoint_not_in_decoded_stages",
                "A native Stage 50 row references an endpoint not yet decoded.",
                "Decode the authoritative table in its owning forensic stage.",
                TOOL_NAME,
            ),
        )

    prior_keys = {
        entity_key(kind, native_id) for kind, native_id in prior
    }
    wiki_counts = _import_wiki(
        connection,
        config=config,
        input_hashes=input_hashes,
        prior_keys=prior_keys,
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
        raise RuntimeError(f"Stage 50 has {orphan_relations} orphan relations")
    wi_reference_rows = connection.execute(
        """
        SELECT substr(locator,1,instr(locator,'[')-1) AS source,
               COUNT(*) AS row_count
        FROM relations
        WHERE dst_entity_key LIKE 'world_interaction:%'
        GROUP BY source ORDER BY source
        """
    ).fetchall()
    wi_reference_sources = {
        str(row["source"]): int(row["row_count"])
        for row in wi_reference_rows
    }
    invalid_wi_references = int(
        connection.execute(
            "SELECT COUNT(*) FROM relations WHERE dst_entity_key=?",
            (entity_key("world_interaction", WORLD_INTERACTION_INVALID_ID),),
        ).fetchone()[0]
    )
    checks = {
        "selected_queries": len(inventory),
        "decoded_tables": len(results),
        "decoded_rows": sum(len(result.rows) for result in results.values()),
        "native_result_absent": len(absent_calls),
        "unmapped_result_boundaries": len(inventory) - len(results) - len(absent_calls),
        "skill_rows": native_counts["skills"],
        "buff_rows": native_counts["buffs"],
        "effect_rows": native_counts["effects"],
        "localizations": len(localized_rows),
        "properties": property_count,
        "relations": relation_count,
        "unknown_endpoints": len(unknown_endpoints),
        "effect_detail_tombstones": sum(effect_tombstones.values()),
        "plot_event_tombstones": len(plot_event_references),
        "plot_event_tombstone_references": sum(
            plot_event_references.values()
        ),
        "unclassified_positive_id_fields": sum(
            unclassified_id_columns.values()
        ),
        "wiki_skill_entities": wiki_counts.get("entities", 0),
        "orphan_relations": orphan_relations,
        "world_interaction_enum_members": wi_counts["enum_members"],
        "world_interaction_detail_rows": wi_counts["detail_rows"],
        "world_interaction_references": sum(
            wi_reference_sources.values()
        ),
        "world_interaction_invalid_references": invalid_wi_references,
    }
    expected = {
        "selected_queries": 141,
        "decoded_tables": 101,
        "decoded_rows": 657_459,
        "native_result_absent": 5,
        "unmapped_result_boundaries": 35,
        "skill_rows": 33_466,
        "buff_rows": 27_303,
        "effect_rows": 60_885,
        "localizations": 176_235,
        "wiki_skill_entities": 4,
        "orphan_relations": 0,
        "plot_event_tombstones": 14,
        "plot_event_tombstone_references": 4_963,
        "world_interaction_enum_members": 105,
        "world_interaction_detail_rows": 60,
        "world_interaction_references": 7_679,
        "world_interaction_invalid_references": 0,
    }
    for key, value in expected.items():
        if checks[key] != value:
            raise RuntimeError(
                f"Stage 50 invariant changed: {key}={checks[key]} "
                f"(expected {value})"
            )
    validation_rows = {
        "x86_x64_layout_parity": architecture,
        "decoded_native_inventory": {
            "tables": len(results),
            "rows": checks["decoded_rows"],
            "row_counts": native_counts,
        },
        "effect_type_string_resolution": {
            "generic_effect_types": len(diagnostics["effect_string_map"]),
            "plot_type_references": len(diagnostics["plot_string_map"]),
        },
        "effect_detail_lifecycle": {
            "tombstones": sum(effect_tombstones.values()),
            "by_table": dict(sorted(effect_tombstones.items())),
            "policy": (
                "referenced actual_id absent from a decoded unfiltered native "
                "result is a tombstone, not an undecoded endpoint"
            ),
        },
        "plot_event_lifecycle": {
            "authoritative_table": "plot_events",
            "authoritative_rows": len(results["plot_events"].rows),
            "tombstones": {
                str(key): value
                for key, value in sorted(plot_event_references.items())
            },
            "incoming_reference_sources": dict(
                sorted(plot_event_reference_sources.items())
            ),
            "policy": (
                "a referenced plot_event ID absent from the complete unfiltered "
                "native plot_events result is a tombstone"
            ),
        },
        "world_interaction_native_enum": {
            "members": wi_counts["enum_members"],
            "detail_rows": wi_counts["detail_rows"],
            "metadata_is_optional": True,
            "invalid_default_excludes": WORLD_INTERACTION_INVALID_ID,
            "x64_switch": world_interactions["x64_switch"]["function"],
            "x86_switch": world_interactions["x86_switch"]["function"],
            "x64_loader": world_interactions["x64_loader"],
            "x86_loader": world_interactions["x86_loader"],
            "columns": list(world_interactions["columns"]),
            "layout": list(world_interactions["layout"]),
            "incoming_reference_sources": wi_reference_sources,
            "invalid_references": invalid_wi_references,
            "detail_value_counts": world_interactions[
                "detail_value_counts"
            ],
        },
        "localization_inventory": {"rows": len(localized_rows)},
        "wiki_corroboration": wiki_counts,
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
                stable_key("validation", "stage", "50", name),
                "stage",
                "50",
                name,
                "confirmed",
                canonical_json(evidence),
            ),
        )
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        ("stage50.input_hashes", canonical_json(input_hashes)),
    )
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        ("stage50.native_row_counts", canonical_json(native_counts)),
    )
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        ("stage50.diagnostics", canonical_json(diagnostics)),
    )
    for key, value in sorted(checks.items()):
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
            (f"stage50.{key}", str(value)),
        )
