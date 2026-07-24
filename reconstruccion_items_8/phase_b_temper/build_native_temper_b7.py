#!/usr/bin/env python3
"""Build cumulative AA8 equipment Phase B7 with native temper execution."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PARSER_PATH = ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"
TEMPER_PATH = ROOT / "reconstruccion_items_8" / "phase_b_temper" / "extract_native_temper.py"

CATALYST_SKILLS = (37723, 37724, 39267, 39268)
CATALYST_ITEMS = {
    45914: 37723,
    45915: 37724,
    45916: 39267,
    45917: 39268,
}
SKILL_EFFECT_IDS = (52272, 52273, 54911, 54912)
EFFECT_IDS = (66960, 66961, 71255, 71256)
SPECIAL_EFFECT_IDS = (31190, 31191, 36581, 36582)
EQUIP_COST_START = 0x85649DD
EQUIP_COST_LAYOUT = ["68", "68"]
EQUIP_COST_COLUMNS = ["slot_type_id", "cost"]
EQUIP_COST_COUNT = 21
FORMULA_59 = (
    " ( if_negative( equip_slot_enchant_cost - 10 , 3/7 , 1 ) * "
    "( ( item_level * 0.37 ) ^ 2.5 * ( scale_cost ^ 3.9 ) * "
    "( equip_slot_enchant_cost * 0.0002 ) + 80000 ) ) * "
    "( 1000 + enchant_scale_cost_mul ) / 1000"
)
FORMULA_FIRST_STRING_REFERENCE = 361069


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--client-compact", required=True, type=Path)
    parser.add_argument("--base-runtime", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def extract_native(game11: Path, client_compact: Path) -> dict[str, Any]:
    parser = load_module(PARSER_PATH, "aa8_temper_parser")
    temper = load_module(TEMPER_PATH, "aa8_temper_b2")
    reader = parser.CachedResultReader(game11.read_bytes())

    ratios, forbids, b2_ranges = temper.extract(game11)
    costs_raw, costs_end = parser.read_cached_result(
        reader, EQUIP_COST_START, EQUIP_COST_LAYOUT
    )
    costs = [dict(zip(EQUIP_COST_COLUMNS, row)) for row in costs_raw]
    if len(costs) != EQUIP_COST_COUNT:
        raise RuntimeError(f"Expected {EQUIP_COST_COUNT} equip costs, got {len(costs)}")

    _, formula_range = parser.locate_cached_result(
        reader,
        ["id", "formula"],
        ["68", "78"],
        59,
        {"formula": FORMULA_59},
    )
    # The cached-query result interns every inline formula. x2game later
    # references those strings by their native cache identifier. Re-read the
    # exact result with the confirmed first identifier so formula 37 resolves
    # to formula 29 and formula 45 resolves to formula 44 instead of leaking
    # opaque <ref:...> values into the runtime.
    formula_reader = parser.CachedResultReader(reader.data)
    formula_reader.begin_string_cache_capture(FORMULA_FIRST_STRING_REFERENCE)
    formula_rows, formula_end = parser.read_cached_result(
        formula_reader,
        formula_range["start"],
        ["68", "78"],
    )
    formula_strings = formula_reader.end_string_cache_capture()
    formulas = [
        dict(zip(("id", "formula"), row))
        for row in formula_rows
    ]
    if formula_end != formula_range["end"]:
        raise RuntimeError(
            f"Formula cached-result end changed: {formula_end} != "
            f"{formula_range['end']}"
        )
    expected_formula_ids = set(range(2, 73)) - {46}
    if len(formulas) != 70 or {
        int(row["id"]) for row in formulas
    } != expected_formula_ids:
        raise RuntimeError(
            "AA8 formula catalogue is not the confirmed 2..72 range (without 46)"
        )
    formulas_by_id = {
        int(row["id"]): str(row["formula"])
        for row in formulas
    }
    if any(value.startswith("<ref:") for value in formulas_by_id.values()):
        raise RuntimeError("One or more native formulas still have unresolved refs")
    if formulas_by_id[37] != formulas_by_id[29]:
        raise RuntimeError("Native formula 37 did not resolve to cached formula 29")
    if formulas_by_id[45] != formulas_by_id[44]:
        raise RuntimeError("Native formula 45 did not resolve to cached formula 44")
    if formulas_by_id[59] != FORMULA_59:
        raise RuntimeError("Native formula 59 differs from the confirmed AA8 formula")
    formula_range["string_cache_first_reference"] = (
        FORMULA_FIRST_STRING_REFERENCE
    )
    formula_range["resolved_references"] = {
        "361088": formula_strings[361088],
        "361101": formula_strings[361101],
    }

    skill_effects, skill_effect_range = parser.locate_cached_result(
        reader,
        parser.SKILL_EFFECT_COLUMNS,
        parser.SKILL_EFFECT_LAYOUT,
        25615,
        {"skill_id": 23136, "effect_id": 32720},
    )
    selected_skill_effects = [
        row for row in skill_effects if int(row["id"]) in SKILL_EFFECT_IDS
    ]
    if {int(row["id"]) for row in selected_skill_effects} != set(SKILL_EFFECT_IDS):
        raise RuntimeError("One or more native temper skill_effect rows are missing")

    special_spec = parser.CLIENT_CONCRETE_RESULT_SPECS["special_effects"]
    special_effects, special_range = parser.locate_cached_result(
        reader,
        special_spec["columns"],
        special_spec["layout"],
        special_spec["anchor_id"],
        special_spec["anchor_values"],
    )
    selected_special_effects = [
        row for row in special_effects if int(row["id"]) in SPECIAL_EFFECT_IDS
    ]
    if {int(row["id"]) for row in selected_special_effects} != set(SPECIAL_EFFECT_IDS):
        raise RuntimeError("One or more native temper special_effect rows are missing")

    connection = sqlite3.connect(
        f"file:{client_compact.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    try:
        placeholders = ",".join("?" for _ in EFFECT_IDS)
        effects = [
            dict(row)
            for row in connection.execute(
                f"SELECT id,actual_type,actual_id FROM effects "
                f"WHERE id IN ({placeholders}) ORDER BY id",
                EFFECT_IDS,
            )
        ]
    finally:
        connection.close()
    if {int(row["id"]) for row in effects} != set(EFFECT_IDS):
        raise RuntimeError("One or more native temper effect rows are missing")
    for row in effects:
        if row["actual_type"] != "<ref:75222>":
            raise RuntimeError(f"Unexpected effect type reference: {row}")
        row["actual_type"] = "SpecialEffect"

    return {
        "ratios": ratios,
        "forbids": forbids,
        "equip_costs": costs,
        "formulas": formulas,
        "skill_effects": selected_skill_effects,
        "effects": effects,
        "special_effects": selected_special_effects,
        "ranges": {
            **b2_ranges,
            "equip_slot_enchanting_costs": {
                "start": EQUIP_COST_START,
                "end": costs_end,
                "rows": len(costs),
                "loader": "x2game.dll native cached-query result",
            },
            "formulas": formula_range,
            "skill_effects": skill_effect_range,
            "special_effects": special_range,
        },
    }


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def upsert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
    aliases: dict[str, str] | None = None,
) -> None:
    aliases = aliases or {}
    columns = table_columns(connection, table)
    for source in rows:
        normalized = {
            target: source.get(aliases.get(target, target))
            for target in columns
            if aliases.get(target, target) in source
        }
        if table == "skill_effects" and normalized.get("end_level") == 99:
            normalized["end_level"] = 255
        names = list(normalized)
        placeholders = ",".join("?" for _ in names)
        connection.execute(
            f"INSERT OR REPLACE INTO {table} ({','.join(names)}) "
            f"VALUES ({placeholders})",
            [normalized[name] for name in names],
        )


def build(
    base_runtime: Path,
    output: Path,
    native: dict[str, Any],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    shutil.copyfile(base_runtime, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")

        connection.execute("DELETE FROM formulas")
        upsert_rows(connection, "formulas", native["formulas"])

        connection.execute("DELETE FROM equip_slot_enchanting_costs")
        upsert_rows(
            connection,
            "equip_slot_enchanting_costs",
            native["equip_costs"],
        )

        connection.execute("DELETE FROM enchant_scale_ratios")
        upsert_rows(connection, "enchant_scale_ratios", native["ratios"])
        connection.execute("DELETE FROM item_cap_scale_forbids")
        upsert_rows(connection, "item_cap_scale_forbids", native["forbids"])

        for table, ids in (
            ("skill_effects", SKILL_EFFECT_IDS),
            ("effects", EFFECT_IDS),
            ("special_effects", SPECIAL_EFFECT_IDS),
        ):
            connection.execute(
                f"DELETE FROM {table} WHERE id IN "
                f"({','.join('?' for _ in ids)})",
                ids,
            )

        upsert_rows(
            connection,
            "skill_effects",
            native["skill_effects"],
            {
                "end_high_ability_resource": "end_combat_resource",
                "start_high_ability_resource": "start_combat_resource",
            },
        )
        upsert_rows(connection, "effects", native["effects"])
        upsert_rows(connection, "special_effects", native["special_effects"])

        metadata = {
            "phase": "B7-native-temper-execution",
            "temper_transaction": "native-aa8-enabled",
            "temper_result_opcode": "0x0B1",
            "temper_formula_id": "59",
            "temper_initial_scale_id": "1",
            "temper_normal_skills": "37723,37724",
            "temper_shining_skills": "39267,39268",
            "temper_provenance": "game11_native+x2game_confirmed+client_compact_8",
            **{f"sha256_{key}": value for key, value in source_hashes.items()},
        }
        for key, value in sorted(metadata.items()):
            connection.execute(
                "INSERT OR REPLACE INTO aaemu_item_phase_b_metadata(key,value) "
                "VALUES (?,?)",
                (key, value),
            )

        connection.commit()
        connection.execute("VACUUM")
        has_combat_provenance = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name='aaemu_combat_provenance'"
        ).fetchone()[0]
        historical_combat_rows = (
            connection.execute(
                "SELECT COUNT(*) FROM aaemu_combat_provenance "
                "WHERE provenance='historical_3_0'"
            ).fetchone()[0]
            if has_combat_provenance
            else 0
        )
        checks = {
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "integrity_check": connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0],
            "formula_count": connection.execute(
                "SELECT COUNT(*) FROM formulas"
            ).fetchone()[0],
            "formula_59": connection.execute(
                "SELECT formula FROM formulas WHERE id=59"
            ).fetchone()[0],
            "unresolved_formula_count": connection.execute(
                "SELECT COUNT(*) FROM formulas WHERE formula LIKE '<ref:%'"
            ).fetchone()[0],
            "ratio_count": connection.execute(
                "SELECT COUNT(*) FROM enchant_scale_ratios"
            ).fetchone()[0],
            "equip_cost_count": connection.execute(
                "SELECT COUNT(*) FROM equip_slot_enchanting_costs"
            ).fetchone()[0],
            "temper_skill_effect_count": connection.execute(
                f"SELECT COUNT(*) FROM skill_effects WHERE id IN "
                f"({','.join('?' for _ in SKILL_EFFECT_IDS)})",
                SKILL_EFFECT_IDS,
            ).fetchone()[0],
            "temper_special_count": connection.execute(
                f"SELECT COUNT(*) FROM special_effects WHERE id IN "
                f"({','.join('?' for _ in SPECIAL_EFFECT_IDS)}) "
                "AND special_effect_type_id=126",
                SPECIAL_EFFECT_IDS,
            ).fetchone()[0],
            "historical_combat_provenance_rows": historical_combat_rows,
        }
        expected = {
            "quick_check": "ok",
            "integrity_check": "ok",
            "formula_count": 70,
            "formula_59": FORMULA_59,
            "unresolved_formula_count": 0,
            "ratio_count": 31,
            "equip_cost_count": 21,
            "temper_skill_effect_count": 4,
            "temper_special_count": 4,
            "historical_combat_provenance_rows": 0,
        }
        if checks != expected:
            raise RuntimeError(
                f"Runtime validation failed:\nactual={checks}\nexpected={expected}"
            )
        for item_id, skill_id in CATALYST_ITEMS.items():
            row = connection.execute(
                "SELECT use_skill_id FROM items WHERE id=?", (item_id,)
            ).fetchone()
            if row is None or int(row[0]) != skill_id:
                raise RuntimeError(
                    f"Catalyst item {item_id} does not use native skill {skill_id}"
                )
        return checks
    finally:
        connection.close()


def main() -> int:
    args = arguments()
    native = extract_native(args.game11, args.client_compact)
    source_hashes = {
        "game11": sha256(args.game11),
        "client_compact": sha256(args.client_compact),
        "base_runtime": sha256(args.base_runtime),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa8-temper-b7-") as temp:
        first = Path(temp) / "first.sqlite3"
        second = Path(temp) / "second.sqlite3"
        checks = build(args.base_runtime, first, native, source_hashes)
        build(args.base_runtime, second, native, source_hashes)
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise RuntimeError(
                f"Non-deterministic build: {first_hash} != {second_hash}"
            )
        shutil.copyfile(first, args.output)

    manifest = {
        "format_version": 1,
        "phase": "B7-native-temper-execution",
        "authority": [
            "client_compact_8",
            "game11_native",
            "x2game_confirmed",
            "server_derived",
        ],
        "sources": source_hashes,
        "ranges": native["ranges"],
        "native_catalysts": CATALYST_ITEMS,
        "protocol": {
            "opcode": "0x0B1",
            "payload": "int32 result, item, uint16 beforeScale, uint16 afterScale",
            "results": {
                "0": "break",
                "1": "downgrade",
                "2": "fail",
                "3": "disable",
                "4": "success",
                "5": "great_success",
            },
        },
        "output": {
            "path": str(args.output),
            "sha256": sha256(args.output),
            **checks,
        },
        "deployment": {
            "deployable": True,
            "requires_mysql_backup": True,
            "recreate": ["game"],
        },
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["output"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
