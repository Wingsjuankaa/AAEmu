# Quest 10028: El eco de Nebe

Target `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`. Padre local `upstream/client_version/zone-10.0.2_r575`, `1017677b40be6508861a8fb74e9d09fa496873c9`. No se cambió de rama ni se integraron cambios del padre. Reparación de datos de spawns, sin cambios de C#, compact ni game_pak.

## Evidencia y causa

El usuario encuentra notas musicales suspendidas sobre el vacío en Celestia, sin piezas sobre las que cruzar. El log de Game del 11 de septiembre a las 22:15 UTC registra el uso de la píldora y la interacción con la flor. Quest10028 reconoce item48975 (objetivo de uso 1/1), pero continúa pendiente el cruce.

Item48975 usa skill43883, efecto83123/BuffEffect32798, buff26190 durante120 segundos. La flor14928 ofrece skill43882 y efecto de interacción83125; éste corresponde al componente43549. El objetivo de llegada es QuestActObjSphere830, esfera2948, componente43550. El archivo nativo `game/worlds/main_world/level_design/zone/382/client/quest_sign_sphere.g` contiene esa llegada en coordenadas locales `(1015.62,1980.64,217.858)`, radio3. SphereQuestManager ya carga estos archivos y convierte sus posiciones a coordenadas del mundo.

El anterior inventario de placements por dependencias de quests contenía las notas14984, pero no las piezas físicas del puente. Esa ausencia no significa que falten en el cliente. La exploración completa con PakDoodadScan del game_pak r575 inmutable encuentra21 piezas en `game/worlds/main_world/level_design/cells/030_034/doodad.g` y `031_034/doodad.g`:14934×4,14935×2,14936×3,14937×2,14948×6,14949×4. Los modelos son los prefabs nativos `garden_quest_bridge_of_sound_a/b/c`.

Evidencia negativa: las entidades XML de esas celdas no contienen el puente; el inventario filtrado anterior no contenía estos IDs;14950/14951 no tienen placements en el escaneo completo y no se añadieron. No se inventan coordenadas ni spawns para cerrar el objetivo.

## Reparación reproducible

`AAEmu.Game/Data/Worlds/main_world/doodad_spawns_aa10_nebe_bridge_r575.json` incorpora los21 placements con coordenadas, escalas y rotaciones extraídas. FuncGroupId se obtiene de la única fase inicial de cada template; las definiciones coinciden entre SQLite autoritativa y compact runtime. Las notas existentes y las condiciones de la misión conservan su comportamiento.

El generador `reconstruccion_cliente_10/scripts/rebuild_nebe_bridge.py` fija el SHA256 del CSV, exige los21 registros y las dos entradas nativas, comprueba fases y descarta duplicados entre overlays fuente/runtime. El CSV pequeño se conserva en `reconstruccion_cliente_10/evidence/quest10028-nebe-placements-r575.csv`.

Desde la raíz del repositorio:

```powershell
C:/Python313/python.exe reconstruccion_cliente_10/scripts/rebuild_nebe_bridge.py --placements reconstruccion_cliente_10/evidence/quest10028-nebe-placements-r575.csv --write
C:/Python313/python.exe reconstruccion_cliente_10/scripts/rebuild_nebe_bridge.py --placements reconstruccion_cliente_10/evidence/quest10028-nebe-placements-r575.csv
```

Para reextraer el CSV, compilar `reconstruccion_cliente_10/tools/PakDoodadScan` en Release y ejecutarlo con el game_pak r575 original y la lista `14934,14935,14936,14937,14948,14949`; guardar stdout sin alterar bytes ni saltos de línea. El generador no despliega automáticamente.

## Validación, despliegue y rollback

Restore y build Release correctos (0 errores; advertencias existentes de dependencias); suite2773/2773. Log `E:/AAEmu/rama_10/artifacts/nebe-gates.log`. Construcción de PakDoodadScan correcta y generación idéntica repetida; no se creó una prueba que se limitara a duplicar el JSON.

Se copia únicamente el nuevo overlay al bind mount `.server_files/AAEmu.Game/Data/Worlds/main_world` y se reinicia Game. Se conserva la imagen en uso `sha256:b15bfc90ace23c4ddf82bbb66ca39d66dd7fe9ad873403f866dc25f4e21d4461`. El manifest recoge hashes de DLL, compact, fuentes y overlay. Backup previo de DB, compact, log y estado World en `E:/AAEmu/rama_10/artifacts/nebe-deploy`. No se operan las Zones.

Rollback del cambio: retirar exclusivamente el archivo nuevo `doodad_spawns_aa10_nebe_bridge_r575.json` del bind mount, que antes no existía, y reiniciar Game. No es necesario restaurar DB, compact ni otra imagen para revertir estos spawns. Conservar los respaldos; no revertir cambios de otras tareas.

Verificación posterior: Game healthy, Login healthy, World API responde y los puertos1239/1240/1250/1280 escuchan. El log confirma21 ObjIds distintos con los seis templates y sus cantidades esperadas, sin ERROR/FATAL. Imagen y hashes de ambas DLL permanecen idénticos; SHA256 del overlay coincide entre fuente, bind mount y archivo visible en el contenedor. Evidencia en `nebe-deploy/game-after.log`, `world-after.json` y manifest.

Aceptación retail pendiente: volver a entrar con Garden iniciado desde Control Center y comprobar que el puente permite cruzar mediante la secuencia normal de la misión. El punto de llegada debe registrar el objetivo. No se ha completado la misión ni modificado el progreso de Dannia por comando.
