# Reconstrucción AA10 — refresco de estadísticas de personaje r575

Fecha: 2026-08-16

Target: `Wingsjuankaa/AAEmu:rama_10`

Cliente: ArcheAge Returns `10.0.2.13 r575`

## Estado

Dos candidatos basados en `SCUnitEquipmentsChanged (0xBF)` fallaron en vivo. La máscara de
activación de 34 slots corrigió el cálculo de armas y permitió demostrar que el cliente recibía los
modificadores, pero la prueba del casco reveló que el slot de cabeza seguía excluido.

La causa final demostrada en r575 estaba en cuatro selectores `slot` del `UnitState`: AAEmu enviaba
`0,0,0,0`, y el cliente interpreta esos cuatro `s8` como una lista de slots que debe excluir al
agregar estadísticas. Por tanto descartaba siempre el slot físico `0` (casco). Se corrigieron a
`-1,-1,-1,-1`, el sentinel nativo de “sin exclusión”. La prueba viva confirmó que equipar el casco
ahora añade `+25 Melee Attack` por cinco gemas y `+150 Physical Defense` por su base.

## Resultado de la comparación binaria AA8 ↔ AA10

Los binarios completos **no son idénticos**:

| Cliente | Tamaño | SHA-256 |
|---|---:|---|
| AA8 `8.0.3.12 r558734` | 18.839.584 | `12229B1DC1EA8BE3453BC792586EC5A56E948CD8F6424132521F9AF7F9A53C4A` |
| AA10 `10.0.2.13 r575` | 21.808.640 | `2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76` |

Por eso no se portó el arreglo por igualdad de archivo o de offsets. Se comparó la función concreta:

- AA8 `FUN_399b10a0` lee `buffId`, niveles, `skillId` y luego un `u32 stack` en BuffData `+0x1c`.
- AA10 `FUN_39ac4ec0` (`RVA 0xAC4EC0`) conserva el mismo orden y lee el mismo `u32 stack` en `+0x1c`.
- Los loaders `FUN_3997ab60` (AA8) y `FUN_39a8dd30` (AA10, `RVA 0xA8DD30`) usan la misma consulta y
  orden de columnas de `unit_modifiers`.

Clasificación: `aa10_confirmed_shared_primitive`. Coincidencia semántica demostrada; no identidad
byte a byte.

## Causas verificadas

### 1. `0xBF` no controla la activación de los modificadores

`EquipmentContainer` emitía `SCUnitEquipmentsChangedPacket (0xBF)` con `self=false`. Incluir al dueño
y luego sustituirlo por un snapshot de 34 slots tampoco fue suficiente: ambas variantes fallaron en
prueba visual. Por eso se retiró el snapshot completo y se conservó `0xBF` para su responsabilidad
real, que es sincronizar el item/vista del slot.

La tabla de registro nativa r575 enlaza el paquete `0xBF` con `FUN_3933bb20`. Ese handler resuelve la
unidad y aplica la vista mediante `FUN_3967ecb0` / `FUN_398dbcd0`. El serializer AA10 confirmado es:

```text
bc uid
u8 num
bool isCharTransform
num * { s8 EquipSlot, EquipView }
u64 flags
```

Aunque el handler acepta hasta 34 entradas, no escribe la tabla de activación que gobierna los
atributos. La comparación con AA8 sólo permitió descubrir un candidato; la validación de AA10 lo
refutó y evitó aceptar un port por semejanza.

El relay World→Zone enviaba además `1UL << slot`. En r575, `flags` indexa las entradas del arreglo,
no el número de slot: para un body de una sola entrada el valor correcto es siempre `1UL`.

### 2. AAEmu borraba las 34 activaciones en cada ItemTask

El codec r575 de `SCItemTaskSuccess`, `FUN_39a9c0a0`, lee un único `u64 flags` y lo expande a 34
booleanos en el objeto del paquete. El handler `FUN_3933ba70` pasa esa tabla a
`FUN_398e05a0`; cuando el task cambia equipo, `FUN_398d8460` la copia a `unit+0x1bf0` y
`FUN_398e05a0` emite el evento local `0x25`. AAEmu escribía siempre `0UL` en ese campo.

El paquete explícito `SCUnitEquipmentsRndAttrUnitModifierAvtivateChanged (0xC0)` confirma la misma
semántica por una ruta independiente. Su codec `FUN_39abee00` serializa `bc uid + u64 flags`; el
handler `FUN_39345b40` reemplaza los mismos 34 bytes y, para el jugador local, vuelve a emitir
evento `0x25`. No es un dirty mask ni una solicitud genérica de repintado.

El dedicate r575 cierra la frontera distribuida: `WZ 0x001F` usa también `bc uid + un solo u64`
(`FUN_3936bbe0`), y `FUN_393633c0 -> FUN_3935cf10` copia esos 34 bytes a la unidad de Zone. El stub
AAEmu escribía dos `long`; se corrigió al cuerpo nativo de uno solo.

La máscara autoritativa de AAEmu se deriva de los slots físicos ocupados. Es coherente con
`UpdateGearBonuses`, que activa todo item aceptado en `EquipmentContainer`. Se usa en cuatro puntos:

1. tail de equipo de `UnitState`, para que el login no nazca con todos los modificadores apagados;
2. tail `flags` de `SCItemTaskSuccess`, calculado al serializar desde el personaje activo;
3. `SC 0xC0` tras entrar o salir del contenedor de equipo;
4. `WZ 0x001F` hacia el Zone autoritativo.

La instrumentación temporal `[CharacterStatsSync]` y el ALB diagnóstico se retiraron después de
cerrar la causa; el cliente volvió al `character_info.alb` original, verificado por SHA-256.

### 3. Los cuatro selectores `slot` excluían siempre el casco

El codec AA10 `FUN_39bb4eb0` serializa cuatro campos consecutivos llamados `slot` como enteros con
signo de un byte. El consumidor `FUN_39bb4cb0` compara cada slot de equipo contra esos cuatro
valores y omite toda coincidencia durante la agregación local de atributos.

`UnitStatePlacementSerializer` usaba `DefaultSlot = 0` para personajes y emitía cuatro ceros. Eso
explica simultáneamente por qué la Nodachi y sus gemas funcionaban (slot distinto de cero) y por qué
el casco, su defensa física y sus gemas de Melee Attack no se reflejaban en `C`.

AA8 usa cuatro `-1`, pero no se aceptó por port ciego: se compararon los codecs nativos. Las funciones
AA8 `FUN_39aa1670` y AA10 `FUN_39bb4eb0` tienen 123 bytes y difieren sólo en los tres bytes del
desplazamiento RIP hacia la cadena `slot`; opcode, control-flow, ancho y sign-extension coinciden.
Clasificación: `aa10_confirmed_shared_primitive`.

### 4. AA10 descartaba `buff_effects.stack`

`SkillManager` ya cargaba `buff_effects.stack`, pero `BuffEffect.Apply` no lo copiaba al objeto
`Buff`, y `BuffCreatedWire` escribía siempre `1`. El handler nativo `SCBuffCreated (0xEB)`,
`FUN_3934c810`, entrega BuffData al subsistema local y ejecuta la ruta de refresco del jugador; no se
necesita inventar un paquete genérico de actualización de estadísticas.

La SQLite AA10 completa y el compact retail contienen 27.105 filas en `buff_effects`: 206 usan un
stack distinto de 1 (valores observados entre 2 y 1000). El valor fijo era por tanto incorrecto.

Se añadió `Buff.Stack` con default 1, se propaga desde `BuffEffect`, se conserva en overwrite y se
serializa en la posición nativa de BuffData.

## Evidencia y reproducibilidad

- SQLite completa: `E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3`, SHA-256
  `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`.
- Compact retail usado para reconstruir stats: SHA-256
  `90839A7FBF260979C401FC4563F4DCCACD62E8A6F4ED25EA9C2ECA9E0DA2A2B0`.
- Compact efectivo final, después de corregir el cap de undergarments: SHA-256
  `075A661C865E2C9357AB9C9E084100C17C832EFAF6913669D672FCA78632411B`; la única diferencia
  posterior a la reconstrucción de stats es `item_rnd_attr_categories.id=23`, documentada en
  `Docs/AA10UndergarmentSynthesisGradeCap_es.md`.
- Corpus de esta frontera: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\character-stats-frontier`.
- Proyecto Ghidra AA10: `E:\AAEmu\rama_10\forensics\ghidra\ghidra-projects-aa10-client-release\AA10X2GameRelease.gpr`.
- Manifest machine-readable: `Docs/AA10CharacterStatsRefreshEvidence.json`.

## Validación automatizada

Comando:

```powershell
dotnet test AAEmu.UnitTests/AAEmu.UnitTests.csproj --no-restore -- --no-ansi --maximum-parallel-tests 4
```

Resultado final de la fase: **1280 correctas, 0 errores, 0 omitidas**.

Las pruebas nuevas fijan la posición nativa de `stack` en BuffData, la máscara de activación en el
tail de `UnitState` y `0xBC`, el cuerpo exacto `bc + u64` de `0xC0` y de `WZ 0x001F`, y que el dirty
mask de una entrada `0xBF` sea el bit cero con independencia del slot físico.

## Validación manual cerrada

El usuario validó la corrección en el cliente Returns 10.0.2.13 r575 el 2026-08-16. Con `C`
abierta, equipar y desequipar armas, casco, armaduras y Lunagem actualizó inmediatamente ataque,
defensas, atributos y estadísticas derivadas. La Nodachi confirmó la ruta de Melee Critical Damage;
el casco confirmó tanto su defensa base como cinco Lunagem de Melee Attack.

Para ampliar el barrido se entregó directamente un kit de 38 Lunagem `Glorious` mediante el Web API
interno, sin escribir MySQL; consultar `Docs/AA10RuntimeTestItemDelivery_es.md`. Después se validó la
misma ruta de actualización durante la síntesis de un `Leopard Undergarments` desde grado inicial
hasta Eternal. El usuario dio por cerrado el arreglo tras alcanzar el grado máximo y observar los
cambios reflejados en la ventana de personaje.

La instrumentación temporal de chat y el `Logger.Info("[CharacterStatsSync]...")` fueron retirados
antes del commit de cierre. Permanecen únicamente los `Verbose()` normales de packets, sujetos al
nivel de logging habitual del servidor.
