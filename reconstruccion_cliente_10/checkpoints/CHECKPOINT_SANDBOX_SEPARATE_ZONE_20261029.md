# Sandbox: Zone411 independiente

Fecha:29oct2026, Santiago. Targetrama_10, HEAD
`9c74824659cc0d144f5e450e3bd7157624e539c3`; padre comunitario
`78533663d9ca93dc4aa610c088359312f91f4293`.

Se aplicó, con autorización exacta del usuario, la nueva Zone411
`aa10_sandbox_lab` al sandbox privado de World3240. Reutiliza la escena exportada
de entrenamiento406 y la distribuye con identidad, catálogo y layout propios;
no se esculpió terreno nuevo. MainWorld0/Instance0 se conserva dentro de las
copias privadas. Cliente principal, catálogos compartidos y Native habitual no
recibieron esta sustitución. Todos los nuevos archivos están en E.

Documentación y contratos completos:
`Docs/AA10SandboxSeparateZone_es.md`.

- Builders reproducibles:410 recursos; full y compact conservan sus esquemas y
  filas previas; sólo cuatro INSERTs de identidad/localización.
-104 pruebas Python OK; verificador C# Release con0 errores/advertencias,
  lectura real de XmlWorld, WorldManager, Hmap24 y SQLite.
- Paquetes aplicados con lock exclusivo, reextracción C# completa de targets
  y cuatro sentinelas ajenos; hash completo final coincide con ensayo previo.
- Cliente:92920312320bytes,
  SHA1785AAABBD389AD8E8AA2A0DCFDF60679FCE511418F9FFBB64A7574320F9C609.
- Native:69552965632bytes,
  SHA79E20088406F9495B81FACB51A1E725E6DE9D9FC753EC4915B62864715360057.
- Plan aplicado:
  SHA3B8AD4366E0E2E6DB1C68C2F22BB8DB8424FFD97C00747CBDB78E78F3327C4B8.
- Native411 PID26648, `+zone aa10_sandbox_lab`, World192.168.1.94:3240,
  `+sv_port65479`, catálogo explícito
  `E:/AAEmu/rama_10/runtime/sandbox-aa10/zone/game/db/compact.sqlite3`.
- API:Session482227815/Zone411/Instance0, `ZoneLoaded`01:49:35UTC y latidos
  sucesivos. Log nativo:Load Zone Finished, Loading Complete.
- Native habitual PID23668 permanece en `+zone w_solzreed_3`.
- Game PID395 bajo dotnet watch, Hot Reload disponible. La nueva prueba con
  jugador no se da por realizada sólo por consultar este estado.

El primer intento abortó antes de modificar paquetes por una comparación
textual de fechas de proceso; rollback379 sin errores. Se corrigió a ticksUTC,
se probaron equivalencias y PID reutilizado, y el segundo intento terminó.

Evidencia:runtime/sandbox-aa10/captures/
`20261030T014937Z-zone411-server-ready.json`.
Backup protegido:runtime/sandbox-aa10/secrets/zone411-backups/
`20261030T014340Z`.

Pendiente: usuario abre el CMD habitual y comprueba entrada automática, aspecto,
suelo, movimiento y cuatro dummies/cuatro servicios. Mantener marker en
`resources_verified` hasta su aceptación; no presentar esta fase como QA visual
completada. No se manejó su escritorio.

Primera apertura:el usuario informó selección de servidor detenida. El driver
registró world_request411; el cliente no pudo cargar el LobbyLevel heredado
`w_hanuimaru_1`. Se corrigió InitialConfig privado a `aa10_sandbox_lab`, con
backup adicional bajo `20261030T014340Z/lobby-fix`; el instalador ahora respalda
y aplica ese campo. No cambian los hashes de los paquetes. Se inició reinicio
aislado de Game/Native411 para repetir la apertura. Suite204 pruebas,7 omitidas,
sin fallos; seis pruebas del despliegue incluyen la regresión de lobby.

Reinicio del lobby corregido terminado:Native411 PID31564, Game396 bajo watch,
Session3225459956/Zone411/Instance0, Loaded01:56:46UTC y latidos estables.
Captura:`20261030T015649Z-zone411-lobby-fixed-server-ready.json`.
Native habitual23668 sigue intacto. Marker continúa en resources_verified;
segunda apertura solicitada al usuario, sin dar todavía por aceptada la escena.

Segunda apertura:world_request41122:58:23; módulo character_select y
character_requestSandbox22:58:26; carga aa10_sandbox_lab completa22:58:31.
API ready/intento1, Sandbox1001/obj273, dummies274–277, servicios278–281,
NativeUnitCount9. Se capturó `zone411-client-entry-server-confirmed`.
Se confirmó entrada automática y población en servidor/log; aceptación visual
del suelo y movimiento todavía pendiente.

## Aceptación final

Usuario confirmó entrada funcional y, después de bajar los actores a las cotas
de terreno individuales:«Sí, ahora están bien apoyados». Origen definitivo
575/506/256.25. DummiesZ256.25/256.30/256.30/256.30; serviciosZ256.35/256.25/
256.30/256.30. Datos persistidos en preset, definición común, perfil privado,
world_spawns privado y configuración MechanicsSandbox.

La aplicación en vivo mantuvo World396, Native31564, sesión3225459956 y
personajeobj273. API confirmó9 unidades y movimiento posterior del personaje
a558.5449/508.76172.79 pruebas sandbox posteriores al ajuste sin fallos.
La suite general previa:204 pruebas,7 omitidas. Los paquetes conservan sus
hashes completos anteriores. Hot Reload disponible; esta prueba fue de datos
en vivo, no una nueva edición de C# con jugador.

MarkerZone411:accepted a02:01UTC. Capturas finales:zone411-ground-adjustment y
zone411-user-final-accepted. Los pendientes anteriores quedan resueltos por
esta aceptación. Acceso habitual conservado; todo el material nuevo en E.

## Cierre del día: skills mantenidas y entrega Git

Por petición del usuario se versionaron las tres skills AA10 bajo Skills/aa10:
reconstrucción nativa, forensics y localización. Incluyen existencia/uso del
sandbox411, controles y API interna, identidad de sesión, recarga C# compatible,
límites de rude edits, permisos de lifecycle y pruebas realizadas por el usuario.
Las rutas instaladas de Codex ahora son junctions a esas fuentes en E; versiones
anteriores preservadas en runtime/sandbox-aa10/backups/skills. El instalador
Scripts/Install-AA10Skills.ps1 se validó e instala de forma idempotente.

Tres validadores de skill correctos, referencias Markdown locales resueltas,
parser PowerShell correcto; suite Python final204 pruebas con7 omitidas.
El C# no cambió durante este cierre y conserva8913/8913 de la reparación23592.
Se excluyó .local de Git y se revisó el lote para impedir publicar binarios,
paquetes, DBs, tokens o credenciales. Commit/push autorizado a origin/rama_10;
el SHA final se verifica en remoto tras publicarlo, sin force-push.
