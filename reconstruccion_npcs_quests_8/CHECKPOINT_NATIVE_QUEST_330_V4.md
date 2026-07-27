# Checkpoint AA8 nativo — quest 330 v4

Fecha: 2026-07-26
Autoridad: cliente Kakao 8.0.3.12 r558734

## Estado

- reconstrucción visual de Lucius: **completa y validada en juego**;
- cadena de facción requerida por la quest 330: **validada en game11**;
- protocolo inicial de interacción: **corregido y desplegado**;
- aparición y aceptación de la quest 330: **pendiente de nueva prueba manual**.

## Evidencia reutilizable del modelo

El procedimiento completo quedó documentado en:

`NPC_MODEL_RECONSTRUCTION_PATTERN_V1.md`

La captura aceptada demuestra rostro, cabello, tocado y vestimenta completos.
Lucius queda como caso patrón para reconstruir los demás modelos de NPC.

## Facción nativa, sin supuesto histórico

Se añadió el extractor reproducible:

`extract_native_system_factions.py`

Resultado nativo en `game11`:

- loader: `x2game.dll FUN_399698b0`;
- rango: `0x605546..0x607AC5`;
- filas: `114`;
- cadena de Wingsjuanka: `101 -> 148 -> 0`;
- requisito de `QuestComponent 1520`: facción madre `148`.

El personaje de raza Nuian y facción `101` sí cumple el requisito nativo de la
quest 330. Esta condición ya no es una hipótesis tomada del runtime histórico.

Manifiesto:

`generated/native-system-factions-v1-manifest.json`

## Corte encontrado en la prueba V3

El cliente envió correctamente:

```text
17:12:32 C->S 003 CSStartInteractionPacket, NpcObjId: 34986
17:12:32 C->S 003 CSStartInteractionPacket, NpcObjId: 34986
```

El servidor no respondió. `CSStartInteractionPacket.Read()` sólo leía el
paquete y escribía un log. Por eso el cliente no avanzaba a `CSInteractNPC` ni
abría el contexto de conversación.

## Corrección V4

`CSStartInteractionPacket` ahora:

1. resuelve el NPC por `objId`;
2. determina la acción de servicio cuando corresponde;
3. para un NPC de quest como Lucius usa la acción nativa por defecto `0`;
4. responde con `SCNpcInteractionSkillListPacket`;
5. conserva todos los campos de la solicitud: NPC, objeto, `extraInfo`,
   `pickId`, mouse y modificadores.

El lector AA8 `x2game.dll FUN_3999db50` confirma la estructura central de la
respuesta: IDs compactos, `extraInfo`, `pickId`, mouse, cantidad, skills e
`interactable`.

## Validación automática y despliegue

- pruebas Python de NPC/quests/spawners: `17/17`;
- pruebas C#: `229/229`;
- build Docker: correcto;
- contenedor `aaemu8-game-1`: recreado;
- servidor `8.0.3.12`: iniciado y registrado en LoginServer;
- tiempo de inicio observado: `00:01:07.4420797`.

## Prueba manual siguiente

Entrar con Wingsjuanka, interactuar con Lucius y confirmar en orden:

1. el servidor envía `SCNpcInteractionSkillListPacket` opcode `0x1BD`;
2. el cliente responde con `CSInteractNPC`;
3. se abre la conversación de Lucius;
4. aparece la quest 330;
5. al aceptarla llega `CSStartQuestContextPacket` para quest `330`;
6. el servidor responde `SCQuestContextStartedPacket`.
