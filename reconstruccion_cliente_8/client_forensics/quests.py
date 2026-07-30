from __future__ import annotations

import hashlib
import json
import re
import struct
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .global_strings import cached_string_signatures, string_cache_digest
from .util import canonical_json
from .world_actors import CachedResultReader


QUEST_CORE_FIRST_CALL = 480
QUEST_CORE_LAST_CALL = 604
QUEST_CORE_HEADER_DELTA = 53
QUEST_ACT_FIRST_STRING_REFERENCE = 320614
QUEST_ACT_NEXT_STRING_REFERENCE = 320699
QUEST_CORE_FIRST_STRING_REFERENCE = 315732
QUEST_COMPONENT_TEXT_FIRST_STRING_REFERENCE = 320790
QUEST_COMPONENT_TEXT_NEXT_STRING_REFERENCE = 329884
ATTACH_ANIMS_FIRST_STRING_REFERENCE = 150126
SKILLS_FIRST_STRING_REFERENCE = 75557
ITEM_GUIDE_FIRST_STRING_REFERENCE = 193700
ITEM_GUIDE_NEXT_STRING_REFERENCE = 194050
RAW_STRING_BLOCK_NEXT_REFERENCE = 216863
ITEMS_NEXT_STRING_REFERENCE = 245499
PRE_QUEST_STRING_REFERENCE_COUNT = QUEST_CORE_FIRST_STRING_REFERENCE

RAW_STRING_BLOCK_START = 75_937_333
ITEMS_RESULT_START = 80_917_979
ITEMS_RESULT_DONE = 89_076_696
ITEMS_RESULT_ROWS = 21_420
NEGATIVE_ITEM_STRING_ANOMALY = 10_849_003

EARLY_SIGNATURE_DELTA = 395
LATE_SIGNATURE_DELTA = 1099

ACCESSOR_PATTERN = re.compile(
    r"\+\s*0x(?P<offset>1c|20|30|34|38|3c|40|60|68|70|78)\)\)"
    r"\s*\(\s*[^,;]+,\s*(?:[^,;]+,\s*)?"
    r"(?P<index>0x[0-9a-fA-F]+|\d+)\s*\)",
    re.MULTILINE,
)
LOOP_ACCESSOR_PATTERN = re.compile(
    r"(?P<variable>\w+)\s*=\s*0\s*;\s*"
    r"do\s*\{(?P<body>.*?)"
    r"(?P=variable)\s*=\s*(?P=variable)\s*\+\s*1\s*;"
    r"(?P<after>.*?)"
    r"\+\s*0x(?P<offset>1c|20|30|34|38|3c|40|60|68|70|78)\)\)"
    r"\s*\(\s*[^,;]+,\s*(?:[^,;]+,\s*)?(?P=variable)\s*\)"
    r"(?P<tail>.*?)"
    r"\}\s*while\s*\(\s*(?P=variable)\s*<\s*(?P<limit>\d+)\s*\)",
    re.MULTILINE | re.DOTALL,
)
TASK_PATTERN = re.compile(
    r"^TASK\t(?P<task>[^\r\n]+)\r?\n"
    r"SQL\t(?P<sql>[^\r\n]+)\r?\n"
    r"(?P<body>.*?)^TASK_END$",
    re.MULTILINE | re.DOTALL,
)
FUNCTION_PATTERN = re.compile(
    r"^FUNCTION_BEGIN\t(?P<name>[^\t\r\n]+)\t(?P<address>[^\r\n]+)\r?\n"
    r"(?P<body>.*?)^FUNCTION_END$",
    re.MULTILINE | re.DOTALL,
)
CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


@dataclass(frozen=True)
class QuestQueryLayout:
    call_index: int
    task: str
    table: str
    sql: str
    columns: tuple[str, ...]
    layout: tuple[str, ...]
    loader: str
    loader_address: str


@dataclass(frozen=True)
class QuestResult:
    spec: QuestQueryLayout
    header: int
    start: int
    done: int
    advertised_rows: int
    rows: tuple[dict[str, Any], ...]
    digest: str
    token_counts: dict[str, int]
    unresolved_references: dict[int, int]
    resolution_evidence: dict[str, Any]


def _sql_columns(sql: str) -> tuple[str, ...]:
    match = re.search(r"^\s*SELECT\s+(.*?)\s+FROM\s", sql, re.I | re.S)
    if match is None:
        return ()
    return tuple(part.strip() for part in match.group(1).split(","))


