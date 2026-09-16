# Quest10045 Restaurar Celestia: efectos de buff y antorchas personales

Target rama_10, HEAD45bba0ad49fee55ab30a80168b4d6caefbb9ac87; padre upstream/client_version/zone-10.0.2_r575. Conserva todos los cambios anteriores. Clasificación server-required. No hay cambios de game_pak, compact, datos persistidos ni requisitos.

## Contrato y evidencia

Log artifacts/quest10045-live.log: acepta10045 a15:46:37 UTC, recibe49007. Usa43968 sobre cinco objetos14968 distintos (101574,101576,101575,101577,101578), entre15:46:45 y15:47:27. Cada Use se autoriza en fase personal44273 frente a shared44272. Func40153/Use11416 declara nextPhase44293, modelo garden.brazier_on;44272/44273 usan garden.brazier_off. El actor tiene client_doodad y once_one_man. Use11416 no agenda otra skill.

Skill43968 aplica83339/Interaction8252 y83354/Buff32962 ->26312. La pila26312 sube1..5; el último log registra la sustitución por26313 y Started trigger13393, que aplica83348/Buff32959 ->26317. Buff26313 dura5000ms y26317 dura3000ms. QuestActObjEffectFire180/act69442/componente43662 exige effects.id83348 una vez. No recibe el evento porque sólo Skill.ApplyEffects lo publicaba; BuffTrigger.ApplyResolved ejecutaba el efecto sin publicación. BuffTriggerTemplate perdía además el ID externo, conservando únicamente el detalle32959. El padre upstream local tampoco publica EffectFire en esa ruta.

Segunda omisión: TryUseCharacterQuestPhase invocaba Use sin completar el cambio visual NextPhase. No es un fallo del modelo ni del placement.

## Reparación

- Loader conserva buff_triggers.effect_id en BuffTriggerTemplate.EffectId, distinto de Effect.Id.
- BuffTrigger publica EffectFire una vez DESPUÉS de Apply, atribuido al personaje del agente source resuelto, siguiendo el canal de objetivos/equipo de Skill. Guardas de tags/agentes impiden publicar si la aplicación no se ejecuta. ID0 no produce evento. El objetivo mantiene su propia regla TeamShare.
- Una interacción personal de tipo Use, terminada y sin otra skill pendiente, envía SC0x151 con el NextPhase nativo sólo al personaje. Se reinicia ToNextPhase antes de aplicar para evitar reutilizar éxito de una interacción anterior. No avanza si hay cancelación/rechazo, multiuso, actor no personal/no cliente o próxima fase no positiva. No muta FuncGroupId compartido ni ejecuta sus phasefuncs para todos los jugadores. No incorpora una nueva persistencia de fases personales; el cliente mantiene su ciclo nativo.

## Pruebas y retest

ColdFlameQuestTests: el trigger real alimenta el objetivo real de10045 usando83348, comprobando aplicación antes de notificación y una sola notificación. Rechazo por tag y ausencia de ID externo no notifican. La fase de encendido44293 sólo se devuelve para Use terminado; se rechazan los estados no autorizados. Las pruebas previas validan el body personal SC0x151.

Gates/build/despliegue se registran en QUEST10045_COLD_FLAMES_20260912.manifest.json y artifacts/quest10045-*.log. Respaldo separado E:/AAEmu/rama_10/backups/quest10045-20260912, rollback aaemu-world:rollback-quest10045-20260912. No se administran Zones. No restaurar el dump sobre progreso posterior.

El evento del primer intento expiró sin incrementar el objetivo; no se concede la misión por consola ni se modifica la DB. Retest: con Garden activo, usar las cinco antorchas; deben mostrar encendido tras cada casteo y el quinto efecto debe habilitar la entrega normal. La aceptación retail de esta reparación está pendiente. El usuario confirmó la entrega de10159 al continuar hasta10045; la misión10042 funcionó usando cinco flechas sobre npc19908/grupo970.

Gates efectivos: restore/build Release, 2799/2799 tests, focal3/3. Imagen sha256:3a9538a98a117c91650d6d2434884789939307eafd18aa29da945518f1ce1b7b. GameService iniciado16:00:33 UTC, Game/Login healthy, puertos1239/1240/1250/1280 y World API disponibles, sin ERROR/FATAL en arranque; compact montado sin cambios. No hay reporte de menú para entity10045 al consultar. Retail pendiente.
