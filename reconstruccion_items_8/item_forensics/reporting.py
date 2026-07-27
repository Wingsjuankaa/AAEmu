from __future__ import annotations

import csv
import html
import io
import json
from pathlib import Path
from typing import Any

from .config import ForensicsConfig
from .db import open_database
from .families import FAMILIES
from .util import canonical_json, sha256_file, write_text_atomic


def explain_item(database: Path, item_id: int) -> dict[str, Any]:
    connection = open_database(database, writable=False)
    try:
        item = connection.execute(
            "SELECT * FROM items WHERE item_id=?",
            (item_id,),
        ).fetchone()
        if item is None:
            raise KeyError(f"AA8 client item {item_id} is not present")
        summary = connection.execute(
            "SELECT * FROM item_summary WHERE item_id=?",
            (item_id,),
        ).fetchone()
        coverage = connection.execute(
            "SELECT * FROM runtime_coverage WHERE item_id=?",
            (item_id,),
        ).fetchone()
        descriptors = [
            dict(row)
            for row in connection.execute(
                """
                SELECT family,table_name,row_key,state,provenance,
                       descriptor_json,evidence_json
                FROM descriptors WHERE item_id=?
                ORDER BY family,table_name,row_key
                """,
                (item_id,),
            )
        ]
        dependencies = [
            dict(row)
            for row in connection.execute(
                """
                SELECT relation,dst_kind,dst_id,required,state,provenance,
                       evidence_json
                FROM dependency_edges
                WHERE src_kind='item' AND src_id=?
                ORDER BY relation,dst_kind,dst_id
                """,
                (str(item_id),),
            )
        ]
        incoming = [
            dict(row)
            for row in connection.execute(
                """
                SELECT src_kind,src_id,relation,required,state,provenance,
                       evidence_json
                FROM dependency_edges
                WHERE dst_kind='item' AND dst_id=?
                ORDER BY src_kind,src_id,relation
                """,
                (str(item_id),),
            )
        ]
        capabilities = [
            dict(row)
            for row in connection.execute(
                """
                SELECT dimension,state,capability,evidence_kind,evidence_json
                FROM server_capabilities WHERE item_id=?
                ORDER BY CASE dimension
                    WHEN 'catalog' THEN 0 WHEN 'descriptor' THEN 1
                    WHEN 'dependency_closure' THEN 2 WHEN 'backend' THEN 3
                    WHEN 'protocol' THEN 4 WHEN 'persistence' THEN 5
                    WHEN 'validation' THEN 6 ELSE 99 END
                """,
                (item_id,),
            )
        ]
        gaps = [
            dict(row)
            for row in connection.execute(
                """
                SELECT dimension,state,severity,blocker_code,reason,required_evidence
                FROM gaps WHERE item_id=?
                ORDER BY severity DESC,dimension,blocker_code
                """,
                (item_id,),
            )
        ]
        surface_references = [
            dict(row)
            for row in connection.execute(
                """
                SELECT s.source_kind,s.path,s.extension,r.token_kind,r.locator,
                       r.state,r.provenance,r.evidence_json
                FROM surface_references r
                JOIN client_surfaces s ON s.surface_id=r.surface_id
                WHERE r.item_id=?
                ORDER BY CASE r.state WHEN 'corroborative' THEN 0 ELSE 1 END,
                         s.source_kind,s.path,r.token_kind,r.locator
                """,
                (item_id,),
            )
        ]
        return {
            "capabilities": capabilities,
            "client_item": {
                **dict(item),
                "client_row": json.loads(str(item["client_row_json"])),
            },
            "dependencies": dependencies,
            "descriptors": descriptors,
            "gaps": gaps,
            "incoming_item_dependencies": incoming,
            "runtime_coverage": dict(coverage) if coverage else None,
            "summary": dict(summary) if summary else None,
            "surface_references": surface_references,
        }
    finally:
        connection.close()


