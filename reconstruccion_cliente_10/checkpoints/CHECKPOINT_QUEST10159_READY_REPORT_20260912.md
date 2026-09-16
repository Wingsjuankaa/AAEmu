# Quest 10159: entrega de la luz de Kyprosa

Target rama_10, HEAD 45bba0ad49fee55ab30a80168b4d6caefbb9ac87; padre upstream/client_version/zone-10.0.2_r575, 1017677b40be6508861a8fb74e9d09fa496873c9. Continúa la reparación 10038 -> 10159 -> 10039. No modifica SQLite, cliente, requisitos, premios ni quests persistidas.

## Evidencia y contrato

El usuario confirmó que ahora pudo aceptar e interactuar. Log artifacts/quest10159-live.log: a las 15:09:57 UTC el servidor selecciona fase personal 45397 y ofrece 10159; a las 15:09:58 la acepta. A las 15:10:03 comienza skill 44495, que termina a las 15:10:13. Se selecciona Use en 45392, nextPhase 45394. El objetivo Interaction1172 pasa a 1/1 y la evaluación encolada activa Ready44189/ReportDoodad399. La captura muestra «[Completada] Luchamos unidos», la luz y «No cumple los requisitos». No llega un nuevo StartSkill11008 de entrega en ese tramo.

Datos r575 ya extraídos en artifacts/quest10038-contract.json: QuestReact2312 en fase45391 reacciona a Ready10159 y va a45394. Allí Func40995/Quest2196 reporta10159; modelo20177. La condición de entrega399 nombra doodad15353. El objetivo no declara HighlightDoodadPhase (valor-1). No se deriva un destino de IDs cercanos ni se elimina el paso intermedio.

La sincronización existente llamaba GetCompletedInteractionReportPhase durante InteractionEffect, ANTES de la evaluación aplazada. Además, ese resolvedor exigía un highlight explícito para reconstruir Use -> report. Por ambas razones no enviaba la fase de entrega a este actor. El contrato SC0x151/ClientDoodad::ChangePhase y su body personal ya están documentados y probados por CompletedInteractionReportPhaseTests; se reutilizan sin variar opcode/body ni emitirlo a otros jugadores.

## Corrección

- Doodad conserva la restauración previa de objetivos con highlight. Si no hay tal ruta, exige una quest Ready cuyo ReportDoodad corresponda al actor y resuelve el grafo nativo personal actual. Sólo acepta el destino si contiene ReportQuest de esa misma quest. No restaura destinos ambiguos ni cambia la fase compartida.
- Quest.RunCurrentStep detecta exclusivamente la transición a Ready y, después de SCQuestContextUpdated, sincroniza los actores visibles que la condición de entrega nombra. No hay sondeo periódico ni actualización repetida por permanecer Ready.
- La ruta de visibilidad individual/lotes ya existente permite recuperar ese estado al volver a entrar con la quest Ready persistida.

## Validación

ReadyQuestReactReportTests cubre el grafo nativo 10038 Completed ->45391 ->10159 Ready ->45394 sin highlight; rechazo antes de Ready aunque el contador ya sea1; rechazo de quest/actor/kind incorrectos y de actores no personales. La prueba de integración invoca RunCurrentStep con región y sesión capturada y verifica el orden real de paquetes ContextUpdated -> PhaseChanged, sin repetición al evaluar Ready de nuevo ni mutación de FuncGroupId compartido. Se mantienen las pruebas previas del body SC0x151 y de los temporizadores/lotes.

Respaldo E:/AAEmu/rama_10/backups/quest10159-ready-20260912, imagen rollback aaemu-world:rollback-quest10159-ready-20260912. La imagen previa conserva la aceptación y el Use que el usuario confirmó. No restaurar el dump sobre progreso posterior: no se cambian datos persistentes en esta reparación. Manifest y logs quest10159 registran los gates y despliegue efectivos.

Aceptación retail pendiente: volver a entrar con Garden activo y entregar la quest10159 ya Ready interactuando con la luz. No abandonarla ni repetir10038. Confirmar después la disponibilidad normal de10039 ante Tahyang antes de cerrar toda la cadena. No se opera el lifecycle de Zones.

Gates efectivos: restore/build Release y 2796/2796 tests, focal4/4. Imagen sha256:729487099b395992c6f38ea3ed61020e0774febfcf29743b681be3f49357e123. GameService iniciado15:24:46 UTC; Game/Login healthy, puertos1239/1240/1250/1280 y World API disponibles, sin ERROR/FATAL en el log de arranque; compact montado sin cambios. Retail pendiente.
