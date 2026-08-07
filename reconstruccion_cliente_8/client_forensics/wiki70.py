from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.request
import urllib.robotparser
from collections import defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, TYPE_CHECKING

from . import TOOL_NAME, TOOL_VERSION
from .config import ForensicsConfig
from .schema import open_read_only
from .util import (
    atomic_text,
    canonical_json,
    entity_key,
    sha256_file,
    sha256_text,
    stable_key,
)

if TYPE_CHECKING:
    from .build import BuildContext


STAGE = 70
WIKI_AUTHORITY = "external_corroborative"
WIKI_PROVENANCE = "wiki.archerage.to_visible_database"
USER_AGENT = (
    "AAEmu-Client-Forensics/0.9 "
    "(local compatibility research; robots-aware)"
)
MINIMUM_DELAY = 1.0
CATALOG_KINDS = ("items", "quests", "npcs", "doodads", "skills")
KIND_MAP = {
    "items": "item",
    "quests": "quest",
    "npcs": "npc",
    "doodads": "doodad",
    "skills": "skill",
    "buffs": "buff",
    "crafts": "craft",
    "achievements": "achievement",
    "titles": "title",
    "slaves": "slave",
}
DETAIL_LINK = re.compile(
    r"^/(?P<locale>[^/]+)/db/"
    r"(?P<kind>items|quests|npcs|doodads|skills|buffs|crafts|"
    r"achievements|titles|slaves)/(?P<id>\d+)(?:[/?#].*)?$"
)
CATALOG_LINK_TEMPLATE = r"/{locale}/db/{kind}/([^\"'/?#]+)"
SPACE = re.compile(r"\s+")


def _clean(value: str) -> str:
    return SPACE.sub(" ", value).strip()


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


def _catalog_paths(
    cache: Path,
    locale: str,
    kind: str,
    slug: str,
) -> tuple[Path, Path]:
    filename = "__root__" if slug == "" else slug
    root = cache / "catalog" / locale / kind
    return root / f"{filename}.html", root / f"{filename}.meta.json"


def _catalog_url(config: ForensicsConfig, kind: str, slug: str) -> str:
    suffix = f"/{slug}" if slug else ""
    return (
        f"{config.wiki_base_url}/{config.wiki_locale}/db/{kind}{suffix}"
    )


def _metadata(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "content_bytes",
        "content_sha256",
        "kind",
        "locale",
        "slug",
        "status_code",
        "url",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"Wiki snapshot metadata missing {missing}: {path}")
    return value


def _write_catalog_snapshot(
    config: ForensicsConfig,
    *,
    kind: str,
    slug: str,
    status_code: int,
    content_type: str,
    payload: bytes,
) -> dict[str, Any]:
    html_path, metadata_path = _catalog_paths(
        config.stage_70_wiki_cache,
        config.wiki_locale,
        kind,
        slug,
    )
    _atomic_bytes(html_path, payload)
    digest = sha256_file(html_path)
    metadata = {
        "content_bytes": len(payload),
        "content_sha256": digest,
        "content_type": content_type,
        "kind": kind,
        "locale": config.wiki_locale,
        "provenance": WIKI_PROVENANCE,
        "slug": slug,
        "status_code": status_code,
        "url": _catalog_url(config, kind, slug),
    }
    atomic_text(metadata_path, canonical_json(metadata, pretty=True))
    return metadata


def _discover_slugs(
    payload: bytes,
    *,
    locale: str,
    kind: str,
) -> list[str]:
    pattern = re.compile(
        CATALOG_LINK_TEMPLATE.format(
            locale=re.escape(locale),
            kind=re.escape(kind),
        ).encode("ascii")
    )
    values = {
        match.decode("utf-8", errors="strict")
        for match in pattern.findall(payload)
        if not match.isdigit()
    }
    return sorted(value for value in values if re.fullmatch(r"[a-z0-9-]+", value))


