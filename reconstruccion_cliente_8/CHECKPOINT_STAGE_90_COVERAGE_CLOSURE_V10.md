# Checkpoint Stage 90 V10 — frontera `npc_ai_id`

## Alcance

Esta iteración continuó exclusivamente el análisis forense del cliente Kakao
8.0.3.12 r558734. No se modificaron AAEmu, la compact activa, `.env`, MySQL,
Docker ni mecánicas de juego.

La frontera comprende:

- layout y copia de `quest_components.npc_ai_id` en x86/x64;
- 121 callers del accessor de componentes;
- reenvíos del puntero a 18 helpers únicos;
- accesos directos al vector crudo de componentes;
- bindings y cuerpos nativos de las APIs AI expuestas a Lua;
- barrido congelado de DLL/EXE, Lua y XML;
- materialización de evidencia negativa en Stage 40, Stage 90 y la consolidada.

## Conclusión

`npc_ai_id` es un campo nativo confirmado que el cliente carga, copia y
conserva, pero no ejecuta por ninguno de los caminos estáticos recuperados.

Los bindings relacionados son stubs explícitos en ambas arquitecturas:

```text
ScriptBindUnit::NpcFollowUnit() we don't support this for client!
ScriptBindUnit::NpcFollowPath() we don't support this for client!
ScriptBindUnit::NpcOnEndedFollowPath() we don't support this for client!
```

Por tanto:

- la presencia, membresía y 32.191 referencias del dominio están confirmadas;
- el estado de implementación cliente es `explicitly_unsupported`;
- la autoridad conductual servidor-side queda `corroborated`, no `confirmed`;
- no se materializan labels humanos;
- `3 → follow_path` y `6 → run_command_set` continúan como candidatos
  estructurales `corroborated`;
- los IDs 1, 2, 3, 4 y 6 permanecen semánticamente abiertos hasta hallar
  autoridad nativa de servidor/protocolo.

## Layout x86/x64

| Arquitectura | Loader | Copy | Tamaño | Offset `npc_ai_id` | Slot |
|---|---|---|---:|---:|---|
| x64 | `FUN_399f3a80` | `FUN_399e1670` | `0xd0` | `0x28` | `uint32[10]` |
| x86 | `FUN_39c64770` | `FUN_39c2f380` | `0x80` | `0x20` | `uint32[8]` |

El desplazamiento cambia únicamente por el tamaño de los campos puntero
anteriores. El orden lógico de columnas es idéntico.

## Clausura de consumidores

### Accessor canónico

| Arquitectura | Accessor | Callers | Cargas del campo | Reenvíos | Fallos decompilación |
|---|---|---:|---:|---:|---:|
| x64 | `FUN_399e1040` | 61 | 0 | 43 | 0 |
| x86 | `FUN_39c22de0` | 60 | 0 | 40 | 0 |

Los reenvíos alcanzan 10 helpers únicos en x64 y 8 en x86. La inspección de
todos ellos tampoco encuentra una lectura de `npc_ai_id`.

### Vector crudo

El camino alternativo que evita el accessor también fue cerrado:

- x64: el vector vive en `manager+0x14228`, usa stride `0xd0` y sólo
  `FUN_399f5cb0` recorre sus filas fuera de inicialización. Lee
  `quest_context_id` en `+0x34`, no `npc_ai_id` en `+0x28`;
- x86: el vector vive en `manager+0xfa7c`, usa stride `0x80` y
  `FUN_39c66050` lee `quest_context_id` en `+0x2c`, no `npc_ai_id` en `+0x20`.

Resultado agregado: cero lecturas conductuales directas, reenviadas o por
vector crudo.

## Scripts, DLL y otras superficies

El snapshot `AA8_NPC_AI_SURFACE_SNAPSHOT_V1` cubre:

| Superficie | Archivos | Bytes | Archivos con coincidencias |
|---|---:|---:|---:|
| bin32 DLL/EXE | 112 | 369.707.768 | 4 |
| bin64 DLL/EXE | 99 | 361.428.600 | 4 |
| Lua 64 | 1.112 | 8.578.461 | 15 |
| Lua 32/mixto | 2.224 | 17.156.922 | 30 |
| XML | 7.698 | 619.822.805 | 5 |
| **Total** | **11.245** | **1.376.694.556** | **58** |

