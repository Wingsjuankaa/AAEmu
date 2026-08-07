# Handoff — construir `quest-item-crosswalk-v1.sqlite3`

Fecha de preparación: 2026-07-31  
Cliente fijado: ArcheAge Kakao `8.0.3.12 r558734`  
Tipo de trabajo: forense, reproducible y sin mutaciones de servidor

## Instrucción para el chat ejecutor

Usar obligatoriamente:

```text
$aa8-client-forensics
```

Leer este documento completo y ejecutar el trabajo hasta cumplir la definición
de terminado. Esta frontera fue solicitada expresamente para que el equipo que
repara AAEmu pueda continuar probando quests mientras este índice se construye
en otro chat.

No usar `aaemu8-native-reconstruction` para implementar o desplegar nada en
este trabajo. La única responsabilidad es producir evidencia forense y una
SQLite derivada que pueda consumir posteriormente el equipo de reconstrucción.

## Objetivo

Construir:

```text
E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1.sqlite3
```

La base debe responder, con procedencia y estado explícitos:

1. qué quests AA8 entregan objetos;
2. en qué fase los entregan;
3. si son objetos fijos, selectivos, por rango o por resultado de rango;
4. item ID, cantidad, grado, rango y flags nativos aplicables;
5. qué página wiki corresponde al mismo `quest_id`;
6. qué objetos menciona visiblemente esa página y bajo qué sección;
7. si la relación nativa y la relación visible coinciden, faltan, divergen o
   siguen ambiguas;
8. si el item y su clausura de dependencias están presentes en el grafo
   forense AA8;
9. qué casos son candidatos seguros para una auditoría posterior del runtime.

La SQLite no debe decidir qué se activa en AAEmu. Debe describir evidencia,
brechas y candidatos; el equipo de reconstrucción tomará la decisión después.

## Separación de autoridad

Orden obligatorio:

```text
Stage 40 / filas nativas AA8
  -> autoridad para quest, component, act, tipo de grant, item y cantidad

Stage 20 + consolidada
  -> autoridad para identidad y clausura nativa del item

Stage 70 / wiki compatible
  -> corroboración visible de nombre, sección, cantidad y enlaces

runtime AAEmu
  -> comparación opcional server_observed; nunca autoridad cliente
```

Reglas:

- La wiki nunca crea ni reemplaza una relación nativa.
- Una coincidencia wiki eleva a `corroborated`, nunca a `confirmed_native`.
- Una ausencia wiki no invalida una fila nativa.
- Un objeto visto sólo en la wiki queda `wiki_only` y no se recomienda para
  importación.
- No usar compact 3.0, datos históricos, nombres parecidos ni `develop` para
  completar huecos.
- Conservar `unknown`, `blocked`, `missing`, `tombstone` y `opaque` sin
  convertirlos en valores supuestos.

## Límites estrictos

Este trabajo puede modificar únicamente:

```text
reconstruccion_cliente_8/client_forensics/**
reconstruccion_cliente_8/config/**
reconstruccion_cliente_8/generated/**
reconstruccion_cliente_8/CHECKPOINT_QUEST_ITEM_CROSSWALK_V1.md
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
ningún servicio activo
```

No desplegar ni reiniciar servicios. No avanzar, completar ni alterar quests
de personajes.

## Estado de entrada verificado

```text
Stage 40:
E:\AAEmu-Research\output\aa8-client-forensics\stage-40-quests.sqlite
bytes=1095278592
sha256=0BB127E819232BFEE6D6559000E845B8C36E7F4C56A5ED64234DCD28B793D72C

Stage 70:
E:\AAEmu-Research\output\aa8-client-forensics\stage-70-wiki.sqlite
bytes=252649472
sha256=CEA4BDE4949F292D791F6A9F1E5C1754640F93305FEA451BC1EAB0B5BB44DFDF

Consolidada:
E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite
sha256=9461C0DCAA69295567004DD5380D517F98E2E88CA37768F5129BBD592327E276
tool_version=0.35.0
schema_version=4
```

