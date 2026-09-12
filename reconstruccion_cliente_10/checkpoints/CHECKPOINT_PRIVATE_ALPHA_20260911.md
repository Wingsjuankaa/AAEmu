# Alpha privada — 2026-09-11

Estado: **V7 desplegada; ventana, catálogo, oro, ítem y revocación probados en retail**.
El cierre V7 al final de este documento sustituye los estados pendientes de los
intentos anteriores; allí se enumeran los casos aún sin prueba nativa.

Target canónico `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`, HEAD de
partida `fd53b458573572cc354c8564293f274801d9aa3e`. Padre exacto actualizado por
fetch a `1017677b40be6508861a8fb74e9d09fa496873c9`; se consultó sin merge. Los
cambios previos de Garden/quests/combate permanecen. No commit ni push de este
checkpoint como feature aceptada.

## Entrega inicial (registro histórico)

- Nuevo item `900001`, **Llave de alpha privada**: bind-on-pickup, no vendible,
  max stack 1, clic derecho en bolso, no se consume.
- Ventana custom con oro, labor, búsqueda por nombre/ID, iconos, páginas de 10,
  cantidad y grado. Búsqueda española normalizada en el servidor.
- Catálogo r575 completo: se restauran 11.876 filas base ausentes en la compact.
  Sus subtipos ya existían. Total cliente 51.011 filas con la llave. Todas las
  filas previamente existentes en todas las tablas se preservan.
- Acceso **sólo Dannia/1007**, conservando su nivel de acceso general 0. La
  autorización está persistida; no se insertaron items directamente en SQL.
  Al terminar la próxima entrada al mundo, Game entregará la llave por su
  lifecycle de inventario, si existe una ranura libre.
- No se creó el proceso futuro de correo para otros jugadores.

## Evidencia

`inventory/sort_bag.lua` y `inventory/sort_inventory.lua` exactos de r575
demuestran `bagInjector:PreUseSlot` y su callback `PreUse`. La recompilación
del fuente de sort_bag es semánticamente igual al ALB efectivo baseline.
Se conserva el resto de su lógica; sólo se agrega el consumidor de la llave.

El RPC reaprovecha la primitiva AA10 comprobada para Ipnya (JoinUserChatChannel,
48 bytes de nombre). Usa otro namespace reservado y no comparte su estado ni
sus permisos. No se portaron opcodes, layouts ni comportamiento de AA8. La
extensión custom se diferencia expresamente de las mecánicas retail.

