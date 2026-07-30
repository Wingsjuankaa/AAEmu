# Checkpoint Stage 90 V5 — catálogo nativo `world_interaction`

## Alcance

Esta iteración continuó exclusivamente el análisis forense del cliente Kakao
8.0.3.12 r558734. No se modificaron AAEmu, la compact activa, `.env`, MySQL,
Docker ni mecánicas de juego.

La frontera cerrada fue `world_interaction`, recomendada por Stage 90 V4:

- 64 IDs distintos observados inicialmente;
- 7.679 referencias desde Stage 50;
- una raíz de identidad y otra de relaciones para el mismo dominio.

## Autoridad nativa recuperada

`x2game.dll` contiene un switch que convierte el valor escalar de
`world_interaction` a su etiqueta exacta. Se recuperó desde los proyectos
Ghidra ya analizados:

- x64: `FUN_39875100`;
- x86: `FUN_398ebc00`.

Ambos switches son idénticos:

- 105 miembros válidos;
- valores `0..94` y `96..105`;
- el valor `95` cae en `default` y devuelve
  `invalid world_interaction`;
- etiquetas exactas desde `looting` hasta `sell_backpack`.

El ID 95 no aparece como entidad ni como referencia en los datos decodificados.
No se utilizó el enum del servidor como autoridad.

## `wi_details`

La consulta nativa exacta es:

```sql
SELECT wi_id, apply_expert, distance_sqrt, lp FROM wi_details
```

Evidencia:

- call index nativo: `611`;
- loader x64: `FUN_39a73700`;
- loader x86: `FUN_39db6ef0`;
- columnas: `wi_id, apply_expert, distance_sqrt, lp`;
- layout x86/x64: `68,38,68,68`;
- header estructural `game11`: índice 558, `0x77360FE`;
- inicio: `0x7736104`;
- fin/`SQLITE_DONE`: `0x773644C`;
- filas anunciadas y decodificadas: 60;
- referencias de strings sin resolver: 0.

`wi_details` no es el catálogo de identidad. Es metadata opcional asociada al
enum: 45 miembros válidos carecen de fila y no son tombstones. Los 60 detalles
presentes contienen:

- `apply_expert`: 59 valores `1` y un valor `0`;
- `distance_sqrt`: 60 valores `0`;
- `lp`: 60 valores `1`.

## Proyección transversal

### Stage 20

El resultado nativo filtrado de recetas habilitadas se proyectó al grafo:

- 9.369 filas `crafts WHERE enable = 't'`;
- 9.172 valores `wi_id > 0`;
- 27 IDs distintos;
- relación `craft -> uses_world_interaction`;
- fila y campos completos preservados en `native_rows` y
  `entity_properties`.

### Stage 40

`quest_act_obj_interactions.wi_id` ahora produce:

- 668 relaciones;
- 6 IDs distintos;
- cero referencias al ID 95.

`quest_act_supply_interactions` conserva su consulta/layout como superficie
periférica hasta mapear su cached-result boundary; no se inventaron filas.

### Stage 50

La stage propietaria materializa:

- 105 entidades `world_interaction`, todas `confirmed/present`;
- 105 etiquetas nativas;
- 60 filas `wi_details`;
- 6.894 referencias desde `interaction_effects`;
- 785 referencias desde `craft_effects`;
- 7.679 relaciones confirmadas en total;
- cero gaps locales del dominio.

## Reconciliación Stage 90

Stage 90 conserva las relaciones y gaps fuente sin reescribirlos, pero registra
su resolución contra la identidad fuerte de Stage 50.

Resultado:

| evidencia | V4 | V5 | delta |
|---|---:|---:|---:|
| reconciliaciones de relaciones | 70.578 | 80.418 | +9.840 |
| reconciliaciones de gaps | 4.636 | 4.642 | +6 |
| reconciliaciones de entidades | 292 | 292 | 0 |
| reconciliaciones totales | 75.506 | 85.352 | +9.846 |
| raíces causales | 500 | 498 | -2 |
| impactos | 448.714 | 448.732 | +18 |

El dominio queda con:

- 17.519 relaciones entrantes observadas;
- 9.840 relaciones cross-stage reconciliadas;
- 6 gaps fuente preservados y reconciliados;
- 0 blocker roots activos de `world_interaction`.

