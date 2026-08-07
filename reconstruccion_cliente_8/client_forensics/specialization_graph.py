from __future__ import annotations

import csv
import hashlib
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
    QuestWikiClient,
    _DomParser,
    _Node,
    _atomic_bytes,
    _clean,
    _walk,
)
from .util import atomic_text, canonical_json, sha256_file, stable_key


SCHEMA_VERSION = 1
PARSER_VERSION = "specialization-skill-structured-v1"
WIKI_AUTHORITY = "external_corroborative"
WIKI_PROVENANCE = "wiki.archerage.to_visible_database"
TERMINAL_STATES = {
    "confirmed",
    "corroborated",
    "missing",
    "tombstone",
    "blocked",
    "unknown",
    "not_applicable",
    "opaque",
}
SPECIALIZATIONS = {
    1: ("battlerage", "Battlerage"),
    2: ("witchcraft", "Witchcraft"),
    3: ("defense", "Defense"),
    4: ("auramancy", "Auramancy"),
    5: ("occultism", "Occultism"),
    6: ("archery", "Archery"),
    7: ("sorcery", "Sorcery"),
    8: ("shadowplay", "Shadowplay"),
    9: ("songcraft", "Songcraft"),
    10: ("vitalism", "Vitalism"),
    11: ("malediction", "Malediction"),
    12: ("swiftblade", "Swiftblade"),
    13: ("gunslinger", "Gunslinger"),
    14: ("spelldance", "Spelldance"),
}
SKILL_LINK = re.compile(
    r"^/(?P<locale>[^/]+)/db/(?P<kind>skills|buffs|items|npcs|doodads)/"
    r"(?P<id>\d+)(?:[/?#].*)?$"
)
RANK = re.compile(r"\(\s*Rank\s+(?P<rank>\d+)\s*\)", re.IGNORECASE)
FIELD_PATTERNS = {
    "mana": re.compile(r"\bMana:\s*(?P<value>[\d,]+)", re.IGNORECASE),
    "range": re.compile(r"\bRange:\s*(?P<value>.+?)(?=\s+(?:Effect|Combo|ID\s*\||$))", re.IGNORECASE),
}
PRESENTATION_TABLES = {
    "anims": "animation",
    "skill_controllers": "controller",
    "projectiles": "projectile",
    "aoe_shapes": "aoe",
    "fx_groups": "fx",
    "fx_items": "fx",
    "fx_particles": "fx",
    "fx_sounds": "sound",
    "sounds": "sound",
    "sound_packs": "sound",
    "sound_pack_items": "sound",
}
EXPAND_KINDS = {
    "anim",
    "anim_action",
    "anim_rule",
    "aoe_shape",
    "asset_file",
    "buff",
    "effect",
    "effect_detail",
    "fx_group",
    "fx_item",
    "fx_particle",
    "fx_sound",
    "icon",
    "item",
    "localization",
    "npc",
    "plot",
    "plot_condition",
    "plot_effect",
    "plot_event",
    "projectile",
    "skill",
    "skill_controller",
    "sound",
    "sound_pack",
    "sound_pack_item",
}
EXPECTED_SHADOWPLAY = {
    "skills": 28,
    "visible": 9,
    "passives": 6,
}


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

