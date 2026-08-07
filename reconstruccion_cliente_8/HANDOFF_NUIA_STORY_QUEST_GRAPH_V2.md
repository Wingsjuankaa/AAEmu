# Handoff: Nuia Story Quest Graph V2

La frontera narrativa Nuia V2 está cerrada. El punto de continuación ya no es
la quest 4411/capítulo 6: la línea principal demostrada alcanza la quest 10682,
capítulo 31.

## Artefacto canónico

```text
E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v2.sqlite3
SHA-256: 39FD2589DC095E80722B94D3EB1D307E649C28AEAEB486AEF8725AD33DE82B5A
```

Consultables asociados:

```text
nuia-story-quest-graph-v2.html
nuia-story-quest-graph-v2-summary.json
nuia-story-quest-graph-v2-gaps.csv
nuia-story-quest-test-order-v2.csv
nuia-story-quest-graph-v2.manifest.json
nuia-story-quest-graph-v2-wiki-snapshot-manifest.json
```

## Qué debe consumir una tarea posterior

1. `story_quests` para el orden editorial nativo de las 294 quests.
2. `story_order_edges` para el orden corroborado, sin convertirlo en FK
   nativa.
3. `story_wiki_edge_resolutions` para distinguir href wiki bruto de la
   variante Nuia resuelta.
4. `story_transition_gates` para los cuatro saltos entre familias/categorías.
5. `scope_boundary_candidates` para el prerrequisito lateral 10159.
6. `story_terminal_audits` para la evidencia terminal de 10682.
7. `story_dependency_closure` y `downstream_audit_queue` para no ejecutar una
   prueba más allá de una dependencia `missing/unknown/opaque/tombstone`.

## Anclas de revisión

```text
4411  Tying Up Loose Ends       -> 7115 Your Legend Continues
8558  The Great Seal of Erenor  -> 9009 A Call for Help
10303 Orien, Warden...          -> 10361 To Mysthrane
10369 Joining Forces            -> 10646 Journey West
10682 A Moment to Reminisce     -> terminal AA8 auditada
```

Los enlaces de variante racial de la wiki no deben volver a recorrerse de
forma literal. Ejemplos: 7115 enlaza por href a 7325, pero su destino Nuia
resuelto es 7119; 7119 enlaza a 7124, pero el destino Nuia es 7123.

## Estado de gates

- selección: 294 quests, capítulos 0–31, ocho categorías;
- wiki: 294/294 snapshots terminales;
- canonización: todas las relaciones internas clasificadas;
- orden: 292 aristas corroboradas y sólo 6839→330 conservada como frontera
  editorial no demostrada;
- dependencia lateral: 10159 preservada explícitamente;
- clausura: cero components/acts descartados;
- transiciones: cuatro clasificadas;
- terminal: cuatro auditorías confirmadas sobre 10682;
- determinismo: dos builds con SHA idéntico;
- SQLite V2 y consolidada: quick/integrity OK;
- pruebas: 16/16 V1+V2.

## Regla de continuidad

No reabrir esta frontera por un cambio de nombre o wiki. Reabrir sólo si
cambia el build del cliente, el hash de Stage 40/70, el parser V2 o aparece
evidencia nativa de un chapter principal posterior a 31. Toda implementación
de servidor pertenece a `aaemu8-native-reconstruction`, no a esta skill.

Detalle completo: `CHECKPOINT_NUIA_STORY_QUEST_GRAPH_V2.md`.
