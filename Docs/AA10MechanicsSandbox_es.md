# Sandbox de mecánicas AA10 r575

Fecha: 2026-10-29 (America/Santiago).

Actualización vigente: el sandbox usa **Zone411 aa10_sandbox_lab**, con terreno
separado reutilizado de retail406 y cuatro servicios. Ver
[AA10SandboxSeparateZone_es.md](AA10SandboxSeparateZone_es.md). Hall379 y los
PIDs de las pruebas V1 inferiores son historia de implementación. El arreglo
de23592 en [AA10PrecisionShotRange_es.md](AA10PrecisionShotRange_es.md) probó
una edición real de mecánica por Hot Reload, conservando la sesión.

## Objetivo y estado

Reducir el ciclo de corregir, compilar, conectar y preparar una prueba. El
producto abre el cliente español con un personaje fijo en una arena
con dummies, permite repetir/restablecer escenarios y conserva capturas que
relacionen el resultado visual con la ejecución del servidor.

Estado: implementados el arranque aislado, la entrada automática por los
consumidores Lua r575, el personaje fijo, los dummies y el reset por tentativa.
La aceptación nativa de la entrega se registra abajo; no confundir las pruebas
unitarias con esa aceptación. La instalación de REA no reconstruye por sí sola
el motor ni demuestra el comportamiento de una habilidad.

La recarga C# quedó aceptada en vivo: modificación y reversión del código real,
dos resets, mismos procesos World 240 / cliente 21824 / Zone 59768 y exactamente los
mismos sockets Game/Stream. El usuario confirmó arena visible y movimiento
después del reset. Evidencia y límites en `Docs/AA10SandboxHotReload_es.md`.

La presentación final usa un panel de carga propio encima del juego. No oculta,
desplaza, minimiza ni activa la ventana gráfica del cliente; las alternativas de
ocultación y posición fuera de pantalla fueron descartadas por pantalla negra,
y DWM rechazó la variante de composición con `0x80070005`. No se elevan permisos
ni se cambia seguridad para sortearlo. La confirmación visual del panel final
se registra en el checkpoint de presentación: el usuario confirmó carga,
arena jugable sin negro y cierre limpio del helper con la sesión conservada.
La entrega quedó capturada en `runtime/sandbox-aa10/captures/*-delivery-accepted.json`.

Ampliación del escenario con cuatro servicios retail, selección de sala y
contrato de reset tras cambiar especializaciones: `Docs/AA10SandboxTrainingHub_es.md`.

## Implementación V1

El runtime está en `E:/AAEmu/rama_10/runtime/sandbox-aa10`:

- `Iniciar sandbox AA10.cmd`: inicia sólo el stack `aaemu10-sandbox`, espera
  la Zone del perfil instalado (411 en el entorno aceptado) y abre su copia
  española. Al autorizar su ejecución, el alcance se limita a ese perfil;
  no arranca perfiles del servidor habitual.
- `Reiniciar escenario.cmd`: solicita reset y espera confirmación `ready`.
- `Estado sandbox.cmd`: muestra World, jugadores y Zones del sandbox.
- `Herramienta de desarrollo.cmd`: abre los controles de la arena e inicia
  World/Game desde las fuentes con `dotnet watch`. Permite reset, posiciones
  y distribución de objetivos en la sesión; muestra recargas C# y reinicios
  de World. Véase `Docs/AA10SandboxHotReload_es.md`.
- `client/`: copia física independiente del español principal, con entrada
  automática opt-in y perfil nativo dirigido a `profile/` en E.
- `db/`: datos privados de MySQL; `backups/` conserva el snapshot coherente
  utilizado para inicializarlos. No importar este snapshot en el servidor habitual.
- `captures/`, `logs/`, `temp/` y `zone-save/`: resultados y temporales en E.

El personaje `Sandbox`, ID1001/cuenta1, se prepara desde el personaje de
prueba desconectado Wingsjuanka mediante snapshot sólo lectura de origen.
Conserva su modelo, habilidades y equipo reales en la DB aislada; las demás
entradas quedan ocultas en ese clon. No se renombra ni altera el original.
Sólo el contenedor `aaemu10-sandbox-db-1` recibe las mutaciones de preparación.

