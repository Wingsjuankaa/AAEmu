# Checkpoint Battlerage V10 — cierre vivo de primera etapa

Fecha: 2026-08-09  
Cliente: ArcheAge Kakao 8.0.3.12 r558734  
Rama: `client_version/8.0.3.12-kakao-r558734-port`

## Decisión

Battlerage queda **cerrada y aceptada en primera etapa**. El usuario confirmó
que todas las familias de la rama funcionan con el comportamiento visual y
funcional esperado después de los cierres V2–V9.

Este estado significa:

- 12 familias activas visibles probadas;
- variantes ancestrales y cadenas internas relevantes probadas;
- 3 skills automáticas presentes y funcionales en el alcance de etapa 1;
- 6 pasivas presentes, con sus efectos observables principales;
- daño, control, buffs, movimiento, presentación, combos, multigolpe y
  cooldown sin blockers conocidos de primera etapa;
- regresiones cruzadas de Sorcery y Archery preservadas durante el cierre.

No significa todavía una certificación exhaustiva de todas las combinaciones
de arma, latencia, segundo cliente, persistencia prolongada, muerte/cambio de
zona o cada condición poco frecuente. Esas combinaciones pertenecen a una
etapa de robustecimiento posterior y no reabren este cierre inicial mientras
no aparezca evidencia contraria.

## Artefacto y runtime aceptados

- compact: `compact-8.0-runtime-battlerage-v5.sqlite3`;
- SHA-256:
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- imagen Game V9:
  `sha256:8dd98d44d5d814e95509a297e007dbccf0073fc969a3b2898f174420cc8119ac`;
- DLL:
  `B8C90AB0374D4CC56F495FAE8CBE30A6D25DEEA931E985F8F77CE6BF41CD3B3C`;
- rollback:
  `aaemu-game:rollback-pre-endless-feedback-v9-20260809`;
- servidor: scripts `0 errors`, puertos `2239/2250`, registro exitoso en
  LoginServer y `RestartCount=0`.

## Evidencia automática final

- suite .NET 3.1: `627/627 PASS`;
- tests dirigidos Combo/admisión: `8/8 PASS`;
- Mechanics Lab Battlerage: `25/25 PASS`;
- escenario Endless Arrows de regresión cruzada: PASS, hash
  `4C3FABEF40F81A6BE2AED2343BADE273BE2A01B916CDC738C77D7F3F1806A4D1`;
- validadores Battlerage: `11/11 + 6/6 PASS`;
- Archery estructural: `17/17 PASS`;
- SQLite: `quick_check=ok`, `integrity_check=ok`;
- builds del runtime: byte a byte deterministas.

## Qué ya existía antes de Battlerage

Para no atribuir como novedad conocimiento heredado:

| Rama previa | Contratos ya aprendidos |
|---|---|
| Sorcery | Combo dirigido por cliente; cancelación de plots con `skillTlId/plotTlId`; cierre de carriers AoE; recursos de combate; aggro y daño periódico |
| Archery | requisitos owner-keyed; cierre de relaciones inversas; casteo liberable; pasivas como raíces; stacks `Multiple`; muerte y efectos tardíos; prueba negativa de wire |

Battlerage reutilizó esos contratos y descubrió las extensiones de la sección
siguiente.

## Evidencia nueva aportada por Battlerage

