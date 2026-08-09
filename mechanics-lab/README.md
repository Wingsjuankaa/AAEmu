# AA8 Mechanics Lab V1

Laboratorio headless determinista para ejecutar skills y combate usando el código real de `AAEmu.Game` y el compact AA8 activo. No inicia LoginServer, no conecta MySQL, no carga spawns globales y no modifica personajes persistentes.

## Autoridad y alcance

- Autoridad de datos: compact de ArcheAge Kakao 8.0.3.12 r558734 indicado explícitamente por `--compact`.
- Autoridad de ejecución: `rama_8`.
- `rama_8_modern` se usa sólo como comparador de patrones, con prueba AA8 previa.
- V1 cubre skills, plots, buffs, daño, AoE, muerte, tareas diferidas y paquetes S→C.
- Quests, economía, items complejos y persistencia quedan fuera de V1.

## Arquitectura

`AAEmu.MechanicsLab` referencia directamente `AAEmu.Game`. Los reemplazos son acotados por `MechanicsRuntime` y sólo existen mientras el proceso del Lab mantiene un contexto activo:

- `ManualMechanicsClock`: reloj virtual y `Delay` sin espera real.
- `ManualMechanicsScheduler`: ejecuta las mismas tareas de juego en orden determinista.
- `MechanicsArena`: `Character` y `Npc` reales en un mundo plano en memoria.
- `RecordingPacketLedger`: plaintext, cuerpo serializado, wire cifrado y orden real de transporte.
- `Rand.PushDeterministicSeed`: generador reproducible y reversible.
- `SQLite.PushReadOnlyDatabasePath`: compact explícito, sólo lectura y reversible.

Fuera del contexto del Lab se conservan los adaptadores productivos: reloj del sistema, Quartz, `WorldManager`, sockets, loot y persistencia normales.

## CLI

Desde la raíz del repositorio:

```powershell
.\Tools\Invoke-AA8MechanicsLab.ps1 `
  -Command run `
  -Scenario .\mechanics-lab\scenarios\archery_blazing_arrow_lethal_counter_wrap.json `
  -Compact D:\ruta\compact-aa8.sqlite3
