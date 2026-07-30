# Checkpoint V15: identidad y lifecycle nativo de endpoints skill

## Alcance

Este checkpoint reconcilia todos los endpoints `skill` positivos alcanzados
por relaciones nativas tipadas de Stage 20, 30, 40 y 50 contra el catálogo
propietario completo de `skills` del cliente Kakao 8.0.3.12 r558734.

El trabajo es exclusivamente forense. No implementa combate, skills ni buffs,
no modifica AAEmu, compact, MySQL o runtime y no usa wiki o datos históricos
como autoridad.

## Autoridad propietaria

La autoridad es la consulta nativa del call 113:

```sql
SELECT id, ... FROM skills
```

La consulta no tiene `WHERE`, join ni filtro de lifecycle. El primer campo
`id` usa el accessor entero `68` y el loader x64 es `FUN_39a41b00`.

El resultado demostrado:

```text
raw_start: 22.360.912
valid_start: 22.361.437
SQLITE_DONE/end: 42.803.022
filas positivas válidas: 33.466
IDs distintos: 33.466
rango de IDs: 10.202..49.202
SHA-256 de IDs uint32_le ordenados:
EB39099026DF6E54980171675609F007901B9E489A1C670931223FDC80C2C62F
SHA-256 de filas:
953F3C9173AA2148BDEBC82436BA0E1A5BA34378C3DF2522D0EF4ECF01F8E31D
```

El task SQL existe también en la superficie x86, pero el dump actual tiene
`STRING_MATCHES=0` y no recupera su loader/layout. Esto queda registrado como
evidencia arquitectónica incompleta, no se inventa paridad.

## Falsa fila estructural anterior

El localizador histórico anunciaba 33.467 filas porque podía interpretar los
bytes inmediatamente anteriores al resultado como una fila mecánica. Esa fila
no pertenece al catálogo:

- `id=1.734.438.241`;
- `ability_id=168.656.229`;
- 16 columnas del layout booleano contienen valores fuera de `0/1`;
- termina exactamente en el inicio real `22.361.437`;
- desde la fila siguiente, las 33.466 filas son positivas, únicas y
  estructuralmente válidas hasta `SQLITE_DONE`.

Por tanto no se descarta silenciosamente una skill: se excluye un falso
positivo de boundary con una prueba reproducible.

El resultado conserva referencias internadas pendientes en `name` y `desc`.
Eso bloquea texto, no identidad: `id` es un campo entero independiente y su
clausura completa está demostrada.

## Regla de lifecycle

- ID positivo presente en las 33.466 filas: `confirmed/present`.
- ID positivo alcanzado por una arista nativa exacta y ausente del resultado:
  `tombstone/tombstone`.
- La arista se confirma independientemente del lifecycle del destino.
- IDs no positivos, assets, wiki y relaciones heurísticas quedan fuera.
- Los gaps reemplazados se conservan como `source_records` superseded.

## Barrido transversal

| Stage | Endpoints observados localmente | Presentes | Tombstones | Relaciones procesadas |
|---|---:|---:|---:|---:|
| Stage 20 | 8.263 | 8.193 | 70 | 14.208 |
| Stage 30 | 639 | 617 | 22 | 18.213 |
| Stage 40 | 173 | 169 | 4 | 1.022 |
| Stage 50 | 1.507 | 0 | 1.507 | 4.095 |

La propagación añade cuatro endpoints/6 relaciones ya fuertes al construir
Stage 40 y 70 endpoints/133 relaciones ya fuertes al construir Stage 50.

La unión real contiene:

- 10.582 endpoints únicos;
- 8.979 skills presentes;
- 1.603 tombstones;
- 37.677 observaciones de relaciones nativas entre los cuatro stages;
- 9.101 relaciones que inicialmente estaban `unknown` o `missing` y ahora
  quedan confirmadas.

El caso de mayor fan-out son 22 IDs históricos usados como `base_skill_id` por
NPCs: acumulan 16.442 relaciones y están ausentes del catálogo completo.

