#!/usr/bin/env python3
"""Build the deterministic AA10 quest Stage 40 evidence bundle.

This is a read-only forensic extractor.  It never writes to the source databases
or to the AAEmu runtime.  All generated rows are ordered and the SQLite layout is
vacuumed so two builds from identical inputs are byte-for-byte reproducible.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_ROOT = Path(r"E:\AAEmu\rama_10")
DEFAULT_CLIENT = DEFAULT_ROOT / "client" / "ArcheAge-Returns-10.0.2.13-r575"
DEFAULT_REPO = DEFAULT_ROOT / "server" / "AAEmu"
DEFAULT_OUTPUT = (
    DEFAULT_ROOT / "forensics" / "output" / "aa10-client-forensics" / "quest-stage40"
)

EXPECTED = {
    "full_db_sha256": "87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F",
    "compact_db_sha256": "8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849",
    "x2game_sha256": "405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734",
    "game_pak_sha256": "AB3B86E694CFC0141453AD9B734BABEE67019C58D8E0B52498036ABC0DCBCBF0",
    "game_pak_size": 68_963_258_880,
}

# AA10 zone-profile crosswalk established from zones.id -> zones.zone_key and
# the exact r575 game_pak index. Phase 6 proved that keys 133 and 149 include
# their native Zone spawners; they are deployable partitions, not blockers.
NUIA_ZONE_CROSSWALK = (
    (125, 179, "present", "intro/chapter 1-2"),
    (9, 142, "present", "intro/chapter 1-2"),
    (124, 178, "present", "intro/chapter 1-2"),
    (11, 144, "present", "chapter 3"),
    (141, 195, "present", "chapter 3-4"),
    (7, 140, "present", "chapter 4"),
    (131, 185, "present", "chapter 4"),
    (10, 143, "present", "chapter 5"),
    (2, 133, "present", "chapter 6"),
    (15, 149, "present", "chapter 6"),
)

PARTIAL_TYPES: dict[str, str] = {}

PHASE3_OBJECTIVES = (
    ("QuestActObjCompleteQuestGroup", "quest_act_obj_complete_quest_groups", "OnQuestComplete", "OnQuestComplete(Owner", "implemented", "accept_with seeds history; later completions increment count"),
    ("QuestActObjConquestWar", "quest_act_obj_conquest_wars", "TowerDef/conquest result authority", "QuestObjectiveEventType.ConquestWar", "implemented", "result-only event; unique faction rank; zone 78 TowerDef 126 and zone 20 authored competition winner"),
    ("QuestActObjConsumeEvolvingMaterial", "quest_act_obj_consume_evolving_materials", "committed ItemEvolving", "ConsumeEvolvingMaterial", "implemented", "emit selected material-slot count only after atomic consumption"),
    ("QuestActObjEnchantScaleCount", "quest_act_obj_enchant_scale_counts", "committed ItemRefurbishment", "EnchantScaleCount", "implemented", "one event per paid and consumed temper attempt"),
    ("QuestActObjFactionCompetition", "quest_act_obj_faction_competitions", "zone-state faction competition authority", "QuestObjectiveEventType.FactionCompetition", "implemented", "live rank for use_result=false; final rank for use_result=true; native threshold, tie and reset rules"),
    ("QuestActObjGainExpPoint", "quest_act_obj_gain_exp_points", "Character.AddExp", "GainExpPoint", "implemented", "positive applied delta after rate and cap logic"),
    ("QuestActObjGainHonorPoint", "quest_act_obj_gain_honor_points", "Character.ChangeGamePoints", "GainHonorPoint", "implemented", "positive clamped balance delta"),
    ("QuestActObjGainLivingPoint", "quest_act_obj_gain_living_points", "Character.ChangeGamePoints", "GainLivingPoint", "implemented", "positive modifier-adjusted clamped balance delta"),
    ("QuestActObjInviteTeamFaction", "quest_act_obj_invite_team_factions", "ExpeditionManager.ReplyInvite", "InviteTeamFaction", "implemented", "accepted expedition member plus required buff 13921"),
    ("QuestActObjMonsterContrGroupHunt", "quest_act_obj_monster_contr_group_hunts", "Npc.DoDie eligible owner credit", "MonsterContribution", "implemented", "native tag/contribution owner and group membership"),
    ("QuestActObjMonsterContrHunt", "quest_act_obj_monster_contr_hunts", "Npc.DoDie eligible owner credit", "MonsterContribution", "implemented", "native tag/contribution owner and exact NPC"),
    ("QuestActObjNpcKill", "quest_act_obj_npc_kills", "QuestManager.DoOnMonsterHuntEvents", "QuestObjectiveEventType.NpcKill", "implemented", "inclusive/open ranges and native grade-id bitmask"),
    ("QuestActObjPcKill", "quest_act_obj_pc_kills", "Character.DoDie hostile relation", "QuestObjectiveEventType.PcKill", "implemented", "hostile kill only; level_gap rejects under-level victims"),
    ("QuestActObjSellBackpackGood", "quest_act_obj_sell_backpack_goods", "SpecialtyManager.SellSpecialty", "SellBackpackGood", "implemented", "after payout mail, pack/labor consumption, and market mutation"),
    ("QuestActObjCondition", "quest_act_obj_conditions", "Quest state transition", "QuestCondition", "implemented", "condition ids 1 complete and 2 fail emitted from transitions"),
    ("QuestActObjEffectFire", "quest_act_obj_effect_fires", "Skill effect Apply", "QuestObjectiveEventType.EffectFire", "implemented", "only after a non-null effect template is applied; team offer filtered by act"),
    ("QuestActObjItemGroupGather", "quest_act_obj_item_group_gathers", "DoItemsAcquiredEvents", "OnItemGroupGather", "implemented", "signed inventory delta clamped at zero; AA10 check_exist rows are false"),
    ("QuestActObjItemGroupUse", "quest_act_obj_item_group_uses", "native item-use group event", "OnItemGroupUse", "implemented", "positive successful-use count"),
    ("QuestActObjSendMail", "quest_act_obj_send_mails", "CharacterMails.SendMailToPlayer", "QuestObjectiveEventType.SendMail", "implemented", "after send and fee; all configured attachment quantities required"),
    ("QuestActObjCompleteQuest", "quest_act_obj_complete_quests", "OnQuestComplete", "OnQuestComplete(Owner", "implemented", "event counter honors count; accept_with alone seeds prior completion"),
    ("QuestActObjDistance", "quest_act_obj_distances", "UnitEvents.OnMovement", "Events.OnMovement", "implemented", "initialize once then re-evaluate on native movement"),
)

PHASE4_REWARDS = (
    ("QuestActSupplyActability", "quest_act_supply_actabilities", "CharacterActability.AddPoint/SCActability", "implemented", "expert cap saturates; durable per-attempt/per-act ledger"),
    ("QuestActSupplyArchePassPoint", "quest_act_supply_arche_pass_points", "character_arche_passes/ArchePassManager.TryAddQuestPoints", "implemented", "persisted pass in progress required; points saturate at last retail tier; durable per-act ledger"),
    ("QuestActSupplyContributionPoint", "quest_act_supply_contribution_points", "ExpeditionManager.TryChangeContributionPoints", "implemented", "member required; uint overflow rejected"),
    ("QuestActSupplyExpeditionExp", "quest_act_supply_expedition_exps", "expedition_quest_progress/SCExpeditionExpAdd", "implemented", "membership required; bigint saturation"),
    ("QuestActSupplyFactionChange", "quest_act_supply_faction_changes", "FactionManager + race-template return target", "implemented", "faction 0 returns to racial default; authored route flags are already resolved by the completed reward quest; incompatible expedition leaves before faction/housing/doodad mutation"),
    ("QuestActSupplyFamilyExp", "quest_act_supply_family_exps", "family_progress/FamilyManager/SCFamilyExpChangeNotify", "implemented", "current-level exp; retail level cap; native u64 is contributing character id; durable per-act ledger"),
    ("QuestActSupplyLeadershipPoint", "quest_act_supply_leadership_points", "character_quest_reward_progress/SCCharacterState", "implemented", "daily UTC reset and uint saturation"),
    ("QuestActSupplyLocalLp", "quest_act_supply_local_lps", "Character.AddLocalLaborPower", "implemented", "premium max_local_labor saturation"),
    ("QuestActSupplyRankedItem", "quest_act_supply_ranked_items", "exact persisted competition rank/item reward pool", "implemented", "exact rank; ledger completes only after inventory/mail distribution"),
    ("QuestActSupplyResidentCharge", "quest_act_supply_resident_charges", "resident_zone_balances/SCResidentBalanceInfo", "implemented", "quest reward adds normal charge with ulong saturation; hunting charge is preserved; settlement remains a separate non-reward lifecycle"),
    ("QuestActSupplyResidentPoint", "quest_act_supply_resident_points", "resident_service_points/SCResidentInfo", "implemented", "per-character and per-zone persistent service points; uint saturation; native active-character query contract"),
    ("QuestActSupplyResultRankedItem", "quest_act_supply_result_ranked_items", "exact persisted final rank/item reward pool", "implemented", "result=true iff final rank is 1; deferred ledger completion"),
)

PHASE2_CONDITIONS = (
    (
        "QuestActConAcceptLevelRange", "quest_act_con_accept_level_ranges", "id;level_min;level_max",
        "QuestManagerEvents.DoOnLevelUpEvents", "auto-accept while owner level is inside the inclusive range",
        "level_min<=level<=level_max; reject inverted ranges", "quest 10930; detail 2; levels 10..19",
    ),
    (
        "QuestActConAcceptNpcGroup", "quest_act_con_accept_npc_groups", "id;quest_monster_group_id",
        "CSStartQuestContextPacket -> CharacterQuests.AddQuestFromNpc", "accept only an NPC provenance whose template belongs to the native monster group",
        "reject non-NPC, zero ids, and non-members", "145 enabled AA10 group starters",
    ),
    (
        "QuestActConReportNpcGroup", "quest_act_con_report_npc_groups", "id;quest_monster_group_id;use_alias;quest_act_obj_alias_id",
        "QuestManagerEvents.DoReportEvents/OnReportNpc", "select reward, move Progress to Ready, and evaluate only for a member NPC",
        "reject zero ids, non-members, and reports before objective readiness", "267 rows; one native-disabled row",
    ),
    (
        "QuestActConAcceptComponent", "quest_act_con_accept_components", "id;quest_context_id",
        "native component/event starter or cross-quest successor", "accept self provenance or materialize the referenced successor once from a reward component",
        "reject zero and unresolved cross references", "299 self references and 176 cross references",
    ),
    (
        "QuestActCheckGuard", "quest_act_check_guards", "id;npc_id",
        "live NPC state in the owner's WorldInstance", "gate the component on a matching living guard/escort NPC",
        "reject missing, mismatched, dead, and zero-HP NPCs", "quest 11198 escort-failure sign fixture; NPC 19131",
    ),
    (
        "QuestActConAcceptNpcEmotion", "quest_act_con_accept_npc_emotions + anims", "id;npc_id;emotion -> anims.id",
        "CSExpressEmotionPacket -> QuestManagerEvents.DoOnExpressFireEvents", "auto-accept with exact NPC and animation provenance stored on the quest instance",
        "reject normal NPC acceptance, wrong NPC, zero or wrong animation id", "quests 10740/10766; fist_ac_worship -> anims.id 124",
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def normalize_bool(value: object) -> bool:
    return str(value).lower() in {"1", "t", "true"}


def source_inventory(args: argparse.Namespace) -> list[dict[str, object]]:
    artifacts = [
        ("game_decrypted.sqlite3", args.full_db, EXPECTED["full_db_sha256"], "computed"),
        ("compact.sqlite3", args.compact_db, EXPECTED["compact_db_sha256"], "computed"),
        ("x2game.dll", args.x2game, EXPECTED["x2game_sha256"], "computed"),
    ]
    rows: list[dict[str, object]] = []
    for name, path, expected, mode in artifacts:
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"{name}: SHA-256 drift: expected {expected}, got {actual}")
        rows.append(
            {"name": name, "path": str(path), "size": path.stat().st_size, "sha256": actual, "hash_mode": mode}
        )

    game_pak = args.game_pak
    if game_pak.stat().st_size != EXPECTED["game_pak_size"]:
        raise RuntimeError(
            f"game_pak: size drift: expected {EXPECTED['game_pak_size']}, got {game_pak.stat().st_size}"
        )
    rows.append(
        {
            "name": "game_pak",
            "path": str(game_pak),
            "size": game_pak.stat().st_size,
            "sha256": EXPECTED["game_pak_sha256"],
            "hash_mode": "frozen by Get-FileHash on 2026-08-20; size rechecked per build",
        }
    )
    return rows


def quick_check(path: Path) -> str:
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        return str(db.execute("PRAGMA quick_check").fetchone()[0])


def output_integrity_checks(path: Path) -> dict[str, str]:
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        return {
            "quick_check": str(db.execute("PRAGMA quick_check").fetchone()[0]),
            "integrity_check": str(db.execute("PRAGMA integrity_check").fetchone()[0]),
        }


def inspect_server(repo: Path) -> tuple[set[str], set[str], set[str], set[str], dict[str, str], str]:
    quest_root = repo / "AAEmu.Game" / "Models" / "Game" / "Quests"
    classes: set[str] = set()
    objective_types: set[str] = set()
    stubs: set[str] = set()
    notes: dict[str, str] = dict(PARTIAL_TYPES)

    for path in sorted(quest_root.rglob("QuestAct*.cs")):
        text = path.read_text(encoding="utf-8-sig")
        for match in re.finditer(r"\bclass\s+(QuestAct\w+)", text):
            name = match.group(1)
            classes.add(name)
            class_tail = text[match.start():]
            next_class = re.search(r"\npublic\s+(?:sealed\s+)?class\s+QuestAct", class_tail[1:])
            class_text = class_tail[: next_class.start() + 1] if next_class else class_tail
            if re.search(r"CountsAsAnObjective\s*=>\s*true", class_text):
                objective_types.add(name)
            if re.search(r"return\s+base\.RunAct\s*\(", class_text):
                stubs.add(name)
                notes[name] = "stub: delegates RunAct to base"

    objective_types.update(row[0] for row in PHASE3_OBJECTIVES)
    manager_root = repo / "AAEmu.Game" / "Core" / "Managers"
    manager_text = "\n".join(
        path.read_text(encoding="utf-8-sig") for path in sorted(manager_root.glob("QuestManager*.cs"))
    )
    loaders = set(re.findall(r'GetComponentByActTemplate\("(QuestAct\w+)"', manager_text))
    loaders.update(re.findall(r'LoadPhase(?:3|4)Rows\([^\n]+"(QuestAct\w+)"', manager_text))
    server_text = "\n".join(
        path.read_text(encoding="utf-8-sig") for path in sorted((repo / "AAEmu.Game").rglob("*.cs"))
    )
    return classes, loaders, objective_types, stubs, notes, server_text


def inspect_loader_tables(repo: Path) -> dict[str, str]:
    manager_root = repo / "AAEmu.Game" / "Core" / "Managers"
    manager_text = "\n".join(
        path.read_text(encoding="utf-8-sig") for path in sorted(manager_root.glob("QuestManager*.cs"))
    )
    table_matches = list(re.finditer(
        r'command\.CommandText\s*=\s*"SELECT \* FROM ([a-z0-9_]+)"', manager_text
    ))
    table_positions = [match.start() for match in table_matches]
    loader_tables: dict[str, str] = {}
    for type_match in re.finditer(r'GetComponentByActTemplate\("(QuestAct\w+)"', manager_text):
        index = bisect_right(table_positions, type_match.start()) - 1
        if index >= 0:
            loader_tables[type_match.group(1)] = table_matches[index].group(1)

    # Phase 3/4 share generic loaders, so their exact table/type pairs live at each callsite.
    loader_tables.update({
        match.group(2): match.group(1)
        for match in re.finditer(
            r'LoadPhase(?:3|4)Rows\(connection,\s*"([^"]+)",\s*"(QuestAct\w+)"',
            manager_text,
        )
    })
    return loader_tables


def read_quest_graph(full_db: Path, compact_db: Path, repo: Path) -> dict[str, object]:
    classes, loaders, objective_types, stub_types, implementation_notes, server_text = inspect_server(repo)
    loader_tables = inspect_loader_tables(repo)
    with sqlite3.connect(f"file:{full_db.as_posix()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        contexts = {row["id"]: dict(row) for row in db.execute("SELECT * FROM quest_contexts ORDER BY id")}
        components = {row["id"]: dict(row) for row in db.execute("SELECT * FROM quest_components ORDER BY id")}
        acts = [dict(row) for row in db.execute("SELECT * FROM quest_acts ORDER BY id")]
        sqlite_tables = {
            str(row[0]) for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        detail_ids_by_type: dict[str, set[int]] = {}
        for detail_type, table_name in loader_tables.items():
            if table_name in sqlite_tables:
                detail_ids_by_type[detail_type] = {
                    int(row[0]) for row in db.execute(f"SELECT id FROM {table_name}")
                }

        type_counts: dict[str, Counter[str]] = defaultdict(Counter)
        bindings: list[tuple[object, ...]] = []
        objective_counts: dict[tuple[int, int], int] = defaultdict(int)
        for act in acts:
            component = components.get(act["quest_component_id"])
            quest_id = int(component["quest_context_id"]) if component else 0
            context = contexts.get(quest_id)
            enabled = normalize_bool(act["enable"])
            detail_type = str(act["act_detail_type"] or "<null>")
            type_counts[detail_type]["total"] += 1
            type_counts[detail_type]["enabled" if enabled else "disabled"] += 1
            if enabled and context and int(context["category_id"]) != 45:
                type_counts[detail_type]["runtime_enabled"] += 1
            if enabled and detail_type in objective_types and component:
                objective_counts[(quest_id, int(component["component_kind_id"]))] += 1
            bindings.append(
                (
                    int(act["id"]),
                    int(act["quest_component_id"]),
                    quest_id,
                    int(context["category_id"]) if context else None,
                    int(act["act_detail_id"] or 0),
                    detail_type,
                    1 if enabled else 0,
                )
            )

        coverage: list[tuple[object, ...]] = []
        for detail_type in sorted(type_counts):
            count = type_counts[detail_type]
            has_class = detail_type in classes
            has_loader = detail_type in loaders
            if not has_class:
                classification = "missing_server_class"
            elif not has_loader:
                classification = "missing_detail_loader"
            elif detail_type in stub_types or detail_type in implementation_notes:
                classification = "stub_or_partial"
            else:
                classification = "implemented_loader_present"
            coverage.append(
                (
                    detail_type,
                    count["total"],
                    count["enabled"],
                    count["disabled"],
                    count["runtime_enabled"],
                    int(has_class),
                    int(has_loader),
                    classification,
                    implementation_notes.get(detail_type, ""),
                )
            )

        overflow_rows = [
            (quest_id, kind, count, "exceeds_10" if count > 10 else "exceeds_5")
            for (quest_id, kind), count in sorted(objective_counts.items())
            if count > 5
        ]

        nuia_quests: list[tuple[object, ...]] = []
        for quest in sorted((q for q in contexts.values() if int(q["category_id"]) == 3), key=lambda q: q["id"]):
            quest_acts = [b for b in bindings if b[2] == quest["id"]]
            unsupported = sum(
                1
                for b in quest_acts
                if b[6] and (b[5] not in classes or b[5] not in loaders)
            )
            nuia_quests.append(
                (
                    int(quest["id"]), str(quest["name"]), int(quest["chapter_idx"]),
                    int(quest["quest_idx"]), int(quest["zone_id"]), len(quest_acts),
                    sum(1 for b in quest_acts if not b[6]), unsupported,
                )
            )

        integrity = {
            "quest_contexts": len(contexts),
            "quest_components": len(components),
            "quest_acts": len(acts),
            "distinct_act_types": len(type_counts),
            "orphan_components": db.execute(
                "SELECT count(*) FROM quest_components c LEFT JOIN quest_contexts q ON q.id=c.quest_context_id WHERE q.id IS NULL"
            ).fetchone()[0],
            "orphan_acts": sum(1 for a in acts if a["quest_component_id"] not in components),
            "disabled_acts": sum(1 for a in acts if not normalize_bool(a["enable"])),
            "nuia_quests": len(nuia_quests),
            "nuia_acts": sum(row[5] for row in nuia_quests),
            "nuia_unsupported_enabled_acts": sum(row[7] for row in nuia_quests),
            "nuia_disabled_acts": sum(row[6] for row in nuia_quests),
            "objective_groups_over_5": len(overflow_rows),
            "objective_groups_over_10": sum(1 for row in overflow_rows if row[2] > 10),
            "arche_pass_mission_config_enum_keys": db.execute(
                "SELECT count(*) FROM enum_content_configs WHERE id BETWEEN 277 AND 280"
            ).fetchone()[0],
            "arche_pass_mission_config_value_rows": db.execute(
                "SELECT count(*) FROM content_configs WHERE kind_id BETWEEN 277 AND 280"
            ).fetchone()[0],
        }
        integrity["enabled_act_refs"] = sum(count["enabled"] for count in type_counts.values())
        integrity["runtime_enabled_act_refs"] = sum(count["runtime_enabled"] for count in type_counts.values())
        integrity["implemented_enabled_act_refs"] = sum(
            row[2] for row in coverage if row[7] == "implemented_loader_present"
        )
        integrity["unresolved_enabled_act_refs"] = sum(
            row[2] for row in coverage if row[7] != "implemented_loader_present"
        )
        integrity["unclassified_act_types"] = sum(
            1 for row in coverage if row[7] != "implemented_loader_present"
        )
        integrity["missing_detail_table_enabled_refs"] = sum(
            1 for act in acts
            if normalize_bool(act["enable"]) and str(act["act_detail_type"] or "<null>") not in detail_ids_by_type
        )
        integrity["missing_detail_row_enabled_refs"] = sum(
            1 for act in acts
            if normalize_bool(act["enable"])
            and str(act["act_detail_type"] or "<null>") in detail_ids_by_type
            and int(act["act_detail_id"] or 0) not in detail_ids_by_type[str(act["act_detail_type"] or "<null>")]
        )
        integrity["duplicate_runtime_detail_bindings"] = int(db.execute(
            "SELECT count(*) FROM ("
            "SELECT a.act_detail_type, a.act_detail_id FROM quest_acts a "
            "JOIN quest_components c ON c.id=a.quest_component_id "
            "JOIN quest_contexts q ON q.id=c.quest_context_id "
            "WHERE lower(CAST(a.enable AS TEXT)) IN ('1','t','true') AND q.category_id<>45 "
            "GROUP BY a.act_detail_type,a.act_detail_id HAVING count(*)>1)"
        ).fetchone()[0])

        coverage_by_type = {row[0]: row for row in coverage}
        phase2_evidence = {
            "QuestActConAcceptLevelRange": dict(db.execute(
                "SELECT count(*) rows, min(level_min) min_level, max(level_max) max_level, "
                "sum(CASE WHEN level_min > level_max THEN 1 ELSE 0 END) invalid_ranges "
                "FROM quest_act_con_accept_level_ranges"
            ).fetchone()),
            "QuestActConAcceptNpcGroup": dict(db.execute(
                "SELECT count(*) rows, count(DISTINCT x.quest_monster_group_id) groups, "
                "sum(CASE WHEN g.id IS NULL THEN 1 ELSE 0 END) unresolved_group_rows, "
                "count(DISTINCT CASE WHEN g.id IS NULL THEN x.quest_monster_group_id END) unresolved_groups, "
                "sum(CASE WHEN g.id IS NOT NULL AND n.quest_monster_group_id IS NULL THEN 1 ELSE 0 END) empty_group_rows "
                "FROM quest_act_con_accept_npc_groups x LEFT JOIN quest_monster_groups g ON g.id=x.quest_monster_group_id LEFT JOIN "
                "(SELECT DISTINCT quest_monster_group_id FROM quest_monster_npcs) n "
                "ON n.quest_monster_group_id=x.quest_monster_group_id"
            ).fetchone()),
            "QuestActConReportNpcGroup": dict(db.execute(
                "SELECT count(*) rows, count(DISTINCT x.quest_monster_group_id) groups, "
                "sum(CASE WHEN g.id IS NULL THEN 1 ELSE 0 END) unresolved_group_rows, "
                "count(DISTINCT CASE WHEN g.id IS NULL THEN x.quest_monster_group_id END) unresolved_groups, "
                "sum(CASE WHEN g.id IS NOT NULL AND n.quest_monster_group_id IS NULL THEN 1 ELSE 0 END) empty_group_rows, "
                "sum(CASE WHEN lower(CAST(use_alias AS TEXT)) IN ('1','t','true') THEN 1 ELSE 0 END) alias_rows "
                "FROM quest_act_con_report_npc_groups x LEFT JOIN quest_monster_groups g ON g.id=x.quest_monster_group_id LEFT JOIN "
                "(SELECT DISTINCT quest_monster_group_id FROM quest_monster_npcs) n "
                "ON n.quest_monster_group_id=x.quest_monster_group_id"
            ).fetchone()),
            "QuestActConAcceptComponent": dict(db.execute(
                "SELECT count(*) rows, sum(CASE WHEN c.quest_context_id=x.quest_context_id THEN 1 ELSE 0 END) self_refs, "
                "sum(CASE WHEN c.quest_context_id<>x.quest_context_id THEN 1 ELSE 0 END) cross_refs, "
                "sum(CASE WHEN q.id IS NULL THEN 1 ELSE 0 END) unresolved_refs "
                "FROM quest_act_con_accept_components x "
                "JOIN quest_acts a ON a.act_detail_type='QuestActConAcceptComponent' AND a.act_detail_id=x.id "
                "JOIN quest_components c ON c.id=a.quest_component_id "
                "LEFT JOIN quest_contexts q ON q.id=x.quest_context_id"
            ).fetchone()),
            "QuestActCheckGuard": dict(db.execute(
                "SELECT count(*) rows, count(DISTINCT g.npc_id) npc_templates, "
                "sum(CASE WHEN n.id IS NULL THEN 1 ELSE 0 END) unresolved_npcs "
                "FROM quest_act_check_guards g LEFT JOIN npcs n ON n.id=g.npc_id"
            ).fetchone()),
            "QuestActConAcceptNpcEmotion": dict(db.execute(
                "SELECT count(*) rows, count(DISTINCT e.npc_id) npc_templates, "
                "sum(CASE WHEN a.id IS NULL THEN 1 ELSE 0 END) unresolved_emotions, "
                "min(a.id) min_anim_id, max(a.id) max_anim_id "
                "FROM quest_act_con_accept_npc_emotions e LEFT JOIN anims a ON a.name=e.emotion"
            ).fetchone()),
        }
        phase2_dossier: list[tuple[object, ...]] = []
        for detail_type, table_name, fields, producer, transition, boundaries, fixture in PHASE2_CONDITIONS:
            cov = coverage_by_type[detail_type]
            phase2_dossier.append(
                (
                    detail_type, table_name, fields, producer, transition, boundaries, fixture,
                    cov[1], cov[2], cov[3], cov[5], cov[6], cov[7],
                    json.dumps(phase2_evidence[detail_type], sort_keys=True, separators=(",", ":")),
                )
            )

        phase2_types = {row[0] for row in phase2_dossier}
        integrity["phase2_enabled_refs"] = sum(row[8] for row in phase2_dossier)
        integrity["phase2_unimplemented_enabled_refs"] = sum(
            row[8] for row in phase2_dossier if row[12] != "implemented_loader_present"
        )
        integrity["phase2_constant_return_enabled_refs"] = sum(
            type_counts[name]["enabled"] for name in phase2_types if name in stub_types
        )
        integrity["phase2_unresolved_native_reference_rows"] = sum(
            int(phase2_evidence[name].get("unresolved_group_rows", 0) or 0)
            + int(phase2_evidence[name].get("unresolved_refs", 0) or 0)
            + int(phase2_evidence[name].get("unresolved_npcs", 0) or 0)
            + int(phase2_evidence[name].get("unresolved_emotions", 0) or 0)
            for name in phase2_types
        )

        phase3_dossier: list[tuple[object, ...]] = []
        for detail_type, table_name, producer, producer_token, status, boundary in PHASE3_OBJECTIVES:
            cov = coverage_by_type[detail_type]
            detail_rows = int(db.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0])
            producer_present = int(bool(producer_token) and producer_token in server_text)
            phase3_dossier.append((
                detail_type, table_name, producer, status, boundary, detail_rows,
                cov[1], cov[2], cov[3], cov[5], cov[6], cov[7], producer_present,
            ))
        integrity["phase3_enabled_refs"] = sum(row[7] for row in phase3_dossier)
        integrity["phase3_implemented_enabled_refs"] = sum(
            row[7] for row in phase3_dossier if row[3] == "implemented" and row[12]
        )
        integrity["phase3_blocked_enabled_refs"] = sum(
            row[7] for row in phase3_dossier if row[3].startswith("blocked_")
        )
        integrity["phase3_missing_producer_enabled_refs"] = sum(
            row[7] for row in phase3_dossier if row[3] == "implemented" and not row[12]
        )

        phase4_dossier: list[tuple[object, ...]] = []
        for detail_type, table_name, consumer, status, boundary in PHASE4_REWARDS:
            cov = coverage_by_type[detail_type]
            detail_rows = int(db.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0])
            phase4_dossier.append((
                detail_type, table_name, consumer, status, boundary, detail_rows,
                cov[1], cov[2], cov[3], cov[5], cov[6], cov[7],
            ))
        integrity["phase4_enabled_refs"] = sum(row[7] for row in phase4_dossier)
        integrity["phase4_implemented_enabled_refs"] = sum(
            row[7] for row in phase4_dossier if row[3] == "implemented"
        )
        integrity["phase4_candidate_enabled_refs"] = sum(
            row[7] for row in phase4_dossier if row[3] == "implemented_candidate"
        )
        integrity["phase4_blocked_enabled_refs"] = sum(
            row[7] for row in phase4_dossier if row[3].startswith("blocked_")
        )
        integrity["phase4_reward_ledger_present"] = int(
            "class QuestRewardLedgerManager" in server_text and
            "RewardAttemptId" in server_text and
            "IQuestRewardPreflight" in server_text and
            "StageDeferredRewardActsForSave" in server_text and
            "CompleteWithinSave" in server_text
        )

    with sqlite3.connect(f"file:{compact_db.as_posix()}?mode=ro", uri=True) as compact:
        integrity.update(
            {
                "compact_quest_contexts": compact.execute("SELECT count(*) FROM quest_contexts").fetchone()[0],
                "compact_quest_components": compact.execute("SELECT count(*) FROM quest_components").fetchone()[0],
                "compact_quest_acts": compact.execute("SELECT count(*) FROM quest_acts").fetchone()[0],
                "compact_orphan_components": compact.execute(
                    "SELECT count(*) FROM quest_components c LEFT JOIN quest_contexts q ON q.id=c.quest_context_id WHERE q.id IS NULL"
                ).fetchone()[0],
            }
        )

    return {
        "coverage": coverage,
        "bindings": bindings,
        "overflow": overflow_rows,
        "nuia_quests": nuia_quests,
        "integrity": integrity,
        "phase2_dossier": phase2_dossier,
        "phase3_dossier": phase3_dossier,
        "phase4_dossier": phase4_dossier,
    }


def evaluate_strict_gate(graph: dict[str, object]) -> list[dict[str, object]]:
    metrics = graph["integrity"]
    findings: list[dict[str, object]] = []

    def require_zero(metric: str) -> None:
        value = int(metrics[metric])
        if value != 0:
            findings.append({"metric": metric, "actual": value, "expected": 0})

    for metric in (
        "orphan_components",
        "orphan_acts",
        "nuia_unsupported_enabled_acts",
        "unresolved_enabled_act_refs",
        "unclassified_act_types",
        "missing_detail_table_enabled_refs",
        "missing_detail_row_enabled_refs",
        "duplicate_runtime_detail_bindings",
        "phase2_unimplemented_enabled_refs",
        "phase2_constant_return_enabled_refs",
        "phase3_blocked_enabled_refs",
        "phase3_missing_producer_enabled_refs",
        "phase4_candidate_enabled_refs",
        "phase4_blocked_enabled_refs",
    ):
        require_zero(metric)

    for implemented, enabled in (
        ("implemented_enabled_act_refs", "enabled_act_refs"),
        ("phase3_implemented_enabled_refs", "phase3_enabled_refs"),
        ("phase4_implemented_enabled_refs", "phase4_enabled_refs"),
    ):
        if int(metrics[implemented]) != int(metrics[enabled]):
            findings.append({
                "metric": implemented,
                "actual": int(metrics[implemented]),
                "expected_metric": enabled,
                "expected": int(metrics[enabled]),
            })

    if int(metrics["phase4_reward_ledger_present"]) != 1:
        findings.append({"metric": "phase4_reward_ledger_present", "actual": 0, "expected": 1})

    return findings


def create_sqlite(path: Path, artifacts: list[dict[str, object]], graph: dict[str, object]) -> None:
    if path.exists():
        path.unlink()
    db = sqlite3.connect(path)
    db.executescript(
        """
        PRAGMA page_size=4096;
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA auto_vacuum=NONE;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
        CREATE TABLE source_artifacts (
            name TEXT PRIMARY KEY, path TEXT NOT NULL, size INTEGER NOT NULL,
            sha256 TEXT NOT NULL, hash_mode TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE quest_inventory (metric TEXT PRIMARY KEY, value INTEGER NOT NULL) WITHOUT ROWID;
        CREATE TABLE act_type_coverage (
            act_detail_type TEXT PRIMARY KEY, total_refs INTEGER NOT NULL,
            enabled_refs INTEGER NOT NULL, disabled_refs INTEGER NOT NULL,
            runtime_enabled_refs INTEGER NOT NULL, server_class_present INTEGER NOT NULL,
            detail_loader_present INTEGER NOT NULL, classification TEXT NOT NULL, notes TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE quest_act_bindings (
            act_id INTEGER PRIMARY KEY, component_id INTEGER NOT NULL, quest_id INTEGER NOT NULL,
            category_id INTEGER, detail_id INTEGER NOT NULL, detail_type TEXT NOT NULL, enabled INTEGER NOT NULL
        );
        CREATE TABLE objective_capacity_findings (
            quest_id INTEGER NOT NULL, component_kind INTEGER NOT NULL, objective_count INTEGER NOT NULL,
            classification TEXT NOT NULL, PRIMARY KEY (quest_id, component_kind)
        ) WITHOUT ROWID;
        CREATE TABLE nuia_quests (
            quest_id INTEGER PRIMARY KEY, name TEXT NOT NULL, chapter_idx INTEGER NOT NULL,
            quest_idx INTEGER NOT NULL, logical_zone_id INTEGER NOT NULL, act_count INTEGER NOT NULL,
            disabled_acts INTEGER NOT NULL, unsupported_enabled_acts INTEGER NOT NULL
        );
        CREATE TABLE nuia_zone_crosswalk (
            logical_zone_id INTEGER PRIMARY KEY, native_zone_key INTEGER NOT NULL,
            partition_status TEXT NOT NULL, chapter_scope TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE phase2_condition_dossier (
            act_detail_type TEXT PRIMARY KEY, detail_table TEXT NOT NULL, table_fields TEXT NOT NULL,
            producer_event TEXT NOT NULL, transition TEXT NOT NULL, boundary_values TEXT NOT NULL,
            fixture TEXT NOT NULL, total_refs INTEGER NOT NULL, enabled_refs INTEGER NOT NULL,
            disabled_refs INTEGER NOT NULL, server_class_present INTEGER NOT NULL,
            detail_loader_present INTEGER NOT NULL, implementation_status TEXT NOT NULL,
            evidence_checks TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE phase3_objective_dossier (
            act_detail_type TEXT PRIMARY KEY, detail_table TEXT NOT NULL,
            producer_event TEXT NOT NULL, producer_status TEXT NOT NULL,
            boundary_values TEXT NOT NULL, detail_rows INTEGER NOT NULL,
            total_refs INTEGER NOT NULL, enabled_refs INTEGER NOT NULL,
            disabled_refs INTEGER NOT NULL, server_class_present INTEGER NOT NULL,
            detail_loader_present INTEGER NOT NULL, implementation_status TEXT NOT NULL,
            producer_callsite_present INTEGER NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE phase4_reward_dossier (
            act_detail_type TEXT PRIMARY KEY, detail_table TEXT NOT NULL,
            consumer TEXT NOT NULL, status TEXT NOT NULL, boundary_values TEXT NOT NULL,
            detail_rows INTEGER NOT NULL, total_refs INTEGER NOT NULL, enabled_refs INTEGER NOT NULL,
            disabled_refs INTEGER NOT NULL, server_class_present INTEGER NOT NULL,
            detail_loader_present INTEGER NOT NULL, implementation_status TEXT NOT NULL
        ) WITHOUT ROWID;
        """
    )
    db.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [
            ("schema", "aa10-quest-stage40-v4"),
            ("client", "ArcheAge Returns 10.0.2.13 r575"),
            ("authority", "AA10 full SQLite + retail compact + exact client + target server"),
            ("generated_at", "deterministic-no-wall-clock"),
        ],
    )
    db.executemany(
        "INSERT INTO source_artifacts VALUES (:name, :path, :size, :sha256, :hash_mode)", artifacts
    )
    db.executemany("INSERT INTO quest_inventory VALUES (?, ?)", sorted(graph["integrity"].items()))
    db.executemany("INSERT INTO act_type_coverage VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", graph["coverage"])
    db.executemany("INSERT INTO quest_act_bindings VALUES (?, ?, ?, ?, ?, ?, ?)", graph["bindings"])
    db.executemany("INSERT INTO objective_capacity_findings VALUES (?, ?, ?, ?)", graph["overflow"])
    db.executemany("INSERT INTO nuia_quests VALUES (?, ?, ?, ?, ?, ?, ?, ?)", graph["nuia_quests"])
    db.executemany("INSERT INTO nuia_zone_crosswalk VALUES (?, ?, ?, ?)", NUIA_ZONE_CROSSWALK)
    db.executemany("INSERT INTO phase2_condition_dossier VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", graph["phase2_dossier"])
    db.executemany("INSERT INTO phase3_objective_dossier VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", graph["phase3_dossier"])
    db.executemany("INSERT INTO phase4_reward_dossier VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", graph["phase4_dossier"])
    db.commit()
    db.execute("VACUUM")
    db.close()


def write_csv(path: Path, header: tuple[str, ...], rows: list[tuple[object, ...]] | tuple[tuple[object, ...], ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def build(args: argparse.Namespace) -> None:
    args.output.mkdir(parents=True, exist_ok=True)
    artifacts = source_inventory(args)
    checks = {"full_db": quick_check(args.full_db), "compact_db": quick_check(args.compact_db)}
    if checks != {"full_db": "ok", "compact_db": "ok"}:
        raise RuntimeError(f"SQLite quick_check failed: {checks}")
    graph = read_quest_graph(args.full_db, args.compact_db, args.repo)
    gate_findings = evaluate_strict_gate(graph)
    gate_report = {
        "schema": "aa10-quest-stage40-strict-gate-v1",
        "status": "pass" if not gate_findings else "fail",
        "findings": gate_findings,
    }
    (args.output / "strict-gate.json").write_text(
        json.dumps(gate_report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    sqlite_path = args.output / "quest-stage40.sqlite3"
    create_sqlite(sqlite_path, artifacts, graph)
    generated_checks = output_integrity_checks(sqlite_path)
    if generated_checks != {"quick_check": "ok", "integrity_check": "ok"}:
        raise RuntimeError(f"Generated SQLite integrity failed: {generated_checks}")
    write_csv(
        args.output / "act-type-coverage.csv",
        ("act_detail_type", "total_refs", "enabled_refs", "disabled_refs", "runtime_enabled_refs",
         "server_class_present", "detail_loader_present", "classification", "notes"),
        graph["coverage"],
    )
    write_csv(
        args.output / "phase2-condition-dossier.csv",
        ("act_detail_type", "detail_table", "table_fields", "producer_event", "transition",
         "boundary_values", "fixture", "total_refs", "enabled_refs", "disabled_refs",
         "server_class_present", "detail_loader_present", "implementation_status", "evidence_checks"),
        graph["phase2_dossier"],
    )
    write_csv(
        args.output / "phase3-objective-dossier.csv",
        ("act_detail_type", "detail_table", "producer_event", "producer_status", "boundary_values",
         "detail_rows", "total_refs", "enabled_refs", "disabled_refs", "server_class_present",
         "detail_loader_present", "implementation_status", "producer_callsite_present"),
        graph["phase3_dossier"],
    )
    write_csv(
        args.output / "phase4-reward-dossier.csv",
        ("act_detail_type", "detail_table", "consumer", "status", "boundary_values",
         "detail_rows", "total_refs", "enabled_refs", "disabled_refs", "server_class_present",
         "detail_loader_present", "implementation_status"),
        graph["phase4_dossier"],
    )
    write_csv(
        args.output / "nuia-quests.csv",
        ("quest_id", "name", "chapter_idx", "quest_idx", "logical_zone_id", "act_count",
         "disabled_acts", "unsupported_enabled_acts"),
        graph["nuia_quests"],
    )
    write_csv(
        args.output / "nuia-zone-crosswalk.csv",
        ("logical_zone_id", "native_zone_key", "partition_status", "chapter_scope"),
        NUIA_ZONE_CROSSWALK,
    )

    outputs = {}
    for name in ("quest-stage40.sqlite3", "act-type-coverage.csv", "phase2-condition-dossier.csv", "phase3-objective-dossier.csv", "phase4-reward-dossier.csv", "nuia-quests.csv", "nuia-zone-crosswalk.csv", "strict-gate.json"):
        file_path = args.output / name
        outputs[name] = {"size": file_path.stat().st_size, "sha256": sha256(file_path)}
    manifest = {
        "schema": "aa10-quest-stage40-manifest-v8",
        "inputs": artifacts,
        "sqlite_checks": checks,
        "generated_sqlite_checks": generated_checks,
        "metrics": graph["integrity"],
        "strict_gate": gate_report,
        "outputs": outputs,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False))
    if args.mode == "strict" and gate_findings:
        raise RuntimeError(f"Stage 40 strict gate failed: {gate_findings}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-db", type=Path, default=DEFAULT_ROOT / "data" / "sqlite" / "authoritative" / "game_decrypted.sqlite3")
    parser.add_argument("--compact-db", type=Path, default=DEFAULT_CLIENT / "game" / "db" / "compact.sqlite3")
    parser.add_argument("--x2game", type=Path, default=DEFAULT_CLIENT / "Bin64" / "x2game.dll")
    parser.add_argument("--game-pak", type=Path, default=DEFAULT_CLIENT / "game_pak")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mode", choices=("report", "strict"), default="report")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