Puertos locales propios: Login3237, Game3239, Stream3250. La autoridad de Zone
usa el puerto3240 de la IP LAN ya validada, porque la DLL r575 rechaza loopback.
MySQL y Web API1280 no se publican. La Zone nativa tiene copia física propia,
configuración3240 y log/save propios, sin cambiar la configuración del perfil
habitual. Se reutiliza el host ConPTY del Control Center para iniciarla oculta.

Código de arranque: `Scripts/aa10_sandbox.py` y `Scripts/Start-AA10Sandbox.ps1`.
El runner rechaza raíces fuera de `E:/AAEmu/rama_10/runtime`, referencias al
cliente principal, bindings distintos y cambios de identidad del parche.
Un proceso previo de la misma Zone no genera un segundo lanzamiento.
El arranque tiene un bloqueo propio en E para rechazar aperturas concurrentes.
Si World se reinicia y la Zone propia ya no responde, el runner sólo recupera
el par helper/hijo registrado, verificando ruta, PID, padre y fecha de creación
antes de detenerlo. Un proceso desconocido se rechaza. Si el personaje está
offline, retira únicamente clientes de la ruta exacta de la copia sandbox
antes de abrir otro; una sesión online reutiliza su cliente.

Detalles del cliente y reversión:

- `reconstruccion_cliente_10/checkpoints/CHECKPOINT_SANDBOX_AUTOENTRY_20261029.md`.
- `Docs/AA10SandboxProfile_es.md`.
- `Docs/AA10MechanicsSandboxResetContract_es.md`.

El reset V1 restablece posición, HP/MP, buffs iniciales, recursos de combate,
cooldowns/cargas, targets/aggro y los cuatro dummies propios. Los callbacks de
la tentativa anterior quedan retirados. Durante una tentativa las fórmulas,
requisitos, animaciones y cooldowns siguen sus consumidores reales. No revierte
inventario, experiencia, misiones ni objetos/invocaciones producidos por otras
mecánicas. Para otra build de personaje se cambia el clon de prueba, no el original.

La autorización del usuario para la prueba nativa 379 fue recibida en este
chat el 2026-10-29, limitada al sandbox y a World3240.

### Almacenamiento

REA y Node están en `E:/AAEmu/rama_10/tools/rea`; su skill física está en
`E:/AAEmu/rama_10/tools/rea-skill`. NuGet, npm, home del CLI, copias de cliente,
respaldos y resultados de esta implementación están en E. Se migraron los
payloads y las entradas de caché atribuibles a la instalación anterior en C.
Codex conserva su configuración de aplicación y un junction de descubrimiento
en C, sin payload de la skill. La revisión automática bloqueó retirar dos
directorios padre antiguos de herramientas/caché de C. La inspección final
confirma que contienen Blender y un prebuild Keytar previos, ajenos a esta
tarea; se conservaron. No son residuos de la instalación del sandbox y no se
intentó sortear ese rechazo.

## Target y autoridad

- Raíz: `E:/AAEmu/rama_10`.
- Repositorio: `server/AAEmu`, rama `rama_10`; HEAD de la inspección
  `9c74824659cc0d144f5e450e3bd7157624e539c3`.
- Padre exacto: `upstream/client_version/zone-10.0.2_r575`, corte local
  `78533663d9ca93dc4aa610c088359312f91f4293`. No se actualizó ni cambió rama.
- Cliente principal:
  `client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
  Producto `es_ES`, canal interno `+locale en_us`. Conservar traducciones y
  parches vigentes; original y piloto histórico no son el runtime elegido.
- Catálogo completo: `data/sqlite/authoritative/game_decrypted.sqlite3`.
  SHA-256 `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`.
- Compact del cliente principal en esta inspección:
  `E5947F15726BF05C392CDC912BC778F2BFE6E407349A1F3A89BAA818B56C3187`.
- `x2game.dll` principal:
  `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.

