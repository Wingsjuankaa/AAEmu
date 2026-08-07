from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from . import TOOL_NAME, TOOL_VERSION
from .config import ForensicsConfig
from .nuia_story_graph import (
    CLOSURE_STATES,
    EXPECTED_QUEST_IDS as V1_QUEST_IDS,
    ClosureResolver,
    WikiQuestEdge,
    _DomParser,
    _Node,
    _atomic_bytes,
    _audit_rows,
    _clean,
    _component_act_rows,
    _create_database,
    _doodad_native_closure,
    _insert_validation,
    _load_native_rows,
    _node_context,
    _open_read_only,
    _read_snapshot_metadata,
    _row_index,
    _snapshot_paths,
    _snapshot_valid,
    _story_relation_hint,
    _walk,
    _write_csv,
    _write_snapshot,
    parse_story_page,
    quest_item_cache,
    _closure_rows,
)
from .quest_item_crosswalk import MINIMUM_DELAY, QuestWikiClient
from .quests import act_detail_table
from .util import atomic_text, canonical_json, sha256_file, sha256_text, stable_key


SCHEMA_VERSION = 2
PARSER_VERSION = "nuia-story-structured-v2"
RACE_MASK_NUIA = 1
STORY_CATEGORIES = (3, 131, 180, 183, 200, 206, 208, 210)
EXPECTED_CATEGORY_COUNTS = {3: 55, 131: 75, 180: 26, 183: 29, 200: 57, 206: 6, 208: 9, 210: 37}
EXPECTED_QUEST_COUNT = 294
BRIDGES = (
    (4411, 7115, "wiki_stage_requirement_and_shared_actor"),
    (8558, 9009, "wiki_stage_requirement_and_shared_actor"),
    (10303, 10361, "wiki_actor_name_category_transition"),
    (10369, 10646, "native_editorial_category_transition"),
)

EXTRA_SCHEMA = """
CREATE TABLE story_wiki_edge_resolutions (
    resolution_key TEXT PRIMARY KEY,
    src_quest_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    raw_dst_quest_id INTEGER NOT NULL,
    resolved_dst_quest_id INTEGER,
    label TEXT,
    resolution_state TEXT NOT NULL,
    candidate_ids_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE story_transition_gates (
    gate_key TEXT PRIMARY KEY,
    src_quest_id INTEGER NOT NULL,
    dst_quest_id INTEGER NOT NULL,
    gate_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE story_terminal_audits (
    audit_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;
CREATE INDEX idx_story_resolution_src ON story_wiki_edge_resolutions(src_quest_id,relation);
CREATE INDEX idx_story_transition_src ON story_transition_gates(src_quest_id,dst_quest_id);
CREATE INDEX idx_story_terminal_quest ON story_terminal_audits(quest_id,dimension);
"""


def story_v2_paths(config: ForensicsConfig) -> dict[str, Path]:
    stem = config.output_dir / "nuia-story-quest-graph-v2"
    return {
        "database": stem.with_suffix(".sqlite3"),
        "manifest": stem.with_suffix(".manifest.json"),
        "summary": stem.with_name(stem.name + "-summary.json"),
        "gaps": stem.with_name(stem.name + "-gaps.csv"),
        "test_order": config.output_dir / "nuia-story-quest-test-order-v2.csv",
        "viewer": stem.with_suffix(".html"),
        "wiki_manifest": stem.with_name(stem.name + "-wiki-snapshot-manifest.json"),
    }


def _race_compatible(race: int) -> bool:
    return race == 255 or bool(race & RACE_MASK_NUIA)


def _selected_context(row: dict[str, Any]) -> bool:
    category = int(row.get("category_id", 0))
    chapter = int(row.get("chapter_idx", 0))
    race = int(row.get("race", 0))
    if category == 3:
        return race == 1
    return category in STORY_CATEGORIES and chapter > 0 and _race_compatible(race)


def _native_story_v2(config: ForensicsConfig) -> dict[str, Any]:
    connection = _open_read_only(config.stage_40)
    try:
        contexts_all = _load_native_rows(connection, "quest_contexts")
        categories_all = _load_native_rows(connection, "quest_categories")
        components_all = _load_native_rows(connection, "quest_components")
        acts_all = _load_native_rows(connection, "quest_acts")
        contexts = [source for source in contexts_all if _selected_context(source["row"])]
        contexts.sort(key=lambda source: (int(source["row"]["chapter_idx"]), int(source["row"]["quest_idx"]), int(source["row"]["id"])))
        quest_ids = {int(source["row"]["id"]) for source in contexts}
        components = [source for source in components_all if int(source["row"].get("quest_context_id", 0)) in quest_ids]
        components.sort(key=lambda source: (_row_index(source), int(source["row"]["id"])))
        component_ids = {int(source["row"]["id"]) for source in components}
        acts = [source for source in acts_all if int(source["row"].get("quest_component_id", 0)) in component_ids]
        acts.sort(key=lambda source: (_row_index(source), int(source["row"]["id"])))
        detail_tables = sorted({act_detail_table(str(source["row"]["act_detail_type"])) for source in acts})
        detail_sources = {
            table: {int(source["row"]["id"]): source for source in _load_native_rows(connection, table)}
            for table in detail_tables
        }
        details: dict[int, dict[str, Any]] = {}
        missing: list[str] = []
        for act in acts:
            table = act_detail_table(str(act["row"]["act_detail_type"]))
            detail_id = int(act["row"]["act_detail_id"])
            detail = detail_sources.get(table, {}).get(detail_id)
            if detail is None:
                missing.append(f"{table}:{detail_id}")
            else:
                details[int(act["row"]["id"])] = {**detail, "source_table": table}
        categories = {int(source["row"]["id"]): source for source in categories_all if int(source["row"]["id"]) in STORY_CATEGORIES}
    finally:
        connection.close()
    if missing:
        raise RuntimeError(f"V2 story act details missing: {sorted(missing)}")
    return {
        "stage40_path": config.stage_40.resolve().as_posix(),
        "categories": categories,
        "category": categories[3],
        "contexts": contexts,
        "contexts_all": contexts_all,
        "components": components,
        "components_all": components_all,
        "acts": acts,
        "acts_all": acts_all,
        "details": details,
        "group_tables": {},
    }


