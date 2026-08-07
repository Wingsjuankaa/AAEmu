import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from build_sorcery_runtime_v9 import DEFAULT_OUTPUT, TRIGGER, build, parse_args


class SorceryRuntimeV9AcceptanceTests(unittest.TestCase):
    def test_runtime_contains_exact_native_absorption_closure(self) -> None:
        with sqlite3.connect(DEFAULT_OUTPUT) as connection:
            connection.row_factory = sqlite3.Row
            self.assertEqual(
                TRIGGER,
                dict(connection.execute(
                    "SELECT * FROM buff_triggers WHERE id=9738"
                ).fetchone()),
            )
            self.assertEqual(
                (67353, "SpecialEffect", 31561, 33, 37837),
                tuple(connection.execute(
                    "SELECT e.id,e.actual_type,e.actual_id,s.special_effect_type_id,s.value1 "
                    "FROM effects e JOIN special_effects s ON s.id=e.actual_id WHERE e.id=67353"
                ).fetchone()),
            )

    def test_runtime_preserves_shield_break_skill_and_root(self) -> None:
        with sqlite3.connect(DEFAULT_OUTPUT) as connection:
            self.assertEqual(1, connection.execute(
                "SELECT count(*) FROM skills WHERE id=37837 AND target_area_radius=6"
            ).fetchone()[0])
            self.assertEqual(1, connection.execute(
                "SELECT count(*) FROM buffs WHERE id=94 AND root=1"
            ).fetchone()[0])
            self.assertEqual((10153, 30000), connection.execute(
                "SELECT cooldown_skill_id,cooldown_skill_time FROM buffs WHERE id=95"
            ).fetchone())

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
                .joinpath("sorcery-specialization-v9.manifest.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(expected["output"]["sha256"], manifest["output"]["sha256"])


if __name__ == "__main__":
    unittest.main()
