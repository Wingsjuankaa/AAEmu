# Dossier consolidado: reconstruccion completa de Sorcery AA8 V1

Fecha de consolidacion: 2026-08-07

## Proposito y estado

Este dossier conserva el hilo tecnico que permitio llevar Sorcery desde una
rama parcialmente legada hasta una clausura `live_accepted`. No sustituye
la evidencia detallada de cada checkpoint; la organiza como una ruta reusable
para Archery y las ramas siguientes.

Sorcery queda `live_accepted` al 100%. Gods' Whip: Wave registro
10 impactos autoritativos, 5.400 puntos de reduccion real de HP, paquetes de
dano y `plot_ended` normal. La repeticion final de Flame Barrier: Mist sobre
la imagen V24 registro `41223 -> 41478`, buffs `24584/24585` atribuidos a la
skill interna y `abilityLevel=52`, 16 ticks autoritativos sobre dos objetivos,
6.625 puntos de reduccion real de HP, `packet=True` en todos los impactos y
limpieza de los diez doodads. Game permanecio activo con `RestartCount=0`.

## Autoridad y fronteras

- Cliente objetivo: ArcheAge Kakao 8.0.3.12 r558734.
- AA8 manda sobre IDs, relaciones, tiempos, formulas, balance y protocolo.
- La SQLite 10.x r575 se uso obligatoriamente como crosswalk para ubicar
  fronteras; ninguna fila de balance 10.x entro al runtime.
- `rama_8_modern` y `rama_10` fueron referencias de arquitectura, no fuentes
  de verdad ni destinos de despliegue.
- Toda promocion exigio una confirmacion AA8 independiente: compact staged,
  cached result, loader/consumidor nativo, Stage 15 o comportamiento vivo.

## Secuencia de reconstruccion demostrada

### 1. Estado de especializacion, aprendizaje y persistencia

El primer defecto no estaba en las formulas de dano: el servidor no mantenia
un estado efectivo coherente entre rama, skills aprendidas, pasivas, puntos y
cliente.

Se repararon como un solo contrato:

1. recuperar el nivel historico de la rama entrante;
2. retirar activas y pasivas de la saliente;
3. materializar la skill por defecto de cada rama;
4. recalcular puntos sin borrar ramas no cambiadas;
5. persistir antes de confirmar;
6. emitir snapshot de ramas, skills, active types y clase;
7. refrescar Change Skillset, ventana Skills y banner en la misma sesion;
8. verificar por relog.

Este orden resolvio el reset a nivel 1, la perdida de skills por defecto y el
estado que solo aparecia despues de volver a seleccion de personaje.

### 2. Progresion y variantes ancestrales

La progresion ancestral requirio separar XP acumulada, cruce de umbral,
persistencia y protocolo. El procesador consume XP excedente en bucle y emite
cada transicion; quedar en 100% dejo de ser un estado terminal.

La seleccion ancestral se trato como estado efectivo, no como mero icono:

`base skill -> heir_skill -> successor skill -> active type -> snapshot G2C`

Se fijaron packets de activar, resetear y listar, y la sucesora efectiva se
usa en el plot sin perder los requisitos heredados de la base.

### 3. Clausura ejecutable, no filas aisladas

Cada skill se reconstruyo siguiendo simultaneamente:

- camino directo: `skill -> effect -> actual effect`;
- camino plot: `skill -> plot -> event -> condition/effect -> next event`;
- camino buff: `BuffEffect -> buff -> tick/trigger/modifier`;
- camino espacial: `plot -> doodad -> phase -> clout -> area/effect`;
- relaciones owner-keyed, tags y skills internas.

Esto explico por que algunas skills consumian MP y mostraban animacion aunque
no mutaban HP: la raiz visible existia, pero faltaba un descendiente o su
consumidor.

### 4. Cancelacion de casteo y scheduler

El servidor aceptaba la cancelacion visual pero mantenia eventos diferidos en
cola. La reparacion hizo que el estado de cancelacion se comprobara antes de
cada nodo y efecto programado. La skill cancelada por movimiento ya no impacta
al terminar su timer.

