# Checkpoint Sorcery V14: canal inmediato de aggro AA8

Fecha: 2026-08-06  
Cliente autoridad: ArcheAge Kakao `8.0.3.12 r558734`  
Rama: `client_version/8.0.3.12-kakao-r558734-port`

## Hipotesis desplegada

Meteor Strike Lightning (`skill 36479`) ya ejecutaba correctamente su impacto,
Greater Shock y la propagacion entre tres objetivos. El snapshot de V13 elimino
la excepcion concurrente del servidor, pero el cliente todavia se desconectaba
despues de procesar la rafaga completa.

La hipotesis de esta etapa estaba en el envelope de
`SCUnitAiAggroPacket`: el port experimental AA8 lo enviaba por nivel `5`,
mientras el contrato heredado usa nivel `1`.

El paquete usa ahora nivel `1` y captura exactamente tres escalares `int32` por
entrada.

## Resultado vivo posterior: no aceptado

La prueba controlada del `2026-08-06 23:24` demostro que cambiar el nivel no
elimina la desconexion. El impacto inicial y tres rondas de dano periodico se
procesaron, pero la sesion cliente se cerro tres segundos despues del cast. El
servidor permanecio sano. Por tanto, V14 conserva la correccion del snapshot y
el canal compatible, pero queda falsificada como explicacion causal completa.

`/clearcombat` ejecutado de forma aislada tampoco desconecto al cliente. La
frontera restante se redujo a la rafaga periodica `CastBuff` y su telemetria de
aggro; continua en `CHECKPOINT_SORCERY_AGGRO_TOP_FLAGS_V15.md`.

## Evidencia viva

En la prueba posterior a V13:

- `skill 36479` ejecuto el grafo completo;
- los tres objetivos recibieron el impacto y `buff 21557`;
- los ticks propagados continuaron durante la duracion del buff;
- no hubo `InvalidOperationException`, `ERROR` ni `FATAL` en Game;
- el cliente cerro la conexion despues de la rafaga y Game solo observo el
  cierre normal de los sockets.

Esto separo el fallo de transporte del fallo de concurrencia ya corregido.

## Contrato AA8 del cuerpo

Stage 15 confirma en x64 y x86 que el lector nativo consume:

1. `npcId` en BC;
2. `count` como `int32`;
3. por entrada, `hostileUnitId` en BC;
4. exactamente tres valores `int32`;
5. `topFlags` como `byte`.

Funciones de evidencia:

- x64 wrapper `009bc9e0`, lector `009b8860`;
- x86 wrapper `00b91760`, lector `00b8e2f0`;
- handler x64 `003186c0`, con capacidad nativa para 100 entradas.

La referencia aparente desde `cryrenderd3d10.dll` al mismo RVA era una colision
entre binarios y fue descartada; no se usa como evidencia.

## Evidencia del canal

El commit experimental AA8
`3e55d80f3d30b7534b91c951f73c298986c899f8` sustituyo
`SCAiAggroPacket` por `SCUnitAiAggroPacket` y cambio a la vez el nivel `1` por
`5`, sin una adaptacion del transporte ni evidencia adjunta. El paquete anterior
ya tenia el mismo cuerpo nativo de tres valores y nivel `1`.

Las implementaciones posteriores de AAEmu, incluida la base actual y la rama
10.x usada solo como referencia comparativa, conservaron nivel `1`. Este dato no
promueve protocolo 10.x: restituye el contrato de transporte preexistente y
explica el fallo vivo especifico del port experimental AA8.

## Cambios

`AAEmu.Game/Core/Packets/G2C/SCUnitAiAggroPacket.cs`:

- nivel `5` -> nivel `1`;
- la lista viva se convierte al construir en tres escalares inmutables;
- faltantes se rellenan con cero;
- valores adicionales no alteran el cuerpo nativo.

`AAEmu.Tests/UnitAiAggroPacketTests.cs`:

- conserva la regresion contra mutacion concurrente;
- exige nivel `1`;
- demuestra que solo se serializan tres valores.

## Verificacion

- pruebas focales: `2/2`;
- suite completa con la SQLite autoridad montada: `516/516`;
- build Docker Game: correcto;
- solo Game fue recreado;
- puertos `2239/2250` activos;
- registro en LoginServer correcto;
- rollback: `aaemu-game:rollback-pre-aggro-channel-v14-20260806`.

## Aceptacion viva pendiente

Lanzar una sola vez Meteor Strike Lightning contra los tres scarecrows, esperar
que Greater Shock expire y permanecer conectado al menos 45 segundos. Deben
verse el impacto, los ticks y la propagacion sin popup de desconexion.
