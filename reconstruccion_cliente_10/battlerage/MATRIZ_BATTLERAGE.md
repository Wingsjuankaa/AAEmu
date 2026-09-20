# Matriz de Battlerage r575

Estado revisado al 2026-09-20. "Catalogado" significa relaciones leídas y consumidor
identificado; no significa habilidad aceptada en el cliente. El informe
reproducible conserva las filas completas y todos sus gates.

Seguimiento actual de las cadenas: [GCD y respuestas reparados](CHAIN_RECOVERY_20260920.md),
desplegado y aceptado por el usuario el 2026-09-20. Pruebas posteriores en cliente y correcciones de ancestrales/Frenesí:
[sesión de Dannia del 20 de septiembre](ANCESTRAL_FRENZY_20260920.md).

## Doce activas

| Habilidad | Activación y cadena r575 | Estado / siguiente prueba |
|---|---|---|
| Tajo triple 18132 | Efectos de daño alternativos según tag propio 3105; sinergia sobre tag 27; Combo 48 encadena 18132 → 18134 → 18131 | Cadencia base aceptada en `f8af778cf`, conservada. Rayo y Terremoto completaron tres etapas en cliente el 20/09. Sinergias/área pendientes. |
| Carga 11918 | Plot 624 más efectos de habilidad; daño 517, buff 22627, disipación 204 y sinergia sobre target tag 6 | Cliente: acercamiento y daño comprobados. Pendientes límites de distancia, target inválido y activación completa de Reckless Charge. |
| Tajo torbellino 13282 | Plots 133/2230/2231, etapas 32040/32049, selección de área y gates; sinergia con tag 161 | Tres etapas con daño y finalización comprobadas en cliente el 20/09. Se conserva la cadencia aceptada. Pendientes área y sinergias. |
| Romper ataduras 12034 | DispelEffect 2633 | Cliente: rechazo sin root y limpieza de root 82/tag27 aplicados para QA. Pendiente comparación con controles que debe conservar. |
| Golpe preciso 12026 | DamageEffect 822 por espalda / 6693 frontal | Cliente: daño comprobado. Pendiente comparar frontal/espalda y variantes. |
| Hendir la tierra 10644 | Plot 649; cooldown compartido 4156 | Cliente: canalización, daño y finalización del plot comprobados. Pendientes área y variantes. |
| Concentración de combate 10377 | Buffs por tramos de nivel: 404/7651/13612/13613, con sus triggers de inicio | Cliente: 7651 del tramo 41–70 aplicado por 20 s y retirado. Pendientes bonificaciones efectivas y otros tramos. |
| Frenesí 10455 | Buffs 182/22690/22689 por nivel y triggers de daño/inicio según cada fila | Corregida extensión/serialización/limite restante según consumidor nativo. Cliente: caducidad normal, extensión por KillAny y límite 40 s comprobados. Variantes y efectos de daño pendientes. |
| Golpe del tigre 13315 | Plot 17 y controllers; ancestrales 2922/2923 | Cliente: movimiento, daño y finalización sobre un objetivo. Pendientes selección sucesiva, cancelación y variantes. |
| Rugido aterrador 18308 | Buffs propios y del adversario por nivel; sinergia con target tag 12 y source tag 4845 | Cliente: cast y buff propio observados. Pendientes área/obstáculos, destinatarios y sinergias. |
| Lanzamiento de martillo 18757 | Plot 440; alcance 15 m; daño, gate de impacto, stun 22532 (1500 ms + duración por nivel) sobre el original; ramal de knockback | Cliente a 14,2 m: daño y stun 22532, retirado; también hubo impacto sin stun con inmunidad retirada. Gate que repite el dado pendiente de cierre nativo; no certificado completo. |
| Tras las líneas enemigas 23587 | Daño 5347, PhysicalExplosion 113, buffs condicionales sobre tags 27/97; buff propio 7543 si source tag 1476 | Cliente: rechazo demasiado cerca, salto y aterrizaje observados. Advertencia de shape 5047 sin radio con fallback de 40 m: área de impacto no aceptada. |

## Ancestrales

| Base | Opciones y auxiliares | Diferencia o riesgo pendiente |
|---|---|---|
| Tajo triple | Rayo 36401/36402/36403; Terremoto 36404/36405/36406 | Gate de selección Zone corregido; ambas cadenas probadas. Terremoto: maná 20 en AA10, 12 en AA8. 36403 declara plot_only sin plot; `Skill.Use` sólo toma el camino exclusivo si existe Plot, por lo que no basta ese flag para diagnosticar una skill muerta. |
| Golpe preciso | Oleaje 36446 / Vendaval 36447 | Verificar área/ángulo y gates propios, no sustituir por la base. |
| Golpe del tigre | Rayo 36448 / Vida 36449 | Corregida duplicación de esperas controller/arista. Rayo: tres daños programados a401/721/1041 ms; fixture AA10 y suite5534. Véase TIGER_TIMING_20260920.md. Aceptación visual y variante Vida pendientes. |
| Tras las líneas enemigas | Vendaval 39661 / Piedra 39662 | Validar desplazamiento y efectos de aterrizaje por separado. |
| Hendir la tierra | Terremoto 41217 / Neblina 41218 | Comparten familia de cooldown 4156; conservar plots 4044/4045. |
| Frenesí | Llama 43188 / Oleaje 43189 | Buffs y triggers propios; no reutilizar automáticamente la secuencia de la base. |

