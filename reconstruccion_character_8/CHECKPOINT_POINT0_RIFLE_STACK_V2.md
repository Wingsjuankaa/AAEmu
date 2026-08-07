# Checkpoint — Point 0 Shoot Rifle stack V2

Fecha: 2026-07-31  
Autoridad: ArcheAge Kakao 8.0.3.12 r558734  
Estado: segundo retest manual fallido; reemplazado por V3.

El segundo retest confirmó que el requisito de arma ya se supera, pero la
skill continúa mostrando sólo GCD, sin animación ni daño. El corte restante
se documenta y corrige en `CHECKPOINT_POINT0_RIFLE_STACK_V3.md`.

## Evidencia del primer retest

Los logs confirmaron múltiples paquetes `CSStartSkill 46938` aceptados desde
`Dannia`. Cada intento produjo directamente `SCPlotEnded`; no apareció ningún
evento de plot, animación o daño. La entrada de protocolo, la skill y el árbol
5796 estaban cargados correctamente.

El primer corte del árbol ocurre en el evento `52244`, cuya condición nativa es:

- `kind_id=6`: `WeaponEquipStatus`;
- `param1=5`;
- `not_condition=0`.

El backend sólo comparaba ese parámetro con `WeaponWieldKind`, dominio que
termina en 3 y describe únicamente las manos principal/secundaria. Por ello el
valor 5 fallaba siempre.

## Autoridad del estado 5

En el corpus AA8, los ocho plots alcanzables que usan
`WeaponEquipStatus=5` pertenecen exclusivamente a skills Archery/Gunslinger
con `active_weapon_id=2`: plots 2957, 4046, 4047, 5389, 5699, 5730, 5732 y
5796. Shoot Rifle además declara `weapon_slot_for_autoattack_id=17`, que es la
ranura física `EquipmentItemSlot.Ranged`.

La reparación conserva las filas nativas sin modificaciones y amplía el
evaluador genérico:

- estados 1–3: se mantiene la comparación de arma de una mano, dos manos y
  dual wield;
- estado 5: requiere un `WeaponTemplate` equipado en `Ranged`;
- cualquier estado desconocido falla cerrado.

## Validación

- Pruebas focalizadas `PlotWeaponEquipStatusTests`: 5/5 aprobadas.
- Suite completa .NET SDK 3.1.409-focal: 310/310 aprobadas.
- Compilación Docker: correcta, imagen
  `sha256:3585bbbbb37691aabc03ad0dac04a42e2e8a6b883f1dce413c2c953fe56f98d4`.
- Runtime montado preservado:
  `503BF9639F2005130C9E63A66A443AEA09577C082D7CE8EDC8AB11DA9118B77A`.
- `main_world` y 54/55 heightmaps cargados.
- Script compiler: 0 errores.
- Puertos 2239/2250 y registro en LoginServer confirmados.
- Arranque sin nuevos errores, excepciones ni fatales.

## Próxima interacción autorizada

Entrar con `Dannia`, equipar el rifle, seleccionar un único mob a no más de
15 m y pulsar `Shoot Rifle` una sola vez. Detenerse después del disparo e
informar por separado animación, proyectil/impacto y daño/vida del objetivo.
