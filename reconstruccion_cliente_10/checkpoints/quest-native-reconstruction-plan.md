# Reconstrucción nativa de misiones AA10 r575

Checkpoint operativo para `Wingsjuankaa/AAEmu:rama_10`. Este documento fija la
evidencia, los vacíos y las puertas de salida; no convierte AA8 ni implementaciones
modernas en autoridad de AA10.

## Línea base congelada

- Fecha del corte: 2026-08-20.
- Rama objetivo: `rama_10`.
- Commit objetivo al iniciar: `69a3b4f6a538367b037610a5eb80e4f1464b4c65`.
- Padre obligatorio: `upstream/client_version/zone-10.0.2_r575` en
  `a3c735c658ebe20d10cb50684b4b3e366b7d87e1`.
- Divergencia al iniciar: 23 commits propios, 0 commits del padre pendientes; el
  padre es ancestro del objetivo.
- Dominio quest limpio antes de esta intervención. Los cambios previos del árbol
  de trabajo, en especial ArchePass/Attendance, se consideran propiedad del usuario.

### Artefactos AA10 autoritativos

| Artefacto | Bytes | SHA-256 |
|---|---:|---|
| `game_decrypted.sqlite3` | 552178688 | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` |
| compact retail | 440827904 | `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849` |
| `x2game.dll` | 21808640 | `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734` |
| `game_pak` | 68963258880 | `AB3B86E694CFC0141453AD9B734BABEE67019C58D8E0B52498036ABC0DCBCBF0` |

Los tres primeros hashes se recalculan en cada Stage 40. El hash del `game_pak`
fue recalculado con `Get-FileHash` en este corte; cada ejecución verifica además
su tamaño. `PRAGMA quick_check` devolvió `ok` en ambas SQLite fuente.

## Fase 0 — inventario y matriz de cobertura (completada)

Extractor versionado:
`reconstruccion_cliente_10/scripts/build_quest_stage40.py`.

Salida fuera del repositorio:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\quest-stage40`.

Se generaron `repro-a` y `repro-b`. Los cinco artefactos son idénticos byte a
byte:

| Archivo | SHA-256 |
|---|---|
| `quest-stage40.sqlite3` | `B739BD54F996B16C2450D5D7207B4107CB84079A5DF4C2E192981B1498D4D1A5` |
| `act-type-coverage.csv` | `8E87EDD9C2CB3904A7DA0294D973D6435943ABE2A9EE89BAFD11172EFA0C79B6` |
| `nuia-quests.csv` | `9450F4AE4E305A610C89F0D772F963FCEE27B6A2AAF61BE2CB437E8117391391` |
| `nuia-zone-crosswalk.csv` | `A617B0ABD55A2552B7B99C65B1BE3AA245B063976EC6281EC5084FFA8394FE78` |
| `manifest.json` | `7D1252E6662C1D37B4591D0BCA4167E3D3ABD25DB48800604033A6103486684C` |

La SQLite generada también devolvió `ok` tanto para `PRAGMA quick_check` como
para `PRAGMA integrity_check` en las dos reproducciones.

### Inventario estructural

- 9011 `quest_contexts`, 33126 componentes y 43795 actos en la SQLite completa.
- 86 tipos distintos de acto; 58 actos deshabilitados.
- Cero componentes o actos huérfanos en la base completa.
- El compact retail conserva los 33126 componentes y 43795 actos, pero sólo
  7944 contextos: deja 3821 componentes proyectados sin contexto. Por ello no es
  una fuente suficiente para reconstruir el grafo completo.
- El runtime omite intencionalmente 110 tutoriales de categoría 45; quedan 8901
  contextos cargables.
- Cuatro grupos de objetivos exceden el límite histórico interno de cinco:
  quests 10748 (12), 10866 (10), 10853 (9) y 8887 (6). Sólo 10748 excede el
  contrato AA10 de diez y queda clasificada como dato incompatible/test hasta
  obtener evidencia nativa adicional.

### Cobertura de actos pendiente

Hay 29 tipos positivos sin loader de detalle utilizable en el servidor, con 2039
referencias habilitadas:

- Condiciones (422): `QuestActConAcceptLevelRange` 10,
  `QuestActConAcceptNpcGroup` 145, `QuestActConReportNpcGroup` 267.
- Objetivos (220): `QuestActObjCompleteQuestGroup` 32,
  `QuestActObjConquestWar` 5, `QuestActObjConsumeEvolvingMaterial` 8,
  `QuestActObjEnchantScaleCount` 5, `QuestActObjFactionCompetition` 6,
  `QuestActObjGainExpPoint` 13, `QuestActObjGainHonorPoint` 37,
  `QuestActObjGainLivingPoint` 38, `QuestActObjInviteTeamFaction` 4,
  `QuestActObjMonsterContrGroupHunt` 21, `QuestActObjMonsterContrHunt` 8,
  `QuestActObjNpcKill` 25, `QuestActObjPcKill` 9 y
  `QuestActObjSellBackpackGood` 9.
- Recompensas (1397): `QuestActSupplyActability` 633,
  `QuestActSupplyArchePassPoint` 325, `QuestActSupplyContributionPoint` 113,
  `QuestActSupplyExpeditionExp` 82, `QuestActSupplyFactionChange` 27,
  `QuestActSupplyFamilyExp` 10, `QuestActSupplyLeadershipPoint` 127,
  `QuestActSupplyLocalLp` 2, `QuestActSupplyRankedItem` 23,
  `QuestActSupplyResidentCharge` 1, `QuestActSupplyResidentPoint` 41 y
  `QuestActSupplyResultRankedItem` 13.

Además, seis clases delegan en `base.RunAct` (238 referencias):
`QuestActObjCondition`, `QuestActObjEffectFire`, `QuestActObjItemGroupGather`,
`QuestActObjItemGroupUse`, `QuestActObjSendMail` y `QuestActSupplySkill`.

Los placeholders parciales que requieren dossier propio son
`QuestActConAcceptComponent`, `QuestActCheckGuard`,
`QuestActConAcceptNpcEmotion`, `QuestActObjDistance` y
`QuestActObjCompleteQuest` (`Count`/`AcceptWith`).

### Cierre Nuia

- Categoría 3: 55 quests, 344 actos y 18 tipos.
- Cero actos deshabilitados y cero actos habilitados sin clase/loader.
- El grafo referencial observado cierra sobre 61 items, 38 NPC, 17 doodads,
  7 skills, 22 cinemas, 2 spheres, 1 monster group y 1 interacción de mundo.
- La primera quest, 6839, depende de sphere 2321, cinema y autocompletado. La
  carga global de spheres existe (2632 áreas en 103 zonas), pero falta una prueba
  E2E autorizada de sphere 2321.
- Capítulos intro–5 tienen cruce de perfiles observado: claves nativas
  142/178/179, 144/195, 140/185/195 y 143.
- El capítulo 6 usa zonas lógicas 2 y 15, cruzadas a claves 133 y 149. Esas dos
  particiones no están en el paquete Zone retail analizado. Este es el principal
  bloqueo espacial conocido de la cadena Nuia; no se rellenará con spawns o
  teleports inventados.

## Plan de acción y puertas de salida

### Fase 1 — contrato base de quests (completada)

1. Unificar capacidad interna, persistencia y wire AA10 en diez objetivos.
2. Leer blobs históricos de cinco objetivos y completar 6–10 con cero.
3. Escribir desde ahora los diez objetivos.
4. Respetar `quest_acts.enable` al cargar actos base.
5. Añadir pruebas de capacidad, round-trip nuevo, migración del blob antiguo y
   filtro SQL.
6. No ocultar la quest 10748: conservarla como hallazgo explícito de capacidad
   mayor que el protocolo hasta resolver su procedencia.

