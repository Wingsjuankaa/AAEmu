from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .quests import _parse_loader_layouts, _structural_headers
from .skills import SkillQuery, SkillResult
from .util import canonical_json
from .world_actors import CachedResultReader


WORLD_INTERACTION_SQL = (
    "SELECT wi_id, apply_expert, distance_sqrt, lp FROM wi_details"
)
WORLD_INTERACTION_CALL_INDEX = 611
WORLD_INTERACTION_HEADER_INDEX = 558
WORLD_INTERACTION_INVALID_ID = 95

# This is deliberately checked against the two decompilations on every build.
# It is a regression oracle, not an independent gameplay-data authority.
WORLD_INTERACTION_LABELS = {
    0: "looting",
    1: "cutdown",
    2: "seeding",
    3: "watering",
    4: "harvest",
    5: "remove",
    6: "cancel",
    7: "error",
    8: "check_water",
    9: "check_growth",
    10: "dig_terrain",
    11: "spray",
    12: "line_spray",
    13: "water_level",
    14: "summon_mine_spot",
    15: "dig_mine",
    16: "summon_cattle",
    17: "shearing",
    18: "feeding",
    19: "use",
    20: "butcher",
    21: "craft_start",
    22: "craft_act",
    23: "craft_info",
    24: "craft_get_item",
    25: "craft_cancel",
    26: "direct_loot",
    27: "hang",
    28: "binding",
    29: "summon_beanstalk",
    30: "give_quest",
    31: "summon_doodad",
    32: "craft_def_interaction",
    33: "mow",
    34: "complete_quest",
    35: "building",
    36: "dooring",
    37: "furniture_make",
    38: "rubber_process",
    39: "siege_weapon_make",
    40: "machinery_assemble",
    41: "tool_make",
    42: "lumber_process",
    43: "weapon_make",
    44: "tanning",
    45: "armor_make",
    46: "fodder_make",
    47: "dailyproduct_make",
    48: "stone_process",
    49: "archium_extract",
    50: "potion_make",
    51: "alchemy",
    52: "dye_purify",
    53: "cooking",
    54: "glassceramic_make",
    55: "oil_extract",
    56: "costume_make",
    57: "accessory_make",
    58: "book_bind",
    59: "flour_mill",
    60: "paper_mill",
    61: "seasoning_purify",
    62: "metal_cast",
    63: "weave",
    64: "mount_make",
    65: "pulp_process",
    66: "gas_extract",
    67: "skin_off",
    68: "crystal_collect",
    69: "treeproduct_collect",
    70: "dairy_collect",
    71: "catch",
    72: "fiber_collect",
    73: "ore_mine",
    74: "rock_mine",
    75: "medicalingredient_mine",
    76: "fruit_pick",
    77: "dyeingredient_collect",
    78: "crop_harvest",
    79: "seed_collect",
    80: "cereal_harvest",
    81: "soil_collect",
    82: "spice_collect",
    83: "plant_collect",
    84: "ground_build",
    85: "soil_framework_build",
    86: "pulp_framework_build",
    87: "stone_framework_build",
    88: "interior_finish_build",
    89: "exterior_finish_build",
    90: "repair_house",
    91: "machine_parts_collect",
    92: "magical_enchant",
    93: "recover_item",
    94: "demolish",
    96: "craft_start_ship",
    97: "summon_doodad_with_ucc",
    98: "navi_doodad_remove",
    99: "throw",
    100: "putdown",
    101: "kick",
    102: "grasp",
    103: "declare_siege",
    104: "buy_siege_ticket",
    105: "sell_backpack",
}

_FUNCTION = re.compile(
    r"^===== (?P<name>\S+) @ (?P<address>[0-9a-fA-F]+) =====\s*$",
    re.MULTILINE,
)
_CASE = re.compile(
    r'case\s+(?P<value>0x[0-9a-fA-F]+|\d+):\s*return\s+"(?P<label>[^"]+)";',
    re.MULTILINE,
)


def parse_world_interaction_switch(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(_FUNCTION.finditer(text))
    candidates: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end]
        if '"invalid world_interaction"' not in body:
            continue
        labels: dict[int, str] = {}
        for case in _CASE.finditer(body):
            value = int(case.group("value"), 0)
            label = case.group("label")
            if value in labels and labels[value] != label:
                raise RuntimeError(
                    f"{path}: duplicate world_interaction case {value}"
                )
            labels[value] = label
        candidates.append(
            {
                "function": match.group("name"),
                "address": match.group("address").lower(),
                "labels": labels,
                "has_invalid_default": True,
            }
        )
    if len(candidates) != 1:
        raise RuntimeError(
            f"{path}: expected one world_interaction switch, got "
            f"{len(candidates)}"
        )
    candidate = candidates[0]
    if candidate["labels"] != WORLD_INTERACTION_LABELS:
        raise RuntimeError(
            f"{path}: native world_interaction enum changed"
        )
    return candidate


