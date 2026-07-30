from __future__ import annotations

import re
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .npc_ai import NPC_AI_CANDIDATES, audit_npc_ai_frontier


CHAT_BUBBLE_KIND_LABELS = {
    1: "normal",
    2: "think",
    3: "system",
}

CHAT_BUBBLE_KIND_CONSTANTS = {
    1: "CBK_NORMAL",
    2: "CBK_THINK",
    3: "CBK_SYSTEM",
}

QUEST_COMPONENT_TEXT_KIND_LABELS = {
    4: "summary",
    5: "body",
    6: "doodad_phase_message",
}

QUEST_COMPONENT_TEXT_KIND_CONSUMERS = {
    4: {
        "x64": [
            "FUN_39774350",
            "FUN_39776910",
            "FUN_397786a0",
            "FUN_3977c850",
            "FUN_39773130",
        ],
        "x86": [
            "FUN_397aa1d0",
            "FUN_397ac9a0",
            "FUN_397ae2a0",
            "FUN_397b0860",
            "FUN_397a87a0",
        ],
        "api": "summary",
        "sinks": ["summary"],
    },
    5: {
        "x64": ["FUN_39773260"],
        "x86": ["FUN_397a8a80"],
        "api": "body",
        "sinks": ["body"],
    },
    6: {
        "x64": ["FUN_395eaf50"],
        "x86": ["FUN_396166b0"],
        "api": "DOODAD_PHASE_MSG",
        "event_id": 0x102,
        "sinks": ["FireUIEvent", "DOODAD_PHASE_MSG"],
    },
}

