from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import TOOL_NAME, TOOL_VERSION
from .quests import _parse_loader_layouts, _structural_headers
from .schema import open_read_only
from .util import canonical_json, entity_key, sha256_file, stable_key, typed_value
from .world_actors import CachedResultReader


STAGE = 60
STREAM_ARTIFACT = "stage60:stream-game11"
COMPACT_ARTIFACT = "stage60:client-compact"
GAMEPAK_ARTIFACT = "stage60:gamepak-index"
X64_ARTIFACT = "stage60:ghidra-asset-loaders-x64"
X86_ARTIFACT = "stage60:ghidra-asset-loaders-x86"
CALL_SEQUENCE_ARTIFACT = "stage60:sql-call-sequence"
TASK_ARTIFACT = "stage60:asset-loader-tasks"

PHYSICAL_EXTENSIONS = frozenset(
    {
        ".alb",
        ".anm",
        ".animevents",
        ".avi",
        ".bai",
        ".bmp",
        ".caf",
        ".cal",
        ".cdf",
        ".cga",
        ".cgf",
        ".cfx",
        ".cfxb",
        ".chr",
        ".dds",
        ".dls",
        ".fev",
        ".fsb",
        ".fsq",
        ".fxcb",
        ".gfx",
        ".jpg",
        ".jpeg",
        ".lmg",
        ".lut",
        ".mtl",
        ".ogg",
        ".png",
        ".swf",
        ".tga",
        ".tif",
        ".tiff",
        ".ttf",
        ".wav",
        ".xml",
    }
)
REFERENCE_PATTERN = re.compile(
    r"""(?ix)
    (?P<path>
      (?:[a-z0-9_@%.$:+-]+[\\/])*
      [a-z0-9_@%.$:+-]+
      \.(?:alb|anm|animevents|avi|bai|bmp|caf|cal|cdf|cga|cgf|cfx|cfxb|
          chr|dds|dls|fev|fsb|fsq|fxcb|gfx|jpe?g|lmg|lut|mtl|ogg|png|
          swf|tga|tiff?|ttf|wav|xml)
    )
    """
)

PREFIX_TABLE_KIND = {
    "zone_score_levels": "zone_score_level",
    "zone_score_kinds": "zone_score_kind",
    "zone_score_contents": "zone_score_content",
    "aoe_shapes": "aoe_shape",
    "climates": "climate",
    "zone_climate_elems": "zone_climate_element",
    "zone_climates": "zone_climate",
    "equip_item_attr_modifiers": "equip_item_attr_modifier",
    "ui_texts": "ui_text",
    "custom_dual_materials": "custom_dual_material",
    "gem_visual_effects": "gem_visual_effect",
    "enhanced_item_materials": "enhanced_item_material",
    "enhanced_item_material_weapon_defaults": (
        "enhanced_item_material_weapon_default"
    ),
    "enhanced_item_material_armor_defaults": (
        "enhanced_item_material_armor_default"
    ),
    "game_stances": "game_stance",
    "anims": "anim",
    "anim_rules": "anim_rule",
    "anim_actions": "anim_action",
    "mount_poses": "mount_pose",
    "blocked_texts": "blocked_text",
    "ignore_texts": "ignore_text",
    "sounds": "sound",
    "sound_pack_items": "sound_pack_item",
    "sound_packs": "sound_pack",
    "instrument_sounds": "instrument_sound",
    "tags": "tag",
    "combat_sounds": "combat_sound",
    "icons": "icon",
}

LOCALIZATION_KIND = {
    "achievements": "achievement",
    "buffs": "buff",
    "crafts": "craft",
    "doodad_almighties": "doodad",
    "housings": "housing",
    "items": "item",
    "npcs": "npc",
    "quest_contexts": "quest",
    "skills": "skill",
    "slaves": "slave",
    "tags": "tag",
    "titles": "title",
    "ui_texts": "ui_text",
}


@dataclass(frozen=True)
class AssetRecord:
    archive_path: str
    lookup_path: str
    asset_key: str
    extension: str
    asset_type: str
    size: int
    offset: int
    md5: str


@dataclass(frozen=True)
class AssetQuery:
    call_index: int
    task: str
    table: str
    sql: str
    columns: tuple[str, ...]
    layout: tuple[str, ...]
    loader: str | None
    loader_address: str | None
    architecture_state: str


@dataclass(frozen=True)
class PrefixResult:
    query: AssetQuery
    header: int
    start: int
    done: int
    advertised_rows: int
    rows: tuple[dict[str, Any], ...]
    digest: str
    token_counts: dict[str, int]


def normalize_archive_path(value: str) -> str:
    result = value.strip().strip("\"'").replace("\\", "/").lower().lstrip("/")
    while result.startswith("./"):
        result = result[2:]
    return result


def lookup_path(value: str) -> str:
    result = normalize_archive_path(value)
    return result[5:] if result.startswith("game/") else result


def asset_key_from_path(value: str) -> str:
    return stable_key("asset-path", lookup_path(value))


def classify_asset(path: str) -> str:
    normalized = normalize_archive_path(path)
    extension = Path(normalized).suffix.lower()
    if normalized.startswith("game/ui/"):
        return "ui_asset"
    if normalized.startswith("game/sounds/") or extension in {
        ".fsb",
        ".fev",
        ".dls",
        ".ogg",
        ".wav",
    }:
        return "audio_asset"
    if extension in {".chr", ".cdf", ".cgf", ".cga"}:
        return "model_asset"
    if extension in {".caf", ".anm", ".animevents", ".lmg", ".fsq", ".cal"}:
        return "animation_asset"
    if extension in {".dds", ".tga", ".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp", ".lut"}:
        return "texture_asset"
    if extension == ".mtl":
        return "material_asset"
    if extension in {".fxcb", ".cfx", ".cfxb"}:
        return "effect_asset"
    if extension in {".lua", ".luac", ".bai"}:
        return "script_asset"
    if extension == ".xml":
        return "xml_asset"
    if extension in {".ttf"}:
        return "font_asset"
    if extension in {".avi", ".swf", ".gfx"}:
        return "media_asset"
    if normalized.startswith("game/worlds/"):
        return "world_asset"
    return "client_asset"


def load_gamepak_index(path: Path) -> tuple[AssetRecord, ...]:
    records: list[AssetRecord] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter=";"):
            archive = normalize_archive_path(str(row["name"]))
            if archive in seen:
                raise RuntimeError(f"Duplicate normalized game_pak path: {archive}")
            seen.add(archive)
            lookup = lookup_path(archive)
            records.append(
                AssetRecord(
                    archive_path=archive,
                    lookup_path=lookup,
                    asset_key=stable_key("asset-path", lookup),
                    extension=Path(archive).suffix.lower() or "<none>",
                    asset_type=classify_asset(archive),
                    size=int(row["size"]),
                    offset=int(row["offset"]),
                    md5=str(row["md5"]).upper(),
                )
            )
    records.sort(key=lambda value: value.archive_path)
    return tuple(records)


