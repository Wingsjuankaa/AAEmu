# AA8 Client Forensics

## Dossiers transversales reutilizables

La consolidada puede convertirse en una clausura acotada y reproducible para
cualquier entidad. El motor no contiene una ruta especial para una quest: toma
una raiz `(kind, native_id)`, recorre el mismo grafo canonico y aplica un perfil
de relaciones declarado en `config/closure-profiles.json`.

```powershell
python -B -m client_forensics explain-closure quest 330
python -B -m client_forensics export-dossier quest 330
python -B -m client_forensics export-dossier item 51185
python -B -m client_forensics export-dossier skill 46956
python -B -m client_forensics export-dossier npc 1234 --profile generic
```

`export-dossier` escribe por defecto dos artefactos fuera de Git:

```text
E:/AAEmu-Research/output/aa8-client-forensics/dossiers/<kind>-<id>.json
E:/AAEmu-Research/output/aa8-client-forensics/dossiers/<kind>-<id>.html
```

El JSON `AA8_RECONSTRUCTION_DOSSIER_V1` es el contrato para una IA o una
herramienta posterior. Contiene nodos, aristas con direccion nativa, paths,
propiedades, localizaciones, cobertura, gaps, blocker roots, corroboracion
wiki, limites del recorrido y la identidad SHA-256 de la consolidada y del
perfil usados. El HTML es autocontenido: permite buscar, filtrar, navegar el
grafo SVG e inspeccionar la evidencia de cada nodo sin red ni servidor.

Los perfiles `quest`, `item` y `skill` heredan de `generic`. Para incorporar
otra familia se agrega un perfil al JSON y reglas ordenadas por precedencia:

```json
{
  "npc": {
    "extends": "generic",
    "rules": [
      {
        "name": "npc-model-required",
        "current_kind": "npc",
        "direction": "outgoing",
        "relation": "references_model",
        "neighbor_kind": "model",
        "action": "expand",
        "importance": "required"
      }
    ]
  }
}
```

Las acciones son `expand`, `terminal` o `skip`; la importancia puede ser
`required`, `structural` o `contextual`. Una regla nunca crea una relacion:
solo controla el recorrido de aristas ya demostradas. Las relaciones opacas se
incluyen como limites y bloqueos, no se completan por heuristica.

Los estados de readiness tienen dos planos separados. `forensic` determina si
la clausura nativa del perfil esta cerrada. `reconstruction` conserva las
auditorias posteriores de backend, protocolo, persistencia, pruebas y
aceptacion. Un gap visual de assets se conserva como auditoria de presentacion,
pero no se confunde con una ausencia de comportamiento.

Núcleo transversal para representar de forma reproducible el conocimiento
extraído del cliente Kakao `8.0.3.12 r558734`.

Este directorio contiene únicamente herramientas forenses. No modifica AAEmu,
compacts runtime, `.env`, MySQL ni Docker.

## Etapas disponibles

```text
stage-00-artifacts.sqlite
stage-10-native-data.sqlite
stage-20-items.sqlite
stage-30-world-actors.sqlite
stage-40-quests.sqlite
stage-50-skills.sqlite
stage-60-assets.sqlite
stage-70-wiki.sqlite
        |
        v
stage-90-coverage-closure.sqlite
        |
        v
aa8-client-knowledge.sqlite
```

Stage 90 calcula el cierre transversal de cobertura. Agrupa `gaps`,
`opaque_regions`, consultas, consumers, entidades y relaciones incompletas en
raíces causales; mide su fan-out y genera una cola determinista por evidencia
requerida. Los faltantes posteriores de backend, protocolo, persistencia y
aceptación se conservan como `downstream_out_of_scope`: no compiten con el
descifrado pendiente del cliente ni se convierten en cambios de servidor.

Stage 70 congela la superficie visible de la wiki compatible como evidencia
externa corroborativa. Recorre las cinco raices de catalogo y todas las
categorias descubiertas respetando `robots.txt`, conserva HTML, metadata,
estado HTTP y SHA-256, e importa tambien los snapshots detallados previos.
Normaliza items, quests, NPCs, doodads y skills en `wiki_*`, con comparaciones
`match`, `wiki_only`, `native_only`, `conflict` y `unresolved`. La ausencia de
un ID en un listado nunca se convierte en un 404 ni rellena un hueco nativo.