def _caller_body(report: str, function_name: str) -> str:
    match = re.search(
        rf"CALLER_DECOMPILE_BEGIN\s+{re.escape(function_name)}\s+[0-9a-fA-F]+"
        rf"(?P<body>.*?)CALLER_DECOMPILE_END",
        report,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError(f"Missing component consumer {function_name}")
    return match.group("body")


def _rows(decoded: dict[str, Any], table: str) -> list[dict[str, Any]]:
    return list(decoded[table].rows)


def _helper_body(report: str, function_name: str) -> str:
    match = re.search(
        rf"=====\s+[0-9a-fA-F]+\s+{re.escape(function_name)}\s+====="
        rf"(?P<body>.*?)(?=\n=====\s+[0-9a-fA-F]+|\Z)",
        report,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError(f"Missing forwarded helper {function_name}")
    return match.group("body")


def _assert_token(report: str, token: str, description: str) -> None:
    if token not in report:
        raise RuntimeError(f"Missing {description}: {token}")


def _audit_chat_bubble_kind(
    *,
    enum_x64: str,
    enum_x86: str,
    lua_chat_bubble: str,
    lua_directing: str,
) -> dict[str, Any]:
    for native_id, constant in sorted(CHAT_BUBBLE_KIND_CONSTANTS.items()):
        x64_pattern = (
            rf'FUN_396ec170\(param_1,"{re.escape(constant)}",{native_id}\);'
        )
        x86_pattern = (
            rf'FUN_390f7aa0\("{re.escape(constant)}",{native_id}\);'
        )
        if re.search(x64_pattern, enum_x64) is None:
            raise RuntimeError(f"Missing x64 binding for {constant}")
        if re.search(x86_pattern, enum_x86) is None:
            raise RuntimeError(f"Missing x86 binding for {constant}")
    for constant in CHAT_BUBBLE_KIND_CONSTANTS.values():
        if constant not in lua_chat_bubble:
            raise RuntimeError(f"Lua chat bubble consumer lost {constant}")
    for constant in ("CBK_THINK", "CBK_SYSTEM"):
        if constant not in lua_directing:
            raise RuntimeError(f"Quest directing consumer lost {constant}")
    return {
        "labels": dict(CHAT_BUBBLE_KIND_LABELS),
        "constants": dict(CHAT_BUBBLE_KIND_CONSTANTS),
        "semantic_label_state": "confirmed",
        "architecture_parity": True,
        "unresolved_semantic_ids": [],
        "consumers": {
            native_id: {
                "api": constant,
                "x64": "FUN_396ec170",
                "x86": "FUN_390f7aa0",
                "lua": [
                    "x2ui/chat/chatbubble.lua",
                    "x2ui/questcontext/quest_context_directing.lua",
                ],
            }
            for native_id, constant in sorted(
                CHAT_BUBBLE_KIND_CONSTANTS.items()
            )
        },
    }


def _audit_component_text_kind(
    *,
    rows: list[dict[str, Any]],
    component_rows: list[dict[str, Any]],
    quest_rows: list[dict[str, Any]],
    context_x64: str,
    context_x86: str,
    helpers_x64: str,
    helpers_x86: str,
    vector_trace_x64: str,
    vector_trace_x86: str,
    data_x64: str,
    data_x86: str,
    event_core_x64: str,
    event_core_x86: str,
    enum_x64: str,
    enum_x86: str,
    surface_snapshot: dict[str, Any],
) -> dict[str, Any]:
    for architecture, report in (
        ("x64", context_x64),
        ("x86", context_x86),
    ):
        expected = QUEST_COMPONENT_TEXT_KIND_CONSUMERS[4][architecture][:4]
        for function_name in expected:
            body = _caller_body(report, function_name)
            if re.search(r"\*\(int \*\)\*\w+\s*==\s*4\b", body) is None:
                raise RuntimeError(
                    f"{architecture} value-4 text comparison missing in "
                    f"{function_name}"
                )
        comparisons = Counter(
            int(value)
            for value in re.findall(
                r"\*\(int \*\)\*\w+\s*==\s*(\d+)\b",
                report,
            )
        )
        if comparisons != Counter({4: 4}):
            raise RuntimeError(
                f"{architecture} component text comparisons changed: "
                f"{dict(comparisons)}"
            )

    helper_specs = {
        "x64": {
            4: ("FUN_39773130", r"\*\(int \*\)\*\w+\s*==\s*4\b"),
            5: ("FUN_39773260", r"\*\(int \*\)\*\w+\s*==\s*5\b"),
            6: ("FUN_395eaf50", r"\*\(int \*\)\*\w+\s*==\s*6\b"),
        },
        "x86": {
            4: ("FUN_397a87a0", r"\*\(int \*\)\*\w+\s*==\s*4\b"),
            5: ("FUN_397a8a80", r"\*\(int \*\)\*\w+\s*==\s*5\b"),
            6: ("FUN_396166b0", r"\*\(int \*\)\*\w+\s*==\s*6\b"),
        },
    }
    helper_reports = {"x64": helpers_x64, "x86": helpers_x86}
    for architecture, specifications in helper_specs.items():
        for native_id, (function_name, pattern) in specifications.items():
            body = _helper_body(helper_reports[architecture], function_name)
            if re.search(pattern, body) is None:
                raise RuntimeError(
                    f"{architecture} kind {native_id} filter missing in "
                    f"{function_name}"
                )

    if "FUN_396c4be0(0x102" not in _helper_body(
        helpers_x64, "FUN_395eaf50"
    ):
        raise RuntimeError("x64 kind 6 UI event 0x102 dispatch changed")
    if "FUN_396fade0(0x102" not in _helper_body(
        helpers_x86, "FUN_396166b0"
    ):
        raise RuntimeError("x86 kind 6 UI event 0x102 dispatch changed")

    for report, architecture, accessor, offset, callers, forwarded in (
        (
            vector_trace_x64,
            "x64",
            "FUN_399e1040",
            "0x88",
            61,
            43,
        ),
        (
            vector_trace_x86,
            "x86",
            "FUN_39c22de0",
            "0x5c",
            60,
            40,
        ),
    ):
        for token in (
            "FORMAT\tAA8_ACCESSOR_FIELD_TRACE_V1",
            f"ACCESSOR\t{accessor}",
            f"FIELD_OFFSET\t{offset}",
            f"CALLER_COUNT\t{callers}",
            "FIELD_LOADS\t4",
            f"FORWARDED_CALLS\t{forwarded}",
            "DECOMPILE_FAILURES\t0",
        ):
            _assert_token(report, token, f"{architecture} vector trace")

    _assert_token(data_x64, "C_STRING\tbody", "x64 body field name")
    _assert_token(data_x86, "C_STRING\tbody", "x86 body field name")
    _assert_token(
        enum_x64,
        'FUN_390abfb0(&DAT_3acf9c20,"DOODAD_PHASE_MSG",0x10);',
        "x64 UI event 0x102 enum entry",
    )
    _assert_token(enum_x86, '"DOODAD_PHASE_MSG"', "x86 UI event enum entry")
    _assert_token(
        event_core_x64,
        '"FireUIEvent - %s",(&DAT_3acf9410)[lVar16]',
        "x64 indexed UI event dispatcher",
    )
    _assert_token(
        event_core_x86,
        '"FireUIEvent - %s",(&DAT_3a8eafc8)[param_1]',
        "x86 indexed UI event dispatcher",
    )

    fixture_rows = [
        row for row in rows if row["quest_component_text_kind_id"] == 5
    ]
    expected_fixture_tokens = {
        "start - Texts - body",
        "progress - Texts - body",
        "ready - Texts - body",
        "reward - Texts - body",
    }
    if {str(row["text"]) for row in fixture_rows} != expected_fixture_tokens:
        raise RuntimeError(
            f"Component text fixture rows changed: {fixture_rows!r}"
        )
    value6_rows = [
        row for row in rows if row["quest_component_text_kind_id"] == 6
    ]
    if len(value6_rows) != 2:
        raise RuntimeError(
            f"Component text kind 6 row set changed: {value6_rows!r}"
        )
    components = {
        int(row["id"]): int(row["quest_context_id"])
        for row in component_rows
    }
    quests = {int(row["id"]) for row in quest_rows}
    fixture_quests = {
        components[int(row["quest_component_id"])] for row in fixture_rows
    }
    value6_quests = {
        components[int(row["quest_component_id"])] for row in value6_rows
    }
    if fixture_quests != {598} or 598 not in quests:
        raise RuntimeError(
            f"Kind 5 fixture ownership changed: {fixture_quests!r}"
        )
    if value6_quests != {1421} or 1421 in quests:
        raise RuntimeError(
            f"Kind 6 orphan lifecycle changed: {value6_quests!r}"
        )

    if surface_snapshot.get("format") != (
        "AA8_COMPONENT_TEXT_SURFACE_SNAPSHOT_V1"
    ):
        raise RuntimeError("Unexpected component text surface snapshot format")
    totals = surface_snapshot.get("totals", {})
    if totals != {
        "bytes_scanned": 1_376_694_556,
        "files_scanned": 11_245,
        "matching_files": 11,
    }:
        raise RuntimeError(f"Component text surface totals changed: {totals!r}")
    matched_paths = {
        str(match["path"])
        for scan in surface_snapshot["scans"]
        for match in scan["matches"]
    }
    for required_path in (
        "x2game.dll",
        "globalui/chat/chat_msg_event.lua",
        "x2ui/centermessage/center_message_manager.lua",
        "x2ui/questcontext/quest_context.lua",
    ):
        if required_path not in matched_paths:
            raise RuntimeError(
                f"Component text surface missing {required_path}"
            )

    return {
        "labels": dict(QUEST_COMPONENT_TEXT_KIND_LABELS),
        "semantic_label_state": "confirmed",
        "architecture_parity": True,
        "unresolved_semantic_ids": [],
        "consumers": dict(QUEST_COMPONENT_TEXT_KIND_CONSUMERS),
        "collection_materialization": {
            "x64": {
                "raw_record_stride": 0x10,
                "raw_vector_offset": 0x13F88,
                "component_vector_offsets": [0x88, 0x90, 0x98],
                "loader": "FUN_399f3a80",
            },
            "x86": {
                "raw_record_stride": 0x0C,
                "raw_vector_offset": 0xF878,
                "component_vector_offsets": [0x5C, 0x60, 0x64],
                "loader": "FUN_39c64770",
            },
        },
        "consumer_evidence": {
            "x64_accessor_callers": 61,
            "x86_accessor_callers": 60,
            "direct_comparison_counts": {
                "x64": {"4": 4},
                "x86": {"4": 4},
            },
            "forwarded_helper_values": [4, 5, 6],
            "ui_event_id": 0x102,
            "ui_event": "DOODAD_PHASE_MSG",
            "surface_snapshot": surface_snapshot["totals"],
            "value5_native_fixtures": fixture_rows,
            "value6_native_rows": value6_rows,
        },
        "domain_properties": {
            "client_collection_materialization": {
                "value": "confirmed",
                "state": "confirmed",
            },
            "client_consumer_state": {
                "value": "confirmed",
                "state": "confirmed",
            },
        },
        "value_properties": {
            4: {
                "native_row_population_state": {
                    "value": "active_native_rows",
                    "state": "confirmed",
                }
            },
            5: {
                "native_row_population_state": {
                    "value": "ddcms_tutorial_fixture",
                    "state": "confirmed",
                },
                "owning_quest_id": {"value": 598, "state": "confirmed"},
            },
            6: {
                "native_row_population_state": {
                    "value": "orphaned_parent_context",
                    "state": "confirmed",
                },
                "owning_quest_id": {"value": 1421, "state": "confirmed"},
                "unresolved_text_reference_count": {
                    "value": sum(
                        str(row["text"]).startswith("<ref:")
                        for row in value6_rows
                    ),
                    "state": "confirmed",
                },
            },
        },
    }


def audit_inline_quest_semantics(
    decoded: dict[str, Any],
    *,
    enum_x64_path: Path,
    enum_x86_path: Path,
    component_context_x64_path: Path,
    component_context_x86_path: Path,
    component_copy_x64_path: Path,
    component_copy_x86_path: Path,
    npc_ai_field_trace_x64_path: Path,
    npc_ai_field_trace_x86_path: Path,
    npc_ai_forwarded_helpers_x64_path: Path,
    npc_ai_forwarded_helpers_x86_path: Path,
    npc_ai_raw_vector_x64_path: Path,
    npc_ai_raw_vector_x86_path: Path,
    npc_ai_lua_bindings_x64_path: Path,
    npc_ai_lua_bindings_x86_path: Path,
    npc_ai_script_stubs_x64_path: Path,
    npc_ai_script_stubs_x86_path: Path,
    npc_ai_surface_snapshot_path: Path,
    component_text_vector_trace_x64_path: Path,
    component_text_vector_trace_x86_path: Path,
    component_text_data_x64_path: Path,
    component_text_data_x86_path: Path,
    ui_event_core_x64_path: Path,
    ui_event_core_x86_path: Path,
    component_text_surface_snapshot_path: Path,
    lua64_root: Path,
) -> dict[str, dict[str, Any]]:
    enum_x64 = enum_x64_path.read_text(encoding="utf-8")
    enum_x86 = enum_x86_path.read_text(encoding="utf-8")
    context_x64 = component_context_x64_path.read_text(encoding="utf-8")
    context_x86 = component_context_x86_path.read_text(encoding="utf-8")
    helpers_x64 = npc_ai_forwarded_helpers_x64_path.read_text(encoding="utf-8")
    helpers_x86 = npc_ai_forwarded_helpers_x86_path.read_text(encoding="utf-8")
    lua_chat_bubble = (
        lua64_root / "x2ui" / "chat" / "chatbubble.lua"
    ).read_text(encoding="utf-8")
    lua_directing = (
        lua64_root
        / "x2ui"
        / "questcontext"
        / "quest_context_directing.lua"
    ).read_text(encoding="utf-8")

    return {
        "chat_bubble_kind": _audit_chat_bubble_kind(
            enum_x64=enum_x64,
            enum_x86=enum_x86,
            lua_chat_bubble=lua_chat_bubble,
            lua_directing=lua_directing,
        ),
        "quest_component_text_kind": _audit_component_text_kind(
            rows=_rows(decoded, "quest_component_texts"),
            component_rows=_rows(decoded, "quest_components"),
            quest_rows=_rows(decoded, "quest_contexts"),
            context_x64=context_x64,
            context_x86=context_x86,
            helpers_x64=helpers_x64,
            helpers_x86=helpers_x86,
            vector_trace_x64=component_text_vector_trace_x64_path.read_text(
                encoding="utf-8"
            ),
            vector_trace_x86=component_text_vector_trace_x86_path.read_text(
                encoding="utf-8"
            ),
            data_x64=component_text_data_x64_path.read_text(encoding="utf-8"),
            data_x86=component_text_data_x86_path.read_text(encoding="utf-8"),
            event_core_x64=ui_event_core_x64_path.read_text(encoding="utf-8"),
            event_core_x86=ui_event_core_x86_path.read_text(encoding="utf-8"),
            enum_x64=enum_x64,
            enum_x86=enum_x86,
            surface_snapshot=json.loads(
                component_text_surface_snapshot_path.read_text(
                    encoding="utf-8"
                )
            ),
        ),
        "npc_ai": audit_npc_ai_frontier(
            rows=_rows(decoded, "quest_components"),
            component_copy_x64_path=component_copy_x64_path,
            component_copy_x86_path=component_copy_x86_path,
            field_trace_x64_path=npc_ai_field_trace_x64_path,
            field_trace_x86_path=npc_ai_field_trace_x86_path,
            forwarded_helpers_x64_path=(
                npc_ai_forwarded_helpers_x64_path
            ),
            forwarded_helpers_x86_path=(
                npc_ai_forwarded_helpers_x86_path
            ),
            raw_vector_x64_path=npc_ai_raw_vector_x64_path,
            raw_vector_x86_path=npc_ai_raw_vector_x86_path,
            lua_bindings_x64_path=npc_ai_lua_bindings_x64_path,
            lua_bindings_x86_path=npc_ai_lua_bindings_x86_path,
            script_stubs_x64_path=npc_ai_script_stubs_x64_path,
            script_stubs_x86_path=npc_ai_script_stubs_x86_path,
            surface_snapshot_path=npc_ai_surface_snapshot_path,
        ),
    }
