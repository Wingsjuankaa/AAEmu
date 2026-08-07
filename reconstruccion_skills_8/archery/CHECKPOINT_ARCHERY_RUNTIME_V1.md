# Checkpoint Archery Runtime V1

## Estado

Archery queda `automatic_verified` para ArcheAge Kakao 8.0.3.12 r558734. Las
35 skills nativas, las seis pasivas y la clausura ancestral estan cargables.
La promocion a `live_accepted` depende de la matriz de prueba dentro del
cliente.

## Causas raiz reparadas

1. La portadora Sorcery V23 contenia las 35 filas `skills`, pero omitia las
   seis filas `passive_buffs` de Archery.
2. Grandes segmentos de los plots ancestrales 2927, 2928, 2941 y 2942 no
   estaban materializados. Concussive Arrow: Mist 36471 apuntaba a plot 2941,
   pero el plot faltaba; el cliente podia mostrar costo/visual sin que el
   servidor alcanzara su dano.
3. `BubbleEffect` estaba registrado y cargado, pero `Apply` era un no-op. Se
   implemento `SCChatBubblePacket` y el envio localizado por ID al objetivo.
4. El extractor consideraba cada `ProjectileAnim (38)` una dependencia de la
   tabla servidora `anims`. Los nueve IDs ausentes eran presentacion cliente;
   las quince relaciones que los usan tienen `add_anim_cs_time=0`. Se separo
   esa evidencia de los `Anim (34)` realmente consumidos por el scheduler.
5. `native_combat_skill_status` aun marcaba raices como `quarantined`. El
   constructor solo las habilita despues de que el grafo V0.40 confirma
   35/35 como `enabled`.
6. El subtipo nativo `SpecialEffect 158` no estaba nombrado ni consumido. AA8
   demuestra que es `charge_cooldown`; las skills 11368, 13281, 38893 y 42851
   conservan `charge_count` y `charge_cooldown_time`. El cargador ahora
   preserva ambos campos y reconoce el descriptor 158 sin inventar un paquete
   ni una politica de rechazo servidora que AAEmu tampoco aplica al cooldown
   ordinario.
7. La clausura por tablas con `id` no detectaba `unit_reqs`, cuya identidad es
   compuesta por owner. AA8 conserva doce requisitos Archery: once
   `equip_ranged` (kind 29, arco) y un `no_buff_tag` (kind 30, tag 27). El
   servidor no cargaba ni evaluaba ninguno. Ahora consume ambos contratos,
   distingue arco (holdable 19) de shotgun (31), conserva los resultados
   nativos `UrkEquipRanged`/`UrkNoBuffTag` y hereda el requisito de la skill
   base cuando se ejecuta una sucesora ancestral. Las ramas OR con un tipo aun
   opaco permanecen abiertas para no convertir evidencia parcial en rechazo.

La auditoria final de subtipos alcanzables reviso 632 `special_effects` de la
clausura Archery. Los tipos 34-38, 35/36, 63 y sus equivalentes de FX,
proyectil y texto son descriptores de presentacion consumidos por el cliente;
no se promovieron como falsos backends servidores. Los caminos servidores de
dano, buff, dispel, targeting, variables, sigilo y cooldown tienen consumidor.
El unico contrato perdido adicional demostrado fue el tipo 158 anterior.

La segunda auditoria, ya fuera de la clausura por `id`, fijo tambien las
relaciones owner-keyed de las 35 raices: 32 `skill_modifiers`, siete
`skill_req_skills`, tres `skill_visual_groups` y doce `unit_reqs`. Sus hashes
canonicos forman parte del manifiesto. `skill_modifiers` ya tiene consumidor
servidor para owners Buff; `skill_req_skills` y `skill_visual_groups` son
metadatos de aprendizaje/presentacion del cliente. El unico consumidor
servidor ausente que afectaba el uso de la rama era `unit_reqs`, reparado en
V1.3. Los modifiers de owner Item con contexto dinamico siguen en la
cuarentena transversal preexistente y no se reinterpretaron como parte de la
rama.

## Autoridad y crosswalk

- Grafo AA8 V0.40: `42F2369F...9719C`.
- Consolidada AA8 V0.40: `A3AB85F0...48559`.
- Crosswalk V1: `44CFFDAF...1A71`.
- Catalogo nativo actualizado: `A6F255B0...CF81`.
- Filas seleccionadas: 4.638.
- Comparadas por crosswalk: 4.638; no comparadas: 0.
- Clasificaciones: 3.931 exactas, 699 con propiedades cambiadas y 8
  conflictos de `plot_next_events`.