def expected_quest_ids(config: ForensicsConfig) -> tuple[int, ...]:
    return tuple(int(source["row"]["id"]) for source in _native_story_v2(config)["contexts"])


def _ancestor_texts(node: _Node) -> list[str]:
    values: list[str] = []
    current = node.parent
    for _ in range(10):
        if current is None:
            break
        value = current.text()
        if value and value not in values:
            values.append(value)
        current = current.parent
    return values


def parse_story_page_v2(payload: bytes, *, quest_id: int, locale: str = "na-en"):
    base = parse_story_page(payload, quest_id=quest_id, locale=locale)
    dom = _DomParser()
    dom.feed(payload.decode("utf-8", errors="replace"))
    edges = list(base.edges)
    seen = {(edge.relation, edge.dst_quest_id, edge.href) for edge in edges}
    ordinal = Counter(edge.relation for edge in edges)
    quest_link = re.compile(rf"^/{re.escape(locale)}/db/quests/(?P<id>\d+)(?:[/?#].*)?$")
    for node in _walk(dom.root):
        if node.tag != "a":
            continue
        href = node.attrs.get("href", "")
        match = quest_link.match(href)
        if match is None:
            continue
        # The page root also contains the phrase in unrelated stage blocks.  Only
        # the anchor's nearest structured block may classify the anchor itself.
        completed = _node_context(node)
        if "completed the quest" not in completed.casefold():
            completed = None
        if completed is None:
            continue
        destination = int(match.group("id"))
        identity = ("requires_precompleted_quest", destination, href)
        if identity in seen:
            continue
        seen.add(identity)
        ordinal[identity[0]] += 1
        edges.append(WikiQuestEdge(identity[0], destination, ordinal[identity[0]], node.text(), href, completed))
    return type(base)(base.name, base.parse_state, tuple(edges), base.relations)


def _wiki_manifest(config: ForensicsConfig, ids: tuple[int, ...], reused: list[int], downloaded: list[int]) -> dict[str, Any]:
    cache = quest_item_cache(config)
    records = []
    for quest_id in ids:
        html_path, metadata_path = _snapshot_paths(cache, quest_id)
        if not metadata_path.is_file():
            records.append({"quest_id": quest_id, "state": "not_requested"})
            continue
        metadata = _read_snapshot_metadata(metadata_path)
        records.append({
            "quest_id": quest_id,
            "status_code": metadata.get("status_code"),
            "page_state": metadata.get("page_state"),
            "content_bytes": metadata.get("content_bytes"),
            "content_sha256": metadata.get("content_sha256"),
            "url": metadata.get("url"),
            "final_url": metadata.get("final_url"),
            "metadata_sha256": sha256_file(metadata_path),
            "html_valid": bool(html_path.is_file() and _snapshot_valid(cache, quest_id)),
        })
    result = {
        "authority": "external_corroborative",
        "client_build": config.client_build,
        "expected_quests": len(ids),
        "parser_version": PARSER_VERSION,
        "records": records,
        "reused_ids": sorted(reused),
        "downloaded_ids": sorted(downloaded),
        "record_digest": sha256_text(canonical_json(records)),
        "schema_version": 2,
    }
    atomic_text(story_v2_paths(config)["wiki_manifest"], canonical_json(result, pretty=True))
    return result


def freeze_nuia_story_wiki_v2(config: ForensicsConfig, *, resume: bool = True, delay: float = MINIMUM_DELAY, progress: Callable[[str], None] | None = None, fetcher: Callable[[str], tuple[Any, ...]] | None = None) -> dict[str, Any]:
    ids = expected_quest_ids(config)
    cache = quest_item_cache(config)
    cache.mkdir(parents=True, exist_ok=True)
    lock_path = cache / ".freeze.lock"
    if lock_path.exists():
        raise RuntimeError(f"Quest wiki acquisition is already active: {lock_path}")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        client = QuestWikiClient(base_url=config.wiki_base_url, requested_delay=delay, fetcher=fetcher)
        sample = f"{config.wiki_base_url}/{config.wiki_locale}/db/quests/{ids[0]}"
        robots, robots_payload = client.load_robots(sample)
        _atomic_bytes(cache / "robots.txt", robots_payload)
        atomic_text(cache / "robots-policy.json", canonical_json(robots, pretty=True))
        reused: list[int] = []
        downloaded: list[int] = []
        failures: list[int] = []
        for index, quest_id in enumerate(ids, 1):
            if resume and _snapshot_valid(cache, quest_id):
                reused.append(quest_id)
            else:
                url = f"{config.wiki_base_url}/{config.wiki_locale}/db/quests/{quest_id}"
                status, payload, content_type, final_url, error = client.fetch(url)
                _write_snapshot(cache, quest_id=quest_id, canonical_url=url, status_code=status, payload=payload, content_type=content_type, final_url=final_url, locale=config.wiki_locale, error=error)
                downloaded.append(quest_id)
                if status not in {200, 404, 410}:
                    failures.append(quest_id)
            if progress and (index % 20 == 0 or index == len(ids)):
                progress(f"nuia story v2 wiki {index}/{len(ids)} downloaded={len(downloaded)} reused={len(reused)} failures={len(failures)}")
        manifest = _wiki_manifest(config, ids, reused, downloaded)
        return {"cache": cache, "downloaded_ids": downloaded, "failures": failures, "manifest": story_v2_paths(config)["wiki_manifest"], "record_digest": manifest["record_digest"], "reused_ids": reused}
    finally:
        lock_path.unlink(missing_ok=True)


