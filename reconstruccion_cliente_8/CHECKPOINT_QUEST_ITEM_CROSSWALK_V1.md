# Checkpoint — Quest ↔ Item Crosswalk V1

Fecha de cierre: 2026-07-31  
Cliente: ArcheAge Kakao `8.0.3.12 r558734`  
Modo: `client_forensics_only`  
Servidor/runtime: fuera de alcance y sin mutaciones

## Resultado

Se construyó la frontera forense solicitada:

```text
E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1.sqlite3
bytes: 34.091.008
SHA-256: 38E5CE75C90B0E64367A69E182E301B844E0904628CA726442F2D08A8DD34709

manifest:
E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1.manifest.json
SHA-256: FE80AD30188B66ECC80A118C85DFE9E711B3539166738D6D81A307E90F28C8FA
```

Salidas derivadas:

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| `quest-item-crosswalk-v1-summary.json` | 1.325 | `91D3594F1FF4694782392AE229EF22E97889A7664AA6242FC4D56A2907E7509D` |
| `quest-item-crosswalk-v1-gaps.csv` | 1.784.329 | `CB7B75BE3ABA9CB856B28F3D74C7AA858C350A47AD58C29119EB3BEFA6C096E2` |
| `quest-item-crosswalk-v1.html` | 2.752.039 | `7E03E890A157CAADE5083290CCF38C6E07A05457E3750A06601EC8061527C3FB` |

El HTML filtra por quest, item, fase, modo de selección, estado wiki, estado
de comparación, clausura del item y blocker. No contiene decisiones de
activación ni una columna `enabled`.

## Autoridad y entradas

Se respetó el orden:

```text
Stage 40 -> relación nativa quest/component/act/detail/item
Stage 20 + consolidada -> identidad y clausura nativa del item
Stage 70 -> corroboración visible estructurada
```

Entradas principales congeladas en `source_artifacts`:

| Entrada | SHA-256 |
|---|---|
| Stage 20 | `1274D10712A913A667364B7B75C47F1DE12013AE77AA7CF41E79F138F3FC979E` |
| Stage 40 | `0BB127E819232BFEE6D6559000E845B8C36E7F4C56A5ED64234DCD28B793D72C` |
| Stage 70 | `21EC69E96CCA23D5BB222C3FDF6831014EBD45F0A66DC05A258E7753A8754106` |
| consolidada | `AFFAA4316DBD0F4F7170FB30CE999805305C644B2AEEA088157A607B41ED201F` |
| manifest del cache detallado | `193E4D03F9AA3C5744A4F39739EC2081B04596E1928CB792F3918B252ADC2ED7` |
| manifest del incidente preservado | `DB99496B71BB5FB068D351E06E45F8FB7D0F7DE8559CAB4008457FC26F6FB6DE` |

La wiki no crea grants nativos. Los 2.645 registros `wiki_only` permanecen
corroborativos y no son candidatos de importación.

## Extracción nativa

La lista se recalculó desde `native_rows` de Stage 40, no desde la wiki:

| Tipo | Grants preservados |
|---|---:|
| `QuestActSupplyItem` | 5.640 |
| `QuestActSupplySelectiveItem` | 552 |
| `QuestActSupplyRankedItem` | 23 |
| `QuestActSupplyResultRankedItem` | 5 |
| **Total** | **6.220** |

Hay 4.293 quests candidatas y 2.491 item IDs nativos distintos. Por fase:
1.247 `initial_supply`, 4.916 `reward` y 57 `other_native_stage`.

Las 712 filas cuyo `quest_context` no está materializado se preservaron con
`native_state=unknown`; conservan component, act y detail nativos. No se
descartó ningún grant.

Los cuatro detalles SupplyItem sin act enlazado están inventariados:

```text
detail 10585 -> item 52599
detail 10587 -> item 52600
detail 10588 -> item 52599
detail 10593 -> item 52599
```

## Adquisición wiki y parser

El catálogo paginado general ya congelado contiene 216 páginas de quests y
digest `FF96138DA9F7501355199F4C086623CC2275465D9F0694669F7370F2CF68BC20`.
Se usó para identidad de catálogo; el detalle se limitó a las 4.293 quests
nativas con grants.

```text
cache: stage70-wiki-cache/detail/na-en/quests
expected/metadata: 4.293 / 4.293
HTTP 200: 3.772
HTTP 404: 521
errores transitorios: 0
snapshots inválidos: 0
detalle presente: 3.772
catálogo match: 3.739
catálogo ausente: 554
```

La separación catálogo/detalle es explícita. Ausencia de catálogo nunca se
convirtió automáticamente en HTTP 404. Hay 33 quests sin catálogo que sí
respondieron HTTP 200 y 33 quests catalogadas cuyo detalle respondió 404.

`robots.txt` permitió el crawl y fijó delay efectivo de 1 segundo:

```text
robots SHA-256: B852C178F0304DEA0F325C5D0D0A2E8F98C423496E2B7435931C68A7C1F03E25
cache digest: 855F36D560EC0AED5A2A08CF818063FA8F5B50FA3E46956CCAB1E9AD905E4D96
```

Una página es `partial`: quest 9154 tiene HTTP 200, marcador exacto
`ID: 9154` y una mención estructurada válida a `item:16327`, pero la wiki
publica el título sin nombre. Se preservó como evidencia terminal; no se
inventó un nombre.

El parser `quest-item-structured-v1` produjo 7.580 menciones y cero
`unknown_section`:

| Sección | Menciones |
|---|---:|
| `fixed_reward` | 3.750 |
| `objective_item` | 2.053 |
| `quest_item` | 1.162 |
| `selective_reward` | 395 |
| `requirement_item` | 135 |
| `ranked_reward` | 85 |

