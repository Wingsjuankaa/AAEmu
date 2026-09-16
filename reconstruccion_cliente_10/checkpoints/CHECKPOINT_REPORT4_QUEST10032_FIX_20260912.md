# Reporte #4: reparación de la melodía del puente

Target rama_10, HEAD45bba0ad49fee55ab30a80168b4d6caefbb9ac87; padre upstream/client_version/zone-10.0.2_r575,1017677b40be6508861a8fb74e9d09fa496873c9. Autorización del usuario: «perfecto, reparalo». Clasificación server-required. Continúa el diagnóstico CHECKPOINT_REPORT4_QUEST10032_REVIEW_20260912.md.

## Cambio

CharacterQuests.ApplySphereBuff elimina al salir únicamente RemoveOnLeaveBuffId. Cero/NULL significa no retirar efectos. Se elimina el fallback a BuffId que borraba la primera nota26248 antes de entrar en la segunda26249. La segunda exige tag4658=26248 para producir26255; las siguientes notas producen el estado final26260 y el buff26262 requerido por esfera2991/quest10032. Se conserva el objetivo nativo, sin autocompletar ni añadir casos por quest/skill ID.

SphereBuffs documenta el significado de cero. Los datos autoritativos/runtime coinciden: sphere_buffs87..93 no retiran sus notas, mientras94 retira explícitamente26261. El catálogo tiene108 filas,54 sin retirada y54 con retirada explícita. Moored13817 y permiso13789 poseen retirada explícita; Ezi13816 no tiene una y desde ahora también conserva su semántica declarada. No se alteran selección de dueño, and_pet, slave_applicable ni aplicación a barcos/mascotas. AA8 dispone del modelo de datos, pero no aportó una implementación de salida que se pudiera reutilizar; el padre AA10 contiene el mismo fallback defectuoso.

## Regresión

SphereBuffExitTests invoca el camino real de salida de CharacterQuests y el validador real de BuffTrigger. Sin nota previa el efecto es rechazado; con la primera nota adquirida, salir de su área dos veces debe conservarla y permitir que el trigger de la segunda se ejecute. En el código anterior falla Count esperado1/real0 y el log muestra REMOVE26248. Después del cambio pasa.

Casos adicionales conservan retirada explícita para Moored, permiso con and_pet y comprobación final de Nebe; un caso de IDs de entrada/salida distintos elimina sólo el destino declarado. Los tests aíslan/restauran singletons y simulan el almacenamiento de buffs; no pretenden demostrar renderizado ni movimiento retail de barcos. La suite existente SphereBuffTargetsTests cubre la selección de receptores.

Restore/build Release correctos; suite2782/2782. Evidencia artifacts/report4-red.log (5 casos,1 fallo esperado anterior), report4-gates.log (cero errores de compilación, advertencias existentes), report4-docker-build.log.

## Entrega y aceptación

Se construye Game/World en Release conservando datos y cliente. Respaldo previo en E:/AAEmu/rama_10/backups/report4-20260912: DB, compact, log, World y hashes. Imagen anterior etiquetada aaemu-world:rollback-report4-20260912. Manifest de reparación recoge identidad de imagen y binarios verificados al desplegar.

Para rollback, restaurar el servicio Game a la imagen etiquetada y conservar los bind mounts actuales. No restaurar la DB de respaldo sobre progresos posteriores: este cambio no migra datos ni modifica el progreso de la quest por fuera del juego. No se operan Zones; el usuario inicia su perfil Garden después de reconectar.

Despliegue verificado: imagen2a70bd30a23306699118a66a8843e7bc92c7baae848b8cc9f94ab87843688cbd; Game healthy, World API responde y puertos1239/1240/1250/1280 escuchando. Arranque sin ERROR/FATAL. Compact SHA256 idéntica al respaldo. Logs y estado en artifacts/report4-deploy; reporte4 actualizado a needs_retest con nota e historial.

Aceptación retail pendiente: con la quest10032 activa, repetir la secuencia normal de flor y regreso por las notas. Deben conservarse las notas entre áreas, generarse26262 al finalizar correctamente y registrarse el objetivo de llegada. No es necesario abandonar la misión. Closed requiere confirmar la prueba del jugador.
