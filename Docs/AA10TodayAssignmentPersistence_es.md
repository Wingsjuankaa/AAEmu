# Persistencia de desbloqueos: ArchePass y Daily Contracts

Fecha: 2026-09-03. Target `rama_10`; padre
`upstream/client_version/zone-10.0.2_r575` (3cc280b). Clasificación:
`server-required`, reparación de instalación/persistencia, no mecánica nueva.

## Causa comprobada

Los dos paneles usan `TodayAssignmentManager` y el catálogo AA10 `today_quest_*`.
En el arranque probado, MySQL no tenía ninguna de estas tablas:

- `character_today_assignments`: grupo/quest/status y día UTC.
- `character_today_step_unlocks`: desbloqueo pagado por personaje/ranura.
- `character_today_reset_counts`: contador del día.

Los logs de Dannia a 19:41:29 UTC reportaron las tres ausencias y después
eliminaron como huérfanas las quests 10245, 10177 y 10239. El gestor atrapaba los
errores SQL, aceptaba pagos y conservaba estado sólo en diccionarios. El relog
no demostraba persistencia: `OnCharacterLogout` de este gestor no tenía caller
y la caché seguía viva hasta reiniciar Game. No fue un reset de medianoche.

El código coincide con el padre exacto en esta frontera; AA8 no tiene este
gestor. No se modifica el wire ni se traslada semántica desde AA8. Los callbacks
Lua r575 de ArchePass consumen X2Achievement/TodayAssignment, igual que el panel
Daily Contracts. Se conserva el reset UTC y la selección de grupos existentes.

## Corrección

Aplicada la migración ya versionada
`SQL/updates/2026-08-09_aaemu_game_character_today_assignments.sql`, que crea las
tres tablas InnoDB. Ejecutada dos veces para verificar idempotencia. No se
eliminan ni reemplazan tablas existentes.

Antes de acceder a la caché o mutar el gestor comprueba que las tres tablas y
sus columnas se puedan consultar. Si falla, aborta entrada, query, unlock,
accept, bulk, reroll o notificación de completion antes de cobrar o limpiar
quests. Una carga SQL fallida ya no se marca como día cargado ni continúa la
limpieza de huérfanas. Esta protección cierra la ausencia observada de esquema;
no equivale a una transacción distribuida de inventario y todas las escrituras
del gestor frente a una caída de DB a mitad de operación.

## Recuperación acotada autorizada

El usuario confirmó **sólo las tres ranuras de ArchePass**, cinco gildas por
ranura. Se restauraron para Dannia (`owner=1007`) únicamente las titularidades
`real_step=50,51,52`, sin cobrar/reembolsar moneda ni conceder rewards/progreso.
Daily Contracts no recibió desbloqueos gratis.

Evidencia SQLite completa r575: step IDs 37/38/36 → real_step 50/51/52; coste
`item_id=23633`, `item_num=5`. Al entrar, el gestor normal las reconstruye en
Ready con grupos elegibles; el usuario debe aceptar la misión, no comprarla.
El progreso perdido no se reconstruyó porque no existía un registro persistido.

Backup previo completo de `aaemu_game`:
`E:/AAEmu/rama_10/runtime/backups/today-persistence-20260903/aaemu_game.sql`,
SHA256 `B24A65305CAE65D346B18010DD565B7F5CC1D062AC5C7F5469A33E445418AD77`.
La recuperación idempotente está en el mismo directorio:
`restore-confirmed-archepass-unlocks.sql`. No restaurar el dump completo para
revertir este corte: descartaría progreso posterior. Conservar las tablas y
sus titularidades aun si se revierte la imagen.

## Pruebas y gate

Restore y build Release sin errores; suite 1748/1748, sin omitidos. Nuevos
tests bloquean las siete rutas públicas relevantes cuando falta almacenamiento,
incluyendo caché caliente y ausencia de personaje. Se verificó en MySQL la
existencia de las tres tablas y la lectura de las tres titularidades desde una
conexión nueva. No se considera cerrada la aceptación visual por esos tests.

Siguiente interacción: después del despliegue, entrar y verificar las tres
ranuras de ArchePass en Ready, sin otro cobro. Aceptar una sola misión, detenerse
y cruzar su fila persistida antes de otro reinicio. El gate de restart/quest
activa y el rollover de día son pruebas separadas pendientes.

## Despliegue

Game desplegado: `sha256:2ff5beeba1b76f8f8c7a0e85e6d1570ecfc3e3a6ebfcac3f181fa3054ffd17a6`.
Rollback de imagen: `aaemu-world:rollback-pre-today-persistence-20260903-155043`.
SHA256 idéntico de ambos ensamblados Game efectivos:
`c50c809d741f0d4826464b252bc4bb111d8f3fa45601c6bea9f43364c81edadc`.
Arranque 19:53:37 UTC: Game/Stream abiertos, registro en Login, healthy;
97 pases/3028 tiers. Login/DB conservaron sus contenedores y Zone no fue operada.

Después de recrear Game, una conexión nueva a MySQL confirmó owner1007 con
real_step50/51/52. ArchePass 19 conserva 77000 puntos y claim normal14, sin
resetear el progreso de pase ni sus rewards. El estado Ready se reconstruirá
en el siguiente ingreso; queda pendiente confirmarlo visualmente con el usuario.