Stage 60 importa los 377.295 paths únicos del índice congelado de `game_pak`,
las 629.661 filas de `localized_texts` y los 18.263 descriptores nativos de
iconos. Reproduce en orden las consultas 3–30 para reconstruir 69.516 strings
internadas y resolver sus 32.313 referencias sin residuos. También recorre las
extracciones XML/Lua existentes y enlaza paths físicos confirmados, eventos de
audio, claves de animación y registros lógicos de FX sin confundirlos entre sí.

Los filenames de iconos que requieren aliases/atlas, los paths textuales que
no aparecen exactamente en el índice y los loaders no recuperados permanecen
como `unknown`/`blocked`; no se aproximan por nombre.

Stage 50 descifra skills, buffs, effects, modifiers, plots, projectiles,
animaciones, FX y sonidos. Conserva 101 resultados nativos con 657.459 filas,
resuelve los 42 tipos concretos de `effects` y la secuencia adicional de tipos
de `plot_effects`, y proyecta relaciones confirmadas sin convertir cada
`*_id` en una clave foránea inventada.

Las 35 consultas cuyo límite exacto todavía no está mapeado, los cinco
resultados nativos ausentes, las referencias de strings aún dependientes de la
caché global y los IDs sin consumer confirmado se mantienen explícitamente en
`opaque_regions`. El snapshot inicial de cuatro páginas de skills de la wiki
vive en `wiki_*` con autoridad `wiki_visible`.

Stage 40 descifra el bloque nativo de quests y proyecta:

```text
quest
  -> components
  -> acts
  -> 85 familias concretas de act_detail
  -> NPCs, items, skills, buffs, doodads, zonas y otras dependencias
```

La etapa conserva 125 resultados core, el resultado separado de
`QuestActObjEffectFire`, paridad de layouts x86/x64, textos localizados,
tombstones y evidencia wiki visible. La wiki se importa en `wiki_*` y nunca
reemplaza filas ni relaciones `client_native`. Las consultas perifericas,
referencias de strings y endpoints aun no descifrados permanecen como
`opaque_regions` o `gaps`.

Stage 30 incorpora NPCs, modelos, actor models, assets de modelos, facciones,
plantillas de personaje, packs de equipo, evidencia de spawners y la frontera
de apariencia nativa. Esta última incluye decals, presets, total customs,
mapas corporales/faciales, customizing item assets, texturas de cabello y los
12 perfiles XML de targets faciales. Los modifiers de `CustomModel` se
proyectan como `int8[128]` sobre el grafo
`model -> actor_model -> face_target_profile -> face_target`; solamente los
slots no-cero sin descriptor XML permanecen opacos.

El compact cliente aporta además `localized_texts`: Stage 30 conserva el valor
crudo de cada cached result y agrega en paralelo el nombre `en_us` confirmado
de los 18.217 NPCs. `attach_anims` reconstruye de forma autocontenida las
referencias globales `VehicleModel` y `ShipModel`, por lo que todos los
subtipos de `models` quedan clasificados. Los catálogos de color sin resultado
nativo, referencias globales restantes y dependencias ausentes se conservan
como blockers explícitos.

Todas las etapas comparten el esquema canónico:

```text
entities
entity_properties
relations
artifacts
decoders
query_specs
cached_results
consumers
assets
localizations
wiki_*
opaque_regions
coverage
gaps
blocker_roots
blocker_impacts
blocker_evidence
source_records
work_queue
validation_events
```

Las tablas específicas conservan la evidencia original y proyectan identidades,
propiedades y relaciones al grafo. La consolidada nunca se edita manualmente.

## Cierre nativo priorizado v2

La primera iteración sobre la cola Stage 90 corrige dos falsos frentes sin
inventar filas:

- Los 109 items sin fila de descriptor visible son tombstones demostrados por
  las consultas nativas sin filtro: 99 recipes, 6 armors, 3 accessories y 1
  slave equipment. El gap original se conserva como evidencia supersedida.
- De las 9.907 referencias `effect_detail` previamente abiertas, 9.819 son
  tombstones porque sus resultados nativos completos no contienen esos IDs.
  Permanecen 88 referencias opacas: 85 `CinemaEffect` y 3
  `MoveToLocationEffect`.

La clausura de `loot_pack` confirma en `x2game.dll` x86 y x64 las consultas,
consumidores y layouts exactos de `loot_packs` y `loots`. Ninguna de las dos
tablas existe en la compact cliente ni aparece en la secuencia cached
catalogada, y el barrido estructural de `game0...game11` no encontró un par de
resultados consecutivos autoritativo. Por ello las 4.195 identidades
referenciadas siguen bloqueadas como `native_result_absent`; no se completan
desde runtime, wiki ni datos históricos.

