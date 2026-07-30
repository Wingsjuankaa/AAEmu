# Checkpoint — Stage 90 coverage closure v2

## Alcance

Esta iteración consume la primera frontera priorizada por Stage 90. Es
exclusivamente forense: reclasifica evidencia nativa, confirma loaders y
layouts, y reconstruye el grafo consolidado. No implementa mecánicas ni
modifica AAEmu, compact runtime, MySQL, `.env` o Docker.

## Resultados cerrados

### Descriptores de items

Los 109 `descriptor_missing` fueron reconciliados con
`descriptor_lifecycle`:

- 99 `item_recipes`
- 6 `item_armors`
- 3 `item_accessories`
- 1 `item_slave_equipments`

Las consultas nativas sin filtro prueban que son tombstones. Stage 20 proyecta
la entidad y la relación `has_descriptor` con ciclo de vida `tombstone`, y la
dimensión descriptor como `not_applicable`. Los gaps fuente no se borran:
quedan preservados en `source_records` como
`superseded_descriptor_gaps`.

### Detalles concretos de efectos

De las 9.907 referencias abiertas:

- 6.609 `NpcSpawnerSpawnEffect` son tombstones.
- 2.591 `NpcSpawnerDespawnEffect` son tombstones.
- 616 `NpcControlEffect` son tombstones.
- 3 `GainLootPackItemEffect` son tombstones.
- 85 `CinemaEffect` siguen `unknown`.
- 3 `MoveToLocationEffect` siguen `unknown`.

Las primeras cuatro familias se comparan contra sus resultados nativos
completos. Stage 50 contiene ahora 9.819 relaciones
`uses_concrete_effect=tombstone` y sólo 88 relaciones `unknown`.

### Frontera loot

Se confirmaron en `x2game.dll`:

- x64: `FUN_398f70e0`
- x86: `FUN_39a07180`
- `SELECT id, war_drop FROM loot_packs`
- layout: `68 38`
- consulta `loots` con 10 columnas
- layout: `68 68 68 68 68 68 68 38 38 68`

La decompilación x86 fue repetida y produjo el mismo SHA-256:

`21B806B5EBD0716DA1CDE4094880D1C16B98D24125284441F5B6492CD1EE1090`

No existen tablas `loot_packs`/`loots` en la compact cliente, las consultas no
aparecen en la secuencia cached catalogada y el barrido estructural de los 12
streams no encontró un par consecutivo no vacío que pueda atribuirse a ambos
resultados. Las 4.195 identidades `loot_pack` referenciadas permanecen
bloqueadas; no se infieren filas desde wiki, runtime o compact 3.0.

## Artefactos aceptados

- `stage-20-items.sqlite`
  - bytes: `1103822848`
  - SHA-256:
    `01E4178D748BEC9AEBB9535BA64A56D77F5C0824F06BAF528B95F6F78D9A49AC`
- `stage-50-skills.sqlite`
  - bytes: `1974710272`
  - SHA-256:
    `ECB7B43252335F521A3EB1E7CFFE5FD50B924219ABFD6D90B96D71182D9C246C`
- `stage-90-coverage-closure.sqlite`
  - bytes: `186531840`
  - SHA-256:
    `ECFFC7079F060618395ABE22C9B8C4894CACE52A8D8BEB118D2CF1F5F5772311`
- `aa8-client-knowledge.sqlite`
  - bytes: `6904066048`
  - SHA-256:
    `9FA3816415BFAA27E40F2A104A9603913BBF1F5A838E00329C7E4EBD40694884`
- `manifest.json`
  - SHA-256:
    `564E74AE373ABFB683F6F09CFF0CD514F3C09EBDA3E6124B3C357737A18E39BA`
- `viewer-coverage-closure.html`
  - SHA-256:
    `D1BB9B0020DBB425686201E1350E2B1826BED2BA358ADC398EA0F466DC99D888`
- `coverage-closure-work-queue.csv`
  - SHA-256:
    `37C3CF58E85B5E43B0436ACD1CD2868283885B3C6EC1562AEC224E69BEC6167C`

Stage 20 y Stage 90 produjeron hashes idénticos en dos builds independientes.
Stage 50 conserva el hash idéntico de sus dos builds de esta iteración.
Dos consolidaciones completas de 6,90 GB también produjeron el mismo SHA-256.

## Modelo agregado

- gaps fuente: 114.430
- regiones opacas fuente: 89
- gaps nativos accionables: 16.533
- gaps de servidor fuera de alcance: 97.897
- `blocker_roots`: 513
- `blocker_impacts`: 460.946
- `blocker_evidence`: 1.004
- `work_queue`: 513

La cola contiene:

- 414 raíces `queued`
- 68 raíces `audit_required`
- 16 raíces wiki `corroborative`
- 15 raíces servidor `deferred`

Frente a v1 se cerraron 9.928 falsos gaps nativos y se redujeron 29.780
impactos repetidos. `descriptor_missing` ya no existe como raíz. Los dos
resultados loot agregan evidencia negativa explícita y elevan el inventario de
regiones opacas de 87 a 89.

## Consolidada

La base consolidada usa esquema v2 y conserva el linaje de las etapas
`0, 10, 20, 30, 40, 50, 60, 70, 90`.

- entidades: 1.649.040
- propiedades: 6.766.724
- relaciones: 2.078.747
- assets: 377.295
- localizaciones: 629.661
- filas cached result: 1.416.263
- entidades wiki: 127.914
- raíces causales: 513
- impactos: 460.946

Aceptación:

- `PRAGMA quick_check = ok`
- `PRAGMA integrity_check = ok`
- cero huérfanos en propiedades, relaciones, cached results, wiki y Stage 90
- 17/17 pruebas Python aprobadas
- igualdad x86/x64 de los layouts loot
- ausencia de inferencias runtime/wiki/3.0

## Siguiente frontera recomendada

Consumir el siguiente lote por fan-out nativo:

1. `quest_component_text_kind` (3 IDs, 13.531 referencias).
2. `quest_detail` (13 IDs, 7.826 referencias).
3. `chat_bubble_kind` (3 IDs, 25.939 referencias).
4. `plot_event` (14 IDs, 4.963 referencias).
5. `npc_ai` (5 IDs, 32.191 referencias).

En paralelo conceptual, pero sin inventar datos, la frontera loot debe quedar
en espera hasta encontrar un nuevo artefacto nativo que contenga sus filas:
otro stream/cache del cliente, un paquete auxiliar confirmado o captura local
no persistente del loader.
