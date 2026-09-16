# Anthalon: cierre de invocación y conservación de timeline

Target canónico `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`, HEAD45bba0ad. Padre exacto `upstream/client_version/zone-10.0.2_r575` ahora67b51f17 (el ref avanzó desde el diagnóstico anterior). Comparado antes de editar: mantiene Task.Run del plot no exclusivo y ambos ReleaseId independientes. AA8 conserva la misma doble propiedad, no aporta solución. No merge/commit/push. Cambios ajenos conservados.

## Evidencia y alcance

Usuario: quest10101, Anthalon20019/1047, Dannia1046, instancia100/zone384. La invocación43979 permanece en la barra y no hay huida al50%. `artifacts/anthalon-lifecycle/before.log`: a23:18:52 se envía PlotEvent42573 con tl0 después de EndSkill; a23:22:31 timeline849 se libera antes de finalizar el plot. No solicitud44012; muerte por daño normal23:28:48. No se afirma que la barra x5 sea por sí sola un porcentaje exacto.

SQLite r575, hash87531f4b…, confirma43979 plot4770 no exclusivo, arista de casteo49296 de2000ms y secuencia posterior. Skill44012 exige HP1..50%, casteo6000ms; aplica26463 para el objetivo de área y habilita salida14993. Consultas y filas en `artifacts/anthalon-lifecycle/native.json`; evidencia previa completa en `artifacts/quest10101/escape-condition.json`. Cola de reportes abierta filtrada10101 vacía; no equivale a todos los reportes históricos.

Defectos probados de implementación: EndSkill y DoPlotEnd reciclaban por separado el mismo TlId, y el puente publicaba WZPlotEvent pero nunca WZPlotEnded. El paquete0x003B/bodyu16 ya está declarado en el transporte AA10; no se inventan opcode ni payload. La ausencia de cierre explica una secuencia remota abierta; que ésta sea la única causa del bloqueo de la fase requiere aceptación real.

## Cambio

Registrar los dos consumidores antes de lanzar el worker y conservar el TlId hasta que ambos terminen, cualquiera sea su orden. Validar rango antes de lanzar plots mixtos y enviar Started antes del primer evento. EndSkill conserva su callback y settlement; DoPlotEnd sólo notifica callback de skill cuando el plot es su único ejecutor. Publicar PlotEnded con el identificador original antes de liberarlo. Cancelación conserva el identificador hasta el cierre del plot; un Stop anterior al BindState se propaga al worker. El entrypoint auxiliar StartPlot declara ejecución sólo de graph.

No se fuerza44012, buff26463, HP, crédito de quest, tiempo, spawn ni destino. No modificaciones de DB/compact/game_pak. Corrección `server-required` de lifecycle; sin ramas por ID de boss/skill.

## Validación y entrega

Build Release correcto; 2840/2840 pruebas. Cuatro casos nuevos ejecutan el árbol real con cast edge y comprueban conservación del identificador en ambos órdenes, cancelación, callback único, consumidor ordinario, plot-only y bytes del paquete existente incluyendo u16 alto. Los20ms son sólo espera reducida de fixture; runtime conserva2000ms nativos. Suite incluye proyectiles, canales, buffs y comandos GM.

Game desplegado con rollback `aaemu-world:rollback-anthalon-lifecycle-20260915`; imagen y hashes en manifiesto. No operaciones sobre Zones. Artefactos build/tests/docker-build/startup bajo `E:/AAEmu/rama_10/artifacts/anthalon-lifecycle`.

Aceptación pendiente: el usuario restaura sus Zones desde Control Center y entra de nuevo. Combate normal, reducir daño cerca del50% y dejar terminar huida44012 (6s); observar26463 y quest. No usar /die para esta comprobación. Comprobar en logs PlotEvent→PlotEnded con TlId no cero y la siguiente solicitud de IA. Si no aparece44012, medir HP World/Zone y selección de habilidad antes de otro cambio; no completar la misión artificialmente.
