# Honor por matar NPCs: diagnóstico, 2026-09-16

**Estado: origen de los 200 identificado; elegibilidad de cualquier NPC pendiente
de confirmación nativa. No se cambia gameplay, configuración, saldos ni runtime.**

El usuario reporta 200 puntos al matar mobs, tanto en su personaje como en la cuenta
de otro probador, `davidwings`. No confundir ese nombre de cuenta con un nombre de
personaje: no aparece como personaje en la consulta efectuada.

## Hechos comprobados

- `premium_grades`: grado interno 6, umbral 400, buff 7153 (ArcheLife 5).
- `unit_modifiers`, fila 32057: buff 7153, atributo 128
  `HonorPointGainNpcKill`, tipo Value, valor **200**. La descripción coreana del
  buff también especifica 200 puntos adicionales por caza de monstruos.
- Estos datos coinciden entre la SQLite completa AA10 y la compact montada.
- `Configurations/CharacterSettings.json`, tanto fuente como archivo visible en
  el contenedor: `ForceMaxPremiumGrade=true`. La configuración ya estaba presente
  en 45bba0ad4 (2026-09-11), anterior al merge que incorporó la entrega de honor.
- Runtime: `SCUpdatePremiumPoint point=400 grade=6 (forceMaxGrade=True, maxGradeId=6,
  chars=3)` para la sesión revisada. Dannia tiene 400 puntos premium persistidos.
- El commit comunitario cd4dfe635 añadió `AwardNpcHonor` a las ramas de muerte
  individual y de grupo. La integración c50ffacca lo incorporó al fork; el primer
  padre de ese merge no contiene esa recompensa.
- La fórmula actual suma el bono incluso con recompensa base cero:
  `(honor del NPC + bono plano) * (100 + bono porcentual) / 100`.
  Por tanto, `0 + 200` da exactamente el síntoma reportado, sin necesitar
  corrupción del catálogo ni un multiplicador accidental.
- 19.434 NPCs del catálogo tienen `honor_point=0`; 88 tienen valores positivos.

## Qué no está demostrado

Que exista el atributo/tooltip no demuestra la condición de elegibilidad del
servidor retail. Falta cerrar si el bono debe concederse por NPCs sin honor base,
o si existen condiciones de nivel, tipo de NPC, zona o límites adicionales.
No se encontró una prueba suficiente para añadir un guard `HonorPoint > 0`:
sería una nueva regla plausible, no una corrección nativa demostrada.

La búsqueda histórica localizó una reproducción del anuncio oficial coreano de
2021-10-28, efectivo el 2021-12-02, que enumera el beneficio +200 por caza:
https://www.inven.co.kr/board/archeage/3263/6041
La página no especifica qué monstruos califican. Se registra como
`external_unresolved`; no se usa para afirmar equivalencia retail del reparto
universal ni como prueba técnica del gate. Tampoco se extrapolan reglas de WAR,
Unchained o servidores privados de otra versión.

Conclusión operativa: **función premium real activada por la integración;
aplicación universal todavía no validada**. No declarar automáticamente que todo
lo observado es correcto, ni retirar la recompensa o Patron sin cerrar esa
frontera. No se descontó honor ganado a ningún jugador.

Evidencia: `E:/AAEmu/rama_10/artifacts/npc-honor-20260916/diagnosis.json`,
`game-before.log`, `Npc-before-merge.cs`, `upstream-honor-introduction.patch`.
Imagen observada: `sha256:ad5d5587b08ac18ed0785eed8c799026a1329aba42f523b615cfc646308b3ae6`.
Target `rama_10`, HEAD b22b3ccfc, padre exacto
`upstream/client_version/zone-10.0.2_r575` b439e1cc0. Consulta de reportes `npc`: vacía.
