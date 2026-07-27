# Checkpoint AA8 nativo — quest 330 V7 ready transition

Fecha: 2026-07-26
Autoridad de datos/protocolo: cliente Kakao 8.0.3.12 r558734
Referencia arquitectónica secundaria: rama `develop`

## Resultado de la prueba V6

La prueba manual con:

```text
/quest force 330
```

demostró que:

- el servidor creó y persistió la quest 330;
- `SCQuestContextStartedPacket` fue aceptado por el cliente;
- `SCQuestsPacket` y `SCCompletedQuestsPacket` se pudieron decodificar;
- el cliente mostró `Exciting News` en el tracker;
- la misión quedó inmediatamente completada en el tracker, como corresponde a
  una misión cuyo único objetivo es reportarse con otro NPC;
- no apareció el símbolo de entrega sobre Gossiper Parish.

Estado observado por `QuestProbe`:

```text
result=ACTIVE quest=330 step=Progress status=Ready component=1520
```

La quest no fue entregada ni añadida al bloque de completadas.

## Cierre nativo de componentes

La quest 330 contiene:

```text
1520 Start  -> QuestActConAcceptNpc  npc=3597  (Lucius)
1521 Ready  -> QuestActConReportNpc  npc=11541 (Gossiper Parish)
1522 Reward -> recompensas
```

No existe componente `Progress`.

El motor heredado calculaba correctamente `Status=Ready`, pero al terminar el
bucle de inicio dejaba:

```text
Step=Progress
ComponentId=1520
```

y sólo enviaba el paquete de inicio. Por tanto, el cliente recibía una misión
lista para entregar que seguía asociada al componente inicial de Lucius y no
recibía la actualización de transición.

## Pareo selectivo con `develop`

`develop` se usó sólo como referencia arquitectónica. Su ciclo transversal:

1. envía el contexto inicial;
2. ejecuta el componente `Start`;
3. avanza por los pasos ausentes;
4. entra en `Ready`;
5. limpia el componente activo del paquete;
6. envía `SCQuestContextUpdatedPacket`.

No se importaron datos, requisitos, opcodes ni layouts de `develop`.

## Corrección V7

Se añadió una normalización genérica y estrecha:

```text
Status == Ready
AND Step == Progress
AND no existe componente Progress
AND existe componente Ready
```

Resultado:

```text
Step=Ready
ComponentId=0
SCQuestContextUpdatedPacket
```

Se aplica:

- después del inicio normal;
- después del inicio forzado GM;
- al cargar una quest antigua persistida con el estado inconsistente.

Las misiones que sí tienen objetivos `Progress` no se reescriben.

## Etiquetas globales de NPC

El vector que `SCInitialConfigPacket` transmite actualmente tiene habilitado:

```text
questNpcTag = bit 94 = 1
```

Por tanto, no se cambió el `FeatureSet` ni se copió el gestor histórico de
`develop`. La ausencia del símbolo inicial sobre Lucius sigue siendo un
problema independiente de oferta/etiqueta y no se considera resuelta por V7.

## Validación

- `git diff --check`: correcto;
- pruebas C#: `234/234`;
- ScriptCompiler: `0 errors`;
- servicio recreado: sólo `game`;
- servidor Game/Stream: `2239/2250`;
- registro en LoginServer: correcto;
- compact montado:
  `compact-8.0-runtime-native-quest330-v5.sqlite3`;
- SHA-256:
  `F9284947A6162004D6E8B62A8D8A33A05B2E47F25B5F7AF8B1827AF8399E714B`;
- errores recientes de inicio: `0`.

## Prueba manual V7

La quest 330 ya permanece activa. No volver a forzarla y no entregarla todavía.

1. volver a entrar con Wingsjuanka;
2. acercarse a Gossiper Parish;
3. comprobar si aparece el símbolo de entrega;
4. comprobar que el tracker conserva `[Complete] Exciting News`;
5. no confirmar la entrega.

Al cargar el personaje se espera:

```text
[Quest] Normalized immediate-ready quest 330 ... Step=Ready, ComponentId=0
```

Interpretación:

- si aparece el símbolo de Parish, el ciclo activo/entrega queda aislado y
  corregido; se continúa separadamente con la oferta de Lucius;
- si no aparece, el siguiente corte es el consumidor nativo de etiquetas de
  NPC y sus entradas de disponibilidad, no volver a tocar requisitos ni
  componentes de la quest 330.