class WikiCatalogClient:
    def __init__(self, config: ForensicsConfig, delay: float) -> None:
        if delay < MINIMUM_DELAY:
            raise ValueError(f"Wiki delay must be at least {MINIMUM_DELAY}")
        self.config = config
        self.delay = delay
        self.last_request: float | None = None

    def _wait(self) -> None:
        if self.last_request is None:
            return
        remaining = self.delay - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)

    def request(self, url: str) -> tuple[int, bytes, str]:
        retryable = {408, 425, 429, 500, 502, 503, 504}
        last: tuple[int, bytes, str] | None = None
        for _ in range(3):
            self._wait()
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT},
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    last = (
                        int(response.status),
                        response.read(),
                        response.headers.get_content_type(),
                    )
            except urllib.error.HTTPError as error:
                last = (
                    int(error.code),
                    error.read(),
                    error.headers.get_content_type() if error.headers else "",
                )
            finally:
                self.last_request = time.monotonic()
            if last[0] not in retryable:
                return last
        assert last is not None
        return last

    def load_robots(self) -> dict[str, Any]:
        url = f"{self.config.wiki_base_url}/robots.txt"
        status, payload, content_type = self.request(url)
        if status != 200:
            raise RuntimeError(f"Unable to freeze wiki robots.txt: HTTP {status}")
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(url)
        parser.parse(payload.decode("utf-8", errors="replace").splitlines())
        sample = _catalog_url(self.config, "items", "")
        if not parser.can_fetch(USER_AGENT, sample):
            raise RuntimeError("wiki robots.txt forbids the catalog acquisition")
        robots_delay = parser.crawl_delay(USER_AGENT)
        if robots_delay is None:
            robots_delay = parser.crawl_delay("*")
        self.delay = max(self.delay, float(robots_delay or 0))
        robots_path = self.config.stage_70_wiki_cache / "robots.txt"
        _atomic_bytes(robots_path, payload)
        policy = {
            "allowed": True,
            "content_bytes": len(payload),
            "content_sha256": sha256_file(robots_path),
            "content_type": content_type,
            "crawl_delay": self.delay,
            "url": url,
            "user_agent": USER_AGENT,
        }
        atomic_text(
            self.config.stage_70_wiki_cache / "robots-policy.json",
            canonical_json(policy, pretty=True),
        )
        return policy


def _snapshot_valid(html_path: Path, metadata_path: Path) -> bool:
    if not html_path.is_file() or not metadata_path.is_file():
        return False
    metadata = _metadata(metadata_path)
    return (
        int(metadata["status_code"]) in {200, 404, 410}
        and int(metadata["content_bytes"]) == html_path.stat().st_size
        and str(metadata["content_sha256"]).upper() == sha256_file(html_path)
    )


def _wiki_cache_manifest(config: ForensicsConfig) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    for path in sorted(
        config.stage_70_wiki_cache.glob("catalog/*/*/*.meta.json"),
        key=lambda value: value.as_posix(),
    ):
        metadata = _metadata(path)
        html_path = path.with_name(path.name.replace(".meta.json", ".html"))
        if not html_path.is_file():
            raise FileNotFoundError(f"Wiki catalog body missing: {html_path}")
        digest = sha256_file(html_path)
        if digest != str(metadata["content_sha256"]).upper():
            raise ValueError(f"Wiki catalog hash mismatch: {html_path}")
        record = {
            "content_bytes": int(metadata["content_bytes"]),
            "content_sha256": digest,
            "kind": str(metadata["kind"]),
            "locale": str(metadata["locale"]),
            "slug": str(metadata["slug"]),
            "status_code": int(metadata["status_code"]),
            "url": str(metadata["url"]),
        }
        records.append(record)
        kind = str(metadata["kind"])
        category_counts[kind] = category_counts.get(kind, 0) + 1
    robots_path = config.stage_70_wiki_cache / "robots-policy.json"
    if not records or not robots_path.is_file():
        raise FileNotFoundError("Stage 70 wiki cache is incomplete")
    manifest = {
        "authority": WIKI_AUTHORITY,
        "cache_digest": sha256_text(canonical_json(records)),
        "catalog_pages": len(records),
        "kinds": dict(sorted(category_counts.items())),
        "locale": config.wiki_locale,
        "provenance": WIKI_PROVENANCE,
        "records": records,
        "robots_policy_sha256": sha256_file(robots_path),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
    }
    atomic_text(
        config.stage_70_wiki_cache / "snapshot-manifest.json",
        canonical_json(manifest, pretty=True),
    )
    return manifest


