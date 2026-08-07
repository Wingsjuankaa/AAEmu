# Handoff — construir `nuia-story-quest-graph-v1.sqlite3`

Fecha de preparación: 2026-07-31  
Cliente fijado: ArcheAge Kakao `8.0.3.12 r558734`  
Tipo de trabajo: forense, reproducible y sin mutaciones de servidor

## Instrucción para el chat ejecutor

Usar obligatoriamente:

```text
$aa8-client-forensics
```

Leer este documento completo antes de actuar y continuar hasta cumplir la
definición de terminado. Esta frontera fue solicitada para que el equipo que
reconstruye AAEmu disponga de un mapa preventivo de toda la historia Nuian y
pueda probar y reparar la cadena en orden, en lugar de descubrir cada brecha
solamente al jugarla.

El trabajo ordinario pendiente en `current-forensic-state.md`
(`LoadItemGradeOrder`) queda aplazado para este chat por esta solicitud
explícita. No debe marcarse como cerrado ni eliminarse de la cola.

No usar `aaemu8-native-reconstruction` para implementar, importar o desplegar
nada. Esta tarea sólo produce evidencia forense y artefactos consultables.

## Prompt corto para iniciar el otro chat

```text
Usa $aa8-client-forensics. Lee completo
D:\Proyectos\AAemu\rama_8\reconstruccion_cliente_8\HANDOFF_NUIA_STORY_QUEST_GRAPH_V1.md
y ejecuta la frontera hasta cumplir todos sus gates. No modifiques AAEmu,
.env, MySQL, Docker, compacts runtime ni servicios activos.
```

## Objetivo

Construir:

```text
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1.sqlite3
```

La base debe responder, con procedencia y estado explícitos:

1. cuáles son todas las quests que el cliente AA8 clasifica como historia
   racial Nuian;
2. por qué cada quest pertenece o no pertenece al arco;
3. capítulos, índices, zonas, niveles y orden nativo disponible;
4. qué sucesiones son explícitas, cuáles son solamente candidatas derivadas
   del orden y cuáles están corroboradas por la wiki;
5. dónde hay ramas, convergencias, comienzos, finales o saltos de capítulo no
   demostrados;
6. todos los componentes y acts de cada quest, sin reducirlos a los items de
   recompensa;
7. NPC, doodad, sphere u otro endpoint de aceptación y reporte;
8. items suministrados, requeridos, reunidos, usados, retirados y entregados
   como recompensa;
9. skills, buffs, effects, plots, animaciones, FX y sonidos alcanzables desde
   la quest, sus componentes, doodads e items;
10. estado de clausura nativa de cada dependencia;
11. relación visible de la wiki: quest anterior requerida, quests abiertas,
    actores, objetivos, items y recompensas;
12. conflictos, tombstones, dependencias ausentes y blockers que conviene
    auditar antes de probar una quest en AAEmu;
13. una secuencia de prueba sugerida que preserve la evidencia y marque puntos
    de detención, sin afirmar que el runtime está reparado.

La SQLite no decide qué se habilita en AAEmu. Describe el cliente, las
relaciones corroborativas y una cola de auditoría downstream.

## Pregunta de alcance que debe quedar probada

La raíz nativa observada es:

```text
quest_contexts.category_id = 3
quest_categories[3].name   = [종족 퀘스트] 누이안
quest_contexts.race        = 1
```

La traducción descriptiva compatible es `[Race Quest] Nuian`. No seleccionar
quests por color de marcador, nombre parecido, continente, zona o proximidad
de ID.

El constructor debe recalcular esta raíz desde Stage 40. También debe auditar:

- cualquier relación nativa explícita que entre o salga del conjunto;
- cualquier enlace wiki de requisito o acceso que entre o salga del conjunto;
- quests con la misma categoría pero otra raza;
- quests con `race=1` fuera de la categoría 3;
- candidatos adyacentes encontrados por relaciones, no sólo por ordinal.

Los candidatos externos se guardan en `scope_boundary_candidates`. No se
incorporan al arco principal sin evidencia nativa suficiente. El resultado
debe poder afirmar con precisión “las quests racialmente Nuian declaradas por
este cliente” y no la formulación más amplia e indemostrada “toda quest que
ocurre en Nuia”.

