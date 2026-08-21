import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "reconstruccion_cliente_10" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_quest_stage40 import evaluate_strict_gate, inspect_server  # noqa: E402
from quest_stage40_ci_gate import evaluate_snapshot, load_baseline  # noqa: E402


class QuestStage40CiGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = load_baseline(
            REPO / "reconstruccion_cliente_10" / "gates" / "quest-stage40-baseline.csv"
        )
        cls.classes, cls.loaders, _, cls.stubs, _, cls.server_text = inspect_server(REPO)
        cls.config_text = (REPO / "AAEmu.Game" / "Configurations" / "QuestCoverage.json").read_text(
            encoding="utf-8-sig"
        )

    def evaluate(self, *, classes=None, loaders=None, stubs=None, server_text=None, config_text=None):
        return evaluate_snapshot(
            self.baseline,
            self.classes if classes is None else classes,
            self.loaders if loaders is None else loaders,
            self.stubs if stubs is None else stubs,
            self.server_text if server_text is None else server_text,
            self.config_text if config_text is None else config_text,
        )

    def test_current_snapshot_passes(self):
        self.assertEqual([], self.evaluate())

    def test_missing_class_fails(self):
        classes = set(self.classes)
        classes.remove("QuestActSupplySkill")
        self.assertIn("missing_server_class", {row["code"] for row in self.evaluate(classes=classes)})

    def test_missing_loader_fails(self):
        loaders = set(self.loaders)
        loaders.remove("QuestActEtcItemObtain")
        self.assertIn("missing_detail_loader", {row["code"] for row in self.evaluate(loaders=loaders)})

    def test_stub_fails(self):
        stubs = set(self.stubs)
        stubs.add("QuestActSupplySkill")
        self.assertIn("stub_or_partial", {row["code"] for row in self.evaluate(stubs=stubs)})

    def test_missing_producer_fails(self):
        text = self.server_text.replace("QuestObjectiveEventType.ConquestWar", "removed-producer")
        self.assertIn("missing_phase3_producer", {row["code"] for row in self.evaluate(server_text=text)})

    def test_report_mode_cannot_replace_strict_default(self):
        self.assertIn("strict_mode_not_enabled", {row["code"] for row in self.evaluate(config_text='{"Mode":"Report"}')})

    def test_full_authority_gate_rejects_an_unresolved_enabled_reference(self):
        metrics = {
            "orphan_components": 0,
            "orphan_acts": 0,
            "nuia_unsupported_enabled_acts": 0,
            "unresolved_enabled_act_refs": 1,
            "unclassified_act_types": 1,
            "missing_detail_table_enabled_refs": 0,
            "missing_detail_row_enabled_refs": 0,
            "duplicate_runtime_detail_bindings": 0,
            "phase2_unimplemented_enabled_refs": 0,
            "phase2_constant_return_enabled_refs": 0,
            "phase3_blocked_enabled_refs": 0,
            "phase3_missing_producer_enabled_refs": 0,
            "phase4_candidate_enabled_refs": 0,
            "phase4_blocked_enabled_refs": 0,
            "implemented_enabled_act_refs": 9,
            "enabled_act_refs": 10,
            "phase3_implemented_enabled_refs": 3,
            "phase3_enabled_refs": 3,
            "phase4_implemented_enabled_refs": 4,
            "phase4_enabled_refs": 4,
            "phase4_reward_ledger_present": 1,
        }
        findings = evaluate_strict_gate({"integrity": metrics})
        self.assertIn("unresolved_enabled_act_refs", {row["metric"] for row in findings})

    def test_full_authority_gate_accepts_a_zero_matrix(self):
        metrics = {
            "orphan_components": 0,
            "orphan_acts": 0,
            "nuia_unsupported_enabled_acts": 0,
            "unresolved_enabled_act_refs": 0,
            "unclassified_act_types": 0,
            "missing_detail_table_enabled_refs": 0,
            "missing_detail_row_enabled_refs": 0,
            "duplicate_runtime_detail_bindings": 0,
            "phase2_unimplemented_enabled_refs": 0,
            "phase2_constant_return_enabled_refs": 0,
            "phase3_blocked_enabled_refs": 0,
            "phase3_missing_producer_enabled_refs": 0,
            "phase4_candidate_enabled_refs": 0,
            "phase4_blocked_enabled_refs": 0,
            "implemented_enabled_act_refs": 10,
            "enabled_act_refs": 10,
            "phase3_implemented_enabled_refs": 3,
            "phase3_enabled_refs": 3,
            "phase4_implemented_enabled_refs": 4,
            "phase4_enabled_refs": 4,
            "phase4_reward_ledger_present": 1,
        }
        self.assertEqual([], evaluate_strict_gate({"integrity": metrics}))


if __name__ == "__main__":
    unittest.main()
