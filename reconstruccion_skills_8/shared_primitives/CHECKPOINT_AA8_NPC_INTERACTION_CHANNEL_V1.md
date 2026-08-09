# Checkpoint AA8: canal de interacción con NPC V1

Fecha: 2026-08-09
Cliente: ArcheAge Kakao 8.0.3.12 r558734
Rama activa: `client_version/8.0.3.12-kakao-r558734-port`

## Resultado

La desconexión aparentemente periódica durante las pruebas de Battlerage se
redujo a la respuesta enviada después de hablar con la Temple Priestess
(`template_id=502`). El servidor permanecía sano, seguía intercambiando
`Ping/Pong` y finalmente registraba `peer_closed`: era el cliente quien cerraba
los sockets Game y Stream.

El handler había regresado a enviar el vaciado de aggro de la interacción como
un paquete inmediato de nivel 1. La implementación AA8 r558734 original, en el
commit `3e55d80f`, sitúa esta respuesta en el stream ordenado DD05, nivel 5.

La corrección separa tres contratos que comparten el mismo cuerpo wire:

- actualizaciones ordinarias de aggro de combate: nivel 1;
- cierre letal previamente validado: fábrica específica de nivel 5;
- acuse de interacción con NPC: fábrica específica de nivel 5.

No se cambió opcode, cuerpo, anchura ni orden de campos.

## Evidencia viva

La búsqueda sobre todas las capturas disponibles encontró sólo dos
`CSInteractNPC` (`0x083`). Ambas apuntan a Temple Priestess y ambas preceden al
cierre de los sockets por parte del cliente.

| Captura | ObjId | Template | Respuesta anterior | Tiempo hasta cierre |
|---|---:|---:|---|---:|
| `aa8-game-20260809-070623726-session-97557940.jsonl` | 62621 | 502 | `SCUnitAiAggro(count=0)`, nivel 1 | 5169 ms |
| `aa8-game-20260809-151944642-session-3390528841.jsonl` | 57423 | 502 | `SCUnitAiAggro(count=0)`, nivel 1 | 38972 ms |

Correlación observada: `2/2`. En la segunda sesión la interacción ocurrió a las
15:21:02 y el cliente cerró ambos sockets a las 15:21:41. Durante ese intervalo
el servidor siguió respondiendo y no hubo excepción, OOM ni reinicio.

## Contrato wire preservado

Stage 15 confirma el cuerpo de `SCUnitAiAggroPacket`:

```text
owner: BC
count: int32
entries[count]: int32 + int32 + int32 + topFlags
```

Para el acuse vacío de interacción sólo se serializan el `owner` del NPC y
`count=0`. La reparación cambia únicamente el nivel de transporte de 1 a 5,
recuperando el DD05 ordenado del port AA8 original.

## Implementación

- `AAEmu.Game/Core/Packets/C2G/CSInteractNPCPacket.cs`: usa la fábrica del
  contrato de interacción.
- `AAEmu.Game/Core/Packets/G2C/SCUnitAiAggroPacket.cs`: añade
  `CreateInteractionClear` sin alterar `CreateClear` de combate.
- `AAEmu.Tests/UnitAiAggroPacketTests.cs`: comprueba nivel 5 y cuerpo idéntico
  al vaciado conocido.

No se portó el handler Modern completo ni se modificó el estado persistente de
interacción: el cambio se limita a la frontera causal demostrada.

## Verificación

- Pruebas focales `UnitAiAggroPacketTests`: `7/7 PASS`.
- Suite .NET Core 3.1 con la compact Battlerage V2 activa: `601/601 PASS`.
- Scripts del servidor: `0 errors`, 8 warnings heredados.
- Compact montada SHA-256:
  `54DD8C77556A35C3EECE4009A6FC713179F72054DD4E50A6DBA08B74533ABF3A`.

## Despliegue

- Imagen de rollback:
  `aaemu-game:rollback-pre-aa8-npc-interaction-channel-v1-20260809`.
- SHA de rollback:
  `sha256:a924aa6d623c5e4837b6821e9b34dc2c0ca528b54163463f291610f022f4d8db`.
- Imagen candidata `aaemu-game:0.0.2.0-alpha`:
  `sha256:9e4e5bdd4a858cce8807f324a04c7979e06ea27eeb1001401c70441a1a389e2f`.
- DLL candidata SHA-256:
  `5EC6873E9CF2B25E8BD676ECA6B790F83A0E2378598B1FD89DF599B5BDEB231D`.
- Sólo se recreó `aaemu8-game-1`; LoginServer y MySQL no fueron recreados.
- Puertos `2239/2250` accesibles y GameServer registrado en LoginServer.

## Aceptación viva

1. Entrar al mundo y hablar con Temple Priestess.
2. Mantener abierta `Change Skillset` durante al menos 60 segundos.
3. Cerrar y volver a abrir la ventana o efectuar un cambio de especialización.
4. Confirmar que el cliente sigue conectado y puede moverse/usar una skill.

Resultado: `PASS` confirmado por el usuario el 2026-08-09. La interacción con
Temple Priestess dejó de desconectar el cliente después de restaurar el
`SCUnitAiAggro(count=0)` posterior a `CSInteractNPC` en nivel 5/DD05.

Este bloqueo previo queda cerrado. La aceptación funcional del árbol
Battlerage continúa separada y depende de su barrido completo de skills.