La leccion reusable es que `cast stopped` y `plot cancelled` deben converger
en una unica fuente de verdad; detener solo la animacion no cancela el dano.

### 5. Buffs propios y recursos

El bucle visible de todas las skills que aplicaban buffs al propio personaje
era transversal. Se auditaron por separado:

- aplicacion/remocion del buff;
- eventos de trigger;
- recurso de combate;
- packets de cambio y su opcode/layout;
- reentrada C2S/G2C.

La correccion comun evito parches por ID y permitio activar todas las pasivas
de Sorcery con su efecto y reversa correspondientes.

### 6. Dano, HP, packet visible y aggro

Se separaron cuatro contratos que antes parecian uno:

1. calculo de dano;
2. mutacion autoritativa de HP;
3. packet de dano al cliente;
4. aggro autoritativo y notificacion de aggro cliente.

Meteor: Lightning demostro que una skill podia dañar y luego desconectar. La
causa transversal fue el transporte de rafagas periodicas/AoE y el canal de
aggro cliente, no la formula. Los efectos de un mismo tick se agrupan en
`CompressedGamePackets`; el aggro servidor permanece activo aunque un packet
cliente no demostrado quede aislado.

Los checkpoints V13-V20 conservaron hipotesis y refutaciones. V21 es el cierre
promovido: dano periodico agrupado, conexion estable y aggro cliente separado
sin desactivar IA.

### 7. Semantica espacial y terreno

Gods' Whip: Wave `39674`, plot `3778`, exponia todos los rayos pero no dañaba.
El evento `33384` usa RandomArea con `p3=4000`; el emulador ubicaba cada punto
exactamente en el radio maximo. Los cubos de impacto posteriores no
intersectaban los objetivos del centro.

La reparacion transversal muestrea distancia en `[0,p3]`, conserva el angulo
aleatorio y aplica la politica AA8 de altura. La Z no se interpreta como
offset arbitrario: se resuelve contra terreno cuando el metodo lo exige.

### 8. Clausura periodica recuperada desde game11

Flame Barrier: Mist tenia slow y visual, pero no daño. Su cadena incompleta
era:

`41223 -> 24583 -> 42478 -> 41478 -> plot 4049 -> doodad 13919 -> clout 3792`

El crosswalk r575 indico `3792 -> 76542`. La relacion se promovio solo despues
de recuperar el cached result AA8 exacto de `game11`:

- inicio `0x8AAEF32`;
- fin `0x8AB0A32`;
- 768 relaciones unicas;
- SHA-256 canonico
  `47D2CFF5B1C7753445B58223DFAC000AC9EA2BFA7F2B1A841D5DA3DE39873C8E`.

La clausura final es:

`3792 -> 76542 -> BuffEffect 29874 -> buff 24585 -> tick 4167 -> 76543 -> DamageEffect 12209`

El buff dura 4000 ms, pulsa cada 1000 ms y conserva el bonus AA8 contra el tag
104. El runtime no contiene balance 10.x.

### 9. Propagacion de origen a traves de doodad y clout

La primera aceptacion viva de Mist demostro un fallo que no pertenecia a la
SQLite: el registro AA8 `doodad_func_clouts/3792` declara
`use_origin_source=1`, pero el emulador descartaba la instancia de skill al
crear el doodad. El campo existia y se cargaba, aunque nunca se consumia.

El contrato restaurado es:

`InteractionEffect -> SummonDoodad -> Doodad.OriginSkill -> DoodadFuncClout -> AreaTrigger -> Buff/EffectSource/CastAction`

Esto conserva el ID `41478`, su `tlId`, el nivel de Sorcery y la atribucion de
los ticks. Los clouts con `use_origin_source=0` siguen aislados y no reciben
contexto accidental. La regla es transversal: todo contenedor diferido
(doodad, area, buff, trigger o tarea) debe transportar explicitamente la
autoridad de la skill cuando la fila AA8 lo ordena; conservar solo el caster no
es suficiente.

