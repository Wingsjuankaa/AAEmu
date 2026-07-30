# Checkpoint V21: catálogo, strings y lifecycle nativo de tag

## Alcance

Este checkpoint cierra el catálogo propietario `tags`, resuelve sus nombres,
verifica los loaders x86/x64 y reconcilia todos los endpoints alcanzados desde
skills, buffs y efectos.

El trabajo es exclusivamente forense. No implementa mecánicas, modifica
AAEmu, compact, MySQL o runtime y no usa wiki ni datos históricos como
autoridad.

## Catálogo propietario

La autoridad de identidad es:

```sql
SELECT id, name FROM tags
```

Resultado demostrado:

```text
inicio: 5.374.123
SQLITE_DONE/end: 5.574.679
filas positivas y distintas: 5.280
rango: 1..5.656
layout: 68 78
loader x64: FUN_39969130
loader x86: FUN_39b43210
SHA-256 de IDs uint32_le ordenados:
45D029E89528E0594D614D3F1231FD955ABFF9193044FA6D57DE8ACC75126795
SHA-256 nativo de filas:
2451220D13CCC6C0D47E39D952BAA7CCDDC31E27EA314A7BE2BBE71150EFD029
```

Los layouts Ghidra de ambas arquitecturas están `confirmed_static`, sin
blockers, y ambos loaders recorren el resultado hasta `SQLITE_DONE`.

## Resolución de strings

Stage 50 había decodificado correctamente las 5.280 identidades, pero
conservaba 58 nombres como `<ref:N>`. El resultado forense propietario ya
contenía la resolución exacta contra `client_compact_8.localized_texts`.

La reconciliación:

- sustituye las 5.280 filas cacheadas por el resultado autoritativo;
- confirma las 5.280 filas nativas;
- confirma las 5.280 propiedades `tags.name`;
- conserva las 58 referencias crudas y su evidencia de resolución;
- marca la región opaca histórica como
  `superseded_string_cache_references_resolved/confirmed`;
- excluye regiones resueltas de la cola Stage 90 sin borrar su linaje.

## Frontera de relaciones

Las relaciones `references_tag` producen:

| Partición | Cantidad |
|---|---:|
| relaciones nativas | 95.008 |
| pares origen/tag/relación únicos | 94.881 |
| endpoints distintos | 4.795 |
| endpoints presentes | 4.784 |
| endpoints tombstone | 11 |
| owners sin referencia entrante en Stage 50 | 496 |
| universo observado | 5.291 |

Los 11 tombstones son:

```text
4, 152, 205, 522, 1273, 1389, 2949, 4902, 21423, 25007, 25041
```

Digests:

```text
endpoints:
B1E911D17FA1CA6A98C7DE443DA59E882FE7ED37FD523164182B9A78227B10FA
presentes:
1A7B17AADC0DA74E30475F8D23CF3874708B3A11B34E1082202CD5C894BC7ECE
tombstones:
EDE0FAAC3E1D9C2E0FF990A3DE83F9D90B71AACC47CFD21E6B6BA03FC129DF46
universo:
1A450AD9DA5706F401F61B13BE416222380D3B6B7A0CC3CDDF95D63433CE0891
pares:
01776C15F42A84C02F63B8423813CF7E57D6C36ED2B74D1FF6798C235E47E1CC
```

## Regla de lifecycle

- ID presente en `tags`: `confirmed/present`.
- ID referenciado por una arista nativa pero ausente del catálogo completo:
  `tombstone/tombstone`.
- Toda arista permanece `confirmed/client_native`, independientemente del
  lifecycle del destino.
- Owner activo sin arista entrante: `incoming_relations=not_applicable`.

Stage 50 es el owner fuerte consolidado para los 5.291 IDs observados.

## Evidencia Ghidra

| Evidencia | SHA-256 |
|---|---|
| loaders x64 | `ABFE61DE734B7524A119BED8C1D11CF7A0DAE754EE4F9F291AA6D0CC9567D89B` |
| loaders x86 | `F6B162CB39F8A0E7D4122070DFC23AB0542D5786B0974590C55305DE590E3410` |
| layouts x64 | `3905F9AC79E0B1020294AA717B11B638F5B55F2CA240F6460607981D02BE7C63` |
| layouts x86 | `9C16B7856358824876D9D2B09BD16908C955089343C5B6D43BBA110992AB1B38` |
| tareas SQL | `DFAF2406998E74D18D1614B71C5E6DFC718E11BC60BA39B9C1959312066D8781` |

## Cobertura consolidada

| Superficie | Cantidad |
|---|---:|
| entidades | 1.657.951 |
| propiedades | 6.999.410 |
| relaciones | 2.113.623 |
| filas de cobertura | 691.178 |
| gaps activos | 108.928 |
| regiones opacas históricas | 91 |
| regiones opacas activas | 90 |
| raíces causales | 390 |
| entradas de cola | 390 |
| impactos bloqueados | 395.858 |

