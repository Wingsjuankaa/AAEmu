# Reconstrucción de Loot Gacha AA10 r575

Fecha: 2026-09-03
Clasificación: reconstrucción de mecánica retail/post-lanzamiento; no es mecánica nueva.

## Autoridad y evidencia nativa

- Datos r575: 11 filas en `gacha_loot_packs`, 24 asociaciones de caja/llave en
  `gacha_loot_pack_items` y 30 premios avanzados en `gacha_advanced_loot_packs`.
- La base compact montada contiene las tres tablas completas. El loader exige exactamente
  11/24/30 y aborta el arranque ante un catálogo incompleto; no existe fallback inventado.
- Lua `x2ui/inventory/loot_gacha.lua`: selección separada de source/consume, ejecución por lote,
  contador restante, cancelación y eventos `GACHA_LOOT_PACK_RESULT`/`LOG`.
- `x2game.dll` r575:
  - `FUN_391ab070` expone `Execute(count)`;
  - `FUN_39132200` conserva el lote y solicita la operación;
  - `FUN_398da340` construye `SkillCaster` item, `SkillCastTarget` item y `SkillObject` tipo 16 con
    un único `u32 count`;
  - `FUN_39132010` calcula el máximo como el menor stock total disponible para los templates
    source/consume; Lua presenta `itemInfo["total"]`, no el tamaño de una instancia;
  - el comando nativo de diagnóstico limita su propio argumento a 1-10, pero la ventana retail
    usa `GetMaxLootCount()` y admite el menor stack completo; ese límite de debug no pertenece al
    gameplay.
- Wire S2C confirmado en serializers/consumers nativos:
  - `0x2E2 SCGachaLootPackItemLogPacket`: `count:u8` y filas
    `itemType:u32 + itemGrade:u8 + stack:i32`;
  - `0x2E3 SCGachaLootPackItemResultPacket`: `error:i16`; en éxito,
    `leftCount:u32 + itemCount:u32 + finish:bool + Item[itemCount]`, máximo 15;
  - `0x2E4 SCDumpGachaRecordPacket`: `count:u32 + glpId:u32 + totalCount:u32` y hasta diez pares
    `galpId:u32 + lastRound:u32`.

