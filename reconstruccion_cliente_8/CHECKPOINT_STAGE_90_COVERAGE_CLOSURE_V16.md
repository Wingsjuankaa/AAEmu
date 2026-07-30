# Checkpoint V16: identidad y lifecycle nativo de endpoints buff

## Alcance

Este checkpoint reconcilia todos los endpoints positivos `buff` alcanzados por
relaciones nativas tipadas de Stage 20, 40 y 50 contra el catálogo propietario
completo del cliente Kakao 8.0.3.12 r558734.

El trabajo es exclusivamente forense. No implementa combate, buffs ni skills,
no modifica AAEmu, compact, MySQL o runtime y no usa wiki o datos históricos
como autoridad.

## Autoridad propietaria

La autoridad es la consulta nativa del call 119:

```sql
SELECT id, ... FROM buffs
```

La consulta no tiene `WHERE`, join ni filtro de lifecycle. El primer campo
`id` usa el accessor entero `68` y el loader x64 es `FUN_39a2ae70`.

El resultado demostrado:

```text
header estructural: 44.170.889
inicio válido: 44.170.895
SQLITE_DONE/end: 64.403.064
filas positivas válidas: 27.303
IDs distintos: 27.303
rango de IDs: 1..31.308
SHA-256 de IDs uint32_le ordenados:
54A3DBE2FC7DC52E3264AF37D2011A8AF55218563C37F25A26E2101659383F67
SHA-256 de filas:
0D5655FDD8952B5966EDE8140C66023AB650C02BE2F2B14AF118FA7935085914
```

El task SQL también existe en la superficie x86, pero el dump disponible tiene
`STRING_MATCHES=0` y no recupera loader/layout. La paridad arquitectónica queda
marcada como incompleta; no se infiere desde x64.

El bloque conserva 23.060 referencias de strings internadas, correspondientes
a 8.442 índices únicos pendientes. Esto bloquea texto, no identidad: `id` es
entero, independiente y fue decodificado hasta el marcador `SQLITE_DONE`.

## Regla de lifecycle

- ID positivo presente en las 27.303 filas: `confirmed/present`.
- ID positivo alcanzado por una arista nativa exacta y ausente del resultado:
  `tombstone/tombstone`.
- La arista se confirma independientemente del lifecycle del destino.
- Localización, assets, wiki y relaciones heurísticas no autorizan tombstones.
- Los gaps reemplazados se conservan como evidencia superseded.

## Barrido transversal

| Stage | Endpoints nuevos | Presentes | Tombstones | Relaciones reconciliadas |
|---|---:|---:|---:|---:|
| Stage 20 | 39 | 0 | 39 | 41 |
| Stage 40 | 3 | 0 | 3 | 3 |
| Stage 50 | 384 | 0 | 384 | 1.100 |

La unión contiene 426 tombstones distintos:

```text
SHA-256 uint32_le de la unión:
7C017C999F2D6FB54378E26115EA72DF1AF6C870AA414CD8B3023F503A8C723B
```

Stage 50 conserva además siete endpoints previamente reconciliados; por ello su
estado materializado total es de 391 tombstones, aunque sólo 384 son nuevos en
este barrido.

## Estado consolidado

Entidades `buff`:

| Estado/lifecycle | Cantidad |
|---|---:|
| `confirmed/present` | 27.303 |
| `tombstone/tombstone` | 426 |
| `unknown/localization_only` | 1.047 |

Las 1.047 localizaciones sin fila física ni referencia nativa exacta no se
promueven. Las 101.818 relaciones consolidadas cuyo destino es `buff` quedan
`confirmed/client_native`; no queda ningún gap activo de identidad, lifecycle
o relación para endpoints buff.

La consolidación protege ownership de las 27.303 filas propietarias de Stage
50 y de los 426 tombstones demostrados en Stage 20/40/50.

Los gaps activos bajan de 109.985 a 109.593. Stage 90 elimina seis raíces y
entradas de cola: 423 → 417. Para `buff` sólo permanecen consultas parciales de
otras tablas (`buff_unit_modifiers`, `armor_grade_buffs` y la superficie textual
de `buffs`) y tres relaciones wiki corroborativas; no son huecos de identidad.

## Cobertura consolidada

