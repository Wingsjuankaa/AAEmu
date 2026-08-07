# Checkpoint — reconstrucción nativa Nuia Story V2

Fecha: 2026-08-01  
Branch: `client_version/8.0.3.12-kakao-r558734-port`  
Base observada: `c911b746`

## Resultado alcanzado

Se extendió el compilador acumulativo sobre el runtime V1 inmutable y se
inventariaron las 294 quests Nuia hasta la terminal 10682. La SQLite forense,
sus manifests y MySQL no fueron modificados.

El runtime V1 sigue siendo el prefijo exacto de 55 quests. El compilador V2:

- clasifica los 1.294 components y 1.354 acts de los 27 tipos nativos;
- conserva cada `detail_row_json` y todos los roles, cantidades, grados y
  flags de items;
- materializa únicamente quests `ready`;
- registra blockers y `recommended_stop_point` para toda quest no ejecutable;
- impide que una quest bloqueada entre en las tablas ejecutables;
- produce builds deterministas desde V1, nunca desde una copia del candidato
  anterior.

## Implementación transversal

- Loaders y comportamiento para `CheckCompleteComponent`, timers,
  `ConAcceptComponent`, NPC groups, report NPC groups, doodad phase checks,
  objective effect fire, cinemas, spheres y talk.
- Closure exacta de la vertical 7115, incluido item 47879, skill 42069,
  effects, NPC 11283/8853/15558 y return point 999.
- Materialización acumulativa de items, NPC templates/modelos/grupos,
  client-doodads y objective effects AA8.
- Proxies auditados de return point 708, 863, 927, 998 y 999, derivados de
  endpoints y spawns únicos nativos; no se inventaron coordenadas para los
  return points sin evidencia.
- Reductor de buffs que conserva filas, triggers y tick effects AA8, sigue
  referencias recursivas y trata iconos/FX solamente como presentación del
  cliente con evidencia explícita.
- Traducción explícita de campos AA8 `combat_resource_*` a los nombres
  históricos `high_ability_resource_*` del loader, conservando sus valores.
- Reconstrucción de `SpecialEffect 27 / GainItem` mediante la ruta persistente
  `Inventory.TryAddNewItem(ItemTaskType.SkillEffectGainItem, ...)`.

## Runtime completo auditado (no desplegado)

Archivo:

`D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-nuia-story-v2-chapter31.sqlite3`

SHA-256:

`009D820472DD6F09E57511E6C1FEF663D336CC4AFE1073DDB5F4691B9E722F31`

Estado:

- 207 quests `ready`;
- 87 quests `blocked` con evidencia exacta;
- 0 `pending_validation`;
- 0 quests bloqueadas materializadas;
- `quick_check=ok` e `integrity_check=ok`;
- quest 10159 conservada como prerrequisito lateral de 10039;
- las cuatro transiciones obligatorias preservadas;
- 10682 demostrada como terminal por cuatro auditorías independientes.

Blockers restantes:

| Tipo | Filas | Causa |
|---|---:|---|
| `missing_npc_spawn_relation` | 109 | 55 NPC sin relación/coordenadas AA8; tampoco existen en el compact legacy compatible. |
| `item_definition_not_creatable` | 23 | Buffs no cerrados, skills de item sin effect-set nativo o return points sin coordenadas. |
| `missing_doodad_use_skill_closure` | 11 | Skills de uso con closure ejecutable incompleta. |
| `missing_sphere_endpoint` | 9 | Los IDs están en los acts AA8, pero las tablas server-side sphere aún no están decodificadas. |
| `unsupported_doodad_function_type` | 7 | `SkillHit`, `Bubble`, `EnterInstance` y `RemoveInstance` todavía sin comportamiento validado. |
| `missing_doodad_function_detail` | 4 | Cuatro detalles `DoodadFuncFakeUse` ausentes tanto del runtime como del legacy. |
| `effect_fire_team_share_not_validated` | 1 | La fila AA8 se conserva, pero no se habilita hasta reconstruir semántica de party-share. |

Primer stop point canónico posterior al bloque A: quest 6615, capítulo 12. Le
faltan exactamente los spawns de NPC 18455, 18457, 18459, 18461, 18463 y
18464. No se agregaron proxies sin autoridad.

## Bloque A desplegable

Archivo:

`D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-nuia-story-v2-chapter11.sqlite3`

SHA-256:

`E7A889EEE77E643C8F4EB51BF066DC192551C2F904ACEB78C9A59C2FA1F0DDDB`

Las 28 quests de capítulos 7–11 están `ready`. El runtime mantiene V1 y no
materializa quests posteriores bloqueadas.

## Validación automática

- Python V2: 28/28, incluidas dos compilaciones independientes idénticas.
- AAEmu.Tests: 328/328.
- ScriptCompiler durante tests: 0 errores, 8 warnings históricos.
- Build Docker .NET Core SDK 3.1: correcto.
- Prefijo V1: byte por byte idéntico en tablas ejecutables.
- Manifest completo:
  `generated/native-nuia-story-v2-runtime-manifest.json`.
- Manifest bloque A:
  `generated/native-nuia-story-v2-chapter11-runtime-manifest.json`.

## Regla para continuar

No declarar capítulos 12–31 como frontera jugable mientras exista un blocker.
Se puede seguir reduciendo verticales independientes, pero el despliegue de la
línea principal debe detenerse en 6615 hasta recuperar una relación de spawn
AA8 autorizada para sus seis miembros de grupo.

## Despliegue validado del bloque A

Fecha: 2026-08-01 (America/Santiago).

- Se configuró únicamente el compact del servicio `game` con el runtime hasta
  capítulo 11; MySQL no fue modificado.
- Se reconstruyó y recreó solamente `game`.
- Imagen desplegada:
  `07B5359459BDA0EFD0FC6626E703DD95E7D2A0E76AB7C178C3CE2A56E5803C5E`.
- Hash leído dentro del contenedor:
  `E7A889EEE77E643C8F4EB51BF066DC192551C2F904ACEB78C9A59C2FA1F0DDDB`.
- `ScriptCompiler`: 0 errores y 8 warnings históricos.
- Puertos 2239 y 2250 escuchando.
- `GameService`: servidor iniciado correctamente en 00:02:20.4013867.
- Login confirmó `Registered GameServer 1`.
- Contenedor estable, sin reinicios, OOM ni errores fatales durante el arranque.

La primera prueba manual autorizada es entrar con el personaje actual y
comprobar que la transición `4411 -> 7115` expone `Your Legend Continues`. La
aceptación y el consumo del item 47879 deben probarse como interacciones
separadas, revisando logs y persistencia entre ambas.
