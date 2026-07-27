from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable

from .config import ForensicsConfig
from .util import (
    canonical_json,
    open_sqlite_read_only,
    sha256_bytes,
    sha256_file,
    table_names,
    write_bytes_atomic,
    write_text_atomic,
)


WIKI_SOURCE = "wiki_archerage_visible"
WIKI_SCHEMA_VERSION = 1
WIKI_PARSER_VERSION = "1"
DEFAULT_BASE_URL = "https://wiki.archerage.to"
DEFAULT_LOCALE = "na-en"
DEFAULT_CRAWL_DELAY = 1.0
USER_AGENT = "AAEmu-Item-Forensics/1.4 (local research; robots-aware)"
ENTITY_KINDS = {
    "items",
    "quests",
    "npcs",
    "doodads",
    "skills",
    "buffs",
    "crafts",
    "achievements",
    "titles",
    "slaves",
}
ENTITY_LINK = re.compile(
    r"^/(?P<locale>[^/]+)/db/"
    r"(?P<kind>items|quests|npcs|doodads|skills|buffs|crafts|"
    r"achievements|titles|slaves)/(?P<id>\d+)(?:[/?#].*)?$"
)
SPACE = re.compile(r"\s+")
TITLE_SUFFIX = re.compile(
    r"\s*-\s*(?:Item|Quest|NPC|Object|Skill|Buff|Craft|Achievement|"
    r"Title|Slave)\s*-\s*ArcheRage Wiki\s*$",
    re.IGNORECASE,
)


WIKI_AUDIT_SCHEMA = """
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE wiki_snapshots (
    entity_kind TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    content_sha256 TEXT,
    content_bytes INTEGER NOT NULL,
    parse_state TEXT NOT NULL,
    native_state TEXT NOT NULL,
    page_type TEXT,
    name TEXT,
    category TEXT,
    grade TEXT,
    level INTEGER,
    text_digest TEXT,
    normalized_json TEXT NOT NULL,
    PRIMARY KEY(entity_kind, entity_id)
) WITHOUT ROWID;

CREATE TABLE wiki_edges (
    src_kind TEXT NOT NULL,
    src_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    dst_kind TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    label TEXT NOT NULL,
    context_json TEXT NOT NULL,
    state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    PRIMARY KEY(src_kind, src_id, relation, dst_kind, dst_id, label)
) WITHOUT ROWID;

CREATE TABLE wiki_assertions (
    entity_kind TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    native_value_json TEXT NOT NULL,
    wiki_value_json TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY(entity_kind, entity_id, field_name)
) WITHOUT ROWID;

CREATE INDEX ix_wiki_edges_dst ON wiki_edges(dst_kind, dst_id);
CREATE INDEX ix_wiki_assertions_state ON wiki_assertions(state, field_name);
"""


def _clean_text(value: str) -> str:
    return SPACE.sub(" ", value).strip()


@dataclass(frozen=True)
class WikiLink:
    kind: str
    entity_id: str
    label: str
    href: str
    context: tuple[str, ...]
    relation_hint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "context": list(self.context),
            "entity_id": self.entity_id,
            "href": self.href,
            "kind": self.kind,
            "label": self.label,
            "relation_hint": self.relation_hint,
        }


@dataclass(frozen=True)
class ParsedWikiPage:
    entity_kind: str
    entity_id: int
    page_type: str | None
    name: str | None
    category: str | None
    grade: str | None
    level: int | None
    text_digest: str
    links: tuple[WikiLink, ...]
    map_links: tuple[str, ...]
    parse_state: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "entity_id": self.entity_id,
            "entity_kind": self.entity_kind,
            "grade": self.grade,
            "level": self.level,
            "links": [link.as_dict() for link in self.links],
            "map_links": list(self.map_links),
            "name": self.name,
            "page_type": self.page_type,
            "parse_state": self.parse_state,
            "text_digest": self.text_digest,
        }


