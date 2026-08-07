import json
import tempfile
import unittest
from pathlib import Path

from build_sorcery_completion_audit_v2 import build_audit
from build_sorcery_live_acceptance_ledger_v1 import FORMAT_VERSION as LEDGER_FORMAT


def write(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


class SorceryCompletionAuditV2Tests(unittest.TestCase):
    def fixtures(self, root: Path):
        baseline = {
            "format_version": "AA8_SORCERY_PERSISTENCE_SNAPSHOT_V1",
            "owner": 1,
            "character": {
                "id": "1",
                "name": "Dannia",
                "ability1": "7",
                "ability2": "6",
                "ability3": "2",
            },
            "sorcery_ability": {"id": "7", "exp": "100"},
            "sorcery_skills": [{"id": "10752", "level": "1", "type": "Skill"}],
            "sorcery_passives": [
                {"id": str(skill_id), "level": "1", "type": "Buff"}
                for skill_id in (15, 38, 99, 257, 258, 301)
            ],
            "summary": {
                "learned_sorcery_passive_count": 6,
                "learned_sorcery_skill_count": 1,
                "heir_activation_count": 0,
            },
        }
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
            "prior.json": {"roots": [{"skill_id": 10752, "manual_acceptance": "pending"}]},
            "reconciliation.json": {"coverage": {"blocked_entrypoints": []}},
            "baseline.json": baseline,
            "live.json": {
                "roots": [
                    {
                        "skill_id": 10752,
                        "runtime_status": "server_lifecycle_complete",
                        "visual_status": "manual_evidence_required",
                    }
                ]
            },
        }
        for name, payload in payloads.items():
            write(root / name, payload)
        return baseline

    def ledger(self, status="pending"):
        evidence = ["client-video:10752"] if status == "confirmed" else []
        return {
            "format_version": LEDGER_FORMAT,
            "roots": [
                {
                    "skill_id": 10752,
                    "manual_gates": {
                        gate: {"status": status, "evidence": evidence, "notes": ""}
                        for gate in ("visual_fx_sound_animation", "second_use", "relog")
                    },
                }
            ],
        }

    def build(self, root: Path, post_relog=None):
        return build_audit(
            root / "executable.json",
            root / "prior.json",
            root / "reconciliation.json",
            root / "baseline.json",
            root / "live.json",
            root / "ledger.json",
            root / "post.json" if post_relog else None,
        )

    def test_pending_manual_or_post_relog_evidence_cannot_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixtures(root)
            write(root / "ledger.json", self.ledger())

            audit = self.build(root)

            self.assertEqual("not_complete", audit["completion"]["status"])
            self.assertEqual(0, audit["completion"]["current_visual_complete_root_count"])
            self.assertIn("visual_repeat_and_relog_matrix", audit["completion"]["incomplete_requirement_ids"])
            self.assertIn("post_relog_persistence", audit["completion"]["incomplete_requirement_ids"])

    def test_complete_requires_confirmed_evidence_and_consistent_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = self.fixtures(root)
            write(root / "ledger.json", self.ledger("confirmed"))
            post = json.loads(json.dumps(baseline))
            post["sorcery_ability"]["exp"] = "125"
            write(root / "post.json", post)

            audit = self.build(root, post_relog=post)

            self.assertEqual("complete", audit["completion"]["status"])
            self.assertEqual(1, audit["completion"]["current_visual_complete_root_count"])
            self.assertEqual(0, audit["completion"]["post_relog_mismatch_count"])
            self.assertEqual([], audit["roots"][0]["remaining"])


if __name__ == "__main__":
    unittest.main()
