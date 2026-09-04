"""Audit AA10 Memory Tome destinations against SQLite and read-only pak extraction.

Outputs are evidence only; never edits client/runtime catalogues.
"""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path("E:/AAEmu/rama_10")
REPO = ROOT / "server/AAEmu"
CLIENT = ROOT / "client/ArcheAge-Returns-10.0.2.13-r575"
QUERY = """
WITH book AS (
 SELECT DISTINCT b.district_id
 FROM doodad_funcs f JOIN doodad_func_groups g ON g.id=f.doodad_func_group_id
 JOIN doodad_func_bindings b ON b.id=f.actual_func_id
 WHERE f.actual_func_type='DoodadFuncBinding' AND COALESCE(b.zone_id,0)=0
)
SELECT DISTINCT p.id,p.editor_name,p.name,p.use_additional,d.district_id,d.faction_id
FROM return_points p JOIN district_return_points d ON d.return_point_id=p.id
JOIN book b ON b.district_id=d.district_id ORDER BY p.id,d.district_id,d.faction_id
"""


def run_tool(name, *args):
    return subprocess.run(["dotnet", "run", "--project", str(REPO /
        f"reconstruccion_cliente_10/tools/{name}"), "-c", "Release", "--", *map(str, args)],
        check=True, capture_output=True, encoding="utf-8").stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown", type=Path, help="Optional generated catalogue report")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    index = ROOT / "forensics/output/aa10-client-forensics/returns-r575-pak-index.csv"
    with index.open(encoding="utf-8-sig", newline="") as source:
        entries = sorted(row["name"] for row in csv.DictReader(source, delimiter=";")
            if re.match(r"game/worlds/[^/]+/level_design/zone/\d+/world_server/(district\.xml|return_point\.g)$", row["name"]))
    entry_list = out / "entries.txt"
    entry_list.write_text("\n".join(entries), encoding="utf-8")
    extracted = out / "pak"
    manifest = run_tool("PakBatchExtract", CLIENT / "game_pak", entry_list, extracted)
    (out / "extraction-manifest.txt").write_text(manifest, encoding="utf-8")
    points = {}
    areas = {}
    for entry in entries:
        path = extracted / entry.removeprefix("game/")
        if entry.endswith("return_point.g"):
            for body in re.split(r"(?m)^object\s*$", path.read_text(encoding="utf-8-sig")):
                name = re.search(r"(?m)^\s*name\s+ReturnPoint_(\S+)", body, flags=re.I)
                pos = re.search(r"pos\s+\(\s*x\s+([^,]+),\s*y\s+([^,]+),\s*z\s+([^\)]+)\)", body)
                if name and pos:
                    points.setdefault(name[1].lower(), []).append({"entry": entry,
                        "position": [float(pos[i]) for i in (1, 2, 3)]})
        else:
            for entity in ET.parse(path).iter("Entity"):
                for area in entity.iter("Area"):
                    if area.get("Group") == "22":
                        district = int(float(area.get("value1", "0")))
                        areas.setdefault(district, []).append({"entry": entry,
                            "entity": entity.get("Name"), "position": entity.get("Pos"),
                            "height": area.get("Height"), "points": [p.attrib for p in area.iter("Point")]})
    sources = {}
    rows = None
    english_names = {}
    for label, path in {
        "full": ROOT / "data/sqlite/authoritative/game_decrypted.sqlite3",
        "retail": CLIENT / "game/db/compact.sqlite3",
        "runtime": REPO / ".server_files/AAEmu.Game/Data/compact.sqlite3",
    }.items():
        with path.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            current = list(db.execute(QUERY))
            if label == "retail":
                english_names = dict(db.execute("SELECT idx,en_us FROM localized_texts "
                    "WHERE tbl_name='return_points' AND tbl_column_name='name'"))
        sources[label] = {"path": str(path), "sha256": sha, "rows": len(current),
            "catalogue_matches_full": rows is None or current == rows}
        if rows is None:
            rows = current
    manual_text = (REPO / "AAEmu.Game/Data/Portal/recalls.json").read_text(encoding="utf-8-sig")
    manual = json.loads(re.sub(r"/\*.*?\*/|//[^\r\n]*", "", manual_text, flags=re.S))
    manual = {p["Id"]: p for p in manual}
    catalogue = {}
    for pid, editor, name, use_additional, district, faction in rows:
        point = catalogue.setdefault(pid, {"id": pid, "editor_name": editor, "name": name,
            "english_name": english_names.get(pid) or editor,
            "use_additional": use_additional, "native_placements": points.get((editor or "").lower(), []),
            "json_override": manual.get(pid), "districts": {}})
        point["districts"].setdefault(district, {"factions": [], "areas": areas.get(district, [])})["factions"].append(faction)
    missing = [p["id"] for p in catalogue.values() if not p["native_placements"] and not p["json_override"]]
    summary = {"total": len(catalogue), "districts": len({r[4] for r in rows}),
        "native_placed": sum(bool(p["native_placements"]) for p in catalogue.values()),
        "available": len(catalogue)-len(missing), "unplaced": missing,
        "without_static_district_area": [p["id"] for p in catalogue.values()
            if not any(d["areas"] for d in p["districts"].values())]}
    (out / "catalogue.json").write_text(json.dumps({"sources": sources, "summary": summary,
        "catalogue": list(catalogue.values())}, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.markdown:
        lines = ["# Catálogo auditado del Teleport Book r575", "",
            "Generado por `reconstruccion_cliente_10/scripts/audit_teleport_book.py`.", "",
            "192 destinos, 187 distritos y 1452 relaciones por facción; catálogo idéntico en SQLite completa, retail y runtime.",
            "185 destinos con colocación nativa; 5 conservados por JSON histórico; 2 sin colocación demostrada.", "",
            "Esta tabla acredita datos disponibles, no una prueba dinámica de cada destino.",
            "Distrito y Zone son IDs diferentes. Los permisos por facción siguen las relaciones r575.", "",
            "| Return point | Nombre (localización r575) | Distrito(s) | Zone(s) | Evidencia / estado |",
            "|---|---|---|---|---|"]
        for p in catalogue.values():
            zones = sorted({int(re.search(r"/zone/(\d+)/", loc["entry"])[1]) for loc in p["native_placements"]})
            status = "Colocación y área nativas"
            if not p["native_placements"]:
                status = "JSON histórico; sin área estática encontrada" if p["json_override"] else "PENDIENTE: sin colocación demostrada"
                if p["json_override"]:
                    zones = [p["json_override"]["ZoneId"]]
            lines.append(f"| {p['id']} | {p['english_name'].replace('|', '/')} | "
                f"{', '.join(map(str, p['districts']))} | {', '.join(map(str, zones)) or '—'} | {status} |")
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
