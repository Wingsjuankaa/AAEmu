# Estado de Fase B — objetos avanzados AA8

Fecha de corte: 2026-07-23.

## Regla de autoridad

Toda fila de gameplay procede de `game11` y todo layout/protocolo está
confirmado en `x2game.dll`. La compact 3.0 no aporta datos ni valores de
fallback.

## B1 — sockets, lunagems y enchanting gems

Artefacto:

```text
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b1-sockets-v1.sqlite3
SHA-256 F5A1539BC2FE45903E2FCFB8E45F6FF9A66B2FC2B60B79D6E8473AAAD9A7C882
```

Cobertura recuperada:

- 484 `item_enchanting_gems`;
- 783 `item_sockets`;
- contexto nativo `SkillObject` 10/11 para instalación y cambio de sockets;
- Lunascales separadas de su acción alternativa de desarme por honor;
- 762 `item_socket_level_limits`;
- 403 `item_socket_num_limits`;
- 8 `item_socket_chances` en el layout corto AA8;
- 27 `item_socket_changes`;
- 26 `gem_visual_effects`.

Protocolo confirmado:

- `SCSocketingResultPacket`, opcode `0x279`;
- `SCEnchantMagicalResultPacket`, opcode `0x2ED`;
- operación `0=remove`, `1=install`.

El backend ya carga y valida definición, target explícito, slot group, grado,
nivel, máximo de sockets y chance set. Las operaciones reales permanecen
bloqueadas porque el cliente AA8 no expone `socket0..socket9`, y aún falta
confirmar la autoridad de resultado, costo y consumo del reactivo.

Los dos paquetes históricos con opcode `0xFFF` fueron eliminados.

## B2 — temper / enchant scale

Artefacto acumulativo:

```text
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b2-temper-v1.sqlite3
SHA-256 75758F658E476174DE63D2E2D1AE7A909846726D76BCBFE9A4F23C049C8E7F7C
```

Cobertura recuperada:

- 31 `enchant_scale_ratios`;
- 37 `item_cap_scale_forbids`;
- cero referencias faltantes desde `items.max_enchant_scale_id`.

Corrección transversal:

- el estado AA8 es `Item.ScaledA`;
- `TemperPhysical` y `TemperMagical` son campos históricos y no gobiernan el
  runtime AA8;
- el multiplicador nativo es `1 + scale / 1000`;
- armas y armaduras consumen ahora el mismo estado que serializa el cliente.

La antigua elección aleatoria `ScaleMin/ScaleMax` fue retirada. La mutación
queda bloqueada hasta confirmar reactivos, moneda y paquete de resultados.

## B3 — síntesis, awakening y reroll

Artefacto acumulativo:

```text
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b3-synthesis-v1.sqlite3
SHA-256 6F0DCE7897C91594B540E671172C7709DF4980EB30A1930A8054706F63E260E9
```

Cobertura recuperada:

- 459 `item_rnd_attr_unit_modifier_group_sets`;
- 3.694 `item_rnd_attr_unit_modifier_groups`;
- 48.022 `item_rnd_attr_unit_modifiers`;
- 10.088 `category_properties`;
- 298 `category_elements`;
- 776 `categories`;
- 38 `category_groups`;
- 142 `category_relations`;
- 74 `item_evolving_materials`;
- 285 `item_change_mapping_groups`;
- 8.468 `item_change_mappings`.

El backend dispone de un catálogo de consulta nativo y del comando:

```text
/item8 evolution <itemId> [grade]
```

La operación de evolución no está activa todavía. El cierre interno del grafo
no tiene referencias huérfanas, pero el subconjunto de objetos de Fase A no
incluye aún 5.037 fuentes, 3.335 destinos, 4 objetos de evolución y 71
materiales referenciados. Esas ausencias se mantienen como bloqueos explícitos;
no se sustituyen con datos de la compact 3.0.

## B4 — regrade

Artefacto acumulativo:

```text
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b4-regrade-v1.sqlite3
SHA-256 672E657D67AF5EADD4ADE48CB245A9990B0032437931F6324823FD2B8BEAFAA2
```

Cobertura recuperada:

- 6 `item_enchant_ratio_groups`;
- 78 `item_enchant_ratios`, frente a las 36 filas incompletas heredadas;
- 2.114 `item_enchant_ratio_items`;
- 99 `item_grade_enchanting_supports` con sus 18 campos AA8.

El backend carga el catálogo mediante `ItemRegradeRuleService` y permite
inspeccionarlo sin mutar objetos:

```text
/item8 regrade <itemId> <grade>
```

La operación queda bloqueada hasta confirmar la transacción, el protocolo y
las recompensas de rotura. No se usan los ratios vacíos de `GradeTemplate`.

## B5 — conversión de apariencia

Artefacto acumulativo:

```text
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b5-appearance-v1.sqlite3
SHA-256 B858B8D4129D8092520E4F18B0AE70F778D7F8AD1784BCD39AA8FCF57B352611
```

Cobertura recuperada:

- 35 conversiones;
- 29 relaciones de holdables;
- 10 relaciones de wearables;
- 30 reactivos de conversión;
- 28 reactivos de reversión.

Todas las referencias internas y de reactivos existen en el catálogo activo.
El modelo del backend conserva costo, nombre, reactivo y reactivo de reversión.

```text
/item8 appearance <itemId>
```

La mutación sigue bloqueada hasta confirmar paquetes y rollback.

## B6 — salvaging, conversión y smelting

Artefacto acumulativo:

```text
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b6-salvaging-v1.sqlite3
SHA-256 BEBD885ECEC6812788D77048AE501575676C7CF3A16D182573CD42FFE82D030E
```

Cobertura recuperada:

- 34.822 reactivos de conversión;
- 124 filtros;
- 5.961 relaciones de paquetes de reactivos;
- 5.774 paquetes de reactivos;
- 5.626 productos;
- 5.842 relaciones de paquetes de productos;
- 5.630 paquetes de productos;
- 6.384 conversiones y 12 grupos;
- 96 relaciones de smelting y 32 definiciones de smelting.

El backend expone cobertura sin calcular resultados:

```text
/item8 salvage <itemId>
```

Bloqueos confirmados:

- falta cerrar el formato cacheado de `item_smelting_probs`;
- 8 relaciones apuntan a paquetes de reactivos ausentes y una a un paquete de
  productos ausente en los datos nativos recuperados;
- siete cadenas localizadas siguen como referencias internadas;
- el subconjunto de objetos de Fase A no contiene aún todos los reactivos y
  productos;
- solicitud, resultado y rollback no están confirmados.

## Validación

- dos builds de cada artefacto producen el mismo SHA-256;
- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- 123 pruebas del repositorio pasan;
- 22 pruebas específicas de los servicios B1–B6 pasan.

## Despliegue

La compact activa de Fase A no fue reemplazada y el servidor no se reinició.
Esto evita activar una operación destructiva o económica todavía incompleta.

Los catálogos B1–B6 están construidos, pero no se desplegarán en conjunto
todavía. El siguiente trabajo ya no es extraer tablas generales: es cerrar,
por operación, los bloqueos de protocolo y transacción empezando por una ruta
de bajo riesgo, con respaldo y rollback verificable.
