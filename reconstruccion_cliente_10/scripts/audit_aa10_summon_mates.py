#!/usr/bin/env python3
"""Build the closed AA10 r575 summon-mate manifest and runtime policy.

Both SQLite inputs are opened read-only with query_only enabled.  The full
database supplies the authoritative item->NPC relation; the compact retail
database decides whether that relation is visible and complete for the shipped
client.  No row is promoted by inference or by the legacy AAEmu implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path


FORMAT = "aa10-summon-mate-manifest-v1"
POLICY_FORMAT = "aa10-summon-mate-runtime-policy-v1"
SPAWN_PET_SPECIAL_TYPE = 24
SUMMON_MATE_IMPL = 11


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def one(connection: sqlite3.Connection, sql: str, *args: object) -> sqlite3.Row | None:
    return connection.execute(sql, args).fetchone()


def exists(connection: sqlite3.Connection, sql: str, *args: object) -> bool:
    return one(connection, sql, *args) is not None


def spawn_effects(connection: sqlite3.Connection, skill_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT se.id AS skill_effect_id, se.consume_source_item, s.id AS special_effect_id,
               s.value1, s.value2, s.value3, s.value4
          FROM skill_effects se
          JOIN effects e ON e.id = se.effect_id
          JOIN special_effects s ON s.id = e.actual_id
         WHERE se.skill_id = ? AND se.enable = 't'
           AND e.actual_type = 'SpecialEffect'
           AND s.special_effect_type_id = ?
         ORDER BY se.id
        """,
        (skill_id, SPAWN_PET_SPECIAL_TYPE),
    ).fetchall()


def relation_blockers(connection: sqlite3.Connection, item_id: int, npc_id: int) -> tuple[list[str], dict]:
    blockers: list[str] = []
    facts: dict[str, object] = {}

    item = one(
        connection,
        "SELECT id, name, impl_id, use_skill_id, use_skill_as_reagent, max_stack_size "
        "FROM items WHERE id = ?",
        item_id,
    )
    facts["itemPresent"] = item is not None
    if item is None:
        blockers.append("missing_item")
        facts.update(itemName=None, skillId=0, npcPresent=False)
        return blockers, facts

    skill_id = int(item["use_skill_id"] or 0)
    facts.update(
        itemName=item["name"],
        implId=int(item["impl_id"] or 0),
        skillId=skill_id,
        useSkillAsReagent=item["use_skill_as_reagent"] == "t",
        maxStackSize=int(item["max_stack_size"] or 0),
    )
    if facts["implId"] != SUMMON_MATE_IMPL:
        blockers.append("wrong_item_impl")
    if skill_id == 0 or not exists(connection, "SELECT 1 FROM skills WHERE id = ?", skill_id):
        blockers.append("missing_use_skill")
    effects = spawn_effects(connection, skill_id) if skill_id else []
    facts["spawnPetEffectCount"] = len(effects)
    facts["spawnPetEffects"] = [dict(row) for row in effects]
    if len(effects) != 1:
        blockers.append("spawn_pet_effect_count")
    elif effects[0]["consume_source_item"] == "t":
        blockers.append("spawn_pet_consumes_source")
    if facts["useSkillAsReagent"]:
        blockers.append("item_use_skill_as_reagent")

    npc = one(
        connection,
        "SELECT id, name, model_id, mate_equip_slot_pack_id FROM npcs WHERE id = ?",
        npc_id,
    )
    facts["npcPresent"] = npc is not None
    if npc is None:
        blockers.append("missing_npc")
        return blockers, facts

    model_id = int(npc["model_id"] or 0)
    slot_pack_id = int(npc["mate_equip_slot_pack_id"] or 0)
    facts.update(
        npcName=npc["name"],
        modelId=model_id,
        mateEquipSlotPackId=slot_pack_id,
    )
    model = one(connection, "SELECT sub_id, sub_type FROM models WHERE id = ?", model_id)
    if model is None:
        blockers.append("missing_model")
    elif model["sub_type"] != "ActorModel" or not exists(
        connection, "SELECT 1 FROM actor_models WHERE id = ?", int(model["sub_id"] or 0)
    ):
        blockers.append("missing_actor_model")

    if slot_pack_id == 0 or not exists(
        connection, "SELECT 1 FROM mate_equip_slot_packs WHERE id = ?", slot_pack_id
    ):
        blockers.append("missing_mate_equip_slot_pack")

    missing_mount_skills = [
        int(row["mount_skill_id"])
        for row in connection.execute(
            """
            SELECT nms.mount_skill_id
              FROM npc_mount_skills nms
         LEFT JOIN mount_skills ms ON ms.id = nms.mount_skill_id
         LEFT JOIN skills sk ON sk.id = ms.skill_id
             WHERE nms.npc_id = ? AND (ms.id IS NULL OR sk.id IS NULL)
             ORDER BY nms.mount_skill_id
            """,
            (npc_id,),
        )
    ]
    facts["missingMountSkillIds"] = missing_mount_skills
    if missing_mount_skills:
        blockers.append("missing_mount_skill")

    missing_buffs = [
        int(row["buff_id"])
        for row in connection.execute(
            """
            SELECT nib.buff_id
              FROM npc_initial_buffs nib
         LEFT JOIN buffs b ON b.id = nib.buff_id
             WHERE nib.npc_id = ? AND b.id IS NULL
             ORDER BY nib.buff_id
            """,
            (npc_id,),
        )
    ]
    facts["missingInitialBuffIds"] = missing_buffs
    if missing_buffs:
        blockers.append("missing_initial_buff")
    return blockers, facts