Recalcular todos los hashes al iniciar. Si cambiaron porque otro trabajo
forense avanzó, usar los artefactos vigentes y registrar el nuevo linaje; no
restaurar ni sobrescribir una etapa más nueva.

## Censo nativo de referencia

Los siguientes valores se midieron directamente desde `native_rows`
confirmadas de Stage 40. Son baselines para detectar pérdida silenciosa, no
valores para hardcodear si la entrada cambia:

```text
quest_contexts                                  7826
quest_components                              32191
quest_acts                                    42446
quest_act_supply_items                         5644 filas detalle
QuestActSupplyItem                             5640 acts enlazados
quests distintas con QuestActSupplyItem        4195

QuestActSupplyItem por component_kind_id:
  kind 1                                          6
  kind 2                                          1
  kind 3                                       1247
  kind 4                                         50
  kind 8                                       4336

kind 3, SupplyItem inicial:
  acts                                         1247
  quests distintas                             1147
  items distintos                              1162

QuestActSupplySelectiveItem:
  acts                                          552
  quests                                        189
  component_kind_id=8 en los 552

QuestActSupplyRankedItem:
  acts                                           23
  quests                                          7
  component_kind_id=8 en los 23

QuestActSupplyResultRankedItem:
  acts                                            5
  quests                                          2
  component_kind_id=8 en los 5

unión de quests con cualquiera de esos grants: 4293
```

Las cuatro filas detalle `quest_act_supply_items` sin act enlazado deben
conservarse en un inventario de huérfanos; no descartarlas ni contarlas como
grants activos.

## Estado wiki y problema que debe resolverse

Stage 70 contiene un catálogo wiki amplio, pero no el detalle necesario para
el cruce:

```text
wiki quest entities                            9680
quest pages con state=confirmed                8538
quest IDs confirmados que coinciden con AA8    7673
páginas de quest con HTML detallado               4
IDs detallados: 330, 2256, 2257, 2258
relaciones quest -> item extraídas                12
```

Para las 4293 quests nativas que entregan items:

```text
página presente en catálogo wiki               3739
match exacto de identidad nativa                3739
sin página confirmada en catálogo                554
```

La página de la quest 2260 está catalogada, pero no estaba congelada como
detalle. Por eso Stage 70 conoce la identidad `quest:2260` pero no su enlace
visible a `item:16260`.

El parser actual también usa una ventana de texto cercana al enlace. Esto ha
clasificado algunos rewards como `report_to` y un quest item como
`accept_from`. No usar `relation_hint` actual como semántica final.

## Adquisición wiki requerida

Congelar las páginas detalladas de la unión exacta de 4293 quests nativas con
grants de item.

URL canónica:

```text
https://wiki.archerage.to/na-en/db/quests/{quest_id}
```

Requisitos:

- respetar `robots.txt` y el delay mínimo de la herramienta;
- cache-first y reanudable;
- no volver a descargar una respuesta válida cuyo hash ya esté congelado;
- usar escritura atómica;
- guardar HTML, metadata, status HTTP, content type, bytes, SHA-256, URL,
  locale, parser version y fecha de captura sólo en metadata operacional;
- clasificar 200, 404/410, redirects, errores transitorios y parse failures;
- no interpretar ausencia de catálogo como HTTP 404;
- permitir `--resume` y progreso durable;
- no perder los cuatro detalles existentes;
- limitar el crawl a la lista nativa calculada, no a todos los IDs posibles.

Ruta sugerida del nuevo cache:

```text
E:\AAEmu-Research\output\aa8-client-forensics\stage70-wiki-cache\detail\na-en\quests\
```

Si el diseño actual exige otra ruta, documentarla y mantener linaje claro. No
mezclar silenciosamente respuestas nuevas con snapshots de otra versión.

## Parser wiki requerido