Se excluyeron links dentro de tablas auxiliares y la identidad de mención
incluye sección y ordinal.

### Incidente de adquisición preservado

Durante una reanudación inicial coexistieron brevemente dos procesos. Se
detuvieron ambos, se delimitó exactamente la ventana
`2026-07-31T21:40:50Z..21:43:28Z` y se movieron, sin borrar, 92 pares
HTML+metadata a:

```text
stage70-wiki-cache/detail-superseded-overlap-v1/na-en/quests
```

El manifest conserva IDs, rutas y hashes. Esos 92 IDs se descargaron otra vez
con un único proceso bajo lock; los otros 4.201 snapshots fueron validados y
reutilizados. El digest de contenido antes y después fue idéntico.

## Comparación y clausura

Estados de comparación:

| Estado | Filas |
|---|---:|
| `match` | 4.714 |
| `native_only` | 402 |
| `wiki_only` | 2.645 |
| `wiki_detail_missing` | 890 |
| `wiki_parse_failed` | 1 |
| `role_conflict` | 85 |
| `count_conflict` | 109 |
| `ambiguous_many_to_many` | 44 |

No hubo estados fuera del vocabulario cerrado. Las 44 filas ambiguas
conservan ambos lados y no fuerzan emparejamientos uno-a-uno.

Estados de clausura para 3.805 items nativos o visibles:

| Estado | Items |
|---|---:|
| `complete_native_closure` | 72 |
| `generic_dependency_free_candidate` | 329 |
| `dependency_closure_unknown` | 1.364 |
| `dependency_closure_missing` | 337 |
| `tombstone` | 1.636 |
| `native_item_missing` | 67 |

Hay 426 comparaciones `match` cuyo item es
`generic_dependency_free_candidate`. Esto es una cola de auditoría posterior,
no una afirmación de que el runtime esté listo.

## Casos ancla

- Quest 2258: `item:16288 -> quest_item` y `item:23633 -> fixed_reward`;
  no reaparecen `accept_from`/`report_to`.
- Quest 2259: se preserva el grant inicial exacto `component=9956`,
  `act=22574`, `detail=2233`, `item=16259`, `count=1`.
- Quest 330: tres grants fijos y dos selectivos; las menciones mantienen
  multiplicidad y ordinal.
- Quest 2260: seis grants nativos. Coinciden visiblemente `16260`, `23633`,
  `47985`, `47986` y `47987`. El nativo `48507 x2` queda `native_only` y la
  wiki muestra `54334 x2` como `wiki_only`; la divergencia se conserva y la
  wiki no reemplaza el dato nativo.

## Integración y determinismo

Se corrigió Stage 70 para elegir un único snapshot por identidad y preferir
el cache estructurado; el cache heurístico antiguo ya no puede añadir una
segunda interpretación de la misma quest.

También se corrigió el bootstrap de `build-stage-90`: la base previa se
consolida sin Stage 90 y sin importar temporalmente el sidecar semántico, para
evitar el ciclo `blocker_roots -> índice semántico -> Stage 90`. La
consolidación normal conserva la validación estricta del sidecar.

Dos builds consecutivos produjeron hashes idénticos:

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| Stage 70 | 268.619.776 | `21EC69E96CCA23D5BB222C3FDF6831014EBD45F0A66DC05A258E7753A8754106` |
| Stage 70 manifest | 2.149 | `B3E595B0FD9EDA941BE25FA9B87FB9F4FE33BBAAE1665BA64EEFF2E1B1BBDDFC` |
| Stage 90 | 294.944.768 | `AD00E6EA28A26AFE62BD59A9E64887AFA2016D98D5C55642E8A135B343B63E6A` |
| Stage 90 manifest | 2.143 | `279DE721BDC28174F2C21824982A863B119AA424A1624DAEC0EC0EDF73B9C064` |
| índice semántico | 599.400.448 | `7AA4107D2527C7767D474980ABD4DD12052CC34FC986EE92082BB973A519A4B8` |
| consolidada | 8.905.900.032 | `AFFAA4316DBD0F4F7170FB30CE999805305C644B2AEEA088157A607B41ED201F` |
| consolidada manifest | 2.263 | `14CA739A5E2CDECA13DAD2BB4C41D92334567AA41F71AE9E8405288C0F1B132D` |
| manifest global | 59.137 | `1C8CC081EA0F17B3D62DFBF415099E9246C405868A77144F179C602963F1B43E` |
| crosswalk | 34.091.008 | `38E5CE75C90B0E64367A69E182E301B844E0904628CA726442F2D08A8DD34709` |
| crosswalk manifest | 4.688 | `FE80AD30188B66ECC80A118C85DFE9E711B3539166738D6D81A307E90F28C8FA` |

## Validación

```text
client_forensics unittest: 93/93 OK
crosswalk validation_events: 12 confirmed, 0 failed
grants sin item_closure: 0
quick_check: ok
integrity_check: ok
Stage 70/90/consolidada: quick_check=ok, integrity_check=ok
referencias huérfanas canónicas: 0
índice semántico: 0 orphan links, 0 critical roots sin path
```

La skill instalada no contiene el nombre histórico `quick_validate.py`; se
usó su validador vigente `scripts/validate_forensics_db.py`, que confirmó el
crosswalk, y `scripts/status.ps1` se ejecuta al cierre.

## Siguiente trabajo

Esta frontera queda cerrada. El siguiente entregable forense único vuelve a:

```text
root: consumer:stage20:item-grades:order-consumer-x86
consumer: LoadItemGradeOrder
estado: blocked_by_opaque_region
cierre: 11 funciones, no truncado
```

No se modificaron AAEmu.Game, AAEmu.Login, AAEmu.Tests, `.env`, MySQL,
Docker, compact runtime ni servicios/personajes activos.
