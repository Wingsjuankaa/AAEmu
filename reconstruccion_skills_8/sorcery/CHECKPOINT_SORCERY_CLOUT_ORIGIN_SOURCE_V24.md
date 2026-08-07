# Checkpoint Sorcery clout origin source V24

Fecha: 2026-08-07

## Hallazgo vivo

La prueba final de Gods' Whip: Wave paso completamente:

- skill `39674`, `tlId=39671`;
- resultado `Success` y `plot_ended cancelled=False`;
- 10 impactos autoritativos;
- dano total y reduccion real de HP: 5.400;
- efectos `11690`, `12133` y `12134`;
- todos los impactos emitieron packet.

Antes de V24, Flame Barrier: Mist completo `41223 -> 41478`, creo diez doodads
`13919`, aplico `24584/24585` a dos dummies y los retiro al expirar. Entre el ultimo
impacto de Gods' Whip y el primer ataque posterior de Archery, sin otra linea
de dano instrumentada, los HP bajaron 3.391 y 3.024 puntos respectivamente.
El usuario confirmo el resultado visible.

La traza anterior mostro sin embargo `skill=0, abilityLevel=1` en los buffs del clout.
Por ello el resumidor clasifico `41478` como
`lifecycle_complete_no_damage_observed`, aunque la mutacion de HP ocurrio.

## Causa

La fila AA8 exacta `doodad_func_clouts/3792` contiene
`use_origin_source=1`. `DoodadManager` cargaba el campo, pero
`DoodadFuncClout` no lo consumia. `SummonDoodad` descartaba la instancia de
skill y `AreaTrigger` aplicaba buffs/efectos con `EffectSource()` vacio.

## Reparacion transversal

Se conserva la instancia originaria mediante:

`InteractionEffect -> SummonDoodad -> Doodad.OriginSkill -> DoodadFuncClout -> AreaTrigger`

`AreaTrigger` usa esa instancia en `EffectSource`, `CastSkill` y los buffs. El
contexto se propaga solo cuando `use_origin_source=true`; el caso falso queda
aislado por prueba.

Archivos directos:

- `AAEmu.Game/Models/Game/DoodadObj/Doodad.cs`;
- `AAEmu.Game/Models/Game/World/Interactions/SummonDoodad.cs`;
- `AAEmu.Game/Models/Game/Skills/Effects/InteractionEffect.cs`;
- `AAEmu.Game/Models/Game/DoodadObj/Funcs/DoodadFuncClout.cs`;
- `AAEmu.Game/Models/Game/World/AreaShape.cs`;
- `AAEmu.Tests/AreaTriggerBuffTagTests.cs`.

## Evidencia y pruebas

- captura previa al arreglo, JSON:
  `runtime-captures/native-skill-live-sorcery-close-v1.json`, SHA-256
  `3E64F74F03DFC7D62955F8CA16E70F02965338581288241239393CFF0CF9B79F`;
- captura previa al arreglo, CSV, SHA-256
  `1BCE525B6D26AA77989742BD0574C773CAC3907B0855EE89DE8E7981122E24E5`;
- captura final V24, JSON:
  `runtime-captures/native-skill-live-sorcery-close-v24.json`, SHA-256
  `DD7FC017F43B869CCCCCBDC63068C79A4E4FE7D972F7A58848AA16FBFDE44EDC`;
- captura final V24, CSV, SHA-256
  `CEB9C69563B978FE86C7F2BBDE5913E1DC1E48D2CC35DB94A516AD3782D65740`;
- prueba focal origin source: 4/4;
- clausura Sorcery V23: 4/4;
- runtime Archery V4: 16/16;
- suite completa SDK 3.1.409: 567/567.

## Gate final aceptado

La repeticion final de Flame Barrier: Mist registro:

1. buffs `24584/24585` atribuidos a skill interna `41478`, nivel 55 y
   `abilityLevel=52`;
2. 16 lineas `[AA8SkillDamage] tree=sorcery skill=41478 effect=12209`;
3. 6.625 de `amount` y delta de HP, sobre dos objetivos, con `packet=True` en
   los 16 impactos;
4. cese al expirar, retiro de buffs y limpieza final de diez doodads `13919`;
5. cero errores en la ventana viva y Game activo con `RestartCount=0`.

`effects/76543` es el wrapper AA8 de `DamageEffect/12209`; la traza registra
el `actual_id`, por lo que ambos identifican el mismo camino autoritativo.
Gods' Whip: Wave y Flame Barrier: Mist quedan `live_accepted`. Con este gate,
Sorcery queda cerrada al 100%.
