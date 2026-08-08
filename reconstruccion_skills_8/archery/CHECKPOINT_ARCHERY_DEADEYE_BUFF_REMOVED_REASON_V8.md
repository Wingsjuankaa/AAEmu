# Checkpoint Archery Deadeye SCBuffRemoved Reason V8

Fecha: 2026-08-07
Cliente: ArcheAge Kakao 8.0.3.12 r558734
Rama: `client_version/8.0.3.12-kakao-r558734-port`
Runtime: `compact-8.0-runtime-archery-v5.sqlite3` (sin cambios de datos)

## Falsacion viva de V7

La traza del cliente demostro que Deadeye creo `buff 27704` con stacks 1..5
e indices independientes y que el servidor envio una retirada para cada uno.
Tambien retiro `27705` y el buff base `27702`. El icono y el bonus terminaron,
pero el FX rosa/verde permanecio. Por tanto, ni una fila AA8 ausente ni la
profundidad Multiple explicaban el residuo completo.

## Contrato nativo recuperado

La descompilacion AA8 confirma el mismo layout en ambas arquitecturas:

- x64 `x2game.dll`, `FUN_399ad0f0`;
- x86 `x2game.dll`, `FUN_39b83420`.

Los dos consumidores serializan, en este orden:

1. `unitId` mediante BC;
2. `buffId`, que en el wire es el indice runtime de la instancia;
3. `reason`, un byte cuyo valor predeterminado nativo es `0`.

El servidor enviaba solo los dos primeros campos. Era un paquete AA8 truncado:
el cliente podia retirar su estado indexado y aun no completar la semantica de
fin/fade del efecto.

## Reparacion V8

- `SCBuffRemovedPacket` incorpora `reason` con valor predeterminado `0`;
- el wire pasa a `unitId + buffId/index + reason`;
- `Verbose()` registra tambien el motivo;
- `BuffRemovedPacketSerializationTests` fija el layout y comprueba tanto el
  valor nativo predeterminado como un valor explicito no cero;
- se conserva la restauracion Multiple de V7, porque es correcta e
  independiente del defecto de protocolo.

No se asignan significados inventados a otros valores de `reason`; se usa el
default probado por el binario hasta recuperar evidencia de cada motivo.

## Verificacion y despliegue

- prueba focal del paquete: 2/2;
- suite completa con SDK .NET 3.1.409 y runtime Archery V5 montado: 570/570;
- no se modifico la SQLite;
- SQLite montada SHA-256:
  `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`;
- imagen Game:
  `sha256:84002b11a68a6e8cbe61835cf2d5f2bee151c93ec9cf1fedece72f17e1d9eb5e`;
- contenedor Game:
  `8cc3d64b318e4172ac0b5ed79a09ad7d1c0a9889870f7975a60cc49c85c6544e`;
- `Server started!`, registro correcto en Login, puertos 2239/2250 y
  `RestartCount=0`;
- se recreo solo Game; Login y MySQL se conservaron.

## Gate vivo

1. activar Deadeye;
2. moverse hasta acumular varias cargas;
3. quedarse quieto hasta que desaparezca el icono;
4. confirmar que desaparecen icono, bonus y FX rosa/verde sin relogueo;
5. verificar en logs retiros `SCBuffRemoved` con indices distintos y
   `reason=0`, sin excepciones ni reinicios.

Estado: implementada, validada y desplegada; pendiente aceptacion viva.
