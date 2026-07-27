#!/usr/bin/env python3
"""Close the AA8 item dependency required to start Nuian quest 2255.

V1 imported the AA8 quest item rows but did not register them in the native
item-definition coverage catalogue.  This builder keeps V1 immutable and
promotes only item 16280 after validating its generic implementation, quest
relations, use skill and concrete effect closure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any


DOMAIN = Path(__file__).resolve().parent
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v1.sqlite3"
)
DEFAULT_CLIENT_COMPACT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v2.sqlite3"
)
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-nuian-green-arc-v2-runtime-manifest.json"
)

EXPECTED_BASE_SHA256 = (
    "F15F3A2AA00DDF2DD0AE31EDA9B7C4CBE00172D342BBE4E713E5FF945A478BC7"
)
EXPECTED_CLIENT_SHA256 = (
    "9FB1838113820D4F5BAC93BB7E79A3E51613CF7B2828B28545B59F506B4F4397"
)
QUEST_ID = 2255
ITEM_ID = 16280
USE_SKILL_ID = 17326
SKILL_EFFECT_ID = 14619
EFFECT_ID = 18267
DISPEL_EFFECT_ID = 385


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def row_dict(
    connection: sqlite3.Connection, sql: str, parameters: tuple[Any, ...]
) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        raise RuntimeError(f"required native row is missing: {sql} {parameters}")
    return dict(row)


def validate_native_closure(
    runtime: sqlite3.Connection, client: sqlite3.Connection
) -> dict[str, Any]:
    runtime_item = row_dict(
        runtime, "SELECT * FROM items WHERE id=?", (ITEM_ID,)
    )
    client_item = row_dict(
        client, "SELECT * FROM items WHERE id=?", (ITEM_ID,)
    )
    shared_columns = sorted(set(runtime_item) & set(client_item))
    differing_columns = [
        column
        for column in shared_columns
        if runtime_item[column] != client_item[column]
    ]
    if differing_columns:
        raise RuntimeError(
            f"runtime item {ITEM_ID} differs from AA8 client compact: "
            f"{differing_columns}"
        )

    expected_item = {
        "impl_id": 0,
        "use_skill_id": USE_SKILL_ID,
        "loot_quest_id": QUEST_ID,
        "max_stack_size": 1,
    }
    actual_item = {key: runtime_item[key] for key in expected_item}
    if actual_item != expected_item:
        raise RuntimeError(
            f"item {ITEM_ID} is not the expected native generic quest item: "
            f"{actual_item}"
        )

    supply = row_dict(
        runtime,
        "SELECT id,item_id,count,grade_id,cleanup,drop_when_destroy,"
        "destroy_when_drop FROM quest_act_supply_items WHERE id=?",
        (1337,),
    )
    item_use = row_dict(
        runtime,
        "SELECT id,item_id,count,use_alias,quest_act_obj_alias_id "
        "FROM quest_act_obj_item_uses WHERE id=?",
        (588,),
    )
    skill = row_dict(
        runtime,
        "SELECT id,target_type_id,target_selection_id,target_unit_param,"
        "casting_time,effect_delay,skip_quest_apply_use_item "
        "FROM skills WHERE id=?",
        (USE_SKILL_ID,),
    )
    skill_effect = row_dict(
        runtime,
        "SELECT id,skill_id,effect_id,consume_item_count,consume_source_item "
        "FROM skill_effects WHERE id=?",
        (SKILL_EFFECT_ID,),
    )
    effect = row_dict(
        runtime,
        "SELECT id,actual_type,actual_id FROM effects WHERE id=?",
        (EFFECT_ID,),
    )
    dispel = row_dict(
        runtime,
        "SELECT id,buff_tag_id,cure_count,dispel_count,stack "
        "FROM dispel_effects WHERE id=?",
        (DISPEL_EFFECT_ID,),
    )
    quest_acts = [
        tuple(row)
        for row in runtime.execute(
            "SELECT qa.quest_component_id,qa.act_detail_type,qa.act_detail_id "
            "FROM quest_acts qa JOIN quest_components qc "
            "ON qc.id=qa.quest_component_id "
            "WHERE qc.quest_context_id=? ORDER BY qa.quest_component_id,qa.id",
            (QUEST_ID,),
        )
    ]
    required_acts = {
        (9942, "QuestActSupplyItem", 1337),
        (9943, "QuestActObjItemUse", 588),
    }
    if not required_acts.issubset(set(quest_acts)):
        raise RuntimeError(
            f"quest {QUEST_ID} item acts are incomplete: {quest_acts}"
        )
    if supply["item_id"] != ITEM_ID or supply["count"] != 1:
        raise RuntimeError(f"quest {QUEST_ID} supply closure differs: {supply}")
    if item_use["item_id"] != ITEM_ID or item_use["count"] != 1:
        raise RuntimeError(f"quest {QUEST_ID} use closure differs: {item_use}")
    if skill_effect != {
        "id": SKILL_EFFECT_ID,
        "skill_id": USE_SKILL_ID,
        "effect_id": EFFECT_ID,
        "consume_item_count": 1,
        "consume_source_item": 0,
    }:
        raise RuntimeError(f"skill effect closure differs: {skill_effect}")
    if effect != {
        "id": EFFECT_ID,
        "actual_type": "DispelEffect",
        "actual_id": DISPEL_EFFECT_ID,
    }:
        raise RuntimeError(f"concrete effect closure differs: {effect}")

    return {
        "item": actual_item,
        "supply_act": supply,
        "item_use_act": item_use,
        "skill": skill,
        "skill_effect": skill_effect,
        "effect": effect,
        "dispel_effect": dispel,
        "quest_item_acts_present": True,
        "runtime_matches_aa8_client_item": True,
    }


def validate_output(connection: sqlite3.Connection) -> dict[str, Any]:
    coverage = row_dict(
        connection,
        "SELECT item_id,concrete_type,coverage,missing_dependencies,provenance "
        "FROM aaemu_item_definition_coverage WHERE item_id=?",
        (ITEM_ID,),
    )
    expected = {
        "item_id": ITEM_ID,
        "concrete_type": "generic",
        "coverage": "complete",
        "missing_dependencies": "",
        "provenance": (
            "client_compact_8+game11_native_skill_closure+"
            "AA8_native_quest_2255_graph"
        ),
    }
    if coverage != expected:
        raise RuntimeError(f"item coverage differs: {coverage}")
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(
            f"SQLite validation failed: quick={quick}, integrity={integrity}"
        )
    return {
        "item_16280_coverage": coverage,
        "quick_check": quick,
        "integrity_check": integrity,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument(
        "--client-compact", type=Path, default=DEFAULT_CLIENT_COMPACT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()

    for path in (options.base_runtime, options.client_compact):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256(options.base_runtime) != EXPECTED_BASE_SHA256:
        raise RuntimeError("base V1 runtime differs from the validated input")
    if sha256(options.client_compact) != EXPECTED_CLIENT_SHA256:
        raise RuntimeError("AA8 client compact differs from the audited input")

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    client = sqlite3.connect(
        f"file:{options.client_compact.resolve().as_posix()}?mode=ro", uri=True
    )
    try:
        closure = validate_native_closure(connection, client)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
            "VALUES (?,?,?,?,?)",
            (
                ITEM_ID,
                "generic",
                "complete",
                "",
                "client_compact_8+game11_native_skill_closure+"
                "AA8_native_quest_2255_graph",
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO aaemu_native_quest_reconstruction
                (phase,authority,source_manifest_sha256,quest_ids)
            VALUES (?,?,?,?)
            """,
            (
                "native-nuian-green-arc-v2",
                "ArcheAge Kakao 8.0.3.12 r558734",
                EXPECTED_BASE_SHA256,
                str(QUEST_ID),
            ),
        )
        connection.commit()
        validation = validate_output(connection)
    except Exception:
        connection.rollback()
        connection.close()
        client.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()
        client.close()

    os.replace(temporary, options.output)
    document = {
        "format_version": 1,
        "phase": "native-nuian-green-arc-v2-runtime",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "sources": {
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": sha256(options.base_runtime),
            },
            "aa8_client_compact": {
                "path": str(options.client_compact),
                "sha256": sha256(options.client_compact),
            },
        },
        "scope": {
            "quest_id": QUEST_ID,
            "item_id": ITEM_ID,
            "use_skill_id": USE_SKILL_ID,
        },
        "native_closure": closure,
        "validation": validation,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
        "deployment": {
            "deployed": False,
            "reason": "Offline native closure built; controlled game restart pending.",
        },
    }
    options.manifest.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {options.output} ({options.output.stat().st_size} bytes, "
        f"sha256={document['output']['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
