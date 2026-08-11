# Checkpoint Sorcery: traza de aceptación viva V1

Fecha: 2026-08-05  
Cliente: ArcheAge Kakao `8.0.3.12 r558734`  
Runtime: `compact-8.0-runtime-transversal-sorcery-v9.sqlite3`  
Runtime SHA-256: `33C0268086CCF7E6914B33CCF75B3BF935F6481CE18C9006E18B76446085C6CF`

## Propósito y límite

La evidencia estática de Sorcery está cerrada, pero un `SkillResult.Success`
no prueba por sí solo que el cliente recibió toda la secuencia, que los plots
ejecutaron sus nodos ni que la selección persistió. La traza V1 convierte el
gate vivo en evidencia reproducible sin modificar fórmulas, balance, paquetes,
cooldowns, efectos ni persistencia.

`SorceryLiveTrace` sólo observa los 43 skill IDs del cierre ejecutable V3. Por
cada ejecución registra:

- `use_result`: aceptación o rechazo exacto;
- `fired`: consumo/cooldown y comienzo de ejecución directa;
- `effects_selected` y `effects_applied`;
- `plot_event_<id>` para cada nodo realmente ejecutado;
- `ended`, `plot_ended` o `stopped`;
- caster, target, `tlId`, mundo/instancia, MP y Magic Source.

El marcador único es `[AA8SorceryLive]`. Los registros son observacionales y
no se usan para decidir gameplay.

## Herramientas

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `AAEmu.Game/Models/Game/Skills/SorceryLiveTrace.cs` | 3.236 | `A43CE9F4FAA0B1443D6119C30089A1D1FF78F3A5D04C2E45A0EE0B9D5A46245D` |
| `summarize_sorcery_live_trace_v1.py` | 7.781 | `214625A88BABC2B11F538C926EA0E781F685CF4F675887F2A0FB240907AEDB48` |
| `snapshot_sorcery_persistence_v1.py` | 4.832 | `CD5C600F8D5BB763E447EB7BDC3B93E4C17C737942724833603E496F3EFFDC69` |
| `build_sorcery_completion_audit_v1.py` | 8.176 | `D1E346E4CA1D73372BFCC1E9A93C1034FB67950826F062418746DA129698158A` |
| `generated/sorcery-completion-audit-v1.json` | 17.107 | `51EB9D8811CA65670F74092D33B5A7D364519C59F13E6E02191C23F4A01A6712` |
| `build_sorcery_live_acceptance_ledger_v1.py` | 5.177 | `C01E244EA74B7CF419C4639D6578630AC03A0CAAAA6088AC57F77F7914D8B4CE` |
| `generated/sorcery-live-acceptance-ledger-v1.json` | 19.375 | `B668F9DCA2A2CCD88B0CA39C77831E8E14BB39F6F8A7191D77ED18E7E2DA7B78` |
| `build_sorcery_completion_audit_v2.py` | 8.624 | `54E04543BE66BED77F35E258FBA3B1B770CD6C80815424B2EF8A595AFAD1E9B7` |
| `generated/sorcery-completion-audit-v2.json` | 29.236 | `D62F7CD3DB74CEE238A91AB0ED595F017E13EBC233F581B20A64C85C4501AE99` |
| `SORCERY_EXTERNAL_CORROBORATION_V1.md` | 2.868 | `5F3679E47D0168C42934C5B6077F49D20D0709C59F8924A1A77363B53B2C2A8B` |

El resumen clasifica por raíz `not_observed`, `rejected_only`,
`interrupted`, `partial_lifecycle` o `server_lifecycle_complete`. Nunca
convierte esa última clase en aprobación visual: `visual_status` permanece
`manual_evidence_required` hasta revisar cliente, repetición y relog.

## Baseline persistente

