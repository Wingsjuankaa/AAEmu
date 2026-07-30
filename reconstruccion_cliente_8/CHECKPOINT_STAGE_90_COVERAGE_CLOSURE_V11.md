# Checkpoint Stage 90 V11 — frontera `quest_component_text_kind`

## Alcance

Esta iteración continuó exclusivamente el análisis forense del cliente Kakao
8.0.3.12 r558734. No se modificaron AAEmu, la compact activa, `.env`, MySQL,
Docker ni mecánicas de juego.

La frontera comprende:

- las 13.531 filas habilitadas de `quest_component_texts`;
- los IDs observados 4, 5 y 6;
- carga, copia y colección runtime por componente en x86/x64;
- consumers directos y helpers que reciben el componente o su vector;
- resolución del evento UI usado por el ID 6;
- lifecycle separado de las seis filas minoritarias;
- barrido transversal congelado de DLL/EXE, Lua 32/64 y XML;
- materialización en Stage 40, Stage 90 y la consolidada.

## Conclusión

El dominio queda semánticamente cerrado con autoridad cliente nativa:

| ID | Label canónico | Referencias | Consumer nativo |
|---:|---|---:|---|
| 4 | `summary` | 13.525 | cinco rutas x64 y cinco x86 |
| 5 | `body` | 4 | `FUN_39773260` / `FUN_397a8a80` |
| 6 | `doodad_phase_message` | 2 | `FUN_395eaf50` / `FUN_396166b0` |

El ID 6 despacha el evento UI `DOODAD_PHASE_MSG`, índice `0x102`. La
semántica del enum y el lifecycle de sus filas se conservan como dimensiones
independientes:

- las cuatro filas `body` pertenecen a los componentes 2357–2360 de la quest
  598, tutorial DDCMS presente;
- las dos filas `doodad_phase_message` pertenecen a componentes que apuntan a
  la quest 1421;
- quest 1421 no tiene fila en el resultado nativo `quest_contexts` y se
  conserva como tombstone por su localización residual;
- la fila 5802 mantiene `text=<ref:321647>` en estado `blocked`.

No se promueve ninguna fila huérfana a activa por haber recuperado la
semántica de su tipo.

## Layout y materialización

`FUN_399f2f00` carga el resultado `quest_component_texts`. El loader de
componentes enlaza después cada registro con su componente:

| Arquitectura | Raw vector | Stride | Loader de componentes | Vector en componente |
|---|---:|---:|---|---|
| x64 | `manager+0x13f88` | `0x10` | `FUN_399f3a80` | `+0x88/+0x90/+0x98` |
| x86 | `manager+0xf878` | `0x0c` | `FUN_39c64770` | `+0x5c/+0x60/+0x64` |

Por tanto, los IDs 5 y 6 no son valores cargados y descartados: forman parte
de las colecciones runtime que alcanzan los consumers confirmados.

## Clausura de consumers

El trazado P-code del vector de textos produjo:

| Arquitectura | Accessor | Callers | Cargas del vector | Reenvíos | Fallos |
|---|---|---:|---:|---:|---:|
| x64 | `FUN_399e1040`, campo `0x88` | 61 | 4 | 43 | 0 |
| x86 | `FUN_39c22de0`, campo `0x5c` | 60 | 4 | 40 | 0 |

Los helpers reenviados demuestran:

- ID 4: filtro nativo y clave de salida `summary`;
- ID 5: filtro nativo y string de campo `body` en ambas arquitecturas;
- ID 6: filtro nativo y llamada al dispatcher con `0x102`.

El inicializador x64 coloca `DOODAD_PHASE_MSG` en
`DAT_3acf9c20`; respecto de la base `DAT_3acf9410`, esa entrada es exactamente
el índice `0x102`. Los dispatchers x86/x64 recuperan el nombre del evento desde
sus tablas indexadas y lo envían a `FireUIEvent`.

## Barrido transversal

El snapshot `AA8_COMPONENT_TEXT_SURFACE_SNAPSHOT_V1` cubre:

| Superficie | Archivos | Bytes | Matches |
|---|---:|---:|---:|
| bin32 DLL/EXE | 112 | 369.707.768 | 1 |
| bin64 DLL/EXE | 99 | 361.428.600 | 1 |
| Lua 64 | 1.112 | 8.578.461 | 3 |
| Lua 32/mixto | 2.224 | 17.156.922 | 6 |
| XML | 7.698 | 619.822.805 | 0 |
| **Total** | **11.245** | **1.376.694.556** | **11** |

Sólo `x2game.dll` contiene la tabla, columna y eventos nativos. Lua contiene
consumers visuales de `DOODAD_PHASE_MSG` en chat y center messages, además del
evento distinto `QUEST_CONTEXT_OBJECTIVE_EVENT`. Ninguna otra DLL ni XML
aporta una semántica contradictoria.

El snapshot se generó dos veces con SHA-256 idéntico:

`8FC3F629B8E438D42C6A2DAF0D629BADD870F7B64C54ACDBF29E9F38C62032F4`.

## Estado canónico

Las tres entidades `quest_component_text_kind` quedan `confirmed` y reciben:

- `semantic_label`;
- `client_collection_materialization=confirmed`;
- `client_consumer_state=confirmed`;
- `native_row_population_state`;
- consumers x86/x64 con locator exacto.

Adicionalmente:

- ID 5: `owning_quest_id=598`,
  `native_row_population_state=ddcms_tutorial_fixture`;
- ID 6: `owning_quest_id=1421`,
  `native_row_population_state=orphaned_parent_context`,
  `unresolved_text_reference_count=1`.

