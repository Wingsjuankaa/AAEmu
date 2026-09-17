# Mapa GM de bancos de pesca — AA10 r575

## Uso

- `/fishspots` o `/fishspots on`: activa los marcadores y responde con el número de bancos presentes. Abrir el mapa con **M**.
- `/fishspots off`: desactiva la vista GM y restaura el radar ordinario, si hay un buff de radar activo.
- Requiere nivel efectivo **100**, obtenido del personaje o de su cuenta. El panel alpha por sí solo no concede este permiso.

La vista comprende los bancos vivos y visibles del mundo **y la instancia actuales**. Incluye bancos de agua dulce y salada, también antes de cebarlos. No enumera lugares potenciales sin un banco presente ni carga zonas adicionales. Se actualiza cada segundo. La selección no aplica el límite de 1.000 metros del comando antiguo `/fishfinder set true`.

El estado es temporal por sesión. Al desconectarse se elimina la inscripción mediante `GameConnection` → `RadarManager.UnRegister`; tras entrar de nuevo hay que ejecutar el comando. La revocación del nivel GM se comprueba durante la actualización y retira la vista ampliada.

## Implementación y evidencia

- `FishSchoolManager.GetAllFishSchools()` usa `FishSchoolLookup.IsPresent`: grupo SportFishing (65), visible, no borrado y registrado en el mundo propietario. Templates principales: 6447 y 6448.
- `RadarManager.SelectFishSchools` conserva el filtro de mundo/instancia. Solo el modo GM explícito omite el filtro de distancia. Los buffs ordinarios conservan `RadarRangeRules`.
- `TelescopeRegistrationEntry` mantiene por separado el alcance del buff y la vista GM. Quitar/reaplicar el buff mientras la vista está activa no la cancela; al salir se restaura el alcance más reciente.
- Se reutilizan los paquetes existentes r575: `SCSchoolOfFishFinderToggledPacket` (0x228, nivel 1, bool + float) y `SCSchoolOfFishDoodadsPacket` (0x229, nivel 1, bool final + byte cantidad + entradas de `Doodad.WriteFishFinderUnit`). No se modifica el protocolo.
- Cada lote contiene como máximo diez bancos. El último lote lleva el indicador final. Un conjunto vacío produce un lote final vacío para actualizar la colección cuando ya no quedan bancos.
- La vista GM anuncia un radio finito de 1.000.000 unidades para la visualización nativa. Es un valor específico del comando, no una distancia retail inferida. La selección del servidor sigue limitada al mundo y la instancia.
- El corpus Lua AA10 ya contiene `UPDATE_FISH_SCHOOL_INFO`, `CLEAR_FISH_SCHOOL_INFO`, `UPDATE_FISH_SCHOOL_AREA` y `REMOVE_FISH_SCHOOL_INFO`, conectados al mapa grande y al minimapa. Fuente extraída: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/private-alpha-panel/all-native-lua/scripts/x2ui/map/world_map.lua`, líneas 531, 575, 666 y 686; también `road_map.lua`.
- Padre comprobado: `upstream/client_version/zone-10.0.2_r575`, hash `b439e1cc0d4bb96647d11dcb76da61b0246a53e1`. El radar anterior ya estaba presente; este comando es una ampliación administrativa local.

No se modifica el cliente, game_pak, SQLite ni los spawns. No se opera el lifecycle de ZoneHost.

## Validación

Restore y build Release correctos. Suite completa: **4.617 correctas, 0 fallos, 0 omitidas**. `FishSpotsTests` aporta siete casos: conservación del buff y sus paquetes de activación, separación por mundo/instancia con bancos a 40 km, radar desactivado y lotes de 0/1/10/11/21 entradas. Los tests existentes de presencia/desaparición y alcance ordinario permanecen verdes.

Los tests de serialización verifican el cuerpo y la emisión de paquetes del servidor. La aceptación visual en el cliente queda pendiente: ejecutar `/fishspots`, abrir M, comprobar bancos distantes, repetir y ejecutar `/fishspots off`. Comprobar además desaparición de un banco agotado y restauración del alcance con radar de barco activo. No presentar las pruebas unitarias como una captura retail.

Logs, respaldos y manifiesto: `E:/AAEmu/rama_10/artifacts/fishspots/20260916`. Imagen anterior conservada como `aaemu-world:before-fishspots-20260916`. La configuración de permisos se sincroniza al bind mount `.server_files/AAEmu.Game/Configurations/AccessLevels.json`.

## Rollback

Restaurar únicamente la entrada `fishspots` de AccessLevels desde el respaldo, preservando cambios posteriores. Retaggear `aaemu-world:before-fishspots-20260916` como `aaemu-world:10.0.2.13-r575-local` y recrear solo el servicio `game` con los mismos archivos Compose. Verificar previamente que el rollback no revierta despliegues posteriores. No reiniciar DB, Login ni ZoneHost para este cambio.
