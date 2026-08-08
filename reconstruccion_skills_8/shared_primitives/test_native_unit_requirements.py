#!/usr/bin/env python3

from __future__ import annotations

import argparse
import unittest
from pathlib import Path

from extract_native_unit_requirements import extract_unit_requirements


class NativeUnitRequirementTests(unittest.TestCase):
    game11: Path

    def test_exact_boundary_and_archery_plot_requirement(self) -> None:
        rows, provenance = extract_unit_requirements(self.game11)
        self.assertEqual(13_053, len(rows))
        self.assertEqual(0x828B2C, provenance["result_start"])
        self.assertEqual(0x87EC3C, provenance["result_end"])
        self.assertEqual(
            [{
                "owner_type": "PlotCondition",
                "owner_id": 14753,
                "display_msg": 1,
                "kind_id": 26,
                "value1": 1,
                "value2": 30,
                "value3": 0,
            }],
            [
                row for row in rows
                if row["owner_type"] == "PlotCondition" and row["owner_id"] == 14753
            ],
        )

    def test_skill_owner_back_reference_and_archery_shotgun_rows(self) -> None:
        rows, provenance = extract_unit_requirements(self.game11)
        self.assertEqual(
            {"<ref:69872>": "Skill"},
            provenance["recovered_owner_type_references"],
        )
        self.assertEqual(
            {"<ref:69872>": 4_405},
            provenance["recovered_owner_type_counts"],
        )
        expected = [
            (11933, 29, 2, 0, 0),
            (13281, 29, 2, 0, 0),
            (14835, 29, 2, 0, 0),
            (14836, 29, 2, 0, 0),
            (14837, 29, 2, 0, 0),
            (15073, 29, 2, 0, 0),
            (15096, 29, 2, 0, 0),
            (16210, 29, 2, 0, 0),
            (23592, 29, 2, 0, 0),
        ]
        actual = sorted(
            (
                int(row["owner_id"]),
                int(row["kind_id"]),
                int(row["value1"]),
                int(row["value2"]),
                int(row["value3"]),
            )
            for row in rows
            if row["owner_type"] == "Skill"
            and int(row["owner_id"]) in {owner_id for owner_id, *_ in expected}
            and int(row["kind_id"]) == 29
            and int(row["value1"]) == 2
        )
        self.assertEqual(expected, actual)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    NativeUnitRequirementTests.game11 = args.game11
    return 0 if unittest.main(argv=[__file__, *remaining], exit=False).result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