def _parse_loader_layouts(path: Path) -> dict[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    language = re.search(r"^LANGUAGE\t([^\r\n]+)$", text, re.MULTILINE)
    pointer_bits = (
        32
        if language is not None and ":32:" in language.group(1)
        else 64
    )
    accessor_offsets = {
        64: {
            "38": "38",
            "40": "40",
            "60": "60",
            "68": "68",
            "70": "70",
            "78": "78",
        },
        32: {
            "1c": "38",
            "20": "40",
            "30": "60",
            "34": "68",
            "38": "70",
            "3c": "78",
        },
    }[pointer_bits]
    layouts: dict[str, dict[str, Any]] = {}
    for task_match in TASK_PATTERN.finditer(text):
        sql = task_match.group("sql")
        columns = _sql_columns(sql)
        candidates: list[dict[str, Any]] = []
        for function in FUNCTION_PATTERN.finditer(task_match.group("body")):
            found: dict[int, set[str]] = {}
            body = function.group("body")
            for accessor in ACCESSOR_PATTERN.finditer(body):
                kind = accessor_offsets.get(accessor.group("offset"))
                if kind is not None:
                    found.setdefault(int(accessor.group("index"), 0), set()).add(
                        kind
                    )
            for accessor in LOOP_ACCESSOR_PATTERN.finditer(body):
                kind = accessor_offsets.get(accessor.group("offset"))
                if kind is None:
                    continue
                for index in range(1, int(accessor.group("limit")) + 1):
                    found.setdefault(index, set()).add(kind)
            layout: list[str] = []
            blocked = False
            for index in range(len(columns)):
                kinds = found.get(index, set())
                if len(kinds) != 1:
                    blocked = True
                    break
                layout.append(next(iter(kinds)))
            if not blocked and not any(index >= len(columns) for index in found):
                candidates.append(
                    {
                        "layout": tuple(layout),
                        "loader": function.group("name"),
                        "address": function.group("address"),
                    }
                )
        unique = {candidate["layout"] for candidate in candidates}
        if len(unique) != 1:
            continue
        chosen = next(
            candidate for candidate in candidates
            if candidate["layout"] == next(iter(unique))
        )
        layouts[sql] = {
            "task": task_match.group("task"),
            "columns": columns,
            **chosen,
        }
    return layouts


def quest_loader_inventory(path: Path) -> tuple[dict[str, Any], ...]:
    text = path.read_text(encoding="utf-8", errors="replace")
    confirmed = _parse_loader_layouts(path)
    rows: list[dict[str, Any]] = []
    for task in TASK_PATTERN.finditer(text):
        task_name = task.group("task")
        sql = task.group("sql")
        if "quest" not in f"{task_name} {sql}".lower():
            continue
        parsed = confirmed.get(sql)
        rows.append(
            {
                "task": task_name,
                "table": task_name.split("@", 1)[0],
                "sql": sql,
                "columns": (
                    list(parsed["columns"])
                    if parsed is not None
                    else list(_sql_columns(sql))
                ),
                "layout": (
                    list(parsed["layout"]) if parsed is not None else []
                ),
                "loader": (
                    str(parsed["loader"]) if parsed is not None else None
                ),
                "loader_address": (
                    str(parsed["address"]) if parsed is not None else None
                ),
                "state": (
                    "confirmed_static" if parsed is not None else "blocked"
                ),
            }
        )
    return tuple(sorted(rows, key=lambda value: (value["table"], value["sql"])))


def load_quest_core_layouts(
    loader_dump: Path,
    call_sequence: Path,
) -> tuple[QuestQueryLayout, ...]:
    layouts = _parse_loader_layouts(loader_dump)
    sequence = json.loads(call_sequence.read_text(encoding="utf-8"))
    if not isinstance(sequence, list):
        raise ValueError("The SQL call sequence must be a JSON array")
    selected: list[QuestQueryLayout] = []
    for call in sequence:
        call_index = int(call["mapped_call_index"])
        if not QUEST_CORE_FIRST_CALL <= call_index <= QUEST_CORE_LAST_CALL:
            continue
        tasks = call["tasks"]
        if len(tasks) != 1:
            raise ValueError(f"SQL call {call_index} does not have one task")
        task = tasks[0]
        sql = str(task["sql"])
        if sql not in layouts:
            raise ValueError(f"Quest SQL layout is blocked at call {call_index}")
        layout = layouts[sql]
        selected.append(
            QuestQueryLayout(
                call_index=call_index,
                task=str(task["task"]),
                table=str(task["task"]).split("@", 1)[0],
                sql=sql,
                columns=tuple(layout["columns"]),
                layout=tuple(layout["layout"]),
                loader=str(layout["loader"]),
                loader_address=str(layout["address"]),
            )
        )
    if len(selected) != 125:
        raise ValueError(f"Expected 125 quest-core calls, found {len(selected)}")
    if [value.call_index for value in selected] != list(
        range(QUEST_CORE_FIRST_CALL, QUEST_CORE_LAST_CALL + 1)
    ):
        raise ValueError("The quest-core SQL call sequence is not contiguous")
    return tuple(selected)


def compare_quest_layouts(
    x64_loader_dump: Path,
    x86_loader_dump: Path,
    call_sequence: Path,
) -> dict[str, Any]:
    x64 = load_quest_core_layouts(x64_loader_dump, call_sequence)
    x86 = load_quest_core_layouts(x86_loader_dump, call_sequence)
    mismatches = []
    for left, right in zip(x64, x86, strict=True):
        if (
            left.sql != right.sql
            or left.columns != right.columns
            or left.layout != right.layout
        ):
            mismatches.append(
                {
                    "call_index": left.call_index,
                    "table": left.table,
                    "x64_columns": left.columns,
                    "x64_layout": left.layout,
                    "x86_columns": right.columns,
                    "x86_layout": right.layout,
                }
            )
    if mismatches:
        raise ValueError(f"Quest x86/x64 layout mismatches: {mismatches}")
    effect_sql = (
        "SELECT id, count, effect_id, quest_act_obj_alias_id, team_share, "
        "use_alias FROM quest_act_obj_effect_fires"
    )
    x64_effect = _parse_loader_layouts(x64_loader_dump).get(effect_sql)
    x86_effect = _parse_loader_layouts(x86_loader_dump).get(effect_sql)
    if x64_effect is None or x86_effect is None:
        raise ValueError("QuestActObjEffectFire is missing from one architecture")
    if (
        x64_effect["columns"] != x86_effect["columns"]
        or x64_effect["layout"] != x86_effect["layout"]
    ):
        raise ValueError("QuestActObjEffectFire differs between x86 and x64")
    return {
        "queries_compared": len(x64) + 1,
        "core_queries_compared": len(x64),
        "effect_fire_compared": True,
        "mismatches": mismatches,
        "x64_loader_functions": len({value.loader for value in x64}),
        "x86_loader_functions": len({value.loader for value in x86}),
    }


def _structural_headers(data: bytes) -> tuple[tuple[int, int, int], ...]:
    headers: list[tuple[int, int, int]] = []
    cursor = 0
    while True:
        header = data.find(b"\x65\x64", cursor)
        if header < 0:
            break
        cursor = header + 1
        if header + 7 > len(data):
            continue
        advertised_rows = struct.unpack_from("<I", data, header + 2)[0]
        start = header + 6
        if advertised_rows > 500_000:
            continue
        if advertised_rows > 0 and data[start] != 100:
            continue
        if advertised_rows == 0 and data[start] != 101:
            continue
        headers.append((header, start, advertised_rows))
    return tuple(headers)


def _decode_result(
    data: bytes,
    spec: QuestQueryLayout,
    header: int,
    start: int,
    advertised_rows: int,
    *,
    first_string_reference: int | None = None,
    reader: CachedResultReader | None = None,
) -> QuestResult:
    if reader is not None and first_string_reference is not None:
        raise ValueError("Cannot combine a shared reader and a local string seed")
    active_reader = reader or CachedResultReader(data, first_string_reference)
    tokens_before = Counter(active_reader.tokens)
    unresolved_before = Counter(active_reader.unresolved)
    first_reference = active_reader.next_reference
    cursor = start
    rows: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    while cursor < len(data) and data[cursor] == 100:
        values, cursor = active_reader.row(cursor, list(spec.layout))
        row = dict(zip(spec.columns, values, strict=True))
        encoded = canonical_json(row).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
        rows.append(row)
    if cursor >= len(data) or data[cursor] != 101:
        raise ValueError(
            f"{spec.table}: expected SQLITE_DONE at 0x{cursor:X}"
        )
    if first_string_reference is not None:
        if active_reader.next_reference != QUEST_ACT_NEXT_STRING_REFERENCE:
            raise ValueError(
                f"{spec.table}: string cache ended at "
                f"{active_reader.next_reference}"
            )
        if active_reader.unresolved:
            raise ValueError(
                f"{spec.table}: unresolved references "
                f"{dict(active_reader.unresolved)}"
            )
    token_counts = Counter(active_reader.tokens)
    token_counts.subtract(tokens_before)
    unresolved = Counter(active_reader.unresolved)
    unresolved.subtract(unresolved_before)
    return QuestResult(
        spec=spec,
        header=header,
        start=start,
        done=cursor,
        advertised_rows=advertised_rows,
        rows=tuple(rows),
        digest=digest.hexdigest().upper(),
        token_counts=dict(
            sorted((key, value) for key, value in token_counts.items() if value)
        ),
        unresolved_references=dict(
            sorted((key, value) for key, value in unresolved.items() if value)
        ),
        resolution_evidence={
            "string_reference_range": {
                "first_reference": first_reference,
                "next_reference": active_reader.next_reference,
            }
        },
    )


def _layout_for_call(
    loader_dump: Path,
    call_sequence: Path,
    call_index: int,
) -> QuestQueryLayout:
    layouts = _parse_loader_layouts(loader_dump)
    sequence = json.loads(call_sequence.read_text(encoding="utf-8"))
    call = next(
        value
        for value in sequence
        if int(value["mapped_call_index"]) == call_index
    )
    task = call["tasks"][0]
    sql = str(task["sql"])
    layout = layouts[sql]
    return QuestQueryLayout(
        call_index=call_index,
        task=str(task["task"]),
        table=str(task["task"]).split("@", 1)[0],
        sql=sql,
        columns=tuple(layout["columns"]),
        layout=tuple(layout["layout"]),
        loader=str(layout["loader"]),
        loader_address=str(layout["address"]),
    )


def _layouts_for_calls(
    loader_dump: Path,
    call_sequence: Path,
    call_indexes: set[int],
) -> dict[int, QuestQueryLayout]:
    layouts = _parse_loader_layouts(loader_dump)
    sequence = json.loads(call_sequence.read_text(encoding="utf-8"))
    result: dict[int, QuestQueryLayout] = {}
    for call in sequence:
        call_index = int(call["mapped_call_index"])
        if call_index not in call_indexes:
            continue
        tasks = call["tasks"]
        if len(tasks) != 1:
            raise ValueError(f"SQL call {call_index} does not have one task")
        task = tasks[0]
        sql = str(task["sql"])
        layout = layouts.get(sql)
        if layout is None:
            raise ValueError(f"Missing replay layout at call {call_index}")
        result[call_index] = QuestQueryLayout(
            call_index=call_index,
            task=str(task["task"]),
            table=str(task["task"]).split("@", 1)[0],
            sql=sql,
            columns=tuple(layout["columns"]),
            layout=tuple(layout["layout"]),
            loader=str(layout["loader"]),
            loader_address=str(layout["address"]),
        )
    missing = call_indexes.difference(result)
    if missing:
        raise ValueError(f"Missing SQL calls for global replay: {sorted(missing)}")
    return result


def _replay_cached_result(
    data: bytes,
    reader: CachedResultReader,
    spec: QuestQueryLayout,
    start: int,
    *,
    advertised_rows: int | None = None,
) -> dict[str, Any]:
    tokens_before = Counter(reader.tokens)
    cursor = start
    rows = 0
    while cursor < len(data) and data[cursor] == 100:
        _, cursor = reader.row(cursor, list(spec.layout))
        rows += 1
    if cursor >= len(data) or data[cursor] != 101:
        raise ValueError(
            f"{spec.table}: replay expected SQLITE_DONE at 0x{cursor:X}"
        )
    if advertised_rows is not None and rows > advertised_rows:
        raise ValueError(
            f"{spec.table}: replay rows {rows} exceed {advertised_rows}"
        )
    token_counts = Counter(reader.tokens)
    token_counts.subtract(tokens_before)
    return {
        "call_index": spec.call_index,
        "table": spec.table,
        "start": start,
        "done": cursor,
        "rows": rows,
        "advertised_rows": advertised_rows,
        "token_counts": dict(
            sorted((key, value) for key, value in token_counts.items() if value)
        ),
    }


def _recover_pre_quest_global_strings(
    data: bytes,
    loader_dump: Path,
    call_sequence: Path,
    headers: tuple[tuple[int, int, int], ...],
) -> tuple[dict[int, str], dict[str, Any]]:
    """Recover every global string reference preceding the quest core.

    The map combines exact execution-order replay with two signature windows
    whose ordinal deltas are independently bracketed by native loaders.  The
    headerless string block and the headerless `items` result are bounded by
    the adjacent results and their independently proven next references.
    """

    wanted_calls = (
        set(range(3, 120))
        | set(range(166, 176))
        | {480}
    )
    specs = _layouts_for_calls(loader_dump, call_sequence, wanted_calls)

    def structural(
        reader: CachedResultReader,
        call_index: int,
        header_index: int,
    ) -> dict[str, Any]:
        _, start, advertised_rows = headers[header_index]
        return _replay_cached_result(
            data,
            reader,
            specs[call_index],
            start,
            advertised_rows=advertised_rows,
        )

    reader = CachedResultReader(data, 0)
    exact_results: list[dict[str, Any]] = []
    for call_index in range(3, 38):
        exact_results.append(structural(reader, call_index, call_index - 3))

    cursor = int(exact_results[-1]["done"]) + 1
    for call_index in range(38, 47):
        result = _replay_cached_result(
            data,
            reader,
            specs[call_index],
            cursor,
        )
        exact_results.append(result)
        cursor = int(result["done"]) + 1
    if cursor - 1 != headers[35][0]:
        raise ValueError("Modifier headerless replay lost its next boundary")

    for call_index in range(47, 67):
        exact_results.append(structural(reader, call_index, call_index - 12))
    # Call 67 has no native result in this stream.
    for call_index in range(68, 94):
        exact_results.append(structural(reader, call_index, call_index - 13))
    # Calls 94–96 are natively absent; calls 92–93 own the two empty headers.
    exact_results.append(structural(reader, 97, 81))
    for call_index in range(98, 110):
        exact_results.append(structural(reader, call_index, call_index - 16))

    cursor = int(exact_results[-1]["done"]) + 1
    result = _replay_cached_result(data, reader, specs[110], cursor)
    exact_results.append(result)
    if int(result["done"]) != headers[94][0]:
        raise ValueError("skill_visual_groups headerless boundary changed")

    result = structural(reader, 111, 94)
    exact_results.append(result)
    result = _replay_cached_result(
        data,
        reader,
        specs[112],
        int(result["done"]) + 1,
    )
    exact_results.append(result)
    if int(result["done"]) != headers[95][0]:
        raise ValueError("attachment_anims headerless boundary changed")
    if reader.next_reference != SKILLS_FIRST_STRING_REFERENCE:
        raise ValueError(
            f"Skills string seed changed: {reader.next_reference}"
        )
    if reader.unresolved:
        raise ValueError(
            f"Early global replay has unresolved refs: {reader.unresolved}"
        )

    for call_index in range(113, 120):
        exact_results.append(structural(reader, call_index, call_index - 18))
    if reader.next_reference != ATTACH_ANIMS_FIRST_STRING_REFERENCE:
        raise ValueError(
            "Pre-attach global replay ended at "
            f"{reader.next_reference}"
        )
    if reader.unresolved:
        raise ValueError(
            f"Skill/buff replay has unresolved refs: {reader.unresolved}"
        )
    values = dict(reader.cache)

    signatures = cached_string_signatures(data)
    signature_offsets = tuple(value.offset for value in signatures)

    quest_probe = structural(
        CachedResultReader(data, None),
        QUEST_CORE_FIRST_CALL,
        QUEST_CORE_FIRST_CALL - QUEST_CORE_HEADER_DELTA,
    )
    calibration_specs = (
        (
            "attach_anims",
            64_403_065,
            64_408_254,
            ATTACH_ANIMS_FIRST_STRING_REFERENCE,
            EARLY_SIGNATURE_DELTA,
        ),
        (
            "item_guide_b_categories",
            74_745_149,
            74_746_808,
            ITEM_GUIDE_FIRST_STRING_REFERENCE,
            EARLY_SIGNATURE_DELTA,
        ),
        (
            "item_armors",
            89_076_702,
            90_029_425,
            ITEMS_NEXT_STRING_REFERENCE,
            LATE_SIGNATURE_DELTA,
        ),
        (
            "item_rnd_attr_categories",
            93_357_456,
            93_389_042,
            247_474,
            LATE_SIGNATURE_DELTA,
        ),
        (
            "doodad_funcs",
            105_602_892,
            106_968_661,
            288_531,
            LATE_SIGNATURE_DELTA,
        ),
        (
            "quest_categories",
            int(quest_probe["start"]),
            int(quest_probe["done"]),
            QUEST_CORE_FIRST_STRING_REFERENCE,
            LATE_SIGNATURE_DELTA,
        ),
    )
    calibrations: list[dict[str, Any]] = []
    for table, start, done, first_reference, expected_delta in calibration_specs:
        candidate_index = bisect_left(signature_offsets, start)
        if candidate_index >= len(signatures):
            raise ValueError(f"{table}: string calibration is out of range")
        signature = signatures[candidate_index]
        if signature.offset > done:
            raise ValueError(f"{table}: no new string inside native result")
        delta = candidate_index - first_reference
        if delta != expected_delta:
            raise ValueError(
                f"{table}: signature delta {delta} != {expected_delta}"
            )
        calibrations.append(
            {
                "table": table,
                "start": start,
                "done": done,
                "first_reference": first_reference,
                "first_signature_offset": signature.offset,
                "candidate_index": candidate_index,
                "candidate_index_delta": delta,
            }
        )

    for reference in range(
        ATTACH_ANIMS_FIRST_STRING_REFERENCE,
        ITEM_GUIDE_FIRST_STRING_REFERENCE,
    ):
        values[reference] = signatures[
            reference + EARLY_SIGNATURE_DELTA
        ].value

    guide_reader = CachedResultReader(
        data, ITEM_GUIDE_FIRST_STRING_REFERENCE
    )
    guide_reader.cache.update(values)
    guide_results: list[dict[str, Any]] = []
    for call_index, header_index in zip(
        range(166, 175),
        range(140, 149),
        strict=True,
    ):
        guide_results.append(
            structural(guide_reader, call_index, header_index)
        )
    if guide_reader.next_reference != ITEM_GUIDE_NEXT_STRING_REFERENCE:
        raise ValueError(
            f"Item-guide replay ended at {guide_reader.next_reference}"
        )
    if guide_reader.unresolved:
        raise ValueError(
            f"Item-guide replay has unresolved refs: {guide_reader.unresolved}"
        )
    values.update(
        {
            key: value
            for key, value in guide_reader.cache.items()
            if ITEM_GUIDE_FIRST_STRING_REFERENCE
            <= key
            < ITEM_GUIDE_NEXT_STRING_REFERENCE
        }
    )

    raw_string_start = int(guide_results[-1]["done"]) + 1
    if raw_string_start != RAW_STRING_BLOCK_START:
        raise ValueError(
            f"Raw string block moved to 0x{raw_string_start:X}"
        )
    raw_first_candidate = bisect_left(signature_offsets, raw_string_start)
    raw_next_candidate = bisect_left(signature_offsets, ITEMS_RESULT_START)
    raw_signatures = signatures[raw_first_candidate:raw_next_candidate]
    expected_raw_strings = (
        RAW_STRING_BLOCK_NEXT_REFERENCE
        - ITEM_GUIDE_NEXT_STRING_REFERENCE
    )
    if len(raw_signatures) != expected_raw_strings:
        raise ValueError(
            "Headerless raw-string block changed: "
            f"{len(raw_signatures)} != {expected_raw_strings}"
        )
    for reference, signature in zip(
        range(
            ITEM_GUIDE_NEXT_STRING_REFERENCE,
            RAW_STRING_BLOCK_NEXT_REFERENCE,
        ),
        raw_signatures,
        strict=True,
    ):
        values[reference] = signature.value

    item_reader = CachedResultReader(
        data, RAW_STRING_BLOCK_NEXT_REFERENCE
    )
    item_reader.cache.update(values)
    item_result = _replay_cached_result(
        data,
        item_reader,
        specs[175],
        ITEMS_RESULT_START,
        advertised_rows=ITEMS_RESULT_ROWS,
    )
    if (
        int(item_result["done"]) != ITEMS_RESULT_DONE
        or int(item_result["rows"]) != ITEMS_RESULT_ROWS
        or item_reader.next_reference != ITEMS_NEXT_STRING_REFERENCE
    ):
        raise ValueError(f"Headerless items calibration changed: {item_result}")
    if dict(item_reader.unresolved) != {NEGATIVE_ITEM_STRING_ANOMALY: 1}:
        raise ValueError(
            "Items string anomaly changed: "
            f"{dict(item_reader.unresolved)}"
        )
    values.update(
        {
            key: value
            for key, value in item_reader.cache.items()
            if RAW_STRING_BLOCK_NEXT_REFERENCE
            <= key
            < ITEMS_NEXT_STRING_REFERENCE
        }
    )

    for reference in range(
        ITEMS_NEXT_STRING_REFERENCE,
        PRE_QUEST_STRING_REFERENCE_COUNT,
    ):
        values[reference] = signatures[
            reference + LATE_SIGNATURE_DELTA
        ].value
    digest = string_cache_digest(
        values,
        PRE_QUEST_STRING_REFERENCE_COUNT,
    )
    if values[110150] != "피 묻은 손의 시체를 조사합니다.":
        raise ValueError("Known skills string reference 110150 changed")

    return values, {
        "format": "AA8_PRE_QUEST_GLOBAL_STRING_CACHE_V1",
        "method": (
            "execution_order_replay_plus_bracketed_signature_windows"
        ),
        "first_reference": 0,
        "next_reference": PRE_QUEST_STRING_REFERENCE_COUNT,
        "value_count": len(values),
        "value_digest": digest,
        "digest_format": "uint32_le_reference+uint32_le_utf8_bytes+utf8",
        "exact_replay": {
            "calls": [[3, 66], [68, 93], [97, 119]],
            "headerless_calls": list(range(38, 47)) + [110, 112],
            "native_absent_calls": [67, 94, 95, 96],
            "skills_first_reference": SKILLS_FIRST_STRING_REFERENCE,
            "attach_anims_first_reference": (
                ATTACH_ANIMS_FIRST_STRING_REFERENCE
            ),
            "results": len(exact_results),
            "rows": sum(int(result["rows"]) for result in exact_results),
        },
        "calibrations": calibrations,
        "early_signature_window": {
            "first_reference": ATTACH_ANIMS_FIRST_STRING_REFERENCE,
            "next_reference": ITEM_GUIDE_FIRST_STRING_REFERENCE,
            "candidate_index_delta": EARLY_SIGNATURE_DELTA,
        },
        "item_guide_replay": {
            "calls": [166, 174],
            "first_reference": ITEM_GUIDE_FIRST_STRING_REFERENCE,
            "next_reference": ITEM_GUIDE_NEXT_STRING_REFERENCE,
            "rows": sum(int(result["rows"]) for result in guide_results),
        },
        "raw_string_block": {
            "start": raw_string_start,
            "done_exclusive": ITEMS_RESULT_START,
            "first_reference": ITEM_GUIDE_NEXT_STRING_REFERENCE,
            "next_reference": RAW_STRING_BLOCK_NEXT_REFERENCE,
            "candidate_count": len(raw_signatures),
        },
        "items_replay": {
            **item_result,
            "first_reference": RAW_STRING_BLOCK_NEXT_REFERENCE,
            "next_reference": ITEMS_NEXT_STRING_REFERENCE,
            "preserved_anomaly": {
                "reference": NEGATIVE_ITEM_STRING_ANOMALY,
                "occurrences": 1,
                "scope": "negative_item_row",
            },
        },
        "late_signature_window": {
            "first_reference": ITEMS_NEXT_STRING_REFERENCE,
            "next_reference": PRE_QUEST_STRING_REFERENCE_COUNT,
            "candidate_index_delta": LATE_SIGNATURE_DELTA,
        },
    }


def _resolve_external_strings(
    result: QuestResult,
    values: dict[int, str],
    evidence: dict[str, Any],
) -> QuestResult:
    unresolved = Counter(result.unresolved_references)
    resolved_occurrences = 0
    rows: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    for row in result.rows:
        resolved_row = dict(row)
        for column, value in tuple(resolved_row.items()):
            if (
                not isinstance(value, str)
                or not value.startswith("<ref:")
                or not value.endswith(">")
            ):
                continue
            reference = int(value[5:-1])
            replacement = values.get(reference)
            if replacement is None:
                continue
            resolved_row[column] = replacement
            unresolved[reference] -= 1
            resolved_occurrences += 1
        encoded = canonical_json(resolved_row).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
        rows.append(resolved_row)
    unresolved = Counter(
        {
            key: value
            for key, value in unresolved.items()
            if value > 0
        }
    )
    tokens = dict(result.token_counts)
    tokens["externally_resolved_reference"] = resolved_occurrences
    return QuestResult(
        spec=result.spec,
        header=result.header,
        start=result.start,
        done=result.done,
        advertised_rows=result.advertised_rows,
        rows=tuple(rows),
        digest=digest.hexdigest().upper(),
        token_counts=dict(sorted(tokens.items())),
        unresolved_references=dict(sorted(unresolved.items())),
        resolution_evidence={
            **result.resolution_evidence,
            "external_string_seed": evidence,
            "externally_resolved_occurrences": resolved_occurrences,
        },
    )


def decode_quest_core(
    game11: Path,
    loader_dump: Path,
    call_sequence: Path,
) -> dict[str, QuestResult]:
    data = game11.read_bytes()
    headers = _structural_headers(data)
    specs = load_quest_core_layouts(loader_dump, call_sequence)
    specs_by_call = {spec.call_index: spec for spec in specs}
    pre_act_insert_counts: dict[int, int] = {}
    for call_index in range(QUEST_CORE_FIRST_CALL, 584):
        spec = specs_by_call[call_index]
        header, start, advertised_rows = headers[
            call_index - QUEST_CORE_HEADER_DELTA
        ]
        probe = _decode_result(
            data,
            spec,
            header,
            start,
            advertised_rows,
        )
        pre_act_insert_counts[call_index] = int(
            probe.token_counts.get("insert", 0)
        )
    derived_first_reference = (
        QUEST_ACT_FIRST_STRING_REFERENCE
        - sum(pre_act_insert_counts.values())
    )
    if derived_first_reference != QUEST_CORE_FIRST_STRING_REFERENCE:
        raise ValueError(
            "Quest-core string seed changed: "
            f"{derived_first_reference}"
        )
    pre_quest_strings, pre_quest_string_evidence = (
        _recover_pre_quest_global_strings(
        data,
        loader_dump,
        call_sequence,
        headers,
        )
    )
    shared_reader = CachedResultReader(data, derived_first_reference)
    decoded: dict[str, QuestResult] = {}
    for spec in specs:
        header_index = spec.call_index - QUEST_CORE_HEADER_DELTA
        header, start, advertised_rows = headers[header_index]
        first_reference = shared_reader.next_reference
        result = _decode_result(
            data,
            spec,
            header,
            start,
            advertised_rows,
            reader=shared_reader,
        )
        result.resolution_evidence["quest_core_global_replay"] = {
            "core_first_call": QUEST_CORE_FIRST_CALL,
            "core_first_reference": derived_first_reference,
            "query_first_reference": first_reference,
            "query_next_reference": shared_reader.next_reference,
            "pre_quest_act_insert_count": sum(
                pre_act_insert_counts.values()
            ),
            "quest_act_reference_anchor": QUEST_ACT_FIRST_STRING_REFERENCE,
        }
        if result.unresolved_references:
            result = _resolve_external_strings(
                result,
                pre_quest_strings,
                pre_quest_string_evidence,
            )
        if result.unresolved_references:
            raise ValueError(
                f"{spec.table} retains unresolved string references: "
                f"{result.unresolved_references}"
            )
        if spec.table == "quest_acts":
            if first_reference != QUEST_ACT_FIRST_STRING_REFERENCE:
                raise ValueError(
                    f"quest_acts started at string ref {first_reference}"
                )
            if shared_reader.next_reference != QUEST_ACT_NEXT_STRING_REFERENCE:
                raise ValueError(
                    "quest_acts string endpoint changed: "
                    f"{shared_reader.next_reference}"
                )
        if spec.table == "quest_component_texts":
            if first_reference != QUEST_COMPONENT_TEXT_FIRST_STRING_REFERENCE:
                raise ValueError(
                    "quest_component_texts first string reference changed: "
                    f"{first_reference}"
                )
            if (
                shared_reader.next_reference
                != QUEST_COMPONENT_TEXT_NEXT_STRING_REFERENCE
            ):
                raise ValueError(
                    "quest_component_texts string endpoint changed: "
                    f"{shared_reader.next_reference}"
                )
        decoded[spec.table] = result

    anchors = {
        "quest_monster_npcs": 0x6CB8F6D,
        "quest_act_obj_spheres": 0x6D396B7,
        "quest_act_con_accept_npcs": 0x6D3DC71,
        "quest_act_con_auto_completes": 0x6D535A6,
        "quest_act_supply_items": 0x6D6B51B,
        "quest_act_supply_exps": 0x6D89D77,
        "quest_act_supply_coppers": 0x6D9309E,
        "quest_act_supply_selective_items": 0x6D9BD7A,
        "quest_acts": 0x6DB2158,
        "quest_components": 121_996_619,
        "quest_contexts": 124_139_000,
    }
    for table, expected in anchors.items():
        if decoded[table].start != expected:
            raise ValueError(
                f"{table}: start 0x{decoded[table].start:X} != 0x{expected:X}"
            )
    if sum(len(result.rows) for result in decoded.values()) != 180_730:
        raise ValueError("Quest-core row total changed")
    if sum(not result.rows for result in decoded.values()) != 12:
        raise ValueError("Quest-core native-empty table count changed")
    filtered_differences = {
        table: (result.advertised_rows, len(result.rows))
        for table, result in decoded.items()
        if result.advertised_rows != len(result.rows)
    }
    if filtered_differences != {
        "quest_acts": (42_462, 42_446),
        "quest_chat_bubbles": (25_943, 25_939),
        "quest_component_texts": (13_537, 13_531),
    }:
        raise ValueError(
            f"Quest filtered-result differences changed: {filtered_differences}"
        )
    return dict(sorted(decoded.items()))


def decode_effect_fire_details(
    game11: Path,
    loader_dump: Path,
) -> QuestResult:
    layouts = _parse_loader_layouts(loader_dump)
    sql = (
        "SELECT id, count, effect_id, quest_act_obj_alias_id, team_share, "
        "use_alias FROM quest_act_obj_effect_fires"
    )
    layout = layouts[sql]
    spec = QuestQueryLayout(
        call_index=102,
        task=str(layout["task"]),
        table="quest_act_obj_effect_fires",
        sql=sql,
        columns=tuple(layout["columns"]),
        layout=tuple(layout["layout"]),
        loader=str(layout["loader"]),
        loader_address=str(layout["address"]),
    )
    data = game11.read_bytes()
    result = _decode_result(
        data,
        spec,
        header=0xE58495,
        start=0xE5849B,
        advertised_rows=143,
    )
    if len(result.rows) != 143 or result.done != 0xE58F38:
        raise ValueError("QuestActObjEffectFire native boundary changed")
    return result


def camel_to_snake(value: str) -> str:
    return CAMEL_BOUNDARY.sub("_", value).lower()


def act_detail_table(actual_type: str) -> str:
    singular = camel_to_snake(actual_type)
    if singular.endswith("y"):
        return singular[:-1] + "ies"
    if singular.endswith(("s", "x", "ch", "sh")):
        return singular + "es"
    return singular + "s"


def relation_target(
    table: str,
    column: str,
) -> tuple[str, str] | None:
    exact: dict[str, tuple[str, str]] = {
        "quest_context_id": ("belongs_to_quest", "quest"),
        "quest_id": ("references_quest", "quest"),
        "context_id": ("references_quest", "quest"),
        "quest_component_id": ("references_component", "quest_component"),
        "component_id": ("references_component", "quest_component"),
        "next_component": ("continues_with_component", "quest_component"),
        "npc_id": ("references_npc", "npc"),
        "npc_group_id": ("references_npc_group", "npc_group"),
        "npc_spawner_id": ("references_npc_spawner", "npc_spawner"),
        "npc_ai_id": ("references_npc_ai", "npc_ai"),
        "item_id": ("references_item", "item"),
        "doodad_id": ("references_doodad", "doodad"),
        "highlight_doodad_id": ("highlights_doodad", "doodad"),
        "skill_id": ("references_skill", "skill"),
        "buff_id": ("references_buff", "buff"),
        "effect_id": ("references_effect", "effect"),
        "sphere_id": ("references_sphere", "sphere"),
        "cinema_id": ("references_cinema", "cinema"),
        "camera_id": ("references_quest_camera", "quest_camera"),
        "quest_camera_id": ("references_quest_camera", "quest_camera"),
        "model_id": ("references_model", "model"),
        "sound_id": ("references_sound", "sound"),
        "summary_voice_id": ("references_voice", "voice"),
        "ai_command_set_id": ("references_ai_command_set", "ai_command_set"),
        "quest_monster_group_id": (
            "references_quest_monster_group",
            "quest_monster_group",
        ),
        "quest_doodad_group_id": (
            "references_quest_doodad_group",
            "quest_doodad_group",
        ),
        "quest_context_group_id": (
            "references_quest_context_group",
            "quest_context_group",
        ),
        "quest_item_group_id": (
            "references_quest_item_group",
            "quest_item_group",
        ),
        "item_group_id": ("references_quest_item_group", "quest_item_group"),
        "quest_act_obj_alias_id": (
            "references_quest_object_alias",
            "quest_act_obj_alias",
        ),
        "quest_mail_id": ("references_quest_mail", "quest_mail"),
        "quest_mail_attachment_id": (
            "references_quest_mail_attachment",
            "quest_mail_attachment",
        ),
        "mail_id": ("references_mail", "mail"),
        "item_grade_id": ("references_item_grade", "item_grade"),
        "grade_id": ("references_item_grade", "item_grade"),
        "craft_id": ("references_craft", "craft"),
        "interaction_id": ("references_interaction", "interaction"),
        "wi_id": ("references_world_interaction", "world_interaction"),
        "actability_group_id": (
            "references_actability_group",
            "actability_group",
        ),
        "appellation_id": ("references_appellation", "appellation"),
        "faction_id": ("references_faction", "system_faction"),
        "ability_id": ("references_ability", "ability"),
        "condition_id": ("references_condition", "condition"),
        "quest_component_text_kind_id": (
            "has_text_kind",
            "quest_component_text_kind",
        ),
        "quest_context_text_kind_id": (
            "has_text_kind",
            "quest_context_text_kind",
        ),
        "quest_name_kind_id": ("has_name_kind", "quest_name_kind"),
        "chat_bubble_kind_id": (
            "has_chat_bubble_kind",
            "chat_bubble_kind",
        ),
        "today_quest_goal_id": (
            "references_today_quest_goal",
            "today_quest_goal",
        ),
        "today_quest_step_id": (
            "references_today_quest_step",
            "today_quest_step",
        ),
        "express_key_id": ("references_express_key", "express_key"),
        "faction_competition_id": (
            "references_faction_competition",
            "faction_competition",
        ),
        "evolving_material_id": (
            "references_evolving_material",
            "item_evolving_material",
        ),
        "enchant_scale_id": (
            "references_enchant_scale",
            "enchant_scale",
        ),
    }
    if column == "category_id" and table == "quest_contexts":
        return "belongs_to_quest_category", "quest_category"
    if column == "category_id" and table in {"quest_mails", "quest_mail_sends"}:
        return "belongs_to_mail_category", "mail_category"
    return exact.get(column)


def table_entity_identity(table: str, native_id: Any) -> tuple[str, str]:
    kinds = {
        "quest_contexts": "quest",
        "quest_components": "quest_component",
        "quest_acts": "quest_act",
        "quest_categories": "quest_category",
        "quest_item_groups": "quest_item_group",
        "quest_monster_groups": "quest_monster_group",
        "quest_doodad_groups": "quest_doodad_group",
        "quest_context_groups": "quest_context_group",
        "quest_act_obj_aliases": "quest_act_obj_alias",
        "quest_mails": "quest_mail",
        "quest_mail_attachments": "quest_mail_attachment",
        "quest_supplies": "quest_supply",
        "quest_cameras": "quest_camera",
        "cinemas": "cinema",
        "today_quest_groups": "today_quest_group",
        "today_quest_steps": "today_quest_step",
        "today_quest_goals": "today_quest_goal",
    }
    if table in kinds:
        return kinds[table], str(native_id)
    if table.startswith("quest_act_"):
        return "quest_act_detail", f"{table}:{native_id}"
    return table.removesuffix("s"), str(native_id)


def quest_act_detail_counts(
    decoded: dict[str, QuestResult],
    effect_fires: QuestResult,
) -> dict[str, Any]:
    tables = {**decoded, effect_fires.spec.table: effect_fires}
    detail_ids = {
        table: {int(row["id"]) for row in result.rows}
        for table, result in tables.items()
        if table.startswith("quest_act_") and table != "quest_acts"
    }
    acts = decoded["quest_acts"].rows
    missing: Counter[str] = Counter()
    referenced: Counter[str] = Counter()
    unused: dict[str, int] = {}
    for act in acts:
        actual_type = str(act["act_detail_type"])
        table = act_detail_table(actual_type)
        native_id = int(act["act_detail_id"])
        referenced[table] += 1
        if native_id not in detail_ids.get(table, set()):
            missing[f"{table}:{native_id}"] += 1
    for table, ids in detail_ids.items():
        used = {
            int(act["act_detail_id"])
            for act in acts
            if act_detail_table(str(act["act_detail_type"])) == table
        }
        unused[table] = len(ids - used)
    return {
        "act_rows": len(acts),
        "detail_types": len(referenced),
        "missing": dict(sorted(missing.items())),
        "referenced_by_table": dict(sorted(referenced.items())),
        "unused_by_table": {
            key: value for key, value in sorted(unused.items()) if value
        },
    }
