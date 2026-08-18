# Reconstrucción AA10 — engemado Lunagem r575

Fecha: 2026-08-15

Target: `Wingsjuankaa/AAEmu:rama_10`

Cliente: ArcheAge Returns `10.0.2.13 r575`

## Estado

Se reconstruyó y validó manualmente el flujo de instalación de Lunagem desde
**Gear Upgrade > Lunagem**. La operación completa casteo, consume reactivo/coste, persiste el socket,
actualiza bonuses, refresca el arma de la bolsa y actualiza inmediatamente la lista del target que ya
está seleccionado. El botón **Confirm** queda habilitado para instalar la siguiente gema sin pulsar
**Equip**, cerrar la ventana ni reloguear.

No se habilitó todavía el cambio, reemplazo o extracción de Lunagem. Su protocolo y transacción
nativos permanecen cerrados; no se extrapolaron desde AA8.

## Checkpoint manual estable — 2026-08-15

La prueba manual final fija este estado como frontera funcional y de regresión:

- casteo completo y sonido;
- instalación efectiva de una Lunagem;
- cobro y descuento inmediato del reactivo;
- persistencia después de reloguear;
- aplicación de estadísticas y actualización correcta del tooltip vivo;
- toast de éxito;
- refresh inmediato de la lista de sockets del panel y continuidad de **Confirm**;
- serialización nativa `UpdateDetail` mediante la unión interna r575 de 128 bytes, sin iconos negros
  ni corrupción del item.

Guardas de este checkpoint: no reemplazar la unión interna de 128 bytes por el detalle compacto, no
cambiar el cuerpo del `SkillObject` tipo 10 y no alterar las reglas, probabilidades o slots para
intentar corregir el frame. Conservar la secuencia y tipos finales descritos en la transacción.

## Síntoma original

La ventana aceptaba el equipo y la Lunagem, mostraba el efecto y el coste, consumía labor, pero no
terminaba la instalación. El comportamiento coincidía superficialmente con el bug que se había
reparado en AA8, aunque AA10 necesitaba cierres propios de protocolo, persistencia y datos.

## Revisión comunitaria previa

Antes de portar código se revisaron los PR del padre `AAEmu/AAEmu`, incluidos abiertos, cerrados y
fusionados. No existe un PR para `client_version/zone-10.0.2_r575` que reconstruya el flujo completo.

- `#1468` sólo añade una guarda antigua para equipo lleno.
- `#1199` separa Dawnstone en una versión anterior.
- `#1245` corrige cantidades de Evenstone; no corresponde a Lunagem.
- `#1528` mejora un fallback genérico de reagentes, pero no implementa el contexto 10 ni el wire r575.

AA8 se usó como comparador selectivo para el orden de validación y transacción. Ningún offset,
estructura persistida, opcode o dato se importó como autoridad automática.

## Causas verificadas

### 1. `CSStartSkill` dejaba seis bytes sin leer

El cliente envía `SkillObject` tipo 10 con este cuerpo:

```text
bool autoUseAaPoint
u32  count
bool continuous
```

El cast observado para una instalación normal llevaba `01 00000000 00`; `count=0` representa una
instalación individual. Como rama_10 no conocía el tipo 10, el efecto recibía un objeto genérico y
quedaban seis bytes sin consumir antes de `inputDirection`.

Se añadió el tipo 10 a `SkillObject`, con lectura/escritura explícita y pruebas de alineación.

### 2. El servidor escribía en estado que AA10 nunca serializa

El código anterior guardaba IDs en `EquipItem.GemIds`, un arreglo local de siete posiciones que no
formaba parte del detalle de item r575. El cliente y MySQL sólo reciben/persisten el bloque PISC
`GemData` de 18 valores.

La decompilación de `x2game.dll` SHA-256
`2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76`, función
`FUN_39792770` (`VA 0x39792770`), confirma `gemInfo` y nueve entradas consecutivas de `socketInfo`.
La disposición reconstruida queda así:

| Índices PISC | Uso r575 |
|---|---|
| `0` | apariencia del item |
| `3` | EXP de synthesis |
| `4..12` | nueve Lunagem |
| `13..17` | cinco efectos de synthesis |

`EquipItem` ahora expone y ensucia correctamente esos nueve slots. Los bonuses de `Unit` y `Slave`
también leen esa fuente persistente.

### 3. Se enviaban respuestas antiguas

