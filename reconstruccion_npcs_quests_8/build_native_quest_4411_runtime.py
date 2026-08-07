#!/usr/bin/env python3
"""Materialize the AA8-native Marian interaction required by quest 4411."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any


DOMAIN = Path(__file__).resolve().parent
CLIENT_ROOT = Path(r"D:\Proyectos\AAemu\client_kakao")
DEFAULT_BASE = CLIENT_ROOT / "compact-8.0-runtime-native-quest3993-v3.sqlite3"
DEFAULT_OUTPUT = CLIENT_ROOT / "compact-8.0-runtime-native-quest4411-v1.sqlite3"
DEFAULT_MANIFEST = DOMAIN / "generated" / "native-quest-4411-marian-v1-manifest.json"
DEFAULT_KNOWLEDGE = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite"
)
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_SKILL_DOSSIER = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\dossiers\skill-41999.json"
)
DEFAULT_DOODAD_DOSSIER = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\dossiers\doodad-14125.json"
)

EXPECTED = {
    "base": "E62DE56D6011CDF577ABDAA2F772338E80E971F82BFA13B1ED0AB9E88CAA0E94",
    "knowledge": "92CDF5D1EB16DAF0C4D5ABFCB80B510DFDF827708D4F8087235CCFACE3CE3C4F",
    "game11": "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
    "skill_dossier": "AE28917E025F7857A693EF62B64546D69889BA979BF4F66E041FF6144B1A77A1",
    "doodad_dossier": "81D9C64CAEA6319CD4EC392D8CFC1743EB01BD0E06E132F29FA3ACD491A388D2",
}

QUEST_ID = 4411
DOODAD_ID = 14125
NPC_ID = 10797
INTERACTION_GROUP_ID = 41603
DOODAD_FUNC_ID = 38602
DOODAD_USE_ID = 10936
SKILL_ID = 41999
SKILL_EFFECT_IDS = (59299, 59325)
EFFECT_IDS = (77957, 77994)
REWARD_ITEMS = (23633, 24087, 25076, 34003, 47866)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')]


def upsert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    columns = list(rows[0])
    available = set(table_columns(connection, table))
    if not set(columns).issubset(available):
        raise RuntimeError(
            f"{table} lacks native columns {sorted(set(columns) - available)}"
        )
    quoted = ",".join(f'"{column}"' for column in columns)
    placeholders = ",".join("?" for _ in columns)
    connection.executemany(
        f'INSERT OR REPLACE INTO "{table}" ({quoted}) VALUES ({placeholders})',
        [[row[column] for column in columns] for row in rows],
    )


def load_decoder():
    path = DOMAIN / "extract_native_nuian_green_arc.py"
    spec = importlib.util.spec_from_file_location("quest4411_doodad_decoder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_doodad(game11_path: Path) -> dict[str, list[dict[str, Any]]]:
    decoder = load_decoder()
    catalog = decoder.load_catalog()
    data = game11_path.read_bytes()
    decoded: dict[str, list[dict[str, Any]]] = {}
    for table, spec in decoder.DOODAD_SPECS.items():
        decoded[table], _ = decoder.decode_rows(
            catalog.CachedResultReader, data, table, spec
        )

    almighties = [
        dict(row) for row in decoded["doodad_almighties"]
        if int(row["id"]) == DOODAD_ID
    ]
    groups = [
        dict(row) for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) == DOODAD_ID
    ]
    group_ids = {int(row["id"]) for row in groups}
    funcs = [
        dict(row) for row in decoded["doodad_funcs"]
        if int(row["doodad_func_group_id"]) in group_ids
    ]
    if len(almighties) != 1 or int(almighties[0]["client_doodad"]) != 1:
        raise RuntimeError("AA8 doodad 14125 identity changed")
    if sorted(group_ids) != [41576, 41577, 41579, 41582, 41602, 41603]:
        raise RuntimeError(f"AA8 doodad 14125 phase set changed: {sorted(group_ids)}")
    expected_func = {
        "id": DOODAD_FUNC_ID,
        "actual_func_type": "DoodadFuncUse",
        "actual_func_id": DOODAD_USE_ID,
        "doodad_func_group_id": INTERACTION_GROUP_ID,
        "func_skill_id": SKILL_ID,
        "next_phase": -1,
    }
    if len(funcs) != 1 or any(funcs[0][key] != value for key, value in expected_func.items()):
        raise RuntimeError(f"AA8 doodad 14125 function closure changed: {funcs}")

    # The cached-result string stream first materializes npctype://10797 in
    # phase 41579, then reuses reference 300997 for phases 41582/41603 and
    # the almighty model. Resolve only that demonstrated replay; generic
    # empty/color references remain empty runtime presentation fields.
    almighty = almighties[0]
    almighty["model"] = f"npctype://{NPC_ID}"
    almighty["name"] = "Marian"
    for key, value in list(almighty.items()):
        if isinstance(value, str) and value.startswith("<ref:"):
            almighty[key] = ""

    for group in groups:
        for key, value in list(group.items()):
            if not (isinstance(value, str) and value.startswith("<ref:")):
                continue
            group[key] = (
                f"npctype://{NPC_ID}"
                if key == "model" and value == "<ref:300997>"
                else ""
            )
    if next(row for row in groups if int(row["id"]) == 41579)["model"] != f"npctype://{NPC_ID}":
        raise RuntimeError("AA8 Marian NPC model binding changed")
    if next(row for row in groups if int(row["id"]) == INTERACTION_GROUP_ID)["model"] != f"npctype://{NPC_ID}":
        raise RuntimeError("AA8 Marian interaction phase replay did not resolve")

    return {
        "doodad_almighties": [almighty],
        "doodad_func_groups": groups,
        "doodad_funcs": funcs,
        "doodad_func_uses": [{"id": DOODAD_USE_ID, "skill_id": SKILL_ID}],
    }


def load_native_row(
    knowledge: sqlite3.Connection,
    entity_key: str,
) -> tuple[str, dict[str, Any]]:
    rows = list(knowledge.execute(
        "SELECT source_table,state,row_json FROM native_rows WHERE entity_key=?",
        (entity_key,),
    ))
    candidates = []
    for row in rows:
        if str(row[1]) != "confirmed":
            continue
        payload = json.loads(str(row[2]))
        if "id" in payload:
            candidates.append((len(payload), str(row[0]), payload))
    if not candidates:
        raise RuntimeError(f"missing confirmed AA8 row {entity_key}")
    _, table, payload = max(candidates, key=lambda candidate: candidate[0])
    return table, payload


def extract_skill_closure(
    connection: sqlite3.Connection,
    knowledge_path: Path,
) -> dict[str, list[dict[str, Any]]]:
    knowledge = sqlite3.connect(
        f"file:{knowledge_path.resolve().as_posix()}?mode=ro", uri=True
    )
    try:
        rows: dict[str, list[dict[str, Any]]] = {
            "skill_effects": [],
            "effects": [],
            "interaction_effects": [],
            "bubble_effects": [],
        }
        aliases = {
            "start_high_ability_resource": "start_combat_resource",
            "end_high_ability_resource": "end_combat_resource",
        }
        for application_id in SKILL_EFFECT_IDS:
            table, native = load_native_row(
                knowledge, f"skill_effect_application:{application_id}"
            )
            if table != "skill_effects" or int(native["skill_id"]) != SKILL_ID:
                raise RuntimeError(f"AA8 skill application {application_id} changed")
            normalized = {}
            for column in table_columns(connection, "skill_effects"):
                source = aliases.get(column, column)
                if source not in native:
                    raise RuntimeError(
                        f"AA8 skill application {application_id} lacks {source}"
                    )
                normalized[column] = native[source]
            rows["skill_effects"].append(normalized)

            effect_id = int(native["effect_id"])
            table, effect = load_native_row(knowledge, f"effect:{effect_id}")
            if table != "effects":
                raise RuntimeError(f"AA8 effect {effect_id} changed table")
            rows["effects"].append(effect)
            detail_table = {
                "InteractionEffect": "interaction_effects",
                "BubbleEffect": "bubble_effects",
            }.get(str(effect["actual_type"]))
            if detail_table is None:
                raise RuntimeError(f"unexpected AA8 effect type {effect['actual_type']}")
            actual_id = int(effect["actual_id"])
            table, detail = load_native_row(
                knowledge, f"effect_detail:{detail_table}:{actual_id}"
            )
            if table != detail_table:
                raise RuntimeError(f"AA8 effect detail {actual_id} changed table")
            rows[detail_table].append(detail)
    finally:
        knowledge.close()

    if sorted(int(row["effect_id"]) for row in rows["skill_effects"]) != list(EFFECT_IDS):
        raise RuntimeError("AA8 skill 41999 effect set changed")
    return rows


def validate_runtime(connection: sqlite3.Connection) -> dict[str, Any]:
    interaction = connection.execute(
        "SELECT count,doodad_id,wi_id FROM quest_act_obj_interactions WHERE id=1115"
    ).fetchone()
    checks = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "quest_interaction": tuple(interaction) if interaction else None,
        "doodad": tuple(connection.execute(
            "SELECT client_doodad,once_one_interaction,once_one_man "
            "FROM doodad_almighties WHERE id=?", (DOODAD_ID,)
        ).fetchone() or ()),
        "interaction_group": tuple(connection.execute(
            "SELECT doodad_almighty_id,model FROM doodad_func_groups WHERE id=?",
            (INTERACTION_GROUP_ID,),
        ).fetchone() or ()),
        "doodad_func": tuple(connection.execute(
            "SELECT actual_func_type,actual_func_id,doodad_func_group_id,"
            "func_skill_id,next_phase FROM doodad_funcs WHERE id=?",
            (DOODAD_FUNC_ID,),
        ).fetchone() or ()),
        "doodad_use": tuple(connection.execute(
            "SELECT skill_id FROM doodad_func_uses WHERE id=?", (DOODAD_USE_ID,)
        ).fetchone() or ()),
        "skill_effects": [tuple(row) for row in connection.execute(
            "SELECT id,effect_id FROM skill_effects WHERE skill_id=? ORDER BY id",
            (SKILL_ID,),
        )],
        "effects": [tuple(row) for row in connection.execute(
            "SELECT id,actual_type,actual_id FROM effects WHERE id IN (77957,77994) "
            "ORDER BY id"
        )],
        "interaction_effect": tuple(connection.execute(
            "SELECT doodad_id,wi_id,source_direction FROM interaction_effects WHERE id=7874"
        ).fetchone() or ()),
        "bubble_effect": tuple(connection.execute(
            "SELECT kind_id,speech FROM bubble_effects WHERE id=6013"
        ).fetchone() or ()),
        "reward_items": [int(row[0]) for row in connection.execute(
            f"SELECT id FROM items WHERE id IN ({','.join('?' for _ in REWARD_ITEMS)}) "
            "ORDER BY id", REWARD_ITEMS
        )],
    }
    expected = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "quest_interaction": (1, DOODAD_ID, 19),
        "doodad": (1, 1, 1),
        "interaction_group": (DOODAD_ID, f"npctype://{NPC_ID}"),
        "doodad_func": (
            "DoodadFuncUse", DOODAD_USE_ID, INTERACTION_GROUP_ID, SKILL_ID, -1
        ),
        "doodad_use": (SKILL_ID,),
        "skill_effects": [(59299, 77957), (59325, 77994)],
        "effects": [
            (77957, "InteractionEffect", 7874),
            (77994, "BubbleEffect", 6013),
        ],
        "interaction_effect": (0, 19, 1),
        "reward_items": list(REWARD_ITEMS),
    }
    failures = {
        key: {"expected": value, "actual": checks[key]}
        for key, value in expected.items()
        if checks[key] != value
    }
    if len(checks["bubble_effect"]) != 2 or not str(checks["bubble_effect"][1]).strip():
        failures["bubble_effect"] = "missing native farewell speech"
    if failures:
        raise RuntimeError(f"generated runtime validation failed: {failures}")
    return checks


def validate_dossier(path: Path, expected_root: str) -> dict[str, Any]:
    dossier = json.loads(path.read_text(encoding="utf-8"))
    if dossier["root"]["entity_key"] != expected_root:
        raise RuntimeError(f"unexpected dossier root in {path}")
    if dossier["readiness"]["forensic"]["state"] != "profile_complete":
        raise RuntimeError(f"forensic dossier is not complete: {path}")
    return {
        "path": str(path),
        "sha256": sha256(path),
        "forensic_state": dossier["readiness"]["forensic"]["state"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_KNOWLEDGE)
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--skill-dossier", type=Path, default=DEFAULT_SKILL_DOSSIER)
    parser.add_argument("--doodad-dossier", type=Path, default=DEFAULT_DOODAD_DOSSIER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()

    sources = {
        "base": sha256(options.base_runtime),
        "knowledge": sha256(options.knowledge),
        "game11": sha256(options.game11),
        "skill_dossier": sha256(options.skill_dossier),
        "doodad_dossier": sha256(options.doodad_dossier),
    }
    if sources != EXPECTED:
        raise RuntimeError(f"AA8 source set changed: {sources}")
    dossiers = {
        "skill": validate_dossier(options.skill_dossier, "skill:41999"),
        "doodad": validate_dossier(options.doodad_dossier, "doodad:14125"),
    }
    doodad_rows = extract_doodad(options.game11)

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    try:
        connection.row_factory = sqlite3.Row
        skill_rows = extract_skill_closure(connection, options.knowledge)
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        for table, rows in doodad_rows.items():
            upsert_rows(connection, table, rows)
        connection.execute("DELETE FROM skill_effects WHERE skill_id=?", (SKILL_ID,))
        for table, rows in skill_rows.items():
            upsert_rows(connection, table, rows)
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "native-quest-4411-marian-v1",
                "ArcheAge Kakao 8.0.3.12 r558734",
                sources["knowledge"],
                str(QUEST_ID),
            ),
        )
        checks = validate_runtime(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()

    os.replace(temporary, options.output)
    document = {
        "format_version": 1,
        "phase": "native-quest-4411-marian-v1-runtime",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "sources": {
            "base_runtime": {"path": str(options.base_runtime), "sha256": sources["base"]},
            "knowledge": {"path": str(options.knowledge), "sha256": sources["knowledge"]},
            "game11": {"path": str(options.game11), "sha256": sources["game11"]},
            "dossiers": dossiers,
        },
        "scope": {
            "quest_id": QUEST_ID,
            "doodad_id": DOODAD_ID,
            "npc_proxy_id": NPC_ID,
            "interaction_group_id": INTERACTION_GROUP_ID,
            "skill_id": SKILL_ID,
            "world_interaction_id": 19,
        },
        "validation": checks,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
    }
    options.manifest.write_text(
        json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