## Separación de autoridad

Orden obligatorio:

```text
Stage 40
  -> autoridad para identidad de quest, categoría, raza, capítulo, índice,
     componentes, acts, endpoints y relaciones quest-side

Stage 20 / Stage 30 / Stage 50 / Stage 60 + consolidada
  -> autoridad para clausura de item, NPC, doodad, skill, buff, effect,
     plot, assets y localización

quest-item-crosswalk-v1.sqlite3
  -> derivado forense ya cerrado para grants quest -> item y comparación wiki

Stage 70 + cache wiki compatible
  -> corroboración visible de nombres, predecesores, sucesores, objetivos,
     actores, items y recompensas

AAEmu/runtime
  -> fuera del alcance de esta tarea
```

Reglas:

- La wiki nunca crea ni reemplaza una relación nativa.
- `chapter_idx` + `quest_idx` demuestran un orden editorial nativo, pero no
  por sí solos una arista ejecutable de prerrequisito.
- Un enlace wiki coincidente eleva una arista derivada a `corroborated_order`,
  no a `confirmed_native_dependency`.
- No interpretar `successive=1` sin cerrar su consumer.
- No tratar `QuestActObjCompleteQuest` automáticamente como prerrequisito de
  aceptación; puede ser un objetivo dentro de la quest.
- No colapsar `AcceptDoodad` o `ReportDoodad` a NPC por similitud visual.
- No usar compact 3.0, `develop`, datos históricos o nombres parecidos para
  completar huecos.
- Conservar `unknown`, `blocked`, `missing`, `tombstone` y `opaque`.
- No materializar en runtime ninguna entidad ausente.

## Límites estrictos

Este trabajo puede modificar únicamente:

```text
reconstruccion_cliente_8/client_forensics/**
reconstruccion_cliente_8/config/**
reconstruccion_cliente_8/generated/**
reconstruccion_cliente_8/CHECKPOINT_NUIA_STORY_QUEST_GRAPH_V1.md
reconstruccion_cliente_8/README.md
skill state/checkpoint forense, cuando corresponda
E:\AAEmu-Research\output\aa8-client-forensics/**
```

No modificar:

```text
AAEmu.Game
AAEmu.Login
AAEmu.Tests
.env
MySQL
Docker
client_kakao/compact-8.0-runtime-*.sqlite3
ningún servicio, personaje o quest activa
```

No desplegar, reiniciar, conectarse para probar ni avanzar quests.

## Estado de entrada verificado

Recalcular hashes al iniciar. Si otra frontera produjo artefactos más nuevos,
usar los vigentes y registrar su linaje; no restaurar ni sobrescribir etapas.

```text
Stage 20:
E:\AAEmu-Research\output\aa8-client-forensics\stage-20-items.sqlite
bytes=2213568512
sha256=1274D10712A913A667364B7B75C47F1DE12013AE77AA7CF41E79F138F3FC979E

Stage 30:
E:\AAEmu-Research\output\aa8-client-forensics\stage-30-world-actors.sqlite
bytes=1209929728
sha256=D9696D2B5048C9103928E98D94C927474E97F9ADC45D664AC9AAEC3C7FA3CD11

Stage 40:
E:\AAEmu-Research\output\aa8-client-forensics\stage-40-quests.sqlite
bytes=1095278592
sha256=0BB127E819232BFEE6D6559000E845B8C36E7F4C56A5ED64234DCD28B793D72C

Stage 50:
E:\AAEmu-Research\output\aa8-client-forensics\stage-50-skills.sqlite
bytes=2240180224
sha256=B15853F5E1D24FC9FAF77C9F4F1697262F32525E6CCDE4EC96D943DD938E9E07

Stage 60:
E:\AAEmu-Research\output\aa8-client-forensics\stage-60-assets.sqlite
bytes=768770048
sha256=423E8872C8AAAEFA46ABB0E04FB299A17F56722ECDCDF97C2888F7AC9061AB02

Stage 70:
E:\AAEmu-Research\output\aa8-client-forensics\stage-70-wiki.sqlite
bytes=268619776
sha256=21EC69E96CCA23D5BB222C3FDF6831014EBD45F0A66DC05A258E7753A8754106

Stage 90:
E:\AAEmu-Research\output\aa8-client-forensics\stage-90-coverage-closure.sqlite
bytes=294944768
sha256=AD00E6EA28A26AFE62BD59A9E64887AFA2016D98D5C55642E8A135B343B63E6A

Consolidada:
E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite
bytes=8905900032
sha256=AFFAA4316DBD0F4F7170FB30CE999805305C644B2AEEA088157A607B41ED201F

Quest/item crosswalk cerrado:
E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1.sqlite3
bytes=34091008
sha256=38E5CE75C90B0E64367A69E182E301B844E0904628CA726442F2D08A8DD34709

Manifest global:
sha256=1C8CC081EA0F17B3D62DFBF415099E9246C405868A77144F179C602963F1B43E
tool_version=0.36.0
schema_version=4
```

