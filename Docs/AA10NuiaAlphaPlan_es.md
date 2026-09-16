# Alpha de Nuia: planificación y primer barrido

Fecha: 2026-09-15. Producto: Returns 10.0.2.13 r575, cliente principal es_ES.

Actualización de actividades: [reparación de misiones amarillas](AA10NuiaYellowQuestRepair_es.md),
con posiciones regionales, invocación de NPC y consumo de objetos plantables;
aceptación jugable pendiente.

## Objetivo y estado

Ofrecer una alpha centrada en **nuianos, elfos y enanos dentro de Nuia**, con
progresión, combate y actividades de vida que se puedan probar sin cargar otros
continentes. Priorizar recorridos completos y reproducibles sobre el número de
funciones habilitadas.

La planificación y la primera reparación de datos están realizadas. **Elfos y
enanos todavía necesitan aceptación jugable completa**; una suite verde y un
catálogo completo no prueban cinemáticas, fases personales ni transiciones.
La aceptación nuiana existente es el control de regresión y no se transfiere
automáticamente a las otras razas.

El alcance Nuia es una decisión de producto. Este cambio no ha implementado un
bloqueo global de creación de otras razas, portales ni desplazamientos. Esa
restricción debe cerrarse antes de invitar jugadores a una alpha geográfica cerrada.

## Resultado del barrido

| Cadena | Misiones | Actos habilitados | Resultado estático actual |
|---|---:|---:|---|
| Elfos, categoría 8, capítulos 0–6 | 54 | 329 | Sin detalles ausentes ni actos sin clase/loader; posiciones nativas auditadas cubiertas en fuente y runtime |
| Enanos, categoría 93, capítulos 0–6 | 68 | 449 | Mismo gate; pendientes específicos de interacción y transformación |
| Continuación compartida compatible, categoría 131 | 76 | 376 | Inventariada para identificar el corte geográfico; incluye contenido fuera del alpha |

`quest_contexts.race` es una máscara: elfo=8, enano=4. Se incluyen las misiones
compartidas con `(race & 12) != 0`; no se confunden estos valores con los enums
Elf=4 y Dwarf=3. Se conserva Nuian=1 como regresión ya documentada.

- 198 misiones, 1.154 actos habilitados, cero detalles ausentes o discrepantes
  entre full y compact para los actos examinados.
- 91 templates doodad relacionados, 334 posiciones main_world y cuatro posiciones
  en otros mundos en el escaneo. La presencia de una dependencia no prueba su uso
  obligatorio: puede ser alternativa de un grupo o recompensa opcional.
- **270 posiciones de 43 templates restauradas** en un overlay: 120 faltaban en
  fuente y runtime, 143 existían solo en fuente y siete solo en runtime. Por eso
  copiar indiscriminadamente el catálogo general no era una reparación acotada.
- Tras sincronizar el overlay, no quedan huecos de posiciones nativas observadas
  en las 122 misiones raciales. Los dos huecos restantes del barrido ampliado se
  relacionan con las misiones compartidas 7147/7148/8551, posteriores al corte.
- 223 de 224 NPC referenciados tienen fuente en el corpus nativo de spawners;
  NPC14750/quest6584 queda sin fuente demostrada y fuera del recorrido inicial.
  Se verificaron por MD5 las 180 entradas del corpus contra el paquete Zone actual.
- Los 139 objetos referenciados tienen metadatos de suministro. Dieciséis aparentes
  ausencias eran recompensas selectivas; se corrigió el auditor para incluirlas.
  Esto no demuestra todavía acceso al proveedor, disponibilidad ni entrega efectiva.
- 2.053 textos de títulos, variantes, objetivos y diálogos coinciden con los JSONL
  contextuales aprobados en la compact suelta del principal. El TM generado estaba
  atrasado; el auditor da prioridad al JSONL editorial. Falta QA visual y no se
  declara reextracción del game_pak en esta tarea.

El overlay conserva XYZ, escala, rotación nativa y el único grupo Start probado
en full/compact. El cargador existente da prioridad a overlays y elimina duplicados
por template/posición. No se inventan NPC ni se salta a fases visibles finales.

## Corte de historia compatible con Nuia

La historia racial 0–6 de ambas razas tiene sus zonas de catálogo en Nuia. La
continuación compartida sigue dentro de Nuia durante los capítulos 7 y 8 y hasta
7138 en el capítulo 9. **7139, «Un objetivo en movimiento», señala
`e_lokas_checkers_2` (zoneKey246), fuera de Nuia.**

Propuesta de alcance de lanzamiento: capítulos raciales 0–6 y continuación hasta
7138, después de probar sus dependencias espaciales. La misión 7137 ya se titula
«Al otro lado del mar»: comprobar en cliente cuándo empieza realmente el viaje
y colocar el aviso/límite antes de ese cruce si sucede antes de 7139. La zona del
catálogo orienta el corte; no sustituye comprobar objetivos, teleports e instancias.

