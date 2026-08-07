from __future__ import annotations

import unittest

from client_forensics.aa10_crosswalk import (
    CLASSIFICATIONS,
    SourceRow,
    _comparison_details,
    _table_classification,
    compare_source_rows,
)


class Aa10CrosswalkClassificationTests(unittest.TestCase):
    def row(self, locator: str, **values: object) -> SourceRow:
        return SourceRow(locator, dict(values), "confirmed")

    def test_exact_id_and_relation(self) -> None:
        rows, relations, counts = compare_source_rows(
            "tagged_skills",
            [self.row("aa8:1", id=1, skill_id=100, tag_id=5)],
            [self.row("aa10:1", id=1, skill_id=100, tag_id=5)],
            ["id", "skill_id", "tag_id"],
        )
        self.assertEqual(rows[0]["classification"], "exact_id_exact_relation")
        self.assertEqual(counts, {"exact_id_exact_relation": 1})
        self.assertEqual(
            {row["classification"] for row in relations},
            {"exact_id_exact_relation"},
        )

    def test_stable_id_changed_property_separates_balance(self) -> None:
        rows, _, _ = compare_source_rows(
            "skill_products",
            [self.row("aa8:1", id=1, skill_id=100, item_id=200, amount=1)],
            [self.row("aa10:1", id=1, skill_id=100, item_id=200, amount=2)],
            ["id", "skill_id", "item_id", "amount"],
        )
        self.assertEqual(rows[0]["classification"], "stable_id_changed_properties")
        self.assertEqual(rows[0]["balance_state"], "changed_not_promotable")
        self.assertEqual(rows[0]["balance_columns"], ["amount"])

    def test_renumbered_row_uses_stable_relation(self) -> None:
        rows, relations, counts = compare_source_rows(
            "tagged_buffs",
            [self.row("aa8:1", id=10, buff_id=100, tag_id=5)],
            [self.row("aa10:1", id=99, buff_id=100, tag_id=5)],
            ["id", "buff_id", "tag_id"],
        )
        self.assertEqual(rows[0]["classification"], "renumbered_row_stable_relation")
        self.assertEqual(counts, {"renumbered_row_stable_relation": 1})
        self.assertEqual(
            {row["classification"] for row in relations},
            {"renumbered_row_stable_relation"},
        )

    def test_same_id_changed_relation_is_conflict(self) -> None:
        rows, relations, _ = compare_source_rows(
            "tagged_skills",
            [self.row("aa8:1", id=1, skill_id=100, tag_id=5)],
            [self.row("aa10:1", id=1, skill_id=101, tag_id=5)],
            ["id", "skill_id", "tag_id"],
        )
        self.assertEqual(rows[0]["classification"], "conflict")
        self.assertIn("conflict", {row["classification"] for row in relations})

    def test_unmatched_rows_remain_version_scoped(self) -> None:
        rows, _, counts = compare_source_rows(
            "skills",
            [self.row("aa8:1", id=1, ability_id=2)],
            [self.row("aa10:2", id=2, ability_id=3)],
            ["id", "ability_id"],
        )
        self.assertEqual(counts, {"aa10_only": 1, "aa8_only": 1})
        self.assertEqual(
            {row["classification"] for row in rows}, {"aa8_only", "aa10_only"}
        )

    def test_structural_candidate_and_tagged_items_quarantine(self) -> None:
        structural = _table_classification(
            table="enum_example",
            aa8_present=False,
            aa10_present=True,
            missing_columns=[],
            aa8_rows=0,
            aa10_rows=3,
            row_counts={},
        )
        tagged = _table_classification(
            table="tagged_items",
            aa8_present=True,
            aa10_present=True,
            missing_columns=[],
            aa8_rows=0,
            aa10_rows=33_226,
            row_counts={},
        )
        self.assertEqual(structural, ("structural_candidate", "cross_version_only"))
        self.assertEqual(tagged, ("conflict", "blocked_cache_boundary"))

    def test_vocabulary_is_exactly_the_required_seven_states(self) -> None:
        self.assertEqual(
            CLASSIFICATIONS,
            {
                "exact_id_exact_relation",
                "stable_id_changed_properties",
                "renumbered_row_stable_relation",
                "aa8_only",
                "aa10_only",
                "structural_candidate",
                "conflict",
            },
        )

    def test_blob_values_are_fingerprinted_without_copying_payloads(self) -> None:
        rows, _, _ = compare_source_rows(
            "appearance_blob",
            [self.row("aa8:1", id=1, payload=b"aa8")],
            [self.row("aa10:1", id=1, payload=b"aa10")],
            ["id", "payload"],
        )
        self.assertEqual(rows[0]["classification"], "stable_id_changed_properties")
        self.assertRegex(rows[0]["aa8_row_sha256"], r"^[0-9A-F]{64}$")

    def test_null_and_zero_are_equivalent_only_for_relations(self) -> None:
        rows, relations, _ = compare_source_rows(
            "skills",
            [self.row("aa8:1", id=1, buff_id=0, cost=0)],
            [self.row("aa10:1", id=1, buff_id=None, cost=None)],
            ["id", "buff_id", "cost"],
        )
        self.assertEqual(rows[0]["classification"], "stable_id_changed_properties")
        self.assertEqual(rows[0]["changed_relations"], [])
        self.assertEqual(relations[0]["classification"], "exact_id_exact_relation")
        self.assertEqual(rows[0]["balance_columns"], ["cost"])


if __name__ == "__main__":
    unittest.main()
