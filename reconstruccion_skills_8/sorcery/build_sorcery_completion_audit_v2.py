#!/usr/bin/env python3
"""Close Sorcery only from static, trace, manual and post-relog evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_sorcery_completion_audit_v1 import build_audit as build_v1
from build_sorcery_completion_audit_v1 import load_json, source
from build_sorcery_live_acceptance_ledger_v1 import FORMAT_VERSION as LEDGER_FORMAT
from build_sorcery_live_acceptance_ledger_v1 import GATE_IDS


FORMAT_VERSION = "AA8_SORCERY_COMPLETION_AUDIT_V2"
SNAPSHOT_FORMAT = "AA8_SORCERY_PERSISTENCE_SNAPSHOT_V1"
ALLOWED_GATE_STATES = {"pending", "confirmed", "failed"}


def normalized_rows(payload: dict[str, Any], key: str) -> list[tuple[str, str, str]]:
    return sorted(
        (str(row["id"]), str(row["level"]), str(row["type"]))
        for row in payload[key]
    )


def validate_ledger(
    ledger: dict[str, Any], required_ids: set[int]
) -> dict[int, dict[str, Any]]:
    if ledger.get("format_version") != LEDGER_FORMAT:
        raise ValueError("unsupported Sorcery acceptance ledger format")
    rows = ledger.get("roots", [])
    ids = [int(row["skill_id"]) for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != required_ids:
        raise ValueError("acceptance ledger roots do not match executable roots")

    by_skill = {}
    for row in rows:
        gates = row.get("manual_gates", {})
        if set(gates) != set(GATE_IDS):
            raise ValueError(f"incomplete manual gates for skill {row['skill_id']}")
        for gate_id, gate in gates.items():
            state = gate.get("status")
            if state not in ALLOWED_GATE_STATES:
                raise ValueError(
                    f"invalid {gate_id} status for skill {row['skill_id']}: {state}"
                )
            if state == "confirmed" and not gate.get("evidence"):
                raise ValueError(
                    f"confirmed {gate_id} lacks evidence for skill {row['skill_id']}"
                )
        by_skill[int(row["skill_id"])] = row
    return by_skill


def validate_post_relog(
    baseline: dict[str, Any], post_relog: dict[str, Any]
) -> list[str]:
    mismatches = []
    if post_relog.get("format_version") != SNAPSHOT_FORMAT:
        mismatches.append("format_version")
    if int(post_relog.get("owner", -1)) != int(baseline.get("owner", -2)):
        mismatches.append("owner")

    for key in ("id", "name"):
        if str(post_relog.get("character", {}).get(key)) != str(
            baseline.get("character", {}).get(key)
        ):
            mismatches.append(f"character.{key}")

    post_abilities = {
        str(post_relog.get("character", {}).get(f"ability{slot}"))
        for slot in (1, 2, 3)
    }
    if "7" not in post_abilities:
        mismatches.append("character.sorcery_not_selected")

    if normalized_rows(post_relog, "sorcery_skills") != normalized_rows(
        baseline, "sorcery_skills"
    ):
        mismatches.append("sorcery_skills")
    if normalized_rows(post_relog, "sorcery_passives") != normalized_rows(
        baseline, "sorcery_passives"
    ):
        mismatches.append("sorcery_passives")

    if str(post_relog.get("sorcery_ability", {}).get("id")) != "7":
        mismatches.append("sorcery_ability.id")
    try:
        if int(post_relog["sorcery_ability"]["exp"]) < int(
            baseline["sorcery_ability"]["exp"]
        ):
            mismatches.append("sorcery_ability.exp_regressed")
    except (KeyError, TypeError, ValueError):
        mismatches.append("sorcery_ability.exp")
    return mismatches


def build_audit(
    executable_path: Path,
    prior_live_path: Path,
    reconciliation_path: Path,
    baseline_path: Path,
    live_summary_path: Path,
    ledger_path: Path,
    post_relog_path: Path | None = None,
) -> dict[str, Any]:
    audit = build_v1(
        executable_path,
        prior_live_path,
        reconciliation_path,
        baseline_path,
        live_summary_path,
    )
    ledger = load_json(ledger_path)
    baseline = load_json(baseline_path)
    required_ids = {int(row["skill_id"]) for row in audit["roots"]}
    ledger_by_skill = validate_ledger(ledger, required_ids)

    visual_complete = []
    visual_failed = []
    for root in audit["roots"]:
        skill_id = int(root["skill_id"])
        manual_gates = ledger_by_skill[skill_id]["manual_gates"]
        states = {gate: manual_gates[gate]["status"] for gate in GATE_IDS}
        if all(state == "confirmed" for state in states.values()):
            visual_complete.append(skill_id)
            root["visual_state"] = "confirmed"
        elif any(state == "failed" for state in states.values()):
            visual_failed.append(skill_id)
            root["visual_state"] = "failed"
        else:
            root["visual_state"] = "pending"
        root["manual_gates"] = manual_gates
        remaining = []
        if root["current_trace_state"] != "server_lifecycle_complete":
            remaining.append("current_runtime_lifecycle")
        remaining.extend(gate for gate, state in states.items() if state != "confirmed")
        root["remaining"] = remaining

    visual_requirement = next(
        row for row in audit["requirements"] if row["id"] == "visual_repeat_and_relog_matrix"
    )
    visual_requirement["status"] = (
        "failed"
        if visual_failed
        else "confirmed"
        if len(visual_complete) == len(required_ids)
        else "pending"
    )
    visual_requirement["evidence"] = {
        "manual_protocol": "SORCERY_LIVE_ACCEPTANCE_PROTOCOL_V2.md",
        "ledger": ledger_path.as_posix(),
        "required_root_count": len(required_ids),
        "current_visual_complete_count": len(visual_complete),
        "failed_skill_ids": visual_failed,
    }

    post_requirement = next(
        row for row in audit["requirements"] if row["id"] == "post_relog_persistence"
    )
    post_mismatches: list[str] = []
    if post_relog_path is None:
        post_requirement["status"] = "pending"
    else:
        post_relog = load_json(post_relog_path)
        post_mismatches = validate_post_relog(baseline, post_relog)
        post_requirement["status"] = "confirmed" if not post_mismatches else "failed"
    post_requirement["evidence"] = {
        "baseline": baseline_path.as_posix(),
        "post_relog": post_relog_path.as_posix() if post_relog_path else None,
        "post_relog_snapshot_captured": post_relog_path is not None,
        "mismatches": post_mismatches,
    }

    audit["format_version"] = FORMAT_VERSION
    audit["sources"]["acceptance_ledger"] = source(ledger_path)
    if post_relog_path is not None:
        audit["sources"]["post_relog"] = source(post_relog_path)

    incomplete = [
        row["id"] for row in audit["requirements"] if row["status"] != "confirmed"
    ]
    audit["completion"].update(
        {
            "status": "complete" if not incomplete else "not_complete",
            "incomplete_requirement_ids": incomplete,
            "current_visual_complete_root_count": len(visual_complete),
            "current_visual_failed_root_count": len(visual_failed),
            "post_relog_mismatch_count": len(post_mismatches),
        }
    )
    return audit


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--executable",
        type=Path,
        default=root / "generated" / "sorcery-executable-semantics-audit-v3.json",
    )
    parser.add_argument(
        "--prior-live",
        type=Path,
        default=root / "generated" / "sorcery-executable-semantics-audit-v2.json",
    )
    parser.add_argument(
        "--reconciliation",
        type=Path,
        default=root / "generated" / "sorcery-forensic-runtime-reconciliation-v1.json",
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--live-summary", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--post-relog", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    audit = build_audit(
        args.executable,
        args.prior_live,
        args.reconciliation,
        args.baseline,
        args.live_summary,
        args.ledger,
        args.post_relog,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
