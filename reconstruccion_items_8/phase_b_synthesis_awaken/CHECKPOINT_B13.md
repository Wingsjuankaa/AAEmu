# Checkpoint B13 — síntesis y awakening AA8

## Política

La única autoridad de gameplay es AA8:

1. compact 8.0 descifrada;
2. filas nativas recuperadas de `game11`;
3. layouts y consumidores confirmados en `x2game.dll`;
4. protocolo observado con el cliente local.

La compact 3.0 no aporta filas, fórmulas, probabilidades ni fallbacks.

## Cerrado en B13a

- Catálogo dirigido Hiram/Erenor reproducible.
- 150 armas de las familias activadas.
- Categorías, propiedades por grado, materiales, relaciones, mappings y
  grupos de atributos extraídos desde `game11`.
- Dos construcciones deterministas con el mismo SHA-256.
- `quick_check` e `integrity_check` en `ok`.
- Cero referencias huérfanas habilitadas.
- Eliminada `item_rnd_attr_category_materials`: sus filas del runtime
  anterior eran históricas y el cliente AA8 no posee ese loader.

## Confirmaciones de `x2game.dll`

- Síntesis: skill `30666`, efecto `20058`, tipo especial `123`.
- Reroll: skill `32060`, efecto `21462`, tipo especial `136`.
- El material viaja como `SkillItem`, el arma como
  `SkillCastItemTarget` y la cantidad en `SkillItem.Type2`.
- `ItemTask` `100` es `evolving`.
- XP de la sección actual: detalle de equipo `+0x40`.
- Cinco IDs de modificadores aleatorios: `+0x44..+0x54`.
- XP aportada: `gain_exp` de la propiedad del material.
- Costo confirmado:
  `truncate(gold_multiplier * material_exp * 0.001000000047)`.
- El ascenso puede atravesar múltiples grados consumiendo `grade_exp`
  sucesivamente.
- Awakening usa el modo 11 del controlador Gear Upgrade. El cliente busca
  `awakenConsumeCount` en el efecto del reactivo.
- La cadena quedó confirmada:
  `item.use_skill_id → skill_effect → SpecialEffect tipo 165`.
  `value1` es el `mapping_group_id`; la relación de skill contiene el ID y
  la cantidad del scroll consumido.
- Para el piloto Hiram se recuperaron:
  - grupo 9: scroll `45908`, skill `39332`, 25 unidades, 300 labor;
  - grupo 10: scroll `45978`, skill `39341`, 1 unidad, 300 labor;
  - grupo 301: scroll `52021`, skill `48094`, 1 unidad, 100 labor.

## Implementado en backend

- `IItemSynthesisService`, `IItemAwakeningService`,
  `IItemRandomAttributeService` e `IItemEvolutionStateService`.
- Estado AA8 de XP, failstack y cinco atributos sin confundirlo con sockets.
- Preview de síntesis, compatibilidad de material, costo y progreso.
- Ejecución de `ItemEvolving` mediante una transacción `ItemTask` 100.
- Refresco inmediato del detalle autoritativo del arma.
- Inspección:
  - `/item8 synthesis <itemId>`
  - `/item8 awakening <itemId>`
  - `/item8 evolutionstate <instanceId>`
  - `/item8 evolutioncoverage <itemId>`
- Modos temporales GM:
  `/evolutiontest mode natural|success|fail|crystallize|bonusxp`
  y `/evolutiontest clear`.
  Se eliminan al desconectar y no modifican compact ni MySQL.

## Bloqueos deliberados

Los siguientes puntos no se ejecutan aún porque inferirlos violaría la
política AA8:

- escala y distribución del bonus XP natural;
- algoritmo de elección inicial y reroll de atributos;
- escala de `success`, fórmula de failstack y cristalización;
- serialización exacta de éxito, fallo y cristalización;
- reemplazo de plantilla durante awakening.

Los comandos muestran los valores crudos confirmados, pero awakening se
mantiene de sólo lectura hasta cerrar esas dependencias.

## Próxima validación

Activar B13b primero en el servidor local y probar Hiram:

1. una y varias unidades del mismo material;
2. rechazo de material no relacionado;
3. XP, oro, labor y cruce de grados;
4. operaciones consecutivas sin cerrar Gear Upgrade;
5. persistencia después de relog;
6. regresión de temper, Lunafrost y Lunagem.

Sólo después se habilitarán atributos/reroll y el piloto de awakening
`45635 → 45828`.