Puerta: build limpio y pruebas quest focalizadas verdes, sin iniciar Zone ni
alterar datos persistentes.

Resultado aplicado:

- `Quest.ObjectiveCount` unifica runtime, persistencia nueva y wire en diez.
- `ReadData` acepta únicamente el layout histórico de 38 bytes o el layout AA10
  de 58 bytes; longitudes desconocidas fallan con diagnóstico explícito.
- El layout histórico importa cinco contadores y completa los otros cinco con
  cero. `WriteData` emite los diez desde este corte.
- `quest_acts.enable` se conserva en el template base. Las 58 filas deshabilitadas
  siguen disponibles sólo para resolver con seguridad sus tablas de detalle, pero
  no se adjuntan al componente y por tanto no se ejecutan. Esto evita el `null`
  que produciría filtrar la metadata antes de construir los detalles.
- `dotnet build AAEmu.UnitTests/AAEmu.UnitTests.csproj --no-restore`: 0 errores.
- Suite `AAEmu.UnitTests`: 1402 correctas, 0 fallidas, 0 omitidas.
- El build conserva advertencias preexistentes, incluidas las alertas NU1902 y
  NU1903 de dependencias; no forman parte del cambio quest y quedan registradas
  como deuda separada.
- No se inició Zone ni se modificaron Docker, `.env`, MySQL, cliente o bases de
  datos fuente.

### Fase 2 — condiciones de aceptación/reporte (completada)

Implementar los tres tipos faltantes y corregir los tres placeholders de
condición. Cada tipo exige dossier AA10 con tabla, campos, productor/evento,
transición, valores límite y al menos una quest fixture.

Puerta: cero condiciones habilitadas sin loader o con retorno constante no
justificado.

Resultado aplicado:

- Se añadieron clase y loader para `QuestActConAcceptLevelRange` (10 referencias
  habilitadas), `QuestActConAcceptNpcGroup` (145) y
  `QuestActConReportNpcGroup` (266 habilitadas y una fila deshabilitada).
- `AcceptLevelRange` usa límites inclusivos y su productor es
  `DoOnLevelUpEvents`; al entrar en el rango inicia la quest si no está activa ni
  completada.
- Los dos tipos de grupo reutilizan exclusivamente
  `quest_monster_npcs`: aceptación exige procedencia NPC y pertenencia; reporte
  usa el evento `OnReportNpc`, valida readiness, conserva la recompensa elegida
  y mueve la quest a `Ready`.
- `QuestActConAcceptComponent` dejó de devolver una constante. Valida las 299
  autorreferencias de starter/evento y las 176 referencias cruzadas sólo cuando
  el `quest_context` referido está materializado. No inicia otra quest como
  efecto lateral inventado; las 475 referencias AA10 resuelven sin huérfanos.
- `QuestActCheckGuard` dejó de devolver una constante y exige un NPC del template
  indicado, vivo y con HP positivo en el `WorldInstance` del propietario. Sus 22
  referencias resuelven a nueve templates NPC existentes; la fixture negativa
  explícita es la quest 11198 de fallo de escolta.
- `QuestActConAcceptNpcEmotion` resuelve el texto nativo contra `anims.id`. Las
  dos filas usan `fist_ac_worship`, ID 124. `CSExpressEmotionPacket` ya entregaba
  ese ID al productor; ahora el evento inicia la quest y conserva el ID en la
  instancia, de modo que una aceptación NPC normal o una emoción distinta no
  puede suplantarlo.
- Stage 40 v2 añade `phase2-condition-dossier.csv` y la tabla SQLite equivalente
  con tabla/campos, productor, transición, límites, fixture y checks por tipo.
  Resultado: 902 referencias habilitadas cubiertas, 0 sin implementación y 0
  retornos constantes.
- Queda evidencia negativa separada del código: 12 referencias habilitadas de
  `QuestActConReportNpcGroup` usan los grupos 894–897, ausentes tanto de
  `quest_monster_groups` como de `quest_monster_npcs` en la SQLite completa y en
  el compact retail AA10. Corresponden a quests de apoyo de materiales 9139–9156.
  No se inventaron miembros; requieren una fuente AA10 adicional si se desea
  rehabilitar ese contenido legacy.
- `repro-a` y `repro-b` son idénticos byte a byte. Hashes principales:
  `quest-stage40.sqlite3`
  `A07DDB989E9CE18934CBE3DC63CE1B42BE1FD3AFD6CAB7064389CB213236BD74`,
  `phase2-condition-dossier.csv`
  `7B80608AB571CFB4741A8D64BB304E2402B8FD5A84618C183AA33A11A207E992`
  y `manifest.json`
  `035AEBA3E221BEA1416ABBCDDE2783C71FC0802FA4CC106887261AF300832364`.
- Build Release sin restore: 0 errores. Fixtures focalizadas: 6/6. Suite completa
  `AAEmu.UnitTests`: 1408 correctas, 0 fallidas y 0 omitidas. Se conservan las
  advertencias de dependencias y análisis ya registradas; no son regresiones de
  quests.
- No se inició Zone ni se modificaron Docker, `.env`, MySQL, cliente, compact
  retail, `game_pak` o SQLite autoritativa.

### Fase 3 — objetivos/eventos (completada, incluida Fase 3B)

Priorizar por impacto y reutilización del productor: honor/labor/XP, NPC/PC kill,
monster contribution, evolving/enchant, faction competition, team invite,
complete quest group y backpack sale. Resolver también los cinco stubs de
objetivo.

Puerta: cada objetivo habilitado recibe un evento nativo demostrable y persiste
su contador; no se aceptan polling o autocompletados como sustituto silencioso.

Resultado aplicado:

- Se añadió un evento interno tipado para transacciones de objetivo. Se publica
  únicamente después del commit de la mecánica y conserva actor, cantidades y
  referencias nativas. La oferta de team share se hace una sola vez en el
  productor; cada act decide si la acepta, evitando loops o doble conteo.
- Se añadieron clase y loader AA10 para los 14 tipos que faltaban, además de
  `quest_context_group_members`. Los cinco stubs de objetivo dejaron de delegar
  en `base.RunAct`: condition, effect fire, item-group gather/use y send mail.
- XP, honor y vocation cuentan el delta positivo realmente aplicado, después de
  rates, modificadores y clamps. No cuentan gastos ni cantidades solicitadas que
  no llegaron al balance.
- `NpcKill`, `PcKill` y monster contribution nacen de kill credit ya validado.
  NPC usa rangos inclusivos/open-ended y el bit nativo `grade_id - 1`; PvP exige
  relación hostil y aplica `level_gap`. Contribution reutiliza los propietarios
  elegibles resueltos por tag/derechos del NPC, no un kill global.
- Synthesis cuenta los slots de material sólo después del consumo atómico;
  temper cuenta un intento después de catalizador/costo/resultado; backpack sale
  cuenta después de correo de pago, consumo de pack/labor y mutación de mercado.
- La invitación de facción se resolvió como expedition porque
  `enum_quest_act_obj_invite_types.id=1` es `expedition`. El accept valida una
  invitación pendiente exacta —inviter y expedition— y el buff AA10 13921 antes
  de acreditar al invitador; los IDs entregados por el cliente no bastan.
- Effect fire se emite después de `effect.Template.Apply`; send mail exige envío
  y fee exitosos y compara todas las cantidades adjuntas. Item groups consumen
  los eventos nativos de inventario/uso y gather aplica deltas firmados sin bajar
  de cero. Las filas AA10 tienen `check_exist=false`, por lo que no se agregó un
  seed de inventario especulativo.