`AAEmu.Game/WorldIntegration.cs` documenta la autoridad actual:
Game/World calcula las skills mediante `Skill.Use`; la Zone nativa controla
IA, movimiento y aggro, y recibe el timeline. ZoneHost es el bootstrap;
su fuente integrada no contiene toda la simulación de las DLL retail.
Un visor externo de modelos no reemplaza esta combinación para aceptar
física, colisiones o sincronización. AA8 Mechanics Lab es sólo comparador:
sus adaptadores, IDs, tiempos y contratos no se promueven automáticamente.

## REA: registro de la instalación inicial, anterior al traslado a E

- Skill: `C:/Users/juank/.codex/skills/reverse-engineer-anything`.
  Instalación con `skill-installer` desde `morluto/rea`, commit
  `3b647132c6221f644cac620016b7cf0a2b548549`, ruta
  `.agents/skills/reverse-engineer-anything`.
- CLI: `rea-agents@6.8.0`, bajo
  `C:/Users/juank/.codex/tools/rea`; dependencias fijadas en su lock local.
- Runtime aislado: `node@24.22.1`. No se sustituyó el Node global.
- MCP registrado sólo para Codex por `rea setup --client codex --skill=false`.
  Respaldo: `C:/Users/juank/.codex/config.toml.rea.backup`.
  Comparación TOML: eliminando el nuevo bloque `mcp_servers.rea`, configuración
  actual y respaldo son equivalentes.
- Proveedor detectado: Ghidra `12.1.3`, ya existente en
  `tools/ghidra/ghidra_12.1.3_PUBLIC`, con JDK `21.0.11+10` existente.
  Setup reporta `ready`, `doctor.healthy=true` para el cliente seleccionado.
- Smoke MCP independiente: `initialize` y `tools/list` correctos;
  servidor `rea` versión `6.8.0`, 229 herramientas, incluidas
  `open_binary`, `close_binary`, `analyze_function`, `inspect_native_exports`
  y `binary_session`. No implica conexión de la sesión de chat ya abierta.
  Recargar MCP/reiniciar Codex para descubrirlo en el chat.
- Smoke CLI real: `inspect-native-exports` sobre el `x2game.dll` principal,
  sin ejecutar el cliente. Cinco exports PE, sin incidencias; entre ellos
  `CreateGame` y `CreateGameStartup`. Esto no prueba una API de arena ni un
  mecanismo de autoselección. No se inició una decompilación nueva.
- Evidencia completa fuera de Git:
  `forensics/output/aa10-client-forensics/sandbox-intake-20261029/x2game-exports.rea.json`.
  ID `ev_00c6cfaceebe7ff15a94f45412f68253c1db525865686ebc9dc0da0a1ac2679a`.

Ejemplo local de CLI, utilizando las versiones instaladas:

```powershell
& "E:\AAEmu\rama_10\tools\rea\node_modules\node\bin\node.exe" `
  "E:\AAEmu\rama_10\tools\rea\node_modules\rea-agents\scripts\rea.mjs" --version
