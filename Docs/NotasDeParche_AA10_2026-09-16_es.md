# Notas de parche — ArcheAge AA10
## 16 de septiembre de 2026

Esta actualización reúne las mejoras recientes de la comunidad, conserva nuestras reconstrucciones y añade correcciones para barcos, pesca y el bloqueo de acciones detectado después de actualizar.

**Estado actual:** ya se puede entrar y volver a realizar acciones, según la prueba del jugador. Las mejoras que se describen a continuación están incorporadas al servidor y deben poder probarse, salvo las funciones indicadas como desactivadas. La comprobación de cada sistema dentro del juego sigue en curso: estas notas no significan que todos sus recorridos estén confirmados.

## Lo más importante

- Corregido el bloqueo general que impedía iniciar ataques, usar muchos objetos y activar planeadores.
- Corregida la búsqueda de una ubicación para invocar barcos desde la orilla.
- Corregida la causa identificada de una caída de Zone al invocar un barco.
- Incorporadas mejoras de combate, efectos, misiones, fabricación, comercio, familias y gremios.
- Conservados los datos existentes de objetos y las asistencias anteriores durante la actualización.

## Ataques, habilidades y planeadores

- Los ataques y objetos que no necesitan opciones adicionales vuelven a pasar a la ejecución de su habilidad. Este era el fallo común que hacía parecer que todo había dejado de funcionar.
- El planeador debe volver a responder a su activación. Su funcionamiento en vuelo todavía necesita una prueba específica.
- Mejorado el control del tiempo de espera compartido entre habilidades y de las secuencias de ataques.
- Una secuencia de efectos ya no debería finalizar por equivocación otra habilidad que esté ejecutándose.
- Las habilidades concedidas por un efecto temporal están disponibles mientras ese efecto siga activo y se retiran cuando termina.
- Incorporadas correcciones en modificadores de velocidad de ataque, precisión, curación, daño contra jugadores y criaturas, daño de asedio y absorción de daño.
- Corregidos los límites de recursos de combate: un límite reducido a cero ya no permite acumular recursos sin límite.

**Qué comprobar:** un ataque básico, una habilidad normal, un objeto utilizable y, después, el planeador. Que las acciones respondan no confirma por sí solo el daño de todas las habilidades.

## Efectos positivos y negativos

- Mejorado el comportamiento de los efectos que acumulan cargas o aplicaciones.
- Los efectos que deben distinguir a quien los aplica mantienen separadas las aplicaciones de cada personaje.
- Corregida la retirada de acumulaciones para evitar borrar por error el efecto de otro lanzador.
- Los efectos permanentes ya no deberían desaparecer al alcanzar su máximo de acumulaciones por un vencimiento incorrecto.
- Los efectos temporales respetan mejor sus reglas de renovación, ampliación y expiración individual.
- Corregidas condiciones de inmunidad y requisitos para aplicar efectos, incluidos ciertos controles, desplazamientos y pérdidas de maná.
- Incorporadas retiradas de efectos al atacar, recibir daño, invocar, cambiar equipo, desmontar o morir su origen, según las condiciones de cada efecto.
- Conservadas las reacciones de los braseros de Hiram: renovación de acumulaciones, transformación y combinación de sus efectos.

## Barcos y monturas

- La invocación desde tierra busca primero agua cercana. Ya no depende únicamente de que el personaje esté nadando.
- Sigue siendo necesario disponer de agua suficientemente profunda y espacio válido: no todas las orillas permiten invocar un barco.
- El aviso sobre transportar carga ya no debe aparecer cuando la causa real sea falta de agua o espacio.
- Corregida la identificación del barco guardada en su pergamino y su actualización al invocarlo.
- Las velas y otros componentes del casco ya no deberían contar como otro barco que sigue invocado.
- Un barco que se retira o está destruido ya no debería volver a aparecer en el mapa por una actualización pendiente.
- Aplicado el arreglo de ZoneHost para la caída identificada al invocar barcos.
- Incorporadas mejoras en asientos, orientación de componentes, montaje y desmontaje. Se conserva el estado persistente propio de mascotas y barcos.

**Pendiente de confirmar:** invocar Moby Drake y el pesquero de los Daru desde la orilla, mantener la Zone estable, retirar el barco y volver a invocarlo.

## Pesca

- Las cañas comprueban los requisitos de nivel y pericia que les correspondan al equiparlas.
- Los requisitos de uso de una habilidad de pesca se comprueban al utilizarla; no se añaden requisitos de equipo que esa caña no tenga.
- Mejorada la protección de la canalización de pesca, incluida la caña definitiva.
- Conservados el tamaño y peso de los peces al actualizar sus objetos.
- Se mantiene la implementación de bancos de peces y cebado, enganche, tensión y rotura, captura, venta y conversión en trofeo.

**Pendiente de confirmar:** completar una captura desde el barco, vender un pez y convertir otro en trofeo. La auditoría encontró datos e implementaciones para ese recorrido; todavía no se declara la pesca completamente validada en el cliente.

## Objetos, equipo y fabricación

- Mejorada la actualización de cantidades y detalles de objetos en el inventario.
- Se conserva el equipo guardado al cargar un personaje, evitando rechazarlo antes de que estén disponibles sus datos de pericia.
- Incorporado el aprendizaje de recetas mediante objetos y mejorada la lectura de objetos que inician misiones.
- Fabricar comprueba mejor la estación, su estado, la distancia y los permisos necesarios.
- Mejorado el tratamiento de cancelaciones y de fabricación por lotes.
- Las conversiones comprueban la ruta, los materiales y las recompensas correspondientes antes de completar la operación.
- Corregido el cobro duplicado de puntos de trabajo cuando una operación recibe dos avisos de finalización.
- Incorporados cambios de lunagem y límites de nivel por ranura, conservando el formato propio del equipo.
- Se mantiene la reparación de equipo desde el inventario.

