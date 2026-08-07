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
