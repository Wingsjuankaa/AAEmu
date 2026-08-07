import unittest
from pathlib import Path

from summarize_sorcery_live_trace_v1 import build_summary, parse_event


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "generated" / "sorcery-executable-semantics-audit-v3.json"


def event(phase, skill, tl_id, result="-", cancelled="-"):
    return (
        "game-1 | 10:00:00 [INFO] SorceryLiveTrace - [AA8SorceryLive] "
        f"phase={phase} skill={skill} tlId={tl_id} caster=100 target=200 "
        "world=0 instance=1 mp=5000 magicSource=20 targets=1 effects=2 "
        f"result={result} cancelled={cancelled}\n"
    )


class SorceryLiveTraceV1Tests(unittest.TestCase):
    def test_parser_ignores_unrelated_and_malformed_lines(self):
        self.assertIsNone(parse_event("ordinary game log"))
        self.assertIsNone(parse_event("[AA8SorceryLive] phase=fired skill=x"))

        parsed = parse_event(event("fired", 10153, 7))
        self.assertEqual(10153, parsed["skill"])
        self.assertEqual(20, parsed["magicSource"])

    def test_summary_separates_complete_partial_and_visual_gates(self):
        log = "".join(
            [
                event("use_result", 10153, 7, "Success"),
                event("fired", 10153, 7),
                event("effects_selected", 10153, 7),
                event("effects_applied", 10153, 7, cancelled="False"),
                event("ended", 10153, 7, cancelled="False"),
                event("use_result", 10151, 8, "Success"),
                event("plot_event_25974", 10151, 8),
                event("plot_ended", 10151, 8, cancelled="False"),
                event("use_result", 10664, 9, "TooFarRange"),
            ]
        ).encode("utf-8")

        summary = build_summary(log, AUDIT)
        rows = {row["skill_id"]: row for row in summary["roots"]}

        self.assertEqual("server_lifecycle_complete", rows[10153]["runtime_status"])
        self.assertEqual("server_lifecycle_complete", rows[10151]["runtime_status"])
        self.assertEqual(1, rows[10151]["plot_event_count"])
        self.assertEqual("rejected_only", rows[10664]["runtime_status"])
        self.assertEqual("not_observed", rows[10667]["runtime_status"])
        self.assertEqual("manual_evidence_required", rows[10153]["visual_status"])
        self.assertFalse(summary["summary"]["visual_gate_complete"])


if __name__ == "__main__":
    unittest.main()
