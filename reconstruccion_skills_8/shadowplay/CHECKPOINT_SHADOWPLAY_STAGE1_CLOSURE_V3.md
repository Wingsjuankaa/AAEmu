# Checkpoint Shadowplay V3 — cierre de Etapa 1

Fecha: 2026-08-10
Cliente: Kakao `8.0.3.12 r558734`
Rama: `client_version/8.0.3.12-kakao-r558734-port`

## Resultado

El runtime V6 aceptado cubre las 12 habilidades visibles, 13 variantes ancestrales,
Rapid Strike interno, cuatro skills auxiliares/login-stage y las seis pasivas
Shadowplay. La barrera final informa:

- raíces/etapas/variantes materializadas: `31`;
- raíces visibles: `12`;
- pasivas: `6`;
- raíces Shadowplay en cuarentena: `0`;
- relaciones server-required: `3`;
- referencias de plot colgantes: `0`;
- eventos del plot `3008`: `32`;
- claves de evidencia: `3019`;
- relaciones con procedencia: `2273`.

Runtime desplegado:

`D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-shadowplay-v6.sqlite3`

SHA-256:

`01088F9835AFD9BA72E2A86504A63909F468154458D36DBAAB08164362C6BAD3`

Dos construcciones independientes produjeron el mismo hash. `quick_check` e
`integrity_check` devolvieron `ok`.

## Primitivas nuevas cerradas

1. Un hit nativo puede materializar una relación server-required omitida de
   la compact mediante `native_server_hit_effects`, consumida por el ejecutor
   genérico de triggers. La relación declara buff preparatorio, dummy/skill
   nativa, máscara de daño y requisito de daño positivo.
2. `BuffSteal type 16` transfiere buffs positivos elegibles conservando caster
   original, skill, nivel, stacks, cargas y duración restante. Los efectos
   Leech de peso positivo usan selección ponderada genérica; no hay rama por
   skill ID.
3. Stealth, anti-stealth y detect-stealth se resuelven en `Unit` para jugadores
   y NPC, con fórmulas AA8 frontal/trasera y lifecycle declarado por cada buff.
4. Los efectos `weight > 0` se seleccionan por el grupo nativo antes de aplicar
   condiciones. En las ramas cerradas 1/6/7/8, Leech es el único consumidor
   con más de una alternativa positiva.

## Evidencia negativa preservada

- `buff_trigger 88000001`, `effect 720`, `BuffEffect 256` y el tratamiento
  codificado por tag `3567` no son nativos y no entran al V3.
- `BubbleEffect 4766` sí es un globo visual AA8: contiene el texto coreano
  “no se puede atacar”. En Shadowsmite Lightning el plot lo emite exactamente
  una vez cuando el tipo no admite teleport y además excede 4 m; no aplica
  daño.
- Los scaffolds completos V1/V2 de `10082/10104/10189` no se promovieron. Sólo
  se retuvieron campos demostrados individualmente por carrier y evidencia
  live; los campos sin prueba se dejaron neutros.
- No se añadieron replay, timers, guards, allow-lists, packet visual artificial
  ni máquinas Combo de servidor para Rapid Strike.

## Validación automática

- `test_shadowplay_native_v3.py`: `7/7 PASS` sobre el contrato V6.
- Suite .NET Core 3.1: `633/633 PASS`.
- Mechanics Lab Shadowplay: 20 escenarios verdes, incluyendo Poison base,
  Flame y Wave; Leech; Stealth; movilidad; Wallop; Rapid Strike; Throw Dagger;
  las ramas válida/inválida de Shadowsmite Lightning y admisión de rifle para
  Poisoned Weapons/Stalker's Mark.
- Regresión Battlerage: 25 escenarios, incluyendo Charge, Behind Enemy Lines
  Gale, Tiger Strike Lightning, Precision Strike Lightning, Triple Slash y
  Whirlwind: `25/25 PASS`.
- Regresión Archery: cuatro cierres letales y wrap/concurrencia: `4/4 PASS`.
- Flamebolt `10752→24894→24895` y Endless Arrows
  `14835→14836→14837` permanecen cubiertas por la suite transversal: la
  continuidad sigue siendo autoridad del cliente.
- Revalidación live-dirigida en Mechanics Lab con arco: Poisoned Weapons base
  y Stalker's Mark `2/2 PASS`, sin excepciones y contra la compact
  `8194F1...B0DD`.

## Correcciones live 2026-08-11: admisión por arma y Transfers