def _call_sequence(path: Path) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_call: dict[int, dict[str, Any]] = {}
    by_sql: dict[str, int] = {}
    for call in raw:
        if len(call["tasks"]) != 1:
            continue
        call_index = int(call["mapped_call_index"])
        task = dict(call["tasks"][0])
        by_call[call_index] = task
        by_sql[str(task["sql"])] = call_index
    return by_call, by_sql


def _registry_sqls(path: Path) -> tuple[tuple[str, str], ...]:
    result = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        task, separator, sql = line.partition("\t")
        if not separator:
            raise RuntimeError(f"Malformed Stage 60 loader task: {line}")
        result.append((task, sql))
    return tuple(result)


def asset_query_inventory(config: Any) -> tuple[AssetQuery, ...]:
    x64 = _parse_loader_layouts(config.source_ghidra_sql_loaders_64)
    x86 = _parse_loader_layouts(config.source_ghidra_asset_loaders_x86)
    _, by_sql = _call_sequence(config.source_ghidra_sql_call_sequence)
    inventory = []
    for task, sql in _registry_sqls(config.source_asset_loader_tasks):
        call_index = by_sql.get(sql)
        if call_index is None:
            raise RuntimeError(f"Stage 60 SQL has no unique call index: {sql}")
        left = x64.get(sql)
        right = x86.get(sql)
        if left is not None and right is not None:
            if left["columns"] != right["columns"] or left["layout"] != right["layout"]:
                state = "architecture_mismatch"
            else:
                state = "confirmed_x86_x64"
            chosen = left
        elif left is not None:
            state = "confirmed_x64_only"
            chosen = left
        elif right is not None:
            state = "confirmed_x86_only"
            chosen = right
        else:
            state = "blocked_loader_absent"
            chosen = None
        inventory.append(
            AssetQuery(
                call_index=call_index,
                task=task,
                table=task.split("@", 1)[0],
                sql=sql,
                columns=tuple(chosen["columns"]) if chosen else (),
                layout=tuple(chosen["layout"]) if chosen else (),
                loader=str(chosen["loader"]) if chosen else None,
                loader_address=str(chosen["address"]) if chosen else None,
                architecture_state=state,
            )
        )
    inventory.sort(key=lambda value: (value.call_index, value.task))
    if any(value.architecture_state == "architecture_mismatch" for value in inventory):
        raise RuntimeError("Stage 60 x86/x64 loader mismatch")
    return tuple(inventory)


def decode_string_prefix(config: Any) -> tuple[dict[int, PrefixResult], dict[str, Any]]:
    inventory = {query.call_index: query for query in asset_query_inventory(config)}
    by_call, _ = _call_sequence(config.source_ghidra_sql_call_sequence)
    x64 = _parse_loader_layouts(config.source_ghidra_sql_loaders_64)
    data = config.source_game11.read_bytes()
    headers = _structural_headers(data)
    reader = CachedResultReader(data, first_string_reference=0)
    results: dict[int, PrefixResult] = {}
    for call_index in range(3, 31):
        registered = inventory.get(call_index)
        task = by_call[call_index]
        layout = x64.get(str(task["sql"]))
        if layout is None:
            raise RuntimeError(f"Missing x64 prefix loader for call {call_index}")
        query = registered or AssetQuery(
            call_index=call_index,
            task=str(task["task"]),
            table=str(task["task"]).split("@", 1)[0],
            sql=str(task["sql"]),
            columns=tuple(layout["columns"]),
            layout=tuple(layout["layout"]),
            loader=str(layout["loader"]),
            loader_address=str(layout["address"]),
            architecture_state="confirmed_x64_prefix",
        )
        header, start, advertised = headers[call_index - 3]
        before = Counter(reader.tokens)
        cursor = start
        rows = []
        digest = hashlib.sha256()
        while cursor < len(data) and data[cursor] == 100:
            values, cursor = reader.row(cursor, list(query.layout))
            row = dict(zip(query.columns, values, strict=True))
            encoded = canonical_json(row).encode("utf-8")
            digest.update(encoded)
            digest.update(b"\n")
            rows.append(row)
        if cursor >= len(data) or data[cursor] != 101:
            raise RuntimeError(
                f"{query.table}: expected SQLITE_DONE at 0x{cursor:X}"
            )
        if len(rows) != advertised:
            raise RuntimeError(
                f"{query.table}: advertised {advertised}, decoded {len(rows)}"
            )
        delta = Counter(reader.tokens)
        delta.subtract(before)
        results[call_index] = PrefixResult(
            query=query,
            header=header,
            start=start,
            done=cursor,
            advertised_rows=advertised,
            rows=tuple(rows),
            digest=digest.hexdigest().upper(),
            token_counts=dict(sorted((k, v) for k, v in delta.items() if v)),
        )
    if reader.unresolved:
        raise RuntimeError(
            f"Stage 60 prefix has unresolved strings: {dict(reader.unresolved)}"
        )
    diagnostics = {
        "calls": [3, 30],
        "results": len(results),
        "rows": sum(len(value.rows) for value in results.values()),
        "first_reference": 0,
        "next_reference": reader.next_reference,
        "cached_strings": len(reader.cache),
        "token_counts": dict(sorted(reader.tokens.items())),
        "unresolved_references": 0,
        "icon_12519": next(
            row["filename"]
            for row in results[30].rows
            if int(row["id"]) == 12519
        ),
        "structural_headers": len(headers),
    }
    return results, diagnostics


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


def _entity_tuple(
    *,
    key: str,
    kind: str,
    native_id: str,
    subtype: str | None,
    lifecycle: str,
    state: str,
    authority: str,
    provenance: str,
    evidence: dict[str, Any],
) -> tuple[Any, ...]:
    return (
        key,
        kind,
        native_id,
        subtype,
        lifecycle,
        state,
        authority,
        STAGE,
        provenance,
        canonical_json(evidence),
    )


