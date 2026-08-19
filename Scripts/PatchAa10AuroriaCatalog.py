#!/usr/bin/env python3
"""Enable the AA10 r575 Auroria catalog in compact.sqlite3.

Returns ships 21 Auroria map resources disabled, all 31 Auroria partitions
closed, and all 13 Auroria conflict cycles closed. This patch is deliberately
build-specific: it validates the complete r575 sets and the ``origin`` world
group before changing only those three gates.

Backups are the caller's responsibility. The retail client prefers the
``game/db/compact.sqlite3`` entry inside ``game_pak`` over the loose database,
so reinsert a successfully patched loose copy with ``Tools/PakEntryReplace``.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from pathlib import Path


EXPECTED_RESOURCES: tuple[tuple[int, str, int, str], ...] = (
    (99, "ZoneGroup", 33, "o_salpimari"),
    (100, "ZoneGroup", 34, "o_nuimari"),
    (101, "ZoneGroup", 43, "o_seonyeokmari"),
    (102, "ZoneGroup", 44, "o_rest_land"),
    (103, "ZoneGroup", 54, "o_abyss_gate"),
    (104, "ZoneGroup", 56, "o_land_of_sunlights"),
    (105, "ZoneGroup", 61, "o_shining_shore"),
    (106, "ZoneGroup", 67, "o_library_1"),
    (107, "ZoneGroup", 65, "o_library_2"),
    (108, "ZoneGroup", 69, "o_library_3"),
    (109, "ZoneGroup", 78, "o_dew_plains"),
    (110, "ZoneGroup", 57, "o_ruins_of_gold"),
    (111, "SubZone", 1126, "o_dew_plains_in"),
    (112, "SubZone", 1075, "o_abyss_gate_ruin_of_vanishing_snake_1f"),
    (113, "SubZone", 1076, "o_abyss_gate_ruin_of_vanishing_snake_2f"),
    (114, "ZoneGroup", 98, "o_room_of_queen"),
    (115, "ZoneGroup", 100, "o_room_of_queen"),
    (116, "ZoneGroup", 63, "o_the_great_reeds"),
    (117, "ZoneGroup", 102, "o_candlestick_of_sea"),
    (118, "ZoneGroup", 103, "o_whale_song_bay"),
    (135, "ZoneGroup", 107, "o_hirama_the_west"),
    (155, "SubZone", 1267, "o_hirama_the_west_hiramas_cave"),
    (158, "ZoneGroup", 110, "o_hirama_the_east"),
    (159, "SubZone", 1273, "o_hirama_the_east_warrior_hall"),
    (178, "ZoneGroup", 139, "o_land_of_magic"),
    (180, "ZoneGroup", 140, "o_mount_ipnir"),
    (181, "SubZone", 1355, "o_mount_ipnir_ipnir_island"),
    (182, "SubZone", 1357, "o_mount_ipnir_ipna_cave"),
    (198, "ZoneGroup", 147, "o_western_prairie"),
    (199, "SubZone", 1372, "o_western_prairie_temp_camp"),
)

EXPECTED_ZONES: tuple[tuple[int, int, str, int], ...] = (
    (148, 33, "o_salpimari", 204),
    (149, 34, "o_nuimari", 205),
    (166, 43, "o_seonyeokmari", 233),
    (167, 44, "o_rest_land", 234),
    (191, 54, "o_abyss_gate", 276),
    (193, 56, "o_land_of_sunlights", 275),
    (197, 61, "o_shining_shore_1", 282),
    (198, 57, "o_ruins_of_gold", 281),
    (200, 63, "o_the_great_reeds", 288),
    (203, 65, "o_library_2", 294),
    (205, 67, "o_library_1", 293),
    (208, 69, "o_library_3", 295),
    (217, 61, "o_shining_shore_2", 301),
    (218, 78, "o_dew_plains", 307),
    (225, 82, "o_epherium_1", 312),
    (226, 82, "o_epherium_2", 314),
    (258, 103, "o_whale_song_bay", 310),
    (261, 102, "o_candlestick_of_sea", 344),
    (266, 107, "o_hirama_the_west_1", 350),
    (267, 107, "o_hirama_the_west_2", 351),
    (270, 110, "o_hirama_the_east_1", 354),
    (271, 110, "o_hirama_the_east_2", 355),
    (277, 116, "library_lobby_1f", 361),
    (278, 117, "library_lobby_2f", 362),
    (279, 118, "library_lobby_3f", 363),
    (280, 119, "library_lobby_4f", 364),
    (301, 139, "o_land_of_magic", 387),
    (302, 140, "o_mount_ipnir_1", 388),
    (305, 140, "o_mount_ipnir_2", 391),
    (311, 147, "o_western_prairie_1", 397),
    (314, 147, "o_western_prairie_2", 401),
)

EXPECTED_CONFLICT_GROUPS: tuple[int, ...] = (
    54,
    56,
    57,
    61,
    63,
    102,
    103,
    107,
    110,
    117,
    139,
    140,
    147,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def quick_check(connection: sqlite3.Connection, path: Path, phase: str) -> None:
    result = connection.execute("PRAGMA quick_check").fetchone()
    if result is None or result[0] != "ok":
        raise RuntimeError(f"{path}: quick_check failed {phase}: {result}")


def validate_catalog(
    connection: sqlite3.Connection, path: Path
) -> tuple[list[tuple], list[tuple], list[tuple]]:
    world_group = connection.execute(
        "SELECT name, map_target_id, map_target_type FROM world_groups WHERE id = 5"
    ).fetchone()
    if world_group != ("origin", 2, "WorldGroup"):
        raise RuntimeError(f"{path}: unexpected world_groups.id=5: {world_group}")

    rows = connection.execute(
        "SELECT id, map_target_type, map_target_id, folder_name, enable "
        "FROM map_resources WHERE substr(folder_name, 1, 2) = 'o_' ORDER BY id"
    ).fetchall()
    identity = tuple((row[0], row[1], row[2], row[3]) for row in rows)
    if identity != EXPECTED_RESOURCES:
        raise RuntimeError(f"{path}: unexpected Auroria resource set: {identity}")

    invalid_states = [(row[0], row[4]) for row in rows if row[4] not in ("f", "t")]
    if invalid_states:
        raise RuntimeError(f"{path}: unexpected enable states: {invalid_states}")

    zones = connection.execute(
        "SELECT z.id, z.group_id, z.name, z.zone_key, z.closed "
        "FROM zones z JOIN zone_groups g ON g.id = z.group_id "
        "WHERE g.target_id = 5 ORDER BY z.id"
    ).fetchall()
    zone_identity = tuple((row[0], row[1], row[2], row[3]) for row in zones)
    if zone_identity != EXPECTED_ZONES:
        raise RuntimeError(f"{path}: unexpected Auroria zone set: {zone_identity}")
    invalid_zone_states = [(row[0], row[4]) for row in zones if row[4] not in ("f", "t")]
    if invalid_zone_states:
        raise RuntimeError(f"{path}: unexpected zone closed states: {invalid_zone_states}")

    conflicts = connection.execute(
        "SELECT c.zone_group_id, c.closed FROM conflict_zones c "
        "JOIN zone_groups g ON g.id = c.zone_group_id "
        "WHERE g.target_id = 5 ORDER BY c.zone_group_id"
    ).fetchall()
    conflict_identity = tuple(row[0] for row in conflicts)
    if conflict_identity != EXPECTED_CONFLICT_GROUPS:
        raise RuntimeError(f"{path}: unexpected Auroria conflict set: {conflict_identity}")
    invalid_conflict_states = [row for row in conflicts if row[1] not in ("f", "t")]
    if invalid_conflict_states:
        raise RuntimeError(
            f"{path}: unexpected conflict closed states: {invalid_conflict_states}"
        )
    return rows, zones, conflicts


def patch_database(path: Path, apply_changes: bool) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)

    before_size = path.stat().st_size
    before_hash = sha256(path)
    connection = sqlite3.connect(path)
    try:
        quick_check(connection, path, "before patch")
        connection.execute("BEGIN IMMEDIATE")
        rows, zones, conflicts = validate_catalog(connection, path)
        disabled_resource_ids = [row[0] for row in rows if row[4] == "f"]
        closed_zone_ids = [row[0] for row in zones if row[4] == "t"]
        closed_conflict_ids = [row[0] for row in conflicts if row[1] == "t"]
        unrelated_resources_before = connection.execute(
            "SELECT id, enable FROM map_resources "
            "WHERE substr(coalesce(folder_name, ''), 1, 2) <> 'o_' ORDER BY id"
        ).fetchall()
        unrelated_zones_before = connection.execute(
            "SELECT z.id, z.closed FROM zones z JOIN zone_groups g ON g.id = z.group_id "
            "WHERE g.target_id <> 5 ORDER BY z.id"
        ).fetchall()
        unrelated_conflicts_before = connection.execute(
            "SELECT c.zone_group_id, c.closed FROM conflict_zones c "
            "JOIN zone_groups g ON g.id = c.zone_group_id "
            "WHERE g.target_id <> 5 ORDER BY c.zone_group_id"
        ).fetchall()

        if apply_changes and disabled_resource_ids:
            placeholders = ",".join("?" for _ in disabled_resource_ids)
            cursor = connection.execute(
                f"UPDATE map_resources SET enable = 't' "
                f"WHERE id IN ({placeholders}) AND enable = 'f'",
                disabled_resource_ids,
            )
            if cursor.rowcount != len(disabled_resource_ids):
                raise RuntimeError(
                    f"{path}: expected {len(disabled_resource_ids)} resource updates, "
                    f"got {cursor.rowcount}"
                )
        if apply_changes and closed_zone_ids:
            placeholders = ",".join("?" for _ in closed_zone_ids)
            cursor = connection.execute(
                f"UPDATE zones SET closed = 'f' "
                f"WHERE id IN ({placeholders}) AND closed = 't'",
                closed_zone_ids,
            )
            if cursor.rowcount != len(closed_zone_ids):
                raise RuntimeError(
                    f"{path}: expected {len(closed_zone_ids)} zone updates, "
                    f"got {cursor.rowcount}"
                )
        if apply_changes and closed_conflict_ids:
            placeholders = ",".join("?" for _ in closed_conflict_ids)
            cursor = connection.execute(
                f"UPDATE conflict_zones SET closed = 'f' "
                f"WHERE zone_group_id IN ({placeholders}) AND closed = 't'",
                closed_conflict_ids,
            )
            if cursor.rowcount != len(closed_conflict_ids):
                raise RuntimeError(
                    f"{path}: expected {len(closed_conflict_ids)} conflict updates, "
                    f"got {cursor.rowcount}"
                )

        after_rows, after_zones, after_conflicts = validate_catalog(connection, path)
        if apply_changes and any(row[4] != "t" for row in after_rows):
            raise RuntimeError(f"{path}: not every Auroria resource is enabled")
        if apply_changes and any(row[4] != "f" for row in after_zones):
            raise RuntimeError(f"{path}: not every Auroria zone is open")
        if apply_changes and any(row[1] != "f" for row in after_conflicts):
            raise RuntimeError(f"{path}: not every Auroria conflict cycle is open")

        unrelated_resources_after = connection.execute(
            "SELECT id, enable FROM map_resources "
            "WHERE substr(coalesce(folder_name, ''), 1, 2) <> 'o_' ORDER BY id"
        ).fetchall()
        if unrelated_resources_after != unrelated_resources_before:
            raise RuntimeError(f"{path}: a non-Auroria resource changed")
        unrelated_zones_after = connection.execute(
            "SELECT z.id, z.closed FROM zones z JOIN zone_groups g ON g.id = z.group_id "
            "WHERE g.target_id <> 5 ORDER BY z.id"
        ).fetchall()
        if unrelated_zones_after != unrelated_zones_before:
            raise RuntimeError(f"{path}: a non-Auroria zone changed")
        unrelated_conflicts_after = connection.execute(
            "SELECT c.zone_group_id, c.closed FROM conflict_zones c "
            "JOIN zone_groups g ON g.id = c.zone_group_id "
            "WHERE g.target_id <> 5 ORDER BY c.zone_group_id"
        ).fetchall()
        if unrelated_conflicts_after != unrelated_conflicts_before:
            raise RuntimeError(f"{path}: a non-Auroria conflict cycle changed")

        quick_check(connection, path, "after patch")
        if apply_changes:
            connection.commit()
        else:
            connection.rollback()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    after_size = path.stat().st_size
    if after_size != before_size:
        raise RuntimeError(f"{path}: size changed from {before_size} to {after_size}")

    print(path)
    print(f"  Auroria resources: {len(EXPECTED_RESOURCES)}")
    print(f"  disabled resources before: {len(disabled_resource_ids)}")
    print(f"  closed zones before:       {len(closed_zone_ids)}")
    print(f"  closed conflicts before:   {len(closed_conflict_ids)}")
    print(f"  action:            {'applied' if apply_changes else 'dry run'}")
    print(f"  before SHA-256:    {before_hash}")
    print(f"  after SHA-256:     {sha256(path)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enable the AA10 r575 Auroria catalog safely."
    )
    parser.add_argument("databases", nargs="+", type=Path)
    parser.add_argument(
        "--apply", action="store_true", help="commit the validated f -> t update"
    )
    args = parser.parse_args()

    for database in args.databases:
        patch_database(database.resolve(), args.apply)
    if not args.apply:
        print("DRY RUN: no database changes were committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
