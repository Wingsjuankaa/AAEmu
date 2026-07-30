from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .quests import (
    TASK_PATTERN,
    _parse_loader_layouts,
    _structural_headers,
)
from .util import canonical_json, sha256_file
from .world_actors import CachedResultReader


STAGE50_CALL_RANGES = (
    range(6, 7),
    range(18, 30),
    range(37, 43),
    range(48, 124),
    range(275, 290),
    range(296, 297),
    range(476, 477),
    range(612, 619),
    range(806, 807),
    range(874, 876),
    range(886, 905),
)
STAGE50_CALLS = frozenset(
    call for selected_range in STAGE50_CALL_RANGES for call in selected_range
)
EFFECT_ABSENT_CALLS = frozenset({67, 95, 96, 97})
FX_ABSENT_CALLS = frozenset({287})
SKILLS_NATIVE_ROWS = 33_466
SKILLS_REFERENCED_TOMBSTONES = 1_603
SKILLS_ID_DIGEST = (
    "EB39099026DF6E54980171675609F007901B9E489A1C670931223FDC80C2C62F"
)
SKILLS_ROW_DIGEST = (
    "953F3C9173AA2148BDEBC82436BA0E1A5BA34378C3DF2522D0EF4ECF01F8E31D"
)
SKILLS_RANGE = {
    "raw_start": 22_360_912,
    "start": 22_361_437,
    "end": 42_803_022,
    "raw_rows": 33_467,
    "rows": SKILLS_NATIVE_ROWS,
    "discarded_leading_rows": 1,
}
BUFFS_NATIVE_ROWS = 27_303
BUFFS_REFERENCED_TOMBSTONES = 426
BUFFS_ID_DIGEST = (
    "54A3DBE2FC7DC52E3264AF37D2011A8AF55218563C37F25A26E2101659383F67"
)
BUFFS_ROW_DIGEST = (
    "0D5655FDD8952B5966EDE8140C66023AB650C02BE2F2B14AF118FA7935085914"
)
BUFFS_RANGE = {
    "header": 44_170_889,
    "start": 44_170_895,
    "end": 64_403_064,
    "rows": BUFFS_NATIVE_ROWS,
}


@dataclass(frozen=True)
class SkillQuery:
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
class SkillResult:
    spec: SkillQuery
    start: int
    end: int
    advertised_rows: int
    rows: tuple[dict[str, Any], ...]
    digest: str
    unresolved_references: dict[int, int]
    boundary_source: str


def _call_sequence(path: Path) -> dict[int, dict[str, Any]]:
    sequence = json.loads(path.read_text(encoding="utf-8"))
    return {
        int(call["mapped_call_index"]): call["tasks"][0]
        for call in sequence
        if len(call["tasks"]) == 1
    }


def _task_sqls(path: Path) -> set[str]:
    values = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        _, separator, sql = line.partition("\t")
        if separator:
            values.add(sql)
    return values


def skill_query_inventory(
    x64_dump: Path,
    x86_dump: Path,
    call_sequence: Path,
    task_registry: Path,
) -> tuple[SkillQuery, ...]:
    x64 = _parse_loader_layouts(x64_dump)
    x86 = _parse_loader_layouts(x86_dump)
    selected_sql = _task_sqls(task_registry)
    calls = _call_sequence(call_sequence)
    inventory: list[SkillQuery] = []
    for call_index in sorted(STAGE50_CALLS):
        task = calls.get(call_index)
        if task is None or str(task["sql"]) not in selected_sql:
            continue
        sql = str(task["sql"])
        left = x64.get(sql)
        right = x86.get(sql)
        if left is not None and right is not None:
            if (
                left["columns"] != right["columns"]
                or left["layout"] != right["layout"]
            ):
                state = "architecture_mismatch"
                chosen = left
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
            state = "blocked"
            chosen = None
        task_name = str(task["task"])
        inventory.append(
            SkillQuery(
                call_index=call_index,
                task=task_name,
                table=task_name.split("@", 1)[0],
                sql=sql,
                columns=(
                    tuple(chosen["columns"]) if chosen is not None else ()
                ),
                layout=tuple(chosen["layout"]) if chosen is not None else (),
                loader=(
                    str(chosen["loader"]) if chosen is not None else None
                ),
                loader_address=(
                    str(chosen["address"]) if chosen is not None else None
                ),
                architecture_state=state,
            )
        )
    if len(inventory) != 141:
        raise RuntimeError(
            f"Expected 141 Stage 50 SQL tasks, found {len(inventory)}"
        )
    mismatches = [
        query for query in inventory
        if query.architecture_state == "architecture_mismatch"
    ]
    if mismatches:
        raise RuntimeError(
            "Stage 50 x86/x64 layout mismatch: "
            + ", ".join(query.table for query in mismatches)
        )
    return tuple(inventory)


