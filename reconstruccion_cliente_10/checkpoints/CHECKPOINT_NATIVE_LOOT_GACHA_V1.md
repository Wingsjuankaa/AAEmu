# CHECKPOINT_NATIVE_LOOT_GACHA_V1

Fecha: 2026-09-03
Target: ArcheAge Returns 10.0.2.13 r575
Branch: `rama_10`
Estado: `ACEPTADO Y CERRADO`

## Decisión

Loot Gacha es una reconstrucción retail AA10. Se ejecuta sobre la invocación de skill nativa tipo
16, no mediante un paquete C2G inventado. Servicio, calculador y tablas de persistencia son
infraestructura interna y no cuentan como mecánica nueva.

## Contratos cerrados

- Catálogo: 11 packs, 24 asociaciones source/consume y 30 advanced packs.
- Lote retail: 1 hasta el menor stock total de caja/llave expuesto por `GetMaxLootCount()`. Las
  instancias seleccionadas autentican owner, bolsa y template; el preflight y consumo abarcan
  todas las pilas elegibles coincidentes, con la seleccionada primero. Cada ronda emite su
  Log/Result y `leftCount` cuenta aperturas pendientes hasta cero. El rango 1-10 sólo pertenece al
  comando de diagnóstico.
- Tipo 16: `flag:u8 + count:u32`, seguido fuera del objeto por `inputDirection`.
- Respuestas: Log `0x2E2`, Result `0x2E3`, Dump `0x2E4`.
- Result máximo: 15 items completos.
- Loot sin multiplicadores ordinarios; pack base por ronda y hasta un advanced por prioridad.
- Persistencia: total por gacha pack y `last_round` por advanced pack.
- Fail-closed: feature, owner, instancia/template, asociación, cantidad, Item Lock, espacio y catálogo.

## Archivos principales

- `AAEmu.Game/GameData/LootGachaGameData.cs`
- `AAEmu.Game/Core/Managers/LootGachaService.cs`
- `AAEmu.Game/Models/Game/Items/Loots/LootGachaCalculator.cs`
- `AAEmu.Game/Models/Game/Char/CharacterGachaRecords.cs`
- `AAEmu.Game/Models/Game/Skills/SkillObject.cs`
- `AAEmu.Game/Core/Packets/G2C/SCGachaLootPackItem*Packet.cs`
- `SQL/updates/2026-09-03_aaemu_game_character_gacha_records.sql`

## Validación y despliegue

- Build completo `AAEmu.slnx`: 0 errores.
- Unit tests finales después de la corrección multi-stack: 1.723/1.723, 0 fallos, 0 omitidos.
- Datos canónicos: 11/24/30.
- Migración aplicada: tablas `character_gacha_records` y
  `character_gacha_advanced_records`, verificadas con 0 filas iniciales.
- Imagen Game con `Max` multi-stack corregido desplegada:
  `sha256:251f07433478e1cb6abdc89d0c1e5b2c3514559ead66d2c64daa7c112cbc3c46`.
- Rollback inmediato anterior a la corrección multi-stack:
  `aaemu-world:rollback-pre-gacha-multistack-fix-20260903-082033`, imagen
  `sha256:6c595e547f3ab41a489f63a179a837a950d5e47227015632a3949b52ed57e306`.
- Rollback de la corrección del límite debug conservado:
  `aaemu-world:rollback-pre-gacha-max-fix-20260903-075957`.
- Rollback de la corrección UI conservado:
  `aaemu-world:rollback-pre-gacha-ui-fix-20260903-074333`.
- Rollback pre-mecánica conservado:
  `aaemu-world:rollback-pre-loot-gacha-20260903-072217`, imagen
  `sha256:d2e2121df0f667d29fa755cfe29bc8d01d6a6235054ac5a29153d604256bffec`.
- Respaldo previo:
  `.server_files/backups/loot-gacha-20260903-072217/aaemu_game_pre_loot_gacha.sql`.
- Game recreado de forma aislada; Login y DB conservaron sus container IDs. Zone quedó bajo
  control explícito del usuario.
- Runtime corregido: healthy, reinicios 0, `Server started!` en `00:01:21.5456964`, loader Gacha completado,
  `lootGacha` habilitado y registro en Login exitoso.
- Aceptación retail completada para caja+llave, lote, relog, multi-stack y catálogo metálico.

## Hallazgo dinámico posterior

La primera apertura retail confirmó consumo y reward, pero dejó la UI trabajando. El servidor
había enviado `leftCount=9` usando erróneamente el stock restante. `FUN_39132f40` y
`FUN_39132b00` del cliente r575 demuestran que el campo repuebla el contador pendiente y vuelve a
entrar en modo Gacha cuando es mayor que cero. Se corrigió a countdown por ronda `N-1 ... 0`, se
redesplegó Game de forma aislada y se verificaron loader, feature, fset y registro en Login. La
repetición retail posterior confirmó cast visible y reactivación del botón.

## Hallazgo dinámico de lote máximo

La aceptación posterior confirmó aperturas unitarias y lote 3, pero el botón `Max` con 300 cajas y
llaves produjo `Item use failed`. Lua y `FUN_39132010` demuestran que la ventana usa el menor stack
completo, mientras que el backend rechazaba cualquier `count > 10`. Se eliminó ese límite de debug
y se conservó el límite representacional `int.MaxValue`, además de todas las validaciones de stock,
ownership, espacio y capacidad wire por ronda. Build, 1.722 pruebas y redespliegue aislado de Game
quedaron correctos; la repetición retail con lotes 11, 20 y `Max=269` fue aceptada.

## Hallazgo dinámico multi-stack

Los lotes 11 y 20 funcionaron, mientras que `Max` 269 falló. La consulta runtime probó que las
cajas 42333 estaban divididas en 100+100+69, la llave 42335 tenía 269 y había espacio libre. Lua
usa `itemInfo["total"]` y el cliente ofrece el total agregado; no existe evidencia de un nuevo
límite retail en 269. El backend comparaba la solicitud con `Count` de la instancia source
seleccionada, pese a que la mutación ya podía recorrer múltiples pilas. El preflight ahora agrega
las pilas destruibles bajo el mismo lock, conserva la instancia seleccionada como preferida y
calcula exactamente los slots liberados. La regresión acepta 269, rechaza 270 y confirma tres
pilas vaciadas. Build completo y 1.723/1.723 pruebas pasaron. La imagen multi-stack fue desplegada
sólo en Game; Login y DB conservaron sus IDs, y Zone no fue operado. La repetición retail posterior
aceptó ese `Max`.

## Aceptación final

El usuario confirmó que `Max=269` funciona después del despliegue: consume las cajas repartidas,
entrega rewards y completa la ventana. También aceptó individualmente los packs metálicos activos
3–8 de ambas familias cobre/plata/oro. Los packs de debug/inactivos quedan excluidos; el pack 10
usa loot ordinario y el 11 no requiere llave, por lo que son casos complementarios separados.

La muestra Silver de 100 aperturas entregó 108 Superior Glow Lunarite, 3 Moonpoint y `1.123g 88s`.
Es compatible con los datos r575 cargados: media base 109,34 lunarite por 100, advanced común con
pity 20 y raro `0,0025%` desde ronda 30 con pity 300. Catálogo y probabilidades de autoridad y
runtime fueron idénticos. Loot Gacha queda cerrada sin desvío conocido.
