from __future__ import annotations

import csv
import html
import json
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .schema import open_read_only, table_count
from .util import atomic_text, canonical_json, sha256_file


HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA8 Client Forensics — Skills</title>
<style>
:root{{color-scheme:dark;--bg:#101418;--panel:#182027;--line:#2a3944;
--text:#e8f0f4;--muted:#91a6b2;--accent:#58c8b6;--bad:#ff8178;--warn:#f3c969}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 system-ui,sans-serif}}header{{padding:20px 24px;border-bottom:1px solid
var(--line);background:#121a20;position:sticky;top:0;z-index:2}}h1{{margin:0 0 4px;
font-size:22px}}.muted{{color:var(--muted)}}main{{display:grid;
grid-template-columns:minmax(520px,1.25fr) minmax(360px,.75fr);gap:16px;padding:16px}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:10px;
overflow:hidden}}.toolbar{{display:flex;gap:8px;flex-wrap:wrap;padding:12px;
border-bottom:1px solid var(--line)}}input,select{{background:#0f151a;color:var(--text);
border:1px solid var(--line);border-radius:6px;padding:8px}}input{{min-width:260px;
flex:1}}button{{background:#22323b;color:var(--text);border:1px solid var(--line);
border-radius:6px;padding:7px 10px;cursor:pointer}}table{{width:100%;
border-collapse:collapse}}th,td{{padding:8px 10px;border-bottom:1px solid #223039;
text-align:left}}th{{color:var(--muted);font-size:12px;position:sticky;top:0;
background:var(--panel)}}tr.skill{{cursor:pointer}}tr.skill:hover{{background:#203039}}
.badge{{display:inline-block;padding:2px 6px;border-radius:999px;background:#24343d;
font-size:11px}}.confirmed{{color:var(--accent)}}.unknown,.blocked{{color:var(--warn)}}
.missing{{color:var(--bad)}}#rows{{max-height:calc(100vh - 190px);overflow:auto}}
#detail{{padding:16px;max-height:calc(100vh - 110px);overflow:auto}}dl{{display:grid;
grid-template-columns:140px 1fr;gap:6px 10px}}dt{{color:var(--muted)}}dd{{margin:0}}
pre{{white-space:pre-wrap;word-break:break-word;background:#11181d;padding:10px;
border-radius:7px;border:1px solid var(--line)}}.stats{{display:flex;gap:12px;
flex-wrap:wrap;margin-top:10px}}.stat{{background:#1d2a31;padding:6px 9px;
border-radius:6px}}@media(max-width:900px){{main{{grid-template-columns:1fr}}
#detail,#rows{{max-height:none}}}}
</style>
</head>
<body>
<header><h1>AA8 Client Forensics — Skills</h1>
<div class="muted">Kakao 8.0.3.12 r558734 · evidencia forense, no runtime</div>
<div class="stats" id="summary"></div></header>
<main>
<section class="panel">
<div class="toolbar">
<input id="search" placeholder="Buscar ID o nombre">
<select id="lifecycle"><option value="">Todos los lifecycle</option></select>
<select id="state"><option value="">Todos los estados</option></select>
<select id="gap"><option value="">Con y sin gaps</option>
<option value="yes">Con gaps</option><option value="no">Sin gaps</option></select>
</div>
<div id="rows"><table><thead><tr><th>ID</th><th>Nombre</th><th>Lifecycle</th>
<th>Estado</th><th>Rel.</th><th>Gaps</th><th>Wiki</th></tr></thead>
<tbody id="body"></tbody></table></div>
</section>
<aside class="panel"><div id="detail"><span class="muted">
Selecciona una skill para inspeccionar su resumen.</span></div></aside>
</main>
<script>
const DATA={payload};
const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({{
'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function options(id,values){{for(const value of [...new Set(values)].sort()){{
const o=document.createElement('option');o.value=value;o.textContent=value;$(id).append(o)}}}}
options('lifecycle',DATA.skills.map(x=>x.lifecycle));
options('state',DATA.skills.map(x=>x.state));
$('summary').innerHTML=Object.entries(DATA.summary).map(([k,v])=>
`<span class="stat"><b>${{Number(v).toLocaleString('es-CL')}}</b> ${{esc(k)}}</span>`).join('');
let visible=[];
function render(){{
const q=$('search').value.trim().toLowerCase(),life=$('lifecycle').value,
state=$('state').value,gap=$('gap').value;
visible=DATA.skills.filter(x=>(!q||String(x.id).includes(q)||x.name.toLowerCase().includes(q))
&&(!life||x.lifecycle===life)&&(!state||x.state===state)
&&(!gap||(gap==='yes'?x.gaps>0:x.gaps===0)));
const shown=visible.slice(0,500);
$('body').innerHTML=shown.map((x,i)=>`<tr class="skill" data-i="${{i}}">
<td>${{esc(x.id)}}</td><td>${{esc(x.name)}}</td><td><span class="badge">${{esc(x.lifecycle)}}</span></td>
<td class="${{esc(x.state)}}">${{esc(x.state)}}</td><td>${{x.outgoing}} / ${{x.incoming}}</td>
<td>${{x.gaps}}</td><td>${{x.wiki}}</td></tr>`).join('');
document.querySelectorAll('tr.skill').forEach(row=>row.onclick=()=>detail(shown[+row.dataset.i]));
}}
function detail(x){{
$('detail').innerHTML=`<h2>skill:${{esc(x.id)}}</h2><h3>${{esc(x.name)||'<span class="muted">sin nombre</span>'}}</h3>
<dl><dt>Fila nativa</dt><dd>${{x.native?'sí':'no'}}</dd><dt>Lifecycle</dt><dd>${{esc(x.lifecycle)}}</dd>
<dt>Estado</dt><dd class="${{esc(x.state)}}">${{esc(x.state)}}</dd>
<dt>Localizaciones</dt><dd>${{x.localizations}}</dd><dt>Relaciones</dt>
<dd>${{x.outgoing}} salientes / ${{x.incoming}} entrantes</dd><dt>Gaps</dt><dd>${{x.gaps}}</dd>
<dt>Severidad máxima</dt><dd>${{x.severity}}</dd><dt>Wiki</dt><dd>${{x.wiki}}</dd></dl>
<h3>Cobertura</h3><pre>${{esc(JSON.stringify(x.coverage,null,2))}}</pre>
<h3>Tipos de relación saliente</h3><pre>${{esc(JSON.stringify(x.relationTypes,null,2))}}</pre>`;
}}
['search','lifecycle','state','gap'].forEach(id=>$(id).addEventListener('input',render));
render();
</script></body></html>"""


def _skill_payload(connection: sqlite3.Connection) -> dict[str, Any]:
    names: dict[str, str] = {}
    localization_counts: dict[str, int] = {}
    for row in connection.execute(
        """
        SELECT entity_key,COUNT(*) AS row_count,
               MAX(CASE
                   WHEN json_extract(evidence_json,'$.table')='skills'
                    AND json_extract(evidence_json,'$.column')='name'
                   THEN text_value ELSE NULL END) AS display_name
        FROM localizations
        WHERE entity_key LIKE 'skill:%'
        GROUP BY entity_key
        """
    ):
        key = str(row["entity_key"])
        localization_counts[key] = int(row["row_count"])
        if row["display_name"] is not None:
            names[key] = str(row["display_name"])

    outgoing = {
        str(row["src_entity_key"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT src_entity_key,COUNT(*) AS row_count FROM relations
            WHERE src_entity_key LIKE 'skill:%' GROUP BY src_entity_key
            """
        )
    }
    incoming = {
        str(row["dst_entity_key"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT dst_entity_key,COUNT(*) AS row_count FROM relations
            WHERE dst_entity_key LIKE 'skill:%' GROUP BY dst_entity_key
            """
        )
    }
    relation_types: dict[str, dict[str, int]] = defaultdict(dict)
    for row in connection.execute(
        """
        SELECT src_entity_key,relation,COUNT(*) AS row_count FROM relations
        WHERE src_entity_key LIKE 'skill:%'
        GROUP BY src_entity_key,relation
        ORDER BY src_entity_key,relation
        """
    ):
        relation_types[str(row["src_entity_key"])][str(row["relation"])] = int(
            row["row_count"]
        )
    gaps = {
        str(row["entity_key"]): (int(row["row_count"]), int(row["severity"]))
        for row in connection.execute(
            """
            SELECT entity_key,COUNT(*) AS row_count,MAX(severity) AS severity
            FROM gaps WHERE entity_key LIKE 'skill:%' GROUP BY entity_key
            """
        )
    }
    wiki = {
        str(row["entity_key"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT entity_key,COUNT(*) AS row_count FROM wiki_entities
            WHERE entity_key LIKE 'skill:%' GROUP BY entity_key
            """
        )
    }
    coverage: dict[str, dict[str, str]] = defaultdict(dict)
    for row in connection.execute(
        """
        SELECT scope_key,dimension,state FROM coverage
        WHERE scope_key LIKE 'skill:%'
        ORDER BY scope_key,dimension,coverage_key
        """
    ):
        coverage[str(row["scope_key"])][str(row["dimension"])] = str(
            row["state"]
        )
    native = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT entity_key FROM native_rows
            WHERE source_table='skills'
            """
        )
    }
    skills = []
    for row in connection.execute(
        """
        SELECT entity_key,native_id,lifecycle,state FROM entities
        WHERE kind='skill'
        ORDER BY CAST(native_id AS INTEGER),native_id
        """
    ):
        key = str(row["entity_key"])
        gap_count, severity = gaps.get(key, (0, 0))
        skills.append(
            {
                "id": str(row["native_id"]),
                "name": names.get(key, ""),
                "native": key in native,
                "lifecycle": str(row["lifecycle"]),
                "state": str(row["state"]),
                "localizations": localization_counts.get(key, 0),
                "outgoing": outgoing.get(key, 0),
                "incoming": incoming.get(key, 0),
                "gaps": gap_count,
                "severity": severity,
                "wiki": wiki.get(key, 0),
                "coverage": coverage.get(key, {}),
                "relationTypes": relation_types.get(key, {}),
            }
        )
    opaque = {
        str(row["blocker_code"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT blocker_code,COUNT(*) AS row_count FROM opaque_regions
            GROUP BY blocker_code ORDER BY blocker_code
            """
        )
    }
    return {
        "summary": {
            "skills": len(skills),
            "filas nativas": len(native),
            "con gaps": sum(value["gaps"] > 0 for value in skills),
            "regiones opacas": table_count(connection, "opaque_regions"),
        },
        "opaque": opaque,
        "skills": skills,
    }


