from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from . import TOOL_NAME, TOOL_VERSION
from .config import ForensicsConfig
from .quest_item_crosswalk import (
    MINIMUM_DELAY,
    PARSER_VERSION as ITEM_PARSER_VERSION,
    QuestWikiClient,
    _DomParser,
    _Node,
    _atomic_bytes,
    _clean,
    _read_snapshot_metadata,
    _snapshot_paths,
    _snapshot_valid,
    _walk,
    _write_snapshot,
    parse_quest_item_page,
    quest_item_cache,
)
from .quests import act_detail_table, relation_target
from .util import atomic_text, canonical_json, sha256_file, sha256_text, stable_key
from .world_actors import CachedResultReader


SCHEMA_VERSION = 1
PARSER_VERSION = "nuia-story-structured-v1"
CATEGORY_ID = 3
RACE_ID = 1
CATEGORY_NATIVE_NAME = "[종족 퀘스트] 누이안"
EXPECTED_QUEST_IDS = (
    6839,
    330, 2531, 2532, 2255, 2256, 2257,
    2258, 2259, 2260, 1525, 2263, 2261, 3503, 2262, 2264, 2265, 2266,
    2485, 4393, 2486, 3573, 2488, 2489, 4394, 4396,
    2490, 2491, 1424, 2492, 4397, 2494, 2495, 2496, 4398,
    2498, 3985, 3986, 4399, 4400, 3987,
    4402, 4403, 4404, 3988, 3989, 4405, 4406, 4407,
    3990, 3991, 4409, 4410, 3993, 4411,
)
EXPECTED_CHAPTERS = {0: 1, 1: 6, 2: 11, 3: 8, 4: 9, 5: 6, 6: 14}
EXPECTED_ZONES = {2: 8, 7: 5, 9: 7, 10: 6, 11: 7, 15: 6, 124: 6, 125: 5, 131: 3, 141: 2}
EXPECTED_ACT_TYPES = {
    "QuestActSupplyItem": 120,
    "QuestActSupplyExp": 55,
    "QuestActConReportNpc": 40,
    "QuestActConAcceptNpc": 39,
    "QuestActObjItemGather": 17,
    "QuestActConAcceptDoodad": 15,
    "QuestActConReportDoodad": 13,
    "QuestActSupplyCopper": 11,
    "QuestActSupplySelectiveItem": 10,
    "QuestActObjItemUse": 9,
    "QuestActObjTalk": 4,
    "QuestActObjInteraction": 3,
    "QuestActConAutoComplete": 2,
    "QuestActObjMonsterHunt": 2,
    "QuestActConAcceptSphere": 1,
    "QuestActObjCinema": 1,
    "QuestActObjMonsterGroupHunt": 1,
    "QuestActObjSphere": 1,
}
ORDER_STATES = {
    "confirmed_native_dependency",
    "corroborated_order",
    "native_ordinal_candidate",
    "wiki_only",
    "conflict",
    "ambiguous",
    "chapter_boundary_unresolved",
    "blocked",
}
CLOSURE_STATES = {
    "complete_native_closure",
    "tombstone",
    "missing",
    "unknown",
    "opaque",
    "blocked",
    "not_applicable",
}
TERMINAL_WIKI_STATES = {
    "confirmed",
    "partial",
    "redirected_confirmed",
    "redirected_partial",
    "permanent_missing",
    "parse_failed",
    "redirected_parse_failed",
}
QUEST_LINK = re.compile(r"^/(?P<locale>[^/]+)/db/quests/(?P<id>\d+)(?:[/?#].*)?$")
ENTITY_LINK = re.compile(
    r"^/(?P<locale>[^/]+)/db/(?P<kind>quests|items|npcs|doodads|skills)/"
    r"(?P<id>\d+)(?:[/?#].*)?$"
)


SCHEMA = """
PRAGMA page_size=4096;
PRAGMA auto_vacuum=NONE;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE source_artifacts (
    artifact_key TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    path TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    authority TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE story_quests (
    quest_id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL,
    race INTEGER NOT NULL,
    chapter_idx INTEGER NOT NULL,
    quest_idx INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    native_name TEXT,
    visible_name TEXT,
    membership_state TEXT NOT NULL,
    native_state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE scope_boundary_candidates (
    candidate_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    direction TEXT NOT NULL,
    reason TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE story_order_edges (
    edge_key TEXT PRIMARY KEY,
    src_quest_id INTEGER NOT NULL,
    dst_quest_id INTEGER NOT NULL,
    edge_kind TEXT NOT NULL,
    native_edge_state TEXT NOT NULL,
    ordinal_state TEXT NOT NULL,
    wiki_requires_state TEXT NOT NULL,
    wiki_opens_state TEXT NOT NULL,
    reciprocal_state TEXT NOT NULL,
    overall_state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE story_quest_components (
    component_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    component_kind_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    row_json TEXT NOT NULL,
    native_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE story_quest_acts (
    act_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    quest_act_id INTEGER NOT NULL,
    act_detail_type TEXT NOT NULL,
    act_detail_id INTEGER NOT NULL,
    detail_row_json TEXT,
    closure_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE story_quest_endpoints (
    endpoint_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    phase TEXT NOT NULL,
    endpoint_kind TEXT NOT NULL,
    endpoint_id INTEGER NOT NULL,
    act_detail_type TEXT NOT NULL,
    act_detail_id INTEGER NOT NULL,
    client_doodad INTEGER,
    proxy_npc_id INTEGER,
    spawn_state TEXT NOT NULL,
    closure_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE story_quest_items (
    relation_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    quest_act_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    item_role TEXT NOT NULL,
    selection_mode TEXT NOT NULL,
    count INTEGER,
    grade_id INTEGER,
    flags_json TEXT NOT NULL,
    native_relation_state TEXT NOT NULL,
    item_closure_state TEXT NOT NULL,
    crosswalk_state TEXT,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE story_dependency_closure (
    closure_key TEXT PRIMARY KEY,
    root_quest_id INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    src_entity_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    dst_entity_key TEXT NOT NULL,
    dst_state TEXT NOT NULL,
    required INTEGER NOT NULL,
    closure_state TEXT NOT NULL,
    blocker_root TEXT,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_story_pages (
    quest_id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_sha256 TEXT,
    detail_state TEXT NOT NULL,
    parser_version TEXT,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_story_edges (
    wiki_edge_key TEXT PRIMARY KEY,
    src_quest_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    dst_quest_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    label TEXT,
    href TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    parse_state TEXT NOT NULL,
    context_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_story_relations (
    wiki_relation_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    dst_kind TEXT NOT NULL,
    dst_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    label TEXT,
    href TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    context_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE downstream_audit_queue (
    audit_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    chapter_idx INTEGER NOT NULL,
    quest_idx INTEGER NOT NULL,
    blocker_kind TEXT NOT NULL,
    blocked_entity_key TEXT,
    severity TEXT NOT NULL,
    recommended_stop_point TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE validation_events (
    validation_key TEXT PRIMARY KEY,
    check_name TEXT NOT NULL,
    state TEXT NOT NULL,
    expected_json TEXT,
    actual_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX idx_story_quests_order ON story_quests(chapter_idx,quest_idx);
CREATE INDEX idx_story_quests_zone_level ON story_quests(zone_id,level);
CREATE INDEX idx_story_edges_src ON story_order_edges(src_quest_id);
CREATE INDEX idx_story_edges_dst ON story_order_edges(dst_quest_id);
CREATE INDEX idx_story_edges_state ON story_order_edges(overall_state);
CREATE INDEX idx_story_components_quest_kind ON story_quest_components(quest_id,component_kind_id);
CREATE INDEX idx_story_acts_quest_type ON story_quest_acts(quest_id,act_detail_type);
CREATE INDEX idx_story_endpoints_quest_phase ON story_quest_endpoints(quest_id,phase);
CREATE INDEX idx_story_endpoints_kind_id ON story_quest_endpoints(endpoint_kind,endpoint_id);
CREATE INDEX idx_story_items_quest_role ON story_quest_items(quest_id,item_role);
CREATE INDEX idx_story_items_item ON story_quest_items(item_id);
CREATE INDEX idx_story_closure_root_depth ON story_dependency_closure(root_quest_id,depth);
CREATE INDEX idx_story_closure_dst_state ON story_dependency_closure(dst_entity_key,closure_state);
CREATE INDEX idx_wiki_story_edges_src_relation ON wiki_story_edges(src_quest_id,relation);
CREATE INDEX idx_audit_order_severity ON downstream_audit_queue(chapter_idx,quest_idx,severity);
"""


@dataclass(frozen=True)
class WikiQuestEdge:
    relation: str
    dst_quest_id: int
    ordinal: int
    label: str
    href: str
    context: str


@dataclass(frozen=True)
class WikiVisibleRelation:
    relation: str
    dst_kind: str
    dst_id: int
    ordinal: int
    label: str
    href: str
    context: str


@dataclass(frozen=True)
class ParsedStoryPage:
    name: str | None
    parse_state: str
    edges: tuple[WikiQuestEdge, ...]
    relations: tuple[WikiVisibleRelation, ...]


def story_paths(config: ForensicsConfig) -> dict[str, Path]:
    stem = config.output_dir / "nuia-story-quest-graph-v1"
    return {
        "database": stem.with_suffix(".sqlite3"),
        "manifest": stem.with_suffix(".manifest.json"),
        "summary": stem.with_name(stem.name + "-summary.json"),
        "gaps": stem.with_name(stem.name + "-gaps.csv"),
        "test_order": config.output_dir / "nuia-story-quest-test-order-v1.csv",
        "viewer": stem.with_suffix(".html"),
        "wiki_manifest": stem.with_name(stem.name + "-wiki-snapshot-manifest.json"),
    }


def _open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _node_context(node: _Node) -> str:
    current = node.parent
    while current is not None:
        if current.tag == "div" and ("mb-2" in current.classes or "m-0" in current.classes):
            value = current.text()
            if value:
                return value
        current = current.parent
    return node.text()


def _story_relation_hint(context: str, kind: str) -> str:
    value = context.casefold()
    if "accept quest from npc" in value:
        return "accept_from"
    if "report to npc" in value:
        return "report_to"
    if "accept quest from doodad" in value:
        return "accept_from_doodad"
    if "report to doodad" in value:
        return "report_to_doodad"
    if "collect item" in value or "obtain item" in value:
        return "objective_item"
    if "use item" in value:
        return "objective_use_item"
    if "reward" in value or "choose item" in value:
        return "reward_item"
    if "kill" in value or "defeat" in value:
        return "objective_actor"
    if "talk" in value:
        return "objective_actor"
    return f"visible_{kind.removesuffix('s')}"


def parse_story_page(payload: bytes, *, quest_id: int, locale: str = "na-en") -> ParsedStoryPage:
    dom = _DomParser()
    dom.feed(payload.decode("utf-8", errors="replace"))
    all_text = dom.root.text()
    item_page = parse_quest_item_page(payload, entity_id=quest_id, locale=locale)
    edge_ordinals: Counter[str] = Counter()
    visible_ordinals: Counter[str] = Counter()
    edges: list[WikiQuestEdge] = []
    relations: list[WikiVisibleRelation] = []
    seen_edges: set[tuple[str, int, str]] = set()
    seen_relations: set[tuple[str, str, int, str]] = set()
    for node in _walk(dom.root):
        if node.tag != "a":
            continue
        href = node.attrs.get("href", "")
        quest_match = QUEST_LINK.match(href)
        context = _node_context(node)
        ancestor_contexts: list[str] = []
        current = node.parent
        for _ in range(8):
            if current is None:
                break
            if current.tag == "div" and {"m-0", "cl-l-yellow"}.issubset(current.classes):
                value = current.text()
                if value and value not in ancestor_contexts:
                    ancestor_contexts.append(value)
            current = current.parent
        relation_context = next(
            (
                value for value in ancestor_contexts
                if "requires precompleted quest" in value.casefold()
                or "opens access to the quest" in value.casefold()
                or "opens access to quest" in value.casefold()
            ),
            context,
        )
        context_cf = relation_context.casefold()
        relation = None
        if "requires precompleted quest" in context_cf:
            relation = "requires_precompleted_quest"
        elif "opens access to the quest" in context_cf or "opens access to quest" in context_cf:
            relation = "opens_access_to"
        if relation and quest_match and quest_match.group("locale") == locale:
            destination = int(quest_match.group("id"))
            identity = (relation, destination, href)
            if identity not in seen_edges:
                seen_edges.add(identity)
                edge_ordinals[relation] += 1
                edges.append(
                    WikiQuestEdge(
                        relation,
                        destination,
                        edge_ordinals[relation],
                        node.text(),
                        href,
                        relation_context,
                    )
                )
            continue
        match = ENTITY_LINK.match(href)
        if not match or match.group("locale") != locale:
            continue
        if node.attrs.get("role-type") != "model-info":
            continue
        kind = match.group("kind")
        destination = int(match.group("id"))
        if kind == "items":
            continue
        hint = _story_relation_hint(context, kind)
        identity = (hint, kind, destination, href)
        if identity in seen_relations:
            continue
        seen_relations.add(identity)
        visible_ordinals[hint] += 1
        relations.append(
            WikiVisibleRelation(
                hint,
                kind.removesuffix("s"),
                destination,
                visible_ordinals[hint],
                node.text(),
                href,
                context,
            )
        )
    for mention in item_page.mentions:
        relations.append(
            WikiVisibleRelation(
                mention.section_kind,
                "item",
                mention.item_id,
                mention.ordinal,
                mention.label,
                mention.href,
                mention.context,
            )
        )
    parse_state = item_page.parse_state if f"ID: {quest_id}" in all_text else "parse_failed"
    return ParsedStoryPage(
        item_page.name,
        parse_state,
        tuple(edges),
        tuple(relations),
    )


