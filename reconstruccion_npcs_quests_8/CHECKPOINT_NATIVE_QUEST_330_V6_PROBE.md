# Checkpoint AA8 nativo — quest 330 V6 probe

Fecha: 2026-07-26
Autoridad de datos/protocolo: cliente Kakao 8.0.3.12 r558734
Referencia arquitectónica secundaria: rama `develop`

## Resultado de la prueba V5

La prueba manual confirmó que el marcador siguió ausente.

Los logs prueban que V5 sí se ejecutó como estaba diseñado:

```text
S->C SCQuestsPacket 0x1B4
S->C SCCompletedQuestsPacket 0x081
S->C SCSystemFactionListPacket 0x101 (6 paquetes)
```

Por tanto, la falta de sincronización de facciones queda refutada como causa
principal. Se conserva la reconstrucción de facciones porque corrige un hueco
real de inicialización AA8, pero ya no se presenta como solución del marcador.

Persistencia de Wingsjuanka comprobada directamente:

- nivel: `1`;
- raza: `1`;
- facción: `101`;
- zone key: `179`;
- quest 330 activa: no;
- bloque de completadas `330 / 64 = 5`: ausente;
- la quest 330 no está marcada accidentalmente como completada.

## Patrón reutilizado desde develop

`develop` no se usó como autoridad de datos ni de protocolo. Sólo se reutilizó
su separación transversal entre:

1. inspeccionar requisitos;
2. intentar el inicio normal;
3. forzar el inicio como herramienta GM;
4. resincronizar el estado de quests.

## Instrumentación añadida

`QuestManager` carga las filas crudas de `unit_reqs` asociadas a
`QuestComponent` sólo para observación. No habilita evaluadores históricos.

El comando `/quest` incorpora:

```text
/quest diagnose <questId>
/quest try <questId>
/quest force <questId>
/quest sync
```

Para la quest 330, `diagnose` informa:

- existencia de template;
- estado activo/completado;
- nivel, raza, zone key y cadena de facción;
- NPC seleccionado: `objId` y template;
- componentes y pasos;
- requisitos crudos;
- evaluación AA8 confirmada de `kind=56` mediante jerarquía de facción;
- actos y enlace `QuestActConAcceptNpc`;
- comparación entre NPC esperado y NPC seleccionado.

Todos los resultados también se escriben en el log con prefijo:

```text
[QuestProbe]
```

`try` usa el flujo normal del servidor y exige que Lucius sea el objetivo.
`force` usa el bypass GM, envía el paquete de inicio y después resincroniza los
snapshots activo/completado.

## Interpretación de la prueba

| Resultado | Conclusión |
|---|---|
| `try` deja la quest activa y aparece | ejecución funciona; el fallo está en la oferta/marcador del cliente |
| `try` falla pero `force` aparece | el inicio normal del servidor falla antes de crear la quest |
| `force` queda activa en servidor pero no aparece | fallo en snapshot/paquete de quest activa o su layout AA8 |
| `force` tampoco queda activa | fallo interno al construir/ejecutar la quest 330 |
| `force` aparece pero no progresa | cierre incompleto de objetivos/acts |

## Validación

- pruebas forenses Python: `21/21`;
- pruebas C#: `232/232`;
- requisitos crudos cargados para `3633` componentes;
- ScriptCompiler: `0` errores;
- servidor y Stream escuchando en `2239/2250`;
- registro en LoginServer: correcto;
- compact V5 montado con hash esperado;
- errores/fatales de inicio: `0`.

## Secuencia manual

Seleccionar a Lucius y ejecutar, en orden:

```text
/quest diagnose 330
/quest try 330
/quest list
```

Si `try` no deja la quest activa:

```text
/quest force 330
/quest list
```

Si el servidor dice `ACTIVE` pero la interfaz no cambia:

```text
/quest sync
```

No usar `/quest reward 330` todavía. La prueba busca aislar el inicio sin
alterar recompensas ni marcar la quest como completada.
