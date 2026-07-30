from __future__ import annotations

import json
import sqlite3
import struct
import tempfile
import unittest
from pathlib import Path

from ..candidates import generate_family, verify_candidate
from ..config import ForensicsConfig
from ..pipeline import _verify_structural_result_absence, run_pipeline
from ..reporting import explain_item, generate_report
from ..util import sha256_file


def create_client(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE items(
            id INTEGER PRIMARY KEY,
            impl_id INTEGER NOT NULL,
            name TEXT,
            description TEXT,
            category_id INTEGER,
            level INTEGER,
            use_skill_id INTEGER,
            buff_id INTEGER,
            craft_id INTEGER,
            loot_quest_id INTEGER
        );
        INSERT INTO items VALUES
            (-1,0,'signed anomaly','',0,0,0,0,0,0),
            (100,33,'Native Material','client',1,1,0,0,0,0),
            (101,7,'Opaque Tool','client',1,1,500,0,0,0),
            (102,27,'Native Dye','client',1,1,500,0,0,0),
            (103,0,'Native Dye Ticket','client',1,1,500,0,0,0);
        """
    )
    connection.commit()
    connection.close()


def create_runtime(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE items(id INTEGER PRIMARY KEY, impl_id INTEGER, name TEXT);
        INSERT INTO items VALUES
            (100,33,'Native Material'),
            (101,7,'Opaque Tool'),
            (102,27,'Native Dye'),
            (103,0,'Native Dye Ticket');
        CREATE TABLE item_evolving_materials(
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL
        );
        INSERT INTO item_evolving_materials VALUES (1,100,3);
        CREATE TABLE skills(id INTEGER PRIMARY KEY);
        INSERT INTO skills VALUES (500);
        CREATE TABLE aaemu_item_definition_coverage(
            item_id INTEGER PRIMARY KEY,
            concrete_type TEXT NOT NULL,
            coverage TEXT NOT NULL,
            missing_dependencies TEXT NOT NULL,
            provenance TEXT NOT NULL
        );
        INSERT INTO aaemu_item_definition_coverage VALUES
            (100,'evolving_material','complete','',
             'client_compact_8+game11_native+x2game_confirmed'),
            (101,'generic','catalog_only','concrete_type_not_recovered',
             'client_compact_8'),
            (102,'dyeing','phase_a_candidate','manual_client_acceptance',
             'client_compact_8+game11_native+x2game_confirmed+backend_implemented'),
            (103,'dyeing_ticket','phase_a_candidate','manual_client_acceptance',
             'client_compact_8+game11_native+x2game_confirmed+backend_implemented');
        """
    )
    connection.commit()
    connection.close()


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        (self.repo / "AAEmu.Game").mkdir()
        source = self.repo / "AAEmu.Game" / "ItemManager.cs"
        source.write_text(
            'const string Table = "item_evolving_materials";',
            encoding="utf-8",
        )
        (self.repo / "AAEmu.Game" / "Dyeing.cs").write_text(
            "public sealed class Dyeing {}",
            encoding="utf-8",
        )
        self.item_root = self.repo / "reconstruccion_items_8"
        self.item_root.mkdir()
        character_generated = (
            self.repo / "reconstruccion_character_8" / "generated"
        )
        character_generated.mkdir(parents=True)
        reviewed_root = root / "reviewed-client"
        reviewed_root.mkdir()
        (reviewed_root / "item-reference.xml").write_text(
            '<reward item_id="100"/>',
            encoding="utf-8",
        )
        (character_generated / "client-filesystem-global-v1-manifest.json").write_text(
            json.dumps(
                {
                    "authority": "Kakao 8.0.3.12 r558734",
                    "classification": {
                        "focus_hits_are_authority": False,
                    },
                    "source": str(reviewed_root),
                    "files": [
                        {
                            "path": "item-reference.xml",
                            "extension": ".xml",
                            "bytes": 23,
                            "sha256": "FIXTURE",
                            "focus_hits": ["item"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        extractor = self.item_root / "extract_native_fixture.py"
        extractor.write_text(
            """
TABLES = {
    "item_evolving_materials": {
        "columns": ["id", "item_id", "category_id"],
        "layout": ["68", "68", "68"],
        "anchor_id": 1,
        "anchor": {"item_id": 100, "category_id": 3},
        "expected": 1,
        "layout_source": "fixture x2game loader",
    }
}
""",
            encoding="utf-8",
        )
        client = root / "client.sqlite"
        runtime = root / "runtime.sqlite"
        create_client(client)
        create_runtime(runtime)
        streams = root / "streams"
        streams.mkdir()
        (streams / "game11").write_bytes(
            b"\x64" + struct.pack("<iii", 1, 100, 3) + b"\x65"
        )
        sql_manifest = root / "sql.json"
        sql_manifest.write_text(
            json.dumps(
                {
                    "binaries": [
                        {
                            "path": "x2game.dll",
                            "sha256": "FIXTURE",
                            "statements": [
                                {
                                    "offset": 10,
                                    "sha256": "QUERY",
                                    "tables": ["item_evolving_materials"],
                                    "value": (
                                        "SELECT id,item_id,category_id "
                                        "FROM item_evolving_materials"
                                    ),
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        runtime_env = self.repo / ".env"
        runtime_env.write_text(f"COMPACT_DB={runtime}\n", encoding="utf-8")
        output = root / "output"
        self.config = ForensicsConfig(
            client_build="Kakao 8.0.3.12 r558734",
            client_compact=client,
            streams_root=streams,
            repo_root=self.repo,
            legacy_item_root=self.item_root,
            output_dir=output,
            runtime_env=runtime_env,
            runtime=runtime,
            sql_manifest=sql_manifest,
            surface_manifest=None,
            gamepak_index=None,
            x2game=(),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_pipeline_is_deterministic_and_generates_safe_candidate(self) -> None:
        first = run_pipeline(self.config, deep=True)
        first_hash = sha256_file(self.config.database)
        second = run_pipeline(self.config, deep=True)
        second_hash = sha256_file(self.config.database)
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first["scan"]["positive_items"], 4)
        self.assertEqual(second["decode"]["result_statuses"]["confirmed"], 1)
        self.assertEqual(second["surfaces"]["manifests"], 2)
        self.assertEqual(second["surfaces"]["references"], 1)

        explanation = explain_item(self.config.database, 100)
        states = {
            value["dimension"]: value["state"]
            for value in explanation["capabilities"]
        }
        self.assertEqual(states["descriptor"], "confirmed")
        self.assertEqual(states["backend"], "confirmed")
        self.assertEqual(len(explanation["surface_references"]), 1)

        dyeing = explain_item(self.config.database, 102)
        dyeing_states = {
            value["dimension"]: value["state"]
            for value in dyeing["capabilities"]
        }
        self.assertEqual(dyeing_states["dependency_closure"], "confirmed")
        self.assertEqual(dyeing_states["backend"], "confirmed")
        self.assertEqual(dyeing_states["protocol"], "confirmed")
        self.assertEqual(dyeing_states["persistence"], "unknown")
        self.assertEqual(dyeing_states["validation"], "unknown")

        ticket = explain_item(self.config.database, 103)
        ticket_states = {
            value["dimension"]: value["state"]
            for value in ticket["capabilities"]
        }
        self.assertEqual(ticket_states["dependency_closure"], "confirmed")
        self.assertEqual(ticket_states["backend"], "confirmed")
        self.assertEqual(ticket_states["protocol"], "confirmed")
        self.assertEqual(ticket_states["persistence"], "unknown")
        self.assertEqual(ticket_states["validation"], "unknown")

        report = generate_report(self.config)
        self.assertTrue(report["html"].is_file())
        self.assertIn("AA8 Item Forensics", report["html"].read_text(encoding="utf-8"))

        candidate = generate_family(self.config, "evolving_material")
        verification = verify_candidate(candidate["directory"])
        self.assertTrue(verification["ok"], verification["failures"])
        manifest = json.loads(candidate["manifest"].read_text(encoding="utf-8"))
        self.assertFalse(manifest["deployable"])
        self.assertEqual(manifest["historical_3_0_gameplay_rows"], 0)

    def test_structural_absence_verifier_detects_an_unassigned_result(self) -> None:
        (self.config.streams_root / "game11").write_bytes(
            b"\x65\x64"
            + struct.pack("<I", 1)
            + b"\x64"
            + struct.pack("<iii", 1, 100, 3)
            + b"\x65"
        )
        verification = _verify_structural_result_absence(
            self.config,
            ("id", "item_id", "category_id"),
            ("68", "68", "68"),
            {},
            {
                "id_column": "id",
                "nonnegative_columns": ["item_id", "category_id"],
            },
        )
        self.assertEqual(
            verification["stream_header_counts"],
            {"game11": 1},
        )
        self.assertEqual(len(verification["structural_matches"]), 1)
        self.assertEqual(len(verification["semantic_matches"]), 1)


if __name__ == "__main__":
    unittest.main()