class _ArcheRagePageParser(HTMLParser):
    def __init__(self, entity_id: int) -> None:
        super().__init__(convert_charrefs=True)
        self.entity_id = entity_id
        self.title_parts: list[str] = []
        self.in_title = False
        self.started = False
        self.ended = False
        self.text: list[str] = []
        self.links: list[tuple[str, str, tuple[str, ...]]] = []
        self.map_links: list[str] = []
        self.anchor_href: str | None = None
        self.anchor_text: list[str] = []
        self.anchor_context: tuple[str, ...] = ()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() == "a" and self.started and not self.ended:
            self.anchor_href = attributes.get("href")
            self.anchor_text = []
            self.anchor_context = tuple(self.text[-6:])

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False
        if tag.lower() != "a" or self.anchor_href is None:
            return
        label = _clean_text(" ".join(self.anchor_text))
        href = self.anchor_href
        if href.startswith("/") and "/db/maps/" in href:
            self.map_links.append(href)
        else:
            match = ENTITY_LINK.match(href)
            if match:
                self.links.append((href, label, self.anchor_context))
        self.anchor_href = None
        self.anchor_text = []
        self.anchor_context = ()

    def handle_data(self, data: str) -> None:
        text = _clean_text(data)
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        if not self.started and text == f"ID: {self.entity_id}":
            self.started = True
        if self.started and (
            "Archerage.to - the first ArcheAge Private Server" in text
            or text == "Database"
        ):
            self.ended = True
        if self.started and not self.ended:
            self.text.append(text)
            if self.anchor_href is not None:
                self.anchor_text.append(text)


def _relation_hint(context: Iterable[str]) -> str:
    value = " | ".join(context).lower()
    rules = (
        ("accept quest from npc", "accept_from"),
        ("report to npc", "report_to"),
        ("opens access to the quest", "unlocks"),
        ("use:", "use"),
        ("quests", "quest"),
        ("reward", "reward"),
        ("spawns", "spawn"),
        ("obtain method", "obtain"),
    )
    for token, relation in rules:
        if token in value:
            return relation
    return "visible_link"


def parse_wiki_page(
    payload: bytes,
    *,
    entity_kind: str,
    entity_id: int,
    locale: str,
) -> ParsedWikiPage:
    text = payload.decode("utf-8", errors="replace")
    parser = _ArcheRagePageParser(entity_id)
    parser.feed(text)
    title = _clean_text(" ".join(parser.title_parts))
    name = TITLE_SUFFIX.sub("", title).strip() or None
    page_type = parser.text[1] if len(parser.text) > 1 else None
    level: int | None = None
    for index, value in enumerate(parser.text):
        if value != "Level:" or index + 1 >= len(parser.text):
            continue
        candidate = parser.text[index + 1]
        if candidate.isdigit():
            level = int(candidate)
        break
    unique_links: dict[tuple[str, str], WikiLink] = {}
    for href, label, context in parser.links:
        match = ENTITY_LINK.match(href)
        if not match or match.group("locale") != locale:
            continue
        link = WikiLink(
            kind=match.group("kind"),
            entity_id=match.group("id"),
            label=label,
            href=href,
            context=context,
            relation_hint=_relation_hint(context),
        )
        key = (link.kind, link.entity_id)
        current = unique_links.get(key)
        score = (
            link.relation_hint != "visible_link",
            bool(link.label and not link.label.isdigit()),
            len(link.label),
        )
        current_score = (
            (
                current.relation_hint != "visible_link",
                bool(current.label and not current.label.isdigit()),
                len(current.label),
            )
            if current
            else (-1, -1, -1)
        )
        if current is None or score > current_score:
            unique_links[key] = link
    normalized_text = "\n".join(parser.text)
    if parser.started and name and page_type:
        state = "confirmed"
    elif parser.started and page_type:
        state = "partial"
    else:
        state = "parse_failed"
    category = None
    grade = None
    if page_type == "Item":
        category = parser.text[2] if len(parser.text) > 2 else None
        grade = parser.text[3] if len(parser.text) > 3 else None
    return ParsedWikiPage(
        entity_kind=entity_kind,
        entity_id=entity_id,
        page_type=page_type,
        name=name,
        category=category,
        grade=grade,
        level=level,
        text_digest=sha256_bytes(normalized_text.encode("utf-8")),
        links=tuple(unique_links[key] for key in sorted(unique_links)),
        map_links=tuple(sorted(set(parser.map_links))),
        parse_state=state,
    )


def _cache_paths(
    cache_dir: Path, locale: str, entity_kind: str, entity_id: int
) -> tuple[Path, Path]:
    root = cache_dir / locale / entity_kind
    return root / f"{entity_id}.html", root / f"{entity_id}.meta.json"