El flujo viejo usaba `SCItemSocketingLunagemResultPacket` `0x9D` y un `ItemUpdate` con framing
incorrecto. La función nativa `FUN_39a9c530` (`RVA 0xA9C530`) confirma que el paquete moderno
`SCItemSocketingResultPacket` `0xCA` tiene exactamente este cuerpo de 15 bytes:

```text
u8   result
u64  itemId
u32  lunagemTemplateId
u8   operation
bool processed
```

El byte que parecía preceder a `result` en el objeto C++ pertenece a metadata del paquete base y no al
cuerpo serializado.

La prueba manual posterior permitió cerrar también el `UpdateDetail` de `SCItemTaskSuccessPacket`
`0xBC`. En el cliente exacto r575, `FUN_39b55c50` deriva la acción 10 a `FUN_39b50d60`, que serializa:

```text
u8   slotType
u8   slotIndex
u64  itemId
u16  byteLength = 128
byte detail[128]
```

La bifurcación de lectura de `FUN_39b50d60` ocultaba inicialmente el framing del escritor: el array usa
el contrato byte-array con `u16 128`. El fallo real estaba dentro del array. `FUN_39b57130` copia sus
128 bytes literalmente a `item + 0x20`, mientras `FUN_39a3ccd0` demuestra que el detalle de equipo
interno no es el snapshot compacto: distribuye los 18 valores PISC en `+0x01`, `+0x08`, `+0x14`,
`+0x40`, `+0x18..0x38` y `+0x44..0x54`, además de los campos escalares. Enviar el detalle compacto en
esa acción reemplazaba el target por un icono negro/inválido. `ItemUpdate` ahora construye la unión
interna exacta antes de refrescar la copia seleccionada que conserva Gear Upgrade.

### 4. Las reglas se reducían a la primera fila de probabilidades

Ahora `ItemManager` carga las tablas r575 completas:

- `item_sockets`;
- `item_socket_chances`;
- `item_socket_num_limits`;
- `item_socket_level_limits`;
- `equip_slot_group_maps`.

La validación comprueba target explícito, grupo de slots, nivel, cantidad máxima por slot/grado,
perfil de éxito y criterios todavía no resueltos. Los criterios `eiset`/tag no implementados fallan
cerrados; no amplían silenciosamente la compatibilidad.

En r575 `socket0` es un centinela. La primera instalación usa `socket1` y la novena `socket9`. La base
completa contiene ocho perfiles. El `compact` desplegado ya fue validado con esos valores y
`PRAGMA quick_check=ok`; el script `Scripts/PatchAa10SocketChances.py` permite auditar otro compact o
restaurar únicamente el estado conocido donde las diez probabilidades vienen en cero:

```powershell
python Scripts\PatchAa10SocketChances.py `
  .server_files\AAEmu.Game\Data\compact.sqlite3

python Scripts\PatchAa10SocketChances.py `
  .server_files\AAEmu.Game\Data\compact.sqlite3 --apply
```

El script rechaza perfiles parciales o metadata distinta y ejecuta la modificación en una transacción.

### 5. El tipo de tarea no abría el gate de refresh de AA10

La transacción llegaba correctamente a `SCItemSocketingResult` (`0xCA`), pero el panel permanecía una
operación atrás. Se instrumentaron temporalmente el Lua del cliente y el servidor con mensajes
correlacionados `[SocketDiag:C/W/S]`. La traza probó que el resultado, la mutación y el
`ItemUpdate` sí llegaban; faltaba un segundo evento aceptado por el controlador nativo.

El consumer `ItemSocketInsert` registra el evento interno `0x21`. Su callback sólo acepta
`ItemEventParam.taskType == 0x2A` (42), compara el template del item afectado con el target
seleccionado y abre un flag. El handler de `0xCA` abre el otro lado del gate mediante el evento
`0x5A`; el refresh se ejecuta cuando ambos lados han ocurrido, independientemente de su orden.

`ItemTaskType.Socketing` (99) aplicaba correctamente las acciones de bolsa, pero el callback lo
ignoraba y nunca habilitaba el refresh. La transacción final usa
`ItemTaskType.SkillEffectGainItem` (42). AA8 conserva 99 en su flujo funcional, por lo que esta
diferencia queda clasificada como `version_sensitive_blocked`: no copiar el valor entre versiones.

## Transacción reconstruida

La instalación:

1. valida equipo, Lunagem, grupo, nivel, slots, perfil, cantidad y coste antes de pagar;
2. interpreta `count=0` como una unidad y acepta cantidad múltiple sólo si todas son 100 % seguras;
3. calcula cada coste con `FormulaKind.ItemSocketingCost` (fórmula 38) y `cost_ratio`;
4. preautoriza y cobra oro o AA Point dentro de la misma transacción visual de socketing;
5. consume la cantidad exacta del template en el bolso mediante el helper atómico multi-stack, sin
   publicar una transacción intermedia;
6. restaura el detalle y reembolsa el coste si el consumo excepcionalmente no puede comprometerse;
7. persiste `GemData[4..12]`, actualiza bonuses si el item está equipado y publica la secuencia
   validada `0xBC ItemTaskSuccess(SkillEffectGainItem/42, [UpdateDetail, wallet, reagent])` →
   `0xBE ItemDetailUpdated` → `0xCA SocketingResult`.

Una falla probabilística legítima consume el reactivo/coste. Si el perfil tiene `fail_break=true`,
elimina las Lunagem instaladas como indican los datos; los perfiles directos v2 usados por Splendid
son seguros y no rompen sockets. Las probabilidades ausentes o en cero nunca se convierten en 100 %.

## Archivos principales

- `AAEmu.Game/Models/Game/Skills/SkillObject.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/ItemSocketing.cs`
- `AAEmu.Game/Models/Game/Items/EquipItem.cs`
- `AAEmu.Game/Models/Game/Items/Services/ItemSocketRuleService.cs`
- `AAEmu.Game/Core/Managers/ItemManager.cs`
- `AAEmu.Game/Core/Packets/G2C/SCItemSocketingResultPacket.cs`
- `AAEmu.Game/Models/Game/Units/Unit.cs`
- `AAEmu.Game/Models/Game/Units/Slave.cs`
- `Scripts/PatchAa10SocketChances.py`
- pruebas nuevas bajo `AAEmu.UnitTests/Game`.

## Validación automática

```powershell
dotnet build AAEmu.Game\AAEmu.Game.csproj --configuration Release --no-restore
dotnet build AAEmu.UnitTests\AAEmu.UnitTests.csproj --configuration Release --no-restore
dotnet test AAEmu.UnitTests\AAEmu.UnitTests.csproj `
  --configuration Release --no-build --no-restore -- `
  --no-ansi --no-progress --maximum-parallel-tests 4
```

Resultado: **1273 pruebas correctas, 0 errores, 0 omitidas**. También pasó `git diff --check` y el
validador del compact no realizó cambios: sus ocho perfiles ya coinciden con la evidencia AA10.

## Prueba manual completada

En el despliegue controlado se verificó:

1. Lunagem compatible sobre equipo compatible, incluida Splendid Fireglow template `43500`;
2. descuento inmediato de una unidad y del coste indicado;
3. socket, efecto y tooltip correctos sin cerrar Gear Upgrade;
4. refresh inmediato de la lista del panel y siguiente **Confirm** disponible;
5. casteo, sonido, toast y persistencia después de relog;
6. decremento correcto de stacks y ausencia de corrupción/iconos negros.

No se debe probar reemplazo/extracción en este checkpoint. Tampoco hay que mezclar compact, IDs ni
implementaciones Kakao/AA8 con el runtime r575.

## Corrección posterior: casteo y refresh del panel

La primera prueba manual confirmó que la Lunagem se instalaba, persistía y aparecía en el tooltip,
pero reveló dos cierres incompletos:

1. `SCSkillStarted` anunciaba SkillObject tipo 10 sin escribir su cuerpo de seis bytes. El cliente
   consumía los tiempos/tail como opciones de socketing y descartaba la línea de casteo. Se añadió
   al escritor SC el eco exacto `bool autoUseAaPoint, u32 count, bool continuous` antes de
   `inputDirection`.
2. `0xBE + 0xCA` actualizaba el item vivo y mostraba el toast, pero no invalidaba el target cacheado por
   X2ItemEnchant. Las primeras pruebas de `ItemTaskType.Socketing/UpdateDetail` con el detalle compacto,
   con y sin prefijo, convirtieron el target en un icono negro. `FUN_39b57130` y `FUN_39a3ccd0`
   identificaron la causa: la acción requiere una unión interna fija de 128 bytes, no el body compacto
   de `SCItemDetailUpdated`. Se implementó ese mapa y se restauró la secuencia `0xBC` → `0xCA`.

La forma del SkillObject queda cubierta por una prueba de ocho bytes (flag, cuerpo e
`inputDirection`) y la prueba manual confirmó el casteo de tres segundos. El `UpdateDetail` queda
cubierto por una prueba de 142 bytes que verifica el prefijo y todos los offsets escalares/PISC de la
unión interna.

