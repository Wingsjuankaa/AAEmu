# Checkpoint AA8 nativo — quest 330 v3

Fecha: 2026-07-26
Autoridad: cliente Kakao 8.0.3.12 r558734

## Resultado desplegado

La V3 corrige los dos fallos observados durante la prueba manual de Lucius:

- el rostro ya no se selecciona por la última fila de `item_body_parts`;
- el estado de misiones completadas ya no se serializa con un índice de 16 bits.

El runtime activo es:

`D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-quest330-v3.sqlite3`

SHA-256:

`35F485CC40A738B279724ECE26C92D0782ED3C9A598ABD07E91E3976B12E0E4A`

## Rostro de Lucius

El modelo humano masculino `10` declara en `characters.face_item_id` la cara
nativa `19838`. La V2 escogía la última cara compatible, `48541`
(`nu_m_mannequin_face`), que explica el rostro blanco de la captura.

La V3:

- incorpora la definición completa del item `19838`;
- conserva su `item_body_parts.asset_id = 10078`;
- hace que `NpcManager` prefiera el `face_item_id` declarado por el modelo.

## Condición nativa de publicación

La secuencia completa `unit_reqs` se extrajo del `game11` nativo:

- rango: `0x7CA0C9..0x87EC3C`;
- filas: `27407`;
- loader: `x2game.dll FUN_3997a330`.

Para el componente de aceptación `1520`, AA8 declara exactamente:

`QuestComponent 1520 -> kind 56 -> value1 148`

La función cliente compara la facción madre requerida con la del personaje.
Wingsjuanka usa facción `101`, cuya madre es `148`, por lo que cumple la
condición. La fila histórica `kind 36 -> 6198` del runtime anterior no
correspondía a AA8 y fue reemplazada.

## Estado de misiones por protocolo

El cliente AA8 lee cada entrada de `SCCompletedQuests` como:

- `count`: `int32`;
- `idx`: `uint32`;
- `body`: máscara de `uint64`.

El servidor escribía `idx` como `ushort`, desplazando el cuerpo y las entradas
siguientes cuando el personaje tenía misiones completadas. Ahora escribe
`uint32`.

También se confirmó que `SCQuests` usa diez contadores de objetivo por misión
activa; `Quest.ObjectiveCount` pasó de `5` a `10`.

## Validación

- extracción Python reproducible: 8/8;
- pruebas C#: 229/229;
- `PRAGMA quick_check`: `ok`;
- `PRAGMA integrity_check`: `ok`;
- contenedor `aaemu8-game-1` reconstruido y operativo;
- hash del compacto montado en `/app/Data/compact.sqlite3` coincide con V3.

## Resultado de la prueba manual

La reconstrucción visual de Lucius quedó **aceptada** en juego:

- rostro humano completo;
- cabello y tocado correctos;
- vestimenta completa;
- sin el placeholder blanco.

La evidencia y el procedimiento reutilizable quedaron preservados en
`NPC_MODEL_RECONSTRUCTION_PATTERN_V1.md`.

La misión `330` todavía no aparece. El log de la misma sesión demuestra que el
cliente sí reconoció a Lucius como interactuable:

```text
17:12:32 C->S 003 CSStartInteractionPacket, NpcObjId: 34986
17:12:32 C->S 003 CSStartInteractionPacket, NpcObjId: 34986
```

El servidor no envió después `SCNpcInteractionSkillListPacket`. El manejador
`CSStartInteractionPacket` sólo registraba el evento y terminaba sin responder.
Por tanto, el siguiente corte confirmado está en el protocolo de interacción,
antes de `CSInteractNPC` y antes de que el cliente abra la conversación de
misiones.