El detalle reproducible de esta iteración vive en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V2.md`.

La segunda iteración de cierre nativo confirma como enums escalares inline a
`quest_detail`, `quest_component_text_kind`, `chat_bubble_kind` y `npc_ai`.
`quest_detail` conserva las etiquetas exactas del switch x86/x64; los otros
tres dominios conservan sus IDs y relaciones confirmadas, pero dejan sus
etiquetas humanas como regiones opacas hasta recuperar un consumidor nativo
que las demuestre. También reconcilia 14 `plot_event` referenciados ausentes de
la consulta completa como tombstones. El detalle reproducible está en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V3.md`.

La tercera iteración añade reconciliación transversal entre stages. Conserva
cada gap, entidad y relación fuente, pero deja de tratarlos como bloqueos
activos cuando otra stage demuestra el destino con autoridad nativa fuerte.
Las 75.506 reconciliaciones quedan auditables en `source_records`; ninguna
correlación de assets por filename, XML, Lua o índice de `game_pak` se
promociona a evidencia nativa. El detalle reproducible está en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V4.md`.

La cuarta iteración cierra `world_interaction` desde el switch nativo x86/x64:
105 miembros válidos con etiquetas exactas, el ID 95 demostrado como inválido
y 60 filas opcionales de `wi_details`. Proyecta 9.172 relaciones desde recetas,
668 desde quests y conserva las 7.679 relaciones de effects. Stage 90
reconcilia 9.840 aristas y 6 gaps, dejando cero blocker roots activos para el
dominio. `viewer-world-interactions.html` permite inspeccionar cada miembro,
sus parámetros, procedencias y reconciliaciones. El detalle reproducible está
en `CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V5.md`.

La quinta y sexta iteración cierran el catálogo base `item_grades` y sus tres
catálogos secundarios. `item_grade_buffs` se corrige desde la secuencia SQL
nativa y sus loaders x86/x64: la asociación histórica de 103 filas queda
preservada como evidencia supersedida y el resultado canónico contiene 8.328
filas de cinco enteros. `item_grade_skills` aporta 8 filas y
`item_grade_distributions` 50 filas cuyas ponderaciones suman 100. Stage 20
materializa 8.386 entidades, 42.372 propiedades y 25.023 relaciones; clasifica
95 endpoints de item y 36 de buff como tombstones mediante catálogos nativos
completos. Stage 90 reconcilia las tres consultas, las ocho relaciones a
skills y deja cero raíces abiertas para estas superficies. Los detalles están
en `CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V6.md` y
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V7.md`.

La séptima iteración cierra `quest_name_kind` y
`quest_context_text_kind` como enums escalares inline. Los 3 kinds de nombre
y 5 kinds de texto quedan materializados con paridad x86/x64; 1.673 relaciones
`has_name_kind` y 918 relaciones `has_text_kind` pasan a estado confirmado.
El único `quest_context_text_kind=5` se conserva como `media_fixture` dormido:
su fila nativa existe, pero el barrido de 186 callers x64 y 192 callers x86 no
encuentra un consumidor dedicado. Stage 90 elimina exactamente seis raíces y
queda en 456. El detalle reproducible está en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V8.md`.

La octava iteración recupera la semántica nativa de
`chat_bubble_kind`: `normal`, `think` y `system` quedan ligados a
`CBK_NORMAL`, `CBK_THINK` y `CBK_SYSTEM` en x86/x64 y a sus consumidores
Lua de chat y dirección de quests. También cierra parcialmente
`quest_component_text_kind`: el ID 4 se observó inicialmente en cuatro
consumidores por arquitectura; los IDs 5 y 6 permanecen opacos porque el
barrido inicial de 61 callers x64 y 60 callers x86 no siguió las colecciones
reenviadas. Para `npc_ai`, los IDs 3 y 6 conservan candidatos estructurales
`follow_path` y `run_command_set`, pero no se promueven a etiquetas confirmadas
sin un binding conductual nativo. La consolidada reduce las regiones opacas de
92 a 91 sin alterar entidades, relaciones ni la cola causal. El detalle está
en `CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V9.md`.

La novena iteración cierra la frontera de consumo cliente de `npc_ai_id`.
El campo se conserva en `quest_components` a `0x28` en x64 y `0x20` en x86,
pero el trazado de 61/60 callers, 18 helpers reenviados y las dos rutas del
vector crudo encuentra cero lecturas conductuales. Los bindings
`NpcFollowUnit`, `NpcFollowPath` y `NpcOnEndedFollowPath` son stubs explícitos
que declaran no estar soportados por el cliente en ambas arquitecturas. Un
snapshot determinista cubre además DLL/EXE, Lua y XML: 11.245 archivos y
1.376.694.556 bytes. Los IDs y sus 32.191 referencias permanecen confirmados;
`3 → follow_path` y `6 → run_command_set` siguen siendo candidatos, no labels.
El detalle reproducible está en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V10.md`.

