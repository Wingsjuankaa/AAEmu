#!/usr/bin/env python3
"""Build the AA10 r575 Halcyona doodad replacement directly from retail cell data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path


REGION = {
    "min_x": 7368.648649,
    "min_y": 9216.0,
    "max_x": 12288.0,
    "max_y": 12168.648649,
}

CELL_HASHES = {
    "007_009": "A5AF97FB31E0F028962F37E3C025C6C59BC68DE995C4D0BC65D100B1941FAE53",
    "007_010": "886F991CE0721D71F2FE2C76E453C5AC448DD73C2C95FA3F98077142E501BDFD",
    "007_011": "A68D84D962D7F66F2F290DF77E642AD876E413975B1CEC35A019A00CC53A5122",
    "008_009": "7005CE1914E807CB7809BC9ED1903A45B46D5574CB4DC16F3E407D17A136178C",
    "008_010": "5D50AEA9922CB645E363E9D9061F283939E8C0FC80402304BF8380D071E4BB1D",
    "008_011": "C071D6FDAE656FE9B21E8AD63CAD09F1B983B12572D9C6252AECA35D30E465BE",
    "009_009": "571F6DCDC24C1D428EC8E21D86B914C28FC8ED94A0EBF2C67C850076506DAF40",
    "009_010": "34F665790059D79650A0D50CC173915197496FF8D03B077E69A24E3FC7002C9B",
    "009_011": "2BCC197E3664119AFEF8394D1778787251A222BD1DFDBA408C2492162AF287A6",
    "010_009": "FACDE2BCEEEF72B9C250D8F9530607D8460C5CD64D4A89494FFAFA2497EF6640",
    "010_010": "D7D93C74763EFF9D48068B985C0488C357FEAB9D6470F5EC49F46B54A8DB44AA",
    "010_011": "4E054B2897F6BBDD8A32B318C28CDBB0FF6ABA438E5E2D9CB929F6C6D5B3D7A9",
    "011_009": "601A6576D6C0E6A288A25E1B85E25823AB50DDBECA7CA72CD34D47BD30069829",
    "011_010": "8EBA93C1387A947570232B6A17D66A2080CE7F0135B5349FE131AEAF057298B0",
    "011_011": "1034E1095A49E924B4EA1FC37087E909933086DF219904EDDC6329C6B4EEF1EA",
}

BLOCK_PATTERN = re.compile(
    r"doodad\s+"
    r"category\s+(?P<category>\d+)\s+"
    r"type\s+(?P<unit_id>\d+)\s+"
    r"family\s+(?P<family>\d+)\s+"
    r"vegetation\s+(?P<vegetation>\w+)\s+"
    r"pos \( x (?P<x>[^,]+), y (?P<y>[^,]+), z (?P<z>[^)]+) \)\s+"
    r"ori \( x (?P<qx>[^,]+), y (?P<qy>[^,]+), z (?P<qz>[^,]+), w (?P<qw>[^)]+) \)\s+"
    r"scale\s+(?P<scale>[^\s]+)",
    re.MULTILINE,
)

EXPECTED_PLACEMENTS = 6600


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cells-dir", type=Path)
    parser.add_argument("--game-pak", type=Path)
    parser.add_argument("--extractor", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def extract_cells(game_pak: Path, extractor: Path, destination: Path) -> None:
    for cell in CELL_HASHES:
        output = destination / f"{cell}.g"
        entry = f"game/worlds/main_world/level_design/cells/{cell}/doodad.g"
        subprocess.run(
            [str(extractor), str(game_pak), entry, str(output)],
            check=True,
        )


def clean(value: float) -> float:
    rounded = round(value, 6)
    return 0.0 if rounded == 0 else rounded


def quaternion_to_degrees(x: float, y: float, z: float, w: float) -> tuple[float, float, float]:
    sin_roll_cos_pitch = 2.0 * (w * x + y * z)
    cos_roll_cos_pitch = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sin_roll_cos_pitch, cos_roll_cos_pitch)

    sin_pitch = 2.0 * (w * y - z * x)
    pitch = math.copysign(math.pi / 2.0, sin_pitch) if abs(sin_pitch) >= 1.0 else math.asin(sin_pitch)

    sin_yaw_cos_pitch = 2.0 * (w * z + x * y)
    cos_yaw_cos_pitch = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(sin_yaw_cos_pitch, cos_yaw_cos_pitch)

    return tuple(clean(math.degrees(angle)) for angle in (roll, pitch, yaw))


def inside_region(x: float, y: float) -> bool:
    return REGION["min_x"] <= x < REGION["max_x"] and REGION["min_y"] <= y < REGION["max_y"]


def parse_cells(cells_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for cell, expected_hash in CELL_HASHES.items():
        path = cells_dir / f"{cell}.g"
        if not path.is_file():
            raise FileNotFoundError(f"Missing extracted retail cell: {path}")
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(f"Unexpected SHA-256 for {cell}: {actual_hash} != {expected_hash}")

        cell_x, cell_y = (int(token) for token in cell.split("_"))
        text = path.read_text(encoding="utf-8")
        for match in BLOCK_PATTERN.finditer(text):
            world_x = (cell_x * 1024.0) + float(match.group("x"))
            world_y = (cell_y * 1024.0) + float(match.group("y"))
            if not inside_region(world_x, world_y):
                continue

            roll, pitch, yaw = quaternion_to_degrees(
                float(match.group("qx")),
                float(match.group("qy")),
                float(match.group("qz")),
                float(match.group("qw")),
            )
            rows.append(
                {
                    "Id": 0,
                    "UnitId": int(match.group("unit_id")),
                    "Title": "",
                    "Position": {
                        "X": clean(world_x),
                        "Y": clean(world_y),
                        "Z": clean(float(match.group("z"))),
                        "Roll": roll,
                        "Pitch": pitch,
                        "Yaw": yaw,
                    },
                    "FuncGroupId": 0,
                    "Scale": clean(float(match.group("scale"))),
                }
            )
    return rows


def validate(rows: list[dict[str, object]]) -> None:
    if len(rows) != EXPECTED_PLACEMENTS:
        raise ValueError(f"Expected {EXPECTED_PLACEMENTS} Halcyona placements, found {len(rows)}")

    rock = [row for row in rows if row["UnitId"] == 8441]
    if len(rock) != 1:
        raise ValueError(f"Expected one solid rock 8441, found {len(rock)}")
    position = rock[0]["Position"]
    expected = {"X": 11017.739, "Y": 10279.9595, "Z": 243.677, "Roll": 0.0, "Pitch": 0.0, "Yaw": 0.0}
    if position != expected or rock[0]["Scale"] != 1.0:
        raise ValueError(f"Solid rock 8441 does not match retail: {rock[0]}")

    if any(row["Scale"] <= 0 for row in rows):
        raise ValueError("Retail replacement contains a non-positive scale")


def write_output(rows: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("[\n")
        for index, row in enumerate(rows):
            suffix = "," if index + 1 < len(rows) else ""
            stream.write("  " + json.dumps(row, ensure_ascii=False, separators=(",", ":")) + suffix + "\n")
        stream.write("]\n")
    temporary.replace(output)


def main() -> int:
    args = parse_args()
    if args.cells_dir:
        rows = parse_cells(args.cells_dir.resolve())
    else:
        if not args.game_pak or not args.extractor:
            raise ValueError("Use --cells-dir or provide both --game-pak and --extractor")
        with tempfile.TemporaryDirectory(prefix="aa10-halcyona-r575-") as temp:
            cells_dir = Path(temp)
            extract_cells(args.game_pak.resolve(), args.extractor.resolve(), cells_dir)
            rows = parse_cells(cells_dir)

    validate(rows)
    write_output(rows, args.output.resolve())
    print(f"Wrote {len(rows)} AA10 r575 Halcyona placements to {args.output}")
    print(f"SHA-256 {sha256(args.output.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
