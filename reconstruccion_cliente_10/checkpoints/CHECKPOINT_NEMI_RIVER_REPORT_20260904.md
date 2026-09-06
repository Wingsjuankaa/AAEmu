# Entrega de9180 a Andega: transición QuestReact conservada

Target rama_10, HEAD bdad11fec1493c43a854369e707de72a20f26f86;
padre upstream/client_version/zone-10.0.2_r575 en
3cc280b14d7da0d874121d14ebbf409f5e032d1c. Se preservan cambios previos.

## Evidencia

El usuario confirma las dos llegadas y muestra a Andega con marcador de entrega.
La DB conserva9180 Ready/status3, objetivos1,1. Los clics skill11008 llegan al
servidor, pero UseQuest informa doodad13393, fase compartida38607, fase calculada
38607, questKind2, candidates0. No se llega a ejecutar la entrega.

Nueve consultas full/compact coinciden, conservadas con SQL en
forensics/output/aa10-client-forensics/nemi-river-report/native-contracts.json.
El doodad13393 es client_doodad y once_one_man. Su fase inicial38607 es invisible;
QuestReact131 la cambia a38961 al alcanzar9180/Progress/component40073.
QuestReact140 también entra a38961 desde Completed. La fase38961 muestra
npctype18743 y tiene DoodadFuncQuest1151 para reportar9180, además de funciones
de9182/9183. No tiene una transición de vuelta por Ready.

El resolver calculaba todo desde38607 usando sólo el estado actual. Al pasar
a Ready ya no coincidía131, aunque el cliente conservaba la transición y el
componente40073 quedaba acreditado en los objetivos persistentes.
El resolver del padre no ofrece una solución para conservar esta transición.
AA8 no tiene equivalente QuestReact en DoodadObj; no se porta lógica de AA8.

## Corrección acotada

Sólo UseQuest de entrega (questKind2) puede reconstruir una arista Progress
previa. Requiere misión Ready, ID de misión exacto, componente Progress explícito
con objetivos cuyo contador guardado alcanza el máximo y ConReportDoodad nativo
para ese mismo doodad. No se reconstruyen componentes vacíos, desconocidos o
incompletos. Las aristas que coinciden con el estado actual siempre prevalecen.
Se usa la fase nativa resultante para seleccionar la función de entrega; no
se muta la fase compartida ni se trata Ready como Progress de forma global.
Los contadores persistentes permiten resolver también tras reconectar.

No hay una prueba automática de reconexión del cliente: se verifica el resolver
con el mismo estado guardado Ready/objetivos. Aceptación interactiva pendiente.

## Validación y operación

Restore y build Release correctos,0 errores/174 advertencias;1796/1796 pruebas.
Regresiones: Andega listo con componente acreditado; rechazo de progreso vacío,
receptor ajeno, estados incorrectos y componente no demostrado; prioridad de
una arista Ready explícita sobre la reconstrucción histórica.

Imagen desplegada6a5f50cef8396f8bd12c24c0525dee886b6f49a805c68f1015f2dd650a3644ad.
Rollback aaemu-world:rollback-pre-nemi-river-report-20260904 conserva
9d584e1e0ff35d404e891200360c59b744183fc010fd1cbc944491a690ec5a2b.
Para revertir código, retag de la anterior como imagen operativa y recrear sólo
Game. No se cambian SQLite, datos de personaje, catálogos ni game_pak.
Backup DB tras parada:
E:/AAEmu/rama_10/backups/nemi-river-report-20260904/aaemu_game.sql,
SHA256954e8525b2fb13813168113ed57d5be48a727202817cacff70a16c1570ba2f74.
DB/Login conservados; Zones bajo control del usuario.

Manifest y logs en
E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/nemi-river-report.
Prueba siguiente: relanzarZone350, reconectar y entregar9180 a Andega una vez.
No repetir objetivos ni reiniciar la misión. Verificar selección38961/1151,
respuesta de entrega y persistencia antes de declarar aceptación.

Verificacion final: Game healthy/0 reinicios, Login registrado, arranque
13:30:24 UTC en74.275s,45785 doodads main_world. DLL /app y /app/game
SHA25603e7a69c114cd80c58becde28770420c606738b6faa733bab745f44613bdffa4.
API responde,0 jugadores y0 Zones. RelanzarZone350 corresponde al usuario.
