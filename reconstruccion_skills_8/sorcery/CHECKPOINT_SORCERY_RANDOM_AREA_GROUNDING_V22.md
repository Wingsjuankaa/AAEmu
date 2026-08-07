# Checkpoint Sorcery RandomArea grounding V22

## Resultado implementado

V22 corrige la altura de los impactos visuales generados por `RandomArea`.
La variante Wave de Gods' Whip 39674 y la variante Wave de Meteor Strike
36478 compartian el mismo defecto: sus impactos se construian exactamente
8 metros sobre el punto anterior, aunque el dano autoritativo podia encontrar
objetivos por coordenadas XY.

La nube principal de Gods' Whip no se modifica. Esa usa el metodo `Area` y su
offset propio de 2 m; V22 afecta solamente el metodo `RandomArea` comun a los
rayos y meteoros secundarios.

## Causa demostrada

Los eventos AA8 33383 y 33384 de Gods' Whip 39674 y el evento 24363 de
Meteor Strike 36478 contienen `target_update_method_param3=4000` y
`target_update_method_param4=8000`.

El emulador heredado llamaba `HeightOffset` a p4 y ejecutaba:

`previous_z + p4 / 1000`

Por ello p4=8000 producia de forma determinista el desplazamiento observado
de +8 m. El nombre y la semantica estaban marcados como no confirmados desde
el cambio historico `bd90e0b7`; la implementacion anterior a ese cambio no
sumaba p4 a Z.

## Evidencia AA8 y reduccion de vacios 10.x

- AA8 identifica 39674 con plot 3778, nube doodad 13407 e impactos doodad
  13406; el ciclo de vida y el dano ya estaban confirmados en vivo.
- AA8 identifica 36478 con plot 2944 y el mismo par p3=4000/p4=8000.
- El crosswalk AA8->10.x r575 clasifica el evento 33383 como
  `exact_id_exact_relation` y 33384 como `stable_id_changed_properties`; sus
  parametros p3/p4 permanecen exactos.
- El crosswalk confirma continuidad de valor y relacion, pero no autoriza a
  importar una semantica 10.x ni una etiqueta de balance.
- Los dossiers Stage 15 de los loaders x2game.dll x64 0x3e7a30 y 0xa75720
  confirman la lectura de las filas, pero no exponen un consumidor con nombre
  semantico para p4.

La autoridad sigue siendo AA8: evidencia visual viva, datos AA8 y la historia
del consumidor demuestran que p4 no es un offset vertical aditivo.

## Politica V22

`PlotTargetRandomAreaParams.TargetUpdateMethodParam4` pasa a llamarse
`TerrainCorrectionLimit`. El nombre nativo exacto aun es opaco, por lo que el
codigo documenta esa frontera.

Para un punto sintetico `RandomArea`:

- con heightmaps desactivados se conserva la Z del objetivo anterior;
- con heightmaps activos se usa la altura del terreno si la correccion
  vertical cabe dentro de `abs(p4)` milimetros;
- si el terreno queda fuera de esa tolerancia se conserva la Z original, para
  no arrastrar al suelo efectos genuinamente aereos.

Esto interpreta el 8000 observado como limite de correccion del terreno, no
como orden de elevar todos los impactos 8 m.

## Verificacion automatica

- pruebas focales `PlotRandomAreaHeightTests`: 4/4;
- suite completa: 524/524;
- build Docker SDK 3.1.409: correcto;
- imagen V22: `sha256:0a463d34c005df94cefd94d668d41e6c10c1c0c533c237c047bc925ec8e6c26a`;
- rollback V21: `aaemu-game:rollback-pre-random-area-grounding-v22-20260806`,
  imagen `sha256:ee11184c2efe2782b821286d6e6951c26bcd870a56f0de8db37a0f9b67b2d5bd`.

## Aceptacion viva pendiente

Probar en el mismo terreno inclinado:

1. Gods' Whip 39674 variante Wave: los rayos deben terminar en el suelo y
   conservar dano/ticks.
2. Meteor Strike 36478 variante Wave: el meteoro debe terminar en el suelo y
   conservar su dano.
3. Confirmar que la nube de Gods' Whip mantiene su altura visual prevista.

