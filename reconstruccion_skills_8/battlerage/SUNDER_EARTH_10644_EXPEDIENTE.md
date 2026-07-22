# Expediente de cierre — Sunder Earth (10644)

## Estado

**Cerrada funcionalmente en la prueba local.**

La habilidad ya ejecuta el casteo, animación, sonido, daño, picos de piedra,
zona persistente, aplicación/retirada de `Earth Energy` y reducción real del
30 % sobre daño melee y spell. Queda pendiente únicamente la regresión con un
segundo cliente exigida por el plan general de replicación multijugador.

Este expediente registra la cadena completa porque las correcciones son
primitivas reutilizables por otras habilidades basadas en plots, objetivos de
posición, proyectiles visuales, doodads de área y modificadores de atributos.

## Fuente de verdad

- Cliente: Kakao 8.0.3.12 `r558734`.
- Compact runtime validada:
  `compact-8.0-runtime-phase4-battlerage-v1.sqlite3`.
- SHA-256 de la compact runtime:
  `84990525F520B22BEBB3EAE4A0941B16A5A78C0A900F697E12AF69017D7B7871`.
- Manifiesto de clausura:
  `generated/battlerage-phase4-closure.json`.
- Los layouts de protocolo indicados abajo se confirmaron en `x2game.dll`; no
  se dedujeron desde versiones históricas.

## Cadena de datos AA8

### Habilidad y plot

- Skill: `10644`.
- Ability: Battlerage (`ability_id=1`), nivel 20.
- `plot_only=1`, plot `649`.
- Casteo: `500 ms`.
- Cooldown: `16000 ms`, tag `4156`.
- Animaciones: `fire_anim_id=412`, `start_anim_id=413`, dos manos `414`.
- Grupo FX de la habilidad: `199`.
- Área declarada: radio `9`, ángulo `45`, máximo `20` objetivos.

### Impacto y picos de piedra

El plot 649 usa objetivos `Location` y ejecuta esta secuencia confirmada:

| Evento | Efecto | Tipo | Retraso al siguiente |
|---:|---:|---|---:|
| 5320 | 9502 | SpecialEffect / projectile 139 | 50 ms |
| 5321 | 9503 | SpecialEffect / projectile 139 | 100 ms |
| 5322 | 9504 | SpecialEffect / projectile 140 | 150 ms |
| 5328 | 9506 | SpecialEffect / projectile 140 | 200 ms |
| 5327 | 9505 | SpecialEffect / projectile 141 | 250 ms |

Los proyectiles visuales usan los grupos FX `734`, `736` y `737`. Los golpes
autoritativos principales alcanzados por el plot son `DamageEffect 4254` y
`DamageEffect 10196`.

### Zona persistente

- Evento `5319` → `InteractionEffect 3435` → doodad `3941`.
- Evento `23028` → `InteractionEffect 6608` → doodad `12120`.
- Ambos efectos usan `source_direction=1`.
- El clout de área normal es `doodad_func_clout 865`:
  - `aoe_shape_id=544`;
  - `buff_id=2596`;
  - duración `7000 ms`;
  - `projectile_id=248`;
  - relación objetivo `1`;
  - exclusión por tag `805`;
  - `use_origin_source=1`.

Existe además la variante de datos `8000010`, con el mismo buff y duración,
para su forma AoE correspondiente.

### Earth Energy y reducción de daño

- Buff: `2596` (`Earth Energy` / `대지의 기운`).
- Descripción AA8: daño recibido reducido en 30 %.
- FX: `549`; icono: `840`; máximo de stacks: `1`.
- Modificador confirmado en `unit_modifiers`:
  - `owner_type='Buff'`;
  - `owner_id=2596`;
  - `unit_attribute_id=58` (`IncomingDamageMul`);
  - `unit_modifier_type_id=0` (`Value`);
  - `value=-300`.

El backend expresa este atributo en milésimas:

```text
IncomingDamageMul = 1 + (-300 / 1000) = 0,70
```

La fórmula se aplica a daño melee, ranged y spell antes de convertir el daño
final a entero. No se añadió una excepción por ID; se utiliza el sistema
genérico de `BonusTemplate` y `UnitAttribute.IncomingDamageMul`.

## Evidencia de ejecución

La prueba del 22-07-2026 quedó registrada con el personaje `ObjId 189372` y el
mismo atacante periódico:

```text
21:29:06  daño sin Earth Energy: 63
21:29:07  SCBuffCreated buff=2596 owner=189372
21:29:07  daño con Earth Energy: 44
21:29:08  daño con Earth Energy: 44
21:29:09  daño con Earth Energy: 44
21:29:10  daño con Earth Energy: 44
21:29:11  daño con Earth Energy: 44
21:29:12  daño con Earth Energy: 44
21:29:13  SCBuffRemoved
21:29:13  daño sin Earth Energy: 63
```

`63 × 0,70 = 44,1`, truncado por la fórmula de daño a `44`. Una segunda captura
con el diagnóstico temporal `[AA8IncomingDamage]` confirmó también golpes
melee directos dentro del aura:

```text
274,27 × 0,700 = 191,99 → 191
210,92 × 0,700 = 147,64 → 147
166,29 × 0,700 = 116,41 → 116
138,91 × 0,700 =  97,24 →  97
253,52 × 0,700 = 177,46 → 177
```

Fuera del aura, tanto melee como spell registraron `incomingMul=1,000`; dentro
del aura ambos registraron `incomingMul=0,700`. Los números flotantes de
`100–200` observados por el jugador son coherentes con los golpes melee ya
reducidos, no con una presentación incorrecta. El diagnóstico temporal se
retiró del código fuente después de obtener esta evidencia.

## Cambios transversales necesarios

1. **Carga de datos AA8:** ampliación de plots, efectos especiales y campos
   adicionales de la compact 8.0 en `PlotManager` y `SkillManager`.
2. **Destino Location:** `PlotEventEffect.ResolveEffectTargets` trata la
   posición como un único destino sintético y no la multiplica por las unidades
   del AoE.
3. **Serialización de PlotObject:** el objeto posicional AA8 incluye dos
   transforms y tres referencias BC. El tail faltante desplazaba el resto de
   `SCPlotEvent` y ocultaba los FX de posición.
4. **SCPlotEvent AA8:** se serializa `inputDirection` después de los flags y del
   bloque opcional de 13 valores, según el consumidor del cliente.
5. **SpecialEffect:** se cargan `value5`, `value6` y `value7`, preservando el
   layout AA8 de las primitivas alcanzadas.
6. **InteractionEffect:** se carga `source_direction`, necesario para orientar
   correctamente doodads creados por una habilidad.
7. **SCDoodadCreated:** el payload AA8 contiene `updatedTime` de 64 bits después
   de `data2`. Sin esos ocho bytes el cliente no terminaba de inicializar la
   fase ni sus FX asociados.
8. **Modificador autoritativo:** la fila `IncomingDamageMul=-300` ya entra por
   la primitiva genérica `BuffTemplate.Start → Unit.AddBonus → DamageEffect`.
   La investigación no justificó modificar la fórmula de daño.

## Archivos y regresiones

Archivos principales implicados:

- `AAEmu.Game/Core/Managers/PlotManager.cs`
- `AAEmu.Game/Core/Managers/SkillManager.cs`
- `AAEmu.Game/Core/Packets/G2C/SCPlotEventPacket.cs`
- `AAEmu.Game/Models/Game/DoodadObj/Doodad.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/InteractionEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/PlotEventEffect.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/PlotObject.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotNode.cs`
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotState.cs`

Pruebas asociadas:

- `AAEmu.Tests/PlotEventPacketTests.cs`
- `AAEmu.Tests/PlotEventEffectTargetTests.cs`
- `AAEmu.Tests/DoodadSerializationTests.cs`
- `AAEmu.Tests/IncomingDamageModifierTests.cs`

La última prueba verifica con los valores reales de AA8 que el buff pasa los
cuatro multiplicadores de daño entrante de `1,0` a `0,7`, convierte `63` en
`44` y vuelve a `1,0` al retirarse.

## Lista de aceptación reutilizable

Para cualquier habilidad similar se debe comprobar, en este orden:

1. clausura completa de skill, plot, efectos, proyectiles, doodads y buffs;
2. serialización íntegra de los objetos de unidad y posición;
3. aparición del impacto inicial y su secuencia temporal;
4. creación, fase y retirada del doodad persistente;
5. aplicación visual del buff/debuff;
6. fila autoritativa de `unit_modifiers` y escala de su atributo;
7. daño/curación real antes, durante y después del modificador en logs;
8. repetición, relog y observación desde un segundo cliente.
