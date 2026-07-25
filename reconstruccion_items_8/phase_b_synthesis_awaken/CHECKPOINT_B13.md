# Checkpoint B13 — síntesis y awakening AA8

## Política

La única autoridad de gameplay es AA8:

1. compact 8.0 descifrada;
2. filas nativas recuperadas de `game11`;
3. layouts y consumidores confirmados en `x2game.dll`;
4. protocolo observado con el cliente local.

La compact 3.0 no aporta filas, fórmulas, probabilidades ni fallbacks.

## Cerrado en B13a

- Catálogo dirigido Hiram/Erenor reproducible: 150 armas.
- Categorías, propiedades por grado, materiales, mappings y grupos de
  atributos extraídos desde `game11`.
- Builds deterministas, integridad SQLite en `ok` y cero referencias
  huérfanas habilitadas.
- Eliminada `item_rnd_attr_category_materials`, porque no existe en el
  loader AA8.

## Cerrado en B13b

- Síntesis: skill `30666`, efecto `20058`, tipo especial `123`.
- Material como `SkillItem`, arma como `SkillCastItemTarget` y cantidad en
  `SkillItem.Type2`.
- XP en detalle `+0x40`; cinco IDs de atributos en `+0x44..+0x54`.
- XP por `gain_exp` y costo:
  `truncate(gold_multiplier * material_exp * 0.001000000047)`.
- Progresión de múltiples grados consumiendo `grade_exp`.
- Bonus XP nativo en permille: chance `150` = 15%; rango `200..500` =
  20%..50% de la XP aportada.
- Resultado AA8 `0x0C6` (`FUN_399a1e60`) y `ItemTask` razón `100`.
- Selección de atributos por `group_set.pick_count`, pesos y restricciones
  AA8.
- Los atributos existentes conservan su grupo y se remapean a la fila del
  nuevo grado; no se vuelven a sortear.
- Nuevos atributos sólo se añaden cuando aumenta `max_unit_modifier_num`.
- Valor efectivo confirmado por `FUN_39a4be10`/`FUN_39a4be30`:
  `minimum + (maximum - minimum) * section_exp / grade_exp`.
- El resultado serializa `unit_attribute_id`, `unit_modifier_type_id` y
  valor; no grado ni IDs históricos.
- Los atributos sintetizados afectan inmediatamente las estadísticas al
  equipar y persisten en el detalle nativo.

## Backend y pruebas

- `IItemSynthesisService`, `IItemAwakeningService`,
  `IItemRandomAttributeService` e `IItemEvolutionStateService`.
- Preview, validación, costo, bonus, progreso y mutación transaccional.
- Comandos `/item8 synthesis|awakening|evolutionstate|evolutioncoverage`.
- Modos GM `/evolutiontest mode
  natural|success|fail|crystallize|bonusxp`.
- 159 pruebas superadas, incluidas selección, interpolación, remapeo y
  serialización byte a byte.

## Awakening confirmado

- Gear Upgrade usa el controlador modo 11.
- `item.use_skill_id → skill_effect → SpecialEffect 165`; `value1` es
  `mapping_group_id`.
- La UI calcula `success + MappingFailBonus * 100` en escala 10000:
  `1000`, `4000` y `10000` representan 10%, 40% y 100%.
- Piloto `45635 → 45828`:
  - grupo 9: scroll `45908`, skill `39332`, 25 unidades, 300 labor;
  - grupo 10: scroll `45978`, skill `39341`, 1 unidad, 300 labor;
  - grupo 301: scroll `52021`, skill `48094`, 1 unidad, 100 labor.

## Cerrado en el backend después de B13b

- Awakening Hiram genérico:
  - éxito, fallo y cristalización;
  - failstack en escala nativa;
  - reemplazo atómico de plantilla;
  - herencia de XP, temper, Lunafrost, Lunagem, durabilidad, binding,
    apariencia y atributos;
  - resultado AA8 `SCItemChangeMappingResultPacket`.
- Reroll aleatorio:
  - objeto `46682`;
  - skill `32060`;
  - efecto `52963`;
  - `SpecialEffect 21462`, tipo `136`.
- Reroll selectivo:
  - objetos `50552` y `50635`;
  - skill `46234`;
  - efecto `88704`;
  - `SpecialEffect 56777`, tipo `187`.
- Ambos rerolls usan el `SkillObject` AA8 tipo `9`:
  índice físico del atributo y grupo de reemplazo.
- Resultado de reroll AA8 `0x05E`, validado byte a byte.
- Descristalización Hiram:
  - objeto `45732`;
  - skill `39040`;
  - efecto `70715`;
  - `SpecialEffect 35710`, tipo `156`;
  - `ItemTask 170`, `restore-disable-enchant`.
