# CHECKPOINT_NATIVE_ITEM_LOCK_V1

Fecha: 2026-08-31
Target: ArcheAge Returns 10.0.2.13 r575
Branch: `rama_10`
Estado: `NÚCLEO RETAIL ACEPTADO / REGRESIÓN AMPLIADA PENDIENTE`

## Decisión

Item Lock se reconstruyó como mecánica retail AA10. No es mecánica nueva. El servicio y la política
son infraestructura interna. `Lock Item Position` permanece fuera de alcance.

## Autoridad cerrada

- 30 categorías con `item_categories.secure=true`.
- 803 templates en `item_secure_exceptions`.
- 9.915 templates elegibles por categoría menos excepción.
- Unlock delay: 4.320 minutos.
- Coste: 0; UI bulk: activa; passwords secundarios: inactivos.
- Requests individuales: body r575 de 10 bytes (`slotType:u8 + slot:u8 + itemId:u64`); requests
  bulk: body vacío.
- Tasks nativos: `ItemLock=94`, `ItemUnlock=95`, `ItemUnlockExcess=96`.
- Errores: condición individual 664; bulk sin aplicables 698/699.

## Producto implementado

- Catálogo/data loader: `ItemSecurityGameData`.
- Orquestación: `ItemSecurityService` para lock/unlock individual y bulk.
- Estado y restricciones: `ItemSecurityPolicy`, fail-closed para consumidores irreversibles no
  clasificados.
- Los cuatro handlers C2G delegan en el servicio.
- Mutaciones sincronizadas por `container.Items` y por item; cambios de flags/fecha quedan dirty y
  se persisten juntos mediante el save existente.
- Guardas centrales y de borde para destrucción parcial/total, consumo, crafting, venta, buyback,
  trade, mail, auction y transformaciones irreversibles conocidas.
- Sin cambios al cliente ni al esquema SQL.

## Validación reproducible

```powershell
dotnet build AAEmu.slnx --configuration Release --no-restore
dotnet test AAEmu.UnitTests\AAEmu.UnitTests.csproj --configuration Release --no-build --no-restore -- --treenode-filter '/*/*/*Security*/*'
dotnet test AAEmu.UnitTests\AAEmu.UnitTests.csproj --configuration Release --no-build --no-restore
dotnet test AAEmu.slnx --configuration Release --no-build --no-restore
```

Resultados:

- Build Release: 0 errores.
- Foco Security: 13/13.
- Unit tests: 1.711/1.711.
- Imagen del wire fix: `sha256:d2e2121df0f667d29fa755cfe29bc8d01d6a6235054ac5a29153d604256bffec`.
- Rollback del wire fix: `aaemu-world:rollback-pre-item-lock-wirefix-20260831-111533` →
  `sha256:bc4de4a6163afd09851bc41f0eebedd5eef1791273015de5d751dd4f29c981fb`.
- Fuente, runtime montado y contenedor: `itemSecure=true`; arranque completo en 93,83 s, feature
  presente en Enabled Features y Game registrado en Login. Zone se desconectó y Codex no operó su
  lifecycle.
- Solución: 1.717/1.718; el único rojo es el harness de
  `QuestManagerTests.GetQuestIdFromStarterItem_ShouldReturnSameResultAsOriginal`, que intenta bindear
  el placeholder `%db_port%` antes de ejecutar la prueba. Login integration y unit tests pasan.

Revalidación después de corregir el framing retail:

- Decompilación de `FUN_39aa83f0`: sólo serializa los miembros `+0x11`, `+0x13` y `+0x18`; los
  ceros en `+0x10`/`+0x12` se inicializan en memoria, pero no viajan en el paquete.
- Build Release: 0 errores.
- Foco Security: 13/13.
- Unit tests: 1.711/1.711.

## Feature gate y runtime

- Primer arranque de control: fuente, runtime montado, contenedor y fset efectivo confirmaron
  `itemSecure=false`; byte 5 cambió de `0x29` a `0x09` y el nombre desapareció de Enabled Features.
- Imagen desplegada: `sha256:bc4de4a6163afd09851bc41f0eebedd5eef1791273015de5d751dd4f29c981fb`.
- Rollback preservado: `aaemu-world:rollback-pre-item-lock-20260831-105220` →
  `sha256:f554bf7857f22f3e136124d08c12a51e599a1fa802a2c4c3da07c4dc8712148b`.
- Tras superar el control se reactivó `itemSecure=true` en fuente y runtime para la prueba retail.
- Game fue recreado; DB y Login no se reiniciaron. Zone se desconectó y no fue operada por Codex.
- Segundo arranque verificado: contenedor healthy, `Server started!` en 84,98 s, Game/Stream activos,
  fset byte 5 `0x29`, `Enabled Features` incluye `itemSecure` y Login registró `GameServerId 1`.

## Aceptación retail recibida el 2026-09-03

Después de desplegar la corrección de framing, el usuario confirmó que el item queda visiblemente
lockeado, conserva el lock tras relog y no puede venderse. Eso cierra mutación, persistencia y una
protección de pérdida real del núcleo Item Lock.

## Regresión ampliada que falta

La primera prueba retail no mutó el item. Game registró
`Attempted to read beyond the end of the stream` al decodificar `CSItemSecurePacket` y respondió
`SCErrorMsgPacket`; el cliente localizó ese error como `Item locked.`. Se corrigió el parser y la
fixture heredada de 12 bytes al contrato nativo de 10 bytes. Por eso no hubo badge ni persistencia
en esa prueba.

1. El usuario inicia la Zone necesaria desde Control Center.
2. Ejecutar con equipo desechable: lock → relog → unlock pendiente → relog →
   vencimiento simulado → unlock final, además de bulk mixto y matriz de operaciones.
3. Capturar logs/wire y persistencia MySQL.
4. Si aparece una regresión en estas ramas extendidas, corregirla sin revertir la aceptación ya
   demostrada de lock/relog/venta.