## Estado consolidado

Entidades `skill`:

| Estado/lifecycle | Cantidad |
|---|---:|
| `confirmed/present` | 33.466 |
| `tombstone/tombstone` | 1.603 |
| `unknown/localization_only` | 634 |

Las 634 entidades `localization_only` no tienen fila física ni referencia
nativa exacta que autorice clasificarlas como tombstone.

Todas las 111.574 relaciones consolidadas cuyo destino es `skill` quedan
`confirmed`. Ya no existen entidades skill `unknown/referenced`,
`unknown/present`, `unknown/unknown` o `missing/unknown`.

Durante la consolidación se detectó y corrigió una degradación de ownership:
18 tombstones de stages anteriores eran reemplazados por observaciones
`localization_only` posteriores. El merge ahora preserva primero los
tombstones demostrados y aplica después las 33.466 filas propietarias de Stage
50. Una validación explícita exige ambos conteos.

Los gaps activos bajan de 111.739 a 109.985:

- 1.680 gaps quedan registrados como superseded;
- otros 74 dejan de generarse gracias a propagación fuerte entre stages.

Stage 90 elimina nueve raíces y entradas de cola: 432 → 423. Para `skill` sólo
permanecen cuatro raíces de cached results/textos todavía incompletos y dos de
corroboración wiki; ya no queda ninguna raíz de identidad, lifecycle o cierre
de relaciones nativas.

## Cobertura consolidada

La consolidada contiene 627.852 filas de cobertura:

| Estado | Filas | Porcentaje |
|---|---:|---:|
| `confirmed` | 390.638 | 62,2182% |
| `corroborated` | 39.424 | 6,2792% |
| `tombstone` | 38.355 | 6,1089% |
| `not_applicable` | 13.518 | 2,1531% |
| `unknown` | 142.026 | 22,6209% |
| `missing` | 3.881 | 0,6181% |
| `blocked` | 10 | 0,0016% |

Estos porcentajes describen filas de evidencia/capacidad, no un porcentaje
único del cliente completo.

## Implementación

- `client_forensics/skills.py`
  - prueba la consulta propietaria y el boundary;
  - registra la falsa fila estructural;
  - genera digests independientes de IDs y filas;
  - conserva honestamente la asimetría x64/x86.
- `client_forensics/skill_endpoint_lifecycle.py`
  - clasifica endpoints por presencia/tombstone;
  - confirma aristas por separado;
  - conserva evidencia y gaps superseded;
  - materializa propiedades, cobertura, catálogos y validaciones.
- `client_forensics/build.py`
  - aplica el cierre en Stage 20, 30, 40 y 50;
  - propaga estados fuertes;
  - protege ownership en la consolidada.
- `client_forensics/tests/test_core.py`
  - prueba catálogo, boundary, falsa fila, x86 surface y lifecycle.
- versión de herramienta: `0.22.0`.

Digests de endpoints por stage:

| Stage | SHA-256 |
|---|---|
| Stage 20 | `6BFFB400088A59BE18639DB8503F869C0F2F3FDB852E9A0A687AA2EA5B32EB29` |
| Stage 30 | `10940B48F8745543B4F950C654D3DF66D49B4541BC20334FA233B88FCCE3F9E4` |
| Stage 40 | `ABE5AEC1E0642FB22FD0B70B39D84FDDC5C015AF5B73BA9978316EBCCE7282EB` |
| Stage 50 | `BF3766C3A2808EDF5F4F637412C88DFA49B27E9D377D848103ABE3712F2E453E` |

## Validación

- 29/29 pruebas Python aprobadas.
- Dos builds consecutivos byte a byte idénticos de Stage 20, 30, 40, 50 y
  Stage 90 después del último cambio aplicable.
- Dos consolidaciones consecutivas byte a byte idénticas.
- `quick_check=ok` e `integrity_check=ok` en todos los stages afectados y la
  consolidada.