- `CompleteQuest` y `CompleteQuestGroup` son contadores event-driven y respetan
  `Count`; `AcceptWith` es la única ruta que permite sembrar completado previo.
  `Distance` hace una evaluación inicial y luego escucha `UnitEvents.OnMovement`;
  ya no hace polling desde `RunAct`.
- Los contadores siguen el contrato de persistencia de diez objetivos cerrado en
  Fase 1. Stage 40 v3 cubre 649 referencias habilitadas de Fase 3: 638 tienen
  clase, loader y callsite productor; 11 quedan clasificadas como bloqueo nativo,
  no como implementación silenciosa.
- Bloqueo exacto: `QuestActObjConquestWar` (5) y
  `QuestActObjFactionCompetition` (6) tienen consumidores y loaders, pero este
  runtime no contiene lifecycle autoritativo de competencia/conquista ni fuente
  de rank/result. Sólo existen el shell de paquete
  `SCFactionCompetitionUpdatePointPacket` y el enum
  `GiveFactionCompetitionPoint`. No se fabricaron resultados ni se conectó un
  autocompletado; cerrar esas 11 referencias exige reconstruir primero ese
  subsistema desde evidencia AA10 adicional.
- Stage 40 v3 añade `phase3-objective-dossier.csv` y la tabla SQLite equivalente.
  Dos regeneraciones fueron idénticas byte a byte. Hashes principales:
  `quest-stage40.sqlite3`
  `5C03783B0B74B520458611FC3A26ECE6A775A9E61606CF99751C6311971B1B54`,
  `phase3-objective-dossier.csv`
  `57EFF3AFDE4ABC2AFBEC26B251FD583CF0D8A625D6526BB2B659A6027185F8E7`
  y `manifest.json`
  `94E0843FE1D8B36CD7998A5935C12BE91D4DD7E16E97F9C398F7128A39B2312F`.
- Build Release: 0 errores. Suite completa `AAEmu.UnitTests`: 1413 correctas,
  0 fallidas y 0 omitidas. Se mantienen advertencias preexistentes de paquetes y
  análisis; no se inició Zone ni se modificaron Docker, `.env`, MySQL, cliente,
  compact retail, `game_pak` o SQLite autoritativa.

#### Fase 3B — competición de facciones y guerra de conquista (completada)

Se reconstruyó el subsistema que bloqueaba las últimas once referencias de
objetivo sin trasladar reglas desde AA8 ni fabricar resultados. La autoridad es
AA10 r575 y se separan expresamente dos ciclos distintos:

- `FactionCompetition` se vincula a las seis zonas declaradas en
  `conflict_zones` (17, 20, 63, 139, 140 y 147), inicia/finaliza con el estado
  de zona autorado y usa los modos PVP/PVE, umbral, reset y cambio forzado de
  `faction_competitions`.
- `ConquestWar` de zona 78 usa el ciclo del TowerDef 126 (Dew Plains, 2400 s).
  El objetivo de zona 20 se publica únicamente para la facción ganadora de la
  competición de purificación que precede a la ocupación. Las cuatro filas de
  zona 78 (`complete_rank=4`) reciben además el snapshot de rango al aceptar la
  misión o entrar durante un ciclo activo; no dependen de que ocurra otro cambio
  de puntaje.
- El ranking es determinista: empates comparten puesto con salto del siguiente;
  un ganador exige líder único y `req_point`. Se conservan los tres resets
  nativos: todos, sólo ganador y todos ignorando requisito.
- Las fuentes de puntos son kill PC, kill NPC filtrado por
  `faction_competition_npc_infos`, quest completada filtrada por
  `faction_competition_quest_infos`, efecto especial 177 y los diez
  `doodad_func_competition_points` periódicos. Todos acreditan después del
  productor autoritativo correspondiente.
- Los TowerDefs de ganador se resuelven por `competition_tower_defs`; el
  `force_stop_tower_def_id` y los TowerDefs de guerra/paz de `conflict_zones`
  quedaron integrados al lifecycle existente.
- Se implementaron y registraron los paquetes exactos r575: point-list `0x336`,
  result `0x337` y update `0x338`. La lista lleva `isZoneIn`, zone group,
  timestamp inicial, duración en segundos y vector `{factionId, point}`; result
  conserva ganador y snapshot final. El cliente recibe resync al entrar.
- Estado global, reloj y puntajes se persisten en MySQL mediante la migración
  `2026-08-20_aaemu_game_faction_competition_states.sql`; no se aplicó la
  migración ni se mutó el MySQL de esta sesión.

Evidencia binaria/datos:

- `x2game.dll` exacta: SHA-256
  `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.
  Vtables/serializadores confirman opcodes, anchos y orden. La función nativa de
  tiempo restante confirma `duration - max(now,start) + start`.
- `faction_competition.lua` (SHA-256
  `48F39E8EDD8C7DDB9753601788ADF33A04AFCECEF85ABF85D31F82360263385C`)
  y su companion `.alb`
  (`70B4B1A7E32B218CCDB071C26152F488FCD59BB137B09C4C0C4FDFB708DB4E9A`)
  fueron extraídos directamente del `game_pak`; los eventos UI observados son `UPDATE_POINT`, `INFO` y
  `RESULT`, y `pointList` contiene `factionId/point`.
- El HUD nativo de conquista también fue extraído: `conquest_state.lua`
  (`F4D3F159FB4FCC8D6E5918FD977579FA4A9FF8EB200FE86F92CD7CD606225C27`)
  y `conquest_state_view.lua`
  (`95FD23DE977CC052CFDCF521BBE7B138493636AAF28C140F1E1BA8D89580CC6A`).
  `X2ZoneGroupState:GetConquestScoreInfos(zoneGroup)` devuelve hasta seis filas
  de facción con `score`, `rank` y `addScore`; esto confirma que
  `QuestActObjConquestWar.complete_rank` compara rango de facción, no una
  contribución personal.
- La DLL Zone dedicada exacta
  (`8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A`)
  registra `conquest_bonus_score`/`conquest_penalty_score` como FormulaKind
  33/34 y las carga junto al catálogo completo. Sus fórmulas AA10 reciben
  `my_score`/`enemy_score`, pero el seguimiento de referencias no demuestra un
  productor de puntos por kill; los escalares 0x21/0x22 próximos pertenecen a
  atributos de combate. No se conectó una regla PvP especulativa: Conquest sólo
  acepta los productores explícitos de puntos reconstruidos.
- SQLite autoritativa: SHA-256
  `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`;
  compact retail:
  `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849`.

Puertas cerradas:

- Stage 40 v3: 649/649 referencias de Fase 3 implementadas, 0 bloqueadas y 0
  productores ausentes. Dos regeneraciones son idénticas byte a byte.
  `quest-stage40.sqlite3`:
  `43F5BDB5EB06985D8B23EA23018BDCAB27798C9118C6178AA0D10B0405242F04`;
  `phase3-objective-dossier.csv`:
  `EF868A9D5894574424A0038DB55B0677EE681B508551131403A46796896B007A`;
  `manifest.json`:
  `61F858B0D503089122DDB78BA746DA5526438913DBC5FD1B06ABFB82DE2841C0`.
- Build integral `AAEmu.slnx`: 0 errores. Se añadieron fixtures de ranking,
  empate/umbral, resets, saturación y layouts de los tres paquetes. Suite
  completa: 1419 correctas, 0 fallidas y 0 omitidas.
- No se inició Zone, Docker ni cliente; no se modificaron `.env`, MySQL,
  `game_pak`, compact retail o SQLite autoritativa. La validación live queda para
  la fase E2E autorizada.

### Fase 4 — recompensas

Implementar monedas/puntos sociales, residentes, familia/expedición, ArchePass,
ranked items y cambio de facción usando los managers AA10 existentes. Coordinar
ArchePass con los cambios previos del usuario para evitar solapamientos.

Puerta: idempotencia, límites, rollback/errores y paquetes de actualización
probados por tipo de recompensa.

#### Corte Fase 4A — loaders, ranking y progreso social persistente (2026-08-20)

Implementado:

- Los 12 tipos AA10 tienen clase concreta y loader desde su tabla nativa. Stage
  40 ya no los clasifica como `missing_server_class`/`missing_detail_loader`.
- `QuestActObjFactionCompetition` y `QuestActObjConquestWar` conservan el rango
  real en el contador persistente de objetivo. Antes se guardaba siempre `1`,
  por lo que `RankedItem` no podía distinguir puestos 1..4 después de relog.
- Actability, ContributionPoint, LocalLp, LeadershipPoint, ExpeditionExp,
  FamilyExp y los dos RankedItem tienen consumidores. Los límites propios de
  actability/local labor/contribution se delegan a los managers existentes; el
  liderazgo usa saturación `uint` y reset diario UTC; expedition exp usa
  `expedition_levels.daily_exp` y reset UTC.
- Se añadió persistencia aislada para liderazgo y experiencia de expedición mediante
  `2026-08-20_aaemu_game_quest_reward_progress.sql`. La migración fue creada y
  validada estáticamente, pero no fue aplicada al MySQL activo en este corte.
- Los paquetes de actualización de familia, expedición y residentes tienen
  fixtures byte a byte de anchos/orden r575. El pool de ranked items reutiliza
  la entrega por bolsa/correo ya existente.
- Familia y residencia conservan loaders y consumidores explícitos, pero fallan
  antes de escribir estado mientras el productor nativo de los campos genéricos
  de sus notify no esté probado. No se dejaron tablas activas basadas sólo en
  una interpretación del layout.
- ArchePass no banca puntos ficticios: si no existe un pass activo persistido,
  `TryAddQuestPoints` devuelve fallo, resincroniza el estado vacío y conserva la
  quest para reintento. Esto respeta el cierre previo de mutaciones Start/Buy/
  Upgrade/Claim del usuario.
- FactionChange también falla antes de mutar. AA10 usa `system_faction_id=0` en
  cinco rutas y las flags `ignore_limit`/`inferior_escape` dependen del cálculo
  de población/cooldown aún ausente; aplicar sólo `SetFaction` dejaría guild,
  housing y quests ligados a facción en estado parcial.

Cobertura Stage 40 v4:

- 1.397 referencias habilitadas de Fase 4 inventariadas.
- 993 implementadas con contrato cerrado.
- 0 candidatas ejecutándose con semántica provisional.
- 404 bloqueadas de forma visible: ArchePassPoint 325, FactionChange 27,
  FamilyExp 10 y ResidentPoint/ResidentCharge 42.
- Nuia continúa con 0 actos habilitados sin clase/loader; estos bloqueos no
  aparecen en los 55 quests de la cadena racial inventariada.

Validación del corte:

- Build integral `AAEmu.slnx`: 0 errores.
- Suite completa: 1.427 correctas, 0 fallidas, 0 omitidas.
- Dos generaciones Stage 40 son byte a byte idénticas.
- `quest-stage40.sqlite3`:
  `DBFD6EFD661DE8BAC0C0A7EF9781627E5938BC4ED77D7C892A0F698CB3C62C50`.
- `phase4-reward-dossier.csv`:
  `868B95555B5C22FE63F1EAEB8C1C43703AF6FB23653A3FD9A36C853ADF30FFBC`.
- `manifest.json`:
  `8222817FA8465851119BDFF6251D21268CB586124B791E6A680186E7C741009C`.
- No se inició/reinició Zone, Docker, cliente o MySQL y no se aplicó ninguna
  migración.

Estado de puerta: **abierta**. No se declara Fase 4 completa hasta cerrar los
404 bloqueos y añadir un ledger
durable/atómico por act de recompensa para cubrir reintentos después de fallo o
reconexión sin duplicación ni pérdida.

#### Corte Fase 4B — preflight y ledger durable por acto (2026-08-20)

Implementado:

- Cada aceptación recibe un `RewardAttemptId` GUID persistido. Los payloads
  históricos de 5 y 10 objetivos siguen cargando y derivan un GUID determinista
  de owner/id/template; el reciclaje de `Quest.Id` ya no puede colisionar con
  una aceptación anterior.
- `quest_reward_ledger` reserva por `(attempt_id, act_id)` y conserva identidad
  de personaje, template, detail type/id y estado pending/completed. Completed
  es un éxito idempotente; pending, conflicto o DB no disponible bloquean de
  forma visible. Un fallo ordinario antes de aplicar libera la reserva.
- Antes de ejecutar el primer reward se hace preflight de todos los actos
  Fase 4 activos. Esto cierra la ejecución parcial causada por el acumulador
  booleano no cortocircuitado de `QuestStep`.
- Los 12 consumidores Fase 4 comparten una base sellada validate/reserve/mutate.
  Family, Resident, Faction y ArchePass positivo fallan en preflight, antes de
  que otro reward del mismo step pueda mutar estado.
- El cierre del ledger se alista en la transacción global de `SaveManager`,
  junto con mail, items, personaje y borrado/persistencia de quest. Los ranked
  items sólo se preparan durante el acto; errores reales de bolsa/backpack/mail
  ahora hacen fallar la distribución. Tras rollback, la marca se conserva para
  reintento en el siguiente save; una segunda pasada limpia sólo filas ya
  observadas como committed.
- Un corte entre una mutación externa ya confirmada (por ejemplo, expedition)
  y el save deja pending. Se bloquea y exige reconciliación explícita: no se
  afirma exactly-once distribuido ni se reotorga a ciegas.

Evidencia nativa adicional:

- Zone r575 `FUN_396d1200(zoneGroup:u16, character, servicePoint:s32)` mantiene
  un valor absoluto por personaje/zona y rechaza decrementos en su caller.
  Queda pendiente reconstruir elegibilidad, reset y persistencia del authority;
  `ResidentPoint` sigue bloqueado.
- `ResidentCharge` usa entradas normal+hunting, total zonal, puntos personales,
  total de puntos, member count y fórmula de dividendo. Sin el dueño del ciclo
  de settlement no es seguro mapear `charge` a una tabla parcial.
- Family exp confirma layouts y evento `FAMILY_EXP_ADD`, pero el binario Zone no
  demuestra el authority que persiste/muta familia. Sigue bloqueado.
- Upstream obligatorio y comparadores AA8/modern sólo contienen stubs/serializers
  para estas fronteras; no existe un port selectivo probado.

Validación:

- Build integral Release: 0 errores.
- Suite unitaria Release: 1.431 correctas, 0 fallidas, 0 omitidas.
- Stage 40 v5 registra `phase4_reward_ledger_present=1`; 993/1.397 refs siguen
  implementadas y 404 permanecen bloqueadas, ahora con clasificación nativa
  específica. Nuia conserva 0 actos habilitados sin clase/loader. Dos builds
  fueron idénticos: SQLite
  `9A9CC938C72B573402CC19DA1ED387B04EBB83EF4D0377CAF30F18FED2812CB7`,
  dossier Fase 4
  `825A10FC1370612B0725C08A8C26A76C11B79E27DF7D589B4A1A0ECD4858EC97`
  y manifest
  `BF81B5FA459064654B38D690C9BA0DED5D219830A19C799942B7BD931ED6FB53`.
- Migración actualizada pero no aplicada. No se inició/reinició Zone, Docker,
  cliente o MySQL.

Estado de puerta 4B: **cerrada satisfactoriamente**. La Fase 4 general permanece
abierta por los 404 actos cuya autoridad de dominio aún no está reconstruida.

#### Corte Fase 4C — núcleo persistente ArchePass y 325 rewards de puntos (2026-08-20)

Implementado:

- `ArchePassGameData` carga las 14 categorías, 97 pases y 3.028 tiers AA10.
  Valida categoría habilitada, vencimiento, catálogo continuo 1..maxTier,
  moneda/coste y upgrade item sin hardcodear un pase concreto.
- Se reconstruyó el ciclo por personaje invalid → buy/owned → start/progress →
  dropped/expired/completed, con una sola ranura owned/progress. Buy usa
  `TryPayCurrency`; premium consume el upgrade item configurado.
- Los seis campos del registro wire r575 quedaron semánticamente cerrados:
  `type`, `point`, `status`, `premium`, `lastRewardTier` y
  `lastPremiumRewardTier`. `SCArchePasses` pagina en bloques máximos de diez.
  No se inventaron reasons de `SCUpdateArchePass`: cada mutación resincroniza el
  estado completo paginado.
- Los claims normal/premium exigen el siguiente tier alcanzado, hacen preflight
  de bolsa, entregan el item retail y avanzan fronteras independientes. Los tiers
  sin reward se saltan; normal complete exige cap + frontera normal cerrada y
  premium se completa al cerrar ambos tracks.
- `QuestActSupplyArchePassPoint` ahora preflighta y acredita sólo un pase
  persistido en progress. Los puntos saturan en el umbral del último tier; las
  325 referencias quedan cubiertas por el ledger durable de 4B.
- `character_arche_passes` se guarda desde `Character.Save` en la misma
  transacción que items, quest y cierre de ledger. La migración
  `2026-08-20_aaemu_game_arche_pass_states.sql` está incluida también en el
  master schema, pero no fue aplicada.
- Si falta la tabla o la persistencia viola la ranura única, el manager falla
  cerrado y no banca puntos ni cobra/entrega rewards.

Frontera conservada:

- El cliente enumera configs 277–280 (`mission_complete_count`,
  `mission_change_count`, `mission_init_count`, `mission_init_item`), pero la
  SQLite retail contiene cero valores en `content_configs`. ChangeMission sigue
  rechazado, counters/bitsets de misión siguen en cero y
  `archePassMissionAccount` permanece apagado. Esto es deuda separada del núcleo
  de pase, no una regla suplida con defaults.
- Upstream obligatorio y comparadores AA8/modern sólo aportan shells; no existía
  una implementación transferible. La autoridad usada es AA10 r575.

Validación:

- Build integral Release: 0 errores. Suite unitaria Release: 1.437 correctas,
  0 fallidas y 0 omitidas.
- Stage 40 v6: 1.318/1.397 referencias Fase 4 implementadas, 79 bloqueadas
  (FactionChange 27, FamilyExp 10 y Resident 42), 0 candidatas. Nuia conserva
  0 actos habilitados sin clase/loader.
- Dos generaciones y el bundle canónico son idénticos byte a byte:
  `quest-stage40.sqlite3`
  `A02E22777482F5CFF93D0376611EA20B71170243BE4A667EA3B673D0625C9A9B`,
  `phase4-reward-dossier.csv`
  `15BD16EE291CA834063CE414FA4CB0EF94106ADAF4C272D39F34A03EAA59963E`
  y `manifest.json`
  `2C100B1E0E4D03A62A44D12347BBEEC54D8C6568D656A939202C58E478DD7146`.
- Dossier forense: `forensics/output/aa10-client-forensics/
  arche-pass-phase4c-frontier/CHECKPOINT.md`.
- No se inició/reinició Zone, Docker, cliente o MySQL; no se aplicó la migración
  ni se modificaron `.env`, compact retail, `game_pak` o SQLite autoritativa.

Estado de puerta 4C: **cerrada satisfactoriamente para el núcleo ArchePass y los
325 rewards de puntos**. La Fase 4 general continúa abierta por 79 rewards de
Faction/Family/Resident; la misión/reroll ArchePass queda como frontera de
LiveOps separada hasta obtener valores autoritativos.

#### Corte final Fase 4 — Family, Resident y Faction (2026-08-20)

Implementado:

- Las 79 referencias restantes quedan cerradas: FactionChange 27, FamilyExp 10,
  ResidentPoint 41 y ResidentCharge 1. Los cuatro tipos pasan por el preflight y
  ledger durable comunes antes de mutar estado.
- Family usa nivel/exp retail persistente, satura en nivel 3 y envía el ID del
  personaje contribuyente en el `u64` nativo de `SCFamilyExpChangeNotify`.
  `SCFamilyInfoSet` resincroniza la familia al login.
- Resident persiste puntos por personaje/zona y fondos normal/hunting por zona.
  Las consultas cliente responden sólo para el personaje activo con punto
  personal, member count, total zonal y ambos fondos. El reward de charge suma
  al fondo normal y conserva hunting.
- Faction ID 0 se resuelve con el template racial. Los targets 199/200 respetan
  su mother faction; una expedición incompatible se abandona antes de cambiar
  facción y se actualizan housing/doodads después.
- Se corrigió `SCDropQuestsByFactionChange` a su layout r575 real: flag final,
  count y lotes de hasta 20 quest IDs. No se inventó el productor que selecciona
  qué quests activas descartar.
- `family_progress`, `resident_service_points` y `resident_zone_balances` están
  tanto en la migración de progreso de quest como en el master schema. La
  migración no fue aplicada al runtime activo.

Fronteras separadas conservadas:

- El reset/settlement/dividendo residencial no forma parte del consumidor de
  reward y permanece sin defaults inventados.
- El selector de quests a descartar después de cambiar facción queda pendiente
  de su autoridad propia; el cambio de facción authored sí está cerrado.
- Las misiones/rerolls ArchePass siguen fuera del núcleo Fase 4C por ausencia de
  valores retail en `content_configs`.

Validación final:

- Restore correcto y build integral Release con 0 errores.
- Suite completa: 1.441 correctas, 0 fallidas y 0 omitidas.
- Stage 40 v7: 1.397/1.397 refs Fase 4 implementadas, 0 bloqueadas y 0
  candidatas. Nuia mantiene 55 quests, 344 actos y 0 actos habilitados sin
  soporte.
- Dos generaciones son idénticas byte a byte: SQLite
  `0964BB4BC551ED444F3DE944FF37845C6C55B154279EFB879CE89EC258548464`,
  dossier Fase 4
  `872CD19F5096E9A00BBF1DCFB2E152A973F9EAEF0068D799E54F09CDDADDCC5B`
  y manifest
  `960DA7D7E9DA8768805F4C02487B786484C90249269D57955164E88A8C937980`.
- Dossier forense: `forensics/output/aa10-client-forensics/
  quest-phase4-close-frontier/CHECKPOINT.md`.
- No se inició/reinició Docker, Game, Login, Zone, cliente o MySQL; no se
  aplicaron migraciones ni se modificaron `.env`, compact, `game_pak` o SQLite
  fuente.

Estado de puerta Fase 4: **cerrada satisfactoriamente**. El alcance cerrado es
el de consumidores de recompensa AA10; las fronteras explícitas anteriores se
mantienen como subsistemas posteriores y no reducen la cobertura 1.397/1.397.

### Fase 5 — validador de cobertura obligatorio (completada)

Convertir Stage 40 en gate de CI/runtime de datos: acto habilitado sin clase,
loader, detalle, productor o consumer debe fallar de forma visible. Mantener un
modo de informe durante la reconstrucción; el modo estricto sólo se activa cuando
la matriz llega a cero para no impedir el arranque con deuda conocida.

Puerta: cero drops silenciosos y cero referencias no clasificadas.

Resultado aplicado:

- Stage 40 v8 admite `--mode report|strict`, emite `strict-gate.json` y falla con
  exit code no cero en estricto ante cualquier acto habilitado sin clase,
  loader, tabla/fila de detalle, productor Fase 3 o consumer Fase 4. También
  exige cero bindings duplicados, huérfanos y referencias Nuia sin soporte.
- Se eliminó el detector impreciso de cualquier `return true`: una condición o
  recompensa puede terminar legítimamente en éxito después de validar o mutar.
  El gate identifica stubs reales por delegación a `base.RunAct` y por la matriz
  explícita de contratos.
- La matriz autoritativa queda en 86 tipos, 43.737 referencias habilitadas,
  43.737 implementadas, 0 sin clasificar, 0 tablas o filas de detalle ausentes y
  0 bindings runtime duplicados. Fase 3 conserva 649/649 productores y Fase 4
  1.397/1.397 consumers; Nuia conserva 55 quests, 344 actos y 0 habilitados sin
  soporte.
- El runtime valida las 43.696 referencias habilitadas materializables (se
  excluyen únicamente contextos tutoriales categoría 45 ya omitidos por diseño)
  después de todos los loaders y antes de publicar las quests. `Report` registra
  cada hallazgo y continúa; `Strict` lanza `InvalidDataException`. El default
  versionado es `Strict` en `Configurations/QuestCoverage.json`.
- Se cerraron los dos stubs reales encontrados al retirar los falsos positivos:
  `QuestActEtcItemObtain` (79 refs) cuenta sólo adquisiciones positivas ocurridas
  después de aceptar y no disminuye al consumir el item;
  `QuestActSupplySkill` (2 refs) ejecuta la skill oculta AA10 sobre el dueño y
  usa el mismo preflight/ledger durable de recompensas. Las skills retail 38440
  y 46452 son efectos inmediatos (pericia de ganadería y buff de notificación),
  no habilidades visibles para aprender.
- CI usa una instantánea versionada de los 86 tipos/contadores porque las SQLite
  y DLL retail no pertenecen al checkout. El job verifica clases, loaders,
  stubs, productores, consumers, ledger, invocación runtime y default estricto;
  corre en push de `rama_10` y en pull requests. La regeneración full-authority
  sigue verificando hashes de las cuatro entradas fuera del repositorio.
- Pruebas negativas: clase, loader, detalle, binding, stub, productor y modo
  estricto ausentes producen hallazgo/fallo; los actos nativamente deshabilitados
  se ignoran de forma explícita. Suite Python: 8 correctas. Suite .NET completa:
  1.449 correctas, 0 fallidas y 0 omitidas; integración Login: 6 correctas,
  0 fallidas y 0 omitidas.
- Dos generaciones estrictas independientes son idénticas en sus nueve
  artefactos. Hashes: SQLite
  `710863737311B403E72002F8209BBC4688F4C229076B94F6D96DD1477DF37F3C`,
  `strict-gate.json`
  `2584985B81DADB7245A7CF2FC698D8895AEE100C446DE91DE3EFA366057F46FD`
  y manifest
  `2B17D0BFDFFCAEF3E2D3F708DF035B041F2D55CC87E92E178C6C955CAC36604F`.
- Dossier: `forensics/output/aa10-client-forensics/
  quest-phase5-close-frontier/CHECKPOINT.md`.
- No se inició/reinició Docker, Game, Login, Zone, cliente o MySQL; no se
  aplicaron migraciones ni se modificaron `.env`, compact, `game_pak` o SQLite
  fuente.

Estado de puerta Fase 5: **cerrada satisfactoriamente**. El siguiente paso es la
Fase 6 E2E Nuia, que conserva su requisito de autorización explícita de lifecycle.

### Fase 6 — validación E2E de raza Nuia

Con autorización explícita de lifecycle: restaurar/build, iniciar stack, capturar
logs y recorrer desde quest 6839 por capítulos. Verificar sphere 2321, NPC,
doodads, cinemas, items y cambios de zona. Para capítulo 6, adquirir la partición
AA10 exacta o demostrar mediante binario/captura que 133/149 se resuelven por otra
ruta; no fabricar contenido.

Puerta final: cadena completa repetible desde personaje nuevo, reconexión y
persistencia incluidas, con captura/log por transición y sin intervención GM.

#### Corte operativo Fase 6 — runtime y primera transición (2026-08-20)

Estado: **E2E manual en curso; puerta todavía abierta**.

- Se respaldó `aaemu_game` antes de aplicar las migraciones en
  `backups/quests/phase6-20260820-140837/`. El dump comprimido pasó `gzip -t` y
  su SHA-256 es
  `B98A6E1354F439E2B67277EF169149E4B8B8B08363D144318D4D43501C4316B7`.
- Se aplicaron las tres migraciones versionadas de progreso/reward, ArchePass y
  faction competition. Las ocho tablas esperadas existen y el estado inicial
  del personaje de prueba no fue adelantado por SQL.
- Login y Game fueron reconstruidos. El arranque runtime cargó 8.901 quests,
  2.632 spheres en 103 zones y cerró el gate `Strict` con 43.696 actos
  materializables y cero hallazgos.
- El arranque real reveló y corrigió dos incompatibilidades de esquema AA10:
  faction competition usa `context_id`, no `quest_id`; los objetivos de exp,
  honor y living point sólo tienen `id` y `point`, sin columnas de alias.
  Ambos loaders reutilizan ahora helpers cubiertos por pruebas de esquema.
- La suite unitaria después de ambas correcciones quedó en 1.451 correctas,
  0 fallidas y 0 omitidas; integración Login quedó en 6/6 y el gate Python en
  8/8. El build integral terminó con 0 errores.
- La única prueba del proyecto `AAEmu.IntegrationTests` no es autocontenida: al
  ejecutar la solución fuente sin materializar el template intenta convertir
  `%db_port%` a `UInt16` y falla antes de probar QuestManager. El runtime
  desplegado sí tiene configuración materializada y arrancó correctamente; este
  requisito de fixture se conserva explícito y no se cuenta como regresión de
  quests.
- La partición inicial se resolvió como `zones.id=125 -> w_solzreed_3 ->
  zone_key=179`. El Zone exacto cargó con `ZWJoin`, `WZJoinResponse`,
  `ZoneLoaded 179`, TCP 1240 y heartbeat estable.
- Se corrigió la evidencia Stage 40: las particiones 133 y 149 no están
  ausentes. Ambas existen en el `game_pak` r575 con spawners nativos exactos;
  no se modificó el paquete fuente.
- El Nuia nuevo `Dannia` (id 7) entró sin GM. Los logs demuestran sphere 2321,
  inicio de quest 6839, cinema 163 iniciada/completada, rewards authored y
  `SCQuestContextCompletedPacket`. La siguiente quest racial es 330 en Lucius
  Quinto (NPC 3597).
- A petición del usuario se retiró todo control automatizado del PC. La
  travesía restante se ejecuta manualmente por el usuario. El protocolo y el
  capturador read-only están en `Docs/AA10QuestPhase6E2E_es.md` y
  `Scripts/CaptureAa10QuestPhase6Evidence.ps1`.
- Stage 40 estricto se regeneró dos veces y los nueve artefactos fueron
  idénticos byte a byte. Hashes: SQLite
  `96EB3A2A9B97A3944C9D373080F29BEB6FA30C0B6731265C39BD51E63034EAC7`,
  crosswalk Nuia
  `2C724CB70126A5513F4B14D589F9BFA357C37E240C51C5E1C5ED7A1D60BA3D54`,
  gate estricto
  `2584985B81DADB7245A7CF2FC698D8895AEE100C446DE91DE3EFA366057F46FD`
  y manifest
  `1B1FC52082CDFD6E094208FCE204D303C84B113B067BA9E417E142B544DD376E`.
- Dossier de frontera:
  `forensics/output/aa10-client-forensics/quest-phase6-runtime-frontier/CHECKPOINT.md`.

No se marcará la Fase 6 como cerrada hasta demostrar capítulos 1–6, relog,
persistencia y repetición desde otro Nuia nuevo. No se usarán comandos GM ni
mutaciones SQL para satisfacer la puerta.

#### Incidente 2532 — tercer corte dinámico

- La versión con resincronización en `CSNotifySubZone(id)` fue desplegada y
  probada manualmente. Los updates `Ready -> Ready` llegaron después de los
  enters 328/639, pero Marian 14074 no apareció y el cliente no envió `0x137`.
- La decompilación read-only del `x2game.dll` r575 exacto cerró la semántica del
  paquete: `FUN_39424f00` envía el ID al entrar y `FUN_39424ff0` envía
  `DAT_3b0ab214=0` al salir. La captura contenía tres salidas `0x165` que el
  handler descartó por su retorno temprano.
- El operador abandonó y aceptó 2532 desde cero antes del tercer intento. La
  reproducción idéntica descarta un contexto persistido obsoleto.
- La extracción exacta de `game_pak` confirmó 4500 y 14074 en
  `cells/014_014/doodad.g`; Marian está a unos 4,5 m del monolito. Los cuatro
  compact comparados contienen las mismas fases 41495/41496 y QuestReact 632.
- `FUN_3933e0a0` -> `FUN_396b2850` -> `FUN_390f0330` demuestra que
  `Ready -> Ready` sí reevalúa callbacks QuestReact ya registrados. Los pulsos
  inmediatos de enter y leave fallaron por estar respectivamente antes y
  después de la ventana de registro.
- AAEmu conserva `SubZoneId` y Portals sólo para IDs no cero. Ahora agenda una
  resincronización única 3 s después de la entrada no-cero vigente; una entrada
  posterior la invalida y el sentinel cero no dispara ni cancela. Se añadieron
  regresiones para entrada vigente, entrada obsoleta y sentinel cero.
- Corte validado el 2026-08-20: restore correcto, build integral Release con
  cero errores y suite .NET 1.455/1.455. La imagen desplegada es
  `sha256:f2193b47858fab8bf0b21e50bab55033fd6df658a746e1f2ad8b077dc63873f1`;
  `AAEmu.Game.dll` tiene SHA-256
  `a03767bf58484698a15a9ea872d03906e9517f669f8895cd4cdaa8071538535f`.
  Se recreó únicamente `Game`; `db`, `login` y `game` quedaron healthy, los
  puertos 1239/1240/1250 escuchando y Game se registró de nuevo en Login.
- Rollback inmediato preservado como
  `aaemu-world:10.0.2.13-r575-local-rollback-20260820-194133`, imagen
  `sha256:efa0cfbf65f10f8653721eeeec0bdd42ef0e11950216a2a42fa5661543a5a5fe`.
- La puerta visual permanece abierta hasta ver a Marian tras esperar 3 s en la
  subzona, recibir `CSDoodadQuestNoti` para template 14074 y completar 2532 sin
  GM ni spawn sintético.

#### Incidente 2532 — cuarto corte dinámico

- La prueba manual limpia con el pulso diferido desplegado confirmó la entrada
  de subzona y `Ready -> Ready` exactamente tres segundos después, pero Marian
  continuó ausente. Quedan refutados timing, distancia y estado persistido.
- La autoridad AA10 clasifica el bit 90 (`fset[11] & 0x04`) como lookup nativo
  de descriptores de doodad. Estaba definido como `fset_11_2_unknown` pero
  apagado tanto en el baseline como en el perfil Docker, impidiendo que el
  doodad cliente 14074 se materializara y registrara QuestReact 632.
- Se habilitó el bit sin crear spawn/NPC sintético ni modificar compact o
  `game_pak`. El byte 11 cambia de `0x98` a `0x9c`; una regresión fija su
  posición exacta y otra fija el blob de configuración completo.
- Restore y build integral Release cerraron sin errores; unitarias 1.457/1.457,
  integración Login 6/6 y Stage 40 CI 43.737 referencias con cero hallazgos.
- Se recreó únicamente Game. La imagen activa es
  `sha256:463b4795b3b14c435e2462b217f483cb00f1da158e78af0c5a73aa0446162bac`;
  el runtime confirmó `fset ... 9c ...`, gate Strict 43.696/0, registro en Login
  y puertos 1239/1240/1250. Rollback:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260820-203851` ->
  `sha256:f2193b47858fab8bf0b21e50bab55033fd6df658a746e1f2ad8b077dc63873f1`.
