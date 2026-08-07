# Backlog de fallos del punto 0

Lote de reparación transversal validado manualmente desde creación de personaje.
Estados: `reportado -> evidenciado -> diagnosticado -> en_lote -> listo_para_retest -> validado`.

## Lote P0-A

| ID | Área | Síntoma | Estado |
|---|---|---|---|
| P0-0001 | Creación / barra | Sólo aparece Triple Slash; faltan acciones básicas y raciales iniciales | `validado` |
| P0-0002 | Skills / animación | Melee Attack aplica daño pero no reproduce animación | `validado` |
| P0-0003 | NPC / terreno | Numerosos mobs aparecen flotando sobre el terreno | `validado` |
| P0-0004 | Skills / rifle | Shoot Rifle no ejecuta animación, proyectil ni daño | `validado` |

## P0-0001 — Barra inicial incompleta

Observación: `Dannia`, Nuian femenina, Battlerage, recibe únicamente Triple Slash.
El libro de habilidades sí expone Melee Attack, Kick, Shoot Arrow, Shoot Rifle,
Dash, Escape y las raciales Nuian.

Causa demostrada: el generador V2 interpretó la ausencia de filas en
`default_action_bar_actions` como una barra vacía salvo la habilidad elegida.
La autoridad AA8 omitida estaba en `default_skills.add_to_slot/slot_index` y en
la relación `character_default_skills` que selecciona las raciales de cada
plantilla. Para Nuian femenina corresponden `35420` en ranura 17 y `35418` en
ranura 18. Algunas plantillas sólo marcan una racial con `add_to_slot=1`; esa
ausencia se conserva. Las once acciones globales ocupan 10, 11, 13–16, 19, 20
y 22–24.

Reparación: reconstruir las 217 ranuras de las 96 combinaciones; conservar la
habilidad elegida en ranura 1, agregar globales y sólo las raciales relacionadas
con la plantilla. No modificar habilidades aprendidas ni puntos de habilidad.

Validación manual final: `Wingsjuanka`, Nuian masculino Battlerage creado desde
cero, mostró las 14 acciones esperadas en sus posiciones nativas. La salida
limpia y la reconexión conservaron la barra; MySQL guardó las 217 ranuras, 14
no vacías, en 329 bytes. `Dannia` conservó su barra anterior y confirma que el
bootstrap no reemplaza barras persistidas.

## P0-0002 — Melee Attack sin animación

Observación: la skill básica `2` causa daño correctamente, pero el personaje no
anima el golpe.

Causa demostrada: `SCSkillFiredPacket` envía correctamente el `fire_anim_id`,
pero la fila runtime de la skill 2 tiene `fire_anim_id=0` y
`weapon_slot_for_autoattack_id=15`. El servidor ignoraba las animaciones nativas
del `holdable` equipado. Para el arma inicial de Dannia, holdable 6, AA8 define
una selección 50/50 entre animación 87 y animación 3.

Reparación: cargar `anim_r1/r2/r3` y sus ratios desde `holdables`; cuando una
skill de autoataque no tenga animación propia, resolverla desde el arma de mano
principal y usar holdable 0 para combate sin arma. No se introduce un hardcode
por ID de skill.

Evidencia: dossier nativo `skill-2.json`, SHA-256
`9FB31F29AD90AC29C9A192E33869A7803A372D93EC92963580584B8D20B8FAEC`.

## P0-0003 — NPC terrestres flotando

Observación: varios mobs, incluido un Solzreed Fox, aparecen elevados respecto
del suelo. `develop` contiene una corrección relacionada.

Compatibilidad demostrada: el arreglo original de `develop` corrige un spawn
terrestre con el heightmap sólo cuando la diferencia es menor que 1 metro. La
rama AA8 ya posee lector de heightmaps del `game_pak` 8.0.3.12, pero estaba
desactivado. El runtime AA8 también trae `actor_models.fly_mode`, campo que el
servidor aún no cargaba. La solución estructural posterior de `develop` no es
portable completa porque esta rama no tiene su arquitectura `WorldCell/BAI`.

Reparación compatible: habilitar el heightmap del cliente AA8, cargar
`fly_mode`, conservar NPC voladores y corregir únicamente NPC terrestres cuya
diferencia absoluta con el terreno sea `< 1 m`. Spawns sobre puentes, muelles o
estructuras con una separación igual o superior a 1 metro conservan su Z.

Validación manual: el usuario confirmó que los mobs terrestres ya apoyan sobre
el terreno con el runtime P0-A.

