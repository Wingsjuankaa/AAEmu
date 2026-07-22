# Fase 3 — Swiftblade 8.0

## Estado reproducible

La Fase 3 parte exclusivamente de la compact estable de Fase 2 y añade sólo la clausura nativa de Swiftblade. No modifica la compact del cliente, `game11`, `x2game.dll`, `game_pak` ni la compact de Fase 2.

Fuentes de autoridad:

1. `D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite`
2. `E:\AAEmu-Research\output\compact-8.0-extracted\game11`
3. `x2game.dll` del cliente Kakao 8.0.3.12 r558734
4. protocolo observado contra el servidor local
5. compact 3.0 y rama `develop`, sólo como referencia histórica

Artefacto generado:

- `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-phase3-swiftblade-v2.sqlite3`
- SHA-256: `335AF2E24E45A3AED57EC067203578E2C3146CB47E25881442440FF31215F42B`
- `PRAGMA quick_check`: `ok`
- `PRAGMA integrity_check`: `ok`

## Despliegue validado

- Fecha de validación: `2026-07-21`.
- Compose: `D:\Proyectos\AAemu\rama_8\docker-compose.yaml`.
- `.env` monta la compact Fase 3 en `/app/Data/compact.sqlite3` como solo lectura.
- El SHA-256 observado dentro del contenedor coincide con el del archivo host.
- Se reconstruyó y recreó únicamente `game`; `db` y `login` conservaron sus contenedores.
- El servidor escucha en `2239` y el stream en `2250`, y se registra correctamente en Login.
- Respaldo previo: `D:\Proyectos\AAemu\backups\aaemu8-before-phase3-swiftblade-20260721-224417.sql`.
- Suite estructural Python: 4/4 pruebas aprobadas.
- Suite .NET aislada en SDK 3.1: 30/30 pruebas aprobadas.

Durante el primer arranque se detectaron columnas modernas nulas en filas históricas. Los loaders ahora aplican el valor neutro confirmado (`0`/`false`) cuando esos campos no existen en la fila original; no se alteraron las filas nativas 8.0.

Dos ejecuciones independientes del generador produjeron bytes idénticos antes de incorporar la política documentada para referencias de texto internadas. El generador sigue siendo determinista; el hash anterior corresponde a la versión final.

## Cobertura recuperada

| Componente | Filas de la clausura |
|---|---:|
| Skills Swiftblade | 46 |
| Skills visibles | 12 |
| Pasivas | 6 |
| `skill_effects` | 140 |
| Efectos maestros | 154 |
| Buffs | 51 |
| Plots | 32 |
| Eventos de plot | 454 |
| Efectos de plot | 760 |
| Siguientes eventos | 462 |
| Condiciones de plot | 319 |
| Animaciones | 18 |
| Controladores | 15 |
| Proyectiles | 1 |
| Shapes AoE | 45 |

La validación de clausura informa cero efectos concretos pendientes, cero tipos de plot sin resolver, cero eventos huérfanos y cero animaciones solicitadas ausentes.

## Evidencia recuperada de DLL

Los layouts se confirmaron en las siguientes funciones del cliente:

| Tabla | Función `x2game.dll` |
|---|---|
| `plots` | `FUN_39a761f0` |
| `plot_events` | `FUN_39a75720` |
| `plot_conditions` | `FUN_39a73990` |
| `plot_aoe_conditions` | `FUN_39a740d0` |
| `plot_event_conditions` | `FUN_39a74390` |
| `plot_effects` | `FUN_39a74690` |
| `plot_next_events` | `FUN_39a75290` |
| `dispel_effects` | `FUN_39970ba0` |
| `anims` | `FUN_39967430` |
| `skill_controllers` | `FUN_399624e0` |
| `projectiles` | `FUN_39955c80` |
| `aggro_effects` | `FUN_3996d460` |
| `interaction_effects` | `FUN_3996ff60` |
| `combat_resource_effects` | `FUN_39974c30` |
| `aoe_shapes` | `FUN_399652b0` |

El valor internado `<ref:75256>` quedó identificado desde el mismo resultado de efectos de `game11` como `CombatResourceEffect`: el stream contiene tanto la primera cadena en claro como sus 139 referencias posteriores.

## Runtime implementado

- Lectura de `param4`, `pure` y `or_unit_reqs` en condiciones.
- Lectura de parámetros de target 10 y 11.
- Lectura de `casting_useable`, `combat_resource` y `weight` en siguientes eventos.
- Lectura de flags `only_*` y `notify_failure`.
- Lectura de los valores 5, 6 y 7 de `special_effects`.
- Lectura de `source_direction` de `InteractionEffect`.
- Registro, loader y modelo genérico de `CombatResourceEffect`.
- Mapeo documentado de columnas modernas `combat_resource` hacia las columnas históricas `high_ability_resource` que consume el backend.

El descriptor `CombatResourceEffect` se carga, pero su ejecución queda intencionalmente bloqueada: el modelo 3.0 no tiene todavía el estado de recurso por unidad ni su paquete 8.0 confirmado. No se inventó esa semántica.

La revisión posterior a la primera prueba recuperó también los 45 `aoe_shapes` alcanzables por Swiftblade desde el resultado nativo de `game11`. La versión v1 omitía esta dependencia: `PlotTargetInfo` recibía un shape nulo y finalizaba el plot antes de `SCSkillFired`. La v2 valida que cada evento `Area`, `RandomUnit` o `RandomArea` tenga su shape nativo correspondiente.

## Cadenas doradas