```

Reutilizar primero los proyectos Ghidra AA10 y checkpoints existentes.
Investigar con REA una pregunta concreta cuando el corpus no la resuelva,
con SHA-256, arquitectura y RVA. Separar evidencia estática, observación
dinámica e hipótesis; no afirmar ejecución a partir de exports o pseudocódigo.

## Componentes reutilizables

| Necesidad | Implementación/evidencia existente | Límite |
| --- | --- | --- |
| Lanzar cliente autenticado | Control Center `src/main/services/ClientService.ts` | No selecciona personaje automáticamente. |
| Esperar Zone disponible | Control Center `ZoneService.waitUntilReady` | Exige `ZoneLoaded`, proceso y heartbeat; un puerto abierto no basta. |
| Anticipar destino | `LoginReservations` y plan `docs/ZONE_ORCHESTRATION_AND_LAN_LAUNCHER_PLAN_ES.md` | El gate automático de entrada sigue pendiente en ese plan. |
| NPC individual o grupo | `AAEmu.Game/Scripts/Commands/Spawn.cs`, `SpawnGrid.cs` | Publican espejo nativo con `WorldIntegration.PublishNpcSpawn`; requieren Zone propietaria cargada. |
| Vida y cooldowns | `Heal.cs`, `ResetSkillCooldowns.cs`, `IgnoreCooldowns.cs` | Son herramientas de preparación; cooldowns normales deben probarse sin exenciones. |
| Comandos externos | `CommandController.cs`, Control Center `WorldApiService.ts` | Personaje online; usar API interna por Docker, sin publicar 1280. |
| Entrada completada | `CSNotifyInGameCompletedPacket.cs`, `WorldEntryCompleted` | No preparar el escenario antes de finalizar la entrada real. |

Dummy confirmado en el catálogo AA10, consulta sólo lectura:

```sql
SELECT id, name, model_id, ai_file_id, npc_ai_param_id
FROM npcs WHERE id = 7512;
```

Resultado: ID `7512`, modelo `1290`, AI `25`, parámetro AI `0`.
Coincide con el alias GM `spawn npc dummy`. Esto acredita presencia estática,
no aceptación visual ni física. La fila full `(npcs, name, 7512).en_us` está
vacía: resolver nombre visible desde el compact español efectivo antes de
crear etiquetas localizadas.

## Arena candidata e independencia del entorno

`gatekeeper_hall`, zoneKey `379`, `main_world`, dispone de aceptación previa
de `ZoneLoaded` y heartbeats sin spawns estáticos. Ver
`reconstruccion_cliente_10/checkpoints/CHECKPOINT_GATEKEEPER_379_NATIVE_LOAD_20260908.md`.
La política exacta vive en Control Center `src/shared/nativeZonePolicy.ts`.
Esa aceptación está ligada a DLL nativa SHA-256
`8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A`.
Hay advertencias de recursos documentadas; medirlas visualmente.

La prueba de carga no certifica combate ni paso del cliente. La Zone pertenece
a `main_world`: elegir esta sala **no aísla** personajes, DB o sesiones.
Un perfil de prueba debe definir explícitamente aislamiento de datos/runtime
o una instancia nativa compatible antes de permitir resets automáticos.
Consultar la posición persistida actual del personaje antes de resolver su
perfil; una posición de un checkpoint histórico no es autoridad actual.

## Primera vertical y puertas de aceptación (plan inicial histórico)

1. Definir perfil de prueba, personaje fijo, destino y propiedad del estado.
   Ningún reset debe alcanzar personajes o NPCs ajenos.
2. Resolver la entrada automática: estudiar Lua/ALB de Lobby y selección,
   después sus consumidores r575 si falta el contrato. No se encontró todavía
   un flag o API de autoselección validado. No sustituir solicitudes del cliente
   por llamadas server-side a `CSSelectCharacter` fuera de su estado esperado.
3. Verificar stack y Zone propietaria con el lifecycle autorizado; abrir el
   cliente español y esperar entrada completa.
4. Preparar personaje, equipo y dummy `7512` mediante consumidores existentes.
   Capturar una skill simple con daño, una AoE y un desplazamiento; verificar
   resultado visual, ejecución Game/World y movimiento/aggro nativos.
5. Implementar reset acotado de posiciones, HP/MP, buffs y cooldowns. No basta
   con curar: comprobar tareas pendientes, muerte/respawn, targets y aggro,
   evitando IDs obsoletos o NPCs duplicados al repetir.
6. Asociar escenario, timestamps, paquetes y estados antes/después a cada
   corrida. Aceptar repetición sólo tras comprobar ausencia de residuos.
7. Integrar el ciclo de recompilar/reconectar/restaurar escenario. La recarga
   en caliente no es universal: evaluarla por recurso y primitiva.

El objetivo inicial es una arena funcional y repetible. La reconstrucción
exhaustiva del motor no es prerrequisito y no se declara alcanzada.

## Operación de la investigación inicial (histórica)

Se instalaron tooling e instrucciones y se hizo inspección estática. No se
cambió gameplay, compact, game_pak ni traducción; no se desplegó Game y no
se inició/detuvo/relanzó ninguna Zone o cliente. La autorización histórica
de una Zone en un checkpoint no se transfiere a esta tarea. El lifecycle
de la prueba nativa conserva la política explícita de la skill AA10.