def write_wiki_snapshot(
    cache_dir: Path,
    *,
    base_url: str,
    locale: str,
    entity_kind: str,
    entity_id: int,
    status_code: int,
    payload: bytes,
    content_type: str = "text/html;charset=UTF-8",
) -> dict[str, Any]:
    if entity_kind not in ENTITY_KINDS:
        raise ValueError(f"Unsupported wiki entity kind: {entity_kind}")
    raw_path, metadata_path = _cache_paths(
        cache_dir, locale, entity_kind, entity_id
    )
    digest = sha256_bytes(payload) if payload else None
    if payload:
        write_bytes_atomic(raw_path, payload)
    elif raw_path.exists():
        raw_path.unlink()
    metadata = {
        "base_url": base_url.rstrip("/"),
        "content_bytes": len(payload),
        "content_sha256": digest,
        "content_type": content_type,
        "entity_id": entity_id,
        "entity_kind": entity_kind,
        "locale": locale,
        "parser_version": WIKI_PARSER_VERSION,
        "provenance": WIKI_SOURCE,
        "status_code": status_code,
        "url": (
            f"{base_url.rstrip('/')}/{locale}/db/{entity_kind}/{entity_id}"
        ),
    }
    write_text_atomic(metadata_path, canonical_json(metadata, pretty=True))
    return metadata


def _read_metadata(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "content_bytes",
        "entity_id",
        "entity_kind",
        "locale",
        "status_code",
        "url",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"Wiki metadata missing {missing}: {path}")
    return value


