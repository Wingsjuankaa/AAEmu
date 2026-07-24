# Frenzy 10455 — expediente AA8

## Resultado esperado

Frenzy aplica durante 20 segundos el buff `22689`. Cada eliminación realizada
por el dueño mientras el buff está activo extiende en 20 segundos el tiempo
restante, con un máximo de 40 segundos restantes.

Esta conducta no está implementada por ID de skill. Es el resultado de dos
primitivas nativas reutilizables:

- trigger de buff `KillAny`;
- regla de stack `Extend`.

## Cadena nativa

Fuente: compact AA8 descifrada y relaciones nativas recuperadas de `game11`.

```text
skill 10455
  -> skill_effect 54075
  -> effect 70064
  -> BuffEffect 26270
  -> buff 22689
```

Plantilla del buff:

| Campo | Valor |
|---|---:|
| `duration` | 20000 ms |
| `max_life_time` | 40000 ms |
| `max_stack` | 1 |
| `stack_rule_id` | 5 (`Extend`) |

Trigger de eliminación:

```text
buff_trigger 10369
  event_id        = 22 (KillAny)
  source_agent_id = 0 (owner)
  target_agent_id = 0 (owner)
  effect_id       = 70056

effect 70056
  -> BuffEffect 26265
  -> buff 22689
```

La variante ancestral con buff `25650` repite el mismo patrón, con duración
10 s y máximo 20 s. Esa coincidencia confirma que se trata de una regla
transversal y no de una excepción de `10455`.

## Defectos encontrados en el backend

1. `KillAny` existía en el enum, pero no se suscribía a ningún evento.
2. Al morir una unidad, `OnKill` informaba al atacante como atacante y víctima.
3. `BuffStackRule.Extend` existía, pero caía en la ruta genérica de reemplazo.
4. El loader ignoraba `buffs.max_life_time`.
5. Una tarea programada para la expiración anterior podía eliminar el buff
   aunque su duración hubiera sido extendida.
6. No existía `SCBuffUpdatedPacket`, necesario para actualizar el estado
   visual sin retirar y recrear el buff.

## Implementación transversal

- `Unit` emite atacante y víctima reales en `OnKill` y `OnKillAny`.
- `KillBuffTrigger` transporta esos dos agentes al resolvedor nativo de
  `source_agent_id` y `target_agent_id`.
- `Buffs.AddBuff` detecta `StackRule.Extend`, conserva la instancia activa y
  extiende su tiempo restante.
- `Buff.CalculateExtendedRemaining` suma la duración de la reaplicación y
  respeta `max_life_time`.
- La tarea de dispel revalida el tiempo restante antes de expirar el buff.
- `SCBuffUpdatedPacket` serializa el layout AA8 confirmado por
  `x2game.dll FUN_399aa9a0`, opcode `0x1DE`.

## Protocolo de prueba

1. Usar Frenzy y comprobar una duración inicial de 20 s.
2. Matar un objetivo cuando resten aproximadamente 10 s.
3. Comprobar que el tiempo restante suba aproximadamente a 30 s.
4. Matar varios objetivos rápidamente y comprobar que nunca supere 40 s.
5. Seguir eliminando objetivos durante más de 40 s y confirmar que el buff
   puede mantenerse activo sin superar 40 s restantes.
6. Dejar de matar y comprobar que expira al llegar a cero.
7. Repetir después de relog y observar la actualización desde un segundo
   cliente.

## Evidencia de protocolo

Artefactos de análisis estático:

- `E:\AAEmu-Research\output\ghidra-static\opcode-1de-scalars.c`
- `E:\AAEmu-Research\output\ghidra-static\buff-updated-vtable.c`

Campos confirmados de `SCBuffUpdated`:

```text
targetId (BC)
buffId (identificador de instancia)
stack
charged
elapsedTime
reason
```

El campo existe y su ancho está confirmado; la semántica de sus valores
continúa opaca. La actualización normal se emite con el valor base `0` y queda
como punto explícito de observación durante la prueba del cliente.

## Estado

Implementado en backend. Pendiente de validación final dentro del cliente con
la secuencia de prueba anterior.
