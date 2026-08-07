#!/usr/bin/env python3
"""Extract the AA8-native shared effect primitive contracts and their skill fanout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = (
    ROOT
    / "reconstruccion_skills_8"
    / "native_combat"
    / "generated"
    / "native-combat-catalog-v1.json"
)
DEFAULT_SEMANTIC_DOSSIERS = (
    Path("E:/AAEmu-Research/output/aa8-native-code/semantic-dossiers")
)
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "generated" / "shared-primitives-v1.json"


PRIMITIVES = {
    "ResetAoeDiminishingEffect": {
        "detail_table": "reset_aoe_diminishing_effects",
        "query_root": "query:stage50:query:89:reset_aoe_diminishing_effects",
    },
    "HealEffect": {
        "detail_table": "heal_effects",
        "query_root": "query:stage50:query:52:heal_effects",
    },
    "RestoreManaEffect": {
        "detail_table": "restore_mana_effects",
        "query_root": "query:stage50:query:53:restore_mana_effects",
    },
    "BubbleEffect": {
        "detail_table": "bubble_effects",
        "query_root": "query:stage50:query:75:bubble_effects",
    },
    "ManaBurnEffect": {
        "detail_table": "mana_burn_effects",
        "query_root": "query:stage50:query:64:mana_burn_effects",
    },
    "SpawnEffect": {
        "detail_table": "spawn_effects",
        "query_root": "query:stage50:query:60:spawn_effects",
    },
    "KillNpcWithoutCorpseEffect": {
        "detail_table": "kill_npc_without_corpse_effects",
        "query_root": "query:stage50:query:72:kill_npc_without_corpse_effects",
    },
    "ExtendChargeEffect": {
        "detail_table": "extend_charge_effects",
        "query_root": "query:stage50:query:99:extend_charge_effects",
    },
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def semantic_dossier_path(root: Path, query_root: str) -> Path:
    slug = query_root.replace(":", "_").replace("/", "_")
    return root / f"{slug}.json"


def parse_reason(value: str) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise RuntimeError("Catalog status reason must be a JSON object")
    return parsed


def extract(catalog_path: Path, semantic_root: Path) -> dict[str, Any]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    effects = {int(row["id"]): row for row in catalog["tables"]["effects"]}
    plot_effects = {
        int(row["id"]): row for row in catalog["tables"]["plot_effects"]
    }
    status_by_skill = {
        int(row["skill_id"]): row for row in catalog["skill_status"]
    }

    records: dict[str, Any] = {}
    for primitive, config in PRIMITIVES.items():
        detail_table = str(config["detail_table"])
        detail_index = {
            int(row["id"]): row for row in catalog["tables"].get(detail_table, [])
        }
        affected_skills = []
        effect_refs: dict[int, dict[str, Any]] = {}
        detail_ids: set[int] = set()
        for skill_id, status in sorted(status_by_skill.items()):
            reason = parse_reason(str(status.get("reason") or ""))
            pending = reason.get("backend_semantics_pending", {})
            refs = []
            table_ids = catalog["skill_table_ids"][str(skill_id)]
            for row_id in table_ids.get("effects", []):
                row = effects.get(int(row_id))
                if row is None or str(row.get("actual_type")) != primitive:
                    continue
                detail_id = int(row["actual_id"])
                detail_ids.add(detail_id)
                refs.append({"source_table": "effects", "row": row})
                effect_refs[int(row_id)] = row
            for row_id in table_ids.get("plot_effects", []):
                row = plot_effects.get(int(row_id))
                if row is None or str(row.get("actual_type")) != primitive:
                    continue
                detail_id = int(row["actual_id"])
                detail_ids.add(detail_id)
                refs.append({"source_table": "plot_effects", "row": row})
                effect_refs[int(row_id)] = row
            if not refs:
                continue
            affected_skills.append(
                {
                    "ability_id": int(status["ability_id"]),
                    "skill_id": skill_id,
                    "status": str(status["status"]),
                    "blocker": str(pending.get(primitive) or ""),
                    "references": refs,
                }
            )

        missing_detail_ids = sorted(detail_ids.difference(detail_index))
        if missing_detail_ids:
            raise RuntimeError(
                f"{primitive} references absent {detail_table} ids {missing_detail_ids}"
            )
        dossier_path = semantic_dossier_path(semantic_root, str(config["query_root"]))
        if not dossier_path.is_file():
            raise FileNotFoundError(dossier_path)
        dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
        dossier_root = dossier["root"]
        if str(dossier_root["root_key"]) != str(config["query_root"]):
            raise RuntimeError(f"Semantic dossier root mismatch for {primitive}")

        records[primitive] = {
            "affected_ability_ids": sorted(
                {int(row["ability_id"]) for row in affected_skills}
            ),
            "affected_skill_count": len(affected_skills),
            "affected_skills": affected_skills,
            "detail_rows": [detail_index[value] for value in sorted(detail_ids)],
            "detail_table": detail_table,
            "effect_reference_count": sum(
                len(row["references"]) for row in affected_skills
            ),
            "query_root": str(config["query_root"]),
            "semantic_dossier": {
                "path": dossier_path.resolve().as_posix(),
                "sha256": sha256_file(dossier_path),
                "closure_status": dossier["closure"]["closure_status"],
                "source_index_sha256": dossier["source_index_sha256"],
                "stage_15_sha256": dossier["stage_15_sha256"],
            },
        }

    return {
        "authority": {
            "aa8_catalog_rows": "runtime_contract",
            "stage_15": "loader_and_native_field_evidence",
            "semantic_dossiers": "derived_triage_not_runtime_authority",
            "wiki": "not_used",
            "historical_runtime": "not_used",
        },
        "client_build": "Kakao 8.0.3.12 r558734",
        "format": "AA8_SHARED_PRIMITIVE_CONTRACTS_V1",
        "primitives": records,
        "sources": {
            "native_combat_catalog": {
                "path": catalog_path.resolve().as_posix(),
                "sha256": sha256_file(catalog_path),
            }
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--semantic-dossiers", type=Path, default=DEFAULT_SEMANTIC_DOSSIERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = extract(args.catalog.resolve(), args.semantic_dossiers.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(result), encoding="utf-8")
    print(
        canonical(
            {
                "output": args.output.resolve().as_posix(),
                "sha256": sha256_file(args.output),
                "primitive_count": len(result["primitives"]),
                "affected_skills": {
                    primitive: row["affected_skill_count"]
                    for primitive, row in result["primitives"].items()
                },
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
