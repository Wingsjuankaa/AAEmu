from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_sorcery_runtime_v4.py")
SPEC = importlib.util.spec_from_file_location("sorcery_runtime_v4_validator", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class SorceryRuntimeV4AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = validator.build_report(validator.parse_args([]))

    def test_complete_static_runtime_gate_is_closed(self) -> None:
        self.assertEqual([], self.report["errors"])
        self.assertEqual("closed", self.report["summary"]["static_runtime_state"])
        self.assertEqual(2272, self.report["checks"]["exact_aa8_rows_compared"])
        self.assertEqual(0, self.report["checks"]["unknown_special_effect_enums"])
        self.assertGreaterEqual(self.report["checks"]["references_checked"], 2500)

    def test_all_visible_active_roots_are_present_and_named(self) -> None:
        roots = {row["skill_id"]: row for row in self.report["roots"]}
        self.assertEqual(set(validator.VISIBLE_ROOTS), set(roots))
        self.assertEqual(12, self.report["summary"]["root_count"])
        for skill_id, expected_name in validator.EXPECTED_ENGLISH_NAMES.items():
            self.assertEqual(expected_name, roots[skill_id]["english_name"])
            self.assertEqual("enabled", roots[skill_id]["runtime_status"])
            self.assertGreater(roots[skill_id]["closure_rows"], 0)

    def test_all_sorcery_passive_contracts_are_live_and_resolved(self) -> None:
        self.assertEqual(6, self.report["summary"]["passive_count"])
        self.assertEqual(
            "accepted_live_and_runtime_resolved", self.report["passives"]["state"]
        )
        actual = {
            int(row["id"]): int(row["buff_id"])
            for row in self.report["passives"]["templates"]
        }
        self.assertEqual(validator.PASSIVE_CONTRACTS, actual)

    def test_sorcery_doodad_runtime_closure_is_present(self) -> None:
        groups = self.report["doodads"]["doodad_groups"]
        self.assertEqual({str(value) for value in validator.AA8_DOODADS}, set(groups))
        for group_ids in groups.values():
            self.assertTrue(group_ids)


if __name__ == "__main__":
    unittest.main()
