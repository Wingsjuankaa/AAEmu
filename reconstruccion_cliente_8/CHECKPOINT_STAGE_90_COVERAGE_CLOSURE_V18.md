# Checkpoint V18: identidad y lifecycle transversal de NPC

## Alcance

Este checkpoint reconcilia todas las referencias nativas positivas a `npc`
producidas por las etapas de items, quests y skills/effects contra el catálogo
propietario completo del cliente Kakao 8.0.3.12 r558734.

El trabajo es exclusivamente forense. No implementa NPCs, summons, quests,
combate o IA; no modifica AAEmu, compact, MySQL o runtime y no usa wiki ni
datos históricos como autoridad.

## Catálogo propietario

La autoridad es la consulta nativa completa:

```sql
SELECT id, ... FROM npcs
```

No contiene `WHERE`, join ni filtro de lifecycle. El campo `id` ocupa el primer
ordinal entero (`68`), el loader x64 es `FUN_39959180` y la consulta está
anclada en `0x39dd1f30`.

Resultado demostrado:

```text
inicio válido: 94.383.773 (0x5A02E9D)
SQLITE_DONE/end: 100.502.933 (0x5FD8D95)
filas positivas: 18.217
IDs distintos: 18.217
rango: 1..21.626
SHA-256 de IDs uint32_le ordenados:
3A27FDCFD378AF49036ACAD53F2421623A4A4F07F97C7320CF9391DA8DB00417
SHA-256 canónico de filas:
963767D30141EBC0CF87F1284D39E4754B2EEF005F4DB982C56B6E87BB27D704
```

El resultado conserva 5.469 referencias de strings todavía no resueltas,
correspondientes a 3.032 índices. Esto mantiene bloqueada la clausura textual
de algunos campos, pero no la identidad: `id` es entero, está antes de los
campos textuales y el reader recorre las 18.217 filas hasta `SQLITE_DONE`.

## Regla de lifecycle

- ID positivo presente en las 18.217 filas: `confirmed/present`.
- ID positivo alcanzado por una arista nativa exacta y ausente del resultado:
  `tombstone/tombstone`.
- La existencia de una arista se confirma independientemente del lifecycle de
  su destino.
- Assets, nombres, wiki y spawners visuales no autorizan un tombstone.
- Stage 30 conserva ownership canónico de todos los NPCs presentes.

## Barrido transversal

| Stage | Relaciones cerradas | Endpoints | Presentes | Tombstones | Gaps superseded |
|---|---:|---:|---:|---:|---:|
| Stage 20 — items/summons | 340 | 301 | 300 | 1 | 0 |
| Stage 40 — quests | 549 | 123 | 0 | 123 | 123 |
| Stage 50 — effects, residual | 41 | 39 | 0 | 39 | 39 |

Stage 50 recibe además los NPC `2026` y `20016` ya clasificados como tombstone
por Stage 40. Sus dos aristas se confirman durante la importación de evidencia
previa y no se vuelven a contar en la frontera residual. Por tanto, Stage 50
conserva 43 aristas a 41 tombstones, aunque el reconciliador sólo necesita
procesar 41 aristas a 39 endpoints.

La unión transversal contiene:

```text
relaciones de la frontera: 932
endpoints distintos: 463
presentes: 300
tombstones distintos: 163
SHA-256 de endpoints uint32_le:
83935E842A7C284D3E27E7266924210E1651082809DB1E2D9B9E1BD0A87DBCEB
SHA-256 de presentes:
4C9D4E3A240B3DAEF8EA058D0AC88D30C0DDC43EBEF4817642B24226E085F6A6
SHA-256 de tombstones:
D149A8D3E51F900A4483F3DB9E5B514BA50D4FBA0099D8FD8DEAE48FD8BF135C
```

## Estado consolidado NPC

| Estado/lifecycle | Ownership | Cantidad |
|---|---|---:|
| `confirmed/present` | Stage 30 | 18.217 |
| `tombstone/tombstone` | Stage 20 | 1 |
| `tombstone/tombstone` | Stage 40 | 121 |
| `tombstone/tombstone` | Stage 50 | 41 |

Las 41.488 relaciones nativas consolidadas cuyo destino es `npc` quedan
`confirmed/client_native`; alcanzan 7.720 IDs distintos entre presentes y
tombstones. Existen además 149 aristas de assets, conservadas separadamente
como `corroborated/client_asset`.

No queda ningún gap activo de identidad, lifecycle o relaciones entrantes para
NPC. Las referencias de spawners y otras tablas propietarias todavía opacas
permanecen como fronteras independientes.

## Cobertura consolidada

Conteos principales de `aa8-client-knowledge.sqlite`:

| Superficie | Cantidad |
|---|---:|
| entidades | 1.657.951 |
| propiedades | 6.992.031 |
| relaciones | 2.113.623 |
| filas de cobertura | 669.041 |
| gaps activos | 108.928 |
| regiones opacas | 91 |
| raíces causales | 407 |
| entradas de cola | 407 |
| impactos bloqueados | 398.657 |

