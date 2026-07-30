# Checkpoint V17: cierre encadenado de craft y npc_group

## Alcance

Este checkpoint congela dos fronteras forenses consecutivas del cliente Kakao
8.0.3.12 r558734:

1. identidad y lifecycle restringido de `craft`;
2. catálogo propietario y lifecycle de endpoints `npc_group`.

El trabajo no implementa crafting, IA ni otra mecánica, no modifica AAEmu,
compact, MySQL o runtime y no usa la wiki ni datos históricos como autoridad
nativa.

## Frontera craft

### Autoridad y restricción demostrada

La consulta nativa cacheada de `crafts` está filtrada:

```sql
SELECT ... FROM crafts WHERE enable='t'
```

El call 674 y su loader x64 `FUN_39a818b0` recuperan exactamente 9.369
identidades habilitadas. El contador físico independiente demuestra 11.615
filas totales, por lo que existen exactamente 2.246 filas deshabilitadas.

Las relaciones y localizaciones nativas amplían el universo observable a
12.071 IDs. La diferencia contiene 2.702 identidades no habilitadas:

```text
2.702 = 2.246 filas deshabilitadas + 456 identidades históricas/tombstone
```

La evidencia estática disponible no permite repartir esos 2.702 IDs
individuales entre ambas categorías. No se aproxima la partición:

- 9.369 IDs: `confirmed/present`;
- 2.702 IDs: `unknown/disabled_or_tombstone`;
- un blocker opaco conserva la partición todavía no demostrada.

Digests congelados:

| Superficie | SHA-256 |
|---|---|
| IDs habilitados | `969EB678991F50D224896B5E3E3C32A0F0949366EA6AC27E0F8BCFBA6D52D61F` |
| endpoints de relaciones nativas | `795E4314BF27E019C73C0A11688B96CC59AA41E455CC3DA7C15BE2E4F9C7491B` |
| localizaciones | `DAC965F348AEEFBF86B7C90ED798C4F23C83E6537315791D15AE545C0BA6B098` |
| universo observable | `604B2DA86486A015FB37EFFC0C60E40D1AAAD8B27ECB77FBD556C0C6958C6396` |
| universo no habilitado | `AC318B420AF5AAFB409A63F0AFD6CFFC294C83157662347BBEFCC2F30AB222E5` |

Las 63.364 relaciones nativas entrantes, dirigidas a 11.946 IDs distintos,
quedan `confirmed/client_native`. Confirmar la arista no presupone que su
destino esté habilitado. Stage 20 materializa las 12.071 identidades y Stage 40
conserva como superseded 276 gaps que ya fueron reconciliados.

## Frontera npc_group

### Catálogo propietario

La autoridad es la consulta completa:

```sql
SELECT id, aggro_rule_id, enable_respawn, name FROM npc_groups
```

Fue localizada en ambos binarios:

| Arquitectura | SHA-256 de x2game | Offset SQL |
|---|---|---:|
| x86 | `078DB1B94236ECB8BBE21DC5C71CE90C178D51B6BF261C4767D32A44809BDDC3` | 17.815.788 |
| x64 | `12229B1DC1EA8BE3453BC792586EC5A56E948CD8F6424132521F9AF7F9A53C4A` | 14.484.528 |

El call 251 y el loader x64 `FUN_3994d6c0` delimitan el cached result:

```text
header estructural: 100.623.898
inicio válido: 100.623.904
SQLITE_DONE/end: 100.630.755
filas: 403
stride: 17 bytes
IDs positivos distintos: 403
rango: 1..482
SHA-256 de IDs:
82812B3AEC5EF5F7240C82AC6C354A64CD31AF6D949A3F338BEB61830FBF27
SHA-256 del bloque:
447F1926776E994830A3C4660EDE4C174D70DB899DAE4C876F065AF51881EEF3
SHA-256 de filas:
F21750016934B24632DA3DC52CDCBE42B998EF67849181607B4A96D715658398
```

La proyección cacheada preserva cuatro enteros por fila, pero no conserva la
semántica ABI suficiente para asignar con seguridad los tres campos
secundarios. Sólo `id` queda confirmado; `raw_field_1..3` se preservan como
evidencia y una región opaca mantiene pendiente su interpretación.

### Lifecycle transversal

- 403 IDs propietarios: `confirmed/present`;
- 213 endpoints nativos ausentes del catálogo completo:
  `tombstone/tombstone`;
- 1.319 relaciones nativas dirigidas a 225 IDs:
  `confirmed/client_native`.

Los 225 gaps de endpoint existentes en Stage 40 quedan superseded. Ya no queda
un hueco de identidad o lifecycle `npc_group`; sólo permanece el blocker de
semántica de los campos secundarios.

## Estado consolidado

Conteos principales de `aa8-client-knowledge.sqlite`:

| Superficie | Cantidad |
|---|---:|
| entidades | 1.657.951 |
| propiedades | 6.991.568 |
| relaciones | 2.113.623 |
| filas de cobertura | 667.652 |
| gaps activos | 109.092 |
| regiones opacas | 91 |
| raíces causales | 413 |
| entradas de cola | 413 |