| Hallazgo nuevo | Evidencia positiva | Evidencia negativa/falsificada | Contrato reusable |
|---|---|---|---|
| Autoridad completa de cooldown | Charge inicia una vez; Behind Gale `12→10→8→6 s` | reset como reducción, inicio al final del plot, snapshot por callback y framing Modern | `../shared_primitives/CHECKPOINT_AA8_COOLDOWN_AUTHORITY_V1.md` |
| Temporización plot/controller | Tiger Lightning: 3 impactos en 640 ms | sumar arista+controller duplicaba cada fase | `../shared_primitives/CHECKPOINT_AA8_PLOT_TIMING_COMBAT_SYNC_V1.md` |
| Combat-sync por perfil | Precision Wave: evento visual a 0 ms, daño a 642 ms | perfil único/fallback cero adelantaba el daño | mismo checkpoint de timing |
| Target de presentación separado | Hammer `SCPlotEvent(3480, POSITION)` y un daño | mantener la unidad o añadir `SCSkillFired` rompía/sesgaba el FX | `../shared_primitives/CHECKPOINT_AA8_PLOT_ONLY_POSITIONAL_PRESENTATION_V1.md` |
| Procedencia ≠ vínculo toggle | Charge publica buffs normales con `toggleSkill=0`; expiración estable | escribir skill origen universal reiniciaba 12 s | `../shared_primitives/CHECKPOINT_AA8_BUFF_CREATED_TOGGLE_LINK_V1.md` |
| Contexto ejecutable de pasivas | proc 5 % de Bleeding al target correcto | ignorar agentes/tags aplicaba al owner y hacía fan-out | `../shared_primitives/CHECKPOINT_AA8_PASSIVE_BUFF_LIFECYCLE_V1.md` |
| Exclusión group/rank | una etapa Bleeding activa y avance monotónico | coexistencia 242/514/515/516/517 duplicaba triggers | mismo checkpoint de pasivas |
| Stack `Extend` y cap vital | Frenzy extiende por `KillAny` hasta `max_life_time` | replace genérico y tareas antiguas expiraban la instancia | mismo checkpoint de pasivas |
| Admisión Combo durante GCD | Triple Lightning 500 ms; Whirlwind 635 ms | bypass del guard aceleró todo; replay servidor compitió con `auto_fire` | `../shared_primitives/CHECKPOINT_AA8_COMBO_GCD_ADMISSION_V1.md` |
| Certificación headless de rama | Mechanics Lab usa código real, reloj manual y hashes repetibles | un cast `Success` aislado no prueba efectos, orden ni tareas tardías | `../shared_primitives/CHECKPOINT_MECHANICS_LAB_V1.md` |

## Resultado vivo por familia

La matriz detallada permanece en `MATRIZ_BATTLERAGE.md`. El cierre de etapa 1
incluye:

- Triple Slash base/Lightning/Quake: cadencia y animación correctas;
- Charge: desplazamiento y cooldown monotónico al expirar buffs;
- Battle Focus: buff propio;
- Whirlwind Slash: tres etapas continuas;
- Sunder Earth: raíz y variantes;
- Frenzy: buff y extensión de lifecycle;
- Precision Strike: daño sincronizado con animación;
- Tiger Strike: tres impactos subsegundo;
- Bondbreaker y Terrifying Roar: liberación/control;
- Ollo's Hammer: martillo posicional sincronizado;
- Behind Enemy Lines: impacto y reducción Gale por objetivo;
- automáticas y pasivas: efectos principales sin blocker de etapa 1.

## Lecciones de causalidad

Battlerage exigió preservar no sólo los aciertos, sino también cuatro familias
de hipótesis falsificadas:

1. correlación temporal no implica causalidad: un cooldown que salta cuando
   sale un buff puede haber almacenado el vínculo erróneo al crearlo;
2. un paquete con nombre/layout parecido no pertenece al opcode hasta enlazar
   factory, vtable y serializer;
3. una suite headless verde no modela necesariamente una carrera entre el
   auto-fire del cliente y callbacks de servidor;
4. un FX faltante no autoriza a añadir un packet directo si el plot ya es la
   autoridad de presentación.

Estas pruebas negativas son parte del cierre y deben consultarse antes de
reparar otra rama.

## Bootstrap obligatorio para la siguiente rama

1. Partir de esta compact/runtime estable, no de un checkpoint anterior.
2. Generar el grafo completo de activas, internas, automáticas y pasivas.
3. Auditar desde el inicio cooldown tags, type 48, type 153, controllers,
   combat-sync, `group_id/group_rank`, `stack_rule`, `max_life_time` y agentes
   de triggers.
4. Clasificar cada skill como directa, `plot_only`, Combo, repetible cliente,
   multigolpe, movilidad, buff propio o cooldown diferido.
5. Añadir escenarios Mechanics Lab antes de la primera prueba visual.
6. Ejecutar la suite compuesta exacta y regresiones Sorcery/Archery/Battlerage.
7. Probar una familia por vez en cliente y conservar timestamps, TlId, target,
   packets y resultado visual.
8. Si una solución altera otra rama, detenerla y buscar una frontera de
   autoridad común; no agregar guards por ID como solución final.

## Estado documental

`CHECKPOINT_BATTLERAGE_V2_CANDIDATE.md` queda como historial de construcción,
hotfixes y falsificaciones. Este documento es el punto de entrada para el
cierre aceptado de primera etapa y para iniciar la siguiente rama.

