from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import canonical_json, write_text_atomic


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
ACCESSOR_OFFSETS = {
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
}
TASK_PATTERN = re.compile(
    r"^TASK\t(?P<table>[^\r\n]+)\r?\n"
    r"SQL\t(?P<sql>[^\r\n]+)\r?\n"
    r"(?P<body>.*?)^TASK_END$",
    re.MULTILINE | re.DOTALL,
)
FUNCTION_PATTERN = re.compile(
    r"^FUNCTION_BEGIN\t(?P<name>[^\t\r\n]+)\t(?P<address>[^\r\n]+)\r?\n"
    r"(?P<body>.*?)^FUNCTION_END$",
    re.MULTILINE | re.DOTALL,
)
INSTRUCTION_FUNCTION_PATTERN = re.compile(
    r"^FUNCTION_BEGIN\t[^\t\r\n]+\t(?P<address>[^\r\n]+)\r?\n"
    r"(?P<body>.*?)^FUNCTION_END$",
    re.MULTILINE | re.DOTALL,
)
INSTRUCTION_ACCESSOR_PATTERN = re.compile(
    r"MOV\s+R8D,0x(?P<index>[0-9a-fA-F]+)"
    r"(?:\r?\n[^\r\n]+){1,5}\r?\n"
    r"[^\r\n]*CALL\s+qword ptr\s+\[[^\]]+\+\s+0x"
    r"(?P<kind>38|40|60|68|70|78)\]",
    re.MULTILINE,
)


@dataclass(frozen=True)
class LayoutCandidate:
    table_name: str
    sql_text: str
    columns: tuple[str, ...]
    layout: tuple[str, ...]
    function_name: str
    function_address: str
    confidence: str
    blockers: tuple[str, ...]


def _sql_columns(sql: str) -> tuple[str, ...]:
    match = re.search(r"^\s*SELECT\s+(.*?)\s+FROM\s", sql, re.I | re.S)
    if not match:
        return ()
    # The item queries in scope do not contain comma-bearing expressions.
    return tuple(part.strip() for part in match.group(1).split(","))


