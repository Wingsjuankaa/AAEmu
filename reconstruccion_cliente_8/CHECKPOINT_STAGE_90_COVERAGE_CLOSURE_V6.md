# Checkpoint Stage 90 V6 — catálogo nativo `item_grade`

## Alcance

Esta iteración continuó exclusivamente el análisis forense del cliente Kakao
8.0.3.12 r558734. No se modificaron AAEmu, la compact activa, `.env`, MySQL,
Docker ni mecánicas de juego.

La frontera cerrada fue `item_grade`:

- 12 IDs referenciados inicialmente desde quests;
- 8.553 relaciones nativas entrantes;
- una raíz de identidad y una raíz de relaciones en Stage 90;
- una asociación histórica incorrecta entre la consulta de orden y el
  resultado descriptor completo.

## Autoridad nativa recuperada

`item_grade` no es un enum inferido. El cliente contiene un catálogo
`item_grades` de 13 filas, IDs `0..12`, con 16 campos por descriptor.

Consulta descriptor:

```sql
SELECT id, color_argb, durability_value, grade_order, icon_id, name,
       refund_multiplier, stat_multiplier, upgrade_ratio,
       var_holdable_armor, var_holdable_dps, var_holdable_heal_dps,
       var_holdable_magic_dps, var_holdable_magic_resist,
       var_wearable_armor, var_wearable_magic_resistance
FROM item_grades
```

Loaders:

- x64: `FUN_39a365c0`;
- x86: `FUN_39d2ec60`;
- layout idéntico:
  `68,78,60,68,68,78,68,68,68,60,60,60,60,60,60,60`.

Resultado `game11`:

- call index nativo: `144`;
- header estructural: índice `120`, `0x46AF857`;
- inicio: `0x46AF85D`;
- fin/`SQLITE_DONE`: `0x46AFDF1`;
- filas: `13`;
- IDs: `0..12`;
- `grade_order`: `0..12`;
- digest:
  `358D7DB348E81DDEE553DD49734F0463B008AF03EAEAFAF40AEBA87C22165669`;
- referencias de strings sin resolver: `0`.

Consulta de orden:

```sql
SELECT id FROM item_grades ORDER BY grade_order ASC
```

Loaders:

- x64: `FUN_39893a10`;
- x86: `FUN_39968900`;
- layout: `68`.

La consulta de orden sólo carga IDs. El resultado de 16 campos pertenece a la
consulta descriptor. La asociación histórica híbrida quedó preservada como
evidencia supersedida y reconciliada contra las dos consultas correctas; no se
reescribió silenciosamente.

## Catálogo y relaciones

Stage 20 materializa:

- 13 entidades `item_grade`, incluyendo el ID 0 que no aparecía en las
  referencias de quests;
- 13 `native_rows`;
- 208 propiedades, 16 por entidad;
- 13 localizaciones nativas `en_us`:
  `Basic`, `Crude`, `Grand`, `Rare`, `Arcane`, `Heroic`, `Unique`,
  `Celestial`, `Divine`, `Epic`, `Legendary`, `Mythic`, `Eternal`;
- 13 relaciones `item_grade -> uses_icon -> icon`;
- 65 coberturas confirmadas:
  identidad, esquema, propiedades, lifecycle y localización para cada grado.

Los 13 iconos existen confirmados en Stage 60. Stage 90 conserva los edges
originales `unknown` como evidencia de su stage de origen y añade 13 registros
de reconciliación con `resolved_state=confirmed`.

Stage 40 reconstruida:

- `quest_contexts`: 7.826 referencias, 8 IDs;
- `quest_item_group_items`: 418 referencias, 12 IDs;
- `quest_act_obj_item_gathers`: 167 referencias, 2 IDs;
- `quest_act_supply_items`: 98 referencias, 10 IDs;
- `quest_act_supply_selective_items`: 44 referencias, 3 IDs;
- total: 8.553 relaciones confirmadas;
- gaps `item_grade`: 0.

## Mejoras transversales

- El registro legado permite ahora fijar una SQL exacta cuando una tabla tiene
  varias consultas embebidas.
- Stage 90 reconcilia consultas equivalentes confirmadas entre stages.
- Una asociación histórica SQL/columnas incompatible puede supersederse por
  dos consultas canónicas complementarias, dejando un registro auditable.
- El consolidador ya no limita `localizations` a Stage 60; fusiona
  localizaciones válidas de todos los stages.
- Stage 20 queda preservada como owner canónica de `item_grade`; las
  identidades referenciales posteriores no reemplazan su subtipo ni
  procedencia.
