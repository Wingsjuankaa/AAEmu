# Puertas de QA

## Unidad

- Identidad compuesta y fuentes con hash.
- Contexto y relaciones presentes.
- Variables, posiciones, colores, tags, escapes y saltos conservados.
- Números y porcentajes explicados si cambian.
- Terminología compatible con el glosario.
- Sin mojibake, NUL ni etiquetas desbalanceadas.
- Longitud revisada contra el widget real cuando corresponda.

## Vertical

- Flujo completo traducido, incluidos errores y estados vacíos.
- Objetos, habilidades, buffs, NPC y diálogos relacionados consistentes.
- Búsqueda y ordenación toleran acentos.
- Inglés/CJK residual clasificado como error, nombre conservado o texto fuera de alcance.

## Build

- Dry-run limpio y número esperado de cambios.
- Solo cambia el canal objetivo y recursos manifestados.
- SQLite íntegro; ALB recompilable; imágenes con formato correcto.
- Entrada de paquete dentro de capacidad o relocalización validada.
- Reextracción idéntica a la entrada aprobada.
- Segunda aplicación sin cambios.
- Rollback restaura hashes exactos.

## Cliente

- Login, HUD, opciones, inventario y cadena piloto completos.
- `áéíóúüñ¿¡` visibles en fuentes y tamaños reales.
- Sin recortes, solapamientos o saltos incorrectos.
- Teclas, variables, cantidades, monedas y porcentajes correctos.
- Relog, cambio de Zone y reinicio conservan el idioma.
- Mecánicas y parches previos no cambian.