def _report_payload(connection) -> dict[str, Any]:
    items = []
    for row in connection.execute(
        """
        SELECT item_id,impl_id,name,family,runtime_coverage,
               max_gap_severity,gap_count,dependency_count
        FROM item_summary ORDER BY item_id
        """
    ):
        item_id = int(row["item_id"])
        capabilities = [
            [value["dimension"], value["state"]]
            for value in connection.execute(
                """
                SELECT dimension,state FROM server_capabilities
                WHERE item_id=? ORDER BY dimension
                """,
                (item_id,),
            )
        ]
        blockers = [
            [value["dimension"], value["state"], value["blocker_code"]]
            for value in connection.execute(
                """
                SELECT dimension,state,blocker_code FROM gaps
                WHERE item_id=? ORDER BY severity DESC,dimension
                """,
                (item_id,),
            )
        ]
        dependencies = [
            [
                value["relation"],
                value["dst_kind"],
                value["dst_id"],
                value["state"],
            ]
            for value in connection.execute(
                """
                SELECT relation,dst_kind,dst_id,state FROM dependency_edges
                WHERE src_kind='item' AND src_id=?
                ORDER BY relation,dst_kind,dst_id LIMIT 100
                """,
                (str(item_id),),
            )
        ]
        surface_reference_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM surface_references WHERE item_id=?",
                (item_id,),
            ).fetchone()[0]
        )
        items.append(
            {
                "id": item_id,
                "impl": int(row["impl_id"]),
                "name": row["name"] or "",
                "family": row["family"],
                "coverage": row["runtime_coverage"],
                "severity": int(row["max_gap_severity"]),
                "gapCount": int(row["gap_count"]),
                "dependencyCount": int(row["dependency_count"]),
                "surfaceReferenceCount": surface_reference_count,
                "capabilities": capabilities,
                "blockers": blockers,
                "dependencies": dependencies,
            }
        )
    return {
        "items": items,
        "summary": {
            "items": len(items),
            "families": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    """
                    SELECT family,COUNT(*) FROM item_summary
                    GROUP BY family ORDER BY family
                    """
                )
            },
            "coverage": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    """
                    SELECT runtime_coverage,COUNT(*) FROM item_summary
                    GROUP BY runtime_coverage ORDER BY runtime_coverage
                    """
                )
            },
            "gapStates": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    "SELECT state,COUNT(*) FROM gaps GROUP BY state ORDER BY state"
                )
            },
            "opaque": int(
                connection.execute("SELECT COUNT(*) FROM opaque_regions").fetchone()[0]
            ),
            "reviewManifests": int(
                connection.execute("SELECT COUNT(*) FROM review_manifests").fetchone()[0]
            ),
            "surfaceReferences": int(
                connection.execute("SELECT COUNT(*) FROM surface_references").fetchone()[0]
            ),
            "corroborativeSurfaceReferences": int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM surface_references
                    WHERE state='corroborative'
                    """
                ).fetchone()[0]
            ),
            "surfaces": {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    """
                    SELECT source_kind,COUNT(*) FROM client_surfaces
                    GROUP BY source_kind ORDER BY source_kind
                    """
                )
            },
        },
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA8 Item Forensics</title>
<style>
:root {{ color-scheme: dark; --bg:#0c1117; --panel:#151d27; --line:#2b3948;
 --text:#e6edf3; --muted:#93a4b7; --ok:#3fb950; --warn:#d29922; --bad:#f85149; }}
* {{ box-sizing:border-box }} body {{ margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 system-ui,Segoe UI,sans-serif }} header {{ padding:24px 28px;
border-bottom:1px solid var(--line);background:#101720;position:sticky;top:0;z-index:2 }}
h1 {{ margin:0 0 4px;font-size:22px }} .muted {{ color:var(--muted) }}
main {{ padding:20px 28px }} .stats {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:10px;margin-bottom:16px }} .card {{ background:var(--panel);border:1px solid var(--line);
border-radius:8px;padding:12px }} .card strong {{ display:block;font-size:20px }}
.filters {{ display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:8px;margin:14px 0 }}
input,select {{ width:100%;background:#0d141d;color:var(--text);border:1px solid var(--line);
border-radius:6px;padding:9px }} table {{ width:100%;border-collapse:collapse;background:var(--panel) }}
th,td {{ padding:8px 10px;border-bottom:1px solid var(--line);text-align:left }}
th {{ position:sticky;top:94px;background:#17212c }} tr {{ cursor:pointer }}
tr:hover {{ background:#1d2936 }} .s0 {{ color:var(--ok) }} .s1 {{ color:var(--warn) }}
.s3,.s4 {{ color:var(--bad) }} #detail {{ margin-top:18px }} code {{
background:#0d141d;padding:2px 4px;border-radius:4px }} ul {{ padding-left:20px }}
@media(max-width:800px) {{ .filters {{ grid-template-columns:1fr }} header {{ position:static }}
th {{ position:static }} }}
</style>
</head>
<body>
<header><h1>AA8 Item Forensics</h1>
<div class="muted">Kakao 8.0.3.12 r558734 · evidencia cliente nativa · sin gameplay 3.0</div></header>
<main>
<div class="stats" id="stats"></div>
<div class="filters">
 <input id="q" placeholder="ID o nombre">
 <select id="family"><option value="">Todas las familias</option></select>
 <select id="coverage"><option value="">Toda cobertura runtime</option></select>
 <select id="severity"><option value="">Toda severidad</option>
  <option value="0">Sin brechas</option><option value="1">Desconocida</option>
  <option value="3">Faltante</option><option value="4">Bloqueada</option></select>
</div>
<div class="muted" id="resultCount"></div>
<table><thead><tr><th>ID</th><th>Nombre</th><th>Impl</th><th>Familia</th>
<th>Runtime</th><th>Brechas</th><th>Deps</th><th>Refs</th></tr></thead><tbody id="rows"></tbody></table>
<section id="detail"></section>
</main>
<script id="payload" type="application/json">{payload}</script>
<script>
const data=JSON.parse(document.getElementById('payload').textContent);
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
$('stats').innerHTML=`<div class=card><span class=muted>Items cliente</span><strong>${{data.summary.items}}</strong></div>
<div class=card><span class=muted>Familias</span><strong>${{Object.keys(data.summary.families).length}}</strong></div>
<div class=card><span class=muted>Catalog only</span><strong>${{data.summary.coverage.catalog_only||0}}</strong></div>
<div class=card><span class=muted>Regiones opacas</span><strong>${{data.summary.opaque}}</strong></div>`;
for(const f of Object.keys(data.summary.families)) $('family').insertAdjacentHTML('beforeend',`<option>${{esc(f)}}</option>`);
for(const c of Object.keys(data.summary.coverage)) $('coverage').insertAdjacentHTML('beforeend',`<option>${{esc(c)}}</option>`);
function filtered(){{
 const q=$('q').value.trim().toLowerCase(),f=$('family').value,c=$('coverage').value,s=$('severity').value;
 return data.items.filter(x=>(!q||String(x.id).includes(q)||x.name.toLowerCase().includes(q))&&
 (!f||x.family===f)&&(!c||x.coverage===c)&&(!s||String(x.severity)===s));
}}
function render(){{
 const values=filtered(); $('resultCount').textContent=`${{values.length}} resultado(s); se muestran hasta 750`;
 $('rows').innerHTML=values.slice(0,750).map(x=>`<tr data-id="${{x.id}}"><td>${{x.id}}</td>
 <td>${{esc(x.name)}}</td><td>${{x.impl}}</td><td>${{esc(x.family)}}</td>
 <td>${{esc(x.coverage)}}</td><td class=s${{x.severity}}>${{x.gapCount}}</td>
 <td>${{x.dependencyCount}}</td><td>${{x.surfaceReferenceCount}}</td></tr>`).join('');
 document.querySelectorAll('tbody tr').forEach(r=>r.onclick=()=>show(Number(r.dataset.id)));
}}
function show(id){{
 const x=data.items.find(v=>v.id===id); if(!x)return; location.hash='item='+id;
 $('detail').innerHTML=`<div class=card><h2>${{x.id}} · ${{esc(x.name)}}</h2>
 <p><code>impl=${{x.impl}}</code> <code>${{esc(x.family)}}</code> <code>${{esc(x.coverage)}}</code></p>
 <h3>Capacidades</h3><ul>${{x.capabilities.map(v=>`<li><b>${{esc(v[0])}}</b>: ${{esc(v[1])}}</li>`).join('')}}</ul>
 <h3>Bloqueos</h3><ul>${{x.blockers.map(v=>`<li>${{esc(v[0])}} · ${{esc(v[1])}} · <code>${{esc(v[2])}}</code></li>`).join('')||'<li>Ninguno</li>'}}</ul>
 <h3>Dependencias</h3><ul>${{x.dependencies.map(v=>`<li>${{esc(v[0])}} → ${{esc(v[1])}} ${{esc(v[2])}} (${{esc(v[3])}})</li>`).join('')||'<li>Ninguna registrada</li>'}}</ul></div>`;
 $('detail').scrollIntoView({{behavior:'smooth'}});
}}
for(const id of ['q','family','coverage','severity']) $(id).addEventListener(id==='q'?'input':'change',render);
render(); const match=location.hash.match(/item=(\\d+)/); if(match) show(Number(match[1]));
</script></body></html>
"""