Hallazgos:

- `x2game.dll` es la única DLL de gameplay con `npc_ai`, bindings
  `NpcFollow*` y las consultas `npc_ai_*`;
- `cryaisystem.dll` y `cryaction.dll` contienen superficies genéricas
  `AICommandSet`/`followpath`, sin vínculo con el enum de quest;
- el match `goaway` de `libcef.dll` es incidental y no tiene autoridad de
  gameplay;
- Lua contiene `follow_path.lua`, `follow_unit.lua`,
  `run_command_set.lua` y `x2ai_command_set.lua`, pero sus llamadas aterrizan
  en los stubs cliente documentados;
- los cinco XML encontrados son SmartObjects/ActionGraphs genéricos de
  `FollowPath`; ninguno relaciona IDs `npc_ai`;
- `attackunit` no aparece en las superficies nativas buscadas.

El snapshot se generó dos veces con SHA-256 idéntico:

`340E4E2C608315576B50EB62B306EE46BB0481D753B564E32B6CF50BBB21EFEF`.

## Estado canónico

Cada una de las cinco entidades `npc_ai` incorpora:

- `client_field_present=true`, `confirmed`;
- `client_direct_field_loads=0`, `confirmed`;
- `client_behavior_implementation=explicitly_unsupported`, `confirmed`;
- `behavior_authority=server_side`, `corroborated`.

No existe ninguna propiedad `semantic_label`. Sólo existen:

| ID | Referencias | Candidato |
|---:|---:|---|
| 1 | 32.139 | ninguno |
| 2 | 3 | ninguno |
| 3 | 18 | `follow_path`, `corroborated` |
| 4 | 4 | ninguno |
| 6 | 27 | `run_command_set`, `corroborated` |

Stage 90 separa esta superficie en la raíz
`client_explicitly_unsupported_behavior`, categoría `negative_evidence`,
disposición `audit_required`, rank 423. La acción recomendada prohíbe repetir
el barrido cliente o promover enums históricos: el siguiente dato válido debe
provenir de servidor/protocolo nativo.

## Implementación forense

Se añadió o amplió:

- `client_forensics/npc_ai.py`: auditor estricto de layout, trazas, helpers,
  vector crudo, bindings, stubs y snapshot;
- `client_forensics/quest_inline_semantics.py`: integración de la auditoría;
- `client_forensics/stage40.py`: artifacts, propiedades y región opaca
  especializada;
- `client_forensics/stage90.py`: clasificación causal y recomendación de
  autoridad;
- `tools/scan_npc_ai_surfaces.py`: snapshot determinista transversal;
- `ghidra/TraceAa8AccessorField.java`: trazado P-code reutilizable del campo;
- configuración explícita de 12 nuevas fuentes;
- pruebas de paridad, ausencia de cargas y stubs cliente.

La herramienta queda en versión `0.17.0`.

## Efecto en el grafo consolidado

Comparación contra V9:

- entidades: `1.657.484 → 1.657.484`;
- propiedades: `6.950.458 → 6.950.478`;
- relaciones: `2.113.623 → 2.113.623`;
- consumidores: `118 → 118`;
- regiones opacas: `91 → 91`;
- cobertura: `544.827 → 544.827`;
- artifacts: `+12`;
- raíces causales: `456 → 457`;
- cola de trabajo: `456 → 457`.

La raíz adicional no representa una regresión. Separa el límite
cliente explícitamente demostrado de la antigua raíz genérica de labels
desconocidos. No hay incremento artificial de cobertura: la dimensión de
consumo cliente queda cerrada, pero la semántica del enum continúa abierta.

## Artefactos y hashes

Evidencia Ghidra:

- field trace x64:
  `7B67685F50452FE96FCD5ED4CC7E4AC6D3E05CE001A880B1417B793DB440673D`;
- field trace x86:
  `BACEAF70B53B218D6AC788CDB5A84AD3DDF2B75D9DFD5040044DF320C21E8A29`;