Distribución de cobertura:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 424.668 | 63,4741% |
| `unknown` | 147.456 | 22,0399% |
| `tombstone` | 39.959 | 5,9726% |
| `corroborated` | 39.424 | 5,8926% |
| `not_applicable` | 13.643 | 2,0392% |
| `missing` | 3.881 | 0,5801% |
| `blocked` | 10 | 0,0015% |

Desde V17:

- cobertura total: 667.652 → 669.041;
- cobertura confirmada: 423.605 → 424.668;
- gaps activos: 109.092 → 108.928;
- raíces y entradas de cola: 413 → 407;
- impactos bloqueados: 399.147 → 398.657.

Estos porcentajes describen evidencia/capacidades ya modeladas; no constituyen
un porcentaje único del cliente completo.

## Implementación y validación

- `client_forensics/npc_endpoint_lifecycle.py`: catálogo exacto, digests,
  restricción textual, clasificación, propiedades, cobertura y reconciliación.
- `client_forensics/build.py`: cierre en Stage 20, 40 y 50 y ownership
  consolidado de Stage 30.
- `client_forensics/tests/test_core.py`: fixture de lifecycle y prueba contra
  el catálogo real.
- versión de herramienta: `0.26.0`.
- 36/36 pruebas Python aprobadas.
- compilación Python aprobada.
- dos builds consecutivos byte a byte idénticos para Stage 20, 40, 50, 90 y
  la consolidada.
- `quick_check=ok` e `integrity_check=ok`.
- cero propiedades, relaciones, cached rows, wiki rows, blocker impacts o
  entradas de cola huérfanas.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-20-items.sqlite` | `B59E759E6017173A0C211BCA8A9454B6B5E61BFD8D75EF9CB9A251B8D62B1BCB` |
| `stage-20-items.manifest.json` | `B7556B4BDA486517FCE8CC90DE86D6BB28FB936B89E844AF87858C96224D0887` |
| `stage-30-world-actors.sqlite` | `7E074A0463000A5444376ECC74C301D5FF6603FF9A3656C028A6F9A0CE7CB711` |
| `stage-40-quests.sqlite` | `11312840EB9A68E6672E9D8406CE65DCC2A782489863DC9C707AC54ADAAE83D4` |
| `stage-40-quests.manifest.json` | `5383EE8F8A54C612CEFDC112F483DBAFB82BCEBC4F84FF486A0550F91FEAC4C0` |
| `stage-50-skills.sqlite` | `866E071B98C16120D295E7F2E7D6017F3124481D53539111729A744027B5301B` |
| `stage-50-skills.manifest.json` | `E33418DF48854DAAB33594B8A2A0C0AAE5A807A42D2C5951E08F749A0AAAED67` |
| `stage-90-coverage-closure.sqlite` | `9A2BD335BB1C73576CB780E6FA566BE4CDAF14B54E004DB034D6774246D0B4D0` |
| `stage-90-coverage-closure.manifest.json` | `241ACCF1A87EBA5BF70A90E82541D6FFCED6D777CC7BD08225727B9DE0DFCD78` |
| `aa8-client-knowledge.sqlite` | `7AAE0AAD4CD2DB374CBB75CDD3EBA003FE7DB76C6608C6CF7364318697B16428` |
| `aa8-client-knowledge.manifest.json` | `DC69FF00A987A2ACEC30C47F2E626FCA375A8EF7E19E1CF130791048C95984B3` |
| manifest final | `E4E82F46A0125888E642092F80D8E076FB7FBC6555A68445B6EA263484BEB116` |
| cola CSV | `C95B01753A0E2B16664933F3A078B70D0C388F3F783727FD687FBC9F917F3CDC` |
| visor de cobertura | `593F085F3F5704F49F05FB66BEA41CE9CC920C13217D2065A028B7C65AB12300` |
| resumen de cobertura | `15B51AEDE556C3D9170D4FB8A580A8A47AD2B387298F3356A562180D28BE5E54` |
| gaps priorizados | `3B78CD59480C1E20BF02E4C29D023FF7BEE322537BF414BD26B4D9A75B3D3970` |
| regiones opacas | `B8424F662DF8CA2157A90D71F63B0E9A462E1525209AE0D25956A1738E40F418` |

## Próxima frontera

`loot_pack`, `sphere`, `asset_reference`, `ability` y `npc_spawner` conservan
mayor prioridad teórica, pero todavía carecen de un resultado propietario
inequívoco o están demostrados como `native_result_absent`.

La próxima frontera segura recomendada es `craft_pack`. El cliente ya aporta
una consulta propietaria completa y sin filtro:

```sql
SELECT id FROM craft_packs
```

El call correspondiente contiene 466 filas exactas, boundary cerrado,
`row_digest=F4B95735E70058B66437FD8843E992EE70A7C6B237633507EE21BA66ABAE9A01`
y loader `FUN_39a82740`. Stage 20 conserva 1.183 IDs referenciados ausentes del
catálogo y 11.523 aristas nativas totales. Por ello puede aplicarse el mismo
cierre de identidad/lifecycle sin inventar datos, antes de volver a las
superficies opacas de mayor prioridad.
