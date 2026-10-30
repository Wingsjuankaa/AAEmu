# Zone independiente del laboratorio AA10

Target `rama_10`, HEAD9c74824659cc0d144f5e450e3bd7157624e539c3;
padre `upstream/client_version/zone-10.0.2_r575`, SHA78533663d9ca93dc4aa610c088359312f91f4293.
Todo el código, staging, pruebas y rollback de esta tarea vive en E.

## Escenario aplicado y aceptado

Zone nueva **411**, nombre `aa10_sandbox_lab`, fila324 y grupo159.
Es una identidad de la herramienta, no una Zone retail descubierta.
Reutiliza terreno, colisiones, iluminación, materiales y decoración exportados
de `instance_training_camp_1on1_ga`/406. Tiene cuatro dummies y los cuatro
puestos de especializaciones, banco, armas y armaduras ya probados.

Se conserva el nombre interno `main_world`/World0/Instance0 **en las copias
privadas del sandbox**. Su definición pasa a una escena de2×2 celdas con una
sola Zone411, conservando la celda0,0 del donante sin trasladar sus binarios.
Así no se mezclan las tablas de materiales del continente y la arena ni se
introduce un WorldId cuyo ordinal y persistencia no están cerrados.
El cliente español principal, el mapa habitual y los catálogos compartidos
permanecen como fuentes inmutables; el sandbox usa derivados y bind-shadows.

No se esculpió una malla nueva. Se crea una escena aparte con identidad,
recursos y distribución propios reutilizando el recinto exportado del juego.
La Zone no tiene portales añadidos, no aparece en abox y su grupo oculta la
posición mundial. Su aislamiento efectivo lo proporciona el runtime privado.

Entrada definitiva: X575/Y506/Z256.25, yaw0. El punto authored del donante
usaba Z260 y se probó inicialmente, pero dejó actores flotando. La colocación
definitiva utiliza las cotas Hmap256.25–256.35 de cada punto y fue aceptada
visualmente por el usuario con Zone411 y el cliente.

## Construcción reproducible

- `Scripts/BuildAa10SandboxZoneAssets.py`:410 recursos/37227921bytes,
 406 copias byte a byte, cuatro cambios de identidad y tres omisiones
 declaradas de spawns/puntos de entrada/puertas interactivas del donante.
 Dos builds idénticos, manifestSHA27D44CD598365785C6AAA8644AA1D5C145828B25AF31395ECC42604AED168EBA.
- `Scripts/BuildAa10SandboxZoneCatalog.py`:añade únicamente zones324,
 zone_groups159 y dos etiquetas españolas. Conserva todos los esquemas,
 filas/ROWIDs y tamaños. Full552178688bytes
 SHA FD66192AE065F42B92579718B6FB91A51A52947D2E0FBFF29D89ADC8DA7E4304;
 compact470106112bytes
 SHA59C47834B802737890304F8584347E85DD61DC519AD62230C66F0760BDA33FCA.
 Dos builds de cada perfil idénticos; quick_check/integrity_check completos OK.
- `Scripts/BuildAa10SandboxZoneEntry.py`:deriva el driver V3 aceptado para
 solicitar411, conservando realm1/AA10 Sandbox y personaje Sandbox. Reproduce
 primero el hash V3 y ejecuta los handlers Lua reales en las pruebas.
- `Scripts/Aa10SandboxZonePak.py`:batch ADD/REPLACE con una sola lectura del
 índice y un commit del suffix; preserva registros cifrados ajenos y tombstones,
 obtiene lock Windows exclusivo y ofrece rollback exacto con mtime original.
 Los recursos crecientes tienen nuevas ubicaciones; no mueve el payload viejo.

El `game.sqlite3` empaquetado original tiene cabecera cifrada y se conserva
opaco. El compact empaquetado es SQLite plano. La Zone usa `+db_location` al
full derivado privado explícito; las copias loose se mantienen consistentes.
No se sustituye una base cifrada por plaintext suponiendo un codec equivalente.

## Plan revisable y aplicación

Staging: `E:/AAEmu/rama_10/artifacts/sandbox/zone411-deployment-a/deployment.json`.
Scripts: `aa10_sandbox_zone.py prepare`, `prove`, `activate`.

