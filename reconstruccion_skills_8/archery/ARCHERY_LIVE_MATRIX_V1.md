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
| aprobada rifle V5 | 14835 | Endless Arrows | 1 | repeticion al mantener, dano ranged y penalizacion a menos de 8 m |
| barrido base V5 | 16210 | Charged Bolt | 3 | dano ranged, slow y golpe no evadible/bloqueable/parry |
| barrido base V5 | 10694 | Float | 10 | elevacion, rango/dano ranged y cancelacion al reutilizar |
| barrido base V5 | 12759 | Mana Force | 15 | dano magico, empuje y restauracion de MP |
| barrido base V5 | 15096 | Blazing Arrow | 20 | dano ranged, Blind acumulable y Stun en cuatro stacks |
| barrido base V5 | 12133 | Snare | 25 | elimina Shackle propio y aplica Snare AoE de 5 m |
| candidata visual V8 | 15073 | Deadeye | 30 | buff de ranged attack quieto; Multiple 1..N confirmado; falta aceptar en vivo el cierre del FX con `SCBuffRemoved.reason` |
| barrido base V5 | 11933 | Concussive Arrow | 35 | dano AoE, Shackle, interrupt, CombatDice unico y trigger Landing |
| barrido base V5 | 10708 | Intensity | 40 | aumento gradual de critico ranged e inmunidad a Fear |
| barrido base V5 | 11368 | Double Recurve | 45 | buff de dano de arma ranged y contrato de dos cargas |
| barrido base V5 | 13281 | Missile Rain | 50 | AoE en terreno y contrato de cinco cargas |
| barrido base V5 | 23592 | Snipe | 55 | dano al objetivo y enemigos en la trayectoria, inmunidad 6 s |

IDs internos de Endless Arrows `14836,14837` deben aparecer en la misma
ejecucion encadenada, no como skills que el jugador aprende por separado.
Los ocho conflictos informativos del crosswalk pertenecen exclusivamente a
los plots 5733 (base), 4673 (Stone) y 5735 (Flame): AA10 cambia enlaces y en
seis filas velocidad/tiempo. Probar las tres cadenas completas manteniendo y
soltando el boton; V4 conserva AA8 y no promueve esos valores 10.x.

Aceptacion con rifle V5: la cadena `14835 -> 14836/14837` produjo 16
timelines aceptados, 13 impactos autoritativos, consumo de MP y HP
decreciente. No aparecio `UrkEquipRanged`. Los rechazos intermedios
`CooldownTime` corresponden a solicitudes del cliente durante la repeticion y
no invalidan las ejecuciones exitosas.

Barrido transversal V5 con rifle: las 12 activas base fueron aceptadas y
completaron timeline. Las ofensivas `11933, 12759, 13281, 14835/14836/14837,
15096, 16210, 23592` registraron dano autoritativo y HP decreciente. Las de
movilidad/control/buff `10694, 10708, 11368, 12133, 15073` completaron sin
rechazo de equipamiento. Este estado confirma ejecucion base; los efectos
secundarios detallados del contrato permanecen como comprobaciones separadas.

Deadeye revelo una regresion transversal posterior al barrido: el icono y el
bonus se retiraban, pero el FX visible permanecia en el personaje. V7 restauro
correctamente `StackRule.Multiple` y la traza viva comprobo altas 1..N y el
retiro de todos los indices; el FX persistio, por lo que esa explicacion fue
falsificada como causa completa. V8 recupera el layout nativo AA8 omitido en
`SCBuffRemoved`: `unitId + buffId/index + reason`. El gate vivo exige acumular
varias cargas, quedarse quieto y comprobar que desaparezcan icono, bonus y FX
sin relogueo, mientras el log muestra `reason=0`.

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

Hallazgo vivo V9 para las dos variantes `casting_useable`: el segundo uso no
repite `CSStartSkill`. AA8 r558734 emite `0x159` con cuerpo exacto
`actorObjId(BC,3) + mode(uint16) + plotTlId(uint16)`. El layout inicial habia
tratado `mode` como byte, desplazando el timeline y descartando silenciosamente
todas las liberaciones. Saltar era el control positivo porque usa
`CSStopCasting 0x004`. La aceptacion debe mostrar `[AA8SkillCastRelease]` sin
salto al volver a pulsar, en al menos tres porcentajes por variante.

Fending Arrow/Mana Force expuso una frontera letal transversal, pero la
hipotesis V9 de diferir `DoDie` hasta despues del DD04 fue falsificada por las
ejecuciones historicas. La imagen Docker estable de las 20:19 permitia matar
NPC y no contiene `deferDeath`, `FinalizeDeferredDeath` ni acciones post-envio;
la imagen de las 20:38 ya contiene el cambio y coincide con el inicio de la
regresion. La clausura vuelve al flujo sincrono probado de AA8: `DoDie`,
`SCUnitPoints(HP=0)` y finalmente el `SCUnitDamaged` acumulado en DD04. Se
conservan por separado las correcciones confirmadas de killer, aggro, target,
EXP, buffs y contador DD05.