La consolidada contiene 629.130 filas de cobertura:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 391.064 | 62,1595% |
| `unknown` | 142.026 | 22,5750% |
| `corroborated` | 39.424 | 6,2664% |
| `tombstone` | 39.207 | 6,2319% |
| `not_applicable` | 13.518 | 2,1487% |
| `missing` | 3.881 | 0,6169% |
| `blocked` | 10 | 0,0016% |

Estos porcentajes describen filas de evidencia/capacidad, no un porcentaje
único del cliente completo.

## Implementación y validación

- `client_forensics/skills.py`: catálogo propietario, boundary, digests,
  strings opacas y asimetría x64/x86.
- `client_forensics/buff_endpoint_lifecycle.py`: reconciliación de endpoints,
  aristas, lifecycle, propiedades, evidencia, cobertura y validaciones.
- `client_forensics/build.py`: cierre en Stage 20, 40 y 50 y ownership
  consolidado.
- `client_forensics/tests/test_core.py`: fixtures de catálogo y lifecycle.
- versión de herramienta: `0.23.0`.
- 31/31 pruebas Python aprobadas.
- Dos builds y dos consolidaciones consecutivos byte a byte idénticos.
- `quick_check=ok` e `integrity_check=ok`.
- Cero relaciones o registros auxiliares huérfanos.

Conteos principales de la consolidada:

- 1.657.484 entidades;
- 6.978.593 propiedades;
- 2.113.623 relaciones;
- 629.130 filas de cobertura;
- 109.593 gaps activos;
- 89 regiones opacas;
- 417 raíces causales y 417 entradas de cola.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-20-items.sqlite` | `3532D13A9856DC827FAA15C787312E3288F4C01B90F0B0BDB5406CC0A9907984` |
| `stage-20-items.manifest.json` | `2C7A5CFC571B7C81EC5DF4EBFDF8F98C479AF2ED48DA93377C9D5EEE45E4FE5B` |
| `stage-40-quests.sqlite` | `1A52BA35983A508BD2872ADD6CFB785B6E73BBF6E7113E944CB26CD6C22CDADB` |
| `stage-40-quests.manifest.json` | `9CF73FEE32CA5A19DCDB0907BC3753A40378BEC3B1907C32D4B0C7E6E5EF9B4D` |
| `stage-50-skills.sqlite` | `DF00A62CC700481BE85DCFDE1B416F3F500D896E1D7FD4BC315A5E8F9943A6AF` |
| `stage-50-skills.manifest.json` | `D0524E769FC959B78D7557265698E4C406B0D48CDF8C1C9C3DDB4CEE51A066E8` |
| `stage-90-coverage-closure.sqlite` | `6C41DF74F70E885509E5F6E2DDF1C89CDBC43810AD9AA154BDEB5B76D00C5DF8` |
| `stage-90-coverage-closure.manifest.json` | `3022FB55F005836E41EA18B59383799105F3A33766A95AEF1FCB619F4F872E05` |
| `aa8-client-knowledge.sqlite` | `0FB7271826C3D13DF49FFAD6980032F984DE2A347CC0C1DC3FFA5A896305923C` |
| `aa8-client-knowledge.manifest.json` | `702DC7BBBAF39F0562A751AFE4960736E2E5AB60384FF8149DF5E51F2CE763D0` |
| manifest final | `63433616189D8BC00000198F727414D77FDB34E590F4453BE61158F4060784CC` |
| cola CSV | `8D22100B6F9A209CDDA06C9A3C62BA8DA6DA959858912E41F582C3C753EF5A36` |
| visor de cobertura | `E5DB123C2ECCD4B179E475D0C1C8A9FB01A4721A9E4F58D787BA7F1EAD9214CC` |
| resumen de cobertura | `6D0B1B2D24967FC05C12481E36B11BC263E64FB7C871E84354AF5015485010A9` |
| gaps priorizados | `D17A757714C08AF44DC7767EDA8BD93B49C3ED203A371565AF79E715F7447602` |
| regiones opacas | `A9F5EFCCB49A0A5D665966BE8197A1125E6D081FD36418FE217C40BFB23119D3` |

## Siguiente frontera

La siguiente frontera es `craft`. La autoridad nativa demuestra 9.369 filas
habilitadas y un total de 11.615 filas, pero la consulta cacheada aplica
`WHERE enable='t'`. Por tanto existen exactamente 2.246 filas deshabilitadas,
aunque su identidad todavía debe separarse de 456 identidades históricas
observables sólo por referencias/localización. La frontera debe expresar esta
restricción sin asignar IDs individuales por aproximación.
