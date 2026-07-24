# Fase B7 — Temper nativo AA8

Esta fase reconstruye el sistema de Temper con datos confirmados de
ArcheAge 8.0.3.12. La compact 3.0 no aporta filas, probabilidades, costos ni
comportamiento al runtime.

## Fuentes de verdad

1. `compact-client-8.0-decrypted.sqlite`.
2. Resultados nativos recuperados desde `game11`.
3. Layouts y comportamiento identificados en `x2game.dll`.
4. Protocolo observado con el cliente local.

Los extractores y generadores de esta carpeta conservan la procedencia y los
rangos binarios usados para reconstruir cada tabla.

## Catálogo nativo

Los cuatro catalizadores habilitados son:

| Item | Skill | Tipo | Resultado especial |
| ---: | ---: | --- | ---: |
| 45914 | 37723 | Sunlight Temper | 31190 |
| 45915 | 37724 | Moonlight Temper | 31191 |
| 45916 | 39267 | Shining Sunlight Temper | 36581 |
| 45917 | 39268 | Shining Moonlight Temper | 36582 |

La operación especial utilizada por AA8 es
`SpecialEffectType.ItemRefurbishment = 126`.

La reconstrucción incluye:

- 31 niveles de `enchant_scale_ratios`;
- 37 restricciones de `item_cap_scale_forbids`;
- 21 costos por ranura de equipamiento;
- las 70 fórmulas nativas AA8 (`2..72`, sin `46`);
- las cuatro cadenas `skill → skill_effect → effect → special_effect`;
- soportes opcionales y sus límites de escala.

## Semántica confirmada

`Item.ScaledA` identifica el descriptor de escala. AA8 utiliza los descriptores
`1..30`; el descriptor `31` es el centinela global. Un equipamiento nuevo que
admita Temper comienza en `1`. Las instancias históricas con valor `0` se
normalizan a `1` al cargarse y se marcan para persistencia.

La escala del descriptor se expresa en milésimas:

```text
multiplicador = 1 + scale / 1000
```

Por ejemplo, `scale=10` equivale a +1%, `scale=100` a +10% y `scale=250` a
+25%.

Las probabilidades se calculan en base 10.000 y reproducen el orden de
conversión y truncado de `x2game.dll`:

1. aplicar el soporte opcional;
2. calcular Great Success como una fracción absoluta de Success;
3. convertir Break, Disable y Downgrade desde la fracción de Failure;
4. asignar el resto a Fail;
5. resolver un único lanzamiento acumulativo.

Los datos AA8 activos no contienen probabilidad de rotura ni deshabilitación.
Si una futura fila incorpora uno de esos resultados, el servidor la rechaza
hasta confirmar su mutación exacta.

El costo usa la fórmula nativa `59`:

```text
(if_negative(equip_slot_enchant_cost - 10, 3/7, 1)
 * ((item_level * 0.37)^2.5
 * scale_cost^3.9
 * (equip_slot_enchant_cost * 0.0002)
 + 80000))
 * (1000 + enchant_scale_cost_mul) / 1000
```

El cliente redondea los resultados positivos sumando `0.5` antes de truncar.

## Transacción y protocolo

Antes de mutar se validan:

- propietario, objeto y contenedor;
- catalizador y soporte;
- tipo de destino (arma o armadura);
- límite de escala;
- restricciones AA8;
- moneda y costo;
- cobertura completa del catálogo.

Después se descuentan moneda y soporte, se aplica el resultado, se persiste
`ScaledA`, se sincroniza el equipamiento si corresponde y se envía
`SCItemRefurbishmentResultPacket` (`0x0B1`):

- `x2game.dll` `FUN_399a1d90` confirma el layout de red exacto:
  `byte result + ItemLink + uint32 reservado + uint16 beforeScale + uint16 afterScale`.
- `FUN_39302650` transforma ese paquete en
  `ITEM_REFURBISHMENT_RESULT(result, itemLink, beforeScale, afterScale)` y no
  consume el `uint32` intermedio.
- El campo reservado se transmite como `0`; no contiene una regla de gameplay.

```text
byte result
item/link
uint32 reserved
uint16 beforeScale
uint16 afterScale
```

El catalizador principal lo consume una sola vez el flujo genérico de Skill,
porque las cuatro filas nativas tienen `consume_source_item = 1`.

## Artefacto generado

```text
compact-8.0-runtime-native-equipment-phase-b7-temper-v1.sqlite3
SHA-256:
2B0A147AE1DBFA866FEF18A5CE92F4027BDB0D1173DA54D1531F9254F73B3D25
```