La décima iteración sigue la colección nativa de textos de cada componente y
cierra los tres valores observados de `quest_component_text_kind` con paridad
x86/x64: `4 = summary`, `5 = body` y
`6 = doodad_phase_message`. El ID 6 despacha exactamente el evento UI
`DOODAD_PHASE_MSG` (`0x102`). Las cuatro filas `body` pertenecen al tutorial
DDCMS 598; las dos filas `doodad_phase_message` conservan por separado su
lifecycle `orphaned_parent_context`, porque apuntan a la quest tombstone 1421,
y una mantiene su referencia global de string bloqueada. El barrido
determinista transversal cubre 11.245 DLL/EXE, Lua y XML sin hallar una
semántica alternativa. El detalle reproducible está en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V11.md`.

La undécima iteración reconstruye la caché global que alimenta
`quest_component_texts`. El replay compartido de las llamadas 480–591 deriva
el primer índice 315.732 desde el anchor nativo de `quest_acts`, alcanza
320.790 al entrar en la consulta y resuelve 4.427 referencias. Las dos
ocurrencias restantes del índice 110.150 se recuperan desde su productor
`skills`, cuyo primer índice 75.557 se demuestra por conteo inverso hasta el
anchor adyacente `attach_anims=150.126`. Las 4.429 ocurrencias quedan resueltas
sin traducciones ni datos históricos; `quest_component_texts` pasa a resultado
confirmado y sale de la cola causal. El detalle reproducible está en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V12.md`.

La duodécima iteración reconstruye el mapa global completo de strings anterior
al núcleo de quests: 315.732 referencias continuas, desde `0` hasta `315731`.
La prueba combina replay exacto en orden de ejecución, dos ventanas de firmas
acotadas por loaders nativos, el bloque crudo sin header y el resultado
headerless de `items`; no extrapola firmas fuera de intervalos demostrados. Con
este mapa se resuelven las 7.926 ocurrencias que quedaban en 16 resultados,
incluidas las 6.705 de `quest_chat_bubbles`. Los 125 resultados de quests
quedan sin `<ref:N>` pendientes y las 16 raíces `query_incomplete` salen de la
cola causal. El detalle reproducible está en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V13.md`.

La decimotercera iteración reconcilia transversalmente todos los endpoints
`item` alcanzados por relaciones nativas contra la consulta propietaria
completa y sin filtros de `items`. Se demuestran 16.139 IDs positivos ausentes
como tombstones y se confirman 72.059 relaciones nativas sin confundir la
existencia de la arista con el lifecycle del destino. Las raíces
`referenced_endpoint*` de items desaparecen, la cola causal baja de 436 a 432
y los 1.452 gaps reemplazados se conservan como evidencia auditable. El detalle
reproducible está en `CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V14.md`.

La decimocuarta iteración demuestra el catálogo propietario de `skills` y
reconcilia sus endpoints en Stage 20, 30, 40 y 50. La consulta nativa sin
filtros contiene 33.466 IDs positivos únicos; la aparente fila 33.467 se
demuestra como bytes estructurales previos que violan 16 campos booleanos del
ABI. Se clasifican 8.979 referencias como skills presentes y 1.603 como
tombstones, y las 111.574 relaciones consolidadas cuyo destino es `skill`
quedan confirmadas. La cola causal baja de 432 a 423. El detalle reproducible
está en `CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V15.md`.

El cierre transversal de endpoints `buff` se encuentra congelado en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V16.md`: 27.303 filas propietarias,
426 tombstones demostrados y 101.818 relaciones nativas confirmadas. La
siguiente frontera es `craft`, separando estrictamente identidad habilitada,
deshabilitada e histórica sin inferir IDs individuales cuando la consulta
nativa está filtrada.