Se tomó un snapshot read-only del personaje `Dannia`, owner `1`:

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\baseline-owner-1.json
bytes: 2.002
SHA-256: 5C3C640049EB2B092DBCD1E2A90655A79E51C409BFB1F6625989E15A9A13B674
```

Estado basal:

- Sorcery en `ability1=7`, EXP `7.784.000`;
- diez activas aprendidas con sus niveles persistidos;
- seis pasivas `15/38/99/257/258/301` persistidas;
- cero selecciones Heir y cero active types;
- MP persistido `9.693`, world `0`, zone `148`.

El snapshot invoca MySQL dentro del contenedor con `MYSQL_PWD` heredado; no
imprime ni escribe credenciales y sólo ejecuta `SELECT`.

## Ledger y auditoría de finalización

El ledger V1 se construye desde las 30 raíces exactas de la auditoría V3. Cada
raíz conserva nombre AA8/inglés, contrato esperado y tres gates manuales:
`visual_fx_sound_animation`, `second_use` y `relog`. Un gate `confirmed` sin
una referencia en `evidence` es inválido; el generador comienza con las 30
raíces en `pending` y no fabrica aceptación.

`sorcery-completion-audit-v2.json` cruza la auditoría ejecutable V3, la
reconciliación AA8→runtime, la evidencia viva V2, el baseline persistente y el
resumen de la imagen actual, el ledger manual y el snapshot post-relog. El
estado honesto es `not_complete`:

- cero blockers estáticos;
- tres roots con evidencia viva anterior parcial: `10667`, `10752`, `12796`;
- cero roots certificados todavía por la traza de la imagen actual;
- pendientes: lifecycle actual, visual/repetición y snapshot post-relog.

La evidencia parcial anterior orienta la prueba, pero no se eleva a aceptación
final porque precede los cambios V8/V9 y no cubre segundo uso ni relog.

## Primera sesión viva instrumentada

La primera ejecución posterior al despliegue quedó preservada en:

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-first-live.json
bytes: 18.129
SHA-256: BD360372C73650E66A97FEF311A8F79869EB47C7CEA33977C4F6B6350DBA24B2

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-first-live.csv
bytes: 3.360
SHA-256: B9713F0B66E6617EAF49F3767B59AF211CC766BB60670BA644E26CBD1A6BCBCA
```

Flamebolt `10752` produjo `Success`, ocho eventos de plot y `plot_ended` con
`cancelled=False`; no hubo rechazo. El MP pasó de `9693` a `9672` y Magic
Source permaneció en `0`. La auditoría V2 acredita 1/30 lifecycle actuales,
pero conserva visual, repetición y relog en `pending`: esta invocación aislada
no demuestra todavía los hijos `24894/24895` de la secuencia de tres usos.

### Dummy seguro para pruebas

La prueba también expuso una diferencia de template que no debe confundirse
con Sorcery:

- `15813`, aunque es un Royal Training Dummy y declara `aggression=0`, usa
  `ai_file_id=15 (HoldPosition)`; al recibir aggro entra en combate y responde;
- `13013` es nivel 50, facción hostil `170`, `no_exp=1` y usa
  `ai_file_id=25 (Dummy)`; `DummyBehavior.Tick` no ejecuta ataque ni movimiento.

Para próximas sesiones se usa `/spawn npc 13013`. `15813` queda descartado
como blanco inerte. La limpieza se realiza con `/despawn npc 13013 30`.

Una segunda ejecución aislada contra el template Dummy aprobado quedó en:

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-flamebolt-dummy13013.json
SHA-256: D0D69B27A6B444A4906D1AA3AA4F8EAD84FF249B8B2682B14211A71BDF82F78B

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-flamebolt-dummy13013.csv
SHA-256: 702AAEFB7D9C9C52C6AFA25829C85DDC317E4599A1ECB82308DF094BF2D16225
```

Repitió exactamente `Success`, ocho eventos, `plot_ended` limpio y MP
`9693→9672`. Esto confirma repetibilidad de lifecycle servidor en dos targets
distintos. El paquete `SCUnitAiAggroPacket` sólo comunica la entrada de daño;
la ausencia de respuesta física del dummy continúa siendo un gate visual del
usuario y no se deduce del log.

## Flamebolt: cierre vivo de la cadena base

La prueba manteniendo pulsada la tecla contra el Dummy `13013` produjo dos
cadenas completas y el inicio de una tercera al soltar: `3 + 3 + 1`
proyectiles visibles. La traza aceptó exactamente:

- `10752` x3;
- `24894` x2;
- `24895` x2.

El MP pasó de `9199` a `9096`. La diferencia de `103` coincide exactamente con
`3×21 + 2×12 + 2×8`; no hubo lanzamiento exitoso ni coste duplicado. Los ocho
reintentos intermedios (`10752` x4 y `24895` x4) recibieron `CooldownTime`
mientras el cliente mantenía la entrada y no generaron proyectil ni daño.

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-flamebolt-hold-3-3-1.json
SHA-256: F95C6C1D9EC87947FC624BD8F5756B8752D6F40FFBBD7252FD8E7C0E5F35C472

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-flamebolt-hold-3-3-1.csv
SHA-256: B1BEEE8D49C689514B3BF2660DA888FC2844D21266DE772EEAD779E29B81B7B2
```