def _digest_rows(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(canonical_json(row).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest().upper()


def audit_world_interactions(config: Any) -> dict[str, Any]:
    x64_switch = parse_world_interaction_switch(
        config.source_ghidra_world_interaction_enum_x64
    )
    x86_switch = parse_world_interaction_switch(
        config.source_ghidra_world_interaction_enum_x86
    )
    if x64_switch["labels"] != x86_switch["labels"]:
        raise RuntimeError("world_interaction x86/x64 switch mismatch")

    x64_layouts = _parse_loader_layouts(config.source_ghidra_sql_loaders_64)
    x86_layouts = _parse_loader_layouts(
        config.source_ghidra_world_interaction_loader_x86
    )
    x64 = x64_layouts.get(WORLD_INTERACTION_SQL)
    x86 = x86_layouts.get(WORLD_INTERACTION_SQL)
    if x64 is None or x86 is None:
        raise RuntimeError("wi_details loader is missing in one architecture")
    if (
        x64["columns"] != x86["columns"]
        or x64["layout"] != x86["layout"]
    ):
        raise RuntimeError("wi_details x86/x64 layout mismatch")
    expected_columns = ("wi_id", "apply_expert", "distance_sqrt", "lp")
    expected_layout = ("68", "38", "68", "68")
    if x64["columns"] != expected_columns or x64["layout"] != expected_layout:
        raise RuntimeError("wi_details native ABI changed")

    task_sqls = {
        line.partition("\t")[2]
        for line in config.source_world_interaction_loader_tasks.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        if line and not line.startswith("#") and "\t" in line
    }
    if task_sqls != {WORLD_INTERACTION_SQL}:
        raise RuntimeError("world_interaction task registry changed")

    sequence = json.loads(
        config.source_ghidra_sql_call_sequence.read_text(encoding="utf-8")
    )
    calls = [
        call
        for call in sequence
        if int(call["mapped_call_index"]) == WORLD_INTERACTION_CALL_INDEX
    ]
    if len(calls) != 1 or len(calls[0]["tasks"]) != 1:
        raise RuntimeError("wi_details SQL call mapping is ambiguous")
    task = calls[0]["tasks"][0]
    if str(task["sql"]) != WORLD_INTERACTION_SQL:
        raise RuntimeError("wi_details SQL is not at native call 611")

    spec = SkillQuery(
        call_index=WORLD_INTERACTION_CALL_INDEX,
        task=str(task["task"]),
        table="wi_details",
        sql=WORLD_INTERACTION_SQL,
        columns=expected_columns,
        layout=expected_layout,
        loader=str(x64["loader"]),
        loader_address=str(x64["address"]),
        architecture_state="confirmed_x86_x64",
    )
    data = config.source_game11.read_bytes()
    headers = _structural_headers(data)
    header, start, advertised = headers[WORLD_INTERACTION_HEADER_INDEX]
    next_header, next_start, _ = headers[WORLD_INTERACTION_HEADER_INDEX + 1]
    reader = CachedResultReader(data, None)
    cursor = start
    rows: list[dict[str, Any]] = []
    while cursor < len(data) and data[cursor] == 100:
        values, cursor = reader.row(cursor, list(expected_layout))
        rows.append(dict(zip(expected_columns, values, strict=True)))
    if cursor >= len(data) or data[cursor] != 101:
        raise RuntimeError(f"wi_details SQLITE_DONE missing at 0x{cursor:X}")
    if advertised != 60 or len(rows) != 60:
        raise RuntimeError(
            f"wi_details expected 60 rows, got {advertised}/{len(rows)}"
        )
    if cursor != next_header or next_start != next_header + 6:
        raise RuntimeError("wi_details structural boundary changed")
    ids = [int(row["wi_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("wi_details contains duplicate wi_id rows")
    if not set(ids).issubset(WORLD_INTERACTION_LABELS):
        raise RuntimeError("wi_details references an invalid enum member")
    if reader.unresolved:
        raise RuntimeError("wi_details unexpectedly contains string references")

    result = SkillResult(
        spec=spec,
        start=start,
        end=cursor,
        advertised_rows=advertised,
        rows=tuple(rows),
        digest=_digest_rows(rows),
        unresolved_references={},
        boundary_source=f"structural_header:0x{header:X}",
    )
    return {
        "spec": spec,
        "result": result,
        "labels": dict(WORLD_INTERACTION_LABELS),
        "detail_ids": frozenset(ids),
        "x64_switch": x64_switch,
        "x86_switch": x86_switch,
        "x64_loader": {
            "function": x64["loader"],
            "address": x64["address"],
        },
        "x86_loader": {
            "function": x86["loader"],
            "address": x86["address"],
        },
        "layout": expected_layout,
        "columns": expected_columns,
        "header": header,
        "next_header": next_header,
        "invalid_id": WORLD_INTERACTION_INVALID_ID,
        "detail_value_counts": {
            column: dict(
                sorted(
                    Counter(int(row[column]) for row in rows).items()
                )
            )
            for column in expected_columns[1:]
        },
    }
