# Garden: rechazo antes del traslado y textos de las puertas

## Incidente y causa

Prueba de Dannia (1007), 2026-09-08 01:12:38 UTC. El servidor registró `Garden transfer ... returnPoint=1005`, después `Zone handoff refused: no ZoneLoaded for newZoneId=379 instanceId=0 bcId=2067`, dos solicitudes de retorno al selector y desconexiones. La posición persistida quedó en zona 379, (499.448,38375.5,131.172). Esto demuestra el rechazo del traslado; no se obtuvo un dump que determine por separado por qué terminó el proceso cliente después del selector.

El perfil de Control Center tenía 354, 378 y 382 habilitadas, pero no 379. Gatekeeper Hall (379) es la sala de entrada; las zonas 378/382 no la sustituyen. No se modificó la posición de Dannia ni se operó el lifecycle de Zones.

La comprobación adicional encontró una limitación del panel: exige npc_spawners.g para iniciar cualquier Zone. La entrada `game/worlds/main_world/level_design/zone/379/zone_server/npc_spawners.g` no existe en el paquete nativo de Zone r575 ni en el índice del cliente. Hay terreno, destinos, áreas de misión y doodads de la sala; la ausencia del archivo de NPCs no demuestra que la sala no pueda cargar. No inventar NPCs ni copiar un spawner de otra zona. Queda pendiente una prueba autorizada del worker exacto `gatekeeper_hall 379` para establecer si puede cargar sin spawner; después se podrá cerrar la excepción correspondiente del panel con evidencia runtime.

## Servidor

Target `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`, padre `upstream/client_version/zone-10.0.2_r575` en `7babcb3a706c64295b5aaaeec8abe57e4d09b4da`. El Return del padre tampoco comprueba disponibilidad antes de mover. Se reutiliza el contrato IsZoneLoaded ya empleado por los retornos a casa/resurrección y comandos GM de AA10; no se introduce un contrato wire de AA8.

Return comprueba la disponibilidad de la zona de su destino explícito antes de SetPosition, SCLoadInstance, FinalizeTransform y SCTeleportUnit. Si ZoneAuthority está activo y no existe un host disponible, emite NoInteractionAvailable y conserva el personaje en su posición. También rechaza una sonda ausente en modo ZoneAuthority. El modo independiente conserva su comportamiento.

Dos pruebas ejecutan Return contra el destino real 1005/379 sin host y sin sonda; comprueban que no cambia Transform ni DisabledSetPosition. Build Release: cero errores. Suite: 2705/2705 correctas.

Imagen desplegada: `sha256:42e5d1a295b88a57838a1cd734877af42bf113a47cfbfa2d4bee202dae38a46b`.
Inicio 01:28:31 UTC; listeners 1239/1250 y Game listo a las 01:30:29; World 1240 desde el inicio; Login conectado y Web API 1280 listo a las 01:30:30. DLL efectiva SHA-256 `a827c04e8f7d386523ae5e5e2483257020bf2cdad6eef853568c939b79b3f4af`.

Rollback: imagen `aaemu-world:rollback-pre-garden-return-guard-20260907` (da891789...). Dump preventivo `failure-20260907/aaemu_game.before.sql`, SHA-256 `EBE536887A11AD34B6C95AFB4A42DE272F558E58DCF4BC3D46F5C5A78F517CAF`. No hubo mutaciones directas de DB ni cambios a compact del servidor.

## Descripción gigante

El consumidor efectivo `game/scriptsbin64/x2ui/interaction/interaction.alb`, SHA-256 `C43F082ABEC5F68A9BFCFC7B589B3A6B8C3068103602A0FBCC8248EEEC438509`, recibe DRAW_DOODAD_TOOLTIP y muestra info.explain sin interpretar variables de combate. El Lua fuente y el ALB decompilado corroboran el mismo comportamiento. No requieren edición.

En la compact efectiva, `(doodad_func_groups,name,45009)` contenía una descripción de daño de un arma naval, con `#{min_damage}~#{max_damage}`, y title_msg decía «La llama del dragón». La fase 49503 tenía textos de pesca y un árbol de combate. El catálogo completo r575 tiene vacíos estos campos mecánicos y sus localizaciones ko/en_us/ru. Se trata de asociaciones de localización incorrectas, no de variables que deban calcularse para un portal.

La revisión de las 13 puertas restauradas encontró ocho celdas afectadas en fases 45009, 43911, 43912 y 49503. `scripts/data/aa10-garden-text-contract.json` registra identidad compuesta, doodad, texto anterior y valor vacío correcto. Restaurar el vacío original es una corrección de asociación; no se eliminan variables de una habilidad válida. Se conservan nombres de puertas y todas las demás traducciones.

Builder `scripts/PatchAa10GardenTexts.py`, aplicador `scripts/ApplyAa10GardenTexts.py`, pruebas `scripts/test_garden_texts.py`. El builder exige tamaño y hash exactos, identidad de fase y campo nativo vacío; verifica esquema, todas las tablas mecánicas y todas las demás columnas/filas localizadas. Tres pruebas focales: identidad compuesta/idempotencia, rechazo de campo nativo no vacío y rechazo de deriva de traducción.

Compact de entrada: 468684800 bytes, SHA-256 `B44EBD1FED6EA82F09E83A239F1ADB9D0245528C4F052958D79056D6E8405ADD`.
Compact corregida: mismo tamaño, SHA-256 `9F776A30890B6E28ACA30139BF7190AE51B275C595357855398A1B667FBE7634`.

Reproducción: ejecutar `C:/Python313/python.exe scripts/ApplyAa10GardenTexts.py` para dry-run y añadir `--apply` para aplicar. El cliente debe estar cerrado. El aplicador usa PakEntryReplace, sincroniza la compact loose del cliente, guarda rollback de ambas y verifica por reextracción junto con mapa/icono/crafting ajenos. Registra hashes completos del paquete antes/después. Se rechazan versiones desconocidas para conservar traducciones posteriores: una reconstrucción desde otro baseline necesita revisar y renovar su contrato antes de reaplicar.

Control Center usa ruta/tamaño/mtime para invalidar caché, no una allowlist cerrada. Su build completo pasó: typecheck, 52 pruebas correctas y 1 omitida, smoke SQLite y compilación del panel. No se cambiaron sus fuentes.

Evidencia: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/garden-gate/failure-20260907`. La aceptación visual del texto y el cruce efectivo con Zone 379 cargada quedan pendientes; los checks estáticos y unitarios no sustituyen esa prueba.
