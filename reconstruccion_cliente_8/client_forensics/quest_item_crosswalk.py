from __future__ import annotations

import csv
import hashlib
import http.client
import json
import os
import re
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urljoin, urlsplit
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable

from . import TOOL_NAME, TOOL_VERSION
from .config import ForensicsConfig
from .util import atomic_text, canonical_json, sha256_file, sha256_text, stable_key


PARSER_VERSION = "quest-item-structured-v1"
SCHEMA_VERSION = 1
WIKI_AUTHORITY = "external_corroborative"
WIKI_PROVENANCE = "wiki.archerage.to_visible_database"
USER_AGENT = (
    "AAEmu-Client-Forensics/0.36 "
    "(local compatibility research; robots-aware)"
)
MINIMUM_DELAY = 1.0
KNOWN_STAGE_40_SHA256 = (
    "0BB127E819232BFEE6D6559000E845B8C36E7F4C56A5ED64234DCD28B793D72C"
)
KNOWN_BASELINES = {
    "QuestActSupplyItem": 5640,
    "QuestActSupplySelectiveItem": 552,
    "QuestActSupplyRankedItem": 23,
    "QuestActSupplyResultRankedItem": 5,
    "candidate_quests": 4293,
    "quest_act_supply_items_orphans": 4,
}
GRANT_TABLES = {
    "QuestActSupplyItem": "quest_act_supply_items",
    "QuestActSupplySelectiveItem": "quest_act_supply_selective_items",
    "QuestActSupplyRankedItem": "quest_act_supply_ranked_items",
    "QuestActSupplyResultRankedItem": "quest_act_supply_result_ranked_items",
}
SELECTION_MODES = {
    "QuestActSupplyItem": "fixed",
    "QuestActSupplySelectiveItem": "selective",
    "QuestActSupplyRankedItem": "ranked",
    "QuestActSupplyResultRankedItem": "result_ranked",
}
SECTION_KINDS = {
    "quest_item",
    "fixed_reward",
    "selective_reward",
    "ranked_reward",
    "objective_item",
    "requirement_item",
    "other_visible_item",
    "unknown_section",
}
OVERALL_STATES = {
    "match",
    "native_only",
    "wiki_only",
    "wiki_detail_missing",
    "wiki_parse_failed",
    "role_conflict",
    "count_conflict",
    "ambiguous_many_to_many",
    "blocked",
}
TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}
SPACE = re.compile(r"\s+")
ITEM_LINK = re.compile(r"^/(?P<locale>[^/]+)/db/items/(?P<id>\d+)(?:[/?#].*)?$")
VISIBLE_COUNT = re.compile(r"^\s*(?P<count>\d[\d,]*)\s+")
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


CROSSWALK_SCHEMA = """
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

CREATE TABLE quest_item_grants (
    grant_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    component_kind_id INTEGER NOT NULL,
    grant_phase TEXT NOT NULL,
    quest_act_id INTEGER NOT NULL,
    act_detail_type TEXT NOT NULL,
    act_detail_id INTEGER NOT NULL,
    selection_mode TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    grade_id INTEGER,
    rank INTEGER,
    result INTEGER,
    cleanup INTEGER,
    destroy_when_drop INTEGER,
    drop_when_destroy INTEGER,
    show_action_bar INTEGER,
    try_equip INTEGER,
    native_state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE orphan_grant_details (
    orphan_key TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    act_detail_id INTEGER NOT NULL,
    item_id INTEGER,
    state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_quest_pages (
    quest_id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_sha256 TEXT,
    page_state TEXT NOT NULL,
    native_identity_state TEXT NOT NULL,
    catalog_state TEXT NOT NULL,
    detail_present INTEGER NOT NULL,
    parser_version TEXT,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_quest_item_mentions (
    mention_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    section_kind TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    visible_count INTEGER,
    label TEXT,
    href TEXT NOT NULL,
    parse_state TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    context_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    UNIQUE(quest_id, section_kind, ordinal)
) WITHOUT ROWID;

CREATE TABLE item_closure (
    item_id INTEGER PRIMARY KEY,
    entity_key TEXT NOT NULL,
    native_state TEXT NOT NULL,
    lifecycle TEXT NOT NULL,
    concrete_type TEXT,
    impl_id INTEGER,
    use_skill_id INTEGER,
    buff_id INTEGER,
    craft_id INTEGER,
    closure_state TEXT NOT NULL,
    missing_dependencies_json TEXT NOT NULL,
    blocker_roots_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE quest_item_comparisons (
    comparison_key TEXT PRIMARY KEY,
    grant_key TEXT,
    mention_key TEXT,
    quest_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    native_relation_state TEXT NOT NULL,
    wiki_relation_state TEXT NOT NULL,
    role_comparison_state TEXT NOT NULL,
    count_comparison_state TEXT NOT NULL,
    overall_state TEXT NOT NULL,
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

CREATE INDEX idx_grants_quest_phase
    ON quest_item_grants(quest_id, grant_phase);
CREATE INDEX idx_grants_item ON quest_item_grants(item_id);
CREATE INDEX idx_grants_type ON quest_item_grants(act_detail_type);
CREATE INDEX idx_mentions_quest_section
    ON wiki_quest_item_mentions(quest_id, section_kind);
CREATE INDEX idx_mentions_item ON wiki_quest_item_mentions(item_id);
CREATE INDEX idx_comparisons_state ON quest_item_comparisons(overall_state);
CREATE INDEX idx_closure_state ON item_closure(closure_state);
"""


def _clean(value: str) -> str:
    return SPACE.sub(" ", value).strip()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(handle)
    temporary = Path(name)
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def quest_item_cache(config: ForensicsConfig) -> Path:
    return (
        config.stage_70_wiki_cache
        / "detail"
        / config.wiki_locale
        / "quests"
    )


def crosswalk_paths(config: ForensicsConfig) -> dict[str, Path]:
    stem = config.output_dir / "quest-item-crosswalk-v1"
    return {
        "database": stem.with_suffix(".sqlite3"),
        "manifest": stem.with_suffix(".manifest.json"),
        "summary": stem.with_name(stem.name + "-summary.json"),
        "gaps": stem.with_name(stem.name + "-gaps.csv"),
        "viewer": stem.with_suffix(".html"),
    }


def _snapshot_paths(cache: Path, quest_id: int) -> tuple[Path, Path]:
    return cache / f"{quest_id}.html", cache / f"{quest_id}.meta.json"


@dataclass
class _Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    parent: _Node | None = None
    text_value: str = ""
    children: list[_Node] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def text(self) -> str:
        parts = [self.text_value] if self.text_value else []
        parts.extend(child.text() for child in self.children)
        return _clean(" ".join(parts))

    def direct_text(self) -> str:
        return _clean(
            " ".join(child.text_value for child in self.children if child.tag == "#text")
        )


class _DomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        lowered = tag.lower()
        node = _Node(
            lowered,
            {key: value or "" for key, value in attrs},
            self.stack[-1],
        )
        self.stack[-1].children.append(node)
        if lowered == "title":
            self.in_title = True
        if lowered not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "title":
            self.in_title = False
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == lowered:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data: str) -> None:
        text = _clean(data)
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        self.stack[-1].children.append(
            _Node("#text", parent=self.stack[-1], text_value=text)
        )


def _walk(node: _Node) -> Iterable[_Node]:
    yield node
    for child in node.children:
        yield from _walk(child)


def _ancestor(node: _Node | None, predicate: Callable[[_Node], bool]) -> _Node | None:
    current = node
    while current is not None:
        if predicate(current):
            return current
        current = current.parent
    return None


def _contains(node: _Node, target: _Node) -> bool:
    if node is target:
        return True
    return any(_contains(child, target) for child in node.children)


def _text_before(container: _Node, target: _Node) -> str:
    parts: list[str] = []

    def visit(node: _Node) -> bool:
        for child in node.children:
            if child is target:
                return True
            if _contains(child, target):
                return visit(child)
            value = child.text()
            if value:
                parts.append(value)
        return False

    visit(container)
    return _clean(" ".join(parts))


def _ancestor_headings(node: _Node) -> list[str]:
    headings: list[str] = []
    child = node
    current = node.parent
    while current is not None:
        if (
            current.tag == "div"
            and "mb-2" in current.classes
            and "ml-2" not in current.classes
        ):
            value = _text_before(current, child).rstrip(":")
            if value and value not in headings and value.casefold() != "actions":
                headings.append(value)
        child = current
        current = current.parent
    return headings


def _normalize_section(action: str, headings: list[str], context: str) -> str:
    action_cf = action.casefold()
    heading_cf = " | ".join(headings).casefold()
    context_cf = context.casefold()
    if "quest item" in heading_cf:
        return "quest_item"
    if "reward" in heading_cf:
        if "result" in action_cf and "rank" in action_cf:
            return "ranked_reward"
        if "rank" in action_cf or "rank" in context_cf:
            return "ranked_reward"
        if action_cf.startswith("choose item") or "select item" in action_cf:
            return "selective_reward"
        return "fixed_reward"
    if action_cf.startswith(
        ("collect item", "obtain item", "deliver item", "summon achieves level")
    ):
        return "objective_item"
    if "use item to accept quest" in action_cf:
        return "requirement_item"
    if any(token in action_cf for token in ("possess item", "have item", "consume item")):
        return "requirement_item"
    if "requirement" in heading_cf and "item" in context_cf:
        return "requirement_item"
    if any(token in heading_cf for token in ("progress", "ready")) and "item" in action_cf:
        return "objective_item"
    if action_cf.startswith(("item", "choose item")):
        return "other_visible_item"
    return "unknown_section"