La región opaca
`quest_component_text_kind.semantic_labels` desaparece. Stage 90 reduce las
raíces y la cola de 457 a 456. Permanece separada la raíz
`query_incomplete:quest_component_texts`, categoría `cached_result_decode`,
por 4.429 referencias globales de string todavía sin resolver en el resultado
completo; ya no representa un desconocimiento del enum o de sus consumers.

## Implementación forense

Se añadió o amplió:

- `client_forensics/quest_inline_semantics.py`: auditor estricto de
  materialización, helpers, labels, evento UI, lifecycle y snapshot;
- `client_forensics/stage40.py`: siete artifacts nuevos, propiedades por ID y
  consumers x86/x64;
- `client_forensics/config.py` y configuración Kakao r558734: fuentes V11
  explícitas;
- `tools/scan_component_text_surfaces.py`: snapshot transversal determinista;
- `ghidra/DumpAa8AddressData.java`: recuperación reproducible de strings y
  xrefs en direcciones concretas;
- pruebas de labels, evento, ownership y lifecycle;
- README y checkpoint.

La herramienta queda en versión `0.18.0`.

## Efecto en el grafo consolidado

Comparación contra V10:

- entidades: `1.657.484 → 1.657.484`;
- propiedades: `6.950.478 → 6.950.492`;
- relaciones: `2.113.623 → 2.113.623`;
- consumers: `118 → 124`;
- regiones opacas: `91 → 90`;
- cobertura: `544.827 → 544.827`;
- artifacts: `887 → 894`;
- raíces causales: `457 → 456`;
- cola de trabajo: `457 → 456`.

No se incrementa artificialmente la cobertura agregada. Se cierra la
dimensión semántica/consumer del enum y se preservan por separado los
blockers de strings y lifecycle.

## Artefactos y hashes

Evidencia principal:

- vector trace x64:
  `98629D4252070EA716120B18FE1CDFEC9DA0F68A43323822281FBF39AC8196A1`;
- vector trace x86:
  `97681037337CEAEFCAECB17F2D3C1AC26650989F1293D5D7A6888C04ADE8BCA6`;
- data/xrefs x64:
  `C2CAE2A9068F0A26DD5C8BE1C1069B1AE38B85DFF97BDC9A9256DA8C9B484900`;
- data/xrefs x86:
  `152A44EEDDB4EEA0D3A0679CFA7C53F48029656C4D3A390B2C03CC319A005D0E`;
- UI event core x64:
  `7E730D312782D26F99E06E6F102D8C0B745ED4D2D7C8F8DCE3302EB1BA37D843`;
- UI event core x86:
  `9C17408976609BE118FDAAEC974DCE422070156C928B9A4419EC508FA8A9B9FE`;
- surface snapshot:
  `8FC3F629B8E438D42C6A2DAF0D629BADD870F7B64C54ACDBF29E9F38C62032F4`.

SQLite y manifests:

- Stage 40:
  `02AE0611EA0D75537AD131974E1086A2CC0EFF9DBB170662D2100CA51D099CBA`;
- manifest Stage 40:
  `0D90F4C2C565E1F0816CF55F5E3C42EE9525117CD69E88E649DA8DD020B3648E`;
- Stage 90:
  `C8DF73BF33D08B7A0198C7CBA3CB5B7DC3D233B13D0896DA8E5D68077D459B34`;
- manifest Stage 90:
  `CC0E2226E8FF489746707196261A9E4605B4FC6CE6D84A51A279924EEF383630`;
- consolidada:
  `3BB7244DFEA10F9B52D552AB0CB3077A6950D7C542B2DCA38DA9E5D1BDB98F47`;
- manifest de la consolidada:
  `2CCD6BD230DC8BB5089A2AE8434321EA842E7FF66432C2D757E29F513CCA8FF1`;
- manifest final:
  `C67D56592C76B1D6453A2E5F8884A4B18913B9AA525C288CBF76784712D2A988`.

Reportes:

- `coverage-summary.csv`:
  `AB056EA1C03EA13C81BA9E76F7B05685D38A13CC07E4FF582077490AD48DD591`;
- `coverage-closure-work-queue.csv`:
  `EA4EFEBEA4C69970DD09B54D622E4E1914284D0B6956EA961425EC4E5795475D`;
- `viewer-coverage-closure.html`:
  `2B9679963A713C8C437688E41DFDB7BE71894E6E89760BEA9BAF5A289EAC8AA5`.

## Aceptación

- 25/25 pruebas Python transversales aprobadas;
- snapshot de 11.245 archivos idéntico en dos ejecuciones;
- Stage 40 idéntica en dos builds;
- Stage 90 idéntica en dos builds;
- consolidada idéntica en dos builds;
- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- cero huérfanos en propiedades, relaciones, cached results, wiki, blockers y
  work queue;
- cero regiones opacas para labels de `quest_component_text_kind`;
- 1.657.484 entidades;
- 6.950.492 propiedades;
- 2.113.623 relaciones;
- 456 raíces causales y 456 entradas de cola.

## Siguiente frontera recomendada

Reconstruir la caché global de strings que precede y alimenta
`quest_component_texts`:

1. identificar los inserts previos a la llamada 591 y reproducirlos en orden
   global, no sólo dentro del bloque core de quests;
2. resolver los 4.429 usos de referencias y congelar el conjunto de índices
   todavía ausentes;
3. distinguir referencias recuperables, tombstones y regiones realmente
   externas;
4. exigir cero `<ref:N>` silenciosos y row digest estable;
5. reclasificar `query_incomplete:quest_component_texts` únicamente cuando la
   evidencia de strings esté cerrada.

Esta frontera desbloquea texto nativo y localización cruzada para miles de
componentes sin implementar ninguna mecánica de juego.