## Instrumentacion que debe conservarse

Los prefijos estables son:

- `[AA8SorceryLive]` para request, resultado, plot y cierre;
- `[AA8ArcheryLive]` para la rama piloto siguiente;
- `[AA8SkillDamage]` para efecto, amount, absorcion y HP before/after;
- `[AA8SkillCastRelease]` para skills cargables y porcentaje liberado.

Una prueba de daño pasa solo si `amount > 0` y `hpAfter < hpBefore`. La
animacion, el numero flotante o el cooldown por si solos no constituyen
evidencia.

## Artefactos y pruebas

- Sorcery base cerrada: `compact-8.0-runtime-sorcery-v23.sqlite3`.
- SHA-256 V23:
  `B6E139D0E6953EE3F7BEAB015E770C9A7D5A270A45978E55016A0324B60CEBC0`.
- Runtime compuesto Archery V4 promovido:
  `compact-8.0-runtime-archery-v4.sqlite3`.
- SHA-256 V4:
  `A8D209F3B30B3DB8DE2B3B0C19B578A6760D68FF2D082B9AC7F5B70616DFFB22`.
- Integridad SQLite: `quick_check=ok`, `integrity_check=ok`.
- Regresion de runtime Archery: 16/16.
- Extractor nativo `unit_reqs`: 1/1, 13.053 filas exactas.
- Auditoria semantica y owner-keyed: 9/9, 35/35 raices, 356 skill tags y 21
  passive buff tags, cero duplicados y cero modificadores sin consumidores.
- Suite servidor SDK 3.1.409 con runtime compuesto: 567/567.

## Inventario de archivos de implementacion intervenidos

Este inventario separa el trabajo de Sorcery de otros cambios preexistentes
del worktree. Son los puntos que deben revisarse al trasladar el metodo a otra
rama.

### Estado, progresion y protocolo ancestral

- `AAEmu.Game/Core/Managers/SkillManager.cs`
- `AAEmu.Game/Core/Network/Game/GameNetwork.cs`
- `AAEmu.Game/Core/Packets/C2G/CSActivateHeirSkillPacket.cs`
- `AAEmu.Game/Core/Packets/C2G/CSHeirLevelUpPacket.cs`
- `AAEmu.Game/Core/Packets/C2G/CSResetHeirSkillPacket.cs`
- `AAEmu.Game/Core/Packets/C2G/CSStartSkillPacket.cs`
- `AAEmu.Game/Core/Packets/C2G/CSStopCastingPacket.cs`
- `AAEmu.Game/Core/Packets/C2G/CSOffsets.cs`
- `AAEmu.Game/Core/Packets/G2C/SCActivatedHeirSkillPacket.cs`
- `AAEmu.Game/Core/Packets/G2C/SCHeirLevelUpPacket.cs`
- `AAEmu.Game/Core/Packets/G2C/SCHeirSkillListPacket.cs`
- `AAEmu.Game/Core/Packets/G2C/SCResetHeirSkillPacket.cs`
- `AAEmu.Game/Core/Packets/G2C/SCListSkillActiveTypsPacket.cs`
- `AAEmu.Game/Core/Packets/G2C/SCUpdateSkillActiveTypePacket.cs`
- `AAEmu.Game/Core/Packets/G2C/SCSkillEndedPacket.cs`
- `AAEmu.Game/Core/Packets/G2C/SCOffsets.cs`
- `AAEmu.Game/GameData/HeirGameData.cs`
- `AAEmu.Game/Models/Game/Char/Character.cs`
- `AAEmu.Game/Models/Game/Char/CharacterAbilities.cs`
- `AAEmu.Game/Models/Game/Char/CharacterHeirProgression.cs`
- `AAEmu.Game/Models/Game/Char/CharacterHeirSkills.cs`
- `AAEmu.Game/Models/Game/Char/CharacterSkillActiveTypes.cs`
- `AAEmu.Game/Models/Game/Char/CharacterSkills.cs`
- `AAEmu.Game/Models/Game/Heirs/HeirProgressionPolicy.cs`
- `AAEmu.Game/Models/Game/Skills/SkillActiveType.cs`
- `SQL/updates/2026-08-04_aa8_heir_sorcery.sql`

