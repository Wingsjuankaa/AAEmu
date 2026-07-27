#!/usr/bin/env python3
"""Inventory AA8-native NPC spawner objects shipped as game_pak layer XML."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from extract_native_npc_quest_catalog import (
    AUTHORITY,
    DEFAULT_GAME11,
    TABLE_SPECS,
    extract_table,
    sha256_file,
)


FORMAT_VERSION = 1
DEFAULT_GAMEPAK_REVIEW = Path(
    r"E:\AAEmu-Research\output\gamepak-aa8-global-review-v1\game"
)
SPAWNER_TYPES = {"NpcPointSpawner", "NpcAreaSpawner"}
LABEL_ID = re.compile(r"^\s*(\d+)")


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def child_attributes(node: ET.Element, path: str) -> list[dict[str, str]]:
    return [dict(sorted(child.attrib.items())) for child in node.findall(path)]


def parse_spawner(path: Path, root: Path, node: ET.Element) -> dict[str, Any]:
    label = node.get("NPC_Spawner_Type", "")
    match = LABEL_ID.match(label)
    return {
        "source": relative_path(path, root),
        "object": dict(sorted(node.attrib.items())),
        "label_primary_id": int(match.group(1)) if match else None,
        "spawner_type_ids": [
            int(child["type"]) for child in child_attributes(node, "./spawnerType")
        ],
        "points": child_attributes(node, "./Points/Point"),
        "tri_infos": child_attributes(node, "./TriInfos/TriInfo"),
        "paths": child_attributes(node, "./Paths/Path"),
        "anchors": child_attributes(node, "./anchors/anchor"),
    }


def canonical_signature(row: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in row.items()
        if key not in {"source", "native_npc"}
    }
    payload["object"] = {
        key: value
        for key, value in payload["object"].items()
        if key not in {"Id", "Name"}
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_native_closure(game11: Path) -> tuple[
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
]:
    data = game11.read_bytes()
    _, npc_rows = extract_table(data, "npcs", TABLE_SPECS["npcs"])
    _, model_rows = extract_table(data, "models", TABLE_SPECS["models"])
    _, actor_rows = extract_table(data, "actor_models", TABLE_SPECS["actor_models"])
    return (
        {int(row["id"]): row for row in npc_rows},
        {int(row["id"]): row for row in model_rows},
        {int(row["id"]): row for row in actor_rows},
    )


def native_npc_link(
    npc_id: int,
    npcs: dict[int, dict[str, Any]],
    models: dict[int, dict[str, Any]],
    actor_models: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    npc = npcs.get(npc_id)
    if npc is None:
        return None
    model = models.get(int(npc["model_id"]))
    actor_model = None
    if model and model["sub_type"] == "ActorModel":
        actor_model = actor_models.get(int(model["sub_id"]))
    return {
        "id": npc["id"],
        "name": npc["name"],
        "model_id": npc["model_id"],
        "model": model,
        "actor_model": actor_model,
    }


def build_manifest(gamepak_root: Path, game11: Path) -> dict[str, Any]:
    npcs, models, actor_models = load_native_closure(game11)
    layer_files = sorted(gamepak_root.rglob("*.lyr"))
    rows: list[dict[str, Any]] = []
    file_hashes: list[dict[str, Any]] = []
    parse_failures: list[dict[str, str]] = []
    quest_id_attributes = 0
    quest_context_id_attributes = 0

    for path in layer_files:
        file_hashes.append(
            {
                "path": relative_path(path, gamepak_root),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            parse_failures.append(
                {"path": relative_path(path, gamepak_root), "error": str(exc)}
            )
            continue
        for node in tree.iter():
            attribute_names = {name.lower() for name in node.attrib}
            quest_id_attributes += len(
                attribute_names & {"questid", "quest_id"}
            )
            quest_context_id_attributes += len(
                attribute_names
                & {"questcontextid", "quest_context_id"}
            )
            if node.get("Type") not in SPAWNER_TYPES:
                continue
            row = parse_spawner(path, gamepak_root, node)
            if node.get("Type") == "NpcPointSpawner":
                row["native_npc"] = native_npc_link(
                    int(row["label_primary_id"]), npcs, models, actor_models
                )
            else:
                row["native_npc"] = None
            rows.append(row)

    rows.sort(
        key=lambda row: (
            row["source"],
            int(row["object"]["spawnerId"]),
            row["object"]["Id"],
        )
    )
    by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_id[int(row["object"]["spawnerId"])].append(row)
    duplicate_ids = {
        str(spawner_id): {
            "row_count": len(group),
            "distinct_signatures": len(
                {canonical_signature(row) for row in group}
            ),
            "sources": sorted({row["source"] for row in group}),
        }
        for spawner_id, group in sorted(by_id.items())
        if len(group) > 1
    }

    point_rows = [
        row for row in rows if row["object"]["Type"] == "NpcPointSpawner"
    ]
    area_rows = [
        row for row in rows if row["object"]["Type"] == "NpcAreaSpawner"
    ]
    point_npc_ids = sorted({int(row["label_primary_id"]) for row in point_rows})
    area_label_ids = sorted({int(row["label_primary_id"]) for row in area_rows})
    source_counts = Counter(row["source"] for row in rows)
    type_counts = Counter(row["object"]["Type"] for row in rows)
    zero_position_rows = [
        {
            "source": row["source"],
            "spawner_id": int(row["object"]["spawnerId"]),
        }
        for row in rows
        if row["object"].get("Pos") == "0,0,0"
    ]

    digest = hashlib.sha256()
    for row in rows:
        digest.update(canonical_signature(row).encode("utf-8"))
        digest.update(b"\n")

    return {
        "format_version": FORMAT_VERSION,
        "authority": AUTHORITY,
        "classification": (
            "AA8-native client layer placement evidence; not yet proven as an "
            "active server world-placement catalogue"
        ),
        "deployable": False,
        "sources": {
            "gamepak_global_review": {
                "path": str(gamepak_root.resolve()),
                "layer_file_count": len(layer_files),
                "layer_files": file_hashes,
                "parse_failures": parse_failures,
            },
            "game11_native_catalogue": {
                "path": str(game11.resolve()),
                "bytes": game11.stat().st_size,
                "sha256": sha256_file(game11),
            },
        },
        "summary": {
            "spawner_rows": len(rows),
            "canonical_rows_sha256": digest.hexdigest().upper(),
            "unique_spawner_ids": len(by_id),
            "files_with_spawners": len(source_counts),
            "rows_by_type": dict(sorted(type_counts.items())),
            "rows_by_source": dict(sorted(source_counts.items())),
            "duplicate_spawner_id_groups": len(duplicate_ids),
            "duplicate_spawner_ids": duplicate_ids,
            "zero_position_rows": zero_position_rows,
        },
        "native_closure": {
            "point_spawner_unique_primary_ids": len(point_npc_ids),
            "point_spawner_primary_ids": point_npc_ids,
            "point_spawner_primary_ids_resolved_as_native_npcs": sum(
                npc_id in npcs for npc_id in point_npc_ids
            ),
            "point_spawner_primary_ids_missing_from_native_npcs": sorted(
                set(point_npc_ids) - set(npcs)
            ),
            "point_spawner_unique_model_ids": len(
                {
                    int(npcs[npc_id]["model_id"])
                    for npc_id in point_npc_ids
                    if npc_id in npcs
                }
            ),
            "area_spawner_primary_ids": area_label_ids,
            "area_spawner_primary_ids_resolved_as_native_npcs": sum(
                npc_id in npcs for npc_id in area_label_ids
            ),
            "classification": (
                "NpcPointSpawner label_primary_id is closed against native npcs; "
                "NpcAreaSpawner label_primary_id is not an NPC identifier and remains "
                "an unresolved spawner/group type."
            ),
        },
        "quest_surface_audit": {
            "quest_id_attributes_in_layer_objects": quest_id_attributes,
            "quest_context_id_attributes_in_layer_objects": (
                quest_context_id_attributes
            ),
            "classification": (
                "The layer files add NPC placements, paths, and roaming geometry, "
                "but do not embed quest-context rows or quest-to-NPC assignments."
            ),
        },
        "activation_gap": {
            "world_id_per_root_layer": "unresolved",
            "active_layer_revision": "unresolved",
            "spawner_runtime_parameters": (
                "npc_spawners and npc_spawner_npcs cached rows remain unlocated"
            ),
            "zero_positions_require_resolution": len(zero_position_rows),
            "status": (
                "Do not deploy until each root layer is tied to an AA8 world/zone "
                "and active revision, and its spawner IDs are reconciled with the "
                "server-side spawner tables."
            ),
        },
        "spawners": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gamepak-root", type=Path, default=DEFAULT_GAMEPAK_REVIEW
    )
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent
        / "generated"
        / "gamepak-native-npc-spawner-layers-v1-manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.gamepak_root.is_dir():
        raise FileNotFoundError(args.gamepak_root)
    if not args.game11.is_file():
        raise FileNotFoundError(args.game11)
    manifest = build_manifest(args.gamepak_root, args.game11)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(manifest["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
