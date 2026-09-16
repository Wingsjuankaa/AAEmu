# Invocación de pesqueros y revisión de pesca — 2026-09-16

Estado: correcciones implementadas, probadas y desplegadas; aceptación en cliente pendiente.
Target: `rama_10`, HEAD inicial `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`.
Padre consultado: `upstream/client_version/zone-10.0.2_r575` (`1b72e88e3`), sin integrar sus cambios.
Se conservaron los cambios locales anteriores a esta reparación.

## Síntoma y alcance

El usuario informó de un aviso similar a «ya tienes barcos invocados» con Moby Drake
y un pesquero normal. Los pergaminos persistidos identificados fueron Moby Drake
38611 (Dannia) y pesquero de los Daru 41559 (Wingsjuan). Ambos tenían detalle legado
de 33 bytes a cero; no había un barco persistido de esos personajes. Por tanto, la
corrección del identificador de un barco ya usado no demuestra por sí sola la causa
del primer intento fallido. Falta el texto exacto y una reproducción correlacionada.

El reporte 6 describe requisitos de las cañas y queda en `needs_retest`.

## Cambios confirmados

- El detalle del pergamino r575 lleva un ID de barco de 32 bits, estado de destrucción,
  fecha de 64 bits, coordenadas X/Y de 64 bits y cuatro bytes finales. El servidor
  escribía un byte de tipo redundante, un ID de 24 bits y una fecha de tamaño variable.
  Ahora emite siempre los 33 bytes nativos y conserva los cuatro finales sin atribuirles
  una semántica no demostrada.
  Las coordenadas opcionales se conservan al leer, pero no se rellenan al invocar:
  el consumidor nativo usa sus valores no nulos para limitar la distancia de la siguiente
  invocación. El marcador del barco activo sigue usando `SCMySlave`.
- `ItemUpdate` escribía ceros para objetos con campos tipados fuera de `Item.Detail`.
  En particular, `UpdateSummonSlaveItem` borraba en el cliente el vínculo del pergamino
  recién invocado. Se serializan ahora sus campos reales dentro de la unión de 128 bytes.
  También se preservan peso y longitud de peces. El equipo mantiene su serializador propio.
- La actualización periódica ya no anuncia barcos muertos o en retirada, después de
  haber enviado `SCSlaveRemoved`, evitando volver a publicar su marcador durante el portal.
  La búsqueda del barco activo excluye velas y otros componentes cuyo propietario es el
  propio barco. Antes podían aparecer como un barco aún invocado mientras el casco se retiraba.
- Se cargan y comprueban `items.actability_group_id`/`actability_requirement` y los límites
  de nivel antes de mover equipo de un personaje. Rechazar una caña no mueve el objeto.
- La protección de canalización reconoce las habilidades de caña por tag 1024 y objetivo
  posición, en lugar de limitarse a plots 809/821. Incluye la habilidad 39905/plot 3706
  de la caña definitiva y respeta los campos de cancelación del catálogo.

La caña definitiva 46503 no exige 150.000 de pesca para equiparse: el requisito de uso
está en `unit_req 61230`, habilidad 39905, grupo 7, valor 150000, incluyendo bonificaciones.
No se añadió un requisito de equipo que el catálogo no contiene.

## Persistencia y protocolo

Los blobs históricos de 33/37 bytes se recuperan como formato legado. Las nuevas
escrituras a MySQL usan un prefijo de almacenamiento `SL10` y el cuerpo nativo de 33 bytes.
Ese prefijo nunca se envía al cliente. La migración ocurre al guardar normalmente el
objeto; no se reescribieron inventarios mediante SQL. Las lecturas repetidas no vuelven
a desplazar el ID. El tratamiento local de fecha evita el conversor genérico defectuoso
`Helpers.UnixTime(long)` sin cambiar consumidores ajenos.

Evidencia nativa x64 del cliente principal:
SHA-256 `405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`.
RVA `0x656080` y `0x656620`: consumidores del estado del pergamino.
RVA `0xA3CCD0`: codec que copia los 33 bytes después del discriminador tipo 2.
Los primeros 64 bytes de los tres puntos coinciden con la base Ghidra usada.
Las pruebas de escritura acreditan el cuerpo; no sustituyen una captura del lifecycle.

## Cobertura de pesca

`Scripts/AuditFishingSummons.py` permite repetir la auditoría de SQLite completa y compact.
Ambas contienen 66 descripciones de tamaño/peso, 24 efectos SpawnFish, 32 funciones de
bancos de peces, 142 relaciones de venta y 103 relaciones de conversión en trofeo.
La base completa no tiene bancos sin spawner/miembros, peces sin objeto ni trofeos sin
objeto de salida. Compact omite tablas de spawners: esas comprobaciones se registran
como no evaluables allí, no como referencias rotas.

