# Dossiers de funciones y relaciones Shadowplay V3

## Stealth y detección

- Entrada: flags AA8 `stealth`, `anti_stealth`, `detect_stealth` y nivel del
  buff activo.
- Fórmula frontal: `min(40, 12*(1+(sourceLevel-targetLevel)/65)/(1+stealthLevel/65))`.
- Factor trasero: `0.5`.
- Consumidor: `Unit.UnitIsVisible`; NPC y Character comparten la fórmula y el
  NPC añade sus límites de FOV/sight.
- Lifecycle: sólo banderas `remove_on_*` de la plantilla. `keep_stealth`
  conserva el estado al inicio; un `CancelStealth` posterior del plot puede
  retirarlo legítimamente.

## Leech / BuffSteal

- `SkillEffect 6101` y `52542`, ambos `weight=1`, eligen el número nativo de
  buffs a robar; las condiciones type 16 de peso cero se aplican normalmente.
- Elegibilidad: buff positivo, no passive/system/owner-only/exempt.
- Transferencia: preserva original source, SkillCaster, skill, stack, charge,
  ability level y duración restante.
- No existe lista de buffs ni condición por ID de Leech.

## Poisoned Weapons

- Base: `22266 → dummy 22271 → triggers 9968/9970/9973 → 21999/18135/dispel`.
- Flame: `24093 → dummy 24095 → trigger 11343 → 21999`; el preparatorio
  persiste durante 3 s. “Transmisión continua”
  significa que cada nuevo golpe de arma válido durante esa ventana puede
  envenenar otro objetivo; no existe en el cierre AA8 una relación de muerte
  que salte automáticamente el veneno al objetivo más cercano.
- Wave: `24235 → dummy 24236 → trigger 11418 → 24237`; `11420` consume.
- El servidor sólo materializa las tres relaciones omitidas mediante la tabla
  genérica `native_server_hit_effects`, después de daño positivo y compatible.
  Un efecto ya disparado no se retroalimenta. Tampoco son hits válidos los
  ticks periódicos: `DamageEffect` conserva esa identidad en `OnAttackArgs`
  para que un DoT melee/ranged no vuelva a consumir la relación de coating.
- `40815` se conserva como identidad interna nativa, pero no tiene una arista
  ejecutable entrante desde `24093`, `24095`, `11343` ni `40787`. Su tag 378
  compartido es genérico y no prueba continuidad. El tooltip de Flame enlaza
  `74638 → DamageEffect 11937`, cuya fórmula coincide con el tick de Poison
  `21999`; no autoriza a iniciar `40815`. La hipótesis V5 que lo hacía emitía
  daño con `TlId=0` y desconectaba al cliente, por lo que queda preservada sólo
  como evidencia negativa.

## Plots, movilidad y ataques múltiples

- Overwhelm y Drop Back reutilizan los controllers `10188` y `10265`.
- Wallop es plot-only y genera cuatro impactos sin `SCSkillFired` artificial.
- Throw Dagger usa el plot `3401` y projectile `16`; el escenario de tres
  objetivos observa cuatro daños totales sin duplicación de presentación.
- Rapid Strike no tiene replay servidor: `18125/18126/18127` son requests C2S
  sucesivos descritos por type 48 y admitidos por type 41.

## Shadowsmite Lightning y BubbleEffect

- `36594 → plot 3008`, cierre completo de 32 eventos.
- El evento 25117 evalúa PlotCondition `9159`, que contiene tres requisitos
  AA8 OR `URK_TARGET_OWNER_TYPE` (`kind 38`): Character `0`, Npc `1` y Mate
  `5`. Para esos tipos ejecuta `SpecialEffect 30549/TeleportToUnit` antes de
  continuar al impacto.
- Si el tipo no es elegible, el evento 25139 verifica rango 0–4 m. Su rama de
  fallo llega a 25140: `BubbleEffect 4766` + efecto visual, sin daño.
- Un NPC a 5 m debe producir `SCUnitBlinkPacket` y daño; un Slave a la misma
  distancia produce un único `SCChatBubblePacket`, sin blink ni daño.
- `TeleportToUnit` consume sus cuatro valores nativos como distancia mínima/
  máxima en milímetros y ángulo relativo mínimo/máximo en grados. Para `36594`
  son `600/600/180/180`: coloca al caster exactamente 0,6 m detrás del target;
  ignorar `value3/value4` lo situaba erróneamente al frente.
- Por tanto, la interpretación chat es client-native y su eliminación habría
  sido una regresión. El nombre del tipo por sí solo no fue la prueba: lo son
  speech, kind, arista, orden y observación del paquete.

### Cierre owner-scoped de `unit_reqs`

- El stream completo `game11` contiene seis filas PlotCondition dentro del
  cierre Shadowplay: `9159=(0|1|5)`, `21578=0`, `21769=0`, `21770=0`, todas
  `kind 38` y con mensaje habilitado.
- La ausencia de estas filas en V4 no era evidencia negativa: el builder sólo
  importaba owners `Skill`. Esto convertía `ConditionUnitRequirements` en
  falso permanente y hacía inalcanzable el teleport.
- `SkillUnitRequirement` resuelve ahora kind 38 mediante el mismo discriminador
  `BaseUnitType` que serializa `SCUnitStatePacket`; no contiene IDs de skill.

### Contrato wire de `SCChatBubblePacket`

- Stage 15 `FUN_39341870` fija el opcode `0x243` y la vtable
  `PTR_FUN_39cfb7a0`; `FUN_399a4440` serializa `Bc objId`, `byte kind` y el
  payload discriminado que reconstruye `FUN_3999de90` (`string` para kind 0,
  `uint32` para 1/2).
- La vtable comparte sus dos primeras entradas con `SCPlotEnded 0x072`,
  `SCSkillCooldownReset 0x098`, `SCSkillCooldownReduce 0x038` y
  `SCCooldowns 0x34D`: es la familia cifrada de nivel 5.
- La implementación histórica enviaba el cuerpo correcto por nivel 1. La rama
  válida de `36594` no lo exponía; la rama 25140 fuera de rango sí lo emitía y
  el cliente terminaba la sesión. No era un fallo del teleport ni del segundo
  cast, sino framing incorrecto de un paquete condicional.
- La regresión exige ahora opcode `0x243`, level 5, consumo exacto del cuerpo,
  contador DD05 y equivalencia wire/plaintext.

## Tombstones `10082/10104/10189`

Los C2S learn prueban identidad y pertenencia. La knowledge filtrada no tiene
las filas completas, por lo que el builder reconstruye cada columna demostrada
desde el carrier validado y registra la procedencia. No copia una fila 10.x ni
promueve el scaffold V2 como unidad; todo campo no probado se neutraliza.

## Regla reusable

Una primitiva nueva sólo se añade al runtime si existe un consumidor AA8 y una
relación de datos que la active. La implementación debe ser genérica y pasar a
la vez las ramas cerradas. Un resultado visual correcto no convierte una
hipótesis custom en contrato nativo.
