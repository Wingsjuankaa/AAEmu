from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_sorcery_runtime_v6.py")
SPEC = importlib.util.spec_from_file_location("sorcery_runtime_v6_validator", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class SorceryRuntimeV6AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = validator.build_report(validator.parse_args([]))

    def test_all_static_gates_are_closed(self) -> None:
        self.assertEqual([], self.report["errors"])
        self.assertEqual("closed", self.report["summary"]["static_runtime_state"])
        self.assertEqual("closed", self.report["summary"]["localization_state"])
        self.assertEqual("closed", self.report["summary"]["doodad_native_state"])

    def test_doodad_candidate_rows_are_promoted_to_aa8(self) -> None:
        checks = self.report["checks"]
        self.assertEqual(21, checks["native_doodad_rows"])
        self.assertEqual(219, checks["native_exact_fields"])
        self.assertEqual(4, checks["reference_resolved_fields"])
        self.assertEqual(
            {
                "aa8_native_exact": 19,
                "aa8_native_with_bounded_string_reference_resolution": 2,
            },
            checks["classifications"],
        )

    def test_new_native_result_boundaries_are_frozen(self) -> None:
        decoder = self.report["decoder_evidence"]
        self.assertEqual(4358, decoder["doodad_func_finals"]["rows"])
        self.assertEqual(15004, decoder["doodad_func_timers"]["rows"])
        self.assertEqual(104686992, decoder["doodad_func_finals"]["start"])
        self.assertEqual(104804496, decoder["doodad_func_timers"]["start"])


if __name__ == "__main__":
    unittest.main()
