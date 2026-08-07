# Checkpoint Sorcery AoE aggro order V20

## Frontera demostrada

V19 estabilizo Meteor Strike Lightning 36479, pero una skill AoE directa,
39669, genero tres `SCUnitAiAggroPacket` a las `00:49:39`; no hubo mas C2S y la
conexion cerro a las `00:49:42`. El servidor permanecio activo. La causa es por
tanto transversal a los impactos AoE y no exclusiva de Plot o CastBuff.

## Hallazgo de orden

`Skill.ApplyEffects` construye un `CompressedGamePackets` DD04 para las
notificaciones de dano de una skill directa. Antes de V20, `DamageEffect`
agregaba `SCUnitDamagedPacket` al lote, pero publicaba inmediatamente
`SCUnitAiAggroPacket` por fuera del lote. En una skill AoE el cliente recibia
la consecuencia de aggro antes de los danos que seguian pendientes de flush.

V20 conserva el mismo cuerpo de ambos paquetes y cambia solamente su orden:
si existe `packetBuilder`, el aggro se agrega inmediatamente despues del dano
correspondiente dentro del mismo DD04. El camino no agrupado mantiene el orden
anterior `damage -> aggro`.

La compuerta V19 continua suprimiendo provisionalmente aggro para `CastPlot` y
`CastBuff`, y dano cliente para `CastBuff`. Por ello esta etapa valida primero
la reparacion de la skill directa 39669 sin reabrir simultaneamente las otras
dos fronteras.

## Verificacion nativa adicional

La inspeccion de las factories nativas corrigio una lectura preliminar:
`0x210` para `SCUnitDamaged` y `0x808` para `SCUnitAiAggro` son el tamano total
de las asignaciones wrapper, no flags de transporte. No autorizan cambiar el
nivel de los paquetes.

El lector AA8 `FUN_399b0290` confirma ademas que el primer PISC de
`SCUnitDamaged` contiene exactamente dos valores (damage y absorbed), el
segundo exactamente tres, y que los campos elementales, ushort de estado,
byte de flags y byte `result` presentes en el escritor actual mantienen su
alineacion. No se modifico ese cuerpo en V20.

## Verificacion automatica

- pruebas focales de wire/aggro: 6/6;
- suite completa con la compact runtime activa montada: 520/520;
- base AA8 y runtime MySQL: sin cambios.

## Prueba viva

Usar una vez la skill 39669 contra los tres scarecrows y permanecer conectado
al menos 15 segundos. Deben verse los tres impactos y el cliente no debe dejar
de transmitir. Meteor 36479 permanece como control estable V19 durante esta
etapa.

### Intento manual 2026-08-06 01:23

El cliente permanecio conectado, pero la traza autoritativa registra dos usos
de `36479` (Meteor Strike: Lightning), no de `39669`. Este intento reconfirma el
control estable V19 y que V20 no introdujo una regresion en Meteor, pero no
promueve aun la correccion de orden AoE directa a aceptada.

La compact AA8 identifica `39669` como `연속 벼락: 번개`, es decir,
**Chain Lightning: Lightning**. La aceptacion V20 queda pendiente de lanzar
esa variante ancestral, preferentemente encadenando sus usos contra los tres
scarecrows, y observar actividad C2S durante al menos 15 segundos.
