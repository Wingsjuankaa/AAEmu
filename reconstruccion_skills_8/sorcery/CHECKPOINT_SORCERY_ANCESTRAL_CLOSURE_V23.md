# Checkpoint Sorcery ancestral closure V23

## Resultado

V23 cierra las dos variantes ancestrales de Sorcery que conservaban animacion,
area y consumo, pero no aplicaban dano:

- Gods' Whip: Wave, skill `39674`, plot `3778`;
- Flame Barrier: Mist, skill visible `41223`, skill interno `41478`.

Son fallos distintos. Gods' Whip requeria corregir una primitiva espacial del
emulador. Flame Barrier requeria restaurar una clausura de datos AA8 que la
compact activa no habia proyectado.

## Gods' Whip: causa y reparacion

El evento AA8 `33384` usa `RandomArea`, radio maximo `p3=4000` y genera ocho
rayos. El emulador V22 colocaba cada punto exactamente a 4 m del centro. Dos
segundos despues, el evento `33388` buscaba objetivos con el cubo AA8 `14282`
de 4x4 m alrededor de cada punto. Los objetivos agrupados en el centro
quedaban fuera de todos los cubos, por eso los logs mostraban ocho eventos
visuales y ocho consultas `targets=0`.

La implementacion historica anterior a `bd90e0b7` ya sorteaba una distancia
entre cero y el radio maximo. V23 restaura ese contrato: `RandomArea` muestrea
todo `[0,p3]`, conserva el angulo aleatorio y mantiene sin cambios la
correccion de terreno V22.

La correccion es transversal y tambien beneficia otras variantes que usan
`RandomArea`, por ejemplo los fragmentos Wave de Chain Lightning.

## Flame Barrier: clausura AA8 recuperada

El flujo vivo confirmado era:

`41223 -> buff 24583 -> trigger 42478 -> skill 41478 -> plot 4049 -> doodad 13919 -> clout 3792`

El clout ya tenia duracion, forma, slow y tick correctos, pero
`doodad_func_clout_effects` estaba vacia en la compact. Por ello el campo
aplicaba `buff 24584` de movimiento y no creaba el dano periodico.

El crosswalk r575 mostro primero el candidato `3792 -> 76542`, pero se mantuvo
como comparativo hasta agotar AA8. La consulta AA8 estaba documentada en
`x2game.dll!FUN_39893750` con layout `68 68`, aunque Stage 50 no habia
decodificado su resultado.

Se recupero el limite exacto en `game11`:

- inicio `0x8AAEF32`;
- fin `0x8AB0A32` (`SQLITE_DONE`);
- 768 relaciones unicas;
- SHA-256 canonico de filas
  `47D2CFF5B1C7753445B58223DFAC000AC9EA2BFA7F2B1A841D5DA3DE39873C8E`;
- relacion AA8 exacta `clout 3792 -> effect 76542`.

Las 768 relaciones AA8 coinciden con r575 y no existe ninguna fila AA8
divergente. Esto convierte el candidato de crosswalk en una relacion nativa
AA8 demostrada.

Stage 50 completa el grafo exacto:

`3792 -> effect 76542 -> BuffEffect 29874 -> buff 24585 -> buff_tick_effect 4167 -> effect 76543 -> DamageEffect 12209`

El buff `24585` dura 4000 ms y pulsa cada 1000 ms. `DamageEffect 12209` es
magico, usa `dps_inc_multiplier=6`, `level_md=7` y el bonus AA8 de 41% contra
el tag objetivo `104`. Tambien se restauraron los cuatro `tagged_buffs` AA8
del buff.

No se importo balance 10.x. Todas las filas de runtime proceden de resultados
cacheados AA8; r575 se uso solo para reducir el vacio y orientar la busqueda.

## Artefactos

- constructor: `build_sorcery_runtime_v23.py`;
- compact: `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-sorcery-v23.sqlite3`;
- SHA-256 compact:
  `B6E139D0E6953EE3F7BEAB015E770C9A7D5A270A45978E55016A0324B60CEBC0`;
- manifiesto: `generated/sorcery-runtime-v23.manifest.json`;
- imagen Game:
  `sha256:1e3244671935a5d98778e48e0f78a0112163208f8fc0c2353e28f7c426dd63cb`;
- rollback V22: `aaemu-game:rollback-pre-sorcery-closure-v23-20260806`,
  imagen `sha256:0a463d34c005df94cefd94d668d41e6c10c1c0c533c237c047bc925ec8e6c26a`.

## Verificacion

- pruebas focales de altura y radio RandomArea: 11/11;
- suite completa Docker SDK 3.1.409: 531/531;
- compact `quick_check=ok`, `integrity_check=ok`;
- Game inicia con la compact V23, cero reinicios;
- puertos 2239 y 2250 escuchando;
- Login y MySQL no fueron recreados.

## Aceptacion viva pendiente

1. Gods' Whip: Wave debe causar dano en los rayos que intersecten objetivos,
   conservando altura de terreno y ocho pulsos.
2. Flame Barrier: Mist debe aplicar el slow al entrar y el dano periodico del
   buff `24585` mientras el objetivo permanece o conserva el buff.
3. Verificar el bonus de dano contra un objetivo Electrocute y que el cliente
   no se desconecte durante todo el ciclo.

## Instrumentacion y despliegue de aceptacion

La imagen de aceptacion incorpora una traza compartida sin cambiar la
semantica de Sorcery. Los eventos `[AA8SorceryLive]` fijan el ciclo de vida de
la skill y `[AA8SkillDamage] tree=sorcery` fija efecto, dano, absorcion, HP
antes/despues y emision del paquete.

- Imagen Game activa:
  `sha256:830ae0be2c3014b3bbc4b06c817bf9b86df607cfa1445793141024bb32697af5`.
- Rollback inmediato:
  `aaemu-game:rollback-pre-periodic-origin-trace-v5-20260807`, imagen
  `sha256:cce2632b4b717c23d888b333eee44da8bbcb6b836530eb844d2e708dac1a995e`.
- Suite completa SDK 3.1.409 con compact Archery V1 montada: 547/547.
- Regresion de clausura ancestral: 4/4 sobre Sorcery V23 y 4/4 sobre el
  runtime compuesto Archery V1.
- Game inicio en 93,55 s, escucha 2239/2250 y permanece con cero reinicios.
- Login y MySQL no fueron recreados.

El orden de prueba obligatorio esta documentado en
`reconstruccion_skills_8/LIVE_ACCEPTANCE_SORCERY_ARCHERY_V1.md`. No se cerrara
Sorcery por evidencia visual aislada: Gods' Whip Wave y Flame Barrier Mist
deben demostrar reduccion de HP en la traza viva.

La regresion durable
`test_sorcery_ancestral_closure_v23.py` fija el camino RandomArea de Gods'
Whip hasta sus seis ramas de `DamageEffect` y la cadena de Flame Barrier hasta
el tick 12209. Se ejecuta tanto contra V23 como contra cualquier runtime
compuesto que deba heredar Sorcery.

Los ticks creados mediante `CastBuff` conservan su skill en `Buff.Skill`. La
instrumentacion V2 recupera esa referencia solo al emitir la traza de dano;
no la inyecta en `EffectSource` ni altera calculo, combat dice o modifiers.
Esto garantiza que Flame Barrier pueda ser observada como skill interna 41478
sin cambiar su conducta.