No anunciar historia 1–17 completa ni Hiram/Auroria/Garden en esta alpha. Un
capítulo posterior que vuelve a Nuia no elimina sus prerrequisitos exteriores.

## Orden de trabajo y puertas de salida

| Orden | Entrega | Prueba de salida |
|---|---|---|
| P0.1 | Datos y arranque de las tres razas | Crear ambos géneros; posición inicial, introducción, NPC y primera misión correctos; sin duplicados |
| P0.2 | Elfos 0–6 | Recorrido con personaje nuevo, sin completar misiones por GM; guardar evidencia por misión y relog por capítulo |
| P0.3 | Enanos 0–6 | Mismo recorrido, más transformación racial, uso de habilidades transformado y restauración al terminar/morir/relog |
| P0.4 | Límite Nuia y continuidad 7–9 | Probar ramas de entrada 7115/7116/8376, cruce 7137–7139, portales, recall, barco y conexión con destino apagado |
| P0.5 | Presupuesto de RAM y concurrencia | Sesión con el cliente y la concurrencia prevista; medir picos, guardado y reentrada, sin paginación sostenida ni caída de Zone |
| P1.1 | Combate y progresión de equipo | Misiones, loot, oro/EXP, muerte, curación, buffs, cambiar equipo; recompensa selectiva y bolso lleno |
| P1.2 | Vida en Nuia | Recolección, siembra/crianza, labor, crafting, vivienda e impuestos, permisos entre dos cuentas |
| P1.3 | Viaje y social | Montura/mascota, planeador, recall, grupo, comercio/correo y sesión de dos jugadores |
| P2 | Actividades opcionales | Comercio terrestre, pesca, embarcaciones costeras e instancia concreta, solo tras probar su recorrido y coste de memoria |

No abrir todas las actividades P2 por disponer de un objeto en el catálogo alpha.
Housing H5-B, funciones pendientes y cualquier instancia conservan sus gates
propios. Item Smelting continúa excluido. Las reparaciones previas de Hiram pueden
reutilizarse como primitivas, pero Hiram no se presenta como contenido territorial
de Nuia.

### Recorridos raciales y particiones

Son zoneKey nativos derivados de los contextos de misión, no todos los sectores
adyacentes que pudiera atravesar el jugador. Antes de cada sesión confirmar la
partición por su posición persistida y por `ZoneLoaded`/entrada al mundo.

| Recorrido | Capítulo | Misiones | zoneKey de catálogo |
|---|---|---:|---|
| Elfo | Introducción + 1 | 6 | 129, 182 |
| Elfo | 2 | 10 | 129, 182 |
| Elfo | 3 | 10 | 144, 182, 195 |
| Elfo | 4 | 14 | 140, 143, 144, 185 |
| Elfo | 5 | 5 | 143, 183, 244 |
| Elfo | 6 | 9 | 133, 183, 186 |
| Enano | Introducción + 1 | 13 | 328 |
| Enano | 2 | 9 | 150 |
| Enano | 3 | 9 | 150 |
| Enano | 4 | 10 | 154, 192, 193 |
| Enano | 5 | 14 | 154, 183, 192 |
| Enano | 6 | 13 | 192, 193 |

Los spawners de 129/150/154/192/193/328 ya están preparados, copiados de entradas
nativas verificadas. Preparar archivos no equivale a haber probado la carga de
esas Zones. El inicio inicial declarado por `characters` es 129 para elfo y 328
para enano, en ambos géneros.

### Casos prioritarios para la prueba manual

- Elfos: actor14178 (2387/2388/2396/2401), actor14177 (213/2391/2392),
  actor14199 (2403/2505/2506/2527/4490), actor14211 y piedra14212
  (3885–3889), actor14231 (3504/4519).
- Enanos: actores14206/14207/14208 (3485–3489), 14218/14219 (3499–3502),
  actor14106 (5796–5798); recolección y objetos personales distribuidos por
  los perfiles nativos 328/150/154/192/193 de la tabla.
- Seis templates ligados a estas razas no tienen posición de celda demostrada:
  1368→5791; 4614→3889; 11987→5801; 14224→5785/5786; 15460→2519;
  17261→3498. No se añaden coordenadas inventadas. Revisar proveedor dinámico,
  alternativa de grupo o referencia antigua antes de calificarlos como bloqueo.
  La búsqueda directa `spawn_effects`/`doodad_func_spawns.sub_type` no los encontró;
  `interaction_effects6551` refiere 11987, lo que por sí solo no prueba un spawn.
- Probar dos personajes sobre el mismo objeto `once_one_man`: el avance de uno
  no debe alterar la fase, modelo o disponibilidad del otro.

## RAM y operación

Nuia contiene **38 particiones de catálogo**. El continente no equivale a un
único proceso. El barrido racial elf/dwarf usa 16 zoneKey distintos, pero no es
necesario cargarlos todos para una sesión por capítulo.