Excepciones del catálogo conservadas: pergamino 1178 referencia slave 11 ausente
(no es ninguno de los pesqueros investigados); relación de venta 143 referencia el
material TEST 42063, que no es un pez y no tiene `fish_details`. No se inventaron filas.

Ya existen implementaciones y pruebas de bancos y cebado, selección ponderada, enganche,
tensión/rotura, coordinación World/Zone, captura y persistencia de tamaño/peso, venta y
trofeos. Esta revisión no demuestra una aceptación completa de todas esas interacciones
en el cliente. Se conservan fronteras de evidencia en fórmulas/timings no cerrados.

## Español

Se consultaron los checkpoints de pesca y vehículos/naval y los textos instalados en
el cliente principal `es_ES-full-preview`, canal interno `en_us`. Los errores usan los
mensajes nativos ya localizados. No se cambiaron traducciones, SQLite del cliente ni
`game_pak`. «Ya está invocado.» corresponde a `SLAVE_SPAWN_ERROR_ALREADY_SPAWNED` (99),
pero el usuario todavía no ha confirmado que fuese ese mensaje exacto.

## Validación y despliegue

Restore correcto, build Release sin errores y 2.879 pruebas correctas, sin omitidas.
Incluyen bytes exactos, ID de 32 bits, fecha, actualización en vivo, recuperación de
blobs legados, tres ciclos de persistencia, rechazo de equipo sin mutación, umbral de
la caña definitiva y regresiones del serializador del equipo.

Imagen desplegada en `aaemu10-game-1`:
`sha256:5fac1ab533e60b063ec2f433c2849920d05614acc6b17bd4f96b510ed5e56b1b`.
Se comprobó que no había personajes conectados antes de recrear Game.
Arranque final confirmado a las 10:13:47 UTC; API responde, contenedor saludable y cero reinicios.
No se operó el lifecycle de Zones. La verificación final de arranque cargó 102 bancos
de peces en el mundo principal. Los avisos de Item Smelting corresponden al dominio
deprecado fuera de alcance; la desconexión Zone inicial corresponde a la recreación de Game.

