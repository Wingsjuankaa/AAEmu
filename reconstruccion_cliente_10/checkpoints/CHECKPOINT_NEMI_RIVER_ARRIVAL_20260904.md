# To the Nemi River 9180: conservar las llegadas

Target `rama_10`, HEAD `bdad11fec1493c43a854369e707de72a20f26f86`.
Padre exacto `upstream/client_version/zone-10.0.2_r575`, SHA
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. El padre conserva el mismo
SetObjective(0) al salir de QuestActObjSphere. No se cambia de rama.

## Evidencia y alcance

El usuario avanzó desde9178 hasta9180 y confirma que los exploradores aparecen.
Al llegar, el primer objetivo se completa; al salir vuelve a pendiente.
El log de12:53:52 UTC muestra ENTER2826 y act753; a12:53:56 LEAVE2826
invoca OnExitSphere y reinicia el contador. Se repite varias veces. La DB
termina con ambos objetivos a0. Dannia1007 se encuentra en Zone350.

Seis consultas exactas coinciden entre full y compact r575:

- Act62191/detail753, componente39877: llegar a esfera2826, explorador.
- Act62368/detail758, componente40073: llegar a esfera2814, capitán.
- Ambos son QuestActObjSphere en componentes Progress distintos.
- SphereQuest1632/1627 enlazan ambas áreas con9180; no hay requisitos de
  presencia adicionales en esos dos componentes.

Se conserva SQL y filas completas en native-contracts.json. Los datos exigen
acumular ambas visitas; el código anterior las convertía en presencia reversible.
AA8 sirve como comparador de la primitiva: OnEnterSphere acumula ObjSphere y
no tiene un reset de objetivo al salir. No se trasladan IDs ni reglas de AA8.
QuestActCheckSphere es el tipo separado que comprueba presencia; no se modifica.

## Corrección

QuestActObjSphere deja de escuchar salidas y de poner su contador a cero.
La llegada sigue pasando por el mismo evento y filtro de componente, y por
SetObjective(1), que limita e ignora repeticiones. El objetivo queda en el
array persistente existente, sin cambiar su formato ni otorgar progreso por DB.
El registro de triggers y su retirada al finalizar se conservan.

## Gates y despliegue

Restore correcto, build Release0 errores/111 advertencias;1793/1793 pruebas.
Tres regresiones cubren visitar explorador, salir, visitar capitán y salir;
componente ajeno y reentrada idempotente; CheckSphere reversible sin cambios.
No se declara completada toda la misión ni el resto del catálogo por estos tests.

Imagen desplegada:
`9d584e1e0ff35d404e891200360c59b744183fc010fd1cbc944491a690ec5a2b`.
Rollback `aaemu-world:rollback-pre-nemi-river-arrival-20260904` conserva
`e462ecb1c61eae3d726b2b31a3532f0fe27273a53962d354abc0fb5e0be5bc43`.
Para revertir código, reetiquetar esa imagen como la operativa y recrear sólo Game.
No hay cambios nuevos de catálogos, SQLite o game_pak que revertir.
Respaldo DB tras detener Game:
`E:/AAEmu/rama_10/backups/nemi-river-arrival-20260904/aaemu_game.sql`, SHA256
`da2b5052850774c25e169828cd845e1d6ea46ea914ce8c83b8c499b94d0a9437`.
DB/Login se conservan; Zones siguen bajo control del usuario.

Evidencias y gate runtime en
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/nemi-river-arrival`.
Aceptación pendiente: relanzar Zone350, entrar una vez al primer punto y salir;
debe conservarse completado y permitir seguir al marcador del capitán.
El progreso previamente borrado no se reconstruye mediante escritura directa.

Verificacion final: Game healthy/0 reinicios, Login registrado, arranque
13:02:25 UTC en68.595s,45785 doodads main_world. DLL /app y /app/game
SHA256 d681d07f15a568ce48107d1aafe297c2bdac3d124f3fcaee0ed4421a67179a37.
API responde,0 jugadores y0 Zones. Relanzar Zone350 corresponde al usuario.
DB/Login conservaron sus IDs y el overlay Hiram conserva su hash anterior.