- La puerta visual continúa abierta hasta reiniciar completamente el cliente
  para recibir el nuevo `SCInitialConfig`, relanzar los Zone bajo control del
  operador y completar 2532 manualmente desde una aceptación limpia.

#### Incidente 2532 — quinto corte, proxy NPC corroborado por AA8

- La distribución AA8 tenía el mismo defecto exacto y su checkpoint nativo
  demuestra la representación `doodad 14074 -> npctype://10581`, con el spawn
  histórico 8182/NPC 10581 usado únicamente como transportador de posición.
- AA10 corroboró la estructura sin heredar datos: el `game_pak` r575 coloca
  14074 en `(15036.458,14739.861,150.425)`; el full DB define la relación de
  NPC 10581 con spawner 11749, pero ese spawner no aparece en ningún
  `npc_spawners.g` del Zone r575. Por tanto, Zone no emite el actor.
- El full DB marca 14074 como `client_doodad`; el grupo Start 41495 no aporta
  el modelo NPC y el Normal 41496 contiene `npctype://10581`. El loader AA10
  omitía `doodad_func_groups.model` y el selector elegía siempre Start.
- Se implementó una primitiva genérica: cargar `model`, detectar grupos
  `npctype://` sólo en templates `client_doodad`, preferir Normal y usar Start
  como fallback. Cuatro regresiones fijan las rutas Normal, fallback Start,
  doodad ordinario y client doodad sin proxy.
