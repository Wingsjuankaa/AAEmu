# En busca de pistas 10060: crédito de fase personal

Target `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`. Se conservan las correcciones anteriores, incluida la caché de áreas por mundo. Padre comparado `upstream/client_version/zone-10.0.2_r575`; no contiene la ruta personal ni una solución equivalente. Sin commit/push.

## Evidencia

El usuario avanza desde10052 hasta10060 y usa los documentos sin crédito. Log `artifacts/quest10060-before.log`,17:40:24 UTC: doodad15163/obj148205, fase compartida44798, fase personal44803; Use44192, siguiente45362, configuredSkill0. Se envía cambio de fase personal, pero no existe evento OnDoodadPhaseCheck para esa interacción.

SQLite retail y compact runtime coinciden en las cinco plantillas (ClientDoodad y OnceOneMan), funciones Use y objetivos. Evidencia serializada en `artifacts/quest10060/native.json`:

| Objetivo | Doodad | Fase requerida |
|---|---|---|
|35|15163|45362|
|36|15162|45364|
|37|15160|45366|
|39|15164|45368|
|40|15169|44814|

Quest10060 contiene cinco QuestActObjDoodadPhaseCheck y autocompletado. Para el documento15163: función40964, fase44803, Use11699, skill44192, Count0, next45362. La ruta compartida DoChangePhase ya notificaba al objetivo; TryUseCharacterQuestPhase sólo cambiaba la representación del objeto para el usuario. Consulta BugReports por10060 sin reportes relacionados.

## Corrección y validación

`CompletePersonalUsePhase` reutiliza el resultado validado de `GetCompletedPersonalUsePhase`. Tras una interacción personal terminada, envía la fase al cliente y notifica OnDoodadPhaseCheck exclusivamente al personaje que interactuó, con template y fase del servidor. Conserva la fase compartida. Usos fallidos, cancelados, diferidos o con cuotas pendientes no notifican.

Restore/build Release correctos; **2821/2821 tests aprobados**. Cinco casos prueban las parejas nativas, crédito sólo al actor correcto, objetivo satisfecho, repetición sin doble evaluación y fase compartida intacta. Un caso adicional rechaza usos incompletos, cancelados, diferidos, cuotas pendientes, fase equivocada y otro doodad. No cambia los cinco objetivos ni completa artificialmente la misión.

## Entrega

Game se recompila y despliega, con imagen/hash efectivos en el manifiesto. Respaldo `E:/AAEmu/rama_10/backups/quest10060-20260913`; rollback `aaemu-world:rollback-quest10060-20260913`. Sin cambios DB, compact o game_pak. No restaurar un dump antiguo sobre progreso nuevo.

Aceptación retail pendiente: usuario restaura Zones si el reinicio las desconecta, entra con Dannia y repite la investigación de documentos. Debe acreditar esa pista y permitir seguir las restantes. No necesita abandonar la misión. Lifecycle ZoneHost bajo control del usuario.

Verificación tras despliegue: World API disponible el 2026-09-13 a las 17:49:42 UTC, 0 jugadores y 0 Zones. Evidencia world-after.json en artifacts/quest10060. No se iniciaron Zones automáticamente.
