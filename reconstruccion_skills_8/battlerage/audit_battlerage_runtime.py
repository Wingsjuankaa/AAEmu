#!/usr/bin/env python3
"""Audit Battlerage presentation and movement against the native AA8 closure.

This is a read-only diagnostic. It never consults the historical 3.0 compact.
It turns the recovered AA8 graph into a per-skill matrix and checks whether
the server has the generic packet/model path required to expose that graph to
the client.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PRESENTATION_TYPES = {34: "Anim", 35: "FxGroup", 36: "FxGroupAnim", 37: "Projectile", 38: "ProjectileAnim"}
MOVEMENT_TYPES = {1: "Charge", 11: "Blink", 13: "KnockBack", 47: "TeleportToUnit", 55: "Detach", 73: "MoveToGround"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def index(rows: list[dict[str, Any]], key: str = "id") -> dict[int, dict[str, Any]]:
    return {int(row[key]): row for row in rows}


def grouped(rows: list[dict[str, Any]], key: str) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[int(row[key])].append(row)
    return result


def has_code_path(source_root: Path, class_name: str) -> dict[str, Any]:
    path = source_root / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Effects" / "SpecialEffects" / f"{class_name}.cs"
    if not path.is_file():
        return {"class": class_name, "exists": False, "server_execution": "missing"}
    text = path.read_text(encoding="utf-8-sig")
    has_todo = "// TODO" in text
    functional_tokens = (
        "SendPacket", "BroadcastPacket", ".Apply(", "SetPosition", "AddBuff", "RemoveBuff",
        "Cooldown", "Transform", "Teleport", "IsInPostCast", "LastCast", "ReduceCurrent",
        "Schedule", "ActiveSkillController",
    )
    has_functional_code = any(token in text for token in functional_tokens)
    is_stub = (has_todo and not has_functional_code) or (
        class_name == "Combo" and "_log.Trace" in text and "Schedule" not in text
    )
    state = "implemented"
    if class_name in PRESENTATION_TYPES.values():
        state = "client_presentation_packet"
    elif is_stub:
        state = "stub"
    elif has_todo:
        state = "partial"
    return {
        "class": class_name,
        "exists": True,
        "server_execution": state,
    }


def parse_special_type_names(source_root: Path) -> dict[int, str]:
    path = source_root / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Effects" / "SpecialEffectType.cs"
    text = path.read_text(encoding="utf-8-sig")
    return {
        int(value): name
        for name, value in re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)\s*,", text, re.MULTILINE)
    }


def build_audit(closure: dict[str, Any], source_root: Path) -> dict[str, Any]:
    tables = closure["tables"]
    skills = sorted(tables["skills"], key=lambda row: int(row["id"]))
    anims = index(tables["anims"])
    controllers = index(tables["skill_controllers"])
    projectiles = index(tables["projectiles"])
    plot_events_by_plot = grouped(tables["plot_events"], "plot_id")
    plot_effects_by_event = grouped(tables["plot_effects"], "event_id")
    special_effects = index(tables["special_effects"])
    special_type_names = parse_special_type_names(source_root)

    rows = []
    all_special_types: Counter[int] = Counter()
    referenced_anim_ids: set[int] = set()
    referenced_controller_ids: set[int] = set()
    referenced_projectile_ids: set[int] = set()

    for skill in skills:
        skill_id = int(skill["id"])
        plot_id = int(skill.get("plot_id") or 0)
        anim_fields = {
            field: int(skill.get(field) or 0)
            for field in ("start_anim_id", "fire_anim_id", "twohand_fire_anim_id", "dual_wield_fire_anim_id", "channeling_anim_id")
        }
        direct_anim_ids = sorted({value for value in anim_fields.values() if value})
        referenced_anim_ids.update(direct_anim_ids)

        controller_ids = []
        direct_controller_id = int(skill.get("skill_controller_id") or 0)
        if direct_controller_id:
            controller_ids.append(direct_controller_id)
            referenced_controller_ids.add(direct_controller_id)

        direct_projectile_id = int(skill.get("projectile_id") or 0)
        if direct_projectile_id:
            referenced_projectile_ids.add(direct_projectile_id)

        special_rows = []
        plot_event_ids = []
        for event in sorted(plot_events_by_plot.get(plot_id, []), key=lambda row: (int(row["position"]), int(row["id"]))) if plot_id else []:
            event_id = int(event["id"])
            plot_event_ids.append(event_id)
            for relation in sorted(plot_effects_by_event.get(event_id, []), key=lambda row: (int(row["position"]), int(row["id"]))):
                if relation["actual_type"] == "SkillController":
                    controller_id = int(relation["actual_id"])
                    controller_ids.append(controller_id)
                    referenced_controller_ids.add(controller_id)
                if relation["actual_type"] != "SpecialEffect":
                    continue
                special = special_effects.get(int(relation["actual_id"]))
                if special is None:
                    continue
                special_type = int(special["special_effect_type_id"])
                all_special_types[special_type] += 1
                raw = {
                    "event_id": event_id,
                    "effect_id": int(special["id"]),
                    "type_id": special_type,
                    "type": special_type_names.get(special_type, f"SpecialType{special_type}"),
                    "values": [int(special.get(f"value{i}") or 0) for i in range(1, 8)],
                }
                special_rows.append(raw)
                if special_type in (34, 38) and raw["values"][0]:
                    referenced_anim_ids.add(raw["values"][0])
                if special_type == 37 and raw["values"][0]:
                    referenced_projectile_ids.add(raw["values"][0])

        presentation_types = sorted({row["type"] for row in special_rows if row["type_id"] in PRESENTATION_TYPES})
        movement_types = sorted({row["type"] for row in special_rows if row["type_id"] in MOVEMENT_TYPES})
        controller_ids = sorted(set(controller_ids))
        controller_kinds = sorted({int(controllers[cid]["kind_id"]) for cid in controller_ids if cid in controllers})

        mode = []
        if direct_anim_ids or int(skill.get("fx_group_id") or 0) or direct_projectile_id:
            mode.append("direct_skill_packet")
        if plot_id:
            mode.append("plot_event_graph")
        if controller_ids:
            mode.append("skill_controller")

        rows.append({
            "skill_id": skill_id,
            "name": skill.get("name") or "",
            "visible": bool(int(skill.get("show") or 0)),
            "learnable": int(skill.get("skill_points") or 0) > 0,
            "plot_id": plot_id,
            "plot_only": bool(int(skill.get("plot_only") or 0)),
            "presentation_mode": mode,
            "animation_fields": anim_fields,
            "direct_animation_ids": direct_anim_ids,
            "fx_group_id": int(skill.get("fx_group_id") or 0),
            "projectile_id": direct_projectile_id,
            "plot_event_count": len(plot_event_ids),
            "plot_presentation_types": presentation_types,
            "plot_movement_types": movement_types,
            "skill_controller_ids": controller_ids,
            "skill_controller_kinds": controller_kinds,
            "missing_animation_ids": sorted(anim_id for anim_id in direct_anim_ids if anim_id not in anims),
            "missing_controller_ids": sorted(controller_id for controller_id in controller_ids if controller_id not in controllers),
            "missing_projectile_ids": [direct_projectile_id] if direct_projectile_id and direct_projectile_id not in projectiles else [],
            "special_effects": special_rows,
        })

    special_paths = {}
    for type_id in sorted(all_special_types):
        name = special_type_names.get(type_id, f"SpecialType{type_id}")
        special_paths[str(type_id)] = has_code_path(source_root, name)

    source_checks = {
        "weapon_animation_variants_loaded": all(
            token in (source_root / "AAEmu.Game" / "Core" / "Managers" / "SkillManager.cs").read_text(encoding="utf-8-sig")
            for token in ("twohand_fire_anim_id", "dual_wield_fire_anim_id")
        ),
        "weapon_animation_variants_selected": "SelectFireAnimId" in (source_root / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Skill.cs").read_text(encoding="utf-8-sig"),
        "plot_target_ids_serialized": "targetUnitIds" in (source_root / "AAEmu.Game" / "Core" / "Packets" / "G2C" / "SCPlotEventPacket.cs").read_text(encoding="utf-8-sig"),
    }

    return {
        "format_version": 1,
        "authority": ["compact-client-8.0-decrypted.sqlite", "game11_native", "x2game_confirmed", "observed_protocol"],
        "scope": {"ability_id": 1, "skill_rows": len(rows), "visible_rows": sum(row["visible"] for row in rows)},
        "source_checks": source_checks,
        "reference_checks": {
            "animation_ids_missing": sorted(referenced_anim_ids.difference(anims)),
            "controller_ids_missing": sorted(referenced_controller_ids.difference(controllers)),
            "projectile_ids_missing": sorted(referenced_projectile_ids.difference(projectiles)),
        },
        "special_effect_code_paths": special_paths,
        "skills": rows,
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Auditoría transversal Battlerage AA8",
        "",
        "Generado únicamente desde la clausura nativa AA8 y el backend actual. No consulta ni reutiliza gameplay 3.0.",
        "",
        "## Resultado",
        "",
        f"- Filas Battlerage auditadas: **{audit['scope']['skill_rows']}**.",
        f"- Filas visibles: **{audit['scope']['visible_rows']}**.",
        f"- Animaciones referenciadas ausentes: `{audit['reference_checks']['animation_ids_missing']}`.",
        f"- Controladores referenciados ausentes: `{audit['reference_checks']['controller_ids_missing']}`.",
        f"- Proyectiles referenciados ausentes: `{audit['reference_checks']['projectile_ids_missing']}`.",
        "",
        "Los efectos `Anim`, `FxGroup`, `FxGroupAnim`, `Projectile` y `ProjectileAnim` de un plot son instrucciones de presentación que ejecuta el cliente al recibir `SCPlotEvent`; que su clase servidor sea un no-op no significa que debamos inventar el FX en backend.",
        "",
        "## Matriz",
        "",
        "| Skill | Visible | Ruta | Animaciones directas | Plot | Presentación del plot | Movimiento/controlador |",
        "|---:|:---:|---|---|---:|---|---|",
    ]
    for row in audit["skills"]:
        name = str(row["name"]).replace("|", "\\|")
        movement = ", ".join(row["plot_movement_types"])
        if row["skill_controller_ids"]:
            movement = (movement + "; " if movement else "") + "controller " + ",".join(map(str, row["skill_controller_ids"]))
        lines.append(
            f"| `{row['skill_id']}` {name} | {'sí' if row['visible'] else 'no'} | "
            f"{', '.join(row['presentation_mode']) or 'sin ruta'} | "
            f"{', '.join(map(str, row['direct_animation_ids'])) or '—'} | "
            f"{row['plot_id'] or '—'} | {', '.join(row['plot_presentation_types']) or '—'} | {movement or '—'} |"
        )
    pending_paths = [
        (type_id, path)
        for type_id, path in audit["special_effect_code_paths"].items()
        if path["server_execution"] in ("missing", "stub", "partial")
    ]
    lines += ["", "## Primitivas servidor pendientes", ""]
    if pending_paths:
        lines += ["| Tipo | Clase | Estado |", "|---:|---|---|"]
        for type_id, path in pending_paths:
            lines.append(f"| `{type_id}` | `{path['class']}` | `{path['server_execution']}` |")
    else:
        lines.append("No se detectaron primitivas pendientes en la clausura Battlerage.")
    lines += [
        "",
        "## Correcciones transversales incluidas",
        "",
        "- Selección de `fire_anim_id`, `twohand_fire_anim_id` o `dual_wield_fire_anim_id` según el arma realmente equipada.",
        "- Cálculo de `CombatSyncTime` con la misma variante de animación enviada al cliente.",
        "- Serialización de la lista real y sin duplicados de objetivos AoE en `SCPlotEvent`.",
        "- Conservación del grafo de plot y de sus FX nativos; no se crean animaciones ni desplazamientos artificiales.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    closure = json.loads(args.closure.read_text(encoding="utf-8"))
    audit = build_audit(closure, args.source_root)
    if args.verify:
        if audit["scope"]["skill_rows"] != 42:
            raise RuntimeError(f"Expected 42 Battlerage rows, found {audit['scope']['skill_rows']}")
        if not all(audit["source_checks"].values()):
            raise RuntimeError(f"Missing backend paths: {audit['source_checks']}")
        if audit["reference_checks"]["animation_ids_missing"]:
            raise RuntimeError(f"Missing animations: {audit['reference_checks']['animation_ids_missing']}")
        # Controller 604 belongs to hidden obsolete skill 11854.
        if set(audit["reference_checks"]["controller_ids_missing"]).difference({604}):
            raise RuntimeError(f"Missing controllers: {audit['reference_checks']['controller_ids_missing']}")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(canonical_json(audit), encoding="utf-8")
    args.markdown_output.write_text(render_markdown(audit), encoding="utf-8")
    print(canonical_json({"json": str(args.json_output.resolve()), "markdown": str(args.markdown_output.resolve()), "checks": audit["source_checks"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
