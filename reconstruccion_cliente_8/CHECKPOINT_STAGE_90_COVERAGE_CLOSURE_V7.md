# Checkpoint Stage 90 V7 — catálogos secundarios `item_grade`

## Alcance

Esta iteración continuó exclusivamente el análisis forense del cliente Kakao
8.0.3.12 r558734. No se modificaron AAEmu, la compact activa, `.env`, MySQL,
Docker ni mecánicas de juego.

La frontera cerrada comprende:

- `item_grade_buffs`;
- `item_grade_skills`;
- `item_grade_distributions`;
- la asociación histórica incorrecta de `item_grade_buffs`;
- la clasificación de todos sus endpoints tipados.

## Corrección de `item_grade_buffs`

La SQL embebida histórica ya declaraba cinco campos:

```sql
SELECT id, buff_id, item_grade_id, item_id, num_pieces
FROM item_grade_buffs
```

Sin embargo, el registro anterior guardaba un layout de cuatro enteros y lo
asociaba por anchor a un bloque ajeno de 103 filas en `game11@0x647EA2C`.
La secuencia SQL nativa, los loaders y los headers estructurales demuestran que
el resultado correcto es:

- call index: `138`;
- header estructural: índice `114`, `0x3F71DBE`;
- inicio: `0x3F71DC4`;
- `SQLITE_DONE`: `0x3F9C8EC`;
- filas: `8.328`;
- layout: `68,68,68,68,68`;
- loader x64: `FUN_39a35750`;
- loader x86: `FUN_39d2e120`;
- digest:
  `18B80E0347939610654F2F788F3F2F8F10F80DD2EA070382E9AA6A3F721A13F1`.

Los IDs son únicos, `item_grade_id` cubre `0..12` y `num_pieces` cubre
`1..4`. Hay 64 filas sin endpoint y en todas ambas columnas, `item_id` y
`buff_id`, valen cero.

La asociación de 103 filas no se eliminó ni reinterpretó silenciosamente:
queda preservada en `source_records` bajo
`superseded_cached_result_associations`, con sus offsets, digest y razón de
supersesión.

## `item_grade_skills`

Consulta:

```sql
SELECT id, item_grade_id, item_id, skill_id
FROM item_grade_skills
```

Autoridad recuperada:

- call index: `139`;
- header: índice `115`, `0x3F9C8EC`;
- inicio: `0x3F9C8F2`;
- `SQLITE_DONE`: `0x3F9C97A`;
- filas: `8`;
- IDs: `8..15`;
- grados: `5..12`;
- loader x64: `FUN_39a35a00`;
- loader x86: `FUN_39d2e340`;
- digest:
  `F8C878652F5FA5F39513755A731952CF884C007AEACD7902EEFD640DE76F770D`.

Las ocho referencias de skill se conservaron inicialmente como relaciones
referenciales de Stage 20 y Stage 90 las reconcilió contra las entidades
nativas confirmadas de Stage 50.

## `item_grade_distributions`

Consulta:

```sql
SELECT id, weight_0, weight_1, weight_2, weight_3, weight_4,
       weight_5, weight_6, weight_7, weight_8, weight_9,
       weight_10, weight_11, weight_12
FROM item_grade_distributions
```

Autoridad recuperada:

- call index: `145`;
- header: índice `121`, `0x46AFDF1`;
- inicio: `0x46AFDF7`;
- `SQLITE_DONE`: `0x46B0919`;
- filas e IDs: `50`, IDs `1..50`;
- layout: catorce enteros;
- loader x64: `FUN_39a369f0`;
- loader x86: `FUN_39d2efa0`;
- digest:
  `E977A488392208F7F16DCC97255B420AA7E8309B855118A110829BAC578F22E2`.

Las trece ponderaciones de cada fila suman exactamente 100. Se proyectaron
143 relaciones no nulas hacia los grados correspondientes.

## Clausura de endpoints y grafo

Stage 20 materializa:

- 8.386 `native_rows` y entidades confirmadas:
  - 8.328 `item_grade_buff`;
  - 8 `item_grade_skill`;
  - 50 `item_grade_distribution`;
- 42.372 propiedades con procedencia por campo;
- 41.930 coberturas confirmadas;
- 25.023 relaciones:
  - 24.856 desde `item_grade_buffs`;
  - 24 desde `item_grade_skills`;
  - 143 desde `item_grade_distributions`;
