#!/usr/bin/env python3
"""Capture a read-only, secret-free AA8 Sorcery persistence snapshot."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Callable


FORMAT_VERSION = "AA8_SORCERY_PERSISTENCE_SNAPSHOT_V1"
SORCERY_SKILL_IDS = {
    10151,
    10153,
    10664,
    10667,
    10670,
    10752,
    11314,
    11939,
    11967,
    12796,
    14774,
    23593,
    36474,
    36475,
    36476,
    36477,
    36478,
    36479,
    39669,
    39674,
    41222,
    41223,
    43068,
    43185,
}
SORCERY_PASSIVE_IDS = {15, 38, 99, 257, 258, 301}


def parse_tsv(text: str, columns: list[str]) -> list[dict[str, str]]:
    rows = []
    for line in text.splitlines():
        if not line:
            continue
        values = line.split("\t")
        if len(values) != len(columns):
            raise ValueError(
                f"expected {len(columns)} columns, received {len(values)}: {line!r}"
            )
        rows.append(dict(zip(columns, values)))
    return rows


def docker_query(container: str, query: str) -> str:
    command = [
        "docker",
        "exec",
        container,
        "sh",
        "-lc",
        'MYSQL_PWD=$MYSQL_ROOT_PASSWORD mysql -uroot -N -B -D aaemu_game -e "$1"',
        "mysql-query",
        query,
    ]
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def build_snapshot(owner: int, query: Callable[[str], str]) -> dict:
    character_rows = parse_tsv(
        query(
            "SELECT id,name,level,heir_level,heir_exp,mp,ability1,ability2,ability3,"
            f"world_id,zone_id,updated_at FROM characters WHERE id={owner} AND deleted=0"
        ),
        [
            "id",
            "name",
            "level",
            "heir_level",
            "heir_exp",
            "mp",
            "ability1",
            "ability2",
            "ability3",
            "world_id",
            "zone_id",
            "updated_at",
        ],
    )
    if len(character_rows) != 1:
        raise RuntimeError(f"owner {owner} resolved to {len(character_rows)} active characters")

    abilities = parse_tsv(
        query(f"SELECT id,exp FROM abilities WHERE owner={owner} ORDER BY id"),
        ["id", "exp"],
    )
    skills = parse_tsv(
        query(f"SELECT id,level,type FROM skills WHERE owner={owner} ORDER BY type,id"),
        ["id", "level", "type"],
    )
    heir_activations = parse_tsv(
        query(
            "SELECT heir_skill_id,successor_skill_id FROM heir_skill_activations "
            f"WHERE owner={owner} ORDER BY heir_skill_id"
        ),
        ["heir_skill_id", "successor_skill_id"],
    )
    active_types = parse_tsv(
        query(
            "SELECT heir_skill_type,skill_type,active_type FROM character_skill_active_types "
            f"WHERE owner={owner} ORDER BY heir_skill_type,skill_type"
        ),
        ["heir_skill_type", "skill_type", "active_type"],
    )

    sorcery_skills = [
        row
        for row in skills
        if row["type"] == "Skill" and int(row["id"]) in SORCERY_SKILL_IDS
    ]
    sorcery_passives = [
        row
        for row in skills
        if row["type"] == "Buff" and int(row["id"]) in SORCERY_PASSIVE_IDS
    ]
    sorcery_ability = next((row for row in abilities if int(row["id"]) == 7), None)

    return {
        "format_version": FORMAT_VERSION,
        "owner": owner,
        "character": character_rows[0],
        "sorcery_ability": sorcery_ability,
        "sorcery_skills": sorcery_skills,
        "sorcery_passives": sorcery_passives,
        "heir_activations": heir_activations,
        "skill_active_types": active_types,
        "summary": {
            "learned_sorcery_skill_count": len(sorcery_skills),
            "learned_sorcery_passive_count": len(sorcery_passives),
            "heir_activation_count": len(heir_activations),
            "active_type_count": len(active_types),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", type=int, required=True)
    parser.add_argument("--container", default="aaemu8-db-1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.owner <= 0:
        parser.error("--owner must be positive")

    snapshot = build_snapshot(
        args.owner, lambda sql: docker_query(args.container, sql)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
