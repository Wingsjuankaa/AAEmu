# Fases B1/B2 — sockets y lunagems nativos AA8

Esta carpeta reconstruye la primera parte de la Fase B del sistema de objetos
sin usar filas de gameplay de la compact 3.0.

Fuentes de autoridad:

1. `compact-client-8.0-decrypted.sqlite`;
2. resultados nativos de `game11`;
3. layouts y protocolo confirmados en `x2game.dll`.

## Taxonomía AA8 confirmada

Los nombres visibles pueden inducir a mezclar tres mecanismos distintos:

- **Lunafrost** usa `item_enchanting_gems`, ocupa el campo único `gemInfo` y
  se instala desde su pestaña separada de Gear Upgrade.
- **Lunascale** usa `item_sockets`. Es una gema final de socket garantizado;
  ocupa una de las nueve posiciones físicas `socketInfo`. También admite una
  acción alternativa de clic derecho para desarmarla y obtener honor.
- **Lunagem base/refinable** también usa el dominio de sockets, pero debe
  convertirse a su forma final antes de poder insertarse.

Por tanto, una Lunascale no es equivalente a Lunafrost. La frase nativa
`Lunascales never fail to socket.` confirma que pertenece al sistema de
sockets, aunque su inserción sea garantizada.

## Contexto nativo de instalación

La reconstrucción B10 confirmó en `x2game.dll`:

- `FUN_39121470`: Gear Upgrade inicia la habilidad del reactivo sobre un
  objetivo de tipo objeto.
- `FUN_399af960`: `SkillObject` tipo `10` serializa
  `autoUseAAPoint`, `count` y `continuous`.
- `SkillObject` tipo `11` serializa `index` e `isAll` para cambios o retiros.

Las 15 Lunascales garantizadas usan `use_skill_id=37186`. En la compact AA8,
esa habilidad posee una única relación nativa:

```text
skill 37186
→ skill_effect 51508
→ effect 65940
→ SpecialEffect 30634
→ GiveHonorPoint(3000)
```

Esa relación corresponde exclusivamente al clic derecho de desarme. Cuando
el mismo skill llega con objetivo de objeto y `SkillObject` tipo `10`, el
backend lo enruta al instalador de socket AA8; no ejecuta el premio de honor.
Así se conservan ambas acciones sin inventar un efecto ni reutilizar datos
3.0.

## Hallazgos confirmados

- `item_enchanting_gems`: 484 definiciones nativas.
- `item_sockets`: 783 definiciones nativas.
- `item_socket_level_limits`: 762 límites.
- `item_socket_num_limits`: 403 combinaciones de ranura y grado.
- `gem_visual_effects`: 26 referencias visuales.
- `item_socket_changes`: 27 conversiones nativas.
- El cliente cargó 8 filas mediante la consulta corta de
  `item_socket_chances`, que sólo contiene `id`, `fail_break` y `cost_ratio`.
- Las probabilidades `socket0` a `socket9` existen en el loader alternativo de
  `x2game.dll`, pero no están presentes en el resultado cacheado de este
  cliente. No se completan con valores históricos ni se asume éxito.
- AA8 usa `SCSocketingResultPacket` (`0x279`) con:
  `byte result`, `uint64 itemId`, `uint32 itemTemplateId`,
  `byte operation`, `bool success`.
- El handler `FUN_39301ac0` confirma `operation=0` para retirar y
  `operation=1` para instalar.
- El enchanting mágico usa un paquete distinto,
  `SCEnchantMagicalResultPacket` (`0x2ED`), con:
  `bool result`, `uint64 itemId`, `uint32 itemTemplateId`.

El runtime generado es candidato y permanece bloqueado hasta que el backend
implemente las reglas nativas y se confirme la fuente autoritativa de las
probabilidades que el cliente no almacena.

## Cierre de layout y primera activación

La auditoría posterior de `x2game.dll` confirmó dos dominios distintos dentro
del detalle de equipamiento AA8:

```text
detail + 0x08       gemInfo
detail + 0x18..0x38 socketInfo[0..8]
```

En el arreglo de persistencia del backend corresponden a:

```text
GemIds[1]     enchanting gem único
GemIds[4..12] nueve sockets físicos
```

La función cliente que calcula el costo de socket recorre exactamente esas
nueve posiciones. Los campos `GemIds[0]`, `GemIds[2..3]` y
`GemIds[13..17]` son extensiones de equipamiento diferentes y no deben contar
como sockets.

También quedó confirmado el cálculo económico:

1. evaluar `FormulaKind.ItemSocketingCost = 38` con `item_level`,
   `socket_item_level`, `item_used_socket` e `item_socketing_cost_mul`;
2. multiplicar por `item_socket_chances.cost_ratio / 100`;
3. redondear el resultado positivo sumando `0.5` antes de convertir a entero.

Estado de activación:

- `EnchantingGem`: activado. Es una operación garantizada, reemplaza
  `gemInfo`, persiste el detalle y actualiza inmediatamente inventario,
  equipamiento y estadísticas.
- Los 484 enchanting gems y 783 socket items tienen tipos concretos
  `enchanting_gem` y `socket`; pueden crearse para pruebas sin el bypass de
  objetos genéricos.
- `Lunagem`: validación, límite de nueve sockets y costo implementados.
- `Lunascale`: 15 definiciones cuya localización descifrada AA8 declara
  literalmente `Lunascales never fail to socket.` quedan activadas con
  probabilidad garantizada. Instalan en el primer socket físico libre,
  descuentan el costo nativo, persisten y actualizan inventario/equipo.
- La familia moderna de `Lunagem` asociada al chance set `7` quedó activada
  en B12 como determinista, conforme al comportamiento observado con el
  cliente Kakao 8.0.3.12 local. El costo sigue aumentando mediante la fórmula
  AA8 `38`, que incorpora el nivel del equipo y la cantidad de sockets usados.
- Los grupos históricos o probabilísticos distintos de `7` continúan
  bloqueados porque el cliente r558734 no contiene `socket0..socket9`; no se
  inventan probabilidades ni se reutilizan valores 3.0.

El ítem `39072` no pertenece a la lista garantizada: aunque una runtime
intermedia contenía el texto agregado, la compact descifrada original no lo
declara. Se mantiene bloqueado para respetar la procedencia AA8.

La búsqueda exhaustiva en los resultados no vacíos de `game0`, `game2`,
`game6`, `game7` y `game11` confirmó que las diez probabilidades no fueron
cacheadas en esta distribución. Este bloqueo es de datos, no del extractor.

## Generación

```powershell
python .\extract_native_sockets.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-v1.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b1-sockets-v1.sqlite3 `
  --manifest ..\generated\native-sockets-phase-b1-v1.json
```

El script construye dos veces el artefacto y exige el mismo SHA-256, además de
ejecutar `quick_check` e `integrity_check`.
