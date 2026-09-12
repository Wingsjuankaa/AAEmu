# Garden: sustitución de rango y multiplicador GM

Target `E:/AAEmu/rama_10/server/AAEmu`, branch `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`. Padre `upstream/client_version/zone-10.0.2_r575`, SHA `7babcb3a706c64295b5aaaeec8abe57e4d09b4da`.

## Evidencia y alcance

El usuario confirma que el daño funciona y que el HUD alcanzó nivel 1, pero el icono permanece en 0 incluso esperando más de 10 segundos. En `E:/AAEmu/rama_10/artifacts/garden-rank-live.log`, Dannia1007 pasa de2485 a2645 puntos a13:37:54; a13:38:02 se envía SCBuffCreated25656 aObj1762. Crear el rango nuevo no retiraba el anterior: AA10 cargaba GroupId/GroupRank pero Buffs.AddBuff no arbitraba los miembros del grupo.

Los 13 rangos pertenecen al grupo244, todos con prioridad GroupRank0. IDs por nivel: 26196,25656,25658,25659,25660,25661,25662,25663,25664,25665,25666,25667,25668. La prioridad de grupo no representa el nivel de Garden. Clausura de grupos244 y10 idéntica en SQLite autoritativa y runtime, `artifacts/garden-rank-group-contract.json`, SHA256 `0ccde681fa206b1d6bf3616e96ace9c78d2e74cad7b3cd5ed81d9b28146ad8f4`.

La implementación AA8 de Buffs.AddBuff aporta la regla de prioridad y sustitución; los datos r575 corroboran los grupos y prioridades, incluyendo Bleeding242/514/515/516/517. No se obtuvo decompilación nativa positiva de la regla: el resultado de CreateBuff en `garden-buff-group-native.log` es un wrapper cliente no soportado y no se usa como prueba positiva. Clasificación: reparación de primitiva compartida `server-required`, sustentada por datos AA10 y contraste AA8; aceptación visual retail pendiente.

## Implementación

Buffs.AddBuff rechaza un miembro de menor prioridad si hay uno superior activo; en otro caso retira los miembros activos distintos de la misma familia mediante Exit(false), antes de crear el nuevo. Conserva las reglas de acumulación de la misma plantilla y los buffs sin grupo. El cambio cubre el grupo nativo, sin ID de Garden incrustado ni paquetes sintéticos. Los ticks nativos de25655 siguen seleccionando el rango; puede tardar hasta el siguiente tick de10 segundos.

Herramienta personalizada solicitada explícitamente por el usuario: `/gardenrate [1..1000]`. Sin argumento consulta; `/gardenrate 20` multiplica por20 las ganancias futuras, `/gardenrate 1` restaura el ritmo normal. Es global para todos los personajes del proceso Game y cambia inmediatamente con lectura/escritura atómica. ACL existente predeterminada100 (GM). Arranca en1 y reiniciar Game lo restaura; no hay persistencia del ajuste. Se aplica una sola vez en CharacterGardenScore.Add a deltas positivos, incluidas bajas y tiempo; no multiplica pérdidas, resets ni cargas de puntuación guardada. Conserva requisitos de misión, topes y umbrales nativos. No se modifica game_pak ni la DB.

## Validación y despliegue

Release:2758/2758 pruebas, cero fallos; build sin errores. BuffTickRequirementsTests recorre todos los rangos, bajadas y saltos usando DispelTask y los requisitos nativos: sólo queda un rango y los ticks repetidos conservan la instancia. Prueba adicional de prioridad y buffs sin grupo. GardenRateTests comprueba consulta, cambios inmediatos, restauración, ACL, entradas inválidas, pérdidas e overflow. `git diff --check` sin errores.

Respaldo antes del despliegue: `E:/AAEmu/rama_10/backups/garden-rank-20260911-135116`, DB transaccional, log y snapshot World. Rollback `aaemu-world:rollback-garden-rank-20260911-135116`, imagen previa `sha256:d20e139bcdd9d5495957c5fa61967e575efb002e3751eb316fa4acec5c0a0411`. Hashes y verificación del despliegue en el manifest adjunto. No se operan Zones; su lifecycle continúa bajo Control Center del usuario.

Prueba retail pendiente: iniciar el perfil Garden desde Control Center, entrar con misión10056 activa, consultar `/gardenrate`, usar20, ganar puntos y esperar un tick para comprobar que HUD y único icono de rango coinciden. Restaurar1 después. Comprobar también salto de varios niveles y relog conservando puntuación. No declarar resueltos todos los modos PvP ni otras mecánicas Garden a partir de esta prueba.
