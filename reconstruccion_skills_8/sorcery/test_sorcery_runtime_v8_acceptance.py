from __future__ import annotations

import importlib.util
import json
import sqlite3
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_sorcery_runtime_v8.py")
SPEC = importlib.util.spec_from_file_location("sorcery_runtime_v8_builder", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


class SorceryRuntimeV8AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.args = builder.parse_args([])
        cls.evidence = builder.validate_sources(cls.args)
        cls.manifest = json.loads(cls.args.manifest.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(cls.args.output)
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_stable_crosswalk_preserves_the_formula_spine(self) -> None:
        comparison = self.evidence["crosswalk"]
        self.assertEqual("stable_id_changed_properties", comparison["classification"])
        self.assertEqual("stable", comparison["relation_state"])
        self.assertEqual("changed", comparison["property_state"])

    def test_insulating_lens_promotes_only_the_corroborated_percent_contract(self) -> None:
        row = dict(
            self.connection.execute(
                "SELECT * FROM extend_charge_effects WHERE id=1"
            ).fetchone()
        )
        self.assertEqual(builder.PROMOTED_ROW, row)
        self.assertEqual(95, row["charge_buff_id"])
        self.assertEqual(5, row["percent_min"])
        self.assertEqual(5, row["percent_max"])
        self.assertEqual(4, row["percent_damage_resource_type_id"])

    def test_aa8_visible_contract_and_resource_enum_are_both_present(self) -> None:
        self.assertIn(
            "#{avg_damage}#{detail_spell_damage}",
            self.evidence["localization"],
        )
        self.assertEqual(
            {"id": 4, "name": "max_mana"},
            self.evidence["resource_enum"],
        )

    def test_manifest_and_sqlite_are_integral(self) -> None:
        self.assertEqual(8, self.manifest["format_version"])
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])
        self.assertEqual(
            self.manifest["output"]["sha256"],
            builder.sha256_file(self.args.output),
        )


if __name__ == "__main__":
    unittest.main()