Evidencia y logs: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\fishing-summon-20260916`.
Respaldo: `E:\AAEmu\rama_10\backups\fishing-summon-20260916`.
Incluye dump consistente de MySQL, compact montado e imagen anterior etiquetada
`aaemu-world:rollback-fishing-20260916`.

**Rollback:** detener Game, restaurar el dump previo antes de volver a la imagen anterior,
o convertir explícitamente los blobs `SL10` al formato antiguo. La imagen anterior no
entiende esos nuevos blobs. Restaurar el dump revierte cambios posteriores al respaldo;
no hacerlo automáticamente después de nuevas sesiones de jugadores. El compact no cambió.

## Aceptación pendiente

Primera interacción: entrar con Dannia, intentar invocar Moby Drake una sola vez en agua
válida y registrar el texto exacto si falla. Revisar logs/persistencia antes de seguir.
Después: retirar, volver a invocar y volver a entrar conservando barco y equipo; repetir
con el pesquero de los Daru. Para pesca: verificar una caña por debajo/en el umbral,
realizar una captura desde el barco, venderla y convertir otra en trofeo conservando tamaño.
No declarar resuelto el aviso original ni la pesca completa hasta cerrar estas pruebas.


## Reproducción del aviso persistente — 11:02–11:07 UTC

La imagen `5fac1ab5...` y el DLL Game `a80f13c3...` estaban activos durante los intentos.
Los logs muestran `SpawnSlave` de Wingsjuan con Moby Drake 38611 y Daru 41559.
Ambos llegaron al servidor y fueron rechazados por no hallar agua con la profundidad
calculada (14,3 m) dentro del radio de búsqueda de 55 m. No eran rechazos por barco activo.

Causa probada del mensaje engañoso: la rama de agua/espacio enviaba error 583
`SLAVE_SPAWN_ERROR_INVALID_AREA`. En AA10 ese código pertenece al retorno de un barco
con carga a la última ubicación de retirada (ui_texts 4667). Coreano, francés y
español instalado coinciden. Se cambia el rechazo de barco a 100
`SLAVE_SPAWN_SHIP_NEED_MORE_SPACE` (ui_texts 101) y el de vehículo terrestre en agua a
95 `SLAVE_CANNOT_SPAWN`. No se modifica la traducción ni se altera el cálculo de
profundidad sin evidencia nativa. Build y 2.879 pruebas correctas.

Se solicitó un intento desde agua abierta para separar la ubicación del umbral de
profundidad. El resultado en juego y el despliegue de esta segunda corrección se
registran en el manifiesto.


Segunda corrección desplegada a las 11:11:32 UTC, imagen
`sha256:8c1e7aeee15b08671f455ac187ae72f0e0bc992c41277411b2d4ffd2c6208b81`,
Game DLL `6089a0a6ddede8e516712947bae731f828fcdd1fd06b2dacb643ee7b3061f6d9`.
Se avisó del reinicio con el jugador conectado. Respaldo adicional de DB e imagen
previa en `backups/fishing-summon-20260916/live-error-message`.
El personaje se desplazó durante la revisión, pero no hubo otro request de invocación
antes del despliegue; la aceptación desde agua abierta sigue pendiente.

El usuario confirmó literalmente el aviso de carga durante este seguimiento; queda
cerrada la identificación del mensaje original como error 583, no error 99.


## Seguimiento: orilla y caída de Zone — 2026-09-16

El usuario reprodujo dos defectos separados: rechazo desde tierra y éxito al nadar,
seguido de caída de Zone 179. Los logs sitúan la orilla en (15647,5;15425,4), suelo
106/superficie 100. La primera invocación aceptada apareció en (15651,94;15485,02),
fuera de los 55 m originales desde tierra, y provocó el crash a las 11:25:34 UTC.
El segundo dump repite la excepción a las 11:27:00 UTC.

**Caída nativa:** el stub de ZoneHost upstream reponía `mov rdx,[rip+disp32]`
con global RVA 0x1738FB8. La instrucción original demuestra 0x1638FB8; ambos dumps
muestran RDX=0 y acceso a dirección 8 en RVA 0x360869. Se conserva el snapshot y
se aplica un parche local reproducible desde el wrapper. Dos pruebas Rust, los
32 archivos de procedencia, tres probes del candidato y la auditoría nativa pasan.
El usuario cerró las Zones y el publicador instaló el EXE corregido a las
11:39:20 UTC, SHA-256 525B02C3894B868D8CBA40B3382FA666A0C02C0F2A6B359C861B87E1F58850B9.
Hay respaldo del EXE anterior bajo Bin64/.zonehost-updates/backups. Codex no operó
procesos de Zone. Detalle de instrucciones y hash DLL en Tools/AAEmu.ZoneHost/patches/README.md.

**Orilla:** si el suelo del personaje está seco, la búsqueda localiza primero
agua real cercana, limitada al desplazamiento preferido del template (15 m para
estos pesqueros), y conserva desde allí el alcance sobre agua (55 m). Nadando
conserva el origen anterior. Sigue exigiendo 14,3 m de profundidad y rechaza
terreno seco, superficial, no finito o polígonos elevados. Esta corrección del
algoritmo del servidor responde a la reproducción; no se presenta como fórmula
nativa reconstruida de calado/colisiones. Las OBB nativas y el calado exacto siguen
siendo frontera separada, sin alterar física por conjetura.

**Regresión preventiva de equipo:** Inventory.Load restaura también la selección
de personajes, antes de cargar pericia. Restaurar el mismo objeto y hueco ya
persistidos no constituye equiparlo de nuevo; se evita rechazarlo por requisitos
sin cargar. Los movimientos reales siguen validando. El ítem 16777536 de Dannia
se comprobó conservado en DB (49210, contenedor65547, equipo8); no se modificó su fila.

Restore/build Release correctos, 2.889 pruebas sin fallos ni omitidas, incluidas
orilla/nado, mirar tierra, agua distante, profundidad y restauración del equipo.
Respaldo adicional de DB y etiqueta de imagen `aaemu-world:rollback-fishing-shore-20260916`
en backups/fishing-summon-20260916/shore-zone-crash. No se cambia compact ni cliente.
Aceptación todavía necesaria: invocar desde esa orilla, observar barco y Zone
estables, retirar/reinvocar y completar captura/venta/trofeo.


Game actualizado a las 11:43:35 UTC con imagen
`sha256:70cd0c2c1d4076fae3a2e7ee02413ddbd4980cad2d62177050e1b03f3341fa2d`.
DLL Game `6e5eec8e39825e87b9f8bc9c01e8d8fda55c99bb786ee65c2327533035151a3a`.
Arranque confirmado 11:45:10 UTC; API operativa, 102 bancos de peces cargados,
compact montado sin cambios y cero reinicios. Prueba solicitada al usuario:
iniciar sus Zones e invocar Moby Drake una sola vez desde la orilla anterior.