- seis consumidores, un loader x86 y otro x64 por consulta;
- tres catálogos nativos completos.

El cierre negativo usa los catálogos completos, no una ausencia parcial:

- 95 IDs de item referenciados no existen en el catálogo completo de items;
- 36 IDs de buff referenciados no existen en el catálogo completo de buffs;
- ambos conjuntos quedan como `tombstone`, nunca como `missing` inferido;
- no quedan endpoints silenciosamente descartados.

## Stage 90 final

Comparación contra V6:

- raíces causales: `465 -> 462`;
- entradas de cola: `465 -> 462`;
- reconciliaciones de consulta: `30 -> 33`;
- reconciliaciones de relaciones: `81.090 -> 81.098`;
- raíces de `item_grade_buffs`: `0`;
- raíces de `item_grade_skills`: `0`;
- raíces de `item_grade_distributions`: `0`.

Las tres raíces eliminadas corresponden exactamente a las consultas
secundarias cerradas. La regla transversal nueva sólo acepta una proyección
histórica mal formada cuando existe una consulta canónica con columnas SQL
completas, resultado confirmado, offset y consumidor nativo.

## Artefactos y hashes

Evidencia Ghidra:

- `ghidra-stage90-item-grade-secondary-x64.txt`
  - `1D1B2A422FD689879D02BCFD0BDC70E05F5C8DFFEAECD3986808E55E2E66E70A`
- `ghidra-stage90-item-grade-secondary-x86.txt`
  - `68FF47EFBD6D12546A91673B5FFE6AF3088C07EAD8AC5A6275448EA5675328BE`
- `stage90-item-grade-secondary-loader-tasks.tsv`
  - `12D1BFC37E40132AE68625367B4626D6B281F01981099CF86C5D7EDE8654844D`

SQLite:

- Stage 20:
  `8CC3692EFAD2A00C67CBF46FBDC6B8187D315FEEFFA5F3F9EEF5F82C34C62C65`
- Stage 90:
  `E944FF3C4B969837254021E82BDC050DD6BAAE3B38134FE271574BF888769653`
- consolidada:
  `FA1E775300B980DD95430F385D8D8B388B42464638DEF0703DA9F05EF05AFBE9`
- manifest final:
  `48732F7B17865704D3C17B6213193C95E71CF8B3BA2871BF1CFF56E0FB1022BC`

Reportes:

- `coverage-summary.csv`
  - `E83DF2501CF10A309B1884019B20C323E9D203831DB1987E1D1386BCD28C970A`
- `coverage-closure-work-queue.csv`
  - `D7EEAA55D4F02CDFEAA8250A59CFDE30C060AFE3F3A729C0E4E2277EC1AEBE0C`
- `viewer-coverage-closure.html`
  - `3EB0938C9F5458703EF04123EA8E9C521BC54ADDDA3BD157FC3759692B4CBA1F`

## Aceptación

- 25/25 pruebas Python transversales aprobadas;
- 2/2 pruebas focalizadas del registro de queries aprobadas;
- Stage 20 idéntica en dos builds;
- Stage 90 idéntica en dos builds;
- consolidada idéntica en dos builds;
- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- cero huérfanos en propiedades, relaciones, cached results, wiki, blockers y
  work queue;
- 1.657.484 entidades;
- 6.950.412 propiedades;
- 2.113.623 relaciones;
- 462 raíces causales y 462 entradas de cola.

## Siguiente frontera recomendada

`loot_pack` continúa primero por fan-out, pero ya está demostrado como
`native_result_absent` en los doce streams y no debe completarse sin una nueva
fuente de autoridad.

La siguiente frontera con mejor relación certeza/impacto es el bloque escalar
de quests:

1. `quest_name_kind`: 3 IDs y 1.673 referencias;
2. `quest_context_text_kind`: 5 IDs y 918 referencias.

Ambos deben investigarse juntos desde switches, consumidores, RTTI, DLL y
scripts x86/x64. Si son enums inline, se materializarán con la misma política
usada para `quest_detail`; si existe una tabla cached, se recuperará su
resultado completo. No se inferirán etiquetas desde nombres de servidor ni
desde datos históricos.
