from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any


QUEST_NAME_KIND_LABELS = {
    1: "journal_subtitle",
    2: "journal_progress_title",
    3: "journal_summary",
}

QUEST_CONTEXT_TEXT_KIND_LABELS = {
    1: "context_summary",
    2: "context_body",
    3: "context_accept_text",
    4: "context_report_text",
    5: "media_fixture",
}

QUEST_NAME_KIND_COUNTS = {1: 764, 2: 108, 3: 801}
QUEST_CONTEXT_TEXT_KIND_COUNTS = {
    1: 36,
    2: 10,
    3: 698,
    4: 173,
    5: 1,
}

QUEST_NAME_KIND_CONSUMERS = {
    1: {
        "api": "GetQuestJournalSubTitleByType",
        "x64": "FUN_39770aa0",
        "x86": "FUN_397a63d0",
    },
    2: {
        "api": "GetQuestJournalProgTitleByType",
        "x64": "FUN_39770c30",
        "x86": "FUN_397a65c0",
    },
    3: {
        "api": "native_journal_summary_builder",
        "x64": "FUN_3977c850",
        "x86": "FUN_397b0860",
    },
}

QUEST_CONTEXT_TEXT_KIND_CONSUMERS = {
    1: {
        "api": "GetQuestContextSummary",
        "x64": "FUN_39772670",
        "x86": "FUN_397a7d80",
    },
    2: {
        "api": "GetQuestContextBody",
        "x64": "FUN_397727b0",
        "x86": "FUN_397a7f90",
    },
    3: {
        "api": "GetQuestContextAcceptText",
        "x64": "FUN_397728f0",
        "x86": "FUN_397a81a0",
    },
    4: {
        "api": "GetQuestContextReportText",
        "x64": "FUN_39772a30",
        "x86": "FUN_397a83b0",
    },
}


