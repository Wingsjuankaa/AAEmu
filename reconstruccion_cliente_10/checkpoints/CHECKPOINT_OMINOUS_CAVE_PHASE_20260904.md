# An Ominous Cave 9178: objetivo de fase del portal

Target `rama_10`, HEAD `bdad11fec1493c43a854369e707de72a20f26f86`.
Padre exacto `upstream/client_version/zone-10.0.2_r575`, SHA
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. No se cambia de rama.

## Evidencia y causa

La captura del usuario muestra 9176 entregada y 9178 activa, con el portal
desaparecido después de usar el objeto. El log del 4 de septiembre registra:

- 12:23:24 UTC: item46494 reunido, 1/1.
- 12:23:37: skill39862 iniciada por Dannia1007.
- 12:23:38: doodad13378/obj101229 cambia38577→38621; se envía
  SCDoodadPhaseChanged. Uso de46494 pasa a1/1.
- El acto de fase20 sigue sin objetivo; DB conserva objetivos1,1,0.
  El objeto46494 x1 sigue en Bag, slot92.

Ocho consultas coinciden entre full y compact r575. Quest9178 tiene tres
objetivos: gather4228, use956, phase20. Este último, act62346/component40049,
exige doodad13378, phase1=38621, phase2=0. El portal y la interacción sí
funcionan; falta conectar el estado ya aplicado con el objetivo de misión.
QuestActObjDoodadPhaseCheck se suscribe a OnDoodadPhaseCheck, pero no había
ningún emisor activo. DoDoodadPhaseCheckEvents existía sin callers.

El padre ofrece un camino en CSDoodadQuestNoti que busca un objeto vivo después
de observar el doodad cliente. El fork conserva únicamente la observación
cliente. Ese paquete no transporta fase y sus IDs locales no autorizan una
fase de servidor. Se conserva ese contrato; no se aceptan fases indicadas por
el cliente ni se inventa una transformación de su object id.

AA8 tiene NotifyQuestPhaseChanged desde la transición del doodad al personaje.
Se usa como comparador de la primitiva, no como autoridad de IDs/objetivos.
El contrato AA10 queda fijado por los datos exactos y el cambio observado.

## Corrección

Doodad.DoChangePhase emite OnDoodadPhaseCheck al personaje que causó la
transición, después de ejecutar las funciones y publicar la fase final.
Se utiliza FuncGroupId final, nunca nextPhase solicitado: las funciones pueden
redirigirlo. El matcher existente valida template y cualquiera de las dos
fases configuradas, y SetObjective mantiene la repetición idempotente.
No se completan objetivos para otros personajes por proximidad.

El catálogo contiene14 actos habilitados de este tipo. Quedan conectados al
evento común; su aceptación individual no queda demostrada por este arreglo.

## Gates y entrega

Restore correcto; build Release0 errores/140 advertencias; suite1790/1790.
Tres pruebas ejecutan DoChangePhase y el receptor real del objetivo: transición
38577→38621, repetición, doodad/fase incorrectos, otro personaje, fase alternativa
y desuscripción. Los singletons de las pruebas se restauran al finalizar.

Imagen desplegada: `e462ecb1c61eae3d726b2b31a3532f0fe27273a53962d354abc0fb5e0be5bc43`.
Rollback: `aaemu-world:rollback-pre-ominous-cave-phase-20260904`, imagen
`13c8672b6d4a04d42536ef3f690f84ce3e7f5cdc6c0f18f812490c997923d48e`.
DB respaldada tras detener Game en
`E:/AAEmu/rama_10/backups/ominous-cave-phase-20260904/aaemu_game.sql`, SHA256
`a553b6a86c6a87cd9ce32ab9ee35bd9c31815a6d4eafe6705a7cd7b1bd3b1902`.
Rollback de código: reetiquetar la imagen anterior como la operativa y recrear
sólo Game. No se modifican SQLite, catálogos ni game_pak.

Evidencias, SQL y verificación final:
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/ominous-cave-phase`.
DB/Login se conservan; Codex no opera Zones. Aceptación pendiente: el usuario
relanza Zone351, reconecta y usa una vez el objeto46494 contra el portal.
Comprobar el evento de fase y el avance de9178 antes de darla por aceptada.

Verificacion final: Game healthy/0 reinicios, Login registrado, arranque
12:32:47 UTC en71.403s,45785 doodads main_world. DLL /app y /app/game
SHA256 f961aa639ae93e6e31b733bd2ef59ddf831b1ad380db505127b622b08f26a73e.
API responde,0 jugadores y0 Zones. Relanzar Zone351 corresponde al usuario.
Se conservan los IDs de DB/Login y el hash del overlay Hiram anterior.