- Cero propiedades, relaciones, cached results, cached rows, blocker impacts o
  entradas de cola huérfanas.

Conteos principales de la consolidada:

- 1.657.484 entidades;
- 6.978.167 propiedades;
- 2.113.623 relaciones;
- 627.852 filas de cobertura;
- 109.985 gaps activos;
- 89 regiones opacas;
- 423 raíces causales y 423 entradas de cola.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-20-items.sqlite` | `A6B534083BA55C8E45E26A5520E44FDB6B8B4C33ED181E794675389BA799E235` |
| `stage-20-items.manifest.json` | `2097C790B46CE7364DF547D311D4DCB2A4456B10048A5AF391BBD421B090FBF0` |
| `stage-30-world-actors.sqlite` | `DCF8048A6777CA5F72D6E95818D5D406FDA4B378A7CEA8891F84F425FA16B9F6` |
| `stage-30-world-actors.manifest.json` | `34FEC92CE315CC672E4718BC2A260813DC282DF23C812A9AE016EBEEBEA4332F` |
| `stage-40-quests.sqlite` | `E2E3BA8956AC8891594AC1AC7725D5A982CDAB6733B86E34E739CD9885CA75EB` |
| `stage-40-quests.manifest.json` | `3107489A0FFAC458AC5A8B0BF28CCD597D8D8B864133D0F2E366DA223B0A7C08` |
| `stage-50-skills.sqlite` | `062FD28C37D3998B3DA1DF7A4B59FFA0F0E4A55BF69D98CE80EA19D265215C72` |
| `stage-50-skills.manifest.json` | `C0E47AF03C0D6BFC58540A4F8714A9D623175F8D6D1CC3E08477769735C9EAEA` |
| `stage-90-coverage-closure.sqlite` | `B64F28E2E42431F511ACC7A0B71CA50FAC9A77222FFFBC9361E263CD08318959` |
| `stage-90-coverage-closure.manifest.json` | `4495185B37DB92D7878D8302042F77D85DBAD4BDAB307D25B9FCB28E128BF227` |
| `aa8-client-knowledge.sqlite` | `030EDC8678B8833F1467DE747C40752E74364AB946955EDB25B5A649740D2C7F` |
| `aa8-client-knowledge.manifest.json` | `7A4D15DAA6CFB497136B922BF0FA0751992DE5BF800F664B27AA599F872E3D52` |
| manifest final | `7F03A485A6B35BF657284DF39CB68849DDDD73C39FFE74B7FBB3B939507A239C` |
| cola CSV | `87E19F1F4D37B52BC3BB9FA1828919AA638F0020B6049676FE26679954F1C156` |
| visor de cobertura | `1A6EEC87A8F55CDD2C56DCF8FB1BE852381FE5F1C535DD01A1D3FFEC3F25E2ED` |
| visor de skills | `E9F3622DD405A362B9A946DD6616E307206DE262906284D22DFFFA8AD49FA958` |

## Siguiente frontera recomendada

`loot_pack` continúa agotada sin autoridad nueva. Aunque `craft` tiene mayor
prioridad numérica, su catálogo actual mezcla presencia, habilitación y
familias parciales; la ausencia todavía no autoriza tombstones.

La siguiente frontera de cierre seguro es `buff`:

- consulta nativa completa y sin filtros del call 119;
- 27.303 IDs propietarios distintos;
- 386 entidades `unknown/referenced`;
- tres entidades `missing/unknown`;
- 1.120 relaciones `unknown` y tres `missing`;
- 1.082 entidades `localization_only`;
- dos tombstones ya demostrados.

Los strings internados pendientes bloquean nombre/desc, pero no necesariamente
la identidad entera. Debe repetirse la prueba completa de boundary, catálogo,
falsa fila si existe, referencias exactas y propagación entre stages antes de
clasificar. Después conviene volver a `craft` para separar explícitamente
enabled, disabled y tombstone en vez de aplicar una regla binaria.
