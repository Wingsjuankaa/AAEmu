# Joining Forces9174: Andega fuera de la cueva

El usuario confirma avance tras Alcos9173 y muestra Joining Forces en Complete,
con objetivo Find Andega outside the cave a1m. Dannia1007 tiene quest9174 Ready3;
Zone351 cargada y saludable. Faltaba el placement del actor cliente13376 tanto
en fuente como en runtime. No era un problema del contador ni del servidor Zone.

Target `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`, HEAD
`bdad11fec1493c43a854369e707de72a20f26f86`. Padre consultado
`upstream/client_version/zone-10.0.2_r575`, SHA
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. El padre carece del overlay de
actores cliente; se reutiliza la primitiva AA10 ya aceptada con Alcos, sin port AA8.

## Evidencia nativa

Full y compact coinciden en el contrato auditado por
`reconstruccion_cliente_10/scripts/audit_hiram_andega.py`.
Evidencia y logs en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\hiram-andega-frontier`.

- Ready39854/act62193 -> QuestActConReportDoodad88 -> doodad13376.
- Doodad13376 es client_doodad, once_one_man, modelo npctype18667.
- Start38575 ejecuta ModelChange10 y contiene Quest1111(report9174) y
  Quest1112(offer9175). No sustituir por un NPC genérico.
- QuestReact90 contempla9175 Ready y bubble139; QuestReact108 contempla9175
  Completed y transiciona a38939 para report9195/offer9235. Se conserva este flujo.
- game_pak r575, `game/worlds/main_world/level_design/cells/019_029/doodad.g`:
  X20194.492 Y30005.484 Z458.459 yaw78.999971, escala1, roll/pitch0.
- La posición de Dannia en la incidencia era20193.1,30005.8,458.475, coincidente
  con el marcador. Se añade únicamente13376 al overlay (31->32 actores).

Comando de extracción read-only utilizado:
`dotnet run --no-build --project reconstruccion_cliente_10/tools/PakDoodadScan --configuration Release -- E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game_pak 13376,13380,13381,13382`.
La auditoría adyacente encuentra dos placements13380 y uno13382 en018_029;
13381 no está en los cells main_world (exit9 del scanner por ese ID).
Estos pertenecen a pasos posteriores y no se agregan sin cerrar sus condiciones.
9175 entrega a NPCGroup905;9176 entrega a doodad13382: registrar esa frontera
si el usuario alcanza ese tramo, sin declarar aceptada toda la cadena.

## Validación y despliegue

Auditoría nativa pass: contrato full/compact, posición, orientación, fase y
unicidad13376. Regresión existente NuiaRacialQuestProxyCatalogTests ampliada
con la fase y coordenadas originales. Sin cambios de protocolo ni progreso DB.
Estado final, hashes, respaldo, suite y startup en `manifest.json` de la frontera.
La aceptación visual de Andega queda pendiente del cliente del usuario.

Desplegado: restore/build Release correctos (111 advertencias,0 errores),
1780/1780 pruebas. Game guardo Dannia y salio exit0 antes del backup.
Imagen `11d310722649a29ef7218bdc700f9f7724d7efdd501d59449aa63be8d6fcd203`,
overlay `49940b9ab1c9c594472484a15212c608d33e18804dc2a9a0973c2aac92fc43bc`
identico en fuente, mount y contenedor. Backup DB/overlay en
`E:\AAEmu\rama_10\backups\hiram-andega-20260903`; rollback conservado.
Startup01:47:55UTC,71.85s,44810 doodads main_world (+1), registro Login correcto,
health healthy,0 reinicios; DB/Login sin recrear. Codex no opero Zones.
Proxima interaccion retail: relanzar Zone351 desde Control Center si hace falta,
reconectar a Dannia y hablar con Andega fuera de la cueva para entregar9174.
