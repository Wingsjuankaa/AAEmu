# Checkpoint Sorcery periodic damage batch V21

## Resultado implementado

V21 restaura la notificacion cliente de `SCUnitDamagedPacket` para impactos
periodicos `CastBuff` sin reabrir la tabla cliente de aggro que las pruebas
vivas V16-V19 aislaron como una frontera incompatible.

El estado autoritativo de HP, los calculos de dano y `Npc.OnDamageReceived`
ya funcionaban en V19. Lo que faltaba era hacer visible cada tick al cliente
sin provocar el cierre tardio de su flujo C2S.

## Frontera nativa y causa

El lector AA8 `x2game.dll!FUN_399adb00` confirma el cuerpo de `CastBuff` tipo
2: `bt`, owner BC, `bid` y dos booleanos. Por ello V21 no cambia el cuerpo de
`CastBuff` ni inventa semantica para sus dos booleanos opacos.

La diferencia demostrable estaba en la frontera de transporte:

- `Skill.ApplyEffects` agrupa los efectos de una accion en un `DD04`;
- `PlotTree` agrupa de igual manera su cola de ejecucion;
- `BuffTemplate.TimeToTimeApply` publicaba cada efecto periodico por separado,
  y un aura solapada podia producir varios sobres fiables por segundo.

V18 demostro que el primer `CastBuff` no era fatal: el cliente consumio ticks
desde `00:36:34` hasta `00:36:41` y cerro a `00:36:42`. Esa latencia es
coherente con perdida del limite transaccional bajo una rafaga sostenida, no
con una desalineacion inmediata del primer cuerpo.

## Cambio V21

`BuffTemplate.TimeToTimeApply` crea un solo `CompressedGamePackets` por tick,
lo comparte con todos los `EffectTemplate.Apply` del tick —incluido el barrido
de `DoAreaTick`— y lo publica una sola vez desde el owner si contiene paquetes.

`DamageEffect.ShouldBroadcastDamagePacket` vuelve a aceptar `CastBuff`; cuando
recibe el builder, cada dano se agrega al lote en vez de transmitirse de forma
independiente. `ShouldBroadcastAggroPacket` conserva la compuerta V19:
`CastPlot` y `CastBuff` siguen sin publicar `SCUnitAiAggroPacket`, aunque la IA
y el aggro autoritativos del NPC continuan actualizandose en el servidor.

Tambien se corrigio el orden de nulidad de `owner`: ya no se consulta el mundo
alrededor de un owner nulo antes de usar al caster como fallback.

## Evidencia comparativa obligatoria

El crosswalk AA8->10.x r575 confirma continuidad estructural para skill 36479,
buff 21557 y sus relaciones de tick. La fila 10.x de buff aparece como
`stable_id_changed_properties`, por lo que no se importaron tiempos, balance ni
propiedades 10.x. La autoridad de runtime sigue siendo AA8.

## Verificacion automatica y despliegue

- pruebas focales `DamageAggroBroadcastTests`: 2/2;
- suite completa con `AAEMU8_SORCERY_RUNTIME` apuntando a la compact AA8 activa:
  520/520;
- imagen V21: `sha256:ee11184c2efe2782b821286d6e6951c26bcd870a56f0de8db37a0f9b67b2d5bd`;
- rollback V20: `aaemu-game:rollback-pre-periodic-tick-batch-v21-20260806`,
  `sha256:6e2a6b95a783c81f1322b10c49ddbe9e75f476c6704cf6f1f9297eefda045152`;
- solo se recreo `aaemu8-game-1`; Login y MySQL quedaron intactos;
- puertos 2239 y 2250 aceptan conexiones, proceso running, cero reinicios.

## Aceptacion viva: aprobada

Prueba correlacionada el 2026-08-06:

- primer uso de skill 36479 a las `02:06:53`, `result=Success`, tres objetivos;
- segundo uso de skill 36479 a las `02:07:14`, `result=Success`, tres objetivos;
- cada uso creo buff 21557 en NPC 10458, 9971 y 9154;
- los tres buffs del primer uso se retiraron a las `02:07:03` y los del
  segundo a las `02:07:23`, sin excepcion ni cierre de Game;
- durante cada intervalo el contador de salida avanzo sobre los lotes DD04. Al
  estar comprimidos, los `SCUnitDamagedPacket(CastBuff)` internos ya no se
  registran como sobres individuales, que es precisamente la frontera V21;
- hubo actividad cliente posterior al primer ciclo y `SCCombatClearedPacket`
  a las `02:07:53`, treinta segundos despues del segundo ciclo;
- a las `22:08:52 -04:00` la conexion TCP de juego iniciada a las `22:05:56`
  seguia `Established`;
- `aaemu8-game-1` continuaba `running`, con cero reinicios y sin eventos de
  desconexion de la sesion en la ventana observada;
- el usuario confirmo que no fue expulsado del servidor.

V21 queda **aceptada** para dano periodico visible agrupado de Meteor Strike:
Lightning 36479. La compuerta de aggro cliente para `CastBuff` y `CastPlot`
permanece intencionalmente cerrada hasta reconstruir esa tabla por separado.
