# AA10 r575 — refresco inmediato de rango de proficiency

## Síntoma reproducido

Al confirmar una promoción de proficiency en el máximo del rango, el servidor aplicaba el nuevo
`step`, pero el cliente seguía mostrando el rango anterior. Después de reloguear, el rango nuevo
sí aparecía mediante `SCActabilityPacket`.

La reproducción de Alchemy registró la petición `CSUpgradeExpertLimitPacket` (`0x151`) y la
respuesta `SCExpertLimitModifiedPacket` (`0x22E`), descartando un fallo de despacho o de mutación
del estado del servidor.

## Evidencia nativa

Autoridad: `x2game.dll` retail ArcheAge Returns 10.0.2.13 r575, SHA-256
`2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76`.

- `FUN_393e3720` registra `SCExpertLimitModifiedPacket` en el opcode `0x22E`.
- `FUN_39ab52a0` lee primero `isUpgrade` y luego llama al codec de estado de actability
  `FUN_39a3ddb0`.
- Ese codec serializa `id` y `point` como un par PISC/PISH, seguido por `step` (`u8`).
- `FUN_3933b430` pasa el registro completo a `FUN_395ecc10`, que actualiza el estado y publica el
  evento de interfaz.

El contrato AA10 es:

```text
isUpgrade(bool) | WritePisc(id, point) | step(u8)
```

AAEmu heredaba el cuerpo antiguo `bool + id(u32) + step(u8)`: faltaba `point` y `id` tampoco
utilizaba la compresión nativa. El cliente no podía completar la lectura y descartaba el paquete.

## Implementación

- `SCExpertLimitModifiedPacket` recibe el estado completo y escribe `WritePisc(id, point)` antes
  de `step`.
- `CharacterActability.Regrade` envía los valores ya mutados de `Id`, `Point` y `Step`.
- No se agregó un resync artificial: el paquete nativo de resultado es suficiente cuando su cuerpo
  es correcto.

## Regresión

`SCExpertLimitModifiedPacketTests` cubre:

- bytes exactos para `upgrade=true`, Alchemy `id=1`, `point=20.000`, `step=2`;
- round-trip y orden de `isUpgrade`, `id`, `point`, `step`, incluyendo valores PISC de longitudes
  distintas y ausencia de bytes sobrantes.
