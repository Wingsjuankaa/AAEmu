# Checkpoint B1 — sockets y enchanting gems AA8

Fecha: 24 de julio de 2026.

## Punto de partida validado

Temper B7 queda cerrado:

- casteo y animación correctos;
- mejora y detalle visibles sin relog;
- costo, porcentaje y nivel se refrescan;
- se pueden ejecutar intentos consecutivos;
- la liberación transversal del estado de habilidad también corrigió el
  bloqueo progresivo del combate.

## Hallazgos nativos B1

La fuente de verdad continúa siendo el cliente Kakao 8.0.3.12 r558734.

`x2game.dll` confirmó:

```text
gemInfo       = detalle +0x08 = GemIds[1]
socketInfo[0] = detalle +0x18 = GemIds[4]
socketInfo[8] = detalle +0x38 = GemIds[12]
```

Por tanto:

- hay un único campo de enchanting gem;
- existen nueve sockets físicos;
- los otros ocho campos de extensión no son sockets y no consumen capacidad.

La función `FUN_39a4dde0` cuenta esas nueve posiciones y calcula el costo con
la fórmula 38, el multiplicador de unidad 258 y el `cost_ratio` del chance set.

## Implementación

- `EquipItem` expone el enchanting gem y las nueve posiciones AA8 sin
  solaparlas.
- `ItemSocketRuleService` cuenta y limita únicamente los sockets nativos.
- El costo nativo de lunagem quedó implementado desde la fórmula del runtime.
- `MagicalEnchant` instala el enchanting gem en `GemIds[1]`, envía
  `ItemAction.UpdateDetail`, actualiza bonos si el objeto está equipado y
  responde con `SCEnchantMagicalResultPacket`.
- La consumición del reactivo continúa en el flujo normal de skill mediante
  `use_skill_as_reagent`; no se duplica en la interacción.

## Bloqueo conservado

Los lunagems probabilísticos no mutan objetos todavía. Esta distribución
contiene las ocho filas cortas de `item_socket_chances`, pero no los campos
`socket0..socket9`. La búsqueda completa sobre los segmentos recuperados de
`game0`, `game2`, `game6`, `game7` y `game11` tampoco encontró las filas
largas.

Se mantiene el fallo cerrado porque sin esos valores no se puede confirmar:

- éxito o fallo por número de socket;
- rotura cuando `fail_break` está activo;
- rollback y resultado económico exactos.

No se utiliza la compact 3.0 como fallback.

## Validación automática

```text
Pruebas:   140
Resultado: 140 aprobadas
Entorno:   SDK/runtime .NET Core 3.1 en Docker
```

Las nuevas regresiones fijan:

- nueve sockets en `GemIds[4..12]`;
- campos de extensión externos sin impacto en la capacidad;
- enchanting gem independiente de los sockets;
- límites y chance indexados por la ocupación física real.

## Prueba manual siguiente

Después del despliegue:

1. obtener un enchanting gem AA8 cuya cobertura no use `eiset` ni item tags;
2. aplicarlo a un arma compatible;
3. confirmar resultado inmediato sin relog;
4. comprobar tooltip, estadísticas y persistencia tras relog;
5. reemplazarlo por un segundo enchanting gem y repetir;
6. verificar que los sockets continúan vacíos e independientes.

Los lunagems deben mostrar el mensaje de bloqueo nativo y no consumir el
reactivo mientras falten sus probabilidades.

El rechazo marca el casteo como cancelado antes de que `Skill.ScheduleEffects`
procese `use_skill_as_reagent`, evitando que una operación bloqueada consuma el
lunagem.