Fuente, outputs, scripts ejecutados y logs:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\private-alpha-panel`.
Contratos reproducibles: `Scripts/Aa10PrivateAlpha.contracts.json`.
Runbook: `Docs/AA10PrivateAlpha_es.md`.

## Gates

- Restore y build Release: correctos.
- Unitarias: **2772 correctas, 0 fallidas, 0 omitidas**.
- Lua 5.1 / parche: **4 correctas**, incluyendo remitente falso, doble clic,
  denegación, búsqueda UTF-8, ausencia de reintento y rollback inverso.
- SQLite: integrity_check correcto, todas las filas previas preservadas,
  tamaño final de entrada idéntico. Este gate V1 fue insuficiente: el padding
  no registrado fue rechazado por el cliente nativo; ver corrección V2 abajo.
- Dry-run, aplicación, reextracción, mapa/icono/Folio y segunda aplicación:
  correctos. Segunda aplicación **already_patched**, sin cambiar el hash.
- Control Center actual: no allowlist de game_pak; caché por ruta/tamaño/mtime.
  Typecheck y build correctos; **65 tests correctos, 1 omitido** por su suite.
- Game recreado con Docker. Login/DB/Game saludables. API local responde y
  puertos Game 1239, Stream 1250 y World 1240 escuchan. Configuración y catálogo
  del bind mount coinciden por SHA-256 con los preparados.
- Los únicos errores de catálogo observados son Smelting 29–32, frontera
  deprecada ya existente, no modificada por este trabajo.

Imagen Game: `sha256:fb81a5e3f16b9866d1bf93c16c4553a1700ece59d4bae885a9fc5a3e55ec93e1`.
Rollback: `aaemu10-private-alpha-rollback:20260911`.
Respaldo DB/imagen previa: `E:\AAEmu\rama_10\backups\private-alpha-deploy-20260911`.
Respaldo de entradas y manifiesto de aplicación:
`E:\AAEmu\rama_10\backups\client-patches\aa10-private-alpha-20260911-192141-265726Z`.

game_pak permanece en **92.412.597.248 bytes**.
SHA antes: `6661BEC7DF834C647F243593D21EFB925C4CB99E509878101C7234C307E954B9`.
SHA después: `8A162666BC1D5F723489674C6EEF49C2EE348EB0F5C2A8AE3CDA1A1F20EF7DBB`.

## Pendiente al terminar V1 (registro histórico, sustituido por V7)

Dannia estaba desconectada y sin llave al cerrar la inspección. Su posición
persistida es world 0, zone 379 (`gatekeeper_hall`), x=500.295, y=38373.5,
z=129.948. World informa `Zones=[]` tras el despliegue. No se iniciaron,
detuvieron ni relanzaron procesos de Zone; el usuario conserva ese lifecycle.

Primera interacción solicitada para aceptación: reconectar `gatekeeper_hall`
desde Control Center, entrar con Dannia en el cliente principal actualizado y
hacer clic derecho en la llave. Verificar primero ventana y autorización; luego
seguir el runbook para entregas/relog/rechazos. El evento de respuesta nativo y
su presentación en el chat de sistema necesitan aceptación real. Ningún test
de mocks, build ni hash sustituye esa evidencia.

Manifest estructurado: `PRIVATE_ALPHA_20260911.manifest.json`.

## Incidencia de arranque y reparación V2

El usuario reportó `Failed to load game data!`. El log nativo del 2026-09-11
16:32:35 informa `failed: database integrity check` y `Page 109470 is never used`.
V1 tenía 109469 páginas lógicas frente a 114772 páginas físicas: 5303 páginas
finales sin registrar después de VACUUM. Python SQLite moderno ignora esa cola
en integrity_check y dio un falso positivo de compatibilidad. Además VACUUM
incrementó schema_version de 1006 a 1007.

V2 reutiliza preserve_sqlite_size del proyecto, registra las 5303 páginas en la
freelist y restaura schema_version=1006. El constructor exige tamaños físico y
lógico iguales. La reparación del hash V1 y la construcción desde el respaldo
pre-alpha producen el mismo SHA-256 compact:
`C328849D7D2DB68E939A4E3C1A723F9E25083087D521401A3DF5B4C1DC839452`.
Se mantienen los 51011 ítems, el ALB y el catálogo de nombres del servidor.

Prueba de regresión: SQLite moderno acepta un archivo con 5303 páginas cero
no registradas; el gate nativo del builder lo rechaza y la reparación conserva
sus filas y crea una freelist válida con varios trunks. Suite Lua/parche: 5 pasan.
Evidencia de fallo preservada: `private-alpha-panel/native-startup-v1-failure.log`.
La aceptación de la ventana y las entregas sigue siendo un gate separado.

### Segundo gate nativo y V3

La ejecución controlada V2 (PID 58852, 16:42:53) aún falló: a las 16:43:09 el
cliente registró `Main freelist: freelist leaf count too big on page 109470`
y otros cuatro trunks. Se preservó `native-startup-v2-failure.log` y se cerró
únicamente ese proceso de prueba. El helper existente usaba 1022 hojas/trunk;
r575 necesita el límite legacy de 1016 para páginas de 4096 bytes, reservando
seis slots finales. Referencia primaria: https://sqlite.org/fileformat.html#the_freelist.
La evidencia nativa confirma el rechazo; no se infiere una versión exacta de SQLite.

V3 reorganiza sólo páginas libres, dejando seis slots finales vacíos, y valida
la cadena, conteo, duplicados y límite nativo. Regresión sintética ahora reproduce
ambos fallos y valida reparación e idempotencia. Compact final esperada:
`E5947F15726BF05C392CDC912BC778F2BFE6E407349A1F3A89BAA818B56C3187`.
V2 queda como intento fallido, no como parche aceptado.

### Despliegue V3 y aceptación de arranque

Aplicado y reextraído con éxito: `E:\AAEmu\rama_10\backups\client-patches\aa10-private-alpha-20260911-194647-327981Z\manifest.json`.
game_pak antes: `95ECDB10D463505525EB60756E8168C1BA62E1CDBBA967B2DF6BBE091D30EAD1`.
game_pak después: `7D35026A2AA81EAF7861A9A593C1D84FDE0B84D327FB6DAE50379DB846D3411D`.
Tamaño sin cambios: 92412597248 bytes. Mapa, icono y Folio conservados.

Prueba real PID 54092, iniciada 16:48:50 con Bin64/archeage.exe r575 del principal.
16:49:07: Loading Game Data; 16:49:15: OnLoadingWorldStart; 16:49:17: Loading
Complete de login2/loginbg4. Ventana r575 responsive. Cero errores de integridad,
freelist, páginas sin usar o Failed to load game data en este arranque.
Evidencia: `private-alpha-panel/native-startup-v3-success.log`.
El error de arranque queda resuelto. La ventana custom y entregas conservan
su aceptación pendiente dentro del mundo. No se operaron servicios ni Zones.

## V4: ventana bloqueada y reloj de respuesta

El usuario confirmó el arranque y aportó captura de Dannia en Gatekeeper Hall:
llave recibida, ventana abierta, controles apagados y respuesta de Game visible
`AA10AP1:60cf0:open:10000,5000,1000`. Confirmó que `Sin respuesta` aparece de
inmediato, no tras 20 segundos. La expiración borra pending y descarta el ACK
posterior. Se reemplaza la acumulación de OnUpdate por diferencia entre marcas
de X2Time:GetUiMsec() tomadas desde cada Request.

Contrato AA10: scripts/x2ui/loot/loot_dice.lua y delay_func_call.lua usan ese
reloj para plazos en milisegundos. Binding r575 VA 39884440 / GetUiMsec y cadena
SCChatMessage -> 3933cc50 -> 3972a0e0 -> 3979d1f0 se reanclaron byte a byte
al x2game.dll efectivo 405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734.
La emisión de CHAT_MESSAGE lleva channel, relation, name, message, info; no
se alteró la firma ni la autorización para intentar arreglar el temporizador.

Seis pruebas focales pasan, incluyendo un OnUpdate con argumento 600016 para
una solicitud de sólo 16 ms: no expira; acepta ACK y habilita controles. Una
segunda solicitud vence realmente a los 20 segundos y nunca se reintenta sola.
El ALB V4 esperado es 74BDCE3E3F77A8E68A86670C3749174E8E326A1F233C691DDF1E66618D7CDEF0,
30430 bytes de chunk rellenados a 30761. Compact se conserva en el hash V3.
Se preparó un candidato diagnóstico pero no se instaló; no quedan logs temporales
en el Lua. La confirmación funcional del temporizador requiere volver a abrir
la llave con este ALB, y permanece pendiente hasta observar esa interacción.

Aplicación V4: `E:\AAEmu\rama_10\backups\client-patches\aa10-private-alpha-20260911-200804-381661Z\manifest.json`.
SHA game_pak V4: `EC887BE54E03EE6AFEE9FAC8DC03194F424B55E50B1FCB1630ADFC041C84E146`; tamaño 92412597248 bytes.
ALB reextraído y mapa/icono/Folio sin cambios. Control Center typecheck/build
correctos, 65 pruebas correctas y 1 omitida. Sin reinicios de servidor/Zone.

## Cierre V7: respuesta nativa y aceptación controlada

V4 resolvió la expiración inmediata, pero la prueba real mostró que el ACK
seguía sin ser reconocido. El dispatcher r575 RVA `0x72a0e0`, anclado al DLL
`405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`, sustituye
el remitente del canal System **-2** por **DAILY_MSG**. El nombre vacío del
paquete no llega vacío a Lua. V7 exige canal -2 y DAILY_MSG, además de prefijo e
ID pendiente. Se mantiene el reloj de 20 segundos de V4. Las comprobaciones
contra otros canales, jugador y remitente vacío pasan en la suite.

V5/V6 fueron instrumentación temporal de diagnóstico; está retirada del fuente
y ALB final. El candidato V7 con error diagnóstico nunca se aplicó. El artefacto
efectivo es `aa10-private-alpha-v7-system-sender`, ALB
`ABDA91D8177C512FC2AD0DCE53BF9F6E3B48C961AC9BC4EFD35D99E6345F24FD`:
30.466 bytes compilados, entrada preservada de 30.761 bytes. Compact conserva
el hash V3 `E5947F15726BF05C392CDC912BC778F2BFE6E407349A1F3A89BAA818B56C3187`.

Aplicación con respaldo y reextracción:
`E:\AAEmu\rama_10\backups\client-patches\aa10-private-alpha-20260911-203738-128119Z\manifest.json`.
SHA-256 game_pak final:
`FECE92CBF0C8E56BFEA71C190F4072C35B4DA97CE6D3AF7631568D18ED16C12C`;
tamaño 92.412.597.248 bytes. Sentinelas mapa, icono y Folio conservadas.
Idempotencia: `aa10-private-alpha-20260911-204108-719370Z/manifest.json`,
`already_patched`, sin modificar bytes. Los manifiestos de aplicación conservan
su estado histórico previo a retail; este checkpoint registra la aceptación.

Pruebas nativas V7 del 2026-09-11, 20:44–20:54 UTC, Dannia/1007:

- Primera apertura `bdbc3`: acceso autorizado y controles activos.
- Catálogo `bdbc4`: 51.010 resultados, 5.101 páginas. Siguiente `bdbc5`
  muestra la segunda página con iconos y nombres.
- Búsqueda «Jarrón» `bdbc6`: 49 resultados. ID 98 `bdbca`: un resultado.
  Texto inexistente `bdbcc`: cero resultados y botones de entrega deshabilitados.
- Oro `bdbc8`, `gold/1`: suma exactamente 10.000 cobres, de 11.748.359.695
  a 11.748.369.695. Chat, inventario y SQL coinciden.
- Ítem `bdbc9`, `item/98/1/0`: Jarrón decorativo nuevo 16777516, count 1,
  bolso 129 → 130/150. El jarrón anterior 16777465 permanece; son dos en total.
- Cantidad 0 rechazada localmente, sin envío. Cantidad 21 `bdbcb` con sólo
  20 ranuras libres: rechazo del servidor, sin entrega parcial.
- Labor `bdbc7` rechazada al tener ya 9.380 de cuenta frente a cap 5.000;
  saldo de cuenta conservado. Regeneración de labor local ajena al panel.
- Revocación con ventana abierta: oro `bdbcd` denegado, controles apagados,
  saldo e ítems sin cambios. Se restauró exactamente la autorización original
  de Dannia (granted_by 0, granted_at 2026-09-11 19:23:59); no hay otros accesos.

Capturas en `private-alpha-panel`: `v7-retail-grant.png`,
`v7-retail-capacity-reject.png`, `v7-retail-access-denied.png`.
La llave 16777515 / template 900001 conserva una sola unidad. Ninguna entrega
de esta prueba se insertó directamente en SQL: se usó la ventana real.

Gates finales automatizados: seis pruebas Lua/parche correctas; Control Center
typecheck/build correctos, 65 pruebas correctas y una omitida. La suite servidor
previa de 2.772 pruebas y su build Release siguen aplicando: V7 no cambió código
servidor, imagen, configuración montada ni reinició servicios.

El usuario autorizó el login y operar únicamente la Zone de Dannia si hiciera
falta. Gatekeeper Hall ya estaba saludable: PID 58300, sesión 2917449124,
ZoneLoaded desde 19:32:45 UTC y heartbeats continuos. No se inició ni reinició.

Límites de aceptación: entrega positiva de labor sin probar por el saldo previo
superior al cap; otro personaje sin acceso, entrega rápida repetida y variaciones
de grado sin prueba nativa. Los rechazos y unitarias no se presentan como prueba
positiva de esos casos. El protocolo custom aún aparece en el chat de sistema.
Correo automático para otros jugadores sigue fuera de esta primera entrega.

Relog final completado a las 21:01 UTC con cliente PID 58288: Dannia vuelve al
mundo, inventario 130/150, saldo 11.748.369.695 cobres, una llave 16777515 y
jarrón nuevo 16777516 persistidos. Primera apertura `6dcba` autorizada sin
timeout; búsqueda posterior `6dcbb` devuelve los 49 jarrones. El cliente queda
abierto con esa búsqueda y la Zone saludable. Evidencia: `v7-retail-relog.png`,
`v7-retail-final.png`, `v7-relog-db.tsv`, `v7-final-zone-health.json` y reporte
`v7-retail-acceptance.json` con hashes de diez artefactos. Logs nativos V7 sin
errores del panel ni de integridad SQLite; permanecen los errores previos de
gm_console/X2Gm y texto voyage, ajenos a esta reparación. `git diff --check`
correcto, sólo advertencias preexistentes de finales de línea.

## Ampliación posterior V8

El estado V7 anterior es histórico. El cliente y Game efectivos avanzaron a V8:
búsqueda al escribir, ES/EN/ID y corrección de tildes españolas en Docker.
Consultar `CHECKPOINT_PRIVATE_ALPHA_SEARCH_20260911.md` y
`PRIVATE_ALPHA_SEARCH_20260911.manifest.json` para hashes actuales, despliegue,
rollback y aceptación nativa final. Los permisos siguen limitados a Dannia.