CREATE TABLE specialization_roots (
    root_key TEXT PRIMARY KEY,
    root_kind TEXT NOT NULL,
    native_id INTEGER NOT NULL,
    ability_id INTEGER NOT NULL,
    membership_state TEXT NOT NULL,
    native_state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE specialization_skills (
    skill_id INTEGER PRIMARY KEY,
    ability_id INTEGER,
    root_member INTEGER NOT NULL,
    visible INTEGER,
    native_name TEXT,
    wiki_name TEXT,
    lifecycle TEXT NOT NULL,
    membership_state TEXT NOT NULL,
    native_state TEXT NOT NULL,
    row_json TEXT,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE skill_runtime_contracts (
    skill_id INTEGER PRIMARY KEY,
    cost INTEGER,
    cooldown_time INTEGER,
    casting_time INTEGER,
    channeling_time INTEGER,
    target_type_id INTEGER,
    min_range REAL,
    max_range REAL,
    projectile_id INTEGER,
    skill_controller_id INTEGER,
    fire_anim_id INTEGER,
    contract_state TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE skill_effect_steps (
    step_key TEXT PRIMARY KEY,
    root_skill_id INTEGER NOT NULL,
    skill_effect_id INTEGER NOT NULL,
    effect_id INTEGER NOT NULL,
    effect_type TEXT,
    ordinal INTEGER NOT NULL,
    chance INTEGER,
    application_method_id INTEGER,
    target_flags_json TEXT NOT NULL,
    state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE buff_contracts (
    contract_key TEXT PRIMARY KEY,
    root_skill_id INTEGER NOT NULL,
    buff_id INTEGER NOT NULL,
    relation_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE combo_conditions (
    condition_key TEXT PRIMARY KEY,
    root_skill_id INTEGER NOT NULL,
    source_table TEXT NOT NULL,
    native_id INTEGER NOT NULL,
    condition_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE combo_outcomes (
    outcome_key TEXT PRIMARY KEY,
    root_skill_id INTEGER NOT NULL,
    source_table TEXT NOT NULL,
    native_id INTEGER NOT NULL,
    outcome_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE presentation_bindings (
    binding_key TEXT PRIMARY KEY,
    root_skill_id INTEGER NOT NULL,
    presentation_kind TEXT NOT NULL,
    native_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    state TEXT NOT NULL,
    row_json TEXT,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE dependency_edges (
    edge_key TEXT PRIMARY KEY,
    root_skill_id INTEGER NOT NULL,
    src_entity_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    dst_entity_key TEXT NOT NULL,
    state TEXT NOT NULL,
    required INTEGER NOT NULL,
    authority TEXT NOT NULL,
    locator TEXT NOT NULL,
    loader_or_consumer TEXT,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE dependency_closure (
    closure_key TEXT PRIMARY KEY,
    root_skill_id INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    entity_key TEXT NOT NULL,
    source_table TEXT,
    native_id TEXT,
    state TEXT NOT NULL,
    blocker_kind TEXT,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_skill_pages (
    skill_id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_sha256 TEXT,
    page_state TEXT NOT NULL,
    parser_version TEXT,
    name TEXT,
    ability TEXT,
    rank INTEGER,
    mana INTEGER,
    range_text TEXT,
    sections_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_skill_relations (
    relation_key TEXT PRIMARY KEY,
    src_skill_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    dst_kind TEXT NOT NULL,
    dst_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    label TEXT,
    href TEXT NOT NULL,
    context TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_skill_resolutions (
    resolution_key TEXT PRIMARY KEY,
    src_skill_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    raw_dst_kind TEXT NOT NULL,
    raw_dst_id INTEGER NOT NULL,
    resolved_native_id INTEGER,
    resolution_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE downstream_implementation_audit (
    audit_key TEXT PRIMARY KEY,
    skill_id INTEGER NOT NULL,
    observed_state TEXT NOT NULL,
    reason TEXT,
    authority TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE reconstruction_test_cases (
    test_key TEXT PRIMARY KEY,
    skill_id INTEGER NOT NULL,
    area TEXT NOT NULL,
    expected_state TEXT NOT NULL,
    oracle_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE audit_queue (
    audit_key TEXT PRIMARY KEY,
    root_skill_id INTEGER,
    blocker_kind TEXT NOT NULL,
    blocked_entity_key TEXT,
    severity TEXT NOT NULL,
    state TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
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

CREATE INDEX idx_roots_kind_id ON specialization_roots(root_kind,native_id);
CREATE INDEX idx_skills_membership ON specialization_skills(membership_state,skill_id);
CREATE INDEX idx_effect_steps_skill ON skill_effect_steps(root_skill_id,ordinal);
CREATE INDEX idx_buff_contracts_skill ON buff_contracts(root_skill_id,buff_id);
CREATE INDEX idx_combo_conditions_skill ON combo_conditions(root_skill_id,source_table);
CREATE INDEX idx_combo_outcomes_skill ON combo_outcomes(root_skill_id,source_table);
CREATE INDEX idx_presentation_skill_kind ON presentation_bindings(root_skill_id,presentation_kind);
CREATE INDEX idx_dependency_edges_root_src ON dependency_edges(root_skill_id,src_entity_key);
CREATE INDEX idx_dependency_closure_root_depth ON dependency_closure(root_skill_id,depth);
CREATE INDEX idx_wiki_relations_src ON wiki_skill_relations(src_skill_id,relation);
CREATE INDEX idx_wiki_resolutions_state ON wiki_skill_resolutions(resolution_state);
CREATE INDEX idx_tests_skill_area ON reconstruction_test_cases(skill_id,area);
CREATE INDEX idx_audit_severity ON audit_queue(severity,root_skill_id);
"""


@dataclass(frozen=True)
class Specialization:
    ability_id: int
    slug: str
    name: str


@dataclass(frozen=True)
class WikiSkillRelation:
    relation: str
    dst_kind: str
    dst_id: int
    ordinal: int
    label: str
    href: str
    context: str


@dataclass(frozen=True)
class ParsedSkillPage:
    skill_id: int
    name: str | None
    ability: str | None
    rank: int | None
    mana: int | None
    range_text: str | None
    effect_text: str | None
    combo_text: str | None
    sections: dict[str, str]
    relations: tuple[WikiSkillRelation, ...]
    parse_state: str


def resolve_specialization(value: str | int) -> Specialization:
    text = str(value).strip().casefold()
    for ability_id, (slug, name) in SPECIALIZATIONS.items():
        if text in {str(ability_id), slug.casefold(), name.casefold()}:
            return Specialization(ability_id, slug, name)
    expected = ", ".join(slug for slug, _ in SPECIALIZATIONS.values())
    raise ValueError(f"Unknown specialization {value!r}; expected one of: {expected}")


def resolve_specialization_suite(
    values: str | Iterable[str | int] | None = None,
) -> tuple[Specialization, ...]:
    if values is None or (isinstance(values, str) and values.strip().casefold() == "all"):
        return tuple(
            Specialization(ability_id, slug, name)
            for ability_id, (slug, name) in sorted(SPECIALIZATIONS.items())
        )
    raw_values: Iterable[str | int]
    if isinstance(values, str):
        raw_values = [value.strip() for value in values.split(",") if value.strip()]
    else:
        raw_values = values
    selected = {resolve_specialization(value).ability_id: resolve_specialization(value) for value in raw_values}
    if not selected:
        raise ValueError("The specialization suite selection is empty")
    return tuple(selected[ability_id] for ability_id in sorted(selected))


def specialization_paths(
    config: ForensicsConfig, specialization: Specialization
) -> dict[str, Path]:
    stem = config.output_dir / f"{specialization.slug}-specialization-graph-v1"
    return {
        "database": stem.with_suffix(".sqlite3"),
        "manifest": stem.with_suffix(".manifest.json"),
        "summary": config.output_dir / f"{specialization.slug}-specialization-summary.json",
        "gaps": config.output_dir / f"{specialization.slug}-specialization-gaps.csv",
        "tests": config.output_dir / f"{specialization.slug}-specialization-test-matrix.csv",
        "viewer": config.output_dir / f"viewer-{specialization.slug}-specialization.html",
        "wiki_manifest": config.output_dir
        / f"{specialization.slug}-specialization-wiki-snapshot-manifest.json",
    }


def specialization_suite_paths(config: ForensicsConfig) -> dict[str, Path]:
    return {
        "index": config.output_dir / "specialization-suite-v1.json",
        "manifest": config.output_dir / "specialization-suite-v1.manifest.json",
        "wiki_manifest": config.output_dir / "specialization-suite-wiki-v1.manifest.json",
    }


def specialization_wiki_cache(
    config: ForensicsConfig, specialization: Specialization
) -> Path:
    return specialization_wiki_kind_cache(config, specialization, "skills")


def specialization_wiki_kind_cache(
    config: ForensicsConfig, specialization: Specialization, entity_kind: str
) -> Path:
    if entity_kind not in {"skills", "buffs"}:
        raise ValueError(f"Unsupported specialization wiki entity kind: {entity_kind}")
    return (
        config.stage_70_wiki_cache
        / "specializations"
        / config.wiki_locale
        / specialization.slug
        / entity_kind
    )


def _native_catalog_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "reconstruccion_skills_8"
        / "native_combat"
        / "generated"
        / "native-combat-catalog-v1.json"
    )


def _open_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _content_container(root: _Node, skill_id: int) -> _Node:
    marker = f"ID: {skill_id}"
    candidates: list[tuple[int, _Node]] = []
    for node in _walk(root):
        if node.tag == "#text" and marker in node.text_value:
            current = node.parent
            while current is not None:
                text = current.text()
                if marker in text and len(text) <= 20_000:
                    candidates.append((len(text), current))
                current = current.parent
    if not candidates:
        return root
    with_table = [
        value
        for value in candidates
        if any(node.tag == "table" for node in _walk(value[1]))
    ]
    if with_table:
        return min(with_table, key=lambda value: value[0])[1]
    detailed = [
        value
        for value in candidates
        if any(
            marker in value[1].text()
            for marker in ("Mana:", "Range:", "Effect Granted:", "Effects Granted:", "Combo:", "Combos:")
        )
    ]
    if detailed:
        return min(detailed, key=lambda value: value[0])[1]
    substantial = [value for value in candidates if len(value[1].text()) >= 80]
    return min(substantial or candidates, key=lambda value: value[0])[1]


def _node_context(node: _Node, container: _Node) -> str:
    current = node.parent
    best = node.text()
    while current is not None and current is not container.parent:
        value = current.text()
        if value and value != best and len(value) <= 500:
            return value
        if value and len(value) <= 1_500:
            best = value
        current = current.parent
    return best


def _relation_hint(context: str, label: str, dst_kind: str) -> str:
    value = f"{context} {label}".casefold()
    if dst_kind == "skill":
        if "combo" in value:
            return "combo_skill"
        if "rank" in value or "variant" in value:
            return "variant_skill"
        if "effect" in value or "granted" in value:
            return "effect_skill"
        return "visible_skill"
    if dst_kind == "buff":
        if "rank" in value or "variant" in value:
            return "variant_buff"
        return "effect_buff" if "effect" in value else "visible_buff"
    return f"visible_{dst_kind}"


def parse_specialization_skill_page(
    payload: bytes, *, skill_id: int, locale: str = "na-en"
) -> ParsedSkillPage:
    dom = _DomParser()
    dom.feed(payload.decode("utf-8", errors="replace"))
    title = _clean(" ".join(dom.title_parts))
    name = re.sub(
        r"\s*-\s*Skill\s*-\s*ArcheRage Wiki\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip() or None
    container = _content_container(dom.root, skill_id)
    text = container.text()
    marker_present = f"ID: {skill_id}" in text
    rank_match = RANK.search(text)
    rank = int(rank_match.group("rank")) if rank_match else None
    mana_match = FIELD_PATTERNS["mana"].search(text)
    mana = int(mana_match.group("value").replace(",", "")) if mana_match else None
    range_match = FIELD_PATTERNS["range"].search(text)
    range_text = _clean(range_match.group("value")) if range_match else None
    ability = None
    for _, (_, candidate) in SPECIALIZATIONS.items():
        if re.search(rf"\b{re.escape(candidate)}\b", text, re.IGNORECASE):
            ability = candidate
            break
    effect_text = None
    combo_text = None
    effect_match = re.search(r"Effect(?:s)? Granted:\s*(?P<value>.+)$", text, re.IGNORECASE)
    if effect_match:
        effect_text = _clean(re.split(r"\s+(?:Combos?:|ID\s*\|)", effect_match.group("value"), maxsplit=1, flags=re.IGNORECASE)[0])
    combo_match = re.search(r"Combos?:\s*(?P<value>.+)$", text, re.IGNORECASE)
    if combo_match:
        combo_text = _clean(re.split(r"\s+(?:Effects? Granted:|ID\s*\|)", combo_match.group("value"), maxsplit=1, flags=re.IGNORECASE)[0])
    sections = {
        "effect": "present" if effect_text else "not_present",
        "combo": "present" if combo_text else "not_present",
        "variants": "not_present",
    }
    ordinals: Counter[str] = Counter()
    relations: list[WikiSkillRelation] = []
    seen: set[tuple[str, str, int, str]] = set()
    for node in _walk(container):
        if node.tag != "a":
            continue
        href = node.attrs.get("href", "")
        match = SKILL_LINK.match(href)
        if not match or match.group("locale") != locale:
            continue
        plural = match.group("kind")
        kind = plural.removesuffix("s")
        destination = int(match.group("id"))
        label = node.text()
        context = _node_context(node, container)
        relation = _relation_hint(context, label, kind)
        identity = (relation, kind, destination, href)
        if identity in seen:
            continue
        seen.add(identity)
        ordinals[relation] += 1
        relations.append(
            WikiSkillRelation(
                relation,
                kind,
                destination,
                ordinals[relation],
                label,
                href,
                context,
            )
        )
        if relation in {"variant_skill", "variant_buff"}:
            sections["variants"] = "present"
    parse_state = "confirmed" if marker_present and name else "parse_failed"
    return ParsedSkillPage(
        skill_id,
        name,
        ability,
        rank,
        mana,
        range_text,
        effect_text,
        combo_text,
        sections,
        tuple(relations),
        parse_state,
    )


def _snapshot_paths(cache: Path, skill_id: int) -> tuple[Path, Path]:
    return cache / f"{skill_id}.html", cache / f"{skill_id}.meta.json"


def _snapshot_valid(cache: Path, skill_id: int) -> bool:
    html_path, metadata_path = _snapshot_paths(cache, skill_id)
    if not html_path.is_file() or not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        int(metadata.get("entity_id", -1)) == skill_id
        and metadata.get("entity_kind") == "skills"
        and metadata.get("status_code") in {200, 404, 410}
        and int(metadata.get("content_bytes", -1)) == html_path.stat().st_size
        and str(metadata.get("content_sha256", "")).upper() == sha256_file(html_path)
    )


def _write_snapshot(
    cache: Path,
    *,
    skill_id: int,
    canonical_url: str,
    status_code: int | None,
    payload: bytes,
    content_type: str,
    final_url: str,
    locale: str,
    error: str | None,
) -> dict[str, Any]:
    html_path, metadata_path = _snapshot_paths(cache, skill_id)
    if status_code is not None:
        _atomic_bytes(html_path, payload)
        digest = sha256_file(html_path)
    else:
        digest = None
    if status_code == 200:
        parsed = parse_specialization_skill_page(payload, skill_id=skill_id, locale=locale)
        page_state = parsed.parse_state
        if final_url.rstrip("/") != canonical_url.rstrip("/"):
            page_state = f"redirected_{page_state}"
    elif status_code in {404, 410}:
        page_state = "permanent_missing"
    elif status_code is None:
        page_state = "transient_error"
    else:
        page_state = "http_error"
    metadata = {
        "content_bytes": len(payload),
        "content_sha256": digest,
        "content_type": content_type,
        "entity_id": skill_id,
        "entity_kind": "skills",
        "error": error,
        "final_url": final_url,
        "locale": locale,
        "page_state": page_state,
        "parser_version": PARSER_VERSION,
        "provenance": WIKI_PROVENANCE,
        "status_code": status_code,
        "url": canonical_url,
    }
    atomic_text(metadata_path, canonical_json(metadata, pretty=True))
    return metadata


def _linked_snapshot_valid(cache: Path, entity_id: int, entity_kind: str) -> bool:
    html_path, metadata_path = _snapshot_paths(cache, entity_id)
    if not html_path.is_file() or not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        int(metadata.get("entity_id", -1)) == entity_id
        and metadata.get("entity_kind") == entity_kind
        and metadata.get("status_code") in {200, 404, 410}
        and int(metadata.get("content_bytes", -1)) == html_path.stat().st_size
        and str(metadata.get("content_sha256", "")).upper() == sha256_file(html_path)
    )


def _write_linked_snapshot(
    cache: Path,
    *,
    entity_id: int,
    entity_kind: str,
    canonical_url: str,
    status_code: int | None,
    payload: bytes,
    content_type: str,
    final_url: str,
    locale: str,
    error: str | None,
) -> dict[str, Any]:
    html_path, metadata_path = _snapshot_paths(cache, entity_id)
    if status_code is not None:
        _atomic_bytes(html_path, payload)
        digest = sha256_file(html_path)
    else:
        digest = None
    if status_code == 200:
        marker = f"ID: {entity_id}"
        page_state = "confirmed" if marker in payload.decode("utf-8", errors="replace") else "parse_failed"
        if final_url.rstrip("/") != canonical_url.rstrip("/"):
            page_state = f"redirected_{page_state}"
    elif status_code in {404, 410}:
        page_state = "permanent_missing"
    elif status_code is None:
        page_state = "transient_error"
    else:
        page_state = "http_error"
    metadata = {
        "content_bytes": len(payload),
        "content_sha256": digest,
        "content_type": content_type,
        "entity_id": entity_id,
        "entity_kind": entity_kind,
        "error": error,
        "final_url": final_url,
        "locale": locale,
        "page_state": page_state,
        "parser_version": PARSER_VERSION,
        "provenance": WIKI_PROVENANCE,
        "status_code": status_code,
        "url": canonical_url,
    }
    atomic_text(metadata_path, canonical_json(metadata, pretty=True))
    return metadata


def _catalog_skill_ids(
    config: ForensicsConfig, specialization: Specialization
) -> tuple[int, ...]:
    connection = _open_read_only(config.stage_70)
    result: set[int] = set()
    try:
        rows = connection.execute(
            """
            SELECT we.entity_key,wp.value_json
            FROM wiki_entities we
            JOIN wiki_properties wp ON wp.wiki_entity_key=we.wiki_entity_key
            WHERE we.entity_key LIKE 'skill:%'
              AND wp.property_name='catalog_membership'
            ORDER BY we.entity_key
            """
        )
        for entity_key, value_json in rows:
            value = json.loads(value_json)
            memberships = value if isinstance(value, list) else [value]
            if specialization.slug in memberships:
                result.add(int(str(entity_key).split(":", 1)[1]))
    finally:
        connection.close()
    return tuple(sorted(result))


def _native_roots(
    config: ForensicsConfig, specialization: Specialization
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    connection = _open_read_only(config.stage_50)
    skills: list[int] = []
    passives: list[int] = []
    try:
        for row in connection.execute(
            "SELECT native_id,row_json FROM native_rows WHERE source_table='skills'"
        ):
            value = json.loads(row["row_json"])
            if int(value.get("ability_id") or 0) == specialization.ability_id:
                skills.append(int(row["native_id"]))
        for row in connection.execute(
            "SELECT native_id,row_json FROM native_rows WHERE source_table='passive_buffs'"
        ):
            value = json.loads(row["row_json"])
            if int(value.get("ability_id") or 0) == specialization.ability_id:
                passives.append(int(row["native_id"]))
    finally:
        connection.close()
    return tuple(sorted(skills)), tuple(sorted(passives))


def _wiki_manifest(
    config: ForensicsConfig,
    specialization: Specialization,
    requested_ids: Iterable[int],
    linked_buff_ids: Iterable[int] = (),
) -> dict[str, Any]:
    cache = specialization_wiki_cache(config, specialization)
    records: list[dict[str, Any]] = []
    for skill_id in sorted(set(requested_ids)):
        html_path, metadata_path = _snapshot_paths(cache, skill_id)
        if not metadata_path.is_file():
            records.append({"entity_kind": "skills", "skill_id": skill_id, "page_state": "not_requested"})
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        records.append(
            {
                "entity_kind": "skills",
                "skill_id": skill_id,
                "status_code": metadata.get("status_code"),
                "page_state": metadata.get("page_state"),
                "content_bytes": metadata.get("content_bytes"),
                "content_sha256": metadata.get("content_sha256"),
                "url": metadata.get("url"),
            }
        )
    buff_cache = specialization_wiki_kind_cache(config, specialization, "buffs")
    for buff_id in sorted(set(linked_buff_ids)):
        html_path, metadata_path = _snapshot_paths(buff_cache, buff_id)
        if not metadata_path.is_file():
            records.append({"entity_kind": "buffs", "entity_id": buff_id, "page_state": "not_requested"})
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        records.append(
            {
                "entity_kind": "buffs",
                "entity_id": buff_id,
                "status_code": metadata.get("status_code"),
                "page_state": metadata.get("page_state"),
                "content_bytes": metadata.get("content_bytes"),
                "content_sha256": metadata.get("content_sha256"),
                "url": metadata.get("url"),
            }
        )
    manifest = {
        "ability_id": specialization.ability_id,
        "authority": WIKI_AUTHORITY,
        "cache": cache.resolve().as_posix(),
        "client_build": config.client_build,
        "parser_version": PARSER_VERSION,
        "records": records,
        "record_digest": hashlib.sha256(
            canonical_json(records).encode("utf-8")
        ).hexdigest().upper(),
        "specialization": specialization.name,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }
    path = specialization_paths(config, specialization)["wiki_manifest"]
    atomic_text(path, canonical_json(manifest, pretty=True))
    return manifest


def freeze_specialization_wiki(
    config: ForensicsConfig,
    specialization_value: str | int,
    *,
    resume: bool = True,
    delay: float = MINIMUM_DELAY,
    progress: Callable[[str], None] | None = None,
    fetcher: Callable[[str], tuple[Any, ...]] | None = None,
) -> dict[str, Any]:
    specialization = resolve_specialization(specialization_value)
    roots, _ = _native_roots(config, specialization)
    requested = set(roots) | set(_catalog_skill_ids(config, specialization))
    cache = specialization_wiki_cache(config, specialization)
    cache.mkdir(parents=True, exist_ok=True)
    client = QuestWikiClient(
        base_url=config.wiki_base_url,
        requested_delay=delay,
        fetcher=fetcher,
    )
    sample = f"{config.wiki_base_url}/{config.wiki_locale}/db/skills/{min(requested)}"
    if fetcher is None:
        client.load_robots(sample)
    queue = deque(sorted(requested))
    processed: set[int] = set()
    downloaded: list[int] = []
    reused: list[int] = []
    failures: list[int] = []
    linked_buff_ids: set[int] = set()
    while queue:
        skill_id = queue.popleft()
        if skill_id in processed:
            continue
        if len(processed) >= 500:
            raise RuntimeError("Specialization wiki closure exceeded the 500-page safety bound")
        processed.add(skill_id)
        if resume and _snapshot_valid(cache, skill_id):
            reused.append(skill_id)
        else:
            url = f"{config.wiki_base_url}/{config.wiki_locale}/db/skills/{skill_id}"
            status, payload, content_type, final_url, error = client.fetch(url)
            metadata = _write_snapshot(
                cache,
                skill_id=skill_id,
                canonical_url=url,
                status_code=status,
                payload=payload,
                content_type=content_type,
                final_url=final_url,
                locale=config.wiki_locale,
                error=error,
            )
            downloaded.append(skill_id)
            if metadata["page_state"] not in {
                "confirmed",
                "redirected_confirmed",
                "permanent_missing",
            }:
                failures.append(skill_id)
        html_path, metadata_path = _snapshot_paths(cache, skill_id)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("status_code") == 200 and html_path.is_file():
            parsed = parse_specialization_skill_page(
                html_path.read_bytes(), skill_id=skill_id, locale=config.wiki_locale
            )
            for relation in parsed.relations:
                if relation.dst_kind == "buff" and relation.relation in {
                    "variant_buff",
                    "effect_buff",
                    "visible_buff",
                }:
                    linked_buff_ids.add(relation.dst_id)
                if relation.dst_kind == "skill" and relation.relation in {
                    "variant_skill",
                    "combo_skill",
                    "effect_skill",
                }:
                    if relation.dst_id not in processed:
                        queue.append(relation.dst_id)
                        requested.add(relation.dst_id)
        if progress:
            progress(
                f"{specialization.slug} wiki {len(processed)}/{len(requested)} "
                f"downloaded={len(downloaded)} reused={len(reused)} failures={len(failures)}"
            )
    buff_cache = specialization_wiki_kind_cache(config, specialization, "buffs")
    buff_cache.mkdir(parents=True, exist_ok=True)
    for index, buff_id in enumerate(sorted(linked_buff_ids), 1):
        if resume and _linked_snapshot_valid(buff_cache, buff_id, "buffs"):
            continue
        url = f"{config.wiki_base_url}/{config.wiki_locale}/db/buffs/{buff_id}"
        status, payload, content_type, final_url, error = client.fetch(url)
        metadata = _write_linked_snapshot(
            buff_cache,
            entity_id=buff_id,
            entity_kind="buffs",
            canonical_url=url,
            status_code=status,
            payload=payload,
            content_type=content_type,
            final_url=final_url,
            locale=config.wiki_locale,
            error=error,
        )
        if metadata["page_state"] not in {
            "confirmed",
            "redirected_confirmed",
            "permanent_missing",
        }:
            failures.append(-buff_id)
        if progress:
            progress(
                f"{specialization.slug} linked buff wiki {index}/{len(linked_buff_ids)} "
                f"failures={len(failures)}"
            )
    manifest = _wiki_manifest(config, specialization, requested, linked_buff_ids)
    return {
        "specialization": specialization.name,
        "ability_id": specialization.ability_id,
        "requested": len(requested),
        "linked_buffs": len(linked_buff_ids),
        "downloaded_ids": sorted(downloaded),
        "reused_ids": sorted(reused),
        "failures": sorted(failures),
        "manifest": specialization_paths(config, specialization)["wiki_manifest"],
        "record_digest": manifest["record_digest"],
    }


def _catalog() -> tuple[Path, dict[str, Any]]:
    path = _native_catalog_path()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path, json.loads(path.read_text(encoding="utf-8"))


def _batches(values: Iterable[str], size: int = 400) -> Iterable[list[str]]:
    batch: list[str] = []
    for value in values:
        batch.append(value)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def _stage_rows(
    config: ForensicsConfig, ability_table_ids: dict[str, list[int]]
) -> tuple[dict[tuple[str, int], dict[str, Any]], dict[str, dict[str, Any]]]:
    connection = _open_read_only(config.stage_50)
    by_table_id: dict[tuple[str, int], dict[str, Any]] = {}
    by_entity: dict[str, dict[str, Any]] = {}
    try:
        for table, ids in sorted(ability_table_ids.items()):
            for batch in _batches([str(value) for value in sorted(ids)]):
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"""
                    SELECT * FROM native_rows
                    WHERE source_table=?
                      AND (
                        native_id IN ({placeholders})
                        OR CAST(json_extract(row_json,'$.id') AS TEXT) IN ({placeholders})
                      )
                    ORDER BY native_row_key
                    """,
                    [table, *batch, *batch],
                )
                for source in rows:
                    row = dict(source)
                    row["decoded"] = json.loads(row["row_json"])
                    decoded_id = row["decoded"].get("id")
                    if decoded_id is None:
                        try:
                            decoded_id = int(row["native_id"])
                        except ValueError:
                            continue
                    key = (table, int(decoded_id))
                    by_table_id[key] = row
                    by_entity[row["entity_key"]] = row
    finally:
        connection.close()
    return by_table_id, by_entity


def _graph_edges(
    config: ForensicsConfig, seed_keys: set[str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    connection = _open_read_only(config.consolidated)
    edges: dict[str, dict[str, Any]] = {}
    entities: dict[str, dict[str, Any]] = {}
    frontier = set(seed_keys)
    visited: set[str] = set()
    try:
        for _ in range(12):
            current = sorted(frontier - visited)
            if not current:
                break
            visited.update(current)
            next_frontier: set[str] = set()
            for batch in _batches(current):
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"""
                    SELECT r.*,s.kind AS src_kind,s.native_id AS src_native_id,
                           d.kind AS dst_kind,d.native_id AS dst_native_id,
                           d.state AS dst_state,d.lifecycle AS dst_lifecycle
                    FROM relations r
                    JOIN entities s ON s.entity_key=r.src_entity_key
                    JOIN entities d ON d.entity_key=r.dst_entity_key
                    WHERE r.src_entity_key IN ({placeholders})
                    ORDER BY r.relation_key
                    """,
                    batch,
                )
                for source in rows:
                    row = dict(source)
                    edges[row["relation_key"]] = row
                    entities[row["dst_entity_key"]] = {
                        "entity_key": row["dst_entity_key"],
                        "kind": row["dst_kind"],
                        "native_id": row["dst_native_id"],
                        "state": row["dst_state"],
                        "lifecycle": row["dst_lifecycle"],
                    }
                    if row["dst_kind"] in EXPAND_KINDS:
                        next_frontier.add(row["dst_entity_key"])
            frontier = next_frontier
            if len(visited | frontier) > 100_000:
                raise RuntimeError("Specialization relation closure exceeded 100000 entities")
    finally:
        connection.close()
    return [edges[key] for key in sorted(edges)], entities


def _root_members(
    root_skill_id: int,
    skill_table_ids: dict[str, list[int]],
    by_table_id: dict[tuple[str, int], dict[str, Any]],
) -> tuple[set[str], list[dict[str, Any]]]:
    keys = {f"skill:{root_skill_id}"}
    closure: list[dict[str, Any]] = []
    for table, ids in sorted(skill_table_ids.items()):
        for native_id in sorted(ids):
            source = by_table_id.get((table, int(native_id)))
            if source:
                entity_key = source["entity_key"]
                state = source["state"]
            else:
                entity_key = f"{table}:{native_id}"
                state = "missing"
            keys.add(entity_key)
            closure.append(
                {
                    "entity_key": entity_key,
                    "source_table": table,
                    "native_id": str(native_id),
                    "state": state,
                }
            )
    return keys, closure


def _runtime_contract(row: dict[str, Any]) -> dict[str, Any]:
    fields = {
        key: value
        for key, value in sorted(row.items())
        if key in {
            "active_weapon_id",
            "auto_fire",
            "auto_reuse",
            "casting_cancelable",
            "casting_delayable",
            "channeling_cancelable",
            "channeling_tick",
            "check_obstacle",
            "check_terrain",
            "damage_type_id",
            "default_gcd",
            "effect_delay",
            "effect_repeat_count",
            "effect_repeat_tick",
            "first_reagent_only",
            "front_angle",
            "level_rule_id",
            "mana_cost",
            "melee_attack",
            "need_target",
            "targeting_type_id",
            "toggle_buff_id",
            "weapon_slot_id",
        }
    }
    return {
        "cost": row.get("cost"),
        "cooldown_time": row.get("cooldown_time"),
        "casting_time": row.get("casting_time"),
        "channeling_time": row.get("channeling_time"),
        "target_type_id": row.get("target_type_id") or row.get("targeting_type_id"),
        "min_range": row.get("min_range") or row.get("min_range_value"),
        "max_range": row.get("max_range") or row.get("max_range_value"),
        "projectile_id": row.get("projectile_id"),
        "skill_controller_id": row.get("skill_controller_id"),
        "fire_anim_id": row.get("fire_anim_id"),
        "fields": fields,
    }


def _condition_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in sorted(row.items())
        if value not in {None, 0, False, ""}
        and any(
            token in key
            for token in (
                "condition",
                "require",
                "source_buff",
                "target_buff",
                "nobuff",
                "except_buff",
                "stack_count",
                "tag_id",
            )
        )
    }


def _wiki_pages(
    config: ForensicsConfig, specialization: Specialization
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cache = specialization_wiki_cache(config, specialization)
    pages: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for metadata_path in sorted(cache.glob("*.meta.json"), key=lambda path: int(path.name.split(".")[0])):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        skill_id = int(metadata["entity_id"])
        html_path = cache / f"{skill_id}.html"
        parsed: ParsedSkillPage | None = None
        digest = metadata.get("content_sha256")
        if metadata.get("status_code") == 200 and html_path.is_file():
            if str(digest).upper() != sha256_file(html_path):
                raise ValueError(f"Wiki skill snapshot hash mismatch: {html_path}")
            parsed = parse_specialization_skill_page(
                html_path.read_bytes(), skill_id=skill_id, locale=config.wiki_locale
            )
        pages.append(
            {
                "skill_id": skill_id,
                "url": metadata["url"],
                "status_code": metadata.get("status_code"),
                "response_sha256": digest,
                "page_state": metadata["page_state"],
                "parser_version": metadata.get("parser_version"),
                "name": parsed.name if parsed else None,
                "ability": parsed.ability if parsed else None,
                "rank": parsed.rank if parsed else None,
                "mana": parsed.mana if parsed else None,
                "range_text": parsed.range_text if parsed else None,
                "sections": parsed.sections if parsed else {},
                "metadata_path": metadata_path,
            }
        )
        if parsed:
            for relation in parsed.relations:
                relations.append(
                    {
                        "src_skill_id": skill_id,
                        "relation": relation.relation,
                        "dst_kind": relation.dst_kind,
                        "dst_id": relation.dst_id,
                        "ordinal": relation.ordinal,
                        "label": relation.label,
                        "href": relation.href,
                        "context": relation.context,
                        "response_sha256": digest,
                    }
                )
    return pages, relations


def _create_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.executescript(SCHEMA)
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return connection


def _insert_metadata(connection: sqlite3.Connection, values: dict[str, Any]) -> None:
    connection.executemany(
        "INSERT INTO metadata(key,value_json) VALUES(?,?)",
        [(key, canonical_json(value)) for key, value in sorted(values.items())],
    )


def _source_artifact(
    connection: sqlite3.Connection,
    *,
    role: str,
    path: Path,
    authority: str,
    provenance: str,
) -> None:
    connection.execute(
        "INSERT INTO source_artifacts VALUES(?,?,?,?,?,?,?,?)",
        (
            stable_key("specialization_artifact", role, path.resolve().as_posix()),
            role,
            path.resolve().as_posix(),
            path.stat().st_size,
            sha256_file(path),
            authority,
            provenance,
            canonical_json({"immutable_input": True}),
        ),
    )


def _validation(
    connection: sqlite3.Connection,
    name: str,
    ok: bool,
    expected: Any,
    actual: Any,
    evidence: Any = None,
) -> None:
    connection.execute(
        "INSERT INTO validation_events VALUES(?,?,?,?,?,?)",
        (
            stable_key("specialization_validation", name),
            name,
            "confirmed" if ok else "failed",
            canonical_json(expected),
            canonical_json(actual),
            canonical_json(evidence or {}),
        ),
    )


def _write_csv(path: Path, fields: tuple[str, ...], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(handle)
    temporary = Path(name)
    try:
        with temporary.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    return {name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in names}


def build_specialization_graph(
    config: ForensicsConfig, specialization_value: str | int
) -> dict[str, Any]:
    specialization = resolve_specialization(specialization_value)
    paths = specialization_paths(config, specialization)
    if not paths["wiki_manifest"].is_file():
        raise FileNotFoundError(
            f"Freeze specialization wiki first: {paths['wiki_manifest']}"
        )
    catalog_path, catalog = _catalog()
    ability_table_ids = catalog["ability_table_ids"].get(str(specialization.ability_id))
    if not ability_table_ids:
        raise ValueError(f"Native combat catalog has no ability {specialization.ability_id}")
    roots, passive_ids = _native_roots(config, specialization)
    by_table_id, by_entity = _stage_rows(config, ability_table_ids)
    actual_edges, external_entities = _graph_edges(config, set(by_entity))
    wiki_pages, wiki_relations = _wiki_pages(config, specialization)
    wiki_by_id = {row["skill_id"]: row for row in wiki_pages}
    skill_table_ids = catalog["skill_table_ids"]
    native_skill_rows: dict[int, dict[str, Any]] = {}
    stage50 = _open_read_only(config.stage_50)
    try:
        for row in stage50.execute(
            "SELECT native_id,row_json,state,entity_key FROM native_rows WHERE source_table='skills' ORDER BY CAST(native_id AS INTEGER)"
        ):
            native_skill_rows[int(row["native_id"])] = {
                "row": json.loads(row["row_json"]),
                "state": row["state"],
                "entity_key": row["entity_key"],
            }
    finally:
        stage50.close()
    temporary = paths["database"].with_name(f".{paths['database'].name}.building")
    connection = _create_database(temporary)
    try:
        _insert_metadata(
            connection,
            {
                "authority_order": [
                    "stage50_client_native",
                    "stage60_client_assets",
                    "consolidated_native_graph",
                    "wiki_corroboration",
                    "server_observed",
                ],
                "client_build": config.client_build,
                "closure_policy": {
                    "catalog_is_candidate_index": True,
                    "stage50_revalidates_every_native_row": True,
                    "wiki_can_create_native_membership": False,
                    "unknown_is_terminal_when_audited": True,
                },
                "schema_version": SCHEMA_VERSION,
                "specialization": {
                    "ability_id": specialization.ability_id,
                    "slug": specialization.slug,
                    "name": specialization.name,
                },
                "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            },
        )
        for role, path, authority, provenance in (
            ("stage50_skills", config.stage_50, "client_native", "stage50"),
            ("stage60_assets", config.stage_60, "client_native", "stage60"),
            ("stage70_wiki", config.stage_70, WIKI_AUTHORITY, "stage70"),
            ("stage90_closure", config.stage_90, "client_native", "stage90"),
            ("consolidated", config.consolidated, "client_native", "stage80"),
            ("native_combat_candidate_index", catalog_path, "derived_native", "native_combat_v1"),
            ("wiki_snapshot_manifest", paths["wiki_manifest"], WIKI_AUTHORITY, WIKI_PROVENANCE),
            ("builder", Path(__file__).resolve(), "client_forensics", "python_source"),
        ):
            _source_artifact(
                connection,
                role=role,
                path=path,
                authority=authority,
                provenance=provenance,
            )
        root_rows: dict[int, dict[str, Any]] = {}
        for skill_id in roots:
            source = by_table_id.get(("skills", skill_id)) or native_skill_rows[skill_id]
            row = source.get("decoded") or source["row"]
            state = source.get("state", "confirmed")
            root_rows[skill_id] = row
            connection.execute(
                "INSERT INTO specialization_roots VALUES(?,?,?,?,?,?,?,?)",
                (
                    stable_key("specialization_root", "skill", skill_id),
                    "skill",
                    skill_id,
                    specialization.ability_id,
                    "exact_native_root",
                    state,
                    canonical_json(row),
                    canonical_json({"predicate": f"skills.ability_id={specialization.ability_id}"}),
                ),
            )
        for passive_id in passive_ids:
            source = by_table_id.get(("passive_buffs", passive_id))
            row = source["decoded"] if source else {}
            connection.execute(
                "INSERT INTO specialization_roots VALUES(?,?,?,?,?,?,?,?)",
                (
                    stable_key("specialization_root", "passive_buff", passive_id),
                    "passive_buff",
                    passive_id,
                    specialization.ability_id,
                    "exact_native_root",
                    source["state"] if source else "missing",
                    canonical_json(row),
                    canonical_json({"predicate": f"passive_buffs.ability_id={specialization.ability_id}"}),
                ),
            )
        candidate_skill_ids = sorted(set(roots) | set(wiki_by_id))
        for skill_id in candidate_skill_ids:
            native = native_skill_rows.get(skill_id)
            wiki = wiki_by_id.get(skill_id)
            if skill_id in roots:
                membership = "exact_native_root"
            elif native and int(native["row"].get("ability_id") or 0) == specialization.ability_id:
                membership = "native_internal_dependency"
            elif native:
                membership = "native_other_specialization"
            elif wiki and str(wiki.get("ability") or "").casefold() == specialization.name.casefold():
                membership = "wiki_variant_candidate"
            else:
                membership = "wiki_only"
            row = native["row"] if native else None
            connection.execute(
                "INSERT INTO specialization_skills VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    skill_id,
                    int(row.get("ability_id") or 0) if row else None,
                    int(skill_id in roots),
                    int(row.get("show") or 0) if row else None,
                    row.get("name") if row else None,
                    wiki.get("name") if wiki else None,
                    "present" if native else "wiki_only",
                    membership,
                    native["state"] if native else "unknown",
                    canonical_json(row) if row else None,
                    canonical_json({"wiki_is_corroborative": True}),
                ),
            )
        actual_by_src: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in actual_edges:
            actual_by_src[edge["src_entity_key"]].append(edge)
        root_closure_members: dict[int, set[str]] = {}
        for skill_id in roots:
            ids = skill_table_ids.get(str(skill_id), {"skills": [skill_id]})
            members, catalog_closure = _root_members(skill_id, ids, by_table_id)
            root_closure_members[skill_id] = members
            depths: dict[str, int] = {f"skill:{skill_id}": 0}
            queue = deque(sorted(members))
            for member in sorted(catalog_closure, key=lambda value: (value["source_table"], int(value["native_id"]))):
                depth = 0 if member["entity_key"] == f"skill:{skill_id}" else 1
                depths[member["entity_key"]] = min(depths.get(member["entity_key"], depth), depth)
                connection.execute(
                    "INSERT OR IGNORE INTO dependency_closure VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        stable_key("specialization_closure", skill_id, member["entity_key"]),
                        skill_id,
                        depth,
                        member["entity_key"],
                        member["source_table"],
                        member["native_id"],
                        member["state"],
                        "stage50_row_missing" if member["state"] == "missing" else None,
                        canonical_json({"algorithm": "native_combat_fixed_point_revalidated_stage50"}),
                    ),
                )
            visited: set[str] = set()
            while queue:
                src = queue.popleft()
                if src in visited:
                    continue
                visited.add(src)
                for edge in actual_by_src.get(src, []):
                    dst = edge["dst_entity_key"]
                    depth = min(depths.get(src, 1) + 1, 99)
                    if dst not in depths or depth < depths[dst]:
                        depths[dst] = depth
                        if edge["dst_kind"] in EXPAND_KINDS:
                            queue.append(dst)
                    connection.execute(
                        "INSERT OR IGNORE INTO dependency_edges VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            stable_key("specialization_edge", skill_id, edge["relation_key"]),
                            skill_id,
                            edge["src_entity_key"],
                            edge["relation"],
                            dst,
                            edge["state"],
                            int(edge["required"]),
                            edge["authority"],
                            edge["locator"],
                            edge["loader_or_consumer"],
                            edge["provenance"],
                            edge["evidence_json"],
                        ),
                    )
                    destination = external_entities.get(dst, {})
                    connection.execute(
                        "INSERT OR IGNORE INTO dependency_closure VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            stable_key("specialization_closure", skill_id, dst),
                            skill_id,
                            depth,
                            dst,
                            None,
                            destination.get("native_id"),
                            destination.get("state", edge["state"]),
                            None,
                            canonical_json({"algorithm": "consolidated_relation_expansion"}),
                        ),
                    )
            row = root_rows[skill_id]
            contract = _runtime_contract(row)
            connection.execute(
                "INSERT INTO skill_runtime_contracts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    skill_id,
                    contract["cost"],
                    contract["cooldown_time"],
                    contract["casting_time"],
                    contract["channeling_time"],
                    contract["target_type_id"],
                    contract["min_range"],
                    contract["max_range"],
                    contract["projectile_id"],
                    contract["skill_controller_id"],
                    contract["fire_anim_id"],
                    "confirmed",
                    canonical_json(contract["fields"]),
                    "stage50_client_native",
                    canonical_json({"row_preserved_in_specialization_skills": True}),
                ),
            )
            for ordinal, effect_id in enumerate(ids.get("skill_effects", []), 1):
                source = by_table_id.get(("skill_effects", int(effect_id)))
                if not source:
                    continue
                effect_row = source["decoded"]
                concrete_id = int(effect_row.get("effect_id") or 0)
                concrete = by_table_id.get(("effects", concrete_id))
                concrete_row = concrete["decoded"] if concrete else {}
                flags = {
                    key: effect_row.get(key)
                    for key in ("friendly", "non_friendly", "front", "back", "always_hit")
                }
                connection.execute(
                    "INSERT INTO skill_effect_steps VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        stable_key("skill_effect_step", skill_id, effect_id),
                        skill_id,
                        int(effect_id),
                        concrete_id,
                        concrete_row.get("actual_type"),
                        ordinal,
                        effect_row.get("chance"),
                        effect_row.get("application_method_id"),
                        canonical_json(flags),
                        source["state"],
                        canonical_json(effect_row),
                        canonical_json({"effect_row_state": concrete["state"] if concrete else "missing"}),
                    ),
                )
                conditions = _condition_fields(effect_row)
                if conditions:
                    connection.execute(
                        "INSERT OR IGNORE INTO combo_conditions VALUES(?,?,?,?,?,?,?,?)",
                        (
                            stable_key("combo_condition", skill_id, "skill_effects", effect_id),
                            skill_id,
                            "skill_effects",
                            int(effect_id),
                            "native_skill_effect_gate",
                            source["state"],
                            canonical_json(conditions),
                            canonical_json({"wiki_not_authoritative": True}),
                        ),
                    )
            for buff_id in ids.get("buffs", []):
                source = by_table_id.get(("buffs", int(buff_id)))
                connection.execute(
                    "INSERT INTO buff_contracts VALUES(?,?,?,?,?,?,?)",
                    (
                        stable_key("buff_contract", skill_id, buff_id),
                        skill_id,
                        int(buff_id),
                        "native_fixed_point_member",
                        source["state"] if source else "missing",
                        canonical_json(source["decoded"] if source else {}),
                        canonical_json({"source_table": "buffs"}),
                    ),
                )
            for table in ("plot_conditions", "plot_event_conditions"):
                for native_id in ids.get(table, []):
                    source = by_table_id.get((table, int(native_id)))
                    connection.execute(
                        "INSERT INTO combo_conditions VALUES(?,?,?,?,?,?,?,?)",
                        (
                            stable_key("combo_condition", skill_id, table, native_id),
                            skill_id,
                            table,
                            int(native_id),
                            "native_plot_condition",
                            source["state"] if source else "missing",
                            canonical_json(source["decoded"] if source else {}),
                            canonical_json({"consumer": "plot_runtime"}),
                        ),
                    )
            for table in ("plot_effects", "buff_triggers", "buff_tick_effects"):
                for native_id in ids.get(table, []):
                    source = by_table_id.get((table, int(native_id)))
                    connection.execute(
                        "INSERT INTO combo_outcomes VALUES(?,?,?,?,?,?,?,?)",
                        (
                            stable_key("combo_outcome", skill_id, table, native_id),
                            skill_id,
                            table,
                            int(native_id),
                            "native_plot_or_buff_outcome",
                            source["state"] if source else "missing",
                            canonical_json(source["decoded"] if source else {}),
                            canonical_json({"wiki_not_authoritative": True}),
                        ),
                    )
            for table, kind in PRESENTATION_TABLES.items():
                for native_id in ids.get(table, []):
                    source = by_table_id.get((table, int(native_id)))
                    connection.execute(
                        "INSERT OR IGNORE INTO presentation_bindings VALUES(?,?,?,?,?,?,?,?)",
                        (
                            stable_key("presentation", skill_id, table, native_id),
                            skill_id,
                            kind,
                            int(native_id),
                            "native_fixed_point_member",
                            source["state"] if source else "missing",
                            canonical_json(source["decoded"]) if source else None,
                            canonical_json({"source_table": table}),
                        ),
                    )
            for field, kind in (("icon_id", "icon"), ("fx_group_id", "fx")):
                native_id = int(row.get(field) or 0)
                if native_id:
                    connection.execute(
                        "INSERT OR IGNORE INTO presentation_bindings VALUES(?,?,?,?,?,?,?,?)",
                        (
                            stable_key("presentation", skill_id, field, native_id),
                            skill_id,
                            kind,
                            native_id,
                            f"skills.{field}",
                            "confirmed",
                            None,
                            canonical_json({"source_table": "skills", "field": field}),
                        ),
                    )
            for field, value in sorted(row.items()):
                if field.endswith("_anim_id") and int(value or 0):
                    connection.execute(
                        "INSERT OR IGNORE INTO presentation_bindings VALUES(?,?,?,?,?,?,?,?)",
                        (
                            stable_key("presentation", skill_id, field, int(value)),
                            skill_id,
                            "animation",
                            int(value),
                            f"skills.{field}",
                            "confirmed",
                            None,
                            canonical_json({"source_table": "skills", "field": field}),
                        ),
                    )
        for page in sorted(wiki_pages, key=lambda value: value["skill_id"]):
            connection.execute(
                "INSERT INTO wiki_skill_pages VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    page["skill_id"],
                    page["url"],
                    page["status_code"],
                    page["response_sha256"],
                    page["page_state"],
                    page["parser_version"],
                    page["name"],
                    page["ability"],
                    page["rank"],
                    page["mana"],
                    page["range_text"],
                    canonical_json(page["sections"]),
                    canonical_json({"authority": WIKI_AUTHORITY, "metadata_path": page["metadata_path"].resolve().as_posix()}),
                ),
            )
        for relation in sorted(
            wiki_relations,
            key=lambda value: (
                value["src_skill_id"],
                value["relation"],
                value["ordinal"],
                value["dst_kind"],
                value["dst_id"],
            ),
        ):
            key = stable_key(
                "wiki_skill_relation",
                relation["src_skill_id"],
                relation["relation"],
                relation["dst_kind"],
                relation["dst_id"],
                relation["ordinal"],
            )
            connection.execute(
                "INSERT INTO wiki_skill_relations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    key,
                    relation["src_skill_id"],
                    relation["relation"],
                    relation["dst_kind"],
                    relation["dst_id"],
                    relation["ordinal"],
                    relation["label"],
                    relation["href"],
                    relation["context"],
                    relation["response_sha256"],
                    "corroborated",
                    canonical_json({"raw_href_preserved": True}),
                ),
            )
            destination = native_skill_rows.get(relation["dst_id"]) if relation["dst_kind"] == "skill" else None
            if relation["dst_kind"] != "skill":
                resolution = "unresolved"
                resolved = None
            elif relation["dst_id"] in roots:
                resolution = "exact_native_root"
                resolved = relation["dst_id"]
            elif destination and int(destination["row"].get("ability_id") or 0) == specialization.ability_id:
                resolution = "native_internal_dependency"
                resolved = relation["dst_id"]
            elif destination:
                resolution = "native_other_specialization"
                resolved = relation["dst_id"]
            elif relation["relation"] == "variant_skill":
                resolution = "wiki_variant_candidate"
                resolved = None
            else:
                resolution = "wiki_only"
                resolved = None
            connection.execute(
                "INSERT INTO wiki_skill_resolutions VALUES(?,?,?,?,?,?,?,?)",
                (
                    stable_key("wiki_skill_resolution", key),
                    relation["src_skill_id"],
                    relation["relation"],
                    relation["dst_kind"],
                    relation["dst_id"],
                    resolved,
                    resolution,
                    canonical_json({"wiki_cannot_create_native_relation": True}),
                ),
            )
        statuses = {int(row["skill_id"]): row for row in catalog.get("skill_status", [])}
        for skill_id in roots:
            status = statuses.get(skill_id, {})
            connection.execute(
                "INSERT INTO downstream_implementation_audit VALUES(?,?,?,?,?,?)",
                (
                    stable_key("downstream_skill_audit", skill_id),
                    skill_id,
                    status.get("status", "unknown"),
                    status.get("reason") or None,
                    "server_observed",
                    canonical_json({"source": "native-combat-catalog-v1", "does_not_change_native_state": True}),
                ),
            )
        areas = (
            "targeting",
            "cost_cooldown",
            "animation_projectile",
            "effects",
            "buff_lifecycle",
            "combos",
            "cast_channel_toggle",
            "chained_skills",
            "assets_localization",
        )
        for skill_id in roots:
            ids = skill_table_ids.get(str(skill_id), {})
            row = root_rows[skill_id]
            states = {
                "targeting": "confirmed",
                "cost_cooldown": "confirmed",
                "animation_projectile": "confirmed" if ids.get("anims") or row.get("fire_anim_id") else "not_applicable",
                "effects": "confirmed" if ids.get("skill_effects") else "not_applicable",
                "buff_lifecycle": "confirmed" if ids.get("buffs") else "not_applicable",
                "combos": "confirmed" if ids.get("plot_conditions") or _condition_fields(row) else "not_applicable",
                "cast_channel_toggle": "confirmed",
                "chained_skills": "confirmed" if len(ids.get("skills", [])) > 1 else "not_applicable",
                "assets_localization": "confirmed" if row.get("icon_id") or row.get("fx_group_id") else "unknown",
            }
            for area in areas:
                state = states[area]
                connection.execute(
                    "INSERT INTO reconstruction_test_cases VALUES(?,?,?,?,?,?)",
                    (
                        stable_key("reconstruction_test", skill_id, area),
                        skill_id,
                        area,
                        state,
                        canonical_json({"native_skill_id": skill_id, "area": area, "expected_state": state}),
                        canonical_json({"authority": "client_native", "wiki_not_oracle": True}),
                    ),
                )
                if state in {"unknown", "missing", "blocked", "opaque"}:
                    connection.execute(
                        "INSERT OR IGNORE INTO audit_queue VALUES(?,?,?,?,?,?,?,?)",
                        (
                            stable_key("specialization_audit", skill_id, area),
                            skill_id,
                            f"{area}_{state}",
                            f"skill:{skill_id}",
                            "medium",
                            state,
                            f"Resolve the native {area} evidence before runtime reconstruction",
                            canonical_json({"terminal_classification": True}),
                        ),
                    )
        missing_rows = connection.execute(
            "SELECT COUNT(*) FROM dependency_closure WHERE state='missing'"
        ).fetchone()[0]
        visible_count = sum(int(root_rows[value].get("show") or 0) != 0 for value in roots)
        expected = EXPECTED_SHADOWPLAY if specialization.ability_id == 8 else None
        _validation(connection, "native_skill_roots", expected is None or len(roots) == expected["skills"], expected["skills"] if expected else len(roots), len(roots))
        _validation(connection, "native_visible_roots", expected is None or visible_count == expected["visible"], expected["visible"] if expected else visible_count, visible_count)
        _validation(connection, "native_passive_roots", expected is None or len(passive_ids) == expected["passives"], expected["passives"] if expected else len(passive_ids), len(passive_ids))
        _validation(connection, "candidate_rows_revalidated", missing_rows == 0, 0, missing_rows)
        terminal_failures = connection.execute(
            "SELECT COUNT(*) FROM reconstruction_test_cases WHERE expected_state NOT IN ('confirmed','corroborated','missing','tombstone','blocked','unknown','not_applicable','opaque')"
        ).fetchone()[0]
        _validation(connection, "all_root_dimensions_terminal", terminal_failures == 0, 0, terminal_failures)
        if specialization.ability_id == 8:
            stealth_root = connection.execute(
                "SELECT root_member,membership_state FROM specialization_skills WHERE skill_id=10082"
            ).fetchone()
            _validation(
                connection,
                "wiki_10082_not_promoted",
                stealth_root is not None and stealth_root[0] == 0 and stealth_root[1] in {"wiki_variant_candidate", "wiki_only"},
                {"root_member": 0, "membership": ["wiki_variant_candidate", "wiki_only"]},
                dict(stealth_root) if stealth_root else None,
            )
            shadow_strike = connection.execute(
                "SELECT COUNT(*) FROM specialization_roots WHERE root_kind='skill' AND native_id=36594"
            ).fetchone()[0]
            audit_36594 = connection.execute(
                "SELECT observed_state,reason FROM downstream_implementation_audit WHERE skill_id=36594"
            ).fetchone()
            _validation(connection, "native_36594_preserved", shadow_strike == 1, 1, shadow_strike)
            _validation(
                connection,
                "native_36594_server_gap_separate",
                audit_36594 is not None and audit_36594[0] == "quarantined",
                "quarantined",
                dict(audit_36594) if audit_36594 else None,
            )
        connection.commit()
        connection.execute("VACUUM")
        connection.execute("PRAGMA optimize")
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        counts = _table_counts(connection)
    finally:
        connection.close()
    temporary.replace(paths["database"])
    db = _open_read_only(paths["database"])
    try:
        summary = {
            "ability_id": specialization.ability_id,
            "specialization": specialization.name,
            "schema_version": SCHEMA_VERSION,
            "tool_version": TOOL_VERSION,
            "root_skills": len(roots),
            "visible_skills": sum(int(root_rows[value].get("show") or 0) != 0 for value in roots),
            "passive_buffs": len(passive_ids),
            "table_counts": counts,
            "validation_states": dict(db.execute("SELECT state,COUNT(*) FROM validation_events GROUP BY state ORDER BY state")),
            "wiki_resolution_states": dict(db.execute("SELECT resolution_state,COUNT(*) FROM wiki_skill_resolutions GROUP BY resolution_state ORDER BY resolution_state")),
            "test_states": dict(db.execute("SELECT expected_state,COUNT(*) FROM reconstruction_test_cases GROUP BY expected_state ORDER BY expected_state")),
            "quick_check": quick,
            "integrity_check": integrity,
        }
        gaps = [dict(row) for row in db.execute("SELECT * FROM audit_queue ORDER BY severity,root_skill_id,audit_key")]
        tests = [dict(row) for row in db.execute("SELECT skill_id,area,expected_state,oracle_json,evidence_json FROM reconstruction_test_cases ORDER BY skill_id,area")]
        viewer_skills = [dict(row) for row in db.execute("SELECT skill_id,root_member,visible,native_name,wiki_name,membership_state,native_state FROM specialization_skills ORDER BY root_member DESC,skill_id")]
    finally:
        db.close()
    atomic_text(paths["summary"], canonical_json(summary, pretty=True))
    _write_csv(paths["gaps"], ("audit_key", "root_skill_id", "blocker_kind", "blocked_entity_key", "severity", "state", "recommended_action", "evidence_json"), gaps)
    _write_csv(paths["tests"], ("skill_id", "area", "expected_state", "oracle_json", "evidence_json"), tests)
    viewer_payload = canonical_json({"summary": summary, "skills": viewer_skills})
    atomic_text(
        paths["viewer"],
        "<!doctype html><meta charset='utf-8'><title>"
        + specialization.name
        + " specialization graph</title><style>body{font:14px system-ui;margin:2rem;background:#10151d;color:#e8eef7}input{padding:.5rem;width:24rem}table{border-collapse:collapse;margin-top:1rem}td,th{padding:.35rem .6rem;border:1px solid #445}</style><h1>"
        + specialization.name
        + " specialization graph V1</h1><input id=q placeholder='skill, name or state'><pre id=s></pre><table><thead><tr><th>ID</th><th>Root</th><th>Visible</th><th>Native name</th><th>Wiki name</th><th>Membership</th><th>State</th></tr></thead><tbody id=b></tbody></table><script>const D="
        + viewer_payload.replace("<", "\\u003c")
        + ";const q=document.querySelector('#q'),b=document.querySelector('#b');document.querySelector('#s').textContent=JSON.stringify(D.summary,null,2);function r(){const x=q.value.toLowerCase();b.innerHTML=D.skills.filter(v=>JSON.stringify(v).toLowerCase().includes(x)).map(v=>`<tr><td>${v.skill_id}</td><td>${v.root_member}</td><td>${v.visible??''}</td><td>${v.native_name??''}</td><td>${v.wiki_name??''}</td><td>${v.membership_state}</td><td>${v.native_state}</td></tr>`).join('')}q.oninput=r;r()</script>",
    )
    source_paths = {
        "stage50": config.stage_50,
        "stage60": config.stage_60,
        "stage70": config.stage_70,
        "stage90": config.stage_90,
        "consolidated": config.consolidated,
        "catalog": catalog_path,
        "wiki_manifest": paths["wiki_manifest"],
        "builder": Path(__file__).resolve(),
    }
    output_paths = {
        key: paths[key]
        for key in ("database", "summary", "gaps", "tests", "viewer")
    }
    manifest = {
        "authority": "client_forensics_only",
        "client_build": config.client_build,
        "commands": [
            f"python -B -m client_forensics freeze-specialization-wiki {specialization.slug} --resume",
            f"python -B -m client_forensics build-specialization-graph {specialization.slug}",
            f"python -B -m client_forensics validate-specialization-graph {specialization.slug}",
        ],
        "determinism": {
            "atomic_output": True,
            "stable_ordering": True,
            "timestamps_in_reproducible_outputs": False,
        },
        "inputs": {
            key: {
                "path": path.resolve().as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for key, path in sorted(source_paths.items())
        },
        "outputs": {
            key: {
                "path": path.resolve().as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for key, path in sorted(output_paths.items())
        },
        "parser_version": PARSER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }
    atomic_text(paths["manifest"], canonical_json(manifest, pretty=True))
    return {
        "database": paths["database"],
        "manifest": paths["manifest"],
        "summary": summary,
        "outputs": manifest["outputs"],
    }


def validate_specialization_graph(
    config: ForensicsConfig, specialization_value: str | int
) -> dict[str, Any]:
    specialization = resolve_specialization(specialization_value)
    paths = specialization_paths(config, specialization)
    for key in ("database", "manifest", "summary", "gaps", "tests", "viewer", "wiki_manifest"):
        if not paths[key].is_file():
            raise FileNotFoundError(paths[key])
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    output_mismatches = []
    for key, record in manifest["outputs"].items():
        path = Path(record["path"])
        actual = sha256_file(path)
        if actual != record["sha256"]:
            output_mismatches.append({"key": key, "expected": record["sha256"], "actual": actual})
    input_mismatches = []
    for key, record in manifest["inputs"].items():
        path = Path(record["path"])
        actual = sha256_file(path)
        if actual != record["sha256"]:
            input_mismatches.append({"key": key, "expected": record["sha256"], "actual": actual})
    connection = _open_read_only(paths["database"])
    try:
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        failed = connection.execute("SELECT COUNT(*) FROM validation_events WHERE state<>'confirmed'").fetchone()[0]
        roots = connection.execute("SELECT COUNT(*) FROM specialization_roots WHERE root_kind='skill'").fetchone()[0]
        passives = connection.execute("SELECT COUNT(*) FROM specialization_roots WHERE root_kind='passive_buff'").fetchone()[0]
        unresolved_orphans = connection.execute("SELECT COUNT(*) FROM dependency_closure WHERE state IS NULL OR state='' ").fetchone()[0]
        tests = connection.execute("SELECT COUNT(*) FROM reconstruction_test_cases").fetchone()[0]
        result = {
            "quick_check": quick,
            "integrity_check": integrity,
            "failed_validation_events": failed,
            "root_skills": roots,
            "passive_buffs": passives,
            "reconstruction_test_cases": tests,
            "unclassified_closure_rows": unresolved_orphans,
            "input_hash_mismatches": input_mismatches,
            "output_hash_mismatches": output_mismatches,
        }
    finally:
        connection.close()
    ok = (
        quick == "ok"
        and integrity == "ok"
        and failed == 0
        and unresolved_orphans == 0
        and not input_mismatches
        and not output_mismatches
    )
    if specialization.ability_id == 8:
        ok = ok and roots == 28 and passives == 6 and tests == 28 * 9
    result["status"] = "confirmed" if ok else "failed"
    if not ok:
        raise ValueError(canonical_json(result, pretty=True))
    return result


def freeze_specialization_wiki_suite(
    config: ForensicsConfig,
    specialization_values: str | Iterable[str | int] | None = None,
    *,
    resume: bool = True,
    delay: float = MINIMUM_DELAY,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    specializations = resolve_specialization_suite(specialization_values)
    records = []
    for specialization in specializations:
        if progress:
            progress(f"specialization-suite wiki {specialization.ability_id}:{specialization.slug}")
        result = freeze_specialization_wiki(
            config,
            specialization.slug,
            resume=resume,
            delay=delay,
            progress=progress,
        )
        wiki_path = specialization_paths(config, specialization)["wiki_manifest"]
        serializable_result = dict(result)
        serializable_result["manifest"] = wiki_path.resolve().as_posix()
        records.append(
            {
                "ability_id": specialization.ability_id,
                "specialization": specialization.name,
                "slug": specialization.slug,
                "manifest_path": wiki_path.resolve().as_posix(),
                "manifest_sha256": sha256_file(wiki_path),
                "result": serializable_result,
            }
        )
    manifest = {
        "authority": WIKI_AUTHORITY,
        "client_build": config.client_build,
        "format": "AA8_SPECIALIZATION_WIKI_SUITE_V1",
        "records": records,
        "selection": [row.slug for row in specializations],
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }
    path = specialization_suite_paths(config)["wiki_manifest"]
    atomic_text(path, canonical_json(manifest, pretty=True))
    return {
        "manifest": path,
        "manifest_sha256": sha256_file(path),
        "specialization_count": len(records),
    }


def _specialization_suite_record(
    config: ForensicsConfig, specialization: Specialization
) -> dict[str, Any]:
    paths = specialization_paths(config, specialization)
    connection = _open_read_only(paths["database"])
    try:
        root_states = dict(
            connection.execute(
                "SELECT native_state,COUNT(*) FROM specialization_skills "
                "WHERE root_member=1 GROUP BY native_state ORDER BY native_state"
            )
        )
        runtime_states = dict(
            connection.execute(
                "SELECT observed_state,COUNT(*) FROM downstream_implementation_audit "
                "GROUP BY observed_state ORDER BY observed_state"
            )
        )
        test_states = dict(
            connection.execute(
                "SELECT expected_state,COUNT(*) FROM reconstruction_test_cases "
                "GROUP BY expected_state ORDER BY expected_state"
            )
        )
        blockers = dict(
            connection.execute(
                "SELECT blocker_kind,COUNT(*) FROM audit_queue "
                "GROUP BY blocker_kind ORDER BY blocker_kind"
            )
        )
        roots = connection.execute(
            "SELECT COUNT(*) FROM specialization_roots WHERE root_kind='skill'"
        ).fetchone()[0]
        visible = connection.execute(
            "SELECT COUNT(*) FROM specialization_skills WHERE root_member=1 AND visible=1"
        ).fetchone()[0]
        passives = connection.execute(
            "SELECT COUNT(*) FROM specialization_roots WHERE root_kind='passive_buff'"
        ).fetchone()[0]
        cases = connection.execute(
            "SELECT COUNT(*) FROM reconstruction_test_cases"
        ).fetchone()[0]
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        connection.close()
    return {
        "ability_id": specialization.ability_id,
        "artifacts": {
            key: {
                "path": path.resolve().as_posix(),
                "sha256": sha256_file(path),
            }
            for key, path in sorted(paths.items())
            if path.is_file()
        },
        "audit_blockers": blockers,
        "integrity_check": integrity,
        "passive_buffs": passives,
        "quick_check": quick,
        "reconstruction_test_cases": cases,
        "root_native_states": root_states,
        "root_skills": roots,
        "runtime_observed_states": runtime_states,
        "slug": specialization.slug,
        "specialization": specialization.name,
        "test_states": test_states,
        "visible_skills": visible,
    }


def build_specialization_graph_suite(
    config: ForensicsConfig,
    specialization_values: str | Iterable[str | int] | None = None,
    *,
    build_graphs: bool = True,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    specializations = resolve_specialization_suite(specialization_values)
    records = []
    for specialization in specializations:
        if progress:
            progress(f"specialization-suite graph {specialization.ability_id}:{specialization.slug}")
        if build_graphs:
            build_specialization_graph(config, specialization.slug)
        validate_specialization_graph(config, specialization.slug)
        records.append(_specialization_suite_record(config, specialization))
    aggregate = {
        "passive_buffs": sum(int(row["passive_buffs"]) for row in records),
        "reconstruction_test_cases": sum(int(row["reconstruction_test_cases"]) for row in records),
        "root_skills": sum(int(row["root_skills"]) for row in records),
        "visible_skills": sum(int(row["visible_skills"]) for row in records),
    }
    index = {
        "aggregate": aggregate,
        "authority": "client_forensics_only",
        "client_build": config.client_build,
        "format": "AA8_SPECIALIZATION_SUITE_V1",
        "records": records,
        "selection": [row.slug for row in specializations],
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "wiki_authority": WIKI_AUTHORITY,
    }
    suite_paths = specialization_suite_paths(config)
    atomic_text(suite_paths["index"], canonical_json(index, pretty=True))
    manifest_inputs = {
        row["slug"]: row["artifacts"]["manifest"]
        for row in records
    }
    manifest = {
        "client_build": config.client_build,
        "determinism": {
            "stable_ordering": True,
            "timestamps_in_reproducible_outputs": False,
        },
        "format": "AA8_SPECIALIZATION_SUITE_MANIFEST_V1",
        "inputs": manifest_inputs,
        "output": {
            "path": suite_paths["index"].resolve().as_posix(),
            "sha256": sha256_file(suite_paths["index"]),
        },
        "selection": index["selection"],
        "tool": index["tool"],
    }
    atomic_text(suite_paths["manifest"], canonical_json(manifest, pretty=True))
    return {
        "aggregate": aggregate,
        "index": suite_paths["index"],
        "index_sha256": sha256_file(suite_paths["index"]),
        "manifest": suite_paths["manifest"],
        "manifest_sha256": sha256_file(suite_paths["manifest"]),
        "specialization_count": len(records),
    }


def validate_specialization_graph_suite(
    config: ForensicsConfig,
    specialization_values: str | Iterable[str | int] | None = None,
) -> dict[str, Any]:
    specializations = resolve_specialization_suite(specialization_values)
    paths = specialization_suite_paths(config)
    if not paths["index"].is_file() or not paths["manifest"].is_file():
        raise FileNotFoundError("The specialization suite index has not been built")
    index = json.loads(paths["index"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    expected_selection = [row.slug for row in specializations]
    output_hash = sha256_file(paths["index"])
    output_match = output_hash == manifest["output"]["sha256"]
    selection_match = index["selection"] == expected_selection == manifest["selection"]
    input_mismatches = []
    validations = {}
    for specialization in specializations:
        record = manifest["inputs"].get(specialization.slug)
        if record is None:
            input_mismatches.append({"slug": specialization.slug, "reason": "missing_manifest_input"})
            continue
        actual = sha256_file(Path(record["path"]))
        if actual != record["sha256"]:
            input_mismatches.append(
                {"slug": specialization.slug, "expected": record["sha256"], "actual": actual}
            )
        validations[specialization.slug] = validate_specialization_graph(
            config, specialization.slug
        )
    records_match = [int(row["ability_id"]) for row in index["records"]] == [
        row.ability_id for row in specializations
    ]
    ok = output_match and selection_match and records_match and not input_mismatches
    result = {
        "input_mismatches": input_mismatches,
        "output_hash_match": output_match,
        "records_match": records_match,
        "selection_match": selection_match,
        "specialization_count": len(specializations),
        "status": "confirmed" if ok else "failed",
        "validations": validations,
    }
    if not ok:
        raise ValueError(canonical_json(result, pretty=True))
    return result
