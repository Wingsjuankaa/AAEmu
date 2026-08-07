import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "reconstruccion_skills_8" / "SORCERY_FULL_BRANCH_RECONSTRUCTION_DOSSIER_V1.md"
GUIDE = ROOT / "reconstruccion_skills_8" / "SKILL_TREE_RECONSTRUCTION_GUIDE_V1.md"
FINAL_CAPTURE = ROOT / "runtime-captures" / "native-skill-live-sorcery-close-v24.json"


class ReconstructionDocumentationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = DOSSIER.read_text(encoding="utf-8")
        cls.guide = GUIDE.read_text(encoding="utf-8")

    def test_documented_implementation_files_exist(self):
        inventory = self.dossier.split(
            "## Inventario de archivos de implementacion intervenidos", 1
        )[1].split("## Criterio reusable", 1)[0]
        paths = sorted(set(re.findall(r"`([^`]+\.(?:cs|py|sql|json))`", inventory)))
        self.assertGreaterEqual(len(paths), 70)
        missing = [path for path in paths if not (ROOT / path).exists()]
        self.assertEqual([], missing)

    def test_inventory_covers_each_reconstruction_layer(self):
        required = {
            "AAEmu.Game/Core/Managers/SkillManager.cs",
            "AAEmu.Game/Models/Game/Char/CharacterHeirProgression.cs",
            "AAEmu.Game/Models/Game/Skills/Skill.cs",
            "AAEmu.Game/Models/Game/Skills/Effects/DamageEffect.cs",
            "AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotTree.cs",
            "AAEmu.Game/Models/Game/DoodadObj/Funcs/DoodadFuncClout.cs",
            "AAEmu.Game/Models/Game/World/AreaShape.cs",
            "AAEmu.Game/Models/Game/Skills/NativeSkillLiveTrace.cs",
            "AAEmu.Tests/SorceryDamageEffectTests.cs",
            "reconstruccion_skills_8/sorcery/build_sorcery_runtime_v23.py",
            "reconstruccion_skills_8/sorcery/test_sorcery_ancestral_closure_v23.py",
        }
        absent = sorted(path for path in required if f"`{path}`" not in self.dossier)
        self.assertEqual([], absent)

    def test_guide_contains_all_reusable_boundaries(self):
        required_phrases = (
            "pase obligatorio por crosswalk 10.x",
            "relaciones owner-keyed",
            "cerrar relaciones consultadas en sentido inverso",
            "cached results owner-keyed sin columna id",
            "casteos liberables y eventos de ciclo de vida",
            "propagar autoridad por contenedores diferidos",
            "una relacion diferida no esta cerrada",
        )
        missing = [phrase for phrase in required_phrases if phrase not in self.guide]
        self.assertEqual([], missing)

    def test_sorcery_live_closure_is_authoritative(self):
        self.assertIn("Sorcery queda `live_accepted` al 100%", self.dossier)
        capture_bytes = FINAL_CAPTURE.read_bytes()
        self.assertEqual(
            "DD7FC017F43B869CCCCCBDC63068C79A4E4FE7D972F7A58848AA16FBFDE44EDC",
            hashlib.sha256(capture_bytes).hexdigest().upper(),
        )
        capture = json.loads(capture_bytes)
        flame_barrier = next(
            execution
            for execution in capture["executions"]
            if execution["skill_id"] == 41478
        )
        self.assertEqual("damage_and_lifecycle_confirmed", flame_barrier["verdict"])
        self.assertEqual(16, flame_barrier["authoritative_hit_count"])
        self.assertEqual(6625, flame_barrier["hp_delta_total"])
        self.assertEqual(16, flame_barrier["packet_true_count"])
        self.assertEqual([], capture["error_lines"])


if __name__ == "__main__":
    unittest.main()
