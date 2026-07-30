from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


EXPECTED_TRACE = {
    "x64": {
        "accessor": "FUN_399e1040",
        "field_offset": "0x28",
        "callers": 61,
        "forwarded_calls": 43,
        "helpers": 10,
    },
    "x86": {
        "accessor": "FUN_39c22de0",
        "field_offset": "0x20",
        "callers": 60,
        "forwarded_calls": 40,
        "helpers": 8,
    },
}

NPC_AI_CANDIDATES = {
    3: "follow_path",
    6: "run_command_set",
}


def _required(text: str, pattern: str, reason: str) -> None:
    if re.search(pattern, text, re.MULTILINE | re.DOTALL) is None:
        raise RuntimeError(reason)


def _trace_summary(
    path: Path,
    *,
    architecture: str,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    expected = EXPECTED_TRACE[architecture]
    _required(
        text,
        rf"^ACCESSOR\s+{expected['accessor']}\s",
        f"{architecture} npc_ai accessor changed",
    )
    _required(
        text,
        rf"^FIELD_OFFSET\s+{expected['field_offset']}$",
        f"{architecture} npc_ai field offset changed",
    )

    def value(name: str) -> int:
        match = re.search(rf"^{name}\s+(\d+)$", text, re.MULTILINE)
        if match is None:
            raise RuntimeError(f"{architecture} npc_ai trace lost {name}")
        return int(match.group(1))

    summary = {
        "accessor": expected["accessor"],
        "field_offset": expected["field_offset"],
        "caller_count": value("CALLER_COUNT"),
        "field_loads": value("FIELD_LOADS"),
        "forwarded_calls": value("FORWARDED_CALLS"),
        "decompile_failures": value("DECOMPILE_FAILURES"),
    }
    if summary != {
        "accessor": expected["accessor"],
        "field_offset": expected["field_offset"],
        "caller_count": expected["callers"],
        "field_loads": 0,
        "forwarded_calls": expected["forwarded_calls"],
        "decompile_failures": 0,
    }:
        raise RuntimeError(
            f"{architecture} npc_ai field trace changed: {summary}"
        )
    return summary


def _helper_summary(
    path: Path,
    *,
    architecture: str,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    functions = re.findall(
        r"^=====\s+([0-9a-fA-F]+)\s+(FUN_[0-9a-fA-F]+)\s+=====$",
        text,
        re.MULTILINE,
    )
    expected = EXPECTED_TRACE[architecture]["helpers"]
    if len(functions) != expected:
        raise RuntimeError(
            f"{architecture} npc_ai forwarded helper count changed: "
            f"{len(functions)}"
        )
    return {
        "functions": [name for _, name in functions],
        "function_count": len(functions),
        "decompile_failures": len(
            re.findall(r"DECOMPILE FAILED", text, re.IGNORECASE)
        ),
        "inspection_state": "confirmed_no_npc_ai_field_read",
    }


def _raw_vector_summary(
    path: Path,
    *,
    architecture: str,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if architecture == "x64":
        _required(
            text,
            r"^scalar=0x14228 functions=2$",
            "x64 quest component raw-vector reference set changed",
        )
        _required(
            text,
            r"lVar14\s*=\s*uVar13\s*\*\s*0xd0\s*\+\s*"
            r"\*\(longlong \*\)\(param_2 \+ 0x14228\);",
            "x64 quest context linker lost component stride",
        )
        _required(
            text,
            r"uVar6\s*=\s*\*\(uint \*\)\(lVar14 \+ 0x34\);",
            "x64 quest context linker lost quest_context_id read",
        )
        if re.search(r"\(lVar14 \+ 0x28\)", text):
            raise RuntimeError("x64 raw-vector path now reads npc_ai_id")
        return {
            "manager_vector_offset": "0x14228",
            "struct_stride": "0xd0",
            "reference_functions": 2,
            "linker": "FUN_399f5cb0",
            "linker_read_offset": "0x34",
            "npc_ai_read_offset": "0x28",
            "npc_ai_reads": 0,
        }

    _required(
        text,
        r"^scalar=0xfa7c functions=1$",
        "x86 quest component raw-vector reference set changed",
    )
    _required(
        text,
        r"\*\(int \*\)\(param_2 \+ 0xfa7c\) \+ 0x2c \+ iVar11",
        "x86 quest context linker lost quest_context_id read",
    )
    if re.search(r"\+ 0x20 \+ iVar11", text):
        raise RuntimeError("x86 raw-vector path now reads npc_ai_id")
    return {
        "manager_vector_offset": "0xfa7c",
        "struct_stride": "0x80",
        "reference_functions": 1,
        "linker": "FUN_39c66050",
        "linker_read_offset": "0x2c",
        "npc_ai_read_offset": "0x20",
        "npc_ai_reads": 0,
    }


def _copy_layout_summary(
    *,
    x64_path: Path,
    x86_path: Path,
) -> dict[str, Any]:
    x64 = x64_path.read_text(encoding="utf-8")
    x86 = x86_path.read_text(encoding="utf-8")
    _required(
        x64,
        r"FUNCTION_BEGIN\s+FUN_399e1670\s+399e1670"
        r".*?param_1\[10\]\s*=\s*param_2\[10\];",
        "x64 quest component copy lost npc_ai_id slot",
    )
    _required(
        x86,
        r"function=FUN_39c2f380"
        r".*?param_1\[8\]\s*=\s*param_2\[8\];",
        "x86 quest component copy lost npc_ai_id slot",
    )
    return {
        "x64": {
            "copy": "FUN_399e1670",
            "struct_size": "0xd0",
            "field_offset": "0x28",
            "typed_slot": "uint32[10]",
        },
        "x86": {
            "copy": "FUN_39c2f380",
            "struct_size": "0x80",
            "field_offset": "0x20",
            "typed_slot": "uint32[8]",
        },
        "architecture_parity": True,
    }


def _script_stub_summary(
    *,
    bindings_x64_path: Path,
    bindings_x86_path: Path,
    stubs_x64_path: Path,
    stubs_x86_path: Path,
) -> dict[str, Any]:
    bindings_x64 = bindings_x64_path.read_text(encoding="utf-8")
    bindings_x86 = bindings_x86_path.read_text(encoding="utf-8")
    stubs_x64 = stubs_x64_path.read_text(encoding="utf-8")
    stubs_x86 = stubs_x86_path.read_text(encoding="utf-8")
    bindings = {
        "NpcFollowUnit": {
            "x64": "FUN_3979da60",
            "x86": "FUN_397cfd40",
        },
        "NpcFollowPath": {
            "x64": "FUN_3979d3d0",
            "x86": "FUN_397cf720",
        },
        "NpcOnEndedFollowPath": {
            "x64": "FUN_3979d400",
            "x86": "FUN_397cf750",
        },
    }
    for name, functions in bindings.items():
        _required(
            bindings_x64,
            rf'local_88\s*=\s*"{name}";.*?local_98\s*=\s*'
            rf"{functions['x64']}|"
            rf"local_98\s*=\s*{functions['x64']}.*?"
            rf'local_88\s*=\s*"{name}";',
            f"x64 script binding changed for {name}",
        )
        _required(
            bindings_x86,
            rf'local_48\s*=\s*"{name}";.*?local_18\s*=\s*'
            rf"{functions['x86']}|"
            rf"local_18\s*=\s*{functions['x86']}.*?"
            rf'local_48\s*=\s*"{name}";',
            f"x86 script binding changed for {name}",
        )
        for architecture, text in (("x64", stubs_x64), ("x86", stubs_x86)):
            _required(
                text,
                rf"FUNCTION_BEGIN\s+{functions[architecture]}\s+"
                rf"{functions[architecture].removeprefix('FUN_')}"
                rf".*?ScriptBindUnit::{name}\(\) we don\\?'t support "
                rf"this for client!",
                f"{architecture} client-only stub changed for {name}",
            )
    return {
        "architecture_parity": True,
        "bindings": bindings,
        "client_implementation_state": "explicitly_unsupported",
        "authority_inference": "server_side_behavior",
    }


def _surface_summary(path: Path) -> dict[str, Any]:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("format") != "AA8_NPC_AI_SURFACE_SNAPSHOT_V1":
        raise RuntimeError("npc_ai surface snapshot format changed")
    scans = list(snapshot["scans"])
    binary_scans = [
        scan for scan in scans if scan["kind"] == "client_binary"
    ]
    if len(binary_scans) != 2:
        raise RuntimeError("npc_ai binary scope lost one architecture")
    for scan in binary_scans:
        x2game = [
            match
            for match in scan["matches"]
            if str(match["path"]).lower() == "x2game.dll"
        ]
        if len(x2game) != 1:
            raise RuntimeError(
                f"npc_ai x2game surface missing from {scan['root']}"
            )
        required = {
            "npc_ai",
            "npcai",
            "ai_command_set",
            "aicommandset",
            "npcfollowpath",
            "npconendedfollowpath",
            "npcfollowunit",
        }
        if not required.issubset(set(x2game[0]["tokens"])):
            raise RuntimeError("npc_ai x2game tokens changed")
    lua_scans = {
        str(scan["kind"]): scan
        for scan in scans
        if str(scan["kind"]).startswith("gamepak_lua")
    }
    required_lua = {
        "ai/behaviors/x2/common/follow_path.lua",
        "ai/behaviors/x2/common/follow_unit.lua",
        "ai/behaviors/x2/common/run_command_set.lua",
        "ai/logic/x2ai_command_set.lua",
    }
    for kind, scan in lua_scans.items():
        paths = {str(match["path"]) for match in scan["matches"]}
        if not required_lua.issubset(paths):
            raise RuntimeError(f"{kind} npc_ai Lua closure changed")
    xml_scan = next(
        scan for scan in scans if scan["kind"] == "gamepak_xml"
    )
    return {
        "format": snapshot["format"],
        "tokens": snapshot["tokens"],
        "totals": snapshot["totals"],
        "binary_architectures": len(binary_scans),
        "binary_matches": {
            str(scan["root"]): [
                {
                    "path": match["path"],
                    "tokens": match["tokens"],
                }
                for match in scan["matches"]
            ]
            for scan in binary_scans
        },
        "lua_match_counts": {
            kind: len(scan["matches"])
            for kind, scan in sorted(lua_scans.items())
        },
        "xml_match_count": len(xml_scan["matches"]),
        "xml_paths": [
            match["path"] for match in xml_scan["matches"]
        ],
    }


def audit_npc_ai_frontier(
    *,
    rows: list[dict[str, Any]],
    component_copy_x64_path: Path,
    component_copy_x86_path: Path,
    field_trace_x64_path: Path,
    field_trace_x86_path: Path,
    forwarded_helpers_x64_path: Path,
    forwarded_helpers_x86_path: Path,
    raw_vector_x64_path: Path,
    raw_vector_x86_path: Path,
    lua_bindings_x64_path: Path,
    lua_bindings_x86_path: Path,
    script_stubs_x64_path: Path,
    script_stubs_x86_path: Path,
    surface_snapshot_path: Path,
) -> dict[str, Any]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["npc_ai_id"]), []).append(row)
    if sorted(grouped) != [1, 2, 3, 4, 6]:
        raise RuntimeError(f"npc_ai membership changed: {sorted(grouped)}")
    path_rows = grouped[3]
    if not all(int(row["ai_path_type_id"]) > 0 for row in path_rows):
        raise RuntimeError("npc_ai 3 lost its native path-type invariant")
    command_rows = grouped[6]
    if not all(
        int(row["ai_command_set_id"]) > 0 for row in command_rows
    ):
        raise RuntimeError("npc_ai 6 lost its native command-set invariant")
    traces = {
        "x64": _trace_summary(field_trace_x64_path, architecture="x64"),
        "x86": _trace_summary(field_trace_x86_path, architecture="x86"),
    }
    helpers = {
        "x64": _helper_summary(
            forwarded_helpers_x64_path,
            architecture="x64",
        ),
        "x86": _helper_summary(
            forwarded_helpers_x86_path,
            architecture="x86",
        ),
    }
    if any(value["decompile_failures"] for value in helpers.values()):
        raise RuntimeError("npc_ai forwarded helper decompilation failed")
    raw_vectors = {
        "x64": _raw_vector_summary(
            raw_vector_x64_path,
            architecture="x64",
        ),
        "x86": _raw_vector_summary(
            raw_vector_x86_path,
            architecture="x86",
        ),
    }
    return {
        "labels": {},
        "semantic_candidates": dict(NPC_AI_CANDIDATES),
        "semantic_label_state": (
            "unknown_client_field_confirmed_behavior_server_side"
        ),
        "architecture_parity": True,
        "unresolved_semantic_ids": [1, 2, 3, 4, 6],
        "client_consumer_state": "confirmed_unconsumed_in_traced_paths",
        "behavior_authority_state": "corroborated_server_side",
        "domain_properties": {
            "client_field_present": {
                "value": True,
                "state": "confirmed",
            },
            "client_direct_field_loads": {
                "value": 0,
                "state": "confirmed",
            },
            "client_behavior_implementation": {
                "value": "explicitly_unsupported",
                "state": "confirmed",
            },
            "behavior_authority": {
                "value": "server_side",
                "state": "corroborated",
            },
        },
        "correlations": {
            "3": {
                "candidate": NPC_AI_CANDIDATES[3],
                "rows": len(path_rows),
                "all_have_positive_ai_path_type_id": True,
                "nonempty_ai_path_name": sum(
                    bool(str(row["ai_path_name"])) for row in path_rows
                ),
            },
            "6": {
                "candidate": NPC_AI_CANDIDATES[6],
                "rows": len(command_rows),
                "all_have_positive_ai_command_set_id": True,
            },
        },
        "negative_consumer_evidence": {
            "field_layout": _copy_layout_summary(
                x64_path=component_copy_x64_path,
                x86_path=component_copy_x86_path,
            ),
            "accessor_traces": traces,
            "forwarded_helpers": helpers,
            "raw_vectors": raw_vectors,
            "script_stubs": _script_stub_summary(
                bindings_x64_path=lua_bindings_x64_path,
                bindings_x86_path=lua_bindings_x86_path,
                stubs_x64_path=script_stubs_x64_path,
                stubs_x86_path=script_stubs_x86_path,
            ),
            "surface_snapshot": _surface_summary(surface_snapshot_path),
        },
    }
