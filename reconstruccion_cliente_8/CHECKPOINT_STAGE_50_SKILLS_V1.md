# Checkpoint Stage 50 - Skills, Buffs, Effects y Plots V1

Estado: aceptado como frontera forense reproducible.

Autoridad: cliente Kakao `8.0.3.12 r558734`. La wiki se conserva como
evidencia visible separada. No se modificó AAEmu, compact runtime, `.env`,
MySQL ni Docker.

## Artefactos aceptados

- `stage-50-skills.sqlite`
  - bytes: `1976455168`
  - SHA-256:
    `2054DFEF3D76772C5C982AF823D96EA601CA2FA323BF1CD936B7E2B7FCBEF307`
- `stage-50-skills.manifest.json`
  - SHA-256:
    `EDFE8F2B20C7DB88FE6659CC26A8A4EB7AE7674B5A9758E265CD6B322F83B158`
- `aa8-client-knowledge.sqlite`
  - bytes: `5799858176`
  - SHA-256:
    `39033345E61B876FA596C1F9336CF0AA0EBE6AA9B43D24F490C7A76D55515685`
- `manifest.json`
  - SHA-256:
    `6884120468429620FA74F3D7F4C2B180A5067E22D6F66C54ECB1D8CF3F104C03`
- `viewer-skills.html`
  - bytes: `15128646`
  - SHA-256:
    `C5AA7F4A74DD74D68671483BFACCF6D3437AC2014AF31399061BA7DD385CCBA9`
- `gaps-priority.csv`
  - bytes: `21658308`
  - SHA-256:
    `0B9F19E5E369B10B911A686F72BEC9EDBDCDDD95E0E3E646D8C2B6CBEF099AAA`

Dos builds finales de Stage 50 produjeron exactamente el mismo SHA-256.
`PRAGMA quick_check` e `integrity_check` devolvieron `ok` tanto para Stage 50
como para la consolidada.

## Inventario Stage 50

- 141 consultas SQL/loader seleccionadas.
- 137 layouts idénticos entre x86 y x64.
- 3 layouts confirmados en x64 y 1 confirmado en x86, sin contradicciones.
- 101 resultados nativos decodificados.
- 657459 filas de cached result y 657459 filas nativas preservadas.
- 33466 skills nativas presentes.
- 27303 buffs nativos.
- 60885 effects polimórficos.
- 42 tipos de `effects` resueltos desde la caché de strings.
- Secuencia adicional de tipos de `plot_effects` resuelta.
- 46088 `skill_effects`.
- 5853 plots, 45959 plot events y 58377 plot effects.
- 18234 AOE shapes, 3083 skill controllers y 1493 projectiles.
- Catálogos de animación, FX, sonidos, sound packs y tags preservados.
- 176235 textos localizados relacionados con skills, buffs, effects o plots.

## Grafo Stage 50

- 686060 entidades.
- 367060 propiedades proyectadas.
- 876631 relaciones:
  - 781368 confirmadas;
  - 95263 con endpoint todavía desconocido.
- 20878 gaps explícitos.
- Cero propiedades o relaciones huérfanas.

Todas las columnas se conservan íntegramente en `native_rows.row_json`.
`entity_properties` proyecta textos y discriminadores polimórficos.
Las relaciones sólo se crean cuando el nombre de columna y el consumer
permiten tipar el destino sin inventarlo.

## IDs y lifecycle de skills

Stage 50 no confunde catálogo nativo con localización:

- 33466 skills tienen fila nativa confirmada.
- El universo observado de entidades `skill` incluye además IDs sólo
  localizados o referenciados.
- 35684 IDs de skills tienen localización.
- 11 skills observadas en el grafo no tienen localización.

Los IDs sin fila nativa no se promueven a `confirmed`; conservan lifecycle
`localization_only` o `referenced` y estado `unknown`.

## Evidencia wiki separada

Se congeló un snapshot inicial de las skills `22727`, `34121`, `39137` y
`45719`.

- 4 `wiki_entities`
- 11 `wiki_properties`
- 73 `wiki_relations`

La wiki nunca reemplaza filas, layouts ni relaciones `client_native`.

## Blockers preservados

1. 35 consultas tienen SQL y layout confirmados, pero todavía no tienen su
   frontera exacta de cached result.
2. Cinco consultas no poseen resultado nativo en esta ejecución:
   - `cinema_effects`
   - `npc_move_to_zone_effect_items`
   - `npc_move_to_zone_effects`
   - `move_to_location_effects`
   - `projectile_params`
3. Veinte tablas contienen referencias de strings cuyo insert ocurrió antes
   de la frontera decodificada. Sus filas numéricas permanecen preservadas.
4. 903957 valores positivos `*_id` no se proyectan aún porque el consumer y
   la tabla destino no están confirmados.
5. 20878 endpoints requieren que otra etapa descifre su catálogo propietario.

No se aproximó ninguno de estos casos con datos 3.0 ni con la wiki.

## Validaciones

- 12 pruebas unitarias aprobadas.
- Cero divergencias de layout x86/x64.
- Cero referencias `<ref:N>` en los discriminadores `actual_type` de
  `effects` y `plot_effects`.
- Cero cached results o cached rows huérfanos.
- Cero propiedades o relaciones huérfanas.
- Consolidación Stage 00/10/20/30/40/50 con seis entradas de lineage.
- Manifest y exportaciones regenerados.
- Visor estático validado sintácticamente con 35703 entidades `skill` del
  grafo consolidado.

## Siguiente frontera recomendada

Continuar con `stage-60-assets.sqlite`: assets, iconos, UI, localización,
texturas, modelos, audio y FX. Esta etapa debe usar los consumers ya
inventariados para tipar parte de los 903957 IDs pendientes y reconstruir la
caché global de strings que bloquea las veinte tablas Stage 50.

En paralelo, la cola Stage 50.1 queda ordenada por fan-out:

1. reconstrucción global de strings internadas;
2. 35 límites de cached result;
3. endpoints de effect detail con mayor número de referencias;
4. consumers de IDs todavía no tipados.
