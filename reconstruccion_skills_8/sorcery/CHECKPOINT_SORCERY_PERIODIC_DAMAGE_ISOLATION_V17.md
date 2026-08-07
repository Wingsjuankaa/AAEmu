# Checkpoint Sorcery periodic damage isolation V17

## Resultado previo que obliga esta frontera

La prueba viva V16 suprimio exclusivamente `SCUnitAiAggroPacket` para impactos
periodicos cuyo `CastAction` es `CastBuff`. El cliente AA8 siguio dejando de
procesar la sesion en el primer tick del Meteor Strike Lightning 36479, mientras
el servidor continuo sano y aplico todos los ticks hasta retirar los buffs.

Esto descarta el canal de aggro periodico. El primer paquete exclusivo que queda
en la frontera es `SCUnitDamagedPacket(CastBuff)`.

## Evidencia nativa AA8

El lector x64 de `CastAction`, `FUN_399adb00` (RVA `0x009adb00`), confirma para
el discriminante 2 el orden exacto:

1. `bt` como `uint32`;
2. dueño como BC;
3. `bid` como `uint32`;
4. dos booleanos `t`.

El lector de `SCUnitDamaged`, `FUN_399b0290` (RVA `0x009b0290`), confirma el
prefijo CastAction + SkillCaster, caster/target BC, damage/absorbed PISC, campos
elementales, ushort de estado/hit, byte de flags y resultado. La forma general
del escritor no esta desplazada.

El log vivo tambien descarta un caster Plot expirado: todos los ticks se
serializaron con `SkillCaster=Unit:31645`, el personaje que seguia activo.

## Cambio diagnostico V17

`DamageEffect` conserva sin cambios:

- calculo y mutacion de HP;
- eventos de combate y procs;
- `Npc.OnDamageReceived` y la IA autoritativa;
- buffs, expiracion y todos los ticks.

Solo se omite el broadcast de `SCUnitDamagedPacket` cuando el `CastAction` es
`CastBuff`. Los impactos directos Skill y Plot mantienen su paquete. Esta no es
una reparacion final: es una sonda de un unico paquete para separar el contrato
de wire de la logica autoritativa.

## Criterio de aceptacion vivo

- Si 36479 completa sus ocho segundos sin expulsar al cliente, el defecto queda
  localizado en el envelope o la rafaga `SCUnitDamaged(CastBuff)`.
- Si vuelve a expulsar, ese paquete queda descartado y la siguiente frontera es
  otro paquete emitido por el tick/buff lifecycle.
- Durante V17 no se esperan numeros flotantes de dano periodico en el cliente;
  el HP de los objetivos si debe disminuir en el servidor.

## Verificacion automatica

- politica focal de wire: `2/2`;
- suite completa con la compact activa montada: `520/520`;
- compilacion con SDK .NET Core 3.1: correcta;
- SQLite, Login y MySQL: sin cambios.

## Resultado vivo

`falsified`: el cliente volvio a quedar expulsado. El log demuestra que dejo
de emitir C2S inmediatamente despues de `SCPlotEndedPacket`, antes del primer
tick. Los envelopes periodicos fueron construidos internamente pero V17 no los
transmitio. La desconexion de sockets cuatro segundos despues fue el timeout,
no el instante causal. Por tanto `SCUnitDamagedPacket(CastBuff)` queda
descartado y V17 no debe conservarse como reparacion.
