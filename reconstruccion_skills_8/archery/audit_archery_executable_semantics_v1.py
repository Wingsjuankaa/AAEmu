#!/usr/bin/env python3
"""Audit every executable AA8 Archery entrypoint with the shared branch walker."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SORCERY_TOOLS = ROOT / "reconstruccion_skills_8" / "sorcery"
sys.path.insert(0, str(SORCERY_TOOLS))

import audit_sorcery_executable_semantics_v3 as shared  # noqa: E402


HERE = Path(__file__).resolve().parent
shared.DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-archery-v5.sqlite3"
)
shared.DEFAULT_MANIFEST = HERE / "generated" / "archery-runtime-v5.manifest.json"
shared.DEFAULT_JSON = HERE / "generated" / "archery-executable-semantics-audit-v1.json"
shared.DEFAULT_CSV = HERE / "generated" / "archery-executable-semantics-matrix-v1.csv"

shared.ABILITY_ID = 6
shared.BASE_ROOTS = (
    10694, 10708, 11368, 11933, 12133, 12759,
    13281, 14835, 15073, 15096, 16210, 23592,
)
shared.HEIR_ROOTS = (
    36468, 36469, 36470, 36471, 36472, 36473,
    39663, 39666, 41219, 41221, 42849, 42851,
)
shared.PUBLIC_ROOTS = shared.BASE_ROOTS + shared.HEIR_ROOTS
shared.LOGIN_STAGE_ROOTS = (12792, 12793, 12794)
shared.CONTEXTUAL_ROOTS = (
    14836, 14837, 38893, 39664, 39665, 39667, 39668, 40580,
)
shared.INTERNAL_ROOTS = shared.LOGIN_STAGE_ROOTS + shared.CONTEXTUAL_ROOTS
shared.AUDITED_ROOTS = shared.PUBLIC_ROOTS + shared.INTERNAL_ROOTS

shared.SPECIAL_STATES.update(
    {
        "ResetCooldown": "implemented_deterministic_aa8_100_percent_contract",
        "Detach": "client_declarative_no_server_mutation_demonstrated",
        "RemoveDoodad": "client_declarative_no_server_mutation_demonstrated",
        "CombatDice": "implemented_single_roll_reused_by_damage_and_condition",
        "SetVariable": "implemented",
        "ChargeCooldown": "implemented_client_charge_recharge_lane",
    }
)
shared.CORE_STATES.update(
    {
        "BubbleEffect": "implemented_localized_target_bubble",
        "SkillController": "implemented_native_controller_scheduler",
    }
)
shared.CONDITION_STATES.update(
    {
        "CastingUseable": "implemented_inclusive_charge_bands_and_release",
        "UnitReqs": "implemented_owner_keyed_target_requirements",
    }
)
shared.BUFF_TRIGGER_EVENT_STATES.update(
    {
        "Landing": "implemented_before_remove_on_land",
        "RemoveOnMove": "implemented_before_remove_on_move",
    }
)


def _owner_keyed_tag_contract(runtime_path: Path) -> dict[str, Any]:
    """Audit relations consumed outside the directed plot/effect graph.

    ``tagged_skills`` is loaded into a server cache keyed by skill and tag.  A
    graph walker starting at a skill or passive buff cannot discover that
    reverse lookup, so it must be closed and validated explicitly.
    """

    root_ids = tuple(shared.AUDITED_ROOTS)
    marks = ",".join("?" for _ in root_ids)
    connection = sqlite3.connect(f"file:{runtime_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tagged_rows = connection.execute(
            f"""
            SELECT id, skill_id, tag_id
            FROM tagged_skills
            WHERE skill_id IN ({marks})
            ORDER BY skill_id, tag_id, id
            """,
            root_ids,
        ).fetchall()
        duplicate_pairs = connection.execute(
            f"""
            SELECT skill_id, tag_id, COUNT(*) AS row_count
            FROM tagged_skills
            WHERE skill_id IN ({marks})
            GROUP BY skill_id, tag_id
            HAVING COUNT(*) <> 1
            ORDER BY skill_id, tag_id
            """,
            root_ids,
        ).fetchall()
        passive_rows = connection.execute(
            "SELECT id, buff_id FROM passive_buffs WHERE ability_id=? ORDER BY id",
            (shared.ABILITY_ID,),
        ).fetchall()
        passive_buff_ids = tuple(int(row["buff_id"]) for row in passive_rows)
        passive_by_buff = {
            int(row["buff_id"]): int(row["id"]) for row in passive_rows
        }
        passive_marks = ",".join("?" for _ in passive_buff_ids)
        modifiers = connection.execute(
            f"""
            SELECT owner_id, skill_attribute_id, skill_id, tag_id,
                   target_buff_id, target_tag_id, value
            FROM skill_modifiers
            WHERE owner_type='Buff'
              AND owner_id IN ({passive_marks})
            ORDER BY owner_id, skill_attribute_id, skill_id, tag_id
            """,
            passive_buff_ids,
        ).fetchall() if passive_buff_ids else []

        modifier_contracts: list[dict[str, Any]] = []
        missing_modifier_consumers: list[dict[str, int]] = []
        for modifier in modifiers:
            tag_id = int(modifier["tag_id"] or 0)
            skill_id = int(modifier["skill_id"] or 0)
            if tag_id:
                consumers = connection.execute(
                    """
                    SELECT skill_id FROM tagged_skills
                    WHERE tag_id=? ORDER BY skill_id
                    """,
                    (tag_id,),
                ).fetchall()
                consumer_ids = [int(row["skill_id"]) for row in consumers]
            elif skill_id:
                consumer_ids = [skill_id]
            else:
                consumer_ids = []
            record = {
                "passive_id": passive_by_buff[int(modifier["owner_id"])],
                "owner_buff_id": int(modifier["owner_id"]),
                "skill_attribute_id": int(modifier["skill_attribute_id"]),
                "skill_id": skill_id,
                "tag_id": tag_id,
                "target_buff_id": int(modifier["target_buff_id"] or 0),
                "target_tag_id": int(modifier["target_tag_id"] or 0),
                "value": int(modifier["value"]),
                "consumer_skill_ids": consumer_ids,
                "consumer_count": len(consumer_ids),
            }
            modifier_contracts.append(record)
            if (tag_id or skill_id) and not consumer_ids:
                missing_modifier_consumers.append(
                    {
                        "passive_id": record["passive_id"],
                        "owner_buff_id": record["owner_buff_id"],
                        "tag_id": tag_id,
                        "skill_id": skill_id,
                    }
                )
    finally:
        connection.close()

    covered_roots = sorted({int(row["skill_id"]) for row in tagged_rows})
    missing_roots = sorted(set(root_ids) - set(covered_roots))
    blockers: list[str] = []
    if missing_roots:
        blockers.append(f"tagged_skills:missing_roots:{','.join(map(str, missing_roots))}")
    if duplicate_pairs:
        blockers.append("tagged_skills:duplicate_skill_tag_pairs")
    if missing_modifier_consumers:
        blockers.append("skill_modifiers:tag_or_skill_without_consumers")

    return {
        "consumer": "server_skill_tag_and_modifier_cache",
        "audited_root_count": len(root_ids),
        "tagged_skill_row_count": len(tagged_rows),
        "tagged_skill_pair_count": len(
            {(int(row["skill_id"]), int(row["tag_id"])) for row in tagged_rows}
        ),
        "covered_root_ids": covered_roots,
        "missing_root_ids": missing_roots,
        "duplicate_pairs": [dict(row) for row in duplicate_pairs],
        "passive_modifier_contracts": modifier_contracts,
        "passive_modifier_tags_without_consumers": missing_modifier_consumers,
        "blockers": blockers,
    }


def _owner_keyed_buff_tag_contract(runtime_path: Path) -> dict[str, Any]:
    """Audit passive buff tags that are consumed as a reverse lookup cache."""

    passive_buff_ids = (480, 486, 888, 889, 7564, 7565)
    marks = ",".join("?" for _ in passive_buff_ids)
    connection = sqlite3.connect(f"file:{runtime_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tagged_rows = connection.execute(
            f"""
            SELECT id, buff_id, tag_id
            FROM tagged_buffs
            WHERE buff_id IN ({marks})
            ORDER BY buff_id, tag_id, id
            """,
            passive_buff_ids,
        ).fetchall()
        duplicate_pairs = connection.execute(
            f"""
            SELECT buff_id, tag_id, COUNT(*) AS row_count
            FROM tagged_buffs
            WHERE buff_id IN ({marks})
            GROUP BY buff_id, tag_id
            HAVING COUNT(*) <> 1
            ORDER BY buff_id, tag_id
            """,
            passive_buff_ids,
        ).fetchall()
    finally:
        connection.close()

    covered_owners = sorted({int(row["buff_id"]) for row in tagged_rows})
    missing_owners = sorted(set(passive_buff_ids) - set(covered_owners))
    blockers: list[str] = []
    if missing_owners:
        blockers.append(
            f"tagged_buffs:missing_passive_owners:{','.join(map(str, missing_owners))}"
        )
    if duplicate_pairs:
        blockers.append("tagged_buffs:duplicate_buff_tag_pairs")

    return {
        "consumer": "server_buff_tag_cache_and_native_passive_dispatch",
        "audited_passive_buff_count": len(passive_buff_ids),
        "tagged_buff_row_count": len(tagged_rows),
        "tagged_buff_pair_count": len(
            {(int(row["buff_id"]), int(row["tag_id"])) for row in tagged_rows}
        ),
        "covered_buff_ids": covered_owners,
        "missing_buff_ids": missing_owners,
        "duplicate_pairs": [dict(row) for row in duplicate_pairs],
        "blockers": blockers,
    }


def build_report(args: Any) -> dict[str, Any]:
    report = shared.build_report(args)
    tag_contract = _owner_keyed_tag_contract(args.runtime)
    buff_tag_contract = _owner_keyed_buff_tag_contract(args.runtime)
    relation_blockers = tag_contract["blockers"] + buff_tag_contract["blockers"]
    report["owner_keyed_relations"] = {
        "skill_tags": tag_contract,
        "passive_buff_tags": buff_tag_contract,
    }
    report["summary"].update(
        {
            "tagged_skill_row_count": tag_contract["tagged_skill_row_count"],
            "tagged_skill_root_coverage_count": len(tag_contract["covered_root_ids"]),
            "tagged_skill_duplicate_pair_count": len(tag_contract["duplicate_pairs"]),
            "passive_modifier_tags_without_consumers": tag_contract[
                "passive_modifier_tags_without_consumers"
            ],
            "tagged_passive_buff_row_count": buff_tag_contract["tagged_buff_row_count"],
            "tagged_passive_buff_duplicate_pair_count": len(
                buff_tag_contract["duplicate_pairs"]
            ),
            "owner_keyed_relation_blockers": relation_blockers,
            "blocked_owner_keyed_relation_count": len(relation_blockers),
        }
    )
    return report


def main() -> int:
    args = shared.parse_args()
    report = build_report(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(shared.canonical(report), encoding="utf-8")
    shared.write_csv(args.output_csv, report)
    print(shared.canonical(report["summary"]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
