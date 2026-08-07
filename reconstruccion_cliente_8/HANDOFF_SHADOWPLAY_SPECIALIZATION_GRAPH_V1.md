# Handoff — reconstrucción nativa de Shadowplay desde el grafo V1

## Contrato para el siguiente chat

Usar `aaemu8-native-reconstruction`. Este documento no autoriza a modificar el
extractor forense ni a sustituir evidencia AA8 con 3.0 o con la wiki.

Leer primero:

1. `CHECKPOINT_SHADOWPLAY_SPECIALIZATION_GRAPH_V1.md`;
2. `shadowplay-specialization-graph-v1.manifest.json`;
3. `shadowplay-specialization-graph-v1.sqlite3`;
4. `shadowplay-specialization-test-matrix.csv`;
5. el contrato común de habilidades AA8 y el estado actual de
   `native_combat`.

Todos los artefactos grandes viven en:

```text
E:\AAEmu-Research\output\aa8-client-forensics
```

## Autoridad y límites

Orden obligatorio:

1. filas y relaciones Stage 50/60;
2. clausura consolidada y consumers nativos;
3. grafo Shadowplay derivado;
4. comportamiento observado;
5. wiki sólo para corroboración visible;
6. material histórico únicamente ante ausencia AA8 demostrada y bajo la
   política de reconstrucción nativa.

No reconstruir `skill 10082` como habilidad raíz: no posee fila `skills`
nativa AA8. Sus enlaces son buffs/rangos wiki y permanecen corroborativos.

`skill 36594` sí es raíz nativa. Debe permanecer bloqueada hasta implementar o
demostrar la semántica AA8 de `BubbleEffect`; no ocultarla ni marcarla lista.

## Flujo de trabajo por skill

Procesar las 28 raíces en orden ascendente de `skill_id`. Para cada una:

1. Leer `specialization_skills` y `skill_runtime_contracts`.
2. Materializar `skill_effect_steps` respetando orden, chance, target flags y
   concrete effect type.
3. Implementar el ciclo completo de todos los `buff_contracts`: duración,
   stacks, ticks, triggers, breakers, modifiers y tags.
4. Traducir `combo_conditions` y `combo_outcomes` como pares condición→efecto;
   nunca deducirlos del texto wiki.
5. Implementar `presentation_bindings`: animaciones, controllers,
   projectiles, AOE, FX, sonido e iconos que tengan consumidor runtime.
6. Seguir `dependency_edges` y `dependency_closure`, incluidas skills internas
   o cruzadas, hasta estado terminal.
7. Consultar `downstream_implementation_audit` para conocer la brecha actual,
   recordando que es `server_observed` y no autoridad cliente.
8. Convertir las nueve filas de `reconstruction_test_cases` de la skill en
   pruebas ejecutables o evidencia explícita `not_applicable`.

Consultas iniciales:

```sql
SELECT * FROM specialization_skills
WHERE root_member=1 ORDER BY skill_id;

SELECT * FROM skill_runtime_contracts WHERE skill_id=?;
SELECT * FROM skill_effect_steps WHERE root_skill_id=? ORDER BY ordinal;
SELECT * FROM buff_contracts WHERE root_skill_id=? ORDER BY buff_id;
SELECT * FROM combo_conditions WHERE root_skill_id=? ORDER BY source_table,native_id;
SELECT * FROM combo_outcomes WHERE root_skill_id=? ORDER BY source_table,native_id;
SELECT * FROM presentation_bindings WHERE root_skill_id=? ORDER BY presentation_kind,native_id;
SELECT * FROM dependency_closure WHERE root_skill_id=? ORDER BY depth,entity_key;
SELECT * FROM reconstruction_test_cases WHERE skill_id=? ORDER BY area;
```

## Gate de una skill

Una skill sólo puede cerrarse cuando:

- coste, cooldown, targeting, cast/channel/toggle y restricciones coinciden;
- todos sus effect steps y concrete effects tienen implementación o blocker;
- buffs y combos cubren apply/tick/trigger/remove/stack;
- animación, projectile/controller/AOE e impacto son visibles en cliente;
- skills internas se ejecutan con el orden nativo;
- todas las filas de la matriz tienen prueba o `not_applicable` demostrado;
- no se añadieron IDs wiki como autoridad;
- el manifest runtime registra exactamente qué filas del grafo consumió.

## Gate de la especialización

- 28/28 roots procesadas;
- 9/9 visibles disponibles en la interfaz correspondiente;
- 6/6 pasivas materializadas;
- cero dependencias silenciosamente descartadas;
- `36594` implementada y validada o conservada explícitamente bloqueada;
- pruebas unitarias, integración y dos clientes cuando la presentación lo
  requiera;
- checkpoint runtime final que cite el SHA del grafo
  `40B7BD4F82B0BA86A1E9FEB8CF6A436B94983634284D01C651FAB5C7C7358AE7`.