def snapshot_manifest(cache_dir: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(cache_dir.glob("*/*/*.meta.json")):
        metadata = _read_metadata(path)
        record = {
            key: metadata.get(key)
            for key in (
                "content_bytes",
                "content_sha256",
                "entity_id",
                "entity_kind",
                "locale",
                "parser_version",
                "provenance",
                "status_code",
                "url",
            )
        }
        records.append(record)
    statuses: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for record in records:
        status = str(record["status_code"])
        statuses[status] = statuses.get(status, 0) + 1
        kind = str(record["entity_kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
    digest = sha256_bytes(canonical_json(records).encode("utf-8"))
    robots_path = cache_dir / "robots-policy.json"
    robots = (
        json.loads(robots_path.read_text(encoding="utf-8"))
        if robots_path.is_file()
        else None
    )
    manifest = {
        "cache_digest": digest,
        "entity_kinds": dict(sorted(kinds.items())),
        "parser_version": WIKI_PARSER_VERSION,
        "provenance": WIKI_SOURCE,
        "records": len(records),
        "robots": robots,
        "schema_version": WIKI_SCHEMA_VERSION,
        "statuses": dict(sorted(statuses.items())),
    }
    write_text_atomic(
        cache_dir / "snapshot-manifest.json",
        canonical_json(manifest, pretty=True),
    )
    return manifest


def wiki_seed_ids(
    database: Path,
    *,
    scope: str,
    explicit_ids: Iterable[int] = (),
    limit: int | None = None,
) -> list[int]:
    requested = sorted({value for value in explicit_ids if value > 0})
    if requested:
        return requested[:limit] if limit is not None else requested
    connection = open_sqlite_read_only(database)
    try:
        if scope == "all":
            statement = "SELECT item_id FROM items WHERE item_id>0 ORDER BY item_id"
        elif scope == "catalog-only":
            statement = """
                SELECT i.item_id
                FROM items i
                JOIN runtime_coverage rc ON rc.item_id=i.item_id
                WHERE i.item_id>0 AND rc.coverage='catalog_only'
                ORDER BY i.item_id
            """
        elif scope == "unresolved":
            statement = """
                SELECT DISTINCT i.item_id
                FROM items i
                JOIN descriptors d ON d.item_id=i.item_id
                WHERE i.item_id>0 AND d.state IN ('missing','unknown','blocked')
                ORDER BY i.item_id
            """
        else:
            raise ValueError(f"Unsupported wiki seed scope: {scope}")
        rows = [int(row[0]) for row in connection.execute(statement)]
    finally:
        connection.close()
    return rows[:limit] if limit is not None else rows


def wiki_edge_ids(
    database: Path,
    *,
    entity_kind: str,
    limit: int | None = None,
) -> list[int]:
    if entity_kind not in ENTITY_KINDS:
        raise ValueError(f"Unsupported wiki entity kind: {entity_kind}")
    connection = open_sqlite_read_only(database)
    try:
        rows = [
            int(row[0])
            for row in connection.execute(
                """
                SELECT DISTINCT CAST(dst_id AS INTEGER)
                FROM wiki_edges
                WHERE dst_kind=?
                  AND dst_id<>'' AND dst_id NOT GLOB '*[^0-9]*'
                  AND CAST(dst_id AS INTEGER)>0
                ORDER BY CAST(dst_id AS INTEGER)
                """,
                (entity_kind,),
            )
        ]
    finally:
        connection.close()
    return rows[:limit] if limit is not None else rows


class WikiHttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        requested_delay: float,
        fetcher: Callable[[str], tuple[int, bytes, str]] | None = None,
    ) -> None:
        if requested_delay < DEFAULT_CRAWL_DELAY:
            raise ValueError(
                f"Wiki crawl delay must be at least {DEFAULT_CRAWL_DELAY} second"
            )
        self.base_url = base_url.rstrip("/")
        self.requested_delay = requested_delay
        self.fetcher = fetcher
        self.last_request: float | None = None
        self.delay = requested_delay
        self.robots_policy: dict[str, Any] | None = None

    def _wait(self) -> None:
        if self.last_request is None:
            return
        remaining = self.delay - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)

    def _request(self, url: str) -> tuple[int, bytes, str]:
        self._wait()
        try:
            if self.fetcher is not None:
                return self.fetcher(url)
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                return (
                    int(response.status),
                    response.read(),
                    response.headers.get_content_type(),
                )
        except urllib.error.HTTPError as error:
            body = error.read()
            return (
                int(error.code),
                body,
                error.headers.get_content_type() if error.headers else "",
            )
        finally:
            self.last_request = time.monotonic()

    def load_robots(self) -> None:
        robots_url = f"{self.base_url}/robots.txt"
        status, payload, _ = self._request(robots_url)
        if status != 200:
            raise RuntimeError(f"Unable to verify wiki robots.txt: HTTP {status}")
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(payload.decode("utf-8", errors="replace").splitlines())
        if not parser.can_fetch(USER_AGENT, f"{self.base_url}/na-en/db/items/1"):
            raise RuntimeError("wiki robots.txt does not permit this scanner")
        robots_delay = parser.crawl_delay(USER_AGENT)
        if robots_delay is None:
            robots_delay = parser.crawl_delay("*")
        self.delay = max(self.requested_delay, float(robots_delay or 0))
        self.robots_policy = {
            "allowed": True,
            "content_sha256": sha256_bytes(payload),
            "crawl_delay": self.delay,
            "url": robots_url,
        }

    def fetch(self, url: str) -> tuple[int, bytes, str]:
        retryable = {408, 425, 429, 500, 502, 503, 504}
        last: tuple[int, bytes, str] | None = None
        for _ in range(3):
            last = self._request(url)
            if last[0] not in retryable:
                return last
        assert last is not None
        return last


def scan_wiki(
    config: ForensicsConfig,
    *,
    entity_kind: str = "items",
    scope: str = "unresolved",
    explicit_ids: Iterable[int] = (),
    limit: int | None = None,
    refresh: bool = False,
    delay: float = DEFAULT_CRAWL_DELAY,
    base_url: str = DEFAULT_BASE_URL,
    locale: str = DEFAULT_LOCALE,
    progress: Callable[[str], None] | None = None,
    fetcher: Callable[[str], tuple[int, bytes, str]] | None = None,
) -> dict[str, Any]:
    if entity_kind not in ENTITY_KINDS:
        raise ValueError(f"Unsupported wiki entity kind: {entity_kind}")
    if not config.database.is_file():
        raise FileNotFoundError(
            f"Run item_forensics run-all before scan-wiki: {config.database}"
        )
    ids = wiki_seed_ids(
        config.database,
        scope=scope,
        explicit_ids=explicit_ids,
        limit=limit,
    )
    cache_dir = config.wiki_cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    client = WikiHttpClient(
        base_url=base_url,
        requested_delay=delay,
        fetcher=fetcher,
    )
    client.load_robots()
    assert client.robots_policy is not None
    write_text_atomic(
        cache_dir / "robots-policy.json",
        canonical_json(client.robots_policy, pretty=True),
    )
    downloaded = 0
    skipped = 0
    permanent_missing = 0
    errors: list[dict[str, Any]] = []
    for index, entity_id in enumerate(ids, 1):
        raw_path, metadata_path = _cache_paths(
            cache_dir, locale, entity_kind, entity_id
        )
        if metadata_path.is_file() and not refresh:
            metadata = _read_metadata(metadata_path)
            digest = metadata.get("content_sha256")
            if (
                not digest
                or (
                    raw_path.is_file()
                    and sha256_file(raw_path) == str(digest)
                )
            ):
                skipped += 1
                continue
        url = f"{base_url.rstrip('/')}/{locale}/db/{entity_kind}/{entity_id}"
        try:
            status, payload, content_type = client.fetch(url)
            if status == 200:
                parsed = parse_wiki_page(
                    payload,
                    entity_kind=entity_kind,
                    entity_id=entity_id,
                    locale=locale,
                )
                if parsed.parse_state == "parse_failed":
                    errors.append(
                        {
                            "entity_id": entity_id,
                            "error": "page did not contain the expected entity marker",
                            "status_code": status,
                        }
                    )
            elif status in {404, 410}:
                permanent_missing += 1
            else:
                errors.append(
                    {
                        "entity_id": entity_id,
                        "error": f"HTTP {status}",
                        "status_code": status,
                    }
                )
                continue
            write_wiki_snapshot(
                cache_dir,
                base_url=base_url,
                locale=locale,
                entity_kind=entity_kind,
                entity_id=entity_id,
                status_code=status,
                payload=payload,
                content_type=content_type,
            )
            downloaded += 1
        except (OSError, RuntimeError, ValueError) as error:
            errors.append({"entity_id": entity_id, "error": str(error)})
        if progress and (index == len(ids) or index % 25 == 0):
            progress(
                f"wiki {index}/{len(ids)} downloaded={downloaded} "
                f"skipped={skipped} errors={len(errors)}"
            )
    manifest = snapshot_manifest(cache_dir)
    error_document = {
        "entity_kind": entity_kind,
        "errors": sorted(errors, key=lambda value: int(value["entity_id"])),
        "locale": locale,
        "provenance": WIKI_SOURCE,
        "requested": len(ids),
    }
    error_path = cache_dir / f"scan-errors-{locale}-{entity_kind}.json"
    write_text_atomic(
        error_path,
        canonical_json(error_document, pretty=True),
    )
    reports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(cache_dir.glob("scan-errors-*.json"))
    ]
    aggregate_errors = {
        "errors": [
            {
                **error,
                "entity_kind": report["entity_kind"],
                "locale": report["locale"],
            }
            for report in reports
            for error in report["errors"]
        ],
        "provenance": WIKI_SOURCE,
        "reports": len(reports),
    }
    write_text_atomic(
        cache_dir / "scan-errors.json",
        canonical_json(aggregate_errors, pretty=True),
    )
    return {
        "cache_dir": cache_dir,
        "crawl_delay": client.delay,
        "downloaded": downloaded,
        "errors": len(errors),
        "errors_report": error_path,
        "manifest": cache_dir / "snapshot-manifest.json",
        "manifest_digest": manifest["cache_digest"],
        "permanent_missing": permanent_missing,
        "requested": len(ids),
        "skipped": skipped,
    }