### Experimento AA8 rechazado y rollback

La comparación selectiva con rama_8 sugirió agrupar wallet, reactivo y `UpdateDetail` en un solo
`ItemTaskSuccess(Socketing)`. La prueba manual AA10 demostró que esa forma **no es compatible con
r575**: el cuerpo `Take` usado para reducir el stack quedó delante de `UpdateDetail` y el cliente dejó
de aplicar también el refresh del arma en inventario, mientras la ventana seguía sin actualizarse.

Ese candidato se retiró íntegramente. La agrupación de rama_8 queda clasificada
`version_sensitive_blocked` y no debe reintroducirse. Una prueba manual posterior demostró además que
volver sólo a `UpdateDetail` no bastaba para fijar establemente el refresh del inventario: el arma
volvió a quedar una operación atrás. Por tanto, esa recuperación no se considera un checkpoint
confirmado.

### Candidato `0x9D` rechazado y pista manual de `Equip`

La reconstrucción posterior del cliente exacto confirmó que r575 conserva dos vistas durante el
engemado:

- `SCItemTaskSuccess/UpdateDetail` (`0xBC`) aplica la unión interna de 128 bytes mediante
  `FUN_39b57130` y alimenta el change-set normal;
- `SCItemDetailUpdated` (`0xBE`) publica el detalle compacto al item vivo de la bolsa;
- `SCItemSocketingResult` (`0xCA`) entra por `FUN_39344150` y eleva el evento interno `0x5A`, usado
  por el resultado/casteo;
- `SCItemSocketingLunagemResult` (`0x9D`) entra por `FUN_39344330` y eleva `0x5B`, pero ese evento
  pertenece a `ItemGemEnchant`, no al modo activo `ItemSocketInsert`.

La prueba manual de `0xBC` → `0xBE` → `0xCA` → `0x9D` no refrescó el frame. El paquete `0x9D` se
retiró para no duplicar resultados ni contaminar otro modo. El usuario confirmó dos veces que pulsar
la subpestaña **Equip** refresca inmediatamente la lista correcta. El Lua exacto muestra que ese clic
ejecuta `SwitchItemEnchantSocketInsertMode()`, `ResetSubTabLayout(index)` y `SlotAllUpdate(false)`.
Esto demuestra que el item vivo está correcto y que el defecto restante es el snapshot del modo.

La reparación estable AA8 ya documentaba el mismo cache atrasado cuando wallet, reactivo y target se
publican como transacciones `Socketing` separadas. El primer intento de agruparlos en AA10 colocó el
`Take` variable antes de `UpdateDetail`; r575 dejó de interpretar las acciones posteriores y también
perdió el refresh de bolsa. El lote final coloca `UpdateDetail` como **primera** acción, conserva
`0xBE` para la vista viva y deja `0xCA` como único resultado. Aun así, el refresh no quedó cerrado
hasta identificar el gate de tipo de tarea: el mismo lote debe publicarse como tipo 42. La prueba
manual confirmó simultáneamente el refresh de bolsa y frame sin pulsar **Equip**.

### Instrumentación temporal y limpieza

Cuando el análisis estático acotó el fallo pero no resolvió el orden de callbacks, se añadieron probes
temporales al cliente y al servidor. Los mensajes mostraron flags del controlador, entrada/salida de
`SlotAllUpdate`, comienzo/fin de casteo, tipo y orden de las acciones, `0xBE` y `0xCA`. Esa correlación
permitió separar “estado correcto” de “gate de UI nunca abierto” y localizar el chequeo 42.

Tras validar el arreglo se retiraron los mensajes y flags del servidor y se restauraron los ALB
originales desde `E:\AAEmu\rama_10\backups\ui-and-client\test-backups\aa10-r575-socket-diag-20260815`. Los hashes
SHA-256 esperados son:

- `enchant_window.alb`: `EB579BCB889A987499D44506C315DE0250209CA54273C25F4BFD68537691CACD`;
- `socket_enchant.alb`: `033165F4F9A47C094153C8F0E23CB477FE63137AE5E9FC355F1DB3351B20C474`.

La metodología queda incorporada a `aaemu10-native-reconstruction`: instrumentar dinámicamente sólo
ante un lifecycle no cerrado, correlacionar ambos extremos, preservar respaldos con hash y retirar
todos los probes antes del commit.