Reemplazar para esta frontera la heurística de seis tokens cercanos por una
representación estructural de la página.

Cada mención de item debe conservar al menos:

```text
quest_id
item_id
href
label visible
cantidad visible, si existe
sección superior
subsección o acción
posición/ordinal dentro de la sección
contexto normalizado
response_sha256
parser_version
parse_state
```

Secciones normalizadas mínimas:

```text
quest_item
fixed_reward
selective_reward
ranked_reward
objective_item
requirement_item
other_visible_item
unknown_section
```

No deduplicar solamente por `(kind,id)`: un mismo item puede aparecer en dos
roles distintos dentro de una quest. La identidad de una mención debe incluir
sección y ordinal.

Si la estructura HTML no permite distinguir una sección con certeza, usar
`unknown_section` y conservar fragmento/contexto; no inferirla por nombre.

## Extracción nativa requerida

Leer Stage 40 en modo read-only y reconstruir los joins desde `native_rows`:

```text
quest_contexts.id
  -> quest_components.quest_context_id
  -> quest_acts.quest_component_id
  -> act_detail_type + act_detail_id
  -> tabla concreta del grant
  -> item_id
```

Tipos incluidos en V1:

```text
QuestActSupplyItem
  -> quest_act_supply_items

QuestActSupplySelectiveItem
  -> quest_act_supply_selective_items

QuestActSupplyRankedItem
  -> quest_act_supply_ranked_items

QuestActSupplyResultRankedItem
  -> quest_act_supply_result_ranked_items
```

Conservar todos los campos disponibles de cada detalle. Campos comunes:

```text
item_id
count
grade_id
```

Campos particulares, si existen:

```text
rank
cleanup
destroy_when_drop
drop_when_destroy
show_action_bar
try_equip
```

Clasificación de fase permitida:

```text
component_kind_id=3 -> initial_supply
component_kind_id=8 -> reward
otros kind          -> other_native_stage
```

No inventar nombres para kinds 1, 2 o 4 en esta SQLite. Conservar el entero y
`other_native_stage` hasta que su consumer demuestre otra semántica.

Clasificación de selección:

```text
QuestActSupplyItem             -> fixed
QuestActSupplySelectiveItem    -> selective
QuestActSupplyRankedItem       -> ranked
QuestActSupplyResultRankedItem -> result_ranked
```

## Clausura del item

Cruzar cada `item_id` contra Stage 20 y la consolidada vigente. No depender de
un compact runtime para definir existencia nativa.

Guardar por item:

```text
entity_key
native lifecycle/state
descriptor/concrete type conocido
impl_id, cuando esté proyectado
use_skill_id
buff_id
craft_id
relaciones salientes requeridas
coverage de identidad, properties, relations y consumer
gaps y blocker roots aplicables
closure_state
```

Estados mínimos de `closure_state`:

```text
complete_native_closure
generic_dependency_free_candidate
dependency_closure_unknown
dependency_closure_missing
tombstone
native_item_missing
blocked
```

`generic_dependency_free_candidate` es una clasificación forense para que el
equipo de servidor audite después; no significa `runtime_ready` ni autoriza
importar el item.

## Esquema mínimo de salida

Puede ampliarse, pero no reducirse:

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

