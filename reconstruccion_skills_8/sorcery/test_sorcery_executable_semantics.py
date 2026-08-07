import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_sorcery_executable_semantics.py")
SPEC = importlib.util.spec_from_file_location("sorcery_executable_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SorceryExecutableSemanticsTests(unittest.TestCase):
    def test_special_type_enum_contains_sorcery_contracts(self):
        names = set(MODULE.parse_special_types().values())
        self.assertTrue(
            {
                "DisturbCasting",
                "KnockBack",
                "SpawnDoodad",
                "SkillUse",
                "ManaCost",
                "Cooldown",
                "GlobalCooldown",
                "Combo",
                "CancelOngoingBuff",
                "AutoAttack",
            }.issubset(names)
        )

    def test_former_no_op_handlers_are_implemented(self):
        for name in ("ResetAoeDiminishingEffect", "CombatResourceEffect"):
            record = MODULE.handler_record(name)
            self.assertTrue(record["present"])
            self.assertTrue(record["state"].startswith("implemented"))

    def test_audit_covers_all_static_and_live_roots(self):
        args = MODULE.parse_args([])
        report = MODULE.build_report(args)
        ids = {row["skill_id"] for row in report["roots"]}
        self.assertEqual(42, len(ids))
        self.assertTrue({10151, 10153, 11939, 39674}.issubset(ids))
        self.assertEqual(42, report["summary"]["root_count"])

    def test_outputs_are_deterministic(self):
        args = MODULE.parse_args([])
        first = MODULE.canonical(MODULE.build_report(args))
        second = MODULE.canonical(MODULE.build_report(args))
        self.assertEqual(first, second)
        parsed = json.loads(first)
        self.assertEqual("Kakao 8.0.3.12 r558734", parsed["client_build"])


if __name__ == "__main__":
    unittest.main()