def _insert_entities(
    connection: sqlite3.Connection, rows: Iterable[tuple[Any, ...]]
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


def _relation_tuple(
    *,
    src: str,
    relation: str,
    dst: str,
    ordinal: int,
    state: str,
    authority: str,
    artifact: str | None,
    locator: str,
    consumer: str | None,
    required: int,
    evidence: dict[str, Any],
) -> tuple[Any, ...]:
    return (
        stable_key("relation", src, relation, dst, ordinal, locator),
        src,
        relation,
        dst,
        ordinal,
        "many",
        state,
        required,
        authority,
        artifact,
        locator,
        consumer,
        TOOL_NAME,
        canonical_json(evidence),
    )


def _property_tuple(
    *,
    owner: str,
    namespace: str,
    name: str,
    value: Any,
    locator: str,
    consumer: str | None,
    state: str = "confirmed",
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
        "client_native",
        STREAM_ARTIFACT,
        locator,
        consumer,
        canonical_json({"string_cache_replayed_from_reference_zero": True}),
    )


def _prior_stage_paths(config: Any) -> tuple[Path, ...]:
    return (
        config.stage_20,
        config.stage_30,
        config.stage_40,
        config.stage_50,
    )


def _used_icon_ids(config: Any) -> set[int]:
    result: set[int] = set()
    for path in _prior_stage_paths(config):
        connection = open_read_only(path)
        try:
            for row in connection.execute(
                """
                SELECT DISTINCT dst_entity_key FROM relations
                WHERE dst_entity_key LIKE 'icon:%'
                """
            ):
                value = str(row[0]).split(":", 1)[1]
                if value.isdigit():
                    result.add(int(value))
        finally:
            connection.close()
    return result


def _copy_referenced_source(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO entities(
            entity_key,kind,native_id,subtype,lifecycle,state,authority,
            source_stage,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        (
            row["entity_key"],
            row["kind"],
            row["native_id"],
            row["subtype"],
            row["lifecycle"],
            row["entity_state"],
            row["entity_authority"],
            STAGE,
            "prior_forensic_stage",
            canonical_json(
                {
                    "copied_for_stage60_relation_endpoint": True,
                    "prior_stage": int(row["prior_stage"]),
                }
            ),
        ),
    )


def _match_physical(
    value: str, by_archive: dict[str, AssetRecord]
) -> AssetRecord | None:
    normalized = normalize_archive_path(value)
    candidates = [normalized]
    if normalized.startswith("game/"):
        candidates.append(normalized[5:])
    else:
        candidates.append("game/" + normalized)
    for candidate in candidates:
        record = by_archive.get(candidate)
        if record is not None:
            return record
    return None


def _looks_physical(value: str) -> bool:
    normalized = normalize_archive_path(value)
    return Path(normalized).suffix.lower() in PHYSICAL_EXTENSIONS


def _scan_extracted_tree(
    connection: sqlite3.Connection,
    *,
    root: Path,
    family: str,
    by_archive: dict[str, AssetRecord],
    client_build: str,
) -> dict[str, Any]:
    file_entries = []
    relation_rows: list[tuple[Any, ...]] = []
    entity_rows: list[tuple[Any, ...]] = []
    unmatched_entities: dict[str, tuple[Any, ...]] = {}
    matched = 0
    unmatched = 0
    references = 0
    unmatched_examples: list[str] = []
    total_bytes = 0
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda value: value.relative_to(root).as_posix().lower(),
    )
    for path in files:
        relative = path.relative_to(root).as_posix()
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest().upper()
        total_bytes += len(payload)
        file_entries.append(
            {"path": relative, "bytes": len(payload), "sha256": digest}
        )
        surface_key = stable_key("surface", family, relative.lower())
        connection.execute(
            """
            INSERT INTO surfaces(
                surface_key,source_stage,source_kind,locator,extension,bytes,
                sha256,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                surface_key,
                STAGE,
                family,
                path.resolve().as_posix(),
                path.suffix.lower() or "<none>",
                len(payload),
                digest,
                "confirmed",
                canonical_json({"relative_path": relative}),
            ),
        )
        source_key = entity_key("source_file", f"{family}:{relative.lower()}")
        entity_rows.append(
            _entity_tuple(
                key=source_key,
                kind="source_file",
                native_id=f"{family}:{relative.lower()}",
                subtype=path.suffix.lower() or None,
                lifecycle="present",
                state="confirmed",
                authority="client_asset" if family == "gamepak_xml" else "client_script",
                provenance="frozen_extracted_tree",
                evidence={"surface_key": surface_key},
            )
        )
        text = payload.decode("utf-8", "replace")
        seen_in_file: set[tuple[str, str]] = set()
        for match in REFERENCE_PATTERN.finditer(text):
            raw = match.group("path")
            normalized = normalize_archive_path(raw)
            record = _match_physical(normalized, by_archive)
            target_identity = record.asset_key if record else normalized
            marker = (target_identity, raw.lower())
            if marker in seen_in_file:
                continue
            seen_in_file.add(marker)
            references += 1
            if record is not None:
                dst = entity_key("asset_file", record.asset_key)
                relation_rows.append(
                    _relation_tuple(
                        src=source_key,
                        relation="references_asset",
                        dst=dst,
                        ordinal=len(relation_rows),
                        state="confirmed",
                        authority=(
                            "client_asset"
                            if family == "gamepak_xml"
                            else "client_script"
                        ),
                        artifact=GAMEPAK_ARTIFACT,
                        locator=f"{relative}@{match.start()}",
                        consumer=family,
                        required=0,
                        evidence={"raw_reference": raw},
                    )
                )
                matched += 1
            else:
                reference_id = stable_key("asset-reference", normalized)
                dst = entity_key("asset_reference", reference_id)
                unmatched_entities[dst] = _entity_tuple(
                    key=dst,
                    kind="asset_reference",
                    native_id=reference_id,
                    subtype=Path(normalized).suffix.lower() or None,
                    lifecycle="referenced",
                    state="unknown",
                    authority=(
                        "client_asset"
                        if family == "gamepak_xml"
                        else "client_script"
                    ),
                    provenance="extracted_text_reference",
                    evidence={"normalized_reference": normalized},
                )
                relation_rows.append(
                    _relation_tuple(
                        src=source_key,
                        relation="references_unresolved_asset",
                        dst=dst,
                        ordinal=len(relation_rows),
                        state="unknown",
                        authority=(
                            "client_asset"
                            if family == "gamepak_xml"
                            else "client_script"
                        ),
                        artifact=None,
                        locator=f"{relative}@{match.start()}",
                        consumer=family,
                        required=0,
                        evidence={"raw_reference": raw},
                    )
                )
                unmatched += 1
                if len(unmatched_examples) < 25:
                    unmatched_examples.append(raw)
        if len(entity_rows) >= 1000:
            _insert_entities(connection, entity_rows)
            entity_rows.clear()
        if len(relation_rows) >= 5000:
            _insert_entities(connection, entity_rows)
            entity_rows.clear()
            _insert_entities(connection, unmatched_entities.values())
            unmatched_entities.clear()
            connection.executemany(
                """
                INSERT OR IGNORE INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,ordinal,
                    cardinality,state,required,authority,source_artifact_key,
                    locator,loader_or_consumer,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                relation_rows,
            )
            relation_rows.clear()
    _insert_entities(connection, entity_rows)
    _insert_entities(connection, unmatched_entities.values())
    connection.executemany(
        """
        INSERT OR IGNORE INTO relations(
            relation_key,src_entity_key,relation,dst_entity_key,ordinal,
            cardinality,state,required,authority,source_artifact_key,
            locator,loader_or_consumer,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        relation_rows,
    )
    tree_sha = hashlib.sha256(canonical_json(file_entries).encode("utf-8")).hexdigest().upper()
    extension_counts = Counter(Path(entry["path"]).suffix.lower() or "<none>" for entry in file_entries)
    for extension, count in sorted(extension_counts.items()):
        size = sum(
            int(entry["bytes"])
            for entry in file_entries
            if (Path(entry["path"]).suffix.lower() or "<none>") == extension
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO surface_inventory(
                source_kind,extension,file_count,total_bytes,evidence_json
            ) VALUES(?,?,?,?,?)
            """,
            (
                family,
                extension,
                count,
                size,
                canonical_json({"tree_sha256": tree_sha}),
            ),
        )
    connection.execute(
        """
        INSERT INTO artifacts(
            artifact_key,source_stage,role,path,bytes,sha256,build,authority,
            state,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            f"stage60:{family}-tree",
            STAGE,
            f"{family}_extracted_tree",
            root.resolve().as_posix(),
            total_bytes,
            tree_sha,
            client_build,
            "client_asset" if family == "gamepak_xml" else "client_script",
            "confirmed",
            TOOL_NAME,
            canonical_json({"files": len(file_entries)}),
        ),
    )
    return {
        "files": len(file_entries),
        "bytes": total_bytes,
        "sha256": tree_sha,
        "references": references,
        "matched": matched,
        "unmatched": unmatched,
        "unmatched_examples": unmatched_examples,
    }


def _insert_gamepak_catalog(
    connection: sqlite3.Connection, records: tuple[AssetRecord, ...]
) -> dict[str, Any]:
    type_counts = Counter()
    extension_counts = Counter()
    extension_bytes = Counter()
    entities: list[tuple[Any, ...]] = []
    assets: list[tuple[Any, ...]] = []
    for record in records:
        type_counts[record.asset_type] += 1
        extension_counts[record.extension] += 1
        extension_bytes[record.extension] += record.size
        key = entity_key("asset_file", record.asset_key)
        entities.append(
            _entity_tuple(
                key=key,
                kind="asset_file",
                native_id=record.asset_key,
                subtype=record.asset_type,
                lifecycle="present",
                state="confirmed",
                authority="client_asset",
                provenance="gamepak_full_index",
                evidence={"indexed": True},
            )
        )
        assets.append(
            (
                record.asset_key,
                record.archive_path,
                record.asset_type,
                None,
                "confirmed",
                GAMEPAK_ARTIFACT,
                canonical_json(
                    {
                        "md5": record.md5,
                        "offset": record.offset,
                        "size": record.size,
                    }
                ),
            )
        )
        if len(entities) >= 5000:
            _insert_entities(connection, entities)
            connection.executemany(
                """
                INSERT INTO assets(
                    asset_key,path,asset_type,sha256,state,source_artifact_key,
                    evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                assets,
            )
            entities.clear()
            assets.clear()
    _insert_entities(connection, entities)
    connection.executemany(
        """
        INSERT INTO assets(
            asset_key,path,asset_type,sha256,state,source_artifact_key,
            evidence_json
        ) VALUES(?,?,?,?,?,?,?)
        """,
        assets,
    )
    for extension in sorted(extension_counts):
        connection.execute(
            """
            INSERT INTO surface_inventory(
                source_kind,extension,file_count,total_bytes,evidence_json
            ) VALUES(?,?,?,?,?)
            """,
            (
                "game_pak_index",
                extension,
                extension_counts[extension],
                extension_bytes[extension],
                canonical_json({"authority": "frozen_full_index"}),
            ),
        )
    return {
        "assets": len(records),
        "bytes": sum(value.size for value in records),
        "types": dict(sorted(type_counts.items())),
        "extensions": dict(sorted(extension_counts.items())),
    }


def _insert_query_evidence(
    connection: sqlite3.Connection,
    inventory: tuple[AssetQuery, ...],
    prefix: dict[int, PrefixResult],
) -> None:
    for query in inventory:
        result = prefix.get(query.call_index)
        query_key = f"stage60:query:{query.call_index}:{query.table}"
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
                600_000 + query.call_index,
                query.table,
                "x2game.dll",
                query.sql,
                canonical_json(query.columns),
                canonical_json(query.layout),
                "game11" if result else None,
                result.start if result else None,
                result.advertised_rows if result else None,
                canonical_json(
                    {
                        "header": result.header if result else None,
                        "done": result.done if result else None,
                    }
                ),
                query.loader,
                (
                    "confirmed"
                    if query.architecture_state.startswith("confirmed")
                    else "blocked"
                ),
                canonical_json(
                    {
                        "architecture_state": query.architecture_state,
                        "call_index": query.call_index,
                        "loader_address": query.loader_address,
                        "selected_for": "assets_ui_localization",
                    }
                ),
            ),
        )
        if result is None:
            continue
        connection.execute(
            """
            INSERT INTO cached_results(
                cached_result_key,source_cached_result_id,query_key,artifact_key,
                start_offset,end_offset,row_count,row_digest,raw_references_json,
                unresolved_references_json,resolution_evidence_json,state,error
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                f"stage60:cached:{query.call_index}:{query.table}",
                600_000 + query.call_index,
                query_key,
                STREAM_ARTIFACT,
                result.start,
                result.done,
                len(result.rows),
                result.digest,
                canonical_json(result.token_counts),
                "{}",
                canonical_json(
                    {
                        "global_execution_order_replayed": True,
                        "first_string_reference": 0,
                    }
                ),
                "confirmed",
                None,
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


def _insert_prefix_graph(
    connection: sqlite3.Connection,
    prefix: dict[int, PrefixResult],
    by_archive: dict[str, AssetRecord],
) -> dict[str, int]:
    counts = Counter()
    for result in prefix.values():
        table = result.query.table
        kind = PREFIX_TABLE_KIND[table]
        ids: list[str] = []
        entities = []
        properties = []
        native_rows = []
        pending_asset_entities: dict[str, tuple[Any, ...]] = {}
        relations = []
        for row_index, row in enumerate(result.rows):
            native_id = str(row.get("id", row_index))
            ids.append(native_id)
            owner = entity_key(kind, native_id)
            entities.append(
                _entity_tuple(
                    key=owner,
                    kind=kind,
                    native_id=native_id,
                    subtype=None,
                    lifecycle="present",
                    state="confirmed",
                    authority="client_native",
                    provenance="game11_cached_result",
                    evidence={
                        "call_index": result.query.call_index,
                        "source_table": table,
                    },
                )
            )
            if table == "icons":
                native_rows.append(
                    (
                        stable_key("native-row", table, native_id, row_index),
                        owner,
                        kind,
                        native_id,
                        table,
                        "confirmed",
                        canonical_json(row),
                        TOOL_NAME,
                        canonical_json(
                            {
                                "call_index": result.query.call_index,
                                "row_index": row_index,
                            }
                        ),
                    )
                )
            for column_index, (column, value) in enumerate(row.items()):
                if column == "id" or not isinstance(value, str) or value == "":
                    continue
                locator = f"{table}[{native_id}].{column}"
                properties.append(
                    _property_tuple(
                        owner=owner,
                        namespace=table,
                        name=column,
                        value=value,
                        locator=locator,
                        consumer=result.query.loader,
                    )
                )
                record = _match_physical(value, by_archive)
                if record is not None:
                    destination = entity_key("asset_file", record.asset_key)
                    relations.append(
                        _relation_tuple(
                            src=owner,
                            relation="uses_asset",
                            dst=destination,
                            ordinal=0,
                            state="confirmed",
                            authority="client_native",
                            artifact=GAMEPAK_ARTIFACT,
                            locator=locator,
                            consumer=result.query.loader,
                            required=0,
                            evidence={
                                "native_string": value,
                                "path_resolution": "exact",
                            },
                        )
                    )
                    counts["prefix_physical_asset_relations"] += 1
                elif _looks_physical(value):
                    reference_id = stable_key(
                        "asset-reference", normalize_archive_path(value)
                    )
                    destination = entity_key("asset_reference", reference_id)
                    pending_asset_entities[destination] = _entity_tuple(
                        key=destination,
                        kind="asset_reference",
                        native_id=reference_id,
                        subtype=Path(value).suffix.lower(),
                        lifecycle="referenced",
                        state="unknown",
                        authority="client_native",
                        provenance="native_cached_string",
                        evidence={"normalized_reference": normalize_archive_path(value)},
                    )
                    relations.append(
                        _relation_tuple(
                            src=owner,
                            relation="references_unresolved_asset",
                            dst=destination,
                            ordinal=0,
                            state="unknown",
                            authority="client_native",
                            artifact=STREAM_ARTIFACT,
                            locator=locator,
                            consumer=result.query.loader,
                            required=0,
                            evidence={"native_string": value},
                        )
                    )
                    counts["prefix_unresolved_asset_relations"] += 1
                if table == "sounds" and column == "path":
                    logical_id = stable_key("audio-event", value)
                    destination = entity_key("audio_event", logical_id)
                    pending_asset_entities[destination] = _entity_tuple(
                        key=destination,
                        kind="audio_event",
                        native_id=logical_id,
                        subtype=None,
                        lifecycle="present",
                        state="confirmed",
                        authority="client_native",
                        provenance="native_sound_descriptor",
                        evidence={"event_path": value},
                    )
                    relations.append(
                        _relation_tuple(
                            src=owner,
                            relation="uses_audio_event",
                            dst=destination,
                            ordinal=0,
                            state="confirmed",
                            authority="client_native",
                            artifact=STREAM_ARTIFACT,
                            locator=locator,
                            consumer=result.query.loader,
                            required=1,
                            evidence={"event_path": value},
                        )
                    )
                    counts["audio_events"] += 1
        _insert_entities(connection, entities)
        _insert_entities(connection, pending_asset_entities.values())
        connection.executemany(
            """
            INSERT OR REPLACE INTO entity_properties(
                property_key,entity_key,namespace,property_name,ordinal,
                value_type,value_text,value_integer,value_real,value_boolean,
                value_json,state,authority,source_artifact_key,locator,consumer,
                evidence_json
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
        connection.executemany(
            """
            INSERT INTO native_rows(
                native_row_key,entity_key,entity_kind,native_id,source_table,
                state,row_json,provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            native_rows,
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
                kind,
                "id",
                "confirmed",
                len(result.rows),
                len(set(ids)),
                "game11_cached_result",
                canonical_json(
                    {
                        "call_index": result.query.call_index,
                        "row_digest": result.digest,
                        "string_cache_resolved": True,
                    }
                ),
            ),
        )
        counts["prefix_entities"] += len(entities)
        counts["prefix_properties"] += len(properties)
    return dict(counts)


def _insert_icon_asset_graph(
    connection: sqlite3.Connection,
    *,
    icons: tuple[dict[str, Any], ...],
    records: tuple[AssetRecord, ...],
    used_icon_ids: set[int],
) -> dict[str, int]:
    by_basename: dict[str, list[AssetRecord]] = defaultdict(list)
    by_ui_relative: dict[str, AssetRecord] = {}
    for record in records:
        by_basename[record.archive_path.rsplit("/", 1)[-1]].append(record)
        prefix = "game/ui/icon/"
        if record.archive_path.startswith(prefix):
            by_ui_relative[record.archive_path[len(prefix) :]] = record
    icon_ids = {int(row["id"]) for row in icons}
    counts = Counter()
    for row in icons:
        icon_id = int(row["id"])
        owner = entity_key("icon", icon_id)
        filename = str(row["filename"])
        normalized_filename = normalize_archive_path(filename)
        ui_match = by_ui_relative.get(normalized_filename)
        basename_matches = by_basename.get(normalized_filename, [])
        if ui_match is not None:
            record = ui_match
            resolution = "game_ui_icon_relative_exact"
        elif len(basename_matches) == 1:
            record = basename_matches[0]
            resolution = "unique_archive_basename"
        else:
            record = None
            resolution = None
        if record is not None:
            connection.execute(
                """
                INSERT OR IGNORE INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,ordinal,
                    cardinality,state,required,authority,source_artifact_key,
                    locator,loader_or_consumer,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                _relation_tuple(
                    src=owner,
                    relation="resolves_to_asset",
                    dst=entity_key("asset_file", record.asset_key),
                    ordinal=0,
                    state="corroborated",
                    authority="client_asset",
                    artifact=GAMEPAK_ARTIFACT,
                    locator=f"icons[{icon_id}].filename",
                    consumer="LoadIconDescs",
                    required=0,
                    evidence={
                        "filename": filename,
                        "resolution": resolution,
                    },
                ),
            )
            state = "corroborated"
            counts[str(resolution)] += 1
        elif basename_matches:
            state = "unknown"
            counts["ambiguous_asset"] += 1
        else:
            state = "unknown"
            counts["asset_absent"] += 1
        connection.execute(
            """
            INSERT INTO coverage(
                coverage_key,scope_key,dimension,state,capability,authority,
                provenance,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("coverage", owner, "physical_asset"),
                owner,
                "physical_asset",
                state,
                "icon_filename_to_gamepak_asset",
                "client_asset",
                TOOL_NAME,
                canonical_json(
                    {
                        "filename": filename,
                        "basename_matches": len(basename_matches),
                        "ui_relative_match": ui_match is not None,
                        "referenced_by_graph": icon_id in used_icon_ids,
                    }
                ),
            ),
        )
        if icon_id in used_icon_ids and state == "unknown":
            connection.execute(
                """
                INSERT INTO gaps(
                    gap_key,entity_key,dimension,state,severity,blocker_code,
                    reason,required_evidence,provenance
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("gap", owner, "physical_asset"),
                    owner,
                    "physical_asset",
                    "unknown",
                    2,
                    (
                        "icon_asset_basename_ambiguous"
                        if basename_matches
                        else "icon_asset_not_in_gamepak_index"
                    ),
                    (
                        f"Native icon filename {filename!r} does not resolve "
                        "to one exact frozen game_pak path."
                    ),
                    "Confirm the UI icon resolver or an atlas/member mapping.",
                    TOOL_NAME,
                ),
            )
            counts["used_icon_gaps"] += 1
    for icon_id in sorted(used_icon_ids - icon_ids):
        owner = entity_key("icon", icon_id)
        _insert_entities(
            connection,
            [
                _entity_tuple(
                    key=owner,
                    kind="icon",
                    native_id=str(icon_id),
                    subtype=None,
                    lifecycle="referenced",
                    state="missing",
                    authority="client_native",
                    provenance="prior_graph_reference",
                    evidence={"icons_descriptor_absent": True},
                )
            ],
        )
        connection.execute(
            """
            INSERT INTO gaps(
                gap_key,entity_key,dimension,state,severity,blocker_code,reason,
                required_evidence,provenance
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("gap", owner, "descriptor"),
                owner,
                "descriptor",
                "missing",
                3,
                "referenced_icon_descriptor_absent",
                "A prior native row references an icon ID absent from icons.",
                "Locate another native icon table, tombstone rule or UI fallback.",
                TOOL_NAME,
            ),
        )
        counts["referenced_descriptor_absent"] += 1
    return dict(counts)


def _insert_localizations(
    connection: sqlite3.Connection, compact_path: Path
) -> dict[str, Any]:
    compact = sqlite3.connect(
        f"file:{compact_path.resolve().as_posix()}?mode=ro", uri=True
    )
    compact.row_factory = sqlite3.Row
    counts = Counter()
    generic_entities: dict[str, tuple[Any, ...]] = {}
    rows = []
    try:
        for row in compact.execute(
            """
            SELECT tbl_name,tbl_column_name,idx,text,locale
            FROM localized_texts
            ORDER BY tbl_name,tbl_column_name,idx,locale,text
            """
        ):
            table = str(row["tbl_name"])
            column = str(row["tbl_column_name"])
            native_id = int(row["idx"])
            kind = LOCALIZATION_KIND.get(table)
            if kind is None:
                kind = "localized_record"
                identity = f"{table}:{native_id}"
                owner = entity_key(kind, identity)
                generic_entities[owner] = _entity_tuple(
                    key=owner,
                    kind=kind,
                    native_id=identity,
                    subtype=table,
                    lifecycle="localization_only",
                    state="corroborated",
                    authority="client_native",
                    provenance="decrypted_client_compact",
                    evidence={"source_table": table},
                )
            else:
                owner = entity_key(kind, native_id)
            rows.append(
                (
                    stable_key(
                        "localization",
                        table,
                        column,
                        native_id,
                        str(row["locale"]),
                    ),
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
                )
            )
            counts[f"{table}.{column}"] += 1
            if len(rows) >= 5000:
                _insert_entities(connection, generic_entities.values())
                generic_entities.clear()
                connection.executemany(
                    """
                    INSERT INTO localizations(
                        localization_key,locale,text_value,entity_key,state,
                        source_artifact_key,evidence_json
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    rows,
                )
                rows.clear()
    finally:
        compact.close()
    _insert_entities(connection, generic_entities.values())
    connection.executemany(
        """
        INSERT INTO localizations(
            localization_key,locale,text_value,entity_key,state,
            source_artifact_key,evidence_json
        ) VALUES(?,?,?,?,?,?,?)
        """,
        rows,
    )
    total = sum(counts.values())
    connection.execute(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "localized_texts",
            "localized_record",
            "tbl_name,tbl_column_name,idx,locale",
            "confirmed",
            total,
            total,
            "decrypted_client_compact",
            canonical_json({"groups": len(counts), "locales": ["en_us"]}),
        ),
    )
    return {
        "rows": total,
        "groups": len(counts),
        "largest_groups": dict(counts.most_common(25)),
    }


def _insert_prior_property_links(
    connection: sqlite3.Connection,
    *,
    config: Any,
    by_archive: dict[str, AssetRecord],
) -> dict[str, int]:
    counts = Counter()
    property_filter = """
        p.value_text IS NOT NULL AND p.value_text <> '' AND (
          lower(p.property_name) LIKE '%path%'
          OR lower(p.property_name) LIKE '%file%'
          OR lower(p.property_name) LIKE '%texture%'
          OR lower(p.property_name) LIKE '%material%'
          OR lower(p.property_name) LIKE '%asset%'
          OR lower(p.property_name) LIKE '%anim%'
          OR p.namespace IN ('sounds','fx_items')
        )
    """
    for path in _prior_stage_paths(config):
        prior = open_read_only(path)
        try:
            query = f"""
                SELECT p.*,e.kind,e.native_id,e.subtype,e.lifecycle,
                       e.state AS entity_state,e.authority AS entity_authority,
                       e.source_stage AS prior_stage
                FROM entity_properties p
                JOIN entities e ON e.entity_key=p.entity_key
                WHERE {property_filter}
                ORDER BY p.property_key
            """
            for row in prior.execute(query):
                _copy_referenced_source(connection, row)
                value = str(row["value_text"])
                src = str(row["entity_key"])
                locator = str(row["locator"])
                namespace = str(row["namespace"])
                property_name = str(row["property_name"])
                if re.fullmatch(r"<ref:\d+>", value):
                    counts["prior_unresolved_strings_skipped"] += 1
                    continue
                record = _match_physical(value, by_archive)
                if record is not None:
                    relation = _relation_tuple(
                        src=src,
                        relation="uses_asset",
                        dst=entity_key("asset_file", record.asset_key),
                        ordinal=int(row["ordinal"]),
                        state="confirmed",
                        authority="client_native",
                        artifact=GAMEPAK_ARTIFACT,
                        locator=locator,
                        consumer=row["consumer"],
                        required=0,
                        evidence={
                            "native_property": f"{namespace}.{property_name}",
                            "path_resolution": "exact",
                        },
                    )
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO relations(
                            relation_key,src_entity_key,relation,dst_entity_key,
                            ordinal,cardinality,state,required,authority,
                            source_artifact_key,locator,loader_or_consumer,
                            provenance,evidence_json
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        relation,
                    )
                    counts["physical_exact"] += 1
                elif _looks_physical(value):
                    reference_id = stable_key(
                        "asset-reference", normalize_archive_path(value)
                    )
                    dst = entity_key("asset_reference", reference_id)
                    _insert_entities(
                        connection,
                        [
                            _entity_tuple(
                                key=dst,
                                kind="asset_reference",
                                native_id=reference_id,
                                subtype=Path(value).suffix.lower(),
                                lifecycle="referenced",
                                state="unknown",
                                authority="client_native",
                                provenance="native_property",
                                evidence={
                                    "normalized_reference": normalize_archive_path(
                                        value
                                    )
                                },
                            )
                        ],
                    )
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO relations(
                            relation_key,src_entity_key,relation,dst_entity_key,
                            ordinal,cardinality,state,required,authority,
                            source_artifact_key,locator,loader_or_consumer,
                            provenance,evidence_json
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        _relation_tuple(
                            src=src,
                            relation="references_unresolved_asset",
                            dst=dst,
                            ordinal=int(row["ordinal"]),
                            state="unknown",
                            authority="client_native",
                            artifact=str(row["source_artifact_key"]),
                            locator=locator,
                            consumer=row["consumer"],
                            required=0,
                            evidence={
                                "native_property": f"{namespace}.{property_name}",
                                "native_string": value,
                            },
                        ),
                    )
                    counts["physical_unresolved"] += 1
                logical_kind = None
                relation_name = None
                if namespace == "sounds" and property_name == "path":
                    logical_kind, relation_name = "audio_event", "uses_audio_event"
                elif namespace == "fx_items" and property_name == "asset_name":
                    logical_kind, relation_name = (
                        "fx_registry_entry",
                        "uses_fx_registry_entry",
                    )
                elif "anim" in property_name.lower():
                    logical_kind, relation_name = (
                        "animation_key",
                        "uses_animation_key",
                    )
                if logical_kind:
                    logical_id = stable_key(logical_kind.replace("_", "-"), value)
                    dst = entity_key(logical_kind, logical_id)
                    _insert_entities(
                        connection,
                        [
                            _entity_tuple(
                                key=dst,
                                kind=logical_kind,
                                native_id=logical_id,
                                subtype=None,
                                lifecycle="present",
                                state="confirmed",
                                authority="client_native",
                                provenance="native_property",
                                evidence={"value": value},
                            )
                        ],
                    )
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO relations(
                            relation_key,src_entity_key,relation,dst_entity_key,
                            ordinal,cardinality,state,required,authority,
                            source_artifact_key,locator,loader_or_consumer,
                            provenance,evidence_json
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        _relation_tuple(
                            src=src,
                            relation=relation_name,
                            dst=dst,
                            ordinal=int(row["ordinal"]),
                            state="confirmed",
                            authority="client_native",
                            artifact=str(row["source_artifact_key"]),
                            locator=locator,
                            consumer=row["consumer"],
                            required=0,
                            evidence={"logical_identifier": value},
                        ),
                    )
                    counts[logical_kind] += 1
        finally:
            prior.close()
    return dict(counts)


def _validation(
    connection: sqlite3.Connection,
    *,
    scope: str,
    name: str,
    status: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO validation_events(
            validation_key,scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            stable_key("validation", "stage", scope, name),
            "stage",
            scope,
            name,
            status,
            canonical_json(evidence),
        ),
    )


def populate_stage_60(
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
        GAMEPAK_ARTIFACT: _artifact(
            connection,
            key=GAMEPAK_ARTIFACT,
            role="game_pak_full_index",
            path=config.source_gamepak_index,
            build=config.client_build,
            authority="client_asset",
        ),
        X64_ARTIFACT: _artifact(
            connection,
            key=X64_ARTIFACT,
            role="asset_loader_decompilation_x64",
            path=config.source_ghidra_sql_loaders_64,
            build=config.client_build,
            authority="client_native",
        ),
        X86_ARTIFACT: _artifact(
            connection,
            key=X86_ARTIFACT,
            role="asset_loader_decompilation_x86",
            path=config.source_ghidra_asset_loaders_x86,
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
            role="asset_loader_task_registry",
            path=config.source_asset_loader_tasks,
            build=config.client_build,
            authority="derived_forensic",
        ),
    }
    inventory = asset_query_inventory(config)
    prefix, prefix_diagnostics = decode_string_prefix(config)
    architecture = Counter(value.architecture_state for value in inventory)
    connection.execute(
        """
        INSERT INTO decoders(
            decoder_key,name,version,sha256,status,inputs_json,assumptions_json,
            provenance
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "stage60:decoder:assets-ui-localization",
            "AA8 asset, UI, localization and global string-prefix decoder",
            TOOL_VERSION,
            None,
            "confirmed",
            canonical_json(input_hashes),
            canonical_json(
                {
                    "architecture": dict(sorted(architecture.items())),
                    "gamepak_rescan": False,
                    "global_string_cache": prefix_diagnostics,
                    "icon_asset_resolution": (
                        "exact paths are confirmed; unique basenames are "
                        "corroborated; absent/ambiguous names remain unknown"
                    ),
                    "logical_identifiers_are_not_physical_assets": True,
                }
            ),
            TOOL_NAME,
        ),
    )
    records = load_gamepak_index(config.source_gamepak_index)
    by_archive = {value.archive_path: value for value in records}
    gamepak = _insert_gamepak_catalog(connection, records)
    _insert_query_evidence(connection, inventory, prefix)
    prefix_graph = _insert_prefix_graph(connection, prefix, by_archive)
    used_icons = _used_icon_ids(config)
    icon_graph = _insert_icon_asset_graph(
        connection,
        icons=prefix[30].rows,
        records=records,
        used_icon_ids=used_icons,
    )
    localizations = _insert_localizations(
        connection, config.source_client_compact
    )
    prior_links = _insert_prior_property_links(
        connection, config=config, by_archive=by_archive
    )
    extracted = {
        "gamepak_xml": _scan_extracted_tree(
            connection,
            root=config.source_gamepak_xml_root,
            family="gamepak_xml",
            by_archive=by_archive,
            client_build=config.client_build,
        ),
        "lua_x64": _scan_extracted_tree(
            connection,
            root=config.source_gamepak_lua64_root,
            family="lua_x64",
            by_archive=by_archive,
            client_build=config.client_build,
        ),
        "lua_x86": _scan_extracted_tree(
            connection,
            root=config.source_gamepak_lua32_root,
            family="lua_x86",
            by_archive=by_archive,
            client_build=config.client_build,
        ),
    }
    unmatched_by_family = {
        family: values["unmatched"] for family, values in extracted.items()
    }
    blocked_queries = [
        query
        for query in inventory
        if query.architecture_state == "blocked_loader_absent"
    ]
    for query in blocked_queries:
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("stage60", "opaque-loader", query.call_index),
                "x2game.dll",
                query.task,
                "asset_sql_loader_not_recovered",
                (
                    "The selected SQL string is confirmed in the execution "
                    "sequence, but the generic decompiler task did not recover "
                    "a column-accessor layout in either architecture."
                ),
                canonical_json(
                    {
                        "call_index": query.call_index,
                        "sql": query.sql,
                        "x64_dump": X64_ARTIFACT,
                        "x86_dump": X86_ARTIFACT,
                        "prior_stage_may_have_specialized_decoder": True,
                    }
                ),
                STAGE,
                "blocked",
            ),
        )
    for family, details in extracted.items():
        if not details["unmatched"]:
            continue
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("stage60", "opaque", family, "asset-references"),
                family,
                config.source_gamepak_xml_root.resolve().as_posix()
                if family == "gamepak_xml"
                else (
                    config.source_gamepak_lua64_root.resolve().as_posix()
                    if family == "lua_x64"
                    else config.source_gamepak_lua32_root.resolve().as_posix()
                ),
                "textual_asset_reference_not_in_gamepak_index",
                (
                    "A textual reference has no exact normalized path in the "
                    "frozen full game_pak index."
                ),
                canonical_json(details),
                STAGE,
                "unknown",
            ),
        )
    if icon_graph.get("asset_absent", 0) or icon_graph.get(
        "ambiguous_asset", 0
    ):
        connection.execute(
            """
            INSERT INTO opaque_regions(
                opaque_key,surface,locator,blocker_code,reason,
                searched_evidence_json,source_stage,state
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "stage60:opaque:icon-physical-resolver",
                "x2game.dll/ui",
                "icons.filename -> game_pak",
                "icon_filename_consumer_not_fully_decoded",
                (
                    "Some native icon filenames are not direct unique archive "
                    "basenames; their UI resolver or atlas membership is opaque."
                ),
                canonical_json(icon_graph),
                STAGE,
                "blocked",
            ),
        )
    connection.executemany(
        """
        INSERT INTO coverage(
            coverage_key,scope_key,dimension,state,capability,authority,
            provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        [
            (
                stable_key("coverage", "stage:60", "asset_catalog"),
                "stage:60",
                "asset_catalog",
                "confirmed",
                "full_frozen_gamepak_index",
                "client_asset",
                TOOL_NAME,
                canonical_json(gamepak),
            ),
            (
                stable_key("coverage", "stage:60", "localization_catalog"),
                "stage:60",
                "localization_catalog",
                "confirmed",
                "all_decrypted_localized_texts",
                "client_native",
                TOOL_NAME,
                canonical_json(localizations),
            ),
            (
                stable_key("coverage", "stage:60", "icon_descriptors"),
                "stage:60",
                "icon_descriptors",
                "confirmed",
                "native_icons_cached_result",
                "client_native",
                TOOL_NAME,
                canonical_json(
                    {
                        "icons": len(prefix[30].rows),
                        "used_icon_ids": len(used_icons),
                    }
                ),
            ),
            (
                stable_key("coverage", "stage:60", "textual_asset_references"),
                "stage:60",
                "textual_asset_references",
                "unknown" if any(unmatched_by_family.values()) else "confirmed",
                "xml_and_lua_reference_graph",
                "client_asset",
                TOOL_NAME,
                canonical_json(unmatched_by_family),
            ),
            (
                stable_key("coverage", "stage:60", "asset_sql_loaders"),
                "stage:60",
                "asset_sql_loaders",
                "blocked" if blocked_queries else "confirmed",
                "x86_x64_loader_inventory",
                "client_native",
                TOOL_NAME,
                canonical_json(
                    {
                        "architecture_states": dict(sorted(architecture.items())),
                        "blocked_calls": [
                            value.call_index for value in blocked_queries
                        ],
                    }
                ),
            ),
        ],
    )
    _validation(
        connection,
        scope="60",
        name="gamepak_index_row_count",
        status="confirmed" if len(records) == 377_295 else "blocked",
        evidence={"expected": 377_295, "actual": len(records)},
    )
    _validation(
        connection,
        scope="60",
        name="localized_text_row_count",
        status=(
            "confirmed"
            if localizations["rows"] == 629_661
            else "blocked"
        ),
        evidence={"expected": 629_661, "actual": localizations["rows"]},
    )
    _validation(
        connection,
        scope="60",
        name="icon_cached_result_closure",
        status=(
            "confirmed"
            if len(prefix[30].rows) == 18_263
            and prefix_diagnostics["unresolved_references"] == 0
            else "blocked"
        ),
        evidence={
            "expected": 18_263,
            "actual": len(prefix[30].rows),
            "prefix": prefix_diagnostics,
        },
    )
    _validation(
        connection,
        scope="60",
        name="zero_x86_x64_layout_contradictions",
        status=(
            "confirmed"
            if not architecture.get("architecture_mismatch", 0)
            else "blocked"
        ),
        evidence=dict(sorted(architecture.items())),
    )
    metadata = {
        "stage60.gamepak": gamepak,
        "stage60.prefix": prefix_diagnostics,
        "stage60.prefix_graph": prefix_graph,
        "stage60.icon_graph": icon_graph,
        "stage60.localizations": localizations,
        "stage60.prior_property_links": prior_links,
        "stage60.extracted_trees": extracted,
        "stage60.input_hashes": input_hashes,
    }
    connection.executemany(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        (
            (key, canonical_json(value))
            for key, value in sorted(metadata.items())
        ),
    )