## Censo nativo de referencia

Estos conteos se midieron en modo read-only y sirven como barrera contra
pérdida silenciosa. Deben recalcularse, no hardcodearse.

```text
quests category_id=3, race=1: 55
components:                    222
acts:                          344

capítulos:
  chapter 0:  1
  chapter 1:  6
  chapter 2: 11
  chapter 3:  8
  chapter 4:  9
  chapter 5:  6
  chapter 6: 14

zonas:
  zone 2:    8
  zone 7:    5
  zone 9:    7
  zone 10:   6
  zone 11:   7
  zone 15:   6
  zone 124:  6
  zone 125:  5
  zone 131:  3
  zone 141:  2

niveles nativos: 1..28
```

Distribución exacta de acts del conjunto:

```text
QuestActSupplyItem              120
QuestActSupplyExp                55
QuestActConReportNpc             40
QuestActConAcceptNpc             39
QuestActObjItemGather            17
QuestActConAcceptDoodad          15
QuestActConReportDoodad          13
QuestActSupplyCopper             11
QuestActSupplySelectiveItem      10
QuestActObjItemUse                9
QuestActObjTalk                   4
QuestActObjInteraction            3
QuestActConAutoComplete           2
QuestActObjMonsterHunt            2
QuestActConAcceptSphere           1
QuestActObjCinema                 1
QuestActObjMonsterGroupHunt       1
QuestActObjSphere                 1
```

El crosswalk ya cerrado contiene para este conjunto:

```text
grants quest -> item:       130
quests con grants:           54
item IDs distintos:          52

initial_supply fixed:        21
other_native_stage fixed:     1
reward fixed:                98
reward selective:            10

items por closure_state:
  dependency_closure_unknown: 23
  tombstone:                  22
  complete_native_closure:     7
```

No reconstruir el crosswalk completo. Consumirlo y ampliar solamente los
roles no cubiertos, especialmente `ObjItemGather`, `ObjItemUse`, condiciones,
remociones, interacciones y cadenas item -> skill/effect/buff.

## Lista ancla de las 55 quests

El orden listado es `(chapter_idx, quest_idx)`, no una afirmación automática
de prerrequisito ejecutable.

```text
chapter 0:
  6839

chapter 1:
  330, 2531, 2532, 2255, 2256, 2257

chapter 2:
  2258, 2259, 2260, 1525, 2263, 2261, 3503, 2262, 2264, 2265, 2266

chapter 3:
  2485, 4393, 2486, 3573, 2488, 2489, 4394, 4396

chapter 4:
  2490, 2491, 1424, 2492, 4397, 2494, 2495, 2496, 4398

chapter 5:
  2498, 3985, 3986, 4399, 4400, 3987

chapter 6:
  4402, 4403, 4404, 3988, 3989, 4405, 4406, 4407,
  3990, 3991, 4409, 4410, 3993, 4411
```

Si el conjunto recalculado difiere, detener el build, explicar qué entrada o
decoder cambió y actualizar baselines con evidencia.

## Reconstrucción del orden

Construir tres capas separadas.

### Capa A — hechos nativos

Conservar por quest:

```text
category_id
race
chapter_idx
quest_idx
zone_id
level/min_level/max_level
successive
repeatable
priority
degree/grade/detail
```