def _audit_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA page_size=4096")
    connection.execute("PRAGMA auto_vacuum=NONE")
    connection.executescript(WIKI_AUDIT_SCHEMA)
    connection.execute(f"PRAGMA user_version={WIKI_SCHEMA_VERSION}")
    return connection


def _assertion(
    connection: sqlite3.Connection,
    *,
    entity_kind: str,
    entity_id: int,
    field_name: str,
    native_value: Any,
    wiki_value: Any,
    state: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO wiki_assertions(
            entity_kind,entity_id,field_name,native_value_json,
            wiki_value_json,state,evidence_json
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            entity_kind,
            entity_id,
            field_name,
            canonical_json(native_value),
            canonical_json(wiki_value),
            state,
            canonical_json(evidence),
        ),
    )


def _item_assertions(
    connection: sqlite3.Connection,
    native: sqlite3.Row | None,
    parsed: ParsedWikiPage | None,
    metadata: dict[str, Any],
) -> None:
    entity_id = int(metadata["entity_id"])
    status = int(metadata["status_code"])
    evidence = {
        "authority": False,
        "content_sha256": metadata.get("content_sha256"),
        "descriptor_family": (
            native["descriptor_family"] if native is not None else None
        ),
        "descriptor_states": (
            native["descriptor_states"] if native is not None else None
        ),
        "provenance": WIKI_SOURCE,
        "url": metadata["url"],
    }
    presence_state = "exact_match" if status == 200 else "wiki_missing"
    if parsed is not None and parsed.parse_state != "confirmed":
        presence_state = f"wiki_{parsed.parse_state}"
    _assertion(
        connection,
        entity_kind="items",
        entity_id=entity_id,
        field_name="page_presence",
        native_value=native is not None,
        wiki_value=status,
        state=presence_state,
        evidence=evidence,
    )
    if native is None or parsed is None:
        return
    for field_name, value in (
        ("category_hint", parsed.category),
        ("grade_hint", parsed.grade),
    ):
        if value is None:
            continue
        _assertion(
            connection,
            entity_kind="items",
            entity_id=entity_id,
            field_name=field_name,
            native_value=None,
            wiki_value=value,
            state="external_hint",
            evidence=evidence,
        )
    native_level = int(native["level"]) if native["level"] is not None else None
    if parsed.level is None:
        level_state = "not_exposed"
    elif parsed.level == native_level:
        level_state = "exact_match"
    else:
        level_state = "conflict"
    _assertion(
        connection,
        entity_kind="items",
        entity_id=entity_id,
        field_name="level",
        native_value=native_level,
        wiki_value=parsed.level,
        state=level_state,
        evidence=evidence,
    )
    native_name = str(native["name"] or "")
    if native_name.startswith("<ref:") and parsed.name:
        name_state = "external_resolves_opaque"
    elif native_name == parsed.name:
        name_state = "exact_match"
    else:
        name_state = "unverifiable_locale"
    _assertion(
        connection,
        entity_kind="items",
        entity_id=entity_id,
        field_name="name",
        native_value=native_name,
        wiki_value=parsed.name,
        state=name_state,
        evidence=evidence,
    )
    linked = {(link.kind, int(link.entity_id)) for link in parsed.links}
    relations = (
        ("use_skill_id", "skills"),
        ("buff_id", "buffs"),
        ("craft_id", "crafts"),
        ("loot_quest_id", "quests"),
    )
    for field_name, target_kind in relations:
        native_value = int(native[field_name] or 0)
        if native_value <= 0:
            continue
        match = (target_kind, native_value) in linked
        _assertion(
            connection,
            entity_kind="items",
            entity_id=entity_id,
            field_name=field_name,
            native_value=native_value,
            wiki_value=match,
            state="exact_match" if match else "not_exposed",
            evidence=evidence,
        )


