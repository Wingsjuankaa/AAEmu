from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_sorcery_runtime_v7.py")
SPEC = importlib.util.spec_from_file_location("sorcery_runtime_v7_validator", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class SorceryRuntimeV7AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = validator.build_report(validator.parse_args([]))

    def test_exact_aa8_heir_catalogue_is_closed(self) -> None:
        self.assertEqual([], self.report["errors"])
        self.assertEqual("closed", self.report["summary"]["aa8_heir_catalogue"])
        self.assertEqual(78, self.report["checks"]["heir_skills"])
        self.assertEqual(159, self.report["checks"]["heir_skill_details"])
        self.assertEqual(71, self.report["checks"]["heir_levels"])
        self.assertEqual(308, self.report["checks"]["evidence_rows"])

    def test_sorcery_has_six_exact_families_and_twelve_successors(self) -> None:
        self.assertEqual(6, self.report["checks"]["sorcery_heir_families"])
        self.assertEqual(12, self.report["checks"]["sorcery_successors"])

    def test_native_cached_result_boundaries_are_frozen(self) -> None:
        evidence = self.report["decoder_evidence"]
        self.assertEqual(113965013, evidence["heir_levels"]["start"])
        self.assertEqual(113967072, evidence["heir_levels"]["done"])
        self.assertEqual(143882320, evidence["heir_skill_details"]["start"])
        self.assertEqual(143887105, evidence["heir_skill_details"]["done"])
        self.assertEqual(143887111, evidence["heir_skills"]["start"])
        self.assertEqual(143888125, evidence["heir_skills"]["done"])


if __name__ == "__main__":
    unittest.main()