La prueba live de Poisoned Weapons `10481` y Stalker's Mark `12139` fue
rechazada antes de entrar al ejecutor con `UrkEquipRanged`; el cliente presentó
el mismo `result=95` como “No corpses nearby”. Dannia tenía la escopeta
`item 50799` (`holdable_id=31`). La primera auditoría sólo consultó el runtime
heredado y concluyó incorrectamente que sus filas de arco eran AA8 completas.

La regresión Archery demostró que `unit_reqs` cruza una frontera de string
cache. Al ejecutar el decoder sobre las 13.053 filas exactas de `game11`, la
referencia internada `69872→Skill` recuperó para Stalker's Mark `12139` la fila
nativa `kind 29/value1=2`; `skills.or_unit_reqs=true` la combina con arco. Para
Poisoned Weapons `10481` no existe ninguna fila en el resultado AA8 completo,
`or_unit_reqs=false` y r575 tampoco declara requisito: su fila de arco provenía
del compact histórico y fue retirada.

El runtime V4 queda así:

- `10481`: cero `unit_reqs`; admite melee, arco o rifle;
- `12139`: `EquipRanged` OR `value1=0` arco / `value1=2` rifle;
- hash determinista: `A63E60BF999F59B2BC15CCA7F34843EC355535E5E1D819657AC9F23961781A12`;
- validador V4 `7/7`, Mechanics Lab con rifle `2/2` y suite .NET `629/629`.

Queda como regla separar admisión y ejecución, resolver `item_id→holdable_id`
y completar referencias internadas antes de usar la ausencia de una relación
owner-keyed como evidencia negativa.

El carro regional que aparecía bloqueando al personaje era un incidente
independiente de Shadowplay. La primera reparación alineó correctamente la
pieza de abordaje con el primer punto de la ruta, pero añadió una inversión de
jerarquía no compatible con el motor AA8: hizo al motor hijo de la pieza y
después siguió escribiendo coordenadas mundiales como locales. La evidencia
live `01:04:34` y `01:07:31–33` mostró la reentrada periódica de los mismos
objetos Transfer `2029/2033` en la región de Dannia.

El contrato restaurado mantiene motor y boarding sin `Parent`; la relación
`StickyParent` existente arrastra la pieza y sus doodads. Sólo se conserva la
alineación inicial al primer punto de ruta y el offset geométrico nativo
`-9.24417 m`. La regresión prueba alineación, ausencia de inversión y el mismo
delta de movimiento para ambas piezas. La suite .NET Core 3.1 queda en
`633/633 PASS` con la compact V6 exacta.

Despliegue de la corrección Transfer:

- rollback: `aaemu-game:rollback-pre-transfer-sticky-root-20260811`
  (`sha256:3e02bf87b488501a46897ac899a7ce2ec34285dafa38f63b00ce01c358a7167e`);
- imagen: `sha256:bfb30416229d5daed6d57a5b823664a3d543277052c625539236ea6809727797`;
- compact V6 montada: `01088F9835AFD9BA72E2A86504A63909F468154458D36DBAAB08164362C6BAD3`;
- `101` Transfers y `156807` doodads cargados, scripts `0 errors`, registro
  exitoso en LoginServer y `RestartCount=0`;
- sólo se recreó `game`.

## Despliegue

Se construyó y recreó sólo `game`. Login y MySQL no se recrearon.

- imagen game: `sha256:ed1341d7023e5ab81f5cdcad4f32dd181c075d703b84a3cb02c58031795c81f0`;
- compact montada: coincide con `A63E60BF...1A12`;
- `game RestartCount=0`, estado `running`;
- Login y MySQL permanecen `running`.

Durante el primer arranque se detectó una carrera preexistente entre tareas
diferidas de doodad que enumeraban y modificaban `ListGroupId`. El tracking de
fases se hizo atómico y se añadió una prueba concurrente. El segundo arranque
completó los `156807` doodads, mantuvo `RestartCount=0` y registró cero
`ERROR/FATAL/Unhandled/Exception`.

Tras la corrección de Transfers, el arranque completó `101` Transfers y
`156807` doodads, se registró en Login, mantuvo `RestartCount=0` y no emitió
`ERROR/FATAL/Unhandled/Exception`. Login y MySQL no fueron recreados.

### Corrección live 2026-08-11: Shadowsmite Lightning fuera de rango

El primer uso válido de `36594` completaba teleport, daño y plot. Un uso
posterior a 5 m tomaba la arista `25139→25140`, enviaba `BubbleEffect 4766` y
el cliente mostraba “Target is too far” antes de desconectarse. La correlación
de logs descartó excepción del servidor y aisló `SCChatBubblePacket 0x243`.

Stage 15 probó tanto el cuerpo discriminado como su pertenencia a la misma
familia cifrada de nivel 5 que `SCPlotEnded` y los paquetes de cooldown. Se
corrigió el framing histórico level 1 sin alterar plot, rango, teleport ni
efectos. Aceptación previa al live:

- `ChatBubblePacketTests`: level 5 y los dos payloads AA8;
- Mechanics Lab `36594` válido e inválido: ambos PASS;
- paquete inválido: `BodyConsumedExactly=true` y `WireMatchesPlaintext=true`;
- Shadowplay, Battlerage y Archery: `suite_failed=0`;
- suite .NET Core 3.1: `629/629 PASS`;
- imagen `sha256:48fb8e9107719af3050ad56e2d466d6eeb6fe4ca3bc131ed95da2ddf1bacc9a7`,
  compact montada `A63E60...A12`, `RestartCount=0`.

La aceptación visual por lotes fue completada el 2026-08-11: todas las skills
base y variantes ancestrales Shadowplay fueron aprobadas por el usuario. La
Etapa 1 queda cerrada como éxito; el incidente de Transfers conserva ciclo,
pruebas y despliegue propios y no reabre la rama de skills.

### Corrección V5: recuperación del teleport a 5 m

La prueba posterior al framing mostró que un NPC a 5 m ya no desconectaba,
pero seguía tomando el bubble. La compact V4 había importado las condiciones
del plot `3008` sin sus relaciones owner-scoped `unit_reqs`; por ello la
condición `9159` siempre devolvía falso y hacía inalcanzable
`SpecialEffect 30549/TeleportToUnit`.

El decoder completo de `game11` recuperó seis filas PlotCondition. Stage 15 y
el enum AA8 identifican `kind 38` como `URK_TARGET_OWNER_TYPE`; `9159` admite
por OR Character `0`, Npc `1` y Mate `5`. V5 importa el cierre exacto e
implementa el consumidor genérico contra el mismo `BaseUnitType` de
`SCUnitStatePacket`, sin condición por skill.

Aceptación automática V5:

- dos builds idénticos, SHA-256 `179660677E1792980333FA050C709D7B7B2FF31C45D29EF3E4EB2E2854A0ABF0`;
- `quick_check=ok`, `integrity_check=ok`, 31 raíces y cero cuarentenas;
- NPC a 5 m: un `SCUnitBlinkPacket`, un daño, cero bubbles y posición final
  0,6 m detrás según `value3/value4=180/180`;
- Slave a 5 m: un bubble, cero blink y cero daño;
- Shadowplay, Battlerage y Archery: `suite_failed=0`;
- suite .NET Core 3.1: `631/631 PASS`.

Despliegue V5:

- se recreó únicamente `game`;
- imagen `sha256:3f09b486fae0e254b91a7dcce4f682032946a331ae6698ed66aea2fce73b9746`;
- compact montada `179660677E1792980333FA050C709D7B7B2FF31C45D29EF3E4EB2E2854A0ABF0`;
- compilador de scripts `0 errors`, log de arranque sin
  `ERROR/FATAL/Unhandled/Exception`;
- registro exitoso en LoginServer y `RestartCount=0`;
- Login y MySQL no fueron recreados.

### Corrección V6 2026-08-11: Flame sin auxiliar servidor

La captura live posterior demostró que la desconexión no dependía de matar al
objetivo: ocurría en el primer hit mientras `24093` estaba activo. El trace
mostró `24095`, Poison `21999` y un `SCUnitDamaged(skill=40815, TlId=0)` creado
por la relación manual V5. Sin la variante Flame no aparecía ese paquete.

La revisión del grafo AA8 completo cerró la contradicción:

- `40787 → 57161 → 74637 → BuffEffect 28839 → buff 24093`;
- `24093 → 24095 → trigger 11343 → Poison 21999` es la relación
  server-required demostrada;
- no existe relación `24093/24095/11343/40787 → 40815`;
- `40815 → DamageEffect 11968` es una identidad interna aislada de daño melee;
- el tag 378 común sólo identifica genéricamente una player skill;
- `tooltip_skill_effect 980` enlaza `40787 → 74638 → DamageEffect 11937`, cuya
  fórmula coincide con el tick de Poison, no con `40815`.

V6 elimina `triggered_skill_id` del contrato `native_server_hit_effects` y
retira el arranque manual de skills desde `AttackBuffTrigger`. Se conservan las
tres relaciones coating→dummy y el ejecutor genérico de triggers. `40815`
permanece materializada para preservar identidad AA8, pero sin arista
ejecutable. La prueba negativa exige que nunca aparezca como ID de daño.

Aceptación V6:

- dos builds byte a byte idénticos, SHA-256
  `01088F9835AFD9BA72E2A86504A63909F468154458D36DBAAB08164362C6BAD3`;
