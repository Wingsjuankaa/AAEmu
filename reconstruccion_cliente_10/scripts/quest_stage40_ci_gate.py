#!/usr/bin/env python3
"""Offline CI gate for the authoritative Stage 40 quest snapshot.

The large retail databases and binaries are deliberately not committed. This gate
uses their committed type/count snapshot and verifies that the current server still
contains every class, loader, producer and runtime strict validator proved by the
full-authority Stage 40 build.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_quest_stage40 import PHASE3_OBJECTIVES, PHASE4_REWARDS, inspect_server


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPO = SCRIPT_DIR.parents[1]
DEFAULT_BASELINE = DEFAULT_REPO / "reconstruccion_cliente_10" / "gates" / "quest-stage40-baseline.csv"
EXPECTED_TYPE_COUNT = 86
EXPECTED_ENABLED_REFS = 43_737


def load_baseline(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return [
            {"act_detail_type": row["act_detail_type"], "enabled_refs": int(row["enabled_refs"])}
            for row in csv.DictReader(stream)
        ]


def evaluate_snapshot(
    baseline: list[dict[str, object]],
    classes: set[str],
    loaders: set[str],
    stubs: set[str],
    server_text: str,
    config_text: str,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    expected_types = [str(row["act_detail_type"]) for row in baseline]

    if len(expected_types) != EXPECTED_TYPE_COUNT or len(set(expected_types)) != EXPECTED_TYPE_COUNT:
        findings.append({"code": "baseline_type_count", "actual": len(expected_types), "expected": EXPECTED_TYPE_COUNT})
    enabled_refs = sum(int(row["enabled_refs"]) for row in baseline)
    if enabled_refs != EXPECTED_ENABLED_REFS:
        findings.append({"code": "baseline_enabled_refs", "actual": enabled_refs, "expected": EXPECTED_ENABLED_REFS})

    for detail_type in expected_types:
        if detail_type not in classes:
            findings.append({"code": "missing_server_class", "act_detail_type": detail_type})
        if detail_type not in loaders:
            findings.append({"code": "missing_detail_loader", "act_detail_type": detail_type})
        if detail_type in stubs:
            findings.append({"code": "stub_or_partial", "act_detail_type": detail_type})

    for detail_type, _table, _producer, producer_token, status, _boundary in PHASE3_OBJECTIVES:
        if status != "implemented":
            findings.append({"code": "phase3_not_implemented", "act_detail_type": detail_type, "status": status})
        if producer_token not in server_text:
            findings.append({"code": "missing_phase3_producer", "act_detail_type": detail_type, "token": producer_token})

    for detail_type, _table, _consumer, status, _boundary in PHASE4_REWARDS:
        if status != "implemented":
            findings.append({"code": "phase4_not_implemented", "act_detail_type": detail_type, "status": status})

    required_tokens = {
        "runtime_validator": "QuestCoverageValidator.Validate",
        "runtime_enforcement": "QuestCoverageValidator.Enforce",
        "runtime_invocation": "ValidateQuestCoverage();",
        "reward_ledger": "class QuestRewardLedgerManager",
        "etc_item_objective": "MatchesAcquisition(questAct.Id, ActId",
        "etc_item_accumulator": "AddObjective(questAct, e.Count)",
        "supply_skill_consumer": "quest.Owner.UseSkill(SkillId, quest.Owner)",
    }
    for contract, token in required_tokens.items():
        if token not in server_text:
            findings.append({"code": "missing_runtime_contract", "contract": contract, "token": token})
    if '"Mode": "Strict"' not in config_text:
        findings.append({"code": "strict_mode_not_enabled"})

    return findings


def inspect_repository(repo: Path, baseline_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    baseline = load_baseline(baseline_path)
    classes, loaders, _objectives, stubs, _notes, server_text = inspect_server(repo)
    config_text = (repo / "AAEmu.Game" / "Configurations" / "QuestCoverage.json").read_text(encoding="utf-8-sig")
    findings = evaluate_snapshot(baseline, classes, loaders, stubs, server_text, config_text)
    return findings, {
        "schema": "aa10-quest-stage40-ci-gate-v1",
        "status": "pass" if not findings else "fail",
        "baseline_types": len(baseline),
        "baseline_enabled_refs": sum(int(row["enabled_refs"]) for row in baseline),
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    findings, report = inspect_repository(args.repo, args.baseline)
    print(json.dumps(report, indent=2, sort_keys=True))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