## P0-0004 — Shoot Rifle no ejecuta su ataque

Observación: la skill básica `46938` aparece en el libro de habilidades y su
tooltip AA8 describe un ataque de rifle de alcance 15 m y 60 % del ataque a
distancia, pero al usarla no ocurre ninguna acción.

Causa demostrada: la fila nativa de la skill está presente y define
`plot_only=1`, `plot_id=5796`, arma a distancia en ranura 17 y auto-fire. El
runtime P0-A no contenía el plot 5796 ni ninguno de sus eventos; por tanto, el
servidor iniciaba una skill cuyo único camino de ejecución estaba vacío.

Reparación: incorporar de forma aislada la clausura AA8 nativa del plot 5796:
16 eventos, 15 transiciones, 17 efectos de plot, condiciones de alcance/azar/
estado/variables, cinco formas AoE, tres daños a distancia con multiplicador
0,6, trece efectos especiales, animación 1074 y proyectil 1347. No se usa ni se
conserva fallback histórico 3.0.

Segunda barrera demostrada por el primer retest: `Dannia` envió múltiples
`CSStartSkill 46938` y el servidor respondió sólo `SCPlotEnded`, sin ejecutar
ningún evento visible. El evento nativo `52244` exige
`WeaponEquipStatus=5`. El backend sólo reconocía los estados 1–3 de armas de
mano y rechazaba siempre el estado AA8 de arma a distancia. Los ocho plots
AA8 que usan el valor 5 pertenecen exclusivamente a skills Archery/Gunslinger
con `active_weapon_id=2`, incluido Shoot Rifle.

Reparación backend V2: conservar intacta la condición nativa y ampliar el
evaluador genérico para que el estado 5 compruebe una definición `Weapon` en la
ranura física `EquipmentItemSlot.Ranged`. Los estados 1–3 conservan su
comportamiento y cualquier estado desconocido falla cerrado.

Tercera barrera demostrada por el segundo retest: el estado 5 ya se supera,
pero el planificador acumulaba los efectos de todos los eventos de retraso cero
y evaluaba sus hijos antes de ejecutarlos. El evento `52251` selecciona hasta
tres objetivos y asigna `A = Targets`; el evento inmediato `52260` comprueba
`A == 0`. Como la asignación seguía pendiente, la condición leía el cero
inicial y terminaba el plot antes de la animación `1074`, el proyectil `1347`
y los efectos de daño.

Reparación backend V3: ejecutar y emitir cada evento aprobado antes de evaluar
o programar sus hijos. Es una corrección genérica del orden causal de plots;
no introduce excepciones por skill y también protege otras ramas AA8 que
dependen de variables o estado producido por el nodo anterior.

Evidencia: dossier nativo `skill-46938.json`, SHA-256
`D4F2864A52CD42BCE51A6AAB9A928702A50904DE98047A6D5DD0E0C40A9515FB`;
catálogo cerrado `native-basic-rifle-v1.json`, SHA-256
`DFD8602EBCE097D2A50E50A963F1F0031AC4BBB87326D2EEF8AAE0C515777A73`.

Estado de despliegue: runtime determinista
`compact-8.0-runtime-point0-rifle-stack-v1.sqlite3`, SHA-256
`503BF9639F2005130C9E63A66A443AEA09577C082D7CE8EDC8AB11DA9118B77A`,
montado en `game` y validado manualmente.

Validación manual final: el usuario confirmó con `Dannia` que Shoot Rifle
funciona y que la animación quedó reparada. P0-0004 se considera cerrado. El
checkpoint V3 conserva los componentes que deben reutilizarse como base del
futuro lote de Gunslinger sin extrapolar mecánicas no demostradas.

## Criterios del retest P0-A

- Un personaje nuevo recibe habilidad inicial, once acciones básicas globales y
  exactamente las raciales de su plantilla marcadas con `add_to_slot=1`.
- La barra persiste tras reconexión y no se sobrescribe después de editarla.
- Melee Attack anima el arma equipada y sigue aplicando el daño una sola vez.
- Los mobs terrestres cercanos al suelo apoyan sobre el terreno; NPC voladores y
  spawns claramente elevados no son desplazados.
- El servidor carga el heightmap AA8 sin errores y supera pruebas automatizadas,
  compilación y verificaciones SQLite.

Resultado final del lote: todos los criterios fueron aceptados por el operador
el 2026-07-31. P0-A queda cerrado como `validado satisfactoriamente`.