Buscar relaciones explícitas de dependencia/sucesión en:

```text
quest_contexts
quest_components
quest_acts y sus detalles concretos
quest_context_groups / quest_context_group_members
consumers/loaders nativos aplicables
relaciones consolidadas y dossiers existentes
```

No promover una relación por compartir NPC, zona o nombre.

### Capa B — candidatos de orden derivados

Generar candidatos deterministas entre vecinos de
`(chapter_idx, quest_idx)`, guardando:

```text
derivation_algorithm
source fields
same_chapter
boundary_reason
confidence
```

Los cinco saltos visibles entre chapters 1..6 y el posible enlace de chapter
0 deben quedar como fronteras independientes hasta hallar evidencia.

### Capa C — corroboración wiki

Parsear estructuralmente:

```text
Requires precompleted quest
Opens access to
```

Cada enlace conserva quest origen, quest destino, encabezado, ordinal, href,
texto visible, response SHA-256, parser version y contexto estructural.

El cache actual tiene 54/55 páginas detalladas con HTTP 200. Falta solamente:

```text
quest 6839
```

Stage 70 sí contiene su identidad de catálogo con HTTP 200 y `match`. Congelar
su detalle mediante el crawler cache-first; no volver a descargar las otras
54 páginas si hashes y metadata son válidos.

El cache existente demuestra 48 pares intrachapter recíprocos:

```text
A: Opens access to B
B: Requires precompleted quest A
```

No hay todavía enlace visible congelado entre los capítulos 1→2, 2→3, 3→4,
4→5 y 5→6. Preservar esta ausencia; no inventar esos cinco bordes. La página
6839 puede aportar o no el borde chapter 0→1 y debe clasificarse según lo que
realmente publique.

## Clausura completa por quest

Para cada una de las 55 quests, recorrer:

```text
quest_context
  -> quest_component
  -> quest_act
  -> concrete act detail
  -> NPC / doodad / sphere / alias / monster group / cinema
  -> item / item group / grade / cleanup flags
  -> item use_skill / buff / craft / loot / descriptor
  -> skill
  -> effect
  -> buff / plot / projectile / animation / FX / sound
  -> asset y localización alcanzables
```

No detenerse en el primer endpoint. Cada referencia debe terminar en entidad,
tombstone, dependencia externa, missing u opaque documentado.

Roles de item mínimos:

```text
initial_supply
fixed_reward
selective_reward
ranked_reward
result_ranked_reward
objective_gather
objective_use
accept_requirement
accept_item_gain
remove_or_cleanup
doodad_or_interaction_product
other_native_role
```

Conservar cantidad, grado, alias, flags de cleanup/drop/destroy, highlight
doodad/phase, show_action_bar, try_equip y cualquier consumer aplicable.

## Endpoints NPC y doodad

No presentar solamente el nombre visible. Para cada aceptación y reporte:

```text
act type + detail ID
npc_id / doodad_id / sphere_id
actor entity lifecycle
spawn o ausencia de spawn
client_doodad
doodad func groups / funcs / quest funcs
model o npctype proxy
localización y zona
closure_state
```

Un doodad lógico respaldado por `npctype://...` sigue siendo doodad.

## Casos ancla obligatorios

### Raíz y orden

- `quest:330` abre visiblemente `quest:2531`.
- `quest:2531` requiere 330 y abre 2532.
- `quest:2265` requiere 2264 y abre 2266.
- Los 48 enlaces intrachapter conocidos deben ser recíprocos.
- Los saltos de capítulo deben conservar su estado no demostrado.

### Quest 2532 — endpoint lógico

Preservar exactamente:

```text
component 10966
QuestActConReportDoodad detail 163
doodad 14074
client_doodad = 1
doodad func group 41496
model = npctype://10581
doodad func 38378
DoodadFuncQuest 1508
quest_kind_id = 2
quest_id = 2532
```

No convertirlo en `ReportNpc 10581`.

### Quest 2264

Cerrar el objeto de objetivo `24967`, el doodad/interacción que lo produce y
el grant/reward correspondiente. Conservar cualquier tombstone como tal.

