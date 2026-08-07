import json
import tempfile
import unittest
from pathlib import Path

from build_sorcery_completion_audit_v1 import build_audit


class SorceryCompletionAuditV1Tests(unittest.TestCase):
    def test_audit_does_not_promote_static_or_partial_live_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payloads = {
                "executable.json": {
                    "summary": {"blocked_root_count": 0},
                    "roots": [
                        {
                            "skill_id": 10752,
                            "name": "Flamebolt",
                            "root_kind": "base",
                            "blockers": [],
                            "missing_rows": [],
                        }
                    ],
                },
                "prior.json": {
                    "roots": [
                        {
                            "skill_id": 10752,
                            "manual_acceptance": "partial_live_chain",
                        }
                    ]
                },
                "reconciliation.json": {
                    "coverage": {"blocked_entrypoints": []}
                },
                "baseline.json": {
                    "summary": {
                        "learned_sorcery_passive_count": 6,
                        "heir_activation_count": 0,
                    }
                },
                "live.json": {
                    "roots": [
                        {
                            "skill_id": 10752,
                            "runtime_status": "not_observed",
                            "visual_status": "manual_evidence_required",
                        }
                    ]
                },
            }
            for name, payload in payloads.items():
                (root / name).write_text(json.dumps(payload), encoding="utf-8")

            audit = build_audit(
                root / "executable.json",
                root / "prior.json",
                root / "reconciliation.json",
                root / "baseline.json",
                root / "live.json",
            )

            self.assertEqual("not_complete", audit["completion"]["status"])
            self.assertEqual(1, audit["completion"]["prior_partial_root_count"])
            self.assertEqual(0, audit["completion"]["current_runtime_complete_root_count"])
            self.assertIn(
                "visual_repeat_and_relog_matrix",
                audit["completion"]["incomplete_requirement_ids"],
            )
            self.assertEqual("confirmed", audit["requirements"][4]["status"])


if __name__ == "__main__":
    unittest.main()
