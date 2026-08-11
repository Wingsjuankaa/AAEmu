# Checkpoint AA8 — contexto de pasivas y lifecycle avanzado de buffs

Fecha: 2026-08-09  
Origen del hallazgo: pasivas Battlerage, Bleeding y Frenzy  
Autoridad: Kakao 8.0.3.12 r558734 y captura viva

## Diferencia respecto de Archery

Archery cerró que una pasiva es una raíz independiente y que sus relaciones
`tagged_buffs/tagged_skills` deben reemplazarse por partición exacta. Battlerage
añadió la siguiente frontera: cargar el trigger y sus tags no basta; el
ejecutor debe transportar los agentes del evento, evaluar condiciones
positivas/negativas y respetar el lifecycle del grupo/stack.

## Contexto de agentes

Los eventos Attack, Damage y Kill deben conservar:

- owner del buff;
- source real del evento;
- target real del evento;
- original source cuando exista.

La resolución validada de `*_agent_id` es:

| ID | Agente |
|---:|---|
| 0 | owner |
| 1 | event source |
| 2 | event target |
| 3 | original source |

Antes de ejecutar el efecto se validan los tags requeridos y excluidos de
owner/source/target. Ignorarlos convierte ramas mutuamente excluyentes en un
fan-out simultáneo.

## Caso Bleeding

Attack Speed Training, pasiva Battlerage `29`, usa:

`buff 811 → effect 56457 → buff 11344 → proc Bleeding 5 %`

El proc es nativo, no fantasma. El defecto histórico ignoraba
`target_agent_id=2` y condiciones de tag; aplicaba al dueño y disparaba varias
etapas. El contrato corregido exige:

- sin pasiva/buff raíz: cero proc;
- con la pasiva: tirada determinista del 5 %;
- target: enemigo golpeado;
- un solo rango de Bleeding activo;
- traza con pasiva, buff requerido, tirada, target, rango y descarte.

## Exclusión por grupo y rango

Los buffs `242/514/515/516/517` pertenecen al mismo `group_id=10` con rangos
1..5. `Buffs.AddBuff` debe:

- rechazar una etapa inferior;
- reemplazar otro miembro del grupo al avanzar;
- dejar que la regla de stack gobierne sólo la reaplicación del mismo
  `buff_id`;
- impedir coexistencia, triggers duplicados y realimentación.

La presencia de varias filas relacionadas no significa que deban coexistir.
Auditar siempre `group_id/group_rank` antes de interpretar una progresión como
cinco procs independientes.

## Stack `Extend` y duración máxima

Frenzy `10455` aportó una segunda semántica, distinta de `Multiple`:

- buff `22689`: 20 s, `stack_rule=Extend`, `max_life_time=40 s`;
- trigger `KillAny`: reaplica el mismo buff al owner;
- cada kill suma 20 s al restante sin superar 40 s;
- la instancia se conserva y se actualiza, no se retira/recrea.

La implementación reusable requiere:

1. emitir atacante y víctima reales en `OnKill/OnKillAny`;
2. suscribir `KillAny`;
3. cargar `max_life_time`;
4. extender el restante con clamp;
5. hacer que la tarea de expiración revalide el tiempo restante, porque una
   tarea antigua no puede retirar una instancia extendida;
6. publicar `SCBuffUpdated 0x1DE` para refrescar el cliente.

## Evidencia negativa preservada

- icono o tooltip no prueba que el modifier/trigger se ejecutó;
- aplicar siempre al owner ignora la semántica del evento;
- omitir tags negativos produce fan-out;
- tratar `Extend` como replace pierde la duración acumulada;
- reprogramar sin revalidar deja tareas antiguas capaces de expirar el buff;
- cinco rangos de un grupo no son cinco buffs simultáneos.

## Gate obligatorio para ramas futuras

- pasiva ausente/presente;
- owner/source/target/original source;
- tags positivos y negativos;
- probabilidad con semillas deterministas;
- mismo buff versus otro rango del grupo;
- `Multiple`, `Extend` y replace como contratos distintos;
- duración inicial, extensión, cap y expiración final;
- actualización visual, segundo uso y relog.

