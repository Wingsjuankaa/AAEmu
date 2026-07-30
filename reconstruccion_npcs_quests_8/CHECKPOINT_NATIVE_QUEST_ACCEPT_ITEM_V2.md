# Checkpoint AA8: QuestActConAcceptItem y catálogo quest V2

Fecha: 2026-07-30

Autoridad: ArcheAge Kakao `8.0.3.12 r558734`

## Resultado

`QuestActConAcceptItem` dejó de ser un tipo opaco para el catálogo transversal.
El servidor ya tenía:

- la clase `QuestActConAcceptItem`;
- el loader de `quest_act_con_accept_items`;
- el consumidor de inicio genérico mediante `Quest.Start()` y `act.Use()`;
- la validación de posesión del item mediante el inventario.

Faltaba cerrar el ciclo de vida. `Quest.RemoveQuestItems()` ahora consume el
item de aceptación al completar o abandonar la misión cuando cualquiera de
los flags nativos `cleanup`, `drop_when_destroy` o `destroy_when_drop` lo
requiere. El consumidor evita escribir el conteo en el arreglo de objetivos,
porque el item pertenece al contexto de aceptación y no a un objetivo de
progreso.

El builder transversal V2 incorpora las `702` filas nativas de
`quest_act_con_accept_items` y verifica igualdad de filas contra el grafo
forense.

## Frontera estricta conservada

Habilitar el tipo de acto no habilita automáticamente sus quests. Cada
`item_id` continúa obligado a tener:

```text
coverage = complete
missing_dependencies = ''
```

Como resultado:

- desaparece `unsupported_act:QuestActConAcceptItem` como razón de cuarentena;
- `incomplete_item_definition` sube de `3.980` a `4.226`, porque el
  clasificador ahora puede seguir las relaciones de item antes ocultas;
- el conjunto activo permanece en `561` quests;
- no se promovió ningún `phase_a_candidate`, `catalog_only` ni tombstone.

## Evidencia negativa: quest 1113

Se auditó la quest racial `1113`, `The Road to Fortune-Telling`, como posible
cierre inicial:

```text
quest dossier
  E:\AAEmu-Research\output\aa8-client-forensics\dossiers\quest-1113.json
  D63BF527EB92160D894ECABE159278986DD9AC81291B255F572B1A5E4B8ED739

item dossier
  E:\AAEmu-Research\output\aa8-client-forensics\dossiers\item-13974.json
  4286BB05D27A046C9957D5EA46BBB1A2F2A9D75E37AADC77CF774E95F887543B

wiki visible
  https://wiki.archerage.to/na-en/db/quests/1113
```

La wiki corrobora aceptación por NPC, recolección de un `Dragonfruit` 13974,
entrega a otro NPC y recompensa. El cliente AA8, sin embargo, conserva la
referencia pero no una identidad positiva para el item 13974 en su catálogo
completo de items. El dossier lo clasifica como tombstone. Por tanto, la quest
permanece en cuarentena y no se sintetizó una definición histórica.

## Artefacto reproducible

Se hicieron dos builds desde el runtime NPC visual validado:

```text
compact-8.0-runtime-native-quest-catalog-v2.sqlite3
compact-8.0-runtime-native-quest-catalog-v2-verify.sqlite3

bytes      137.498.624
SHA-256    D8FBD65AC8906ACC876D31A10F31293CA4A8E1DD40BF3712FF2DFBEC696A2744
```

Ambos artefactos son idénticos byte por byte.

## Validación

```text
unittest del catálogo SQLite                 8/8
suite completa .NET Core 3.1               282/282
PRAGMA quick_check                              ok
PRAGMA integrity_check                          ok
auditorías de huérfanos                          0
detalles AcceptItem ausentes                     0
```

La compilación se hizo contra `netcoreapp3.1`; las pruebas se ejecutaron con
`DOTNET_ROLL_FORWARD=Major` porque el host tiene runtimes .NET 6–10 pero no el
runtime 3.1.

## Decisión de despliegue

El candidato V2 no se desplegó.

Aunque el consumidor nuevo está cerrado, la transición del catálogo sigue
retirando `6.096` quests de las `6.628` presentes en la base activa. Tampoco
existe todavía una familia inicial completa con todos sus items, doodads,
skills, requisitos y actos validados. El runtime NPC visual y `.env`
permanecen sin cambios.

## Próximo cierre

El siguiente trabajo debe atacar una dependencia positiva y cerrable:

1. recuperar un tipo concreto de item `impl_id=10` usado por `AcceptItem`, o
   validar un item genérico de quest positivo;
2. cerrar su skill/effect/protocolo si corresponde;
3. promover sólo ese item de forma versionada;
4. comprobar que la quest resultante completa aceptación, progreso, reporte,
   recompensa y persistencia;
5. repetir hasta cerrar una familia inicial completa antes de desplegar.
