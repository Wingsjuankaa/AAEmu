#!/usr/bin/env python3
"""Build the AA8 quest 2260 reward and Moonrise crate closure V3.

The generated runtime is an incremental layer over the currently validated
Point 0 runtime. Quest rows come from the quest relationship dossier backed by
game11; skill applications come from the decoded game11 stream; item/effect
rows and crate descriptions come from the decrypted AA8 client compact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SKILL_EXTRACTOR = (
    ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"
)

AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734"
PHASE = "native-quest-reward-explorer-closure-v3-runtime"
QUEST_ID = 2260
REWARD_COMPONENT_ID = 9962
QUEST_ACT_IDS = (64100, 65260, 65261, 65262, 65675)
SELECTIVE_DETAIL_IDS = (3655, 3656, 3657)
BOX_IDS = (47985, 47986, 47987)
BOX_SKILL_IDS = (42226, 42228, 42230)
SKILL_EFFECT_IDS = (59714, 59716, 59718)
EFFECT_IDS = (78590, 78592, 78594)
GAIN_EFFECT_IDS = (4216, 4218, 4220)
LOOT_PACK_IDS = (12951, 12953, 12955)
RESULT_ITEMS = {
    47985: (48018, 48020, 48021),
    47986: (48025, 48027, 48028),
    47987: (48032, 48034, 48035),
}

EXPECTED_HASHES = {
    "base_runtime": "BD25C9EC6086E76A36C5E9DF7A41A1FCB7EA1D1599FB06A614235339B919604C",
    "client_compact": "4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57",
    "game11": "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
    "quest_dossier": "574CA90A7E98B863C491610D00D965F3D3C0512C1AE38C9AAC086286679B8549",
    "item_47985_dossier": "ACE0CA3AE511D4E6CC3F9997DE9411DCA4BF91F937DAEBC3BFC452AAF889E6DB",
    "item_47986_dossier": "80F334C41446DB05AD937429A07F543BC3BBA268F7A2DC05EAEAD9178D1EC594",
    "item_47987_dossier": "C8D2B58C938266ABA6FF00C5EFAC9A339C3CFF9FE18C1649A8B385147A28C565",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def require_hash(label: str, path: Path) -> str:
    actual = sha256(path)
    expected = EXPECTED_HASHES[label]
    if actual != expected:
        raise RuntimeError(
            f"{label} hash mismatch: expected {expected}, got {actual}: {path}"
        )
    return actual


def property_map(node: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    value_columns = (
        "value_integer",
        "value_text",
        "value_real",
        "value_boolean",
        "value_json",
    )
    for prop in node.get("properties", []):
        value = next(
            (prop.get(column) for column in value_columns if prop.get(column) is not None),
            None,
        )
        result[str(prop["property_name"])] = value
    return result


def extract_quest_rows(dossier_path: Path) -> dict[str, list[dict[str, Any]]]:
    dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
    if dossier.get("root", {}).get("entity_key") != f"quest:{QUEST_ID}":
        raise RuntimeError("Quest dossier root is not quest 2260")
    nodes = {node["entity_key"]: node for node in dossier["graph"]["nodes"]}

    acts: list[dict[str, Any]] = []
    for act_id in QUEST_ACT_IDS:
        node = nodes[f"quest_act:{act_id}"]
        if node.get("state") != "confirmed" or node.get("source_stage") != 40:
            raise RuntimeError(f"Quest act {act_id} is not confirmed Stage 40 evidence")
        row = property_map(node)
        if int(row["quest_component_id"]) != REWARD_COMPONENT_ID:
            raise RuntimeError(f"Quest act {act_id} is outside reward component 9962")
        acts.append(row)

    details: dict[str, list[dict[str, Any]]] = {
        "quest_act_supply_exps": [],
        "quest_act_supply_selective_items": [],
        "quest_act_supply_coppers": [],
    }
    detail_keys = {
        "quest_act_supply_exps": (3930,),
        "quest_act_supply_selective_items": SELECTIVE_DETAIL_IDS,
        "quest_act_supply_coppers": (3823,),
    }
    for table, identifiers in detail_keys.items():
        for identifier in identifiers:
            key = f"quest_act_detail:{table}:{identifier}"
            node = nodes[key]
            if node.get("state") != "confirmed" or node.get("source_stage") != 40:
                raise RuntimeError(f"Quest detail {key} is not confirmed Stage 40 evidence")
            details[table].append(property_map(node))

    expected_acts = [
        (64100, "QuestActSupplyExp", 3930, 9962),
        (65260, "QuestActSupplySelectiveItem", 3655, 9962),
        (65261, "QuestActSupplySelectiveItem", 3656, 9962),
        (65262, "QuestActSupplySelectiveItem", 3657, 9962),
        (65675, "QuestActSupplyCopper", 3823, 9962),
    ]
    actual_acts = sorted(
        (
            int(row["id"]),
            str(row["act_detail_type"]),
            int(row["act_detail_id"]),
            int(row["quest_component_id"]),
        )
        for row in acts
    )
    if actual_acts != expected_acts:
        raise RuntimeError(f"Unexpected native reward acts: {actual_acts}")
    if details["quest_act_supply_exps"] != [{"exp": 2800, "id": 3930}]:
        raise RuntimeError("Quest 2260 native EXP reward changed")
    if details["quest_act_supply_coppers"] != [{"amount": 2500, "id": 3823}]:
        raise RuntimeError("Quest 2260 native copper reward changed")
    selective = sorted(
        (int(row["id"]), int(row["item_id"]), int(row["count"]), int(row["grade_id"]))
        for row in details["quest_act_supply_selective_items"]
    )
    if selective != [(3655, 47985, 1, 0), (3656, 47986, 1, 0), (3657, 47987, 1, 0)]:
        raise RuntimeError(f"Quest 2260 native selective rewards changed: {selective}")
    return {"quest_acts": acts, **details}


def load_skill_extractor():
    spec = importlib.util.spec_from_file_location("aa8_v3_skills", SKILL_EXTRACTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load skill extractor: {SKILL_EXTRACTOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_rows(
    connection: sqlite3.Connection,
    table: str,
    identifiers: Iterable[int],
) -> list[dict[str, Any]]:
    identifiers = tuple(identifiers)
    placeholders = ",".join("?" for _ in identifiers)
    connection.row_factory = sqlite3.Row
    return [
        dict(row)
        for row in connection.execute(
            f"SELECT * FROM {table} WHERE id IN ({placeholders}) ORDER BY id",
            identifiers,
        )
    ]


def extract_box_rows(
    client_compact: Path,
    game11: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[int, tuple[int, ...]]]:
    extractor = load_skill_extractor()
    relationships = extractor.extract_client_relationships(game11)
    skill_effects = [
        dict(row)
        for row in relationships["skill_effects"]
        if int(row["skill_id"]) in BOX_SKILL_IDS
    ]
    for row in skill_effects:
        if "start_combat_resource" in row:
            row["start_high_ability_resource"] = row.pop("start_combat_resource")
        if "end_combat_resource" in row:
            row["end_high_ability_resource"] = row.pop("end_combat_resource")
        if int(row.get("end_level") or 0) == 99:
            row["end_level"] = 255
    if sorted(int(row["id"]) for row in skill_effects) != list(SKILL_EFFECT_IDS):
        raise RuntimeError("Moonrise skill-effect application closure is incomplete")

    with sqlite3.connect(f"file:{client_compact}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        skills = fetch_rows(connection, "skills", BOX_SKILL_IDS)
        effects = fetch_rows(connection, "effects", EFFECT_IDS)
        gain_effects = fetch_rows(connection, "gain_loot_pack_item_effects", GAIN_EFFECT_IDS)
        boxes = {
            int(row["id"]): dict(row)
            for row in connection.execute(
                "SELECT id,name,description,use_skill_id FROM items "
                "WHERE id IN (47985,47986,47987) ORDER BY id"
            )
        }
        all_item_names: dict[str, list[int]] = {}
        for row in connection.execute("SELECT id,name FROM items"):
            all_item_names.setdefault(str(row["name"]), []).append(int(row["id"]))

    if sorted(int(row["id"]) for row in skills) != list(BOX_SKILL_IDS):
        raise RuntimeError("Moonrise skill templates are incomplete")
    if sorted(int(row["id"]) for row in effects) != list(EFFECT_IDS):
        raise RuntimeError("Moonrise effect templates are incomplete")
    if sorted(int(row["id"]) for row in gain_effects) != list(GAIN_EFFECT_IDS):
        raise RuntimeError("Moonrise GainLootPack details are incomplete")
    for row in effects:
        row["actual_type"] = "GainLootPackItemEffect"

    contents: dict[int, tuple[int, ...]] = {}
    for box_id in BOX_IDS:
        if int(boxes[box_id]["use_skill_id"]) not in BOX_SKILL_IDS:
            raise RuntimeError(f"Moonrise box {box_id} has an unexpected use skill")
        names = [
            line[2:].strip()
            for line in str(boxes[box_id]["description"]).splitlines()
            if line.startswith("- ")
        ]
        item_ids: list[int] = []
        for name in names:
            matches = all_item_names.get(name, [])
            if len(matches) != 1:
                raise RuntimeError(
                    f"Moonrise box {box_id} description item {name!r} has {len(matches)} matches"
                )
            item_ids.append(matches[0])
        contents[box_id] = tuple(item_ids)
        if contents[box_id] != RESULT_ITEMS[box_id]:
            raise RuntimeError(
                f"Moonrise box {box_id} result closure changed: {contents[box_id]}"
            )

    return {
        "skills": skills,
        "skill_effects": skill_effects,
        "effects": effects,
        "gain_loot_pack_item_effects": gain_effects,
    }, contents


def insert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    available = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    columns = [column for column in rows[0] if column in available]
    if "id" not in columns:
        raise RuntimeError(f"No id column available for {table}")
    identifiers = sorted({int(row["id"]) for row in rows})
    placeholders = ",".join("?" for _ in identifiers)
    connection.execute(f"DELETE FROM {table} WHERE id IN ({placeholders})", identifiers)
    values = ",".join(f":{column}" for column in columns)
    connection.executemany(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({values})",
        sorted(rows, key=lambda row: int(row["id"])),
    )


def install(
    base_runtime: Path,
    target: Path,
    quest_rows: dict[str, list[dict[str, Any]]],
    box_rows: dict[str, list[dict[str, Any]]],
    contents: dict[int, tuple[int, ...]],
) -> None:
    if target.exists():
        target.unlink()
    shutil.copyfile(base_runtime, target)
    with sqlite3.connect(target) as connection:
        connection.execute("BEGIN IMMEDIATE")
        for table in (
            "quest_acts",
            "quest_act_supply_exps",
            "quest_act_supply_selective_items",
            "quest_act_supply_coppers",
        ):
            insert_rows(connection, table, quest_rows[table])
        for table in ("skills", "skill_effects", "effects", "gain_loot_pack_item_effects"):
            insert_rows(connection, table, box_rows[table])

        for box_id, pack_id in zip(BOX_IDS, LOOT_PACK_IDS):
            connection.execute("DELETE FROM loots WHERE loot_pack_id=?", (pack_id,))
            connection.execute("DELETE FROM loot_groups WHERE pack_id=?", (pack_id,))
            for group_no, item_id in enumerate(contents[box_id], start=1):
                connection.execute(
                    "INSERT INTO loots "
                    "(id,\"group\",item_id,drop_rate,min_amount,max_amount,"
                    "loot_pack_id,grade_id,always_drop) "
                    "VALUES (?,?,?,10000000,1,1,?,0,'t')",
                    (91_400_000 + pack_id * 10 + group_no, group_no, item_id, pack_id),
                )

        provenance = "client_compact_8+game11_native+quest2260_reward_explorer_v3"
        for item_id in BOX_IDS:
            connection.execute(
                "DELETE FROM aaemu_item_definition_coverage WHERE item_id=?",
                (item_id,),
            )
            connection.execute(
                "INSERT INTO aaemu_item_definition_coverage "
                "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
                "VALUES (?,'generic','complete','',?)",
                (item_id, provenance),
            )

        connection.execute(
            "CREATE TABLE IF NOT EXISTS aaemu_quest_reward_explorer_closure_manifest "
            "(phase TEXT PRIMARY KEY, authority TEXT NOT NULL, quest_id INTEGER NOT NULL, "
            "reward_component_id INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_quest_reward_explorer_closure_manifest "
            "(phase,authority,quest_id,reward_component_id) VALUES (?,?,?,?)",
            (PHASE, AUTHORITY, QUEST_ID, REWARD_COMPONENT_ID),
        )
        connection.commit()
        connection.execute("VACUUM")
    connection.close()


def validate(path: Path) -> dict[str, Any]:
    with sqlite3.connect(path) as connection:
        reward_acts = connection.execute(
            "SELECT id,act_detail_type,act_detail_id,quest_component_id "
            "FROM quest_acts WHERE id IN (64100,65260,65261,65262,65675) ORDER BY id"
        ).fetchall()
        selective = connection.execute(
            "SELECT id,item_id,count,grade_id FROM quest_act_supply_selective_items "
            "WHERE id IN (3655,3656,3657) ORDER BY id"
        ).fetchall()
        loot_rows = connection.execute(
            "SELECT loot_pack_id,\"group\",item_id,drop_rate,min_amount,max_amount,always_drop "
            "FROM loots WHERE loot_pack_id IN (12951,12953,12955) "
            "ORDER BY loot_pack_id,\"group\""
        ).fetchall()
        checks = {
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "reward_acts": [list(row) for row in reward_acts],
            "selective_rewards": [list(row) for row in selective],
            "exp": connection.execute(
                "SELECT exp FROM quest_act_supply_exps WHERE id=3930"
            ).fetchone()[0],
            "copper": connection.execute(
                "SELECT amount FROM quest_act_supply_coppers WHERE id=3823"
            ).fetchone()[0],
            "skill_effects": connection.execute(
                "SELECT id,skill_id,effect_id,consume_source_item,end_level "
                "FROM skill_effects WHERE id IN (59714,59716,59718) ORDER BY id"
            ).fetchall(),
            "effects": connection.execute(
                "SELECT id,actual_type,actual_id FROM effects "
                "WHERE id IN (78590,78592,78594) ORDER BY id"
            ).fetchall(),
            "gain_effects": connection.execute(
                "SELECT id,loot_pack_id FROM gain_loot_pack_item_effects "
                "WHERE id IN (4216,4218,4220) ORDER BY id"
            ).fetchall(),
            "loot_rows": [list(row) for row in loot_rows],
            "coverage": connection.execute(
                "SELECT item_id,concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id IN (47985,47986,47987) "
                "ORDER BY item_id"
            ).fetchall(),
            "orphan_loot_items": connection.execute(
                "SELECT COUNT(*) FROM loots l LEFT JOIN items i ON i.id=l.item_id "
                "LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=l.item_id "
                "WHERE l.loot_pack_id IN (12951,12953,12955) "
                "AND (i.id IS NULL OR c.coverage!='complete')"
            ).fetchone()[0],
        }
    connection.close()
    expected_acts = [
        (64100, "QuestActSupplyExp", 3930, 9962),
        (65260, "QuestActSupplySelectiveItem", 3655, 9962),
        (65261, "QuestActSupplySelectiveItem", 3656, 9962),
        (65262, "QuestActSupplySelectiveItem", 3657, 9962),
        (65675, "QuestActSupplyCopper", 3823, 9962),
    ]
    if checks["quick_check"] != "ok" or checks["integrity_check"] != "ok":
        raise RuntimeError("Generated SQLite failed integrity checks")
    if reward_acts != expected_acts:
        raise RuntimeError(f"Reward acts are incomplete: {reward_acts}")
    if selective != [(3655, 47985, 1, 0), (3656, 47986, 1, 0), (3657, 47987, 1, 0)]:
        raise RuntimeError(f"Selective rewards are incomplete: {selective}")
    if checks["exp"] != 2800 or checks["copper"] != 2500:
        raise RuntimeError("Base EXP/copper rewards are incomplete")
    if len(checks["skill_effects"]) != 3 or len(checks["gain_effects"]) != 3:
        raise RuntimeError("Moonrise skill/effect closure is incomplete")
    if len(loot_rows) != 9 or checks["orphan_loot_items"] != 0:
        raise RuntimeError("Moonrise loot closure is incomplete")
    if any(row[2] != "complete" or row[3] for row in checks["coverage"]):
        raise RuntimeError("Moonrise source boxes are not complete")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--client-compact", type=Path, required=True)
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--quest-dossier", type=Path, required=True)
    parser.add_argument("--item-dossier-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    source_hashes = {
        "base_runtime": require_hash("base_runtime", args.base_runtime),
        "client_compact": require_hash("client_compact", args.client_compact),
        "game11": require_hash("game11", args.game11),
        "quest_dossier": require_hash("quest_dossier", args.quest_dossier),
    }
    for item_id in BOX_IDS:
        label = f"item_{item_id}_dossier"
        source_hashes[label] = require_hash(
            label,
            args.item_dossier_dir / f"item-{item_id}.json",
        )

    quest_rows = extract_quest_rows(args.quest_dossier)
    box_rows, contents = extract_box_rows(args.client_compact, args.game11)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    first = args.output.with_suffix(args.output.suffix + ".build-a")
    second = args.output.with_suffix(args.output.suffix + ".build-b")
    for candidate in (first, second):
        install(args.base_runtime, candidate, quest_rows, box_rows, contents)
    first_hash = sha256(first)
    second_hash = sha256(second)
    if first_hash != second_hash:
        raise RuntimeError(
            f"Non-deterministic builds: {first_hash} != {second_hash}"
        )
    checks = validate(second)
    if args.output.exists():
        args.output.unlink()
    os.replace(second, args.output)
    first.unlink()

    manifest = {
        "format_version": 3,
        "phase": PHASE,
        "authority": AUTHORITY,
        "sources": {
            "base_runtime": {"path": str(args.base_runtime), "sha256": source_hashes["base_runtime"]},
            "client_compact": {"path": str(args.client_compact), "sha256": source_hashes["client_compact"]},
            "game11": {"path": str(args.game11), "sha256": source_hashes["game11"]},
            "quest_dossier": {"path": str(args.quest_dossier), "sha256": source_hashes["quest_dossier"]},
            "item_dossiers": {
                str(item_id): {
                    "path": str(args.item_dossier_dir / f"item-{item_id}.json"),
                    "sha256": source_hashes[f"item_{item_id}_dossier"],
                }
                for item_id in BOX_IDS
            },
            "wiki": {
                "url": "https://wiki.archerage.to/na-en/db/quests/2260",
                "authority": "corroboration_only",
            },
        },
        "scope": {
            "quest_id": QUEST_ID,
            "reward_component_id": REWARD_COMPONENT_ID,
            "reward_act_ids": list(QUEST_ACT_IDS),
            "selective_items": list(BOX_IDS),
            "box_skills": list(BOX_SKILL_IDS),
            "loot_packs": list(LOOT_PACK_IDS),
            "result_items": {str(key): list(value) for key, value in contents.items()},
            "server_derived": [
                "loots rows only: exact AA8 item descriptions enumerate every result; loots is server-only"
            ],
            "historical_3_0_rows": 0,
        },
        "determinism": {
            "build_a_sha256": first_hash,
            "build_b_sha256": second_hash,
            "identical": True,
        },
        "validation": checks,
        "output": {
            "path": str(args.output),
            "bytes": args.output.stat().st_size,
            "sha256": sha256(args.output),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
