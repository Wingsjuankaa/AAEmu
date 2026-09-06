# Purifying Energy: retención de objetos al completar misiones

Target `rama_10`, HEAD `bdad11fec1493c43a854369e707de72a20f26f86`.
Padre exacto `upstream/client_version/zone-10.0.2_r575`, SHA
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`; conserva el mismo problema.

## Causa comprobada

El usuario confirma que los doodads restaurados aparecen y que pudo avanzar
desde la estatua. Esto acepta esa interacción, no las 439 misiones del barrido.
En Purifying Energy 9176 falta el objeto 46452. Los logs del 4 de septiembre
muestran que Dannia sí recibió la energía a las 11:33:46 UTC: la misión 9212
registró 46452, 1/1. A las 11:33:51, completar 9212 emitió
`QuestRemoveSupplies`. A las 11:33:52, 9176 registró 46452, 0/1.

Full y compact r575 coinciden: QuestActObjItemGather 4244 de 9212 tiene
`cleanup=false`, `destroy_when_drop=true`. La energía debe conservarse al
completar, pero eliminarse al abandonar. El paso Reward llamaba a DropQuest,
que ejecutaba tanto QuestCleanup como QuestDropped, destruyendo el objeto.
9176 no define una entrega nueva: utiliza la energía conservada desde 9212.
Sus actos 4245/4246 sí piden cleanup al terminar (46537 x8 y 46452 x1).

La estatua 13319 ejecuta skill39660, GainLootPackItemEffect3892, pack12628,
loot94168, item46452 x1. Sus requisitos nativos permiten recuperar la energía
con 9176 activa. No se alteran recompensas, requisitos, SQLite ni game_pak.

## Corrección y alcance

CharacterQuests.RemoveCompletedQuest retira una misión completada ejecutando
su cleanup y finalizadores, sin invocar abandono. DropQuest conserva el camino
de abandono. Quest.FinalizeRemoval desactiva primero el contexto: los eventos
de inventario no pueden reentrar en la retirada y una evaluación ya encolada
no puede volver a ejecutar recompensas. La retirada es idempotente.

El auditor reproducible `scripts/audit_quest_item_retention.py` encuentra 91
contratos idénticos en full y compact con cleanup falso y destroy_when_drop
verdadero. Seis pertenecen al barrido Hiram/posterior: 9181, 9212, 9957,
10048, 10391 y 11033. Esto prueba el alcance de los datos, no la aceptación
interactiva de cada misión. La corrección es del ciclo de vida común.

## Validación y despliegue

Restore correcto; build Release con 0 errores y 174 advertencias;
suite **1787/1787**. Tres regresiones cubren retención nativa de 9212,
callbacks de abandono y retirada/evaluación repetida. Imagen candidata y
operativa `13c8672b6d4a04d42536ef3f690f84ce3e7f5cdc6c0f18f812490c997923d48e`.
Game DLL en /app y /app/game:
`94beef0b0d4b7a4090b1030865ba377c24ff39adde70fa5483d74f7ec08c29b0`.
Los placements anteriores mantienen SHA256
`e0e510e2bca245368673d7493263cfbc8d444839f47bc96eddc9a378fecd3755`.

Respaldo DB tras detener Game:
`E:/AAEmu/rama_10/backups/quest-item-retention-20260904/aaemu_game.sql`, SHA256
`09cc45ca117f5dd05fcfa04def3ab756b366e75ffe89c4dd2baf30ed4bfe0080`.
Rollback: `aaemu-world:rollback-pre-quest-item-retention-20260904` conserva
la imagen `1f1ed96af79261dc9e9595e6f75b5d990ca67ecbe8fec78bea2b098eac302aab`.
Reetiquetarla como `aaemu-world:10.0.2.13-r575-local` y recrear sólo Game
revierte este cambio de código; no hay cambios nuevos de catálogo que retirar.
No restaurar DB salvo necesidad comprobada, pues perdería progreso posterior.
DB/Login se conservan. Zones permanecen bajo control del usuario.

Evidencias y comprobación final de arranque en
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/quest-completion-item-retention/manifest.json`.
Dannia estaba offline antes del despliegue; no se inyectó ningún objeto.
Aceptación pendiente: reconectar con Zone351 y activar una vez la estatua;
comprobar que aparece Purifying Energy en inventario antes de seguir.

Verificacion final: Game healthy, 0 reinicios; arranque 11:48:37 UTC en
69.923 segundos, Login registrado, 45785 doodads main_world. API responde,
0 jugadores y 0 Zones conectadas. El usuario debe relanzar Zone351 desde
Control Center para la prueba. DB/Login conservaron sus IDs de contenedor.

## Reintento observado 12:08 UTC

El usuario informa que sigue sin energia. El log demuestra abandono9176 a
12:08:21 y nueva aceptacion con NPC a12:08:24; no contiene uso39660 ni
activacion de estatua en este intento. Nueve consultas de recovery-native-contracts.json
coinciden full/compact; loot94168 presenta ceros en compact (0 cantidades y
probabilidad) pero full conserva46452 x1 y10000000. 9176 carece de SupplyItem, QuestReact251 activa39119
para9176/status1, y skill39660 permite ProgressQuestContext9176 dentro
de su OR con9212/9956. Esto establece datos nativos de recuperacion, pero
no demuestra que la interaccion haya sucedido. La aceptacion sigue pendiente.
No se justifica otro parche ni reinicio con esta captura; solicitar una unica
activacion real de la estatua y correlacionar solicitud, efecto e inventario.

La SQLite montada en Game conserva loot94168 exactamente como full:
item46452, min/max1, drop_rate10000000. No utiliza las cantidades cero
del compact cliente para esta entrega. No hay un fallo nuevo de loot probado.

## Aceptacion del usuario - 2026-09-04

El usuario confirma: "efectivamente tenia que recojerla nuevamente ahora si funciona".
Recuperacion de Purifying Energy46452 desde la estatua con9176 activa aceptada.
No se requiere otro parche ni despliegue. Esta confirmacion no acredita aun
la entrega final de9176 ni las otras misiones del barrido.
