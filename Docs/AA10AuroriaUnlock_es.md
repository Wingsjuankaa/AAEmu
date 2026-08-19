# Desbloqueo de Auroria AA10 r575 — evidencia y runbook

**Fecha:** 18 de agosto de 2026

**Cliente:** ArcheAge Returns `10.0.2.13 r575`

**Estado:** aplicado y aceptado en cliente; mapa continental y Western Hiram
Mountains funcionales.

## Resultado técnico

Auroria estaba cerrada por tres gates independientes:

1. `x2game.dll` interceptaba el clic sobre `world_groups.id=5` (`origin`) y
   mostraba el aviso de contenido no disponible;
2. 21 de los 30 recursos `o_*` de `map_resources` tenían `enable='f'`;
3. las 31 particiones de `zones` cuyo `zone_group.target_id=5` y los 13 ciclos
   correspondientes de `conflict_zones` tenían `closed='t'`.

El tercer gate es necesario en AAEmu, no sólo en la UI. `ZoneManager` carga
`zones.closed` y lo usa para portales, skills de viaje y cambios de zona. Sólo
inicializa el estado de guerra de un `conflict_zone` cuando su fila no está
cerrada.

La corrección abre exclusivamente esos conjuntos r575. No inicia procesos
ZoneHost ni hace que una partición sin spawner sea ejecutable.

## Evidencia del cliente

El script recibido en `E:\AAEmu\rama_10\docs\unlock_auroria.py`, SHA-256
`8F746F8541FB80F3FE835A4B68CC0C525A183CDC53467B1EDCA135CD718A0F43`,
localiza la constante a partir del aviso chino y de su único puntero absoluto.
No depende de un offset fijo entre builds.

En el cliente r575:

| Binario | Offset | Cambio | Bytes distintos | Estado |
|---|---:|---|---:|---|
| `x2game.dll` | `0x1336778` | `5 -> 9999` | 2 | aplicado |
| `x2game-dev.dll` | `0x15e18e0` | `5 -> 9999` | 2 | aplicado |
| `x2game-dev_dedicate.dll` | `0x156e938` | sin cambio | 0 | bloqueado por una Zone activa; no requerido por la UI release |

El binario efectivo del cliente es `x2game.dll`. Su SHA-256 cambió de
`2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76` a
`405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.
El backup original está junto al DLL como `x2game.dll.pre_auroria.bak`.

## Parche reproducible del catálogo

`Scripts/PatchAa10AuroriaCatalog.py` valida antes de escribir:

- `world_groups.id=5`, nombre `origin` y parent `WorldGroup 2`;
- la identidad completa de 30 recursos `o_*`;
- la identidad de las 31 particiones con `zone_groups.target_id=5`;
- los 13 `conflict_zones` Auroria;
- estados booleanos `f/t`, ausencia de cambios externos, tamaño constante y
  `PRAGMA quick_check=ok`.

Aplicación reproducible:

```powershell
python -B Scripts\PatchAa10AuroriaCatalog.py `
  'E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game\db\compact.sqlite3' `
  '.server_files\AAEmu.Game\Data\compact.sqlite3' --apply
