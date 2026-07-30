# Checkpoint V19: identidad, lifecycle y registro nativo de craft_pack

## Alcance

Este checkpoint cierra la identidad y el lifecycle de todos los endpoints
`craft_pack` alcanzados por `craft_pack_crafts`. También reconcilia el estado
de las dos consultas propietarias y sus loaders x86/x64.

El trabajo es exclusivamente forense. No implementa crafting, modifica
recetas, altera AAEmu, compact, MySQL o runtime y no usa wiki ni datos
históricos como autoridad.

## Catálogo propietario

La autoridad de identidad es la consulta completa y sin filtro:

```sql
SELECT id FROM craft_packs
```

Resultado demostrado:

```text
inicio: 134.953.917
SQLITE_DONE/end: 134.956.247
filas positivas y distintas: 466
rango: 1..549
SHA-256 de IDs uint32_le ordenados:
1B656B7AD4D6484122AE7B8CC0E5AD32E258631FEBE5929AAEC48186E1B594E5
SHA-256 nativo de filas:
F4B95735E70058B66437FD8843E992EE70A7C6B237633507EE21BA66ABAE9A01
```

El loader x64 es `FUN_39a82740`; el loader x86 es `FUN_39dc2ad0`.
Ambos leen un único entero `68` y recorren el resultado hasta
`SQLITE_DONE`.

## Tabla de membresía

La relación exacta se obtiene de:

```sql
SELECT id, craft_pack_id, craft_id FROM craft_pack_crafts
```

Evidencia:

```text
inicio: 134.798.548
SQLITE_DONE/end: 134.953.911
filas: 11.951
pares craft_id -> craft_pack_id únicos: 11.523
endpoints distintos: 1.621
loader x64: FUN_39a82500
loader x86: FUN_39dc2920
layout: 68 68 68
SHA-256 nativo de filas:
EA259B17FC64AA5330550774CE67FD26DBA66FAC157085C0409E49CEC306AAFD
```

Los 428 registros repetidos representan pares ya observados y no se convierten
en aristas duplicadas dentro del grafo.

## Regla de lifecycle

- ID positivo presente en las 466 filas propietarias:
  `confirmed/present`.
- ID positivo alcanzado por `craft_pack_crafts` y ausente del resultado
  completo: `tombstone/tombstone`.
- La arista de membresía queda `confirmed/client_native` aunque su destino sea
  tombstone.
- No se usan nombres, wiki, runtime ni datos históricos para completar IDs.

Clasificación:

| Partición | IDs |
|---|---:|
| catálogo propietario | 466 |
| endpoints referenciados presentes | 438 |
| endpoints referenciados tombstone | 1.183 |
| endpoints referenciados totales | 1.621 |
| relaciones únicas confirmadas | 11.523 |

Digests de las particiones:

```text
endpoints:
EDB3FD79E706981D47B3B34B19F02E3952A0A541A9256054CA241DFAF98CB988
presentes:
D6539F3285F17E1581EFA2EE8B31E2F4F748B59632A1E30FA9075E8E8571D46E
tombstones:
84C0D71B45A2737CD92E61D8984679AF61CFDB2CE362EBDCE6169B48BA52DE4B
```

## Registro SQL y consumers

Los `query_specs` históricos de `craft_packs` y `craft_pack_crafts` estaban
marcados `registered/unknown`, aunque ambos tenían resultados confirmados,
boundary cerrado, cero referencias sin resolver y loaders estáticos.

Stage 10 ahora conserva:

- ambas consultas como `confirmed`;
- consumer x64 y x86 independiente para cada consulta;
- paridad de layout x86/x64;
- procedencia del registry, cached result, stream y loader;
- una validación explícita del cambio de estado.

Se preservó además la clausura aceptada de `item_grades` al reconstruir
Stage 10. Su resultado de 13 filas, offsets `0x46AF85D..0x46AFDF1` y loaders
`FUN_39a365c0`/`FUN_39d2ec60` impiden que el registro histórico vuelva a
producir una raíz causal falsa.

## Cobertura consolidada

Conteos principales:

| Superficie | Cantidad |
|---|---:|
| entidades | 1.657.951 |
| propiedades | 6.993.652 |
| relaciones | 2.113.623 |
| filas de cobertura | 673.904 |
| gaps activos | 108.928 |
| regiones opacas | 91 |
| raíces causales | 401 |
| entradas de cola | 401 |
| impactos bloqueados | 396.287 |

Distribución de cobertura:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 427.165 | 63,3866% |
| `unknown` | 147.456 | 21,8809% |
| `tombstone` | 42.325 | 6,2806% |
| `corroborated` | 39.424 | 5,8501% |
| `not_applicable` | 13.643 | 2,0245% |
| `missing` | 3.881 | 0,5759% |
| `blocked` | 10 | 0,0015% |

Desde V18:

- cobertura total: 669.041 → 673.904 (`+4.863`);
- cobertura confirmada: 424.668 → 427.165 (`+2.497`);
- cobertura tombstone: 39.959 → 42.325 (`+2.366`);
- raíces y entradas de cola: 407 → 401 (`-6`);
- impactos bloqueados: 398.657 → 396.287 (`-2.370`);
- gaps activos: sin cambio.

Las seis raíces eliminadas corresponden a una raíz conjunta de
identidad/lifecycle, una de relaciones, dos consultas y dos consumers
`craft_pack`. Estos porcentajes describen filas de
evidencia/capacidad modeladas, no un porcentaje único del cliente completo.

## Implementación y validación

- `client_forensics/craft_pack_lifecycle.py`: auditoría de resultados,
  digests, paridad x86/x64, lifecycle, propiedades, cobertura y relaciones.
- `client_forensics/build.py`: reconciliación Stage 10/20 y ownership
  consolidado de Stage 20.
- `client_forensics/tests/test_core.py`: catálogo real y fixture de lifecycle.
- versión de herramienta: `0.27.0`.
- 38/38 pruebas Python aprobadas.
- compilación Python aprobada.
- dos builds consecutivos byte a byte idénticos de Stage 10, Stage 20,
  Stage 90 y la consolidada.
- `quick_check=ok` e `integrity_check=ok`.
- cero propiedades, relaciones, cached rows, wiki rows, blocker impacts,
  blocker evidence o entradas de cola huérfanas.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-10-native-data.sqlite` | `6246655E220154822E6B0A2776DD38077AC3211A1C322D0FA718466DC9149EEE` |
| `stage-10-native-data.manifest.json` | `E92A19AC7B15D94CCA6DFD936907BE1F2C4F7AAAE78C5B5FEA75F78A32F5D5FC` |
| `stage-20-items.sqlite` | `9667FF1D9259847EF55ED58995CBCFCCF4806D45D527B1A5E32877BC31BB6557` |
| `stage-20-items.manifest.json` | `AF10ECA37FED14EEE85FF6B5D7187E3BE0F18AB6B0A0A30BBD4515A6A0301E9C` |
| `stage-90-coverage-closure.sqlite` | `07038E89978594E4ADABEF0671EEDAE3725974175D4CA08054D88947EFE3BD47` |
| `stage-90-coverage-closure.manifest.json` | `8483F52FA8B4FD5A2BF6E8FA218C249A274FB520D79BE1EDE56E909D51C8CF34` |
| `aa8-client-knowledge.sqlite` | `0BE22831321EBF4D886D1084CFF1EE6101C31EC99B4162EE1E128E0DE8C021A5` |
| `aa8-client-knowledge.manifest.json` | `0BFA94E998D939966A0DFA177F541E9CD4652864256DF056E6615AB036C8F891` |
| manifest final | `55B98B1C68CA24543601C04700713028799F34C2B0F2CA7542B72D252117CACC` |
| cola CSV | `A556AC6DFD06D8A9A423B505EB454BD373BC02860CE1CBA47FE027A23F6736ED` |
| visor de cobertura | `DD0A07D00B4224FAADFC6D0632272424BD0F603F527365A14DBB8E1AAD26FCE5` |
| resumen de cobertura | `43E36E5FD84DAF50C04269F47C3A786E9CA4E810DEA9696F8C0064A6F63D9486` |
| gaps priorizados | `3B78CD59480C1E20BF02E4C29D023FF7BEE322537BF414BD26B4D9A75B3D3970` |
| regiones opacas | `B8424F662DF8CA2157A90D71F63B0E9A462E1525209AE0D25956A1738E40F418` |

## Próxima frontera

Las fronteras de mayor prioridad teórica (`loot_pack`, `sphere`, `ability` y
`npc_spawner`) siguen careciendo de un resultado propietario inequívoco o
están documentadas como `native_result_absent`; no deben aproximarse.

La próxima frontera segura recomendada es `item_guide`. Ya existen dos
resultados nativos cerrados:

```text
item_guides:
  consulta completa sin filtro
  464 owners, IDs 492..992
  start=74.766.590, done=74.792.156
  digest=E18F9B990C49EA17957B4C282E1603994F01D69973B3F1D0F6297D054E49687A
  loader x64=FUN_39a3b3f0

item_guide_elems:
  4.459 filas, 386 item_guide_id distintos
  start=148.249.139, done=148.329.401
  digest=FF243317895F8C32661E66EEB620743287B6A5BA11F9720F795D6CF5EB0C9802
  loader x64=FUN_398f6750
```

De los 386 endpoints referenciados, 383 están presentes y exactamente tres
(`488`, `490`, `491`) están ausentes del catálogo completo. Por ello pueden
clasificarse como tombstones sin inventar datos, además de reconciliar las
4.459 relaciones y los registros/consumers asociados. Antes de promover la
frontera se recuperará o bloqueará explícitamente el loader x86 de
`item_guides`; `item_guide_elems` ya conserva `FUN_39a06820`.