- `explain` incluye reconciliaciones cross-stage. Por ejemplo,
  `item_grade:12` muestra `Eternal`, owner Stage 20 y el destino
  `icon:15402` resuelto en Stage 60.

## Stage 90 final

Comparación contra V5:

- raíces causales: `498 -> 465`;
- impactos: `448.732 -> 448.666`;
- entradas de cola: `498 -> 465`;
- raíces `item_grade`: `0`;
- entradas de cola `item_grade`: `0`.

La reducción adicional proviene de 30 asociaciones de consulta equivalentes
reconciliadas de forma demostrable, incluyendo la asociación híbrida de
`item_grades`.

## Artefactos y hashes

Fuentes Ghidra:

- `ghidra-stage90-item-grade-x64.txt`
  - `796887426DF204CDEF933A76ECC7EE7F29ED4B2C6AE398A5CEDC1A612F844334`
- `ghidra-stage90-item-grade-x86.txt`
  - `49501081D388986AEEA77EC2F8B71A634267C2ED80184A33C654984DC6A50A19`
- `ghidra-stage90-item-grade-desc-x64.txt`
  - `6015360C3B00F29AE707DF762B71F8191B77C4AF256B9767AD185617BDF1413B`
- `ghidra-stage90-item-grade-desc-x86.txt`
  - `E8DCA77C5842D107704499C1695A312CEB8ED083ABFA1C42EFE38098D26CFE12`
- `stage90-item-grade-loader-tasks.tsv`
  - `4AA76C959EEF1BFA1F2CAF47138AE1933201003A046A5CA610BB52CAC29EA405`

SQLite:

- item-forensics fuente:
  `36C2A49F90E1B4CE0C1BD3B83A0D6A0261E6222F8A093BEE5087F55DBA3293B8`
- Stage 20:
  `987AAC4AC01D02676653D70C5997F1E85A3235E8EE62E48D67B544073B513CE2`
- Stage 40:
  `27F7FFB2BA3081F25F427FB975B8B1861E01ED6CCE5D225A765C1F7DCB1BF8B4`
- Stage 90:
  `007F2513F618F6EDB6D94C4EC2A9AE160525C3E9822A08EBD2D20901BA6F752A`
- consolidada:
  `D97FF8852CFC63F062DF62CFAF5656CF933BEC3AB93B06A4350758086C788879`
- manifest final:
  `D664A1D3A1C0799E7888D7E27805B3E1E049CDF958FD8FDAB5EFD3F4699FE465`

Reportes:

- `coverage-summary.csv`
  - `BF22413253FB5B48E545D9A386ED1B89B5D19456ED2AE7292B4A67704F3EBF4D`
- `gaps-priority.csv`
  - `82EAA7F111871E64A07D972507F337CDDBDDC483C6424D42FABF2AFA5A9A6ABB`
- `coverage-closure-work-queue.csv`
  - `62185B6EFFD77A1E764E8519DAE724747CEFA7B19BFD52835CDADE5730300EC3`
- `opaque-regions.json`
  - `F56A8F57BCCAF7C8FB1807D5A35013D9C36174F79513AE47036DD9BDC9CB7499`
- `viewer-coverage-closure.html`
  - `85B22DE4C235B2888EFFD43E57774DA35757F3C632BB9594EC07B21C004C0407`

## Aceptación

- 23/23 pruebas Python transversales aprobadas;
- 17/17 pruebas focalizadas item-forensics aprobadas;
- Stage 20 idéntica en dos builds;
- Stage 40 idéntica en dos builds;
- Stage 90 idéntica en dos builds;
- consolidada idéntica en dos builds;
- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- cero huérfanos en propiedades, relaciones, cached results, wiki, blockers y
  work queue;
- linaje completo de nueve stages;
- 13/13 `item_grade` cerrados en todas sus dimensiones forenses conocidas.

## Siguiente frontera recomendada

El catálogo base `item_grade` está cerrado al 100 %. Las tablas con prefijo
similar son superficies distintas y no deben confundirse con el catálogo:

1. `item_grade_buffs`, todavía `query_layout`, rank 238;
2. `item_grade_distributions`, auditoría de estado, rank 388;
3. `item_grade_skills`, auditoría de estado, rank 396.

La siguiente frontera coherente es cerrar `item_grade_buffs` y, en la misma
pasada, resolver las dos auditorías de estado si sus cached results y
consumidores ya observados permiten promoverlas sin decodificación nueva.
Globalmente, la cola conserva `loot_pack` como mayor fan-out, pero esa
superficie sigue bajo evidencia `native_result_absent` y no debe inventarse.
