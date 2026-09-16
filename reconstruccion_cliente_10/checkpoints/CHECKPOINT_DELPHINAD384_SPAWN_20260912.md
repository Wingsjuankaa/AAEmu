# Delphinad Mirage384: restaurar entrada nativa

2026-09-12; rama_10 HEAD45bba0ad49fee55ab30a80168b4d6caefbb9ac87, padre upstream/client_version/zone-10.0.2_r575 @1017677b40be6508861a8fb74e9d09fa496873c9. Clasificación client-native (dato ausente de configuración).

## Evidencia
Durante quest10050, usar44250 en doodad15196 crea World100/template59, instance_phantom_of_delphinad. A las16:37:49 UTC Dungeon anuncia384 en SCLoadInstance, pero a las16:37:50 PlayerEnterService rechaza zoneId0 y devuelve a selección. La384 manual estaba ZoneLoaded desde16:37:35 con33 NPCs; no era una Zone apagada. world_spawns.json no tenía el mundo/zona; XmlWorldZone.SpawnPosition nace con ceros y Dungeon copiaba ese objeto al Transform. La ausencia también está en el padre exacto y en el catálogo AA8 consultado.

DB después del fallo: Dannia1007 conserva zone382, XYZ33281.3/34842.8/282.717, su posición anterior al portal. Character.Save ya usa MainWorldPosition para instancias: no se editó DB ni se otorgaron/completaron misiones. LoginReservations mostraba382; el reinicio permite comenzar una sesión limpia. Reportes quest10050 sin entradas asociadas.

## Fuente nativa exacta
Referencia inmutable r575: extracción read-only de game_pak bajo artifacts/delphinad-native. No se escribió en ningún cliente.
- game/worlds/instance_phantom_of_delphinad/world.xml, SHA2569969c75997520fb4e7e95b5f6733bf091f7f1632db6057eb0f2ee8eac86bed7e: Zone384 originX1/originY1.
- level_design/zone/384/world_server/spawn_point.g, SHA256f859b3f2bf673a47d011aca2f2592a91ec87eed72b77ad16b2938b83c1df1fb0: local524.66/1045.13/282.607, zRot -2.0944 rad.
- Conversión de ZoneManager: origen*1024 + local. Mundo1548.66/2069.13/282.607; yaw -120.0002806121996 grados conforme al catálogo world_spawns.
- El punto cae en celda nativa(1,2), incluida en world.xml. ID de región137, zoneKey384 y templateWorld59 son dominios distintos.

## Cambio
Añadida una única entrada instance_phantom_of_delphinad a AAEmu.Game/Data/Worlds/world_spawns.json y al bind .server_files/AAEmu.Game/Data/Worlds/world_spawns.json. Nombre coincide tanto con World como con XmlWorldZone, por lo que carga384 y sus coordenadas en ambos. No se cambian reglas de instancias, fallback de hosts manuales, requisitos, costes o progreso.

Scripts/RestoreAa10DelphinadSpawn.py reproduce el dato confirmado, dry-run por defecto, --apply con respaldo; conserva comentarios/otras entradas, valida el resultado, rechaza una entrada conflictiva y no repite modificaciones. Ejemplo desde repo: python Scripts/RestoreAa10DelphinadSpawn.py --world-spawns AAEmu.Game/Data/Worlds/world_spawns.json .server_files/AAEmu.Game/Data/Worlds/world_spawns.json --apply.

## Validación y despliegue
Restore/build Release y suite2808/2808 correctos. Verificación del script: dry-run no muta, conserva entradas/comentarios, idempotencia, rechazo de conflicto sin escritura; propiedad de celda comprobada contra XML nativo. game_pak/compact intactos. Nueva imagen construida y sólo Game recreado; hash efectivo y startup en manifest.

Rollback: backups/delphinad384-20260912 contiene DB/compact/world_spawns/log/World; aaemu-world:rollback-delphinad384-20260912 conserva imagen previa607c2bcb397712a865007a79ecce8b4a919c8fc37f45a7e25a80ec8f43fa4715. Por ser bind, revertir world_spawns además de imagen. No restaurar DB sobre progreso nuevo para rollback de configuración.

Aceptación retail pendiente: usuario relanza Garden y384 desde Control Center, abre cliente de nuevo, entra con Dannia en Garden y vuelve a cruzar portal. Confirmar EnterZone384 y presencia estable; no operar Zones desde esta tarea. Cierre esperado: entrada en Delphinad y entrega10050 al doodad15086.