```

El cliente prioriza `game/db/compact.sqlite3` dentro de `game_pak`. La copia
validada se reinsertó con `Tools/PakEntryReplace`, preservando los
`440,823,808` bytes y reabriendo la entrada para verificar su hash.

| Artefacto | SHA-256 anterior | SHA-256 Auroria |
|---|---|---|
| compact cliente / entrada `game_pak` | `F8C7A0268A26D4EFAEC47A2A2B1B525447BF16C274506CD97BF571839B5E6D29` | `0ADAA070936F8AFBE0A60307C391CF1C08ECCB98DD48A32024D4F295C140FC86` |
| compact runtime | `FB9273AE82F69FAFCF5FF94E2FF95D7BBCB29A3AD3F6502CAF05713251BAFDAF` | `23FEC0E7CD7F362125CDDE3CF32F0D60D3EDC3C5BCEFF60DFE7244B67B68373B` |
| `game_pak` completo | `32499AC6BF3ED1C1CE24B5A15A151355CB0C5A352A0C2BA727769AEEB3FC89D5` | `4DC5F729D54A8976802C2282F8D27512136BDF2354CB6B1594AAC7E626CCA8EB` |

La verificación idempotente final obtuvo cero recursos deshabilitados, cero
particiones cerradas y cero conflictos cerrados dentro del conjunto Auroria.
Los tres `map_resources` deshabilitados ajenos a Auroria permanecieron sin
cambios.

## Validación automática

- dry-run final del parche sobre compact cliente y runtime: cero cambios
  pendientes y `PRAGMA quick_check=ok` en ambas;
- segunda ejecución de `PakEntryReplace`: `Already patched`, tamaño y SHA-256
  exactos;
- comparación binaria con los backups: dos bytes distintos en cada DLL de
  cliente parcheado y cero en el dedicate bloqueado;
- build completo Release: 0 errores;
- suite TUnit Release: 1.322 correctas, 0 fallos, 0 omitidas.

Las advertencias de paquetes y análisis ya existentes permanecen visibles y no
pertenecen a este cambio de catálogo.

## Runtime

Se reinició únicamente `game` para que `ZoneManager` releyera el compact
montado. El servicio volvió a `healthy`; DB y Login no se reiniciaron. La Zone
Solzreed `142` se desconectó durante el reinicio y debe relanzarse desde AAEmu
Control Center si se necesita nuevamente.

Codex no inicia, detiene ni relanza Zones. El usuario mantiene control exclusivo
de su lifecycle desde el panel.

## Aceptación jugable

El usuario confirmó el 18 de agosto de 2026 que el mapa de Auroria abre y carga
correctamente sus regiones y estados visuales. Después levantó Western Hiram
Mountains desde AAEmu Control Center:

- `zoneKey=351` alcanzó `ZoneLoaded` a las `02:20:23`;
- `zoneKey=350` alcanzó `ZoneLoaded` a las `02:20:28`;
- ambas particiones anunciaron sus spawners y registraron cobertura NPC sin
  ventanas cerradas;
- el teletransporte controlado a coordenadas de `zoneKey=350` funcionó y el
  usuario confirmó que la zona era jugable.

Con esto quedan aceptados el desbloqueo del continente, los recursos de mapa,
la apertura runtime, la carga de las dos particiones de Western Hiram y la
entrada real del personaje. Las demás regiones de Auroria conservan el mismo
catálogo abierto, pero todavía no tienen aceptación jugable individual.

## Primera aceptación controlada

1. Con el cliente cerrado durante el parche, iniciarlo nuevamente.
2. Abrir el mapa mundial y pulsar Auroria. Debe abrir el continente sin el aviso
   de “próximamente”.
3. Recorrer las regiones y confirmar fondos, nombres, iconos y estados de
   conflicto. No debe aparecer ningún panel vacío por `map_resources.enable`.
4. Para probar entrada real, seleccionar en el panel una sola partición. Se
   recomienda `o_shining_shore_1`, `zoneKey=282`, después de validar/cargar su
   spawner.
5. Esperar `ZoneLoaded zoneId=282` y heartbeat antes de usar `/teleport ds`.
6. Confirmar handoff, movimiento, NPCs, doodads, mapa local y estado de
   conflicto. Guardar y reloguear antes de ampliar el perfil.

Stop point: no levantar todas las particiones de Auroria a la vez en la primera
prueba. Validar una Zone, luego sus particiones hermanas y finalmente ampliar el
perfil por región.

## Rollback

Respaldos:

```text
E:\AAEmu\rama_10\backups\feature-reconstruction\aa10-auroria-unlock-20260818\
  client-compact-before-auroria.sqlite3
  runtime-compact-before-auroria.sqlite3
```

Además, cada DLL procesado conserva su `*.pre_auroria.bak` junto al original.

Para revertir:

1. cerrar el cliente;
2. restaurar `x2game.dll` desde `x2game.dll.pre_auroria.bak`;
3. reemplazar la entrada `game/db/compact.sqlite3` de `game_pak` usando
   `client-compact-before-auroria.sqlite3` y exigiendo como hash actual
   `0ADAA070936F8AFBE0A60307C391CF1C08ECCB98DD48A32024D4F295C140FC86`;
4. restaurar las copias sueltas cliente/runtime desde los respaldos;
5. reiniciar sólo Game y relanzar desde el panel las Zones requeridas.

No se modificaron la SQLite completa autoritativa, los respaldos retail, MySQL,
`.env`, DB, Login ni los binarios del servidor Zone r575.