La semántica nueva queda resuelta por tres fuentes concordantes:

1. `skills.desc` AA8 indica máximo de tres ataques consecutivos, sin casteo en
   los usos sucesivos y uso automático al mantener pulsado;
2. los SpecialEffect `23309` y `15763`, tipo `48 (Combo)`, enlazan
   `10752→24894→24895` con ventana de `1000 ms`;
3. Stage 15, `x2game.dll` x64 `FUN_39899660`, recorre los efectos de la skill,
   detecta tipo `0x30 (Combo)`, selecciona el siguiente ID y continúa de forma
   recursiva en el cliente. La sesión viva muestra esos IDs llegando como
   solicitudes ordinarias al servidor.

Por tanto, `Combo` es una transición dirigida por el cliente. El handler del
servidor conserva el descriptor como declarativo y no agenda un segundo cast;
hacerlo duplicaría daño y maná. Los gates `visual_fx_sound_animation` y
`second_use` de Flamebolt quedan confirmados. Falta únicamente su gate `relog`.

## Interrupción por movimiento: defecto transversal de PlotTree

La prueba posterior al relog descubrió un defecto independiente de Flamebolt:
al moverse durante el casteo, el cliente cancelaba la barra y enviaba
`CSStopCastingPacket`, pero el servidor continuaba el plot hasta consumir MP y
aplicar daño. La ventana viva de las `22:13` conserva:

- 220 paquetes `CSStopCastingPacket`;
- 16 resoluciones que alcanzaron `SCUnitDamagedPacket` con `cast=Plot`;
- 16 finales `plot_ended ... cancelled=False`;
- cero finales `cancelled=True`.

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-flamebolt-move-cancel-before-fix.json
SHA-256: 67B0DEF05CB120A7C0A8C8A5F737838BC553A61DBC244244F32BB4B84F4B48A6

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-flamebolt-move-cancel-before-fix.csv
SHA-256: 880EEEF52FD11C67FCB40A6840F7BC752DB5E1518331A455CAE7B89B3DB4C793
```

La causa estaba en el contrato del servidor. `CSStopCastingPacket` sólo
consultaba `Unit.SkillTask`, mientras las skills plot-only castean dentro de
`PlotTree` y mantienen su lifecycle en `Unit.ActivePlotState`; por ello el
paquete válido se descartaba antes de llegar a `RequestCancellation()`.

La primera corrección alcanzó `ActivePlotState`, pero la sesión comparativa
mostró que AA8 transporta dos timelines distintos en el mismo paquete:

- primer `ushort`: `skillTlId`, usado por `SkillTask`;
- segundo `ushort`: `plotTlId`, usado por `PlotTree`.

El primer intento seguía comparando el estado del plot con `skillTlId`. Por
eso Meteor Strike `10664`, Gods' Whip `23593` y Magic Circle `11314` terminaron
con `cancelled=True`, mientras Flamebolt `10752` y Arc Lightning `10670`
continuaron con `cancelled=False`, consumieron MP y causaron cuatro impactos
plot en la ventana capturada.

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-cancel-split-timeline-before-plot-tlid-fix.json
SHA-256: BF236E6DEAF67C706037671F50E69A0AA8B1A612D88E455D880FFF4F2ED119CE

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-cancel-split-timeline-before-plot-tlid-fix.csv
SHA-256: 0C1FFD7411D7C4E3BC92CE82125C6FE490233A6AA8582699D7A176D22025070F
```

La corrección definitiva compara `plotTlId` con
`ActivePlotState.ActiveSkill.TlId`, solicita la cancelación del plot y marca
`ActiveSkill.Cancelled`; si el segundo timeline es cero admite `skillTlId`
como compatibilidad. Independientemente, compara `skillTlId` con `SkillTask`
y conserva su cancelación legada. El filtro por `objId` y ambos timeline IDs
impide cancelar casts de otra unidad o una ejecución posterior. Esto es una
primitiva transversal para cualquier skill plot-only, no una excepción
específica de Sorcery.