@dataclass(frozen=True)
class QuestItemMention:
    item_id: int
    section_kind: str
    ordinal: int
    visible_count: int | None
    label: str
    href: str
    parse_state: str
    upper_section: str | None
    subsection: str | None
    action: str | None
    context: str


@dataclass(frozen=True)
class StructuredWikiLink:
    kind: str
    entity_id: str
    label: str
    href: str
    context: tuple[str, ...]
    relation_hint: str
    ordinal: int


@dataclass(frozen=True)
class ParsedQuestItemPage:
    entity_kind: str
    entity_id: int
    page_type: str | None
    name: str | None
    category: str | None
    grade: str | None
    level: int | None
    text_digest: str
    links: tuple[StructuredWikiLink, ...]
    map_links: tuple[str, ...]
    parse_state: str
    mentions: tuple[QuestItemMention, ...]


def parse_quest_item_page(
    payload: bytes,
    *,
    entity_kind: str = "quests",
    entity_id: int,
    locale: str = "na-en",
) -> ParsedQuestItemPage:
    parser = _DomParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    all_text = parser.root.text()
    title = _clean(" ".join(parser.title_parts))
    name = re.sub(
        r"\s*-\s*Quest\s*-\s*ArcheRage Wiki\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip() or None
    marker_present = f"ID: {entity_id}" in all_text
    section_ordinals: Counter[str] = Counter()
    mentions: list[QuestItemMention] = []
    for node in _walk(parser.root):
        if node.tag != "a":
            continue
        href = node.attrs.get("href", "")
        match = ITEM_LINK.match(href)
        if not match or match.group("locale") != locale:
            continue
        if _ancestor(node, lambda value: value.tag == "table") is not None:
            continue
        label_wrapper = _ancestor(
            node,
            lambda value: value.tag == "div"
            and {"mb-1", "ml-2"}.issubset(value.classes),
        )
        if label_wrapper is None:
            continue
        entry = _ancestor(
            label_wrapper.parent,
            lambda value: value.tag == "div"
            and {"mb-2", "ml-2"}.issubset(value.classes),
        )
        if entry is None:
            continue
        label = node.text() or label_wrapper.text()
        action = _text_before(entry, label_wrapper).rstrip(":") or None
        headings = _ancestor_headings(entry)
        context = entry.text()
        section = _normalize_section(action or "", headings, context)
        section_ordinals[section] += 1
        count_match = VISIBLE_COUNT.match(label)
        visible_count = (
            int(count_match.group("count").replace(",", ""))
            if count_match
            else None
        )
        mentions.append(
            QuestItemMention(
                item_id=int(match.group("id")),
                section_kind=section,
                ordinal=section_ordinals[section],
                visible_count=visible_count,
                label=label,
                href=href,
                parse_state=("confirmed" if section != "unknown_section" else "ambiguous"),
                upper_section=headings[0] if headings else None,
                subsection=headings[1] if len(headings) > 1 else None,
                action=action,
                context=context,
            )
        )
    normalized = "\n".join(node.text_value for node in _walk(parser.root) if node.tag == "#text")
    if marker_present and name:
        parse_state = "confirmed"
    elif marker_present:
        parse_state = "partial"
    else:
        parse_state = "parse_failed"
    links = tuple(
        StructuredWikiLink(
            kind="items",
            entity_id=str(mention.item_id),
            label=mention.label,
            href=mention.href,
            context=tuple(
                value
                for value in (
                    mention.upper_section,
                    mention.subsection,
                    mention.action,
                    mention.context,
                )
                if value
            ),
            relation_hint=mention.section_kind,
            ordinal=mention.ordinal,
        )
        for mention in mentions
    )
    return ParsedQuestItemPage(
        entity_kind=entity_kind,
        entity_id=entity_id,
        page_type="Quest" if marker_present else None,
        name=name,
        category=None,
        grade=None,
        level=None,
        text_digest=sha256_text(normalized),
        links=links,
        map_links=(),
        parse_state=parse_state,
        mentions=tuple(mentions),
    )


@dataclass(frozen=True)
class NativeExtraction:
    grants: tuple[dict[str, Any], ...]
    orphans: tuple[dict[str, Any], ...]
    quest_ids: tuple[int, ...]
    stats: dict[str, Any]


def _open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _load_native_table(
    connection: sqlite3.Connection, table: str
) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in connection.execute(
        """
        SELECT native_row_key,state,row_json,provenance,evidence_json
        FROM native_rows WHERE source_table=? ORDER BY native_row_key
        """,
        (table,),
    ):
        payload = json.loads(row["row_json"])
        native_id = int(payload["id"])
        if native_id in result:
            raise RuntimeError(f"Duplicate {table}.id={native_id}")
        result[native_id] = {
            "row": payload,
            "native_row_key": str(row["native_row_key"]),
            "state": str(row["state"]),
            "provenance": str(row["provenance"]),
            "evidence_json": str(row["evidence_json"]),
        }
    return result


def extract_native_grants(stage_40: Path) -> NativeExtraction:
    connection = _open_read_only(stage_40)
    try:
        contexts = _load_native_table(connection, "quest_contexts")
        components = _load_native_table(connection, "quest_components")
        acts = _load_native_table(connection, "quest_acts")
        details = {
            act_type: _load_native_table(connection, table)
            for act_type, table in GRANT_TABLES.items()
        }
    finally:
        connection.close()
    grants: list[dict[str, Any]] = []
    orphans: list[dict[str, Any]] = []
    referenced: dict[str, set[int]] = defaultdict(set)
    act_counts: Counter[str] = Counter()
    for act_id in sorted(acts):
        act_source = acts[act_id]
        act = act_source["row"]
        act_type = str(act.get("act_detail_type", ""))
        if act_type not in GRANT_TABLES:
            continue
        act_counts[act_type] += 1
        detail_id = int(act["act_detail_id"])
        referenced[act_type].add(detail_id)
        detail_source = details[act_type].get(detail_id)
        component_id = int(act["quest_component_id"])
        component_source = components.get(component_id)
        failure = None
        if detail_source is None:
            failure = "referenced_detail_missing"
        elif component_source is None:
            failure = "quest_component_missing"
        if failure:
            row = detail_source["row"] if detail_source else act
            orphans.append(
                {
                    "source_table": GRANT_TABLES[act_type] if detail_source else "quest_acts",
                    "act_detail_id": detail_id,
                    "item_id": row.get("item_id"),
                    "state": failure,
                    "row": row,
                    "evidence": {
                        "act_native_row_key": act_source["native_row_key"],
                        "act_type": act_type,
                        "component_id": component_id,
                    },
                }
            )
            continue
        assert detail_source is not None and component_source is not None
        detail = detail_source["row"]
        component = component_source["row"]
        quest_id = int(component["quest_context_id"])
        kind_id = int(component["component_kind_id"])
        phase = (
            "initial_supply"
            if kind_id == 3
            else ("reward" if kind_id == 8 else "other_native_stage")
        )
        states = {
            act_source["state"],
            component_source["state"],
            detail_source["state"],
        }
        context_source = contexts.get(quest_id)
        if context_source is not None:
            states.add(context_source["state"])
        native_state = "confirmed" if states == {"confirmed"} else (
            "blocked" if "blocked" in states else "unknown"
        )
        if context_source is None and native_state == "confirmed":
            native_state = "unknown"
        grant = {
            "quest_id": quest_id,
            "component_id": component_id,
            "component_kind_id": kind_id,
            "grant_phase": phase,
            "quest_act_id": act_id,
            "act_detail_type": act_type,
            "act_detail_id": detail_id,
            "selection_mode": SELECTION_MODES[act_type],
            "item_id": int(detail["item_id"]),
            "count": int(detail["count"]),
            "grade_id": detail.get("grade_id"),
            "rank": detail.get("rank"),
            "result": detail.get("result"),
            "cleanup": detail.get("cleanup"),
            "destroy_when_drop": detail.get("destroy_when_drop"),
            "drop_when_destroy": detail.get("drop_when_destroy"),
            "show_action_bar": detail.get("show_action_bar"),
            "try_equip": detail.get("try_equip"),
            "native_state": native_state,
            "provenance": "stage40.native_rows",
            "evidence": {
                "act_native_row_key": act_source["native_row_key"],
                "component_native_row_key": component_source["native_row_key"],
                "context_native_row_key": (
                    context_source["native_row_key"] if context_source else None
                ),
                "context_state": (
                    context_source["state"] if context_source else "missing"
                ),
                "detail_native_row_key": detail_source["native_row_key"],
                "source_table": GRANT_TABLES[act_type],
            },
        }
        grant["grant_key"] = stable_key(
            "quest_item_grant", act_type, act_id, detail_id, grant["item_id"]
        )
        grants.append(grant)
    for act_type, table in GRANT_TABLES.items():
        for detail_id in sorted(set(details[act_type]) - referenced[act_type]):
            detail_source = details[act_type][detail_id]
            detail = detail_source["row"]
            orphans.append(
                {
                    "source_table": table,
                    "act_detail_id": detail_id,
                    "item_id": detail.get("item_id"),
                    "state": "unlinked_detail",
                    "row": detail,
                    "evidence": {
                        "detail_native_row_key": detail_source["native_row_key"],
                        "act_type": act_type,
                        "searched_quest_acts": True,
                    },
                }
            )
    grants.sort(key=lambda row: (row["quest_id"], row["quest_act_id"], row["act_detail_id"]))
    orphans.sort(key=lambda row: (row["source_table"], row["act_detail_id"], row["state"]))
    quest_ids = tuple(sorted({int(row["quest_id"]) for row in grants}))
    stats = {
        "candidate_quests": len(quest_ids),
        "grant_counts": dict(sorted(Counter(row["act_detail_type"] for row in grants).items())),
        "source_act_counts": dict(sorted(act_counts.items())),
        "source_detail_counts": {
            act_type: len(details[act_type]) for act_type in sorted(details)
        },
        "orphans_by_table": dict(sorted(Counter(row["source_table"] for row in orphans).items())),
        "orphan_states": dict(sorted(Counter(row["state"] for row in orphans).items())),
    }
    return NativeExtraction(tuple(grants), tuple(orphans), quest_ids, stats)


class QuestWikiClient:
    def __init__(
        self,
        *,
        base_url: str,
        requested_delay: float,
        fetcher: Callable[[str], tuple[Any, ...]] | None = None,
    ) -> None:
        if requested_delay < MINIMUM_DELAY:
            raise ValueError(f"Wiki crawl delay must be at least {MINIMUM_DELAY}")
        self.base_url = base_url.rstrip("/")
        self.delay = requested_delay
        self.fetcher = fetcher
        self.last_request: float | None = None
        self._connection: http.client.HTTPSConnection | None = None

    def _wait(self) -> None:
        if self.fetcher is not None or self.last_request is None:
            return
        remaining = self.delay - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)

    def _request(self, url: str) -> tuple[int | None, bytes, str, str, str | None]:
        self._wait()
        try:
            if self.fetcher is not None:
                value = self.fetcher(url)
                if len(value) == 3:
                    status, payload, content_type = value
                    final_url = url
                else:
                    status, payload, content_type, final_url = value
                return int(status), bytes(payload), str(content_type), str(final_url), None
            final_url = url
            for _ in range(6):
                parsed = urlsplit(final_url)
                base = urlsplit(self.base_url)
                if parsed.scheme != "https" or parsed.netloc != base.netloc:
                    request = urllib.request.Request(
                        final_url, headers={"User-Agent": USER_AGENT}
                    )
                    with urllib.request.urlopen(request, timeout=120) as response:
                        return (
                            int(response.status),
                            response.read(),
                            response.headers.get_content_type(),
                            response.geturl(),
                            None,
                        )
                if self._connection is None:
                    self._connection = http.client.HTTPSConnection(
                        parsed.hostname,
                        parsed.port or 443,
                        timeout=120,
                    )
                target = parsed.path or "/"
                if parsed.query:
                    target += f"?{parsed.query}"
                self._connection.request(
                    "GET",
                    target,
                    headers={"User-Agent": USER_AGENT, "Connection": "keep-alive"},
                )
                response = self._connection.getresponse()
                payload = response.read()
                status = int(response.status)
                if status in {301, 302, 303, 307, 308} and response.getheader("Location"):
                    final_url = urljoin(final_url, str(response.getheader("Location")))
                    continue
                return (
                    status,
                    payload,
                    response.headers.get_content_type(),
                    final_url,
                    None,
                )
            return None, b"", "", final_url, "redirect_limit_exceeded"
        except urllib.error.HTTPError as error:
            return (
                int(error.code),
                error.read(),
                error.headers.get_content_type() if error.headers else "",
                error.geturl(),
                None,
            )
        except (OSError, http.client.HTTPException, urllib.error.URLError) as error:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
            return None, b"", "", url, f"{type(error).__name__}: {error}"
        finally:
            self.last_request = time.monotonic()

    def fetch(self, url: str) -> tuple[int | None, bytes, str, str, str | None]:
        last: tuple[int | None, bytes, str, str, str | None] | None = None
        for _ in range(3):
            last = self._request(url)
            if last[0] not in TRANSIENT_HTTP and last[0] is not None:
                return last
        assert last is not None
        return last

    def load_robots(self, sample_url: str) -> tuple[dict[str, Any], bytes]:
        url = f"{self.base_url}/robots.txt"
        status, payload, content_type, final_url, error = self.fetch(url)
        if status != 200 or error:
            raise RuntimeError(f"Unable to verify wiki robots.txt: HTTP {status}; {error}")
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(url)
        parser.parse(payload.decode("utf-8", errors="replace").splitlines())
        if not parser.can_fetch(USER_AGENT, sample_url):
            raise RuntimeError("wiki robots.txt forbids quest detail acquisition")
        robots_delay = parser.crawl_delay(USER_AGENT)
        if robots_delay is None:
            robots_delay = parser.crawl_delay("*")
        self.delay = max(self.delay, float(robots_delay or 0))
        return (
            {
                "allowed": True,
                "captured_at": _utc_now(),
                "content_bytes": len(payload),
                "content_sha256": _sha256_bytes(payload),
                "content_type": content_type,
                "crawl_delay": self.delay,
                "final_url": final_url,
                "url": url,
                "user_agent": USER_AGENT,
            },
            payload,
        )


