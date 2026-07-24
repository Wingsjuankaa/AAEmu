# Reconstrucción de la cuarentena AA8

Fecha: 2026-07-23

## Recuperado desde fuentes AA8

De las 57 instancias inicialmente puestas en cuarentena se restauraron 16:

- 5 body parts de los personajes: cuerpo, rostro y cabello.
- 11 objetos genéricos AA8 (`impl_id=0`), entre ellos Coinpurses y
  contenedores de equipo no identificado.

Junto con las dos instancias que nunca salieron de `items`, el inventario
activo contiene ahora 18 filas. Todas las restauraciones mantienen la copia
original en `quarantined_items` y registran `restored_at`.

## Pendiente

Quedan 41 instancias, correspondientes a 31 IDs únicos que no aparecen en el
resultado general `items` del cliente AA8:

- 25 instancias de armas o armaduras antiguas. `game11` conserva sus filas
  concretas como datos residuales, pero no conserva una definición base AA8
  activa con nivel, grado, reglas y atributos completos.
- 16 materiales, suministros iniciales y objetos de misión retirados del
  catálogo AA8.

No se restauraron porque hacerlo exigiría copiar la definición base desde la
compact 3.0 o inventar una equivalencia moderna. Ambas opciones violan la
autoridad nativa AA8.

## Siguiente cierre

La vía correcta es reconstruir `character_supplies` y las reglas de creación
de personaje desde `game11`, identificar el conjunto inicial vigente en AA8 y
crear una migración explícita. Los objetos antiguos seguirán preservados en
cuarentena hasta que exista una correspondencia confirmada; no se perderán ni
se reemplazarán automáticamente.
