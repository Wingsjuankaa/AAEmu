from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .config import ForensicsConfig
from .util import canonical_json, sha256_file


NUMBER_TOKEN = re.compile(r"(?<!\d)(\d{1,10})(?!\d)")
TEXT_EXTENSIONS = {
    ".cfg",
    ".config",
    ".csv",
    ".ini",
    ".json",
    ".lua",
    ".txt",
    ".xml",
}
MAX_TEXT_FILE_BYTES = 64 * 1024 * 1024


def _json_document(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _compact_summary(document: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in sorted(document):
        value = document[key]
        if key == "files" and isinstance(value, list):
            summary[key] = {"count": len(value)}
        elif isinstance(value, list):
            summary[key] = {"count": len(value)}
        elif isinstance(value, dict):
            compact: dict[str, Any] = {}
            for child_key in sorted(value):
                child = value[child_key]
                if isinstance(child, (str, int, float, bool)) or child is None:
                    compact[child_key] = child
                elif isinstance(child, (list, dict)):
                    compact[child_key] = {"count": len(child)}
            summary[key] = compact
        elif isinstance(value, (str, int, float, bool)) or value is None:
            summary[key] = value
    return summary


def _discover_manifests(config: ForensicsConfig) -> list[Path]:
    discovered: set[Path] = set()
    for root in sorted(config.repo_root.glob("reconstruccion_*_8")):
        if not root.is_dir():
            continue
        for pattern in (
            "generated/*manifest*.json",
            "**/generated/*manifest*.json",
            "**/manifest-b*.json",
        ):
            discovered.update(
                path.resolve()
                for path in root.glob(pattern)
                if path.is_file()
            )
    for configured in (config.sql_manifest, config.surface_manifest):
        if configured is not None and configured.is_file():
            discovered.add(configured.resolve())
    return sorted(discovered, key=lambda path: path.as_posix().lower())


def _record_manifest(
    connection: sqlite3.Connection,
    path: Path,
    document: dict[str, Any],
) -> None:
    classification = document.get("classification", {})
    connection.execute(
        """
        INSERT OR REPLACE INTO review_manifests(
            path,sha256,authority,classification_json,summary_json
        ) VALUES (?,?,?,?,?)
        """,
        (
            path.resolve().as_posix(),
            sha256_file(path),
            str(document.get("authority", "")) or None,
            canonical_json(classification),
            canonical_json(_compact_summary(document)),
        ),
    )


def _surface(
    connection: sqlite3.Connection,
    *,
    source_kind: str,
    path: str,
    extension: str,
    bytes_count: int | None,
    digest: str | None,
    status: str,
    evidence: dict[str, Any],
) -> int:
    connection.execute(
        """
        INSERT OR IGNORE INTO client_surfaces(
            source_kind,path,extension,bytes,sha256,status,evidence_json
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            source_kind,
            path.replace("\\", "/"),
            extension.lower() or "<none>",
            bytes_count,
            digest,
            status,
            canonical_json(evidence),
        ),
    )
    row = connection.execute(
        "SELECT surface_id FROM client_surfaces WHERE source_kind=? AND path=?",
        (source_kind, path.replace("\\", "/")),
    ).fetchone()
    assert row is not None
    return int(row[0])


def _record_reference(
    connection: sqlite3.Connection,
    *,
    surface_id: int,
    item_id: int,
    token_kind: str,
    locator: str,
    provenance: str,
    evidence: dict[str, Any],
    state: str = "corroborative",
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO surface_references(
            surface_id,item_id,token_kind,locator,state,provenance,evidence_json
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            surface_id,
            item_id,
            token_kind,
            locator,
            state,
            provenance,
            canonical_json(evidence),
        ),
    )


def _inventory(
    connection: sqlite3.Connection,
    source_kind: str,
    counts: Counter[str],
    byte_counts: Counter[str],
    evidence: dict[str, Any],
) -> None:
    for extension in sorted(counts):
        connection.execute(
            """
            INSERT OR REPLACE INTO surface_inventory(
                source_kind,extension,file_count,total_bytes,evidence_json
            ) VALUES (?,?,?,?,?)
            """,
            (
                source_kind,
                extension,
                int(counts[extension]),
                int(byte_counts[extension]),
                canonical_json(evidence),
            ),
        )


def _scan_client_filesystem_manifest(
    connection: sqlite3.Connection,
    manifest_path: Path,
    document: dict[str, Any],
) -> tuple[int, list[Path]]:
    source = Path(str(document.get("source", "")))
    files = document.get("files")
    if not isinstance(files, list):
        return 0, []
    text_paths: list[Path] = []
    count = 0
    counts: Counter[str] = Counter()
    byte_counts: Counter[str] = Counter()
    for value in files:
        if not isinstance(value, dict) or "path" not in value:
            continue
        relative = str(value["path"]).replace("\\", "/")
        extension = str(value.get("extension") or Path(relative).suffix or "<none>").lower()
        bytes_count = int(value.get("bytes") or 0)
        _surface(
            connection,
            source_kind="client_filesystem",
            path=relative,
            extension=extension,
            bytes_count=bytes_count,
            digest=str(value.get("sha256") or "") or None,
            status="reviewed",
            evidence={
                "focus_hits": value.get("focus_hits", []),
                "manifest": manifest_path.resolve().as_posix(),
            },
        )
        count += 1
        counts[extension] += 1
        byte_counts[extension] += bytes_count
        absolute = source / Path(relative)
        if extension in TEXT_EXTENSIONS and absolute.is_file():
            text_paths.append(absolute)
    _inventory(
        connection,
        "client_filesystem",
        counts,
        byte_counts,
        {"manifest": manifest_path.resolve().as_posix()},
    )
    return count, text_paths


def _scan_lua_manifest(
    connection: sqlite3.Connection,
    manifest_path: Path,
    document: dict[str, Any],
) -> tuple[int, list[Path]]:
    files = document.get("files")
    if not isinstance(files, list):
        return 0, []
    input_root = Path(str(document.get("input", "")))
    name = input_root.name
    output_root = input_root.with_name(
        name.replace("-v1", "-decompiled-v1")
        if name.endswith("-v1")
        else name + "-decompiled"
    )
    text_paths: list[Path] = []
    counts: Counter[str] = Counter()
    byte_counts: Counter[str] = Counter()
    for value in files:
        if not isinstance(value, dict) or "path" not in value:
            continue
        relative = Path(str(value["path"]))
        lua_relative = relative.with_suffix(".lua")
        lua_path = output_root / lua_relative
        bytes_count = int(value.get("lua_size") or 0)
        _surface(
            connection,
            source_kind="gamepak_lua_decompiled",
            path=lua_relative.as_posix(),
            extension=".lua",
            bytes_count=bytes_count,
            digest=str(value.get("lua_sha256") or "") or None,
            status="decompiled" if lua_path.is_file() else "manifest_only",
            evidence={
                "source_path": relative.as_posix(),
                "source_sha256": value.get("source_sha256"),
                "luac_sha256": value.get("luac_sha256"),
                "manifest": manifest_path.resolve().as_posix(),
            },
        )
        counts[".lua"] += 1
        byte_counts[".lua"] += bytes_count
        if lua_path.is_file():
            text_paths.append(lua_path)
    _inventory(
        connection,
        "gamepak_lua_decompiled",
        counts,
        byte_counts,
        {"manifest": manifest_path.resolve().as_posix(), "root": output_root.as_posix()},
    )
    return sum(counts.values()), text_paths


def _xml_roots(document: dict[str, Any]) -> list[Path]:
    roots: set[Path] = set()
    for key in ("all_xml", "world_client_entities", "world_missions"):
        value = document.get(key)
        if isinstance(value, dict) and value.get("root"):
            roots.add(Path(str(value["root"])))
    return sorted(roots, key=lambda path: path.as_posix().lower())


def _add_text_tree(
    connection: sqlite3.Connection,
    root: Path,
    source_kind: str,
) -> list[Path]:
    if not root.is_dir():
        return []
    paths: list[Path] = []
    counts: Counter[str] = Counter()
    byte_counts: Counter[str] = Counter()
    for path in sorted(
        (value for value in root.rglob("*") if value.is_file()),
        key=lambda value: value.as_posix().lower(),
    ):
        extension = path.suffix.lower() or "<none>"
        stat = path.stat()
        relative = path.relative_to(root).as_posix()
        _surface(
            connection,
            source_kind=source_kind,
            path=relative,
            extension=extension,
            bytes_count=stat.st_size,
            digest=None,
            status="reviewed_extraction",
            evidence={"root": root.resolve().as_posix()},
        )
        counts[extension] += 1
        byte_counts[extension] += stat.st_size
        if extension in TEXT_EXTENSIONS and stat.st_size <= MAX_TEXT_FILE_BYTES:
            paths.append(path)
    _inventory(
        connection,
        source_kind,
        counts,
        byte_counts,
        {"root": root.resolve().as_posix()},
    )
    return paths


def _scan_gamepak_index(
    connection: sqlite3.Connection,
    path: Path,
    item_ids: set[int],
) -> dict[str, int]:
    if not path.is_file():
        return {"files": 0, "references": 0}
    counts: Counter[str] = Counter()
    byte_counts: Counter[str] = Counter()
    matches = 0
    files = 0
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        for row in reader:
            name = str(row.get("name") or "").replace("\\", "/")
            if not name:
                continue
            files += 1
            extension = Path(name).suffix.lower() or "<none>"
            size = int(row.get("size") or 0)
            counts[extension] += 1
            byte_counts[extension] += size
            ids = sorted(
                {
                    int(match.group(1))
                    for match in NUMBER_TOKEN.finditer(name)
                    if int(match.group(1)) in item_ids
                }
            )
            if not ids:
                continue
            surface_id = _surface(
                connection,
                source_kind="gamepak_index",
                path=name,
                extension=extension,
                bytes_count=size,
                digest=str(row.get("md5") or "") or None,
                status="indexed",
                evidence={
                    "index": path.resolve().as_posix(),
                    "offset": row.get("offset"),
                    "digest_kind": "md5",
                },
            )
            for item_id in ids:
                _record_reference(
                    connection,
                    surface_id=surface_id,
                    item_id=item_id,
                    token_kind="path_numeric_token",
                    locator=name,
                    provenance="game_pak",
                    evidence={
                        "authority": False,
                        "note": "Filename correlation only; not gameplay authority.",
                    },
                )
                matches += 1
    _inventory(
        connection,
        "gamepak_index",
        counts,
        byte_counts,
        {"index": path.resolve().as_posix(), "sha256": sha256_file(path)},
    )
    return {"files": files, "references": matches}


def _surface_id_for_text_path(
    connection: sqlite3.Connection,
    path: Path,
) -> tuple[int, str]:
    resolved = path.resolve().as_posix()
    candidates = connection.execute(
        """
        SELECT surface_id,source_kind,path FROM client_surfaces
        WHERE ? LIKE '%' || replace(path, '\\', '/')
        ORDER BY length(path) DESC, surface_id LIMIT 1
        """,
        (resolved,),
    ).fetchone()
    if candidates is not None:
        return int(candidates["surface_id"]), str(candidates["source_kind"])
    stat = path.stat()
    return (
        _surface(
            connection,
            source_kind="reviewed_text",
            path=resolved,
            extension=path.suffix.lower() or "<none>",
            bytes_count=stat.st_size,
            digest=None,
            status="reviewed_extraction",
            evidence={"absolute_path": True},
        ),
        "reviewed_text",
    )


def _scan_text_references(
    connection: sqlite3.Connection,
    paths: Iterable[Path],
    item_ids: set[int],
) -> dict[str, int]:
    token_pattern = re.compile(rb"(?<!\d)(\d{1,10})(?!\d)")
    files_scanned = 0
    references = 0
    for path in sorted(set(paths), key=lambda value: value.as_posix().lower()):
        try:
            if not path.is_file() or path.stat().st_size > MAX_TEXT_FILE_BYTES:
                continue
            surface_id, source_kind = _surface_id_for_text_path(connection, path)
            seen: set[int] = set()
            payload = path.read_bytes()
            for match in token_pattern.finditer(payload):
                item_id = int(match.group(1))
                if item_id not in item_ids or item_id in seen:
                    continue
                seen.add(item_id)
                context_bytes = payload[
                    max(0, match.start() - 100):match.end() + 100
                ]
                context = context_bytes.decode("utf-8", errors="replace").strip()
                item_context = bool(
                    re.search(
                        r"(?i)(item|equip|weapon|armor|loot|reward|recipe|craft)",
                        context,
                    )
                )
                _record_reference(
                    connection,
                    surface_id=surface_id,
                    item_id=item_id,
                    token_kind=(
                        "text_item_context"
                        if item_context
                        else "text_numeric_token"
                    ),
                    locator=f"byte:{match.start()}",
                    provenance=source_kind,
                    evidence={
                        "authority": False,
                        "context": context[:240],
                        "context_mentions_item_domain": item_context,
                    },
                    state="corroborative" if item_context else "unknown",
                )
                references += 1
            files_scanned += 1
        except (OSError, UnicodeError):
            continue
    return {"files": files_scanned, "references": references}


def scan_reviewed_surfaces(
    connection: sqlite3.Connection,
    config: ForensicsConfig,
) -> dict[str, Any]:
    connection.execute("DELETE FROM surface_references")
    connection.execute("DELETE FROM client_surfaces")
    connection.execute("DELETE FROM surface_inventory")
    connection.execute("DELETE FROM review_manifests")
    manifests = _discover_manifests(config)
    documents: dict[Path, dict[str, Any]] = {}
    for path in manifests:
        document = _json_document(path)
        if document is None:
            continue
        documents[path] = document
        _record_manifest(connection, path, document)

    item_ids = {
        int(row[0])
        for row in connection.execute("SELECT item_id FROM items ORDER BY item_id")
    }
    text_paths: list[Path] = []
    registered = 0
    reviewed_roots: set[tuple[str, Path]] = set()
    for path, document in documents.items():
        name = path.name.lower()
        if name == "client-filesystem-global-v1-manifest.json":
            count, values = _scan_client_filesystem_manifest(
                connection, path, document
            )
            registered += count
            text_paths.extend(values)
        if name == "gamepak-full-lua-decompilation-v1-manifest.json":
            count, values = _scan_lua_manifest(connection, path, document)
            registered += count
            text_paths.extend(values)
        if name == "gamepak-full-xml-world-evidence-v1-manifest.json":
            for root in _xml_roots(document):
                reviewed_roots.add(("gamepak_xml_extracted", root))
        if name == "gamepak-global-content-scan-v1-manifest.json":
            scan = document.get("scan")
            if isinstance(scan, dict):
                extension_counts = scan.get("extension_counts")
                if isinstance(extension_counts, dict):
                    counts = Counter(
                        {
                            str(extension).lower(): int(count)
                            for extension, count in extension_counts.items()
                        }
                    )
                    _inventory(
                        connection,
                        "gamepak_reviewed_content_scan",
                        counts,
                        Counter(),
                        {
                            "manifest": path.resolve().as_posix(),
                            "processed_files": scan.get("processed_files"),
                            "processed_bytes": scan.get("processed_bytes"),
                            "note": "Reuses the prior 5.4 GB content sweep; raw files are not rescanned.",
                        },
                    )

    for source_kind, root in sorted(
        reviewed_roots, key=lambda value: (value[0], value[1].as_posix().lower())
    ):
        values = _add_text_tree(connection, root, source_kind)
        registered += int(
            connection.execute(
                "SELECT COUNT(*) FROM client_surfaces WHERE source_kind=?",
                (source_kind,),
            ).fetchone()[0]
        )
        text_paths.extend(values)

    index_summary = (
        _scan_gamepak_index(connection, config.gamepak_index, item_ids)
        if config.gamepak_index is not None
        else {"files": 0, "references": 0}
    )
    text_summary = _scan_text_references(connection, text_paths, item_ids)
    totals = {
        "manifests": len(documents),
        "registered_surfaces": int(
            connection.execute("SELECT COUNT(*) FROM client_surfaces").fetchone()[0]
        ),
        "inventory_files": int(
            connection.execute(
                "SELECT COALESCE(SUM(file_count),0) FROM surface_inventory"
            ).fetchone()[0]
        ),
        "gamepak_index_files": index_summary["files"],
        "gamepak_index_references": index_summary["references"],
        "text_files_scanned": text_summary["files"],
        "text_references": text_summary["references"],
        "references": int(
            connection.execute("SELECT COUNT(*) FROM surface_references").fetchone()[0]
        ),
    }
    connection.execute(
        """
        INSERT OR REPLACE INTO validation_events(
            scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES ('client','reviewed_surfaces','global_surface_inventory','ok',?)
        """,
        (canonical_json(totals),),
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO opaque_regions(
            surface,locator,blocker_code,reason,searched_evidence_json
        ) VALUES (
            'client_surfaces','binary_semantics',
            'corroborative_surface_without_native_consumer',
            'DLL/script/XML/asset hits remain corroborative until tied to a native loader or consumer.',
            ?
        )
        """,
        (canonical_json(totals),),
    )
    return totals
