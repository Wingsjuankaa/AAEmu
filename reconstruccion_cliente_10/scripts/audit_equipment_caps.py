#!/usr/bin/env python3
"""Audit equipment synthesis grade caps without modifying the client database."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


GRADE_NAMES = {
    0: "Basic",
    1: "Crude",
    2: "Grand",
    3: "Rare",
    4: "Arcane",
    5: "Heroic",
    6: "Unique",
    7: "Celestial",
    8: "Divine",
    9: "Epic",
    10: "Legendary",
    11: "Mythic",
    12: "Eternal",
}

EXCLUDE_TOKENS = ("test", ".material", "cosplay", "dummy", "sample")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("output_directory", type=Path)
    return parser.parse_args()


def localized_item_names(connection: sqlite3.Connection) -> dict[int, tuple[str, str]]:
    return {
        row[0]: (row[1] or "", row[2] or "")
        for row in connection.execute(
            """
            SELECT idx, en_us, es
            FROM localized_texts
            WHERE tbl_name = 'items' AND tbl_column_name = 'name'
            """
        )
    }


def main() -> int:
    args = parse_args()
    database = args.database.resolve(strict=True)
    output_directory = args.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
    if quick_check != "ok":
        raise RuntimeError(f"SQLite quick_check failed: {quick_check}")

    names = localized_item_names(connection)
    equipment: dict[int, list[int]] = defaultdict(list)
    for row in connection.execute(
        """
        SELECT item_rnd_attr_category_id AS category_id, item_id
        FROM item_armors
        WHERE COALESCE(item_rnd_attr_category_id, 0) > 0
        UNION ALL
        SELECT item_rnd_attr_category_id AS category_id, item_id
        FROM item_weapons
        WHERE COALESCE(item_rnd_attr_category_id, 0) > 0
        """
    ):
        equipment[row["category_id"]].append(row["item_id"])

    property_max = dict(
        connection.execute(
            """
            SELECT item_rnd_attr_category_id, MAX(grade_id)
            FROM item_rnd_attr_category_properties
            GROUP BY item_rnd_attr_category_id
            """
        )
    )

    mappings: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in connection.execute(
        """
        SELECT m.source_item_id, m.target_item_id, m.source_grade_id,
               m.target_grade_id, g.id AS group_id, g.name AS group_name,
               g.disable
        FROM item_change_mappings m
        JOIN item_change_mapping_groups g ON g.id = m.mapping_group_id
        """
    ):
        mappings[row["source_item_id"]].append(row)

    categories = {
        row["id"]: row
        for row in connection.execute(
            """
            SELECT id, name, max_evolving_grade, desc
            FROM item_rnd_attr_categories
            """
        )
    }

    rows: list[dict[str, object]] = []
    orphan_category_ids: list[int] = []
    for category_id, item_ids in sorted(equipment.items()):
        category = categories.get(category_id)
        if category is None:
            orphan_category_ids.append(category_id)
            continue
        cap = category["max_evolving_grade"]
        ladder_max = property_max.get(category_id, -1)
        if cap < 0 or ladder_max <= cap:
            continue

        category_mappings = [entry for item_id in item_ids for entry in mappings[item_id]]
        enabled = [entry for entry in category_mappings if entry["disable"] == 0]
        disabled = [entry for entry in category_mappings if entry["disable"] != 0]
        normalized_name = (category["name"] or "").lower()
        excluded = any(token in normalized_name for token in EXCLUDE_TOKENS)

        if excluded:
            classification = "test_material_or_cosmetic"
        elif enabled:
            classification = "expected_awakening_gate"
        elif disabled:
            classification = "disabled_mapping_frontier"
        else:
            classification = "terminal_no_mapping_candidate"

        sample_names: list[str] = []
        for item_id in sorted(item_ids)[:8]:
            en_name, es_name = names.get(item_id, ("", ""))
            display_name = es_name or en_name
            sample_names.append(f"{item_id}:{display_name}" if display_name else str(item_id))

        target_ids = sorted({entry["target_item_id"] for entry in category_mappings})
        enabled_groups = sorted(
            {f'{entry["group_id"]}:{entry["group_name"]}' for entry in enabled}
        )
        disabled_groups = sorted(
            {f'{entry["group_id"]}:{entry["group_name"]}' for entry in disabled}
        )
        target_categories = sorted(
            {
                target[0]
                for target_id in target_ids
                for target in connection.execute(
                    """
                    SELECT item_rnd_attr_category_id FROM item_armors WHERE item_id = ?
                    UNION
                    SELECT item_rnd_attr_category_id FROM item_weapons WHERE item_id = ?
                    """,
                    (target_id, target_id),
                )
                if target[0]
            }
        )

        rows.append(
            {
                "category_id": category_id,
                "category_name": category["name"],
                "current_cap_id": cap,
                "current_cap_name": GRADE_NAMES.get(cap, str(cap)),
                "property_ladder_max_id": ladder_max,
                "property_ladder_max_name": GRADE_NAMES.get(ladder_max, str(ladder_max)),
                "item_count": len(item_ids),
                "mapping_count": len(category_mappings),
                "enabled_mapping_count": len(enabled),
                "disabled_mapping_count": len(disabled),
                "enabled_mapping_groups": " | ".join(enabled_groups),
                "disabled_mapping_groups": " | ".join(disabled_groups),
                "target_category_ids": ";".join(map(str, target_categories)),
                "sample_items": " | ".join(sample_names),
                "classification": classification,
            }
        )

    fieldnames = list(rows[0]) if rows else []
    csv_path = output_directory / "equipment-grade-cap-audit.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    by_classification: dict[str, int] = defaultdict(int)
    by_cap: dict[str, int] = defaultdict(int)
    for row in rows:
        by_classification[str(row["classification"])] += 1
        by_cap[f'{row["current_cap_id"]}->{row["property_ladder_max_id"]}'] += 1

    summary = {
        "source": {
            "path": str(database),
            "bytes": database.stat().st_size,
            "sha256": sha256(database),
            "quick_check": quick_check,
        },
        "method": (
            "Equipment categories whose synthesis property ladder extends above "
            "max_evolving_grade; mapping state separates expected awakening gates "
            "from disabled or terminal frontiers. This is candidate evidence, not "
            "authorization to patch caps."
        ),
        "candidate_category_count": len(rows),
        "equipment_orphan_category_ids": orphan_category_ids,
        "counts_by_classification": dict(sorted(by_classification.items())),
        "counts_by_cap": dict(sorted(by_cap.items())),
        "csv": csv_path.name,
    }
    summary_path = output_directory / "equipment-grade-cap-audit.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(summary_path)
    print(csv_path)
    print(json.dumps(summary["counts_by_classification"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
