# Reconstrucción de Item Lock AA10 r575

## Clasificación y autoridad

Item Lock es una mecánica retail de ArcheAge Returns 10.0.2.13 r575 que falta en el fork; no es
gameplay nuevo. La autoridad se aplica en este orden: SQLite full/compact, Lua/localización,
consumer y serializer de `x2game.dll`, comportamiento retail, upstream y finalmente AA8 como
candidato estructural.

## Evidencia cerrada

- `item_categories.secure=true` en 30 categorías de equipo.
- `item_secure_exceptions` contiene 803 templates; 9.915 templates quedan elegibles.
- Regla exacta: categoría segura y template ausente de excepciones.
- Content config 43: `item_secure_unlock_delay_time=4320` minutos (72 horas).
- Content configs 214/215/222/223: coste 0, UI de equipo activa, segundo password de lock/unlock
  desactivado.
- Lua `item_lock.lua`: lock/unlock individual y lock/unlock de todo el equipamiento.
- Requests r575: `CSItemSecurePacket` y `CSItemUnsecurePacket` serializan exactamente
  `slotType:u8 + slot:u8 + itemId:u64` (10 bytes); ambos requests de equipamiento tienen body
  vacío. Los bytes cero en los offsets internos `+0x10` y `+0x12` del objeto C++ no se transmiten.
- El servidor ya conserva `ItemFlag.Secure`, `UnsecureTime`, `items.unsecure_time`,
  `ItemUpdateSecurity` y `ItemTaskType` 94-96.
- Localización: un item bloqueado no debe destruirse ni transferirse; backpacks/trade packs no son
  elegibles. Los mensajes bulk son 698/699.

## Corroboración externa

- ArcheRage, *Items Lock System*: https://na.archerage.to/forums/threads/server-updates-3-28-easter-festival-start-items-lock-system-risopoda-mount-and-more.11190/
- ArcheRage FAQ: https://na.archerage.to/forums/threads/faq-frequently-asked-questions.7292/

Las fuentes externas sólo corroboran la intención de protección. El coste externo de 10 gold se
descarta porque AA10 r575 fija coste cero. `Lock Item Position` es otra función y queda fuera.

## Contrato implementado

1. Lock nuevo: fija `Secure`, limpia `UnsecureTime`, emite `ItemLock`/`ItemUpdateSecurity`.
2. Unlock nuevo: mantiene `Secure`, fija `now + 72 h`, emite `ItemUnlock`.
3. Unlock repetido antes del plazo: no muta ni reinicia el reloj.
4. Unlock al vencer: limpia flag y fecha, emite `ItemUnlockExcess`.
5. Lock durante espera: cancela el unlock pendiente sin quitar la protección.
6. Bulk: opera sólo equipo elegible y agrupa las acciones por task type.
7. Equipo bloqueado puede moverse dentro del mismo dueño, equiparse, desequiparse, repararse y
   perder durabilidad. No puede destruirse, consumirse, venderse, tradearse, enviarse, subastarse o
   sufrir una transformación irreversible.

## Gate de activación

`itemSecure` permaneció en `false` durante implementación y primer arranque desplegado. Después de
superar build, suite, carga de datos y startup se reactivó para la prueba con cliente retail. El
lifecycle de Zone pertenece al usuario y no se opera desde este trabajo sin autorización separada.

## Resultados

### Implementación cerrada

- `ItemSecurityGameData` carga las 30 categorías, 803 excepciones y los cinco content configs sin
  duplicar el catálogo en código.
- `ItemSecurityService` atiende los cuatro requests, revalida owner/container/slot/id bajo el lock
  de la lista del contenedor y usa reloj inyectable.
- `ItemSecurityPolicy` concentra las transiciones y tres familias de riesgo: consumo/destrucción,
  transferencia de propiedad y transformación irreversible.
- `flags` y `unsecure_time` marcan el mismo objeto dirty y el save existente los escribe en el mismo
  `REPLACE INTO items`; no hubo migración SQL.
