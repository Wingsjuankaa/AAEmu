# Contrato común de habilidades AA8

## Propósito

Este documento es la referencia operativa para reparar una habilidad de
ArcheAge 8.0 sin introducir datos o comportamientos heredados de la compact
3.0. Reúne las variables y rutas de ejecución confirmadas durante la
reconstrucción de Battlerage, Swiftblade y las correcciones transversales del
runtime.

No reemplaza los manifiestos generados: define cómo interpretarlos, qué debe
comprobarse y cuándo una habilidad puede considerarse terminada.

## Autoridad y política de no inferencia

Orden obligatorio de autoridad:

1. `compact-client-8.0-decrypted.sqlite`;
2. filas nativas recuperadas desde `game11`;
3. layouts y semántica confirmados en `x2game.dll`;
4. paquetes y comportamiento observados con el cliente 8.0 local;
5. recursos de `game_pak` para animación, sonido y FX;
6. `develop` y compact 3.0 sólo como referencia de implementación histórica.

Reglas:

- No copiar una fila 3.0 para completar una dependencia AA8.
- No asignar significado a un campo `unk`, `valueN` u objeto comprimido sin
  evidencia del cliente.
- No codificar una animación, radio, daño, buff o desplazamiento por ID de
  habilidad si existe una relación nativa que lo describe.
- Si falta una dependencia, aislar la habilidad e informar la cadena exacta.
- Toda corrección de backend debe implementarse en la primitiva genérica
  correspondiente y cubrirse con una regresión.

## Modelo de una habilidad

Una habilidad no es solamente una fila de `skills`. Su clausura ejecutable es:

```text
ability
  -> skill visible
  -> skills internas, variantes y reemplazos
  -> skill_effects
  -> effects
  -> concrete effects
  -> buffs, modificadores, triggers y ticks
  -> plot
  -> eventos, condiciones, destinos y transiciones
  -> aoe_shapes
  -> anims, skill_controllers y projectiles
  -> paquetes AA8 que presentan la transición al cliente
```

La clausura se recorre hasta un punto fijo. Un trigger puede alcanzar otro
efecto, que puede alcanzar otro buff o skill interna.

## Variables por capa

### 1. Identidad, aprendizaje y costo

| Variable | Función |
|---|---|
| `id` | ID nativo de la skill o variante. |
| `ability_id` | Especialidad propietaria. |
| `show` | Visibilidad en la interfaz; no basta para decidir si una skill interna debe importarse. |
| `auto_learn`, `need_learn` | Flujo de aprendizaje. |
| `ability_level`, `level_step` | Requisitos y escalado de nivel. |
| `req_points`, `skill_points` | Requisitos y consumo de puntos. |
| `mana_cost`, `mana_level_md` | Costo base y componente de escalado. |
| `consume_labor_power` | Costo de labor. |
| `cooldown_time`, `cooldown_tag_id` | Cooldown individual y compartido. |
| `ignore_global_cooldown`, `default_gcd`, `custom_gcd` | Política de GCD. |

### 2. Selección y validación del objetivo

| Variable | Función |
|---|---|
| `target_type_id` | Tipo lógico de objetivo requerido por la skill. |
| `target_selection_id` | Método de selección. |
| `target_relation_id` | Relación permitida entre caster y objetivo. |
| `min_range`, `max_range` | Rango válido. |
| `valid_height`, `target_valid_height` | Restricción vertical. |
| `target_area_count` | Límite de unidades. |
| `target_area_radius`, `target_area_angle`, `target_angle` | Área declarada por la skill. No sustituyen la geometría de un plot. |
| `target_dead`, `target_alive`, `target_water`, `target_only_water` | Estado requerido del objetivo. |
| `check_terrain`, `source_not_collided` | Requisitos del entorno. |

La relación debe evaluarse mediante el mismo dominio de
`SkillTargetRelation` usado por el cliente. Los filtros genéricos no deben
eliminar unidades antes de que la relación nativa sea evaluada.

### 3. Tiempo, animación y presentación

| Variable | Función |
|---|---|
| `casting_time` | Tiempo de casteo previo. |
| `channeling_time`, `channeling_tick` | Duración y pulsos de canalización. |
| `effect_delay`, `effect_speed` | Momento del impacto; la velocidad puede aportar retraso por distancia. |
| `effect_repeat_count`, `effect_repeat_tick` | Repetición del efecto. |
| `fire_anim_id` | Animación base enviada en `SCSkillFired`. |
| `twohand_fire_anim_id`, `dual_wield_fire_anim_id` | Variantes por disposición de armas. |
| `start_anim_id` | Animación de inicio definida por la skill. |
| `use_anim_time` | Incorpora `CombatSyncTime` de la animación elegida al retraso autoritativo. |
| `match_animation` | Indica coordinación adicional con la animación. |
| `skill_controller_id` | Controlador de movimiento o transición. |
| `skill_controller_at_end`, `end_skill_controller` | Momento y cierre del controlador. |

La animación de la skill y la animación de un controlador son dominios
distintos. Si `fire_anim_id=0`, no se debe sustituir por
`skill_controller.start_anim_id`: el cliente puede iniciar esa animación como
parte del controlador.