El lote autónomo posterior queda congelado en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V17.md`. `craft` materializa 9.369
identidades habilitadas y conserva 2.702 identidades como
`disabled_or_tombstone` porque la evidencia nativa no permite repartirlas sin
inventar; sus 63.364 relaciones sí quedan reconciliadas. `npc_group` recupera
403 filas propietarias, demuestra 213 tombstones y confirma 1.319 relaciones.
La consolidada resultante contiene 667.652 filas de cobertura y 413 raíces
causales. La próxima frontera segura es el lifecycle transversal de `npc`.

El cierre transversal de `npc` queda congelado en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V18.md`: Stage 30 conserva los 18.217
owners presentes, 163 IDs referenciados quedan demostrados como tombstones y
las 41.488 aristas nativas entrantes están confirmadas. La consolidada contiene
669.041 filas de cobertura, 108.928 gaps y 407 raíces causales. La próxima
frontera segura es `craft_pack`, cuyo catálogo propietario de 466 filas ya
tiene consulta, boundary, digest y loader nativos confirmados.

El cierre de `craft_pack` queda congelado en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V19.md`: 466 owners permanecen presentes,
1.183 endpoints referenciados se demuestran como tombstones y 11.523 aristas
`craft -> member_of_craft_pack -> craft_pack` quedan confirmadas. Stage 10
reconcilia además las dos consultas y sus cuatro consumers x86/x64. La
consolidada contiene 673.904 filas de cobertura y 401 raíces causales. La
próxima frontera segura es `item_guide`: 464 owners completos, 4.459 filas de
elementos y tres referencias ausentes clasificables con evidencia negativa.

El cierre de `item_guide` queda congelado en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V20.md`: 464 owners permanecen
presentes, los IDs `488`, `490` y `491` se demuestran como tombstones y las
4.459 aristas `item -> listed_in_item_guide -> item_guide` quedan confirmadas.
Los cuatro consumers x86/x64 y los boundaries de ambas consultas quedan
registrados. La consolidada contiene 675.305 filas de cobertura y 395 raíces
causales. La próxima frontera segura es `tag`, cuyo resultado propietario
completo contiene 5.280 IDs.

El cierre de `tag` queda congelado en
`CHECKPOINT_STAGE_90_COVERAGE_CLOSURE_V21.md`: 5.280 owners permanecen
presentes, 11 IDs referenciados se demuestran como tombstones y las 95.008
aristas nativas `references_tag` quedan confirmadas. También se resuelven las
58 referencias de nombres que mantenían `tags` parcialmente opaco en
Stage 50. La consolidada contiene 691.178 filas de cobertura, 390 raíces
causales y 90 regiones opacas activas. La próxima frontera segura es
`doodad`, comenzando por recuperar su loader x86.

## Uso

Desde este directorio:

```powershell
python -B -m client_forensics status
python -B -m client_forensics build-stage-30
python -B -m client_forensics build-stage-40
python -B -m client_forensics build-stage-50
python -B -m client_forensics build-stage-60
python -B -m client_forensics freeze-stage-70-wiki
python -B -m client_forensics build-stage-70
python -B -m client_forensics build-stage-90
python -B -m client_forensics consolidate
python -B -m client_forensics finalize
python -B -m client_forensics run-all
python -B -m client_forensics validate
python -B -m client_forensics explain npc 3597
python -B -m client_forensics explain quest 330
python -B -m client_forensics explain skill 34121
```

Para cambiar entradas o salidas:

```powershell
python -B -m client_forensics --config .\config\kakao-r558734.json run-all
python -B -m client_forensics --source-items <db> --output-dir <dir> run-all
```

Las rutas conocidas viven en el archivo de configuración. El código no consulta
`COMPACT_DB`.

## Salidas

Por defecto se escriben fuera de Git en:

```text
E:\AAEmu-Research\output\aa8-client-forensics
```

Cada SQLite tiene un manifest independiente. `manifest.json` registra el
linaje completo, hashes SHA-256, conteos, evidencia negativa y validaciones.
`viewer-skills.html` ofrece búsqueda y filtros sobre las skills del grafo
consolidado; `viewer-assets.html` permite inspeccionar iconos y su estado de
resolución física. `viewer-world-interactions.html` expone el enum nativo, sus
detalles opcionales y relaciones agrupadas. `viewer-coverage-closure.html` y
`coverage-closure-work-queue.csv` exponen raíces causales, fan-out y evidencia
de aceptación. `gaps-priority.csv` conserva además los gaps originales
ordenados por severidad.