- La colocación AA10 exacta se publica como datos en
  `doodad_spawns_aa10_client_quest_proxies.json`, tanto en el árbol fuente como
  en el bind mount Docker. No hay hardcode de quest/NPC en la lógica y no se
  modifica compact, `game_pak`, SQLite ni Zone.
- Validación cerrada: build integral con 0 errores, unitarias 1.461/1.461,
  integración Login 6/6, gate Python 8/8 y Stage 40 full-authority Strict con
  43.737/43.737 referencias, 43.696 materializables y cero hallazgos.
- Se desplegó únicamente Game con imagen
  `sha256:1debea5a952eade6c8fd8b6c673a6d5f3a533bb938040995795194c9fbd77a6e`.
  El runtime cargó 42.611 doodads, conservó fset byte 11 `0x9c`, cerró Strict
  43.696/0 y se registró en Login. `db`, `login` y `game` quedaron healthy.
  Rollback:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260820-214806` ->
  `sha256:463b4795b3b14c435e2462b217f483cb00f1da158e78af0c5a73aa0446162bac`.
- No se inició, detuvo ni reinició Zone ni se controló el cliente.
- La puerta visual sigue abierta hasta que el operador relance Zone 179,
  reinicie el cliente y confirme aparición, interacción y entrega de 2532.

#### Incidente 2532 — sexto corte, handoff hacia quest 2255

- La prueba manual cerró aparición e interacción: Marian 14074/10581 fue
  visible y permitió entregar 2532. La base persistió su bit completado y quitó
  2532 de activas; 2255 no estaba activa ni completada.
- La interacción siguiente reabrió el diálogo de 2532. El grupo AA10 41496
  contiene cuatro wrappers `DoodadFuncQuest` sin skill propia, pero las rutas
  `GiveQuest`/`CompleteQuest` usaban `Doodad.Use`, que elegía el primero. Además,
  `DoodadFuncQuest.Use` trataba toda quest ausente como oferta sin considerar
  kind, completado ni repetibilidad.
- Se añadió una primitiva genérica `Doodad.UseQuest`: enumera todos los wrappers
  de la fase, filtra kind 1/2 y selecciona según quest activa, completada y
  repetible. `DoodadFuncQuest` repite la elegibilidad como defensa. En la cadena
  exacta AA10 esto descarta 2532 y selecciona 2255 (`The Golden Mark`). AA8 sólo
  corroboró la forma de la primitiva.
- Evidencia visual: Marian visible
  `BC62874C5E10B55B1331DF6DD9F754CF5B7E9776C6832B22BA83A19DE27AF624`;
  diálogo 2532 repetido
  `F59E90BECAFFA7DCBFBB45CEEF886D0832B9FF863FB195EC1C7E541783737FB0`.
- Validación: solución Release con cero errores, unitarias 1.466/1.466,
  integración Login 6/6, gate Python 8/8 y runtime Strict 43.696/0.
- Se desplegó únicamente Game con imagen integrada
  `sha256:67faf05dce381d331658927836f71c6949d5df52bb1ca562e018a4b699c6da20`;
  DLL Game
  `91A84F95FC9D946E113D899C8C31FD3737925F187EE486E5DE0EFDAD5986E356`.
  `db`, `login` y `game` quedaron healthy, 1239/1240/1250 escuchando y Game
  registrado en Login. Rollback:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260821-064835` ->
  `sha256:1debea5a952eade6c8fd8b6c673a6d5f3a533bb938040995795194c9fbd77a6e`.