def _story_wiki_manifest(config: ForensicsConfig, *, reused: list[int], downloaded: list[int]) -> dict[str, Any]:
    cache = quest_item_cache(config)
    records = []
    for quest_id in EXPECTED_QUEST_IDS:
        html_path, metadata_path = _snapshot_paths(cache, quest_id)
        if not metadata_path.is_file():
            records.append({"quest_id": quest_id, "state": "not_requested"})
            continue
        metadata = _read_snapshot_metadata(metadata_path)
        records.append(
            {
                "quest_id": quest_id,
                "status_code": metadata.get("status_code"),
                "page_state": metadata.get("page_state"),
                "content_bytes": metadata.get("content_bytes"),
                "content_sha256": metadata.get("content_sha256"),
                "content_type": metadata.get("content_type"),
                "url": metadata.get("url"),
                "final_url": metadata.get("final_url"),
                "parser_version": metadata.get("parser_version"),
                "metadata_sha256": sha256_file(metadata_path),
                "html_valid": bool(html_path.is_file() and _snapshot_valid(cache, quest_id)),
            }
        )
    manifest = {
        "authority": "external_corroborative",
        "client_build": config.client_build,
        "expected_quests": len(EXPECTED_QUEST_IDS),
        "parser_version": PARSER_VERSION,
        "records": records,
        "reused_ids": sorted(reused),
        "downloaded_ids": sorted(downloaded),
        "record_digest": sha256_text(canonical_json(records)),
        "schema_version": 1,
    }
    atomic_text(story_paths(config)["wiki_manifest"], canonical_json(manifest, pretty=True))
    return manifest


def freeze_nuia_story_wiki(
    config: ForensicsConfig,
    *,
    resume: bool = True,
    delay: float = MINIMUM_DELAY,
    progress: Callable[[str], None] | None = None,
    fetcher: Callable[[str], tuple[Any, ...]] | None = None,
) -> dict[str, Any]:
    cache = quest_item_cache(config)
    cache.mkdir(parents=True, exist_ok=True)
    lock_path = cache / ".freeze.lock"
    if lock_path.is_file():
        try:
            owner_pid = int(lock_path.read_text(encoding="ascii").strip())
            os.kill(owner_pid, 0)
        except (OSError, ValueError):
            lock_path.unlink(missing_ok=True)
        else:
            raise RuntimeError(f"Quest wiki acquisition is already active in PID {owner_pid}")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        descriptor = -1
        client = QuestWikiClient(
            base_url=config.wiki_base_url,
            requested_delay=delay,
            fetcher=fetcher,
        )
        sample = f"{config.wiki_base_url}/{config.wiki_locale}/db/quests/{EXPECTED_QUEST_IDS[0]}"
        robots, robots_payload = client.load_robots(sample)
        _atomic_bytes(cache / "robots.txt", robots_payload)
        atomic_text(cache / "robots-policy.json", canonical_json(robots, pretty=True))
        reused: list[int] = []
        downloaded: list[int] = []
        failures: list[int] = []
        for index, quest_id in enumerate(EXPECTED_QUEST_IDS, 1):
            if _snapshot_valid(cache, quest_id):
                reused.append(quest_id)
            else:
                url = f"{config.wiki_base_url}/{config.wiki_locale}/db/quests/{quest_id}"
                status, payload, content_type, final_url, error = client.fetch(url)
                _write_snapshot(
                    cache,
                    quest_id=quest_id,
                    canonical_url=url,
                    status_code=status,
                    payload=payload,
                    content_type=content_type,
                    final_url=final_url,
                    locale=config.wiki_locale,
                    error=error,
                )
                downloaded.append(quest_id)
                if status not in {200, 404, 410}:
                    failures.append(quest_id)
            if progress and (index % 10 == 0 or index == len(EXPECTED_QUEST_IDS)):
                progress(
                    f"nuia story wiki {index}/{len(EXPECTED_QUEST_IDS)} "
                    f"downloaded={len(downloaded)} reused={len(reused)} failures={len(failures)}"
                )
        manifest = _story_wiki_manifest(config, reused=reused, downloaded=downloaded)
        return {
            "cache": cache,
            "downloaded_ids": downloaded,
            "failures": failures,
            "manifest": story_paths(config)["wiki_manifest"],
            "record_digest": manifest["record_digest"],
            "reused_ids": reused,
        }
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        lock_path.unlink(missing_ok=True)


DOODAD_RESULT_SPECS: dict[str, dict[str, Any]] = {
    "doodad_func_clout_effects": {
        "columns": "doodad_func_clout_id effect_id".split(),
        "layout": "68 68".split(),
        "start": 0x8AAEF32,
        "done": 0x8AB0A32,
        "rows": 768,
        "key_columns": ("doodad_func_clout_id", "effect_id"),
        "require_sorted": False,
    },
    "doodad_func_clouts": {
        "columns": (
            "id aoe_shape_id buff_id check_no_target_tag_src "
            "check_projectile_high_priority check_target_tag_src duration "
            "fx_group_id next_phase projectile_id show_to_friendly_only "
            "target_buff_tag_id target_max_count target_no_buff_tag_id "
            "target_parent target_relation_id tick use_origin_source"
        ).split(),
        "layout": (
            "68 68 68 38 38 38 68 68 68 68 38 68 68 68 38 68 68 38"
        ).split(),
        "start": 0x635CABF,
        "done": 0x638D39F,
        "rows": 3616,
    },
    "doodad_func_loot_items": {
        "columns": "id count_max count_min group_id item_id percent remain_time wi_id".split(),
        "layout": ["68"] * 8,
        "start": 0x639B4E6,
        "done": 0x63ABBFF,
        "rows": 2041,
    },
    "doodad_func_quests": {
        "columns": "id quest_kind_id quest_id".split(),
        "layout": ["68"] * 3,
        "start": 0x63AF0F4,
        "done": 0x63B4A61,
        "rows": 1761,
    },
    "doodad_func_finals": {
        "columns": (
            "id after max_time min_time respawn show_end_time show_tip tip"
        ).split(),
        "layout": "68 68 68 68 38 38 38 78".split(),
        "start": 0x63D6590,
        "done": 0x63EE303,
        "rows": 4358,
    },
    "doodad_func_timers": {
        "columns": (
            "id delay keep_requester next_phase reset_first_interaction "
            "show_end_time show_tip tip"
        ).split(),
        "layout": "68 68 38 68 38 38 38 78".split(),
        "start": 0x63F3090,
        "done": 0x643B261,
        "rows": 15004,
    },
    "doodad_funcs": {
        "columns": (
            "id act_count actual_func_type actual_func_id doodad_func_group_id "
            "forbid_on_climb func_skill_id next_phase perm_id popup_desc "
            "popup_warn reset_first_interaction sound_id"
        ).split(),
        "layout": "68 68 78 68 68 38 68 68 68 78 38 38 68".split(),
        "start": 0x64B5F4C,
        "done": 0x6603655,
        "rows": 31625,
        "first_string_reference": 288531,
    },
    "doodad_phase_funcs": {
        "columns": "id actual_func_type actual_func_id doodad_func_group_id".split(),
        "layout": "68 78 68 68".split(),
        "start": 0x660365B,
        "done": 0x66D35BA,
        "rows": 47255,
        "first_string_reference": 288638,
    },
    "doodad_func_groups": {
        "columns": (
            "id color doodad_almighty_id doodad_func_group_kind_id icon_key "
            "is_msg_to_world is_msg_to_zone model msg_to_faction_id name "
            "over_head_mark_gap phase_msg sound_time sound_id title_color "
            "title_msg use_ui_msg"
        ).split(),
        "layout": "68 78 68 68 78 38 38 78 68 78 68 78 68 68 78 78 38".split(),
        "start": 0x66D3C1A,
        "done": 0x69D7173,
        "rows": 43792,
        "first_string_reference": 288692,
    },
    "doodad_almighties": {
        "columns": (
            "id childable client_doodad climate_id collide_ship collide_vehicle "
            "custom_dual_material_id delete_when_not_exist_creator "
            "despawn_on_collision faction_id force_tod_top_priority "
            "force_up_action group_id growth_time load_model_from_world mark_model "
            "max_time mgmt_spawn min_time model model_kind_id name no_collision "
            "once_one_interaction once_one_man or_unit_reqs parentable "
            "pass_through_innerside pass_through_outerside pass_update_dist "
            "percent place_area_kind_id reset_data restrict_zone_id save_indun "
            "show_minimap show_name sim_height sim_radius spawn_fx_group_id "
            "system_doodad target_decal_size use_creator_faction use_target_decal "
            "use_target_highlight use_target_silhouette view_dist_ratio"
        ).split(),
        "layout": (
            "68 38 38 68 38 38 68 38 38 68 38 38 68 68 38 78 68 38 "
            "68 78 68 78 38 38 38 38 38 38 38 38 68 68 38 68 38 38 "
            "38 68 68 68 38 60 38 38 38 38 68"
        ).split(),
        "start": 0x69E2DCB,
        "done": 0x6BC0107,
        "rows": 15290,
    },
}


