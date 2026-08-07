# Checkpoint Sorcery combined wire isolation V19

## Objetivo

Validar conjuntamente las dos fronteras cliente-servidor observadas en Meteor
Strike Lightning 36479, sin desactivar dano, muerte, buffs ni aggro autoritativo
en el servidor.

## Evidencia previa

- V17 retiro `SCUnitDamagedPacket(CastBuff)`, pero el cliente dejo de enviar
  antes del primer tick porque aun recibia la rafaga de aggro Plot.
- V18 retiro `SCUnitAiAggroPacket` para `CastPlot` y `CastBuff`. El cliente
  supero el impacto inicial, recibio ticks `CastBuff` entre `00:36:34` y
  `00:36:41`, y se desconecto a las `00:36:42`.

La diferencia temporal prueba dos disparadores superpuestos, no una caida del
servidor.

## Cambio diagnostico

- `SCUnitAiAggroPacket` no se publica para `CastPlot` ni `CastBuff`;
- `SCUnitDamagedPacket` no se publica para `CastBuff`;
- el impacto `CastPlot` sigue publicando `SCUnitDamagedPacket`;
- `Npc.OnDamageReceived` sigue ejecutandose para todos los origenes, por lo que
  HP, muerte y seleccion de objetivo continúan siendo autoritativos;
- `CastSkill` permanece como control positivo para ambos paquetes.

La politica es transversal por tipo de `CastAction`; no contiene IDs de
Sorcery, Meteor, buffs ni NPCs.

## Criterio vivo

Lanzar una sola vez Meteor Strike Lightning sobre tres dummies y permanecer en
el mundo mas de 15 segundos.

- deben verse los impactos iniciales;
- no se veran numeros flotantes de los ticks periodicos durante esta sonda;
- los HP internos deben seguir disminuyendo y los NPC pueden morir;
- el cliente no debe desconectarse.

Si se mantiene conectado, quedan confirmadas ambas fronteras y el siguiente
paso es reconstruir sus contratos de wire nativos, no conservar las
supresiones como solucion definitiva.

## Verificacion automatica

- politica focal: `2/2`;
- suite completa con compact activa montada: `520/520`;
- SDK .NET Core 3.1 y ScriptCompiler: sin errores;
- SQLite, Login y MySQL: sin cambios.

## Resultado vivo

`accepted`: Meteor Strike Lightning 36479 completo su secuencia y el cliente
permanecio conectado cuando se aislaron conjuntamente la tabla cliente de
aggro para Plot/Buff y la notificacion de dano periodico CastBuff. Esto confirma
que las dos fronteras son reales e independientes; no convierte las
supresiones diagnosticas en contratos nativos finales.

La sesion dejo ademas una evidencia transversal nueva. A las `00:49:39`, la
skill directa AoE 39669 produjo tres `SCUnitAiAggroPacket` consecutivos antes de
que cesara completamente el C2S y los sockets cerraran a las `00:49:42`. Por
tanto el primer defecto no pertenece a Meteor ni a CastPlot: tambien existe
cuando un `CastSkill` agrupa varios danos.
