# Checkpoint V20: identidad, lifecycle y grafo nativo de item_guide

## Alcance

Este checkpoint cierra el catálogo propietario de `item_guide`, su tabla de
elementos, los consumers x86/x64 y el lifecycle de todos los IDs observados.

El trabajo es exclusivamente forense. No implementa mecánicas, modifica
AAEmu, compact, MySQL o runtime y no usa wiki ni datos históricos como
autoridad.

## Catálogo propietario

La autoridad de identidad es la consulta completa y sin filtro:

```sql
SELECT id, item_guide_impl_id, level, loot_main_category_id,
loot_sub_category_id, name, show, show_order, way_to_loot, zone_key
FROM item_guides
```

Resultado demostrado:

```text
inicio: 74.766.590
SQLITE_DONE/end: 74.792.156
filas positivas y distintas: 464
rango: 492..992
layout: 68 68 68 68 68 78 38 68 78 68
loader x64: FUN_39a3b3f0
loader x86: FUN_39d327f0
SHA-256 de IDs uint32_le ordenados:
E85EEBD554E6B833345617CC370E6850EF47E617E91023D97038A7E766F64A0A
SHA-256 nativo de filas:
E18F9B990C49EA17957B4C282E1603994F01D69973B3F1D0F6297D054E49687A
```

Los dos loaders leen las diez columnas con los mismos primitivos, recorren
`SQLITE_ROW` y exigen `SQLITE_DONE`. `FUN_39d327f0` se recuperó desde el
proyecto Ghidra x86 ya analizado; no fue inferido desde x64.

## Elementos y relaciones

La relación exacta se obtiene de:

```sql
select item_guide_id, item_id, item_guide_a_category_id,
item_guide_b_category_id, show_craft
from item_guide_elems
ORDER BY item_guide_id, visible_order
```

Evidencia:

```text
inicio: 148.249.139
SQLITE_DONE/end: 148.329.401
filas y pares item_id -> item_guide_id únicos: 4.459
endpoints item_guide distintos: 386
layout: 68 68 68 68 38
loader x64: FUN_398f6750
loader x86: FUN_39a06820
SHA-256 nativo de filas:
FF243317895F8C32661E66EEB620743287B6A5BA11F9720F795D6CF5EB0C9802
SHA-256 de pares uint32_le:
208D6F0FFE2D65258374768B0E240B6B4852090BD668C0300583B2BD6FCCCE74
```

## Regla de lifecycle

- ID positivo presente en las 464 filas propietarias:
  `confirmed/present`.
- ID positivo alcanzado por `item_guide_elems` y ausente del resultado
  completo: `tombstone/tombstone`.
- La arista `item -> listed_in_item_guide -> item_guide` queda
  `confirmed/client_native` aunque su destino sea tombstone.
- Una guía propietaria sin elementos no es desconocida: su dimensión
  `incoming_relations` es `not_applicable`.

Clasificación:

| Partición | IDs |
|---|---:|
| catálogo propietario | 464 |
| owners con elementos | 383 |
| owners sin elementos | 81 |
| endpoints tombstone | 3 |
| universo observado | 467 |
| relaciones confirmadas | 4.459 |

Los tombstones son exactamente `488`, `490` y `491`.

Digests de las particiones:

```text
endpoints:
16A80DDB16F2571E5A942AA53729817F40C8E0766C1E388822AAD9B5C569A15C
endpoints presentes:
C0D74849F9E3B092381A76417AE7FCD5B2AB552DC3DCC3A4C7C3F94DE2E2D398
tombstones:
D079B0F3FAF9186C7217266039EF2C322F044AE99FFC4A2D5968E1C406A8A365
universo:
A534EF760C6C733A3A5B7B69EA39C9F229A81446A915ECF51E39BCE96467D80E
```

## Registro SQL y evidencia Ghidra

Stage 10 conserva:

- ambas consultas como `confirmed`;
- un consumer x64 y uno x86 independiente por consulta;
- paridad de layouts y primitivos;
- límites exactos, conteos, hashes de filas y cero strings sin resolver;
- tres artefactos configurables: resultados Ghidra x64, x86 y tareas SQL.

Hashes de la evidencia:

| Evidencia | SHA-256 |
|---|---|
| loaders x64 | `D13DF47D82E2C973532BEB595404C445CFB23B7D4362B6CA70B4B962B4A996FC` |
| loaders x86 | `77C789C6C8F761C5DD41FAAA0C03B381A84F2C2FCE97D39F02ED4EDD6ABE3940` |
| tareas SQL | `0C5784341E49560C21B46DAA786D7C2C5690F956A110DC7910EB84ED6D7AF1DC` |

## Cobertura consolidada

Conteos principales:

| Superficie | Cantidad |
|---|---:|
| entidades | 1.657.951 |
| propiedades | 6.994.119 |
| relaciones | 2.113.623 |
| filas de cobertura | 675.305 |
| gaps activos | 108.928 |
| regiones opacas | 91 |
| raíces causales | 395 |
| entradas de cola | 395 |
| impactos bloqueados | 395.894 |