def _decode_result(data: bytes, table: str, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reader = CachedResultReader(data, spec.get("first_string_reference"))
    cursor = int(spec["start"])
    rows: list[dict[str, Any]] = []
    while cursor < len(data) and data[cursor] == 100:
        values, cursor = reader.row(cursor, list(spec["layout"]))
        rows.append(dict(zip(spec["columns"], values, strict=True)))
    if cursor != int(spec["done"]) or cursor >= len(data) or data[cursor] != 101:
        raise RuntimeError(f"{table}: cached result ended at 0x{cursor:X}")
    if len(rows) != int(spec["rows"]):
        raise RuntimeError(f"{table}: expected {spec['rows']} rows, found {len(rows)}")
    key_columns = tuple(spec.get("key_columns", ("id",)))
    keys = [tuple(row[column] for column in key_columns) for row in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError(f"{table}: native keys are not unique")
    if spec.get("require_sorted", True) and keys != sorted(keys):
        raise RuntimeError(f"{table}: native keys are not sorted")
    return rows, {
        "columns": list(spec["columns"]),
        "layout": list(spec["layout"]),
        "start": int(spec["start"]),
        "done": int(spec["done"]),
        "rows": len(rows),
        "key_columns": list(key_columns),
        "rows_sha256": sha256_text("\n".join(canonical_json(row) for row in rows) + "\n"),
    }


def _load_native_rows(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    result = []
    for row in connection.execute(
        "SELECT native_row_key,state,row_json,provenance,evidence_json "
        "FROM native_rows WHERE source_table=? ORDER BY native_row_key",
        (table,),
    ):
        result.append(
            {
                "native_row_key": str(row["native_row_key"]),
                "state": str(row["state"]),
                "row": json.loads(row["row_json"]),
                "provenance": str(row["provenance"]),
                "evidence": json.loads(row["evidence_json"]),
            }
        )
    return result


def _row_index(source: dict[str, Any]) -> int:
    return int(source["evidence"].get("row_index", 0))


def _native_story(config: ForensicsConfig) -> dict[str, Any]:
    connection = _open_read_only(config.stage_40)
    try:
        contexts_all = _load_native_rows(connection, "quest_contexts")
        categories = _load_native_rows(connection, "quest_categories")
        components_all = _load_native_rows(connection, "quest_components")
        acts_all = _load_native_rows(connection, "quest_acts")
        category = next(
            (row for row in categories if int(row["row"]["id"]) == CATEGORY_ID),
            None,
        )
        if category is None:
            raise RuntimeError("Stage 40 has no quest category 3")
        contexts = [
            row for row in contexts_all
            if int(row["row"].get("category_id", 0)) == CATEGORY_ID
            and int(row["row"].get("race", 0)) == RACE_ID
        ]
        contexts.sort(key=lambda row: (int(row["row"]["chapter_idx"]), int(row["row"]["quest_idx"]), int(row["row"]["id"])))
        quest_ids = {int(row["row"]["id"]) for row in contexts}
        components = [
            row for row in components_all
            if int(row["row"].get("quest_context_id", 0)) in quest_ids
        ]
        components.sort(key=lambda row: (_row_index(row), int(row["row"]["id"])))
        component_ids = {int(row["row"]["id"]) for row in components}
        acts = [
            row for row in acts_all
            if int(row["row"].get("quest_component_id", 0)) in component_ids
        ]
        acts.sort(key=lambda row: (_row_index(row), int(row["row"]["id"])))
        detail_tables = sorted({act_detail_table(str(row["row"]["act_detail_type"])) for row in acts})
        detail_sources = {
            table: {int(value["row"]["id"]): value for value in _load_native_rows(connection, table)}
            for table in detail_tables
        }
        details: dict[int, dict[str, Any]] = {}
        missing_details = []
        for act in acts:
            table = act_detail_table(str(act["row"]["act_detail_type"]))
            detail_id = int(act["row"]["act_detail_id"])
            detail = detail_sources.get(table, {}).get(detail_id)
            if detail is None:
                missing_details.append(f"{table}:{detail_id}")
            else:
                details[int(act["row"]["id"])] = {**detail, "source_table": table}
        group_tables = {
            name: _load_native_rows(connection, name)
            for name in ("quest_context_groups", "quest_context_group_members")
        }
    finally:
        connection.close()
    if missing_details:
        raise RuntimeError(f"Story act details missing: {sorted(missing_details)}")
    return {
        "stage40_path": config.stage_40.resolve().as_posix(),
        "category": category,
        "contexts": contexts,
        "contexts_all": contexts_all,
        "components_all": components_all,
        "acts_all": acts_all,
        "components": components,
        "acts": acts,
        "details": details,
        "group_tables": group_tables,
    }


def _doodad_native_closure(config: ForensicsConfig, story: dict[str, Any]) -> dict[str, Any]:
    doodad_ids: set[int] = set()
    for act in story["acts"]:
        detail = story["details"][int(act["row"]["id"])]
        payload = detail["row"]
        for field in ("doodad_id", "highlight_doodad_id"):
            value = int(payload.get(field, 0) or 0)
            if value > 0:
                doodad_ids.add(value)
    data = config.source_game11.read_bytes()
    decoded: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, Any] = {}
    for table, spec in DOODAD_RESULT_SPECS.items():
        decoded[table], evidence[table] = _decode_result(data, table, spec)
    almighties = {
        int(row["id"]): row for row in decoded["doodad_almighties"]
        if int(row["id"]) in doodad_ids
    }
    groups = [
        row for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) in doodad_ids
    ]
    group_ids = {int(row["id"]) for row in groups}
    funcs = [
        row for row in decoded["doodad_funcs"]
        if int(row["doodad_func_group_id"]) in group_ids
    ]
    quest_ids = {
        int(row["actual_func_id"]) for row in funcs
        if str(row["actual_func_type"]) == "DoodadFuncQuest"
    }
    loot_ids = {
        int(row["actual_func_id"]) for row in funcs
        if str(row["actual_func_type"]) == "DoodadFuncLootItem"
    }
    quest_funcs = {
        int(row["id"]): row for row in decoded["doodad_func_quests"]
        if int(row["id"]) in quest_ids
    }
    loot_funcs = {
        int(row["id"]): row for row in decoded["doodad_func_loot_items"]
        if int(row["id"]) in loot_ids
    }
    loot_catalog_anchor_2482 = next(
        (row for row in decoded["doodad_func_loot_items"] if int(row["id"]) == 2482),
        None,
    )
    return {
        "doodad_ids": sorted(doodad_ids),
        "almighties": almighties,
        "groups": groups,
        "funcs": funcs,
        "quest_funcs": quest_funcs,
        "loot_funcs": loot_funcs,
        "loot_catalog_anchor_2482": loot_catalog_anchor_2482,
        "decoder_evidence": evidence,
    }


def _load_story_wiki(config: ForensicsConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[int, str | None]]:
    cache = quest_item_cache(config)
    pages: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    names: dict[int, str | None] = {}
    for quest_id in EXPECTED_QUEST_IDS:
        html_path, metadata_path = _snapshot_paths(cache, quest_id)
        url = f"{config.wiki_base_url}/{config.wiki_locale}/db/quests/{quest_id}"
        if not metadata_path.is_file():
            pages.append(
                {
                    "quest_id": quest_id,
                    "url": url,
                    "status_code": None,
                    "response_sha256": None,
                    "detail_state": "not_requested",
                    "parser_version": None,
                    "evidence": {"metadata_present": False},
                }
            )
            names[quest_id] = None
            continue
        metadata = _read_snapshot_metadata(metadata_path)
        status = metadata.get("status_code")
        digest = metadata.get("content_sha256")
        detail_state = str(metadata.get("page_state", "unknown"))
        parsed = None
        if status == 200 and html_path.is_file() and digest:
            actual = sha256_file(html_path)
            if actual != str(digest).upper():
                detail_state = "hash_mismatch"
            else:
                parsed = parse_story_page(
                    html_path.read_bytes(),
                    quest_id=quest_id,
                    locale=config.wiki_locale,
                )
                detail_state = (
                    detail_state if detail_state.startswith("redirected_")
                    else parsed.parse_state
                )
        names[quest_id] = parsed.name if parsed else None
        pages.append(
            {
                "quest_id": quest_id,
                "url": str(metadata.get("url", url)),
                "status_code": status,
                "response_sha256": digest,
                "detail_state": detail_state,
                "parser_version": PARSER_VERSION,
                "evidence": {
                    "metadata_path": metadata_path.resolve().as_posix(),
                    "metadata_sha256": sha256_file(metadata_path),
                    "source_parser_version": metadata.get("parser_version"),
                    "authority": "external_corroborative",
                },
            }
        )
        if parsed is None:
            continue
        for edge in parsed.edges:
            edges.append(
                {
                    "wiki_edge_key": stable_key(
                        "nuia_story_wiki_edge",
                        quest_id,
                        edge.relation,
                        edge.dst_quest_id,
                        edge.ordinal,
                    ),
                    "src_quest_id": quest_id,
                    "relation": edge.relation,
                    "dst_quest_id": edge.dst_quest_id,
                    "ordinal": edge.ordinal,
                    "label": edge.label,
                    "href": edge.href,
                    "response_sha256": str(digest),
                    "parse_state": "confirmed",
                    "context": {"structural_container": edge.context},
                    "evidence": {
                        "authority": "external_corroborative",
                        "parser_version": PARSER_VERSION,
                        "source_html": html_path.resolve().as_posix(),
                    },
                }
            )
        for relation in parsed.relations:
            relations.append(
                {
                    "wiki_relation_key": stable_key(
                        "nuia_story_wiki_relation",
                        quest_id,
                        relation.relation,
                        relation.dst_kind,
                        relation.dst_id,
                        relation.ordinal,
                    ),
                    "quest_id": quest_id,
                    "relation": relation.relation,
                    "dst_kind": relation.dst_kind,
                    "dst_id": relation.dst_id,
                    "ordinal": relation.ordinal,
                    "label": relation.label,
                    "href": relation.href,
                    "response_sha256": str(digest),
                    "context": {"structural_container": relation.context},
                    "evidence": {
                        "authority": "external_corroborative",
                        "parser_version": PARSER_VERSION,
                        "source_html": html_path.resolve().as_posix(),
                    },
                }
            )
    pages.sort(key=lambda row: row["quest_id"])
    edges.sort(key=lambda row: row["wiki_edge_key"])
    relations.sort(key=lambda row: row["wiki_relation_key"])
    return pages, edges, relations, names


def _order_edges(contexts: list[dict[str, Any]], wiki_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        (row["row"] for row in contexts),
        key=lambda row: (int(row["chapter_idx"]), int(row["quest_idx"]), int(row["id"])),
    )
    requires = {
        (int(row["dst_quest_id"]), int(row["src_quest_id"]))
        for row in wiki_edges if row["relation"] == "requires_precompleted_quest"
    }
    opens = {
        (int(row["src_quest_id"]), int(row["dst_quest_id"]))
        for row in wiki_edges if row["relation"] == "opens_access_to"
    }
    story_ids = {int(row["id"]) for row in ordered}
    result: list[dict[str, Any]] = []
    ordinal_pairs: set[tuple[int, int]] = set()
    for left, right in zip(ordered, ordered[1:]):
        src = int(left["id"])
        dst = int(right["id"])
        pair = (src, dst)
        ordinal_pairs.add(pair)
        same_chapter = int(left["chapter_idx"]) == int(right["chapter_idx"])
        has_requires = pair in requires
        has_opens = pair in opens
        reciprocal = has_requires and has_opens
        if same_chapter and reciprocal:
            overall = "corroborated_order"
        elif same_chapter:
            overall = "native_ordinal_candidate"
        elif reciprocal:
            overall = "corroborated_order"
        else:
            overall = "chapter_boundary_unresolved"
        result.append(
            {
                "edge_key": stable_key("nuia_story_order", src, dst, "ordinal"),
                "src_quest_id": src,
                "dst_quest_id": dst,
                "edge_kind": "native_editorial_ordinal",
                "native_edge_state": "not_demonstrated",
                "ordinal_state": "same_chapter_neighbor" if same_chapter else "chapter_boundary_neighbor",
                "wiki_requires_state": "corroborated_visible" if has_requires else "absent_in_snapshot",
                "wiki_opens_state": "corroborated_visible" if has_opens else "absent_in_snapshot",
                "reciprocal_state": "reciprocal" if reciprocal else ("one_way" if has_requires or has_opens else "absent"),
                "overall_state": overall,
                "provenance": "stage40_native_ordinal+stage70_wiki_corroboration",
                "evidence": {
                    "derivation_algorithm": "adjacent_rows_sorted_by_chapter_idx_quest_idx_id_v1",
                    "same_chapter": same_chapter,
                    "source_fields": {
                        "src": [left["chapter_idx"], left["quest_idx"]],
                        "dst": [right["chapter_idx"], right["quest_idx"]],
                    },
                    "wiki_does_not_create_native_dependency": True,
                },
            }
        )
    wiki_pairs = requires | opens
    for src, dst in sorted(wiki_pairs - ordinal_pairs):
        if src not in story_ids or dst not in story_ids:
            continue
        has_requires = (src, dst) in requires
        has_opens = (src, dst) in opens
        result.append(
            {
                "edge_key": stable_key("nuia_story_order", src, dst, "wiki_only"),
                "src_quest_id": src,
                "dst_quest_id": dst,
                "edge_kind": "wiki_visible_nonordinal",
                "native_edge_state": "not_demonstrated",
                "ordinal_state": "not_adjacent",
                "wiki_requires_state": "corroborated_visible" if has_requires else "absent_in_snapshot",
                "wiki_opens_state": "corroborated_visible" if has_opens else "absent_in_snapshot",
                "reciprocal_state": "reciprocal" if has_requires and has_opens else "one_way",
                "overall_state": "wiki_only",
                "provenance": "stage70_wiki_corroboration_only",
                "evidence": {"wiki_does_not_create_native_relation": True},
            }
        )
    result.sort(key=lambda row: row["edge_key"])
    return result


def _scope_candidates(story: dict[str, Any], wiki_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    story_ids = {int(row["row"]["id"]) for row in story["contexts"]}
    rows: dict[str, dict[str, Any]] = {}

    def add(quest_id: int, direction: str, reason: str, state: str, evidence: dict[str, Any]) -> None:
        key = stable_key("nuia_story_scope", quest_id, direction, reason, canonical_json(evidence))
        rows[key] = {
            "candidate_key": key,
            "quest_id": quest_id,
            "direction": direction,
            "reason": reason,
            "state": state,
            "evidence": evidence,
        }

    for source in story["contexts_all"]:
        row = source["row"]
        quest_id = int(row["id"])
        if quest_id in story_ids:
            continue
        if int(row.get("category_id", 0)) == CATEGORY_ID:
            add(
                quest_id,
                "parallel_partition",
                "same_category_other_race",
                "excluded_native",
                {"category_id": row.get("category_id"), "race": row.get("race")},
            )
        elif int(row.get("race", 0)) == RACE_ID:
            add(
                quest_id,
                "parallel_partition",
                "same_race_outside_category",
                "excluded_native",
                {"category_id": row.get("category_id"), "race": row.get("race")},
            )
    for edge in wiki_edges:
        src = int(edge["src_quest_id"])
        dst = int(edge["dst_quest_id"])
        if src in story_ids and dst not in story_ids:
            add(dst, "outgoing", "wiki_story_link_crosses_native_scope", "external_candidate", {"wiki_edge_key": edge["wiki_edge_key"]})
        elif src not in story_ids and dst in story_ids:
            add(src, "incoming", "wiki_story_link_crosses_native_scope", "external_candidate", {"wiki_edge_key": edge["wiki_edge_key"]})
    component_to_quest = {
        int(row["row"]["id"]): int(row["row"]["quest_context_id"])
        for row in story["components_all"]
    }
    all_act_owner = {
        (act_detail_table(str(row["row"]["act_detail_type"])), int(row["row"]["act_detail_id"])):
            component_to_quest.get(int(row["row"]["quest_component_id"]))
        for row in story["acts_all"]
    }
    detail_tables = sorted({value["source_table"] for value in story["details"].values()})
    connection = _open_read_only(Path(story["stage40_path"]))
    try:
        for table in detail_tables:
            for source in _load_native_rows(connection, table):
                target = int(source["row"].get("quest_id", source["row"].get("context_id", 0)) or 0)
                if target <= 0:
                    continue
                owner = all_act_owner.get((table, int(source["row"]["id"])))
                if owner in story_ids and target not in story_ids:
                    add(target, "outgoing", "native_quest_act_reference_crosses_scope", "external_candidate", {"owner_quest_id": owner, "source_table": table, "detail_id": source["row"]["id"]})
                elif owner not in story_ids and target in story_ids and owner:
                    add(int(owner), "incoming", "native_quest_act_reference_crosses_scope", "external_candidate", {"target_story_quest_id": target, "source_table": table, "detail_id": source["row"]["id"]})
    finally:
        connection.close()
    return [rows[key] for key in sorted(rows)]


def _crosswalk(config: ForensicsConfig) -> tuple[Path, dict[tuple[Any, ...], dict[str, Any]], dict[int, dict[str, Any]]]:
    path = config.output_dir / "quest-item-crosswalk-v1.sqlite3"
    connection = _open_read_only(path)
    try:
        grants = {}
        placeholders = ",".join("?" for _ in EXPECTED_QUEST_IDS)
        for row in connection.execute(
            f"SELECT * FROM quest_item_grants WHERE quest_id IN ({placeholders}) ORDER BY grant_key",
            EXPECTED_QUEST_IDS,
        ):
            key = (
                int(row["quest_id"]),
                int(row["component_id"]),
                int(row["quest_act_id"]),
                str(row["act_detail_type"]),
                int(row["act_detail_id"]),
                int(row["item_id"]),
            )
            if key in grants:
                raise RuntimeError(f"Duplicate crosswalk grant identity: {key}")
            grants[key] = dict(row)
        closures = {
            int(row["item_id"]): dict(row)
            for row in connection.execute("SELECT * FROM item_closure ORDER BY item_id")
        }
    finally:
        connection.close()
    return path, grants, closures


def _normalize_item_closure(value: str | None) -> str:
    mapping = {
        "complete_native_closure": "complete_native_closure",
        "generic_dependency_free_candidate": "complete_native_closure",
        "native_item_missing": "missing",
        "dependency_closure_missing": "missing",
        "dependency_closure_unknown": "unknown",
        "tombstone": "tombstone",
        "blocked": "blocked",
        "unknown": "unknown",
        "missing": "missing",
    }
    return mapping.get(str(value), "unknown")


class ClosureResolver:
    BRIDGE_PREFIXES = (
        "skill_effect_application:",
        "buff_effect_application:",
        "plot_event:",
        "plot_event_condition:",
        "plot_event_effect:",
        "fx_group_fx_item:",
        "sound_pack_item:",
    )
    TRAVERSABLE_KINDS = {
        "item", "item_descriptor", "skill", "skill_effect_application",
        "effect", "effect_detail", "buff", "buff_effect_application",
        "plot", "plot_event", "plot_event_condition", "plot_event_effect",
        "projectile", "anim", "animation", "fx", "fx_group", "fx_item",
        "sound", "sound_pack", "sound_pack_item", "icon", "model",
        "asset", "asset_reference", "client_asset", "doodad", "npc",
        "npc_template", "craft", "cinema", "voice",
        "world_interaction", "interaction", "quest_item_group",
        "quest_act_obj_alias", "quest_monster_group", "npc_group",
    }
    ALLOWED_TARGET_KINDS = TRAVERSABLE_KINDS | {
        "sphere", "npc_ai", "npc_spawner", "item_grade", "system_faction",
        "ai_command_set", "ability", "interaction_effect", "doodad_func", "tag",
    }

    def __init__(self, connection: sqlite3.Connection, item_closures: dict[int, dict[str, Any]]) -> None:
        self.connection = connection
        self.item_closures = item_closures
        self._entity: dict[str, dict[str, Any] | None] = {}
        self._state: dict[str, tuple[str, str, str | None]] = {}
        self._outgoing: dict[str, list[dict[str, Any]]] = {}

    @staticmethod
    def kind(key: str) -> str:
        return key.split(":", 1)[0]

    def entity(self, key: str) -> dict[str, Any] | None:
        if key not in self._entity:
            row = self.connection.execute(
                "SELECT * FROM entities WHERE entity_key=?", (key,)
            ).fetchone()
            self._entity[key] = dict(row) if row is not None else None
        return self._entity[key]

    def state(self, key: str, relation_state: str = "confirmed") -> tuple[str, str, str | None]:
        cache_key = f"{key}\0{relation_state}"
        if cache_key in self._state:
            return self._state[cache_key]
        if key.startswith("asset_reference_path:"):
            result = ("unknown", "unknown", "textual_asset_reference_requires_stage60_resolution")
        elif key.startswith("doodad_func_detail:"):
            result = ("opaque", "opaque", "doodad_func_detail_not_decoded")
        elif key.startswith(("doodad_func_group:", "doodad_func:")):
            result = ("confirmed", "complete_native_closure", None)
        elif key.startswith("item:") and key.split(":", 1)[1].isdigit() and int(key.split(":", 1)[1]) in self.item_closures:
            closure = self.item_closures[int(key.split(":", 1)[1])]
            terminal = _normalize_item_closure(str(closure.get("closure_state")))
            blocker_values = json.loads(closure.get("blocker_roots_json") or "[]")
            blocker = next((str(value.get("root_code")) for value in blocker_values if value.get("root_code")), None)
            result = (str(closure.get("native_state", "unknown")), terminal, blocker)
        else:
            entity = self.entity(key)
            if entity is None:
                result = ("missing", "missing", "referenced_entity_absent")
            elif str(entity.get("lifecycle")) == "tombstone" or str(entity.get("state")) == "tombstone":
                result = ("tombstone", "tombstone", "native_tombstone")
            else:
                gaps = list(
                    self.connection.execute(
                        "SELECT state,blocker_code FROM gaps WHERE entity_key=? ORDER BY severity DESC,gap_key",
                        (key,),
                    )
                )
                gap_states = {str(row["state"]) for row in gaps}
                blocker = str(gaps[0]["blocker_code"]) if gaps else None
                if "blocked" in gap_states or str(entity.get("state")) == "blocked":
                    result = (str(entity.get("state")), "blocked", blocker or "native_entity_blocked")
                elif "missing" in gap_states:
                    result = (str(entity.get("state")), "missing", blocker or "native_dependency_missing")
                elif "unknown" in gap_states or str(entity.get("state")) == "unknown":
                    result = (str(entity.get("state")), "unknown", blocker or "native_dependency_unknown")
                elif relation_state not in {"confirmed", "corroborated"}:
                    result = (str(entity.get("state")), "unknown", "relation_state_not_confirmed")
                else:
                    result = (str(entity.get("state")), "complete_native_closure", None)
        self._state[cache_key] = result
        return result

    def outgoing(self, key: str) -> list[dict[str, Any]]:
        if key in self._outgoing:
            return self._outgoing[key]
        rows = [
            dict(row) for row in self.connection.execute(
                "SELECT * FROM relations WHERE src_entity_key=? "
                "AND authority<>'external_corroborative' ORDER BY relation,ordinal,relation_key",
                (key,),
            )
            if self.kind(str(row["dst_entity_key"])) in self.ALLOWED_TARGET_KINDS
            and str(row["relation"]) not in {"belongs_to_quest", "references_component"}
        ]
        if self.kind(key) in {"skill", "buff", "plot", "fx_group", "sound_pack"}:
            for row in self.connection.execute(
                "SELECT * FROM relations WHERE dst_entity_key=? "
                "AND authority<>'external_corroborative' ORDER BY src_entity_key,relation,ordinal,relation_key",
                (key,),
            ):
                source = str(row["src_entity_key"])
                if not source.startswith(self.BRIDGE_PREFIXES):
                    continue
                value = dict(row)
                value["src_entity_key"] = key
                value["dst_entity_key"] = source
                value["relation"] = f"has_{self.kind(source)}"
                value["locator"] = f"inverse_native_relation:{row['relation_key']}"
                value["evidence_json"] = canonical_json(
                    {"derived_direction": True, "source_relation_key": row["relation_key"]}
                )
                rows.append(value)
        rows.sort(key=lambda row: (str(row["relation"]), int(row.get("ordinal", 0)), str(row["dst_entity_key"]), str(row["relation_key"])))
        self._outgoing[key] = rows
        return rows

    def traversable(self, key: str) -> bool:
        return self.kind(key) in self.TRAVERSABLE_KINDS

    def follow(self, source: str, destination: str, depth: int) -> bool:
        destination_kind = self.kind(destination)
        source_kind = self.kind(source)
        # Depth nine is required by the native doodad -> skill -> skill effect
        # application -> effect -> concrete effect -> world interaction chain.
        # The destination at depth nine is recorded but not expanded further.
        if not self.traversable(destination) or depth >= 9:
            return False
        # Dependent recipe/loot/equipment items are recorded as terminal
        # destinations. Only item IDs directly reached from a story act are
        # expanded, preventing a quest from absorbing the global economy.
        if destination_kind == "item" and source_kind not in {"item_descriptor"}:
            return False
        # NPC/doodad roots are expanded when directly seeded; secondary actors
        # remain explicit terminals unless an alias/group owns them.
        if destination_kind in {"npc", "doodad"} and source_kind not in {
            "quest_act_obj_alias", "quest_monster_group", "npc_group"
        }:
            return False
        return True


def _component_act_rows(
    story: dict[str, Any],
    doodads: dict[str, Any],
    crosswalk_grants: dict[tuple[Any, ...], dict[str, Any]],
    resolver: ClosureResolver,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[int, set[str]]]:
    components_by_id = {int(row["row"]["id"]): row for row in story["components"]}
    component_ordinals: dict[int, int] = defaultdict(int)
    component_rows: list[dict[str, Any]] = []
    for source in story["components"]:
        row = source["row"]
        quest_id = int(row["quest_context_id"])
        component_ordinals[quest_id] += 1
        component_rows.append(
            {
                "component_key": stable_key("nuia_story_component", quest_id, row["id"]),
                "quest_id": quest_id,
                "component_id": int(row["id"]),
                "component_kind_id": int(row["component_kind_id"]),
                "ordinal": component_ordinals[quest_id],
                "row_json": canonical_json(row),
                "native_state": source["state"],
                "evidence": {
                    "native_row_key": source["native_row_key"],
                    "source_row_index": _row_index(source),
                },
            }
        )
    act_rows: list[dict[str, Any]] = []
    item_rows: list[dict[str, Any]] = []
    endpoint_rows: list[dict[str, Any]] = []
    quest_seeds: dict[int, set[str]] = defaultdict(set)
    for source in story["acts"]:
        act = source["row"]
        act_id = int(act["id"])
        component_id = int(act["quest_component_id"])
        component = components_by_id[component_id]["row"]
        quest_id = int(component["quest_context_id"])
        detail = story["details"][act_id]
        payload = detail["row"]
        detail_type = str(act["act_detail_type"])
        detail_id = int(act["act_detail_id"])
        act_rows.append(
            {
                "act_key": stable_key("nuia_story_act", quest_id, act_id),
                "quest_id": quest_id,
                "component_id": component_id,
                "quest_act_id": act_id,
                "act_detail_type": detail_type,
                "act_detail_id": detail_id,
                "detail_row_json": canonical_json(payload),
                "closure_state": "complete_native_closure" if detail["state"] == "confirmed" else "unknown",
                "evidence": {
                    "act_native_row_key": source["native_row_key"],
                    "act_source_row_index": _row_index(source),
                    "detail_native_row_key": detail["native_row_key"],
                    "detail_source_table": detail["source_table"],
                    "detail_source_row_index": _row_index(detail),
                },
            }
        )
        endpoint_types = {
            "QuestActConAcceptNpc": ("accept", "npc", "npc_id"),
            "QuestActConReportNpc": ("report", "npc", "npc_id"),
            "QuestActConAcceptDoodad": ("accept", "doodad", "doodad_id"),
            "QuestActConReportDoodad": ("report", "doodad", "doodad_id"),
            "QuestActConAcceptSphere": ("accept", "sphere", "sphere_id"),
        }
        if detail_type in endpoint_types:
            phase, kind, field = endpoint_types[detail_type]
            endpoint_id = int(payload[field])
            entity_key = f"{kind}:{endpoint_id}"
            quest_seeds[quest_id].add(entity_key)
            native_state, closure_state, blocker = resolver.state(entity_key)
            client_doodad = None
            proxy_npc_id = None
            if kind == "doodad":
                almighty = doodads["almighties"].get(endpoint_id)
                if almighty is not None:
                    client_doodad = int(almighty["client_doodad"])
                    proxy_groups = [
                        row for row in doodads["groups"]
                        if int(row["doodad_almighty_id"]) == endpoint_id
                        and re.fullmatch(r"npctype://\d+", str(row.get("model", "")))
                    ]
                    proxy_ids = {int(str(row["model"]).split("//", 1)[1]) for row in proxy_groups}
                    proxy_npc_id = next(iter(proxy_ids)) if len(proxy_ids) == 1 else None
                spawn_state = (
                    "logical_client_doodad_proxy"
                    if client_doodad == 1 and proxy_npc_id is not None
                    else "native_doodad_spawn_not_closed"
                )
            else:
                spawn = resolver.connection.execute(
                    "SELECT COUNT(*) FROM relations WHERE dst_entity_key=? "
                    "AND (relation LIKE '%spawn%' OR src_entity_key LIKE '%spawn%') "
                    "AND state='confirmed'",
                    (entity_key,),
                ).fetchone()[0]
                spawn_state = "confirmed_native_spawn" if int(spawn) else "native_spawn_not_closed"
            endpoint_rows.append(
                {
                    "endpoint_key": stable_key("nuia_story_endpoint", quest_id, act_id, kind, endpoint_id),
                    "quest_id": quest_id,
                    "phase": phase,
                    "endpoint_kind": kind,
                    "endpoint_id": endpoint_id,
                    "act_detail_type": detail_type,
                    "act_detail_id": detail_id,
                    "client_doodad": client_doodad,
                    "proxy_npc_id": proxy_npc_id,
                    "spawn_state": spawn_state,
                    "closure_state": closure_state,
                    "evidence": {
                        "blocker": blocker,
                        "detail_native_row_key": detail["native_row_key"],
                        "native_entity_state": native_state,
                        "proxy_is_not_endpoint_kind_rewrite": True,
                    },
                }
            )
        item_role = None
        selection = "not_applicable"
        if detail_type == "QuestActSupplyItem":
            item_role = "initial_supply" if int(component["component_kind_id"]) == 3 else ("fixed_reward" if int(component["component_kind_id"]) == 8 else "other_native_role")
            selection = "fixed"
        elif detail_type == "QuestActSupplySelectiveItem":
            item_role, selection = "selective_reward", "selective"
        elif detail_type == "QuestActSupplyRankedItem":
            item_role, selection = "ranked_reward", "ranked"
        elif detail_type == "QuestActSupplyResultRankedItem":
            item_role, selection = "result_ranked_reward", "result_ranked"
        elif detail_type == "QuestActObjItemGather":
            item_role, selection = "objective_gather", "objective"
        elif detail_type == "QuestActObjItemUse":
            item_role, selection = "objective_use", "objective"
        elif detail_type == "QuestActConAcceptItem":
            item_role, selection = "accept_requirement", "requirement"
        elif detail_type == "QuestActConAcceptItemGain":
            item_role, selection = "accept_item_gain", "fixed"
        elif detail_type == "QuestActSupplyRemoveItem":
            item_role, selection = "remove_or_cleanup", "fixed"
        elif detail_type == "QuestActEtcItemObtain":
            item_role, selection = "doodad_or_interaction_product", "fixed"
        if item_role and int(payload.get("item_id", 0) or 0) > 0:
            item_id = int(payload["item_id"])
            entity_key = f"item:{item_id}"
            quest_seeds[quest_id].add(entity_key)
            crosswalk_key = (quest_id, component_id, act_id, detail_type, detail_id, item_id)
            linked = crosswalk_grants.get(crosswalk_key)
            _, item_closure, blocker = resolver.state(entity_key)
            flags = {
                key: value for key, value in payload.items()
                if key not in {"id", "item_id", "count", "grade_id", "item_grade_id"}
            }
            item_rows.append(
                {
                    "relation_key": stable_key("nuia_story_item", quest_id, act_id, detail_id, item_id, item_role),
                    "quest_id": quest_id,
                    "component_id": component_id,
                    "quest_act_id": act_id,
                    "item_id": item_id,
                    "item_role": item_role,
                    "selection_mode": selection,
                    "count": payload.get("count"),
                    "grade_id": payload.get("grade_id", payload.get("item_grade_id")),
                    "flags_json": canonical_json(flags),
                    "native_relation_state": "confirmed" if detail["state"] == "confirmed" else detail["state"],
                    "item_closure_state": item_closure,
                    "crosswalk_state": "linked" if linked is not None else ("not_applicable" if selection in {"objective", "requirement"} else "missing"),
                    "evidence": {
                        "blocker": blocker,
                        "crosswalk_grant_key": linked.get("grant_key") if linked else None,
                        "detail_native_row_key": detail["native_row_key"],
                    },
                }
            )
        for field, value in payload.items():
            if not field.endswith("_id") or field in {"id", "item_id"}:
                continue
            try:
                native_id = int(value or 0)
            except (TypeError, ValueError):
                continue
            if native_id <= 0:
                continue
            target = relation_target(detail["source_table"], field)
            if target is not None:
                quest_seeds[quest_id].add(f"{target[1]}:{native_id}")
    component_rows.sort(key=lambda row: row["component_key"])
    act_rows.sort(key=lambda row: row["act_key"])
    item_rows.sort(key=lambda row: row["relation_key"])
    endpoint_rows.sort(key=lambda row: row["endpoint_key"])
    return component_rows, act_rows, endpoint_rows, item_rows, quest_seeds


def _closure_rows(
    story: dict[str, Any],
    doodads: dict[str, Any],
    resolver: ClosureResolver,
    quest_seeds: dict[int, set[str]],
) -> list[dict[str, Any]]:
    components_by_quest: dict[int, list[dict[str, Any]]] = defaultdict(list)
    acts_by_component: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for component in story["components"]:
        components_by_quest[int(component["row"]["quest_context_id"])].append(component)
    for act in story["acts"]:
        acts_by_component[int(act["row"]["quest_component_id"])].append(act)
    group_by_doodad: dict[int, list[dict[str, Any]]] = defaultdict(list)
    funcs_by_group: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for group in doodads["groups"]:
        group_by_doodad[int(group["doodad_almighty_id"])].append(group)
    for func in doodads["funcs"]:
        funcs_by_group[int(func["doodad_func_group_id"])].append(func)
    rows: dict[str, dict[str, Any]] = {}

    def add(
        root: int,
        depth: int,
        src: str,
        relation: str,
        dst: str,
        *,
        relation_state: str = "confirmed",
        required: int = 1,
        evidence: dict[str, Any] | None = None,
        identity: str = "",
        forced_closure: str | None = None,
        forced_dst_state: str | None = None,
        forced_blocker: str | None = None,
    ) -> None:
        native_state, closure, blocker = resolver.state(dst, relation_state)
        key = stable_key("nuia_story_closure", root, src, relation, dst, identity)
        rows[key] = {
            "closure_key": key,
            "root_quest_id": root,
            "depth": depth,
            "src_entity_key": src,
            "relation": relation,
            "dst_entity_key": dst,
            "dst_state": forced_dst_state or native_state,
            "required": int(required),
            "closure_state": forced_closure or closure,
            "blocker_root": forced_blocker if forced_blocker is not None else blocker,
            "evidence": evidence or {},
        }

    for quest_id in sorted(components_by_quest):
        quest_key = f"quest:{quest_id}"
        for component in sorted(components_by_quest[quest_id], key=lambda row: (_row_index(row), int(row["row"]["id"]))):
            component_id = int(component["row"]["id"])
            component_key = f"quest_component:{component_id}"
            add(
                quest_id, 1, quest_key, "has_component", component_key,
                evidence={"native_row_key": component["native_row_key"], "row": component["row"]},
                identity=component["native_row_key"],
            )
            for field, value in component["row"].items():
                if not field.endswith("_id") or field in {"id", "quest_context_id"}:
                    continue
                try:
                    native_id = int(value or 0)
                except (TypeError, ValueError):
                    continue
                if native_id <= 0:
                    continue
                target = relation_target("quest_components", field)
                if target is None:
                    continue
                destination = f"{target[1]}:{native_id}"
                quest_seeds[quest_id].add(destination)
                add(
                    quest_id, 2, component_key, target[0], destination,
                    evidence={"field": field, "native_row_key": component["native_row_key"]},
                    identity=f"{component['native_row_key']}:{field}",
                )
            for act in sorted(acts_by_component[component_id], key=lambda row: (_row_index(row), int(row["row"]["id"]))):
                act_id = int(act["row"]["id"])
                act_key = f"quest_act:{act_id}"
                detail = story["details"][act_id]
                detail_key = f"quest_act_detail:{detail['source_table']}:{act['row']['act_detail_id']}"
                add(
                    quest_id, 2, component_key, "has_act", act_key,
                    evidence={"native_row_key": act["native_row_key"], "row": act["row"]},
                    identity=act["native_row_key"],
                )
                add(
                    quest_id, 3, act_key, "uses_act_detail", detail_key,
                    evidence={"native_row_key": detail["native_row_key"], "row": detail["row"], "source_table": detail["source_table"]},
                    identity=detail["native_row_key"],
                )
                for field, value in detail["row"].items():
                    if not field.endswith("_id") or field == "id":
                        continue
                    try:
                        native_id = int(value or 0)
                    except (TypeError, ValueError):
                        continue
                    if native_id <= 0:
                        continue
                    target = relation_target(detail["source_table"], field)
                    if target is None:
                        continue
                    destination = f"{target[1]}:{native_id}"
                    quest_seeds[quest_id].add(destination)
                    add(
                        quest_id, 4, detail_key, target[0], destination,
                        evidence={"field": field, "native_row_key": detail["native_row_key"]},
                        identity=f"{detail['native_row_key']}:{field}",
                    )
                if str(act["row"]["act_detail_type"]) == "QuestActObjItemGather":
                    item_id = int(detail["row"].get("item_id", 0) or 0)
                    highlighted = int(detail["row"].get("highlight_doodad_id", 0) or 0)
                    if item_id > 0 and highlighted > 0:
                        add(
                            quest_id,
                            4,
                            f"doodad:{highlighted}",
                            "candidate_produces_objective_item",
                            f"item:{item_id}",
                            evidence={
                                "derivation": "quest_objective_item_plus_highlight_doodad",
                                "native_product_edge_demonstrated": False,
                                "native_row_key": detail["native_row_key"],
                            },
                            identity=f"candidate:{detail['native_row_key']}",
                            forced_closure="unknown",
                            forced_dst_state="tombstone" if item_id == 24967 else None,
                            forced_blocker="native_doodad_product_edge_not_demonstrated",
                        )
        for seed in sorted(value for value in quest_seeds[quest_id] if value.startswith("doodad:")):
            doodad_id = int(seed.split(":", 1)[1])
            almighty = doodads["almighties"].get(doodad_id)
            if almighty is None:
                continue
            for group in sorted(group_by_doodad.get(doodad_id, []), key=lambda row: int(row["id"])):
                group_id = int(group["id"])
                group_key = f"doodad_func_group:{group_id}"
                add(
                    quest_id, 5, seed, "has_doodad_func_group", group_key,
                    evidence={"doodad_almighty": almighty, "row": group, "decoder": "game11_cached_result"},
                    identity=f"group:{group_id}",
                )
                model = str(group.get("model", ""))
                if model:
                    match = re.fullmatch(r"npctype://(\d+)", model)
                    if match:
                        destination = f"npc:{int(match.group(1))}"
                        quest_seeds[quest_id].add(destination)
                        add(
                            quest_id, 6, group_key, "uses_npctype_proxy_model", destination,
                            evidence={"model": model, "logical_doodad_remains_endpoint": True},
                            identity=f"model:{model}",
                        )
                    else:
                        destination = f"asset_reference_path:{sha256_text(model)}"
                        add(
                            quest_id, 6, group_key, "uses_model_asset", destination,
                            evidence={"model": model}, identity=f"model:{model}",
                        )
                for func in sorted(funcs_by_group.get(group_id, []), key=lambda row: int(row["id"])):
                    func_id = int(func["id"])
                    func_key = f"doodad_func:{func_id}"
                    add(
                        quest_id, 6, group_key, "has_doodad_func", func_key,
                        evidence={"row": func, "decoder": "game11_cached_result"},
                        identity=f"func:{func_id}",
                    )
                    actual_type = str(func["actual_func_type"])
                    actual_id = int(func["actual_func_id"])
                    if actual_type == "DoodadFuncQuest" and actual_id in doodads["quest_funcs"]:
                        detail = doodads["quest_funcs"][actual_id]
                        destination = f"quest:{int(detail['quest_id'])}"
                        add(
                            quest_id, 7, func_key, "doodad_quest_function", destination,
                            evidence={"row": detail, "actual_func_type": actual_type},
                            identity=f"quest_func:{actual_id}",
                        )
                    elif actual_type == "DoodadFuncLootItem" and actual_id in doodads["loot_funcs"]:
                        detail = doodads["loot_funcs"][actual_id]
                        destination = f"item:{int(detail['item_id'])}"
                        quest_seeds[quest_id].add(destination)
                        add(
                            quest_id, 7, func_key, "doodad_loots_item", destination,
                            evidence={"row": detail, "actual_func_type": actual_type},
                            identity=f"loot_func:{actual_id}",
                        )
                    else:
                        destination = f"doodad_func_detail:{actual_type}:{actual_id}"
                        add(
                            quest_id, 7, func_key, "uses_doodad_func_detail", destination,
                            evidence={"actual_func_type": actual_type, "actual_func_id": actual_id},
                            identity=f"actual:{actual_type}:{actual_id}",
                        )
                    for field, kind in (("func_skill_id", "skill"), ("sound_id", "sound")):
                        value = int(func.get(field, 0) or 0)
                        if value > 0:
                            destination = f"{kind}:{value}"
                            quest_seeds[quest_id].add(destination)
                            add(
                                quest_id, 7, func_key, f"references_{kind}", destination,
                                evidence={"field": field, "row": func},
                                identity=f"{field}:{value}",
                            )
        queue: deque[tuple[str, int]] = deque((seed, 5) for seed in sorted(quest_seeds[quest_id]))
        visited: set[str] = set()
        while queue:
            source_key, depth = queue.popleft()
            if source_key in visited or depth > 9:
                continue
            visited.add(source_key)
            if len(visited) > 5000:
                add(
                    quest_id, depth, quest_key, "closure_truncated", f"opaque:closure_limit:{quest_id}",
                    forced_closure="blocked", forced_dst_state="blocked",
                    forced_blocker="closure_node_limit", evidence={"limit": 5000},
                )
                break
            for relation in resolver.outgoing(source_key):
                destination = str(relation["dst_entity_key"])
                relation_state = str(relation["state"])
                add(
                    quest_id,
                    depth + 1,
                    source_key,
                    str(relation["relation"]),
                    destination,
                    relation_state=relation_state,
                    required=int(relation["required"]),
                    evidence={
                        "authority": relation["authority"],
                        "locator": relation["locator"],
                        "loader_or_consumer": relation["loader_or_consumer"],
                        "native_relation_key": relation["relation_key"],
                        "native_evidence": json.loads(relation["evidence_json"]),
                    },
                    identity=str(relation["relation_key"]),
                )
                if destination not in visited and resolver.follow(source_key, destination, depth + 1):
                    queue.append((destination, depth + 1))
    return [rows[key] for key in sorted(rows)]


def _audit_rows(
    contexts: list[dict[str, Any]],
    closure_rows: list[dict[str, Any]],
    item_rows: list[dict[str, Any]],
    endpoint_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    context_map = {int(row["row"]["id"]): row["row"] for row in contexts}
    item_phase = {
        (int(row["quest_id"]), f"item:{int(row['item_id'])}"): row["item_role"]
        for row in item_rows
    }
    endpoint_phase = {
        (int(row["quest_id"]), f"{row['endpoint_kind']}:{int(row['endpoint_id'])}"): row["phase"]
        for row in endpoint_rows
    }
    rows: dict[str, dict[str, Any]] = {}
    for closure in closure_rows:
        state = str(closure["closure_state"])
        if state in {"complete_native_closure", "not_applicable"}:
            continue
        quest_id = int(closure["root_quest_id"])
        destination = str(closure["dst_entity_key"])
        if endpoint_phase.get((quest_id, destination)) == "accept" or item_phase.get((quest_id, destination)) == "initial_supply":
            stop = "stop_after_acceptance_before_objective"
        elif endpoint_phase.get((quest_id, destination)) == "report" or item_phase.get((quest_id, destination)) in {"fixed_reward", "selective_reward", "ranked_reward", "result_ranked_reward"}:
            stop = "stop_before_report_or_reward_commit"
        else:
            stop = "stop_before_or_during_objective_dependency"
        severity = {
            "blocked": "critical",
            "missing": "high",
            "opaque": "high",
            "tombstone": "high",
            "unknown": "medium",
        }.get(state, "medium")
        context = context_map[quest_id]
        blocker = str(closure.get("blocker_root") or state)
        key = stable_key("nuia_story_audit", quest_id, destination, blocker, stop)
        rows[key] = {
            "audit_key": key,
            "quest_id": quest_id,
            "chapter_idx": int(context["chapter_idx"]),
            "quest_idx": int(context["quest_idx"]),
            "blocker_kind": blocker,
            "blocked_entity_key": destination,
            "severity": severity,
            "recommended_stop_point": stop,
            "state": "open",
            "evidence": {
                "closure_key": closure["closure_key"],
                "closure_state": state,
                "not_runtime_validation": True,
            },
        }
    return [rows[key] for key in sorted(rows)]


def _create_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.executescript(SCHEMA)
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return connection


def _insert_validation(connection: sqlite3.Connection, name: str, passed: bool, expected: Any, actual: Any, evidence: dict[str, Any] | None = None) -> None:
    connection.execute(
        "INSERT INTO validation_events VALUES(?,?,?,?,?,?)",
        (
            stable_key("nuia_story_validation", name),
            name,
            "confirmed" if passed else "blocked",
            None if expected is None else canonical_json(expected),
            canonical_json(actual),
            canonical_json(evidence or {}),
        ),
    )


def _build_validation_events(
    connection: sqlite3.Connection,
    *,
    story: dict[str, Any],
    doodads: dict[str, Any],
    crosswalk_grants: dict[tuple[Any, ...], dict[str, Any]],
    wiki_manifest: dict[str, Any],
) -> None:
    contexts = [row["row"] for row in story["contexts"]]
    actual_ids = tuple(int(row["id"]) for row in contexts)
    _insert_validation(connection, "root_selected_by_category_3_and_race_1", actual_ids == EXPECTED_QUEST_IDS, EXPECTED_QUEST_IDS, actual_ids)
    category = story["category"]["row"]
    _insert_validation(connection, "category_3_native_nuian_race_quest", str(category.get("name")) == CATEGORY_NATIVE_NAME, CATEGORY_NATIVE_NAME, category.get("name"), {"native_row_key": story["category"]["native_row_key"]})
    _insert_validation(connection, "story_quest_count", len(contexts) == 55, 55, len(contexts))
    component_count = int(connection.execute("SELECT COUNT(*) FROM story_quest_components").fetchone()[0])
    act_count = int(connection.execute("SELECT COUNT(*) FROM story_quest_acts").fetchone()[0])
    _insert_validation(connection, "story_component_count", component_count == 222, 222, component_count)
    _insert_validation(connection, "story_act_count", act_count == 344, 344, act_count)
    chapters = dict(Counter(int(row["chapter_idx"]) for row in contexts))
    zones = dict(Counter(int(row["zone_id"]) for row in contexts))
    levels = [int(row["level"]) for row in contexts]
    _insert_validation(connection, "chapter_distribution", chapters == EXPECTED_CHAPTERS, EXPECTED_CHAPTERS, chapters)
    _insert_validation(connection, "zone_distribution", zones == EXPECTED_ZONES, EXPECTED_ZONES, zones)
    _insert_validation(connection, "native_level_range", (min(levels), max(levels)) == (1, 28), [1, 28], [min(levels), max(levels)])
    act_types = dict(connection.execute("SELECT act_detail_type,COUNT(*) FROM story_quest_acts GROUP BY act_detail_type ORDER BY act_detail_type").fetchall())
    _insert_validation(connection, "all_18_act_types_preserved", act_types == EXPECTED_ACT_TYPES, EXPECTED_ACT_TYPES, act_types)
    linked = int(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE crosswalk_state='linked'").fetchone()[0])
    supply_missing = int(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE selection_mode IN ('fixed','selective','ranked','result_ranked') AND crosswalk_state<>'linked'").fetchone()[0])
    _insert_validation(connection, "crosswalk_130_grants_linked", linked == 130 and supply_missing == 0 and len(crosswalk_grants) == 130, {"linked": 130, "missing": 0}, {"linked": linked, "missing": supply_missing, "source_grants": len(crosswalk_grants)})
    gather = int(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE item_role='objective_gather'").fetchone()[0])
    uses = int(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE item_role='objective_use'").fetchone()[0])
    _insert_validation(connection, "objective_item_roles_closed", (gather, uses) == (17, 9), [17, 9], [gather, uses])
    endpoint_count = int(connection.execute("SELECT COUNT(*) FROM story_quest_endpoints").fetchone()[0])
    item_count = int(connection.execute("SELECT COUNT(*) FROM story_quest_items").fetchone()[0])
    _insert_validation(
        connection,
        "zero_components_acts_endpoints_or_items_discarded",
        (component_count, act_count, endpoint_count, item_count) == (222, 344, 108, 156),
        {"components": 222, "acts": 344, "endpoints": 108, "items": 156},
        {"components": component_count, "acts": act_count, "endpoints": endpoint_count, "items": item_count},
    )
    bad_endpoints = int(connection.execute("SELECT COUNT(*) FROM story_quest_endpoints WHERE closure_state NOT IN ('complete_native_closure','tombstone','missing','unknown','opaque','blocked','not_applicable') OR spawn_state='' OR spawn_state IS NULL").fetchone()[0])
    _insert_validation(connection, "every_endpoint_has_closure_and_spawn_state", bad_endpoints == 0, 0, bad_endpoints)
    bad_items = int(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE item_closure_state NOT IN ('complete_native_closure','tombstone','missing','unknown','opaque','blocked','not_applicable')").fetchone()[0])
    _insert_validation(connection, "every_item_has_terminal_closure_state", bad_items == 0, 0, bad_items)
    bad_dependencies = int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE closure_state NOT IN ('complete_native_closure','tombstone','missing','unknown','opaque','blocked','not_applicable')").fetchone()[0])
    _insert_validation(connection, "every_dependency_has_terminal_classification", bad_dependencies == 0, 0, bad_dependencies)
    terminal_pages = int(connection.execute("SELECT COUNT(*) FROM wiki_story_pages WHERE detail_state IN (%s)" % ",".join("?" for _ in TERMINAL_WIKI_STATES), tuple(sorted(TERMINAL_WIKI_STATES))).fetchone()[0])
    _insert_validation(connection, "all_55_wiki_pages_terminal", terminal_pages == 55, 55, terminal_pages)
    reused = sorted(int(value) for value in wiki_manifest.get("reused_ids", []))
    downloaded = sorted(int(value) for value in wiki_manifest.get("downloaded_ids", []))
    _insert_validation(connection, "wiki_54_snapshots_reused_and_6839_frozen", len(reused) == 54 and downloaded == [6839], {"reused": 54, "downloaded": [6839]}, {"reused": len(reused), "downloaded": downloaded})
    reciprocal = int(connection.execute("SELECT COUNT(*) FROM story_order_edges WHERE ordinal_state='same_chapter_neighbor' AND reciprocal_state='reciprocal'").fetchone()[0])
    _insert_validation(connection, "wiki_48_intrachapter_pairs_reciprocal", reciprocal == 48, 48, reciprocal)
    bad_boundaries = int(connection.execute("SELECT COUNT(*) FROM story_order_edges WHERE ordinal_state='chapter_boundary_neighbor' AND overall_state NOT IN ('chapter_boundary_unresolved','corroborated_order')").fetchone()[0])
    boundary_count = int(connection.execute("SELECT COUNT(*) FROM story_order_edges WHERE ordinal_state='chapter_boundary_neighbor'").fetchone()[0])
    _insert_validation(connection, "chapter_boundaries_not_invented", bad_boundaries == 0 and boundary_count == 6, {"boundaries": 6, "invalid": 0}, {"boundaries": boundary_count, "invalid": bad_boundaries})
    candidate_count = int(connection.execute("SELECT COUNT(*) FROM scope_boundary_candidates").fetchone()[0])
    mixed_candidates = int(connection.execute("SELECT COUNT(*) FROM scope_boundary_candidates c JOIN story_quests q USING(quest_id)").fetchone()[0])
    _insert_validation(connection, "external_candidates_inventoried_not_mixed", candidate_count > 0 and mixed_candidates == 0, {"minimum": 1, "mixed": 0}, {"candidates": candidate_count, "mixed": mixed_candidates})
    orphans = {
        "components": int(connection.execute("SELECT COUNT(*) FROM story_quest_components c LEFT JOIN story_quests q USING(quest_id) WHERE q.quest_id IS NULL").fetchone()[0]),
        "acts": int(connection.execute("SELECT COUNT(*) FROM story_quest_acts a LEFT JOIN story_quest_components c ON c.component_id=a.component_id AND c.quest_id=a.quest_id WHERE c.component_key IS NULL").fetchone()[0]),
        "items": int(connection.execute("SELECT COUNT(*) FROM story_quest_items i LEFT JOIN story_quest_acts a ON a.quest_act_id=i.quest_act_id AND a.quest_id=i.quest_id WHERE a.act_key IS NULL").fetchone()[0]),
        "endpoints": int(connection.execute("SELECT COUNT(*) FROM story_quest_endpoints e LEFT JOIN story_quests q USING(quest_id) WHERE q.quest_id IS NULL").fetchone()[0]),
        "closure": int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure c LEFT JOIN story_quests q ON q.quest_id=c.root_quest_id WHERE q.quest_id IS NULL").fetchone()[0]),
    }
    _insert_validation(connection, "zero_unexplained_orphans_and_silent_discards", sum(orphans.values()) == 0 and component_count == len(story["components"]) and act_count == len(story["acts"]), {"orphans": 0, "components": len(story["components"]), "acts": len(story["acts"])}, {"orphans": orphans, "components": component_count, "acts": act_count})
    anchor_2532 = {
        "endpoint": int(connection.execute("SELECT COUNT(*) FROM story_quest_endpoints WHERE quest_id=2532 AND endpoint_kind='doodad' AND endpoint_id=14074 AND act_detail_type='QuestActConReportDoodad' AND act_detail_id=163 AND client_doodad=1 AND proxy_npc_id=10581").fetchone()[0]),
        "group": int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE root_quest_id=2532 AND src_entity_key='doodad:14074' AND dst_entity_key='doodad_func_group:41496'").fetchone()[0]),
        "func": int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE root_quest_id=2532 AND src_entity_key='doodad_func_group:41496' AND dst_entity_key='doodad_func:38378'").fetchone()[0]),
        "quest": int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE root_quest_id=2532 AND src_entity_key='doodad_func:38378' AND relation='doodad_quest_function' AND dst_entity_key='quest:2532'").fetchone()[0]),
    }
    _insert_validation(connection, "anchor_2532_logical_doodad_preserved", all(value == 1 for value in anchor_2532.values()), {"endpoint": 1, "group": 1, "func": 1, "quest": 1}, anchor_2532)
    anchor_2264 = {
        "objective": int(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE quest_id=2264 AND item_id=24967 AND item_role='objective_gather' AND item_closure_state='tombstone' AND json_extract(flags_json,'$.highlight_doodad_id')=14310").fetchone()[0]),
        "product_candidate": int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE root_quest_id=2264 AND src_entity_key='doodad:14310' AND relation='candidate_produces_objective_item' AND dst_entity_key='item:24967' AND closure_state='unknown' AND blocker_root='native_doodad_product_edge_not_demonstrated'").fetchone()[0]),
        "interaction_skill": int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE root_quest_id=2264 AND relation='references_skill' AND dst_entity_key='skill:17310'").fetchone()[0]),
        "interaction_use": int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE root_quest_id=2264 AND dst_entity_key='world_interaction:19'").fetchone()[0]),
        "reward": int(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE quest_id=2264 AND item_role='fixed_reward'").fetchone()[0]),
    }
    _insert_validation(connection, "anchor_2264_object_doodad_product_reward", all(value > 0 for value in anchor_2264.values()), {"all_positive": True}, anchor_2264)
    anchor_2265 = dict(connection.execute("SELECT item_id,COUNT(*) FROM story_quest_items WHERE quest_id=2265 AND item_id IN (21604,23633,34000) GROUP BY item_id ORDER BY item_id").fetchall())
    anchor_2265_counts = dict(connection.execute("SELECT item_id,SUM(count) FROM story_quest_items WHERE quest_id=2265 AND item_id IN (21604,23633,34000) GROUP BY item_id ORDER BY item_id").fetchall())
    skill_chain = int(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE root_quest_id=2265 AND src_entity_key='item:34000' AND dst_entity_key='skill:35238'").fetchone()[0])
    _insert_validation(connection, "anchor_2265_items_and_skill_chain", anchor_2265 == {21604: 1, 23633: 1, 34000: 1} and anchor_2265_counts == {21604: 1, 23633: 1, 34000: 5} and skill_chain == 1, {"rows": {21604: 1, 23633: 1, 34000: 1}, "counts": {21604: 1, 23633: 1, 34000: 5}, "skill_chain": 1}, {"rows": anchor_2265, "counts": anchor_2265_counts, "skill_chain": skill_chain})
    anchor_2258 = dict(connection.execute("SELECT dst_id,relation FROM wiki_story_relations WHERE quest_id=2258 AND dst_kind='item' AND dst_id IN (16288,23633) ORDER BY dst_id").fetchall())
    _insert_validation(connection, "anchor_2258_wiki_parser_roles", anchor_2258 == {16288: "quest_item", 23633: "fixed_reward"}, {16288: "quest_item", 23633: "fixed_reward"}, anchor_2258)
    modes_330 = dict(connection.execute("SELECT selection_mode,COUNT(*) FROM story_quest_items WHERE quest_id=330 GROUP BY selection_mode ORDER BY selection_mode").fetchall())
    _insert_validation(connection, "anchor_330_reward_multiplicity", modes_330.get("fixed", 0) > 0 and modes_330.get("selective", 0) > 0, {"fixed": ">0", "selective": ">0"}, modes_330)
    loot_anchor = doodads["loot_catalog_anchor_2482"]
    _insert_validation(connection, "doodad_decoder_native_anchors", doodads["decoder_evidence"]["doodad_func_loot_items"]["rows"] == 2041 and loot_anchor is not None and int(loot_anchor["item_id"]) == 24967, {"loot_rows": 2041, "detail_2482_item": 24967}, {"loot_rows": doodads["decoder_evidence"]["doodad_func_loot_items"]["rows"], "detail_2482": loot_anchor})
    _insert_validation(connection, "closed_vocabularies", not set(dict(connection.execute("SELECT DISTINCT overall_state,1 FROM story_order_edges")).keys()) - ORDER_STATES and not set(dict(connection.execute("SELECT DISTINCT closure_state,1 FROM story_dependency_closure")).keys()) - CLOSURE_STATES, {"order": sorted(ORDER_STATES), "closure": sorted(CLOSURE_STATES)}, {"order": sorted(dict(connection.execute("SELECT DISTINCT overall_state,1 FROM story_order_edges")).keys()), "closure": sorted(dict(connection.execute("SELECT DISTINCT closure_state,1 FROM story_dependency_closure")).keys())})


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _write_viewer(path: Path, data: dict[str, Any]) -> None:
    payload = canonical_json(data).replace("</script", "<\\/script")
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>AA8 Nuian Story Quest Graph V1</title>
<style>body{{margin:0;background:#0b1220;color:#e5edf7;font:14px system-ui}}header{{padding:18px 24px;background:#111b2e;position:sticky;top:0;z-index:3}}h1{{margin:0 0 8px;font-size:22px}}main{{padding:18px 24px}}.filters{{display:grid;grid-template-columns:repeat(6,minmax(120px,1fr));gap:8px}}input,select{{background:#17233a;color:#fff;border:1px solid #3b4d69;padding:7px}}.cards{{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}}.card{{background:#142038;border:1px solid #273a59;border-radius:7px;padding:9px 12px}}table{{border-collapse:collapse;width:100%;margin:12px 0}}th,td{{padding:6px;border-bottom:1px solid #263750;text-align:left;vertical-align:top}}th{{background:#0b1220;position:sticky;top:106px}}.confirmed_native_dependency{{color:#6ee7b7}}.corroborated_order{{color:#93c5fd}}.native_ordinal_candidate{{color:#fcd34d}}.chapter_boundary_unresolved,.bad{{color:#fca5a5}}details{{background:#101a2d;border:1px solid #263750;border-radius:6px;margin:8px 0;padding:7px}}code{{white-space:pre-wrap;word-break:break-word}}.graph{{display:flex;gap:5px;overflow:auto;padding:10px 0}}.node{{white-space:nowrap;background:#17233a;border:1px solid #3b4d69;border-radius:5px;padding:6px}}.arrow{{padding:6px 0}}</style></head><body>
<header><h1>AA8 Nuian Story Quest Graph V1</h1><div class="filters"><input id="quest" placeholder="quest id/name"><select id="chapter"><option value="">chapter</option></select><select id="zone"><option value="">zone</option></select><select id="level"><option value="">level</option></select><select id="act"><option value="">act type</option></select><select id="closure"><option value="">closure state</option></select></div></header>
<main><div id="cards" class="cards"></div><h2>Editorial/native + wiki order</h2><div id="graph" class="graph"></div><table><thead><tr><th>Chapter/Idx</th><th>Quest</th><th>Zone/Lvl</th><th>Acts</th><th>Endpoints</th><th>Items</th><th>Blockers</th></tr></thead><tbody id="rows"></tbody></table><h2>Chapter boundaries and edge evidence</h2><div id="edges"></div></main>
<script id="data" type="application/json">{payload}</script><script>
const D=JSON.parse(document.getElementById('data').textContent), ids=['chapter','zone','level','act','closure'];
for(const id of ids){{const e=document.getElementById(id), vals=[...new Set(D.quests.flatMap(q=>id==='act'?q.acts:id==='closure'?q.closures:[q[id]]).filter(v=>v!==null&&v!==''))].sort((a,b)=>String(a).localeCompare(String(b),undefined,{{numeric:true}}));for(const v of vals){{let o=document.createElement('option');o.value=v;o.textContent=v;e.append(o)}}e.onchange=render}}quest.oninput=render;
cards.innerHTML=Object.entries(D.summary).map(([k,v])=>`<div class="card"><b>${{k}}</b><br>${{typeof v==='object'?JSON.stringify(v):v}}</div>`).join('');
edges.innerHTML=D.edges.map(e=>`<details><summary class="${{e.overall_state}}">${{e.src_quest_id}} → ${{e.dst_quest_id}} · ${{e.overall_state}}</summary><code>${{JSON.stringify(e,null,2)}}</code></details>`).join('');
function render(){{const text=quest.value.toLowerCase().trim();const selected=Object.fromEntries(ids.map(id=>[id,document.getElementById(id).value]));const qs=D.quests.filter(q=>(!text||String(q.quest_id).includes(text)||(q.visible_name||'').toLowerCase().includes(text))&&(!selected.chapter||String(q.chapter)===selected.chapter)&&(!selected.zone||String(q.zone)===selected.zone)&&(!selected.level||String(q.level)===selected.level)&&(!selected.act||q.acts.includes(selected.act))&&(!selected.closure||q.closures.includes(selected.closure)));graph.innerHTML=qs.map((q,i)=>`${{i?'<span class="arrow">→</span>':''}}<span class="node">${{q.chapter}}.${{q.idx}} #${{q.quest_id}}</span>`).join('');rows.innerHTML=qs.map(q=>`<tr><td>${{q.chapter}}.${{q.idx}}</td><td><b>${{q.quest_id}}</b><br>${{q.visible_name||q.native_name||''}}</td><td>${{q.zone}} / ${{q.level}}</td><td>${{q.acts.join('<br>')}}</td><td><details><summary>${{q.endpoints.length}}</summary><code>${{JSON.stringify(q.endpoints,null,2)}}</code></details></td><td><details><summary>${{q.items.length}}</summary><code>${{JSON.stringify(q.items,null,2)}}</code></details></td><td class="${{q.blockers.length?'bad':''}}"><details><summary>${{q.blockers.length}}</summary><code>${{JSON.stringify(q.blockers,null,2)}}</code></details></td></tr>`).join('')}}render();
</script></body></html>"""
    atomic_text(path, html)


def _export_outputs(config: ForensicsConfig, database: Path) -> dict[str, Any]:
    paths = story_paths(config)
    connection = _open_read_only(database)
    try:
        tables = (
            "story_quests", "scope_boundary_candidates", "story_order_edges",
            "story_quest_components", "story_quest_acts", "story_quest_endpoints",
            "story_quest_items", "story_dependency_closure", "wiki_story_pages",
            "wiki_story_edges", "wiki_story_relations", "downstream_audit_queue",
        )
        table_counts = {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
        summary = {
            "act_types": dict(connection.execute("SELECT act_detail_type,COUNT(*) FROM story_quest_acts GROUP BY act_detail_type ORDER BY act_detail_type").fetchall()),
            "closure_states": dict(connection.execute("SELECT closure_state,COUNT(*) FROM story_dependency_closure GROUP BY closure_state ORDER BY closure_state").fetchall()),
            "edge_states": dict(connection.execute("SELECT overall_state,COUNT(*) FROM story_order_edges GROUP BY overall_state ORDER BY overall_state").fetchall()),
            "item_roles": dict(connection.execute("SELECT item_role,COUNT(*) FROM story_quest_items GROUP BY item_role ORDER BY item_role").fetchall()),
            "schema_version": SCHEMA_VERSION,
            "table_counts": table_counts,
            "tool_version": TOOL_VERSION,
            "wiki_states": dict(connection.execute("SELECT detail_state,COUNT(*) FROM wiki_story_pages GROUP BY detail_state ORDER BY detail_state").fetchall()),
        }
        atomic_text(paths["summary"], canonical_json(summary, pretty=True))
        gaps = [dict(row) for row in connection.execute("SELECT quest_id,chapter_idx,quest_idx,severity,blocker_kind,blocked_entity_key,recommended_stop_point,state,evidence_json FROM downstream_audit_queue ORDER BY chapter_idx,quest_idx,CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,audit_key")]
        _write_csv(paths["gaps"], ("quest_id","chapter_idx","quest_idx","severity","blocker_kind","blocked_entity_key","recommended_stop_point","state","evidence_json"), gaps)
        test_rows = []
        for quest in connection.execute("SELECT * FROM story_quests ORDER BY chapter_idx,quest_idx,quest_id"):
            blockers = [dict(row) for row in connection.execute("SELECT severity,blocker_kind,blocked_entity_key,recommended_stop_point FROM downstream_audit_queue WHERE quest_id=? ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,audit_key", (quest["quest_id"],))]
            first = blockers[0] if blockers else {}
            test_rows.append({
                "chapter_idx": quest["chapter_idx"], "quest_idx": quest["quest_idx"],
                "quest_id": quest["quest_id"], "visible_name": quest["visible_name"] or "",
                "blocker_count": len(blockers), "first_severity": first.get("severity", "none"),
                "first_blocker": first.get("blocker_kind", ""),
                "blocked_entity_key": first.get("blocked_entity_key", ""),
                "recommended_stop_point": first.get("recommended_stop_point", "proceed_with_forensic_audit_only"),
                "runtime_state": "not_assessed",
            })
        _write_csv(paths["test_order"], ("chapter_idx","quest_idx","quest_id","visible_name","blocker_count","first_severity","first_blocker","blocked_entity_key","recommended_stop_point","runtime_state"), test_rows)
        viewer_quests = []
        for quest in connection.execute("SELECT * FROM story_quests ORDER BY chapter_idx,quest_idx,quest_id"):
            quest_id = int(quest["quest_id"])
            acts = [str(row[0]) for row in connection.execute("SELECT DISTINCT act_detail_type FROM story_quest_acts WHERE quest_id=? ORDER BY act_detail_type", (quest_id,))]
            endpoints = [dict(row) for row in connection.execute("SELECT phase,endpoint_kind,endpoint_id,client_doodad,proxy_npc_id,spawn_state,closure_state FROM story_quest_endpoints WHERE quest_id=? ORDER BY endpoint_key", (quest_id,))]
            items = [dict(row) for row in connection.execute("SELECT item_id,item_role,selection_mode,count,grade_id,item_closure_state,crosswalk_state FROM story_quest_items WHERE quest_id=? ORDER BY relation_key", (quest_id,))]
            blockers = [dict(row) for row in connection.execute("SELECT severity,blocker_kind,blocked_entity_key,recommended_stop_point FROM downstream_audit_queue WHERE quest_id=? ORDER BY audit_key", (quest_id,))]
            closures = sorted({str(row[0]) for row in connection.execute("SELECT DISTINCT closure_state FROM story_dependency_closure WHERE root_quest_id=?", (quest_id,))})
            viewer_quests.append({"quest_id": quest_id, "chapter": quest["chapter_idx"], "idx": quest["quest_idx"], "zone": quest["zone_id"], "level": quest["level"], "native_name": quest["native_name"], "visible_name": quest["visible_name"], "acts": acts, "endpoints": endpoints, "items": items, "blockers": blockers, "closures": closures})
        edges = [{**dict(row), "evidence_json": json.loads(row["evidence_json"])} for row in connection.execute("SELECT * FROM story_order_edges ORDER BY src_quest_id,dst_quest_id,edge_key")]
        _write_viewer(paths["viewer"], {"summary": {"quests": table_counts["story_quests"], "components": table_counts["story_quest_components"], "acts": table_counts["story_quest_acts"], "dependencies": table_counts["story_dependency_closure"], "blockers": table_counts["downstream_audit_queue"]}, "quests": viewer_quests, "edges": edges})
        return summary
    finally:
        connection.close()


def build_nuia_story_quest_graph(config: ForensicsConfig) -> dict[str, Any]:
    paths = story_paths(config)
    if not paths["wiki_manifest"].is_file():
        raise FileNotFoundError(f"Freeze Nuian story wiki first: {paths['wiki_manifest']}")
    story = _native_story(config)
    doodads = _doodad_native_closure(config, story)
    crosswalk_path, crosswalk_grants, item_closures = _crosswalk(config)
    wiki_manifest = json.loads(paths["wiki_manifest"].read_text(encoding="utf-8"))
    wiki_pages, wiki_edges, wiki_relations, visible_names = _load_story_wiki(config)
    order_edges = _order_edges(story["contexts"], wiki_edges)
    scope_candidates = _scope_candidates(story, wiki_edges)
    consolidated = _open_read_only(config.consolidated)
    resolver = ClosureResolver(consolidated, item_closures)
    try:
        component_rows, act_rows, endpoint_rows, item_rows, quest_seeds = _component_act_rows(
            story, doodads, crosswalk_grants, resolver
        )
        closure_rows = _closure_rows(story, doodads, resolver, quest_seeds)
    finally:
        consolidated.close()
    audit_rows = _audit_rows(story["contexts"], closure_rows, item_rows, endpoint_rows)
    source_paths = {
        "stage_20_items": config.stage_20,
        "stage_30_world_actors": config.stage_30,
        "stage_40_quests": config.stage_40,
        "stage_50_skills": config.stage_50,
        "stage_60_assets": config.stage_60,
        "stage_70_wiki": config.stage_70,
        "stage_90_coverage_closure": config.stage_90,
        "consolidated": config.consolidated,
        "quest_item_crosswalk": crosswalk_path,
        "game11_cached_results": config.source_game11,
        "nuia_story_wiki_manifest": paths["wiki_manifest"],
        "builder": Path(__file__).resolve(),
    }
    for path in source_paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hashes = {role: sha256_file(path) for role, path in source_paths.items()}
    paths["database"].parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{paths['database'].stem}.", suffix=".sqlite3", dir=paths["database"].parent)
    os.close(descriptor)
    temporary = Path(name)
    temporary.unlink(missing_ok=True)
    connection: sqlite3.Connection | None = None
    try:
        connection = _create_database(temporary)
        metadata = {
            "authority_order": ["stage40_native", "stage20_stage30_stage50_stage60_consolidated", "stage70_wiki_corroboration"],
            "category_root": {"category_id": CATEGORY_ID, "race": RACE_ID, "native_name": story["category"]["row"]["name"]},
            "client_build": config.client_build,
            "closure_policy": {"unknown_is_preserved": True, "wiki_can_create_native_relation": False, "runtime_ready_is_forbidden": True},
            "doodad_decoder_evidence": doodads["decoder_evidence"],
            "order_derivation": "adjacent_rows_sorted_by_chapter_idx_quest_idx_id_v1",
            "parser_version": PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        }
        connection.executemany(
            "INSERT INTO metadata VALUES(?,?)",
            [(key, canonical_json(value)) for key, value in sorted(metadata.items())],
        )
        for role, path in sorted(source_paths.items()):
            if role.startswith("stage_") and role != "stage_70_wiki" or role == "game11_cached_results":
                authority = "client_native"
            elif role in {"stage_70_wiki", "nuia_story_wiki_manifest"}:
                authority = "external_corroborative"
            else:
                authority = "derived_forensic"
            connection.execute(
                "INSERT INTO source_artifacts VALUES(?,?,?,?,?,?,?,?)",
                (
                    stable_key("nuia_story_source", role), role,
                    path.resolve().as_posix(), path.stat().st_size,
                    source_hashes[role], authority, TOOL_NAME,
                    canonical_json({"read_only": role != "builder", "recalculated_sha256": True}),
                ),
            )
        story_quests = []
        for source in story["contexts"]:
            row = source["row"]
            quest_id = int(row["id"])
            story_quests.append(
                {
                    "quest_id": quest_id,
                    "category_id": int(row["category_id"]),
                    "race": int(row["race"]),
                    "chapter_idx": int(row["chapter_idx"]),
                    "quest_idx": int(row["quest_idx"]),
                    "zone_id": int(row["zone_id"]),
                    "level": int(row["level"]),
                    "native_name": row.get("name"),
                    "visible_name": visible_names.get(quest_id),
                    "membership_state": "confirmed_native_nuian_story",
                    "native_state": source["state"],
                    "provenance": "stage40.native_rows.quest_contexts",
                    "evidence_json": canonical_json({"native_row": row, "native_row_key": source["native_row_key"], "source_row_index": _row_index(source), "membership_predicate": {"category_id": CATEGORY_ID, "race": RACE_ID}}),
                }
            )
        connection.executemany(
            "INSERT INTO story_quests VALUES(:quest_id,:category_id,:race,:chapter_idx,:quest_idx,:zone_id,:level,:native_name,:visible_name,:membership_state,:native_state,:provenance,:evidence_json)",
            story_quests,
        )
        connection.executemany(
            "INSERT INTO scope_boundary_candidates VALUES(:candidate_key,:quest_id,:direction,:reason,:state,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in scope_candidates],
        )
        connection.executemany(
            "INSERT INTO story_order_edges VALUES(:edge_key,:src_quest_id,:dst_quest_id,:edge_kind,:native_edge_state,:ordinal_state,:wiki_requires_state,:wiki_opens_state,:reciprocal_state,:overall_state,:provenance,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in order_edges],
        )
        connection.executemany(
            "INSERT INTO story_quest_components VALUES(:component_key,:quest_id,:component_id,:component_kind_id,:ordinal,:row_json,:native_state,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in component_rows],
        )
        connection.executemany(
            "INSERT INTO story_quest_acts VALUES(:act_key,:quest_id,:component_id,:quest_act_id,:act_detail_type,:act_detail_id,:detail_row_json,:closure_state,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in act_rows],
        )
        connection.executemany(
            "INSERT INTO story_quest_endpoints VALUES(:endpoint_key,:quest_id,:phase,:endpoint_kind,:endpoint_id,:act_detail_type,:act_detail_id,:client_doodad,:proxy_npc_id,:spawn_state,:closure_state,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in endpoint_rows],
        )
        connection.executemany(
            "INSERT INTO story_quest_items VALUES(:relation_key,:quest_id,:component_id,:quest_act_id,:item_id,:item_role,:selection_mode,:count,:grade_id,:flags_json,:native_relation_state,:item_closure_state,:crosswalk_state,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in item_rows],
        )
        connection.executemany(
            "INSERT INTO story_dependency_closure VALUES(:closure_key,:root_quest_id,:depth,:src_entity_key,:relation,:dst_entity_key,:dst_state,:required,:closure_state,:blocker_root,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in closure_rows],
        )
        connection.executemany(
            "INSERT INTO wiki_story_pages VALUES(:quest_id,:url,:status_code,:response_sha256,:detail_state,:parser_version,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in wiki_pages],
        )
        connection.executemany(
            "INSERT INTO wiki_story_edges VALUES(:wiki_edge_key,:src_quest_id,:relation,:dst_quest_id,:ordinal,:label,:href,:response_sha256,:parse_state,:context_json,:evidence_json)",
            [{**row, "context_json": canonical_json(row["context"]), "evidence_json": canonical_json(row["evidence"])} for row in wiki_edges],
        )
        connection.executemany(
            "INSERT INTO wiki_story_relations VALUES(:wiki_relation_key,:quest_id,:relation,:dst_kind,:dst_id,:ordinal,:label,:href,:response_sha256,:context_json,:evidence_json)",
            [{**row, "context_json": canonical_json(row["context"]), "evidence_json": canonical_json(row["evidence"])} for row in wiki_relations],
        )
        connection.executemany(
            "INSERT INTO downstream_audit_queue VALUES(:audit_key,:quest_id,:chapter_idx,:quest_idx,:blocker_kind,:blocked_entity_key,:severity,:recommended_stop_point,:state,:evidence_json)",
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in audit_rows],
        )
        _build_validation_events(
            connection,
            story=story,
            doodads=doodads,
            crosswalk_grants=crosswalk_grants,
            wiki_manifest=wiki_manifest,
        )
        connection.commit()
        connection.execute("VACUUM")
        connection.close()
        connection = None
        temporary.replace(paths["database"])
    except Exception:
        if connection is not None:
            connection.close()
        temporary.unlink(missing_ok=True)
        raise
    summary = _export_outputs(config, paths["database"])
    output_hashes = {
        key: {"path": path.resolve().as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for key, path in paths.items()
        if key not in {"manifest", "wiki_manifest"} and path.is_file()
    }
    manifest = {
        "authority": "client_forensics_only",
        "client_build": config.client_build,
        "commands": [
            "python -B -m client_forensics freeze-nuia-story-wiki --resume",
            "python -B -m client_forensics build-nuia-story-quest-graph",
            "python -B -m client_forensics validate-nuia-story-quest-graph",
        ],
        "determinism": {"atomic_output": True, "stable_ordering": True, "timestamps_in_reproducible_outputs": False},
        "inputs": {
            role: {"path": path.resolve().as_posix(), "bytes": path.stat().st_size, "sha256": source_hashes[role]}
            for role, path in sorted(source_paths.items())
        },
        "outputs": output_hashes,
        "parser_version": PARSER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }
    atomic_text(paths["manifest"], canonical_json(manifest, pretty=True))
    return {"database": paths["database"], "database_sha256": output_hashes["database"]["sha256"], "manifest": paths["manifest"], "summary": summary}


def validate_nuia_story_quest_graph(config: ForensicsConfig) -> dict[str, Any]:
    paths = story_paths(config)
    for key, path in paths.items():
        if key != "wiki_manifest" and not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    connection = _open_read_only(paths["database"])
    try:
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        failures = [dict(row) for row in connection.execute("SELECT check_name,state,expected_json,actual_json FROM validation_events WHERE state<>'confirmed' ORDER BY check_name")]
        checks = {"quick_check": quick, "integrity_check": integrity, "failed_validation_events": failures}
        if quick != "ok" or integrity != "ok" or failures:
            raise RuntimeError(f"Nuian story quest graph validation failed: {checks}")
        for key, record in manifest["outputs"].items():
            actual = sha256_file(paths[key])
            if actual != str(record["sha256"]).upper():
                raise RuntimeError(f"Output hash mismatch for {key}: {actual}")
        return {
            "checks": checks,
            "database": paths["database"],
            "database_sha256": sha256_file(paths["database"]),
            "manifest": paths["manifest"],
            "manifest_sha256": sha256_file(paths["manifest"]),
            "status": "confirmed",
        }
    finally:
        connection.close()
