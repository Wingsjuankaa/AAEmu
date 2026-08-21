#!/usr/bin/env python3
"""Audit every enabled AA10 quest act that materializes an item.

The authoritative database is read-only. The report records aggregate closure
and only expands anomalous/special rows, keeping the output reviewable while
the SQL still covers the complete enabled corpus.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path


ACT_TABLES = {
    "QuestActSupplyItem": "quest_act_supply_items",
    "QuestActSupplySelectiveItem": "quest_act_supply_selective_items",
    "QuestActSupplyRankedItem": "quest_act_supply_ranked_items",
    "QuestActSupplyResultRankedItem": "quest_act_supply_result_ranked_items",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def audit(database: Path) -> dict:
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    summaries = []
    findings = []

    try:
        for act_type, detail_table in ACT_TABLES.items():
            rows = connection.execute(
                f"""
                SELECT a.id AS act_id,
                       a.quest_component_id AS component_id,
                       qc.quest_context_id AS quest_id,
                       qc.component_kind_id,
                       q.name AS quest_name,
                       q.category_id,
                       q.race,
                       d.item_id,
                       d.count,
                       i.id IS NOT NULL AS item_exists,
                       i.name AS item_name
                  FROM quest_acts a
                  JOIN {detail_table} d ON d.id = a.act_detail_id
                  JOIN quest_components qc ON qc.id = a.quest_component_id
                  JOIN quest_contexts q ON q.id = qc.quest_context_id
             LEFT JOIN items i ON i.id = d.item_id
                 WHERE a.enable = 't' AND a.act_detail_type = ?
              ORDER BY a.id
                """,
                (act_type,),
            ).fetchall()

            summaries.append(
                {
                    "act_type": act_type,
                    "enabled_references": len(rows),
                    "distinct_items": len({row["item_id"] for row in rows}),
                    "missing_item_references": sum(not row["item_exists"] for row in rows),
                    "nonpositive_count_references": sum(row["count"] <= 0 for row in rows),
                }
            )

            for row in rows:
                if row["item_exists"] and row["count"] > 0:
                    continue
                finding = dict(row)
                finding["act_type"] = act_type
                if not row["item_exists"]:
                    finding["code"] = "missing_item_template"
                    finding["classification"] = (
                        "authored_test_content" if row["category_id"] == 55 else "production_review"
                    )
                else:
                    finding["code"] = "nonpositive_count"
                    finding["classification"] = "safe_noop_runtime"
                findings.append(finding)

        flag_rows = connection.execute(
            """
            SELECT a.id AS act_id,
                   qc.quest_context_id AS quest_id,
                   q.name AS quest_name,
                   s.item_id,
                   s.try_equip,
                   s.check_exist
              FROM quest_acts a
              JOIN quest_act_supply_items s ON s.id = a.act_detail_id
              JOIN quest_components qc ON qc.id = a.quest_component_id
              JOIN quest_contexts q ON q.id = qc.quest_context_id
             WHERE a.enable = 't'
               AND a.act_detail_type = 'QuestActSupplyItem'
               AND (s.try_equip = 't' OR s.check_exist = 't')
          ORDER BY a.id
            """
        ).fetchall()
    finally:
        connection.close()

    return {
        "database": str(database.resolve()),
        "summaries": summaries,
        "totals": {
            "enabled_references": sum(row["enabled_references"] for row in summaries),
            "missing_item_references": sum(row["missing_item_references"] for row in summaries),
            "nonpositive_count_references": sum(
                row["nonpositive_count_references"] for row in summaries
            ),
        },
        "findings": findings,
        "special_flag_references": [dict(row) for row in flag_rows],
    }


def write_report(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "quest-item-supply-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    fields = [
        "code", "classification", "act_type", "act_id", "component_id",
        "quest_id", "quest_name", "category_id", "race", "component_kind_id",
        "item_id", "item_name", "count", "item_exists",
    ]
    with (output / "quest-item-supply-findings.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["findings"])

    totals = report["totals"]
    lines = [
        "# AA10 r575 quest item-supply audit",
        "",
        f"Authoritative database: `{report['database']}`.",
        "",
        "| Act type | Enabled refs | Distinct items | Missing refs | Count <= 0 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["summaries"]:
        lines.append(
            f"| {row['act_type']} | {row['enabled_references']} | "
            f"{row['distinct_items']} | {row['missing_item_references']} | "
            f"{row['nonpositive_count_references']} |"
        )
    lines.extend(
        [
            "",
            f"Total enabled references: **{totals['enabled_references']}**.",
            f"Missing item references: **{totals['missing_item_references']}**.",
            f"Non-positive counts: **{totals['nonpositive_count_references']}**.",
            "",
            "The detailed JSON and CSV classify every exception. Category 55 missing "
            "templates are authored test content; a zero count is handled as a successful "
            "no-op by the runtime. Special `try_equip`/`check_exist` references are retained "
            "separately and are not acceptance-time materialization failures.",
        ]
    )
    (output / "CHECKPOINT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    report = audit(args.database)
    write_report(report, args.output)
    print(json.dumps(report["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
