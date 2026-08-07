#!/usr/bin/env python3
"""Summarize AA8 Sorcery/Archery lifecycle and authoritative damage logs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


FORMAT_VERSION = "AA8_NATIVE_SKILL_LIVE_SUMMARY_V1"
LIFECYCLE_MARKERS = {
    "[AA8SorceryLive]": "sorcery",
    "[AA8ArcheryLive]": "archery",
}
DAMAGE_MARKER = "[AA8SkillDamage]"
PASSIVE_MARKER = "[AA8ArcheryPassive]"
PAIR_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=([^\s]+)")
INTEGER_FIELDS = {
    "skill", "tlId", "caster", "target", "world", "instance", "mp",
    "magicSource", "targets", "effects", "effect", "amount", "absorbed",
    "hpBefore", "hpAfter", "passive", "buff", "char",
}
FLOAT_FIELDS = {
    "move", "rangedAccuracy", "rangedCritical", "rangedCriticalBonus",
    "rangedCriticalMul", "rangedDamageMul", "endlessDamage", "endlessRange",
    "concussiveCooldown",
}
ERROR_RE = re.compile(r"\[(?:ERROR|FATAL)\]|Unhandled|Exception", re.IGNORECASE)


def _fields(fragment: str) -> dict[str, Any] | None:
    result: dict[str, Any] = {}
    for key, raw_value in PAIR_RE.findall(fragment):
        if key in INTEGER_FIELDS:
            try:
                result[key] = int(raw_value)
            except ValueError:
                return None
        elif key in FLOAT_FIELDS:
            try:
                result[key] = float(raw_value)
            except ValueError:
                return None
        else:
            result[key] = raw_value
    return result


def parse_line(line: str) -> dict[str, Any] | None:
    index = line.find(PASSIVE_MARKER)
    if index >= 0:
        fields = _fields(line[index + len(PASSIVE_MARKER):])
        required = {"phase", "passive", "buff", "char", *FLOAT_FIELDS}
        if fields is None or not required.issubset(fields):
            return None
        return {"kind": "passive", "tree": "archery", **fields}
    for marker, tree in LIFECYCLE_MARKERS.items():
        index = line.find(marker)
        if index >= 0:
            fields = _fields(line[index + len(marker):])
            if fields is None or not {"phase", "skill", "tlId", "caster"}.issubset(fields):
                return None
            return {"kind": "lifecycle", "tree": tree, **fields}
    index = line.find(DAMAGE_MARKER)
    if index >= 0:
        fields = _fields(line[index + len(DAMAGE_MARKER):])
        required = {
            "tree", "skill", "tlId", "effect", "caster", "target",
            "amount", "absorbed", "hpBefore", "hpAfter", "packet",
        }
        if fields is None or not required.issubset(fields):
            return None
        return {"kind": "damage", **fields}
    return None


def _key(event: dict[str, Any]) -> tuple[str, int, int, int]:
    return (
        str(event["tree"]),
        int(event["skill"]),
        int(event["tlId"]),
        int(event["caster"]),
    )


def summarize_group(
    key: tuple[str, int, int, int], events: list[dict[str, Any]]
) -> dict[str, Any]:
    tree, skill_id, tl_id, caster_id = key
    lifecycle = [event for event in events if event["kind"] == "lifecycle"]
    damage = [event for event in events if event["kind"] == "damage"]
    phases = Counter(str(event["phase"]) for event in lifecycle)
    results = Counter(
        str(event["result"])
        for event in lifecycle
        if event.get("phase") == "use_result" and event.get("result") != "-"
    )
    hp_delta = sum(
        max(0, int(event["hpBefore"]) - int(event["hpAfter"]))
        for event in damage
    )
    authoritative_hits = [
        event
        for event in damage
        if int(event["amount"]) > 0 and int(event["hpAfter"]) < int(event["hpBefore"])
    ]
    accepted = results.get("Success", 0) > 0
    rejected = sum(count for result, count in results.items() if result != "Success")
    completed = phases.get("ended", 0) > 0 or phases.get("plot_ended", 0) > 0
    cancelled = phases.get("stopped", 0) > 0 or any(
        event.get("cancelled") == "True" for event in lifecycle
    )
    if rejected and not accepted:
        verdict = "rejected"
    elif authoritative_hits and completed:
        verdict = "damage_and_lifecycle_confirmed"
    elif authoritative_hits:
        verdict = "damage_confirmed_lifecycle_partial"
    elif accepted and completed:
        verdict = "lifecycle_complete_no_damage_observed"
    elif accepted:
        verdict = "accepted_partial"
    else:
        verdict = "observed_without_result"
    return {
        "tree": tree,
        "skill_id": skill_id,
        "tl_id": tl_id,
        "caster_id": caster_id,
        "verdict": verdict,
        "accepted_count": results.get("Success", 0),
        "rejected_count": rejected,
        "completed": completed,
        "cancelled": cancelled,
        "lifecycle_event_count": len(lifecycle),
        "damage_event_count": len(damage),
        "authoritative_hit_count": len(authoritative_hits),
        "damage_amount_total": sum(int(event["amount"]) for event in damage),
        "absorbed_total": sum(int(event["absorbed"]) for event in damage),
        "hp_delta_total": hp_delta,
        "packet_true_count": sum(event.get("packet") == "True" for event in damage),
        "target_ids": sorted({int(event["target"]) for event in events if "target" in event}),
        "effect_ids": sorted({int(event["effect"]) for event in damage}),
        "phase_counts": dict(sorted(phases.items())),
        "result_counts": dict(sorted(results.items())),
    }


def build_summary(log_bytes: bytes) -> dict[str, Any]:
    text = log_bytes.decode("utf-8", errors="replace")
    lines = text.splitlines()
    events = [event for line in lines if (event := parse_line(line))]
    execution_events = [event for event in events if event["kind"] != "passive"]
    passive_events = [event for event in events if event["kind"] == "passive"]
    groups: dict[tuple[str, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for event in execution_events:
        groups[_key(event)].append(event)
    rows = [summarize_group(key, groups[key]) for key in sorted(groups)]
    passive_groups: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for event in passive_events:
        passive_groups[(event["char"], event["passive"], event["buff"])].append(event)
    passive_rows = []
    for key in sorted(passive_groups):
        snapshots = passive_groups[key]
        transitions = []
        for before_phase, after_phase in (("before_apply", "after_apply"),
                                          ("before_remove", "after_remove")):
            before = next((row for row in snapshots if row["phase"] == before_phase), None)
            after = next((row for row in snapshots if row["phase"] == after_phase), None)
            if before is None or after is None:
                continue
            changed = [field for field in sorted(FLOAT_FIELDS)
                       if before[field] != after[field]]
            transitions.append({
                "operation": before_phase.removeprefix("before_"),
                "changed_fields": changed,
                "before": {field: before[field] for field in sorted(FLOAT_FIELDS)},
                "after": {field: after[field] for field in sorted(FLOAT_FIELDS)},
            })
        passive_rows.append({
            "character_id": key[0],
            "passive_id": key[1],
            "buff_id": key[2],
            "snapshot_count": len(snapshots),
            "phase_counts": dict(sorted(Counter(row["phase"] for row in snapshots).items())),
            "transitions": transitions,
        })
    errors = [line for line in lines if ERROR_RE.search(line)]
    return {
        "format_version": FORMAT_VERSION,
        "input": {
            "bytes": len(log_bytes),
            "sha256": hashlib.sha256(log_bytes).hexdigest().upper(),
        },
        "summary": {
            "parsed_event_count": len(events),
            "execution_count": len(rows),
            "passive_snapshot_count": len(passive_events),
            "passive_transition_count": sum(len(row["transitions"]) for row in passive_rows),
            "authoritative_damage_execution_count": sum(
                row["authoritative_hit_count"] > 0 for row in rows
            ),
            "error_line_count": len(errors),
            "server_start_count": text.count("Server started!"),
            "trees": dict(sorted(Counter(row["tree"] for row in rows).items())),
        },
        "executions": rows,
        "passive_transitions": passive_rows,
        "error_lines": errors,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "tree", "skill_id", "tl_id", "caster_id", "verdict",
        "accepted_count", "rejected_count", "completed", "cancelled",
        "lifecycle_event_count", "damage_event_count", "authoritative_hit_count",
        "damage_amount_total", "absorbed_total", "hp_delta_total",
        "packet_true_count", "target_ids", "effect_ids", "phase_counts",
        "result_counts",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = dict(row)
            for field in ("target_ids", "effect_ids"):
                normalized[field] = ";".join(map(str, row[field]))
            for field in ("phase_counts", "result_counts"):
                normalized[field] = json.dumps(
                    row[field], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
            writer.writerow(normalized)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, help="Docker Game log captured as UTF-8")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    log_bytes = args.log.read_bytes() if args.log else sys.stdin.buffer.read()
    summary = build_summary(log_bytes)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(args.output_csv, summary["executions"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
