import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
BUILDER = DOMAIN / "build_native_nuian_green_arc_v2_runtime.py"


class NativeNuianGreenArcV2Tests(unittest.TestCase):
    def test_runtime_builder_closes_quest_2255_item_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "runtime.sqlite3"
            manifest = Path(directory) / "manifest.json"
            subprocess.run(
                [
                    sys.executable,
                    str(BUILDER),
                    "--output",
                    str(output),
                    "--manifest",
                    str(manifest),
                ],
                cwd=DOMAIN.parent,
                check=True,
                capture_output=True,
                text=True,
            )
            connection = sqlite3.connect(output)
            try:
                self.assertEqual(
                    connection.execute(
                        "SELECT concrete_type,coverage,missing_dependencies "
                        "FROM aaemu_item_definition_coverage WHERE item_id=16280"
                    ).fetchone(),
                    ("generic", "complete", ""),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT impl_id,use_skill_id,loot_quest_id,max_stack_size "
                        "FROM items WHERE id=16280"
                    ).fetchone(),
                    (0, 17326, 2255, 1),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT skill_id,effect_id,consume_item_count "
                        "FROM skill_effects WHERE id=14619"
                    ).fetchone(),
                    (17326, 18267, 1),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT actual_type,actual_id FROM effects WHERE id=18267"
                    ).fetchone(),
                    ("DispelEffect", 385),
                )
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone(),
                    ("ok",),
                )
            finally:
                connection.close()
            document = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertTrue(
                document["native_closure"]["runtime_matches_aa8_client_item"]
            )

    def test_builder_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hashes = []
            for index in range(2):
                output = Path(directory) / f"runtime-{index}.sqlite3"
                manifest = Path(directory) / f"manifest-{index}.json"
                subprocess.run(
                    [
                        sys.executable,
                        str(BUILDER),
                        "--output",
                        str(output),
                        "--manifest",
                        str(manifest),
                    ],
                    cwd=DOMAIN.parent,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                hashes.append(
                    json.loads(manifest.read_text(encoding="utf-8"))["output"][
                        "sha256"
                    ]
                )
            self.assertEqual(hashes[0], hashes[1])


if __name__ == "__main__":
    unittest.main()
