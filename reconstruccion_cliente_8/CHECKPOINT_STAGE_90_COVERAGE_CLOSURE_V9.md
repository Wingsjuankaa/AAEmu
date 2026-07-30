# Checkpoint Stage 90 V9 — semántica inline de quests y chat

## Alcance

Esta iteración continuó exclusivamente el análisis forense del cliente Kakao
8.0.3.12 r558734. No se modificaron AAEmu, la compact activa, `.env`, MySQL,
Docker ni mecánicas de juego.

La frontera comprende:

- `chat_bubble_kind`: cierre semántico total de 3 IDs y 25.939 referencias;
- `quest_component_text_kind`: cierre del ID 4 y evidencia negativa para los
  IDs 5 y 6, sobre 13.531 referencias;
- `npc_ai`: correlación estructural de 5 IDs y 32.191 referencias, sin promover
  candidatos a semántica confirmada;
- consumidores x86/x64, consumidores Lua y regiones opacas por ID;
- propagación reproducible hacia Stage 90 y la consolidada.

## `chat_bubble_kind`

El registro nativo liga exactamente:

| ID | Constante | Etiqueta canónica | Referencias |
|---:|---|---|---:|
| 1 | `CBK_NORMAL` | `normal` | 25.192 |
| 2 | `CBK_THINK` | `think` | 151 |
| 3 | `CBK_SYSTEM` | `system` | 596 |

Los bindings son:

- x64: `FUN_396ec170(param_1, "CBK_*", id)`;
- x86: `FUN_390f7aa0("CBK_*", id)`.

`x2ui/chat/chatbubble.lua` contiene las tres ramas de renderizado.
`x2ui/questcontext/quest_context_directing.lua` confirma además que
`CBK_THINK` envuelve el texto en paréntesis y que `CBK_SYSTEM` usa la
presentación de sistema sin autor ordinario.

Los tres valores quedan con propiedad `semantic_label` en estado `confirmed`.
La región opaca completa de este dominio se elimina.

## `quest_component_text_kind`

El accessor del kind es:

- x64: `FUN_399e1040`, con 61 callers auditados;
- x86: `FUN_39c22de0`, con 60 callers auditados.

Sólo existe una comparación conductual en ambas arquitecturas:

| ID | Etiqueta canónica | Referencias | Consumidores x64 | Consumidores x86 |
|---:|---|---:|---|---|
| 4 | `objective_description` | 13.525 | `FUN_39774350`, `FUN_39776910`, `FUN_397786a0`, `FUN_3977c850` | `FUN_397aa1d0`, `FUN_397ac9a0`, `FUN_397ae2a0`, `FUN_397b0860` |
| 5 | opaco | 4 | ninguno dedicado | ninguno dedicado |
| 6 | opaco | 2 | ninguno dedicado | ninguno dedicado |

Los cuatro consumidores del ID 4 alimentan los sinks nativos `description` o
`summary`. El conjunto completo de comparaciones recuperado es exactamente
`{4: 4}` en x64 y `{4: 4}` en x86.

El ID 5 conserva cuatro filas fixture nativas:

```text
start - Texts - body
progress - Texts - body
ready - Texts - body
reward - Texts - body
```

El ID 6 conserva dos filas nativas, pero ninguna comparación dedicada. Los IDs
5 y 6 continúan en `opaque_regions`; ni sus textos ni una enumeración histórica
se usan para inventar etiquetas.

## `npc_ai`

La distribución nativa observada es:

| ID | Referencias | Evidencia estructural | Estado semántico |
|---:|---:|---|---|
| 1 | 32.139 | sin discriminador exclusivo recuperado | opaco |
| 2 | 3 | sin discriminador exclusivo recuperado | opaco |
| 3 | 18 | 18/18 con `ai_path_type_id > 0`; 17 con path no vacío | candidato `follow_path` |
| 4 | 4 | sin discriminador exclusivo recuperado | opaco |
| 6 | 27 | 27/27 con `ai_command_set_id > 0` | candidato `run_command_set` |

Los candidatos de los IDs 3 y 6 se materializan como
`semantic_candidate`, autoridad `client_native`, estado `corroborated`. No se
materializa ninguna propiedad `semantic_label` para `npc_ai`.

El switch `FUN_39628bd0`, inicialmente compatible por rango 1..6, fue
descartado tras recuperar su contexto: consume estados de plot/quest y no el
campo `npc_ai_id`. Esta evidencia negativa evita una asignación falsa.

## Implementación forense

Se añadió:

- `client_forensics/quest_inline_semantics.py`, auditor estricto de bindings,
  callers, fixtures, invariantes estructurales y evidencia negativa;
- `ghidra/DumpAa8RangeTokenMatches.java`, script reutilizable para decompilar un
  rango y conservar sólo funciones que cumplan tokens requeridos/opcionales;