La aceptación posterior al despliegue ejecutó dos cancelaciones de Flamebolt
y dos de Arc Lightning. Las cuatro terminaron con `cancelled=True`, ninguna
registró `plot_ended ... cancelled=False` y no hubo daño `cast=Plot`. En la
misma ventana Insulating Lens y Meteor también cancelaron correctamente. El
usuario confirmó que el proyectil/impacto ya no sale después de moverse.

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-cancel-split-timeline-after-fix.json
SHA-256: E7C2A488BF9FB1AAE3C1BA48012321F55D9F5B90EE54A7D2D0419A7A97FD901D

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-cancel-split-timeline-after-fix.csv
SHA-256: AFC556D07CEC8AD23414C54FBD326C4A8A1601D423CFDAC545F812D6CEFD9294
```

## Aprendizaje de las dos raíces tombstone

La sesión de aceptación aprendió `10151` Freezing Earth y `10153` Insulating
Lens sin rechazo. El servidor recibió dos `CSLearnSkillPacket` y respondió dos
`SCSkillLearnedPacket`. El snapshot MySQL posterior conserva:

- 12/12 activas Sorcery aprendidas;
- `10151` nivel 6;
- `10153` nivel 5;
- 6/6 pasivas Sorcery;
- cero activaciones Heir, como corresponde antes de esa matriz.

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\post-learn-tombstones-owner-1.json
SHA-256: C947C1A325E9FE84F01E118C7671714627E576CFDB40A2DAE78C83C4C32EFFDC
```

Esto confirma el gate vivo de materialización de ambas raíces; todavía no
certifica sus efectos visuales ni su closure conductual.

## Freezing Earth: carrier AoE ausente antes de V10

Las primeras seis ejecuciones de `10151` fueron aceptadas y consumieron MP,
pero sólo alcanzaron los eventos `25974/25975/25976`. Inmediatamente después,
el loop del plot lanzó `NullReferenceException` desde
`WorldManager.GetAroundByShape -> PlotTargetInfo.UpdateAreaTarget`. El mismo
resultado contra dummy y mob normal descartó una inmunidad del objetivo.

La causa fue la ausencia de `aoe_shapes:11815`, referenciada por el evento
`25977`. La captura previa a la corrección queda congelada en:

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-freezing-earth-missing-aoe-shape-before-v10.json
SHA-256: E55A1458B00EC505576D2BF6FFD98EC104A20D7569358972716BC37153ACE35B

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-freezing-earth-missing-aoe-shape-before-v10.csv
SHA-256: 6AB69ECFE38153C4DD46A53C6E033FB21D3579E8A9899C8E1B7E549840781A48
```

El runtime V10 restaura la fila AA8 exacta, corroborada por el crosswalk como
`exact_id_exact_relation`, y la auditoría V3 ahora trata todas las formas AoE
de plots como dependencias ejecutables obligatorias. El detalle reproducible
está en `CHECKPOINT_SORCERY_NATIVE_RUNTIME_V10.md`.

La aceptación posterior confirmó cuatro ejecuciones completas contra un mob
normal. Todas llegaron a `25977/25978/25981/25979`, causaron daño y aplicaron
`buff 94`; dos recorrieron además la rama condicional `25980` con `buff 21990`.
No hubo excepciones y el usuario confirmó el resultado visual y conductual.

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-freezing-earth-after-v10.json
SHA-256: 2E5700E6AF961EE975FE628ED06C9B6A55851CB6B94456BB26DAF65D8A5F1F17

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-freezing-earth-after-v10.csv
SHA-256: 4FD89762C9AD2EC2EF72846A7A0302513F548B9516C17C6144CEB6E0385C0C63
```

Como `10151` se aprendió antes del reinicio de Game y se utilizó después de
reconectar, también queda confirmado su gate de persistencia/relog.

## Insulating Lens y colisión transversal de resource point

La siguiente prueba ejecutó `10153 Insulating Lens`. El lifecycle, `buff 95`,
Magic Source y el cooldown diferido fueron correctos, pero el cliente repitió
el banner Stormcaster durante toda la descarga del recurso. El usuario confirmó
el mismo patrón con otras skills que aplican un buff/recurso al personaje.