def _write_gap_csv(connection: sqlite3.Connection, path: Path) -> None:
    handle, name = tempfile.mkstemp(
        prefix=".gaps-priority.", suffix=".csv", dir=path.parent
    )
    os.close(handle)
    temporary = Path(name)
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(
                (
                    "severity",
                    "entity_key",
                    "dimension",
                    "state",
                    "blocker_code",
                    "reason",
                    "required_evidence",
                )
            )
            for row in connection.execute(
                """
                SELECT severity,entity_key,dimension,state,blocker_code,reason,
                       required_evidence
                FROM gaps
                ORDER BY severity DESC,blocker_code,entity_key,dimension
                """
            ):
                writer.writerow(tuple(row))
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


ASSET_HTML_TEMPLATE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA8 Client Forensics — Assets</title>
<style>
:root{{color-scheme:dark;--bg:#101418;--panel:#182027;--line:#2a3944;
--text:#e8f0f4;--muted:#91a6b2;--accent:#58c8b6;--warn:#f3c969}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 system-ui,sans-serif}}header{{padding:20px 24px;border-bottom:1px
solid var(--line);background:#121a20}}h1{{margin:0 0 4px;font-size:22px}}
.muted{{color:var(--muted)}}main{{display:grid;grid-template-columns:1fr 1fr;
gap:16px;padding:16px}}.panel{{background:var(--panel);border:1px solid
var(--line);border-radius:10px;padding:14px;overflow:auto}}.stats{{display:flex;
gap:10px;flex-wrap:wrap;margin-top:10px}}.stat{{background:#1d2a31;padding:7px
10px;border-radius:6px}}input,select{{background:#0f151a;color:var(--text);
border:1px solid var(--line);border-radius:6px;padding:8px;margin:0 6px 10px 0}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:7px 9px;
border-bottom:1px solid #223039;text-align:left}}th{{color:var(--muted)}}
.confirmed,.corroborated{{color:var(--accent)}}.unknown,.blocked{{color:var(--warn)}}
pre{{white-space:pre-wrap;word-break:break-word}}@media(max-width:900px){{
main{{grid-template-columns:1fr}}}}</style></head>
<body><header><h1>AA8 Client Forensics — Assets</h1>
<div class="muted">Kakao 8.0.3.12 r558734 · catálogo, UI y localización; no runtime</div>
<div class="stats" id="summary"></div></header><main>
<section class="panel"><h2>Tipos del game_pak</h2><table><thead><tr>
<th>Tipo</th><th>Archivos</th></tr></thead><tbody id="types"></tbody></table>
<h2>Extracciones y relaciones</h2><pre id="relations"></pre></section>
<section class="panel"><h2>Iconos nativos</h2>
<input id="search" placeholder="Buscar ID o filename"><select id="state">
<option value="">Todos los estados</option><option>corroborated</option>
<option>unknown</option><option>missing</option></select>
<table><thead><tr><th>ID</th><th>Filename</th><th>Asset</th><th>Usado</th>
<th>Gaps</th></tr></thead><tbody id="icons"></tbody></table></section>
</main><script>
const DATA={payload};const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({{
'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
$('summary').innerHTML=Object.entries(DATA.summary).map(([k,v])=>
`<span class="stat"><b>${{Number(v).toLocaleString('es-CL')}}</b> ${{esc(k)}}</span>`).join('');
$('types').innerHTML=DATA.assetTypes.map(x=>`<tr><td>${{esc(x.type)}}</td>
<td>${{Number(x.count).toLocaleString('es-CL')}}</td></tr>`).join('');
$('relations').textContent=JSON.stringify(DATA.relationStates,null,2);
function render(){{const q=$('search').value.toLowerCase(),s=$('state').value;
const rows=DATA.icons.filter(x=>(!q||x.id.includes(q)||x.filename.toLowerCase().includes(q))
&&(!s||x.assetState===s)).slice(0,1000);$('icons').innerHTML=rows.map(x=>
`<tr><td>${{esc(x.id)}}</td><td>${{esc(x.filename)}}</td>
<td class="${{esc(x.assetState)}}">${{esc(x.assetState)}}</td>
<td>${{x.used?'sí':'no'}}</td><td>${{x.gaps}}</td></tr>`).join('')}}
['search','state'].forEach(id=>$(id).addEventListener('input',render));render();
</script></body></html>"""


def _asset_payload(connection: sqlite3.Connection) -> dict[str, Any]:
    asset_types = [
        {"type": str(row["asset_type"]), "count": int(row["row_count"])}
        for row in connection.execute(
            """
            SELECT asset_type,COUNT(*) AS row_count FROM assets
            GROUP BY asset_type ORDER BY row_count DESC,asset_type
            """
        )
    ]
    filenames = {
        str(row["entity_key"]): str(row["value_text"])
        for row in connection.execute(
            """
            SELECT entity_key,value_text FROM entity_properties
            WHERE namespace='icons' AND property_name='filename'
            """
        )
    }
    mapped = {
        str(row["src_entity_key"]): str(row["state"])
        for row in connection.execute(
            """
            SELECT src_entity_key,state FROM relations
            WHERE relation='resolves_to_asset'
            """
        )
    }
    incoming = {
        str(row["dst_entity_key"])
        for row in connection.execute(
            """
            SELECT DISTINCT dst_entity_key FROM relations
            WHERE dst_entity_key LIKE 'icon:%'
              AND relation<>'resolves_to_asset'
            """
        )
    }
    gaps = {
        str(row["entity_key"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT entity_key,COUNT(*) AS row_count FROM gaps
            WHERE entity_key LIKE 'icon:%' GROUP BY entity_key
            """
        )
    }
    icons = []
    for row in connection.execute(
        """
        SELECT entity_key,native_id,state FROM entities
        WHERE kind='icon' ORDER BY CAST(native_id AS INTEGER),native_id
        """
    ):
        key = str(row["entity_key"])
        icons.append(
            {
                "id": str(row["native_id"]),
                "filename": filenames.get(key, ""),
                "assetState": mapped.get(
                    key, "missing" if str(row["state"]) == "missing" else "unknown"
                ),
                "used": key in incoming,
                "gaps": gaps.get(key, 0),
            }
        )
    relation_states = {
        f"{row['relation']}:{row['state']}": int(row["row_count"])
        for row in connection.execute(
            """
            SELECT relation,state,COUNT(*) AS row_count FROM relations
            WHERE relation IN (
              'uses_asset','resolves_to_asset','references_asset',
              'references_unresolved_asset','uses_audio_event',
              'uses_fx_registry_entry','uses_animation_key'
            )
            GROUP BY relation,state ORDER BY relation,state
            """
        )
    }
    return {
        "summary": {
            "assets": table_count(connection, "assets"),
            "localizaciones": table_count(connection, "localizations"),
            "iconos": len(icons),
            "iconos usados": sum(value["used"] for value in icons),
            "gaps de iconos": sum(value["gaps"] for value in icons),
        },
        "assetTypes": asset_types,
        "relationStates": relation_states,
        "icons": icons,
    }


WIKI_HTML_TEMPLATE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA8 Client Forensics - Wiki</title>
<style>
:root{{color-scheme:dark;--bg:#101418;--panel:#182027;--line:#2a3944;
--text:#e8f0f4;--muted:#91a6b2;--ok:#58c8b6;--bad:#ff8178;--warn:#f3c969}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 system-ui,sans-serif}}header{{padding:20px 24px;border-bottom:1px
solid var(--line);background:#121a20;position:sticky;top:0;z-index:2}}
h1{{margin:0 0 4px;font-size:22px}}.muted{{color:var(--muted)}}
main{{padding:16px}}.panel{{background:var(--panel);border:1px solid var(--line);
border-radius:10px;overflow:hidden}}.toolbar{{display:flex;gap:8px;flex-wrap:wrap;
padding:12px;border-bottom:1px solid var(--line)}}input,select{{background:#0f151a;
color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px}}
input{{min-width:280px;flex:1}}table{{width:100%;border-collapse:collapse}}
th,td{{padding:7px 9px;border-bottom:1px solid #223039;text-align:left}}
th{{color:var(--muted);position:sticky;top:0;background:var(--panel)}}
.match{{color:var(--ok)}}.native_only,.wiki_only,.unresolved{{color:var(--warn)}}
.conflict{{color:var(--bad)}}#rows{{max-height:calc(100vh - 205px);overflow:auto}}
.stats{{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}}.stat{{
background:#1d2a31;padding:7px 10px;border-radius:6px}}</style></head>
<body><header><h1>AA8 Client Forensics - Wiki compatible</h1>
<div class="muted">Evidencia externa corroborativa; nunca reemplaza la autoridad nativa</div>
<div class="stats" id="summary"></div></header><main><section class="panel">
<div class="toolbar"><input id="search" placeholder="Buscar kind, ID o nombre">
<select id="kind"><option value="">Todas las clases</option></select>
<select id="comparison"><option value="">Todos los resultados</option></select>
</div><div id="rows"><table><thead><tr><th>Entidad</th><th>Nombre wiki</th>
<th>Respuesta</th><th>Comparacion</th><th>Prop.</th><th>Rel.</th></tr></thead>
<tbody id="body"></tbody></table></div></section></main><script>
const DATA={payload};const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({{
'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function options(id,values){{for(const value of [...new Set(values)].sort()){{
const o=document.createElement('option');o.value=value;o.textContent=value;$(id).append(o)}}}}
options('kind',DATA.entities.map(x=>x.kind));
options('comparison',DATA.entities.map(x=>x.comparison));
$('summary').innerHTML=Object.entries(DATA.summary).map(([k,v])=>
`<span class="stat"><b>${{Number(v).toLocaleString('es-CL')}}</b> ${{esc(k)}}</span>`).join('');
function render(){{const q=$('search').value.trim().toLowerCase(),
k=$('kind').value,c=$('comparison').value;const rows=DATA.entities.filter(x=>
(!q||x.key.toLowerCase().includes(q)||x.name.toLowerCase().includes(q))&&
(!k||x.kind===k)&&(!c||x.comparison===c)).slice(0,2000);
$('body').innerHTML=rows.map(x=>`<tr><td><a href="${{esc(x.url)}}">${{esc(x.key)}}</a></td>
<td>${{esc(x.name)}}</td><td>${{esc(x.state)}}</td>
<td class="${{esc(x.comparison)}}">${{esc(x.comparison)}}</td>
<td>${{x.properties}}</td><td>${{x.relations}}</td></tr>`).join('')}}
['search','kind','comparison'].forEach(id=>$(id).addEventListener('input',render));render();
</script></body></html>"""


def _wiki_payload(connection: sqlite3.Connection) -> dict[str, Any]:
    names = {
        str(row["wiki_entity_key"]): str(json.loads(row["value_json"]))
        for row in connection.execute(
            """
            SELECT wiki_entity_key,value_json FROM wiki_properties
            WHERE property_name='name'
            """
        )
        if isinstance(json.loads(row["value_json"]), str)
    }
    properties = {
        str(row["wiki_entity_key"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT wiki_entity_key,COUNT(*) AS row_count FROM wiki_properties
            GROUP BY wiki_entity_key
            """
        )
    }
    relations = {
        str(row["src_wiki_entity_key"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT src_wiki_entity_key,COUNT(*) AS row_count FROM wiki_relations
            GROUP BY src_wiki_entity_key
            """
        )
    }
    entities = []
    for row in connection.execute(
        """
        SELECT wiki_entity_key,entity_key,url,state,comparison_state
        FROM wiki_entities
        ORDER BY
          substr(entity_key,1,instr(entity_key,':')-1),
          CAST(substr(entity_key,instr(entity_key,':')+1) AS INTEGER),
          entity_key
        """
    ):
        key = str(row["entity_key"])
        wiki_key = str(row["wiki_entity_key"])
        entities.append(
            {
                "key": key,
                "kind": key.split(":", 1)[0],
                "name": names.get(wiki_key, ""),
                "url": str(row["url"]),
                "state": str(row["state"]),
                "comparison": str(row["comparison_state"]),
                "properties": properties.get(wiki_key, 0),
                "relations": relations.get(wiki_key, 0),
            }
        )
    comparisons = {
        str(row["comparison_state"]): int(row["row_count"])
        for row in connection.execute(
            """
            SELECT comparison_state,COUNT(*) AS row_count FROM wiki_entities
            GROUP BY comparison_state ORDER BY comparison_state
            """
        )
    }
    return {
        "summary": {
            "entidades comparadas": len(entities),
            "propiedades wiki": table_count(connection, "wiki_properties"),
            "relaciones wiki": table_count(connection, "wiki_relations"),
            "coincidencias": comparisons.get("match", 0),
            "conflictos": comparisons.get("conflict", 0),
        },
        "comparisons": comparisons,
        "entities": entities,
    }


CLOSURE_HTML_TEMPLATE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA8 Client Forensics — Coverage Closure</title>
<style>
:root{color-scheme:dark;--bg:#101418;--panel:#182027;--line:#2a3944;
--text:#e8f0f4;--muted:#91a6b2;--accent:#58c8b6;--warn:#f3c969}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 system-ui,sans-serif}header{padding:20px 24px;border-bottom:1px
solid var(--line);background:#121a20;position:sticky;top:0;z-index:2}
h1{margin:0 0 4px;font-size:22px}.muted{color:var(--muted)}
main{padding:16px}.summary{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;
padding:10px 14px}.card b{display:block;font-size:20px;color:var(--accent)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
input,select{background:#0f151a;color:var(--text);border:1px solid var(--line);
border-radius:6px;padding:8px}input{min-width:300px;flex:1}
.table{overflow:auto;border:1px solid var(--line);border-radius:8px}
table{width:100%;border-collapse:collapse;background:var(--panel)}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;
vertical-align:top}th{position:sticky;top:83px;background:#162028}
tr:hover{background:#202c34}.rank,.score{text-align:right;font-variant-numeric:tabular-nums}
.deferred{color:var(--muted)}code{white-space:nowrap}
</style></head><body>
<header><h1>Stage 90 — cierre de cobertura</h1>
<div class="muted">Raíces causales, fan-out y cola reproducible; no implementa servidor.</div></header>
<main><div id="summary" class="summary"></div>
<div class="toolbar"><input id="search" placeholder="buscar código, ámbito o acción">
<select id="lane"><option value="">todas las líneas</option></select>
<select id="category"><option value="">todas las categorías</option></select></div>
<div class="table"><table><thead><tr><th>#</th><th>Línea</th><th>Categoría</th>
<th>Raíz</th><th>Ámbito</th><th>Stage</th><th>Estado</th><th>Impacto</th>
<th>Puntaje</th><th>Siguiente evidencia</th></tr></thead><tbody id="rows"></tbody>
</table></div></main><script>
const data=__PAYLOAD__;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",
">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const summary=document.querySelector("#summary");
Object.entries(data.summary).forEach(([k,v])=>summary.insertAdjacentHTML("beforeend",
`<div class="card"><b>${esc(v)}</b>${esc(k)}</div>`));
for(const [id,field] of [["lane","lane"],["category","category"]]){
 const values=[...new Set(data.queue.map(x=>x[field]))].sort();
 const select=document.querySelector("#"+id);
 values.forEach(v=>select.insertAdjacentHTML("beforeend",`<option>${esc(v)}</option>`));
}
function render(){
 const q=document.querySelector("#search").value.toLowerCase();
 const lane=document.querySelector("#lane").value;
 const category=document.querySelector("#category").value;
 const rows=data.queue.filter(x=>(!lane||x.lane===lane)&&
  (!category||x.category===category)&&(!q||JSON.stringify(x).toLowerCase().includes(q)));
 document.querySelector("#rows").innerHTML=rows.map(x=>`<tr class="${x.status==="deferred"?"deferred":""}">
 <td class="rank">${x.rank}</td><td>${esc(x.lane)}</td><td>${esc(x.category)}</td>
 <td><code>${esc(x.root_code)}</code></td><td>${esc(x.scope_kind)}: ${esc(x.scope_value)}</td>
 <td>${x.owner_stage}</td><td>${esc(x.state)}</td><td class="score">${x.fanout_score}</td>
 <td class="score">${x.priority_score}</td><td>${esc(x.next_action)}</td></tr>`).join("");
}
document.querySelectorAll("input,select").forEach(e=>e.addEventListener("input",render));
render();
</script></body></html>"""


def _closure_payload(connection: sqlite3.Connection) -> dict[str, Any]:
    queue = [
        dict(row)
        for row in connection.execute(
            """
            SELECT q.rank,q.lane,q.owner_stage,q.status,q.priority_score,
                   q.effort_score,q.fanout_score,q.next_action,
                   r.root_code,r.category,r.scope_kind,r.scope_value,r.state,
                   r.disposition,r.gap_count,r.opaque_count,r.coverage_count,
                   r.query_count,r.consumer_count,r.relation_count,r.entity_count,
                   r.incoming_fanout,r.outgoing_fanout
            FROM work_queue q
            JOIN blocker_roots r ON r.blocker_root_key=q.blocker_root_key
            ORDER BY q.rank
            """
        )
    ]
    active = sum(1 for row in queue if row["status"] != "deferred")
    downstream = sum(
        int(row["gap_count"])
        for row in queue
        if row["disposition"] == "downstream_out_of_scope"
    )
    return {
        "summary": {
            "raíces causales": len(queue),
            "trabajo forense activo": active,
            "diferidas al servidor": len(queue) - active,
            "gaps downstream preservados": downstream,
        },
        "queue": queue,
    }


def _write_closure_csv(connection: sqlite3.Connection, path: Path) -> None:
    columns = (
        "rank", "lane", "owner_stage", "status", "priority_score",
        "effort_score", "fanout_score", "root_code", "category",
        "scope_kind", "scope_value", "state", "disposition", "gap_count",
        "opaque_count", "coverage_count", "query_count", "consumer_count",
        "relation_count", "entity_count", "incoming_fanout",
        "outgoing_fanout", "next_action",
    )
    rows = connection.execute(
        """
        SELECT q.rank,q.lane,q.owner_stage,q.status,q.priority_score,
               q.effort_score,q.fanout_score,r.root_code,r.category,
               r.scope_kind,r.scope_value,r.state,r.disposition,r.gap_count,
               r.opaque_count,r.coverage_count,r.query_count,r.consumer_count,
               r.relation_count,r.entity_count,r.incoming_fanout,
               r.outgoing_fanout,q.next_action
        FROM work_queue q
        JOIN blocker_roots r ON r.blocker_root_key=q.blocker_root_key
        ORDER BY q.rank
        """
    )
    handle, name = tempfile.mkstemp(
        prefix=".coverage-closure.", suffix=".csv", dir=path.parent
    )
    os.close(handle)
    temporary = Path(name)
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(columns)
            for row in rows:
                writer.writerow(tuple(row))
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


WORLD_INTERACTION_HTML_TEMPLATE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA8 Client Forensics — World Interactions</title>
<style>
:root{color-scheme:dark;--bg:#101418;--panel:#182027;--line:#2a3944;
--text:#e8f0f4;--muted:#91a6b2;--accent:#58c8b6;--warn:#f3c969}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 system-ui,sans-serif}header{padding:18px 22px;border-bottom:1px solid
var(--line);background:#121a20;position:sticky;top:0;z-index:2}h1{margin:0 0 4px;
font-size:22px}.muted{color:var(--muted)}main{display:grid;
grid-template-columns:minmax(600px,1.25fr) minmax(380px,.75fr);gap:16px;padding:16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;
overflow:hidden}.toolbar{padding:12px;border-bottom:1px solid var(--line)}
input{width:100%;background:#0f151a;color:var(--text);border:1px solid var(--line);
border-radius:6px;padding:9px}table{width:100%;border-collapse:collapse}
th,td{padding:8px 10px;border-bottom:1px solid #223039;text-align:left}
th{color:var(--muted);font-size:12px;position:sticky;top:0;background:var(--panel)}
tr.wi{cursor:pointer}tr.wi:hover{background:#203039}.yes{color:var(--accent)}
.unknown{color:var(--warn)}#rows{max-height:calc(100vh - 175px);overflow:auto}
#detail{padding:16px;max-height:calc(100vh - 105px);overflow:auto}
dl{display:grid;grid-template-columns:175px 1fr;gap:6px 10px}dt{color:var(--muted)}
dd{margin:0}pre{white-space:pre-wrap;word-break:break-word;background:#11181d;
padding:10px;border-radius:7px;border:1px solid var(--line)}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-top:9px}.stat{background:#1d2a31;
padding:6px 9px;border-radius:6px}@media(max-width:950px){main{grid-template-columns:1fr}
#detail,#rows{max-height:none}}
</style></head><body>
<header><h1>AA8 Client Forensics — World Interactions</h1>
<div class="muted">Kakao 8.0.3.12 r558734 · enum y relaciones nativas · no runtime</div>
<div class="stats" id="summary"></div></header>
<main><section class="panel"><div class="toolbar">
<input id="search" placeholder="Buscar ID, etiqueta o superficie"></div>
<div id="rows"><table><thead><tr><th>ID</th><th>Etiqueta nativa</th>
<th>wi_details</th><th>Referencias</th><th>Reconciliadas</th><th>Gaps activos</th>
</tr></thead><tbody id="body"></tbody></table></div></section>
<aside class="panel"><div id="detail"><span class="muted">Selecciona una interacción.
</span></div></aside></main><script>
const DATA=__PAYLOAD__;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({
'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
document.querySelector("#summary").innerHTML=Object.entries(DATA.summary).map(([k,v])=>
`<span class="stat"><b>${Number(v).toLocaleString("es-CL")}</b> ${esc(k)}</span>`).join("");
function detail(x){
 document.querySelector("#detail").innerHTML=`<h2>world_interaction:${esc(x.id)}</h2>
 <h3>${esc(x.label)}</h3><dl><dt>Estado</dt><dd>${esc(x.state)}</dd>
 <dt>Detalle opcional</dt><dd>${x.hasDetail?"sí":"no aplica"}</dd>
 <dt>apply_expert</dt><dd>${esc(x.detail.apply_expert)}</dd>
 <dt>distance_sqrt</dt><dd>${esc(x.detail.distance_sqrt)}</dd>
 <dt>lp</dt><dd>${esc(x.detail.lp)}</dd><dt>Referencias entrantes</dt>
 <dd>${x.incoming}</dd><dt>Reconciliaciones</dt><dd>${x.reconciledRelations}</dd>
 <dt>Gaps reconciliados</dt><dd>${x.reconciledGaps}</dd>
 <dt>Gaps fuente preservados</dt><dd>${x.sourceGaps}</dd>
 <dt>Gaps activos</dt><dd>${x.activeGaps}</dd></dl>
 <h3>Relaciones por procedencia</h3><pre>${esc(JSON.stringify(x.sources,null,2))}</pre>
 <h3>Cobertura</h3><pre>${esc(JSON.stringify(x.coverage,null,2))}</pre>`;
}
function render(){
 const q=document.querySelector("#search").value.trim().toLowerCase();
 const rows=DATA.interactions.filter(x=>!q||String(x.id).includes(q)||
 x.label.toLowerCase().includes(q)||JSON.stringify(x.sources).toLowerCase().includes(q));
 document.querySelector("#body").innerHTML=rows.map((x,i)=>`<tr class="wi" data-i="${i}">
 <td>${x.id}</td><td>${esc(x.label)}</td><td class="${x.hasDetail?"yes":""}">
 ${x.hasDetail?"sí":"—"}</td><td>${x.incoming}</td><td>${x.reconciledRelations}</td>
 <td class="${x.activeGaps?"unknown":""}">${x.activeGaps}</td></tr>`).join("");
 document.querySelectorAll("tr.wi").forEach(row=>row.onclick=()=>detail(rows[+row.dataset.i]));
}
document.querySelector("#search").addEventListener("input",render);render();
</script></body></html>"""


def _world_interaction_payload(
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    properties: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in connection.execute(
        """
        SELECT entity_key,namespace,property_name,value_type,value_text,
               value_integer,value_real,value_boolean,value_json
        FROM entity_properties
        WHERE entity_key LIKE 'world_interaction:%'
        ORDER BY entity_key,namespace,property_name,property_key
        """
    ):
        value_type = str(row["value_type"])
        value = (
            row["value_text"]
            if value_type == "text"
            else row["value_integer"]
            if value_type == "integer"
            else row["value_real"]
            if value_type == "real"
            else bool(row["value_boolean"])
            if value_type == "boolean"
            else json.loads(row["value_json"])
            if row["value_json"] is not None
            else None
        )
        properties[str(row["entity_key"])][
            f"{row['namespace']}.{row['property_name']}"
        ] = value

    incoming: Counter[str] = Counter()
    sources: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in connection.execute(
        """
        SELECT dst_entity_key,relation,state,locator,COUNT(*) AS row_count
        FROM relations
        WHERE dst_entity_key LIKE 'world_interaction:%'
        GROUP BY dst_entity_key,relation,state,
                 substr(locator,1,instr(locator,'[')-1)
        ORDER BY dst_entity_key,relation,state,locator
        """
    ):
        key = str(row["dst_entity_key"])
        count = int(row["row_count"])
        incoming[key] += count
        locator = str(row["locator"] or "")
        surface = locator.split("[", 1)[0] or "unknown"
        source_key = f"{surface}.{row['relation']} [{row['state']}]"
        sources[key][source_key] += count

    active_gaps = Counter(
        {
            str(row["entity_key"]): int(row["row_count"])
            for row in connection.execute(
                """
                SELECT entity_key,COUNT(*) AS row_count FROM gaps
                WHERE entity_key LIKE 'world_interaction:%'
                GROUP BY entity_key
                """
            )
        }
    )
    reconciled_relations = Counter(
        {
            str(row["entity_key"]): int(row["row_count"])
            for row in connection.execute(
                """
                SELECT json_extract(record_json,'$.entity_key') AS entity_key,
                       COUNT(*) AS row_count
                FROM source_records
                WHERE source_table='cross_stage_relation_reconciliations'
                  AND json_extract(record_json,'$.entity_key')
                      LIKE 'world_interaction:%'
                GROUP BY entity_key
                """
            )
        }
    )
    reconciled_gaps = Counter(
        {
            str(row["entity_key"]): int(row["row_count"])
            for row in connection.execute(
                """
                SELECT json_extract(record_json,'$.entity_key') AS entity_key,
                       COUNT(*) AS row_count
                FROM source_records
                WHERE source_table='cross_stage_gap_reconciliations'
                  AND json_extract(record_json,'$.entity_key')
                      LIKE 'world_interaction:%'
                GROUP BY entity_key
                """
            )
        }
    )
    coverage: dict[str, dict[str, str]] = defaultdict(dict)
    for row in connection.execute(
        """
        SELECT scope_key,dimension,state FROM coverage
        WHERE scope_key LIKE 'world_interaction:%'
        ORDER BY scope_key,dimension,coverage_key
        """
    ):
        coverage[str(row["scope_key"])][str(row["dimension"])] = str(
            row["state"]
        )

    interactions = []
    for row in connection.execute(
        """
        SELECT entity_key,native_id,state,lifecycle FROM entities
        WHERE kind='world_interaction'
        ORDER BY CAST(native_id AS INTEGER),native_id
        """
    ):
        key = str(row["entity_key"])
        values = properties.get(key, {})
        interactions.append(
            {
                "id": int(row["native_id"]),
                "label": str(
                    values.get(
                        "world_interaction.enum.semantic_label", ""
                    )
                ),
                "state": str(row["state"]),
                "lifecycle": str(row["lifecycle"]),
                "hasDetail": bool(
                    values.get(
                        "world_interaction.enum.has_wi_detail", False
                    )
                ),
                "detail": {
                    name: values.get(f"wi_details.{name}")
                    for name in ("apply_expert", "distance_sqrt", "lp")
                },
                "incoming": incoming[key],
                "reconciledRelations": reconciled_relations[key],
                "reconciledGaps": reconciled_gaps[key],
                "sourceGaps": active_gaps[key],
                "activeGaps": max(
                    0, active_gaps[key] - reconciled_gaps[key]
                ),
                "sources": dict(sorted(sources[key].items())),
                "coverage": coverage.get(key, {}),
            }
        )
    if len(interactions) != 105:
        raise RuntimeError(
            f"Expected 105 world interactions in viewer, got "
            f"{len(interactions)}"
        )
    if any(not row["label"] for row in interactions):
        raise RuntimeError("A world interaction is missing its native label")
    return {
        "summary": {
            "interacciones válidas": len(interactions),
            "filas wi_details": sum(row["hasDetail"] for row in interactions),
            "referencias entrantes": sum(incoming.values()),
            "relaciones reconciliadas": sum(reconciled_relations.values()),
            "gaps reconciliados": sum(reconciled_gaps.values()),
            "blocker roots activos": int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM blocker_roots
                    WHERE scope_kind='world_interaction'
                       OR scope_value LIKE 'world_interaction:%'
                    """
                ).fetchone()[0]
            ),
        },
        "interactions": interactions,
    }


def generate_static_viewer(database: Path, output_dir: Path) -> dict[str, Any]:
    connection = open_read_only(database)
    try:
        payload = _skill_payload(connection)
        viewer = output_dir / "viewer-skills.html"
        text = HTML_TEMPLATE.format(
            payload=canonical_json(payload).replace("</", "<\\/")
        )
        atomic_text(viewer, text)
        asset_payload = _asset_payload(connection)
        asset_viewer = output_dir / "viewer-assets.html"
        asset_text = ASSET_HTML_TEMPLATE.format(
            payload=canonical_json(asset_payload).replace("</", "<\\/")
        )
        atomic_text(asset_viewer, asset_text)
        wiki_payload = _wiki_payload(connection)
        wiki_viewer = output_dir / "viewer-wiki.html"
        wiki_text = WIKI_HTML_TEMPLATE.format(
            payload=canonical_json(wiki_payload).replace("</", "<\\/")
        )
        atomic_text(wiki_viewer, wiki_text)
        gaps = output_dir / "gaps-priority.csv"
        _write_gap_csv(connection, gaps)
        closure_payload = _closure_payload(connection)
        closure_viewer = output_dir / "viewer-coverage-closure.html"
        atomic_text(
            closure_viewer,
            CLOSURE_HTML_TEMPLATE.replace(
                "__PAYLOAD__",
                canonical_json(closure_payload).replace("</", "<\\/"),
            ),
        )
        closure_csv = output_dir / "coverage-closure-work-queue.csv"
        _write_closure_csv(connection, closure_csv)
        world_interaction_payload = _world_interaction_payload(connection)
        world_interaction_viewer = (
            output_dir / "viewer-world-interactions.html"
        )
        atomic_text(
            world_interaction_viewer,
            WORLD_INTERACTION_HTML_TEMPLATE.replace(
                "__PAYLOAD__",
                canonical_json(world_interaction_payload).replace(
                    "</", "<\\/"
                ),
            ),
        )
    finally:
        connection.close()
    return {
        "viewer_skills": {
            "path": viewer.resolve().as_posix(),
            "bytes": viewer.stat().st_size,
            "sha256": sha256_file(viewer),
            "entities": len(payload["skills"]),
        },
        "viewer_assets": {
            "path": asset_viewer.resolve().as_posix(),
            "bytes": asset_viewer.stat().st_size,
            "sha256": sha256_file(asset_viewer),
            "entities": len(asset_payload["icons"]),
        },
        "viewer_wiki": {
            "path": wiki_viewer.resolve().as_posix(),
            "bytes": wiki_viewer.stat().st_size,
            "sha256": sha256_file(wiki_viewer),
            "entities": len(wiki_payload["entities"]),
        },
        "gaps_priority": {
            "path": gaps.resolve().as_posix(),
            "bytes": gaps.stat().st_size,
            "sha256": sha256_file(gaps),
        },
        "viewer_coverage_closure": {
            "path": closure_viewer.resolve().as_posix(),
            "bytes": closure_viewer.stat().st_size,
            "sha256": sha256_file(closure_viewer),
            "roots": len(closure_payload["queue"]),
        },
        "coverage_closure_work_queue": {
            "path": closure_csv.resolve().as_posix(),
            "bytes": closure_csv.stat().st_size,
            "sha256": sha256_file(closure_csv),
        },
        "viewer_world_interactions": {
            "path": world_interaction_viewer.resolve().as_posix(),
            "bytes": world_interaction_viewer.stat().st_size,
            "sha256": sha256_file(world_interaction_viewer),
            "entities": len(world_interaction_payload["interactions"]),
        },
    }
