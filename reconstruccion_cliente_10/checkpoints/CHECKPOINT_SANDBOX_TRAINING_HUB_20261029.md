# Sandbox AA10: laboratorio con servicios retail

Estado 2026-10-29 21:57 America/Santiago: perfil aplicado y aceptado. El usuario confirmó
por separado «Llegó a la arena» y «Veo los cuatro y abren sus menús», en
respuesta a la comprobación de suelo/aspecto y menús de los cuatro puestos.
Después cambió una especialización y confirmó tras el reset:
«Sí, conserva la especialización y puedo moverme».

## Target y fuentes

`E:/AAEmu/rama_10/server/AAEmu`, rama_10 HEAD9c74824659cc0d144f5e450e3bd7157624e539c3.
Padre upstream/client_version/zone-10.0.2_r575 SHA78533663d9ca93dc4aa610c088359312f91f4293.
Sin commit/push ni cambio de rama. Código, runtime, evidencias y temporales en E.
No se usó computer-use ni se tomaron capturas del escritorio.

Informes y contratos:

- `Docs/AA10SandboxTrainingHub_es.md`.
- `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/sandbox-custom-20261029/arena/REPORT.md`.
- `.../services/REPORT_es.md` y `.../services/PASSIVE_369_BLOCKER_es.md`.
- REA CLI6.8.0, inspección real de proyección SQLite reproducible;
  evidencia ev_5202271487335596228ef1c00c862f5fdb44614181f987eb2c06b1a347243c81.
  La proyección es parcial; no se presenta como toda la DB ni como prueba visual.

## Aplicación en vivo

Se conserva main_world/Zone379, origen500.295/38373.5/129.948.
No hubo una migración de mapa ni cambios de malla/colisión/pak.
La escena reaprovecha suelo/decoración del Hall y actores del catálogo AA10.

Aplicación por `Scripts/aa10_sandbox.py hub`, 21:52:09:

| Actor | ObjectIds | Template |
|---|---|---|
| Personaje Sandbox | 387 | clon1001/cuenta1 |
| Dummies | 392–395 | 7512 |
| Toosten, especializaciones | 396 | 18870 |
| Tiri, banco | 397 | 1023 |
| Vigdia, armas | 398 | 1497 |
| Giyolla, armaduras | 399 | 1498 |

WorldPID3626 antes/después; cliente30576 y sockets54495→3239,
54497→3250 exactamente iguales. ZonePID7644, SessionId2123043086,
ZoneLoaded/heartbeat vigente y UnitCount9. Los cuatro dummies388–391
de la escena anterior se retiraron antes de crear los nuevos.

Evidencia en `E:/AAEmu/rama_10/runtime/sandbox-aa10/captures/`:
`20261030T005210Z-training-hub-applied.json`,
`custom-hub-session-before.json`, `custom-hub-session-after.json`,
`20261030T005253Z-training-hub-session-preserved.json`.
Los timestamps de ficheros son UTC; la fecha local del trabajo es29 de octubre.

## Bloqueos cerrados durante el trabajo

- La modificación inicial de firma de constructor produjo ENC0011 y reinicio
  de World240→3626 cuando no había cliente conectado. Se registró como reinicio,
  no como Hot Reload. El primer CMD del usuario esperaba la carga de datos;
  ahora el lanzador anuncia la espera y muestra progreso cada15s.
- WinError5 al ordenar el panel: alternativa usa sólo la ventana propia y
  constantes de Z-order, sin ancla de otro proceso después del rechazo.
  En la entrada30576 el helper cerró sin error de presentación y el lanzador
  completó la preparación. La aceptación visual corresponde al usuario.
- El nuevo preflight descubrió pasivo369→26210→25267→TimeoutSkill42427/plot4364,
  con daño/spawn/buffs. Se mantuvo el rechazo de esa cadena y no se declaró
  NPC-only. El perfil de combate excluye únicamente369 del libro activo del
  actor vinculado, al cargarlo y al conceder automáticamente. La fila DB se
  conserva para reversión, y el servidor habitual mantiene su comportamiento.
  Logs reales a21:51:46 prueban ambas exclusiones; preflight posterior validated.
- El lanzador anterior agotó240s tras el rechazo y cerró cliente21292. Se corrigió:
  rechazo inmediato y conservación del cliente si ya completó la entrada.
  Regresión Python prueba que se revela el panel sin terminate/cancel del juego.

## Validación

Build Release final sin errores; suite completa8906 .NET correctos,
64 Python correctos. Logs `runtime/sandbox-aa10/temp/custom-hub-build-final-combat.log`,
`custom-hub-tests-combat.log`, `custom-hub-python-tests.log`.
No se repitieron las compras ni se alteró inventario para simular una interacción.
Confirmados por el usuario: entrada, suelo/aspecto y menús de los cuatro NPCs.
Cambio real a21:54:50: CSSwapAbility obj396 old7/new6; registro de servidor
Fight/Vocation/Magic→Fight/Vocation/Wild. El reset a21:55:12 pasó preflight,
subió intento1→2, retiró/recreó los ocho actores y mantuvo cliente30576,
World3626, Zone7644/SessionId2123043086 y los sockets54495/54497.
La Zone volvió a UnitCount9, sin duplicados. Puestos finales400–403;
IDs388–391 reciclados para los cuatro dummies por el allocator normal.
El usuario confirmó la especialización nueva y movimiento sin reconexión.
Evidencia `20261030T005512Z-training-hub-{before,after}-swap-reset.json` y
`20261030T005544Z-training-hub-swap-reset-session-preserved.json`.

## Reversión

Backup automático del perfil previo bajo `runtime/sandbox-aa10/backups/`.
El aplicador revierte configuración y escena ante rechazo/fallo. Para volver al
libro original, CombatProfile=false y una nueva conexión; el preflight volverá
a rechazar el productor de tesoros hasta cerrar su restitución. No se borró su
persistencia. El runner sólo arranca/recupera el perfil sandbox379/World3240.
