# Checkpoint Sorcery V13: Meteor Strike Lightning y snapshot de aggro

Fecha: 2026-08-06  
Cliente autoridad: ArcheAge Kakao `8.0.3.12 r558734`  
Rama: `client_version/8.0.3.12-kakao-r558734-port`

## Resultado

La variante ancestral Lightning de Meteor Strike (`skill 36479`) ejecutaba su
grafo AA8 correcto contra tres objetivos, pero el primer tick simultaneo de
Greater Shock (`buff 21557`) podia desconectar al cliente. La causa no era una
skill, buff o ID ancestral equivocado: `SCUnitAiAggroPacket` conservaba una
referencia a `Character.SummarizeDamage` y la enumeraba cuando otros ticks de
combate todavia modificaban esa misma lista.

El paquete conserva ahora una instantanea inmutable tomada en su constructor.
La correccion es transversal a cualquier dano AoE o DoT concurrente y no cambia
el contrato de bytes del paquete.

## Evidencia viva del fallo

La ejecucion observada a las `22:27:52` fue:

```text
CSStartSkillPacket skill=36479
plot 2950: 24483 -> 24486 -> 24484
24484 -> 24488 (por objetivo, dano inicial)
24484 -> 24491 (crea doodad 888)
24488 -> 24489 -> 24490 (aplica buff 21557 Greater Shock)
SCPlotEndedPacket
primeros ticks de buff sobre tres objetivos
InvalidOperationException: Collection was modified
  at SCUnitAiAggroPacket.Write(...):36
```

Antes de la excepcion, los tres objetivos recibieron dano inicial (`830`,
`780`, `740`) y Greater Shock. Los pulsos posteriores de `30/45` son el efecto
periodico y propagado declarado por el buff, no una habilidad ajena.

## Pase obligatorio AA8 -> 10.x

El crosswalk V1 confirma identidad estable para:

- `skills:36479` -> `plot_id=2950`, `fx_group_id=2889`, `projectile_id=831`;
- `plots:2950`;
- `plot_events:24491` como `exact_id_exact_relation`;
- `plot_events:26071` como ID estable con propiedades descriptivas cambiadas;
- `plot_next_events:28505`, clave natural
  `24484 -> 24491`, como `exact_id_exact_relation`.

Se reviso luego la SQLite raw 10.x r575 de forma acotada. Tanto AA8 como 10.x
contienen el evento `26071` en la posicion 9, pero ninguna de las dos versiones
tiene una transicion entrante o saliente para el. Por lo tanto es evidencia
negativa reproducida entre versiones y no se inventa ni importa una arista.
El grafo ejecutado coincide con la semantica visible del tooltip Lightning:
rayo instantaneo, dano inicial, Greater Shock y dano periodico/propagado.

## Cambio implementado

Archivo:
`AAEmu.Game/Core/Packets/G2C/SCUnitAiAggroPacket.cs`

- `List<int>` viva sustituida por `int[]` privada.
- snapshot `summarizeDamage?.ToArray() ?? Array.Empty<int>()` al construir.
- la serializacion solo enumera el snapshot.

Regresion:
`AAEmu.Tests/UnitAiAggroPacketTests.cs`

La prueba construye el paquete, modifica la lista origen y demuestra que el
payload sigue siendo el capturado en el instante de construccion.

## Verificacion

- prueba focal: `1/1` aprobada;
- suite completa: `515/515` aprobadas;
- no se modifico la SQLite runtime;
- no se importaron propiedades, balance ni relaciones desde 10.x.

## Prueba viva pendiente

Tras desplegar Game, lanzar una sola vez Meteor Strike Lightning contra los
tres scarecrows cercanos y esperar la expiracion completa de Greater Shock.
El criterio de aceptacion es: dano inicial en los tres, ticks durante el buff,
sin `InvalidOperationException` y sin desconexion.

## Resultado de la prueba viva

El snapshot elimino la `InvalidOperationException`: el servidor completo todos
los ticks sin `ERROR` ni `FATAL`. Sin embargo, el cliente se desconecto despues
de la rafaga de paquetes de aggro. La segunda causa y su correccion transversal
quedan documentadas en
`CHECKPOINT_SORCERY_AGGRO_CHANNEL_V14.md`.
