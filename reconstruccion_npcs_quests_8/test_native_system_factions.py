#!/usr/bin/env python3
"""Regression tests for the AA8 native faction snapshot used by quest 330."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
GENERATED = DOMAIN / "generated"
GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
EXTRACTOR = DOMAIN / "extract_native_system_factions.py"
BUILDER = DOMAIN / "build_native_quest_330_v5_runtime.py"
DATA = GENERATED / "native-system-factions-v1-data.json"
MANIFEST = GENERATED / "native-system-factions-v1-manifest.json"
RUNTIME_MANIFEST = GENERATED / "native-system-factions-v2-runtime-manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class NativeSystemFactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.runtime_manifest = json.loads(
            RUNTIME_MANIFEST.read_text(encoding="utf-8")
        )

    def test_native_catalogue_and_quest_chain_are_complete(self) -> None:
        rows = self.data["rows"]
        by_id = {int(row["id"]): row for row in rows}
        self.assertEqual(114, len(rows))
        self.assertEqual(114, len(by_id))
        self.assertEqual(148, int(by_id[101]["mother_id"]))
        self.assertEqual(0, int(by_id[148]["mother_id"]))
        self.assertEqual(
            {204, 205, 206, 209},
            {
                int(row["id"])
                for row in rows
                if int(row["integration_faction"])
            },
        )
        self.assertEqual(
            set(),
            {
                int(row["mother_id"])
                for row in rows
                if int(row["mother_id"]) not in by_id
                and int(row["mother_id"]) != 0
            },
        )
        self.assertEqual("초승달 왕좌", by_id[101]["name"])
        self.assertEqual("누이아 연합", by_id[148]["name"])

    def test_extraction_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            manifest = output / MANIFEST.name
            data = output / DATA.name
            subprocess.run(
                [
                    sys.executable,
                    str(EXTRACTOR),
                    "--game11",
                    str(GAME11),
                    "--output",
                    str(manifest),
                    "--data-output",
                    str(data),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(MANIFEST.read_bytes(), manifest.read_bytes())
            self.assertEqual(DATA.read_bytes(), data.read_bytes())

    def test_v5_runtime_is_deterministic_and_has_no_orphans(self) -> None:
        base = Path(self.runtime_manifest["sources"]["base_runtime"]["path"])
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            first = directory / "first.sqlite3"
            second = directory / "second.sqlite3"
            for output in (first, second):
                subprocess.run(
                    [
                        sys.executable,
                        str(BUILDER),
                        "--base-runtime",
                        str(base),
                        "--data",
                        str(DATA),
                        "--output",
                        str(output),
                        "--manifest",
                        str(directory / f"{output.stem}.json"),
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            self.assertEqual(sha256(first), sha256(second))

            connection = sqlite3.connect(first)
            try:
                self.assertEqual(
                    (114, 1, 211),
                    connection.execute(
                        "SELECT COUNT(*), MIN(id), MAX(id) FROM system_factions"
                    ).fetchone(),
                )
                self.assertEqual(
                    (148, 0),
                    connection.execute(
                        """
                        SELECT child.mother_id, mother.mother_id
                        FROM system_factions child
                        JOIN system_factions mother ON mother.id=child.mother_id
                        WHERE child.id=101
                        """
                    ).fetchone(),
                )
                self.assertEqual(
                    0,
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM system_faction_relations relation
                        LEFT JOIN system_factions first
                          ON first.id=relation.faction1_id
                        LEFT JOIN system_factions second
                          ON second.id=relation.faction2_id
                        WHERE first.id IS NULL OR second.id IS NULL
                        """
                    ).fetchone()[0],
                )
                self.assertEqual(
                    "ok",
                    connection.execute("PRAGMA integrity_check").fetchone()[0],
                )
            finally:
                connection.close()

    def test_login_sends_native_factions_but_not_historical_relations(self) -> None:
        source = (
            ROOT
            / "AAEmu.Game"
            / "Core"
            / "Packets"
            / "C2G"
            / "CSSelectCharacterPacket.cs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "FactionManager.Instance.SendFactions(Connection.ActiveChar);",
            source,
        )
        self.assertIn(
            "//FactionManager.Instance.SendRelations(Connection.ActiveChar);",
            source,
        )


if __name__ == "__main__":
    unittest.main()
