# Portal interno de Delphinad: destino 1023

Target `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`, HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`. Padre comparado `upstream/client_version/zone-10.0.2_r575` (`1017677b40be6508861a8fb74e9d09fa496873c9`). Se conservan los cambios anteriores. Sin commit/push.

## Evidencia y causa

Portal de la guarida de Anthalon: doodad 15221, fase 44936, función 40651, skill 44246. Su efecto 83770 / SpecialEffect 49378 usa Return (25), value1=1023. El editor_name retail es `delphinad_room_potal`. El catálogo sólo examinaba main_world, omitiendo los return points de Delphinad. Return asumía además que todo destino resuelto pertenecía a la instancia principal; un destino ausente podía devolver al personaje a MainWorldPosition.

Fuente r575 exportada: `artifacts/delphinad-native/game/worlds/instance_phantom_of_delphinad/level_design/zone/384/world_server/return_point.g`: x=737.503, y=1089.59, z=273, zRot=-2.61799 rad. `world.xml` declara origen (1,1): destino mundial (1761.503,2113.59,273), yaw aproximado -150 grados. SQLite y hashes de ambos archivos en `artifacts/portal1023/native.json`. No se inventaron coordenadas ni se modificó game_pak.

El padre no incluye catálogo nativo equivalente; Return AA8 usa MainWorldPosition y no resuelve esta frontera. No se portó comportamiento AA8. Consulta BugReports por quest/entity 10063 sin resultados; no se asigna ese ID como identificación de esta misión.

## Cambio

- PortalManager añade la carpeta de return points de `instance_phantom_of_delphinad` a la lectura nativa; conserva el libro de teletransportes limitado a main_world y el rechazo de destinos ambiguos. También queda disponible la salida nativa declarada en el mismo archivo.
- Return resuelve el template propietario por zoneKey. Si es el mundo principal, mantiene el retorno anterior a la instancia principal; si coincide con el mundo actual, conserva la copia exacta del jugador y envía teleport sin SCLoadInstance. Rechaza otro mundo instanciado o un template ausente.
- Destinos ausentes o sin ZoneLoaded se rechazan antes de cambiar posición. No se usa MainWorldPosition como sustituto de un destino desconocido.

## Validación y entrega

Restore/build Release correctos; 2827/2827 pruebas, cero fallos. Casos nuevos: coordenadas nativas/origen/yaw sin desbloqueo de libro, aislamiento de copias 100 y 101, retorno a mundo principal, rechazo de otra instancia/template desconocido, zona 384 apagada y destino desconocido aun teniendo MainWorldPosition. Tolerancia de coordenadas de un milímetro por redondeo float.

Artefactos: `E:/AAEmu/rama_10/artifacts/portal1023`. Respaldo: `E:/AAEmu/rama_10/backups/portal1023-20260915`; rollback de imagen `aaemu-world:rollback-portal1023-20260915`. Despliegue sólo Game con Compose canónico. No cambiar DB, compact, progreso ni lifecycle de Zones.

Aceptación retail pendiente: usuario inicia/restaura zona 384 si hace falta, entra y utiliza el portal una vez. Debe conservar su instancia, aparecer en la sala de Anthalon y evitar selección de personajes. Startup/hash/API efectivos en manifiesto asociado.

Runtime verificado: punto 1023 cargado en zone 384, xyz=(1761.5029,2113.5898,273), y salida 1021. World API disponible a las 22:14:37 UTC, 0 jugadores/0 Zones. No se operaron Zones. Imagen y hashes DLL en manifiesto.