def freeze_stage_70_wiki(
    config: ForensicsConfig,
    *,
    refresh: bool = False,
    delay: float = MINIMUM_DELAY,
    progress: Any = None,
) -> dict[str, Any]:
    """Freeze all visible root/category catalogs without crawling every ID."""

    config.stage_70_wiki_cache.mkdir(parents=True, exist_ok=True)
    client = WikiCatalogClient(config, delay)
    robots = client.load_robots()
    downloaded = 0
    skipped = 0
    discovered: dict[str, list[str]] = {}
    for kind in CATALOG_KINDS:
        root_html, root_meta = _catalog_paths(
            config.stage_70_wiki_cache,
            config.wiki_locale,
            kind,
            "",
        )
        if refresh or not _snapshot_valid(root_html, root_meta):
            status, payload, content_type = client.request(
                _catalog_url(config, kind, "")
            )
            if status != 200:
                raise RuntimeError(f"Wiki catalog {kind} returned HTTP {status}")
            _write_catalog_snapshot(
                config,
                kind=kind,
                slug="",
                status_code=status,
                content_type=content_type,
                payload=payload,
            )
            downloaded += 1
        else:
            payload = root_html.read_bytes()
            skipped += 1
        discovered[kind] = _discover_slugs(
            payload,
            locale=config.wiki_locale,
            kind=kind,
        )

    queue = [
        (kind, slug)
        for kind in CATALOG_KINDS
        for slug in discovered[kind]
    ]
    for index, (kind, slug) in enumerate(queue, 1):
        html_path, metadata_path = _catalog_paths(
            config.stage_70_wiki_cache,
            config.wiki_locale,
            kind,
            slug,
        )
        if not refresh and _snapshot_valid(html_path, metadata_path):
            skipped += 1
        else:
            status, payload, content_type = client.request(
                _catalog_url(config, kind, slug)
            )
            if status not in {200, 404, 410}:
                raise RuntimeError(
                    f"Wiki catalog {kind}/{slug} returned HTTP {status}"
                )
            _write_catalog_snapshot(
                config,
                kind=kind,
                slug=slug,
                status_code=status,
                content_type=content_type,
                payload=payload,
            )
            downloaded += 1
        if progress and (index % 25 == 0 or index == len(queue)):
            progress(
                f"wiki catalogs {index}/{len(queue)} "
                f"downloaded={downloaded} skipped={skipped}"
            )
    manifest = _wiki_cache_manifest(config)
    manifest["downloaded"] = downloaded
    manifest["skipped"] = skipped
    manifest["robots"] = robots
    manifest["discovered_categories"] = {
        key: len(value) for key, value in discovered.items()
    }
    return manifest


@dataclass
class CatalogRow:
    entity_id: int
    values: dict[str, str]