- Filas 10.x promovidas al runtime: 0. Los ocho conflictos quedaron resueltos
  por las filas AA8, no por datos r575.

## Artefactos

- Constructor: `build_archery_runtime_v1.py`.
- Pruebas: `test_archery_runtime_v1.py`.
- Manifiesto: `generated/archery-runtime-v1.manifest.json`.
- Compact: `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-archery-v1.sqlite3`.
- SHA-256 compact: `67D1A8812B9261AE90A4B7159652D04BACBA2420C7E1896696B69C44E3EFBAA6`.
- Tamano: 141.053.952 bytes.

## Verificacion automatica

- Grafo de especializacion: confirmado, cero eventos fallidos y cero filas sin
  clasificar.
- Auditoria downstream: 35 enabled, 0 quarantined.
- Runtime Archery: 14/14 pruebas.
- Requisitos focales C#: 7/7.
- Trazas focales Sorcery/Archery: 5/5.
- Suite AAEmu SDK 3.1.409 con compact candidata montada: 547/547.
- Herencia Sorcery V23 en el runtime compuesto: 4/4.
- Resumidor de trazas vivas: 3/3.
- SQLite `quick_check=ok`, `integrity_check=ok`.
- Rollback: `aaemu-game:rollback-pre-archery-v1-20260807`, imagen
  `sha256:1e324467...c426dd63cb`.

## Despliegue V1.4

- Imagen Game activa:
  `sha256:830ae0be2c3014b3bbc4b06c817bf9b86df607cfa1445793141024bb32697af5`.
- Rollback inmediato previo a la instrumentacion:
  `aaemu-game:rollback-pre-periodic-origin-trace-v5-20260807`, imagen
  `sha256:cce2632b4b717c23d888b333eee44da8bbcb6b836530eb844d2e708dac1a995e`.
- Compact montada de solo lectura:
  `/app/Data/compact.sqlite3` desde `compact-8.0-runtime-archery-v1.sqlite3`.
- Game inicio final en 93,55 s, escucha 2239/2250, registro correcto en Login y cero
  reinicios. Login y MySQL conservaron contenedor, imagen y uptime.
- El error unico de concurrencia preexistente en `TransferManager.GetTransfers`
  durante el spawn no reinicio el proceso y queda fuera del cambio Archery.

## Matriz viva pendiente

Probar en el cliente, como minimo:

1. aprender y remover las seis pasivas, verificando cambio de estadisticas;
2. ejecutar las doce activas base en objetivo unico y AoE;
3. activar/resetear y reloguear las doce variantes ancestrales;
4. confirmar dano y burbuja de Concussive Arrow: Mist;
5. validar proyectil, dano, numero de impactos y estabilidad de Endless
   Arrows, Missile Rain y Snipe;
6. cancelar casts/movimiento y comprobar que no queda impacto tardio;
7. verificar cooldown, costo, combos, marcas y ausencia de desconexiones.
8. con arco equipado, confirmar activas base y sucesoras ancestrales; luego
   retirar el arco y comprobar rechazo nativo inmediato, sin gasto de MP,
   cooldown ni impacto tardio.

Sorcery V23 permanece como base del artefacto, por lo que este runtime no
revierte ninguna de sus reparaciones.

## Trazabilidad viva

Las 35 raices exactas de Archery estan en una allowlist cerrada. Para ellas,
`[AA8ArcheryLive]` registra request, resultado, eventos del plot, cancelacion y
fin; `[AA8SkillDamage] tree=archery` registra efecto, dano calculado,
absorcion, HP antes/despues y emision del paquete. Esto permite separar un
fallo de datos o targeting de un fallo puramente visual del cliente.

La matriz se ejecuta una interaccion por vez siguiendo
`reconstruccion_skills_8/LIVE_ACCEPTANCE_SORCERY_ARCHERY_V1.md`. El estado
permanece `automatic_verified`; la traza no sustituye el gate vivo.

Los 12 botones base, 12 sucesoras ancestrales, seis pasivas y once filas
internas quedaron separados por ID y contrato en
`reconstruccion_skills_8/archery/ARCHERY_LIVE_MATRIX_V1.md`.
