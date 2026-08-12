# Checkpoint AA8: clausura letal de NPC V1

Fecha: 2026-08-08  
Cliente: ArcheAge Kakao 8.0.3.12 r558734  
Rama activa: `client_version/8.0.3.12-kakao-r558734-port`

## Resultado

La desconexión al matar un NPC se aisló en una regresión de la transacción que
cierra el combate, no en el wrap DD05 ni en el cuerpo wire de
`SCUnitDeathPacket`.

El contrato aceptado por el cliente AA8 y observado en la última imagen Docker
funcional de 2026-08-07 20:19 es:

```text
SCUnitDeath(victim, killer)
SCUnitAiAggro(owner=killer, count=0)       [level 1]
SCCombatCleared(victim)
SCCombatCleared(killer)
SCTargetChanged(killer, 0)
SCUnitPoints(victim, HP=0, MP=0)
SCUnitDamaged(...)
SCPlotEnded(...)
```

La regresión había cambiado el propietario del vaciado de aggro al NPC muerto
y eliminado ambos `SCCombatCleared`. Ese cambio parecía plausible por el nombre
genérico `npcId` del paquete, pero contradice el A/B vivo de esta revisión.

## Evidencia de regresión

Se compararon los ensamblados extraídos de:

- imagen funcional: `sha256:4d829910b9b7...` (20:19);
- imagen posterior con el fallo: ensamblado en
  `runtime-captures/image-diff/current-src`.

El diff de `Unit.DoDie` aisló exactamente estas diferencias:

- funcional: `SCUnitAiAggro(killer.ObjId, 0)`;
- roto: `SCUnitAiAggro(victim.ObjId, 0)`;
- funcional: dos `SCCombatCleared`, para victim y killer;
- roto: ninguno.

Las diez capturas fallidas disponibles repiten la misma firma:

| Captura | Victim | Owner aggro vacío | CombatCleared | Cierre posterior |
|---|---:|---:|---:|---:|
| 015210 | 59509 | 59509 | 0 | 1684 ms |
| 020250 | 57282 | 57282 | 0 | 1891 ms |
| 022320 | 60415 | 60415 | 0 | 7628 ms |
| 025832 | 54805 | 54805 | 0 | 3579 ms |
| 045208 | 55141 | 55141 | 0 | 3174 ms |
| 135557 | 61849 | 61849 | 0 | 4269 ms |
| 150153 | 58901 | 58901 | 0 | 3809 ms |
| 153500 | 61699 | 61699 | 0 | 2347 ms |
| 160319 | 58889 | 58889 | 0 | 2180 ms |
| 223744 | 55076 | 55076 | 0 | 1510 ms |

La correlación es 10/10: aggro vacío atribuido a la víctima, ningún cierre de
combate y desconexión posterior.

## Límite de la evidencia nativa

Stage 15 confirma que `SCUnitAiAggro` contiene un identificador llamado
`npcId`, un conteo y sus entradas. Eso documenta el layout del paquete, pero no
demuestra por sí solo que el owner de una notificación vacía dentro de esta
transacción de muerte deba ser la víctima.

El corpus nativo también expone estructuras internas de muerte más anchas que
el cuerpo wire observado. La imagen funcional usa el cuerpo compacto y por eso
no se promovieron campos internos ni se modificó `SCUnitDeathPacket`.

Regla resultante: para esta frontera manda la transacción viva AA8 completa;
los nombres reflectivos no autorizan a cambiar su semántica.

## Implementación

La reparación está en:

- `AAEmu.Game/Models/Game/Units/Unit.cs`;
- `AAEmu.Tests/UnitDeathPacketSerializationTests.cs`;
- `AAEmu.Tests/UnitAiAggroPacketTests.cs`;
- los tres escenarios `mechanics-lab/scenarios/archery_blazing_arrow_lethal_*`.

La prueba `Aa8LethalCombatClosureMatchesLastKnownGoodTransaction` fija el owner,
los dos cierres y el orden. `EmptyAggroTableSerializesOnlyOwnerAndZeroCount`
sólo fija el layout de un aggro vacío; deliberadamente no infiere quién debe ser
el owner en una mecánica concreta.

## Validación automatizada

Compact Archery activo:

```text
SHA-256 4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2
```

Resultados headless posteriores a la reparación:

```text
counter 10:        9F04996C1D16885EFD1EC75489111F119AA350931B490BACF089EE20E51308E9
wrap 255 -> 0:     7055080BCE88F87CE483FE1730EFB7B07EC87CFF99F72746D5C1D639FB2FFB26
concurrent wrap:   FD4DB3AC64BD3652F8F00721A4E73D2E40FF72BEFF1B783F89DAF8982ECB1296
repeat concurrent: FD4DB3AC64BD3652F8F00721A4E73D2E40FF72BEFF1B783F89DAF8982ECB1296
```

Los tres escenarios pasan, no dejan tareas que muten al NPC muerto durante los
15 segundos posteriores, no crean buffs no aplicables después de la muerte y
consumen exactamente los cuerpos conocidos. El caso concurrente es byte a byte
determinista en dos procesos independientes.

Suite completa con el compact Sorcery V10 montado explícitamente en Linux:

```text
Total: 594
Passed: 594
Failed: 0
```

## Build y despliegue

Se reconstruyó y recreó únicamente el servicio `game`:

```text
imagen activa  sha256:7c159714a3e0761683d29b2b146cce5e1a8725429bb96a97428f91fe792a48de
AAEmu.Game.dll f307345ec0c30acd792ccef486a279629db14673ed06202a8afe30a4667a554f
rollback       sha256:94ce2da2a7d337efa3387ce4ddbd5b616c575a18d9ecaf7c2dfae44cb013cdd4
```

El rollback está etiquetado como
`aaemu-game:rollback-pre-aa8-lethal-closure-v16-20260808`.

Verificación del runtime:

- compact dentro del contenedor: `4AA3CD82...29F7E2`;
- scripts: cero errores;
- errores fatales/de arranque: cero;
- puertos `2237`, `2239` y `2250`: accesibles;
- GameServer registrado en LoginServer;
- captura completa habilitada en `runtime-captures/packet-traces`.

## Aceptación viva pendiente

El runtime queda preparado para una única comprobación del cliente:

1. matar un NPC normal;
2. permanecer conectado 15 segundos;
3. moverse;
4. usar otra habilidad.

La captura debe mostrar el owner del `SCUnitAiAggro` igual al personaje y dos
`SCCombatCleared` entre muerte y cambio de target. Si el cliente aún cerrara el
socket, esa captura sería una causa adicional y no autorizaría a revertir este
contrato ya probado.

## V1.17 - canal ordenado del clear letal (2026-08-09)

La prueba viva de V1.16 falsificó su aceptación final. La captura
`aa8-game-20260809-021500644-session-3061724227.jsonl` muestra una muerte del
NPC `2308` con contador DD05 `48`, lejos del wrap. El cliente continuó enviando
`Proxy Ping` durante unos 27 segundos después de la muerte, dejó de transmitir
y el servidor observó `peer_closed` unos 4,8 segundos más tarde. No hubo crash
ni excepción del servidor.

El control Docker denominado "funcional" de las pruebas anteriores no era un
control pre-regresión: ya contenía el commit `575a436c`, que movió
`SCUnitAiAggro` de DD05/nivel 5 a nivel 1. El padre real `575a436c^` conserva el
aggro vacío de cierre letal en el canal ordenado DD05. Esta fecha coincide con
el inicio reportado de las desconexiones después del trabajo de aggro.

La corrección no revierte el paquete completo. Los updates normales de aggro
siguen en nivel 1; solamente la forma vacía que cierra una transacción letal se
construye mediante `SCUnitAiAggroPacket.CreateCombatClear(...)` en nivel 5.
Owner, cuerpo, muerte síncrona, los dos `SCCombatCleared`, EXP y cierre de plot
permanecen sin cambios.

Validación antes del despliegue:

- suite completa .NET Core 3.1: `595/595`;
- `archery_blazing_arrow_lethal_counter_10`: `19/19`;
- `archery_blazing_arrow_lethal_counter_wrap`: `19/19`;
- `archery_blazing_arrow_lethal_concurrent_wrap`: `19/19`;
- `archery_npc_2308_lethal_closure`: `16/16`;
- compact: `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`.

La aceptación viva sigue siendo obligatoria. Hasta matar un NPC, permanecer 15
segundos, moverse y usar otra habilidad sin desconexión, V1.17 se considera
probada headless y desplegable, no cerrada en cliente.

Runtime preparado para aceptación viva:

- imagen `game`: `sha256:850817a6fe0961e8fe2a18005eb5694e7e68a6af012a091e8a9c853d491ee073`;
- `AAEmu.Game.dll`: `f326f33d1332338b5d55ac7bda05bf0a93aa6b28fe3b6e72643ba6a65bde781a`;
- rollback: `aaemu-game:rollback-pre-aa8-lethal-aggro-channel-v17-20260809` (`sha256:7c159714a3e0761683d29b2b146cce5e1a8725429bb96a97428f91fe792a48de`);
- scripts: `0 errors`, `8 warnings` preexistentes;
- sockets `2239` y `2250` activos;
- registro estable en LoginServer confirmado.

## Aceptación viva final

El 2026-08-09 el cliente AA8 real confirmó que, tras matar un NPC con V1.17,
la sesión permanece conectada y el jugador puede continuar operando. Con esta
prueba queda aceptado el contrato selectivo: updates ordinarios de aggro en
nivel 1 y `SCUnitAiAggro(count=0)` de clausura letal en DD05/nivel 5.

Estado final: **cerrado en vivo**.

## Extensión V1.18: ningún aggro positivo después del clear

Poisoned Weapons Flame expuso una segunda vía hacia la misma corrupción de
lifecycle. La auxiliar `40815` podía matar al NPC y completar correctamente
el cierre; luego el epílogo ordinario de `DamageEffect` publicaba un
`SCUnitAiAggro(count=1)` level 1 para la víctima ya muerta. La captura viva
mostró ese paquete después del `SCUnitAiAggro(count=0)` DD05 y de ambos
`SCCombatCleared`, inmediatamente antes de que el cliente dejara de transmitir.

El contrato queda ampliado sin cambiar el wire aceptado:

- el clear letal `count=0` continúa en DD05/nivel 5;
- updates positivos continúan en nivel 1 únicamente mientras `Hp > 0`;
- después de aplicar daño letal no se llama `Npc.OnDamageReceived` ni se
  publica una tabla positiva;
- el Mechanics Lab registra owner/count y falla toda transacción que observe
  `AggroCount > 0` después de `SCUnitDeath`.

La regresión permanente
`shadowplay_poisoned_weapons_flame_lethal_auxiliary.json` prueba una muerte por
efecto auxiliar, no sólo por el skill raíz, y conserva la secuencia letal ya
aceptada.