La variante de arma se selecciona así:

```text
TwoHanded   -> twohand_fire_anim_id si existe
DualWielded -> dual_wield_fire_anim_id si existe
otro caso   -> fire_anim_id
```

### 4. Plots y condiciones

| Variable | Función |
|---|---|
| `plot_id`, `plot_only` | Grafo autoritativo; `plot_only=1` impide tratar la skill como una lista directa de efectos. |
| `plot_event.id`, `kind_id` | Evento y operación que realiza. |
| `source_id`, `target_id` | Objetos de entrada y salida del evento. |
| `target_count`, `aoe_shape_id` | Cantidad y geometría de selección. |
| `relation_id`, `unit_count`, `unit_type_mask` | Filtro nativo del conjunto AoE. |
| `delay`, `weight`, `combat_resource` | Temporización y parámetros del evento. |
| `plot_condition.kind_id` | Tipo de condición. |
| `not_condition` | Invierte el resultado después de evaluar la condición. |
| `param1..param4` | Parámetros cuyo significado depende exclusivamente de `kind_id`. |
| `plot_next_events` | Transiciones; pueden ser por objetivo y producir ramas diferentes. |

No interpretar `param1..param4` globalmente. Ejemplo confirmado:

- Hammer Toss `18757`, plot `440`;
- condición `10733`;
- `kind_id=2` (`Relation`);
- `param1=5` (`Others`);
- `not_condition=1`;
- el resultado distingue el objetivo primario de los enemigos cercanos:
  el primario recibe stun y los secundarios siguen la rama de knockback.

### 5. Efectos y buffs

Para cada `skill_effect` o `plot_effect` se debe comprobar:

- `effect_id` y tipo concreto;
- origen y destino;
- retraso y orden;
- probabilidad y condiciones;
- fórmula y escalado;
- buff o skill interna alcanzada;
- efecto autoritativo y presentación al cliente.

Para cada buff:

| Grupo | Variables relevantes |
|---|---|
| Plantilla | duración, stacks, tags, icono y grupo FX |
| Modificadores | `owner_type`, `owner_id`, `unit_attribute_id`, `unit_modifier_type_id`, `value` |
| Triggers | evento de activación, caster/target, tags requeridos o excluidos |
| Ticks | periodo, efecto, condición y objetivo |
| Retirada | ataque, daño, expiración, reemplazo, muerte o controlador |

Un icono visible no demuestra que el modificador se aplique. Debe compararse
la estadística o el resultado autoritativo antes, durante y después del buff.

### 6. Controladores, movilidad y proyectiles

`skill_controllers` contiene:

- `id`;
- `kind_id`;
- `value1..value15`;
- `active_weapon_id`;
- `start_anim_id`, `end_anim_id`;
- animaciones de transición confirmadas.

Los `valueN` dependen del `kind_id`; no tienen un significado global.

Ejemplo confirmado para Behind Enemy Lines:

- skill `23587`;
- objetivo de posición;
- controlador `10258`;
- `kind_id=2` (`Leap`);
- `start_anim_id=560`, nombre nativo `all_co_sk_leapattack_2`;
- `value3=700`;
- `value4=-1000`;
- la skill tiene `fire_anim_id=0`.

La creación del controlador debe conservar el objetivo de posición. El cliente
inicia el controlador local y luego informa su estado mediante el paquete
correspondiente; simular solamente la posición final produce movimiento sin
la animación original.

Los proyectiles y FX se validan por sus relaciones nativas. Un proyectil puede
ser visual y no representar por sí mismo el impacto autoritativo.

## Contrato de protocolo AA8

### `CSStartSkill`

Orden confirmado:

```text
skillId
SkillCaster
SkillCastTarget
flag y SkillObject opcional
inputDirection
```

El tipo de `SkillCastTarget` determina todo el layout posterior. Leer un campo
menos puede dejar el ID de skill correcto y aun así desalinear flags,
dirección, animaciones o controladores.

### Objetivo `Position`

Layout confirmado en `x2game.dll`:

```text
X       int64, coordenada convertida
Y       int64, coordenada convertida
Z       float
PosRot  float
ObjId1  BC
ObjId2  BC
ObjId3  BC
```

Los tres identificadores BC son parte del contrato. Su semántica individual
continúa opaca y no debe inventarse. La ausencia de `ObjId3` desalineaba el
resto de `CSStartSkill` y `SCSkillFired`: Behind Enemy Lines aplicaba el daño,
pero el cliente no creaba el controlador Leap ni mostraba la animación.

### `SCSkillFired`

Campos relevantes confirmados:

```text
transaction id
caster
target
skill object
computed delay
channeling time
flag de auto-cast
PISC(skill_id, fire_anim_id)
flag final
```

AA8 serializa `skill_id` y `fire_anim_id` juntos mediante PISC. Escribir el
tipo de skill en una posición histórica desplaza el resto y el cliente descarta
la transición visual aunque el servidor aplique el resultado.

### `SCPlotEvent`

Después de caster, target, tiempos y lista de objetivos:

```text
flag
bloque opcional de 13 valores si flag.bit3 = 1
inputDirection
```

`inputDirection` siempre se escribe después del bloque opcional. La lista AoE
debe estar deduplicada y contener exactamente el número anunciado.

### Objetos posicionales de plot

El `PlotObject` posicional AA8 incluye dos transforms y tres referencias BC.
Es distinto de `SkillCastPositionTarget`; ambos layouts deben verificarse de
manera independiente.

## Rutas comunes de ejecución

### Skill directa contra unidad

```text
CSStartSkill
  -> validar aprendizaje, objetivo, relación, rango y costo
  -> SCSkillFired
  -> efecto directo o proyectil
  -> daño/buff/control
  -> paquetes de impacto y cooldown
```

### Skill `plot_only`

```text
CSStartSkill
  -> SCSkillFired
  -> raíz del plot
  -> SCPlotEvent por transición visible
  -> condiciones y selección de objetivos
  -> efectos concretos
  -> siguientes eventos
```

### Skill de posición con movilidad

```text
CSStartSkill + SkillCastPositionTarget completo
  -> validar terreno, altura y rango
  -> crear destino sintético de posición
  -> crear SkillController con kind y valueN nativos
  -> SCSkillFired sin sustituir fire_anim_id
  -> controlador local del cliente
  -> daño/AoE/efectos en el destino
  -> cierre del controlador
```

### Skill de área persistente

```text
impacto inicial
  -> FX/proyectiles visuales
  -> InteractionEffect
  -> doodad y fase
  -> clout AoE
  -> buff/debuff
  -> modificador autoritativo
  -> retirada por duración o condición
```

## Flujo obligatorio para reparar una habilidad

1. **Identificar la skill:** ID visible, internas, ancestrales, variantes y
   reemplazos temporales.
2. **Construir la clausura:** effects, buffs, plots, condiciones, AoE,
   animaciones, controladores y proyectiles hasta punto fijo.
3. **Registrar procedencia:** compact AA8, game11, x2game, protocolo o derivado
   exclusivamente del servidor.
4. **Clasificar la ruta:** directa, `plot_only`, posición, canalizada,
   proyectil, área persistente o combinación.
5. **Verificar el protocolo antes de tocar gameplay:** layout completo del
   target y de cada paquete consumido por el cliente.
6. **Comprobar presentación:** casteo, animación por arma, sonido, FX,
   proyectil, impacto y número flotante.
7. **Comprobar autoridad:** costo, GCD, cooldown, daño/curación, buffs,
   modificadores, control, movimiento, combos y aggro.
8. **Probar condiciones y ramas:** objetivo primario, secundarios, aliados,
   hostiles, estados requeridos, límites y geometría.
9. **Repetir:** varios usos consecutivos, relog, cambio de especialidad y
   observación desde un segundo cliente.
10. **Cerrar con pruebas:** regresión unitaria/byte a byte, evidencia de logs y
    expediente por habilidad cuando descubra una primitiva nueva.

## Matriz mínima de aceptación

| Área | Verificación |
|---|---|
| Inicio | La skill se puede usar repetidamente y no queda gris. |
| Casteo | Barra, cancelación y tiempo coinciden con AA8. |
| Animación | Inicio, fire, variante de arma, transición y fin son nativos. |
| Sonido/FX | Lanzamiento, trayectoria, impacto y área son visibles. |
| Resultado | Daño, curación, control, buff o dispel se aplican en el momento correcto. |
| Objetivos | Primario, secundarios, relación, geometría y límite son correctos. |
| Movimiento | Posición, orientación, controlador, regreso y cierre funcionan. |
| Estado | Costo, GCD, cooldown, combo, stacks y reemplazo de skill se actualizan. |
| Persistencia | Relog y cambio de especialidad no corrompen skill ni barra. |
| Red | Un segundo cliente observa la misma transición. |
| Estabilidad | Sin crash, desalineación de serializer ni crecimiento sostenido de memoria. |

## Expedientes que sirven como referencia

- **Triple Slash:** selección AoE, deduplicación, relación, geometría y límite.
- **Sunder Earth:** plot posicional, FX, proyectiles, doodad persistente, clout
  y modificador de daño recibido.
- **Hammer Toss:** ramas de plot, condición `Relation`, stun primario y
  knockback secundario.
- **Behind Enemy Lines:** objetivo de posición, contrato de tres BC,
  controlador Leap y separación entre `fire_anim_id` y animación de
  controlador.
- **Swiftblade:** habilidades internas, plots, combos, movilidad y
  controladores modernos.

## Plantilla para registrar una habilidad

```text
Nombre / ID:
Especialidad:
Fuente y hashes:
Skills internas/variantes:
Ruta de ejecución:
Target layout:
Plot y eventos:
Condiciones:
AoE:
Efectos concretos:
Buffs/modificadores:
Animaciones por arma:
Controlador/proyectil:
Paquetes confirmados:
Comportamiento esperado:
Resultado probado:
Regresiones:
Dependencias pendientes:
Estado: aislada | parcial | completa
```