- Un recreate transitorio omitió el override AA10, falló por ausencia de client
  worlds y fue reemplazado antes de servir por la topología `aaemu-world`
  integrada. No hubo migraciones ni mutaciones de progreso.
- No se inició, detuvo ni reinició Zone ni se controló el cliente. La siguiente
  puerta manual es relanzar Zone 179/cliente y confirmar que Marian ofrece 2255.

#### Incidente 2256 — séptimo corte, sincronización de sucesión e items

- La prueba manual completó 2255 de extremo a extremo, incluidos suministro
  16280 y reward 18792. Marian abrió el diálogo de 2256, pero el cliente nunca
  mostró Aceptar ni envió `CSStartQuestContextPacket`.
- 2256 no entrega items al aceptar: su item 18791 x5 pertenece al reward 10366.
  El start 10362 depende de `CompleteQuestContext(2255)`, completado en reward
  component 9946.
- `SCQuestContextCompletedPacket` AA10 mantiene quest id + component id. El
  runtime descartaba el componente y enviaba cero, dejando la dependencia viva
  sólo después de un nuevo login. Se preserva y emite el componente real antes
  de `DropQuest`.
- La captura del diálogo sin Aceptar tiene SHA-256
  `9298FFA041AD1E29FCF802C336475C4F931830849D1B1B4CF10161763D8C975D`.
