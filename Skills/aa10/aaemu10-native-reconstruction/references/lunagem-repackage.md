# Transmuter y reempaquetado de Lunagem AA10

Leer esta referencia al diagnosticar o probar `ItemConversion`, Transmuter o la reapertura selectiva
de Lunagem en r575.

## Contrato cerrado

- Transmuter: item 42876, skill 35945, 500 labor base, special effect 49 con `value1=8`.
- `value1=8` es `item_conv_sets.id=8` (`repackage`). No es un ID de reagent pack ni product pack.
- Prueba canónica: 44684 -> item_conv 4579 -> rpack 4579 -> ppack 4652 -> 44773 x1.
- 44773 usa skill 38063 y `selective_item_effects.id=391`; la opción 4 devuelve 44684.
- Dossier: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\lunagem-repackage-frontier`.
- Checkpoint: `E:\AAEmu\rama_10\server\AAEmu\Docs\AA10LunagemRepackageReconstruction_es.md`.

## Invariantes de implementación

Recorrer siempre las tablas de miembros:

`item_conv_set -> item_conv -> item_conv_rpack_members -> reagent/filter`

y:

`item_conv -> item_conv_ppack_members -> ppack chance -> weighted product`.

No comparar directamente `item_conv_rpack_id` con `item_conv_ppack_id`: para 44684 la coincidencia
numérica 4579 selecciona un pack ajeno. Validar set, instancia exacta del consumible y del target,
labor y capacidad antes de mutar. El reempaquetado y el selector deben rechazar sin consumo parcial.
Un grado de producto -1 hereda el del target; el template de salida puede normalizarlo a grado fijo.

## Estado y prueba canónica

Build Release y 1344 pruebas quedaron verdes el 2026-08-19, incluida resolución contra la SQLite
autoritativa local. La aceptación dinámica dentro del cliente 10.0.2.13 r575 también quedó cerrada:

- `Wingsjuanka`, Zone 351 `o_hirama_the_west_2`, única `AAEmu.ZoneHost.exe` activa.
- **Recloak** consumió 42876 y 44684, descontó 500 labor y entregó 44773, grado 5, sin soulbind.
- **Uncloak**, opción 4, consumió 44773 y devolvió 44684 Healing, grado 5, soulbound.
- El instance 16777336 permaneció en Inventory/64 a través de salida a selección y nuevo ingreso;
  no reaparecieron 42876 ni 44773.
- La traza de conversión resolvió `set=8, route=4579, products=44773x1@5`; la de reapertura
  registró `picks=[4]` y `received [44684x1@0]`.

Usar esta secuencia como smoke test de regresión. Para aceptación completa se requiere probar ambos
diálogos, verificar el snapshot tipado antes y después, y reloguear; una prueba sólo por comando o
SQLite no sustituye el recorrido del cliente.
