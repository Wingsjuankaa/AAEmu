# Checkpoint — AA8 Mechanics Lab V1

Fecha: 2026-08-08

## Estado

Implementado un runner headless sobre `rama_8` con reloj, scheduler, mundo, transporte, RNG y compact deterministas. La ejecución usa `Skill.Use`, plots, efectos, buffs, muerte y serializadores productivos reales.

## Primer hallazgo confirmado

El contador DD05 no falla por el wrap `255 → 0`. El escenario secuencial cruzó el límite correctamente. La variante concurrente sí reprodujo una inversión entre asignación y escritura:

```text
counter reservado: 252,253
counter enviado:    253,252
```

La frontera causante era `GameConnection.SendPacket(GamePacket)`: `Encode` asignaba el contador y el socket se escribía fuera de una exclusión mutua. `rama_8_modern` contiene el mismo patrón de cierre atómico. Se portó selectivamente el lock que cubre `Encode → capture → transport`, sin alterar opcodes, layouts ni cifrado AA8.

## Oráculos del fixture letal

- daño antes de muerte;
- una sola muerte lógica;
- remoción única de buffs `2214`, `20933`, `21987`;
- ninguna creación de buff después de la muerte;
- HP final cero;
- una adjudicación lógica de EXP;
- timeline completo de inicio, eventos y cierre de plot;
- limpieza única de aggro y target;
- cero referencias finales desde o hacia la unidad muerta;
- contador DD05 monotónico módulo 256 en orden real de transporte;
- plaintext y wire equivalentes;
- cuerpo exacto para paquetes conocidos;
- cero tareas pendientes, mutaciones post-muerte o excepciones tras 15 segundos virtuales.

El oráculo de referencias hizo visible una segunda malformación: efectos posteriores al nodo letal recreaban aggro en el cadáver. Se cerró en la frontera mínima (`Npc.OnDamageReceived` no admite HP cero y `Npc.DoDie` elimina su target) y el escenario permanente demuestra que el estado no reaparece durante los 15 segundos posteriores.

La captura productiva del NPC `2308` y el A/B binario posterior identificaron
la regresión en la propia muerte diferida. La imagen Docker estable de las
20:19 no contiene `deferDeath`, `FinalizeDeferredDeath` ni acciones
post-envío; la imagen de las 20:38 ya los contiene. La traza defectuosa
publicaba `SCUnitDamaged → SCUnitPoints(0) → SCUnitDeath` y el cliente dejaba
de emitir C2S al comenzar esa clausura. Se restauró el flujo sincrónico del
ejecutable estable: clausura de `DoDie`, `SCUnitPoints(0)` y después el
`SCUnitDamaged` que permanecía en su lote DD04. El Lab valida ese contrato con
`stable_lethal_closure_order` sin retirar las verificaciones de layout,
contadores, buffs, aggro ni referencias post-muerte.

## Resultados reproducibles

Compact: `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`

```text
counter wrap     ACF8D6080DE36B688B75EACD285C968EE954FD59108F987A0D2CAA7D9F9A5474
concurrent wrap  1952536FEC807C93BDBDEE658C082C81F4382B955F3520E7C7D9142F266502AA
npc 2308 closure  422202CEE020F4A3B85755D39AB94A2BACFF1546271BEB5721C2D038EE4DE9EE
```

La variante concurrente fue repetida en procesos separados y produjo el mismo hash.

## Archivos principales

- `AAEmu.Game/Models/Mechanics/MechanicsRuntime.cs`
- `AAEmu.MechanicsLab/MechanicsLab.cs`
- `AAEmu.MechanicsLab/MechanicsArena.cs`
- `AAEmu.MechanicsLab/ManualMechanicsClock.cs`
- `AAEmu.MechanicsLab/ManualMechanicsScheduler.cs`
- `AAEmu.MechanicsLab/MechanicsLedger.cs`
- `AAEmu.MechanicsLab.Cli/Program.cs`
- `mechanics-lab/scenarios/archery_blazing_arrow_lethal_*.json`
- `Tools/Invoke-AA8MechanicsLab.ps1`

## Evidencia y límites

El compact AA8 sigue siendo la autoridad. Modern justificó sólo el patrón de lock después de que el Lab reprodujera la carrera. El Lab no usa MySQL, no persiste actores, no inicia LoginServer y no automatiza la GUI.

## Validación y despliegue de la reversión sincrónica

- suite completa .NET Core 3.1 en Docker: `593/593` pruebas aprobadas;
- tres escenarios letales permanentes aprobados: wrap normal, wrap concurrente y NPC `2308`;
- compact desplegado y verificado: `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`;
- imagen `game` desplegada: `sha256:260648813fb1ca28562e2c4935be5cd5389466eef5e40f48ea58b76b436dd8c1`;
- rollback preservado como `aaemu-game:rollback-pre-sync-death-20260808`;
- `game` escucha en `2239/2250`, carga scripts con cero errores y queda registrado en LoginServer.

