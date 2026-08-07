# Checkpoint — Nuia Story Quest Graph V1

Fecha de cierre: 2026-08-01  
Cliente: ArcheAge Kakao `8.0.3.12 r558734`  
Modo: `client_forensics_only`  
Servidor/runtime: fuera de alcance y sin mutaciones

## Resultado

La frontera solicitada quedó cerrada como un grafo forense consultable y
reproducible:

```text
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1.sqlite3
bytes: 25.890.816
SHA-256: AF5D48C4AF1C9A266B058FF6D1D0A571C4A5E17C412320360C01F34FEA2056F9

manifest:
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1.manifest.json
SHA-256: 94B4F2921BD6C5A99CCA63FFA1084F8D3A9B5DB6E8B84A1C5028604EC4F545ED
```

Salidas derivadas:

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| `nuia-story-quest-graph-v1-summary.json` | 1.523 | `A67715552B186F440C098331C415DE0972570EFB65703BE0B73B3B34AEF17591` |
| `nuia-story-quest-graph-v1-gaps.csv` | 2.381.446 | `CA9068CA81F87615C9C648E9314145D72661521C1EB9FF21613A7ED68161A881` |
| `nuia-story-quest-test-order-v1.csv` | 6.895 | `F90D8F328BB2D63051C3C13F94CB9A5C7605EC927219DECD796A765FA325E974` |
| `nuia-story-quest-graph-v1.html` | 1.775.620 | `B8800722670FFE957AE8D4172C7E968570300951FB3035D39F51A2C770BEAF0F` |

El visor filtra por quest, chapter, zona, nivel, tipo de act y estado de
clausura. Presenta por separado orden editorial, corroboración wiki, fronteras
de capítulo y blockers. No contiene decisiones de activación ni estado de
runtime.

## Autoridad y raíz

La selección se recalculó desde `native_rows` de Stage 40:

```text
quest_categories.id = 3
quest_categories.name = [종족 퀘스트] 누이안
quest_contexts.category_id = 3
quest_contexts.race = 1
```

No se seleccionaron quests por rango de IDs, nombre, zona ni enlaces wiki. El
resultado exacto contiene 55 quests, 222 components y 344 acts. La distribución
por capítulos es `1/6/11/8/9/6/14` y se preservan los 18 tipos de act con sus
conteos nativos.

La jerarquía de autoridad quedó fijada así:

```text
Stage 40 -> identidad quest/component/act/detail y raíz narrativa
Stage 20/30/50/60 + consolidada -> clausura nativa alcanzable
quest-item-crosswalk-v1 -> grants nativos ya materializados
Stage 70/wiki cache -> corroboración visible, nunca autoridad nativa
game11 cached results -> funciones doodad exactas usadas por los anchors
```

## Contenido preservado

| Superficie | Filas |
|---|---:|
| quests | 55 |
| components | 222 |
| acts | 344 |
| endpoints | 108 |
| items alcanzados | 156 |
| grants enlazados desde el crosswalk | 130 |
| `ObjItemGather` | 17 |
| `ObjItemUse` | 9 |
| aristas de orden | 54 |
| pares intrachapter corroborados recíprocamente | 48 |
| fronteras de capítulo no resueltas | 6 |
| candidatos de frontera de scope | 16 |
| clausuras de dependencia | 24.695 |
| cola downstream | 10.005 |

Estados terminales de clausura:

| Estado | Filas |
|---|---:|
| `complete_native_closure` | 6.714 |
| `tombstone` | 9.400 |
| `unknown` | 6.621 |
| `missing` | 1.953 |
| `opaque` | 7 |

Cada endpoint conserva `closure_state` y `spawn_state`; cada item y cada
skill/buff/effect/plot alcanzado conserva una clasificación terminal. Los
estados incompletos se exportan a la cola de auditoría y no se convierten en
afirmaciones de readiness.

## Wiki y orden narrativo

La adquisición fue cache-first, bajo lock y respetando `robots.txt`. Se
validaron y reutilizaron los 54 snapshots existentes y sólo se descargó la
quest 6839:

```text
HTTP: 200
bytes: 170.091
content SHA-256: 561945265032415D444AF575CC0DDF17C6FCF78675FE4993395966FAA6BB8714
page_state: confirmed
```

Manifest de adquisición:

```text
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1-wiki-snapshot-manifest.json
SHA-256: 4CD3AC0CD565BDC0C361DEEC618D2C683033248FEDE6B3F98427EA37174D5671
record_digest: 1D5459FC377BEA2E78402D958D303D88E4F5DEF3447E864555D01D23F27943AF
reused/downloaded: 54 / 1
```