Los demás registros incluyen etapas, skills obsoletas y animaciones de login/vídeo.
No se presentan como habilidades nuevas del jugador. `inventory.md` enumera los 42.

## Seis pasivas

| Puntos / buff | Activador comprobado en datos AA10 | Consumidor / situación |
|---|---|---|
| 3 / 2610 — Deflect and Retaliate | CombatBuff 23: melee/ranged parry, aplica 2611; timeout → trigger1374 → efecto15008 → ResetCooldown4636, tag415 | Cadena de activación presente. Ejecutar el reset completo estaba roto: corregido. Falta ensayo parry real y verificar supresión de 12 s; no se inventó un temporizador. |
| 4 / 7542 — Reckless Charge | Tag1476 habilita buff7543 en las skills indicadas; modificadores143/145=-150 | Cadena presente. Probar los tres desplazamientos, los 4 s y retirada exacta de la reducción física. |
| 5 / 2621 — Physical Penetration | CombatBuff24: melee critical → 2622 → timeout1390 → efecto15055 → SkillUse4670 → skill16185 | Cadena presente. Destinatario y supresión pendientes: no certificar sólo porque SkillUse existe. |
| 6 / 811 — Attack Speed Training | CombatBuff51: hit tag4749, máscara101 → buff22277 (1000ms, inmunidad a su tag3714) → Started14546 → CombatResourceEffect494 → recurso1 | Corregida carga/aplicación de sus unit_modifiers: +5 pp daño crítico/+30 velocidad por punto, máximo5. Tests de ganancia/límite/gasto/retirada; aceptación visual/cadencia real pendientes. Véase TIGER_PASSIVES_20260920.md. |
| 7 / 831 — Weapon Mastery | SkillModifier1842: tag415, atributo Damage10, tipo porcentual, valor10 | Datos y consumidor presentes. Comparar daño con/sin pasiva y una skill fuera de tag415. |
| 8 / 7544 — Weapon Training | UnitModifier56117: atributo77, valor60 | +6 pp crítico probado al aplicar/retirar PassiveBuff, sin gate de equipo en el modifier. C y la condición separada de parry ranged con 2H/dual pendientes. |

## Candidatos AA8

| Componente | Clasificación | Decisión |
|---|---|---|
| Selectores de plot que conservan BaseUnit | aa10_confirmed_shared_primitive | Aplicado; los anchors proceden del grafo r575. |
| Visibilidad espacial de un anchor | aa10_confirmed_shared_primitive a nivel de grafo; consumidor binario de Visible pendiente | Adaptación mínima; las unidades reales conservan su gate anterior. |
| Reset por skill/tag y grupos | aa10_confirmed_shared_primitive | Adaptado al consumer/flags r575, no copiado literalmente. |
| Máscara y reutilización de combat dice | structural_candidate | Datos enum coincidentes; requiere cerrar conjuntamente DamageEffect y gates. |
| Autorización efímera de Combo | aa10_confirmed_shared_primitive | Enlaces/ventana conservados; GCD y respuestas corregidos en `f8af778cf` y aceptados por el usuario. Las excepciones experimentales anteriores no son autoridad. |
| Proc derivado AA8 811→11344 | version_sensitive_blocked | AA10 tiene otra cadena, basada en CombatResource. |
| Automáticas AA8 34119/34120/34124 | aa8_only en el catálogo comparado | Ausentes en full AA10; no habilitadas artificialmente. |

## Matriz jugable pendiente

1. Dannia: un enemigo válido a 12–15 m, cast único de 18757. Correlacionar daño y stun
   tras el vuelo; hay un éxito y un impacto sin stun en la sesión del 20/09.
   Registrar el dado original y el del gate, y cerrar el consumidor nativo.
2. Repetir con otro enemigo dentro de 3 m: distinguir stun del original y el
   ramal de knockback. Probar target muerto, fuera de 15 m e inmune.
3. Con pasiva2610 aprendida, dejar Carga/Hendir/Tigre en cooldown y provocar un
   parry. Verificar que el cliente permite volver a usar las tres y el servidor
   lo acepta, incluidos los grupos compartidos. No forzar éxito desactivando GCD.
4. Repetir la activación pronto para medir la supresión real; no declarar 12 s
   implementados basándose en el tooltip.
5. Continuar con Tajo triple y su resultado de impacto antes de pasar a otra rama.

Cada aceptación debe anotar build, skills aprendidas, equipo, objetivo, distancia,
tags/buffs previos, eventos recibidos y limpieza de overrides. La sesión del 20/09 ejecutó los casos descritos
en el informe enlazado; los casos de esta lista siguen pendientes en su alcance completo.
