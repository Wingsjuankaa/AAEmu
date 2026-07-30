# Checkpoint — Stage 90 coverage closure v1

## Alcance

Stage 90 es una etapa exclusivamente forense. Clasifica el trabajo pendiente
del cliente Kakao `8.0.3.12 r558734`, agrupa señales repetidas en raíces
causales, calcula fan-out y produce una cola reproducible. No implementa
mecánicas ni modifica AAEmu, compacts runtime, MySQL, `.env` o Docker.

## Artefactos aceptados

- `stage-90-coverage-closure.sqlite`
  - bytes: `201719808`
  - SHA-256:
    `90A0624EF27BBDD4E0D4121BAB7EE5354C717503F15960DE11E096C188D6E015`
- `aa8-client-knowledge.sqlite`
  - SHA-256:
    `3B212969970C94FDBF493D52BF2A430E84E332C399C085B63FF0FAF57CF58C75`
- `manifest.json`
  - SHA-256:
    `7C3373C3E1F69F4EC88861BF1650AD42619E2D6C7289219261D96428D9154CCA`
- `viewer-coverage-closure.html`
  - SHA-256:
    `6B3EF34A5A9CDFE4BCADD50BE4852FA5DE78D323F135B438E753506AE49D06B3`
- `coverage-closure-work-queue.csv`
  - SHA-256:
    `45BAAC16E749B1A47589B0F7F3D5D48FFA206557EFF118889843C6AC19B3ED82`

Dos builds independientes de Stage 90 produjeron el mismo SHA-256.

## Modelo agregado

- `blocker_roots`: 513
- `blocker_impacts`: 490.726
- `blocker_evidence`: 1.003
- `work_queue`: 513

La cola contiene:

- 413 raíces `queued`.
- 68 raíces `audit_required`.
- 16 raíces wiki `corroborative`.
- 16 raíces de servidor `deferred`.

Los 124.358 gaps y las 87 regiones opacas de entrada quedaron clasificados sin
pérdida. Los 97.897 gaps de backend, protocolo, persistencia, validación y
clausura de servidor permanecen preservados como
`downstream_out_of_scope`; no desplazan el trabajo de descifrado nativo.

## Consolidada

La base consolidada usa esquema v2 y contiene el linaje de las etapas
`0, 10, 20, 30, 40, 50, 60, 70, 90`.

- entidades: 1.649.040
- propiedades: 6.766.724
- relaciones: 2.078.747
- assets: 377.295
- localizaciones: 629.661
- filas cached result: 1.416.263
- entidades wiki: 127.914

Aceptación:

- `PRAGMA quick_check = ok`
- `PRAGMA integrity_check = ok`
- cero propiedades, relaciones, cached results, wiki rows o filas Stage 90
  huérfanas
- 16/16 pruebas Python aprobadas

## Frontera recomendada

La siguiente iteración debe consumir la cola por raíces, no abrir una nueva
stage temática ni ampliar toda la wiki. El primer lote recomendado es:

1. Los 109 `descriptor_missing` de items.
2. Clausura de `loot_pack` y `effect_detail`.
3. Familias pequeñas de alto fan-out: `quest_component_text_kind`,
   `quest_detail`, `chat_bubble_kind`, `plot_event` y `npc_ai`.
4. Después, resultados nativos ausentes y layouts bloqueados de P0.

La wiki se consultará sólo para las entidades que ese lote priorizado necesite
corroborar.