- La auditoría completa cubrió 6.434 referencias enabled que materializan
  items. Sólo dos referencias rotas pertenecen a quests test category 55;
  existe un count cero authored en quest 3782. Cantidad cero o ya satisfecha se
  trata ahora como no-op exitoso, sin crear un item de count cero.
- Dossier:
  `forensics/output/aa10-client-forensics/quest-phase6-item-supply-cut7/`;
  auditor reproducible:
  `reconstruccion_cliente_10/scripts/audit_quest_item_supply.py`.
- Validación: build Release sin errores, unitarias 1.471/1.471, Login 6/6,
  gate Python 8/8 y runtime Strict 43.696/0.
- Se desplegó únicamente `game` con ambos compose e imagen integrada
  `sha256:df6b9af8078e693f36d001e4f735c3215cfde545a826f3fa1e9b1862a63ff8b5`;
  DLL Game
  `750B52298F5CC4D395C15536DB22CB6D046221C1EB13DD4DDB1E861A667213D8`.
  `db`, `login` y `game` quedaron healthy, 1239/1240/1250 escuchando y Game
  registrado en Login. Rollback:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260821-075742` ->
  `sha256:67faf05dce381d331658927836f71c6949d5df52bb1ca562e018a4b699c6da20`.
- El recreate de World/Game cerró la conexión del Zone que seguía abierto. No
  se inició, detuvo ni relanzó Zone ni se controló el cliente.

#### Incidente 2256 — octavo corte, hard cap de apertura del mundo

- La acción en `G` apareció de forma transitoria y fue reemplazada por
  `Kick Immediately`; captura SHA-256
  `66D8780B6FBC3DBFBD0B56010E70498D3EC2FEDE1AA566A13289060DC29AB264`.
  Game envió `SCDoodadQuestAcceptPacket`, pero el cliente no devolvió
  `CSStartQuestContextPacket`.
- `Kick Immediately` es la localización inglesa defectuosa de
  `ui_texts.id=12213`, `world_level_hard_cap`: el texto original indica que se
  alcanzó el nivel límite y no puede aceptarse una misión principal.
- Dannia estaba en nivel 28. `world_level_hard_caps` impide nuevas quests en
  días 0–1 al nivel 28 (`get_quest=false`) y sólo habilita `get_quest=true`
  desde el día 9, con hard cap 55. El item 18791 x5 de 2256 sigue siendo reward
  final, no suministro de aceptación.
- La ruta nativa quedó probada en `x2game.dll`:
  `GetWorldLevelHardCapInfo`/`FUN_39850220` calcula los días desde el tiempo de
  apertura guardado en `ClientPlayer+16000` y selecciona hard cap,
  `expModifier` y `get_quest`; `GetServerOpenTime`/`FUN_3984afb0` lee el mismo
  campo e `IsWorldLevelEnabled`/`FUN_3984adf0` gobierna la mecánica.
- `SCServerInfoPacket` enviaba el reloj actual como apertura en cada conexión,
  reiniciando el mundo a día cero para el cliente. Se sustituyó por
  `InitialConfig.ServerOpenTimeUnixSeconds`, configurado tanto en la copia
  distribuida como en la montada a `1782403200` (`2026-06-25 16:00:00 UTC`),
  el timestamp exacto de la captura original. Hay tests del wire little-endian
  `80503D6A00000000` y de la configuración distribuida.
- Validación: build Release sin errores, unitarias 1.473/1.473, Login 6/6,
  Stage 40 sin hallazgos y runtime Strict 43.696/0 con 8.901 quests.
- Se desplegó únicamente `game` con ambos compose. Imagen activa
  `sha256:c2effa60a1de6b5e9a87c5705fad6225f31a8dbbf205501d63de24d50cd45487`;
  DLL Game
  `6460E91FBC45F38679872BFD7268C8DF69C6E8EE6647AED2788384E9D3AB0548`.
  Rollback:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260821-082340` ->
  `sha256:df6b9af8078e693f36d001e4f735c3215cfde545a826f3fa1e9b1862a63ff8b5`.
  `db`, `login` y `game` quedaron healthy, 1239/1240/1250 escuchando y Game
  registrado en Login.
- `SCServerInfoPacket` se consume al reconectar desde lobby. El recreate de
  Game cerró la conexión Zone existente; no se inició, detuvo ni relanzó Zone
  ni se controló el cliente.

## Límites de este checkpoint

- Fases 0 y 1 no autorizan iniciar, detener o reiniciar Zone, Docker, cliente o
  MySQL.
- No se modifica `.env`, compact retail, `game_pak` ni la SQLite autoritativa.
- AA8 se usa sólo como corroboración estructural (por ejemplo, capacidad interna
  de diez); toda semántica se decide con evidencia AA10.
- No se publica ni se crea commit remoto en este corte.