### Quest 2265

Preservar:

```text
initial supply item 21604 x1
fixed reward item 23633 x1
fixed reward item 34000 x5
wiki previous 2264
wiki next 2266
```

Seguir `item:34000 -> skill:35238 -> effects/buffs` sin asumir comportamiento
de servidor.

### Quest 2258

Mantener la regresión del parser ya cerrada:

```text
item 16288 -> quest_item
item 23633 -> fixed_reward
```

No deben reaparecer `accept_from` o `report_to` como roles de item.

### Quest 330

Conservar recompensas fijas y selectivas con multiplicidad y ordinal. No
deduplicar solamente por `(quest_id,item_id)`.

## Esquema mínimo de salida

Puede ampliarse, pero no reducirse conceptualmente:

```sql
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);

CREATE TABLE source_artifacts (
    artifact_key TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    path TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    authority TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE story_quests (
    quest_id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL,
    race INTEGER NOT NULL,
    chapter_idx INTEGER NOT NULL,
    quest_idx INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    native_name TEXT,
    visible_name TEXT,
    membership_state TEXT NOT NULL,
    native_state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE scope_boundary_candidates (
    candidate_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    direction TEXT NOT NULL,
    reason TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE story_order_edges (
    edge_key TEXT PRIMARY KEY,
    src_quest_id INTEGER NOT NULL,
    dst_quest_id INTEGER NOT NULL,
    edge_kind TEXT NOT NULL,
    native_edge_state TEXT NOT NULL,
    ordinal_state TEXT NOT NULL,
    wiki_requires_state TEXT NOT NULL,
    wiki_opens_state TEXT NOT NULL,
    reciprocal_state TEXT NOT NULL,
    overall_state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE story_quest_components (
    component_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    component_kind_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    row_json TEXT NOT NULL,
    native_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE story_quest_acts (
    act_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    quest_act_id INTEGER NOT NULL,
    act_detail_type TEXT NOT NULL,
    act_detail_id INTEGER NOT NULL,
    detail_row_json TEXT,
    closure_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE story_quest_endpoints (
    endpoint_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    phase TEXT NOT NULL,
    endpoint_kind TEXT NOT NULL,
    endpoint_id INTEGER NOT NULL,
    act_detail_type TEXT NOT NULL,
    act_detail_id INTEGER NOT NULL,
    client_doodad INTEGER,
    proxy_npc_id INTEGER,
    spawn_state TEXT NOT NULL,
    closure_state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE story_quest_items (
    relation_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    quest_act_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    item_role TEXT NOT NULL,
    selection_mode TEXT NOT NULL,
    count INTEGER,
    grade_id INTEGER,
    flags_json TEXT NOT NULL,
    native_relation_state TEXT NOT NULL,
    item_closure_state TEXT NOT NULL,
    crosswalk_state TEXT,
    evidence_json TEXT NOT NULL
);

CREATE TABLE story_dependency_closure (
    closure_key TEXT PRIMARY KEY,
    root_quest_id INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    src_entity_key TEXT NOT NULL,
    relation TEXT NOT NULL,
    dst_entity_key TEXT NOT NULL,
    dst_state TEXT NOT NULL,
    required INTEGER NOT NULL,
    closure_state TEXT NOT NULL,
    blocker_root TEXT,
    evidence_json TEXT NOT NULL
);

CREATE TABLE wiki_story_pages (
    quest_id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_sha256 TEXT,
    detail_state TEXT NOT NULL,
    parser_version TEXT,
    evidence_json TEXT NOT NULL
);

CREATE TABLE wiki_story_edges (
    wiki_edge_key TEXT PRIMARY KEY,
    src_quest_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    dst_quest_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    label TEXT,
    href TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    parse_state TEXT NOT NULL,
    context_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE downstream_audit_queue (
    audit_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    chapter_idx INTEGER NOT NULL,
    quest_idx INTEGER NOT NULL,
    blocker_kind TEXT NOT NULL,
    blocked_entity_key TEXT,
    severity TEXT NOT NULL,
    recommended_stop_point TEXT NOT NULL,
    state TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE validation_events (
    validation_key TEXT PRIMARY KEY,
    check_name TEXT NOT NULL,
    state TEXT NOT NULL,
    expected_json TEXT,
    actual_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);
```

