import unittest
from pathlib import Path

from build_sorcery_live_acceptance_ledger_v1 import (
    FORMAT_VERSION,
    GATE_IDS,
    ROOT_CONTRACTS,
    build_ledger,
)


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "generated" / "sorcery-executable-semantics-audit-v3.json"


class SorceryLiveAcceptanceLedgerV1Tests(unittest.TestCase):
    def test_template_covers_exact_executable_roots_without_false_acceptance(self):
        ledger = build_ledger(AUDIT)
        rows = ledger["roots"]

        self.assertEqual(FORMAT_VERSION, ledger["format_version"])
        self.assertEqual(30, len(rows))
        self.assertEqual(set(ROOT_CONTRACTS), {row["skill_id"] for row in rows})
        self.assertEqual(30, ledger["summary"]["pending_root_count"])
        self.assertEqual(0, ledger["summary"]["confirmed_root_count"])
        for row in rows:
            self.assertEqual(set(GATE_IDS), set(row["manual_gates"]))
            self.assertTrue(row["english_name"])
            self.assertTrue(row["expected_contract"])
            for gate in row["manual_gates"].values():
                self.assertEqual("pending", gate["status"])
                self.assertEqual([], gate["evidence"])


if __name__ == "__main__":
    unittest.main()
