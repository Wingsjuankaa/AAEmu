# Delphinad Mirage: contenido de la instancia

Target `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`, HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`.
Padre comparado: `upstream/client_version/zone-10.0.2_r575` (`1017677b40be6508861a8fb74e9d09fa496873c9`).
Conservar las correcciones anteriores sin commit/push. No modificar cliente, compact ni progreso de Dannia.

## Síntoma y causa probada

Después de corregir la entrada, Dannia llegó a WorldInstance 100 / zoneKey 384.
`Una ciudad misteriosa` (10050) quedó Ready, buscando Hayden, en una instancia vacía.
Log `artifacts/delphinad-empty.log`: 16:52:35 UTC, `MirrorZoneNpcSpawn` descarta NPC
de zoneId=384/instanceId=0 porque todavía no existe un mundo que los contenga.
A las 16:54:29 se crea la copia 100 y `SpawnManager` carga **0 doodads**.
El host manual 384 mantiene sus registros, pero sólo existía un remirror global al
inicio del mundo principal. No había replay al crear una mazmorra posteriormente.

La diferencia iid=0 frente a world=100 no prueba por sí sola un error: el resolver
existente admite un host manual para la única copia del mismo template. Se conserva
ese contrato; no se altera el handshake ni el identificador nativo del host.

## Restauración

- `Scripts/RestoreAa10DelphinadContent.py`: lee el pak en modo rb o exports nativos,
  valida hashes de ambas celdas, parseo completo, 68 ubicaciones únicas y plantilla
  y fase inicial en SQLite. Produce el catálogo de servidor, con rechazo de
  sobrescrituras diferentes y modo de diagnóstico predeterminado.
- `AAEmu.Game/Data/Worlds/instance_phantom_of_delphinad/doodad_spawns_aa10_retail.json`:
  68 ubicaciones del release r575, 52 plantillas; espejo idéntico en el bind runtime.
  Las fases iniciales siguen las plantillas originales, sin adelantar quests.
- Hayden: doodad15086, modelo inicial npctype20050, fase44622,
  mundo X1572.845/Y2068.8956/Z282.8. Quest10050 reporta a este doodad.
- `DungeonLoaderTask` llama el replay tras preparar contenido y esperar ZoneLoaded,
  antes de declarar lista la instancia y mover jugadores.
- `NpcSpawnRelay.RemirrorDungeon` filtra host cargado, zoneKey y mundo propietario;
  rechaza un host manual ambiguo con varias copias. Reutiliza bcIds y marcadores
  WZNpcState existentes, sin recrear AI de NPC que ya recibieron estado.

Fuentes positivas:
- `game/worlds/instance_phantom_of_delphinad/level_design/cells/001_001/doodad.g`,
  SHA256 `b5a97696a14d7140cc1e28be190ef26e81944c2898ecf8683e2500b6b6623829` (13 ubicaciones).
- Celda `001_002/doodad.g`, SHA256 `003d1c07f72a92bc294b532ad60f1326cf26678b8f064a98bbd52c27b0ef9a56` (55 ubicaciones).
- XML editor `cells/001_002/editor/02_00/doodad.xml`: Hayden local
  36.845398/20.89563/282.79999, corroborando celda1024/subcelda256.
- SQLite completa `87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f`;
  todas las plantillas y fases iniciales también existen en compact montada.

La conversión de celdas/cuaterniones reutiliza el parser versionado de Halcyona;
no se necesita importar contratos AA8. El padre no contiene replay en este punto.
Consulta `BugReports.py --category quest --entity 10050`: sin reportes relacionados.

## Verificación

Restore, build Release sin errores y **2812/2812 tests** correctos. Cuatro regresiones
prueban host manual recibido antes del mundo, copia exacta sin afectar hermanas,
rechazo de host ambiguo y espera de ZoneLoaded. Se preserva el registro pendiente
y el iid nativo. No simulan una aceptación completa del cliente.

Builder probado contra pak original en sólo lectura: mismo resultado que exports.
Pruebas negativas: hash alterado rechazado, archivo diferente no sobrescrito.
Fuente y bind idénticos: SHA256 `1e065fa4a924717d639d17231391616355ea146c5240c5f077fe1cbd7b52b44c`.

Reproducir desde el repo:
```powershell
C:/Python313/python.exe Scripts/RestoreAa10DelphinadContent.py --game-pak E:/AAEmu/rama_10/client/ArcheAge-Returns-10.0.2.13-r575/game_pak --database .server_files/AAEmu.Game/Data/compact.sqlite3 --output AAEmu.Game/Data/Worlds/instance_phantom_of_delphinad/doodad_spawns_aa10_retail.json .server_files/AAEmu.Game/Data/Worlds/instance_phantom_of_delphinad/doodad_spawns_aa10_retail.json --apply
```

## Despliegue y aceptación

Ver manifiesto adjunto para imagen y hashes efectivos. Respaldos en
`E:/AAEmu/rama_10/backups/delphinad-content-20260912`: dump DB, compact e imagen anterior.
Rollback: usar `aaemu-world:rollback-delphinad-content-20260912` y retirar únicamente
el nuevo `doodad_spawns_aa10_retail.json` del bind; conservar world_spawns de la corrección previa.
No se editaron DB/compact, por lo que no corresponde restaurarlos y perder progreso nuevo.
Lifecycle ZoneHost permanece a cargo del usuario.

Aceptación retail pendiente: relanzar 384 si se desconectó al desplegar Game,
entrar con Dannia, comprobar que Hayden se ve en su posición y entrega10050.
Revisar log de replay sin descartes, NPC presentes y estabilidad de entrada.
La restauración de ubicaciones no declara validadas todas las futuras mecánicas de la instancia.

Runtime verificado: imagen `b6f3e02bd1969b88640442fe6e0e4571f5b880380bda170108c67a7e1a50bdbe`, Game/Login healthy, Server started 17:17:30 UTC, puertos1239/1240/1250/1280 escuchando. Cero Zones conectadas tras reinicio; falta aceptación retail. Se registraron cuatro diagnósticos de definiciones Item Smelting29–32, subsistema deprecado excluido; no errores Delphinad ni FATAL. Compact sin cambios.