```

Comandos directos de la CLI:

```text
aa8-mechanics run --scenario <json> --compact <sqlite> --output <dir>
aa8-mechanics analyze-trace --trace <jsonl> --output <json>
aa8-mechanics import-trace --trace <jsonl> --fixture <json> --output <scenario>
```

El wrapper usa `mcr.microsoft.com/dotnet/sdk:3.1.409-focal`, monta el compact como `/compact.sqlite3:ro` y deja resultados en `runtime-captures/mechanics-lab`.

## Matriz permanente Battlerage V2

Los fixtures `battlerage_*.json` cubren las doce familias visibles y sus
variantes ancestrales, además de buffs, liberación de CC, AoE, carga,
knockback y desplazamiento. Los campos `melee_dps` y `melee_dps_inc` usan la
escala fija interna x1000 del servidor; por ejemplo, `800000` representa 800
DPS visibles en el cliente.

La instrumentación `skill_effects_selected`, `skill_effects_applied`,
`damage_calculated` y `damage_skipped` sólo se emite cuando el Lab instala un
`MechanicsRuntimeContext`. Permite diferenciar un cast aceptado de un efecto
realmente aplicado sin alterar el proceso productivo.

El checkpoint Battlerage V2 exige dos ejecuciones completas con hashes de
resultado idénticos. Sus escenarios se mantienen como regresión permanente
junto con los cuatro fixtures `archery_*` de muerte de NPC y wrap DD05.

## Esquema de escenario V1

Un escenario declara:

- `seed`, `clock_utc` y `dd05_initial`;
- actores, HP/MP, ability level, facción, posición y arma ranged;
- buffs iniciales;
- acciones `cast`, `cast-concurrent`, `release`, `cancel`, `move`, `advance` y `set-state`;
- secuencia esperada, paquetes prohibidos después de muerte, buffs removidos, HP y número de muertes.

`cast-concurrent` inicia un envío DD05 de ruido y la skill real bajo una sonda de reordenamiento acotada. La sonda no falsifica contadores: fuerza una ventana reproducible en el transporte para verificar que `reservar contador → codificar → capturar → enviar` sea una sola transacción.

## Artefactos

Cada corrida produce:

- `<scenario>.result.json`: hashes, timeline de acciones/plots, snapshots, referencias inválidas a muertos, excepciones y validaciones;
- `<scenario>.packets.json`: ledger plaintext/wire y orden de transporte;
- `<scenario>.tasks.json`: scheduler, ejecuciones, cancelaciones y excepciones.

Los paquetes AA8 conocidos validan consumo exacto del cuerpo y equivalencia plaintext/wire. Un contrato sin oráculo debe declararse como tal; nunca se aprueba por parecido con otra revisión.

## Escenario permanente: muerte y wrap DD05

Los tres fixtures `archery_blazing_arrow_lethal_*` usan skill `36469`, rifle AA8, Forward Scarecrow `13013`, buffs `2214`, `20933` y `21987`, y avanzan 15 segundos después del cierre del plot.

La prueba concurrente reprodujo antes de la corrección:

```text
reserva DD05:    252,253,254,255,0,1,2,3
orden wire DD05: 253,252,254,255,0,1,2,3
```

La causa fue que `GameConnection.SendPacket(GamePacket)` asignaba el contador dentro de `Encode`, pero no serializaba junto a ello la escritura. Se confirmó el mismo cierre atómico en Modern y se portó únicamente el lock alrededor de encode, captura y envío. El mismo escenario ahora conserva el orden incluso cuando cruza `255 → 0`.

Esto distingue dos conclusiones:

- el wrap módulo 256 es correcto;
- una carrera entre productores de paquetes sí podía entregar `N+1` antes que `N` y provocar la desconexión del cliente.

El oráculo ampliado detectó además que eventos restantes del mismo plot podían volver a crear aggro después de la muerte. `Npc.OnDamageReceived` ahora rechaza mutaciones con HP cero y `Npc.DoDie` cierra su target antes de entregar el evento de muerte al Lab. La arena conserva la relación de combate que crearía la IA, aunque no ejecuta su loop, para probar el cleanup productivo completo.

La reproducción exacta con el NPC productivo `2308` y el A/B entre las
imágenes Docker de las 20:19 y 20:38 falsificaron la muerte diferida. La imagen
estable no contiene `deferDeath`, `FinalizeDeferredDeath` ni acciones
post-envío; la primera imagen que los contiene coincide con el inicio de la
regresión. Se restauró el flujo AA8 observado: `DoDie` y su clausura se
completan sincrónicamente, luego se publica `SCUnitPoints(HP=0, MP=0)` y el
`SCUnitDamaged` acumulado conserva su lote original. El ledger valida este
orden con `stable_lethal_closure_order` y sigue comprobando los valores
precisos de HP/MP.

Un segundo A/B, esta vez sobre el ensamblado funcional de las 20:19 y el
desplegado posterior, falsificó la promoción de `FUN_39AB5D30` como serializer
wire de `SCUnitDeath`. Esa función inicializa estado interno; añadir sus campos
no transmitidos desplazaba siete bytes de la rama con killer. El Lab conserva
el layout compacto de la imagen funcional como oráculo observado.

Resultados de aceptación del compact `4AA3CD82...29F7E2`:

```text
wrap 255 -> 0:    ACF8D6080DE36B688B75EACD285C968EE954FD59108F987A0D2CAA7D9F9A5474
concurrent wrap:  1952536FEC807C93BDBDEE658C082C81F4382B955F3520E7C7D9142F266502AA
npc 2308 closure:  422202CEE020F4A3B85755D39AB94A2BACFF1546271BEB5721C2D038EE4DE9EE
```

Dos procesos independientes del caso concurrente produjeron exactamente el mismo hash.

### Clausura de combate posterior a la muerte

La comparación posterior con la imagen funcional de las 20:19 encontró una
segunda regresión independiente. El servidor había cambiado el vaciado de
aggro desde `killer.ObjId` a `victim.ObjId` y había quitado los dos paquetes
`SCCombatCleared`. Las diez capturas fallidas compartían esa misma firma.

Los fixtures permanentes ahora fijan la transacción AA8 completa:

```text
SCUnitDeath -> SCUnitAiAggro(killer, 0)
            -> SCCombatCleared(victim)
            -> SCCombatCleared(killer)
            -> SCTargetChanged(killer, 0)
            -> SCUnitPoints -> SCUnitDamaged -> SCPlotEnded
```

No se infiere el owner a partir del nombre genérico `npcId`: el oráculo es el
A/B de la revisión r558734 que permanecía conectada. Con la clausura restaurada,
los tres casos pasan y el concurrente repite exactamente el hash
`FD4DB3AC64BD3652F8F00721A4E73D2E40FF72BEFF1B783F89DAF8982ECB1296`.
El dossier completo está en
`reconstruccion_skills_8/shared_primitives/CHECKPOINT_AA8_NPC_DEATH_CLOSURE_V1.md`.

## Regla de incorporación

Cada bug de mecánica reparado debe agregar un escenario permanente que falle antes del cambio y pase después. El cliente real queda reservado para la validación visual final: matar una unidad, permanecer 15 segundos, moverse y usar otra habilidad.