La documentación externa sólo se usa como corroboración de intención. Las guías históricas de
Metallic Boxes describen cajas selladas abiertas con llaves de cobre/plata, y la base de items
documenta llaves cuyo consumo depende de la caja. No reemplazan los IDs, tasas ni fórmulas r575:
[ArcheRage 3.0 loot update](https://na.archerage.to/forums/threads/3-0-updates-loot-weapons-armor.4908/),
[Golden Key](https://wiki.archerage.to/na-en/db/items/52541).

## Contrato implementado

1. El uso ordinario de la caja sólo abre la ventana; la segunda invocación, con objeto tipo 16,
   ejecuta el lote autoritativo.
2. Se aceptan entre 1 y el menor stock total de caja/llave presentado por la UI. La instancia
   seleccionada autentica owner, bolsa y template; la disponibilidad y el consumo abarcan todas
   las pilas elegibles del mismo template, comenzando por la seleccionada. Pack, caja, llave y
   cantidades se revalidan bajo el monitor del inventario. El límite técnico superior es
   `int.MaxValue`, representación del contador servidor.
3. Se consume exactamente una caja y una llave por apertura. Un objeto Item Lock falla con
   `ItemSecureCondition`; no se sustituye silenciosamente por otro stack.
4. Todos los loot packs se generan sin multiplicadores de drop/gold del personaje o del mundo.
5. Los premios avanzados usan el registro retail: `add_round` bloquea el premio hasta el mínimo de
   rondas desde su última entrega; `give_term` lo fuerza al llegar al pity; `rate` usa escala
   10.000.000 y se evalúa prioridad numérica ascendente. Como máximo se entrega un pack avanzado
   por ronda, además del pack base.
6. Antes de consumir se generan y agregan los resultados, se valida el máximo wire de 15 items y se
   simula espacio considerando los slots liberados por caja/llave.
7. Se publican las tareas de consumo/adquisición y un par Log/Result por ronda. `leftCount` es el
   número de aperturas pendientes del lote y desciende `N-1 ... 0`; no es el stock disponible.
8. `total_count` y el `last_round` de cada premio avanzado viven por personaje y se guardan en la
   misma transacción de autosave que personaje e items.

## Negativos y límites

- Rechaza count 0, valores fuera de la representación del inventario, feature apagado, pack
  inactivo, combinación caja/llave inválida, instancias ajenas u obsoletas, cantidad insuficiente,
  item lockeado, pack ausente y bolsa llena.
- No intercepta items que abren un `GainLootPackItemEffect` ordinario aunque aparezcan en datos
  históricos de Gacha; sólo actúa sobre `GainGachaLootPackItem` y tipo 16.
- Los requests se serializan mediante la sincronización de skill/inventario existente. El wire no
  incluye nonce, por lo que la garantía verificable es una transacción por cast aceptado y consumo
  exacto; no se afirma idempotencia frente a una retransmisión fabricada con recursos nuevos.

## Validación

- Build completo `AAEmu.slnx`: 0 errores.
- Suite unitaria final, recompilada después de la corrección multi-stack: 1.723/1.723,
  0 fallos y 0 omitidas.
- Fixtures nuevas: tipo 16, Log, Result éxito/error y Dump record.
- Calculador: prioridad, cooldown `add_round`, tasa y reinicio de pity por `last_round`.
- Catálogo canónico: 11/24/30 y asociación activa `42333 + 42335 -> pack 3`.
- Migración runtime aplicada: `character_gacha_records` y
  `character_gacha_advanced_records`, ambas inicialmente vacías.
- Imagen con `Max` multi-stack corregido desplegada sólo en Game:
  `sha256:251f07433478e1cb6abdc89d0c1e5b2c3514559ead66d2c64daa7c112cbc3c46`.
- Rollback inmediato anterior a la corrección multi-stack:
  `aaemu-world:rollback-pre-gacha-multistack-fix-20260903-082033`
  (`sha256:6c595e547f3ab41a489f63a179a837a950d5e47227015632a3949b52ed57e306`).
  Se conserva además `aaemu-world:rollback-pre-gacha-max-fix-20260903-075957`.
  Se conserva además `aaemu-world:rollback-pre-gacha-ui-fix-20260903-074333`.
  Se conserva además el rollback pre-mecánica
  `aaemu-world:rollback-pre-loot-gacha-20260903-072217`.
- Arranque corregido: Game healthy, reinicios 0, `Server started!` en `00:01:21.5456964`,
  catálogo cargado, `lootGacha` presente en Features/fset y GameServer registrado en Login.
- Login y DB no fueron recreados. Zone no fue iniciado, detenido ni relanzado por Codex.
- Aceptación retail completada: cast, reactivación de Confirm, lotes grandes/multi-stack, seis
  asociaciones metálicas y persistencia visible confirmados por el usuario.

### Corrección dinámica 2026-09-03

La primera prueba retail entregó correctamente el premio y consumió 1+1, pero dejó `Confirm`
deshabilitado y el spinner en 9. El log probó el timeline completo de skill 32270, con cast nativo
de 500 ms, `SkillStarted`, `SkillFired`, Result y `SkillEnded`. La causa fue devolver como
`leftCount` el stock restante (9). El consumer nativo conserva ese campo como trabajo pendiente y
vuelve a entrar en `IsWorkingLoot`; para una apertura debe recibir 0. La implementación ahora emite
un Log/Result por ronda con countdown hasta cero, de modo que el evento
`UPDATE_GACHA_LOOT_MODE` vuelve a habilitar el botón al terminar.

La corrección se desplegó en Game y superó nuevamente build completo y suite. Queda como único
gate la repetición retail: visibilidad del cast nativo y salida del estado de trabajo al recibir
`leftCount=0`.

### Corrección dinámica de lotes grandes 2026-09-03

La segunda prueba retail confirmó el lote corto y la reactivación de la UI, pero `Max` con stacks
de 300 devolvió `Item use failed`. El log mostró skill 32270 aceptada por el pipeline sin entrada al
commit Gacha. La causa era el límite servidor provisional de 10, derivado erróneamente del comando
de diagnóstico. Lua fija el spinner en `GetMaxLootCount()` y el consumer nativo calcula ese valor
como el menor stack disponible. Se retiró el límite de debug; owner, instancias, stock, espacio y
capacidad por resultado siguen validándose antes de mutar.

La corrección superó build completo, 1.722 pruebas y despliegue aislado de Game. El nuevo runtime
cargó Loot Gacha, publicó el feature/fset y se registró en Login; queda repetir `Max` en retail.

### Corrección dinámica multi-stack de `Max` 2026-09-03

La tercera prueba confirmó lotes 11 y 20, pero `Max` con 269 falló. No apareció un límite retail:
el inventario tenía 269 cajas repartidas como 100+100+69, 269 llaves en una pila y suficiente
espacio. Lua muestra `itemInfo["total"]` para source y consume, por lo que el 269 visible y el
resultado de `GetMaxLootCount()` representan stock agregado por template.

El backend revalidaba erróneamente `source.Count >= requestedCount` sobre la única instancia
seleccionada, aunque `ItemContainer.ConsumeItem` ya soportaba consumir la pila preferida y luego
las demás pilas coincidentes. El preflight ahora replica ese orden, suma exclusivamente pilas
destruibles bajo el lock de inventario y calcula cuántas se vaciarán para la simulación de espacio.
Si existe stock nominal suficiente pero parte está protegida por Item Lock, falla cerrado con
`ItemSecureCondition`; si el total real es insuficiente, devuelve `NotEnoughRequiredItem`.

La regresión automatizada reproduce 100+100+69: 269 es válido, 270 no, y el cálculo de slots
liberados es exacto. Build completo y 1.723/1.723 pruebas quedaron correctos. La imagen
`sha256:251f07433478e1cb6abdc89d0c1e5b2c3514559ead66d2c64daa7c112cbc3c46` fue desplegada sólo en
Game; arrancó healthy sin reinicios, cargó Loot Gacha, publicó el feature y se registró en Login.
La aceptación retail del usuario confirmó después que `Max=269` consume correctamente las pilas
100+100+69, entrega los premios y finaliza la UI. El gate multi-stack queda cerrado.

### Gate final de catálogo por tiers

El usuario recorrió y aceptó por separado las seis asociaciones metálicas activas de los packs
3–8, que forman dos familias cobre/plata/oro. Cada tier abrió con su llave y entregó su reward. Los
packs internos `gachatest*` no forman parte del gate retail: 53736 usa `GainLootPackItemEffect`
ordinario y 54461 es Gacha activo sin llave, por lo que continúan clasificados como casos
complementarios y no como tiers metálicos.

Como auditoría estadística final, 100 aperturas Silver produjeron 108 Superior Glow Lunarite,
3 Moonpoint y `1.123g 88s`. Los datos AA10 seleccionados por el runtime coinciden exactamente con
la autoridad: la esperanza del pack base es 109,34 lunarite por 100, el advanced común se fuerza
cada 20 rondas y el raro tiene tasa `0,0025%` desde ronda 30 con `give_term=300`. La muestra queda
dentro de lo esperado y no muestra pérdida de loot ni una tasa servidor reducida. El resultado
Gold observado también fue coherente con su pack. Con esto Loot Gacha queda `ACEPTADA Y CERRADA`.

## Prueba retail propuesta

Con cuenta GM, crear cajas y llaves compatibles, incluyendo cajas repartidas en varias pilas:

```text
/item add self 42333 269
/item add self 42335 269
```

Pulsar `Max` y verificar que consume las pilas 100+100+69 y 269 llaves, que `Opened Boxes` llega a
269, que la lista conserva sólo los últimos 20 resultados y que Confirm vuelve a activarse. Luego
reloguear y confirmar que premios e inventario persisten. También intentar caja sin llave, bolsa
llena y caja lockeada; ninguna debe consumirse.
