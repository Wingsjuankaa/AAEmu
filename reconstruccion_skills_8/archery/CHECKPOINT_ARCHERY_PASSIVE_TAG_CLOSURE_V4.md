# Checkpoint Archery passive/tag closure V4

Fecha: 2026-08-07

## Resultado

V4 corrige una segunda frontera de cache inverso descubierta al aplicar la
guia de reconstruccion completa a Archery. V3 ya reemplazaba correctamente
`tagged_skills`, pero el grafo de especializacion solo exponia el wrapper
`passive_buffs` y su `buff_id`; no materializaba las seis filas `buffs` ni
cerraba todas sus relaciones `tagged_buffs`.

El runtime portador conservaba filas historicas para esos owners. Ademas, el
upsert por `id` no podia retirar relaciones antiguas con `id` nulo, por lo que
ocho pares naturales `(buff_id, tag_id)` estaban duplicados. Un consumidor que
itera tags podia ejecutar dos veces una misma rama.

La reparacion V4:

- materializa desde `aa8-client-knowledge.sqlite` los buffs exactos
  `480,486,888,889,7564,7565`;
- materializa 21 relaciones AA8 exactas de tags para esas seis pasivas;
- cierra `tagged_buffs` para todos los buffs seleccionados de Archery;
- elimina primero la particion completa de cada owner y luego inserta las
  relaciones exactas;
- valida por hash la fila completa, no solo la presencia del ID;
- conserva AA8 como unica autoridad y usa el crosswalk solo como pase de
  reduccion de vacios.

## Contratos AA8 recuperados

La base forense AA8 ya contenia las descripciones y relaciones actuales. La
discrepancia no provenia de una ausencia del cliente ni justificaba sintetizar
desde AA10: el runtime portador retenia copias legadas.

- buff 480: contrato textual AA8 de escalado de dano por distancia; requiere
  prueba viva del consumidor hardcoded/tagged;
- buff 486: movimiento `+8%`, `unit attribute 10 / value 80`;
- buff 888: reduccion de mana `-10%` bajo los estados de disparo descritos por
  AA8; requiere prueba viva del consumidor;
- buff 889: dano de skills Archery `+10%`, tag 3750 / attribute 10, con 24
  skills consumidoras;
- buff 7564: critico ranged `+9%`, `unit attribute 82 / value 90`;
- buff 7565: Feral Mark por critico ranged, ataque `+40` y reduccion de
  cooldown de disparos Archery por stack, hasta cinco; requiere prueba viva
  del consumidor nativo.

No se promueven estos textos por si solos a comportamiento servidor. Los
modificadores declarativos se validan estructuralmente; los contratos
hardcoded/tagged pasan solo con traza viva.

## Frontera binaria comprobada

Se consulto tambien el indice reproducible Stage 15 antes de declarar un
consumidor hardcoded:

- busquedas FTS por `Feral Claws`, `Feral`, `Sharpshooting` y
  `Archery Expertise`: cero funciones;
- la unica coincidencia decimal `7565` fue `FUN_39368390`
  (`x2game.dll` x64, RVA `0x368390`, function key terminado en
  `:00368390`), donde Ghidra prueba que es el offset de estructura
  `[RBX+0x1D8D]`, no un ID de buff;
- no existe por tanto evidencia binaria suficiente para implementar 480, 888
  o 7565 como formulas nuevas en el servidor.

Esto es evidencia negativa, no permiso para copiar balance 10.x. La prueba
viva instrumentada es la siguiente frontera exacta: si falla, su traza dara el
evento/estadistica ausente para abrir una busqueda binaria mas estrecha.

## Clausura y hashes

- filas AA8 materializadas en la capa: 5.022;
- `buffs`: 49, incluidas las seis pasivas exactas;
- `tagged_buffs`: 229 filas para 49 owners;
- pares duplicados seleccionados: cero;
- `tagged_skills`: 356 pares unicos y 35/35 raices;
- filas runtime AA10: cero;
- filas sin clasificar por el crosswalk: cero;
- conflictos informativos del crosswalk: ocho; ninguno se usa como fila
  runtime;
- las 21 relaciones pasivas son `exact_id_exact_relation` en AA10;
- los seis buffs conservan identidad estable y clasifican
  `stable_id_changed_properties`; el crosswalk marca balance
  `exact_or_absent`, y en 480/888/889/7565 la diferencia declarada es `name`,
  no una formula promovible;
- hash canonico de las seis filas `buffs`:
  `C63FF2EC974C68D4C449FDEB5C8AF4FFBC7A45CD9C2D4C83562A8DF847B1FB7E`;