Los logs aislaron 21 emisiones de `SCCombatResourcePointPacket` marcadas como
`type 175`: el punto inicial 20 y veinte decrementos hasta 0. Stage 15 probó que
`0x175` es `SCAbilitySwappedPacket` y que la fábrica AA8 de resource point,
`FUN_3933FFE0`, escribe `0x315`. El serializer `FUN_39B6C080` confirma además
el layout ya implementado: `bc`, resource id, `point` de 64 bits y
`updateTime`.

La corrección de protocolo y sus RVAs quedan documentadas en
`CHECKPOINT_SORCERY_COMBAT_RESOURCE_PROTOCOL_V11.md`. No hubo cambio de datos
ni de comportamiento del buff.

```text
E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-insulating-lens-resource-opcode-before-fix.json
SHA-256: 5262605A066AA379E5543E621B1028281E8924C64B15B271E3EFFB66CB903096

E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-20260805-insulating-lens-resource-opcode-before-fix.csv
SHA-256: C5B7D4DE6F8F8CBECC90457DE48651F4EE64DFEA869333A3FE6261E3B904B3D9
```

## Chain Lightning (Wave): Snare transversal

La prueba AoE viva confirmó daño y `buff 21449` en objetivos secundarios, pero
sin inmovilización aunque el efecto Freezing era visible. El grafo y el buff son
AA8 exactos y el crosswalk AA10 los corrobora; la causa fue que el runtime
cargaba `buffs.root` pero la IA nunca lo consultaba. La corrección genérica y su
validación 514/514 están congeladas en
`CHECKPOINT_SORCERY_CHAIN_LIGHTNING_WAVE_SNARE_V12.md`. Queda pendiente la
aceptación conductual posterior al despliegue.

## Captura y resumen

Después de una sesión de prueba:

```powershell
docker compose logs --no-color --since 30m game |
  python reconstruccion_skills_8\sorcery\summarize_sorcery_live_trace_v1.py `
    --output-json E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-v1.json `
    --output-csv E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-v1.csv

python reconstruccion_skills_8\sorcery\snapshot_sorcery_persistence_v1.py `
  --owner 1 `
  --output E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\post-relog-owner-1.json

python reconstruccion_skills_8\sorcery\build_sorcery_completion_audit_v2.py `
  --baseline E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\baseline-owner-1.json `
  --live-summary E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\session-v1.json `
  --ledger reconstruccion_skills_8\sorcery\generated\sorcery-live-acceptance-ledger-v1.json `
  --post-relog E:\AAEmu-Research\output\aa8-client-forensics\sorcery-live\post-relog-owner-1.json `
  --output reconstruccion_skills_8\sorcery\generated\sorcery-completion-audit-v2.json