El generador construye el archivo dos veces y exige hashes idénticos. Además
valida `quick_check`, `integrity_check`, las cantidades de filas y la ausencia
de procedencia histórica dentro del dominio de combate.

## Prueba manual

Con un personaje GM:

```text
/item8 info 45914
/item8 info 45915
/item8 info 45916
/item8 info 45917
/additem 45914 10
/additem 45915 10
/additem 45916 10
/additem 45917 10
```

Se debe probar por separado:

1. arma con Sunlight Temper;
2. armadura con Moonlight Temper;
3. sus variantes Shining;
4. intento con tipo incorrecto;
5. objeto en su nivel máximo;
6. operación con dinero insuficiente;
7. repetición y relog.

En cada éxito o descenso, el nivel y las estadísticas deben cambiar
inmediatamente y conservarse después del relog. Un intento inválido no debe
consumir catalizador, soporte, dinero ni labor.

## Incidente de sincronización inmediata

La primera prueba exitosa persistía correctamente el nuevo nivel de Temper,
pero el objeto mostraba un icono inválido hasta relog. La causa no estaba en
la fórmula ni en MySQL: la acción AA8 `ItemAction.UpdateDetail = 10` consume
directamente este wire:

```text
byte action
byte log
byte slotType
byte slot
uint64 itemId
uint16 detailLength = 128
byte detail[128]
```

`x2game.dll`, función `FUN_39a502f0`, llama al método genérico
`ReadBytes("detail", ..., 0x80)`. Su pareja de escritura es `WriteBytes`; ambas
rutas serializan primero la longitud de 16 bits y después el contenido. El
`0x80` del cuarto argumento es la capacidad máxima del destino, no una
instrucción para omitir la longitud.

El bloque tampoco usa el formato variable de `Item.WriteDetails`. Es la unión
interna de detalles reconstruida por `FUN_3991f540`. Para equipamiento:

```text
detail + 0x00  detailType
detail + 0x05  durability
detail + 0x06  chargeCount
detail + 0x0c  chargeTime
detail + 0x3c  scaledA (nivel de Temper)
detail + 0x3e  evolveChance
detail + 0x58  chargeProcTime
detail + 0x60  mappingFailBonus
detail + 0x61  elementLevel
```

Los 18 `GemIds` ocupan los offsets no contiguos confirmados por la misma
función. La regresión fija el bloque completo: la longitud está en el offset
12, el bloque comienza en el offset 14, la durabilidad queda en el offset 19 y
`scaledA` en el offset 74. El tamaño total de la acción es exactamente 142
bytes.

El inicio de casteo usa dos tiempos distintos confirmados por
`FUN_399b2390` y `FUN_39985ac0`: tiempo real después de modificadores y tiempo
base nativo. Para Temper `37723`, el segundo valor siempre procede de
`skills.casting_time = 1500`; el primero incorpora `CastTimeMul`. Ambos se
serializan como `uint16` en unidades de 10 ms.

El objeto contextual de ese casteo también es específico de AA8. El
controlador de Refurbishment (`FUN_391226e0`) usa `SkillObject` tipo `6`, y
`FUN_399af960` confirma su payload:

```text
byte   flag = 6
uint64 supportItemId
bool   autoUseAaPoint
byte   inputDirection
```

El servidor histórico interpretaba el tipo `6` como una cadena y reservaba el
soporte para el tipo `7`. Esto desplazaba `SCSkillStartedPacket`, impidiendo
que el cliente iniciara la animación aunque el resultado se aplicara. El tipo
`6` quedó corregido y protegido con lectura y escritura byte a byte.

## Refresco continuo de la ventana

El controlador nativo de Temper escucha dos eventos internos del cliente:

- `0x5E`: resultado de `SCItemRefurbishmentResultPacket`;
- `0x1F`: actualización de inventario cuyo `ItemTask` debe tener el motivo
  AA8 `scale-cap` (`0x7F`, decimal 127).

El primer evento actualiza el resultado y los valores visibles. El segundo
invoca la transición que vuelve a validar y habilitar la siguiente operación.
Usar el motivo histórico `enchant-physical` (`50`) deja el botón **Confirm**
bloqueado aunque el objeto, el porcentaje y el costo ya se hayan actualizado.

Por ello, toda mutación de dinero, soporte y detalle producida por Temper usa
`ItemTaskType.Refurbishment`, alias explícito del motivo nativo AA8
`ItemTaskType.ScaleCap = 127`.