Crear índices al menos por:

```text
story_quests(chapter_idx, quest_idx)
story_quests(zone_id, level)
story_order_edges(src_quest_id)
story_order_edges(dst_quest_id)
story_order_edges(overall_state)
story_quest_components(quest_id, component_kind_id)
story_quest_acts(quest_id, act_detail_type)
story_quest_endpoints(quest_id, phase)
story_quest_endpoints(endpoint_kind, endpoint_id)
story_quest_items(quest_id, item_role)
story_quest_items(item_id)
story_dependency_closure(root_quest_id, depth)
story_dependency_closure(dst_entity_key, closure_state)
wiki_story_edges(src_quest_id, relation)
downstream_audit_queue(chapter_idx, quest_idx, severity)
```

## Vocabularios cerrados mínimos

`story_order_edges.overall_state`:

```text
confirmed_native_dependency
corroborated_order
native_ordinal_candidate
wiki_only
conflict
ambiguous
chapter_boundary_unresolved
blocked
```

`closure_state`:

```text
complete_native_closure
tombstone
missing
unknown
opaque
blocked
not_applicable
```

`membership_state`:

```text
confirmed_native_nuian_story
external_candidate
excluded_native
ambiguous
```

No introducir un estado `runtime_ready` ni una columna `enabled`.

## Adquisición wiki requerida

Usar la ruta canónica:

```text
https://wiki.archerage.to/na-en/db/quests/{quest_id}
```

Requisitos:

- cache-first, reanudable y bajo el lock existente;
- respetar `robots.txt` y el delay configurado;
- validar los 54 snapshots actuales antes de reutilizarlos;
- descargar solamente 6839 y cualquier candidato externo justificado;
- guardar HTML, metadata, status, content type, bytes, SHA-256, URL y parser;
- escritura atómica;
- clasificar 200, 404/410, redirect, transient y parse failure;
- no confundir ausencia de catálogo con HTTP 404;
- parser estructural por encabezado/DOM, no ventana de texto cercana;
- mantener los datos wiki en namespace separado.

## Salidas adicionales

Además de la SQLite:

```text
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1.manifest.json
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1-summary.json
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1-gaps.csv
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-test-order-v1.csv
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1.html
```

El CSV de prueba debe ordenar por capítulo/índice, mostrar blockers y proponer
un punto de detención después de aceptación, objetivo o reporte según la
dependencia afectada. Es una guía downstream, no una prueba del runtime.

El visor HTML estático debe permitir:

- navegar el grafo y la lista tabular;
- filtrar por chapter, zone, level, quest, act type y closure state;
- distinguir visualmente aristas nativas, derivadas y wiki;
- inspeccionar procedencia y hashes;
- expandir items, skills, buffs, effects, NPCs y doodads;
- listar fronteras de capítulo, conflictos y blockers;
- funcionar sin CDN ni conexión de red.

Mantener código, tests y checkpoint en Git. Mantener SQLite, cache, HTML
masivo y exportaciones grandes fuera de Git.

## CLI sugerida

Integrar comandos equivalentes a:

```powershell
Set-Location D:\Proyectos\AAemu\rama_8\reconstruccion_cliente_8

python -B -m client_forensics freeze-nuia-story-wiki --resume
python -B -m client_forensics build-nuia-story-quest-graph
python -B -m client_forensics validate-nuia-story-quest-graph
```

Los nombres pueden ajustarse a la arquitectura existente. Registrar en el
manifest los comandos efectivos y sus versiones.

## Pruebas obligatorias

Agregar pruebas para:

