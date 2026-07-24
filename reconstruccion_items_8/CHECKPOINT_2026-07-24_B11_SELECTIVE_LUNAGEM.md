# Checkpoint B11 — refinado selectivo de Lunagem AA8

## Corrección de alcance

La Lunascale no se usa como piloto de esta fase. Al entrar en la pestaña
Lunagem aparece deshabilitada porque corresponde a otro contexto de
instalación. B11 restaura primero los Lunagem comunes de AA8, como Fireglow,
Waveglow y las familias equivalentes.

## Flujo nativo recuperado

```text
Lunagem base (categoría 152)
→ use_skill_id
→ efecto game11 selective_item
→ selector de opciones del cliente
→ CSBagHandleSelectiveItemsPacket (0x1C4)
→ consumo y resultado atómicos
→ ItemTaskType 150
```

`game/scriptsbin64/x2ui/inventory/selective_item.alb` confirma que:

- el clic derecho abre el selector;
- las opciones se registran por índice uno-basado;
- `tryCount` permite repetir el refinado si `is_multi=true`;
- el objeto fuente no debe consumirse al abrir la ventana;
- el consumo ocurre al confirmar.

El layout confirmado en `x2game.dll` es:

```text
byte slotType
byte slot
uint32 tryCount
uint32 optionCount
uint32[optionCount] optionIndices
```

Los resultados almacenados en `game11` son UIDs. Cada UID se resuelve contra
`items.uid` de la compact AA8 descifrada. Una acción con un solo UID no
resuelto queda bloqueada completa.

## Catálogo

- 13 acciones cerradas.
- 106 resultados cerrados.
- Incluye las seis familias base:
  - `43476` / lista `v2.socket_1tier_red`;
  - `43477` / lista `v2.socket_1tier_brown`;
  - `43478` / lista `v2.socket_1tier_blue`;
  - `43479` / lista `v2.socket_1tier_yellow`;
  - `43480` / lista `v2.socket_1tier_green`;
  - `43481` / lista `v2.socket_1tier_pink`.
- Las variantes incompletas se mantienen en `blocked_actions` del manifiesto.

## Corrección Tier 1 / Tier 2

La primera prueba reveló que enlazar por `items.use_skill_id` entregaba
Splendid al abrir una gema base. AA8 contiene listas separadas por alias:

```text
43476 Fireglow base -> v2.socket_1tier_red -> 43490..43499
43483 Splendid base -> v2.socket_2tier_red -> 43500..43509
```

Se reconstruyó el mismo enlace para brown, blue, yellow, green y pink usando
alias, icono/color y `fixed_grade` nativos. La progresión hacia el objeto
Splendid continúa perteneciendo a Handicrafts.

## Runtime activo

```text
compact-8.0-runtime-native-equipment-phase-b11-selective-lunagem-v2.sqlite3
SHA-256 269F4896CCB88E987D5C78BF8F93E21D4C1FE8E3ADC093BD55BA1597F2C51CAB
```

Validación:

- dos construcciones idénticas;
- `PRAGMA quick_check = ok`;
- `PRAGMA integrity_check = ok`;
- cero referencias huérfanas.

## Backend

- Nuevo catálogo `SelectiveItemCatalogueService`.
- Implementado y registrado `CSBagHandleSelectiveItemsPacket`.
- `ItemTaskType.SelectiveItem = 150`.
- El consumo de `UseSkillAsReagent` se difiere sólo para las acciones
  selectivas cerradas.
- Se valida ranura, skill, cantidad, opciones, cobertura AA8 y capacidad antes
  de mutar.
- Consumo y creación se notifican juntos mediante el estado autoritativo.
- Un rechazo reenvía el inventario autoritativo y nunca recurre a datos 3.0.

## Verificación

- Compilación local: correcta.
- Build Docker con SDK 3.1 original: correcto.
- Pruebas `SelectiveItemCatalogueServiceTests`: 3/3.
- Se recreó únicamente `aaemu8-game-1`.
- Login y MySQL no fueron reiniciados.
