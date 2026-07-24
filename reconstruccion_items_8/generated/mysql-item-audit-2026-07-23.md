# Auditoría de objetos persistidos antes de AA8 nativo

Auditoría **sólo lectura** realizada sobre `aaemu_game.items` y comparada con
`compact-8.0-runtime-native-equipment-v1.sqlite3`.

No se movió, eliminó ni normalizó ninguna instancia.

| Clasificación | Templates | Instancias |
|---|---:|---:|
| ID inexistente en el catálogo del cliente AA8 | 36 | 46 |
| ID AA8 presente, tipo concreto todavía no recuperado | 10 | 11 |
| Definición concreta AA8 candidata de Fase A | 2 | 2 |
| **Total** | **48** | **59** |

Además:

- 22 instancias están equipadas.
- 37 instancias están en inventario.
- No existen objetos cuyo `owner` esté ausente de `characters`.
- `quarantined_items` todavía no existe en la base activa.

Conclusión: activar ahora el runtime nativo obligaría a aislar 57 de las 59
instancias. Por eso la migración permanece en modo seco y la compact candidata
continúa marcada como no desplegable.
