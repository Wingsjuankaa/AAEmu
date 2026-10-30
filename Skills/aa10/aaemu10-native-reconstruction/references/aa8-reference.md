# Uso selectivo de AA8

AA8 y AA10 son clientes x64 relativamente próximos y comparten motor y muchas
familias de entidades. Esto permite reutilizar análisis, patrones nativos,
primitivas de lifecycle y código server, pero no garantiza compatibilidad.

## Orden

1. Definir la clausura y evidencia AA10.
2. Inspeccionar upstream padre.
3. Inspeccionar el cambio equivalente en `rama_8`, sus tests, manifest y
   dossier forense.
4. Comparar campo, transición, ownership, cleanup, persistencia y wire.
5. Clasificar cada parte y portar sólo el mínimo confirmado.

## Clases

- `generic_x64_compatible`: algoritmo sin dato/wire de versión.
- `aa10_confirmed_shared_primitive`: AA10 prueba la misma primitiva.
- `structural_candidate`: forma útil, prueba AA10 incompleta.
- `version_sensitive_blocked`: packet, ID, schema, fórmula, timing o branch.
- `aa8_only`: no existe o contradice AA10.

No copiar compacts, filas, opcodes, packet layouts, balance, tiempos, rates,
fórmulas ni allow-lists AA8. Registrar commit/ruta AA8 consultados y evidencia
AA10 independiente.

El inventario inicial detectó alrededor de 50 commits AA8 con lógica potencial,
agrupados en items/Hiram, housing/doodads, crafting/quests/summons y
movimiento/skills. Son candidatos de reimplementación, no cherry-picks C#.
