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
SHA-256 405C6B68CA3F808F3CC176A4CC3DA5FD74A7C4796A57507EC317F20295FC173E
```

Validación:

- dos builds deterministas con el mismo SHA-256;
- `quick_check = ok`;
- `integrity_check = ok`;
- tres clausuras skill/effect/special completas;
- tres objetos del reroll set `230` presentes;
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
