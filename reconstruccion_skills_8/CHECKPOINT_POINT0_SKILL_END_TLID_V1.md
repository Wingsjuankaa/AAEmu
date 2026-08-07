# Checkpoint Point 0 — cierre transversal de casteos por `tlId` V1

Fecha: 2026-07-31

## Síntoma

Después de terminar una acción con casteo —abrir una caja, una bolsa o una
infusión— el cliente conservaba durante varios segundos el brillo de la mano
y el sonido de casteo.

El caso observado fue la skill `43013`, usada por la infusión `48507`:

```text
SCSkillStarted tl=1366
SCSkillFired   tl=1366
SCSkillEnded  completed=true
```

La entrega del ítem y su persistencia eran correctas. El defecto quedaba
limitado al ciclo de vida visible de la skill en el cliente.

## Cierre nativo recuperado

El `fx_group_id=1291` de las skills de apertura contiene cuatro entradas:

- partícula `item_unpacking`, evento inicial `0`, evento final `5`;
- partícula `item_unpacking_launch`, evento inicial `3`, evento final `5`;
- sonido `unpack_form`, evento inicial `0`, evento final `5`;
- sonido `unpack_launch`, evento inicial `3`, evento final `5`.

La ruta entrante de Kakao 8.0.3.12 r558734 es:

```text
opcode 0x345
→ registro FUN_393676c0
→ handler FUN_392f96c0
→ FUN_396197c0(tlId)
→ búsqueda y eliminación de la transacción
→ cierre de animación y FX asociados
```

`FUN_396197c0` usa el valor recibido como llave de la transacción activa. El
servidor había sido cambiado para enviar un booleano, por lo que una acción
con `tlId=1366` transmitía solamente `01` y el cliente intentaba cerrar la
transacción `1`.

La causa fue confundir `FUN_399952d0`, lector booleano de la dirección
contraria del protocolo, con el payload `SC` que llega al handler anterior.

## Reparación

- `SCSkillEndedPacket` vuelve a serializar `UInt16 tlId`.
- Todas las rutas de cierre normales, cancelaciones, autoataque y operaciones
  de equipo vuelven a entregar el identificador real.
- Las rutas especiales de rechazo conservan el `skill.TlId`; no fabrican ids
  ni temporizadores.
- No se modificaron las duraciones, animaciones ni el grupo FX nativos.

## Validación estática

- serialización de `0x0556`: `56 05`;
- prueba de no colapso `0xFF01`: `01 FF`;
- suite `AAEmu.Tests` en .NET Core 3.1: `311/311`.

## Prueba manual validada

Validación realizada por el usuario con Dannia el 2026-07-31. Al abrir el ítem
`47983`, el servidor registró:

```text
SCSkillStarted skill=42227 tl=1451 item=47983
SCSkillFired   skill=42227 tl=1451
SCItemTaskSuccess Loot x4
SCItemTaskSuccess SkillReagents x1
SCSkillEnded   tl=1451
```

Se confirmó que:

1. el resultado se entrega una sola vez;
2. el brillo y el sonido terminan junto con la transición de lanzamiento;
3. no queda una transacción visual residual;
4. el resultado persiste tras desconexión limpia.

Estado del stack: **satisfactorio y cerrado**.

## Despliegue de validación

- imagen `game`: `sha256:e30c05b1f829ac2a5822914b745eec94de455342dc542767d3407b2faffcd4bd`;
- respaldo anterior: `aaemu-game:pre-point0-skill-end-tlid-v1-20260731`;
- `compact.sqlite3`: `84a2e6af2b890a3fe066129f80f041dde2ff6b071b151ad0d05e2fb509073e0f`;
- `db` y `login`: sin recrear;
- arranque: `Server started` en `00:01:50`, puertos `2239/2250` y registro
  satisfactorio en LoginServer;
- reinicios del contenedor: `0`.
