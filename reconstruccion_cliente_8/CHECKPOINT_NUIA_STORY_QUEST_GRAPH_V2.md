# Checkpoint: Nuia Story Quest Graph V2

Fecha: 2026-08-01  
Cliente: ArcheAge Kakao 8.0.3.12 r558734  
Herramienta: `aa8-client-forensics 0.38.0`  
Autoridad: forense del cliente; la wiki es sólo corroborativa.

## Resultado cerrado

V2 conserva las 55 quests de V1 como prefijo y extiende la historia Nuia
principal hasta la terminal nativa del capítulo 31. La selección no se hace por
nombre: parte de `quest_contexts`, exige compatibilidad racial Nuia
(`race=255` o bit 1 activo) y sólo incorpora las categorías/chapter partitions
demostradas por la continuidad wiki.

| Categoría | Quests | Capítulos |
|---:|---:|---:|
| 3 | 55 | 0–6 |
| 131 | 75 | 7–17 |
| 180 | 26 | 18–21 |
| 183 | 29 | 21–23 |
| 200 | 57 | 24–28 |
| 206 | 6 | 29 |
| 208 | 9 | 30 |
| 210 | 37 | 31 |
| **Total** | **294** | **0–31** |

La SQLite final contiene 1.294 components, 1.354 acts, 559 endpoints, 428
relaciones de item y 108.662 filas de clausura. No se descartó ningún
component ni act seleccionado.

## Estrategia wiki aplicada

- Se congelaron y validaron 294/294 páginas, todas HTTP 200 y `confirmed`.
- El parser V2 reconoce tanto los bloques visibles `Requires/Opens` como los
  requisitos de stage `Completed the quest`.
- Cada enlace bruto permanece en `wiki_story_edges`; su resolución racial
  separada vive en `story_wiki_edge_resolutions`.
- Los href erróneos 7325, 8376, 7124 y 7126 se corrigieron por etiqueta
  visible + existencia nativa + race mask + orden de capítulo. La wiki nunca
  se elevó a dependencia nativa.
- La quest lateral 10159 se preservó como
  `external_native_prerequisite`, no se descartó ni se mezcló con la línea
  principal.

La única arista editorial que permanece `chapter_boundary_unresolved` es
6839→330, heredada del arranque/tutorial de V1: no corta una continuación
posterior y no se inventó una dependencia wiki o nativa inexistente.

Puentes clasificados:

| Desde | Hacia | Evidencia | Estado |
|---:|---:|---|---|
| 4411 | 7115 | stage requirement wiki | `corroborated_wiki_stage` |
| 8558 | 9009 | stage requirement wiki | `corroborated_wiki_stage` |
| 10303 | 10361 | actor visible Ardios + orden nativo | `corroborated_actor_name` |
| 10369 | 10646 | stage link wiki | `corroborated_wiki_stage` |

La terminal 10682 (`A Moment to Reminisce`) pasó cuatro auditorías:
sin `Opens`, sin successor por inverse `Requires`, sin chapter principal
nativo posterior a 31 y sin successor descubierto por sus actores visibles.

## Artefactos y hashes

```text
nuia-story-quest-graph-v2.sqlite3
bytes: 115.576.832
SHA-256: 39FD2589DC095E80722B94D3EB1D307E649C28AEAEB486AEF8725AD33DE82B5A

nuia-story-quest-graph-v2.manifest.json
SHA-256: B291A58E50A7401F13FA0EB190364CB25525AF3846DC0EEEB06F9CEAA6485CBF

nuia-story-quest-graph-v2-wiki-snapshot-manifest.json
SHA-256: 413D1B53E8B4122A41408B34DA624EE9D907AD5C5387E52CB896D20EA388C60C

Stage 70: 6D0CE29761CE4D9C042AA55DFD38FDECB50AE7FB2A69EB61F576899CCB85974B
Stage 90: CFB653BEBAB8F12023CCEF933D8A914C18D10ED6F9653BB5CE3BFEC9498BCFA7
Consolidada: F9CE51A05D7BC84FC50755E77E3FEA6E5A42B0E0C549B1504032CAB3FCFD86B3
Manifest global: 2D47C98FAA98731B8FFC52DF232EC10D6F46A852FFFBA33EFD9BAC01E0A7E2E9
```

Dos builds V2 consecutivos produjeron exactamente el mismo SHA-256. La
SQLite V2 y la consolidada dieron `quick_check=ok`, `integrity_check=ok`; 16
pruebas V1+V2 pasaron y no hay eventos de validación fallidos.

## Reproducción

```powershell
python -B -m client_forensics freeze-nuia-story-wiki-v2 --resume
python -B -m client_forensics build-stage-70
python -B -m client_forensics build-stage-90
python -B -m client_forensics build-native-semantic-index --resume
python -B -m client_forensics consolidate
python -B -m client_forensics finalize
python -B -m client_forensics build-nuia-story-quest-graph-v2
python -B -m client_forensics validate-nuia-story-quest-graph-v2
```

## Límites

Este cierre no implementa mecánicas, no declara runtime-ready y no modifica
AAEmu, MySQL, `.env`, Docker ni compact runtime. Los estados `missing`,
`unknown`, `opaque` y `tombstone` de la clausura transversal siguen siendo
evidencia forense y permanecen en la cola de auditoría.