```

## Validación

- 40/40 pruebas C# dirigidas a traza, movimiento y efectos especiales.
- 8/8 pruebas C# de estado de casting/plot, incluidas separación de
  `skillTlId`/`plotTlId`, compatibilidad con timeline único y rechazo de IDs
  ajenos para `CSStopCastingPacket`.
- 496/496 pruebas C# completas.
- 51/51 pruebas Python Sorcery.
- El parser rechaza eventos truncados y conserva por separado lifecycle y
  gate visual.
- El snapshot rechaza pérdida silenciosa de columnas y filtra únicamente
  skills/pasivas Sorcery.
- La auditoría V2 no acepta un ledger pendiente, una confirmación sin evidencia
  ni un snapshot con regresión de EXP, skills, pasivas o selección Sorcery.

## Gate restante

La instrumentación deja el servidor listo para una aceptación controlada. La
reconstrucción sólo podrá declararse completamente cerrada cuando la matriz V2
tenga evidencia visual positiva, el resumen registre lifecycle completo para
cada raíz ejecutable aplicable y el snapshot post-relog conserve pasivas,
niveles y selecciones Heir.

## Regresión 2026-08-09: Flamebolt reiniciado por modo GM

Después del cierre Battlerage/Archery, Flamebolt dejó de recorrer sus hijos
`24894/24895`: cada pulsación mantenida repetía únicamente el root casteado
`10752`. La traza descartó pérdida de datos o de relaciones type 48. Después
de cada `plot_ended` aparecían dos paquetes `0x098` y
`AA8CooldownReset skill=10752 tags=[3308]`.

La causa fue la interacción entre `IgnoreSkillCooldowns` y la autoridad nueva
de cooldown. `ResetSkillCooldown` enviaba resets de skill/tag aunque
`cooldown_time=0` y el runtime no tuviera estado que eliminar. El cliente usó
el reset del tag para reiniciar su máquina Combo. La corrección hace que el
reset sea un delta real: no-op servidor significa cero paquetes y cero
expansión a tags. No se cambió el compact, el plot ni la cadena cliente.

Gates automatizados posteriores: 42/42 en Sorcery/cooldown/Combo y 628/628 en
la suite completa .NET 3.1 contra
`compact-8.0-runtime-battlerage-v5.sqlite3`.

## Regresión 2026-08-10: inversión transversal del orden de PlotNode

Tras eliminar los resets espurios, la captura
`runtime-captures/packet-traces/aa8-game-20260810-230807748-session-3672589487.jsonl`
continuó mostrando `10752 x3`, `24894 x0`, `24895 x0`. Cada root terminó
limpio en ~1.44 s y el siguiente request volvió a ser el root; no hubo
`SCSkillCooldownReset 0x098` ni rechazo `CooldownTime` que explicara la
pérdida del hijo.

La comparación determinista de las compact Sorcery V10, Sorcery V23, Archery
V5, Battlerage V2 y Battlerage V5 dio igualdad exacta para `skills`,
`skill_effects`, `plots`, `plot_events`, `plot_next_events`, `plot_effects` y
`plot_event_conditions` del cierre `10752/24894/24895`. El problema era código.

Git conserva el control positivo en `835b42e1`. Entre ese commit y
`73243c9e`, `PlotNode` comenzó a insertar globalmente `SCPlotEvent` antes de
los resultados del mismo nodo. La reparación candidata recupera la secuencia
anterior sólo cuando la plantilla demuestra `auto_fire + SpecialEffect type
48`; no contiene IDs y no cambia Endless Arrows ni los plots ordinarios de
Precision/Tiger.

Evidencia automática previa al gate live:

- `CooldownResetTests`, `PlotNextEventWeightTests` y
  `PlotCastingStateTests`: `40/40 PASS`;
- `sorcery_flamebolt_root_combo_presentation`: PASS, SHA-256 lógico
  `2A9C46835C51CD7CBE11A4DD6F533DA53924A6C75DA2E1D5119FC410F8098C99`;
- Precision Strike Wave y Tiger Strike Lightning: PASS;
- Endless Arrows client-owned, sin callbacks/replay: PASS.

La evidencia automática no promueve por sí sola la cadena. Falta confirmar en
cliente `10752 -> 24894 -> 24895`, dos proyectiles instantáneos, MP exacto y
ausencia de regresión visual en Endless/Precision antes de cerrar esta sección.

## Regresión 2026-08-10: carrera entre `custom_gcd=10` y guard de 150 ms

El gate live del arreglo anterior avanzó: el cliente volvió a solicitar y a
mostrar ocasionalmente los hijos `24894/24895`, pero no de forma estable. La
traza `aa8-game-20260810-234154357-session-3716780330.jsonl` contiene en una
sola sesión cadenas exitosas y fallidas. Los requests tempranos de `24895`
recibieron `CooldownTime` hasta superar aproximadamente 150 ms desde la etapa
anterior.

No eran dos condiciones de datos ni dos ramas del plot: todos los roots
observados recorrieron `plot_event_19208`. La competencia estaba entre:

- el guard histórico AAEmu de 150 ms;
- la cadencia nativa explícita de `24894/24895`, `auto_fire=1` y
  `custom_gcd=10`.

`Skill.ResolveRequestGuardMilliseconds` conserva 150 ms como baseline, pero
permite que un `auto_fire` con `custom_gcd` positivo menor declare su cadencia
real. El GCD continúa validándose por separado. Endless (`220 ms`) y las
cadenas Battlerage (`>=200 ms`) no se aceleran por esta regla.

La instrumentación de admisión ahora distingue `request_guard` de
`global_cooldown`. Antes del nuevo gate live pasaron 43/43 pruebas dirigidas y
los fixtures Flamebolt/Endless conservaron exactamente sus hashes aceptados.

## Enmienda definitiva 2026-08-10: retirada de la capa Combo custom

La captura UTC `aa8-game-20260811-000043728-session-136818707.jsonl`
falsificó la hipótesis anterior: registró siete requests `10752`, cero
`24894/24895` y ningún rechazo de cooldown para Flamebolt. Por tanto, ni el
guard de 150 ms ni `custom_gcd=10` podían ser la causa de esa sesión; el cliente
nunca llegó a pedir los hijos.

El contraste con el último control positivo, commit `835b42e1`, aisló la
regresión transversal real: `PlotNode` había sido cambiado después de Sorcery
para invertir globalmente el orden observable del nodo y agrupar primero
`SCPlotEvent`, seguido de daño/buffs. Sobre esa inversión se fueron acumulando
clasificadores `auto_fire`, excepciones de feedback y guards variables. La
intermitencia aparecía porque distintas ramas terminaban dependiendo de esas
excepciones superpuestas.

Se retira completa esa capa custom y se restaura el contrato del control
positivo:

- efectos/resultados del nodo y luego su `SCPlotEvent`, sin inversión/batch
  global;
- guard histórico único de 150 ms, sin resolverlo desde `auto_fire` ni
  `custom_gcd`;
- respuesta nativa `SCSkillStarted` para rechazos, sin supresión o clasificación
  por tipo de cadena;
- ningún replay, callback, cola, transición Combo o cast sintético de servidor;
- type 48 permanece como dato consumido por el cliente, no como máquina de
  admisión del servidor.

Se conservan dos correcciones independientes y ya probadas: el reset GM es
no-op cuando no existe cooldown real, y `SCBuffCreated` sólo enlaza la skill
opcional cuando `toggle_buff_id` coincide con el buff creado. La autoridad de
cooldown real (inicio único, reducción y reset separados) tampoco se altera.

El fixture root-only de Flamebolt se elimina: podía comprobar daño y cierre,
pero no demostrar `10752 -> 24894 -> 24895`. Esa aceptación vuelve a ser
exclusivamente live.

Validación y despliegue candidato:

- .NET Core 3.1: `620/620 PASS`;
- Mechanics Lab Battlerage: `suite_failed=0`;
- estructura/runtime V5: `11/11 PASS`;
- artefactos Phase 4: `6/6 PASS`;
- cierre documental: `4/4 PASS`;
- SQLite: `quick_check=ok`, `integrity_check=ok` y SHA-256
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- imagen `game`: `sha256:2c5652ff6e85d6d9316a50061bcf1a21c6ed5654e3265bba445750abf4ff6600`;
- `AAEmu.Game.dll`:
  `C59BD55AC31F8D9E4FFAAEF6C46AB7BAB1D2E93CF97084A6574F2A70D3C85B65`;
- rollback: `aaemu-game:rollback-pre-native-plot-baseline-20260810`;
- sólo se recreó `game`; scripts `0 errors`, puertos `2239/2250`, registro en
  LoginServer y `RestartCount=0`.

## Regresión 2026-08-10: el guard fijo sobrevivió a la retirada Combo

La prueba posterior demostró que restaurar transporte, feedback y resets no era
suficiente. En
`runtime-captures/packet-traces/aa8-game-20260811-002109290-session-1246466874.jsonl`
el cliente produjo una cadena real: `24894` fue aceptada y `24895` llegó a 74,
91, 112 y 183 ms. Los tres primeros requests fueron rechazados con
`CooldownTime`; sólo el cuarto pasó el guard histórico de 150 ms. Otras siete
ejecuciones de la misma sesión repitieron sólo `10752`, reproduciendo la
intermitencia visual indicada por el usuario.

La evidencia del compact elimina la necesidad de inferir una excepción Combo:
los plots `280/1454/1455` aplican type 41 con 1000/10/10 ms respectivamente.
Endless aplica 200 ms en su plot compartido. Se retiró por ello
`SkillLastUsed + 150 ms` y su estado en `Unit`; la admisión usa exclusivamente
el `GlobalCooldown` declarado por AA8, el cooldown propio y los requisitos de
skill. No se añadió lógica por ID ni una máquina type 48 en el servidor.

Estado candidato: compilación y suite .NET Core 3.1 `620/620 PASS`; pendiente
captura live posterior al despliegue para confirmar `10752 -> 24894 -> 24895`
estable y Endless sin aceleración.

## Corrección 2026-08-11: propietario de casteo en `SCPlotEvent`

El gate anterior descartó también la retirada del guard como causa primaria:
el servidor aceptaba y cerraba `10752`, pero el cliente seguía sin solicitar
`24894/24895`. Para dejar de comparar aproximaciones de Git se recuperó el
artefacto exacto que produjo la captura positiva del 2026-08-05:

- imagen `sha256:c49c09ecbd...`;
- `AAEmu.Game.dll` SHA-256
  `EEC1E52B9B98F34CA77D6F8146252B3587A040402B50A69A4E57D4A03BCA947A`;
- fuente decompilada preservada en
  `runtime-captures/flamebolt-good-20260805-c49c09ec/`.

El cierre lógico de Flamebolt en Sorcery V23, Archery V5, Battlerage V2 y
Battlerage V5 es idéntico, con SHA-256 conjunto
`f4d463...`: skills, effects, type 48, plots, 47 eventos, 33 aristas, 77
plot-effects y 53 condiciones. Queda descartada una deriva del compact.

La diferencia ejecutable estaba en el actor publicado por `SCPlotEvent`. El
runtime positivo asocia el caster cuando el evento fue alcanzado a través de
una arista padre `Casting` o `Channeling`; la regresión consultaba las aristas
salientes del evento y marcaba el nodo que inicia la fase. Esa inversión cambia
el ciclo de casteo observado por el cliente justo antes de que éste seleccione
la continuación type 48.

`PlotNode` vuelve al contrato probado:

```text
SCPlotEvent.actor = ParentNextEvent is Casting/Channeling ? caster : 0
```

No se añadió ninguna excepción por skill. `casting_useable` tampoco justifica
la inversión: AA8 lo libera mediante el opcode independiente `0x159`, con
actor BC3, modo `u16` y `plotTlId u16`. La prueba de regresión fija ahora tanto
el padre casting/channeling como el caso sin padre.

Gate automático previo al live: 35/35 pruebas dirigidas PASS; Precision Strike
Wave, Tiger Strike Lightning y Tiger Strike base PASS; suite .NET Core 3.1
`620/620 PASS`. Candidato desplegado sólo en `game`:

- imagen `sha256:943967cb1395cfbe3b2efb258a07276543a91e7568e906ebff6369567acfa591`;
- DLL SHA-256
  `BB577AD8CB43E33D78900AC5CFD4DAC875318EE9C61CE10164329A5DAAEFD493`;
- compact montado y verificado
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- rollback `aaemu-game:rollback-pre-flamebolt-cast-owner-20260811`;
- scripts `0 errors`, puertos `2239/2250`, LoginServer registrado y
  `RestartCount=0`.

La aceptación definitiva sigue siendo una captura cliente estable
`10752 -> 24894 -> 24895`.

## Aceptación live final 2026-08-11

El usuario confirmó en cliente que Flamebolt volvió a ejecutar su ciclo nativo:
un root casteado y dos bolas instantáneas, repetible al mantener pulsada la
habilidad. En la misma validación confirmó correctas las ramas Battlerage y
Archery previamente cerradas.

La captura
`runtime-captures/packet-traces/aa8-game-20260811-011526503-session-630269949.jsonl`
aporta evidencia servidor adicional: dos ciclos registraron Burning con
`originSkill=10752` y luego Conflagration con `originSkill=24895`, separados por
aproximadamente 260-270 ms. Esto prueba que el hijo final fue solicitado y
ejecutado; no existe replay ni cast sintético capaz de fabricar ese origen.

Resultado promovido:

- Flamebolt `10752 -> 24894 -> 24895`: PASS visual y lifecycle;
- Endless Arrows: PASS visual con autoridad type 41 nativa;
- Battlerage validado: sin regresión observada;
- `SCPlotEvent.actor` resuelto desde `ParentNextEvent Casting/Channeling`;
- ninguna máquina Combo, guard de request, allow-list, replay o timer custom.

La regresión queda cerrada. La lección se promueve a
`SKILL_TREE_RECONSTRUCTION_GUIDE_V1.md` V1.20 y a la skill global
`references/native-first-regression-control.md`.