def _normalize_name(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def _load_wiki_v2(config: ForensicsConfig, contexts: list[dict[str, Any]], contexts_all: list[dict[str, Any]] | None = None):
    cache = quest_item_cache(config)
    ids = tuple(int(source["row"]["id"]) for source in contexts)
    order = {quest_id: index for index, quest_id in enumerate(ids)}
    pages: list[dict[str, Any]] = []
    parsed_by_id: dict[int, Any] = {}
    names: dict[int, str | None] = {}
    metadata_by_id: dict[int, dict[str, Any]] = {}
    for quest_id in ids:
        html_path, metadata_path = _snapshot_paths(cache, quest_id)
        url = f"{config.wiki_base_url}/{config.wiki_locale}/db/quests/{quest_id}"
        metadata = _read_snapshot_metadata(metadata_path) if metadata_path.is_file() else {}
        status = metadata.get("status_code")
        digest = metadata.get("content_sha256")
        parsed = None
        state = str(metadata.get("page_state", "not_requested"))
        if status == 200 and html_path.is_file() and digest and sha256_file(html_path) == str(digest).upper():
            parsed = parse_story_page_v2(html_path.read_bytes(), quest_id=quest_id, locale=config.wiki_locale)
            state = parsed.parse_state
        parsed_by_id[quest_id] = parsed
        names[quest_id] = parsed.name if parsed else None
        metadata_by_id[quest_id] = metadata
        pages.append({"quest_id": quest_id, "url": str(metadata.get("url", url)), "status_code": status, "response_sha256": digest, "detail_state": state, "parser_version": PARSER_VERSION, "evidence": {"metadata_path": metadata_path.resolve().as_posix(), "metadata_sha256": sha256_file(metadata_path) if metadata_path.is_file() else None, "authority": "external_corroborative"}})
    name_index: dict[str, list[int]] = defaultdict(list)
    for quest_id, name in names.items():
        if _normalize_name(name):
            name_index[_normalize_name(name)].append(quest_id)
    raw_edges: list[dict[str, Any]] = []
    resolved_edges: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    selected = set(ids)
    compatible_native = {
        int(source["row"]["id"])
        for source in (contexts_all or contexts)
        if _race_compatible(int(source["row"].get("race", 0)))
    }
    for quest_id in ids:
        parsed = parsed_by_id[quest_id]
        if parsed is None:
            continue
        digest = str(metadata_by_id[quest_id].get("content_sha256") or "")
        html_path, _ = _snapshot_paths(cache, quest_id)
        for edge in parsed.edges:
            raw = int(edge.dst_quest_id)
            label_candidates = list(name_index.get(_normalize_name(edge.label), []))
            directional = [candidate for candidate in label_candidates if (order[candidate] < order[quest_id] if edge.relation == "requires_precompleted_quest" else order[candidate] > order[quest_id])]
            if raw in selected and raw in directional:
                resolved = raw
                state = "raw_compatible_exact_label"
            elif len(directional) == 1:
                resolved = directional[0]
                state = "canonicalized_label_native_order"
            elif directional:
                resolved = max(directional, key=lambda candidate: order[candidate]) if edge.relation == "requires_precompleted_quest" else min(directional, key=lambda candidate: order[candidate])
                state = "canonicalized_label_nearest_native_order"
            elif raw in selected:
                resolved = raw
                state = "raw_compatible_label_unmatched"
            elif raw in compatible_native:
                resolved = raw
                state = "external_native_prerequisite"
            else:
                resolved = None
                state = "external_or_unresolved"
            raw_key = stable_key("nuia_story_v2_raw_edge", quest_id, edge.relation, raw, edge.ordinal, edge.href)
            raw_edges.append({"wiki_edge_key": raw_key, "src_quest_id": quest_id, "relation": edge.relation, "dst_quest_id": raw, "ordinal": edge.ordinal, "label": edge.label, "href": edge.href, "response_sha256": digest, "parse_state": "confirmed", "context": {"structural_container": edge.context}, "evidence": {"authority": "external_corroborative", "parser_version": PARSER_VERSION, "raw_edge_preserved": True, "source_html": html_path.resolve().as_posix()}})
            resolution_key = stable_key("nuia_story_v2_resolution", quest_id, edge.relation, raw, edge.ordinal)
            resolutions.append({"resolution_key": resolution_key, "src_quest_id": quest_id, "relation": edge.relation, "raw_dst_quest_id": raw, "resolved_dst_quest_id": resolved, "label": edge.label, "resolution_state": state, "candidate_ids_json": canonical_json(directional), "evidence_json": canonical_json({"raw_href": edge.href, "visible_label": edge.label, "race_mask": RACE_MASK_NUIA, "wiki_is_corroborative": True, "does_not_create_native_dependency": True})})
            if resolved is not None:
                resolved_edges.append({**raw_edges[-1], "dst_quest_id": resolved, "wiki_edge_key": stable_key("nuia_story_v2_resolved_edge", quest_id, edge.relation, resolved, edge.ordinal), "evidence": {**raw_edges[-1]["evidence"], "resolution_key": resolution_key, "raw_dst_quest_id": raw, "resolution_state": state}})
        for relation in parsed.relations:
            relations.append({"wiki_relation_key": stable_key("nuia_story_v2_relation", quest_id, relation.relation, relation.dst_kind, relation.dst_id, relation.ordinal), "quest_id": quest_id, "relation": relation.relation, "dst_kind": relation.dst_kind, "dst_id": relation.dst_id, "ordinal": relation.ordinal, "label": relation.label, "href": relation.href, "response_sha256": digest, "context": {"structural_container": relation.context}, "evidence": {"authority": "external_corroborative", "parser_version": PARSER_VERSION, "source_html": html_path.resolve().as_posix()}})
    return pages, raw_edges, resolved_edges, resolutions, relations, names


def _crosswalk_v2(config: ForensicsConfig, ids: tuple[int, ...]):
    path = config.output_dir / "quest-item-crosswalk-v1.sqlite3"
    connection = _open_read_only(path)
    try:
        grants: dict[tuple[Any, ...], dict[str, Any]] = {}
        for offset in range(0, len(ids), 500):
            chunk = ids[offset:offset + 500]
            placeholders = ",".join("?" for _ in chunk)
            for row in connection.execute(f"SELECT * FROM quest_item_grants WHERE quest_id IN ({placeholders}) ORDER BY grant_key", chunk):
                key = (int(row["quest_id"]), int(row["component_id"]), int(row["quest_act_id"]), str(row["act_detail_type"]), int(row["act_detail_id"]), int(row["item_id"]))
                grants[key] = dict(row)
        closures = {int(row["item_id"]): dict(row) for row in connection.execute("SELECT * FROM item_closure ORDER BY item_id")}
    finally:
        connection.close()
    return path, grants, closures


def _order_edges_v2(contexts: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = [source["row"] for source in contexts]
    requires = {(int(row["dst_quest_id"]), int(row["src_quest_id"])) for row in edges if row["relation"] == "requires_precompleted_quest"}
    opens = {(int(row["src_quest_id"]), int(row["dst_quest_id"])) for row in edges if row["relation"] == "opens_access_to"}
    bridge_map = {(src, dst): kind for src, dst, kind in BRIDGES}
    result = []
    for left, right in zip(ordered, ordered[1:]):
        src, dst = int(left["id"]), int(right["id"])
        pair = (src, dst)
        same_chapter = int(left["chapter_idx"]) == int(right["chapter_idx"])
        has_requires, has_opens = pair in requires, pair in opens
        bridge = bridge_map.get(pair)
        if has_requires and has_opens:
            overall = "corroborated_order"
        elif has_requires or has_opens:
            overall = "corroborated_order"
        elif bridge == "wiki_actor_name_category_transition":
            overall = "corroborated_order"
        elif bridge:
            overall = "chapter_boundary_unresolved"
        elif same_chapter:
            overall = "native_ordinal_candidate"
        else:
            overall = "chapter_boundary_unresolved"
        result.append({"edge_key": stable_key("nuia_story_v2_order", src, dst), "src_quest_id": src, "dst_quest_id": dst, "edge_kind": bridge or "native_editorial_ordinal", "native_edge_state": "not_demonstrated", "ordinal_state": "same_chapter_neighbor" if same_chapter else "chapter_boundary_neighbor", "wiki_requires_state": "corroborated_visible" if has_requires else "absent_in_snapshot", "wiki_opens_state": "corroborated_visible" if has_opens else "absent_in_snapshot", "reciprocal_state": "reciprocal" if has_requires and has_opens else ("one_way" if has_requires or has_opens else "absent"), "overall_state": overall, "provenance": "stage40_native_ordinal+wiki_corroboration_v2", "evidence": {"same_chapter": same_chapter, "transition_classification": bridge, "wiki_does_not_create_native_dependency": True}})
    return result


def _transition_gates(resolved_edges: list[dict[str, Any]], relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs = {(int(row["src_quest_id"]), int(row["dst_quest_id"])) for row in resolved_edges if row["relation"] == "opens_access_to"} | {(int(row["dst_quest_id"]), int(row["src_quest_id"])) for row in resolved_edges if row["relation"] == "requires_precompleted_quest"}
    by_quest = defaultdict(list)
    for relation in relations:
        by_quest[int(relation["quest_id"])].append(relation)
    rows = []
    for src, dst, kind in BRIDGES:
        evidence: dict[str, Any] = {"wiki_pair_present": (src, dst) in pairs, "wiki_is_corroborative": True}
        if (src, dst) == (10303, 10361):
            actor_name = lambda value: _normalize_name(re.sub(r"^\s*\[[^]]+\]\s*", "", value or ""))
            source_names = {actor_name(row["label"]) for row in by_quest[src] if row["dst_kind"] in {"npc", "doodad"}}
            destination_names = {actor_name(row["label"]) for row in by_quest[dst] if row["dst_kind"] in {"npc", "doodad"}}
            evidence.update({"source_report_actor_names": sorted(source_names), "destination_accept_actor_names": sorted(destination_names), "shared_actor_names": sorted(source_names & destination_names)})
            state = "corroborated_actor_name" if source_names & destination_names else "classified_transparent_gap"
        elif (src, dst) == (10369, 10646):
            evidence.update({"direct_wiki_dependency_absent": (src, dst) not in pairs, "reason": "wiki stage link" if (src, dst) in pairs else "next native main chapter begins without a visible direct prerequisite"})
            state = "corroborated_wiki_stage" if (src, dst) in pairs else "classified_transparent_gap"
        else:
            state = "corroborated_wiki_stage" if (src, dst) in pairs else "classified_transparent_gap"
        rows.append({"gate_key": stable_key("nuia_story_v2_transition", src, dst), "src_quest_id": src, "dst_quest_id": dst, "gate_kind": kind, "state": state, "evidence_json": canonical_json(evidence)})
    return rows


def _terminal_audits(contexts: list[dict[str, Any]], resolved_edges: list[dict[str, Any]], relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last = int(contexts[-1]["row"]["id"])
    outgoing = [row for row in resolved_edges if int(row["src_quest_id"]) == last and row["relation"] == "opens_access_to"]
    inverse = [row for row in resolved_edges if int(row["dst_quest_id"]) == last and row["relation"] == "requires_precompleted_quest"]
    dimensions = {
        "direct_opens_link": {"successors": [row["dst_quest_id"] for row in outgoing]},
        "inverse_requires_scan": {"successors": [row["src_quest_id"] for row in inverse]},
        "native_main_chapter_scan": {"max_chapter": max(int(source["row"]["chapter_idx"]) for source in contexts)},
        "endpoint_actor_scan": {"endpoint_relations": [row["wiki_relation_key"] for row in relations if int(row["quest_id"]) == last]},
    }
    return [{"audit_key": stable_key("nuia_story_v2_terminal", last, dimension), "quest_id": last, "dimension": dimension, "state": "terminal_confirmed" if dimension != "endpoint_actor_scan" or bool(evidence["endpoint_relations"]) else "terminal_no_actor_link", "evidence_json": canonical_json(evidence)} for dimension, evidence in dimensions.items()]


def _export_v2(config: ForensicsConfig, database: Path) -> dict[str, Any]:
    paths = story_v2_paths(config)
    connection = _open_read_only(database)
    try:
        tables = ("story_quests", "story_order_edges", "story_quest_components", "story_quest_acts", "story_quest_endpoints", "story_quest_items", "story_dependency_closure", "wiki_story_pages", "wiki_story_edges", "wiki_story_relations", "story_wiki_edge_resolutions", "story_transition_gates", "story_terminal_audits", "downstream_audit_queue")
        counts = {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
        summary = {"schema_version": SCHEMA_VERSION, "tool_version": TOOL_VERSION, "table_counts": counts, "category_counts": dict(connection.execute("SELECT category_id,COUNT(*) FROM story_quests GROUP BY category_id ORDER BY category_id").fetchall()), "chapter_counts": dict(connection.execute("SELECT chapter_idx,COUNT(*) FROM story_quests GROUP BY chapter_idx ORDER BY chapter_idx").fetchall()), "edge_states": dict(connection.execute("SELECT overall_state,COUNT(*) FROM story_order_edges GROUP BY overall_state ORDER BY overall_state").fetchall()), "wiki_resolution_states": dict(connection.execute("SELECT resolution_state,COUNT(*) FROM story_wiki_edge_resolutions GROUP BY resolution_state ORDER BY resolution_state").fetchall()), "closure_states": dict(connection.execute("SELECT closure_state,COUNT(*) FROM story_dependency_closure GROUP BY closure_state ORDER BY closure_state").fetchall())}
        atomic_text(paths["summary"], canonical_json(summary, pretty=True))
        gaps = [dict(row) for row in connection.execute("SELECT quest_id,chapter_idx,quest_idx,severity,blocker_kind,blocked_entity_key,recommended_stop_point,state,evidence_json FROM downstream_audit_queue ORDER BY chapter_idx,quest_idx,audit_key")]
        _write_csv(paths["gaps"], ("quest_id","chapter_idx","quest_idx","severity","blocker_kind","blocked_entity_key","recommended_stop_point","state","evidence_json"), gaps)
        test_rows = [dict(row) for row in connection.execute("SELECT chapter_idx,quest_idx,quest_id,COALESCE(visible_name,'') visible_name,category_id,race,level FROM story_quests ORDER BY chapter_idx,quest_idx,quest_id")]
        _write_csv(paths["test_order"], ("chapter_idx","quest_idx","quest_id","visible_name","category_id","race","level"), test_rows)
        payload = {"summary": summary, "quests": test_rows, "edges": [dict(row) for row in connection.execute("SELECT src_quest_id,dst_quest_id,edge_kind,overall_state FROM story_order_edges ORDER BY src_quest_id,dst_quest_id")]}
        escaped = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
        atomic_text(paths["viewer"], "<!doctype html><meta charset='utf-8'><title>Nuia story graph V2</title><style>body{font:14px system-ui;margin:2rem;background:#10151d;color:#e8eef7}table{border-collapse:collapse}td,th{padding:.35rem .6rem;border:1px solid #445}input{padding:.5rem;width:24rem}</style><h1>Nuia story graph V2</h1><input id=q placeholder='quest, chapter or name'><div id=s></div><table><thead><tr><th>Chapter</th><th>Idx</th><th>ID</th><th>Name</th><th>Category</th><th>Race</th><th>Level</th></tr></thead><tbody id=b></tbody></table><script>const D=" + escaped + ";const b=document.querySelector('#b'),q=document.querySelector('#q'),s=document.querySelector('#s');s.textContent=JSON.stringify(D.summary.table_counts);function r(){let x=q.value.toLowerCase();b.innerHTML=D.quests.filter(v=>JSON.stringify(v).toLowerCase().includes(x)).map(v=>`<tr><td>${v.chapter_idx}</td><td>${v.quest_idx}</td><td>${v.quest_id}</td><td>${v.visible_name}</td><td>${v.category_id}</td><td>${v.race}</td><td>${v.level}</td></tr>`).join('')}q.oninput=r;r()</script>")
        return summary
    finally:
        connection.close()


def build_nuia_story_quest_graph_v2(config: ForensicsConfig) -> dict[str, Any]:
    paths = story_v2_paths(config)
    if not paths["wiki_manifest"].is_file():
        raise FileNotFoundError(f"Freeze Nuian story V2 wiki first: {paths['wiki_manifest']}")
    story = _native_story_v2(config)
    ids = tuple(int(source["row"]["id"]) for source in story["contexts"])
    doodads = _doodad_native_closure(config, story)
    crosswalk_path, grants, item_closures = _crosswalk_v2(config, ids)
    wiki_pages, raw_edges, resolved_edges, resolutions, wiki_relations, names = _load_wiki_v2(config, story["contexts"], story["contexts_all"])
    order_edges = _order_edges_v2(story["contexts"], resolved_edges)
    transitions = _transition_gates(resolved_edges, wiki_relations)
    terminals = _terminal_audits(story["contexts"], resolved_edges, wiki_relations)
    consolidated = _open_read_only(config.consolidated)
    resolver = ClosureResolver(consolidated, item_closures)
    try:
        component_rows, act_rows, endpoint_rows, item_rows, quest_seeds = _component_act_rows(story, doodads, grants, resolver)
        closure_rows = _closure_rows(story, doodads, resolver, quest_seeds)
    finally:
        consolidated.close()
    audit_rows = _audit_rows(story["contexts"], closure_rows, item_rows, endpoint_rows)
    source_paths = {"stage_20_items": config.stage_20, "stage_30_world_actors": config.stage_30, "stage_40_quests": config.stage_40, "stage_50_skills": config.stage_50, "stage_60_assets": config.stage_60, "stage_70_wiki": config.stage_70, "stage_90_coverage_closure": config.stage_90, "consolidated": config.consolidated, "quest_item_crosswalk": crosswalk_path, "game11_cached_results": config.source_game11, "nuia_story_v2_wiki_manifest": paths["wiki_manifest"], "builder_v2": Path(__file__).resolve(), "builder_v1_helpers": Path(__file__).with_name("nuia_story_graph.py").resolve()}
    for path in source_paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hashes = {role: sha256_file(path) for role, path in source_paths.items()}
    descriptor, name = tempfile.mkstemp(prefix=f".{paths['database'].stem}.", suffix=".sqlite3", dir=paths["database"].parent)
    os.close(descriptor)
    temporary = Path(name)
    temporary.unlink(missing_ok=True)
    connection = None
    try:
        connection = _create_database(temporary)
        connection.executescript(EXTRA_SCHEMA)
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        metadata = {"authority_order": ["stage40_native", "native_closure", "wiki_corroboration"], "client_build": config.client_build, "closure_policy": {"wiki_can_create_native_relation": False, "raw_and_resolved_wiki_edges_are_separate": True, "unknown_is_preserved": True}, "membership_predicate": {"categories": STORY_CATEGORIES, "nuia_race_mask": 1, "non_initial_categories_require_chapter_gt_zero": True}, "parser_version": PARSER_VERSION, "schema_version": SCHEMA_VERSION, "tool": {"name": TOOL_NAME, "version": TOOL_VERSION}}
        connection.executemany("INSERT INTO metadata VALUES(?,?)", [(key, canonical_json(value)) for key, value in sorted(metadata.items())])
        for role, path in sorted(source_paths.items()):
            authority = "external_corroborative" if "wiki" in role else ("client_native" if role.startswith("stage_") or role == "game11_cached_results" else "derived_forensic")
            connection.execute("INSERT INTO source_artifacts VALUES(?,?,?,?,?,?,?,?)", (stable_key("nuia_story_v2_source", role), role, path.resolve().as_posix(), path.stat().st_size, source_hashes[role], authority, TOOL_NAME, canonical_json({"recalculated_sha256": True})))
        quests = []
        for source in story["contexts"]:
            row = source["row"]
            quest_id = int(row["id"])
            quests.append({"quest_id": quest_id, "category_id": int(row["category_id"]), "race": int(row["race"]), "chapter_idx": int(row["chapter_idx"]), "quest_idx": int(row["quest_idx"]), "zone_id": int(row["zone_id"]), "level": int(row["level"]), "native_name": row.get("name"), "visible_name": names.get(quest_id), "membership_state": "confirmed_native_nuia_story_v2", "native_state": source["state"], "provenance": "stage40.native_rows.quest_contexts", "evidence_json": canonical_json({"native_row": row, "native_row_key": source["native_row_key"], "source_row_index": _row_index(source), "membership_predicate_v2": True})})
        connection.executemany("INSERT INTO story_quests VALUES(:quest_id,:category_id,:race,:chapter_idx,:quest_idx,:zone_id,:level,:native_name,:visible_name,:membership_state,:native_state,:provenance,:evidence_json)", quests)
        scope_candidates = []
        for row in resolutions:
            if row["resolution_state"] != "external_native_prerequisite":
                continue
            quest_id = int(row["resolved_dst_quest_id"])
            scope_candidates.append({"candidate_key": stable_key("nuia_story_v2_scope", row["src_quest_id"], quest_id, row["relation"]), "quest_id": quest_id, "direction": "incoming_prerequisite", "reason": "wiki_visible_native_side_prerequisite", "state": "external_native_preserved", "evidence_json": canonical_json({"source_story_quest_id": row["src_quest_id"], "resolution_key": row["resolution_key"], "not_silently_discarded": True})})
        connection.executemany("INSERT INTO scope_boundary_candidates VALUES(:candidate_key,:quest_id,:direction,:reason,:state,:evidence_json)", scope_candidates)
        connection.executemany("INSERT INTO story_order_edges VALUES(:edge_key,:src_quest_id,:dst_quest_id,:edge_kind,:native_edge_state,:ordinal_state,:wiki_requires_state,:wiki_opens_state,:reciprocal_state,:overall_state,:provenance,:evidence_json)", [{**row, "evidence_json": canonical_json(row["evidence"])} for row in order_edges])
        connection.executemany("INSERT INTO story_quest_components VALUES(:component_key,:quest_id,:component_id,:component_kind_id,:ordinal,:row_json,:native_state,:evidence_json)", [{**row, "evidence_json": canonical_json(row["evidence"])} for row in component_rows])
        connection.executemany("INSERT INTO story_quest_acts VALUES(:act_key,:quest_id,:component_id,:quest_act_id,:act_detail_type,:act_detail_id,:detail_row_json,:closure_state,:evidence_json)", [{**row, "evidence_json": canonical_json(row["evidence"])} for row in act_rows])
        connection.executemany("INSERT INTO story_quest_endpoints VALUES(:endpoint_key,:quest_id,:phase,:endpoint_kind,:endpoint_id,:act_detail_type,:act_detail_id,:client_doodad,:proxy_npc_id,:spawn_state,:closure_state,:evidence_json)", [{**row, "evidence_json": canonical_json(row["evidence"])} for row in endpoint_rows])
        connection.executemany("INSERT INTO story_quest_items VALUES(:relation_key,:quest_id,:component_id,:quest_act_id,:item_id,:item_role,:selection_mode,:count,:grade_id,:flags_json,:native_relation_state,:item_closure_state,:crosswalk_state,:evidence_json)", [{**row, "evidence_json": canonical_json(row["evidence"])} for row in item_rows])
        connection.executemany("INSERT INTO story_dependency_closure VALUES(:closure_key,:root_quest_id,:depth,:src_entity_key,:relation,:dst_entity_key,:dst_state,:required,:closure_state,:blocker_root,:evidence_json)", [{**row, "evidence_json": canonical_json(row["evidence"])} for row in closure_rows])
        connection.executemany("INSERT INTO wiki_story_pages VALUES(:quest_id,:url,:status_code,:response_sha256,:detail_state,:parser_version,:evidence_json)", [{**row, "evidence_json": canonical_json(row["evidence"])} for row in wiki_pages])
        connection.executemany("INSERT INTO wiki_story_edges VALUES(:wiki_edge_key,:src_quest_id,:relation,:dst_quest_id,:ordinal,:label,:href,:response_sha256,:parse_state,:context_json,:evidence_json)", [{**row, "context_json": canonical_json(row["context"]), "evidence_json": canonical_json(row["evidence"])} for row in raw_edges])
        connection.executemany("INSERT INTO wiki_story_relations VALUES(:wiki_relation_key,:quest_id,:relation,:dst_kind,:dst_id,:ordinal,:label,:href,:response_sha256,:context_json,:evidence_json)", [{**row, "context_json": canonical_json(row["context"]), "evidence_json": canonical_json(row["evidence"])} for row in wiki_relations])
        connection.executemany("INSERT INTO story_wiki_edge_resolutions VALUES(:resolution_key,:src_quest_id,:relation,:raw_dst_quest_id,:resolved_dst_quest_id,:label,:resolution_state,:candidate_ids_json,:evidence_json)", resolutions)
        connection.executemany("INSERT INTO story_transition_gates VALUES(:gate_key,:src_quest_id,:dst_quest_id,:gate_kind,:state,:evidence_json)", transitions)
        connection.executemany("INSERT INTO story_terminal_audits VALUES(:audit_key,:quest_id,:dimension,:state,:evidence_json)", terminals)
        connection.executemany("INSERT INTO downstream_audit_queue VALUES(:audit_key,:quest_id,:chapter_idx,:quest_idx,:blocker_kind,:blocked_entity_key,:severity,:recommended_stop_point,:state,:evidence_json)", [{**row, "evidence_json": canonical_json(row["evidence"])} for row in audit_rows])
        category_counts = dict(Counter(int(source["row"]["category_id"]) for source in story["contexts"]))
        chapters = sorted({int(source["row"]["chapter_idx"]) for source in story["contexts"]})
        _insert_validation(connection, "v2_story_quest_count", len(ids) == EXPECTED_QUEST_COUNT, EXPECTED_QUEST_COUNT, len(ids))
        _insert_validation(connection, "v2_category_distribution", category_counts == EXPECTED_CATEGORY_COUNTS, EXPECTED_CATEGORY_COUNTS, category_counts)
        _insert_validation(connection, "v2_chapters_zero_through_thirty_one", chapters == list(range(32)), list(range(32)), chapters)
        _insert_validation(connection, "v1_prefix_preserved", ids[:len(V1_QUEST_IDS)] == V1_QUEST_IDS, V1_QUEST_IDS, ids[:len(V1_QUEST_IDS)])
        _insert_validation(connection, "all_story_rows_race_compatible", all(_selected_context(source["row"]) for source in story["contexts"]), True, all(_selected_context(source["row"]) for source in story["contexts"]))
        _insert_validation(connection, "all_wiki_pages_terminal", all(row["detail_state"] in {"confirmed", "partial", "redirected_confirmed", "redirected_partial"} for row in wiki_pages), EXPECTED_QUEST_COUNT, Counter(row["detail_state"] for row in wiki_pages))
        unresolved_internal = [row for row in resolutions if row["resolved_dst_quest_id"] is None and row["raw_dst_quest_id"] in ids]
        _insert_validation(connection, "zero_unclassified_internal_wiki_edges", not unresolved_internal, 0, len(unresolved_internal))
        corrected = {(row["src_quest_id"], row["raw_dst_quest_id"], row["resolved_dst_quest_id"]) for row in resolutions}
        _insert_validation(connection, "race_variant_links_canonicalized", {(7115, 7325, 7119), (7119, 8376, 7115), (7119, 7124, 7123), (7123, 7325, 7119), (7123, 7126, 7125)} <= corrected, True, sorted(corrected & {(7115, 7325, 7119), (7119, 8376, 7115), (7119, 7124, 7123), (7123, 7325, 7119), (7123, 7126, 7125)}))
        _insert_validation(connection, "all_transition_gates_classified", all(row["state"] in {"corroborated_wiki_stage", "corroborated_actor_name", "classified_transparent_gap"} for row in transitions), True, {f"{row['src_quest_id']}->{row['dst_quest_id']}": row["state"] for row in transitions})
        _insert_validation(connection, "terminal_10682_four_dimensions", len(terminals) == 4 and all(row["quest_id"] == 10682 and row["state"].startswith("terminal_") for row in terminals), 4, terminals)
        _insert_validation(connection, "zero_components_discarded", len(component_rows) == len(story["components"]), len(story["components"]), len(component_rows))
        _insert_validation(connection, "zero_acts_discarded", len(act_rows) == len(story["acts"]), len(story["acts"]), len(act_rows))
        _insert_validation(connection, "closure_states_classified", all(row["closure_state"] in CLOSURE_STATES for row in closure_rows), True, Counter(row["closure_state"] for row in closure_rows))
        connection.commit(); connection.execute("VACUUM"); connection.close(); connection = None
        temporary.replace(paths["database"])
    except Exception:
        if connection is not None:
            connection.close()
        temporary.unlink(missing_ok=True)
        raise
    summary = _export_v2(config, paths["database"])
    output_hashes = {key: {"path": path.resolve().as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for key, path in paths.items() if key not in {"manifest", "wiki_manifest"} and path.is_file()}
    manifest = {"authority": "client_forensics_only", "client_build": config.client_build, "commands": ["python -B -m client_forensics freeze-nuia-story-wiki-v2 --resume", "python -B -m client_forensics build-nuia-story-quest-graph-v2", "python -B -m client_forensics validate-nuia-story-quest-graph-v2"], "determinism": {"atomic_output": True, "stable_ordering": True, "timestamps_in_reproducible_outputs": False}, "inputs": {role: {"path": path.resolve().as_posix(), "bytes": path.stat().st_size, "sha256": source_hashes[role]} for role, path in sorted(source_paths.items())}, "outputs": output_hashes, "parser_version": PARSER_VERSION, "schema_version": SCHEMA_VERSION, "summary": summary, "tool": {"name": TOOL_NAME, "version": TOOL_VERSION}}
    atomic_text(paths["manifest"], canonical_json(manifest, pretty=True))
    return {"database": paths["database"], "database_sha256": output_hashes["database"]["sha256"], "manifest": paths["manifest"], "summary": summary}


def validate_nuia_story_quest_graph_v2(config: ForensicsConfig) -> dict[str, Any]:
    paths = story_v2_paths(config)
    for key, path in paths.items():
        if key != "wiki_manifest" and not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    connection = _open_read_only(paths["database"])
    try:
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        failures = [dict(row) for row in connection.execute("SELECT check_name,state,expected_json,actual_json FROM validation_events WHERE state<>'confirmed' ORDER BY check_name")]
        if quick != "ok" or integrity != "ok" or failures:
            raise RuntimeError(f"Nuian story quest graph V2 validation failed: quick={quick} integrity={integrity} failures={failures}")
        for key, record in manifest["outputs"].items():
            actual = sha256_file(paths[key])
            if actual != str(record["sha256"]).upper():
                raise RuntimeError(f"Output hash mismatch for {key}: {actual}")
        return {"checks": {"quick_check": quick, "integrity_check": integrity, "failed_validation_events": failures}, "database": paths["database"], "database_sha256": sha256_file(paths["database"]), "manifest": paths["manifest"], "manifest_sha256": sha256_file(paths["manifest"]), "status": "confirmed"}
    finally:
        connection.close()
