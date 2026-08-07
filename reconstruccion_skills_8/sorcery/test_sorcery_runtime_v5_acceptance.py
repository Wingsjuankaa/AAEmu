from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_sorcery_runtime_v5.py")
SPEC = importlib.util.spec_from_file_location("sorcery_runtime_v5_validator", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class SorceryRuntimeV5AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = validator.build_report(validator.parse_args([]))

    def test_runtime_and_localization_gates_are_closed(self) -> None:
        self.assertEqual([], self.report["errors"])
        self.assertEqual("closed", self.report["summary"]["static_runtime_state"])
        self.assertEqual("closed", self.report["summary"]["localization_state"])
        self.assertEqual(222, self.report["checks"]["exact_aa8_localization_rows"])
        self.assertEqual(2272, self.report["checks"]["exact_aa8_rows_compared"])

    def test_visible_roots_have_exact_aa8_localization(self) -> None:
        self.assertEqual(12, len(self.report["roots"]))
        for row in self.report["roots"]:
            self.assertEqual("enabled", row["runtime_status"])
            self.assertEqual("exact_aa8_compact_r558734", row["localization_state"])

    def test_tombstone_roots_preserve_exact_aa8_lifecycle_evidence(self) -> None:
        roots = self.report["tombstone_roots"]
        self.assertEqual({"10151", "10153"}, set(roots))
        self.assertEqual(20, roots["10151"]["confirmed_incoming_relations"])
        self.assertEqual(18, roots["10153"]["confirmed_incoming_relations"])
        for row in roots.values():
            self.assertEqual("tombstone", row["lifecycle"])
            self.assertEqual(
                "absent_in_complete_unfiltered_result", row["compact_skills_row"]
            )

    def test_localization_repair_scope_is_frozen(self) -> None:
        localization = self.report["localization"]
        self.assertEqual({"skills": 126, "buffs": 96}, localization["row_counts"])
        self.assertEqual(
            {"different": 81, "exact": 44, "missing": 97},
            localization["prior_state_counts"],
        )


if __name__ == "__main__":
    unittest.main()