Queda pendiente únicamente la aceptación visual con cliente real: matar un NPC normal, permanecer conectado 15 segundos, moverse y ejecutar una habilidad. Hasta completar esa comprobación, el resultado se considera aprobado headless y desplegado, no cerrado en vivo.

## Segunda causa aislada: cuerpo wire de muerte

La aceptación anterior siguió cerrando el cliente. La captura exacta mostró
una sola muerte lógica, DD05 monotónico y un `Ping` posterior, seguido por
`peer_closed`. El diff de los ensamblados Docker funcional `4d829910...` y
actual `260648813...` aisló una diferencia de siete bytes en
`SCUnitDeathPacket`: se había tratado el bloque interno inicializado por
`FUN_39AB5D30` como si fuera el serializer de red.

Se restauró el cuerpo wire de la imagen funcional: dos tiempos `uint32`,
`lostExp i32`, durabilidad `u8`, killer BC y, si existe killer, cola con
`type u8`. Se conservaron el killer y reason reales. Las ramas con y sin killer
quedaron fijadas por pruebas de longitud y serialización exacta. Requiere una
nueva aceptación viva antes de cerrar la incidencia.

### Validación y despliegue del cuerpo wire estable

- suite completa .NET Core 3.1 en Docker: `593/593` pruebas aprobadas;
- Mechanics Lab: `19/19`, `19/19` y `16/16` validaciones aprobadas para
  wrap, concurrencia y NPC `2308`;
- compact desplegado y verificado dentro del contenedor:
  `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`;
- imagen `game` desplegada:
  `sha256:aea8c4a7e86662ed41e3b099a2e1e223eb8d0394c873b291ce0f4ac578a6bef2`;
- imagen anterior preservada como
  `aaemu-game:rollback-pre-aa8-death-wire-stable-20260808`
  (`sha256:260648813fb1ca28562e2c4935be5cd5389466eef5e40f48ea58b76b436dd8c1`);
- `game` escucha en `2239/2250`, compiló scripts con cero errores y quedó
  registrado correctamente en LoginServer.

La comprobación pendiente sigue siendo deliberadamente viva: matar el mismo
NPC normal, esperar 15 segundos y luego moverse y ejecutar una habilidad.

## Tercera causa aislada: clausura de combate incompleta

El cierre del cliente persistió aun con muerte sincrónica y wire compacto. Un
A/B nuevo contra la imagen funcional `4d829910...` aisló la diferencia en la
transacción posterior a `SCUnitDeath`: la imagen funcional vaciaba aggro con
owner igual al killer y enviaba dos `SCCombatCleared`; la variante rota usaba
como owner al NPC muerto y había eliminado ambos cierres.

Las diez capturas fallidas disponibles contienen exactamente la variante rota.
La secuencia funcional fue restaurada y añadida como requisito permanente de
los tres fixtures letales. Resultados actuales:

```text
counter 10        9F04996C1D16885EFD1EC75489111F119AA350931B490BACF089EE20E51308E9
counter wrap      7055080BCE88F87CE483FE1730EFB7B07EC87CFF99F72746D5C1D639FB2FFB26
concurrent wrap   FD4DB3AC64BD3652F8F00721A4E73D2E40FF72BEFF1B783F89DAF8982ECB1296
repeat concurrent FD4DB3AC64BD3652F8F00721A4E73D2E40FF72BEFF1B783F89DAF8982ECB1296
```

La suite completa, con el compact Sorcery V10 montado explícitamente dentro
del contenedor Linux, pasa `594/594`. El dossier causal y la matriz de las diez
capturas están en `CHECKPOINT_AA8_NPC_DEATH_CLOSURE_V1.md`.

La imagen desplegada para aceptación viva es
`sha256:7c159714a3e0761683d29b2b146cce5e1a8725429bb96a97428f91fe792a48de`.
La imagen previa quedó preservada como
`aaemu-game:rollback-pre-aa8-lethal-closure-v16-20260808`. El servidor inició
con cero errores, registró `game` en LoginServer y mantiene la captura de
paquetes habilitada.

## V1.17 - oráculo de canal para clear de aggro letal

La regresión viva posterior a V1.16 demostró que igualdad de cuerpo no implica
igualdad de contrato: `SCUnitAiAggro(count=0)` debe conservar el canal ordenado
DD05/nivel 5 cuando forma parte de la clausura letal, mientras los updates
ordinarios de aggro usan nivel 1. El Lab ahora ejecuta esa distinción a través
de `CreateCombatClear` y la fija en `UnitAiAggroPacketTests`.

Los escenarios normal, wrap, concurrente y NPC `2308` pasan respectivamente
`19/19`, `19/19`, `19/19` y `16/16`; la suite completa pasa `595/595`. Este
hallazgo obliga a incluir nivel/canal y orden de envío en todo oráculo de
paquetes, incluso cuando opcode y bytes del cuerpo sean idénticos.

La aceptación posterior con el cliente AA8 real pasó sin desconexión al morir
el NPC. El escenario queda promovido a regresión permanente del Mechanics Lab.