def _caller_body(report: str, function_name: str) -> str:
    match = re.search(
        rf"CALLER_BEGIN\s+{re.escape(function_name)}\s+[0-9a-fA-F]+"
        rf"(?P<body>.*?)CALLER_END",
        report,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError(f"Missing scalar consumer {function_name}")
    return match.group("body")


def _positive_counts(
    rows: list[dict[str, Any]],
    column: str,
) -> Counter[int]:
    return Counter(
        int(row[column])
        for row in rows
        if isinstance(row.get(column), int)
        and not isinstance(row.get(column), bool)
        and int(row[column]) > 0
    )


def _assert_api_binding(
    api_report: str,
    api_name: str,
    function_name: str,
) -> None:
    pattern = re.compile(
        rf"uStack_60\s*=\s*{re.escape(function_name)}\s*;"
        rf".{{0,300}}local_c8\s*=\s*\"{re.escape(api_name)}\"\s*;",
        re.DOTALL,
    )
    if pattern.search(api_report) is None:
        raise RuntimeError(
            f"Missing native API binding {api_name} -> {function_name}"
        )


def _assert_x64_name_kind(body: str, native_id: int) -> None:
    if re.search(rf"\+\s*0xc\)\s*==\s*{native_id}\b", body) is None:
        raise RuntimeError(f"x64 quest_name_kind {native_id} comparison missing")


def _assert_x86_name_kind(body: str, native_id: int) -> None:
    if re.search(rf"\)\[2\]\s*(?:==|!=)\s*{native_id}\b", body) is None:
        raise RuntimeError(f"x86 quest_name_kind {native_id} comparison missing")


def _assert_x64_context_kind(body: str, native_id: int) -> None:
    if re.search(
        rf"\*\(int\s*\*\)\*puVar\d+\s*==\s*{native_id}\b",
        body,
    ) is None:
        raise RuntimeError(
            f"x64 quest_context_text_kind {native_id} comparison missing"
        )


def _assert_x86_context_kind(body: str, native_id: int) -> None:
    if re.search(
        rf"\*\(int\s*\*\)\*local_\w+\s*==\s*{native_id}\b",
        body,
    ) is None:
        raise RuntimeError(
            f"x86 quest_context_text_kind {native_id} comparison missing"
        )


def _report_caller_count(report: str) -> int:
    match = re.search(r"^CALLER_COUNT\s+(\d+)\s*$", report, re.MULTILINE)
    if match is None:
        raise RuntimeError("Filtered-caller report lacks CALLER_COUNT")
    return int(match.group(1))


def audit_quest_text_kind_domains(
    decoded: dict[str, Any],
    *,
    native_sql_tables: set[str],
    api_x64_path: Path,
    consumers_x64_path: Path,
    consumers_x86_path: Path,
) -> dict[str, dict[str, Any]]:
    api_x64 = api_x64_path.read_text(encoding="utf-8")
    consumers_x64 = consumers_x64_path.read_text(encoding="utf-8")
    consumers_x86 = consumers_x86_path.read_text(encoding="utf-8")

    if "TARGET\tFUN_399c2190\t399c2190" not in consumers_x64:
        raise RuntimeError("x64 quest-context accessor target changed")
    if "TARGET\tFUN_39ba2020\t39ba2020" not in consumers_x86:
        raise RuntimeError("x86 quest-context accessor target changed")
    x64_caller_count = _report_caller_count(consumers_x64)
    x86_caller_count = _report_caller_count(consumers_x86)
    if (x64_caller_count, x86_caller_count) != (186, 192):
        raise RuntimeError(
            "Quest-context accessor caller inventory changed: "
            f"{x64_caller_count}/{x86_caller_count}"
        )

    for native_id, consumer in sorted(QUEST_NAME_KIND_CONSUMERS.items()):
        x64_body = _caller_body(consumers_x64, consumer["x64"])
        x86_body = _caller_body(consumers_x86, consumer["x86"])
        _assert_x64_name_kind(x64_body, native_id)
        _assert_x86_name_kind(x86_body, native_id)
        if native_id in {1, 2}:
            _assert_api_binding(
                api_x64,
                str(consumer["api"]),
                str(consumer["x64"]),
            )
        elif '"summary"' not in x64_body or '"summary"' not in x86_body:
            raise RuntimeError("Native quest_name_kind 3 summary sink changed")

    for native_id, consumer in sorted(
        QUEST_CONTEXT_TEXT_KIND_CONSUMERS.items()
    ):
        x64_body = _caller_body(consumers_x64, consumer["x64"])
        x86_body = _caller_body(consumers_x86, consumer["x86"])
        _assert_x64_context_kind(x64_body, native_id)
        _assert_x86_context_kind(x86_body, native_id)
        _assert_api_binding(
            api_x64,
            str(consumer["api"]),
            str(consumer["x64"]),
        )

    name_counts = _positive_counts(
        decoded["quest_names"].rows,
        "quest_name_kind_id",
    )
    context_counts = _positive_counts(
        decoded["quest_context_texts"].rows,
        "quest_context_text_kind_id",
    )
    if name_counts != Counter(QUEST_NAME_KIND_COUNTS):
        raise RuntimeError(f"quest_name_kind counts changed: {dict(name_counts)}")
    if context_counts != Counter(QUEST_CONTEXT_TEXT_KIND_COUNTS):
        raise RuntimeError(
            "quest_context_text_kind counts changed: "
            f"{dict(context_counts)}"
        )
    for owner_table in ("quest_name_kinds", "quest_context_text_kinds"):
        if owner_table in native_sql_tables:
            raise RuntimeError(
                f"Inline scalar domain gained an owner table: {owner_table}"
            )

    media_rows = [
        row
        for row in decoded["quest_context_texts"].rows
        if row.get("quest_context_text_kind_id") == 5
    ]
    if media_rows != [
        {
            "id": 1483,
            "quest_context_text_kind_id": 5,
            "quest_context_id": 598,
            "text": "문장들 - media",
        }
    ]:
        raise RuntimeError(f"Native media fixture changed: {media_rows!r}")
    if re.search(r"==\s*5\b", consumers_x64) is not None:
        raise RuntimeError("x64 gained a dedicated context-text kind 5 consumer")
    if re.search(r"==\s*5\b", consumers_x86) is not None:
        raise RuntimeError("x86 gained a dedicated context-text kind 5 consumer")

    return {
        "quest_name_kind": {
            "domain_type": "inline_scalar_enum",
            "ids": sorted(QUEST_NAME_KIND_LABELS),
            "labels": dict(QUEST_NAME_KIND_LABELS),
            "counts": {
                str(key): value
                for key, value in sorted(QUEST_NAME_KIND_COUNTS.items())
            },
            "references": sum(QUEST_NAME_KIND_COUNTS.values()),
            "source_table": "quest_names",
            "source_column": "quest_name_kind_id",
            "loader_x64": "FUN_399e2620",
            "loader_x86": "FUN_39c4dcb0",
            "consumers": QUEST_NAME_KIND_CONSUMERS,
            "owner_query_absent": True,
            "architecture_parity": True,
            "semantic_label_state": "confirmed",
        },
        "quest_context_text_kind": {
            "domain_type": "inline_scalar_enum",
            "ids": sorted(QUEST_CONTEXT_TEXT_KIND_LABELS),
            "labels": dict(QUEST_CONTEXT_TEXT_KIND_LABELS),
            "counts": {
                str(key): value
                for key, value in sorted(
                    QUEST_CONTEXT_TEXT_KIND_COUNTS.items()
                )
            },
            "references": sum(QUEST_CONTEXT_TEXT_KIND_COUNTS.values()),
            "source_table": "quest_context_texts",
            "source_column": "quest_context_text_kind_id",
            "loader_x64": "FUN_399e2380",
            "loader_x86": "FUN_39c4da90",
            "consumers": QUEST_CONTEXT_TEXT_KIND_CONSUMERS,
            "owner_query_absent": True,
            "architecture_parity": True,
            "semantic_label_state": "confirmed_except_dormant_fixture",
            "dormant_values": [5],
            "negative_consumer_evidence": {
                "value": 5,
                "x64_accessor_callers": x64_caller_count,
                "x86_accessor_callers": x86_caller_count,
                "dedicated_comparisons": 0,
                "native_fixture": media_rows[0],
                "consumer_state": "not_applicable",
            },
        },
    }
