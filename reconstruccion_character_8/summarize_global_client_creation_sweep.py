#!/usr/bin/env python3
"""Build the deterministic conclusion manifest for the AA8 global client sweep."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


MANIFEST_NAMES = (
    "global-client-surfaces-v1-manifest.json",
    "cached-result-streams-global-v1-manifest.json",
    "client-filesystem-global-v1-manifest.json",
    "client-sql-surfaces-v1-manifest.json",
    "gamepak-full-lua32-decompilation-v1-manifest.json",
    "gamepak-lua-architecture-comparison-v1-manifest.json",
    "gamepak-full-xml-world-evidence-v1-manifest.json",
    "client-binary-creation-evidence-v1-manifest.json",
    "gamepak-global-review-surfaces-v1-manifest.json",
    "gamepak-supplemental-review-surfaces-v1-manifest.json",
    "gamepak-global-content-scan-v1-manifest.json",
)

GHIDRA_EVIDENCE = (
    "aa8-auto-register-item-callers.c",
    "aa8-auto-register-spell-callers-global.c",
    "aa8-auto-register-spell-slot-finder-callers.c",
    "aa8-bank-slots-global.c",
    "aa8-first-actionbar-index-state-xrefs-global.c",
    "aa8-inven-slots-global.c",
    "aa8-num-bank-slots-global.c",
    "aa8-num-inven-slots-global.c",
    "aa8-skill-learned-handler-callers-global.c",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", required=True, type=Path)
    parser.add_argument("--ghidra", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected object manifest: {path}")
    return value


def artifact(path: Path, root: Path) -> dict[str, Any]:
    return {
        "bytes": path.stat().st_size,
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
    }


def main() -> int:
    options = parse_args()
    manifests: dict[str, dict[str, Any]] = {}
    manifest_artifacts: list[dict[str, Any]] = []
    for name in MANIFEST_NAMES:
        path = options.generated / name
        if not path.is_file():
            raise FileNotFoundError(path)
        manifests[name] = load_json(path)
        manifest_artifacts.append(artifact(path, options.generated))

    ghidra_artifacts: list[dict[str, Any]] = []
    for name in GHIDRA_EVIDENCE:
        path = options.ghidra / name
        if not path.is_file():
            raise FileNotFoundError(path)
        ghidra_artifacts.append(artifact(path, options.ghidra))

    extraction = manifests[
        "gamepak-global-review-surfaces-v1-manifest.json"
    ]["extraction"]
    supplemental = manifests[
        "gamepak-supplemental-review-surfaces-v1-manifest.json"
    ]["extraction"]
    content_scan = manifests[
        "gamepak-global-content-scan-v1-manifest.json"
    ]
    lua_comparison = manifests[
        "gamepak-lua-architecture-comparison-v1-manifest.json"
    ]
    filesystem = manifests["client-filesystem-global-v1-manifest.json"]
    cached_results = manifests[
        "cached-result-streams-global-v1-manifest.json"
    ]
    sql = manifests["client-sql-surfaces-v1-manifest.json"]

    integrity_failures: list[str] = []
    if extraction["failures"]:
        integrity_failures.append("gamepak extraction command failures")
    if extraction["missing"]:
        integrity_failures.append("gamepak selected entries missing")
    if extraction["size_mismatches"]:
        integrity_failures.append("gamepak selected entry size mismatches")
    if supplemental["failures"]:
        integrity_failures.append("gamepak supplemental extraction failures")
    if supplemental["missing"]:
        integrity_failures.append("gamepak supplemental entries missing")
    if supplemental["mismatches"]:
        integrity_failures.append("gamepak supplemental integrity mismatches")
    if content_scan["integrity"]["md5_mismatches"]:
        integrity_failures.append("gamepak selected entry MD5 mismatches")
    if content_scan["integrity"]["missing_index_entries"]:
        integrity_failures.append("gamepak scan files absent from complete index")
    if (
        lua_comparison["comparison"]["content_differences"]
        or lua_comparison["comparison"]["lua32_only"]
        or lua_comparison["comparison"]["lua64_only"]
    ):
        integrity_failures.append("32/64-bit Lua source differences")

    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "classification": "global_native_client_creation_sweep",
        "conclusion": {
            "acceptance_deployable": False,
            "current_focus": (
                "Native new-character position, starter equipment/supplies, "
                "initial skill, 217-slot action bar and reconnect persistence."
            ),
            "result": (
                "The global client sweep found no additional AA8-native source "
                "that authorizes the four missing server bootstrap values. It "
                "strengthens their classification as server-owned state rather "
                "than supplying values that can safely be inferred."
            ),
        },
        "coverage": {
            "cached_result_streams": cached_results["inventory"],
            "client_filesystem_outside_gamepak": filesystem["inventory"],
            "embedded_sql": {
                "common_statement_count": sql["comparison"]["common_statements"],
                "statement_union": sql["comparison"]["statement_union"],
                "statements_not_common": sql["comparison"][
                    "statements_not_common"
                ],
            },
            "gamepak": {
                "extracted_bytes": extraction["extracted_bytes"],
                "excluded_classes": manifests[
                    "gamepak-global-review-surfaces-v1-manifest.json"
                ]["classification"]["excluded_classes"],
                "selected_entries": extraction["selected_entries"],
                "selected_extensions": extraction["selected_extensions"],
                "supplemental_entries": supplemental["entries"],
                "supplemental_extensions": supplemental["extension_counts"],
                "scan": {
                    "decoded_output_md5_differences": len(
                        content_scan["integrity"][
                            "decoded_output_md5_differences"
                        ]
                    ),
                    "hit_counts": content_scan["scan"]["hit_counts"],
                    "md5_unavailable_in_source_index": len(
                        content_scan["integrity"][
                            "md5_unavailable_in_source_index"
                        ]
                    ),
                    "processed_bytes": content_scan["scan"]["processed_bytes"],
                    "processed_files": content_scan["scan"]["processed_files"],
                },
            },
            "lua": {
                "architecture_comparison": lua_comparison["comparison"],
                "focus_scan": lua_comparison["focus_hits"],
            },
        },
        "current_blockers": [
            {
                "code": "spawn_transform_unproven",
                "global_sweep_result": (
                    "The complete structured/world-container scan and all "
                    "unpacked client binaries expose no authoritative per-race "
                    "XYZ/angles. FUN_3991e9f0 serializes position, angles and "
                    "zone from server-owned character state."
                ),
                "required_authority": (
                    "Authentic AA8 packet/database observation or server binary."
                ),
            },
            {
                "code": "action_bar_bootstrap_unproven",
                "global_sweep_result": (
                    "The native default action table is empty. The only proven "
                    "spell auto-registration chain starts in explicit "
                    "SCSkillLearned handling and selects the first empty base "
                    "slot below level 21; creation does not prove that packet is "
                    "sent, nor a complete initial 217-slot snapshot."
                ),
                "required_authority": (
                    "Authentic post-creation packet sequence or server data."
                ),
            },
            {
                "code": "supply_inventory_slots_unproven",
                "global_sweep_result": (
                    "character_supplies has no slot field; client inventory "
                    "consumers receive slots from the server. All four supply "
                    "templates disable action-bar auto-registration."
                ),
                "required_authority": (
                    "Authentic created-character inventory rows or packets."
                ),
            },
            {
                "code": "initial_inventory_capacity_unproven",
                "global_sweep_result": (
                    "FUN_3991e9f0, FUN_39926040 and FUN_3997dfa0 consume "
                    "inventory/bank capacities from server state. No client "
                    "initializer or native creation table supplies their values."
                ),
                "required_authority": (
                    "Authentic created-character row/full-state packet or server "
                    "binary."
                ),
            },
        ],
        "future_review_catalogue": [
            {
                "area": "inventory_ui_topology",
                "native_surfaces": [
                    "default_inventory_tabs",
                    "default_inventory_tab_groups",
                    "item_bags",
                ],
                "scope": (
                    "Useful for a future AA8 inventory/UI reconstruction; not an "
                    "authority for initial character capacity or supply slots."
                ),
            },
            {
                "area": "client_action_bar_behavior",
                "native_surfaces": [
                    "SCSkillLearned auto-registration",
                    "inventory item auto-registration",
                    "first action-bar page state",
                    "ACTION_BAR_AUTO_REGISTERED UI event",
                ],
                "scope": (
                    "Useful for later action-bar behavior parity; it cannot "
                    "replace an observed initial server snapshot."
                ),
            },
            {
                "area": "world_and_login_stage_assets",
                "native_surfaces": [
                    "all world DAT/CTC containers",
                    "login2 level",
                    "structured CryEngine containers",
                ],
                "scope": (
                    "Useful for future intro/camera/world reconstruction. Visual "
                    "or entity transforms are not automatically player spawn "
                    "authority without a native consumer."
                ),
            },
            {
                "area": "client_database_consumers",
                "native_surfaces": [
                    "1014 common embedded SQL statements",
                    "compact",
                    "game0/game2/game6/game7/game11 cached result streams",
                ],
                "scope": (
                    "Reusable routing catalogue for later AA8 domains; SQL layout "
                    "alone does not establish a server gameplay relation."
                ),
            },
        ],
        "integrity": {
            "failures": integrity_failures,
            "status": "clean" if not integrity_failures else "failed",
        },
        "schema_version": 1,
        "sources": {
            "ghidra_artifacts": ghidra_artifacts,
            "ghidra_root": options.ghidra.resolve().as_posix(),
            "manifests": manifest_artifacts,
        },
    }

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if not integrity_failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