El parser estructural produjo 96 enlaces wiki dirigidos, equivalentes a 48
pares recíprocos `Requires precompleted quest`/`Opens access to`. Los links de
navegación no se promovieron a story edges. La quest 6839 no publica un enlace
visible que demuestre la frontera capítulo 0→1; las seis fronteras permanecen
`chapter_boundary_unresolved`. `chapter_idx/quest_idx` sólo genera candidatos
editoriales y nunca se promueve a dependencia nativa.

## Casos ancla

- Quest 2532 conserva `doodad:14074` como doodad lógico. El modelo proxy
  `npctype://10581`, el grupo 41496, la función 38378 y su referencia a quest
  2532 quedan enlazados sin convertir el doodad en NPC.
- Quest 2258 conserva los roles wiki `item:16288 -> quest_item` y
  `item:23633 -> fixed_reward`.
- Quest 2264 conserva el objetivo tombstone `item:24967`, el doodad resaltado
  14310, el reward y la cadena nativa doodad → skill 17310 → effect →
  `world_interaction:19 (use)`. La posible producción 14310→24967 se registra
  sólo como `candidate_produces_objective_item`, estado `unknown`, blocker
  `native_doodad_product_edge_not_demonstrated`; no se atribuye falsamente el
  detalle global `DoodadFuncLootItem:2482` a ese doodad.
- Quest 2265 conserva items 21604×1, 23633×1 y 34000×5, además de la cadena
  `item:34000 -> skill:35238`.
- Quest 330 conserva tres rewards fijos y dos selectivos sin colapsar
  multiplicidad.

## Integración staged y determinismo

Stage 70 incorporó el snapshot nuevo; Stage 90 mantuvo el mismo conjunto causal
de 391 roots. El bootstrap de Stage 90 se ejecutó sin Stage 90 ni sidecar
semántico para evitar el ciclo de frescura. La consolidación normal volvió a
validar estrictamente el sidecar. El índice semántico no necesitó regeneración:
su proyección causal siguió siendo idéntica y su SHA permaneció
`7AA4107D2527C7767D474980ABD4DD12052CC34FC986EE92082BB973A519A4B8`.

Dos builds consecutivos dieron hashes idénticos:

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| Stage 70 | 268.619.776 | `EB70E8A4489BABE948A403CA9A7BD4C3BADBBEB22362668E553BEE38212F7BC3` |
| Stage 70 manifest | 2.149 | `A50EF2F68A87BFA0C934D858F7CA88740F67BF609DD15786616E24D798182421` |
| Stage 90 | 294.944.768 | `351E77C4B326892CDF9766385633E1C589E9FAEA2ABD593509719F06CDC0EBF3` |
| Stage 90 manifest | 2.143 | `F1914AAA1423EB4F49A12EFB8D5215BFA85AF1F2B17FE6C8C29A1F06BD873911` |
| consolidada | 8.905.900.032 | `63BBA93992D87B7BA9E2946CAC1C2077849CAC9BF4FA4C07D08424E91B8E568B` |
| consolidada manifest | 2.263 | `C531EA56B7B3E3AA6DA46E2DC469E424C83AC0800D42A2525D7B77CD3B7327A9` |
| manifest global | 59.137 | `C52003367EC27E45FFC4B1CCA07B27F69D52070D21AAB9DFCFCE0F4DEC267D0E` |
| grafo Nuia | 25.890.816 | `AF5D48C4AF1C9A266B058FF6D1D0A571C4A5E17C412320360C01F34FEA2056F9` |
| grafo Nuia manifest | 6.223 | `94B4F2921BD6C5A99CCA63FFA1084F8D3A9B5DB6E8B84A1C5028604EC4F545ED` |

## Validación

```text
client_forensics unittest: 105/105 OK
pruebas específicas Nuia: 12/12 OK
validation_events Nuia: 28 confirmed, 0 failed
quick_check: ok
integrity_check: ok
scripts/validate_forensics_db.py: ok
validación global: 0 relaciones/propiedades/filas huérfanas
índice semántico: 0 orphan links, 0 critical roots sin path
```

Todos los gates del handoff quedaron cumplidos: raíz, conteos, tipos, grants,
clausuras, wiki, reciprocidad, fronteras, candidatos externos, anchors,
determinismo, regeneración staged, outputs, checkpoint, estado y validadores.

## Reanudación y siguiente trabajo

Comandos efectivos:

```powershell
python -B -m client_forensics freeze-nuia-story-wiki --resume
python -B -m client_forensics build-nuia-story-quest-graph
python -B -m client_forensics validate-nuia-story-quest-graph
```

La frontera queda cerrada. El siguiente entregable forense vuelve a:

```text
root: consumer:stage20:item-grades:order-consumer-x86
consumer: LoadItemGradeOrder
estado: blocked_by_opaque_region
cierre: 11 funciones, no truncado
```

No se modificaron AAEmu.Game, AAEmu.Login, AAEmu.Tests, `.env`, MySQL,
Docker, compact runtime ni servicios/personajes activos.

