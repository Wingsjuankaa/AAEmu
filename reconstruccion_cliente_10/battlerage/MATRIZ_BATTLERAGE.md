# Matriz de Battlerage r575

Estado revisado al 2026-09-20. "Catalogado" significa relaciones leídas y consumidor
identificado; no significa habilidad aceptada en el cliente. El informe
reproducible conserva las filas completas y todos sus gates.

Seguimiento actual de las cadenas: [GCD y respuestas reparados](CHAIN_RECOVERY_20260920.md),
desplegado y pendiente de aceptación visual. Las menciones de rechazo siguientes
describen la prueba anterior, conservada como historial.

## Doce activas

| Habilidad | Activación y cadena r575 | Estado / siguiente prueba |
|---|---|---|
| Tajo triple 18132 | Efectos de daño alternativos según tag propio 3105; sinergia sobre tag 27; Combo 48 encadena 18132 → 18134 → 18131 | Presencia de los tres golpes registrada. **Cadencia rechazada por el usuario y sin resolver**: [rectificación](CADENCIA_20260920.md). Pendientes sinergias y variantes ancestrales. |
| Carga 11918 | Plot 624 más efectos de habilidad; daño 517, buff 22627, disipación 204 y sinergia sobre target tag 6 | Catalogado. Probar acercamiento, distancia, target inválido y activación de Reckless Charge. |
| Tajo torbellino 13282 | Plots 133/2230/2231, etapas 32040/32049, selección de área y gates; sinergia con tag 161 | Presencia de los tres golpes registrada. **Cadencia rechazada por el usuario y sin resolver**: [rectificación](CADENCIA_20260920.md). Pendientes múltiples objetivos y sinergias. |
| Romper ataduras 12034 | DispelEffect 2633 | Catalogado. Verificar las familias de control que permite disipar y las que conserva. |
| Golpe preciso 12026 | DamageEffect 822 por espalda / 6693 frontal | Catalogado. Medir ambos ángulos y sus variantes ancestrales sin duplicar daño. |
| Hendir la tierra 10644 | Plot 649; cooldown compartido 4156 | Catalogado. El reset de su grupo queda cubierto por pruebas; faltan área, efectos, daño y cadencia en cliente. |
| Concentración de combate 10377 | Buffs por tramos de nivel: 404/7651/13612/13613, con sus triggers de inicio | Catalogado. Validar selección del tramo, duración, renovación y retirada de modificadores. |
| Frenesí 10455 | Buffs 182/22690/22689 por nivel y triggers de daño/inicio según cada fila | Catalogado. Probar subida/bajada de efectos y limpieza, sin confundirlo con el recurso de la pasiva 811. |
| Golpe del tigre 13315 | Plot 17 y controllers; ancestrales 2922/2923 | Catalogado. Probar selección sucesiva, movimiento, cancelación y destino muerto. |
| Rugido aterrador 18308 | Buffs propios y del adversario por nivel; sinergia con target tag 12 y source tag 4845 | Catalogado. AA10 exige check_obstacle; conservarlo. Probar área/obstáculo y destinatarios de cada buff. |
| Lanzamiento de martillo 18757 | Plot 440; alcance 15 m; daño, gate de impacto, stun 22532 de 1500 ms sobre el original; ramal de knockback | Dos bloqueos corregidos y 10 pruebas de regresión. Falta prueba real de lanzamiento, impacto, stun, inmunidad, secundarios y vuelo. El gate de combat dice sigue siendo una frontera independiente. |
| Tras las líneas enemigas 23587 | Daño 5347, PhysicalExplosion 113, buffs condicionales sobre tags 27/97; buff propio 7543 si source tag 1476 | Catalogado. Probar salto, aterrizaje, efectos sobre varios enemigos y defensa temporal de la pasiva. |

## Ancestrales

| Base | Opciones y auxiliares | Diferencia o riesgo pendiente |
|---|---|---|
| Tajo triple | Rayo 36401/36402/36403; Terremoto 36404/36405/36406 | Terremoto: maná 20 en AA10, 12 en AA8. 36403 declara plot_only sin plot; `Skill.Use` sólo toma el camino exclusivo si existe Plot, por lo que no basta ese flag para diagnosticar una skill muerta. |
| Golpe preciso | Oleaje 36446 / Vendaval 36447 | Verificar área/ángulo y gates propios, no sustituir por la base. |
| Golpe del tigre | Rayo 36448 / Vida 36449 | Validar controllers y selección distinta entre variantes. |
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
| 6 / 811 — Attack Speed Training | CombatBuff51: hit tag4749, máscara101 → buff22277 (1000ms, inmunidad a su tag3714) → Started14546 → CombatResourceEffect494 → recurso1 | Mecanismo diferente de AA8. Recurso máximo5, recuperación9000ms/-6. Probar acumulación, expiración y bonificación efectiva; no importar el proc11344. |
| 7 / 831 — Weapon Mastery | SkillModifier1842: tag415, atributo Damage10, tipo porcentual, valor10 | Datos y consumidor presentes. Comparar daño con/sin pasiva y una skill fuera de tag415. |
| 8 / 7544 — Weapon Training | UnitModifier56117: atributo77, valor60 | Modificador presente. La condición de parry ranged con 2H/dual no queda cerrada por esta fila: validación pendiente. |

## Candidatos AA8

| Componente | Clasificación | Decisión |
|---|---|---|
| Selectores de plot que conservan BaseUnit | aa10_confirmed_shared_primitive | Aplicado; los anchors proceden del grafo r575. |
| Visibilidad espacial de un anchor | aa10_confirmed_shared_primitive a nivel de grafo; consumidor binario de Visible pendiente | Adaptación mínima; las unidades reales conservan su gate anterior. |
| Reset por skill/tag y grupos | aa10_confirmed_shared_primitive | Adaptado al consumer/flags r575, no copiado literalmente. |
| Máscara y reutilización de combat dice | structural_candidate | Datos enum coincidentes; requiere cerrar conjuntamente DamageEffect y gates. |
| Autorización efímera de Combo | aa10_confirmed_shared_primitive | SkillComboMan confirma enlaces y ventana; **no confirma las excepciones de GCD implementadas**. Aceptación de cadencia retirada; investigación transversal pendiente. |
| Proc derivado AA8 811→11344 | version_sensitive_blocked | AA10 tiene otra cadena, basada en CombatResource. |
| Automáticas AA8 34119/34120/34124 | aa8_only en el catálogo comparado | Ausentes en full AA10; no habilitadas artificialmente. |

## Prueba jugable siguiente

1. Dannia: un enemigo válido a 12–15 m, cast único de 18757. Esperar daño y stun
   de 1,5 s tras el vuelo; registrar resultado de impacto y eventos de plot.
2. Repetir con otro enemigo dentro de 3 m: distinguir stun del original y el
   ramal de knockback. Probar target muerto, fuera de 15 m e inmune.
3. Con pasiva2610 aprendida, dejar Carga/Hendir/Tigre en cooldown y provocar un
   parry. Verificar que el cliente permite volver a usar las tres y el servidor
   lo acepta, incluidos los grupos compartidos. No forzar éxito desactivando GCD.
4. Repetir la activación pronto para medir la supresión real; no declarar 12 s
   implementados basándose en el tooltip.
5. Continuar con Tajo triple y su resultado de impacto antes de pasar a otra rama.

Cada aceptación debe anotar build, skills aprendidas, equipo, objetivo, distancia,
tags/buffs previos, eventos recibidos y limpieza de overrides. No se realizaron
estas acciones en el cliente durante esta entrega.
