# Checkpoint Stage 40 - Quests V1

Estado: aceptado como frontera forense reproducible.

Autoridad: cliente Kakao `8.0.3.12 r558734`. La wiki es evidencia visible
separada y no reemplaza datos nativos. No se modifico AAEmu, compact runtime,
`.env`, MySQL ni Docker.

## Artefactos aceptados

- `stage-40-quests.sqlite`
  - bytes: `1021902848`
  - SHA-256:
    `90036423FEE92051871F0DCF78E3DE18B3D8B3A598449BCA1618924C498ECD7C`
- `stage-40-quests.manifest.json`
  - SHA-256:
    `13B67BFBE7B457CE151C02CFE70F261C6AB8972CCBDA9C082623FDE234E3DEC0`
- `aa8-client-knowledge.sqlite`
  - bytes: `3829989376`
  - SHA-256:
    `AF615129A3B6CCF486FE0C08B89BE90E3E3D5D69C9CA31388E7DFAEEDB6186AA`
- `manifest.json`
  - SHA-256:
    `73C6A7C7F6E338F1CAF604E391C536A2158D4615D45BEE52345EAD34DC770361`

Dos builds aislados de Stage 40 produjeron exactamente el mismo SHA-256.
`PRAGMA quick_check` e `integrity_check` devolvieron `ok`.

## Inventario Stage 40

- 156 superficies SQL relacionadas con quests inventariadas.
- 154 layouts estaticos completos y 2 layouts bloqueados.
- 125 resultados core decodificados en el rango de llamadas `480..604`.
- `QuestActObjEffectFire` decodificado fuera del bloque core.
- 126 consultas/resultados nativos preservados.
- 180873 filas de cached results y 180873 filas nativas.
- 7826 quests presentes y confirmadas.
- 969 IDs de quest preservados como tombstones de localizacion.
- 42446 quest acts.
- 85 tipos concretos de `act_detail`.
- Cero acts sin su fila concreta de detalle.
- 74980 textos localizados relacionados con quests.
- 198904 entidades, 1651635 propiedades y 333741 relaciones.
- 228235 relaciones confirmadas y 105506 con endpoint aun desconocido.
- 5197 gaps explicitos; cero propiedades o relaciones huerfanas.

## Evidencia wiki separada

Se congelo un snapshot inicial de las quests `330`, `2256`, `2257` y `2258`.

- 4 `wiki_entities`
- 12 `wiki_properties`
- 26 `wiki_relations`

Las cuatro identidades fueron corroboradas contra entidades nativas. Los
destinos visibles de la quest 330 (NPCs, items y quest enlazada) ya existen en
el grafo nativo. Las afirmaciones wiki conservan autoridad `wiki_visible`.

El comando `explain` ahora entrega tambien localizaciones y los tres conjuntos
`wiki_entities`, `wiki_properties` y `wiki_relations`.

## Blockers preservados

1. Dos layouts estaticos incompletos:
   - `conflict_zone_quest_completions`
   - join `loots INNER JOIN items` con `items.loot_quest_id`
2. 33 consultas perifericas con SQL/layout catalogado pero sin frontera exacta
   de cached result asignada.
3. 21524 referencias de strings no localizadas aun dependen de reconstruir la
   cache global previa al bloque core. `quest_acts` ya esta resuelto.
4. 5197 endpoints pertenecen a tablas que deben cerrar sus etapas propietarias.

Estos casos no se aproximaron con datos 3.0 ni con la wiki.

## Validaciones

- Paridad exacta de 126 layouts entre `x2game.dll` x86 y x64.
- Clausura completa `quest_act -> act_detail`.
- Conteo exacto de localizaciones y tombstones.
- Snapshot wiki con hashes de payload y metadata.
- Cero relaciones nativas huerfanas.
- Cero propiedades o relaciones wiki huerfanas.
- 11 pruebas unitarias aprobadas.
- Consolidacion Stage 00/10/20/30/40 con cinco entradas de lineage.

## Siguiente etapa recomendada

Continuar con `stage-50-skills.sqlite`: skills, effects, buffs, modifiers,
plots, proyectiles, animaciones, FX, sonidos, controllers y protocolo
observado, siempre de forma descriptiva y sin implementar mecanicas.

Los cuatro blockers anteriores quedan en la cola de descifrado transversal y
se enlazaran desde Stage 50/60 cuando esas etapas aporten sus autoridades.