class _CatalogParser(HTMLParser):
    def __init__(self, kind: str, locale: str) -> None:
        super().__init__(convert_charrefs=True)
        self.kind = kind
        self.locale = locale
        self.table_depth = 0
        self.headers: list[str] = []
        self.rows: list[CatalogRow] = []
        self.in_header = False
        self.in_row = False
        self.in_cell = False
        self.cell_index = -1
        self.cells: list[list[str]] = []
        self.row_id: int | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {key: value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "table":
            if attributes.get("id") == f"{self.kind}-list":
                self.table_depth = 1
            elif self.table_depth:
                self.table_depth += 1
            return
        if not self.table_depth:
            return
        if tag == "th":
            self.in_header = True
            self.headers.append(
                attributes.get("data-data") or f"column_{len(self.headers)}"
            )
        elif tag == "tr" and not self.in_row:
            self.in_row = True
            self.cells = []
            self.cell_index = -1
            self.row_id = None
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.cell_index += 1
            self.cells.append([])
        elif tag == "a" and self.in_row:
            match = DETAIL_LINK.match(attributes.get("href", ""))
            if (
                match
                and match.group("locale") == self.locale
                and match.group("kind") == self.kind
            ):
                self.row_id = int(match.group("id"))
        elif tag == "img" and self.in_cell:
            src = attributes.get("src")
            if src:
                self.cells[self.cell_index].append(src)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "table" and self.table_depth:
            self.table_depth -= 1
            return
        if not self.table_depth:
            return
        if tag == "th":
            self.in_header = False
        elif tag == "td":
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            values = {
                header: _clean(" ".join(self.cells[index]))
                for index, header in enumerate(self.headers)
                if index < len(self.cells)
                and _clean(" ".join(self.cells[index]))
            }
            candidate = self.row_id
            if candidate is None and values.get("id", "").isdigit():
                candidate = int(values["id"])
            if candidate is not None:
                self.rows.append(CatalogRow(candidate, values))
            self.in_row = False
            self.in_cell = False

    def handle_data(self, data: str) -> None:
        if self.table_depth and self.in_cell:
            value = _clean(data)
            if value:
                self.cells[self.cell_index].append(value)


def parse_catalog_page(
    payload: bytes,
    *,
    kind: str,
    locale: str,
) -> list[CatalogRow]:
    parser = _CatalogParser(kind, locale)
    parser.feed(payload.decode("utf-8", errors="replace"))
    return parser.rows


@dataclass
class WikiAggregate:
    kind: str
    entity_id: int
    values: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    catalogs: set[str] = field(default_factory=set)
    response_hashes: set[str] = field(default_factory=set)
    detail_sources: list[dict[str, Any]] = field(default_factory=list)
    detail_pages: list[Any] = field(default_factory=list)
    explicit_statuses: set[int] = field(default_factory=set)


@dataclass(frozen=True)
class NativeEntity:
    entity_key: str
    kind: str
    entity_id: int
    lifecycle: str
    state: str
    properties: dict[str, Any]


def _native_entities(config: ForensicsConfig) -> dict[tuple[str, int], NativeEntity]:
    paths = (
        config.stage_20,
        config.stage_30,
        config.stage_40,
        config.stage_50,
        config.stage_60,
    )
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    entities: dict[str, dict[str, Any]] = {}
    property_candidates: dict[str, dict[str, list[tuple[int, str, Any]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    namespace_priority = {
        "client.items": 100,
        "quest_contexts": 100,
        "localized_text": 95,
        "npcs": 90,
        "skills": 100,
    }
    for stage_index, path in enumerate(paths):
        connection = open_read_only(path)
        try:
            for row in connection.execute(
                """
                SELECT entity_key,kind,native_id,lifecycle,state
                FROM entities
                WHERE kind IN ('item','quest','npc','doodad','skill')
                ORDER BY entity_key
                """
            ):
                native_id = str(row["native_id"])
                if not native_id.isdigit() or int(native_id) <= 0:
                    continue
                entities[str(row["entity_key"])] = {
                    "entity_key": str(row["entity_key"]),
                    "kind": str(row["kind"]),
                    "entity_id": int(native_id),
                    "lifecycle": str(row["lifecycle"]),
                    "state": str(row["state"]),
                }
            for row in connection.execute(
                """
                SELECT entity_key,namespace,property_name,value_type,
                       value_text,value_integer,value_real,value_boolean,value_json
                FROM entity_properties
                WHERE property_name IN ('name','level')
                ORDER BY property_key
                """
            ):
                key = str(row["entity_key"])
                if key not in entities:
                    continue
                value_type = str(row["value_type"])
                if value_type == "text":
                    value: Any = row["value_text"]
                elif value_type == "integer":
                    value = row["value_integer"]
                elif value_type == "real":
                    value = row["value_real"]
                elif value_type == "boolean":
                    value = bool(row["value_boolean"])
                else:
                    continue
                priority = (
                    stage_index * 1000
                    + namespace_priority.get(str(row["namespace"]), 0)
                )
                property_candidates[key][str(row["property_name"])].append(
                    (priority, str(row["namespace"]), value)
                )
        finally:
            connection.close()
    result: dict[tuple[str, int], NativeEntity] = {}
    for value in entities.values():
        properties = {
            name: sorted(candidates, key=lambda item: (item[0], item[1]))[-1][2]
            for name, candidates in property_candidates[
                value["entity_key"]
            ].items()
        }
        item = NativeEntity(properties=properties, **value)
        result[(item.kind, item.entity_id)] = item
    return result


def _detail_metadata_paths(config: ForensicsConfig) -> list[Path]:
    roots = (
        config.stage_70_wiki_cache / "detail" / config.wiki_locale / "quests",
        config.stage_70_wiki_cache / "specializations",
        config.source_item_wiki_cache,
        config.source_quest_wiki_cache,
        config.source_skill_wiki_cache,
    )
    values: set[Path] = set()
    for root in roots:
        patterns = ("*.meta.json", "**/*.meta.json")
        for pattern in patterns:
            values.update(path.resolve() for path in root.glob(pattern))
    structured_root = (
        config.stage_70_wiki_cache / "detail" / config.wiki_locale / "quests"
    ).resolve()
    return sorted(
        values,
        key=lambda path: (
            0 if structured_root in path.parents else 1,
            path.as_posix(),
        ),
    )


def _load_detail_parser(config: ForensicsConfig) -> Any:
    package_parent = str(config.source_item_tool_root.parent)
    if package_parent not in sys.path:
        sys.path.insert(0, package_parent)
    from item_forensics.wiki import parse_wiki_page

    return parse_wiki_page


def _detail_html_path(metadata_path: Path) -> Path:
    return metadata_path.with_name(
        metadata_path.name.replace(".meta.json", ".html")
    )


def _comparison_for_value(
    native: NativeEntity | None,
    name: str,
    wiki_values: list[str],
) -> str:
    if native is None:
        return "wiki_only"
    if len(wiki_values) != 1:
        return "conflict"
    native_value = native.properties.get(name)
    if native_value is None:
        return "unresolved"
    wiki_value = wiki_values[0]
    if isinstance(native_value, str):
        if native_value.startswith("<ref:"):
            return "unresolved"
        if _clean(native_value).casefold() == _clean(wiki_value).casefold():
            return "match"
        # The Kakao compact is predominantly ko-KR while this frozen wiki
        # surface is en-US. Different localized labels are not a semantic
        # contradiction and must not be promoted to a native data conflict.
        return "unresolved" if name == "name" else "conflict"
    try:
        return "match" if float(native_value) == float(wiki_value) else "conflict"
    except (TypeError, ValueError):
        return "unresolved"


def _insert_artifact(
    connection: sqlite3.Connection,
    config: ForensicsConfig,
    *,
    role: str,
    path: Path,
    digest: str,
    evidence: dict[str, Any],
) -> str:
    key = stable_key("artifact", role, path.resolve().as_posix(), digest)
    connection.execute(
        """
        INSERT OR IGNORE INTO artifacts(
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
            config.client_build,
            WIKI_AUTHORITY,
            "confirmed",
            WIKI_PROVENANCE,
            canonical_json(evidence),
        ),
    )
    return key


def _insert_validation(
    connection: sqlite3.Connection,
    *,
    check_name: str,
    status: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO validation_events(
            validation_key,scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            stable_key("validation", "stage", "70", check_name),
            "stage",
            "70",
            check_name,
            status,
            canonical_json(evidence),
        ),
    )


def _aggregate_catalogs(
    config: ForensicsConfig,
    connection: sqlite3.Connection,
) -> tuple[dict[tuple[str, int], WikiAggregate], dict[str, int], str]:
    manifest_path = config.stage_70_wiki_cache / "snapshot-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Freeze Stage 70 wiki catalogs first: {manifest_path}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    aggregates: dict[tuple[str, int], WikiAggregate] = {}
    parsed_rows: dict[str, int] = defaultdict(int)
    for metadata_path in sorted(
        config.stage_70_wiki_cache.glob("catalog/*/*/*.meta.json"),
        key=lambda path: path.as_posix(),
    ):
        metadata = _metadata(metadata_path)
        html_path = _detail_html_path(metadata_path)
        digest = sha256_file(html_path)
        if digest != str(metadata["content_sha256"]).upper():
            raise ValueError(f"Wiki catalog hash mismatch: {html_path}")
        kind = str(metadata["kind"])
        slug = str(metadata["slug"])
        rows = parse_catalog_page(
            html_path.read_bytes(),
            kind=kind,
            locale=config.wiki_locale,
        )
        parsed_rows[kind] += len(rows)
        artifact_key = _insert_artifact(
            connection,
            config,
            role="wiki_catalog_snapshot",
            path=html_path,
            digest=digest,
            evidence={
                "artifact_metadata": metadata_path.resolve().as_posix(),
                "kind": kind,
                "slug": slug,
                "status_code": int(metadata["status_code"]),
                "url": str(metadata["url"]),
            },
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO surfaces(
                surface_key,source_stage,source_kind,locator,extension,bytes,
                sha256,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("surface", "wiki_catalog", kind, slug),
                STAGE,
                "wiki_catalog_html",
                str(metadata["url"]),
                ".html",
                html_path.stat().st_size,
                digest,
                "confirmed",
                canonical_json(
                    {
                        "artifact_key": artifact_key,
                        "raw_path": html_path.resolve().as_posix(),
                        "slug": slug,
                    }
                ),
            ),
        )
        label = "__root__" if not slug else slug
        for row in rows:
            canonical_kind = KIND_MAP[kind]
            key = (canonical_kind, row.entity_id)
            aggregate = aggregates.setdefault(
                key,
                WikiAggregate(kind=kind, entity_id=row.entity_id),
            )
            aggregate.catalogs.add(label)
            aggregate.response_hashes.add(digest)
            for name, value in row.values.items():
                if name != "id" and value:
                    aggregate.values[name].add(value)
    return aggregates, dict(sorted(parsed_rows.items())), str(manifest["cache_digest"])


def _merge_detail_pages(
    config: ForensicsConfig,
    connection: sqlite3.Connection,
    aggregates: dict[tuple[str, int], WikiAggregate],
) -> dict[str, int]:
    parser = _load_detail_parser(config)
    counts: dict[str, int] = defaultdict(int)
    # The ordered source list puts the structured quest-detail cache first.
    # Freeze one snapshot per wiki identity so an older cache cannot add a
    # second, heuristic interpretation of the same page.
    seen_sources: set[tuple[str, int]] = set()
    for metadata_path in _detail_metadata_paths(config):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        plural_kind = str(metadata.get("entity_kind", ""))
        if plural_kind not in KIND_MAP:
            continue
        entity_id = int(metadata["entity_id"])
        canonical_kind = KIND_MAP[plural_kind]
        status = int(metadata["status_code"])
        source_identity = (plural_kind, entity_id)
        if source_identity in seen_sources:
            continue
        seen_sources.add(source_identity)
        key = (canonical_kind, entity_id)
        aggregate = aggregates.setdefault(
            key,
            WikiAggregate(kind=plural_kind, entity_id=entity_id),
        )
        aggregate.explicit_statuses.add(status)
        source = {
            "metadata_path": metadata_path.resolve().as_posix(),
            "status_code": status,
            "url": str(metadata["url"]),
        }
        aggregate.detail_sources.append(source)
        counts[plural_kind] += 1
        if status != 200:
            continue
        html_path = _detail_html_path(metadata_path)
        if not html_path.is_file():
            raise FileNotFoundError(f"Wiki detail body missing: {html_path}")
        digest = sha256_file(html_path)
        if digest != str(metadata["content_sha256"]).upper():
            raise ValueError(f"Wiki detail hash mismatch: {html_path}")
        _insert_artifact(
            connection,
            config,
            role="wiki_detail_snapshot",
            path=html_path,
            digest=digest,
            evidence=source,
        )
        if str(metadata.get("parser_version")) == "quest-item-structured-v1":
            from .quest_item_crosswalk import parse_quest_item_page

            page = parse_quest_item_page(
                html_path.read_bytes(),
                entity_kind=plural_kind,
                entity_id=entity_id,
                locale=str(metadata["locale"]),
            )
        else:
            page = parser(
                html_path.read_bytes(),
                entity_kind=plural_kind,
                entity_id=entity_id,
                locale=str(metadata["locale"]),
            )
        aggregate.detail_pages.append(page)
        aggregate.response_hashes.add(digest)
        for name in ("name", "category", "grade", "level", "page_type"):
            value = getattr(page, name)
            if value is not None:
                aggregate.values[name].add(str(value))
        aggregate.values["detail_parse_state"].add(str(page.parse_state))
        aggregate.values["detail_text_digest"].add(str(page.text_digest))
    return dict(sorted(counts.items()))


def populate_stage_70(
    destination: sqlite3.Connection,
    _item_source: sqlite3.Connection,
    context: BuildContext,
) -> None:
    config = context.config
    aggregates, parsed_rows, cache_digest = _aggregate_catalogs(
        config,
        destination,
    )
    detail_counts = _merge_detail_pages(config, destination, aggregates)
    native = _native_entities(config)
    all_keys = sorted(
        set(native) | set(aggregates),
        key=lambda value: (value[0], value[1]),
    )
    relation_rows: dict[str, tuple[Any, ...]] = {}
    comparison_counts: dict[str, int] = defaultdict(int)
    property_counts: dict[str, int] = defaultdict(int)
    explicit_missing = 0
    for canonical_kind, native_id in all_keys:
        native_row = native.get((canonical_kind, native_id))
        aggregate = aggregates.get((canonical_kind, native_id))
        plural_kind = (
            aggregate.kind
            if aggregate is not None
            else next(
                key for key, value in KIND_MAP.items()
                if value == canonical_kind and key in CATALOG_KINDS
            )
        )
        present = bool(
            aggregate
            and (
                aggregate.catalogs
                or aggregate.response_hashes
                or 200 in aggregate.explicit_statuses
            )
        )
        explicit_404 = bool(
            aggregate
            and not present
            and aggregate.explicit_statuses.intersection({404, 410})
        )
        if present and native_row is not None:
            comparison = "match"
        elif present:
            comparison = "wiki_only"
        else:
            comparison = "native_only" if native_row is not None else "unresolved"
        comparison_counts[comparison] += 1
        if explicit_404:
            explicit_missing += 1
        canonical_url = (
            f"{config.wiki_base_url}/{config.wiki_locale}/db/"
            f"{plural_kind}/{native_id}"
        )
        response_hash = None
        if aggregate and aggregate.response_hashes:
            response_hash = sha256_text(
                canonical_json(sorted(aggregate.response_hashes))
            )
        statuses = sorted(aggregate.explicit_statuses) if aggregate else []
        status_code = (
            200 if present else (statuses[0] if len(statuses) == 1 else None)
        )
        wiki_key = stable_key("wiki_entity", plural_kind, native_id)
        destination.execute(
            """
            INSERT INTO wiki_entities(
                wiki_entity_key,entity_key,url,status_code,response_sha256,
                state,comparison_state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                wiki_key,
                entity_key(canonical_kind, native_id),
                canonical_url,
                status_code,
                response_hash,
                "confirmed" if present else ("missing" if explicit_404 else "unknown"),
                comparison,
                canonical_json(
                    {
                        "authority": WIKI_AUTHORITY,
                        "catalog_memberships": (
                            sorted(aggregate.catalogs) if aggregate else []
                        ),
                        "detail_sources": (
                            aggregate.detail_sources if aggregate else []
                        ),
                        "native_lifecycle": (
                            native_row.lifecycle if native_row else None
                        ),
                        "native_state": native_row.state if native_row else None,
                        "negative_evidence_scope": (
                            "all_visible_root_and_category_catalogs"
                            if not present
                            else None
                        ),
                        "response_hashes": (
                            sorted(aggregate.response_hashes)
                            if aggregate
                            else []
                        ),
                    }
                ),
            ),
        )
        if not aggregate:
            continue
        values = dict(aggregate.values)
        if aggregate.catalogs:
            values["catalog_membership"] = set(aggregate.catalogs)
        for property_name in sorted(values):
            wiki_values = sorted(values[property_name])
            comparison_state = (
                _comparison_for_value(
                    native_row,
                    property_name,
                    wiki_values,
                )
                if property_name in {"name", "level"}
                else ("wiki_only" if native_row is None else "unresolved")
            )
            property_counts[comparison_state] += 1
            value: Any = wiki_values[0] if len(wiki_values) == 1 else wiki_values
            destination.execute(
                """
                INSERT INTO wiki_properties(
                    wiki_property_key,wiki_entity_key,property_name,value_json,
                    comparison_state,evidence_json
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    stable_key(
                        "wiki_property",
                        plural_kind,
                        native_id,
                        property_name,
                    ),
                    wiki_key,
                    property_name,
                    canonical_json(value),
                    comparison_state,
                    canonical_json(
                        {
                            "catalog_memberships": sorted(aggregate.catalogs),
                            "native_value": (
                                native_row.properties.get(property_name)
                                if native_row
                                else None
                            ),
                            "source_response_hashes": sorted(
                                aggregate.response_hashes
                            ),
                        }
                    ),
                ),
            )
        for page in aggregate.detail_pages:
            for link in page.links:
                dst_kind = KIND_MAP.get(link.kind, link.kind.rstrip("s"))
                destination_known = (dst_kind, int(link.entity_id)) in native
                relation_comparison = (
                    "match"
                    if destination_known
                    else (
                        "wiki_only"
                        if link.kind in KIND_MAP
                        else "unresolved"
                    )
                )
                relation_key = stable_key(
                    "wiki_relation",
                    plural_kind,
                    native_id,
                    link.relation_hint,
                    dst_kind,
                    link.entity_id,
                    getattr(link, "ordinal", None),
                )
                relation_rows[relation_key] = (
                    relation_key,
                    wiki_key,
                    link.relation_hint,
                    dst_kind,
                    str(link.entity_id),
                    relation_comparison,
                    canonical_json(
                        {
                            "context": list(link.context),
                            "href": link.href,
                            "label": link.label,
                            "native_destination_present": destination_known,
                            "ordinal": getattr(link, "ordinal", None),
                        }
                    ),
                )
            for href in page.map_links:
                relation_key = stable_key(
                    "wiki_relation",
                    plural_kind,
                    native_id,
                    "map",
                    "map",
                    href,
                )
                relation_rows[relation_key] = (
                    relation_key,
                    wiki_key,
                    "map",
                    "map",
                    href,
                    "unresolved",
                    canonical_json({"href": href}),
                )
    destination.executemany(
        """
        INSERT INTO wiki_relations(
            wiki_relation_key,src_wiki_entity_key,relation,dst_kind,dst_id,
            comparison_state,evidence_json
        ) VALUES(?,?,?,?,?,?,?)
        """,
        [relation_rows[key] for key in sorted(relation_rows)],
    )

    for kind in CATALOG_KINDS:
        canonical_kind = KIND_MAP[kind]
        native_count = sum(1 for key in native if key[0] == canonical_kind)
        wiki_count = sum(
            1
            for key, value in aggregates.items()
            if key[0] == canonical_kind
            and (
                value.catalogs
                or value.response_hashes
                or 200 in value.explicit_statuses
            )
        )
        destination.execute(
            """
            INSERT INTO coverage(
                coverage_key,scope_key,dimension,state,capability,authority,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("coverage", "stage70", kind),
                f"wiki_catalog:{kind}",
                "external_visible_catalog",
                "confirmed",
                "corroborative_inventory",
                WIKI_AUTHORITY,
                WIKI_PROVENANCE,
                canonical_json(
                    {
                        "cache_digest": cache_digest,
                        "native_entities": native_count,
                        "parsed_table_rows": parsed_rows.get(kind, 0),
                        "unique_wiki_entities": wiki_count,
                    }
                ),
            ),
        )
        native_only = sum(
            1
            for key in native
            if key[0] == canonical_kind and key not in aggregates
        )
        if native_only:
            destination.execute(
                """
                INSERT INTO opaque_regions(
                    opaque_key,surface,locator,blocker_code,reason,
                    searched_evidence_json,source_stage,state
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("opaque", "stage70", kind, "native_only"),
                    "wiki_visible_catalog",
                    kind,
                    "wiki_catalog_absence_not_http_absence",
                    (
                        "Native IDs absent from the frozen visible catalogs "
                        "were not individually requested; robots-aware catalog "
                        "absence is not proof that their canonical pages do not exist."
                    ),
                    canonical_json(
                        {
                            "cache_digest": cache_digest,
                            "native_only": native_only,
                            "searched": "root_and_all_discovered_category_catalogs",
                        }
                    ),
                    STAGE,
                    "unknown",
                ),
            )

    destination.execute(
        """
        INSERT INTO decoders(
            decoder_key,name,version,sha256,status,inputs_json,
            assumptions_json,provenance
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "stage70:wiki-html-parser",
            "ArcheRage visible catalog/detail HTML normalizer",
            TOOL_VERSION,
            None,
            "confirmed",
            canonical_json(
                {
                    "catalog_cache_digest": cache_digest,
                    "catalog_kinds": list(CATALOG_KINDS),
                    "detail_snapshot_counts": detail_counts,
                }
            ),
            canonical_json(
                {
                    "catalog_absence_is_not_http_404": True,
                    "gameplay_authority": False,
                    "wiki_never_fills_native_gaps": True,
                }
            ),
            WIKI_PROVENANCE,
        ),
    )
    metadata = {
        "stage70.cache_digest": cache_digest,
        "stage70.catalog_rows": sum(parsed_rows.values()),
        "stage70.detail_snapshots": sum(detail_counts.values()),
        "stage70.explicit_missing": explicit_missing,
        "stage70.wiki_entities": len(all_keys),
        "stage70.wiki_relations": len(relation_rows),
    }
    destination.executemany(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        sorted((key, str(value)) for key, value in metadata.items()),
    )
    _insert_validation(
        destination,
        check_name="all_five_catalog_kinds_parsed",
        status="confirmed" if set(parsed_rows) == set(CATALOG_KINDS) else "blocked",
        evidence={"parsed_rows": parsed_rows},
    )
    _insert_validation(
        destination,
        check_name="wiki_entity_union_classified",
        status="confirmed",
        evidence={
            "comparison_states": dict(sorted(comparison_counts.items())),
            "native_entities": len(native),
            "union_entities": len(all_keys),
        },
    )
    _insert_validation(
        destination,
        check_name="wiki_properties_compared",
        status="confirmed",
        evidence={"comparison_states": dict(sorted(property_counts.items()))},
    )
    orphan_properties = int(
        destination.execute(
            """
            SELECT COUNT(*) FROM wiki_properties p
            LEFT JOIN wiki_entities e
              ON e.wiki_entity_key=p.wiki_entity_key
            WHERE e.wiki_entity_key IS NULL
            """
        ).fetchone()[0]
    )
    orphan_relations = int(
        destination.execute(
            """
            SELECT COUNT(*) FROM wiki_relations r
            LEFT JOIN wiki_entities e
              ON e.wiki_entity_key=r.src_wiki_entity_key
            WHERE e.wiki_entity_key IS NULL
            """
        ).fetchone()[0]
    )
    if orphan_properties or orphan_relations:
        raise RuntimeError(
            "Stage 70 orphan wiki rows: "
            f"properties={orphan_properties} relations={orphan_relations}"
        )
    _insert_validation(
        destination,
        check_name="zero_orphan_wiki_rows",
        status="confirmed",
        evidence={
            "orphan_properties": orphan_properties,
            "orphan_relations": orphan_relations,
        },
    )
