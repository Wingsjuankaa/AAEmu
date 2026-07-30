from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .quests import _parse_loader_layouts, _structural_headers
from .util import canonical_json
from .world_actors import CachedResultReader


ITEM_GRADE_BUFFS_SQL = (
    "SELECT id, buff_id, item_grade_id, item_id, num_pieces "
    "FROM item_grade_buffs"
)
ITEM_GRADE_SKILLS_SQL = (
    "SELECT id, item_grade_id, item_id, skill_id FROM item_grade_skills"
)
ITEM_GRADE_DISTRIBUTIONS_SQL = (
    "SELECT id, weight_0, weight_1, weight_2, weight_3, weight_4, "
    "weight_5, weight_6, weight_7, weight_8, weight_9, weight_10, "
    "weight_11, weight_12 FROM item_grade_distributions"
)


@dataclass(frozen=True)
class ItemGradeSecondarySpec:
    table: str
    entity_kind: str
    sql: str
    columns: tuple[str, ...]
    layout: tuple[str, ...]
    call_index: int
    header_index: int
    header: int
    start: int
    done: int
    rows: int
    digest: str
    x64_loader: str
    x86_loader: str


ITEM_GRADE_SECONDARY_SPECS = (
    ItemGradeSecondarySpec(
        table="item_grade_buffs",
        entity_kind="item_grade_buff",
        sql=ITEM_GRADE_BUFFS_SQL,
        columns=(
            "id",
            "buff_id",
            "item_grade_id",
            "item_id",
            "num_pieces",
        ),
        layout=("68", "68", "68", "68", "68"),
        call_index=138,
        header_index=114,
        header=0x3F71DBE,
        start=0x3F71DC4,
        done=0x3F9C8EC,
        rows=8_328,
        digest=(
            "18B80E0347939610654F2F788F3F2F8F"
            "10F80DD2EA070382E9AA6A3F721A13F1"
        ),
        x64_loader="FUN_39a35750",
        x86_loader="FUN_39d2e120",
    ),
    ItemGradeSecondarySpec(
        table="item_grade_skills",
        entity_kind="item_grade_skill",
        sql=ITEM_GRADE_SKILLS_SQL,
        columns=("id", "item_grade_id", "item_id", "skill_id"),
        layout=("68", "68", "68", "68"),
        call_index=139,
        header_index=115,
        header=0x3F9C8EC,
        start=0x3F9C8F2,
        done=0x3F9C97A,
        rows=8,
        digest=(
            "F8C878652F5FA5F39513755A731952CF"
            "884C007AEACD7902EEFD640DE76F770D"
        ),
        x64_loader="FUN_39a35a00",
        x86_loader="FUN_39d2e340",
    ),
    ItemGradeSecondarySpec(
        table="item_grade_distributions",
        entity_kind="item_grade_distribution",
        sql=ITEM_GRADE_DISTRIBUTIONS_SQL,
        columns=(
            "id",
            "weight_0",
            "weight_1",
            "weight_2",
            "weight_3",
            "weight_4",
            "weight_5",
            "weight_6",
            "weight_7",
            "weight_8",
            "weight_9",
            "weight_10",
            "weight_11",
            "weight_12",
        ),
        layout=("68",) * 14,
        call_index=145,
        header_index=121,
        header=0x46AFDF1,
        start=0x46AFDF7,
        done=0x46B0919,
        rows=50,
        digest=(
            "E977A488392208F7F16DCC97255B420A"
            "A7E8309B855118A110829BAC578F22E2"
        ),
        x64_loader="FUN_39a369f0",
        x86_loader="FUN_39d2efa0",
    ),
)


