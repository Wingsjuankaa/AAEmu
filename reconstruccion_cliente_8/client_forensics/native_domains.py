from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


QUEST_DETAIL_LABELS = {
    1: "normal",
    2: "main",
    3: "saga",
    4: "tutorial",
    5: "hidden",
    7: "daily",
    8: "livelihood",
    9: "group",
    10: "daily_hunt",
    11: "daily_livelihood",
    12: "daily_group",
    13: "today",
    14: "hero",
    15: "weekly",
    16: "expedition",
}

QUEST_DETAIL_FUNCTIONS = {
    "x64": "FUN_398764f0",
    "x86": "FUN_398ece80",
}

SCALAR_DOMAIN_SPECS = {
    "quest_component_text_kind": {
        "source_table": "quest_component_texts",
        "source_column": "quest_component_text_kind_id",
        "expected_counts": {4: 13_525, 5: 4, 6: 2},
        "loader_x64": "FUN_399f2f00",
        "semantic_state": "unknown",
    },
    "chat_bubble_kind": {
        "source_table": "quest_chat_bubbles",
        "source_column": "chat_bubble_kind_id",
        "expected_counts": {1: 25_192, 2: 151, 3: 596},
        "loader_x64": "FUN_399e1f80",
        "semantic_state": "unknown",
    },
    "npc_ai": {
        "source_table": "quest_components",
        "source_column": "npc_ai_id",
        "expected_counts": {1: 32_139, 2: 3, 3: 18, 4: 4, 6: 27},
        "loader_x64": "FUN_399f3a80",
        "semantic_state": "unknown",
    },
}


def _function_body(report: str, function_name: str) -> str:
    pattern = re.compile(
        rf"FUNCTION_BEGIN\s+{re.escape(function_name)}\s+[0-9a-fA-F]+"
        rf"(?P<body>.*?)FUNCTION_END",
        re.DOTALL,
    )
    match = pattern.search(report)
    if match is None:
        raise RuntimeError(f"Missing native function {function_name}")
    return match.group("body")


def parse_quest_detail_labels(path: Path, architecture: str) -> dict[int, str]:
    function_name = QUEST_DETAIL_FUNCTIONS[architecture]
    body = _function_body(path.read_text(encoding="utf-8"), function_name)
    labels: dict[int, str] = {}
    for raw_value, label in re.findall(
        r'case\s+(0x[0-9a-fA-F]+|\d+):\s*return\s+"([^"]+)";',
        body,
    ):
        labels[int(raw_value, 0)] = label
    if labels != QUEST_DETAIL_LABELS:
        raise RuntimeError(
            f"Native quest_detail mapping changed for {architecture}: {labels}"
        )
    if 'return "invalid quest_detail";' not in body:
        raise RuntimeError(
            f"Native quest_detail default sentinel missing for {architecture}"
        )
    return labels


def audit_quest_detail_parity(
    x64_report: Path,
    x86_report: Path,
) -> dict[str, Any]:
    x64 = parse_quest_detail_labels(x64_report, "x64")
    x86 = parse_quest_detail_labels(x86_report, "x86")
    if x64 != x86:
        raise RuntimeError("quest_detail x86/x64 mappings disagree")
    return {
        "architecture_parity": True,
        "invalid_sentinel": 6,
        "labels": {str(key): value for key, value in sorted(x64.items())},
        "x64_consumer": QUEST_DETAIL_FUNCTIONS["x64"],
        "x86_consumer": QUEST_DETAIL_FUNCTIONS["x86"],
    }


def _positive_integer_counts(
    rows: Iterable[dict[str, Any]],
    column: str,
) -> Counter[int]:
    return Counter(
        int(row[column])
        for row in rows
        if isinstance(row.get(column), int)
        and not isinstance(row.get(column), bool)
        and int(row[column]) > 0
    )


def audit_scalar_domains(
    decoded: dict[str, Any],
    *,
    native_sql_tables: set[str],
) -> dict[str, dict[str, Any]]:
    audits: dict[str, dict[str, Any]] = {}
    for kind, spec in sorted(SCALAR_DOMAIN_SPECS.items()):
        table = str(spec["source_table"])
        column = str(spec["source_column"])
        counts = _positive_integer_counts(decoded[table].rows, column)
        expected = Counter(spec["expected_counts"])
        if counts != expected:
            raise RuntimeError(
                f"Native scalar domain changed for {kind}: {dict(counts)}"
            )
        owner_table = f"{kind}s"
        if owner_table in native_sql_tables:
            raise RuntimeError(
                f"{kind} now has an authoritative SQL owner table: {owner_table}"
            )
        audits[kind] = {
            "domain_type": "inline_scalar_enum",
            "ids": sorted(counts),
            "counts": {str(key): value for key, value in sorted(counts.items())},
            "references": sum(counts.values()),
            "source_table": table,
            "source_column": column,
            "loader_x64": spec["loader_x64"],
            "semantic_label_state": spec["semantic_state"],
            "owner_query_absent": True,
        }
    return audits


def quest_detail_reference_counts(
    decoded: dict[str, Any],
) -> Counter[int]:
    counts = _positive_integer_counts(
        decoded["quest_contexts"].rows,
        "detail_id",
    )
    unexpected = set(counts) - set(QUEST_DETAIL_LABELS)
    if unexpected:
        raise RuntimeError(
            f"Unexpected quest_detail values in native rows: {sorted(unexpected)}"
        )
    return counts
