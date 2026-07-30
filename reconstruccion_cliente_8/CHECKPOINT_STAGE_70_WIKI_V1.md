# Checkpoint Stage 70 Wiki V1

## Alcance

Stage 70 congela y normaliza la base visible compatible de
`https://wiki.archerage.to/na-en/db` como evidencia externa corroborativa.
No modifica AAEmu, compacts, `.env`, MySQL, Docker ni datos nativos.

La wiki nunca rellena una fila nativa ni convierte una inferencia externa en
autoridad de gameplay. Sus resultados viven exclusivamente en `wiki_entities`,
`wiki_properties`, `wiki_relations`, artefactos y superficies de evidencia.

## Adquisicion congelada

- Raices: `items`, `quests`, `npcs`, `doodads`, `skills`.
- Categorias/rutas descubiertas: 471.
- Snapshots totales: 476.
- HTTP 200: 471.
- HTTP 404 conservados: 5 (`*/group` expuesto por la navegacion).
- Bytes HTML congelados: 258.706.130.
- `Crawl-delay`: 1 segundo, tomado de `robots.txt`.
- Digest canonico del cache:
  `FF96138DA9F7501355199F4C086623CC2275465D9F0694669F7370F2CF68BC20`.

El cache vive fuera de Git en:

```text
E:\AAEmu-Research\output\aa8-client-forensics\stage70-wiki-cache
```

Cada snapshot conserva URL, status HTTP, tipo de contenido, bytes, SHA-256 y
metadata determinista sin timestamps.

## Normalizacion

Filas de tablas visibles procesadas:

| Clase | Filas |
|---|---:|
| items | 66.000 |
| quests | 23.485 |
| npcs | 42.388 |
| doodads | 24.364 |
| skills | 10.470 |
| Total | 166.707 |

Tambien se importaron 238 snapshots detallados ya congelados en las fronteras
de items, quests y skills. En conjunto se registraron:

- 714 artefactos wiki: 476 catalogos + 238 detalles.
- 476 superficies HTML.
- 127.914 entidades en la union wiki/nativa.
- 368.654 propiedades wiki.
- 9.186 relaciones wiki tipadas.
- 5 regiones opacas agregadas, una por clase principal.

## Matriz de presencia

| Clase | match | native_only | wiki_only |
|---|---:|---:|---:|
| item | 24.482 | 13.470 | 9.653 |
| quest | 7.673 | 1.142 | 865 |
| npc | 15.307 | 3.073 | 600 |
| doodad | 10.852 | 4.549 | 462 |
| skill | 10.468 | 25.235 | 13 |
| buff | 0 | 0 | 1 |
| craft | 0 | 0 | 69 |
| Total | 68.782 | 47.469 | 11.663 |

`native_only` significa que el ID no aparecio en ninguna raiz/categoria
congelada. No significa HTTP 404: la pagina individual no fue solicitada y
queda correctamente como evidencia desconocida.

Los IDs personalizados de ArcheRage se conservan como `wiki_only`; no se
descartan ni se confunden con carencias del cliente Kakao.

## Propiedades y relaciones

Comparacion de propiedades:

- `match`: 32.191.
- `conflict`: 261.
- `unresolved`: 271.177.
- `wiki_only`: 65.025.

Los 261 conflictos son exclusivamente valores `level`. Las diferencias de
nombre entre el compact Kakao coreano y la wiki inglesa son `unresolved`, no
conflictos semanticos. Los nombres identicos si se conservan como `match`.

Comparacion de relaciones detalladas:

- `match`: 2.747.
- `wiki_only`: 6.368.
- `unresolved`: 71.

Las membresias de catalogo se guardan como propiedades y no como relaciones
de gameplay. Las relaciones detalladas preservan `href`, etiqueta y contexto
visible.

## SQLite y reproducibilidad

Stage 70:

```text
E:\AAEmu-Research\output\aa8-client-forensics\stage-70-wiki.sqlite
bytes: 252.428.288
sha256: A4507D6291740E830FF69E0352445A4EBCA8BC01898BA0933674F743EC4CC6D5
manifest sha256: A8EB135DF6D6DC016646967C2EDFE5A5FB8399C21355B4529B7A585D1F07B1B6
```

Dos builds consecutivos de Stage 70 produjeron el mismo SHA-256.

Consolidada Stage 80:

```text
E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite
bytes: 6.704.500.736
sha256: 0EA9E0934FF6A0DE9C80E77ACDAA281BF41E4BEEA575AAD9BE277FA2307A0102
manifest sha256: 7F819C00EF032B0842A448398E9407FE1F761B801772B458956477A6BF7863B7
final manifest sha256: 0CA5831F8A74F22F5E6BF11BE731A55060AF0AA9B458EB8D1172E2D517336AB7
```

Dos consolidaciones consecutivas produjeron el mismo SHA-256.

Validaciones:

- `PRAGMA quick_check=ok`.
- `PRAGMA integrity_check=ok`.
- Ocho stages exactos: `0,10,20,30,40,50,60,70`.
- Cero propiedades o relaciones nativas huerfanas.
- Cero cached results huerfanos.
- Cero propiedades wiki huerfanas.
- Cero relaciones wiki sin entidad fuente.
- 15 pruebas Python aprobadas.

## Visor

```text
E:\AAEmu-Research\output\aa8-client-forensics\viewer-wiki.html
bytes: 23.793.376
sha256: AA7AB42CAE28EA0E8F92FB5980311C238C67F525A2AD463F7DC29367E6FF8C00
```

Permite buscar por clase, ID o nombre, filtrar el resultado de comparacion,
abrir la URL canonica y consultar los conteos de propiedades y relaciones.

## Frontera pendiente recomendada

La expansion de paginas individuales debe ser dirigida por clausura, no un
barrido indiscriminado. Prioridad:

1. Destinos de relaciones wiki que todavia son `wiki_only`.
2. Los 261 conflictos de nivel.
3. Entidades nativas `native_only` con mayor grado en el grafo nativo.
4. IDs que bloquean una relacion item -> quest/NPC/doodad/skill.

Cada nueva pagina se congelara con la misma politica, se importara dentro de
Stage 70 y debera conservar el determinismo del Stage 70 y Stage 80.
