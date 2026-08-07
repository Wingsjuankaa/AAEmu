# Checkpoint Archery executable V2

Fecha: 2026-08-07

> Nota de continuidad: el runtime V2 fue sustituido por V3 al cerrar las 356
> relaciones AA8 `tagged_skills` que consume el cache servidor. El codigo y
> los contratos ejecutables de este checkpoint permanecen vigentes; mount,
> hashes, auditoria y despliegue actuales estan en
> `CHECKPOINT_ARCHERY_TAG_CLOSURE_V3.md`.

## Resultado

La aplicacion de la guia Sorcery cerro cinco contratos ejecutables que la
primera clausura de datos Archery no detectaba:

1. `plot_conditions.kind_id=18` (`casting_useable`) ahora selecciona la rama
   segun porcentaje real de carga y `CSStopCasting` libera en vez de cancelar;
2. `plot_conditions.kind_id=20` carga requisitos owner-keyed desde AA8;
3. `unit_reqs` kind 26 evalua target HP estrictamente menor que el porcentaje;
4. SpecialEffect CombatDice materializa un unico resultado por target;
5. buff triggers Landing y RemoveOnMove se emiten antes de retirar el buff.

## Evidencia AA8 nueva

El cached result `unit_reqs` fue recuperado desde
`E:\AAEmu-Research\output\compact-8.0-extracted\game11`:

- SHA-256
  `E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031`;
- offsets `0x828B2C..0x87EC3C`;
- 13.053 filas, layout `78 68 38 68 68 68 68`;
- fila exacta `PlotCondition,14753,1,26,1,30,0`.

Esta fila gobierna Snipe: Flame `41221`: la rama condicionada solo pasa bajo
30% HP. AA10 r575 se uso para nombrar el enum, no como fuente runtime.

Las bandas kind 18 se demostraron en AA8:

- Concussive Arrow: Flame `36470`, plot 2928, 4000 ms, cinco bandas de 25%;
- Snipe: Lightning `41219`, plot 4046, 5000 ms, cinco bandas de 20% mas 100%.

## Artefactos

- extractor reusable:
  `shared_primitives/extract_native_unit_requirements.py`;
- prueba del extractor:
  `shared_primitives/test_native_unit_requirements.py`;
- constructor actualizado: `build_archery_runtime_v1.py`;
- runtime promovido:
  `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-archery-v2.sqlite3`;
- SHA-256:
  `E0724C6A0EA3713B185F94B9BA91499BED6848DB75E30EF8405B1BB74C1E7ADC`;
- manifiesto:
  `generated/archery-runtime-v2.manifest.json`.

El runtime contiene 4.639 filas AA8 materializadas en esta capa, cero filas
runtime AA10, `quick_check=ok` e `integrity_check=ok`.

## Verificacion

- extractor AA8: 1/1;
- runtime Archery: 14/14;
- condiciones/requisitos/casteo/eventos focales: 66/66;
- suite completa Docker SDK 3.1.409: 565/565.

La prueba numero 13 fija el dominio ejecutable completo de los 18 plots de
Archery: condiciones `5,6,8,9,11,12,16,18,20`, metodos de source `1,3,4` y
metodos de target `1,2,4,5,6,7`. Todos tienen consumidor servidor; un cambio
futuro en la compact que introduzca un tipo nuevo falla antes del despliegue.

La auditoria complementaria de la clausura confirmo que los triggers de buff
alcanzables son `Damage(6)`, `Landing(11)`, `Started(12)` y
`RemoveOnMove(13)`, todos suscritos. Los `actual_type` alcanzables se limitan
a dano, aggro, buff, dispel, bubble, controller y special effect, todos
cargables. `ResetCooldown` conserva `value7=100`, por lo que el consumidor
actual no pierde una rama probabilistica en Archery.

La prueba numero 14 fija tambien la frontera exacta de las pasivas: AA8 tiene
dos modificadores de unidad directos (`486 -> attribute 10/value 80` y
`7564 -> attribute 82/value 90`) y un modificador de skill
(`889 -> tag 3750/attribute 10/value 10%`). No se sintetizaron relaciones
para 480, 888 o 7565; sus contratos restantes dependen de tags/consumidores y
se conservan como casos vivos, no como balance deducido desde el tooltip.