La captura siguiente falsifico otra hipotesis intermedia: una muerte de NPC
causada por el jugador no usa `killer=0`. La rama AA8 original y Modern pasan
el killer real al mismo bloque opcional que el parser nativo AA8 consume. El
sentinela cero queda reservado para muertes sin causante. La traza defectuosa
registro `victim=57282, killer=0`; V10 restaura el killer y fija el contrato
con una prueba de transaccion, ademas de las pruebas del serializer.

La repeticion sin Fending falsifico esa causa como cierre completo: el mismo
NPC desconecto al morir con Endless Arrows aun con el orden corregido. Una
primera lectura promovio incorrectamente el bloque interno creado por
`FUN_39AB5D30` como si fuera el serializer wire: agrego un tercer tiempo
`uint32` y ensancho `type` de byte a `uint32`. El A/B posterior contra la imagen
Docker de las 20:19 demostro que esa imagen funcional transmitia el cuerpo
compacto original. La estructura nativa de estado y el cuerpo de red no son
intercambiables. V15 restaura exactamente el wire observado y fija sus dos
ramas con pruebas byte a byte.

Las sucesoras sin fila `unit_reqs` propia heredan el requisito de la base.
Esto debe probarse positivamente con arco y rifle AA8 validos, y negativamente
sin arma en el slot ranged.

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
### Enmienda V1.13: muerte de NPC y propietario de aggro AA8

- La desconexión que persistía después de corregir `SCUnitDeathPacket`
  no era exclusiva de Fending Arrow: también ocurría al matar el mismo NPC
  con otras habilidades.
- El registro vivo aisló la detención del flujo C2S en la ráfaga de muerte.
  La evidencia nativa x64 `x2game.dll` RVA `0x009B8860` y x86 RVA
  `0x00B8E2F0` confirma `unitAiAggro = npcId BC + count int32 + entries`.
- El servidor emitía el paquete de limpieza con `killer.ObjId`, que en este
  caso era el Character. Se corrigió a `victim.ObjId`: el propietario de la
  tabla de aggro es el NPC muerto.
- El trazado genérico de paquetes nivel 1 ahora incluye `Verbose()` para que
  las futuras fallas entre canales inmediatos y cifrados conserven ID, conteo
  y valores en el log.

### Enmienda V1.14: no aplicar debuffs normales despues de la muerte

La captura `aa8-game-20260808-022320750-session-624062999.jsonl` demostro una
regresion distinta al layout de `SCUnitDeath`. Blazing Arrow (`skill 15096`)
produjo el dano letal y la muerte correcta de la unidad `60415`, pero el mismo
plot continuo y publico despues `SCBuffCreated` para el buff `2214` sobre el
NPC ya muerto. La fila AA8 declara `dead_applicable=0` y `remove_on_death=1`.

La admision se corrigio en la ruta activa `BuffEffect.Apply`: si el objetivo
es una `Unit` con `Hp <= 0`, un buff solo puede entrar cuando su contrato AA8
declara `DeadApplicable`. No se aplico el filtro en `Buffs.AddBuff`, porque ese
punto tambien participa en restauracion e inicializacion y una barrera global
rompia consumidores que todavia no han materializado HP.

La regresion automatizada `DeadUnitRejectsBuffThatIsNotDeadApplicable` fija el
caso y la suite completa pasa 585/585. La aceptacion viva debe matar una vez
con Blazing Arrow, permanecer conectada al menos 15 segundos y verificar que
no aparezca ningun `SCBuffCreated buff=2214` posterior a `SCUnitDeath`.

### Enmienda V1.15: distinguir estado nativo y wire de `SCUnitDeath`

- La captura posterior a la reversión de muerte diferida cerró el peer tras el
  único `SCUnitDeath` de la sesión; DD05 siguió monotónico y el cliente alcanzó
  a responder un `Ping` antes de cerrar.
- El diff de ensamblados `4d829910...` (20:19, funcional) contra
  `260648813...` aisló siete bytes añadidos al cuerpo de muerte.
- `FUN_39AB5D30` inicializa un bloque interno de 17 bytes, pero no es el
  serializer de red. Promover sus cinco campos directamente desplazó la rama
  condicional con killer.
- El contrato wire vuelve a dos `uint32` antes de `lostExp` y a `type u8`; se
  preservan killer real, reason real, nombre y el resto del cierre letal.
