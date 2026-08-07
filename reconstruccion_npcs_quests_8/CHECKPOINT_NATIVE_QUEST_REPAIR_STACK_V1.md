# Checkpoint — primer stack transversal de reparación de quests AA8

Fecha: `2026-07-30`

Cliente y autoridad: ArcheAge Kakao `8.0.3.12 r558734`

Branch:

```text
client_version/8.0.3.12-kakao-r558734-port
```

## Resultado

El primer stack de fallos observados quedó implementado y desplegado sobre el
catálogo amplio que ya convivía con las quests existentes. No se reactivó el
catálogo estricto V2 ni se eliminó contenido del runtime.

Incidentes cubiertos:

```text
QF-0002  feedback inmediato de cofres selectivos
QF-0003  casteo de cadáver y duplicación de Bloodhand Glove
QF-0004  diálogo bloqueado al iniciar quest 2259
```

`QF-0001` permanece evidenciado como el incidente del catálogo estricto que
motivó el rollback. Su contención sigue siendo el runtime amplio; no se inventó
un paquete de fallo sin layout AA8 demostrado.

## Quest bloqueante 2259

La traza demostró esta secuencia:

```text
CSCompleteQuestContext quest=2258
SCQuestContextCompleted
CSStartQuestContext quest=2259
AA8QuestStartGuard:
  item=16259
  reason=missing_item_template
diálogo cliente pendiente
```

El grafo nativo existente declara:

```text
2259 The General's Orders
  AcceptNpc  -> General Govannon 3611
  SupplyItem -> General Govannon's Letter 16259 x1
  ItemGather -> General Govannon's Letter 16259 x1
  ReportNpc  -> Coast Guard Captain Baker 10582
```

Se extrajo la fila exacta de item `16259` desde `game11` mediante el loader
nativo ya reconstruido. La wiki sólo se usó como corroboración visible.

Dossiers:

```text
quest-2259.json
sha256=8F7F9578060849342CA19D30B179C829ED28D399D02E50C7F197E8FCCE824565

item-16259.json
sha256=D585FE288552A65A89050A1D6873301D0893A84B8F06A41EC8F26091690C7267
```

## Runtime incremental

Builder:

```text
build_native_quest_repair_stack_v1_runtime.py
```

Base preservada:

```text
compact-8.0-runtime-native-npc-visual-v1.sqlite3
sha256=A97D4162020F02AA579D2F95AA41B02F90302EC708E3ADD30A0156467281F5F7
```

Salida:

```text
compact-8.0-runtime-native-quest-repair-stack-v1.sqlite3
sha256=7C0100208A4846058F62377203DE48E237D332CFB77E926F90D96B5397C5DB25
bytes=140525568
```

Dos construcciones independientes produjeron el mismo SHA-256.

La única mutación de datos es:

```text
items[16259] = fila exacta game11
aaemu_item_definition_coverage[16259]
  concrete_type=generic
  coverage=complete
  missing_dependencies=""
  provenance=game11_native_items:quest2259_delivery_item
```

No se importaron filas históricas 3.0 y no se restringieron las `6628` quests
del runtime base.

## Reparaciones transversales del servidor

### Delta de items selectivos

`CSBagHandleSelectiveItemsPacket` comparaba snapshots sólo por instance ID y
cantidad. El contenedor puede consumir el cofre y reutilizar inmediatamente el
mismo ID para el arma; si la cantidad también era uno, el delta quedaba vacío.

`SelectiveItemDeltaBuilder` ahora emite:

```text
mismo ID + identidad distinta -> ItemRemove + ItemAdd
mismo ID + identidad estable  -> ItemCountUpdate cuando cambia count
ID eliminado                  -> ItemRemove
ID nuevo                       -> ItemAdd
```

La identidad incluye template, contenedor y slot. El catálogo activo contiene
`16` acciones y `122` opciones que usan esta ruta.

### Idempotencia de loot de quest

Los eventos `OnItemGather` y `OnItemUse` ya no pueden devolver una quest
`Ready` a `Progress`.