Distribución:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 443.834 | 64,2141% |
| `unknown` | 147.456 | 21,3340% |
| `tombstone` | 42.353 | 6,1277% |
| `corroborated` | 39.424 | 5,7039% |
| `not_applicable` | 14.220 | 2,0574% |
| `missing` | 3.881 | 0,5615% |
| `blocked` | 10 | 0,0014% |

Desde V20:

- cobertura total: 675.305 → 691.178 (`+15.873`);
- cobertura confirmada: 428.479 → 443.834 (`+15.355`);
- cobertura tombstone: 42.331 → 42.353 (`+22`);
- cobertura `not_applicable`: 13.724 → 14.220 (`+496`);
- propiedades: 6.994.119 → 6.999.410 (`+5.291`);
- raíces y cola: 395 → 390 (`-5`);
- impactos bloqueados: 395.894 → 395.858 (`-36`);
- regiones opacas activas: 91 → 90 (`-1`);
- entidades, relaciones y gaps: sin cambio.

Los porcentajes describen filas de evidencia/capacidad, no un porcentaje
único del cliente.

## Implementación y validación

- `client_forensics/tag_lifecycle.py`: catálogo, strings, Ghidra, consumers,
  lifecycle, cobertura y relaciones.
- `client_forensics/build.py`: reconciliación Stage 10/50 y ownership fuerte.
- `client_forensics/stage90.py`: regiones resueltas dejan de generar roots.
- `client_forensics/tests/test_core.py`: catálogo real y fixture lifecycle.
- versión de herramienta: `0.29.0`.
- 42/42 pruebas Python aprobadas.
- dos builds idénticos de Stage 10, Stage 50, Stage 90 y consolidada.
- `quick_check=ok`, `integrity_check=ok` y cero huérfanos.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-10-native-data.sqlite` | `95E5405BAB8C0C31803B41BD1B5A9FA11FE0475F01220C025B7E3E2EE584D0D1` |
| `stage-10-native-data.manifest.json` | `6D753D337C77A07887765AFA540F24E8CE9334D3504FAEEC6A45A7EF4F9A98E0` |
| `stage-50-skills.sqlite` | `AC6DDA3F55704E7C7CB4A458673E529A613955DF540A4F079CA43E1BA6B15C8C` |
| `stage-50-skills.manifest.json` | `1B4BA6B44B12D9A4C450CFB277DF2146C39625ABB866ED8F3D04F8077569B857` |
| `stage-90-coverage-closure.sqlite` | `9B08879C2F60A7F97D73B357231725F00B44A4784D6B87061C3CEF57DB80A9FB` |
| `stage-90-coverage-closure.manifest.json` | `5EB2C1B3DEEB9E4EB836922CB610910FFDA7824D3C9B37095E726C88679378A8` |
| `aa8-client-knowledge.sqlite` | `807BDABAC73BEDE4D5477BDF6A953C709B8D7007BAFB5286EB3C36575D9D36EC` |
| `aa8-client-knowledge.manifest.json` | `48361961C96ACF9405161C3595758606CB3CDE9D7C91A43489A21A3AC8D434B5` |
| manifest final | `359B24B1737911CE587B4AF918A9BA452DF9E5C897791978A1C264462F23A094` |
| cola CSV | `8DAB7A78689E451E1F84E2FA95FC727FE716EE704128536337B280F078E10ECE` |
| visor de cobertura | `EAF5BDA340FB34D80019AFB89E580161BAB5B67DE82654FF7EEDBCFFB7D0FEEE` |
| resumen de cobertura | `4C4E5E9E6DEA14F3D9440F7137FAB0DAFAD3A548866045303E52B75F77BB5B36` |
| gaps priorizados | `3B78CD59480C1E20BF02E4C29D023FF7BEE322537BF414BD26B4D9A75B3D3970` |
| regiones opacas activas | `21AAD7274EAAA6BC45DF01138855863BB0D992BEA7DAF3D77AF92EA15DF93B71` |

## Próxima frontera

Las primeras posiciones teóricas (`loot_pack`, `sphere`, `ability` y
`npc_spawner`) siguen sin catálogo propietario inequívoco.

La próxima frontera segura recomendada es `doodad`. Ya existe una consulta
propietaria completa:

```text
tabla: doodad_almighties
filas/IDs: 15.290
inicio: 111.029.707
SQLITE_DONE/end: 112.984.327
loader x64: FUN_39931d20
digest:
CF692C58250F6FA065782E611C8716AA172FA86D4ECA6B09B04EA33F42A06A28
```

El grafo conserva 111 IDs `doodad` referenciados fuera de owners fuertes y
203 aristas todavía no confirmadas. El siguiente entregable debe recuperar
primero el loader x86 y separar el cierre de identidad/lifecycle de los campos
de texto que aún permanecen opacos.
