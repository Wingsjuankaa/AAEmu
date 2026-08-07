from __future__ import annotations

import unittest

from summarize_native_skill_live_trace_v1 import build_summary, parse_line


class NativeSkillLiveTraceSummaryV1Tests(unittest.TestCase):
    def test_parses_and_summarizes_archery_passive_transition(self) -> None:
        base = (
            "move=1.0000 rangedAccuracy=0.9000 rangedCritical=0.1000 "
            "rangedCriticalBonus=0.0000 rangedCriticalMul=1.5000 "
            "rangedDamageMul=1.0000 endlessDamage=100.0000 "
            "endlessRange=20.0000 concussiveCooldown=4000.0000"
        )
        changed = base.replace("move=1.0000", "move=1.0800")
        log = "\n".join((
            f"[AA8ArcheryPassive] phase=before_apply passive=2 buff=480 char=7 {base}",
            f"[AA8ArcheryPassive] phase=after_apply passive=2 buff=480 char=7 {changed}",
        )).encode()

        summary = build_summary(log)
        self.assertEqual(2, summary["summary"]["passive_snapshot_count"])
        self.assertEqual(1, summary["summary"]["passive_transition_count"])
        transition = summary["passive_transitions"][0]["transitions"][0]
        self.assertEqual("apply", transition["operation"])
        self.assertEqual(["move"], transition["changed_fields"])

    def test_parses_damage_event(self) -> None:
        event = parse_line(
            "game | [AA8SkillDamage] tree=sorcery skill=39674 tlId=12 "
            "effect=12133 caster=1 target=2 type=Magic amount=500 absorbed=20 "
            "hpBefore=1000 hpAfter=500 packet=True"
        )
        self.assertEqual("damage", event["kind"])
        self.assertEqual(500, event["amount"])
        self.assertEqual("True", event["packet"])

    def test_confirms_authoritative_damage_and_lifecycle(self) -> None:
        log = "\n".join(
            (
                "[AA8SorceryLive] phase=use_result skill=39674 tlId=12 caster=1 "
                "target=2 world=1 instance=0 mp=900 magicSource=0 targets=-1 "
                "effects=-1 result=Success cancelled=-",
                "[AA8SorceryLive] phase=plot_event_executed skill=39674 tlId=12 "
                "caster=1 target=2 world=1 instance=0 mp=900 magicSource=0 "
                "targets=3 effects=1 result=- cancelled=-",
                "[AA8SkillDamage] tree=sorcery skill=39674 tlId=12 effect=12133 "
                "caster=1 target=2 type=Magic amount=500 absorbed=20 "
                "hpBefore=1000 hpAfter=500 packet=True",
                "[AA8SorceryLive] phase=plot_ended skill=39674 tlId=12 caster=1 "
                "target=2 world=1 instance=0 mp=900 magicSource=0 targets=-1 "
                "effects=-1 result=- cancelled=False",
            )
        ).encode()
        summary = build_summary(log)
        row = summary["executions"][0]
        self.assertEqual("damage_and_lifecycle_confirmed", row["verdict"])
        self.assertEqual(1, row["authoritative_hit_count"])
        self.assertEqual(500, row["hp_delta_total"])
        self.assertEqual(1, row["packet_true_count"])

    def test_separates_rejection_and_reports_errors(self) -> None:
        log = "\n".join(
            (
                "[AA8ArcheryLive] phase=use_result skill=11933 tlId=4 caster=7 "
                "target=9 world=1 instance=0 mp=1000 targets=-1 effects=-1 "
                "result=UrkEquipRanged cancelled=-",
                "[ERROR] synthetic failure",
            )
        ).encode()
        summary = build_summary(log)
        self.assertEqual("rejected", summary["executions"][0]["verdict"])
        self.assertEqual(1, summary["summary"]["error_line_count"])


if __name__ == "__main__":
    unittest.main()
