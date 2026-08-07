# Matriz viva Archery V1

Fecha: 2026-08-07

Autoridad de nombres y descripciones: `localized_texts` AA8 de la compact
activa. Autoridad de IDs y relaciones ancestrales: `skills`, `heir_skills` y
`heir_skill_details` AA8. Los nombres de elemento de las sucesoras se
normalizan al texto que muestra el cliente ingles.

Esta matriz se usa junto a
`reconstruccion_skills_8/LIVE_ACCEPTANCE_SORCERY_ARCHERY_V1.md`. Ejecutar una
sola fila por vez y revisar la traza antes de avanzar.

## Activas base

| Estado | ID | Skill | Nivel | Contrato visible minimo |
|---|---:|---|---:|---|
| pendiente | 14835 | Endless Arrows | 1 | repeticion al mantener, dano ranged y penalizacion a menos de 8 m |
| pendiente | 16210 | Charged Bolt | 3 | dano ranged, slow y golpe no evadible/bloqueable/parry |
| pendiente | 10694 | Float | 10 | elevacion, rango/dano ranged y cancelacion al reutilizar |
| pendiente | 12759 | Mana Force | 15 | dano magico, empuje y restauracion de MP |
| pendiente | 15096 | Blazing Arrow | 20 | dano ranged, Blind acumulable y Stun en cuatro stacks |
| pendiente | 12133 | Snare | 25 | elimina Shackle propio y aplica Snare AoE de 5 m |
| pendiente | 15073 | Deadeye | 30 | buff de ranged attack quieto; movimiento ejecuta RemoveOnMove y termina el bonus |
| pendiente | 11933 | Concussive Arrow | 35 | dano AoE, Shackle, interrupt, CombatDice unico y trigger Landing |
| pendiente | 10708 | Intensity | 40 | aumento gradual de critico ranged e inmunidad a Fear |
| pendiente | 11368 | Double Recurve | 45 | buff de dano de arma ranged y contrato de dos cargas |
| pendiente | 13281 | Missile Rain | 50 | AoE en terreno y contrato de cinco cargas |
| pendiente | 23592 | Snipe | 55 | dano al objetivo y enemigos en la trayectoria, inmunidad 6 s |

IDs internos de Endless Arrows `14836,14837` deben aparecer en la misma
ejecucion encadenada, no como skills que el jugador aprende por separado.
Los ocho conflictos informativos del crosswalk pertenecen exclusivamente a
los plots 5733 (base), 4673 (Stone) y 5735 (Flame): AA10 cambia enlaces y en
seis filas velocidad/tiempo. Probar las tres cadenas completas manteniendo y
soltando el boton; V4 conserva AA8 y no promueve esos valores 10.x.

## Variantes ancestrales

| Estado | Base | Sucesora | Variante | Plot | Contrato adicional |
|---|---:|---:|---|---:|---|
| pendiente | 16210 | 36468 | Charged Bolt: Flame | 2927 | dano y efectos Flame de AA8 |
| pendiente | 16210 | 36469 | Charged Bolt: Gale | 5732 | dano y efectos Gale de AA8 |
| pendiente | 11933 | 36470 | Concussive Arrow: Flame | 2928 | liberar a 0/25/50/75/100%, canal de dano y efectos Flame |
| pendiente | 11933 | 36471 | Concussive Arrow: Mist | 2941 | dano y burbuja localizada `BubbleEffect 7542` |
| pendiente | 13281 | 36472 | Missile Rain: Flame | 2942 | AoE Flame y cargas heredadas |
| pendiente | 13281 | 36473 | Missile Rain: Mist | 2957 | AoE Mist y cargas heredadas |
| pendiente | 14835 | 39663 | Endless Arrows: Flame | 5735 | repeticion Flame sin impacto tardio |
| pendiente | 14835 | 39666 | Endless Arrows: Stone | 4673 | repeticion Stone sin impacto tardio |
| pendiente | 23592 | 41221 | Snipe: Flame | 4047 | trayectoria, dano, lockout heredado y rama target HP <30% |
| pendiente | 23592 | 41219 | Snipe: Lightning | 4046 | liberar a 0/20/40/60/80/100%, trayectoria, dano y efectos Lightning |
| pendiente | 11368 | 42849 | Double Recurve: Flame | 0 | buff Flame y tres cargas de 8 s |
| pendiente | 11368 | 42851 | Double Recurve: Life | 0 | buff Life y tres cargas de 8 s |

Las sucesoras sin fila `unit_reqs` propia heredan el requisito de la base.
Esto debe probarse positivamente con arco y negativamente sin arco.

## Pasivas

Cada prueba debe incluir las dos lineas `[AA8ArcheryPassive]` de la operacion
(`before_apply/after_apply` o `before_remove/after_remove`). La columna
`changed_fields` del resumen es la evidencia primaria; un icono verde sin
cambio servidor sigue siendo fallo.

Advertencia de autoridad: V4 demostro que la base forense AA8 si contiene las
filas actuales; las copias obsoletas estaban en el carrier historico. La
columna de comprobacion distingue contratos declarativos de consumidores
hardcoded/tagged que aun requieren prueba viva. AA10 no aporta balance.

| Estado | Passive ID | Buff ID | Nombre AA8 | Comprobacion |
|---|---:|---:|---|---|
| pendiente | 7 | 486 | Wild Instincts | fila AA8 y modifier: movimiento +8%; medir delta y reversa |
| pendiente | 35 | 888 | Archery Expertise | fila AA8: mana -10% bajo estados de disparo; medir consumo y tags del consumidor |
| pendiente | 2 | 480 | Sharpshooting | fila AA8: escalado de dano por distancia hasta +30%; medir bins de distancia |
| pendiente | 256 | 7565 | Feral Claws | fila AA8: Feral Mark por crit ranged, ataque +40 y cooldown -0,4 s por stack, maximo cinco |
| pendiente | 300 | 889 | Marksman | contrato nativo: tag 3750, attribute 10, +10%; comprobar 24 skills consumidoras |
| pendiente | 255 | 7564 | Eagle Eyes | fila AA8 y modifier: critico ranged +9%; medir delta y reversa |

V4 contiene 356 relaciones `tagged_skills`, 229 `tagged_buffs` para 49 owners
y 21 tags exactos de las seis pasivas. Cubre 35/35 raices sin duplicados y da
24 consumidores al tag 3750. Si el snapshot/probe no cambia pese a esa
clausura, el fallo esta en el consumidor servidor y no se corrige
reinterpretando texto ni importando AA10.

## Filas internas que no son casos de aprendizaje

- login-stage: `12792,12793,12794`;
- Endless Arrows encadenadas: `14836,14837`;
- auxiliares/presentacion ancestrales: `38893,39664,39665,39667,39668,40580`.

Estas filas deben quedar cargadas y alcanzables por sus consumidores, pero no
se cuentan como botones adicionales en la aceptacion del jugador. Si aparecen
como aprendibles, la presentacion/flag `show` esta rota.

## Registro de resultado

Para cada fila sustituir `pendiente` por `pasa` o `falla` y anotar en el mismo
commit/checkpoint: timestamp, personaje, target, `tlId`, primeras/ultimas
lineas de traza, HP antes/despues, relogueo y cualquier excepcion. No agrupar
dos skills en una sola evidencia.