`prepare` no modifica el runtime. `prove` valida las reextracciones C# de los
candidatos sparse, compara todos los registros ajenos, verifica el hash completo
original y calcula el hash completo final esperado sin escribir el paquete vivo.
Los fixtures sparse no son clientes ejecutables; sólo contienen todos los
targets y cuatro sentinelas, manteniendo los demás payloads como huecos.

`activate` exige el hash del plan y autorización explícita para probar411 y
recuperar379 si falla. Bloquea aperturas simultáneas del sandbox, respalda sólo
sus archivos en `runtime/sandbox-aa10/secrets/zone411-backups`, retira la escena,
cierra únicamente su cliente y su Zone379 y detiene sólo su Game/World.
Después aplica y reextrae todos los recursos, comprueba hashes completos,
instala las copias loose y el catálogo servidor privado, migra únicamente la
posición de Sandbox1001/cuenta1 y levanta el perfil411 contra World3240.

El archivo Data/compact.sqlite3 compartido no recibe escrituras: se añade un
bind-shadow privado. También se deriva un world_spawns.json con entrada Main
en411. Las credenciales de Compose sólo se respaldan en el directorio protegido.
En este runtime se desactiva la población estática legacy de doodads, transfers
y gimmicks de otros mapas. Los efectos de skills y la creación dinámica de
actores continúan usando sus consumidores normales.
Los rollback de paquetes, archivos/configuración y posición se coordinan antes
de recuperar el Hall379. No se importa una DB completa sobre el servidor habitual.

El cambio de mapa requiere reiniciar el sandbox. La recarga C# compatible sigue
usando dotnet watch; no se presenta la sustitución de geometría como Hot Reload.
El acceso habitual seguirá siendo `Iniciar sandbox AA10.cmd`.

## Evidencia

`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/sandbox-zone-separate-20261029/`:
`assets/REPORT_es.md`, `registration/REPORT_es.md`, `package/REPORT_es.md`,
`managed-consumer-verification.json`, ensayos en `rehearsal/` y hashes completos
en `complete-package-rehearsal.json` cuando termine prove.

## Aplicación autorizada y comprobación nativa

El usuario autorizó expresamente probar Zone411 contra World3240, cerrar
únicamente el cliente del sandbox y recuperar379 si fallaba. El cambio terminó
el29 de octubre de2026 a las22:49 de Santiago (30oct01:49UTC).
Zone411 sustituyó al Hall379 únicamente en el runtime privado.

El primer intento abortó antes de cambiar paquetes por una comparación textual
de fechas de creación del proceso. Se recuperó379 sin errores. La guarda ahora
compara instantes UTC en ticks, tolera procesos que ya terminaron y sigue
rechazando PID reutilizado o ejecutable distinto. Las pruebas incluyen los tres
casos. El segundo intento terminó correctamente.

Plan aplicado SHA256:
`3B8AD4366E0E2E6DB1C68C2F22BB8DB8424FFD97C00747CBDB78E78F3327C4B8`.
Hashes completos finales, iguales al ensayo previo y comprobados después de
escribir y reextraer todos los recursos:

| Copia privada | Bytes | SHA256 |
|---|---:|---|
| Cliente |92920312320|1785AAABBD389AD8E8AA2A0DCFDF60679FCE511418F9FFBB64A7574320F9C609|
| Native |69552965632|79E20088406F9495B81FACB51A1E725E6DE9D9FC753EC4915B62864715360057|

ZoneHost PID26648 arrancó con `+zone aa10_sandbox_lab`, World3240 y
`+db_location` al catálogo full privado. World confirmó sesión482227815,
ZoneId411/InstanceId0 y `ZoneLoaded` a01:49:35UTC, seguida de latidos.
El log nativo confirma `Load Zone Finished` y `Loading Complete`.
La escena no trae NPCs, puertas interactivas ni gimmicks estáticos del donante;
los cuatro dummies y cuatro servicios se crean al entrar mediante el sandbox.
El Native habitual PID23668 conservó su ejecutable y línea de comandos.

Game corre bajo dotnet watch, PID395 dentro del contenedor, con soporte de
Hot Reload. Esto confirma la disponibilidad del mecanismo tras cambiar mapa;
no constituye por sí solo una nueva prueba de edición en caliente con jugador.
La suite Python completó104 pruebas y el verificador C# compiló sin errores ni
advertencias y leyó los recursos usando los consumidores reales del servidor.

Evidencia del arranque:
`runtime/sandbox-aa10/captures/20261030T014937Z-zone411-server-ready.json`.
Backup protegido para recuperación:
`runtime/sandbox-aa10/secrets/zone411-backups/20261030T014340Z`.