- 169 pruebas automatizadas aprobadas.

## Runtime B13c

```text
compact-8.0-runtime-native-equipment-phase-b13c-hiram-erenor-evolution.sqlite3
SHA-256 252F682548CF2D5BAC0003326EBA9F249F9B3757D801D4B1EAE759694AE422A9
```

Validación:

- dos builds deterministas con el mismo SHA-256;
- `quick_check = ok`;
- `integrity_check = ok`;
- tres clausuras skill/effect/special completas;
- tres objetos del reroll set `230` presentes;
- 20 descriptores `ItemEvolvingMaterialDesc` (`impl_id 33`) con cobertura
  completa y creación controlada habilitada;
- cero tabla histórica `item_rnd_attr_category_materials`.

## Bloqueado sin inferencias

- El camino sin reactivo que consume cargas libres de
  `EquipItem.EvolveChance` permanece deshabilitado hasta confirmar su skill
  por defecto y decremento exacto.
- No se emite el offset SC `0x113`: aún no se ha identificado su serializer
  como paquete de red. La actualización autoritativa de descristalización usa
  el `ItemTask 170` confirmado.
- B13c habilita el mismo motor y catálogo para armas Erenor, pero su cierre
  funcional requiere las pruebas manuales de síntesis, atributos y
  transiciones que correspondan a sus mappings AA8.

## Despliegue local B13c

Desplegado el 2026-07-24 recreando únicamente el servicio `game`.

- Imagen local: `aaemu-game:0.0.2.0-alpha`.
- Image ID: `sha256:a9c457430a5e8472ec40ac7f471c8b84fbf0ba58fad99d05f3e90acf18f1d4d4`.
- Compact montada en `/app/Data/compact.sqlite3`.
- SHA-256 comprobado dentro del contenedor:
  `252F682548CF2D5BAC0003326EBA9F249F9B3757D801D4B1EAE759694AE422A9`.
- Game escucha en `2239` y Stream en `2250`.
- Registro contra LoginServer confirmado.
- Login y MySQL no fueron recreados.

Respaldo anterior al despliegue:

```text
E:\AAEmu-Research\backups\aa8-evolution-b13c\aaemu8-pre-b13c-2026-07-24.sql
SHA-256 F0434EF8CBAB46B92A702F5595274952165C685B73E142FAE88EE4F076351B6E
```

El despliegue técnico está cerrado. La aceptación funcional de Hiram y Erenor
permanece pendiente de las pruebas manuales indicadas en este documento.

## Corrección previa a la aceptación manual

El resolver de compatibilidad ya no interpreta
`item_rnd_attr_category_relations` como la autoridad de Hiram/Erenor. Esa
tabla contiene relaciones de objetos pertenecientes a otra mecánica.

La compatibilidad de síntesis utiliza ahora los pares de grupos AA8
confirmados por el catálogo:

- grupo `1`, Ancient Growth, acepta grupo `2`, Ancient Materials;
- grupo `29`, Ancient T4-T5 Growth, acepta grupo `30`, Ancient T4-T5 Materials;
- grupo `21`, Crafted Weapon Growth, acepta grupos `24` y `25`, Crafted
  Common/Weapon Materials.

Esto impide aceptar los IDs de peces `29722` y similares como materiales
Hiram, y habilita correctamente las infusiones AA8 `488xx`. La regresión
automatizada queda en 171 pruebas aprobadas.

Los 20 materiales `488xx` alcanzables por B13c se promueven a cobertura
`complete` sólo cuando cumplen simultáneamente:

- existencia en `item_evolving_materials`;
- existencia en `items`;
- `impl_id = 33`, confirmado como `ItemEvolvingMaterialDesc`.

Así `/additem 48828 100` crea una infusión AA8 completa sin relajar las reglas
de cobertura para ningún otro objeto genérico.

## Checkpoint B13d — 2026-07-25

Se restauraron los envoltorios apilables de infusión Hiram y la generación
del material `48825` con calidad variable:

- `45731`: Grand/Rare/Arcane, pesos `60/30/10`;
- `46023`: Rare/Arcane/Heroic, pesos `60/30/10`;
- `47052`: Heroic/Unique/Celestial, pesos `60/30/10`.

La tabla completa de 50 distribuciones de grado, con `weight_0..weight_12`,
proviene de `game11`. Skills, relaciones y efectos provienen de la compact
AA8 y `game11`. El selector de calidad se hizo transversal y cuenta con
pruebas de límites para impedir grados de peso cero.

Estado técnico:

