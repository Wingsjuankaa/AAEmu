# Checkpoint B2 — Lunascales garantizados AA8

Fecha: 24 de julio de 2026.

## Fuente de verdad

La compact descifrada de Kakao 8.0.3.12 r558734 contiene 15 descripciones en
inglés con la declaración literal:

```text
Lunascales never fail to socket.
```

Esas 15 definiciones se registran en `aaemu_item_socket_policies` con
procedencia `client_compact_8`. El ítem `39072` queda excluido porque su
descripción original no contiene esa garantía.

Los lunagem comunes y refinados continúan bloqueados. El loader activo del
cliente sólo contiene `id`, `fail_break` y `cost_ratio`; las probabilidades
privadas `socket0..socket9` no están en la distribución y no se sustituyen con
datos 3.0.

## Runtime

```text
compact-8.0-runtime-native-equipment-phase-b9-lunascales-v1.sqlite3
SHA-256 BEBE4DAF6BED5CCDB960E83D49C90005AA24FB19E2D200FC2A55CEF660FDE19A
quick_check: ok
integrity_check: ok
```

Dos generaciones consecutivas produjeron el mismo SHA-256.

## Implementación

- `ItemSocketRuleService` distingue políticas garantizadas de probabilidades
  privadas ausentes.
- Se conserva el límite AA8 por ranura y grado y la capacidad física máxima de
  nueve sockets.
- El costo usa `FormulaKind.ItemSocketingCost = 38`, `cost_ratio` y las
  variables confirmadas en `x2game.dll`.
- La instalación garantizada:
  - valida destino, grupo de ranura, grado y nivel;
  - descuenta oro;
  - escribe el primer `socketInfo` libre;
  - envía `ItemTaskType.Socketing` y `SCSocketingResultPacket`;
  - actualiza inventario, equipo y estadísticas;
  - deja el consumo del reactivo al flujo nativo `use_skill_as_reagent`.
- Cualquier rechazo cancela el skill antes del consumo.

## Validación automática

```text
Pruebas:   141
Resultado: 141 aprobadas
Entorno:   SDK/runtime .NET Core 3.1 en Docker
```

## Prueba manual

Usar un Lunascale garantizado compatible, comprobar instalación inmediata,
consumo, costo, estadísticas y persistencia tras relog. Repetir hasta el límite
de sockets del objeto.

Como control negativo, un Lunagem probabilístico debe seguir rechazándose sin
consumo ni modificación del equipo.