Antes de materializar un item de loot con `loot_quest_id`, el servidor comprueba
si existe una relación exacta `QuestActObjItemGather` y si todavía queda
capacidad tanto en el objetivo como en el inventario. Si la relación exacta
existe pero la quest está ausente, Ready o completa, el loot se rechaza antes
de crear el item.

Alcance analizado:

```text
838 items con loot_quest_id
197 con relación exacta QuestActObjItemGather: guard activo
641 con otra semántica: comportamiento anterior preservado
```

### Casteo e interacción AA8

Se carga `skills.casting_useable`. Una skill con valor nativo `0` rechaza una
segunda entrada mientras existe un `CastTask`, respondiendo `OnCasting` por la
ruta de rechazo AA8 ya implementada.

Para skill `41925`:

```text
casting_time=3000
casting_useable=0
casting_cancelable=0
casting_delayable=0
start_anim_id=56
```

También se implementó el `SkillObject` nativo tipo `28 (0x1C)`:

```text
byte header
UInt32 field1
UInt32 field2
byte inputDirection
```

Esto evita que el servidor trunque el objeto recibido y que la respuesta
`SCSkillStarted` devuelva al cliente un layout incompleto.

## Validación automática

SQLite:

```text
dos builds con SHA-256 idéntico
quick_check=ok
integrity_check=ok
grafo 2259 exacto
item 16259 exacto
NPC 3611 y 10582 cerrados
reward 18792 con cobertura complete
```

Pruebas:

```text
prueba Python dirigida                         6/6
suite Python NPC/quests                      58/58
pruebas .NET Core 3.1 dirigidas              58/58
suite completa AAEmu.Tests .NET Core 3.1    295/295
ScriptCompiler                                 0 errores
```

Las advertencias `NU1701` de `Ionic.Zlib` y `JitterPhysics`, y las ocho
advertencias históricas del compilador de scripts, permanecen sin cambios.

## Despliegue

Se respaldó MySQL antes del cambio:

```text
D:\Proyectos\AAemu\backups\quest-repair-stack-v1-20260730-140006\
  mysql-all.sql
sha256=CCB5745FDCAF0FF1F9C50936AA3DF5685724AB6443E718EF785C83C2691994B0
```

Imagen anterior recuperable:

```text
aaemu-game:pre-quest-repair-stack-v1-20260730-140006
sha256:3804a8da1e9d9dcd1d87a136a3172625a70e0505addb3c21aac757a3978c1d07
```

Imagen activa:

```text
aaemu-game:0.0.2.0-alpha
sha256:98ae661c1f134c625a5e7a4b46d29fa716dc19a6b04f68f1b498c3edba2a596a
```

Verificación:

```text
servicio recreado: game solamente
compact montado read-only
hash dentro del contenedor:
  7C0100208A4846058F62377203DE48E237D332CFB77E926F90D96B5397C5DB25
restart_count=0
Game 2239=abierto
Stream 2250=abierto
LoginServer=registrado
ScriptCompiler=0 errores
```

Durante el arranque apareció una excepción puntual ya fuera del stack en
`TransferManager.GetTransfers`, mientras spawneaban transfers en paralelo. El
servidor continuó, abrió ambos puertos, se registró y no reinició. Se conserva
como observación separada; no se amplió esta reparación a transfers.

## Retest manual solicitado

Probar primero el bloqueo actual:

1. Volver a interactuar con General Govannon.
2. Aceptar `The General's Orders` una sola vez.
3. Confirmar que el diálogo se cierra.
4. Confirmar exactamente una carta `16259`.
5. Confirmar que el journal apunta a Captain Baker.
6. Detenerse y reportar el resultado.

Después, en personajes/estados adecuados:

```text
QF-0002:
  confirmar un cofre 2H y uno ranged;
  verificar cierre y delta inmediato sin reabrir la bolsa.

QF-0003:
  interactuar una vez con Bloodhand Corpse;
  observar el casteo;
  intentar una segunda vez;
  verificar que sólo existe un Bloodhand Glove.
```

Las tres familias permanecen `listo_para_retest` hasta validación con el
cliente real.