## Auditoria semantica dirigida

El walker reusable de Sorcery ahora recibe `ABILITY_ID` y se aplico sin una
segunda implementacion del algoritmo a las 35 entradas Archery. Parte de 12
activas, 12 sucesoras, tres filas de login y ocho internas/contextuales;
expande plots, Combo/SkillUse, buffs, ticks, triggers y controllers.

- auditor: `audit_archery_executable_semantics_v1.py`;
- regresiones originales: `test_archery_executable_semantics_v1.py`, 6/6;
- JSON: `generated/archery-executable-semantics-audit-v1.json`, SHA-256
  `387827DF14DBE59DEA890C8BD93C34FFD935621206DF1CF5E639BFB6C74BE325`;
- CSV: `generated/archery-executable-semantics-matrix-v1.csv`, SHA-256
  `07D9243A1362F067A9832345FFF5CCC93D8FF5CC409558FAA9146C93430572BD`.

Resultado: 35/35 raices, seis pasivas, cero filas ausentes, cero subtipos
especiales bloqueados, cero unknowns externos y cero blockers estaticos. El
auditor tambien fija que los seis `ResetCooldown` de Intensity llevan
`value7=100`; por tanto su cola extendida es determinista y no abre un hueco
probabilistico.

## Frontera de aceptacion viva

Este checkpoint es `automatic_verified`, no `live_accepted`. La matriz debe
probar una fila por vez y revisar la traza:

- `[AA8SkillCastRelease]` para 36470 y 41219;
- `[AA8SkillDamage] tree=archery` con amount positivo y HP decreciente;
- Snipe: Flame a 29% y 30% HP para fijar el limite estricto;
- Deadeye quieto y luego movimiento para RemoveOnMove;
- Concussive Arrow sobre jugador/mob que aterrice para Landing;
- cero desconexiones y cero reinicios Game.

SpecialEffect Detach y RemoveDoodad permanecen clasificados como presentacion
/ limpieza cliente hasta que una prueba viva demuestre una mutacion servidora
ausente. No se implementaron de forma especulativa.

La aceptacion de pasivas ya no depende del icono cliente. `CharacterSkills`
emite snapshots antes y despues de aplicar o retirar cada una de las seis
pasivas mediante `[AA8ArcheryPassive]`. La linea contiene las estadisticas
servidoras de movimiento, accuracy/critico/dano ranged y tres probes de
modificadores sobre Endless Arrows y Concussive Arrow. El resumidor agrupa
estas lineas por personaje, passive y buff, y enumera los campos que realmente
cambiaron en cada transicion. Es instrumentacion observacional: no altera
formulas, buffs ni modificadores.

## Despliegue

- imagen Game: `sha256:0a647c2e16376e1ec1bfabe3c182afdb2d69280eb1fd973740242c4012064453`;
- contenedor Game: `330328c89b6f286e8d0ad6833795c5b0fcc4f6808bb632b74c0f5b4f182e61eb`;
- mount: `compact-8.0-runtime-archery-v2.sqlite3 -> /app/Data/compact.sqlite3`;
- rollback: `aaemu-game:rollback-pre-archery-executable-v2-20260807`, imagen
  `sha256:830ae0be2c3014b3bbc4b06c817bf9b86df607cfa1445793141024bb32697af5`;
- Game registrado una vez en Login, puertos 2239/2250 accesibles, cero fatal
  y `RestartCount=0`;
- Login y MySQL conservaron IDs y horas de inicio.

El baseline posterior al despliegue es
`runtime-captures/native-skill-live-baseline-v3.json`, SHA-256
`5EBF02236694AA5E8B961577196078DFEE4AE2F616A5C31CFCB87F7C746F123B`.
Registra un unico error no fatal de arranque en `TransferManager.GetTransfers`
(copia concurrente del diccionario mientras cargan transfers), anterior a
cualquier prueba de skills. Se separa como ruido de infraestructura: no hubo
reinicio, no impidio el registro y no cuenta como evidencia A1-A5.

Este baseline y mount son historicos. V3 arranco sin ese error y usa
`runtime-captures/native-skill-live-baseline-v4.json`.