def _read_snapshot_metadata(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if int(value.get("entity_id", -1)) <= 0:
        raise ValueError(f"Invalid quest detail metadata: {path}")
    return value


def _snapshot_valid(cache: Path, quest_id: int) -> bool:
    html_path, metadata_path = _snapshot_paths(cache, quest_id)
    if not metadata_path.is_file():
        return False
    metadata = _read_snapshot_metadata(metadata_path)
    if (
        int(metadata.get("entity_id", -1)) != quest_id
        or str(metadata.get("entity_kind")) != "quests"
        or str(metadata.get("locale")) != cache.parent.name
    ):
        return False
    status = metadata.get("status_code")
    if status not in {200, 404, 410}:
        return False
    digest = metadata.get("content_sha256")
    if not digest or not html_path.is_file():
        return False
    return (
        int(metadata.get("content_bytes", -1)) == html_path.stat().st_size
        and str(digest).upper() == sha256_file(html_path)
    )


def _write_snapshot(
    cache: Path,
    *,
    quest_id: int,
    canonical_url: str,
    status_code: int | None,
    payload: bytes,
    content_type: str,
    final_url: str,
    locale: str,
    error: str | None,
    migrated_from: str | None = None,
    source_parser_version: str | None = None,
) -> dict[str, Any]:
    html_path, metadata_path = _snapshot_paths(cache, quest_id)
    if status_code is not None:
        _atomic_bytes(html_path, payload)
        digest = sha256_file(html_path)
    else:
        digest = None
    if status_code == 200 and payload:
        parsed = parse_quest_item_page(payload, entity_id=quest_id, locale=locale)
        page_state = (
            f"redirected_{parsed.parse_state}"
            if final_url.rstrip("/") != canonical_url.rstrip("/")
            else parsed.parse_state
        )
    elif status_code in {404, 410}:
        page_state = "permanent_missing"
    elif status_code is None or status_code in TRANSIENT_HTTP:
        page_state = "transient_error"
    elif status_code is not None and 300 <= status_code < 400:
        page_state = "redirect_error"
    else:
        page_state = "http_error"
    metadata = {
        "captured_at": _utc_now(),
        "content_bytes": len(payload),
        "content_sha256": digest,
        "content_type": content_type,
        "entity_id": quest_id,
        "entity_kind": "quests",
        "error": error,
        "final_url": final_url,
        "locale": locale,
        "migrated_from": migrated_from,
        "page_state": page_state,
        "parser_version": PARSER_VERSION,
        "provenance": WIKI_PROVENANCE,
        "source_parser_version": source_parser_version,
        "status_code": status_code,
        "url": canonical_url,
    }
    atomic_text(metadata_path, canonical_json(metadata, pretty=True))
    return metadata


def _migrate_existing_details(
    config: ForensicsConfig,
    quest_ids: Iterable[int],
) -> int:
    source = config.source_quest_wiki_cache
    target = quest_item_cache(config)
    migrated = 0
    for quest_id in quest_ids:
        if _snapshot_valid(target, quest_id):
            continue
        source_html = source / f"{quest_id}.html"
        source_meta = source / f"{quest_id}.meta.json"
        if not source_html.is_file() or not source_meta.is_file():
            continue
        metadata = json.loads(source_meta.read_text(encoding="utf-8"))
        digest = str(metadata.get("content_sha256") or "").upper()
        if int(metadata.get("status_code", 0)) not in {200, 404, 410}:
            continue
        if not digest or digest != sha256_file(source_html):
            continue
        _write_snapshot(
            target,
            quest_id=quest_id,
            canonical_url=str(metadata["url"]),
            status_code=int(metadata["status_code"]),
            payload=source_html.read_bytes(),
            content_type=str(metadata.get("content_type", "text/html")),
            final_url=str(metadata["url"]),
            locale=config.wiki_locale,
            error=None,
            migrated_from=source_meta.resolve().as_posix(),
            source_parser_version=str(metadata.get("parser_version", "unknown")),
        )
        migrated += 1
    return migrated


def build_quest_item_cache_manifest(
    config: ForensicsConfig,
    expected_quest_ids: Iterable[int],
) -> dict[str, Any]:
    cache = quest_item_cache(config)
    expected = tuple(sorted(set(expected_quest_ids)))
    records: list[dict[str, Any]] = []
    for quest_id in expected:
        _, metadata_path = _snapshot_paths(cache, quest_id)
        if not metadata_path.is_file():
            records.append({"entity_id": quest_id, "page_state": "not_requested"})
            continue
        metadata = _read_snapshot_metadata(metadata_path)
        records.append(
            {
                key: metadata.get(key)
                for key in (
                    "content_bytes",
                    "content_sha256",
                    "content_type",
                    "entity_id",
                    "entity_kind",
                    "error",
                    "final_url",
                    "locale",
                    "page_state",
                    "parser_version",
                    "provenance",
                    "status_code",
                    "url",
                )
            }
        )
    statuses = Counter(str(row.get("status_code")) for row in records)
    states = Counter(str(row.get("page_state")) for row in records)
    record_digest = sha256_text(canonical_json(records))
    robots_policy_path = cache / "robots-policy.json"
    robots_txt_path = cache / "robots.txt"
    robots_policy = (
        json.loads(robots_policy_path.read_text(encoding="utf-8"))
        if robots_policy_path.is_file()
        else {}
    )
    manifest = {
        "authority": WIKI_AUTHORITY,
        "cache_digest": record_digest,
        "expected_quests": len(expected),
        "locale": config.wiki_locale,
        "page_states": dict(sorted(states.items())),
        "parser_version": PARSER_VERSION,
        "provenance": WIKI_PROVENANCE,
        "records": records,
        "robots": {
            key: robots_policy.get(key)
            for key in (
                "allowed",
                "content_bytes",
                "content_sha256",
                "content_type",
                "crawl_delay",
                "url",
                "user_agent",
            )
        },
        "robots_txt_sha256": (
            sha256_file(robots_txt_path) if robots_txt_path.is_file() else None
        ),
        "schema_version": 1,
        "statuses": dict(sorted(statuses.items())),
    }
    atomic_text(cache / "snapshot-manifest.json", canonical_json(manifest, pretty=True))
    return manifest


def _freeze_quest_item_wiki_unlocked(
    config: ForensicsConfig,
    *,
    resume: bool = True,
    delay: float = MINIMUM_DELAY,
    progress: Callable[[str], None] | None = None,
    fetcher: Callable[[str], tuple[Any, ...]] | None = None,
    quest_ids: Iterable[int] | None = None,
) -> dict[str, Any]:
    extraction = extract_native_grants(config.stage_40)
    expected = tuple(sorted(set(quest_ids or extraction.quest_ids)))
    if not expected:
        raise RuntimeError("Stage 40 produced no quests with item grants")
    cache = quest_item_cache(config)
    cache.mkdir(parents=True, exist_ok=True)
    migrated = _migrate_existing_details(config, expected)
    client = QuestWikiClient(
        base_url=config.wiki_base_url,
        requested_delay=delay,
        fetcher=fetcher,
    )
    sample = f"{config.wiki_base_url}/{config.wiki_locale}/db/quests/{expected[0]}"
    robots, robots_payload = client.load_robots(sample)
    _atomic_bytes(cache / "robots.txt", robots_payload)
    atomic_text(cache / "robots-policy.json", canonical_json(robots, pretty=True))
    downloaded = 0
    skipped = 0
    failures = 0
    for index, quest_id in enumerate(expected, 1):
        if _snapshot_valid(cache, quest_id):
            skipped += 1
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
            downloaded += 1
            if status not in {200, 404, 410}:
                failures += 1
        if index % 25 == 0 or index == len(expected):
            durable = {
                "completed": index,
                "downloaded": downloaded,
                "expected": len(expected),
                "failures": failures,
                "last_quest_id": quest_id,
                "resume": bool(resume),
                "skipped": skipped,
            }
            atomic_text(cache / "progress.json", canonical_json(durable, pretty=True))
            if progress:
                progress(
                    f"quest wiki {index}/{len(expected)} downloaded={downloaded} "
                    f"skipped={skipped} failures={failures}"
                )
    manifest = build_quest_item_cache_manifest(config, expected)
    return {
        "cache": cache,
        "cache_digest": manifest["cache_digest"],
        "crawl_delay": client.delay,
        "downloaded": downloaded,
        "expected": len(expected),
        "failures": failures,
        "manifest": cache / "snapshot-manifest.json",
        "migrated": migrated,
        "page_states": manifest["page_states"],
        "skipped": skipped,
    }


def freeze_quest_item_wiki(
    config: ForensicsConfig,
    *,
    resume: bool = True,
    delay: float = MINIMUM_DELAY,
    progress: Callable[[str], None] | None = None,
    fetcher: Callable[[str], tuple[Any, ...]] | None = None,
    quest_ids: Iterable[int] | None = None,
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
            raise RuntimeError(
                f"Quest wiki acquisition is already active in PID {owner_pid}"
            )
    descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        descriptor = -1
        return _freeze_quest_item_wiki_unlocked(
            config,
            resume=resume,
            delay=delay,
            progress=progress,
            fetcher=fetcher,
            quest_ids=quest_ids,
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _create_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.executescript(CROSSWALK_SCHEMA)
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return connection


def _insert_metadata(connection: sqlite3.Connection, key: str, value: Any) -> None:
    connection.execute(
        "INSERT INTO metadata(key,value_json) VALUES(?,?)",
        (key, canonical_json(value)),
    )


def _insert_validation(
    connection: sqlite3.Connection,
    check_name: str,
    state: str,
    expected: Any,
    actual: Any,
    evidence: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO validation_events(
            validation_key,check_name,state,expected_json,actual_json,evidence_json
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            stable_key("quest_item_validation", check_name),
            check_name,
            state,
            None if expected is None else canonical_json(expected),
            canonical_json(actual),
            canonical_json(evidence or {}),
        ),
    )


def _insert_source_artifact(
    connection: sqlite3.Connection,
    *,
    role: str,
    path: Path,
    digest: str,
    authority: str,
    provenance: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO source_artifacts(
            artifact_key,role,path,bytes,sha256,authority,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            stable_key("quest_item_source", role, path.resolve().as_posix(), digest),
            role,
            path.resolve().as_posix(),
            path.stat().st_size,
            digest,
            authority,
            provenance,
            canonical_json(evidence),
        ),
    )


def _native_identity_states(stage_70: Path) -> dict[int, tuple[str, str]]:
    connection = _open_read_only(stage_70)
    try:
        result = {}
        for row in connection.execute(
            """
            SELECT entity_key,state,comparison_state,evidence_json
            FROM wiki_entities WHERE entity_key LIKE 'quest:%'
            """
        ):
            quest_id = int(str(row["entity_key"]).split(":", 1)[1])
            native_identity_state = (
                "match"
                if str(row["state"]) == "confirmed"
                and str(row["comparison_state"]) in {"match", "corroborated_native_identity"}
                else str(row["comparison_state"])
            )
            evidence = json.loads(str(row["evidence_json"]))
            catalog_present = bool(evidence.get("catalog_memberships"))
            catalog_state = (
                "catalog_match"
                if catalog_present and native_identity_state == "match"
                else (
                    "catalog_present_unresolved"
                    if catalog_present
                    else "catalog_absent"
                )
            )
            result[quest_id] = (native_identity_state, catalog_state)
        return result
    finally:
        connection.close()


def _load_wiki_pages_and_mentions(
    config: ForensicsConfig,
    quest_ids: Iterable[int],
    identity_states: dict[int, tuple[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pages: list[dict[str, Any]] = []
    mentions: list[dict[str, Any]] = []
    cache = quest_item_cache(config)
    for quest_id in sorted(quest_ids):
        native_identity_state, catalog_state = identity_states.get(
            quest_id, ("missing", "catalog_absent")
        )
        html_path, metadata_path = _snapshot_paths(cache, quest_id)
        url = f"{config.wiki_base_url}/{config.wiki_locale}/db/quests/{quest_id}"
        if not metadata_path.is_file():
            pages.append(
                {
                    "quest_id": quest_id,
                    "url": url,
                    "status_code": None,
                    "response_sha256": None,
                    "page_state": "not_requested",
                    "native_identity_state": native_identity_state,
                    "catalog_state": catalog_state,
                    "detail_present": 0,
                    "parser_version": None,
                    "evidence": {"metadata_present": False},
                }
            )
            continue
        metadata = _read_snapshot_metadata(metadata_path)
        status = metadata.get("status_code")
        digest = metadata.get("content_sha256")
        detail_present = int(status == 200 and html_path.is_file() and bool(digest))
        page_state = str(metadata.get("page_state", "unknown"))
        page = {
            "quest_id": quest_id,
            "url": str(metadata.get("url", url)),
            "status_code": status,
            "response_sha256": digest,
            "page_state": page_state,
            "native_identity_state": native_identity_state,
            "catalog_state": catalog_state,
            "detail_present": detail_present,
            "parser_version": metadata.get("parser_version"),
            "evidence": {
                "final_url": metadata.get("final_url"),
                "metadata_path": metadata_path.resolve().as_posix(),
                "metadata_sha256": sha256_file(metadata_path),
                "provenance": WIKI_PROVENANCE,
            },
        }
        pages.append(page)
        if not detail_present:
            continue
        actual = sha256_file(html_path)
        if actual != str(digest).upper():
            page["page_state"] = "hash_mismatch"
            page["detail_present"] = 0
            continue
        parsed = parse_quest_item_page(
            html_path.read_bytes(), entity_id=quest_id, locale=config.wiki_locale
        )
        page["page_state"] = (
            page_state if page_state.startswith("redirected_") else parsed.parse_state
        )
        for mention in parsed.mentions:
            mention_key = stable_key(
                "quest_item_mention",
                quest_id,
                mention.item_id,
                mention.section_kind,
                mention.ordinal,
            )
            mentions.append(
                {
                    "mention_key": mention_key,
                    "quest_id": quest_id,
                    "item_id": mention.item_id,
                    "section_kind": mention.section_kind,
                    "ordinal": mention.ordinal,
                    "visible_count": mention.visible_count,
                    "label": mention.label,
                    "href": mention.href,
                    "parse_state": mention.parse_state,
                    "response_sha256": actual,
                    "context": {
                        "action": mention.action,
                        "context": mention.context,
                        "subsection": mention.subsection,
                        "upper_section": mention.upper_section,
                    },
                    "evidence": {
                        "authority": WIKI_AUTHORITY,
                        "parser_version": PARSER_VERSION,
                        "source_html": html_path.resolve().as_posix(),
                    },
                }
            )
    return pages, mentions


def _property_integer(
    connection: sqlite3.Connection, entity_key: str, name: str
) -> int | None:
    row = connection.execute(
        """
        SELECT value_integer FROM entity_properties
        WHERE entity_key=? AND property_name=? AND value_integer IS NOT NULL
        ORDER BY CASE WHEN namespace='client.items' THEN 0 ELSE 1 END,
                 ordinal,property_key
        LIMIT 1
        """,
        (entity_key, name),
    ).fetchone()
    return int(row[0]) if row is not None else None


def _item_closure_row(
    stage20: sqlite3.Connection,
    consolidated: sqlite3.Connection,
    item_id: int,
) -> dict[str, Any]:
    key = f"item:{item_id}"
    stage20_entity = stage20.execute(
        "SELECT * FROM entities WHERE entity_key=?", (key,)
    ).fetchone()
    consolidated_entity = consolidated.execute(
        "SELECT * FROM entities WHERE entity_key=?", (key,)
    ).fetchone()
    if stage20_entity is None and consolidated_entity is None:
        return {
            "item_id": item_id,
            "entity_key": key,
            "native_state": "missing",
            "lifecycle": "missing",
            "concrete_type": None,
            "impl_id": None,
            "use_skill_id": None,
            "buff_id": None,
            "craft_id": None,
            "closure_state": "native_item_missing",
            "missing_dependencies": [],
            "blocker_roots": [],
            "provenance": "stage20+consolidated:negative_lookup",
            "evidence": {"stage20_present": False, "consolidated_present": False},
        }
    # Stage 20 remains the native item-identity authority.  The consolidated
    # graph is preferred for properties, relations, coverage and blockers
    # because later stages may have closed dependencies without replacing the
    # underlying native identity.
    entity = stage20_entity if stage20_entity is not None else consolidated_entity
    owner = consolidated if consolidated_entity is not None else stage20
    properties = {
        name: _property_integer(owner, key, name)
        for name in ("impl_id", "use_skill_id", "buff_id", "craft_id")
    }
    coverage_rows = list(
        owner.execute(
            "SELECT dimension,state,capability,provenance FROM coverage WHERE scope_key=? ORDER BY dimension,coverage_key",
            (key,),
        )
    )
    coverage = {
        str(row["dimension"]): {
            "state": str(row["state"]),
            "capability": str(row["capability"]),
            "provenance": str(row["provenance"]),
        }
        for row in coverage_rows
    }
    relation_rows = list(
        owner.execute(
            """
            SELECT relation,dst_entity_key,state,required,provenance,evidence_json
            FROM relations WHERE src_entity_key=? AND required=1
            ORDER BY relation,dst_entity_key,relation_key
            """,
            (key,),
        )
    )
    required_relations: list[dict[str, Any]] = []
    missing_dependencies: list[dict[str, Any]] = []
    concrete_type = str(entity["subtype"]) if entity["subtype"] is not None else None
    for relation in relation_rows:
        target = consolidated.execute(
            "SELECT subtype,lifecycle,state FROM entities WHERE entity_key=?",
            (relation["dst_entity_key"],),
        ).fetchone()
        item = {
            "relation": str(relation["relation"]),
            "destination": str(relation["dst_entity_key"]),
            "relation_state": str(relation["state"]),
            "destination_lifecycle": target["lifecycle"] if target else None,
            "destination_state": target["state"] if target else "missing",
        }
        required_relations.append(item)
        if relation["relation"] == "has_descriptor" and target is not None:
            concrete_type = str(target["subtype"] or relation["dst_entity_key"].split(":", 1)[0])
        if target is None or str(target["state"]) in {"missing", "blocked"}:
            missing_dependencies.append(item)
    gap_rows = list(
        consolidated.execute(
            """
            SELECT dimension,state,severity,blocker_code,reason,required_evidence,provenance
            FROM gaps WHERE entity_key=? ORDER BY gap_key
            """,
            (key,),
        )
    )
    gaps = [dict(row) for row in gap_rows]
    blocker_rows = list(
        consolidated.execute(
            """
            SELECT r.blocker_root_key,r.root_code,r.category,r.state,r.disposition,
                   r.priority_score,r.recommended_action
            FROM blocker_impacts i
            JOIN blocker_roots r USING(blocker_root_key)
            WHERE i.entity_key=? ORDER BY r.priority_score DESC,r.blocker_root_key
            """,
            (key,),
        )
    )
    blockers = [dict(row) for row in blocker_rows]
    lifecycle = str(entity["lifecycle"])
    native_state = str(entity["state"])
    dependency_state = coverage.get("dependency_closure", {}).get("state")
    dependency_gap_codes = {str(row["blocker_code"]) for row in gap_rows}
    nonzero_dependencies = any(value not in (None, 0) for value in properties.values())
    non_descriptor_required = any(
        row["relation"] != "has_descriptor" for row in required_relations
    )
    if lifecycle == "tombstone" or native_state == "tombstone":
        closure_state = "tombstone"
    elif native_state == "blocked" or dependency_state == "blocked":
        closure_state = "blocked"
    elif missing_dependencies or dependency_state == "missing" or "dependency_closure_missing" in dependency_gap_codes:
        closure_state = "dependency_closure_missing"
    elif (
        lifecycle == "present"
        and native_state == "confirmed"
        and not nonzero_dependencies
        and not non_descriptor_required
        and concrete_type in {None, "generic", "items"}
    ):
        closure_state = "generic_dependency_free_candidate"
    elif dependency_state == "unknown" or "dependency_closure_unknown" in dependency_gap_codes:
        closure_state = "dependency_closure_unknown"
    elif dependency_state == "confirmed":
        closure_state = "complete_native_closure"
    else:
        closure_state = "dependency_closure_unknown"
    coverage_projection = {
        "identity": coverage.get("identity") or coverage.get("catalog") or {"state": native_state},
        "properties": coverage.get("properties") or coverage.get("catalog") or {"state": native_state},
        "relations": coverage.get("relations") or coverage.get("dependency_closure") or {"state": "unknown"},
        "consumer": coverage.get("consumer") or coverage.get("backend") or {"state": "unknown"},
    }
    return {
        "item_id": item_id,
        "entity_key": key,
        "native_state": native_state,
        "lifecycle": lifecycle,
        "concrete_type": concrete_type,
        **properties,
        "closure_state": closure_state,
        "missing_dependencies": missing_dependencies,
        "blocker_roots": blockers,
        "provenance": "stage20+aa8-client-knowledge",
        "evidence": {
            "coverage": coverage_projection,
            "gaps": gaps,
            "required_relations": required_relations,
            "source_stage": int(entity["source_stage"]),
            "stage20_present": stage20_entity is not None,
            "consolidated_present": consolidated_entity is not None,
        },
    }


def _expected_sections(grant: dict[str, Any]) -> set[str]:
    if grant["grant_phase"] == "initial_supply":
        return {"quest_item"}
    if grant["grant_phase"] != "reward":
        return {"unknown_section", "other_visible_item"}
    return {
        "fixed": {"fixed_reward"},
        "selective": {"selective_reward"},
        "ranked": {"ranked_reward"},
        "result_ranked": {"ranked_reward"},
    }[grant["selection_mode"]]


def _pair_comparison(
    grant: dict[str, Any], mention: dict[str, Any]
) -> tuple[str, str, str]:
    expected = _expected_sections(grant)
    role = "match" if mention["section_kind"] in expected else "conflict"
    count = (
        "unresolved"
        if mention["visible_count"] is None
        else ("match" if int(mention["visible_count"]) == int(grant["count"]) else "conflict")
    )
    if role == "conflict":
        overall = "role_conflict"
    elif count == "conflict":
        overall = "count_conflict"
    elif count == "match":
        overall = "match"
    else:
        overall = "ambiguous_many_to_many"
    return role, count, overall


def _comparison_rows(
    grants: Iterable[dict[str, Any]],
    mentions: Iterable[dict[str, Any]],
    pages: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    native_groups: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    wiki_groups: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    page_map = {int(row["quest_id"]): row for row in pages}
    for row in grants:
        native_groups[(int(row["quest_id"]), int(row["item_id"]))].append(row)
    for row in mentions:
        wiki_groups[(int(row["quest_id"]), int(row["item_id"]))].append(row)
    result: list[dict[str, Any]] = []

    def add(
        key: tuple[int, int],
        grant: dict[str, Any] | None,
        mention: dict[str, Any] | None,
        *,
        role: str,
        count: str,
        overall: str,
        evidence: dict[str, Any],
    ) -> None:
        quest_id, item_id = key
        comparison_key = stable_key(
            "quest_item_comparison",
            quest_id,
            item_id,
            grant["grant_key"] if grant else None,
            mention["mention_key"] if mention else None,
            overall,
        )
        result.append(
            {
                "comparison_key": comparison_key,
                "grant_key": grant["grant_key"] if grant else None,
                "mention_key": mention["mention_key"] if mention else None,
                "quest_id": quest_id,
                "item_id": item_id,
                "native_relation_state": "confirmed_native" if grant else "missing",
                "wiki_relation_state": "corroborated_visible" if mention else "missing",
                "role_comparison_state": role,
                "count_comparison_state": count,
                "overall_state": overall,
                "evidence": evidence,
            }
        )

    for key in sorted(set(native_groups) | set(wiki_groups)):
        natives = sorted(native_groups.get(key, []), key=lambda row: row["grant_key"])
        visible = sorted(wiki_groups.get(key, []), key=lambda row: row["mention_key"])
        if not natives:
            for mention in visible:
                add(key, None, mention, role="wiki_only", count="wiki_only", overall="wiki_only", evidence={})
            continue
        if not visible:
            page = page_map.get(key[0], {})
            page_state = str(page.get("page_state", "not_requested"))
            if page_state in {
                "parse_failed",
                "partial",
                "redirected_parse_failed",
                "redirected_partial",
            }:
                overall = "wiki_parse_failed"
            elif page_state in {"transient_error", "http_error", "redirect_error", "hash_mismatch"}:
                overall = "blocked"
            elif int(page.get("detail_present", 0)) == 0:
                overall = "wiki_detail_missing"
            else:
                overall = "native_only"
            for grant in natives:
                add(
                    key,
                    grant,
                    None,
                    role="native_only",
                    count="native_only",
                    overall=overall,
                    evidence={"page_state": page_state},
                )
            continue
        remaining_native = list(natives)
        remaining_visible = list(visible)
        pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
        changed = True
        while changed:
            changed = False
            candidates: dict[str, list[dict[str, Any]]] = {}
            reverse: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for grant in remaining_native:
                matches = [
                    mention
                    for mention in remaining_visible
                    if mention["section_kind"] in _expected_sections(grant)
                    and (
                        mention["visible_count"] is None
                        or int(mention["visible_count"]) == int(grant["count"])
                    )
                ]
                candidates[grant["grant_key"]] = matches
                for mention in matches:
                    reverse[mention["mention_key"]].append(grant)
            for grant in list(remaining_native):
                matches = candidates[grant["grant_key"]]
                if len(matches) != 1 or len(reverse[matches[0]["mention_key"]]) != 1:
                    continue
                mention = matches[0]
                pairs.append((grant, mention))
                remaining_native.remove(grant)
                remaining_visible.remove(mention)
                changed = True
                break
        if len(remaining_native) == 1 and len(remaining_visible) == 1:
            pairs.append((remaining_native.pop(), remaining_visible.pop()))
        for grant, mention in pairs:
            role, count, overall = _pair_comparison(grant, mention)
            add(key, grant, mention, role=role, count=count, overall=overall, evidence={"pairing": "unique_structural_match"})
        if remaining_native and remaining_visible:
            evidence = {
                "native_candidates": [row["grant_key"] for row in remaining_native],
                "wiki_candidates": [row["mention_key"] for row in remaining_visible],
            }
            for grant in remaining_native:
                add(key, grant, None, role="ambiguous", count="ambiguous", overall="ambiguous_many_to_many", evidence=evidence)
            for mention in remaining_visible:
                add(key, None, mention, role="ambiguous", count="ambiguous", overall="ambiguous_many_to_many", evidence=evidence)
        else:
            for grant in remaining_native:
                add(key, grant, None, role="native_only", count="native_only", overall="native_only", evidence={"detail_present": True})
            for mention in remaining_visible:
                add(key, None, mention, role="wiki_only", count="wiki_only", overall="wiki_only", evidence={"detail_present": True})
    result.sort(key=lambda row: row["comparison_key"])
    return result


def _write_viewer(path: Path, data: dict[str, Any]) -> None:
    payload = canonical_json(data).replace("</script", "<\\/script")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>AA8 Quest Item Crosswalk V1</title>
<style>
body{{font:14px system-ui;margin:20px;background:#111827;color:#e5e7eb}}h1{{font-size:22px}}
.filters{{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:8px;margin:16px 0}}
input,select{{background:#1f2937;color:#fff;border:1px solid #4b5563;padding:7px}}
table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #374151;padding:6px;text-align:left}}
th{{position:sticky;top:0;background:#111827}}.bad{{color:#fca5a5}}.ok{{color:#86efac}}
</style></head><body><h1>AA8 Quest ↔ Item Crosswalk V1</h1>
<div id="summary"></div><div class="filters">
<input id="quest" placeholder="quest_id"><input id="item" placeholder="item_id">
<select id="phase"><option value="">grant_phase</option></select>
<select id="selection"><option value="">selection_mode</option></select>
<select id="wiki"><option value="">wiki state</option></select>
<select id="comparison"><option value="">comparison state</option></select>
<select id="closure"><option value="">closure state</option></select>
<input id="blocker" placeholder="blocker">
</div><div id="count"></div><table><thead><tr><th>Quest</th><th>Item</th><th>Phase</th><th>Mode</th><th>Wiki</th><th>Comparison</th><th>Closure</th><th>Blocker</th></tr></thead><tbody id="rows"></tbody></table>
<script id="data" type="application/json">{payload}</script><script>
const D=JSON.parse(document.getElementById('data').textContent), rows=D.rows;
summary.textContent=`grants ${{D.summary.grants}} · mentions ${{D.summary.mentions}} · comparisons ${{rows.length}}`;
const ids=['phase','selection','wiki','comparison','closure'];
for(const id of ids){{const e=document.getElementById(id),vals=[...new Set(rows.map(r=>r[id]).filter(Boolean))].sort();for(const v of vals){{let o=document.createElement('option');o.value=v;o.textContent=v;e.append(o)}}e.onchange=render}}
quest.oninput=item.oninput=blocker.oninput=render;
function render(){{const q=quest.value.trim(),i=item.value.trim(),b=blocker.value.toLowerCase();let shown=rows.filter(r=>(!q||String(r.quest_id).includes(q))&&(!i||String(r.item_id).includes(i))&&(!b||r.blocker.toLowerCase().includes(b))&&ids.every(id=>!document.getElementById(id).value||r[id]===document.getElementById(id).value));count.textContent=`${{shown.length}} rows`;document.getElementById('rows').innerHTML=shown.slice(0,20000).map(r=>`<tr><td>${{r.quest_id}}</td><td>${{r.item_id}}</td><td>${{r.phase||''}}</td><td>${{r.selection||''}}</td><td>${{r.wiki||''}}</td><td class="${{r.comparison==='match'?'ok':'bad'}}">${{r.comparison}}</td><td>${{r.closure||''}}</td><td>${{r.blocker||''}}</td></tr>`).join('')}}render();
</script></body></html>"""
    atomic_text(path, html)


def _export_outputs(config: ForensicsConfig, database: Path) -> dict[str, Any]:
    paths = crosswalk_paths(config)
    connection = _open_read_only(database)
    try:
        table_counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "quest_item_grants",
                "orphan_grant_details",
                "wiki_quest_pages",
                "wiki_quest_item_mentions",
                "item_closure",
                "quest_item_comparisons",
            )
        }
        comparison_counts = dict(
            connection.execute(
                "SELECT overall_state,COUNT(*) FROM quest_item_comparisons GROUP BY overall_state ORDER BY overall_state"
            ).fetchall()
        )
        closure_counts = dict(
            connection.execute(
                "SELECT closure_state,COUNT(*) FROM item_closure GROUP BY closure_state ORDER BY closure_state"
            ).fetchall()
        )
        wiki_counts = dict(
            connection.execute(
                "SELECT page_state,COUNT(*) FROM wiki_quest_pages GROUP BY page_state ORDER BY page_state"
            ).fetchall()
        )
        wiki_identity_counts = dict(
            connection.execute(
                "SELECT native_identity_state,COUNT(*) FROM wiki_quest_pages GROUP BY native_identity_state ORDER BY native_identity_state"
            ).fetchall()
        )
        wiki_catalog_counts = dict(
            connection.execute(
                "SELECT catalog_state,COUNT(*) FROM wiki_quest_pages GROUP BY catalog_state ORDER BY catalog_state"
            ).fetchall()
        )
        wiki_http_counts = dict(
            connection.execute(
                "SELECT COALESCE(CAST(status_code AS TEXT),'none'),COUNT(*) FROM wiki_quest_pages GROUP BY status_code ORDER BY status_code"
            ).fetchall()
        )
        wiki_detail_counts = dict(
            connection.execute(
                "SELECT CASE detail_present WHEN 1 THEN 'present' ELSE 'missing' END,COUNT(*) FROM wiki_quest_pages GROUP BY detail_present ORDER BY detail_present DESC"
            ).fetchall()
        )
        summary = {
            "closure_states": closure_counts,
            "comparison_states": comparison_counts,
            "native_grant_types": dict(
                connection.execute(
                    "SELECT act_detail_type,COUNT(*) FROM quest_item_grants GROUP BY act_detail_type ORDER BY act_detail_type"
                ).fetchall()
            ),
            "schema_version": SCHEMA_VERSION,
            "table_counts": table_counts,
            "tool_version": TOOL_VERSION,
            "wiki_detail_presence": wiki_detail_counts,
            "wiki_http_statuses": wiki_http_counts,
            "wiki_catalog_states": wiki_catalog_counts,
            "wiki_identity_states": wiki_identity_counts,
            "wiki_page_states": wiki_counts,
        }
        atomic_text(paths["summary"], canonical_json(summary, pretty=True))
        gap_rows: list[dict[str, Any]] = []
        for row in connection.execute(
            """
            SELECT c.quest_id,c.item_id,c.overall_state,cl.closure_state,
                   cl.blocker_roots_json,c.evidence_json
            FROM quest_item_comparisons c
            LEFT JOIN item_closure cl USING(item_id)
            WHERE c.overall_state<>'match'
               OR cl.closure_state NOT IN ('complete_native_closure','generic_dependency_free_candidate')
            ORDER BY c.quest_id,c.item_id,c.comparison_key
            """
        ):
            blockers = json.loads(row["blocker_roots_json"] or "[]")
            gap_rows.append(
                {
                    "quest_id": row["quest_id"],
                    "item_id": row["item_id"],
                    "comparison_state": row["overall_state"],
                    "closure_state": row["closure_state"],
                    "blocker": "|".join(str(value.get("root_code", "")) for value in blockers),
                    "evidence_json": row["evidence_json"],
                }
            )
        paths["gaps"].parent.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(prefix=f".{paths['gaps'].name}.", dir=paths["gaps"].parent)
        os.close(handle)
        temporary = Path(name)
        try:
            with temporary.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=("quest_id", "item_id", "comparison_state", "closure_state", "blocker", "evidence_json"),
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(gap_rows)
            temporary.replace(paths["gaps"])
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        viewer_rows = []
        for row in connection.execute(
            """
            SELECT c.quest_id,c.item_id,c.overall_state,
                   g.grant_phase,g.selection_mode,p.page_state,cl.closure_state,
                   cl.blocker_roots_json
            FROM quest_item_comparisons c
            LEFT JOIN quest_item_grants g USING(grant_key)
            LEFT JOIN wiki_quest_pages p USING(quest_id)
            LEFT JOIN item_closure cl USING(item_id)
            ORDER BY c.quest_id,c.item_id,c.comparison_key
            """
        ):
            blockers = json.loads(row["blocker_roots_json"] or "[]")
            viewer_rows.append(
                {
                    "quest_id": row["quest_id"],
                    "item_id": row["item_id"],
                    "phase": row["grant_phase"],
                    "selection": row["selection_mode"],
                    "wiki": row["page_state"],
                    "comparison": row["overall_state"],
                    "closure": row["closure_state"],
                    "blocker": " | ".join(str(value.get("root_code", "")) for value in blockers),
                }
            )
        _write_viewer(
            paths["viewer"],
            {
                "rows": viewer_rows,
                "summary": {
                    "grants": table_counts["quest_item_grants"],
                    "mentions": table_counts["wiki_quest_item_mentions"],
                },
            },
        )
        return summary
    finally:
        connection.close()


def build_quest_item_crosswalk(config: ForensicsConfig) -> dict[str, Any]:
    paths = crosswalk_paths(config)
    extraction = extract_native_grants(config.stage_40)
    cache_manifest = quest_item_cache(config) / "snapshot-manifest.json"
    if not cache_manifest.is_file():
        raise FileNotFoundError(f"Freeze quest item wiki first: {cache_manifest}")
    source_paths = {
        "stage_20_items": config.stage_20,
        "stage_40_quests": config.stage_40,
        "stage_70_wiki": config.stage_70,
        "consolidated": config.consolidated,
        "quest_detail_cache_manifest": cache_manifest,
        "builder": Path(__file__).resolve(),
    }
    overlap_incident = (
        config.stage_70_wiki_cache
        / "detail-superseded-overlap-v1"
        / "incident-manifest.json"
    )
    if overlap_incident.is_file():
        source_paths["quest_detail_overlap_incident_manifest"] = overlap_incident
    for path in source_paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hashes = {role: sha256_file(path) for role, path in source_paths.items()}
    identity_states = _native_identity_states(config.stage_70)
    pages, mentions = _load_wiki_pages_and_mentions(config, extraction.quest_ids, identity_states)
    item_ids = sorted(
        {int(row["item_id"]) for row in extraction.grants}
        | {int(row["item_id"]) for row in mentions}
    )
    stage20 = _open_read_only(config.stage_20)
    consolidated = _open_read_only(config.consolidated)
    try:
        closures = [_item_closure_row(stage20, consolidated, item_id) for item_id in item_ids]
    finally:
        stage20.close()
        consolidated.close()
    comparisons = _comparison_rows(extraction.grants, mentions, pages)
    paths["database"].parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        prefix=f".{paths['database'].stem}.", suffix=".sqlite3", dir=paths["database"].parent
    )
    os.close(handle)
    temporary = Path(name)
    temporary.unlink(missing_ok=True)
    connection: sqlite3.Connection | None = None
    try:
        connection = _create_database(temporary)
        _insert_metadata(connection, "client_build", config.client_build)
        _insert_metadata(connection, "tool", {"name": TOOL_NAME, "version": TOOL_VERSION})
        _insert_metadata(connection, "schema_version", SCHEMA_VERSION)
        _insert_metadata(connection, "parser_version", PARSER_VERSION)
        _insert_metadata(connection, "authority_order", ["stage40_native", "stage20_and_consolidated", "stage70_wiki"])
        _insert_metadata(connection, "native_extraction", extraction.stats)
        _insert_metadata(connection, "comparison_vocabulary", sorted(OVERALL_STATES))
        _insert_metadata(
            connection,
            "closure_state_policy",
            {
                "generic_dependency_free_candidate_is_runtime_ready": False,
                "wiki_can_create_native_relation": False,
            },
        )
        for role, path in source_paths.items():
            authority = (
                "client_native"
                if role.startswith("stage_") and role != "stage_70_wiki"
                else ("external_corroborative" if "wiki" in role or "cache" in role else "derived_forensic")
            )
            _insert_source_artifact(
                connection,
                role=role,
                path=path,
                digest=source_hashes[role],
                authority=authority,
                provenance=TOOL_NAME,
                evidence={"read_only": role != "builder"},
            )
        connection.executemany(
            """
            INSERT INTO quest_item_grants VALUES(
                :grant_key,:quest_id,:component_id,:component_kind_id,:grant_phase,
                :quest_act_id,:act_detail_type,:act_detail_id,:selection_mode,
                :item_id,:count,:grade_id,:rank,:result,:cleanup,:destroy_when_drop,
                :drop_when_destroy,:show_action_bar,:try_equip,:native_state,
                :provenance,:evidence_json
            )
            """,
            [
                {**row, "evidence_json": canonical_json(row["evidence"])}
                for row in extraction.grants
            ],
        )
        connection.executemany(
            "INSERT INTO orphan_grant_details VALUES(?,?,?,?,?,?,?)",
            [
                (
                    stable_key("orphan_grant_detail", row["source_table"], row["act_detail_id"], row["state"]),
                    row["source_table"],
                    row["act_detail_id"],
                    row["item_id"],
                    row["state"],
                    canonical_json(row["row"]),
                    canonical_json(row["evidence"]),
                )
                for row in extraction.orphans
            ],
        )
        connection.executemany(
            """
            INSERT INTO wiki_quest_pages VALUES(
                :quest_id,:url,:status_code,:response_sha256,:page_state,
                :native_identity_state,:catalog_state,:detail_present,
                :parser_version,:evidence_json
            )
            """,
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in pages],
        )
        connection.executemany(
            """
            INSERT INTO wiki_quest_item_mentions VALUES(
                :mention_key,:quest_id,:item_id,:section_kind,:ordinal,
                :visible_count,:label,:href,:parse_state,:response_sha256,
                :context_json,:evidence_json
            )
            """,
            [
                {
                    **row,
                    "context_json": canonical_json(row["context"]),
                    "evidence_json": canonical_json(row["evidence"]),
                }
                for row in mentions
            ],
        )
        connection.executemany(
            """
            INSERT INTO item_closure VALUES(
                :item_id,:entity_key,:native_state,:lifecycle,:concrete_type,
                :impl_id,:use_skill_id,:buff_id,:craft_id,:closure_state,
                :missing_dependencies_json,:blocker_roots_json,:provenance,
                :evidence_json
            )
            """,
            [
                {
                    **row,
                    "missing_dependencies_json": canonical_json(row["missing_dependencies"]),
                    "blocker_roots_json": canonical_json(row["blocker_roots"]),
                    "evidence_json": canonical_json(row["evidence"]),
                }
                for row in closures
            ],
        )
        connection.executemany(
            """
            INSERT INTO quest_item_comparisons VALUES(
                :comparison_key,:grant_key,:mention_key,:quest_id,:item_id,
                :native_relation_state,:wiki_relation_state,
                :role_comparison_state,:count_comparison_state,:overall_state,
                :evidence_json
            )
            """,
            [{**row, "evidence_json": canonical_json(row["evidence"])} for row in comparisons],
        )
        actual_counts = Counter(row["act_detail_type"] for row in extraction.grants)
        source_counts = extraction.stats["source_act_counts"]
        for act_type in GRANT_TABLES:
            actual = int(actual_counts[act_type])
            expected = int(source_counts.get(act_type, 0))
            _insert_validation(
                connection,
                f"native_grants_preserved:{act_type}",
                "confirmed" if actual == expected else "blocked",
                expected,
                actual,
                {"stage40_sha256": source_hashes["stage_40_quests"]},
            )
        terminal_pages = sum(
            1
            for row in pages
            if row["page_state"]
            in {
                "confirmed",
                "partial",
                "redirected_confirmed",
                "redirected_partial",
                "permanent_missing",
                "parse_failed",
            }
        )
        _insert_validation(
            connection,
            "candidate_quests_have_reproducible_wiki_state",
            "confirmed" if terminal_pages == len(extraction.quest_ids) else "blocked",
            len(extraction.quest_ids),
            terminal_pages,
        )
        invalid_mentions = sum(
            1
            for row in mentions
            if row["section_kind"] not in SECTION_KINDS or int(row["ordinal"]) <= 0
        )
        _insert_validation(
            connection,
            "wiki_mentions_preserve_section_and_ordinal",
            "confirmed" if invalid_mentions == 0 else "blocked",
            0,
            invalid_mentions,
        )
        _insert_validation(
            connection,
            "item_ids_preserved",
            "confirmed" if len(closures) == len(item_ids) else "blocked",
            len(item_ids),
            len(closures),
        )
        unexplained_orphans = sum(
            1 for row in extraction.orphans if row["state"] != "unlinked_detail"
        )
        _insert_validation(
            connection,
            "orphan_relations_explained",
            "confirmed" if unexplained_orphans == 0 else "blocked",
            0,
            unexplained_orphans,
            {"orphan_states": extraction.stats["orphan_states"]},
        )
        context_missing_grants = sum(
            1
            for row in extraction.grants
            if row["evidence"].get("context_state") == "missing"
        )
        _insert_validation(
            connection,
            "missing_context_identities_preserved",
            "confirmed",
            None,
            context_missing_grants,
            {
                "classification": "grant_preserved_from_component_act_detail_join",
                "native_state": "unknown",
            },
        )
        invalid_comparisons = sorted(
            {row["overall_state"] for row in comparisons} - OVERALL_STATES
        )
        _insert_validation(
            connection,
            "comparison_vocabulary_closed",
            "confirmed" if not invalid_comparisons else "blocked",
            [],
            invalid_comparisons,
        )
        anchor_actual = {
            "quest_2259": sum(
                1
                for row in extraction.grants
                if row["quest_id"] == 2259
                and row["component_id"] == 9956
                and row["quest_act_id"] == 22574
                and row["act_detail_id"] == 2233
                and row["item_id"] == 16259
                and row["count"] == 1
            ),
            "quest_2260_grants": sum(
                1 for row in extraction.grants if row["quest_id"] == 2260
            ),
            "quest_2258_sections": {
                str(row["item_id"]): row["section_kind"]
                for row in mentions
                if row["quest_id"] == 2258 and row["item_id"] in {16288, 23633}
            },
            "quest_330_modes": sorted(
                {row["selection_mode"] for row in extraction.grants if row["quest_id"] == 330}
            ),
        }
        anchor_expected = {
            "quest_2259": 1,
            "quest_2260_grants": 6,
            "quest_2258_sections": {"16288": "quest_item", "23633": "fixed_reward"},
            "quest_330_modes": ["fixed", "selective"],
        }
        _insert_validation(
            connection,
            "mandatory_anchor_cases",
            "confirmed" if anchor_actual == anchor_expected else "blocked",
            anchor_expected,
            anchor_actual,
        )
        if source_hashes["stage_40_quests"] == KNOWN_STAGE_40_SHA256:
            baseline_actual = {
                **{key: int(actual_counts[key]) for key in GRANT_TABLES},
                "candidate_quests": len(extraction.quest_ids),
                "quest_act_supply_items_orphans": sum(
                    1
                    for row in extraction.orphans
                    if row["source_table"] == "quest_act_supply_items"
                    and row["state"] == "unlinked_detail"
                ),
            }
            _insert_validation(
                connection,
                "known_stage40_baseline",
                "confirmed" if baseline_actual == KNOWN_BASELINES else "blocked",
                KNOWN_BASELINES,
                baseline_actual,
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
        key: {
            "bytes": path.stat().st_size,
            "path": path.resolve().as_posix(),
            "sha256": sha256_file(path),
        }
        for key, path in paths.items()
        if key != "manifest" and path.is_file()
    }
    manifest = {
        "authority": "client_forensics_only",
        "client_build": config.client_build,
        "commands": [
            "python -B -m client_forensics freeze-quest-item-wiki --resume",
            "python -B -m client_forensics build-quest-item-crosswalk",
            "python -B -m client_forensics validate-quest-item-crosswalk",
        ],
        "determinism": {
            "atomic_output": True,
            "stable_ordering": True,
            "timestamps_in_reproducible_outputs": False,
        },
        "inputs": {
            role: {
                "bytes": path.stat().st_size,
                "path": path.resolve().as_posix(),
                "sha256": source_hashes[role],
            }
            for role, path in source_paths.items()
        },
        "outputs": output_hashes,
        "parser_version": PARSER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }
    atomic_text(paths["manifest"], canonical_json(manifest, pretty=True))
    return {
        "database": paths["database"],
        "database_sha256": output_hashes["database"]["sha256"],
        "manifest": paths["manifest"],
        "summary": summary,
    }


def validate_quest_item_crosswalk(config: ForensicsConfig) -> dict[str, Any]:
    paths = crosswalk_paths(config)
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    connection = _open_read_only(paths["database"])
    try:
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        failed_events = [
            dict(row)
            for row in connection.execute(
                "SELECT check_name,state,actual_json FROM validation_events WHERE state<>'confirmed' ORDER BY check_name"
            )
        ]
        vocabulary = {
            str(row[0])
            for row in connection.execute("SELECT DISTINCT overall_state FROM quest_item_comparisons")
        }
        invalid_vocabulary = sorted(vocabulary - OVERALL_STATES)
        orphan_grants = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM quest_item_grants g
                LEFT JOIN item_closure c USING(item_id)
                WHERE c.item_id IS NULL
                """
            ).fetchone()[0]
        )
        anchor_2259 = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM quest_item_grants
                WHERE quest_id=2259 AND component_id=9956 AND quest_act_id=22574
                  AND act_detail_id=2233 AND item_id=16259 AND count=1
                """
            ).fetchone()[0]
        )
        anchor_2260 = int(
            connection.execute(
                "SELECT COUNT(*) FROM quest_item_grants WHERE quest_id=2260"
            ).fetchone()[0]
        )
        anchor_2258 = dict(
            connection.execute(
                """
                SELECT item_id,section_kind FROM wiki_quest_item_mentions
                WHERE quest_id=2258 AND item_id IN (16288,23633)
                ORDER BY item_id
                """
            ).fetchall()
        )
        anchor_330_modes = dict(
            connection.execute(
                """
                SELECT selection_mode,COUNT(*) FROM quest_item_grants
                WHERE quest_id=330 GROUP BY selection_mode ORDER BY selection_mode
                """
            ).fetchall()
        )
        checks = {
            "quick_check": quick,
            "integrity_check": integrity,
            "failed_validation_events": failed_events,
            "invalid_comparison_vocabulary": invalid_vocabulary,
            "grants_without_item_closure": orphan_grants,
            "anchor_2259": anchor_2259,
            "anchor_2260_grants": anchor_2260,
            "anchor_2258_sections": anchor_2258,
            "anchor_330_modes": anchor_330_modes,
        }
        expected_anchors = (
            anchor_2259 == 1
            and anchor_2260 == 6
            and anchor_2258.get(16288) == "quest_item"
            and anchor_2258.get(23633) == "fixed_reward"
            and anchor_330_modes.get("fixed", 0) > 0
            and anchor_330_modes.get("selective", 0) > 0
        )
        if (
            quick != "ok"
            or integrity != "ok"
            or failed_events
            or invalid_vocabulary
            or orphan_grants
            or not expected_anchors
        ):
            raise RuntimeError(f"Quest item crosswalk validation failed: {checks}")
        for key, record in manifest["outputs"].items():
            path = paths[key]
            actual = sha256_file(path)
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