- `quick_check=ok`, `integrity_check=ok`, validador `7/7 PASS`;
- Flame en dos objetivos sucesivos: ambos reciben `21999`, ninguno recibe
  daño `40815`;
- Mechanics Lab Shadowplay `20/20`, Battlerage `25/25` y Archery `4/4 PASS`;
- suite .NET Core 3.1: `633/633 PASS`.

Despliegue V6:

- rollback preservado como
  `aaemu-game:rollback-pre-shadowplay-poison-flame-v6-20260811`
  (`sha256:3badc1cd0a69d29077c406201d3ceef7c6c1a2ae06dba847013f1d698f4f43c0`);
- se reconstruyó y recreó únicamente `game` con imagen
  `sha256:3e02bf87b488501a46897ac899a7ce2ec34285dafa38f63b00ce01c358a7167e`;
- compact read-only montada y verificada dentro del contenedor:
  `01088F9835AFD9BA72E2A86504A63909F468154458D36DBAAB08164362C6BAD3`;
- loader: `AA8 native server hit effects loaded: 3`;
- scripts `0 errors`, registro exitoso en LoginServer, puertos 2239/2250 y
  `RestartCount=0`;
- Login y MySQL no fueron recreados.

El escenario V5 que exigía una muerte por `40815` queda retirado como falsa
aceptación. Se conserva su resultado histórico como evidencia negativa: fue
construido alrededor de una hipótesis custom y por tanto no podía validar el
contrato del cliente.

### Registro histórico V5 retirado: Flame, ticks periódicos y cierre letal

> **No promovible.** La sección siguiente documenta la hipótesis descartada
> `24093 → 40815`. Sus afirmaciones de ejecución y aceptación por `40815` no
> forman parte del runtime V6 ni deben reutilizarse.

La captura `aa8-game-20260812-000121513-session-3106981453.jsonl` identificó
el uso ancestral `40787`. El primer impacto creó `21999/24095` y ejecutó la
auxiliar `40815`. Un tick posterior de Bleeding fue publicado como `OnAttack`
melee ordinario, volvió a disparar el coating y la segunda `40815` mató al NPC.
Después de `SCUnitDeath`, del aggro vacío ordenado y de los dos
`SCCombatCleared`, `DamageEffect` emitió de nuevo
`SCUnitAiAggro(owner=victim,count=1)`. El servidor siguió estable, pero el
cliente cerró la sesión por esa reapertura de una transacción letal completa.

El contrato AA8 de Flame quedó delimitado con sus datos:

- `40787 → buff 24093` durante 3 s;
- cada hit melee/ranged positivo aplica `24095 → trigger 11343 → poison 21999`
  y la auxiliar `40815`;
- `21999` es un DoT de 6 s sin radio ni relación de muerte/propagación;
- “transmitir continuamente” permite envenenar objetivos sucesivos golpeados
  durante el coating; no prueba un salto automático al morir.

La reparación es transversal y declarativa: `OnAttackArgs` conserva si el
origen es periódico, el consumidor genérico rechaza ticks y efectos ya
disparados, no crea el impacto sobre HP cero y `DamageEffect` no reintroduce
aggro/AI después de la muerte. No contiene IDs de Poison ni selección custom
de un objetivo cercano.

Aceptación automática:

- `ShadowplayPoisonTriggerTests`: `10/10 PASS`;
- Mechanics Lab Shadowplay: `20/20 PASS`;
- nuevo escenario `shadowplay_poisoned_weapons_flame_lethal_auxiliary`: muerte
  por `40815`, cierre estable y `no_positive_aggro_after_death=true`;
- Poison base/Flame/Wave y rifle: todos PASS;
- cierres letales Archery `npc_2308` y `counter_wrap`: ambos PASS;
- suite .NET Core 3.1 con V5 montada: `633/633 PASS`.

Despliegue:

- rollback preservado como
  `aaemu-game:rollback-pre-shadowplay-poison-flame-20260811`
  (`sha256:3f09b486fae0e254b91a7dcce4f682032946a331ae6698ed66aea2fce73b9746`);
- se recreó únicamente `game` con imagen
  `sha256:3badc1cd0a69d29077c406201d3ceef7c6c1a2ae06dba847013f1d698f4f43c0`;
- compact montada y verificada:
  `179660677E1792980333FA050C709D7B7B2FF31C45D29EF3E4EB2E2854A0ABF0`;
- scripts `0 errors`, arranque completo en `00:01:47`, registro exitoso en
  LoginServer, puertos 2239/2250 activos y `RestartCount=0`;
- Login y MySQL permanecieron activos y no fueron recreados.
