# Cadena10038 ->10159 ->10039: temporizador personal del objeto

Target rama_10; HEAD45bba0ad49fee55ab30a80168b4d6caefbb9ac87, padre upstream/client_version/zone-10.0.2_r575,1017677b40be6508861a8fb74e9d09fa496873c9. Clasificación server-required: reconstrucción de la fase de un actor client_doodad/once_one_man al validar una interacción. Conserva la reparación SphereBuff del reporte4 y el resto del árbol. No cambia cliente, compact ni placements.

## Evidencia

Captura del usuario: «Flora demoníaca»10038 completada; exclamación junto a Tahyang devuelve «No puedes usar esto». Log artifacts/quest10038-live.log confirma entrega a14:38:29 contra doodad14955/Obj101544. Intentos de11006 a14:38:41 y14:39:25 apuntan a OTRO actor15353/Obj101639: sharedPhase45390, characterPhase45391, candidates0.

Quest10039 exige completar10038 y10159 (unit_reqs69300 y79516, componente43622). Por eso omitir10159 no es la reparación correcta. Doodad15353 posee once_one_man y client_doodad. Contrato:

-QuestReact2300:10038 Completed ->45391.
-Timer18429: espera500ms ->45397.
-Func40997/Quest2198 en45397 ofrece10159.
-QuestReact2307:10159 Progress ->45392; Func40993, Use44495 ->45394.
-Objetivo1172 de10159 pide interacción19 con15353; reporte en el mismo actor.
-Ready de10159 resuelve45394; Completed resuelve45396. Una vez entregada10159, se cumple el requisito adicional de10039.

Clausura de funciones, temporizador y requisitos idéntica full/runtime: artifacts/quest10038-contract.json SHA2565ee4427a14be9417dcf8d9f78aa3e6d4566ec598571e7b917bcdffd90266214c. El resolvedor local anterior sólo recorría QuestReact, sin saltos de temporizador. Ni el padre local ni AA8 contienen ese resolvedor personal equivalente para reutilizar la corrección. No se inventó un paquete de fase ni se ejecutó el timer compartido para todos los jugadores.

## Corrección

CharacterQuests registra en memoria el momento de una nueva finalización y la primera visibilidad de cada actor personal. El reloj comienza en el más reciente de ambos eventos. Una finalización cargada desde DB usa la nueva visibilidad; salir de visibilidad descarta la observación, de forma que relog/reaparición no aprovechen un reloj antiguo. Los datos permanecen separados por CharacterQuests.

Doodad.ResolveQuestReactPhase puede continuar por un único DoodadFuncTimer cuando el actor es client_doodad y once_one_man, la transición actual está justificada por Completed y su reloj observado ya cumplió el delay nativo. Descuenta el tiempo de cada salto consecutivo; no adelanta el reloj. Sin observación, sin finalización o con múltiples timers ambiguos no avanza. Las reacciones actuales tienen prioridad; los ciclos siguen limitados por visited. No muta FuncGroupId compartido, no aplica efectos del timer ni recastea. La selección posterior conserva DoodadFuncQuest.IsEligible y los requisitos de aceptación.

## Validación y entrega

ClientQuestTimerPhaseTests:8 casos. Límites0/499/500/12000ms, observación/finalización ausentes, sucesor Progress/Ready/Completed, tiempos consecutivos/ciclos y separación de relojes por personaje/reaparición. Suite completa2790/2790, build Release sin errores; advertencias existentes. Artefactos quest10038-focal.log, quest10038-gates.log y quest10038-docker-build.log.

Backup previo en E:/AAEmu/rama_10/backups/quest10038-20260912: DB, compact, log, World y hashes. Rollback de Game: aaemu-world:rollback-quest10038-20260912, que conserva la reparación del puente. No restaurar DB sobre progreso posterior: no hay migraciones ni cambios manuales a las quests. Manifest de despliegue registra imagen y DLL efectivas. No se operan Zones.

Reporte4 cerrado por confirmación del usuario y avance a10038; esta incidencia nueva no tiene reporte en la cola al consultar. No se alteró el reporte3 de prueba.

Aceptación retail pendiente: volver a entrar con el perfil Garden activo e interactuar con la exclamación junto a Tahyang. Debe ofrecer10159 en vez de NoInteractionAvailable. Validar luego su interacción y entrega normal antes de afirmar cerrada toda la cadena10039. No repetir ni abandonar10038.

Despliegue verificado: imagen e4bc61069835acd18a24487b066a1c5c8cfd186a5601588034a0f4a00754e1d8, Game healthy, World API responde, puertos1239/1240/1250/1280 disponibles y arranque sin ERROR/FATAL. Compact conserva el hash previo. Evidencia en artifacts/quest10038-deploy; aceptacion del cliente aun pendiente.

## Retest fallido y corrección de visibilidad por lotes

El usuario confirmó que el primer despliegue NO resolvió el caso. Los intentos del 12/09 a las 14:54:31 y 14:54:59 UTC siguen en characterPhase=45391, candidates=0 (artifacts/quest10038-retest.log). No considerar la suite anterior ni el startup como aceptación retail.

Causa localizada: el reloj se inicializaba únicamente en Doodad.AddVisibleObject, pero Region.AddToCharacters y WorldManager.ResendVisibleObjectsToCharacter excluyen explícitamente los doodads de esa ruta y emiten SCDoodadsCreatedPacket en lotes. La entrada/reconexión de Dannia no registraba visibilidad; GetClientDoodadCompletionAge devolvía null y el resolvedor conservaba la fase previa al timer. La salida de región también usa SCDoodadsRemovedPacket y omitía descartar relojes.

Se centraliza la notificación posterior al create en Doodad.OnVisibilityCreated: creación individual, lote de región y reenvío de login/cinema. Conserva la sincronización de reportes ya existente. Region.RemoveFromCharacters descarta las observaciones de los IDs incluidos en cada lote de eliminación. No cambia el formato ni agrega paquetes. La ruta de InteractionEffect que sólo sincroniza un reporte no inicializa relojes.

Regresión añadida que invoca Region.AddToCharacters/RemoveFromCharacters con 31 doodads (dos lotes), comprueba que ambos lotes habilitan la fase nativa 45397 después de 500 ms y que repetir un snapshot no reinicia el reloj. También cubre creación/eliminación individual y exclusión de actores que no sean personales y client_doodad. Esta prueba cubre la ruta omitida por las ocho pruebas previas, que llamaban directamente a ObserveClientDoodadPhase.

Restore y build Release sin errores; suite completa 2792/2792 y focal 10/10. Logs artifacts/quest10038-batch-{focal,gates,docker-build}.log. Respaldo independiente E:/AAEmu/rama_10/backups/quest10038-batch-20260912, imagen rollback aaemu-world:rollback-quest10038-batch-20260912. Se conservan DB, compact y arreglos anteriores; no se conceden quests manualmente ni se opera el lifecycle de Zones. Pendiente nueva aceptación retail tras el segundo despliegue.

Segundo despliegue verificado: imagen sha256:15fdfc7160c7337406eefb6680371eb6ff3781f783c560f1bb327b00ea253a9d, Game/Login healthy, GameService started a las 15:06:37 UTC, puertos1239/1240/1250/1280 y World API disponibles, sin ERROR/FATAL en el log de arranque. Compact sin cambios. Evidencia en artifacts/quest10038-batch-deploy. Pendiente interacción del usuario; no se declara cerrada la cadena.