Estado: recursos verificados y Zone nativa cargada. Se solicitó al usuario abrir
el acceso habitual; la entrada automática, el aspecto, el suelo y la colocación
de los ocho actores en este nuevo mapa siguen pendientes de su observación.
`zone411-installed.json` permanece en `resources_verified` hasta esa aceptación.

### Corrección del lobby detectada en la primera apertura

El cliente solicitó411 automáticamente, pero quedó en selección de servidor.
Su log mostró `Level w_hanuimaru_1 not found` antes de cargar el módulo de
selección de personaje. `FinishStatePacket` envía `SetGameTypePacket` usando
`InitialConfig.LobbyLevel`, que aún conservaba el fondo del continente anterior.
No fue un fallo de credenciales ni una aceptación de entrada al nuevo mapa.

La corrección cambia sólo `InitialConfig.LobbyLevel` a `aa10_sandbox_lab` en la
configuración privada, respaldada bajo el mismo backup protegido, y reinicia
únicamente Game y Native411 del sandbox. Los paquetes conservan los hashes de
la aplicación anterior. El instalador incorpora este campo a su backup y su
aplicación para evitar repetir la omisión. La prueba del plan comprueba el
cambio, su idempotencia, la preservación de los otros ajustes y el rechazo de
un lobby inesperado. Suite ampliada:204 pruebas,7 omitidas, sin fallos.
La aceptación del cliente continúa pendiente tras esta corrección.

Reinicio terminado a22:56:49 de Santiago. Native411 PID31564, Game PID396,
sesión3225459956, ZoneLoaded a01:56:46UTC con latidos sucesivos. Evidencia:
`runtime/sandbox-aa10/captures/20261030T015649Z-zone411-lobby-fixed-server-ready.json`.
Se validaron otra vez la identidad física de ambos paquetes y los enlaces
privados. El marker registra la corrección del lobby sin reemplazar el hash
histórico del plan que aplicó los paquetes. El usuario fue invitado a repetir
la apertura con el acceso normal.

Segunda apertura con lobby corregido:el cliente registró `world_request411`
a22:58:23, carga del módulo de selección a22:58:26 y `character_requestSandbox`
en el mismo segundo. Completó `aa10_sandbox_lab` a22:58:31. World confirmó
Sandbox1001/obj273 en411, escenario ready/intento1, dummies274–277 y
servicios278–281. La Zone informa9 unidades. No se observa ya la referencia
ausente a `w_hanuimaru_1`. Esto prueba la ruta automática y la población desde
los logs y el servidor; continúa pendiente la observación visual del usuario.

## Aceptación final y alturas persistentes

A las23:01 de Santiago el usuario confirmó la entrada y, tras la corrección,
«Sí, ahora están bien apoyados». Inicialmente los dummies flotaban y los NPCs
saltaban: se eliminó la cota260 del spawn del donante y se usaron las alturas
individuales que leyó el consumidor Hmap real. Origen256.25; primer dummy256.25,
los otros tres256.30; Toosten256.35, Tiri256.25, Vigdia/Giyolla256.30.

Se persistieron el preset411, la definición de escena, sandbox.json, el spawn
privado y MechanicsSandbox.json. El instalador obtiene las coordenadas desde
la definición común. El cambio se publicó mediante el controlador existente,
retiró la escena anterior y recreó los ocho actores conservando World PID396,
Native PID31564, sesión3225459956 y personajeobj273. El usuario continuó
moviéndose; API confirma posición posterior558.5449/508.76172 y9 unidades.
No se reinició el cliente para ajustar las alturas.

Verificación posterior:79 pruebas del conjunto sandbox sin fallos y comprobación
de cada posición contra el resultado del lector Hmap. La suite general había
completado204 pruebas con7 omitidas antes del ajuste de datos. Paquetes sin
cambios desde los hashes completos registrados arriba. Hot Reload continúa
disponible bajo watch; esta corrección de posiciones fue una publicación de
datos en vivo, no una nueva prueba de edición de C#.

Marker `runtime/sandbox-aa10/zone411-installed.json`: **accepted**.
Capturas `zone411-ground-adjustment` y `zone411-user-final-accepted` en el
directorio privado `captures`. Las notas de pendiente anteriores describen
las etapas intermedias; la entrada y la colocación ya quedaron aceptadas.
