#!/usr/bin/env python3
"""Build a recoverable AA8 item-quarantine transaction.

This tool is deliberately read-only: it inspects a candidate runtime and a
TSV inventory export, then emits SQL for review.  It never connects to or
mutates MySQL.  The generated transaction preserves every original `items`
column and refuses to treat Phase-A candidates as compatible.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


ITEM_COLUMNS = [
    "id",
    "type",
    "template_id",
    "slot_type",
    "slot",
    "count",
    "details",
    "lifespan_mins",
    "made_unit_id",
    "unsecure_time",
    "unpack_time",
    "owner",
    "grade",
    "flags",
    "created_at",
    "bounded",
    "ucc",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument(
        "--inventory-tsv",
        type=Path,
        required=True,
        help="Headered TSV export containing at least id, template_id, slot_type and owner",
    )
    parser.add_argument("--output-sql", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--allow-phase-a-candidates",
        action="store_true",
        help=(
            "Controlled staging only: retain phase_a_candidate instances "
            "without promoting them to complete"
        ),
    )
    return parser.parse_args()


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def load_coverage(path: Path) -> dict[int, dict[str, Any]]:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        exists = connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name='aaemu_item_definition_coverage'
            """
        ).fetchone()[0]
        if not exists:
            raise RuntimeError("Runtime has no aaemu_item_definition_coverage table")
        return {
            int(row["item_id"]): dict(row)
            for row in connection.execute(
                "SELECT * FROM aaemu_item_definition_coverage"
            )
        }
    finally:
        connection.close()


def classify(
    row: dict[str, str],
    coverage: dict[int, dict[str, Any]],
    allow_phase_a_candidates: bool,
) -> str | None:
    item_id = int(row["template_id"])
    definition = coverage.get(item_id)
    if definition is None:
        return "item_id_not_present_in_aa8"
    state = definition["coverage"]
    if state == "complete":
        return None
    if state == "phase_a_candidate" and allow_phase_a_candidates:
        return None
    if state == "catalog_only":
        return "aa8_concrete_definition_not_recovered"
    if state == "phase_a_candidate":
        return "aa8_phase_a_definition_not_yet_accepted"
    return f"aa8_definition_{state}"


def main() -> int:
    options = arguments()
    coverage = load_coverage(options.runtime)
    with options.inventory_tsv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        missing = {"id", "template_id", "slot_type", "owner"} - set(
            reader.fieldnames or []
        )
        if missing:
            raise RuntimeError(f"Inventory TSV lacks columns: {sorted(missing)}")
        inventory = list(reader)

    quarantined: list[tuple[int, str]] = []
    compatible = 0
    equipped = 0
    reason_counts: dict[str, int] = {}
    for row in inventory:
        reason = classify(
            row, coverage, options.allow_phase_a_candidates
        )
        if reason is None:
            compatible += 1
            continue
        quarantined.append((int(row["id"]), reason))
        if row["slot_type"].lower() == "equipment":
            equipped += 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    runtime_hash = sha256(options.runtime)
    tuples = ",\n".join(
        f"({item_id}, {sql_string(reason)})"
        for item_id, reason in quarantined
    )
    columns = ", ".join(f"`{column}`" for column in ITEM_COLUMNS)
    if quarantined:
        transaction = f"""-- Generated from {options.runtime}
-- Runtime SHA-256: {runtime_hash}
-- REVIEW THIS FILE AND VERIFY A FULL MYSQL BACKUP BEFORE EXECUTION.
-- The game service must be stopped while this transaction runs.

START TRANSACTION;

CREATE TEMPORARY TABLE `aa8_quarantine_plan` (
  `id` bigint(20) UNSIGNED NOT NULL PRIMARY KEY,
  `reason` varchar(255) NOT NULL
);

INSERT INTO `aa8_quarantine_plan` (`id`, `reason`) VALUES
{tuples};

-- Fail closed if the reviewed instances changed or disappeared.
SELECT
  COUNT(*) AS planned,
  COUNT(i.`id`) AS present
FROM `aa8_quarantine_plan` p
LEFT JOIN `items` i ON i.`id`=p.`id`;

CREATE TEMPORARY TABLE `aa8_quarantine_guard` (
  `must_be_zero` int NOT NULL CHECK (`must_be_zero` = 0)
);
INSERT INTO `aa8_quarantine_guard` (`must_be_zero`)
SELECT
  COUNT(*) - COUNT(i.`id`)
FROM `aa8_quarantine_plan` p
LEFT JOIN `items` i ON i.`id`=p.`id`;

INSERT INTO `quarantined_items`
  ({columns}, `quarantine_reason`, `source_runtime_sha256`, `quarantined_at`, `restored_at`)
SELECT
  {", ".join(f"i.`{column}`" for column in ITEM_COLUMNS)},
  p.`reason`,
  {sql_string(runtime_hash)},
  UTC_TIMESTAMP(),
  NULL
FROM `items` i
JOIN `aa8_quarantine_plan` p ON p.id=i.id;

DELETE i
FROM `items` i
JOIN `aa8_quarantine_plan` p ON p.id=i.id;

COMMIT;
"""
    else:
        transaction = f"""-- Generated from {options.runtime}
-- Runtime SHA-256: {runtime_hash}
-- No incompatible instances were selected. This file is intentionally a no-op.
SELECT 0 AS quarantine_rows;
"""

    options.output_sql.parent.mkdir(parents=True, exist_ok=True)
    options.report.parent.mkdir(parents=True, exist_ok=True)
    options.output_sql.write_text(transaction, encoding="utf-8")
    report = {
        "runtime": str(options.runtime),
        "runtime_sha256": runtime_hash,
        "inventory_rows": len(inventory),
        "compatible_rows": compatible,
        "allow_phase_a_candidates": options.allow_phase_a_candidates,
        "quarantine_rows": len(quarantined),
        "equipped_rows_to_clear": equipped,
        "reason_counts": reason_counts,
        "sql": str(options.output_sql),
        "executed": False,
    }
    options.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
