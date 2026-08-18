# AA10 r575 — undergarments de Celestial a Eternal

Fecha: 2026-08-16

Target: `Wingsjuankaa/AAEmu:rama_10`

Padre: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`

## Síntoma

Un `Leopard Undergarments` sintetizado hasta Celestial mostraba `Max Grade` y
rechazaba más EXP. No era una restricción de esa plantilla: las doce piezas de
undergarments sintetizables de r575 apuntan a la categoría `23`.

## Causa

`item_rnd_attr_categories.id=23`
(`live.16.10.cash_underwear.total_attr`) venía con
`max_evolving_grade=7`, aunque la misma categoría incluye la escalera completa
hasta Eternal:

| Grado | ID | `grade_exp` | `gain_exp` | Máx. efectos |
|---|---:|---:|---:|---:|
| Celestial | 7 | 2,100 | 3,420 | 4 |
| Divine | 8 | 2,400 | 4,680 | 4 |
| Epic | 9 | 3,200 | 6,120 | 4 |
| Legendary | 10 | 6,600 | 8,000 | 5 |
| Mythic | 11 | 10,000 | 12,000 | 5 |
| Eternal | 12 | 15,000 | 18,000 | 5 |

El cliente lee el mismo cap y por eso mostraba `Celestial — Max Grade`; AAEmu
también lo cargaba directamente y detenía la promoción. No existe un mapping de
awakening intermedio para esta familia.

Como contraste externo, ArcheAge Codex publica el template `53416`, presente en
este mismo r575 y unido a la categoría `23`, hasta Eternal con `15,000` EXP y
`18,000` EXP como material: valores idénticos a la escalera local.

## Corrección reproducible

`Scripts/PatchAa10UndergarmentGradeCap.py` valida nombre, grupo, las seis filas
Celestial-Eternal, la presencia de plantillas y `PRAGMA quick_check`; después
cambia transaccionalmente sólo la categoría `23` de `7` a `12` y exige que el
tamaño del archivo no cambie.

```powershell
python Scripts/PatchAa10UndergarmentGradeCap.py `
  '<cliente>\game\db\compact.sqlite3' `
  '.server_files\AAEmu.Game\Data\compact.sqlite3'
```

El cliente prioriza la entrada `game/db/compact.sqlite3` de `game_pak`, por lo
que también se reemplazó con `Tools/PakEntryReplace`, exigiendo hash previo y
tamaño idéntico.

Comando reproducible aplicado sobre la entrada efectiva:

```powershell
dotnet run --project Tools/PakEntryReplace/PakEntryReplace.csproj --configuration Release -- `
  '<cliente>\game_pak' 'game/db/compact.sqlite3' `
  '<cliente>\game\db\compact.sqlite3' `
  '90839A7FBF260979C401FC4563F4DCCACD62E8A6F4ED25EA9C2ECA9E0DA2A2B0'
```

`PakEntryReplace` comprueba el SHA-256 de la entrada actual, exige que el reemplazo conserve sus
`440,823,808` bytes, recalcula el MD5 interno del paquete, cierra y reabre `game_pak`, vuelve a
extraer la entrada y exige tamaño y SHA-256 finales. La igualdad se refiere al tamaño lógico de la
entrada. El contenedor completo puede crecer por la nueva representación comprimida y metadatos.

## Identidad desplegada

| Artefacto | SHA-256 anterior | SHA-256 corregido |
|---|---|---|
| compact cliente / entrada de `game_pak` | `90839A7FBF260979C401FC4563F4DCCACD62E8A6F4ED25EA9C2ECA9E0DA2A2B0` | `075A661C865E2C9357AB9C9E084100C17C832EFAF6913669D672FCA78632411B` |
| compact runtime | `DF10A47C10D65D6AE64187BE37FE1708646EF5CED284E46ADA3016E112957E0A` | `EDA870B4256C8DACF47823E60422DCC0604923913C76BE9CF285C5E3E79C3BDA` |

Identidad final del paquete activo:

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| `game_pak` completo después del reemplazo | `68,963,258,880` | `7BAAAA4AE6C42D7478A6A75F338E0748B18B2871EE6A16D9C12601F68538CF1E` |
| entrada extraída `game/db/compact.sqlite3` | `440,823,808` | `075A661C865E2C9357AB9C9E084100C17C832EFAF6913669D672FCA78632411B` |

La verificación final idempotente devolvió:

```text
Already patched game/db/compact.sqlite3 (440823808 bytes,
SHA-256 075A661C865E2C9357AB9C9E084100C17C832EFAF6913669D672FCA78632411B)
```

Respaldos:

```text
E:\AAEmu\rama_10\backups\feature-reconstruction\aa10-undergarment-cap-20260816\
  client-compact-before-undergarment-cap.sqlite3
  runtime-compact-before-undergarment-cap.sqlite3
```

El respaldo cliente también es la copia exacta de la entrada anterior de
`game_pak`, por lo que permite rollback sin duplicar el paquete completo.

Para rollback: cerrar el cliente, ejecutar `PakEntryReplace` usando
`client-compact-before-undergarment-cap.sqlite3` como reemplazo y el hash corregido `075A...411B`
como hash esperado; después restaurar `runtime-compact-before-undergarment-cap.sqlite3` en
`.server_files/AAEmu.Game/Data/compact.sqlite3` y reiniciar Game. No se versionan el paquete de
~69 GB, las SQLite ni los respaldos; Git conserva el parche reproducible, hashes y procedimiento.

## Prueba de aceptación

1. Abrir el `Leopard Undergarments` Celestial: ya no debe mostrar `Max Grade`.
2. Abrir Bag → Gear Upgrade → Synthesis y alimentar un `Bound Worn Costume`.
3. Si la pieza conservó la barra Celestial llena (`2,100/2,100`), un material
   Unique de `3,200` EXP debe dejarla en Epic con `800/3,200` sin bonus; el
   bonus aleatorio puede aumentar ese remanente.
4. Continuar hasta Eternal y comprobar la quinta línea de efecto en Legendary.
5. Reloguear y verificar grado, EXP, efectos y estadísticas en `C`.

## Resultado de aceptación

Aceptado por el usuario el 2026-08-16 sobre el cliente exacto r575. Se eliminó la pieza antigua, se
entregó un `Leopard Undergarments` nuevo (`template 51032`) mediante el comando GM normal y se
sintetizó hasta **Eternal, grado 12**. El tooltip dejó de bloquearse en Celestial, consumió materiales
en todos los tramos Divine–Eternal y la ventana `C` reflejó sus modificadores. Con este recorrido se
dio por cerrada la fase.