- Runtime:
  `compact-8.0-runtime-native-equipment-phase-b13d-hiram-infusion-wrappers.sqlite3`
- SHA-256:
  `A1E8370FCA25502124CFFE0F383916BCCDFABBDD449F1477399282DC2442F245`
- SQLite: `quick_check = ok`, `integrity_check = ok`.
- Pruebas: `175/175`.
- Despliegue: sólo se reconstruyó y recreó `game`; Login y MySQL se
  conservaron.
- Puertos: Game `2239`, Stream `2250`.

## Corrección B13e — protocolo de confirmación de síntesis

Las pruebas manuales demostraron que el dato previo del contexto de casteo
era incorrecto. El cliente Kakao 8.0 envió la skill `30666` con:

- `SkillCasterUnit`;
- `SkillCastItemTarget` para el equipo;
- `SkillObject` tipo `8`;
- `materialItemId` como campo binario de 48 bytes para seis materiales;
- `autoUseAAPoint` y luego `inputDirection`.

`x2game.dll` confirma el layout del tipo `8`, pero el serializer denominado
`string` transporta aquí bytes arbitrarios, no texto UTF-8. El segundo intento
manual completó el casteo y volvió a mostrar el rechazo porque la primera
implementación trataba el bloque como una concatenación decimal.

El protocolo observado contiene seis `UInt64` little-endian consecutivos:
`16777238`, `16777277`, `16777280`, `16777278`, `16777281`, `16777279`.
Corresponden a las seis infusiones persistidas y sus `gain_exp` suman
exactamente los `5200` mostrados por Gear Upgrade. El backend conserva ahora
los 48 bytes, decodifica hasta seis IDs, rechaza payloads mal formados o
duplicados, valida todos los materiales antes de mutar y consume exactamente
las instancias seleccionadas en una sola transacción de `ItemTask`.

La inspección de MySQL posterior al rechazo confirmó que el arma
`16777247` seguía en grado 4 con su detalle intacto y que las seis infusiones
continuaban presentes. No hubo consumo ni progreso parcial.

Validación automatizada:

- pruebas dirigidas de protocolo y síntesis: `13/13`;
- suite completa .NET Core 3.1: `177/177`;
- runtime B13d sin cambios:
  `A1E8370FCA25502124CFFE0F383916BCCDFABBDD449F1477399282DC2442F245`.

Despliegue local B13e:

- sólo se reconstruyó y recreó `game`;
- imagen:
  `sha256:259c3528b433ba7426e14a6988b27b9bf0f7bd8b8e14f03a5aab241b598eb8b8`;
- compact montada con el hash B13d esperado;
- `ScriptCompiler`: 0 errores;
- Game `2239` y Stream `2250` escuchando;
- registro estable en LoginServer confirmado.

## Corrección B13f — refresco inmediato al subir de grado

La tercera prueba manual completó la síntesis y confirmó la persistencia, pero
el arma no cambió visualmente en Gear Upgrade ni en el inventario hasta
reingresar al personaje.

Evidencia observada a las `05:42:51`:

- el servidor envió `SCItemTaskSuccessPacket` razón `100` con 8 tareas;
- luego envió `SCEvolvingResultPacket` `0x0C6`;
- aplicó `5200 + 1497` XP, grado `4 -> 5` y dejó `1302` XP de sección;
- MySQL confirmó el arma `16777247` en grado 5 y las seis infusiones
  consumidas.

El análisis de `x2game.dll` aisló la causa:

- `FUN_39a502f0` serializa `UpdateDetail` (acción 10);
- `FUN_39a56560` copia únicamente su bloque interno de 128 bytes;
- el grado del objeto vive fuera de ese bloque;
- `FUN_39a550d0` y `FUN_39a56b90` confirman el serializer y consumidor de
  `ChangeGrade` (acción 15).

El lote de síntesis ahora añade `ChangeGrade` antes de `UpdateDetail` cuando
el grado final difiere del inicial. Cuando la síntesis permanece dentro del
mismo grado sólo se emite `UpdateDetail`.

Validación automatizada:

- pruebas dirigidas de ItemTask y síntesis: `24/24`;
- suite completa .NET Core 3.1: `179/179`;
- runtime B13d sin cambios:
  `A1E8370FCA25502124CFFE0F383916BCCDFABBDD449F1477399282DC2442F245`.

Despliegue local B13f:

- sólo se reconstruyó y recreó `game`;
- imagen:
  `sha256:b16ed20b655bd669f7b23d86bf45fb0172938bad160b938b6daf28068b58ae95`;
- `ScriptCompiler`: 0 errores;
- Game `2239` y Stream `2250` escuchando;
- registro estable en LoginServer confirmado.
