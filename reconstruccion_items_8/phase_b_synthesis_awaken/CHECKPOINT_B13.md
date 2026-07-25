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

## Pendiente sin inferencias

- Cerrar el protocolo de resultado de awakening.
- Confirmar condición y resultado de cristalización.
- Implementar fallo, failstack, éxito y reemplazo atómico de plantilla.
- Implementar reroll con skill `32060`, efecto `21462`, tipo `136`.
- Activar Erenor sólo tras aprobar el piloto Hiram.
