# Checkpoint V12: `quest_component_texts` y replay global de strings

## Alcance

Este checkpoint cierra la frontera forense `quest_component_texts` del cliente
Kakao 8.0.3.12 r558734. El trabajo se limita a descifrado, evidencia, grafo y
reportes; no implementa mecánicas ni modifica AAEmu, compact, MySQL o runtime.

La autoridad utilizada es exclusivamente nativa:

- stream cacheado `game11`;
- orden real de consultas del cliente;
- layouts/loaders x64 y sus anchors;
- productor nativo anterior de las referencias heredadas.

La wiki y los textos localizados no se usaron como autoridad para completar
valores.

## Hallazgo principal

El decoder anterior abría una caché de strings aislada para cada cached result.
Eso hacía aparecer como opacas las 4.429 referencias de
`quest_component_texts`, aunque el cliente consume los resultados de forma
secuencial con una caché compartida.

La semilla exacta del bloque quest se deriva sin aproximaciones:

1. los calls 480–583 producen 4.882 strings nuevas;
2. `quest_acts` comienza en la referencia nativa 320.614;
3. por tanto el call 480 comienza en `320614 - 4882 = 315732`;
4. el replay compartido sitúa `quest_component_texts` en el intervalo
   `[320790, 329884)`.

Ese replay resuelve 4.427 referencias. Las dos ocurrencias restantes apuntan a
la referencia 110.150, usada por los IDs 20.616 y 20.617.

La referencia heredada también quedó demostrada desde el stream:

- `attach_anims` comienza en la referencia 150.126;
- `skills` (call 113) inserta 42.727 strings;
- `buffs` (call 119) inserta 31.842 strings;
- los calls 114–118 no insertan strings;
- la semilla de `skills` es
  `150126 - 42727 - 31842 = 75557`;
- la referencia 110.150 resuelve a
  `피 묻은 손의 시체를 조사합니다.`.

No se sustituyó ningún `<ref:N>` mediante heurísticas, 3.0 o wiki.

## Resultado nativo

`quest_component_texts` queda:

- 13.531 filas habilitadas;
- estado `confirmed`;
- cero referencias sin resolver;
- rango de strings `[320790, 329884)`;
- digest
  `86D95A2A55F10D6AA677CFD1012C5E08745B09C70060A5E74CCD3BCFB5BA712E`.

El mismo replay global cierra correctamente tres resultados adicionales:

| Resultado | Filas | SHA-256 del conjunto |
|---|---:|---|
| `quest_mails` | 2 | `9A7B8B08E67231172276D798036E4995F328A094F1BB9342D6F00A990CF6F608` |
| `cinema_captions` | 224 | `64BCC5DAB60A8661E6A1285DA76734CF14CCE24A918234DFDDF7FB89757B993D` |
| `quest_context_texts` | 918 | `28E6CC992FF7F2A1812E6429F6B81D2ED2C2D9EC192A244AEE5F9B1A88AB5D3F` |

Las cuatro raíces `query_incomplete:*` desaparecen de Stage 90 y de la
consolidada. Las raíces causales y la cola pasan de 456 a 452.

## Pendiente preservado

No se declara resuelta toda la caché global. Permanecen 7.926 ocurrencias
opacas, repartidas en 16 resultados:

- `quest_chat_bubbles`: 6.705;
- `quest_contexts`: 639;
- `quest_monster_groups`: 213;
- `quest_act_obj_aliases`: 114;
- `quest_names`: 87;
- `quest_categories`: 77;
- `quest_item_groups`: 21;
- `quest_act_obj_spheres`: 19;
- `quest_cameras`: 17;
- `today_quest_groups`: 15;
- `quest_act_obj_sell_backpack_goods`: 5;
- `today_quest_steps`: 5;
- `quest_doodad_groups`: 3;
- `cinema_subtitles`: 2;
- `quest_act_con_accept_npc_emotions`: 2;
- `quest_context_groups`: 2.

Sus referencias apuntan a productores anteriores al call 480. Se conservan
como evidencia negativa verificable; no se inventaron valores.

## Implementación

- `client_forensics/quests.py`
  - replay compartido de calls 480–604;
  - derivación y validación de la semilla 315.732;
  - recuperación exacta de la semilla de `skills`;
  - resolución externa con procedencia por productor;
  - guardas de inicio, fin y referencias pendientes.
- `client_forensics/stage40.py`
  - preserva la evidencia de resolución en `cached_results`.
- `client_forensics/tests/test_core.py`
  - fija conteos de tokens, rangos, textos y digests;
  - cubre los tres cierres colaterales.
- versión de herramienta: `0.19.0`.

## Validación

- 25/25 pruebas Python aprobadas.
- Dos builds Stage 40 byte a byte idénticos.
- Dos builds Stage 90 byte a byte idénticos.
- Dos consolidaciones explícitas byte a byte idénticas.
- `quick_check=ok` e `integrity_check=ok` en Stage 40, Stage 90 y consolidada.
- Cero propiedades, relaciones, cached rows, impactos o entradas de cola
  huérfanas.
- Cero `<ref:N>` en las 13.531 filas de `quest_component_texts`.
- IDs 20.616 y 20.617 confirmados tanto en Stage 40 como en la consolidada.

## Artefactos congelados

| Artefacto | SHA-256 |
|---|---|
| `stage-40-quests.sqlite` | `C53517260ACF7518D12571B05E98BA405A0B52C2C0A63E9D9896E73E85EC7E24` |
| `stage-40-quests.manifest.json` | `8FD841DA89B63F6E594C6D5790349EFA649AD310E9286B888A35743E10302DFA` |
| `stage-90-coverage-closure.sqlite` | `F47337F9A8B58B2F0D2A937B0CA3DECC88E65F565834ED8CA0951E517E71A62F` |
| `stage-90-coverage-closure.manifest.json` | `EC66F015D6DCEC7F82DCB3CD44BE0652BABC0AE377AB34804A9AA37DEFDCAD52` |
| `aa8-client-knowledge.sqlite` | `E99605C8AEE841E2E5D4225BD4F39F3359F892D812B7C07B155680124BAF50DE` |
| `aa8-client-knowledge.manifest.json` | `699D5902DEA9B040E93CEF612947409D3294E82BE7F52D30A93A011A32D7AD3D` |
| manifest final | `D7293A7EB84FFA2A638457ABB60AE6CDCEE0D07B8B8D4DE3F83F8EFD041C768D` |
| cola CSV | `CAA39671FCD0A9EE7D0808CF1754985502EFC413B6EF9C6C997B74A4FB5C6228` |
| visor de cobertura | `A11A027BA9EA59AD3DAA5CEA8507B8F2776B708AD9E4D608B4DC0DCD741BFF49` |

Conteos principales de la consolidada:

- 1.657.484 entidades;
- 6.950.492 propiedades;
- 2.113.623 relaciones;
- 544.827 filas de cobertura;
- 452 raíces causales y 452 entradas de cola.

## Siguiente frontera recomendada

La siguiente frontera debe ser la reconstrucción transversal de la caché global
anterior al call 480, usando `quest_chat_bubbles` como objetivo de aceptación.
Es preferible a resolver tablas una por una porque un único mapa de productores
puede cerrar hasta 16 raíces y 7.926 ocurrencias. El primer objetivo medible es
resolver las 6.705 ocurrencias de `quest_chat_bubbles`, congelar su digest y
propagar cualquier cierre colateral demostrado.