- `40331`: `DamageEffect 12250` + `SpecialEffect 42648` (`Combo` hacia `40377`, ventana 1000 ms).
- `40337`: `DamageEffect 12257`.
- `40339`: nueve relaciones nativas, incluyendo cuatro daños, dos buffs, dispel, teletransporte y tipo especial `176`.

## Bloqueos explícitos

Los tipos especiales `153`, `172` y `176` permanecen numéricos. Sus filas y sus siete argumentos están presentes en la compact, pero no se añadieron nombres ni acciones al backend porque la semántica todavía no está confirmada en `x2game.dll`.

`Combo` continúa sin ejecución autoritativa en el backend histórico. Los plots y habilidades internas sí están importados; la prueba de cliente decidirá si el cliente conduce la transición a partir de `SCPlotEvent` o si hace falta reproducir un paquete adicional. No se modificará protocolo por similitud.

`FxGroup` y `FxGroupAnim` siguen siendo acciones vacías del backend. Los recursos visuales/sonoros permanecen en `game_pak`; cualquier paquete faltante se implementará sólo después de localizar el consumidor y serializador 8.0.

## Reproducción

```powershell
python reconstruccion_skills_8\swiftblade\extract_swiftblade_phase3.py `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --runtime-compact D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-phase2-native-skills-v2.sqlite3 `
  --server-reference D:\Proyectos\AAemu\ArcheAge_Server_Compact_r208088_v1.2.4.13_update_2026-01-23\compact.sqlite3 `
  --client-game-stream E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --output reconstruccion_skills_8\swiftblade\generated\swiftblade-phase3-closure-v2.json `
  --verify

python reconstruccion_skills_8\swiftblade\build_phase3_swiftblade_compact.py `
  --runtime-compact D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-phase2-native-skills-v2.sqlite3 `
  --closure reconstruccion_skills_8\swiftblade\generated\swiftblade-phase3-closure-v2.json `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-phase3-swiftblade-v2.sqlite3 `
  --manifest reconstruccion_skills_8\swiftblade\generated\phase3-swiftblade-v2-compact-manifest.json `
  --verify
```

## Orden de prueba en cliente

### Correccion transversal de eventos visuales 8.0

La prueba de cliente posterior a la compact v2 mostro que el dano y los numeros
flotantes funcionaban, pero Fireball y las habilidades `plot_only` de Swiftblade
perdian el inicio de su animacion. Frozen Arrow, que usa el flujo normal de
`SCSkillStarted -> SCSkillFired`, sirvio como control positivo.

El lector nativo de `SCPlotEvent` en `x2game.dll` quedo identificado como
`FUN_399a38b0` mediante el constructor del opcode `0x0D5`
(`FUN_39335a20`, vtable `PTR_LAB_39d04990`). Ese lector siempre consume
`inputDirection` despues de las banderas y del bloque opcional de trece enteros.
El serializador historico de AAEmu terminaba antes de ese byte, dejando cada
subpaquete de plot corto y desalineando la secuencia visual comprimida.

`SCPlotEventPacket` ahora escribe el byte real recibido en
`SkillObject.InputDirection`. La correccion es transversal para cualquier
habilidad `plot_only`; no contiene IDs ni tiempos de animacion codificados a
mano. Las regresiones `PlotEventPacketTests` cubren tanto el layout normal como
el bloque opcional activado por la bandera `0x08`.

1. `Crescent Slice (40337)`: daño, número flotante, sonido/impacto, cooldown y repetición.
2. `Blade Flurry (40331)`: primer impacto y transiciones `40377 → 40378`.
3. `Sinister Strike (40339)`: daños, buffs, dispel, teletransporte; registrar especialmente el tipo `176`.
4. Resto de visibles, movilidad y áreas.
5. Seis pasivas y relog.
6. Segundo cliente observador.

### Correccion transversal de desplazamiento 8.0

La compact 8.0 confirma que Charge (`11918`), Blade Flurry III (`40378`) y
otras habilidades antiguas y modernas comparten controladores de tipo `Leap`.
Charge ejecuta el controlador `6779` desde su plot; Blade Flurry ejecuta el
controlador `11942` sobre el propio caster con `distance_offset = 5000` y
`duration = 100`. El backend tenia cargadas estas filas, pero
`SkillControllerTemplate.Apply` era una operacion vacia y los controladores de
habilidad solo se activaban para NPC.

La implementacion ahora activa `Leap` para cualquier `Unit`, diferencia entre
destino propio (direccion de mirada) y destino externo (linea caster-target),
convierte correctamente grados a radianes, actualiza la posicion autoritativa y
notifica el movimiento al propio cliente y a observadores. `end_skill_controller`
tambien finaliza y libera el controlador activo.

Para Blink se confirmo directamente en `x2game.dll` el lector del opcode
`SCUnitBlinkPacket 0x10E`: `BC unitId`, `float distance`, `float degree`,
`bool move3D`, `long x`, `long y`, `float z`. El paquete historico omitia
`move3D`, y las acciones Blink/TeleportToUnit enviaban en cambio un opcode sin
mapear (`0xFFF`). Ambas acciones usan ahora el layout 8.0 confirmado y actualizan
la posicion del servidor.

Las regresiones en `SkillMovementTests` cubren el salto hacia la mirada, el
offset respecto de un objetivo y el layout binario completo de Blink. No se
implementaron por inferencia los controladores `Rotate`, `Floating` o
`Wandering`.

Después de cada prueba deben revisarse logs, memoria, persistencia y regresiones de login, barras, cambio de especialidad, Battlerage, loot y consumibles.

La compact y el backend están desplegados para estas pruebas, pero esta fase no se considera funcionalmente cerrada hasta validar el cliente y resolver con evidencia los bloqueos enumerados arriba.