def compare_skill_layouts(inventory: tuple[SkillQuery, ...]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for query in inventory:
        counts[query.architecture_state] = (
            counts.get(query.architecture_state, 0) + 1
        )
    return {
        "queries_compared": len(inventory),
        "states": dict(sorted(counts.items())),
        "mismatches": 0,
        "x86_x64_exact": counts.get("confirmed_x86_x64", 0),
        "x64_only": counts.get("confirmed_x64_only", 0),
        "x86_only": counts.get("confirmed_x86_only", 0),
        "blocked": counts.get("blocked", 0),
    }


def _digest_rows(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(canonical_json(row).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest().upper()


def _decode(
    data: bytes,
    spec: SkillQuery,
    *,
    start: int,
    advertised_rows: int,
    boundary_source: str,
    cached_layout: tuple[str, ...] | None = None,
) -> SkillResult:
    reader = CachedResultReader(data, None)
    cursor = start
    rows: list[dict[str, Any]] = []
    physical_layout = cached_layout or spec.layout
    while cursor < len(data) and data[cursor] == 100:
        values, cursor = reader.row(cursor, list(physical_layout))
        rows.append(dict(zip(spec.columns, values, strict=True)))
    if cursor >= len(data) or data[cursor] != 101:
        raise RuntimeError(
            f"{spec.table}: expected SQLITE_DONE at 0x{cursor:X}"
        )
    return SkillResult(
        spec=spec,
        start=start,
        end=cursor,
        advertised_rows=advertised_rows,
        rows=tuple(rows),
        digest=_digest_rows(rows),
        unresolved_references=dict(sorted(reader.unresolved.items())),
        boundary_source=boundary_source,
    )


def _from_rows(
    spec: SkillQuery,
    rows: list[dict[str, Any]],
    result_range: dict[str, Any],
    *,
    boundary_source: str,
) -> SkillResult:
    actual = [dict(row) for row in rows]
    unresolved: Counter[int] = Counter()
    for row in actual:
        for value in row.values():
            if (
                isinstance(value, str)
                and value.startswith("<ref:")
                and value.endswith(">")
            ):
                try:
                    unresolved[int(value[5:-1])] += 1
                except ValueError:
                    continue
    return SkillResult(
        spec=spec,
        start=int(result_range["start"]),
        end=int(result_range["end"]),
        advertised_rows=int(
            result_range.get("raw_rows", result_range.get("rows", len(actual)))
        ),
        rows=tuple(actual),
        digest=_digest_rows(actual),
        unresolved_references=dict(sorted(unresolved.items())),
        boundary_source=boundary_source,
    )


def _legacy_modules(config: Any) -> dict[str, Any]:
    root = config.source_skills_tool_root
    swiftblade = root / "swiftblade"
    passives = root / "battlerage" / "passives"
    for path in (root, swiftblade, passives):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
    from build_phase2_compact import extract_game_stream_rows
    from extract_battlerage_manifest import extract_client_relationships
    from extract_native_skill_modifiers import extract as extract_skill_modifiers
    from extract_swiftblade_phase3 import extract_native_tables
    from native_combat.extract_native_combat_catalog import (
        native_effect_type_map,
        native_plot_type_map,
    )

    return {
        "extract_game_stream_rows": extract_game_stream_rows,
        "extract_client_relationships": extract_client_relationships,
        "extract_native_tables": extract_native_tables,
        "extract_skill_modifiers": extract_skill_modifiers,
        "native_effect_type_map": native_effect_type_map,
        "native_plot_type_map": native_plot_type_map,
    }


def native_skill_identity_catalog(config: Any) -> tuple[frozenset[int], dict[str, Any]]:
    """Recover the complete positive skill-ID catalog and its native proof.

    The identity projection is independently confirmable even while cached
    name/description references remain unresolved: `id` is the first strict
    integer accessor in the unfiltered query and every accepted row is
    positive, unique and structurally valid through SQLITE_DONE.
    """

    inventory = skill_query_inventory(
        config.source_ghidra_sql_loaders_64,
        config.source_ghidra_skill_loaders_x86,
        config.source_ghidra_sql_call_sequence,
        config.source_skill_loader_tasks,
    )
    queries = [query for query in inventory if query.table == "skills"]
    if len(queries) != 1:
        raise RuntimeError(
            f"Expected one native skills query, found {len(queries)}"
        )
    query = queries[0]
    normalized_sql = " ".join(query.sql.split())
    if (
        query.call_index != 113
        or not normalized_sql.endswith(" FROM skills")
        or " where " in normalized_sql.lower()
        or not query.columns
        or query.columns[0] != "id"
        or not query.layout
        or query.layout[0] != "68"
        or query.loader is None
    ):
        raise RuntimeError("The native skills identity query is not authoritative")

    modules = _legacy_modules(config)
    rows, _, _, ranges = modules["extract_game_stream_rows"](
        config.source_game11
    )
    result_range = ranges["skills"]
    observed_range = {
        key: int(result_range[key]) for key in SKILLS_RANGE
    }
    if observed_range != SKILLS_RANGE:
        raise RuntimeError(
            f"The native skills result range changed: {observed_range}"
        )
    ids = [int(row["id"]) for row in rows]
    active_ids = frozenset(ids)
    if (
        len(ids) != SKILLS_NATIVE_ROWS
        or len(active_ids) != SKILLS_NATIVE_ROWS
        or any(value <= 0 for value in ids)
    ):
        raise RuntimeError("The positive native skill catalog changed")
    identity_digest = hashlib.sha256(
        b"".join(struct.pack("<I", value) for value in sorted(active_ids))
    ).hexdigest().upper()
    row_digest = _digest_rows(rows)
    if identity_digest != SKILLS_ID_DIGEST or row_digest != SKILLS_ROW_DIGEST:
        raise RuntimeError("The native skills catalog digest changed")

    data = config.source_game11.read_bytes()
    raw_reader = CachedResultReader(data, None)
    leading_values, leading_end = raw_reader.row(
        SKILLS_RANGE["raw_start"], list(query.layout)
    )
    leading_row = dict(zip(query.columns, leading_values, strict=True))
    boolean_columns = [
        name
        for name, primitive in zip(query.columns, query.layout, strict=True)
        if primitive == "38"
    ]
    invalid_booleans = {
        name: int(leading_row[name])
        for name in boolean_columns
        if leading_row[name] not in (0, 1)
    }
    if (
        leading_end != SKILLS_RANGE["start"]
        or int(leading_row["id"]) != 1_734_438_241
        or int(leading_row["ability_id"]) != 168_656_229
        or len(invalid_booleans) != 16
    ):
        raise RuntimeError("The false structural row before skills changed")

    x86_text = config.source_ghidra_skill_loaders_x86.read_text(
        encoding="utf-8", errors="replace"
    )
    task_marker = "TASK\tskills@df7920"
    task_start = x86_text.find(task_marker)
    task_end = x86_text.find("TASK_END", task_start)
    if task_start < 0 or task_end < 0:
        raise RuntimeError("The x86 skills task surface is absent")
    x86_block = x86_text[task_start:task_end]
    if query.sql not in x86_block or "STRING_MATCHES\t0" not in x86_block:
        raise RuntimeError("The x86 skills task evidence changed")

    evidence = {
        "architecture": {
            "x64": {
                "loader": query.loader,
                "loader_address": query.loader_address,
                "layout_columns": len(query.layout),
                "state": query.architecture_state,
            },
            "x86": {
                "sql_task_present": True,
                "string_matches": 0,
                "loader_layout": "not_recovered_from_current_xref_dump",
            },
        },
        "call_index": query.call_index,
        "columns": len(query.columns),
        "false_leading_structural_row": {
            "ability_id": int(leading_row["ability_id"]),
            "id": int(leading_row["id"]),
            "invalid_boolean_columns": invalid_booleans,
            "reason": (
                "pre-result bytes parse mechanically as one row but violate "
                "the native boolean ABI; the valid result begins at the next "
                "row and remains valid through SQLITE_DONE"
            ),
        },
        "game11_sha256": sha256_file(config.source_game11),
        "identity_digest": identity_digest,
        "positive_ids": len(active_ids),
        "range": observed_range,
        "row_digest": row_digest,
        "sql": query.sql,
        "unfiltered_positive_scope": True,
        "unresolved_text_does_not_block_identity": True,
    }
    return active_ids, evidence


def native_buff_identity_catalog(config: Any) -> tuple[frozenset[int], dict[str, Any]]:
    """Recover the complete positive buff-ID catalog and its native proof."""

    inventory = skill_query_inventory(
        config.source_ghidra_sql_loaders_64,
        config.source_ghidra_skill_loaders_x86,
        config.source_ghidra_sql_call_sequence,
        config.source_skill_loader_tasks,
    )
    queries = [query for query in inventory if query.table == "buffs"]
    if len(queries) != 1:
        raise RuntimeError(
            f"Expected one native buffs query, found {len(queries)}"
        )
    query = queries[0]
    normalized_sql = " ".join(query.sql.split())
    if (
        query.call_index != 119
        or not normalized_sql.endswith(" FROM buffs")
        or " where " in normalized_sql.lower()
        or not query.columns
        or query.columns[0] != "id"
        or not query.layout
        or query.layout[0] != "68"
        or query.loader is None
    ):
        raise RuntimeError("The native buffs identity query is not authoritative")

    modules = _legacy_modules(config)
    relationships = modules["extract_client_relationships"](
        config.source_game11
    )
    rows = relationships["buffs"]
    result_range = relationships["result_ranges"]["buffs"]
    observed_range = {
        "header": BUFFS_RANGE["header"],
        "start": int(result_range["start"]),
        "end": int(result_range["end"]),
        "rows": int(result_range["rows"]),
    }
    if observed_range != BUFFS_RANGE:
        raise RuntimeError(
            f"The native buffs result range changed: {observed_range}"
        )

    ids = [int(row["id"]) for row in rows]
    active_ids = frozenset(ids)
    if (
        len(ids) != BUFFS_NATIVE_ROWS
        or len(active_ids) != BUFFS_NATIVE_ROWS
        or any(value <= 0 for value in ids)
        or min(active_ids) != 1
        or max(active_ids) != 31_308
    ):
        raise RuntimeError("The positive native buff catalog changed")
    identity_digest = hashlib.sha256(
        b"".join(struct.pack("<I", value) for value in sorted(active_ids))
    ).hexdigest().upper()
    row_digest = _digest_rows(rows)
    if identity_digest != BUFFS_ID_DIGEST or row_digest != BUFFS_ROW_DIGEST:
        raise RuntimeError("The native buffs catalog digest changed")

    data = config.source_game11.read_bytes()
    matching_headers = [
        (header, start, advertised)
        for header, start, advertised in _structural_headers(data)
        if start == BUFFS_RANGE["start"]
    ]
    if matching_headers != [
        (
            BUFFS_RANGE["header"],
            BUFFS_RANGE["start"],
            BUFFS_NATIVE_ROWS,
        )
    ]:
        raise RuntimeError(
            f"The buffs structural header changed: {matching_headers}"
        )
    if (
        data[BUFFS_RANGE["header"]] != 101
        or data[BUFFS_RANGE["header"] + 1] != 100
        or data[BUFFS_RANGE["start"]] != 100
        or data[BUFFS_RANGE["end"]] != 101
    ):
        raise RuntimeError("The buffs cached-result boundary markers changed")

    x86_text = config.source_ghidra_skill_loaders_x86.read_text(
        encoding="utf-8", errors="replace"
    )
    task_marker = "TASK\tbuffs@df84f0"
    task_start = x86_text.find(task_marker)
    task_end = x86_text.find("TASK_END", task_start)
    if task_start < 0 or task_end < 0:
        raise RuntimeError("The x86 buffs task surface is absent")
    x86_block = x86_text[task_start:task_end]
    if query.sql not in x86_block or "STRING_MATCHES\t0" not in x86_block:
        raise RuntimeError("The x86 buffs task evidence changed")

    unresolved = Counter()
    for row in rows:
        for value in row.values():
            if (
                isinstance(value, str)
                and value.startswith("<ref:")
                and value.endswith(">")
            ):
                try:
                    unresolved[int(value[5:-1])] += 1
                except ValueError:
                    continue
    evidence = {
        "architecture": {
            "x64": {
                "loader": query.loader,
                "loader_address": query.loader_address,
                "layout_columns": len(query.layout),
                "state": query.architecture_state,
            },
            "x86": {
                "sql_task_present": True,
                "string_matches": 0,
                "loader_layout": "not_recovered_from_current_xref_dump",
            },
        },
        "boundary": {
            "advertised_rows": BUFFS_NATIVE_ROWS,
            "header": BUFFS_RANGE["header"],
            "previous_result_done": BUFFS_RANGE["header"],
            "sqlite_done": BUFFS_RANGE["end"],
            "structural_header_exact": True,
        },
        "call_index": query.call_index,
        "columns": len(query.columns),
        "game11_sha256": sha256_file(config.source_game11),
        "identity_digest": identity_digest,
        "positive_ids": len(active_ids),
        "range": observed_range,
        "row_digest": row_digest,
        "sql": query.sql,
        "unfiltered_positive_scope": True,
        "unresolved_string_references": {
            "occurrences": sum(unresolved.values()),
            "unique_indices": len(unresolved),
        },
        "unresolved_text_does_not_block_identity": True,
    }
    return active_ids, evidence


def load_stage50_results(
    config: Any,
    inventory: tuple[SkillQuery, ...],
) -> tuple[dict[str, SkillResult], dict[str, Any]]:
    modules = _legacy_modules(config)
    by_call = {query.call_index: query for query in inventory}
    by_table = {
        query.table: query
        for query in inventory
        if query.table != "tagged_buffs" or query.call_index == 114
    }
    data = config.source_game11.read_bytes()
    headers = _structural_headers(data)
    results: dict[str, SkillResult] = {}

    def add(result: SkillResult, *, replace: bool = False) -> None:
        current = results.get(result.spec.table)
        if current is not None and not replace:
            if current.rows != result.rows:
                raise RuntimeError(
                    f"Conflicting Stage 50 rows for {result.spec.table}"
                )
            return
        results[result.spec.table] = result

    skills, levels, passives, core_ranges = modules[
        "extract_game_stream_rows"
    ](config.source_game11)
    for table, rows in (
        ("skills", skills),
        ("levels", levels),
        ("passive_buffs", passives),
    ):
        add(
            _from_rows(
                by_table[table],
                rows,
                core_ranges[table],
                boundary_source="confirmed_legacy_native_extractor",
            )
        )

    relationships = modules["extract_client_relationships"](
        config.source_game11
    )
    relationship_rows = {
        "skill_effects": relationships["skill_effects"],
        "buffs": relationships["buffs"],
        **relationships["buff_relations"],
    }
    for table, rows in relationship_rows.items():
        add(
            _from_rows(
                by_table[table],
                rows,
                relationships["result_ranges"][table],
                boundary_source="confirmed_legacy_native_extractor",
            ),
            replace=True,
        )

    native, native_ranges = modules["extract_native_tables"](
        config.source_game11
    )
    plot_type_map, plot_type_evidence = modules["native_plot_type_map"](native)
    preferred_native = {
        "aoe_shapes",
        "anims",
        "skill_controllers",
        "projectiles",
        "plot_conditions",
        "plot_aoe_conditions",
        "plot_event_conditions",
        "plot_effects",
        "plot_next_events",
        "plot_events",
        "plots",
    }
    for table in sorted(preferred_native):
        rows = [dict(row) for row in native[table]]
        if table == "plot_effects":
            for row in rows:
                actual_type = str(row["actual_type"])
                row["actual_type"] = plot_type_map.get(
                    actual_type, actual_type
                )
        add(
            _from_rows(
                by_table[table],
                rows,
                native_ranges[table],
                boundary_source="confirmed_legacy_native_extractor",
            ),
            replace=True,
        )

    for call_index in range(18, 30):
        spec = by_call[call_index]
        if spec.table in results:
            continue
        header, start, advertised = headers[call_index - 3]
        add(
            _decode(
                data,
                spec,
                start=start,
                advertised_rows=advertised,
                boundary_source=f"structural_header:0x{header:X}",
            )
        )

    header_index = 39
    for call_index in range(51, 103):
        spec = by_call[call_index]
        if call_index in EFFECT_ABSENT_CALLS:
            continue
        header, start, advertised = headers[header_index]
        header_index += 1
        add(
            _decode(
                data,
                spec,
                start=start,
                advertised_rows=advertised,
                boundary_source=(
                    f"structural_header:0x{header:X}"
                    + (
                        ";cached_physical_layout=68,38"
                        if spec.table == "npc_spawner_despawn_effects"
                        else ""
                    )
                ),
                # Both clients request column 1 with the integer accessor, but
                # game11 serializes this table's three 0/1 spawner values as
                # one-byte cells. Keep the loader ABI in query_specs and record
                # the physical cache representation separately.
                cached_layout=(
                    ("68", "38")
                    if spec.table == "npc_spawner_despawn_effects"
                    else None
                ),
            ),
            replace=True,
        )
    if header_index != 87:
        raise RuntimeError(f"Effect block ended at header {header_index}")

    for call_index, header_index in zip(
        range(105, 110), range(89, 94), strict=True
    ):
        header, start, advertised = headers[header_index]
        add(
            _decode(
                data,
                by_call[call_index],
                start=start,
                advertised_rows=advertised,
                boundary_source=f"structural_header:0x{header:X}",
            )
        )

    for call_index in (117, 118):
        header_index = 99 if call_index == 117 else 100
        header, start, advertised = headers[header_index]
        add(
            _decode(
                data,
                by_call[call_index],
                start=start,
                advertised_rows=advertised,
                boundary_source=f"structural_header:0x{header:X}",
            )
        )

    for call_index in range(275, 290):
        spec = by_call[call_index]
        if call_index in FX_ABSENT_CALLS:
            continue
        # skin_colors (call 274) owns header 226. projectile_params (287)
        # has no native cached result, so calls 288+ resume at header 239.
        header_index = call_index - 48
        if call_index > 287:
            header_index -= 1
        header, start, advertised = headers[header_index]
        add(
            _decode(
                data,
                spec,
                start=start,
                advertised_rows=advertised,
                boundary_source=f"structural_header:0x{header:X}",
            ),
            replace=True,
        )

    compact = sqlite3.connect(
        f"file:{config.source_client_compact.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    compact.row_factory = sqlite3.Row
    try:
        effect_map, effect_evidence = modules["native_effect_type_map"](
            compact, data
        )
        effect_rows = []
        for row in compact.execute(
            "SELECT id,actual_type,actual_id FROM effects ORDER BY id"
        ):
            value = dict(row)
            value["actual_type"] = effect_map.get(
                str(value["actual_type"]), value["actual_type"]
            )
            effect_rows.append(value)
    finally:
        compact.close()
    plot_result = results["plot_effects"]
    resolved_plot_rows = []
    for source_row in plot_result.rows:
        row = dict(source_row)
        actual_type = str(row["actual_type"])
        row["actual_type"] = effect_map.get(actual_type, actual_type)
        resolved_plot_rows.append(row)
    results["plot_effects"] = SkillResult(
        spec=plot_result.spec,
        start=plot_result.start,
        end=plot_result.end,
        advertised_rows=plot_result.advertised_rows,
        rows=tuple(resolved_plot_rows),
        digest=_digest_rows(resolved_plot_rows),
        unresolved_references={},
        boundary_source=(
            plot_result.boundary_source
            + ";effect_and_plot_string_cache_resolved"
        ),
    )
    effect_header, effect_start, effect_advertised = headers[87]
    if effect_advertised != len(effect_rows):
        raise RuntimeError(
            f"Effects compact/cache mismatch: {len(effect_rows)} "
            f"vs {effect_advertised}"
        )
    results["effects"] = SkillResult(
        spec=by_call[103],
        start=effect_start,
        end=effect_start,
        advertised_rows=effect_advertised,
        rows=tuple(effect_rows),
        digest=_digest_rows(effect_rows),
        unresolved_references={},
        boundary_source=(
            f"compact_rows_plus_string_cache:0x{effect_header:X}"
        ),
    )

    modifier_rows, modifier_start, modifier_end = modules[
        "extract_skill_modifiers"
    ](config.source_game11)
    results["skill_modifiers"] = _from_rows(
        by_call[41],
        modifier_rows,
        {
            "start": modifier_start,
            "end": modifier_end,
            "rows": len(modifier_rows),
        },
        boundary_source="confirmed_native_modifier_extractor",
    )

    diagnostics = {
        "effect_string_map": effect_evidence,
        "plot_string_map": plot_type_evidence,
        "skills_cache_prefix": {
            key: core_ranges["skills"].get(key)
            for key in (
                "raw_start",
                "start",
                "raw_rows",
                "rows",
                "discarded_leading_rows",
            )
        },
        "native_result_absent_calls": sorted(
            EFFECT_ABSENT_CALLS | FX_ABSENT_CALLS
        ),
        "decoded_tables": len(results),
        "decoded_rows": sum(len(result.rows) for result in results.values()),
        "structural_headers": len(headers),
    }
    return dict(sorted(results.items())), diagnostics