## Comercio y paquetes de mercancías

- Incorporado el mercado persistente de especialidades y cargas, con existencias, precios e historial.
- Incorporadas las reglas y eventos de mercado disponibles en esta versión.
- Mejorado el recorrido de los paquetes físicos: fabricación, colocación, transporte y entrega.
- La fabricación de paquetes conserva los datos de origen y frescura necesarios para su venta.
- Corregidas recetas de carga que no entregaban toda su producción.
- Mejoradas las comprobaciones de cobro, entrega y recuperación ante operaciones fallidas.

## Misiones y eventos del mundo

- Mejoradas la aceptación, el progreso y la entrega de misiones, incluidos avisos cuando se rechaza una solicitud.
- Conservados los objetivos y recompensas reconstruidos previamente, combinados con las mejoras comunitarias compatibles.
- Mejoradas las reacciones de objetos de misión para que el progreso de un jugador no altere indebidamente el de otro.
- Mejorado el guardado de efectos pendientes de cinemáticas y su aplicación al volver a entrar al mundo.
- Corregidas cargas duplicadas de datos de misiones y objetos que impedían arrancar el servidor tras la integración.
- Incorporados ciclos programados de zonas en conflicto y correcciones en la participación que cuenta para sus misiones.
- Conservada la coordinación con las defensas de torres y sus cambios de estado.

## Familias y gremios

- Incorporadas mejoras de invitaciones, entrada, salida y expulsión, con comprobación de miembros, capacidad y permisos.
- Mejorado el guardado de integrantes, roles, avisos y progreso familiar.
- Incorporadas comprobaciones de certificados, costes y plazos cuando una operación familiar los requiere.
- Ampliado el soporte de gestión de gremios: reclutamiento, roles, cambios de nombre, contribuciones, actividades e historiales.
- Las recompensas de misiones de familia y gremio se aplican al mismo estado que utiliza su sistema de progreso.

## Vivienda y residencia

- Incorporadas mejoras de venta de viviendas, impuestos y pago anticipado.
- Mejorada la información de vivienda y residencia que recibe el cliente.
- Corregidas comprobaciones de demolición, permisos y conservación de viviendas al conectar una Zone.
- Incorporadas correcciones para imágenes personalizadas de viviendas y otros objetos compatibles.

## Recompensas, ArchePass y correo

- Mejorado el guardado de asistencia y recompensas de eventos, con controles para evitar reclamaciones repetidas.
- La asistencia utiliza el calendario de su campaña; no reutiliza automáticamente una campaña vencida.
- Conservada nuestra implementación de ArchePass y su progreso, combinándola con los cambios compatibles de la comunidad.
- Conservado el funcionamiento propio de Bless Uthstin: páginas, previsualización, aplicación, cancelación y reinicio diario.
- Mejorado el tratamiento de compras, cupones, monedas y recompensas cuando una operación falla al guardar.
- Incorporadas mejoras del correo, de la conservación de mensajes y de la entrega de recompensas por correo.

## Movimiento, portales, música y justicia

- Incorporadas correcciones para reducir parpadeos y movimientos duplicados de personajes y criaturas.
- Mejoradas la escala, altura y representación de criaturas, incluidos ciertos movimientos acuáticos.
- Corregidas comprobaciones de distancia de portales y transiciones al aterrizar o abandonar un asiento.
- La recuperación de experiencia comprueba las condiciones y el coste antes de cobrar y retirar la penalización.
- Incorporadas correcciones de partituras: notas escritas por jugadores, títulos, límites de notas y finalización de la interpretación.
- Incorporada la reconstrucción comunitaria del recorrido de crimen, arresto, juicio, jurado, pruebas, votación y prisión, con controles de participantes y fases. Este recorrido requiere todavía una prueba específica dentro del juego.

## Funciones que siguen desactivadas y pruebas pendientes

- **Farmhand / Butler:** hay mejoras incorporadas en el código, pero el sistema sigue desactivado en este servidor. No se anuncia como función disponible.
- **Item Smelting:** permanece desactivado y fuera del alcance de esta actualización.
- **Disparo de precisión:** existe un reporte previo de que se ejecuta sin hacer daño. No se da por corregido únicamente porque las acciones vuelvan a responder.
- **Barcos y pesca:** siguen pendientes las pruebas completas indicadas arriba.
- **Cliente español:** se mantienen sus traducciones y parches. Esta actualización no publica una nueva traducción completa.

## Orden sugerido para las próximas pruebas

1. Ataque básico y una habilidad normal.
2. Un objeto utilizable y activación del planeador.
3. Moby Drake desde la orilla, retirada y nueva invocación.
4. Repetir con el pesquero de los Daru.
5. Captura, venta y trofeo de pesca.
6. Fabricación y comercio con cantidades pequeñas; después, misiones y sistemas sociales.

Si aparece un fallo, anotar la acción, el nombre del objeto o habilidad, el personaje y el texto exacto del aviso facilita encontrarlo. Conviene terminar cada prueba antes de pasar a la siguiente.

---

**Referencia de esta versión:** integración de 200 commits comunitarios hasta `b439e1cc0`, conservando cambios propios; corrección posterior de acciones en `410d36871`. Compilación y 4.599 pruebas automáticas aprobadas. Las pruebas automáticas no sustituyen la comprobación de cada recorrido dentro del juego.
