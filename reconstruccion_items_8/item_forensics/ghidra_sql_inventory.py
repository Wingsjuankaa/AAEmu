from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .util import canonical_json, sha256_file, write_text_atomic


SELECT = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
FROM = re.compile(r"\bFROM\b", re.IGNORECASE)
CALL = re.compile(r"\b(FUN_[0-9a-f]+)\s*\(")


def build_all_sql_tasks(
    sql_manifest: Path,
    destination: Path,
    *,
    binary_name: str = "bin64",
) -> dict[str, Any]:
    document = json.loads(sql_manifest.read_text(encoding="utf-8-sig"))
    binaries = [
        binary
        for binary in document.get("binaries", [])
        if binary_name.lower() in str(binary.get("path", "")).lower()
    ]
    if len(binaries) != 1:
        raise ValueError(
            f"Expected one {binary_name} SQL inventory, found {len(binaries)}"
        )
    seen: set[str] = set()
    rows: list[tuple[str, str]] = []
    for statement in binaries[0].get("statements", []):
        sql = str(statement.get("value", ""))
        if not SELECT.search(sql) or not FROM.search(sql) or sql in seen:
            continue
        seen.add(sql)
        tables = [str(value) for value in statement.get("tables", [])]
        label = (
            tables[0] if tables else "select"
        ) + "@" + format(int(statement["offset"]), "x")
        rows.append((label, sql.replace("\t", " ")))
    write_text_atomic(
        destination,
        "".join(f"{label}\t{sql}\n" for label, sql in rows),
    )
    return {
        "tasks": len(rows),
        "sha256": sha256_file(destination),
        "path": destination.resolve().as_posix(),
    }


def _loader_function_tasks(
    loader_dump: Path,
) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    task = ""
    sql = ""
    for line in loader_dump.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        if line.startswith("TASK\t"):
            task = line.split("\t", 1)[1]
        elif line.startswith("SQL\t"):
            sql = line.split("\t", 1)[1]
        elif line.startswith("FUNCTION_BEGIN\t"):
            function = line.split("\t", 2)[1]
            entry = {"task": task, "sql": sql}
            values = result.setdefault(function, [])
            if entry not in values:
                values.append(entry)
    return result


def build_master_sql_call_sequence(
    master_dump: Path,
    loader_dump: Path,
    destination: Path,
) -> dict[str, Any]:
    master = master_dump.read_text(encoding="utf-8", errors="replace")
    section_match = re.search(
        r"^===== FUN_399005a0 @ 399005a0 =====\r?\n"
        r".*?(?=^=====|\Z)",
        master,
        re.MULTILINE | re.DOTALL,
    )
    if section_match is None:
        raise ValueError("FUN_399005a0 was not found in the master dump")
    function_section = section_match.group(0)
    function_tasks = _loader_function_tasks(loader_dump)
    rows: list[dict[str, Any]] = []
    for match in CALL.finditer(function_section):
        function = match.group(1)
        tasks = function_tasks.get(function)
        if not tasks:
            continue
        rows.append(
            {
                "mapped_call_index": len(rows),
                "function": function,
                "master_line": function_section.count(
                    "\n",
                    0,
                    match.start(),
                ) + 1,
                "tasks": tasks,
            }
        )
    write_text_atomic(destination, canonical_json(rows, pretty=True))
    return {
        "mapped_calls": len(rows),
        "unique_functions": len({row["function"] for row in rows}),
        "sha256": sha256_file(destination),
        "path": destination.resolve().as_posix(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic AA8 Ghidra SQL task and call inventories."
    )
    parser.add_argument("--sql-manifest", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--binary-name", default="bin64")
    parser.add_argument("--master-dump", type=Path)
    parser.add_argument("--loader-dump", type=Path)
    parser.add_argument("--sequence", type=Path)
    options = parser.parse_args(argv)
    result = {
        "tasks": build_all_sql_tasks(
            options.sql_manifest,
            options.tasks,
            binary_name=options.binary_name,
        )
    }
    sequence_options = (
        options.master_dump,
        options.loader_dump,
        options.sequence,
    )
    if any(sequence_options) and not all(sequence_options):
        parser.error(
            "--master-dump, --loader-dump and --sequence must be used together"
        )
    if all(sequence_options):
        result["sequence"] = build_master_sql_call_sequence(
            options.master_dump,
            options.loader_dump,
            options.sequence,
        )
    print(canonical_json(result, pretty=True), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
