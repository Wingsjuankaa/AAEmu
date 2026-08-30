# AA10 r575 — cantidades adquiridas y descontadas en notificaciones de items

Fecha: 2026-08-30

## Síntoma

Al adquirir unidades que cabían en una pila existente, el chat mostraba el total final de la pila.
Ejemplo observado: una adquisición de 300 unidades podía aparecer como `Acquired x734` cuando 734
era el total resultante en la bolsa.

La corrección positiva fue aceptada dinámicamente por el usuario el 2026-08-29: las recolecciones ya
muestran el delta adquirido. La misma raíz seguía abierta para consumos parciales. Al colocar 40
`Chick` desde una pila que quedó en 750, el cliente mostró `Acquired: [Chick] x750` en vez de la
remoción de 40.

## Causa confirmada

`ItemCountUpdate` usa `ItemAction.Take` (acción 6) para resincronizar una pila mediante el item
completo. En el cliente Returns 10.0.2.13 r575, `FUN_398d50a0` toma el `stackSize` del snapshot como
cantidad visible de la notificación; por eso el mensaje refleja el total.

El consumer nativo de `ItemAction.Create` (acción 5) tiene semántica incremental para una pila ya
existente:

- codec `FUN_39b50ab0`: `slotType, index, itemId u64, amount s32, templateId u32`;
- apply `FUN_39b56cb0`: resuelve el slot y suma `amount` al conteo existente;
- evento `FUN_398d50a0`: publica ese mismo `amount`, no el total final.

La revisión específica del descuento cerró además la semántica signed del mismo contrato:

- `FUN_39b50ab0` decodifica `amount` como `int32` en el offset `0x10` del cuerpo de acción 5;
- `FUN_39b56cb0` suma ese valor de 32 bits al count de la pila, por lo que `-40` produce el descuento;
- `FUN_398d50a0`, caso 5, entrega el mismo `amount` signed a `FUN_398e2c40`;
- `FUN_398e2c40` acumula el delta sin perder el signo;
- `FUN_398e2ea0` separa `amount > 0`, convierte sólo la magnitud a positiva y envía el camino de UI
  positivo (`0x80`) o negativo (`0x82`). El camino negativo es el que renderiza la remoción.

Binario anclado: `x2game.dll` x86-64, SHA-256
`405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.

## Cierre implementado

Se añadió `ItemCountIncrease`, positivo y exclusivo para adquisiciones/recompensas que amplían una
pila existente. `AcquireDefaultItemEx` y los dos caminos transaccionales de recompensas lo usan.

Se añadió `ItemCountDecrease`, cuya API recibe una magnitud positiva y serializa su negativo signed
en acción 5. Los consumos parciales de `ItemContainer` —incluido `DoodadCreate`—, housing, crafting,
destroy y trade usan esta acción. Las eliminaciones completas conservan `ItemRemoveSlot` más
force-remove. Los movimientos y merges conservan `ItemCountUpdate/Take` como resincronización final,
separando esa frontera de los mensajes de economía.

## Linaje y comparación

- target: `Wingsjuankaa/AAEmu:rama_10` en `3cfa66343f2000f39c1a01b80b306ea85688d403`;
- padre consultado: `upstream/client_version/zone-10.0.2_r575` en
  `3cc280b14d7da0d874121d14ebbf409f5e032d1c`;
- AA8 consultado sólo como lead estructural en
  `96a21119e1926e69648f000f2e9f1436788ede51`; su acción incremental fue promovida únicamente tras
  corroborar codec, apply y evento en el binario AA10 exacto.

## Despliegue local

Desplegado el 2026-08-30 recreando únicamente el servicio Docker `game`; `db` y `login`
permanecieron activos. La imagen resultante es
`sha256:6a612dc58a601de0c0f3cba740ab3fedbf058a8e46f2f65fbd6b31f86a7b4396` y el
`AAEmu.Game.dll` montado en World tiene SHA-256
`52264BBBCA7586D91C048405D5E107575D4773A00981A614A67FBDA12CB19376`. Ambas copias del
ensamblado dentro del contenedor son idénticas y contienen `ItemCountIncrease` e
`ItemCountDecrease`.

El gate de runtime cerró con `game` saludable, `RestartCount=0`, Game `1239` y Stream `1250`
escuchando, `Server started!` y una conexión establecida/registrada contra Login `1234`.

La Zone `w_solzreed_1` que estaba activa antes de recrear World perdió la conexión y terminó. No se
relanzó porque la autorización de despliegue no incluye lifecycle de Zones; debe iniciarse desde el
AAEmu Control Center antes de la aceptación en cliente. La imagen anterior
`sha256:a0c950dc5f977e52a010ce79fa000dd0ac1826f4ffe7c524e5ec42554c5501d3` queda identificada
como rollback.

El descuento fue aceptado dinámicamente por el usuario el 2026-08-30 con el cliente retail r575.

## Aceptación dinámica

La adquisición positiva y el descuento fueron aceptados por el usuario. El caso de granja confirmó
que la pila conserva su total real y el chat muestra la magnitud retirada, sin volver a presentar el
total restante como una adquisición. Los criterios cerrados fueron:

1. una pila de 790 `Chick` que consume 40 queda en 750;
2. el chat muestra `Removed: [Chick] x40`, nunca `Acquired x750`;
3. los consumos aplican el delta exacto, sin duplicarlo ni ignorarlo;
4. el arreglo no altera la cantidad persistida del item.

## Validación local

- `dotnet restore`: correcto; sólo advisories NuGet ya presentes.
- `dotnet build --configuration Release --no-restore`: correcto, 0 errores.
- `ItemUpdateWireTests`: 3/3 correctas; fija total 734/delta `+300` y total 750/delta `-40`.
- `CraftItemExchangeTests`: 16/16 correctas; confirma que una recompensa sobre pila existente usa
  `ItemCountIncrease` y un consumo parcial usa `ItemCountDecrease`.
- `ItemContainerCommittedTaskPacketTests`: 3/3 correctas; conserva el framing independiente de
  consumos multi-stack.
- suite completa: 1.669/1.670 correctas. El único fallo fue el test ajeno `MailTests.MoneyTest`
  (`UnableToFindRecipient`) por interferencia de singletons al correr toda la suite; la clase
  `MailTests` aislada pasó 2/2. No hay fallo de inventario, loot ni serialización.