def build_task_tsv(database: Path, destination: Path) -> int:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT q.table_name,q.sql_text
            FROM query_specs q
            JOIN cached_results r ON r.query_spec_id=q.query_spec_id
            WHERE r.status='layout_missing'
            ORDER BY q.table_name,q.source_module
            """
        ).fetchall()
    finally:
        connection.close()
    lines = [
        f"{row['table_name']}\t{str(row['sql_text']).replace(chr(9), ' ')}"
        for row in rows
        if row["sql_text"]
    ]
    write_text_atomic(destination, "\n".join(lines) + ("\n" if lines else ""))
    return len(lines)


def _function_candidate(
    table: str,
    sql: str,
    name: str,
    address: str,
    body: str,
    pointer_bits: int = 64,
    instruction_accessors: dict[int, set[str]] | None = None,
) -> LayoutCandidate:
    columns = _sql_columns(sql)
    found: dict[int, set[str]] = {}
    for match in ACCESSOR_PATTERN.finditer(body):
        index = int(match.group("index"), 0)
        kind = ACCESSOR_OFFSETS[pointer_bits].get(match.group("offset"))
        if kind is not None:
            found.setdefault(index, set()).add(kind)
    for match in LOOP_ACCESSOR_PATTERN.finditer(body):
        kind = ACCESSOR_OFFSETS[pointer_bits].get(match.group("offset"))
        if kind is None:
            continue
        for index in range(1, int(match.group("limit")) + 1):
            found.setdefault(index, set()).add(kind)
    for index, kinds in (instruction_accessors or {}).items():
        found.setdefault(index, set()).update(kinds)

    blockers: list[str] = []
    layout: list[str] = []
    for index in range(len(columns)):
        kinds = found.get(index, set())
        if not kinds:
            blockers.append(f"missing_accessor:{index}")
            layout.append("?")
        elif len(kinds) > 1:
            blockers.append(
                f"conflicting_accessor:{index}:{','.join(sorted(kinds))}"
            )
            layout.append("?")
        else:
            layout.append(next(iter(kinds)))
    extra = sorted(index for index in found if index >= len(columns))
    if extra:
        blockers.append("out_of_range_accessors:" + ",".join(map(str, extra)))
    if not columns:
        blockers.append("sql_columns_not_parsed")
    confidence = "confirmed_static" if not blockers else "blocked"
    return LayoutCandidate(
        table_name=table,
        sql_text=sql,
        columns=columns,
        layout=tuple(layout),
        function_name=name,
        function_address=address,
        confidence=confidence,
        blockers=tuple(blockers),
    )


def _instruction_accessors(source: Path | None) -> dict[str, dict[int, set[str]]]:
    if source is None:
        return {}
    text = source.read_text(encoding="utf-8", errors="replace")
    result: dict[str, dict[int, set[str]]] = {}
    for function in INSTRUCTION_FUNCTION_PATTERN.finditer(text):
        values: dict[int, set[str]] = {}
        for match in INSTRUCTION_ACCESSOR_PATTERN.finditer(function.group("body")):
            values.setdefault(int(match.group("index"), 16), set()).add(
                match.group("kind")
            )
        result[function.group("address")] = values
    return result


def parse_ghidra_output(
    source: Path,
    instruction_source: Path | None = None,
) -> list[dict[str, Any]]:
    text = source.read_text(encoding="utf-8", errors="replace")
    language_match = re.search(r"^LANGUAGE\t([^\r\n]+)$", text, re.MULTILINE)
    pointer_bits = (
        32
        if language_match is not None
        and ":32:" in language_match.group(1)
        else 64
    )
    instruction_values = _instruction_accessors(instruction_source)
    result: list[dict[str, Any]] = []
    for task in TASK_PATTERN.finditer(text):
        table = task.group("table")
        sql = task.group("sql")
        body = task.group("body")
        functions = [
            _function_candidate(
                table,
                sql,
                function.group("name"),
                function.group("address"),
                function.group("body"),
                pointer_bits,
                instruction_values.get(function.group("address")),
            )
            for function in FUNCTION_PATTERN.finditer(body)
        ]
        confirmed = [
            candidate for candidate in functions
            if candidate.confidence == "confirmed_static"
        ]
        unique_layouts = sorted({candidate.layout for candidate in confirmed})
        selected = (
            next(
                candidate
                for candidate in confirmed
                if candidate.layout == unique_layouts[0]
            )
            if len(unique_layouts) == 1
            else None
        )
        blockers: list[str] = []
        if "STRING_MATCHES\t0" in body:
            blockers.append("embedded_sql_not_found")
        if not functions:
            blockers.append("loader_function_not_found")
        if len(unique_layouts) > 1:
            blockers.append("conflicting_complete_layouts")
        if selected is None and functions:
            blockers.append("no_complete_static_layout")
        result.append(
            {
                "table_name": table,
                "sql_text": sql,
                "columns": list(_sql_columns(sql)),
                "status": (
                    "confirmed_static"
                    if selected is not None
                    else "blocked"
                ),
                "layout": list(selected.layout) if selected else [],
                "loader": (
                    {
                        "function": selected.function_name,
                        "address": selected.function_address,
                    }
                    if selected
                    else None
                ),
                "blockers": blockers,
                "function_candidates": [
                    {
                        "function": candidate.function_name,
                        "address": candidate.function_address,
                        "layout": list(candidate.layout),
                        "confidence": candidate.confidence,
                        "blockers": list(candidate.blockers),
                    }
                    for candidate in functions
                ],
            }
        )
    return result


def write_candidates(
    source: Path,
    destination: Path,
    instruction_source: Path | None = None,
) -> dict[str, int]:
    candidates = parse_ghidra_output(source, instruction_source)
    write_text_atomic(destination, canonical_json(candidates, pretty=True))
    return {
        "tasks": len(candidates),
        "confirmed_static": sum(
            candidate["status"] == "confirmed_static"
            for candidate in candidates
        ),
        "blocked": sum(
            candidate["status"] == "blocked"
            for candidate in candidates
        ),
    }
