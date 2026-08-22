# Checkpoint nativo: boton de salida de instancias r575

## Resultado

El cliente ArcheAge Returns 10.0.2.13 r575 ya incluye y carga el boton flotante de salida de dungeon. No se requiere parchear la interfaz ni el `game_pak`. Habia dos vacios coordinados en el servidor: el flujo de dungeon no sembraba el estado retail de instancia que habilita el boton y, si el cliente enviaba la peticion de salida, esta solo se atendia para battlefields.

## Evidencia del cliente

- `game/scriptsbin64/x2ui/hud/toc.g` carga `indun_out_button.lua` de forma nativa.
- `indun_out_button.lua` crea `indunOutBtn`, aplica el estilo `instance_out` y lo ancla a `zoneNameInformer`.
- La visibilidad se decide mediante `X2Indun:IsEntranceIndunMatch()` en `LEFT_LOADING` y `ENTERED_WORLD`.
- Al confirmar la salida, el Lua llama `X2Indun:AskLeaveInstantGame()`.
- En `x2game.dll` r575, `AskLeaveInstantGame` (`FUN_39198520`) construye y envia `CSLeaveInstantGamePacket`, opcode `0x12A`.
- `IsEntranceIndunMatch` (`FUN_39198600`) exige tanto una zona instanciada valida como que la maquina de estados de entrada haya superado la aplicacion e invitacion nativas. Howling Abyss cumple el contrato retail: `zone_key=265`, `group_id=51`, `instances.id=20`.
- `game/ui/button/instance_enter.dds` confirma que `instance_out` es una flecha circular dorada. Ese control no aparece en la captura original; el icono negro y blanco a la izquierda del minimapa es la brujula.

## Reconstruccion aplicada

`IndunGameData` construye el cruce generico entre `indun_zones.zone_group_id` e `instances.id` para objetivos `IndunZone`. Para Howling Abyss usa `20`, no el grupo `51`, sin hardcodear una dungeon concreta.

La entrada normal reconstruye el handshake compartido r575 antes de cargar la Zone:

1. `SCAppliedToInstantGamePacket(instances.id)` lleva el cliente a estado 1.
2. `SCInviteToInstantGamePacket` presenta la invitacion nativa y lleva el cliente a estado 2. Su cuerpo r575 exacto es `invitationTime -> ZoneInstanceId -> type -> matchingKey -> packet vacio -> accept -> maxEntry`; para una entrada directa de dungeon `accept=1` y `maxEntry=1` seleccionan el dialogo de confirmacion inmediata, no la espera de matchmaking.
3. Al aceptarla, el cliente pasa a estado 3 y envia `CSInvitationAnswerPacket`.
4. El servidor valida tanto el personaje como el `invitationTime` pendiente y recien entonces encola la entrada. `SCProcessingInstancePacket` envia el par completo `zoneId + instanceId` antes de `SCLoadInstancePacket`; aunque el serializer denomina `state` al segundo `u32`, el handler r575 compara ambos campos como un `ZoneInstanceId` de 64 bits.

`CSCancelInstantGamePacket` intenta primero retirar una invitacion de dungeon pendiente. Si existe, elimina su token y envia `SCCancelInstantGamePacket` por la ruta que restablece la maquina de estados del cliente; si no existe, conserva la cancelacion de matchmaking/battlefield. Las instancias de sistema mantienen la entrada directa previa.

La primera prueba en cliente detecto dos incompatibilidades que el handshake incompleto ocultaba: el port base serializaba `SCInviteToInstantGamePacket` como `ZoneInstanceId -> ruleset -> corps -> qualifier`, desplazando todos los campos que r575 esperaba, y enviaba `SCProcessingInstancePacket(zoneId, 0)` aunque la instancia dinamica era `100`. El sintoma reproducible fue el icono de preparacion visible, la ventana `Creating the Howling Abyss dungeon`, ausencia total de `CSInvitationAnswerPacket` y un `CSCancelInstantGamePacket` que no retiraba la solicitud. La correccion actual reemplaza ambos layouts y cubre el cancel de esa ventana.

`CSLeaveInstantGamePacket` conserva primero la ruta de `CurrentInstantGame` para arenas/battlefields. Cuando no existe una partida instantanea activa, delega en `IndunManager.RequestLeaveInstance`, el mismo camino ya utilizado por los doodads nativos de salida de dungeon. Este dispara `OnDungeonLeave` y restaura `MainWorldPosition` mediante `SCLoadInstancePacket`.

No se usa `SCSysIndunIndexPacket` para forzar la interfaz: la rutina nativa r575 demuestra que ese paquete solo actualiza el indice de canal si coinciden zona e instancia y no participa en la condicion de visibilidad del boton.

## Validacion requerida en cliente

1. Solicitar entrada a Howling Abyss con la Zone instanciada levantada y aceptar la invitacion nativa.
2. Comprobar que la carga de la DG ocurre despues de aceptar.
3. Comprobar que aparece la flecha circular dorada de salida junto al informador de zona/minimapa y pulsarla.
4. Confirmar el dialogo de salida.
5. Verificar retorno al punto guardado del mundo principal, marcador del mapa y posibilidad de movimiento sin relog.

## Validacion automatizada

- Compilacion `Release`: correcta.
- Suite `AAEmu.UnitTests`: `1500/1500` correcta, sin errores ni omisiones.
- Pruebas nuevas: cruce generico del catalogo de instancias, contrato canonico Howling `51 -> 20`, serializacion del paquete de aplicacion, layout completo de invitacion r575 incluido su packet vacio, tupla de procesamiento `265/100`, respuesta correlacionada por token, cancelacion de invitacion pendiente, preservacion de `CurrentInstantGame`, delegacion de salida aceptada, rechazo propagado y personaje ausente sin acceso al manager.
- Imagen `aaemu-world:10.0.2.13-r575-local` reconstruida y servicio Game desplegado en estado `healthy`; listeners `1239`, `1240` y `1250` publicados. No se reiniciaron ni controlaron las ZoneHost.
