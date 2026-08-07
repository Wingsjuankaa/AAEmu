import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from build_sorcery_runtime_v10 import DEFAULT_OUTPUT, RUNTIME_SHAPE, build, parse_args


class SorceryRuntimeV10AcceptanceTests(unittest.TestCase):
    def test_runtime_contains_exact_freezing_earth_shape(self) -> None:
        with sqlite3.connect(DEFAULT_OUTPUT) as connection:
            connection.row_factory = sqlite3.Row
            self.assertEqual(
                RUNTIME_SHAPE,
                dict(connection.execute(
                    "SELECT * FROM aoe_shapes WHERE id=11815"
                ).fetchone()),
            )

    def test_freezing_earth_plot_references_restored_shape(self) -> None:
        with sqlite3.connect(DEFAULT_OUTPUT) as connection:
            self.assertEqual(
                (3096, 5, 11815),
                connection.execute(
                    "SELECT plot_id,target_update_method_id,target_update_method_param1 "
                    "FROM plot_events WHERE id=25977"
                ).fetchone(),
            )

    def test_builder_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = parse_args([
                "--output", str(root / "runtime.sqlite3"),
                "--manifest", str(root / "manifest.json"),
            ])
            manifest = build(args)
            expected = json.loads(
                Path(__file__).with_name("generated")
                .joinpath("sorcery-specialization-v10.manifest.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(expected["output"]["sha256"], manifest["output"]["sha256"])


if __name__ == "__main__":
    unittest.main()
