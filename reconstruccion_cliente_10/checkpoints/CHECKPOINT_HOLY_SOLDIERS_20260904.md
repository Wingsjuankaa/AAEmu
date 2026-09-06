# Quest9191: Alcos permanece en la interacción después de cumplir el objetivo

## Autoridad y causa

Target `rama_10`, HEAD `bdad11fec1493c43a854369e707de72a20f26f86`; padre exacto
`upstream/client_version/zone-10.0.2_r575` SHA `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
El padre no incluye el resolver personal. AA8 tiene una ruta parcial que también
omite completar la fase, y rechaza fases con PhaseFuncs; no se portó esa limitación.
Clasificación: `server-required`, proyección personal de estado AA10 confirmado.

El log de las16:18:51 UTC registra skill40100 sobre Alcos13447/obj101267,
fase compartida38981 y personal39004. La función Use acredita el objetivo1080,
pero `TryUseCharacterQuestPhase` sólo ejecuta `func.Use`, sin publicar el destino.
La quest pasa a Ready y las siguientes interacciones siguen enviando40100.
La persistencia de Dannia conserva ambos objetivos en1, status3, sin entregar9191.

Los catálogos full, compact retail y compact runtime coinciden:

- Alcos13447 es `client_doodad`, `once_one_man`, modelo `npctype://18865`.
- ObjInteraction1080: Use19, doodad13447, highlight13447/fase39004, count1.
- Func35810: fase39004, DoodadFuncUse9972, skill40100, destino39007, act_count0.
- En39007 están Report9191 (FuncQuest1169) y Offer9193 (1170).
- ConReportDoodad105 confirma13447 como destinatario de9191.

No se sustituye el doodad por un NPC inventado. Su fase nativa contiene las
funciones de conversación, animación y cambio de modelo.

## Consumidor nativo

`x2game.dll` x64, SHA256 `405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`,
base0x39000000. Se verificaron2048 bytes de cada entrada contra el DLL actual,
idénticos al programa Ghidra analizado:

- Registro RVA0x3ebd60: SCDoodadPhaseChanged, slot0xa90, opcode0x151.
- Handler RVA0x33d660 -> lookup por ObjId RVA0xf04a0 -> cambio de fase RVA0x6f5950.
- Serializer RVA0xa9e750: bc, phase32, data32, growing32, puzzle32, item32, isGoods8.
- El consumidor aplica modelo/funciones de fase y notifica el cambio local. No se
  modifica DLL, game_pak, protocolo de Zone ni catálogos.
- SCDoodadHit se inspeccionó y descartó para este arreglo: su consumidor busca
  funciones de tipo0x0e; no es necesario añadirlo a la interacción Use.

Evidencia: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/holy-soldiers-9191/`.
Reproducir cierre de catálogos con `scripts/audit_holy_soldiers_9191.py`.

## Implementación

Se restaura el destino únicamente para una quest Ready con destinatario exacto,
objetivo Use cumplido, highlight explícito del mismo doodad, una sola función
Use de origen y un destino que contiene Report de esa misma quest. Se rechazan
alternativas ambiguas y act_count>1. No se extrapola desde una animación o nombre.

Se usa ese destino al resolver la entrega y se envía SCDoodadPhaseChanged sólo
al personaje correspondiente, después de acreditar la interacción y después de
las rutas de visibilidad individual, por región y resync de World. Así se recupera
la quest ya guardada sin abandonarla ni suministrar otra daga. El proxy compartido
y los objetivos permanecen intactos; no se repiten efectos ni recompensas.

La reconstrucción deliberadamente no cubre cadenas sin highlight explícito,
varias interacciones alternativas o contadores que no demuestren la transición.

## Validación y despliegue

- Restore/build Release correctos. Suite1804/1804, cinco pruebas nuevas:
  recuperación sin caché de sesión, repetición, aislamiento, rechazos y body exacto.
- Auditoría full/retail/runtime idéntica; sin cambios en SQLite ni placements.
- Imagen `sha256:56103bb47bb8d4a82cfd850bc0619e4edc1ab440eba0e0aafad9436edff8a102`.
- Game DLL en `/app` y `/app/game`:
  `7304580fec67832b11e8862b408b2b4a1894cbf94ee4077745db2657142cba96`.
- Rollback `aaemu-world:rollback-pre-holy-soldiers-20260904` = imagen anterior
  `d016f25793a5c76ccf4c5d67478d7549cd582981cb0b594b250a02fd9bd0f697`.
- Backup DB `E:/AAEmu/rama_10/backups/holy-soldiers-20260904/aaemu_game.sql`,
  SHA256 `7f95385e8f4906adddbbe3214270141384471b2e03873268081c78de4b7fe81d`.
  Compact respaldado en el mismo directorio, SHA256
  `85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
- Sólo se recreó Game; DB/Login y puertos/mounts conservados. No se operaron Zones.
- Posición persistida: Dannia world0/zone351, (20234.8,29762.2,376.127), perfil
  `o_hirama_the_west_2`. El usuario administra su arranque en Control Center.
- Aceptación retail9191 pendiente: volver a entrar y hablar con Alcos. No abandonar
  la misión. Las pruebas de servidor y wire no equivalen a verificar el diálogo en retail.

## Aceptación anterior

La captura y logs16:18:34 confirman que Dannia terminó9190, recibió/entregó
Nubira's Dagger y aceptó9191. La corrección de símbolos anterior queda aceptada
para esta secuencia retail; no implica cerrar sus limitaciones generales de buffs.
