# Integración adaptada del padre r575 — 18 de septiembre de 2026

Se absorbe `AAEmu/AAEmu:client_version/zone-10.0.2_r575` hasta
`30837660a75e4beef5a38f37bf95809edf055f53` sobre `rama_10`, cuyo estado previo era
`86b6d0b46284919ee8ff323cf05f00405e54a1c3`. Se mantiene el historial mediante merge.
La incorporación tiene 139 commits de origen: 116 cambios y 23 merges, incluidos
los últimos PR de asedios, protección sensible y reconstrucción de viviendas.

El [informe de revisión](AA10UpstreamReview20260918_es.md) describe **cada uno de
los 139 commits**, con enlaces, archivos afectados, dependencias y riesgos. Ese
informe registra la evaluación anterior; este documento registra las decisiones
tomadas durante la integración posterior autorizada por el usuario.

## Qué se conserva y qué se combina

| Área | Implementación resultante |
|---|---|
| Creación de personajes | Se conserva byte por byte el cierre de autoridad GM: `X2EnterWorldResponse` escribe `1`, nunca `101`. Permanecen iguales EnterWorldManager, CSCreateCharacter, CharacterManager y las pruebas del handshake. La autorización GM sigue en el servidor. |
| Viviendas | Una única transacción, `TryRebuildHouse`, conserva materiales, impuestos, ambos fondos de trabajo, profesión, propiedad, decoraciones, cambio de plantilla y nombre personalizado. La API del padre delega en ella. |
| Catálogo de remodelación | Los comandos del padre usan una proyección del catálogo nativo ya cargado, sin volver a cargar cinco tablas ni mantener otra autoridad de costes. Se incorpora la resolución del identificador `0xFFFF` desde la vivienda gestionada y la concesión de habilidades del pack al propietario. |
| Wire de remodelación | Se conserva CS tipo 7 con el `housings.id` seleccionado; la corrección SC del padre no reenvía el contexto exclusivo de petición. El campo fiscal `pd` permanece `double`, con entradas reales, en lugar de reinterpretarlo como `ulong`. |
| Seguridad de objetos | Las APIs nuevas delegan en `ItemSecurityService`: elegibilidad nativa, propiedad, contenedor y ranura. El replay al entrar usa las tareas 94/95/96 según bloqueo, espera y vencimiento; se preservan los nueve sockets. |
| Plots | Cola temporal ordenada y liberación atómica del padre, combinadas con visitas por rama, ejecución antes de condiciones hijas y vida del timeline de nuestro fork. Un plot mixto arranca una sola vez y no repite el callback al terminar. |
| Combate | Se respeta `use_condition_bits` en ambos filtros de control de masas. `DamageEffect` transmite su tipo al consumidor de HP/reflexión. La reducción de crítico usa la fórmula calculada; el retraso de casteo suma al tiempo restante. |
| Geometría | Se corrige la incoherencia interna del padre: el ángulo completo se divide por dos antes de comparar el rumbo. Es integración de la interpretación documentada upstream; queda pendiente contraste visual en cliente. |
| Movimiento | Se mantiene la autoridad de Zone para jugadores, monturas y barcos. Los controladores standalone nuevos no pueden competir por su posición. Se conserva el cierre de propulsión del fork y se aplica también a modificadores condicionales sin conversión especulativa. |
| Equipo y rankings | Multiplicadores de gear score en centésimas, catálogo, tablas, consulta, actualización de clasificaciones y registro de actividad. Se conservan `NativeSocketItemIds` y el trabajo realmente gastado de ambos fondos. |
| Buffs y efectos | Se incorporan las mejoras del padre en absorción, reflexión, pilas, condiciones, fórmulas, canales, efectos y sincronización, conservando nuestros cierres de pesca y snapshot inicial de buffs de Zone. |
| Interfaz y contenido | Se absorben contratos de eventos/residencia, filtros de contenido y paquetes de asedios. El tablero de eventos sigue cubriendo principalmente el caso vacío; no se presenta como sistema de eventos completo. |
| Español | Se conserva el cliente principal traducido y su canal `en_us`. Se traducen los tres nuevos rechazos visibles de protección sensible. No se modifican claves de protocolo ni bases/paquetes del cliente. La ayuda de los comandos GM nuevos conserva por ahora el texto upstream. |

## Cambios descartados o pendientes

- **Entrega automática de premios de rankings:** no integrada. El padre entrega
  antes de marcar el periodo, con conexiones independientes, y omite monedas si
  el destinatario está desconectado. Se mantiene la planificación/consulta, pero
  no se entregan premios ni se marcan periodos como pagados. El arranque lo
  anuncia. Requiere un registro durable y entrega transaccional antes de activarla.