SHA-256 lógico del ledger de reconciliación:

`7EFA840D015EF4B3CDA5D1CE98D8101370940F7ACFC0740171ECF4DB7652651C`

## Visor

Se añadió `viewer-world-interactions.html`, con:

- búsqueda por ID, etiqueta o superficie;
- los 105 miembros y sus etiquetas nativas;
- presencia/ausencia no tombstone de `wi_details`;
- valores `apply_expert`, `distance_sqrt` y `lp`;
- referencias agrupadas por tabla, relación y estado fuente;
- relaciones y gaps reconciliados;
- gaps fuente preservados y blocker roots activos.

El visor contiene el ID 105, excluye el 95 y reporta cero gaps activos para los
105 miembros.

## Artefactos de evidencia

- `ghidra-stage90-world-interaction-cutdown-x64.txt`
  - 51.566 bytes
  - `830E0E1F2EB6E10DC43616D5A53CF6592A95488EC05FF7618D7612BEA7E3EE5E`
- `ghidra-stage90-world-interaction-cutdown-x86.txt`
  - 49.514 bytes
  - `51AE3E810640FB0F8C077CFD33DBF1CB12C0F1BFBF78EA08521FB980C48D4547`
- `ghidra-stage90-world-interaction-x86.txt`
  - 3.272 bytes
  - `54D1C3D07D77965CE1DAF8A5DE6F7634E33F575D0C0C0C621D989AF51F110F8F`
- `ghidra-all-sql-loaders-64.txt`
  - 6.325.951 bytes
  - `F502F2C278C348A21C0CF4B16DC69EE72F7EDD56A791753373C7E009B784EA92`

## Artefactos aceptados

- `stage-20-items.sqlite`
  - 1.164.685.312 bytes
  - `8AA3C6A698745C08292487FBAE83438C98EC3D149BE88C14C1CF688A0E365BC9`
- `stage-40-quests.sqlite`
  - 1.023.115.264 bytes
  - `B212E77794D9A130DEF53D1BE6744C0A2303CA35CDB665D359DE4E99EF56A372`
- `stage-50-skills.sqlite`
  - 1.975.173.120 bytes
  - `0D7497F801E3FBDDF46F4C0CEF13B9288C9607A016DE2F06455829FFC0EAAA2D`
- `stage-90-coverage-closure.sqlite`
  - 274.264.064 bytes
  - `BE80EAADD841FF7E4506BFFF89A2030A72A5562FD07259A40F0B3FAD62010873`
- `aa8-client-knowledge.sqlite`
  - 7.054.516.224 bytes
  - `95F43100C4AEC000DAA9D7B9B83F66CF14C4443AA1FA70FAA19E6F11D8856547`
- `manifest.json`
  - `CA93A5F06550FE9E6C251AFC47156056361551FAB1AA49F126DB48314FFA4FD4`
- `viewer-world-interactions.html`
  - 56.429 bytes
  - `2F0960F061DC3F22C903967A0260DC6BB6ED192B39E0C0A2BD6D41A2667B783E`

## Aceptación

- 20/20 pruebas Python aprobadas;
- Stage 20 idéntica en dos builds;
- Stage 40 idéntica en dos builds;
- Stage 50 idéntica en dos builds;
- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- cero huérfanos en propiedades, relaciones, cached results, wiki, blockers y
  work queue;
- 105/105 identidades y etiquetas nativas;
- cero relaciones o entidades para el ID inválido 95;
- sólo nueve SQLite canónicas de stage y una consolidada, sin temporales,
  journals o builds abandonados.

## Siguiente frontera recomendada

La siguiente frontera debe ser `item_grade`:

- sólo 12 IDs;
- 8.553 relaciones actualmente abiertas;
- está en el puesto 5 de la cola por identidad y en el 21 por relaciones;
- no depende de un resultado nativo ausente como `loot_pack`;
- permite validar el mismo patrón de enum/tabla propietaria con alto fan-out y
  riesgo acotado.

Después: `quest_name_kind`, `quest_context_text_kind`, `npc_group` y `sphere`.
`loot_pack` continúa como `native_result_absent` y no debe rellenarse desde
runtime, wiki ni datos históricos.
