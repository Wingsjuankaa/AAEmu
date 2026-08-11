import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "reconstruccion_skills_8"
BATTLERAGE = SKILLS / "battlerage"
CLOSURE = BATTLERAGE / "CHECKPOINT_BATTLERAGE_STAGE1_CLOSURE_V10.md"
MATRIX = BATTLERAGE / "MATRIZ_BATTLERAGE.md"
GUIDE = SKILLS / "SKILL_TREE_RECONSTRUCTION_GUIDE_V1.md"

SHARED = (
    "CHECKPOINT_AA8_COOLDOWN_AUTHORITY_V1.md",
    "CHECKPOINT_AA8_PLOT_TIMING_COMBAT_SYNC_V1.md",
    "CHECKPOINT_AA8_PASSIVE_BUFF_LIFECYCLE_V1.md",
    "CHECKPOINT_AA8_COMBO_GCD_ADMISSION_V1.md",
    "CHECKPOINT_AA8_PLOT_ONLY_POSITIONAL_PRESENTATION_V1.md",
    "CHECKPOINT_AA8_BUFF_CREATED_TOGGLE_LINK_V1.md",
    "CHECKPOINT_MECHANICS_LAB_V1.md",
)


class BattlerageStage1DocumentationV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = CLOSURE.read_text(encoding="utf-8")
        cls.matrix = MATRIX.read_text(encoding="utf-8")
        cls.guide = GUIDE.read_text(encoding="utf-8")

    def test_all_visible_families_are_stage1_accepted(self):
        active_table = self.matrix.split("## Activas visibles", 1)[1].split(
            "## Automáticas y pasivas", 1
        )[0]
        rows = [
            line
            for line in active_table.splitlines()
            if re.match(r"^\| [A-Za-z]", line)
            and not line.startswith("| Habilidad")
        ]
        self.assertEqual(12, len(rows))
        self.assertTrue(all("PASS etapa 1" in row for row in rows))
        self.assertNotIn("pendiente", active_table.lower())

    def test_closure_separates_inherited_and_new_evidence(self):
        required = (
            "## Qué ya existía antes de Battlerage",
            "## Evidencia nueva aportada por Battlerage",
            "Evidencia negativa/falsificada",
            "## Bootstrap obligatorio para la siguiente rama",
            "627/627 PASS",
            "25/25 PASS",
            "BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58",
        )
        self.assertEqual([], [item for item in required if item not in self.closure])

    def test_promoted_shared_checkpoints_exist_and_are_linked(self):
        shared_root = SKILLS / "shared_primitives"
        missing = [name for name in SHARED if not (shared_root / name).is_file()]
        self.assertEqual([], missing)
        unlinked = [name for name in SHARED if name not in self.closure]
        self.assertEqual([], unlinked)

    def test_guide_promotes_battlerage_boundaries(self):
        required = (
            "Enmienda V1.16: cooldown como estado autoritativo",
            "Enmienda V1.17: componer tiempos por fase",
            "Enmienda V1.18: el catálogo de pasivas",
            "Enmienda V1.19: cierre de rama basado en delta",
            "CHECKPOINT_BATTLERAGE_STAGE1_CLOSURE_V10.md",
        )
        self.assertEqual([], [item for item in required if item not in self.guide])


if __name__ == "__main__":
    unittest.main()