Medición inicial de esta tarea: Windows tenía aproximadamente 63,8 GiB físicos
y 27,4 GiB libres; Game usaba 2,65 GiB en Docker. Los dos ZoneHost observados
tenían 1,20/1,33 GiB privados y un working set mucho menor. Es una fotografía,
no un pico bajo jugadores, y no permite extrapolar capacidad por multiplicación.

Propuesta de operación inicial:

1. Sesiones por recorrido de la tabla, activando solo las particiones necesarias
   y las adyacentes demostradas. El usuario conserva el lifecycle de Zones en
   Control Center.
2. Medir arranque, 15 minutos en reposo y 30–60 minutos jugando con cliente abierto:
   memoria privada/commit, física disponible, hard faults, pausas, heartbeat y
   tiempos de guardado. Repetir con la concurrencia que se quiera admitir.
3. Reservar inicialmente el mayor de 8 GiB o 20% de la RAM física para sistema,
   cliente y variación; tratarlo como objetivo operativo a ajustar con medición.
4. Autorizar otra partición solo si el pico medido mantiene ese margen. Publicar
   el máximo simultáneo y el recorrido disponible en cada sesión.
5. Antes de reducir zonas, resolver jugadores guardados y destinos de regreso.
   Validar que una entrada o teleport a una partición apagada falla sin perder
   al personaje. No cerrar procesos saludables para conseguir memoria sin coordinarlo.

El despliegue de esta tarea reinicia únicamente Game para leer el catálogo.
No inicia, detiene ni relanza ZoneHost. La reconexión/relanzamiento de los perfiles
que se quieran probar queda en Control Center.

## Protocolo de aceptación y diversión de la sesión

Separar personajes de progresión normal y personajes con acceso al panel α.
El primero permite encontrar fallos de suministros, labor, dinero y recompensas;
el segundo acelera pruebas dirigidas de crafting/equipo/vivienda sin falsear
la aceptación de la historia.

Para cada misión registrar: personaje/raza, ID y capítulo, build y hashes,
zoneKey/posición, aceptación, objetivo, diálogo, recompensa, siguiente misión,
relog cuando corresponda, resultado y reporte asociado. Usar **Reportar un error**
y conservar el ID. La consulta inicial de pendientes de categoría quest solo
devolvió reporte3/10029, en Garden, sin incidencia específica elf/dwarf; no es
prueba de ausencia de errores ni un inventario de reportes cerrados.

Sesión recomendada tras cerrar P0: historia y combate al comienzo, actividad de
vida en una zona ya cargada y una prueba cooperativa al final. Rotar grupos por
recorridos para ampliar cobertura sin ampliar simultáneamente los procesos.

**Gate de invitación:** cero bloqueos conocidos en el recorrido publicado,
recompensas sin duplicación, guardado/relog correctos, aislamiento entre dos
jugadores, límite geográfico probado, RAM medida y rollback verificado.

## Evidencia y reproducción

### Misiones amarillas

El barrido adicional y la cola por mecanismos están en
[AA10NuiaYellowQuestAudit_es.md](AA10NuiaYellowQuestAudit_es.md).
Separa 1.184 candidatas regionales de 1.383 entradas asignadas a la zona genérica,
y prioriza bote 2393 y caballo 4292/4294/4295. Esa auditoría es diagnóstica:
no añade objetos a la carga de memoria ni declara aceptación en cliente.

- Script de barrido: `reconstruccion_cliente_10/scripts/audit_nuia_alpha.py`.
- Builder: `reconstruccion_cliente_10/scripts/build_nuia_alpha_placements.py`.
- Fixture nativa: `AAEmu.UnitTests/Fixtures/nuia_alpha_r575_placements.csv`.
- Prueba: `NuiaAlphaQuestPlacementTests` comprueba geometría, escala, fase,
  unicidad y deserialización del catálogo contra la fixture extraída.
- Evidencia por misión: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/nuia-alpha-20260915/quest-matrix.csv`.
- En esa misma carpeta: `audit-before.json`, `audit.json`, `native-contracts.json`,
  `all-world-placements.csv`, `supplier-coverage.json`, `localization.json`,
  `npc-corpus-verification.json`, `placement-build.json`, `deployment.json` y logs.

Primero ejecutar el auditor para obtener `requested-ids.txt`; usar PakDoodadScan
contra el game_pak r575 con esos IDs y `--all-worlds`. Conservar el resultado
completo como `all-world-placements.csv` y filtrar main_world en `placements.csv`.
Reejecutar el auditor. El builder consume el `audit-before.json` congelado y
rechaza cambios de identidad de las SQLite. El auditor posterior debe conservar
en cero los huecos raciales. Los archivos de NPC usados por el auditor de
suministros deben corresponder al corpus verificado contra `zone-pak-index.csv`.

Rollback: quitar únicamente los archivos nuevos enumerados en `deployment.json`,
tras comprobar que conservan su hash `after`, y reiniciar Game para retirar el
overlay. Los seis spawners no alteran el runtime mientras sus Zones no se inicien.
DB, compact, cliente y paquete no se modificaron. La imagen Docker se conserva.
