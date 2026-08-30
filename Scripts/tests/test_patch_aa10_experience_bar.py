from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "PatchAa10ExperienceBar.py"
SPEC = importlib.util.spec_from_file_location("patch_aa10_experience_bar", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


class PatchAa10ExperienceBarTests(unittest.TestCase):
    def test_build_restores_archeage_header_and_preserves_fixed_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "exp_bar_set.lua"
            alb = root / "exp_bar_set.before.alb"
            luac = root / "luac51.exe"
            output = root / "exp_bar_set.replacement.alb"
            source.write_bytes(b"retail source")
            alb.write_bytes(b"original-alb" + bytes(20))
            luac.write_bytes(b"fixture")

            compiled = PATCHER.LUA_51_HEADER + b"compiled"
            expected = bytearray(compiled)
            expected[11] = 8
            expected.extend(bytes(32 - len(expected)))

            def fake_compile(command: list[str], check: bool) -> None:
                self.assertTrue(check)
                Path(command[command.index("-o") + 1]).write_bytes(compiled)

            with (
                mock.patch.object(PATCHER, "EXPECTED_SIZE", 32),
                mock.patch.object(PATCHER, "SOURCE_SHA256", sha256(source.read_bytes())),
                mock.patch.object(PATCHER, "ORIGINAL_SHA256", sha256(alb.read_bytes())),
                mock.patch.object(PATCHER, "PATCHED_SHA256", sha256(expected)),
                mock.patch.object(PATCHER.subprocess, "run", side_effect=fake_compile) as run,
            ):
                result = PATCHER.build(source, alb, luac, output)

            self.assertEqual(result, sha256(expected))
            self.assertEqual(output.read_bytes(), expected)
            run.assert_called_once()

    def test_already_patched_is_idempotent_without_compiling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "exp_bar_set.lua"
            alb = root / "exp_bar_set.before.alb"
            luac = root / "luac51.exe"
            output = root / "exp_bar_set.replacement.alb"
            source.write_bytes(b"retail source")
            alb.write_bytes(b"patched-entry")
            luac.write_bytes(b"fixture")

            with (
                mock.patch.object(PATCHER, "EXPECTED_SIZE", len(alb.read_bytes())),
                mock.patch.object(PATCHER, "SOURCE_SHA256", sha256(source.read_bytes())),
                mock.patch.object(PATCHER, "PATCHED_SHA256", sha256(alb.read_bytes())),
                mock.patch.object(PATCHER.subprocess, "run") as run,
            ):
                result = PATCHER.build(source, alb, luac, output)

            self.assertEqual(result, sha256(alb.read_bytes()))
            self.assertEqual(output.read_bytes(), alb.read_bytes())
            run.assert_not_called()

    def test_unknown_source_is_rejected_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "exp_bar_set.lua"
            alb = root / "exp_bar_set.before.alb"
            luac = root / "luac51.exe"
            output = root / "exp_bar_set.replacement.alb"
            source.write_bytes(b"unexpected source")
            alb.write_bytes(b"original-alb")
            luac.write_bytes(b"fixture")

            with (
                mock.patch.object(PATCHER, "EXPECTED_SIZE", len(alb.read_bytes())),
                mock.patch.object(PATCHER, "SOURCE_SHA256", "0" * 64),
                self.assertRaises(SystemExit),
            ):
                PATCHER.build(source, alb, luac, output)

            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
