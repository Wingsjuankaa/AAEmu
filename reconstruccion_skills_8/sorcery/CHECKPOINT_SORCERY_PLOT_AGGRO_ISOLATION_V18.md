# Checkpoint Sorcery Plot aggro isolation V18

## Frontera probada por V17

En la prueba viva de Meteor Strike Lightning 36479, el ultimo C2S fue
`CSStartSkillPacket` a las `00:26:33`. En ese mismo segundo el servidor envio
los impactos Plot, tres `SCUnitAiAggroPacket`, los buffs 21557 y
`SCPlotEndedPacket`. No hubo otro C2S. El primer tick periodico ocurrio despues,
con sus `SCUnitDamagedPacket(CastBuff)` suprimidos por V17. El socket Stream se
cerro a `00:26:37` por timeout.

Esto demuestra que la secuencia inicial Plot, no el tick, detiene al cliente.

## Cambio diagnostico

- se restaura el broadcast de todos los `SCUnitDamagedPacket`, incluido
  `CastBuff`;
- se conserva la IA y aggro autoritativos mediante `Npc.OnDamageReceived`;
- se omite exclusivamente `SCUnitAiAggroPacket` para `CastPlot` y `CastBuff`;
- `CastSkill` sigue enviando aggro como control positivo.

La sonda es transversal por tipo de origen; no contiene IDs de Sorcery.

## Criterio vivo

- si el cliente supera la secuencia inicial y los ticks, el defecto esta en la
  rafaga de aggro Plot;
- si deja de responder antes del tick, el aggro queda descartado y se aisla el
  siguiente grupo inicial: damage Plot, buff 21557, doodad o PlotEnded;
- si supera el inicio pero falla al primer tick, se reabre la frontera
  periodica con la nueva evidencia temporal.

## Verificacion automatica

- politica focal: `2/2`;
- suite completa con compact activa montada: `520/520`;
- SDK .NET Core 3.1 y ScriptCompiler: sin errores;
- SQLite, Login y MySQL: sin cambios.

## Resultado vivo

V18 fue parcialmente positiva y separo dos fallos superpuestos:

- `CSStartSkillPacket` se recibio a las `00:36:32`;
- los tres impactos `CastPlot` y `SCPlotEndedPacket` se enviaron a las
  `00:36:33` sin publicar la tabla de aggro Plot;
- a diferencia de V17, el cliente sobrevivio a la secuencia inicial;
- desde `00:36:34` hasta `00:36:41` recibio una rafaga sostenida de
  `SCUnitDamagedPacket(CastBuff)` sobre tres objetivos;
- el socket se cerro a las `00:36:42`, sin excepcion ni reinicio del servidor.

Conclusion: la rafaga de `SCUnitAiAggroPacket` de los impactos Plot era el
primer disparador. Al retirarla, queda expuesto un segundo disparador tardio en
las notificaciones periodicas `SCUnitDamagedPacket(CastBuff)`. V19 debe combinar
ambos aislamientos para validar las dos fronteras en una sola ejecucion.
