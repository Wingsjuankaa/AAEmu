# Auditoría transversal Battlerage V2 AA8

## Alcance y autoridad

La auditoría parte de la compact y del corpus nativo de ArcheAge Kakao
8.0.3.12 r558734. `rama_8_modern` se consultó únicamente como comparador de
implementación. El crosswalk 10.x fue el pase obligatorio para reducir vacíos
de identidad y relación, pero ninguna fila 10.x fue promovida al runtime.

## Inventario cerrado

- 42 skills Battlerage: 37 raíces/variantes jugables, 3 automáticas y 2
  internas obsoletas.
- 12 activas visibles con costo de puntos.
- 3 automáticas visibles de costo cero: `34119`, `34120`, `34124`.
- 6 pasivas exactas: `29`, `32`, `92`, `244`, `245`, `295`.
- 115 relaciones `skill_effects`.
- 18 plots y todas sus transiciones alcanzables.
- 64 buffs alcanzables.
- 299 relaciones `tagged_skills` y 287 `tagged_buffs`.
- 1.571 skill modifiers nativos.
- Cero efectos, tipos de plot, animaciones, proyectiles o formas AoE jugables
  sin resolver.

El controller `604` sólo aparece en la skill oculta obsoleta `11854`, por lo
que se conserva como evidencia negativa y no bloquea Battlerage jugable.

## Presentación

Los nodos `Anim`, `FxGroup`, `FxGroupAnim`, `Projectile` y `ProjectileAnim`
son instrucciones de presentación consumidas por el cliente al recibir los
eventos de skill/plot. El servidor conserva los IDs, orden y target nativos; no
se inventan efectos visuales backend.

Familias con plot o controller relevante:

| Familia | Plot/controllers AA8 |
|---|---|
| Triple Slash | plots `2541`, `2855–2857` |
| Charge | plot `624`; controllers `6779/8229` |
| Whirlwind Slash | plots `133`, `2230`, `2231` |
| Sunder Earth | plots `649`, `4044`, `4045` |
| Precision Strike | plots `2903`, `2921` |
| Tiger Strike | plots `17`, `2922`, `2923`; controllers `2278/2279`, `11024–11028`, `11067/11068` |
| Ollo's Hammer | plot `440`; controller `11306` |
| Behind Enemy Lines | controllers `10258`, `11525`, `11526` |
| Bladefall automática | plot `8000065` |

## Primitives revalidadas

| Primitive | Resultado |
|---|---|
| Mana/cooldown/GCD | implementación genérica y reloj manual/real cerrados |
| StopManaRegen | scheduler real/manual cerrado |
| CancelStealth | remoción genérica de buffs cerrada |
| KnockBack | movimiento genérico y fixture permanente PASS |
| CombatDice | acierto determinista del Lab y ramas de override cubiertas por tests |
| AoE | radio específico AA8, orden determinista y cap de targets cerrados |
| RandomUnit | columnas nativas `param7/8/9` confirmadas |
| Area target de volumen cero | conserva target previo; Ollo's Hammer PASS |
| AutoAttack/automáticas | identidades/consumidores presentes; aceptadas en el cierre vivo de primera etapa V10 |

No se añadieron hacks por skill ID ni se cambió opcode, nivel, anchura, orden o
rama condicional de paquetes.

## Resultado ejecutable

- Battlerage Mechanics Lab: 24/24 PASS dos veces.
- Determinismo: 24/24 hashes idénticos.
- Archery/muerte de NPC: 4/4 PASS.
- .NET Core 3.1: 600/600 PASS.
- Validadores estructurales: 9/9 V2 y 6/6 Phase 4.
- Certificación A/B: `C4A5DC628D1645915C0CDC730DC33FA112F958CA54AA04AB45E2428F12B22693`.

La aceptación visual de primera etapa quedó cerrada en
`CHECKPOINT_BATTLERAGE_STAGE1_CLOSURE_V10.md`. Persistencia prolongada,
segundo cliente y combinaciones de soak permanecen como robustecimiento
posterior, según `MATRIZ_BATTLERAGE.md`.
