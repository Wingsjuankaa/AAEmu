# Checkpoint AA8 nativo — quest 330 v5

Fecha: 2026-07-26
Autoridad: cliente Kakao 8.0.3.12 r558734

## Estado

- modelo completo de Lucius: **validado en juego**;
- interacción inicial AA8 con Lucius: **validada en juego**;
- catálogo nativo de facciones AA8: **reconstruido y desplegado**;
- marcador, oferta y aceptación de la quest 330: **pendientes de prueba manual V5**.

## Hipótesis de múltiples Lucius

La hipótesis queda descartada para este fallo:

- el runtime tiene un solo spawn con `UnitId=3597`;
- la quest enlaza con la plantilla de NPC `3597`, no con el `objId` efímero de
  una aparición concreta;
- la posición del spawn está en Solzreed y coincide con el personaje;
- varias apariciones narrativas de la misma plantilla ofrecerían la misma
  quest si el personaje cumple sus requisitos; no la ocultarían.

## Evidencia de la prueba V4

La interacción ya superó el corte anterior:

```text
C->S CSStartInteractionPacket (Lucius)
S->C SCNpcInteractionSkillListPacket 0x1BD
C->S CSInteractNPCPacket 0x083
C->S CSInteractNPCEnd
```

El cliente nunca envió `CSStartQuestContextPacket`. Por tanto, la quest fue
descartada localmente antes de intentar aceptarla.

## Causa V5

El componente inicial `1520` de la quest 330 contiene:

```text
UnitReq kind=56 value1=148
```

El cliente evalúa ese requisito mediante su administrador de facciones y la
cadena madre:

```text
Wingsjuanka faction 101 -> mother 148 -> 0
```

Durante `InitCharacter`, el cliente reinicia su catálogo dinámico de facciones.
`CSSelectCharacterPacket` enviaba estados de quest, pero mantenía
`FactionManager.SendFactions` deshabilitado. Sin la definición `101 -> 148`,
la evaluación local sólo podía comparar los IDs crudos `101 != 148`, ocultando
el marcador y la oferta sin generar una petición al servidor.

Consumidores nativos confirmados:

- loader `system_factions`: `x2game.dll FUN_399698b0`;
- evaluación de jerarquía: `FUN_3951bd90` / `FUN_399f7ba0`;
- lector del paquete: `x2game.dll FUN_3999a730`.

## Reconstrucción aplicada

Se extrajeron las 114 filas nativas de `game11`:

- rango: `0x605546..0x607AC5`;
- IDs: `1..211`;
- cadena 101 → 148 → 0 cerrada;
- todas las referencias `mother_id` cerradas;
- facciones de integración nativas: `204, 205, 206, 209`.

El runtime V5:

- reemplaza las 94 definiciones heredadas por las 114 definiciones AA8;
- añade `integration_faction`;
- elimina 54 relaciones que dependían del sentinel histórico `901`, ausente
  del cliente AA8;
- conserva las relaciones restantes sólo para lógica interna del servidor;
- **no envía** el catálogo histórico de relaciones al cliente.

El protocolo `SystemFaction` ahora serializa los valores AA8 reales de
`is_diplomacy_tgt` e `integration_faction`, en lugar de `true/false` fijos.
Al seleccionar un personaje se envían las 114 facciones en seis paquetes
`SCSystemFactionListPacket` (`0x101`) antes de que aparezcan los NPC.

## Artefactos

- extractor:
  `extract_native_system_factions.py`;
- datos:
  `generated/native-system-factions-v1-data.json`;
- manifiesto forense:
  `generated/native-system-factions-v1-manifest.json`;
- builder:
  `build_native_quest_330_v5_runtime.py`;
- manifiesto runtime:
  `generated/native-system-factions-v2-runtime-manifest.json`;
- compact:
  `compact-8.0-runtime-native-quest330-v5.sqlite3`;
- SHA-256:
  `F9284947A6162004D6E8B62A8D8A33A05B2E47F25B5F7AF8B1827AF8399E714B`.

## Validación

- extracción determinista: correcta;
- dos builds V5: SHA-256 idéntico;
- `PRAGMA quick_check`: `ok`;
- `PRAGMA integrity_check`: `ok`;
- relaciones huérfanas: `0`;
- pruebas Python: `21/21`;
- pruebas C#: `230/230`;
- `FactionManager`: 114 facciones cargadas;
- ScriptCompiler: 0 errores;
- puertos Game/Stream: `2239/2250`;
- registro en LoginServer: correcto;
- hash montado: coincide con V5;
- errores/fatales de inicio: `0`.

## Prueba manual V5

Es obligatorio volver a la selección de personaje —preferiblemente cerrar y
abrir el cliente— porque el nuevo catálogo se entrega al seleccionar el
personaje.

Con Wingsjuanka:

1. seleccionar el personaje y entrar al mundo;
2. acercarse a Lucius;
3. comprobar si aparece el signo de quest sin interactuar;
4. interactuar y aceptar la quest;
5. confirmar que aparece en el tracker.

En logs se espera:

```text
S->C SCSystemFactionListPacket 0x101 (6 paquetes, 114 filas)
C->S CSStartQuestContextPacket (quest 330)
S->C SCQuestContextStartedPacket
```

No declarar la quest completa hasta validar marcador, aceptación, objetivos,
recompensas, entrega y persistencia tras relog.
