from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
MANIFEST = (
    DOMAIN / "generated" / "native-npc-visual-v1-runtime-manifest.json"
)
RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-npc-visual-v1.sqlite3"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


class NativeNpcVisualCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(
            f"file:{RUNTIME.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_manifest_identity_and_deterministic_output_hash(self) -> None:
        self.assertEqual("native-npc-visual-catalog-v1", self.manifest["phase"])
        self.assertEqual(
            "ArcheAge Kakao 8.0.3.12 r558734",
            self.manifest["authority"],
        )
        self.assertEqual(
            self.manifest["output"]["sha256"],
            sha256(RUNTIME),
        )
        self.assertEqual(
            "ECCC638F6DC1042F3ACD764729B8B1B4D0B326DB04F5A0DF38DB8AFB4285E319",
            self.manifest["dossier"]["json_sha256"],
        )

    def test_bounded_visible_npc_scope_is_frozen(self) -> None:
        scope = self.manifest["scope"]
        self.assertEqual(14921, scope["target_npcs"])
        self.assertEqual(285, scope["deferred_spawned_native_npcs"])
        self.assertEqual(940, scope["target_models"])
        self.assertEqual(895, scope["target_actor_models"])
        self.assertEqual(1546, scope["total_character_customs"])
        self.assertEqual(2717, scope["visual_items"])
        self.assertEqual(1552, scope["armor_items"])
        self.assertEqual(448, scope["weapon_items"])
        self.assertEqual(717, scope["body_parts"])

    def test_runtime_closure_has_no_enabled_visual_orphans(self) -> None:
        validation = self.manifest["validation"]
        self.assertEqual("ok", validation["quick_check"])
        self.assertEqual("ok", validation["integrity_check"])
        self.assertTrue(validation["items_catalog_unchanged"])
        self.assertTrue(validation["item_definition_coverage_unchanged"])
        self.assertTrue(
            validation["existing_npc_non_presentation_fields_unchanged"]
        )
        self.assertTrue(validation["native_presentation_projection_exact"])
        self.assertTrue(
            all(value == 0 for value in validation["orphan_audits"].values())
        )

    def test_presentation_allow_list_is_descriptor_bounded(self) -> None:
        counts = dict(
            self.connection.execute(
                "SELECT visual_kind,COUNT(*) FROM aaemu_npc_visual_items "
                "GROUP BY visual_kind ORDER BY visual_kind"
            )
        )
        self.assertEqual(
            {"armor": 1552, "body_part": 717, "weapon": 448},
            counts,
        )
        sentinel_count = self.connection.execute(
            "SELECT COUNT(*) FROM aaemu_npc_visual_items WHERE item_id=0"
        ).fetchone()[0]
        self.assertEqual(0, sentinel_count)
        missing = self.connection.execute(
            """
            SELECT COUNT(*) FROM aaemu_npc_visual_items v
            LEFT JOIN item_armors a
              ON v.visual_kind='armor' AND a.item_id=v.item_id
            LEFT JOIN item_weapons w
              ON v.visual_kind='weapon' AND w.item_id=v.item_id
            LEFT JOIN item_body_parts b
              ON v.visual_kind='body_part' AND b.item_id=v.item_id
            WHERE a.item_id IS NULL AND w.item_id IS NULL AND b.item_id IS NULL
            """
        ).fetchone()[0]
        self.assertEqual(0, missing)

    def test_legacy_spawn_ids_without_aa8_rows_remain_negative_evidence(self) -> None:
        ids = self.manifest["negative_evidence"][
            "configured_spawn_templates_absent_from_runtime_and_native_catalog"
        ]
        self.assertEqual(46, len(ids))
        placeholders = ",".join("?" for _ in ids)
        inserted = self.connection.execute(
            f"SELECT COUNT(*) FROM npcs WHERE id IN ({placeholders})", ids
        ).fetchone()[0]
        self.assertEqual(0, inserted)

        deferred = self.manifest["negative_evidence"][
            "configured_spawn_templates_native_but_runtime_deferred"
        ]
        self.assertEqual(285, len(deferred))
        placeholders = ",".join("?" for _ in deferred)
        inserted = self.connection.execute(
            f"SELECT COUNT(*) FROM npcs WHERE id IN ({placeholders})", deferred
        ).fetchone()[0]
        self.assertEqual(0, inserted)


if __name__ == "__main__":
    unittest.main()
