#!/usr/bin/env python3
"""Create the deterministic manual/live acceptance ledger for AA8 Sorcery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FORMAT_VERSION = "AA8_SORCERY_LIVE_ACCEPTANCE_LEDGER_V1"
GATE_IDS = ("visual_fx_sound_animation", "second_use", "relog")

ROOT_CONTRACTS: dict[int, tuple[str, str]] = {
    10151: ("Freezing Earth", "AoE, damage/control, clean second use"),
    10153: ("Insulating Lens", "shield, one absorption trigger, expiry and cooldown"),
    10664: ("Meteor Strike", "cast, impact AoE, trip and single displacement"),
    10667: ("Freezing Arrow", "projectile, single impact, slow and cooldown"),
    10670: ("Arc Lightning", "cast, shock and nearby propagation without self-hit"),
    10752: ("Flamebolt", "10752 to 24894 to 24895 chain, Burning and clean end"),
    11314: ("Frigid Tracks", "tracks, freeze on crossing and complete cleanup"),
    11939: ("Searing Rain", "area, repeated ticks and active second execution"),
    11967: ("Chain Lightning", "up to five jumps and decreasing jump damage"),
    12796: ("Magic Circle", "oriented circle, enter/leave buff and cleanup"),
    14774: ("Flame Barrier", "wall, ticks, slow and no invisible residue"),
    23593: ("Gods' Whip", "five stages, progressive cost/damage and clean end"),
    36474: ("Flamebolt: Flame", "selected Heir visual and complete lifecycle"),
    36475: ("Flamebolt: Lightning", "selected Heir visual and complete lifecycle"),
    36476: ("Chain Lightning: Flame", "selected Heir visual and complete lifecycle"),
    36477: ("Chain Lightning: Wave", "selected Heir visual and complete lifecycle"),
    36478: ("Meteor Strike: Wave", "selected Heir visual and complete lifecycle"),
    36479: ("Meteor Strike: Lightning", "selected Heir visual and complete lifecycle"),
    39669: ("Gods' Whip: Lightning", "five-stage Heir chain and clean end"),
    39674: ("Gods' Whip: Wave", "Heir area chain and clean end"),
    41222: ("Flame Barrier: Wave", "Heir wall lifecycle and cleanup"),
    41223: ("Flame Barrier: Mist", "child 41478 remains anchored and cleans up"),
    43068: ("Magic Circle: Flame", "Heir circle and contextual return 43464"),
    43185: ("Magic Circle: Quake", "Heir circle and contextual return 43465"),
    12789: ("Login Stage Flamebolt", "preview without packet error or placeholder"),
    12790: ("Login Stage Ice Arrow", "preview without packet error or placeholder"),
    12791: ("Login Stage Raging Thunder", "preview without packet error or placeholder"),
    42012: ("Move Magic Circle", "single return to base anchor and anchor consume"),
    43464: ("Magic Circle: Flame Teleport", "single same-instance return and consume"),
    43465: ("Magic Circle: Quake Teleport", "single same-instance return and consume"),
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_ledger(executable_path: Path) -> dict[str, Any]:
    executable = load_json(executable_path)
    audit_ids = [int(row["skill_id"]) for row in executable["roots"]]
    if len(audit_ids) != len(set(audit_ids)):
        raise ValueError("duplicate skill_id in executable audit")
    if set(audit_ids) != set(ROOT_CONTRACTS):
        missing = sorted(set(ROOT_CONTRACTS) - set(audit_ids))
        extra = sorted(set(audit_ids) - set(ROOT_CONTRACTS))
        raise ValueError(f"root contract mismatch: missing={missing} extra={extra}")

    roots = []
    for row in executable["roots"]:
        skill_id = int(row["skill_id"])
        english_name, contract = ROOT_CONTRACTS[skill_id]
        roots.append(
            {
                "skill_id": skill_id,
                "root_kind": row["root_kind"],
                "english_name": english_name,
                "aa8_name": row.get("name"),
                "expected_contract": contract,
                "manual_gates": {
                    gate: {"status": "pending", "evidence": [], "notes": ""}
                    for gate in GATE_IDS
                },
            }
        )

    return {
        "format_version": FORMAT_VERSION,
        "client_build": "8.0.3.12 r558734",
        "allowed_statuses": ["pending", "confirmed", "failed"],
        "gate_ids": list(GATE_IDS),
        "roots": roots,
        "summary": {
            "required_root_count": len(roots),
            "confirmed_root_count": 0,
            "failed_root_count": 0,
            "pending_root_count": len(roots),
        },
    }


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--executable",
        type=Path,
        default=root / "generated" / "sorcery-executable-semantics-audit-v3.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ledger = build_ledger(args.executable)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