- Las guardas cubren destrucción parcial/total, crafting/reactivos, venta/buyback, mail, auction,
  trade y los consumidores irreversibles reconstruidos. Equipar, reparar, desgaste y movimientos
  internos del mismo owner continúan permitidos.

### Gates ejecutados el 2026-08-31

- Build `AAEmu.slnx` Release: 0 errores.
- Foco `*Security*`: 13/13 pruebas.
- Suite `AAEmu.UnitTests`: 1.711/1.711 pruebas.
- `AAEmu.Login.IntegrationTests`: verde dentro de la pasada de solución.
- Pasada completa de solución: 1.717/1.718; la única prueba de `AAEmu.IntegrationTests` no llega al
  código de quests porque su `Config.json` generado conserva `%db_port%`. Es una limitación conocida
  del harness, también registrada por checkpoints anteriores, no una falla de Item Lock.
- Primera verificación desplegada con feature oculto: fuente, runtime, contenedor y fset efectivo
  confirmaron `itemSecure=false` (`byte 5: 0x09`).
- Imagen desplegada: `sha256:bc4de4a6163afd09851bc41f0eebedd5eef1791273015de5d751dd4f29c981fb`;
  rollback: `aaemu-world:rollback-pre-item-lock-20260831-105220`.
- La configuración fue reactivada después de ese gate para la aceptación retail. Zone se desconectó
  al recrear Game y no fue iniciada ni relanzada por Codex.
- Segundo arranque: fuente/runtime/contenedor `itemSecure=true`; fset byte 5 `0x29` y
  `Enabled Features` incluye `itemSecure`. Game quedó healthy, levantó Game/Stream/WebApi y Login
  registró nuevamente `GameServerId 1`.

### Aceptación retail del núcleo (2026-09-03)

El usuario confirmó después del wire fix que el item queda visiblemente bloqueado incluso tras
reloguear y que la tienda impide venderlo. Con esta evidencia el núcleo solicitado se clasifica
`ACEPTADO`: mutación visible, persistencia y una protección irreversible real. El unlock temporizado
y bulk mixto se mantienen en la matriz de regresión ampliada, pero ya no bloquean la siguiente
reconstrucción del roadmap.

### Gates de regresión ampliada

- Prueba retail con equipamiento desechable: lock, reconexión, unlock, vencimiento controlado y
  unlock final, incluyendo equipo mixto bulk.
- Confirmar persistencia real tras reinicio y capturar wire cliente-servidor.
- Mantener capturas del unlock temporizado, vencimiento controlado y bulk mixto en una pasada futura.

### Corrección posterior a la primera prueba retail

- La primera acción individual mostró `Item locked.` en el chat, pero no produjo badge ni
  persistencia. El log de Game registró `Attempted to read beyond the end of the stream` antes de
  `CSItemSecurePacket` y respondió con `SCErrorMsgPacket`; no existió commit de Item Lock.
- La causa fue una fixture heredada incorrecta de 12 bytes: el parser consumía dos ceros que sólo
  existen en la estructura C++ del cliente. La serialización nativa de `FUN_39aa83f0` escribe
  únicamente los miembros `+0x11`, `+0x13` y `+0x18`, mediante los serializers de `u8`, `u8` y
  `u64` respectivamente.
- Secure y Unsecure ahora leen el body retail de 10 bytes y la fixture binaria fija este contrato.
- Revalidación: build Release sin errores, 13/13 pruebas Security y 1.711/1.711 unit tests.
- Fix desplegado en `sha256:d2e2121df0f667d29fa755cfe29bc8d01d6a6235054ac5a29153d604256bffec`;
  rollback inmediato `aaemu-world:rollback-pre-item-lock-wirefix-20260831-111533` →
  `sha256:bc4de4a6163afd09851bc41f0eebedd5eef1791273015de5d751dd4f29c981fb`.
- Fuente, runtime montado y contenedor conservan `itemSecure=true`; Game quedó healthy, terminó el
  arranque en 93,83 s, publicó `itemSecure` en Enabled Features y se registró nuevamente en Login.
- El recreate desconectó Zone; Codex no inició ni relanzó su proceso.