def build(
    full_path: Path, compact_path: Path, runtime_path: Path, x2game_path: Path
) -> tuple[dict, dict]:
    with (
        connect_readonly(full_path) as full,
        connect_readonly(compact_path) as compact,
        connect_readonly(runtime_path) as runtime,
    ):
        full_check = full.execute("PRAGMA quick_check").fetchone()[0]
        compact_check = compact.execute("PRAGMA quick_check").fetchone()[0]
        runtime_check = runtime.execute("PRAGMA quick_check").fetchone()[0]
        if full_check != "ok" or compact_check != "ok" or runtime_check != "ok":
            raise RuntimeError(
                "SQLite quick_check failed: "
                f"full={full_check}, compact={compact_check}, runtime={runtime_check}"
            )
        full_integrity = full.execute("PRAGMA integrity_check").fetchone()[0]
        compact_integrity = compact.execute("PRAGMA integrity_check").fetchone()[0]
        runtime_integrity = runtime.execute("PRAGMA integrity_check").fetchone()[0]
        if full_integrity != "ok" or compact_integrity != "ok" or runtime_integrity != "ok":
            raise RuntimeError(
                "SQLite integrity_check failed: "
                f"full={full_integrity}, compact={compact_integrity}, runtime={runtime_integrity}"
            )

        relations = full.execute(
            "SELECT id, item_id, npc_id FROM item_summon_mates ORDER BY item_id, id"
        ).fetchall()
        duplicate_items = [
            item_id for item_id, count in Counter(int(r["item_id"]) for r in relations).items() if count != 1
        ]
        if duplicate_items:
            raise RuntimeError(f"Duplicate item_summon_mates item IDs: {duplicate_items}")

        rows: list[dict] = []
        contracts: list[dict] = []
        for relation in relations:
            item_id = int(relation["item_id"])
            npc_id = int(relation["npc_id"])
            full_blockers, full_facts = relation_blockers(full, item_id, npc_id)
            compact_relation = one(
                compact,
                "SELECT npc_id FROM item_summon_mates WHERE item_id = ?",
                item_id,
            )
            compact_blockers, compact_facts = relation_blockers(compact, item_id, npc_id)
            if compact_relation is None:
                compact_blockers.insert(0, "missing_relation")
            elif int(compact_relation["npc_id"]) != npc_id:
                compact_blockers.insert(0, "relation_mismatch")

            runtime_relation = one(
                runtime,
                "SELECT npc_id FROM item_summon_mates WHERE item_id = ?",
                item_id,
            )
            runtime_blockers, runtime_facts = relation_blockers(runtime, item_id, npc_id)
            if runtime_relation is None:
                runtime_blockers.insert(0, "missing_relation")
            elif int(runtime_relation["npc_id"]) != npc_id:
                runtime_blockers.insert(0, "relation_mismatch")

            blockers = [f"full:{value}" for value in full_blockers]
            blockers.extend(f"compact:{value}" for value in compact_blockers)
            blockers.extend(f"runtime:{value}" for value in runtime_blockers)
            executable = not blockers
            row = {
                "relationId": int(relation["id"]),
                "itemId": item_id,
                "npcId": npc_id,
                "state": "executable" if executable else "blocked",
                "blockers": blockers,
                "full": full_facts,
                "compact": compact_facts,
                "runtime": runtime_facts,
            }
            rows.append(row)
            if executable:
                contracts.append(
                    {
                        "itemId": item_id,
                        "skillId": int(compact_facts["skillId"]),
                        "npcId": npc_id,
                    }
                )

    reason_counts = Counter(reason for row in rows for reason in row["blockers"])
    manifest = {
        "format": FORMAT,
        "build": "ArcheAge Returns 10.0.2.13 r575",
        "sources": {
            "full": {"path": str(full_path), "sha256": sha256(full_path)},
            "compactRetail": {"path": str(compact_path), "sha256": sha256(compact_path)},
            "compactRuntime": {"path": str(runtime_path), "sha256": sha256(runtime_path)},
            "x2game": {"path": str(x2game_path), "sha256": sha256(x2game_path)},
        },
        "nativeEvidence": {
            "loaderFunction": "FUN_39b265b0@39b265b0",
            "query": "SELECT item_id, npc_id FROM item_summon_mates",
            "spawnPetSpecialTypeId": SPAWN_PET_SPECIAL_TYPE,
            "sqliteChecks": {"quickCheck": "ok", "integrityCheck": "ok"},
        },
        "summary": {
            "relations": len(rows),
            "executable": len(contracts),
            "blocked": len(rows) - len(contracts),
            "blockerOccurrences": dict(sorted(reason_counts.items())),
        },
        "rows": rows,
    }
    manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    policy = {
        "format": POLICY_FORMAT,
        "sourceManifestSha256": hashlib.sha256(manifest_bytes).hexdigest().upper(),
        "contracts": contracts,
    }
    return manifest, policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", required=True, type=Path)
    parser.add_argument("--compact", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--x2game", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    args = parser.parse_args()

    manifest, policy = build(
        args.full.resolve(), args.compact.resolve(), args.runtime.resolve(), args.x2game.resolve()
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.policy.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_bytes(
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    args.policy.write_bytes((json.dumps(policy, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(manifest["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