- helpers x64:
  `9E1501E3FB3A0B13C0671D0E52BA4C484EB2F43F94DA28CFD55972E74CE654E1`;
- helpers x86:
  `022494C57B037EE585AFEF0B5487E0F61CEFA3131143CDB6DD949E80FBE8D0D0`;
- vector crudo x64:
  `E10735FCEA4D1436EF5B83080E8A1F636EC03C4FCD3E846ADD69FA382D00AA56`;
- vector crudo x86:
  `1E97C81C9950E0D2C26729FBFFD12A880D7E3117A9EA5C5456ADC23D9FB7E6D6`;
- copy x86:
  `E6AD201F497B9A04B84D0EDDC8DD8109AA5D90B2BCBE3B8BC6CF257532BF951A`;
- bindings x64:
  `C7DD9C4B43AC52A1EE72050E7E7E2FF9F1B721C2A342CC5E4562BC88F29456A7`;
- bindings x86:
  `7B71B7EB4D1C99A04227727F14E1204FA1119AE58D378F211242B28E8CD60F4D`;
- stubs x64:
  `E53D38DC16D5DC88053C5AE7BFCC81DE95C599A53A8F031BE3CB78DA1A622356`;
- stubs x86:
  `B19811723CE4D98AE98489FEBB7A6D46D549F1301151CE851CDF268660D08342`.

SQLite y manifests:

- Stage 40:
  `677BD050AC89202A656B85B8E42DD01F07633BE5A47A1B7DDD0FB9424B062FC2`;
- manifest Stage 40:
  `D41C47280F5C57A1569C455D65479B702FAF9F41B0E5D79E5E90E671C907E34E`;
- Stage 90:
  `D7A7AE520A9BCEE024C21C6D8A13222EDD42EEA6277FBC61DC5FD5B9E4EFADD2`;
- manifest Stage 90:
  `5B86F7814918390CE1BA901F0B46561C7533C4F10673D9551076CA59474FCE44`;
- consolidada:
  `C385E79C059392B6EF861A2014CE08FB71D841811050F653C23F78D630AAEA5E`;
- manifest de la consolidada:
  `980683D0859BB83107E88F8BC6F488F4C8D850779B21CB6171F159DB93A75703`;
- manifest final:
  `4C63B0F3BC8E0D734F78521F301292A457B5F4859C76BE5C30C31576AE5F43E3`.

Reportes:

- `coverage-summary.csv`:
  `AB056EA1C03EA13C81BA9E76F7B05685D38A13CC07E4FF582077490AD48DD591`;
- `coverage-closure-work-queue.csv`:
  `F3A3DD0752603616C6A843BC450B31CCA58CF0184B7A98765E63D1B8470EE552`;
- `viewer-coverage-closure.html`:
  `015A0AF080464DF3C681E8338DAE65AB77A77EFD3943799C0C9AF9F91E7D5E09`.

## Aceptación

- 25/25 pruebas Python transversales aprobadas;
- snapshot de 11.245 archivos idéntico en dos ejecuciones;
- Stage 40 idéntica en dos builds;
- Stage 90 idéntica en dos builds;
- consolidada idéntica en dos builds;
- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- cero huérfanos en propiedades, relaciones, cached results, wiki, blockers y
  work queue;
- 1.657.484 entidades;
- 6.950.478 propiedades;
- 2.113.623 relaciones;
- 457 raíces causales y 457 entradas de cola.

## Siguiente frontera recomendada

La siguiente frontera puramente cliente debe cerrar
`quest_component_text_kind` 5 y 6:

1. rastrear las colecciones de textos que reciben los componentes, no sólo los
   61/60 callers del accessor;
2. buscar constructores, serializers y fixtures de tooling que puedan consumir
   esos valores fuera del runtime UI;
3. demostrar si son fixtures/tombstones inalcanzables y, si lo son,
   clasificarlos como tales sin inventar labels.

Continuar los nombres de `npc_ai` requiere autoridad nativa servidor/protocolo
y queda fuera de esta skill cliente hasta que exista esa evidencia.