- **Reducción de daño AoE con ventana de diez segundos:** retirada de la ejecución
  y del candidato; el propio padre reconoce que ese tiempo es una suposición.
  El catálogo se puede leer, pero no modifica el daño ni crea contadores.
- **Dash, Wandering y Floating:** se excluyen las tres implementaciones nuevas y
  sus pruebas específicas. Su velocidad/duración y significado de columnas se
  basaban en aproximaciones, sin cierre nativo suficiente.
- **`ray_off_set`:** se conserva como dato inventariado, sin sumarlo a la altura
  final de aparición. No se introduce el desplazamiento vertical inferido.
- Segunda contraseña y protección sensible conservan sus flags desactivados;
  `itemSecure` y `rebuildHouse` siguen activos. Butler e ItemSmelting permanecen
  desactivados. El catálogo de interacciones de slaves no implica consumidores
  completos; la pregunta de verificación de bots sigue incompleta.

## Validación y límites

- Estado previo: restore/build Release y **4.638/4.638 pruebas**.
- Se resolvieron 20 archivos con conflictos y se inspeccionaron los solapamientos
  automáticos. La compilación encontró además referencias cruzadas perdidas en
  trabajo, propulsión condicional y replay de buffs; se corrigieron.
- Candidato: restore/build Release y **5.414/5.414 pruebas**, cero fallos y cero
  omitidas. Las pruebas nuevas recorren `DamageEffect.Apply` hasta
  HP, verificando daño positivo, tres golpes y propagación de Magic/Ranged/Siege.
- Migración aditiva aplicada dos veces sobre `aaemu_mergecheck_20260918`:
  cinco tablas nuevas y una columna. Las 46 sentencias de datos existentes se
  conservan lógicamente. La restauración mysqldump normaliza un `-0` de doodad
  a `0`; no hay diferencia de valor ni reescritura de personajes/objetos.
- El contenedor aislado usa esa copia y no publica puertos. La conexión Login
  se apunta a loopback/puerto 9 para que no registre el clon en el Login real.
  Su carga de contenido, redes, servicio y primer refresco de rankings se validan
  en el log de arranque.
- La corrección de creación está preservada y cubierta por pruebas, pero esto
  **no sustituye crear un personaje visualmente en el cliente tras reconectar**.
  Tampoco se declara corregido ningún reporte de combate solo por importar
  commits. La aceptación en cliente de vivienda, combate y movimiento queda
  identificada como prueba pendiente.

## Respaldo, migración y entrega

- Rama de respaldo: `backup/rama_10-before-upstream-20260918-86b6d0b46`.
- Imagen Game anterior: `aaemu-world:rollback-pre-upstream-20260918`.
- Imagen Login anterior: `aaemu-login:rollback-pre-upstream-20260918`.
- Artefactos privados: `E:\AAEmu\rama_10\artifacts\upstream-integration-20260918`:
  dumps, configuración, manifiestos, logs y comparación de creación. Pueden
  contener datos privados; no se incorporan al repositorio.
- Migrador: `Scripts/IntegrateAa10Upstream20260918.py`. Por defecto muestra el
  plan; `--apply` exige Game parado para la base real. No borra tablas ni cambia
  filas de jugadores. La segunda aplicación es inocua.
- Login y Commons no tienen cambios de código en este merge. No se necesita
  reconstruir Login. Se usa la configuración efectiva montada, manteniendo puertos
  y bind mounts.
- No se inicia, detiene ni reinicia ningún proceso Zone. Tras reiniciar World,
  el usuario debe relanzar su perfil de Zones desde Control Center antes de
  probar la entrada al mundo; la creación de personajes no necesita Zones.
- No se publica el merge al remoto en esta entrega.

Game/World se desplegó el 2026-09-18 a las 15:35:32 UTC con la imagen
`sha256:2171ce2e376006cb81b13292c3ace6dc7c3f9b55734a5b204d42239d930da74c`.
El servicio terminó de arrancar a las 15:36:59 UTC. Login conserva su imagen.
Los puertos 1237, 1239 y 1250 aceptan conexiones; se conservaron los bind mounts
y las 21 copias comparadas de configuración. La migración real conserva
**exactamente** las 46 sentencias de datos previas de jugadores, sin siquiera la
normalización de cero observada al restaurar la copia aislada.

Los cuatro mensajes de error de recetas ItemSmelting 29–32 también existen en
la versión anterior; esa función permanece desactivada. No se encontraron
errores nuevos de arranque respecto a la referencia. La aceptación visual del
cliente sigue pendiente como se indica arriba.