- selección de raíz por categoría 3 y raza 1;
- exclusión de quests vecinas por ID, zona o nombre;
- conteos 55/222/344 y distribución por capítulos;
- conservación de los 18 tipos de act observados;
- orden por chapter/quest_idx sin promoverlo a dependencia explícita;
- parser wiki de `Requires precompleted quest` y `Opens access to`;
- reciprocidad y multiplicidad de enlaces;
- fronteras entre capítulos no inventadas;
- página 6839 presente, ausente, 404, transient y parse failure;
- caso 2532 sin convertir doodad 14074 en NPC;
- casos 2258, 2264, 2265 y 330;
- consumo del crosswalk sin reconstruirlo ni perder multiplicidad;
- `ObjItemGather` y `ObjItemUse` con flags completos;
- clausura item -> skill -> effect -> buff/plot;
- entidades tombstone preservadas;
- scope boundary candidates dentro y fuera del conjunto;
- cero componentes, acts, endpoints o item IDs descartados;
- generación determinista.

Ejecutar la suite completa de `client_forensics`, no sólo las pruebas nuevas.

## Gates de aceptación

No declarar terminado hasta cumplir todo:

```text
[ ] raíz recalculada desde Stage 40
[ ] category 3 se identifica nativamente como Nuian race quest
[ ] 55 quests preservadas
[ ] 222 components preservados
[ ] 344 acts preservados
[ ] distribución de chapters 1/6/11/8/9/6/14 preservada
[ ] los 18 tipos de act y sus conteos cuadran
[ ] 130 grants del crosswalk enlazados sin duplicación ni pérdida
[ ] 17 ObjItemGather y 9 ObjItemUse cerrados
[ ] cada endpoint NPC/doodad/sphere tiene estado de clausura
[ ] cada item alcanzado tiene estado de clausura
[ ] cada skill/buff/effect/plot alcanzado tiene estado terminal
[ ] 55 páginas wiki tienen estado terminal o error reproducible
[ ] los 54 snapshots existentes se reutilizan si son válidos
[ ] quest 6839 se congela cache-first
[ ] los 48 pares intrachapter conocidos permanecen recíprocos
[ ] fronteras de capítulo se conservan sin relaciones inventadas
[ ] candidatos externos se inventarían y no se mezclan silenciosamente
[ ] cero relaciones huérfanas no explicadas
[ ] cero filas descartadas silenciosamente
[ ] casos 2532, 2258, 2264, 2265 y 330 pasan
[ ] PRAGMA quick_check=ok
[ ] PRAGMA integrity_check=ok
[ ] dos builds producen SQLite y manifest con hashes idénticos
[ ] manifest registra hashes y versiones de todas las entradas
[ ] summary, gaps, test-order y visor se regeneran
[ ] etapas afectadas, Stage 90 y consolidada se reconstruyen dos veces
[ ] CHECKPOINT_NUIA_STORY_QUEST_GRAPH_V1.md queda actualizado
[ ] current-forensic-state.md queda actualizado con hashes y siguiente trabajo
[ ] scripts/status.ps1 pasa
[ ] scripts/validate_forensics_db.py pasa sobre la SQLite nueva
[ ] suite completa de client_forensics pasa
```

Si la descarga de 6839 o un candidato externo queda bloqueada por red, producir
un checkpoint reanudable y conservar el error reproducible. No declarar el
grafo completo mientras una entrada requerida siga transitoria.

## Entrega esperada al chat de reconstrucción

El artefacto debe permitir consultas como:

```sql
-- Orden de prueba Nuian por capítulo e índice, con la naturaleza de cada
-- arista y el primer blocker de clausura de la quest.

-- Quests que entregan o requieren items tombstone/incompletos y el momento
-- exacto: aceptación, objetivo, uso, reporte o recompensa.

-- Quests cuyo endpoint es un client_doodad lógico o carece de spawn cerrado.

-- Items de quest que activan skills y su clausura effect/buff/plot.

-- Diferencias entre orden editorial nativo y enlaces visibles de la wiki.

-- Próxima quest segura para auditar manualmente y punto exacto donde detenerse.
```

No incluir SQL que modifique AAEmu, inventarios, personajes o quests.

## Definición de terminado

La frontera queda cerrada únicamente cuando el cliente AA8 puede consultarse
como un grafo completo de las 55 quests racialmente Nuian, cada relación tiene
procedencia, cada dependencia alcanzada termina en un estado explícito, la
wiki sólo corrobora, las fronteras entre capítulos no están inventadas, las
salidas son reproducibles y el estado forense vigente apunta al siguiente
trabajo real.

