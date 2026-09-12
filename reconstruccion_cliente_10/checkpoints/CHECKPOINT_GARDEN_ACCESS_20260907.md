# Garden: acceso público y portales — 2026-09-07

Target `rama_10`, HEAD previo `fd53b458573572cc354c8564293f274801d9aa3e`.
Padre `upstream/client_version/zone-10.0.2_r575`, commit `7babcb3a706c64295b5aaaeec8abe57e4d09b4da`.

## Política solicitada y resultado

El usuario solicitó Garden habilitado para todos, incluidas cuentas nuevas, con sólo nivel 55 y puntuación de equipo 8000 como requisitos de entrada. `Account.FreeGardenAccess=true` está en CharacterSettings.json versionado y en el bind mount efectivo. AccountAttributeManager proporciona ULC 1 a todas las cuentas y el publicador existente lo envía al cliente. Es un permiso efectivo de configuración; no modifica filas de cuenta ni concede Patron. Patron ya estaba activo mediante ForceMaxPremiumGrade.

La política filtra los requisitos de la entrada 43900 a Level y GearScore. Las validaciones normales de uso de habilidades siguen vigentes. El permiso ULC es independiente de Patron. Desactivar FreeGardenAccess restaura la evaluación nativa de requisitos en la siguiente sesión. Esta apertura global es una personalización explícita del usuario.

## Causa y cierre de implementación

- Faltaban las colocaciones del portal: 14855 es el modelo visual; 16879 es la interacción real. Se restauraron 13 colocaciones exactas del cliente, incluidas las puertas interiores y la salida 14862, sin modificar game_pak.
- La habilidad de entrada 43900 usa SpecialEffect 182, antes presente sólo como enum en este fork y su padre. TeleportToIntegrationWorld reutiliza Return y el catálogo nativo de destinos. Dirección 0 usa const_return_points.gatekeeper_hall=1005; dirección 1 usa return_points.navel_of_the_world=1011. Una dirección desconocida rechaza la operación.
- El requisito GearScore 122 no estaba implementado. Se añaden comparaciones inclusivas mínima (selector 0) y máxima (selector 1), corroboradas con los pares de requisitos del catálogo, y el error nativo UrkGearScore 0xC0.
- Se conserva la misión 10011 y su entrega a Kyprosa 14838. No se fuerza el progreso de la misión.

La ruta de integración se adapta al servidor local: ambos destinos se resuelven dentro de main_world y utilizan el traslado existente. No implementa un servicio distribuido entre reinos.

## Evidencia y reproducción

Evidencia: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/garden-gate`.
`native-contract.json` registra el contrato del catálogo completo y compact. `placements.csv`, `placements-active.csv` y `return-points.csv` provienen de lectura del game_pak principal r575.

Para regenerar las entradas CSV, usar PakDoodadScan sobre el game_pak principal con `--all-worlds` y los conjuntos `14855,14862,14838,14864,14865,14866,14867,14868` y `16879,15321,14856,14857,14858,14859,14861`; conservar stdout como los dos CSV respectivos. PakReturnPointScan extrae los destinos. No se escribe al cliente.

`reconstruccion_cliente_10/scripts/rebuild_garden_gate.py` verifica las colocaciones contra los dos catálogos y compara el overlay. `--write` genera el archivo si falta y rechaza sobrescribir uno distinto. Excluye colocaciones de mundos de instancia ajenos. El modelo y el hotspot de entrada están aproximadamente en (20571.805,31848.8,604), zona 354. El destino 1005 queda en (499.448,38375.493,131.172), zona 379.

## Validación y despliegue

Restore y build Release correctos; 2703 pruebas aprobadas, cero fallos. Las pruebas nuevas verifican concesión global idempotente sin Patron, representación del permiso en el paquete, límites de equipo/nivel y rechazo de dirección desconocida. No constituyen aceptación visual del cliente.

Game fue recreado el 2026-09-08 01:01:14 UTC; listo a las 01:02:57 UTC. Verificados listeners 1239/1240/1250, conexión a Login y Web API 1280. `startup.log` conserva evidencia. Imagen, DLL, overlay y configuración efectivos figuran con hashes en el manifiesto. Compact y game_pak no se modificaron. Se conservaron los cambios anteriores de las misiones 9565 y 9989.

## Aceptación pendiente y Zones

Pendiente probar el cruce en el cliente tras volver a iniciar sesión, para recibir el permiso ULC efectivo. En la inspección del perfil de Control Center sólo figura habilitada la zona 354 entre 354/379/378/382; 379 (Gatekeeper Hall), 378 y 382 no figuran en ese perfil. La entrada requiere que el usuario tenga operativa la zona 379; las zonas 378 y 382 sirven el interior de Garden. No se operó el lifecycle de ninguna Zone, conforme a la preferencia permanente del usuario. No se afirma que el cruce ni toda la cadena interior estén probados.

## Reversión

Respaldo en `E:/AAEmu/rama_10/backups/garden-gate-20260907`: `aaemu_game.sql` y `CharacterSettings.before.json`. Imagen anterior etiquetada `aaemu-world:rollback-pre-garden-gate-20260907`.

Para revertir la política únicamente, establecer FreeGardenAccess=false tanto en la configuración versionada como en el montaje y reiniciar Game. Para revertir todo el despliegue, restaurar CharacterSettings.before.json al montaje, retirar sólo el nuevo doodad_spawns_aa10_garden_gates.json del montaje, retaggear la imagen de rollback a aaemu-world:10.0.2.13-r575-local y recrear únicamente Game con los dos archivos compose habituales. No restaurar la base de datos por defecto: esta entrega no mutó cuentas; restaurar el dump descartaría progreso posterior.