- dos fuentes Ghidra configurables para los callers del accessor de
  `quest_component_text_kind`;
- artifacts individuales para los consumidores Lua;
- materialización de labels confirmadas, candidatos corroborados, consumers
  por arquitectura y regiones opacas parciales.

La herramienta queda en versión `0.16.0`.

## Efecto en el grafo consolidado

Comparación contra V8:

- entidades: `1.657.484 -> 1.657.484`;
- propiedades: `6.950.452 -> 6.950.458`;
- relaciones: `2.113.623 -> 2.113.623`;
- consumidores: `104 -> 118`;
- regiones opacas: `92 -> 91`;
- cobertura: `544.827 -> 544.827`;
- raíces causales: `456 -> 456`;
- cola de trabajo: `456 -> 456`.

La cola no disminuye porque `chat_bubble_kind.semantic_labels` no era una raíz
causal independiente en Stage 90. La mejora es semántica y auditable, no un
incremento artificial de cobertura por entidad. Los candidatos `npc_ai`
tampoco cuentan como cierre.

## Artefactos y hashes

Evidencia principal:

- `ghidra-stage90-enum-consumers-x64.txt`
  - `C8CAA33F3E14564F2D0421DA65E7F1331D44964BE7BBDCD4523D80B13F147460`
- `ghidra-stage90-enum-consumers-x86.txt`
  - `8FE213FFC9091DA9AB3798F5785A6F5468CBC5D369E44EE5C5ECFDE12172D624`
- `ghidra-stage90-v9-component-accessor-context-x64.txt`
  - `121C2A4AFAEDE5DD5152648E3975D584DFB79425B741FE1F71B6E8001ED81102`
- `ghidra-stage90-v9-component-accessor-context-x86.txt`
  - `DF472B3680BF2CD61265931C2A10407BC87765D4C06D8B27566D4703CCA2C19C`
- `x2ui/chat/chatbubble.lua`
  - `44A5F9178248F156ABAC742C2DDFA6D63D329932869A2FAEA68EA95FC3AAE311`
- `x2ui/questcontext/quest_context_directing.lua`
  - `AEF717D9D4278AFFFC3FD7EE5CB5025B760B9CF4ED9C18D0AE462E208DA1B8FF`

SQLite y manifests:

- Stage 40:
  `FAF039678A277EDF5177536EFEA1F53A6C44C1F55404EAC12940D1B41528521C`
- manifest Stage 40:
  `E38184882556379503D629E5245D314AE1A6A87A4CECFF25FF41FCA153CFB287`
- Stage 90:
  `3F1A996BD65E21F26A8087AB3B42717DFFBEC58E7E7AC54A0BFB0B5124395E34`
- manifest Stage 90:
  `C00C1351E5813D61A38955FB665B8DE3F0F4F8BA2F228A196960A3C67583F247`
- consolidada:
  `4622A0C37386AA1890EA01AF6119195B6F0DF063B3368B1F1C544988BD7C13FF`
- manifest de la consolidada:
  `3108532EC98CFF84B969D18613F786E5E2C8F067970D3F7837CAADBAE6600701`
- manifest final:
  `D49BFDE0A52CB8003E04FA1711894707FEF4335FB94AFB8438BEEC879774F1E7`

Reportes:

- `coverage-summary.csv`
  - `AB056EA1C03EA13C81BA9E76F7B05685D38A13CC07E4FF582077490AD48DD591`
- `coverage-closure-work-queue.csv`
  - `5F7E671A5D7CF2D4597742F42AE601F58B07C7C104D91B1E6EC2C8FAD76E9382`
- `viewer-coverage-closure.html`
  - `DFF1D2F6630812ADFF55A6D3029157B5A1D980B589DF2AA90917C79FC20880EA`

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
- 6.950.458 propiedades;
- 2.113.623 relaciones;
- 456 raíces causales y 456 entradas de cola.

## Siguiente frontera recomendada

La siguiente frontera de descifrado puro debe profundizar en los dos residuos
que esta iteración dejó delimitados:

1. seguir `npc_ai_id` desde el layout de `quest_components` hasta el consumidor
   conductual que despacha path, command set y los casos 1/2/4, con paridad
   x86/x64;
2. demostrar si `quest_component_text_kind` 5 y 6 son fixtures/tombstones
   inalcanzables o si existe un consumidor fuera de los 61/60 callers ya
   auditados.

La ruta estática prioritaria es seguir el campo del componente hacia los
builders/eventos y serializers que lo copian. Si la estática sigue sin exponer
el dispatch, la siguiente evidencia autorizada es instrumentación local,
no persistente, de los accessors del cliente. Wiki, AAEmu histórico y nombres
humanos sólo pueden corroborar; no pueden cerrar esta frontera.