### Ejecucion, plots, dano, buffs y recursos

- `AAEmu.Game/Core/Managers/PlotManager.cs`
- `AAEmu.Game/Core/Managers/TaskManager.cs`
- `AAEmu.Game/Models/Game/Skills/Buff.cs`
- `AAEmu.Game/Models/Game/Skills/CastAction.cs`
- `AAEmu.Game/Models/Game/Skills/Skill.cs`
- `AAEmu.Game/Models/Game/Skills/SkillObject.cs`
- `AAEmu.Game/Models/Game/Skills/Buffs/BuffEvents.cs`
- `AAEmu.Game/Models/Game/Skills/Buffs/BuffTriggersHandler.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/AggroEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/CombatResourceEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/DamageEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/DispelEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/ResetAoeDiminishingEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/RestoreManaEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/CancelOngoingBuff.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/CombatDice.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/Combo.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/DisturbCasting.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/ManaCost.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/SkillUse.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/PlotCondition.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/PlotEventEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotNode.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotState.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotTargetInfo.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotTree.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/UpdateTargetMethods/PlotTargetRandomAreaParams.cs`
- `AAEmu.Game/Models/Game/Skills/Templates/BuffTemplate.cs`
- `AAEmu.Game/Models/Game/Skills/Templates/SkillTemplate.cs`
- `AAEmu.Game/Models/Game/Units/Buffs.cs`
- `AAEmu.Game/Models/Game/Units/CombatResourceState.cs`
- `AAEmu.Game/Models/Game/Units/Unit.cs`
- `AAEmu.Game/Models/Game/Units/UnitEvents.cs`
- `AAEmu.Game/Models/Tasks/CombatResourceRecoveryTask.cs`
- `AAEmu.Game/Models/Tasks/Skills/InterruptSkillTask.cs`

### Doodads, areas y efectos diferidos

- `AAEmu.Game/Core/Managers/UnitManagers/DoodadManager.cs`
- `AAEmu.Game/Models/Game/DoodadObj/Doodad.cs`
- `AAEmu.Game/Models/Game/DoodadObj/Funcs/DoodadFuncClout.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/InteractionEffect.cs`
- `AAEmu.Game/Models/Game/World/AreaShape.cs`
- `AAEmu.Game/Models/Game/World/Interactions/SummonDoodad.cs`
- `AAEmu.Game/Models/Tasks/Doodads/DoodadFuncCloutTask.cs`

### Instrumentacion y regresiones directamente asociadas

- `AAEmu.Game/Models/Game/Skills/NativeSkillLiveTrace.cs`
- `AAEmu.Game/Models/Game/Skills/SorceryLiveTrace.cs`
- `AAEmu.Tests/Aa8HeirProgressionTests.cs`
- `AAEmu.Tests/Aa8HeirSorceryProtocolTests.cs`
- `AAEmu.Tests/AreaTriggerBuffTagTests.cs`
- `AAEmu.Tests/CombatResourceRuntimeTests.cs`
- `AAEmu.Tests/DamageAggroBroadcastTests.cs`
- `AAEmu.Tests/NativeRestoreManaEffectTests.cs`
- `AAEmu.Tests/NativeSkillLiveTraceTests.cs`
- `AAEmu.Tests/PlotCastingStateTests.cs`
- `AAEmu.Tests/PlotCombatDiceResultTests.cs`
- `AAEmu.Tests/PlotRandomAreaHeightTests.cs`
- `AAEmu.Tests/SkillEndedPacketSerializationTests.cs`
- `AAEmu.Tests/SkillMovementTests.cs`
- `AAEmu.Tests/SorceryAbsorptionRuntimeTests.cs`
- `AAEmu.Tests/SorceryDamageEffectTests.cs`
- `AAEmu.Tests/SorceryLiveTraceTests.cs`
- `AAEmu.Tests/SorceryManaCostTests.cs`
- `AAEmu.Tests/SorcerySpecialEffectPrimitiveTests.cs`

