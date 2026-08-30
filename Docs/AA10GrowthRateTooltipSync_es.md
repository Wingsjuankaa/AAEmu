# Sincronización del tooltip de crecimiento AA10

## Motivo

El servidor aplica `World.GrowthRate` a cada `DoodadFuncGrowth`, pero el cliente
AA10 r575 calcula el tiempo total del tooltip combinando la fase actual recibida
del servidor con los delays nativos de las fases futuras guardados en
`game/db/compact.sqlite3`. Sin sincronización, los cultivos crecen a la tasa del
servidor mientras el tooltip conserva horas retail.

## Fuente de verdad

`Scripts/SyncAa10GrowthRateTooltip.py` toma:

1. `GrowthRate` desde el `World.json` efectivo de `.server_files`; si este no
   existe, usa la configuración versionada de `AAEmu.Game`.
2. Los delays originales desde `data/sqlite/retail/compact.sqlite3`.
3. Como destino de construcción, un `compact.sqlite3` extraído del `game_pak`
   efectivo del cliente AA10 r575.

La rutina reemplaza únicamente `doodad_func_growths.delay`. Siempre calcula
`floor(delay_retail / GrowthRate)` desde retail, nunca desde valores previamente
escalados. Por ello es idempotente y permite cambiar la tasa en cualquier
dirección sin acumular redondeos.

## Ejecución

La comprobación manual no modifica datos:

```powershell
python Scripts\SyncAa10GrowthRateTooltip.py
```

La aplicación validada es:

```powershell
python Scripts\SyncAa10GrowthRateTooltip.py --apply
```

Para desplegar el resultado real se ejecuta, con ArcheAge cerrado:

```powershell
.\Scripts\ApplyAa10GrowthRateGamePakPatch.ps1 -Apply -SkipFullPakHash
```

Este wrapper extrae `game/db/compact.sqlite3` del PAK, construye el reemplazo,
hace `VACUUM`, rellena hasta el tamaño exacto de la entrada, sustituye, vuelve a
extraer y verifica el hash. Además conserva el original y un manifiesto de
rollback bajo `backups/client-patches`.

La operación se ejecuta manualmente cada vez que se cambia `GrowthRate` en el
servidor. No está ligada al launcher ni al Control Center, porque el cliente se
distribuye finalmente con los mismos delays ya incorporados en `game_pak`.

Cada ejecución valida identidad de filas, `PRAGMA quick_check`, tasa finita en el
rango soportado `1..1000` y el estado posterior completo. Las transacciones de
SQLite protegen el resto de parches ya presentes en el cliente.

## Límite de cambios en caliente

El comando GM `/world set growthrate` solo cambia la configuración en memoria.
No modifica `World.json` ni existe un paquete servidor-a-cliente que actualice
los descriptores ya cargados. Para alinear una tasa nueva, se debe cambiar el
archivo efectivo y volver a abrir el cliente. No hace falta reiniciar Zone para
la sincronización del archivo del cliente.

## Rollback

Configurar `GrowthRate` en `1.0` y ejecutar nuevamente el wrapper restaura los
delays retail desde la base inmutable. También puede aplicarse cualquier otra
tasa válida del mismo modo. Para una restauración byte a byte, cada ejecución
conserva `compact.before.sqlite3` y su hash esperado en `manifest.json`.
