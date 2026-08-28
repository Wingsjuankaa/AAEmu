#!/usr/bin/env python3
"""Deterministic forensic checks for the AA10 Housing H1 catalogue."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


PROJECT = Path(r"E:\AAEmu\rama_10")
REPO = PROJECT / "server" / "AAEmu"
DB = PROJECT / "data" / "sqlite" / "authoritative" / "game_decrypted.sqlite3"
COMPACT_DB = PROJECT / "client" / "ArcheAge-Returns-10.0.2.13-r575" / "game" / "db" / "compact.sqlite3"
RUNTIME_DB = REPO / ".server_files" / "AAEmu.Game" / "Data" / "compact.sqlite3"
OUTPUT = REPO / "AAEmu.Game" / "Data" / "housing_area_shapes_aa10_h1.json"
MANIFEST = REPO / "reconstruccion_cliente_10" / "housing_h1" / "generated" / "aa10-housing-h1-manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    shapes = payload["Shapes"]
    assert payload["SchemaVersion"] == 1
    assert shapes
    assert manifest["output"]["sha256"] == sha256(OUTPUT)
    assert manifest["metrics"]["promoted_shapes"] == len(shapes)
    assert manifest["constraints"]["aa8_values_copied"] == 0
    assert all(shape["World"] == "main_world" for shape in shapes)
    assert all(len(shape["Points"]) >= 3 for shape in shapes)
    assert all(
        shape["MinX"] <= point["X"] <= shape["MaxX"]
        and shape["MinY"] <= point["Y"] <= shape["MaxY"]
        for shape in shapes
        for point in shape["Points"]
    )

    for source in (DB, COMPACT_DB, RUNTIME_DB):
        connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
        try:
            connection.execute("PRAGMA query_only=ON")
            assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            connection.close()

    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        assert connection.execute(
            "SELECT count(*) FROM housings h JOIN housing_sizes s ON s.id=h.housing_size_id"
        ).fetchone()[0] == manifest["metrics"]["housings"]
    finally:
        connection.close()

    print("AA10 Housing H1 forensic checks: ok")


if __name__ == "__main__":
    main()