def _row_digest(
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> str:
    return hashlib.sha256(
        canonical_json(
            [[row[column] for column in columns] for row in rows]
        ).encode("utf-8")
    ).hexdigest().upper()


def audit_item_grade_secondary(config: Any) -> dict[str, Any]:
    x64 = _parse_loader_layouts(
        config.source_ghidra_item_grade_secondary_x64
    )
    x86 = _parse_loader_layouts(
        config.source_ghidra_item_grade_secondary_x86
    )
    task_rows = [
        tuple(line.split("\t", 1))
        for line in config.source_item_grade_secondary_loader_tasks.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        if line and not line.startswith("#")
    ]
    expected_tasks = {(spec.table + "@" + {
        "item_grade_buffs": "dfdb10",
        "item_grade_skills": "dfdbf0",
        "item_grade_distributions": "dfde90",
    }[spec.table], spec.sql) for spec in ITEM_GRADE_SECONDARY_SPECS}
    if set(task_rows) != expected_tasks:
        raise RuntimeError("Secondary item-grade task registry changed")

    sequence = json.loads(
        config.source_ghidra_sql_call_sequence.read_text(encoding="utf-8")
    )
    if not isinstance(sequence, list):
        raise RuntimeError("Native SQL call sequence is not an array")
    sequence_by_index = {
        int(call["mapped_call_index"]): call
        for call in sequence
        if "mapped_call_index" in call
    }

    data = config.source_game11.read_bytes()
    headers = _structural_headers(data)
    results: dict[str, dict[str, Any]] = {}
    for spec in ITEM_GRADE_SECONDARY_SPECS:
        left = x64.get(spec.sql)
        right = x86.get(spec.sql)
        if left is None or right is None:
            raise RuntimeError(
                f"{spec.table}: loader missing in one architecture"
            )
        for actual, expected, label in (
            (tuple(left["columns"]), spec.columns, "x64 columns"),
            (tuple(right["columns"]), spec.columns, "x86 columns"),
            (tuple(left["layout"]), spec.layout, "x64 layout"),
            (tuple(right["layout"]), spec.layout, "x86 layout"),
            (str(left["loader"]), spec.x64_loader, "x64 loader"),
            (str(right["loader"]), spec.x86_loader, "x86 loader"),
        ):
            if actual != expected:
                raise RuntimeError(
                    f"{spec.table}: {label} changed: "
                    f"{actual!r} != {expected!r}"
                )

        call = sequence_by_index.get(spec.call_index)
        if call is None or len(call.get("tasks", [])) != 1:
            raise RuntimeError(
                f"{spec.table}: native call {spec.call_index} is ambiguous"
            )
        task = call["tasks"][0]
        if str(task["sql"]) != spec.sql:
            raise RuntimeError(
                f"{spec.table}: SQL changed at call {spec.call_index}"
            )

        header, start, advertised_rows = headers[spec.header_index]
        if (
            header != spec.header
            or start != spec.start
            or advertised_rows != spec.rows
        ):
            raise RuntimeError(
                f"{spec.table}: structural header changed"
            )
        reader = CachedResultReader(data, first_string_reference=None)
        cursor = start
        rows: list[dict[str, Any]] = []
        while cursor < len(data) and data[cursor] == 100:
            values, cursor = reader.row(cursor, list(spec.layout))
            rows.append(dict(zip(spec.columns, values, strict=True)))
        if cursor != spec.done or data[cursor] != 101:
            raise RuntimeError(
                f"{spec.table}: SQLITE_DONE boundary changed at 0x{cursor:X}"
            )
        if len(rows) != spec.rows:
            raise RuntimeError(
                f"{spec.table}: expected {spec.rows} rows, got {len(rows)}"
            )
        digest = _row_digest(rows, spec.columns)
        if digest != spec.digest:
            raise RuntimeError(
                f"{spec.table}: row digest changed: {digest}"
            )
        if reader.unresolved:
            raise RuntimeError(
                f"{spec.table}: unexpected string references"
            )
        ids = [int(row["id"]) for row in rows]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"{spec.table}: duplicate native IDs")

        results[spec.table] = {
            "spec": spec,
            "rows": rows,
            "digest": digest,
            "header": header,
            "start": start,
            "done": cursor,
            "advertised_rows": advertised_rows,
            "x64": left,
            "x86": right,
        }

    buffs = results["item_grade_buffs"]["rows"]
    if {int(row["item_grade_id"]) for row in buffs} != set(range(13)):
        raise RuntimeError("item_grade_buffs does not cover grades 0..12")
    if {int(row["num_pieces"]) for row in buffs} != {1, 2, 3, 4}:
        raise RuntimeError("item_grade_buffs num_pieces domain changed")
    zero_rows = [
        row
        for row in buffs
        if int(row["item_id"]) == 0 or int(row["buff_id"]) == 0
    ]
    if len(zero_rows) != 64 or any(
        bool(int(row["item_id"])) != bool(int(row["buff_id"]))
        for row in zero_rows
    ):
        raise RuntimeError("item_grade_buffs zero-endpoint rows changed")

    distributions = results["item_grade_distributions"]["rows"]
    if {int(row["id"]) for row in distributions} != set(range(1, 51)):
        raise RuntimeError("item_grade_distributions ID domain changed")
    if any(
        sum(int(row[f"weight_{grade_id}"]) for grade_id in range(13))
        != 100
        for row in distributions
    ):
        raise RuntimeError("item_grade_distributions weights no longer sum to 100")

    skills = results["item_grade_skills"]["rows"]
    if {int(row["id"]) for row in skills} != set(range(8, 16)):
        raise RuntimeError("item_grade_skills ID domain changed")
    if {int(row["item_grade_id"]) for row in skills} != set(range(5, 13)):
        raise RuntimeError("item_grade_skills grade domain changed")

    return {
        "results": results,
        "tables": len(results),
        "rows": sum(len(value["rows"]) for value in results.values()),
        "item_grade_buff_zero_endpoint_rows": len(zero_rows),
        "item_grade_distribution_positive_weights": sum(
            int(row[f"weight_{grade_id}"]) > 0
            for row in distributions
            for grade_id in range(13)
        ),
        "x86_x64_layout_parity": True,
    }