CREATE TABLE quest_item_grants (
    grant_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    component_id INTEGER NOT NULL,
    component_kind_id INTEGER NOT NULL,
    grant_phase TEXT NOT NULL,
    quest_act_id INTEGER NOT NULL,
    act_detail_type TEXT NOT NULL,
    act_detail_id INTEGER NOT NULL,
    selection_mode TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    grade_id INTEGER,
    rank INTEGER,
    cleanup INTEGER,
    destroy_when_drop INTEGER,
    drop_when_destroy INTEGER,
    show_action_bar INTEGER,
    try_equip INTEGER,
    native_state TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE orphan_grant_details (
    orphan_key TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    act_detail_id INTEGER NOT NULL,
    item_id INTEGER,
    state TEXT NOT NULL,
    row_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE wiki_quest_pages (
    quest_id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_sha256 TEXT,
    page_state TEXT NOT NULL,
    native_identity_state TEXT NOT NULL,
    detail_present INTEGER NOT NULL,
    parser_version TEXT,
    evidence_json TEXT NOT NULL
);

CREATE TABLE wiki_quest_item_mentions (
    mention_key TEXT PRIMARY KEY,
    quest_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    section_kind TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    visible_count INTEGER,
    label TEXT,
    href TEXT NOT NULL,
    parse_state TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    context_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE item_closure (
    item_id INTEGER PRIMARY KEY,
    entity_key TEXT NOT NULL,
    native_state TEXT NOT NULL,
    lifecycle TEXT NOT NULL,
    concrete_type TEXT,
    impl_id INTEGER,
    use_skill_id INTEGER,
    buff_id INTEGER,
    craft_id INTEGER,
    closure_state TEXT NOT NULL,
    missing_dependencies_json TEXT NOT NULL,
    blocker_roots_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE quest_item_comparisons (
    comparison_key TEXT PRIMARY KEY,
    grant_key TEXT,
    mention_key TEXT,
    quest_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    native_relation_state TEXT NOT NULL,
    wiki_relation_state TEXT NOT NULL,
    role_comparison_state TEXT NOT NULL,
    count_comparison_state TEXT NOT NULL,
    overall_state TEXT NOT NULL,
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
quest_item_grants(quest_id, grant_phase)
quest_item_grants(item_id)
quest_item_grants(act_detail_type)
wiki_quest_item_mentions(quest_id, section_kind)
wiki_quest_item_mentions(item_id)
quest_item_comparisons(overall_state)
item_closure(closure_state)
```

## Estados de comparación

`overall_state` debe usar un vocabulario cerrado y documentado:

```text
match
native_only
wiki_only
wiki_detail_missing
wiki_parse_failed
role_conflict
count_conflict
ambiguous_many_to_many
blocked
```

El algoritmo debe comparar por `(quest_id,item_id)` y luego resolver roles y
cantidades sin destruir multiplicidad. No forzar un match uno-a-uno cuando
existan varias filas nativas o menciones visibles.

## Casos ancla obligatorios

### Quest 2259

```text
quest_id=2259
initial_supply fixed:
  component=9956
  act=22574
  detail=2233
  item=16259
  count=1
```

### Quest 2260 — caso principal

```text
quest_id=2260

initial_supply fixed:
  component=9960
  act=14159
  detail=1334
  item=16260
  count=1

reward fixed:
  component=9962
  detail=4815
  item=23633
  count=1

reward fixed:
  component=9962
  detail=8711
  item=48507
  count=2

reward selective:
  detail=3655 item=47985 count=1
  detail=3656 item=47986 count=1
  detail=3657 item=47987 count=1
```

La página detallada `2260` debe quedar congelada y sus menciones visibles
comparadas sin usarla como fuente de filas nativas.

### Quest 2258 — regresión del parser

Debe comprobarse que:

```text
item 16288 -> quest_item
item 23633 -> fixed_reward
```

No deben volver a quedar clasificados respectivamente como `accept_from` o
`report_to` por contaminación del contexto.

### Quest 330 — selección múltiple

Debe conservar recompensas fijas y selectivas como menciones/filas distintas,
sin deduplicarlas sólo por tipo de entidad.

## Salidas adicionales

Además de la SQLite:

```text
E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1.manifest.json
E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1-summary.json
E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1-gaps.csv
E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1.html
```

El visor HTML debe permitir filtrar por:

```text
quest_id
item_id
grant_phase
selection_mode
wiki state
comparison state
item closure state
blocker
```

Mantener código, pruebas y checkpoint en Git; mantener SQLite, HTML masivo,
cache y demás artefactos grandes fuera de Git.

## CLI sugerida

Integrar comandos equivalentes a:

```powershell
Set-Location D:\Proyectos\AAemu\rama_8\reconstruccion_cliente_8

python -B -m client_forensics freeze-quest-item-wiki --resume
python -B -m client_forensics build-quest-item-crosswalk
python -B -m client_forensics validate-quest-item-crosswalk
```

Los nombres pueden ajustarse a la arquitectura existente, pero el manifest
debe registrar los comandos efectivos.

## Pruebas obligatorias

Agregar pruebas unitarias para:

- join `quest -> component -> act -> detail -> item`;
- los cuatro tipos de grant incluidos;
- multiplicidad por quest/item;
- detalles huérfanos preservados;
- parser de secciones wiki con fixtures congelados;
- regresión 2258 contra contaminación `accept_from/report_to`;
- quest 2260 completa;
- páginas 404/410, transient error y parse failure;
- comparación `match/native_only/wiki_only/conflict/ambiguous`;
- clausura de item sin convertir corroboración en autoridad;
- generación determinista;
- cero referencias silenciosamente descartadas.

Ejecutar la suite completa de `client_forensics`, no sólo las pruebas nuevas.

## Gates de aceptación

No declarar terminado hasta cumplir todo:

```text
[ ] lista de 4293 quests recalculada desde Stage 40
[ ] 5640 QuestActSupplyItem enlazados preservados
[ ] 552 SelectiveItem preservados
[ ] 23 RankedItem preservados
[ ] 5 ResultRankedItem preservados
[ ] cuatro detalles SupplyItem huérfanos inventariados
[ ] cada quest candidata tiene estado wiki terminal o error reproducible
[ ] cada mención wiki conserva sección y ordinal
[ ] cero grants nativos sin fila de salida
[ ] cero item IDs descartados
[ ] cero relaciones huérfanas no explicadas
[ ] casos 2258, 2259, 2260 y 330 pasan
[ ] PRAGMA quick_check=ok
[ ] PRAGMA integrity_check=ok
[ ] dos builds producen SQLite y manifest deterministas idénticos
[ ] manifest registra hashes de todas las entradas
[ ] Stage 70/consolidada se regeneran si el nuevo detalle wiki se integra
[ ] visor, gaps y resumen regenerados
[ ] CHECKPOINT_QUEST_ITEM_CROSSWALK_V1.md actualizado
[ ] current-forensic-state.md actualizado con hashes y siguiente trabajo
[ ] scripts/status.ps1 y quick_validate.py pasan
```

Si una descarga masiva queda incompleta por red, no declarar la base completa:
producir un checkpoint reanudable, conservar estados por página y continuar en
el mismo chat hasta terminar o documentar un blocker externo real.

## Consumidor posterior esperado

El equipo de `aaemu8-native-reconstruction` usará la SQLite para consultar:

```sql
-- SupplyItem iniciales cuya fila nativa existe y no tiene dependencias
-- conocidas, priorizados por coincidencia visible wiki.

-- Quests que fallarán por item nativo ausente/incompleto en el runtime.

-- Recompensas fijas/selectivas/ranked que requieren cierre antes de autorizar
-- el reporte manual.
```

No agregar al crosswalk una columna `enabled` ni modificar un runtime. La
salida apropiada es evidencia + estado + blocker. La activación pertenece al
chat de reconstrucción.

## Entrega al usuario

Al finalizar, informar de forma breve:

1. ruta y SHA-256 de `quest-item-crosswalk-v1.sqlite3`;
2. cobertura nativa por tipo de grant;
3. cobertura wiki: present/detail/missing/error;
4. conteos de `match`, `native_only`, `wiki_only`, conflictos y ambiguos;
5. conteos por `item_closure.closure_state`;
6. pruebas, integridad y determinismo;
7. enlace al checkpoint y manifest;
8. cualquier blocker que el equipo de reconstrucción deba conocer.