Distribución de cobertura:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 423.605 | 63,4470% |
| `unknown` | 147.456 | 22,0858% |
| `tombstone` | 39.633 | 5,9362% |
| `corroborated` | 39.424 | 5,9049% |
| `not_applicable` | 13.643 | 2,0434% |
| `missing` | 3.881 | 0,5813% |
| `blocked` | 10 | 0,0015% |

Estos porcentajes miden filas de evidencia/capacidad ya modeladas. No se
presentan como un porcentaje único del cliente completo.

Desde V16:

- gaps activos: 109.593 → 109.092;
- raíces y entradas de cola: 417 → 413;
- las dos fronteras reducen cuatro raíces causales;
- las identidades indeterminadas de `craft` y los campos secundarios de
  `npc_group` continúan visibles, no se silencian.

## Implementación y validación

- `client_forensics/craft_identity.py`: restricción de identidad, clasificación
  honesta y reconciliación transversal de `craft`.
- `client_forensics/npc_groups.py`: catálogo propietario, boundary, lifecycle,
  aristas y evidencia opaca de `npc_group`.
- `client_forensics/build.py`: integración en Stage 20, 30, 40 y consolidación.
- `client_forensics/tests/test_core.py`: fixtures y contratos de ambas
  fronteras.
- versión de herramienta: `0.25.0`.
- 34/34 pruebas Python aprobadas.
- compilación Python aprobada.
- dos builds y dos consolidaciones consecutivos byte a byte idénticos.
- `quick_check=ok` e `integrity_check=ok`.
- cero relaciones o registros auxiliares huérfanos.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-20-items.sqlite` | `C2D9E69B241ACFC5F60AD62744D985FBE296FCE312F2266DF547E3CC12E0EB46` |
| `stage-20-items.manifest.json` | `955BCE6E760755B41E6C3E971019060A56CFBDEB2DAF657BD7BC355E45EC8899` |
| `stage-30-world-actors.sqlite` | `7E074A0463000A5444376ECC74C301D5FF6603FF9A3656C028A6F9A0CE7CB711` |
| `stage-30-world-actors.manifest.json` | `302D952D3EED85B10783EC15D089DF3369E3C1D4FA15A53A41138858B70BA298` |
| `stage-40-quests.sqlite` | `DA701736C8BA3CADCDE05E50E4824D5C74F4D5E74EE212E149B8268D59F19AB9` |
| `stage-40-quests.manifest.json` | `D716D0719328122A90481B163174A160BF2511C5FE8F2281649B5C861D2BF125` |
| `stage-50-skills.sqlite` | `DF00A62CC700481BE85DCFDE1B416F3F500D896E1D7FD4BC315A5E8F9943A6AF` |
| `stage-60-assets.sqlite` | `75375AA1DFF350A71D8609B1E7549F628C3EF908CF2DBE9EB47A3B9A2FB64D1D` |
| `stage-70-wiki.sqlite` | `A4507D6291740E830FF69E0352445A4EBCA8BC01898BA0933674F743EC4CC6D5` |
| `stage-90-coverage-closure.sqlite` | `831BC7B9C5C79F459B2A49D5FAC3CEBEC8E12B58370B203B5248161CCA0FCE2E` |
| `stage-90-coverage-closure.manifest.json` | `E51915CFCCCFCE8E42F1F99F549F940F922427A5499CB185EB226D8C12ECE42E` |
| `aa8-client-knowledge.sqlite` | `83E9CCAB79EFA16BC34EBC1970C597AAB9B4A090180C5B2EE2CAA746F2913D2A` |
| `aa8-client-knowledge.manifest.json` | `F66F144B8A8CA5235CB2819D5105663288D6EDAA599862341CA28D224597CF86` |
| manifest final | `DC28EFFCD72E4B1A7713391891C60C26D10523C5ABD0E7FF6DC92A52603FE33A` |
| cola CSV | `7D11724CE1054082A56D1D55E7B66484C1AA0A2B0DAE4735B10A586B700CABED` |
| visor de cobertura | `F2CC10D5FFEEB2E3FACFC36E5C658F9F19D0FE93F53F1A482855BF8C11D53C65` |
| resumen de cobertura | `C85BF44D7679B0DC53EED29D53DD91F896097AFA5C28739387DEB7D339F7FAFD` |
| gaps priorizados | `0371A6BA639A8E8BDFE97F44E6BA3E0D7EE615143E94FD2A0AC336D894400FD0` |
| regiones opacas | `B8424F662DF8CA2157A90D71F63B0E9A462E1525209AE0D25956A1738E40F418` |

## Próxima frontera

La cola sitúa primero `loot_pack` y `sphere`, pero ambas superficies continúan
sin un resultado propietario inequívoco. El bloque asociado a `sphere` que
parecía contener identidades resultó ser una tabla polimórfica de nueve tipos,
no el catálogo de 999 owners; usarlo habría producido una falsa cobertura.

La siguiente frontera segura recomendada es reconciliar lifecycle de endpoints
`npc`: Stage 30 ya posee el catálogo propietario completo de 18.217 NPCs y
Stage 40 conserva el conjunto acotado de referencias entrantes. Esto permite
clasificar presentes y tombstones con autoridad nativa antes de volver a las
superficies opacas `loot_pack` y `sphere`.