Los constructores, auditores, manifiestos y checkpoints versionados viven en
`reconstruccion_skills_8/sorcery/`. El cierre vigente usa especialmente
`reconstruccion_skills_8/sorcery/build_sorcery_runtime_v23.py`,
`reconstruccion_skills_8/sorcery/test_sorcery_ancestral_closure_v23.py` y
`reconstruccion_skills_8/sorcery/generated/sorcery-runtime-v23.manifest.json`.
La captura viva final es
`runtime-captures/native-skill-live-sorcery-close-v24.{json,csv}`. El JSON
tiene SHA-256
`DD7FC017F43B869CCCCCBDC63068C79A4E4FE7D972F7A58848AA16FBFDE44EDC` y
el CSV
`CEB9C69563B978FE86C7F2BBDE5913E1DC1E48D2CC35DB94A516AD3782D65740`.
La instrumentacion informa `effect=12209`: es el `actual_id` de DamageEffect
alcanzado mediante el wrapper AA8 `effects/76543`, no una identidad distinta.

## Criterio reusable para cerrar otra rama

Una rama nueva debe pasar, en este orden:

1. inventario visible, interno, pasivo y ancestral;
2. clausura AA8 completa y relaciones owner-keyed;
3. crosswalk obligatorio para cada vacio;
4. escalamiento a cached result/binario solo con bloqueo exacto;
5. implementacion de primitivas compartidas antes de hacks por skill;
6. constructor reproducible, manifiesto, hashes e integridad;
7. pruebas focales y suite completa;
8. despliegue Game aislado con rollback;
9. matriz viva, una interaccion por vez;
10. promocion a `live_accepted` solo con traza autoritativa.

Archery ya valido la reutilizacion del metodo y encontro nuevas primitivas
genericas: requisitos de arma, condiciones target HP, liberacion porcentual de
casteos, CombatDice materializado, Landing y RemoveOnMove. Esos hallazgos se
integran a la guia comun en vez de quedar ocultos como excepciones de Archery.

Archery tambien refuto una suposicion del primer auditor: una clausura dirigida
sin blockers no demuestra los caches de lookup inverso. `tagged_skills` no era
alcanzable desde el walker, aunque `skill_modifiers` la consumia por tag. V3
cerro 356 filas AA8; V4 demostro que `passive_buffs -> buffs -> tagged_buffs`
tenia el mismo problema y reemplazo 229 relaciones para 49 owners, incluidas
21 relaciones de las seis pasivas. Este pase bidireccional forma ahora parte
del proceso comun antes de cualquier aceptacion viva.

## Referencias de evidencia

- `sorcery/CHECKPOINT_SORCERY_NATIVE_RUNTIME_V4.md` a V10;
- `sorcery/CHECKPOINT_SORCERY_METEOR_LIGHTNING_AGGRO_V13.md`;
- `sorcery/CHECKPOINT_SORCERY_AGGRO_CHANNEL_V14.md` a V20;
- `sorcery/CHECKPOINT_SORCERY_PERIODIC_DAMAGE_BATCH_V21.md`;
- `sorcery/CHECKPOINT_SORCERY_RANDOM_AREA_GROUNDING_V22.md`;
- `sorcery/CHECKPOINT_SORCERY_ANCESTRAL_CLOSURE_V23.md`;
- `sorcery/CHECKPOINT_SORCERY_LIVE_TRACE_V1.md`;
- `archery/CHECKPOINT_ARCHERY_EXECUTABLE_V2.md`;
- `archery/CHECKPOINT_ARCHERY_TAG_CLOSURE_V3.md`;
- `archery/CHECKPOINT_ARCHERY_PASSIVE_TAG_CLOSURE_V4.md`;
- `LIVE_ACCEPTANCE_SORCERY_ARCHERY_V1.md`.