- hash canonico de las 21 relaciones pasivas `tagged_buffs`:
  `404827C91918E3191F7A09B11E1E665D2BA62CDA6AA403197F8D9D78F9233D1A`;
- `quick_check=ok`, `integrity_check=ok`.

Los ocho conflictos del crosswalk quedaron localizados y no son opacos:

- `plot_next_events` 48364, 48367, 60051 y 60055: Endless Arrows Stone,
  plot 4673;
- 60059 y 60071: Endless Arrows base, plot 5733;
- 60076 y 60082: Endless Arrows Flame, plot 5735;
- AA10 cambia `next_event_id` en los ocho y tambien `speed`/tiempo de
  animacion en seis, por lo que el crosswalk los marca
  `changed_not_promotable` donde corresponde.

V4 conserva las ramas AA8. La matriz viva exige mantener/repetir cada una y
comprobar que no exista impacto tardio; AA10 no resuelve estos conflictos.

Tres construcciones limpias produjeron el mismo runtime:

- archivo: `compact-8.0-runtime-archery-v4.sqlite3`;
- bytes: 141.082.624;
- SHA-256:
  `A8D209F3B30B3DB8DE2B3B0C19B578A6760D68FF2D082B9AC7F5B70616DFFB22`;
- manifiesto: `generated/archery-runtime-v4.manifest.json`;
- SHA-256 del manifiesto:
  `10FA800C3A6977FDA38A3522D15CB5E451F992B63742ED8D229DB05D7A381355`.

Al excluir solamente paths/nombres de destino, los tres manifiestos tienen el
mismo hash semantico:
`1A2D0DA61DF03F660DE7A6D1DBDD9354D2A80048ED514FEC1EF08117AB360EA8`.

## Verificacion automatica

- regresion estructural runtime: 16/16;
- auditor ejecutable: 9/9;
- 35/35 raices de skill y 6/6 pasivas;
- 356 `tagged_skills`, 21 tags pasivos y cero pares duplicados;
- cero blockers graficos u owner-keyed;
- suite servidor SDK 3.1.409: 565/565;
- JSON de auditoria SHA-256:
  `8834BC7F8DB7858B730104A1813B46D890094053B15B0A1F8E5C164B27686CC5`;
- CSV de auditoria SHA-256:
  `07D9243A1362F067A9832345FFF5CCC93D8FF5CC409558FAA9146C93430572BD`.

## Despliegue controlado

- imagen Game preservada:
  `sha256:0a647c2e16376e1ec1bfabe3c182afdb2d69280eb1fd973740242c4012064453`;
- contenedor Game:
  `ada451a3f67a93d28d6b693ace0e041dddfe930d42a684afaf4a2a9652195b2a`;
- mount:
  `compact-8.0-runtime-archery-v4.sqlite3 -> /app/Data/compact.sqlite3`;
- Login preservado: `72a1b87ae15badcd6fcdf1bdbd99819db84707a980d8fbf47c58bd12b01a8406`;
- MySQL preservado: `48ab25a4d483901da9ec9e05a5588eb81dbfb8eee94a56083550a2ddae14d89a`;
- rollback: `aaemu-game:rollback-pre-archery-executable-v2-20260807`;
- `RestartCount=0`, puertos 2239/2250 abiertos, cero errores/fatal y registro
  correcto en Login.

Baseline V5:

- `runtime-captures/native-skill-live-baseline-v5.json`, SHA-256
  `31E0D50D31EB7D2A3C1B929028942D7B8697715FE107F9268B8E7D8E941C36C2`;
- CSV SHA-256
  `03710B80A4B03BD134280DD8AD5E5B92D8FFEFEE8DA0840D30C021D792A275C6`;
- un arranque, cero ejecuciones, cero snapshots pasivos y cero errores.

## Estado y siguiente gate

Archery queda `automatic_verified`, no `live_accepted`. Sorcery ya completo
S1/S2 y esta `live_accepted` al 100%. El gate A0 de Archery registro 12
confirmaciones de aprendizaje de activas y las seis pasivas AA8, sin errores
en la ventana ni reinicios de Game. Los detalles quedan en
`CHECKPOINT_ARCHERY_LIVE_LEARNING_V5.md`.

El siguiente tramo es A1-A5 segun
`reconstruccion_skills_8/LIVE_ACCEPTANCE_SORCERY_ARCHERY_V1.md`.

La animacion o el tooltip no sustituyen las lineas autoritativas de dano,
mutacion de HP y snapshots `[AA8ArcheryPassive]`.
