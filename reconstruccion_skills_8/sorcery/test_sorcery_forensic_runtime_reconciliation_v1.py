from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("reconcile_sorcery_forensic_graph_v1.py")
SPEC = importlib.util.spec_from_file_location("sorcery_reconciliation_v1", SCRIPT)
reconcile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(reconcile)


class SorceryForensicRuntimeReconciliationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = reconcile.build_report(reconcile.parse_args([]))

    def test_all_native_roots_are_covered_and_terminal(self) -> None:
        coverage = self.report["coverage"]
        self.assertEqual(40, coverage["native_sorcery_graph_roots"])
        self.assertEqual([], coverage["native_roots_missing_from_executable_audit"])
        self.assertEqual([], coverage["unclassified_executable_skills"])
        self.assertEqual({"enabled": 40}, coverage["downstream_states"])

    def test_six_internal_entrypoints_close_previous_scope_gap(self) -> None:
        coverage = self.report["coverage"]
        self.assertEqual(24, coverage["audited_public_entrypoints"])
        self.assertEqual(6, coverage["audited_internal_entrypoints"])
        self.assertEqual(30, coverage["audited_entrypoints"])

    def test_only_known_non_root_executable_skills_remain(self) -> None:
        self.assertEqual(
            [10151, 10153, 15317],
            self.report["coverage"]["executable_rows_outside_native_sorcery_roots"],
        )
        classes = {row["skill_id"]: row for row in self.report["classifications"]}
        for skill_id in (10151, 10153):
            self.assertEqual(
                "runtime_confirmed_tombstone_parent_candidate",
                classes[skill_id]["classification"],
            )
            self.assertFalse(classes[skill_id]["promotion_allowed"])
        self.assertEqual(
            "exact_aa8_cross_ability_reachable_child",
            classes[15317]["classification"],
        )


if __name__ == "__main__":
    unittest.main()
