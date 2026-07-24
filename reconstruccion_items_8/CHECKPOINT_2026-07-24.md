# Checkpoint — reconstrucción nativa AA8 de objetos y equipamiento

Fecha de corte: 24 de julio de 2026.

Rama:

```text
client_version/8.0.3.12-kakao-r558734-port
```

## Regla de autoridad

El dominio de objetos y equipamiento se reconstruye usando:

1. `compact-client-8.0-decrypted.sqlite`;
2. resultados nativos recuperados desde `game11`;
3. layouts y consumidores confirmados en `x2game.dll`;
4. protocolo observado con el cliente AA8 local;
5. recursos y localización de `game_pak`.

La compact 3.0 no aporta filas, fórmulas, probabilidades ni comportamiento al
runtime AA8. Sólo puede utilizarse como referencia arqueológica.

## Runtime activo

```text
D:\Proyectos\AAemu\client_kakao\
  compact-8.0-runtime-native-equipment-phase-b7-temper-v1.sqlite3
SHA-256:
2B0A147AE1DBFA866FEF18A5CE92F4027BDB0D1173DA54D1531F9254F73B3D25
```

El runtime contiene acumulativamente combate nativo AA8, Fase A de
equipamiento y los catálogos de Fase B hasta Temper B7. La compact generada
permanece fuera de Git; extractores, manifiestos y documentación sí se
versionan.

## Fase A — núcleo de objetos y equipamiento

### Catálogo recuperado

- 21.419 objetos AA8 activos.
- 1.879 armas.
- 4.446 armaduras.
- 399 accesorios.
- 850 mochilas.
- 718 partes corporales.
- 32 holdables, 71 wearables, 16 ranuras y 47 grupos de ranuras.
- 13 grados.
- 495 conjuntos de equipamiento, 247 sets y 938 bonos.
- 2.127 modificadores alcanzables.
- Fórmulas de holdables y wearables resueltas desde la caché nativa de
  `game11`.

Las definiciones se clasifican como `complete`, `phase_a_candidate` o
`catalog_only`. No se permite crear un objeto genérico cuando falta su tipo
concreto AA8.

### Modelos y carga

El backend carga los campos AA8 confirmados para:

- objetos generales y grados;
- armas, armaduras, accesorios y mochilas;
- holdables, wearables y ranuras;
- durabilidad actual y máxima;
- nivel, escalado, fórmulas y modificadores;
- partes corporales y apariencia base;
- detalles persistentes de equipo.

Los `item_body_parts` se cargan como resultado nativo independiente. No
requieren una fila general en `items`; filtrarlos fue la causa del personaje
sin cuerpo y quedó corregido.

### Reglas centrales de equipamiento

`IEquipmentRuleService` y `EquipmentTransitionPlan` son la autoridad para
validar y aplicar transiciones:

- 1H sola;
- dual wield;
- 1H con escudo;
- arma de dos manos;
- transición entre 1H/offhand y 2H;
- rechazo atómico cuando no existe espacio;
- requisitos, ranuras y restricciones;
- actualización de estadísticas y apariencia desde el estado canónico.

Una 2H ya no puede coexistir con secundaria. Los movimientos se calculan
antes de mutar contenedores y no dejan operaciones parciales.

### Sincronización inmediata

Se corrigieron:

- máscaras de las 32 posiciones usando el slot físico real;
- snapshots de inventario y equipamiento;
- `SCUnitStatePacket`;
- `ItemTask` de creación, movimiento y actualización;
- igualdad entre snapshot e `ItemAdd`;
- recuperación autoritativa ante contenedores desincronizados;
- creación con durabilidad válida;
- actualización de estadísticas y observadores al equipar.

Esto eliminó los estados fantasma 2H + offhand y los objetos rojos o rotos
recién creados que sólo se corregían mediante relog.

### Comandos y cobertura

```text
/item8 search <texto> [all|weapon|armor|accessory|consumable] [nivel]
/item8 info <itemId>
/item8 coverage <itemId>
/item8 quarantine list [owner]
/item8 evolution <itemId> [grade]
/item8 regrade <itemId> <grade>
/item8 appearance <itemId>
/item8 salvage <itemId>
/equipment audit [self|target]
/equipment resync [self|target]
```

`/additem` consulta la cobertura AA8, usa grados nativos, crea durabilidad
completa y rechaza IDs históricos o definiciones incompletas.

### Migración y cuarentena

- MySQL fue respaldado antes de la activación.
- Se incorporó `quarantined_items`.
- La auditoría inicial encontró 59 instancias.
- Dos candidatas compatibles se conservaron.
- 57 instancias se aislaron sin reemplazarlas por objetos parecidos.
- La fila original completa y el motivo quedan disponibles para recuperación.
- Los body parts válidos se reconstruyeron desde su catálogo AA8 para no dejar
  personajes invisibles.

## Fase B — sistemas avanzados

### B1 — sockets y lunagems

Catálogo, validadores y paquetes AA8 recuperados. Las mutaciones permanecen
bloqueadas hasta confirmar por completo índice de socket, costo, consumo,
resultado y rollback con el cliente.

### B2/B7 — Temper

La extracción inicial B2 reconstruyó niveles y restricciones. B7 cerró la
operación:

- catalizadores `45914..45917`;
- skills `37723`, `37724`, `39267` y `39268`;
- 31 niveles de escala;
- 37 restricciones;
- 21 costos por ranura;
- fórmula nativa `EnchantScaleCost = 59`;
- probabilidades AA8 en base 10.000;
- validación de target, propietario, tipo, límite, moneda y soporte;
- persistencia de `Item.ScaledA`;
- `SCItemRefurbishmentResultPacket` con layout confirmado.

El resultado y la persistencia funcionan: después de relog el arma conserva el
nivel correcto. Durante las pruebas aparecieron dos fallos distintos de
protocolo incremental:

1. `ItemAction.UpdateDetail` estaba precedido por una longitud inexistente.
2. El bloque fijo de 128 bytes se llenaba con el formato variable del snapshot.

`FUN_39a502f0` y `FUN_3991f540` confirmaron que `UpdateDetail` copia la unión
interna AA8. Para equipamiento:

```text
detail + 0x00  detailType
detail + 0x05  durability
detail + 0x06  chargeCount
detail + 0x0c  chargeTime
detail + 0x3c  scaledA
detail + 0x3e  evolveChance
detail + 0x58  chargeProcTime
detail + 0x60  mappingFailBonus
detail + 0x61  elementLevel
```

También se corrigió el inicio del casteo. El controlador nativo usa
`SkillObject` tipo `6`:

```text
byte flag = 6
uint64 supportItemId
bool autoUseAaPoint
byte inputDirection
```

El backend histórico interpretaba ese tipo como una cadena, desplazando
`SCSkillStartedPacket`. La lectura y escritura byte a byte ya reproducen el
contrato AA8.

Estado al cerrar el día: ambas correcciones están compiladas y desplegadas,
pero todavía no fueron validadas manualmente por el jugador. Temper B7 no debe
marcarse como cerrado hasta comprobar animación y actualización inmediata.

### B3 — síntesis, awakening y reroll

El grafo nativo fue extraído y el catálogo puede consultarse. La mutación está
bloqueada porque el subconjunto activo todavía no cubre todos los objetos,
materiales y destinos referenciados.

### B4 — regrade

Ratios, relaciones y soportes AA8 fueron reconstruidos. El servicio permite
auditar un intento, pero la operación permanece bloqueada hasta cerrar
transacción, protocolo y resultado de rotura.

### B5 — apariencia

Conversiones, relaciones y reactivos están catalogados. Falta confirmar
solicitud, mutación, resultado y reversión antes de habilitarla.

### B6 — salvaging, conversión y smelting

Se recuperaron reactivos, filtros, paquetes, productos, conversiones y
relaciones de smelting. Continúan bloqueados el formato de probabilidades,
algunas referencias nativas ausentes y el protocolo transaccional.

## Validación automática al cierre

```text
Pruebas totales: 135
Resultado:       135 aprobadas
Build Docker:    correcto
Contenedor game: recreado
Registro login:  correcto
RestartCount:    0
```

Las pruebas nuevas fijan:

- máscaras físicas de equipamiento;
- reglas 1H/offhand/2H;
- creación y detalles de objetos;
- equivalencia snapshot/ItemAdd;
- unión interna AA8 de `UpdateDetail`;
- resultado de Refurbishment;
- `SkillObject` tipo 6 de Temper;
- servicios de sockets, Temper, regrade, evolución y salvaging.

## Primera prueba de mañana

Conservar el cliente abierto después de aplicar Temper y verificar, sin relog:

1. aparece el casteo de 1,5 segundos;
2. se reproduce su animación;
3. el arma no cambia a icono corrupto ni estado roto;
4. el nivel pasa inmediatamente, por ejemplo, de `+4` a `+5`;
5. durabilidad, DPS y Equipment Points se actualizan;
6. puede repetirse la operación;
7. el mismo estado persiste después de relog.

Si falla, conservar la sesión y revisar en orden:

```text
CSStartSkill
SCSkillStarted
SCSkillFired
SCItemTaskSuccess / ItemAction.UpdateDetail
SCItemRefurbishmentResult
SCSkillEnded
```

No se añadirán paquetes ni campos por similitud; cualquier corrección deberá
confirmarse nuevamente en el cliente AA8.

## Continuación recomendada

1. Cerrar formalmente Temper B7 después de la prueba manual.
2. Activar sockets/lunagems como siguiente operación aislada:
   - confirmar solicitud C2S;
   - cerrar costo y consumo;
   - confirmar índices visibles;
   - implementar transacción y rollback;
   - desplegar sólo `game`;
   - ejecutar regresión de inventario/equipamiento.
3. Continuar con síntesis/awakening, regrade, apariencia y salvaging, una
   operación por vez.
4. Retirar la excepción staging cuando todas las definiciones necesarias
   alcancen cobertura `complete`.

## Rollback

Para volver al punto anterior:

1. detener únicamente `game`;
2. restaurar `COMPACT_DB` al runtime AA8 previo conservado;
3. restaurar MySQL sólo si la operación bajo prueba mutó instancias;
4. recrear únicamente `game`;
5. verificar registro contra LoginServer.

Nunca reemplazar objetos en cuarentena por equivalencia aproximada.
