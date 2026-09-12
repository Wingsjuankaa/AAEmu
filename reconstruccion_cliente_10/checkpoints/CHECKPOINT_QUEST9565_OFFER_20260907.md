# Un artefacto antiguo (9565): oferta de doodad sin requisitos de inicio

Estado: corrección backend desplegada, aceptación interactiva pendiente.
Clasificación: `server-required`; requisitos AA10 positivos y rechazo del proceso
operativo confirmados. No se modifica game_pak, catálogo ni progreso de personajes.

Target `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`, HEAD inicial
`fd53b458573572cc354c8564293f274801d9aa3e`, árbol inicialmente limpio.
Padre exacto `upstream/client_version/zone-10.0.2_r575` en
`7babcb3a706c64295b5aaaeec8abe57e4d09b4da`. El padre carece de la validación
previa de oferta; su baseline también envía SCDoodadQuestAccept sin ese gate.

## Evidencia

El usuario informa que el juego queda bloqueado en el primer diálogo de Enos:
«¿Has encontrado un trozo de Haradio, dices?». Identidad localizada 9565,
componente Start 41750, burbuja 38948. La etiqueta rusa de hablante procede del
campo localizado `change_speaker_name`; es un defecto de textos independiente y
no demuestra una causa de cuelgue. No se parchea el cliente por esa coincidencia.

Logs del 2026-09-07 UTC:

- 23:05:13 y 23:41:40: doodad13567/obj101316, fase compartida39579,
  fase del personaje40471, offer kind1, skill11006: selecciona quest9565.
- 23:05:31 y 23:43:43: llega CSStartQuestContext opcode0x117; AddQuest rechaza
  «does not meet requirements ... Quest 9565, ComponentId 41750».

No se capturó un dump de bloqueo del cliente. Lo probado es que el servidor
ofreció una misión imposible de aceptar y luego devolvió false sin resolver esa
sesión de diálogo. La corrección evita abrir esa sesión inválida; no se declara
probado un deadlock del ejecutable ni se inventa un paquete de cancelación.

Full AA10 SHA256 `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`
y compact montada SHA256 `85024F044F2A0B119776012EE516F90FDD9DB28B4E5581403D40526B1B7D8C65`
coinciden en los requisitos:

| Quest / Start | unit_reqs | kind | value1 requerido |
| --- | --- | --- | --- |
| 9563 / 41742 | 67201 | 31 complete_quest_context | 9266 |
| 9564 / 41746 | 67203 | 31 complete_quest_context | 9563 |
| 9565 / 41750 | 67247 | 31 complete_quest_context | 9564 |

Dannia1007, zona354: sin quests activas 9560–9570 y sin bloque149 en
completed_quests. Bloque144=`0000E8FFF6DF0700`: 9266 sí está completada.
No se cambió ningún flag para saltar la cadena.

## Corrección

`DoodadFuncQuest.IsEligible(kind, character, template)` comprueba además de
activa/completada/repetible los límites de contexto (nivel/raza) y todos los
componentes Start mediante el evaluador nativo existente `CanComponentRun`.
Es el mismo gate que AddQuest aplicaba demasiado tarde. Los reportes mantienen
su comprobación de misión activa y no vuelven a evaluar requisitos de aceptación.

`Doodad.UseQuest` filtra candidatos con esa validación antes de escoger el
primero; una oferta inválida no tapa otra válida posterior. `DoodadFuncQuest.Use`
revalida antes de emitir la oferta, cubriendo el camino genérico de ejecución.
Si no hay interacción válida, devuelve el error existente NoInteractionAvailable.
No hay excepciones por ID de misión ni bypass de requisitos.

## Validación y despliegue

Restore y build Release aprobados. Suite **2686/2686**. Cuatro regresiones nuevas
usan la fila retail67247 cargada desde SQLite: rechazo sin mutación antes de9564,
aceptación después, selección de otra oferta válida, nivel/raza/repetibilidad y
reporte de misiones activas independiente del requisito de inicio.

Imagen previa: `afcfc2047e50bd02e22e358fc7e5e0a9fe59080ff247282cb3f8cf745c019d66`.
Rollback conservado: `aaemu-world:rollback-pre-quest9565-offer-20260907`.
Imagen desplegada: `94ba0d7a521bd34baf6a08b3d31c63ccf314eaefc1a354880e2858e46bb25876`.
Game DLL idéntica en `/app` y `/app/game`:
`ED7ED5480F9DBE8E7C9FFD30313106E0448E16658C818591E2E1716F3D444B79`.

Respaldo consistente de DB, tomado antes de recrear Game:
`E:\AAEmu\rama_10\backups\quest9565-offer-20260907\aaemu_game.sql`, SHA256
`06155C22F6F7CA9D83F34EECBFFBADEA0C352C89A4478643091F5F41E48E70B8`.
Sólo se recreó Game, a las23:54:34 UTC; DB y Login se conservaron.
No se iniciaron ni relanzaron procesos Zone. El usuario debe relanzar Zone354.
Para rollback, reetiquetar la imagen anterior como
`aaemu-world:10.0.2.13-r575-local` y recrear sólo Game con los dos compose canónicos.
No restaurar DB para revertir este cambio de código.

Evidencia local:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\quest9565-offer`
(native-contract.json, rejected-starts.log, tests.log, docker-build.log).
El manifiesto de este checkpoint registra la verificación final de startup.
Game confirmó `Server started!` a las23:56:20 UTC (96.25s), conexión con Login,
listeners1239/1240/1250 y API interno1280. Contenedor healthy, cero reinicios.
Los mensajes de Item Smelting permanecen fuera de alcance por decisión vigente.

## Continuación y aceptación

La cadena empieza usando **Mineral resplandeciente**48471, después de
«Camino al Jardín»9266. Acepta9563 (texto actual «Una misteriosa orejita»), que
se reporta a un miembro del grupo947: Evonbro8627, Pamela8664 o Camila8665.
Luego9564 («Ore A diferencia de los otros») entrega48472 y se reporta al doodad
correspondiente; su finalización desbloquea9565. Los nombres mal traducidos se
conservan aquí para que el usuario reconozca su cliente actual.

Origen del mineral confirmado en full y compact montada: NPC19009 **Millennium
Mammoth**, loot_pack13016, loot95454, item48471, rate2000000, cantidad1–1.
La compact del cliente omite esos valores de botín, pero el servidor conserva
los valores completos. Dannia no tiene guardados48471/48472/48475/48476.

Prueba inmediata: reconectar y relanzar Zone354; interactuar con el mismo doodad.
Mientras9564 siga pendiente, no debe abrir la cámara de9565; otra oferta válida
puede abrirse o debe recibirse NoInteractionAvailable. Después de completar la
cadena,9565 debe ofrecerse y aceptarse normalmente. Esos resultados visuales
requieren confirmación del usuario; las pruebas automatizadas no los sustituyen.
