# Reporte #4: De vuelta al otro lado (10032)

Revisión solicitada mediante el nuevo menú de reportes. Target rama_10, HEAD45bba0ad49fee55ab30a80168b4d6caefbb9ac87; padre upstream/client_version/zone-10.0.2_r575,1017677b40be6508861a8fb74e9d09fa496873c9. Diagnóstico, sin parche de gameplay ni despliegue.

## Recepción

Scripts/BugReports.py recuperó el reporte4, creado2026-09-12 14:02:35 UTC: Dannia1007, quest10032 Back Across, estadoProgress, zone382/instance0, posición31702.342/35768.91/217.3623, cliente10.0.2.13-r575. Descripción: no completa al cruzar pasando por la melodía. El reporte3 contiene TEST DE ERROR de quest10029 y no forma parte de esta reparación. No se alteró el texto original. El estado del reporte4 pasa a investigating con historial.

## Evidencia

Quest10032 requiere objeto49004 (componente43618), efecto83125 de interacción con la flor (43570) y esfera2991 (43651). Log13:57:38 y14:00:52 registra aceptación y objeto1/1;14:01:05 y14:01:20 registra skill43882 contra doodad14928. No aparece callback de llegada para el objetivo847. World API confirma Garden382 ZoneLoaded con heartbeat y Dannia conectada; no es una Zone caída.

La llegada exige buff26262 mediante unit_req69362. Éste nace del trigger13377 de buff26261 cuando existe tag4669 (buff26260), al terminar la secuencia inversa de notas. Las esferas2983..2990 aplican los buffs26248..26254 y26261. Sus definiciones y requisitos coinciden en SQLite autoritativa y compact runtime; evidencia guardada en artifacts/report4-contract.json.

Prueba concreta de ruptura en el log:

-14:01:07 se aplica buff26248, primera nota inversa, detalleSphereBuff87.
-14:01:08 el servidor ejecuta SphereBuff REMOVE para26248 al abandonar el área.
-14:01:09 entra en26249. Su trigger13371 exige tag4658, cuyo único miembro es26248; ya fue eliminado, así que no aplica el siguiente estado26255.
-Las notas posteriores se detectan, pero la cadena no progresa hasta26260/26262. La línea antigua «BuffTrigger executed. Applying...» se escribe antes de validar tags y no demuestra ejecución efectiva del efecto.

CharacterQuests.ApplySphereBuff usa al salir `RemoveOnLeaveBuffId != 0 ? RemoveOnLeaveBuffId : BuffId`. Los datos nativos de las primeras siete notas tienen remove_on_leave_buff_id=NULL, duración0: el fallback elimina un buff que debe conservarse para la secuencia. El padre AA10 local contiene el mismo fallback. La comprobación final26261 sí tiene retirada explícita al salir. No se deben retirar los requisitos de melodía para dar la quest por completada.

Las notas visuales14984 y las piezas físicas son distintas del estado de la melodía. Este diagnóstico demuestra una ruptura server-side suficiente para impedir la quest; no demuestra un fallo visual adicional ni que falte otro spawn. El puente restaurado para10028 no resuelve esta semántica de salida.

## Estado y frontera de corrección

Reporte en revisión, no fixed/closed. No se cambió el progreso del jugador, no se reiniciaron servicios ni se operaron Zones. Evidencia: artifacts/report4-live.log, report4-review.json y report4-contract.json.

Corrección pendiente: respetar el ID explícito de retirada de SphereBuff, cubriendo con regresión la secuencia26248 ->26249 ->26255, persistencia entre notas y eliminación sólo cuando está declarada. Revisar también los consumidores de muelles, mascotas y barcos antes de desplegar ese cambio compartido; no sustituir la secuencia por finalización manual. La aceptación retail seguirá pendiente hasta repetir el regreso y recibir el objetivo normalmente.
