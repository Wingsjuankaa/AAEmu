# Checkpoint Stage 90 V4 — reconciliación transversal

## Alcance

Esta iteración continuó exclusivamente el análisis forense del cliente Kakao
8.0.3.12 r558734. No se modificaron AAEmu, la compact activa, `.env`, MySQL,
Docker ni mecánicas de juego.

Antes del cierre se auditó el directorio de salida. Sólo existen las nueve
SQLite canónicas de stages y la consolidada; no quedaron SQLite ocultas,
temporales, parciales, journals o builds abandonados.

## Problema corregido

La consolidación conserva cada `gap` de las stages fuente, pero la versión
anterior de Stage 90 evaluaba esos gaps y relaciones únicamente contra el
estado materializado al final de la consolidación. Debido a la política
`INSERT OR REPLACE`, una observación débil de una stage posterior podía ocultar
una entidad `confirmed` o `tombstone` demostrada por otra stage.

Esto no era pérdida de evidencia, pero sí generaba falsos bloqueos en la cola
de cobertura.

## Resolución

Se añadió un resolver transversal que:

1. reúne las entidades candidatas desde gaps de endpoint, relaciones no
   resueltas y entidades débiles;
2. consulta directamente Stage 00, 10, 20, 30, 40, 50, 60 y 70;
3. acepta sólo observaciones `confirmed` o `tombstone` con autoridad fuerte;
4. falla si dos stages presentan estados fuertes contradictorios;
5. conserva el gap o relación fuente sin modificar;
6. registra cada reconciliación derivada en `source_records`, con observaciones,
   procedencia, stage y hash determinista.

Las relaciones sólo se cierran cuando la arista ya es nativa y lo único
pendiente era su destino. Las correlaciones por filename, XML, Lua o índice de
`game_pak` permanecen abiertas como `asset_resolution`.

## Resultado

Se reconciliaron 75.506 registros:

| origen | reconciliados |
|---|---:|
| gaps | 4.636 |
| entidades | 292 |
| relaciones | 70.578 |

Desglose principal:

| origen y destino | reconciliados |
|---|---:|
| gap → icon | 4.094 |
| gap → sound | 231 |
| gap → skill | 173 |
| gap → effect | 135 |
| gap → item | 3 |
| entity → item | 292 |
| relation → icon | 60.604 |
| relation → skill | 4.772 |
| relation → quest | 4.333 |
| relation → sound | 435 |
| relation → npc | 183 |
| relation → effect | 143 |
| relation → item | 108 |

El ledger completo tiene SHA-256 lógico:

`0217DD1709A7A1196FBF11842B85522EF8063AED6F4A3DF81D178C2CF2128C4E`

La evidencia fuente permanece intacta:

- gaps fuente: 114.392
- gaps activos en raíces: 109.756
- gaps reconciliados: 4.636
- regiones opacas: 92
- reconciliaciones de assets promovidas: 0

Stage 90 V4 contiene:

- 500 raíces causales
- 448.714 impactos
- 998 evidencias agrupadas
- 75.506 `source_records` de reconciliación
- 500 entradas en la cola de trabajo

## Corrección de autoridad en quests

Stage 40 actualizaba correctamente 969 quests a `lifecycle=tombstone`, pero
conservaba la autoridad débil de la entidad de localización preexistente. La
actualización ahora fija también:

- `authority=client_native`
- `source_stage=40`
- `provenance=aa8-client-forensics`

Los 969 tombstones quedaron confirmados con esa autoridad y Stage 40 volvió a
ser determinista.

## Artefactos aceptados

- `stage-40-quests.sqlite`
  - 1.022.758.912 bytes
  - SHA-256:
    `ED6851E8222F16FEB208CBE80BEF843E99EDF379719CEDAE57ABEFA2B9EAAAC9`
- `stage-90-coverage-closure.sqlite`
  - 262.660.096 bytes
  - SHA-256:
    `182C114EEA6D12C0D4F4EA77139CA4CDC925D0D34CD64857DD47820B9E62326C`
- `aa8-client-knowledge.sqlite`
  - 6.981.079.040 bytes
  - SHA-256:
    `890B13375ACC5C51934B0925DB2D092B4289F009EE990C2C5A42ADCB64F89F02`
- `manifest.json`
  - SHA-256:
    `035FE0BE03824F745218B6A001C7192A82A980031E1913DAB1B63E10A5C39662`

Reportes regenerados:

- `coverage-closure-work-queue.csv`
  - `0FF5B90AF88BDF4EC0C3D562C4EB2F132B7560EB6B8D4403543DB10C671821EF`
- `viewer-coverage-closure.html`
  - `8BD23467A3C9E4E98482FA46B4CD429503200F087BE623FF0A4653D7F24E804A`
- `viewer-assets.html`
  - `3C0F8ED675DBA95EAB73183597716FF8B8981782511096B6F0532692D90F08A0`
- `viewer-skills.html`
  - `52F6FBE3E2E60BC232FE02560DA19DDCFC7EC4BF52A3E161D992740E8F7942DC`
- `viewer-wiki.html`
  - `AA7AB42CAE28EA0E8F92FB5980311C238C67F525A2AD463F7DC29367E6FF8C00`

## Aceptación

- 19/19 pruebas Python aprobadas
- Stage 40 idéntica en dos builds
- Stage 90 idéntica en dos builds
- consolidada idéntica en dos builds
- `PRAGMA quick_check = ok`
- `PRAGMA integrity_check = ok`
- cero huérfanos en propiedades, relaciones, cached results, wiki, blockers y
  work queue
- linaje completo de nueve stages
- cero promoción de evidencia corroborativa de assets
- cero SQLite temporales o abandonadas

## Siguiente frontera recomendada

La siguiente frontera debe ser `world_interaction`:

- 64 IDs distintos
- 7.679 referencias
- una raíz de entidad y otra de relaciones que representan el mismo dominio
- alto fan-out con tamaño acotado
- no depende del resultado nativo ausente de `loot_pack`

El orden recomendado posterior es:

1. `item_grade`: 12 IDs y 8.553 referencias.
2. `quest_name_kind`: 3 IDs y 1.673 referencias.
3. `quest_context_text_kind`: 5 IDs y 918 referencias.
4. `npc_group` y `sphere`, separando enums escalares de tablas propietarias.
5. auditar las referencias residuales de `item`, `skill`, `buff` y `craft` por
   procedencia antes de intentar un descifrado masivo.

`loot_pack` conserva 4.195 IDs y evidencia `native_result_absent`. Su fan-out
es alto, pero no debe reinterpretarse ni rellenarse hasta localizar un stream,
paquete auxiliar o captura local autoritativa que contenga sus filas.
