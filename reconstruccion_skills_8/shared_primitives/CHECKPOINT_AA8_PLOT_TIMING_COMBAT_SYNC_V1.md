# Checkpoint AA8 — temporización de plots y combat-sync

Fecha: 2026-08-09  
Origen del hallazgo: Tiger Strike y Precision Strike de Battlerage  
Autoridad: Kakao 8.0.3.12 r558734, compact, game_pak y captura viva

## Regla reusable

Los tiempos de una arista de plot y de un `SkillController` pueden describir
la misma fase. Sumarlos siempre duplica artificialmente la pausa. La
composición validada es:

`animSync + projectileTravel + max(edgeDelay, controllerCompletionDelay)`

El ajuste de casting sólo se conserva cuando la arista está declarada como
casting. No se corrige una skill acelerando el GCD, quitando el guard global o
introduciendo excepciones por ID.

## Caso de referencia

Tiger Strike: Lightning `36448` declara tres fases 400/300/300 ms. El runtime
sumaba controller y arista, aunque representaban la misma espera, y tardaba más
de dos segundos. Con la composición transversal:

- tres daños exactos sobre el mismo objetivo;
- cero cuarto impacto;
- orden monotónico;
- primer→tercer impacto: 640 ms en Mechanics Lab;
- aceptación visual: tres golpes fluidos dentro del contrato subsegundo.

Toda rama debe auditar los plots que combinan `SkillController value3/value5`
con delay explícito antes de cambiar datos de la skill.

## Combat-sync por perfil

`add_anim_cs_time` no puede resolverse con un único modelo ni caer
silenciosamente a cero. El catálogo se construye desde
`combat_sync_event_list.g` y se indexa por animación y perfil de
modelo/esqueleto:

1. perfil exacto de raza/género;
2. familia de esqueleto compatible declarada por AA8;
3. ausencia de timing probado: blocker, no fallback cero.

La variante de animación usada para calcular el marcador debe ser la misma que
se envía al cliente según arma/perfil.

## Orden visual y autoritativo

Los nodos con combat-sync se procesan en dos fases:

1. publicar `SCPlotEvent` e iniciar animación/movimiento;
2. esperar el marcador y aplicar daño, buffs y resultados.

Precision Strike: Wave `36446` es la referencia: evento visual a 0 ms y daño
después del marcador no nulo, observado a 642 ms. Aplicar daño antes del evento
visual produce el desync aunque la fórmula y el monto sean correctos.

## Presentación y target

El target de presentación puede ser una posición distinta de la unidad que
recibe daño. No añadir `SCSkillFired` para compensar un FX faltante si el plot
ya contiene `Anim/FxGroupAnim/ProjectileAnim`. El contrato completo está en
`CHECKPOINT_AA8_PLOT_ONLY_POSITIONAL_PRESENTATION_V1.md`.

## Evidencia negativa preservada

- sumar incondicionalmente delay de arista y controller: duplica fases;
- usar siempre `nuian_male`: deja marcadores cero para otros perfiles;
- fallback cero: adelanta daño respecto de la animación;
- insertar `SCSkillFired` en una skill `plot_only`: puede duplicar o adelantar
  la presentación;
- cambiar timings desde Modern: no es autoridad AA8.

## Gate obligatorio para ramas futuras

- mismo perfil/animación para packet y combat-sync;
- `SCPlotEvent` antes del efecto autoritativo;
- timestamps del primer y último impacto en skills multigolpe;
- conteo exacto de impactos;
- auditoría controller+edge;
- arma 1H/2H/dual cuando existan animaciones alternativas;
- validación visual real, porque un ledger correcto no prueba el FX cliente.

## Enmienda: combat-sync entre nodos no autoriza reorden global intranodo

Flamebolt expuso que hay dos relaciones distintas:

- una arista `add_anim_cs_time` publica el evento padre, espera el marcador y
  ejecuta después el nodo hijo de daño;
- el orden de paquetes producidos dentro de un mismo nodo puede alimentar una
  máquina cliente `auto_fire + Combo` y no debe invertirse transversalmente.

Precision Strike Wave `36446` confirma la separación: el evento `24126`
contiene las animaciones `900/901`; sus aristas `27523/27643` tienen
`add_anim_cs_time=1`, y el daño vive en nodos posteriores `23992/23993` o
`24694/24695`. Por ello restaurar el orden histórico intranodo únicamente para
Combo cliente no adelanta su daño ni elimina el marcador de 642 ms.

Flamebolt tampoco debía "acelerarse": `game_pak` prueba para
`all_co_sk_spell_launch_fireball` un combat-sync de `156 ms` tanto en
`nuian_female` como `nuian_male`; sumado al viaje del proyectil explica el
plot live de ~1441 ms. Ese tiempo ya existía en el commit Sorcery bueno y no
es la causa de la pérdida de las dos etapas instantáneas.

Gate nuevo para toda reparación de timing: comparar por separado
`parent-event -> edge wait -> child effect` y el orden de paquetes dentro del
mismo nodo; una validación de Precision/Tiger no autoriza a cambiar cadenas
Combo no incluidas en esa prueba.
