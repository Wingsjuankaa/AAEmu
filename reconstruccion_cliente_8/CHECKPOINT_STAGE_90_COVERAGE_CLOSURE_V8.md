# Checkpoint Stage 90 V8 — kinds escalares de texto de quests

## Alcance

Esta iteración continuó exclusivamente el análisis forense del cliente Kakao
8.0.3.12 r558734. No se modificaron AAEmu, la compact activa, `.env`, MySQL,
Docker ni mecánicas de juego.

La frontera cerrada comprende:

- `quest_name_kind`: 3 IDs y 1.673 referencias;
- `quest_context_text_kind`: 5 IDs y 918 referencias;
- los loaders, accessors y consumidores x86/x64;
- la clasificación negativa del único valor sin consumidor dedicado.

## Naturaleza de los dominios

No existen consultas ni tablas propietarias `quest_name_kinds` o
`quest_context_text_kinds`. Ambos dominios son enums escalares inline:

```sql
SELECT id, name, quest_context_id, quest_name_kind_id
FROM quest_names

SELECT id, quest_context_text_kind_id, quest_context_id, text
FROM quest_context_texts
```

Los layouts son cuatro enteros/string según el orden SQL y tienen paridad
x86/x64:

- `quest_names`
  - loader x64: `FUN_399e2620`;
  - loader x86: `FUN_39c4dcb0`;
  - filas: 1.673.
- `quest_context_texts`
  - loader x64: `FUN_399e2380`;
  - loader x86: `FUN_39c4da90`;
  - filas: 918.

## `quest_name_kind`

El binding de API, los accessors y los sinks nativos confirman:

| ID | Etiqueta canónica | Referencias | Consumidor x64 | Consumidor x86 |
|---:|---|---:|---|---|
| 1 | `journal_subtitle` | 764 | `FUN_39770aa0` | `FUN_397a63d0` |
| 2 | `journal_progress_title` | 108 | `FUN_39770c30` | `FUN_397a65c0` |
| 3 | `journal_summary` | 801 | `FUN_3977c850` | `FUN_397b0860` |

Los IDs 1 y 2 están ligados respectivamente a
`GetQuestJournalSubTitleByType` y `GetQuestJournalProgTitleByType`. El ID 3
alimenta el campo `summary` del builder nativo del journal en ambas
arquitecturas.

Estas etiquetas contradicen la interpretación histórica de servidor que
trataba los valores como estados `Complete/Fail/Ready`. Esa interpretación no
se importó.

## `quest_context_text_kind`

Los accessors nativos confirman:

| ID | Etiqueta canónica | Referencias | Consumidor x64 | Consumidor x86 |
|---:|---|---:|---|---|
| 1 | `context_summary` | 36 | `FUN_39772670` | `FUN_397a7d80` |
| 2 | `context_body` | 10 | `FUN_397727b0` | `FUN_397a7f90` |
| 3 | `context_accept_text` | 698 | `FUN_397728f0` | `FUN_397a81a0` |
| 4 | `context_report_text` | 173 | `FUN_39772a30` | `FUN_397a83b0` |
| 5 | `media_fixture` | 1 | no aplicable | no aplicable |

Los bindings de los primeros cuatro valores son
`GetQuestContextSummary`, `GetQuestContextBody`,
`GetQuestContextAcceptText` y `GetQuestContextReportText`.

El ID 5 no se promovió a una capacidad activa. Su única fila nativa es:

```text
id=1483
quest_context_id=598
quest_context_text_kind_id=5
text="문장들 - media"
```

La quest 598 es un fixture tutorial/development. Se auditaron los 186 callers
del accessor x64 `FUN_399c2190` y los 192 callers del accessor x86
`FUN_39ba2020`; no existe una comparación dedicada contra el valor 5. Por
ello su entidad queda `confirmed`, su lifecycle es `dormant_fixture` y la
dimensión de consumidor es `not_applicable`. La etiqueta `media_fixture`
procede del literal nativo, no de un enum histórico.

## Materialización y clausura

Stage 40 añade:

- 8 entidades `inline_scalar_enum` confirmadas;
- 40 propiedades con procedencia por campo;
- 14 consumidores, uno x86 y otro x64 para cada valor activo;
- 48 filas de cobertura dimensional;
- 1.673 relaciones `has_name_kind` confirmadas;
- 918 relaciones `has_text_kind` confirmadas;
- cero gaps y cero endpoints huérfanos para ambos dominios.

La relación `has_text_kind` también se usa para
`quest_component_text_kind`; por eso las métricas de esta frontera siempre se
filtran por kind de destino y no sólo por nombre de relación.

## Stage 90 final

Comparación contra V7:

- raíces causales: `462 -> 456`;
- entradas de cola: `462 -> 456`;
- raíces de `quest_name_kind`: `3 -> 0`;
- raíces de `quest_context_text_kind`: `3 -> 0`;
- reconciliaciones de consulta: 33;
- reconciliaciones de relaciones: 81.098.

Las seis raíces eliminadas corresponden exactamente a:

- endpoint referenciado ausente de stages previas;
- entidad desconocida;
- relación desconocida;

para cada uno de los dos kinds. No desapareció ninguna raíz ajena.

## Artefactos y hashes

Evidencia Ghidra:

- `ghidra-stage90-quest-scalar-api-x64.txt`
  - `0AB97D5F594A205B568E9F8B7214FF7E9B715DE6A1FE7DDF6900F48667BAA305`
- `ghidra-stage90-quest-scalar-consumers-x64.txt`
  - `B1BD3BACCC3929EB6016CC460B55950135E728BF79019FCF9188AB44C6A6F3D4`
- `ghidra-stage90-quest-scalar-consumers-x86.txt`
  - `926726A987FF0F8A7AD887B828027BD862633CE02D7B3297841AC6520B0AA3D0`

SQLite:

- Stage 40:
  `E568FA9726A3B2DF78554367FF3692CAF69A57FDF5FD54D51B11F1D51075A3FB`
- Stage 90:
  `164A154A424589161F77DEE2FCD675E540079F25C072DEDA2AAA7E833FA5CE17`
- consolidada:
  `640E894031240EDC5CB83A38BA1E5DF0F839D3D0245DA9AB20C56C0A74699BD9`
- manifest final:
  `CA818C937CC52EF6E837050D671BF5937489A6447B87908FC1A2787A474363BD`

Reportes:

- `coverage-summary.csv`
  - `AB056EA1C03EA13C81BA9E76F7B05685D38A13CC07E4FF582077490AD48DD591`
- `coverage-closure-work-queue.csv`
  - `0A8DB7C4F6D7CC72EDD485D9D91EB8B5E459F3053AA1B0A0D16D19A43B49C7D7`
- `viewer-coverage-closure.html`
  - `875CA8A7BB02173B48FC7C1413E13619440B5ABD415B028A9FFA700471092FD0`

## Aceptación

- 25/25 pruebas Python transversales aprobadas;
- Stage 40 idéntica en dos builds;
- Stage 90 idéntica en dos builds;
- consolidada idéntica en dos builds;
- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- cero huérfanos en propiedades, relaciones, cached results, wiki, blockers y
  work queue;
- 1.657.484 entidades;
- 6.950.452 propiedades;
- 2.113.623 relaciones;
- 456 raíces causales y 456 entradas de cola.

## Siguiente frontera recomendada

La siguiente frontera de descifrado puro es cerrar conjuntamente las
etiquetas semánticas de los otros tres enums inline ya materializados:

1. `quest_component_text_kind`: 3 IDs y 13.531 referencias;
2. `chat_bubble_kind`: 3 IDs y 25.939 referencias;
3. `npc_ai`: 5 IDs y 32.191 referencias.

Sus identidades y aristas ya están confirmadas, pero comparten la región opaca
`native_enum_semantic_labels_not_yet_recovered`. Deben resolverse desde
switches, callbacks/UI, RTTI y consumidores x86/x64, manteniendo separados los
3.342 parámetros `npc_ai_param`/`npc_ai_client_param` todavía desconocidos.