Distribución de cobertura:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 428.479 | 63,4497% |
| `unknown` | 147.456 | 21,8355% |
| `tombstone` | 42.331 | 6,2684% |
| `corroborated` | 39.424 | 5,8380% |
| `not_applicable` | 13.724 | 2,0323% |
| `missing` | 3.881 | 0,5747% |
| `blocked` | 10 | 0,0015% |

Desde V19:

- cobertura total: 673.904 → 675.305 (`+1.401`);
- cobertura confirmada: 427.165 → 428.479 (`+1.314`);
- cobertura tombstone: 42.325 → 42.331 (`+6`);
- cobertura `not_applicable`: 13.643 → 13.724 (`+81`);
- propiedades: 6.993.652 → 6.994.119 (`+467`);
- raíces y entradas de cola: 401 → 395 (`-6`);
- impactos bloqueados: 396.287 → 395.894 (`-393`);
- entidades, relaciones, gaps y regiones opacas: sin cambio.

Las seis raíces retiradas corresponden a identidad/lifecycle, relaciones,
consultas y consumers de `item_guide`. Los porcentajes son distribución de
filas de evidencia/capacidad modeladas, no un porcentaje único del cliente.

## Implementación y validación

- `client_forensics/item_guide_lifecycle.py`: auditoría de cached results,
  digests, Ghidra, paridad x86/x64, lifecycle, cobertura y relaciones.
- `client_forensics/build.py`: reconciliación Stage 10/20 y ownership fuerte
  de Stage 20 en la consolidada.
- `client_forensics/tests/test_core.py`: catálogo real y fixture que incluye
  owner activo sin elementos y tombstone referenciado.
- versión de herramienta: `0.28.0`.
- 40/40 pruebas Python aprobadas.
- compilación Python aprobada.
- dos builds consecutivos byte a byte idénticos de Stage 10, Stage 20,
  Stage 90 y la consolidada.
- `quick_check=ok` e `integrity_check=ok`.
- cero propiedades, relaciones, cached rows, wiki rows, blocker impacts,
  blocker evidence o entradas de cola huérfanas.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-10-native-data.sqlite` | `F0B98642BF63C68DC47BB4470009929ACCAA7EC6ADC0542DB8A291FE04354E52` |
| `stage-10-native-data.manifest.json` | `79B4F14237D4869E628A5E5EE10F1253410D0801D57142DF786706A6842B8A06` |
| `stage-20-items.sqlite` | `DD39ED55BFEBC21B7DBE0DBD7B9C0F1BEA352B40A3000EA6F47C5D9D7329CB71` |
| `stage-20-items.manifest.json` | `9F49AA49EFB072438FF249C3ECEB37A24E85A57FF8E2F583DD1EE960C0842FF8` |
| `stage-90-coverage-closure.sqlite` | `FF3B1EFE855E4E03DAB49C42E8652355CFF4FFD930B1F2DC0594EC816BD3F8C5` |
| `stage-90-coverage-closure.manifest.json` | `B73BCAC7D37E7EAAE8FFBE68956ADE8CED0989A12D90DE7710855C08CB96E215` |
| `aa8-client-knowledge.sqlite` | `6685412B51856A7B7924DBE217397B164AC7F9A49E0A095047EB5039868FFAF7` |
| `aa8-client-knowledge.manifest.json` | `201D60C003173D4B4E88055F2ECE3B99B71E223F3912428104D5FC3DB70AE65C` |
| manifest final | `73F3A0CE274C41459CF0C0E55E6635F5925184D7B252A30F5E5F3A909E928C61` |
| cola CSV | `DEE7EA2D5118A1C69C050AFB7F4EDD9671C5280132847D47F8BBABEED624E756` |
| visor de cobertura | `55BE2149B8FA77E3C782335F987CEB21F3D4ED49AEDCC4CEDBA1A2E927CA6697` |
| resumen de cobertura | `C4981089DD5E204E6EDD37DD8C776AD6CC0FFB725E863BD0DA293AC09890354F` |
| gaps priorizados | `3B78CD59480C1E20BF02E4C29D023FF7BEE322537BF414BD26B4D9A75B3D3970` |
| regiones opacas | `B8424F662DF8CA2157A90D71F63B0E9A462E1525209AE0D25956A1738E40F418` |

## Próxima frontera

Las primeras posiciones teóricas (`loot_pack`, `sphere`, `ability` y
`npc_spawner`) todavía carecen de un resultado propietario inequívoco. No
deben cerrarse por semejanza o wiki.

La próxima frontera segura recomendada es `tag`:

```text
consulta propietaria: SELECT id, name FROM tags
owners nativos confirmados: 5.280
inicio: 5.374.123
SQLITE_DONE/end: 5.574.679
layout: 68 78
digest:
2451220D13CCC6C0D47E39D952BAA7CCDDC31E27EA314A7BE2BBE71150EFD029
```

El grafo ya contiene 11 IDs `tag` referenciados fuera del catálogo y 14
aristas entrantes. El siguiente entregable debe recuperar/verificar sus
loaders x86/x64, calcular la partición exacta y clasificar únicamente mediante
la consulta completa.
