#!/usr/bin/env python3
"""Summarize behavior-neutral AA8 Sorcery lifecycle evidence from game logs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


FORMAT_VERSION = "AA8_SORCERY_LIVE_TRACE_SUMMARY_V1"
MARKER = "[AA8SorceryLive]"
PAIR_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=([^\s]+)")
INTEGER_FIELDS = {
    "skill",
    "tlId",
    "caster",
    "target",
    "world",
    "instance",
    "mp",
    "magicSource",
    "targets",
    "effects",
}


def parse_event(line: str) -> dict[str, Any] | None:
    marker_index = line.find(MARKER)
    if marker_index < 0:
        return None
    fields: dict[str, Any] = {}
    for key, raw_value in PAIR_RE.findall(line[marker_index + len(MARKER) :]):
        if key in INTEGER_FIELDS:
            try:
                fields[key] = int(raw_value)
            except ValueError:
                return None
        else:
            fields[key] = raw_value
    required = {"phase", "skill", "tlId", "caster"}
    if not required.issubset(fields):
        return None
    return fields


def load_roots(audit_path: Path) -> list[dict[str, Any]]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    roots = []
    for row in audit["roots"]:
        roots.append(
            {
                "skill_id": int(row["skill_id"]),
                "name": row.get("name"),
                "root_kind": row["root_kind"],
                "uses_plot": int(row.get("closure_counts", {}).get("plots", 0)) > 0,
            }
        )
    return roots


def classify_root(root: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    phases = Counter(str(event["phase"]) for event in events)
    results = Counter(
        str(event["result"])
        for event in events
        if event.get("phase") == "use_result" and event.get("result") != "-"
    )
    accepted = results.get("Success", 0) > 0
    rejected = sum(count for result, count in results.items() if result != "Success")
    plot_event_count = sum(
        count for phase, count in phases.items() if phase.startswith("plot_event_")
    )
    completed = phases.get("plot_ended", 0) > 0 if root["uses_plot"] else phases.get("ended", 0) > 0
    interrupted = phases.get("stopped", 0) > 0 or any(
        event.get("cancelled") == "True" for event in events
    )

    if not events:
        runtime_status = "not_observed"
    elif not accepted:
        runtime_status = "rejected_only"
    elif interrupted and not completed:
        runtime_status = "interrupted"
    elif root["uses_plot"] and completed and plot_event_count > 0:
        runtime_status = "server_lifecycle_complete"
    elif not root["uses_plot"] and completed and phases.get("fired", 0) > 0:
        runtime_status = "server_lifecycle_complete"
    else:
        runtime_status = "partial_lifecycle"

    return {
        **root,
        "runtime_status": runtime_status,
        "visual_status": "manual_evidence_required",
        "event_count": len(events),
        "accepted_count": results.get("Success", 0),
        "rejected_count": rejected,
        "plot_event_count": plot_event_count,
        "phase_counts": dict(sorted(phases.items())),
        "result_counts": dict(sorted(results.items())),
        "caster_ids": sorted({int(event["caster"]) for event in events}),
        "tl_ids": sorted({int(event["tlId"]) for event in events}),
        "mp_min": min((int(event["mp"]) for event in events if "mp" in event), default=None),
        "mp_max": max((int(event["mp"]) for event in events if "mp" in event), default=None),
        "magic_source_min": min(
            (int(event["magicSource"]) for event in events if "magicSource" in event),
            default=None,
        ),
        "magic_source_max": max(
            (int(event["magicSource"]) for event in events if "magicSource" in event),
            default=None,
        ),
    }


def build_summary(log_bytes: bytes, audit_path: Path) -> dict[str, Any]:
    text = log_bytes.decode("utf-8", errors="replace")
    events = [event for line in text.splitlines() if (event := parse_event(line))]
    events_by_skill: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_skill[int(event["skill"])].append(event)

    roots = load_roots(audit_path)
    rows = [classify_root(root, events_by_skill[root["skill_id"]]) for root in roots]
    observed_closure_ids = sorted(events_by_skill)
    non_root_closure_ids = sorted(set(observed_closure_ids) - {row["skill_id"] for row in roots})

    status_counts = Counter(row["runtime_status"] for row in rows)
    return {
        "format_version": FORMAT_VERSION,
        "input": {
            "bytes": len(log_bytes),
            "sha256": hashlib.sha256(log_bytes).hexdigest().upper(),
            "audit_path": audit_path.as_posix(),
            "audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest().upper(),
        },
        "summary": {
            "parsed_event_count": len(events),
            "root_count": len(rows),
            "observed_root_count": sum(row["event_count"] > 0 for row in rows),
            "server_lifecycle_complete_count": status_counts.get(
                "server_lifecycle_complete", 0
            ),
            "runtime_status_counts": dict(sorted(status_counts.items())),
            "observed_closure_skill_ids": observed_closure_ids,
            "observed_non_root_closure_skill_ids": non_root_closure_ids,
            "visual_gate_complete": False,
        },
        "roots": rows,
    }


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    fieldnames = [
        "skill_id",
        "name",
        "root_kind",
        "uses_plot",
        "runtime_status",
        "visual_status",
        "event_count",
        "accepted_count",
        "rejected_count",
        "plot_event_count",
        "caster_ids",
        "tl_ids",
        "mp_min",
        "mp_max",
        "magic_source_min",
        "magic_source_max",
        "phase_counts",
        "result_counts",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = dict(row)
            for field in ("caster_ids", "tl_ids"):
                normalized[field] = ";".join(map(str, row[field]))
            for field in ("phase_counts", "result_counts"):
                normalized[field] = json.dumps(
                    row[field], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
            writer.writerow(normalized)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, help="docker compose log captured as UTF-8")
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path(__file__).with_name("generated")
        / "sorcery-executable-semantics-audit-v3.json",
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    log_bytes = args.log.read_bytes() if args.log else sys.stdin.buffer.read()
    summary = build_summary(log_bytes, args.audit)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(args.output_csv, summary["roots"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