def _write_audit_csv(connection: sqlite3.Connection, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(
            handle, "w", encoding="utf-8", newline="", closefd=True
        ) as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(
                (
                    "entity_kind",
                    "entity_id",
                    "field_name",
                    "state",
                    "native_value_json",
                    "wiki_value_json",
                )
            )
            for row in connection.execute(
                """
                SELECT entity_kind,entity_id,field_name,state,
                       native_value_json,wiki_value_json
                FROM wiki_assertions
                ORDER BY
                    CASE state WHEN 'conflict' THEN 0 ELSE 1 END,
                    entity_kind,entity_id,field_name
                """
            ):
                writer.writerow(tuple(row))
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def audit_wiki(
    config: ForensicsConfig,
    *,
    cache_dir: Path | None = None,
    output_database: Path | None = None,
) -> dict[str, Any]:
    source_cache = (cache_dir or config.wiki_cache_dir).resolve()
    target = (output_database or config.wiki_database).resolve()
    if not config.database.is_file():
        raise FileNotFoundError(f"Forensics database not found: {config.database}")
    metadata_paths = sorted(source_cache.glob("*/*/*.meta.json"))
    if not metadata_paths:
        raise FileNotFoundError(f"No frozen wiki snapshots found: {source_cache}")
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".sqlite", dir=target.parent
    )
    os.close(handle)
    Path(temporary_name).unlink()
    try:
        native = open_sqlite_read_only(config.database)
        client = open_sqlite_read_only(config.client_compact)
        connection = _audit_connection(Path(temporary_name))
        native_items = {
            int(row["item_id"]): row
            for row in native.execute(
                """
                SELECT
                    i.item_id,i.name,i.level,i.use_skill_id,i.buff_id,
                    i.craft_id,i.loot_quest_id,
                    (
                        SELECT GROUP_CONCAT(d.state, ',')
                        FROM descriptors d
                        WHERE d.item_id=i.item_id
                    ) AS descriptor_states,
                    (
                        SELECT d.family
                        FROM descriptors d
                        WHERE d.item_id=i.item_id
                        ORDER BY
                            CASE d.state WHEN 'confirmed' THEN 0
                                         WHEN 'unknown' THEN 1 ELSE 2 END,
                            d.family
                        LIMIT 1
                    ) AS descriptor_family
                FROM items i WHERE i.item_id>0 ORDER BY i.item_id
                """
            )
        }
        item_ids = set(native_items)
        client_tables = table_names(client)
        skill_ids = (
            {
                int(row[0])
                for row in client.execute(
                    "SELECT id FROM skills WHERE id>0 ORDER BY id"
                )
            }
            if "skills" in client_tables
            else set()
        )
        native_ids_by_kind: dict[str, set[int]] = {"items": item_ids}
        if "skills" in client_tables:
            native_ids_by_kind["skills"] = skill_ids
        native_entity_kinds = {
            "buffs": "buff",
            "crafts": "craft",
            "doodads": "doodad",
        }
        for wiki_kind, native_kind in native_entity_kinds.items():
            native_ids_by_kind[wiki_kind] = {
                int(row[0])
                for row in native.execute(
                    """
                    SELECT DISTINCT entity_id
                    FROM native_entities
                    WHERE entity_kind=?
                      AND state='confirmed'
                    ORDER BY entity_id
                    """,
                    (native_kind,),
                )
            }
        manifest = snapshot_manifest(source_cache)
        metadata_values = {
            "authority": "corroborative_only",
            "native_database_sha256": sha256_file(config.database),
            "parser_version": WIKI_PARSER_VERSION,
            "provenance": WIKI_SOURCE,
            "schema_version": WIKI_SCHEMA_VERSION,
            "snapshot_digest": manifest["cache_digest"],
        }
        connection.executemany(
            "INSERT INTO metadata(key,value) VALUES (?,?)",
            sorted((key, str(value)) for key, value in metadata_values.items()),
        )
        for metadata_path in metadata_paths:
            metadata = _read_metadata(metadata_path)
            entity_kind = str(metadata["entity_kind"])
            entity_id = int(metadata["entity_id"])
            status = int(metadata["status_code"])
            raw_path, _ = _cache_paths(
                source_cache,
                str(metadata["locale"]),
                entity_kind,
                entity_id,
            )
            parsed: ParsedWikiPage | None = None
            parse_state = "not_available"
            normalized: dict[str, Any] = {}
            if status == 200:
                if not raw_path.is_file():
                    raise FileNotFoundError(f"Wiki snapshot body missing: {raw_path}")
                digest = sha256_file(raw_path)
                if digest != metadata.get("content_sha256"):
                    raise ValueError(f"Wiki snapshot hash mismatch: {raw_path}")
                parsed = parse_wiki_page(
                    raw_path.read_bytes(),
                    entity_kind=entity_kind,
                    entity_id=entity_id,
                    locale=str(metadata["locale"]),
                )
                parse_state = parsed.parse_state
                normalized = parsed.as_dict()
            connection.execute(
                """
                INSERT INTO wiki_snapshots(
                    entity_kind,entity_id,url,status_code,content_sha256,
                    content_bytes,parse_state,native_state,page_type,name,
                    category,grade,level,text_digest,normalized_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    entity_kind,
                    entity_id,
                    metadata["url"],
                    status,
                    metadata.get("content_sha256"),
                    int(metadata["content_bytes"]),
                    parse_state,
                    (
                        "confirmed"
                        if entity_kind in native_ids_by_kind
                        and entity_id in native_ids_by_kind[entity_kind]
                        else (
                            "missing"
                            if entity_kind in native_ids_by_kind
                            else "unknown"
                        )
                    ),
                    parsed.page_type if parsed else None,
                    parsed.name if parsed else None,
                    parsed.category if parsed else None,
                    parsed.grade if parsed else None,
                    parsed.level if parsed else None,
                    parsed.text_digest if parsed else None,
                    canonical_json(normalized),
                ),
            )
            if parsed:
                for link in parsed.links:
                    context = {
                        "authority": False,
                        "content_sha256": metadata.get("content_sha256"),
                        "href": link.href,
                        "text": list(link.context),
                    }
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO wiki_edges(
                            src_kind,src_id,relation,dst_kind,dst_id,label,
                            context_json,state,provenance
                        ) VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            entity_kind,
                            entity_id,
                            link.relation_hint,
                            link.kind,
                            link.entity_id,
                            link.label,
                            canonical_json(context),
                            (
                                "native_match"
                                if link.kind in native_ids_by_kind
                                and int(link.entity_id)
                                in native_ids_by_kind[link.kind]
                                else (
                                    "wiki_only"
                                    if link.kind in native_ids_by_kind
                                    else "unknown_native"
                                )
                            ),
                            WIKI_SOURCE,
                        ),
                    )
                for map_link in parsed.map_links:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO wiki_edges(
                            src_kind,src_id,relation,dst_kind,dst_id,label,
                            context_json,state,provenance
                        ) VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            entity_kind,
                            entity_id,
                            "map",
                            "map",
                            map_link,
                            "",
                            canonical_json({"authority": False, "href": map_link}),
                            "unknown_native",
                            WIKI_SOURCE,
                        ),
                    )
            if entity_kind == "items":
                _item_assertions(
                    connection,
                    native_items.get(entity_id),
                    parsed,
                    metadata,
                )
        client.close()
        native.close()
        connection.commit()
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if quick != "ok" or integrity != "ok":
            raise RuntimeError(
                f"Wiki audit SQLite validation failed: "
                f"quick={quick}, integrity={integrity}"
            )
        connection.execute("VACUUM")
        connection.commit()
        summary = {
            "assertion_states": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    """
                    SELECT state,COUNT(*) FROM wiki_assertions
                    GROUP BY state ORDER BY state
                    """
                )
            },
            "edge_states": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    """
                    SELECT state,COUNT(*) FROM wiki_edges
                    GROUP BY state ORDER BY state
                    """
                )
            },
            "closure_frontier": {
                f"{row[0]}:{row[1]}": int(row[2])
                for row in connection.execute(
                    """
                    SELECT e.dst_kind,e.state,COUNT(DISTINCT e.dst_id)
                    FROM wiki_edges e
                    LEFT JOIN wiki_snapshots s
                      ON s.entity_kind=e.dst_kind
                     AND CAST(s.entity_id AS TEXT)=e.dst_id
                    WHERE s.entity_id IS NULL
                    GROUP BY e.dst_kind,e.state
                    ORDER BY e.dst_kind,e.state
                    """
                )
            },
            "item_categories": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    """
                    SELECT category,COUNT(*) FROM wiki_snapshots
                    WHERE entity_kind='items' AND category IS NOT NULL
                    GROUP BY category ORDER BY COUNT(*) DESC,category
                    """
                )
            },
            "integrity_check": integrity,
            "opaque_names_resolved": int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM wiki_assertions
                    WHERE state='external_resolves_opaque'
                    """
                ).fetchone()[0]
            ),
            "parse_states": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    """
                    SELECT parse_state,COUNT(*) FROM wiki_snapshots
                    GROUP BY parse_state ORDER BY parse_state
                    """
                )
            },
            "snapshot_native_states": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    """
                    SELECT native_state,COUNT(*) FROM wiki_snapshots
                    GROUP BY native_state ORDER BY native_state
                    """
                )
            },
            "quick_check": quick,
            "snapshot_digest": manifest["cache_digest"],
            "snapshots": int(
                connection.execute("SELECT COUNT(*) FROM wiki_snapshots").fetchone()[0]
            ),
        }
        _write_audit_csv(connection, config.wiki_audit_csv)
        connection.close()
        Path(temporary_name).replace(target)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    summary["database"] = target.resolve().as_posix()
    summary["database_sha256"] = sha256_file(target)
    summary["csv"] = config.wiki_audit_csv.resolve().as_posix()
    report = {
        "authority": "corroborative_only",
        "database_sha256": summary["database_sha256"],
        "provenance": WIKI_SOURCE,
        "summary": summary,
    }
    write_text_atomic(
        config.wiki_audit_report,
        canonical_json(report, pretty=True),
    )
    return summary
