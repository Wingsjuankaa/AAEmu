from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from build_specialization_runtime import (
    DEFAULT_CATALOG,
    configured_output_dir,
    env_value,
    extend_interaction_doodad_closure,
    resolve_ability,
    select_runtime_rows,
    validate_graph,
)


class SpecializationRuntimeIdentityTests(unittest.TestCase):
    def test_ability_accepts_id_name_and_slug(self) -> None:
        self.assertEqual(resolve_ability("12"), (12, "Swiftblade", "swiftblade"))
        self.assertEqual(resolve_ability("Swiftblade"), (12, "Swiftblade", "swiftblade"))
        self.assertEqual(resolve_ability("swiftblade"), (12, "Swiftblade", "swiftblade"))

    def test_unknown_ability_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_ability("not-a-spec")

    def test_compact_carrier_is_read_from_env(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".env"
            path.write_text("IGNORED=1\nCOMPACT_DB='D:/runtime.sqlite3'\n", encoding="utf-8")
            self.assertEqual(env_value(path, "COMPACT_DB"), "D:/runtime.sqlite3")


class SpecializationRuntimeContractTests(unittest.TestCase):
    def test_sorcery_graph_keeps_only_native_blockers_quarantined(self) -> None:
        output = configured_output_dir()
        graph = output / "sorcery-specialization-graph-v1.sqlite3"
        manifest = output / "sorcery-specialization-graph-v1.manifest.json"
        if not graph.is_file() or not manifest.is_file() or not DEFAULT_CATALOG.is_file():
            self.skipTest("AA8 forensic artifacts are not available")
        contract = validate_graph(
            graph,
            manifest,
            7,
            "Sorcery",
            "sorcery",
            DEFAULT_CATALOG,
        )
        catalog = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
        _, selection = select_runtime_rows(contract, catalog)

        self.assertEqual(len(contract["root_skill_ids"]), 40)
        self.assertEqual(len(contract["visible_skill_ids"]), 10)
        self.assertEqual(sum(contract["test_states"].values()), 360)
        self.assertEqual(len(selection["enabled_skill_ids"]), 36)
        self.assertEqual(
            selection["quarantined_skill_ids"],
            [11939, 36477, 36478, 39674],
        )
        self.assertEqual(selection["passive_ids"], [15, 38, 99, 257, 258, 301])
        self.assertEqual(
            selection["passive_buff_ids"],
            [536, 962, 963, 2910, 7566, 7567],
        )

    def test_swiftblade_graph_and_catalog_form_a_closed_slice(self) -> None:
        output = configured_output_dir()
        graph = output / "swiftblade-specialization-graph-v1.sqlite3"
        manifest = output / "swiftblade-specialization-graph-v1.manifest.json"
        if not graph.is_file() or not manifest.is_file() or not DEFAULT_CATALOG.is_file():
            self.skipTest("AA8 forensic artifacts are not available")
        contract = validate_graph(
            graph,
            manifest,
            12,
            "Swiftblade",
            "swiftblade",
            DEFAULT_CATALOG,
        )
        catalog = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
        selected, selection = select_runtime_rows(contract, catalog)
        doodads = extend_interaction_doodad_closure(selected, selection, catalog, 12)
        self.assertEqual(len(contract["root_skill_ids"]), 46)
        self.assertEqual(len(contract["visible_skill_ids"]), 12)
        self.assertEqual(sum(contract["test_states"].values()), 414)
        self.assertEqual(len(selection["enabled_skill_ids"]), 46)
        self.assertEqual(selection["quarantined_skill_ids"], [])
        self.assertEqual(len(selection["passive_ids"]), 6)
        self.assertTrue({13939, 14104, 14130, 14131}.issubset(doodads["doodad_ids"]))
        self.assertTrue({13939, 14104, 14130, 14131}.issubset(doodads["materialized_doodad_ids"]))
        self.assertTrue({41129, 41531, 41584, 41585}.issubset(doodads["group_ids"]))
        self.assertEqual(doodads["func_ids"], [])
        self.assertTrue(doodads["func_ids_pending"])
        self.assertTrue({3805, 3826, 3828, 3829}.issubset(doodads["clout_ids"]))
        self.assertTrue({52656, 53018, 53088, 53089}.issubset(doodads["phase_func_ids"]))
        self.assertTrue(
            {24640, 24906, 24951, 24952}.issubset(
                doodads["native_buff_closure"]["buffs"]
            )
        )
        self.assertTrue(
            {15500, 15686, 15707, 15708}.issubset(
                doodads["native_buff_closure"]["aoe_shapes"]
            )
        )


if __name__ == "__main__":
    unittest.main()
