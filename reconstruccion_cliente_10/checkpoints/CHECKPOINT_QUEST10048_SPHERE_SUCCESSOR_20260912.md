# Quest 10048 -> 10049: reevaluación del área de aceptación

Fecha: 2026-09-12. Target rama_10, HEAD 45bba0ad49fee55ab30a80168b4d6caefbb9ac87; padre upstream/client_version/zone-10.0.2_r575 (1017677b40be6508861a8fb74e9d09fa496873c9). Clasificación: server-required, contrato client-native r575.

## Síntoma y causa
Dannia despertó al guardián, entregó automáticamente 10048 «Devolver a su dueño» y quedó sin continuación. El log muestra entrada al área2997 a las 16:08:47 UTC, seguida de rechazo de 10049 por component43679. La 10048 se completó a las 16:09:18; no hubo una nueva entrada al área2997. ReconcileQuestAreaSpheres sólo comprobaba aceptación al entrar, aunque el requisito acababa de cambiar dentro del volumen.

## Contrato AA10
- 10049 Start43679: QuestActConAcceptSphere948 -> sphere2997.
- UnitReq69490: CompleteQuestContext31 -> 10048, habilitado; no quitar requisito.
- Sphere2997: entrada, trigger condition3 (trigger_every_n_time_after), tiempo0; SphereQuest1733 -> quest10049, trigger3 AcceptForce. La ruta existente AddQuestFromSphere mantiene validación de contexto y componentes.
- La misión continúa con objetivos de áreas3005–3009 y entrega en doodad14838. No se inventa autocompletado ni se altera el progreso.
- Evidencia completa en artifacts/quest10048-contract.json, autoridad game_decrypted.sqlite3 SHA256 87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f.
- Padre exacto conserva el problema de comprobación al entrar. La revisión selectiva de CharacterQuests/SphereQuest en rama_8 no aporta la reevaluación; no se porta contrato AA8.
- BugReports: filtro quest/10048 sin reportes asociados; captura del usuario y log son evidencia del síntoma.

## Corrección
CharacterQuests marca un cambio de requisitos sólo cuando cambia un bit de misión completada. La próxima reconciliación consume esa marca y revisa aceptación en las áreas donde el personaje continúa físicamente dentro. Sólo SphereQuest de entrada, repetible inmediato y AcceptForce/AcceptConditional. Excluye activas y completadas; utiliza AddQuestFromSphere sin forzar. No repite objetivos, buffs, escenas ni eventos de entrada. Nuevas entradas siguen por su ruta normal; otras clases de trigger y tiempos positivos quedan intactos. La marca es atómica; no hay sondeo continuo de requisitos fallidos ni recursión desde entrega.

## Validación y alcance
9 pruebas focales: rechazo real antes de requisito, candidato10049 después de completar10048 sin nueva entrada, idempotencia, requisito conservado ante otra misión completada, fuera del área, misión activa/completada, triggers de una sola vez, temporizados, de salida, buff y de completar. Restore/build Release correctos; suite completa 2808/2808, cero fallos. Advertencias preexistentes de dependencias/análisis se conservan.

Sólo cambia código del servidor; compact y game_pak intactos. Preserva arreglos anteriores de 10032/10038/10159/10045. La aceptación en cliente de 10045 queda confirmada por avance hasta10048.

## Despliegue y rollback
Imagen previa 3a9538a98a117c91650d6d2434884789939307eafd18aa29da945518f1ce1b7b conservada como aaemu-world:rollback-quest10048-20260912. Respaldo en E:/AAEmu/rama_10/backups/quest10048-20260912: DB, compact, log y estadoWorld. No hubo migración de DB; no restaurar el dump sobre progreso posterior para revertir código. Runtime final y hashes en manifiesto homónimo.

Recreado únicamente Game mediante compose canónico. Zones quedan bajo control del usuario. Prueba retail pendiente: relanzar Garden desde Control Center, reconectar Dannia y comprobar que10049 se ofrece/activa al estar en el área del guardián. No repetir entrega10048 ni otorgar misión con GM. Si el personaje se movió fuera de2997, volver a la zona del guardián.