def generate_report(config: ForensicsConfig) -> dict[str, Any]:
    connection = open_database(config.database, writable=False)
    try:
        payload = _report_payload(connection)
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(
            [
                "item_id",
                "impl_id",
                "name",
                "family",
                "runtime_coverage",
                "dimension",
                "state",
                "severity",
                "blocker_code",
                "reason",
                "required_evidence",
            ]
        )
        for row in connection.execute(
            """
            SELECT s.item_id,s.impl_id,s.name,s.family,s.runtime_coverage,
                   g.dimension,g.state,g.severity,g.blocker_code,g.reason,
                   g.required_evidence
            FROM gaps g JOIN item_summary s ON s.item_id=g.item_id
            ORDER BY g.severity DESC,s.item_id,g.dimension,g.blocker_code
            """
        ):
            writer.writerow(list(row))
        opaque = [
            dict(row)
            for row in connection.execute(
                """
                SELECT surface,locator,blocker_code,reason,searched_evidence_json
                FROM opaque_regions ORDER BY surface,locator,blocker_code
                """
            )
        ]
        ghidra_tasks = [
            dict(row)
            for row in connection.execute(
                """
                SELECT q.table_name,q.sql_text,q.columns_json,q.layout_json,
                       q.loader_consumer,q.status AS spec_status,
                       r.status AS result_status,r.error,q.evidence_json
                FROM query_specs q
                JOIN cached_results r ON r.query_spec_id=q.query_spec_id
                WHERE q.status IN (
                          'layout_missing',
                          'invalid_layout',
                          'offset_and_anchor_missing'
                      )
                   OR r.status='decode_failed'
                ORDER BY
                    CASE r.status
                        WHEN 'blocked_unresolved_string_references' THEN 0
                        WHEN 'layout_missing' THEN 1
                        ELSE 2
                    END,
                    q.table_name,q.source_module
                """
            )
        ]
        family_queue = []
        for row in connection.execute(
            """
            SELECT family,COUNT(*) AS items,
                   SUM(CASE WHEN runtime_coverage='catalog_only' THEN 1 ELSE 0 END)
                       AS catalog_only,
                   SUM(CASE WHEN max_gap_severity>=4 THEN 1 ELSE 0 END) AS blocked
            FROM item_summary GROUP BY family ORDER BY family
            """
        ):
            name = str(row["family"])
            family = next(
                (value for value in FAMILIES.values() if value.name == name),
                None,
            )
            confirmed_descriptors = int(
                connection.execute(
                    """
                    SELECT COUNT(DISTINCT item_id) FROM descriptors
                    WHERE family=? AND state='confirmed'
                    """,
                    (name,),
                ).fetchone()[0]
            )
            items_count = int(row["items"])
            family_queue.append(
                {
                    "family": name,
                    "items": items_count,
                    "catalog_only": int(row["catalog_only"] or 0),
                    "blocked": int(row["blocked"] or 0),
                    "native_data_complete": (
                        confirmed_descriptors == items_count
                    ),
                    "protocol_known": bool(family and family.protocol_known),
                    "non_destructive": bool(family and not family.destructive),
                    "non_economic": bool(family and not family.economic),
                    "confirmed_descriptors": confirmed_descriptors,
                }
            )
        family_queue.sort(
            key=lambda value: (
                not value["native_data_complete"],
                not value["protocol_known"],
                not value["non_destructive"],
                not value["non_economic"],
                -value["items"],
                value["family"],
            )
        )
        reviewed_surfaces = {
            "inventory": [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT source_kind,extension,file_count,total_bytes,evidence_json
                    FROM surface_inventory ORDER BY source_kind,extension
                    """
                )
            ],
            "manifests": [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT path,sha256,authority,classification_json,summary_json
                    FROM review_manifests ORDER BY path
                    """
                )
            ],
            "references_by_source": [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT s.source_kind,r.token_kind,r.state,COUNT(*) AS count
                    FROM surface_references r
                    JOIN client_surfaces s ON s.surface_id=r.surface_id
                    GROUP BY s.source_kind,r.token_kind,r.state
                    ORDER BY s.source_kind,r.token_kind,r.state
                    """
                )
            ],
        }
    finally:
        connection.close()
    payload_json = canonical_json(payload)
    html_text = HTML_TEMPLATE.format(
        payload=payload_json.replace("</", "<\\/")
    )
    html_path = config.output_dir / "report.html"
    json_path = config.output_dir / "report-data.json"
    csv_path = config.output_dir / "gaps.csv"
    opaque_path = config.output_dir / "opaque-regions.json"
    ghidra_path = config.output_dir / "ghidra-layout-tasks.json"
    queue_path = config.output_dir / "family-queue.json"
    surfaces_path = config.output_dir / "reviewed-surfaces.json"
    write_text_atomic(html_path, html_text)
    write_text_atomic(json_path, canonical_json(payload, pretty=True))
    write_text_atomic(csv_path, buffer.getvalue())
    write_text_atomic(opaque_path, canonical_json(opaque, pretty=True))
    write_text_atomic(ghidra_path, canonical_json(ghidra_tasks, pretty=True))
    write_text_atomic(queue_path, canonical_json(family_queue, pretty=True))
    write_text_atomic(
        surfaces_path,
        canonical_json(reviewed_surfaces, pretty=True),
    )
    report_manifest = {
        "database_sha256": sha256_file(config.database),
        "files": {
            path.name: sha256_file(path)
            for path in (
                csv_path,
                ghidra_path,
                html_path,
                json_path,
                opaque_path,
                queue_path,
                surfaces_path,
            )
        },
        "historical_3_0_gameplay_rows": 0,
        "summary": payload["summary"],
    }
    report_manifest_path = config.output_dir / "report-manifest.json"
    write_text_atomic(
        report_manifest_path,
        canonical_json(report_manifest, pretty=True),
    )
    return {
        "html": html_path,
        "csv": csv_path,
        "json": json_path,
        "opaque": opaque_path,
        "ghidra_tasks": ghidra_path,
        "family_queue": queue_path,
        "reviewed_surfaces": surfaces_path,
        "manifest": report_manifest_path,
        "summary": payload["summary"],
    }
