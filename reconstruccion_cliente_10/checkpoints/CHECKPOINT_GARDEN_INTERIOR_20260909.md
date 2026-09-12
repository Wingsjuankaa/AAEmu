# Garden: teletransportes interiores

Dannia pudo entrar en Gatekeeper Hall (379) e interactuar con sus puertas; el objetivo de «Al Elysio» avanzaba, pero el traslado no ocurría. Los intentos de skill 43677 a las 00:59:25 y 01:00:16 UTC del 2026-09-09 registraron `Unknown special effect: ZonePermissionCheck`. Las zonas 378 y 382 ya tenían ZoneLoaded y heartbeats: no era ausencia del host de destino.

## Contrato y alcance

La SQLite completa r575 y la compact efectiva coinciden en cinco SpecialEffect de tipo 184, selector value1=149 y return_point en value2:

| Skill | SpecialEffect | Return point | Zone |
|---|---|---|---|
| 43677 | 51372 | 1008 | 378 |
| 43634 | 51373 | 1006 | 378 |
| 43698 | 51374 | 1010 | 382 |
| 43870 | 51375 | 1013 | 382 |
| 43687 | 51376 | 1009 | 378 |

Evidencia: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/garden-interior-20260909/contract.json`. El padre `upstream/client_version/zone-10.0.2_r575` no implementa el handler; la búsqueda en AA8 tampoco encontró un equivalente. No se porta semántica desde otra versión.

El significado nativo general del selector 149 sigue sin resolverse. El handler implementa exclusivamente la personalización pública de Garden ya autorizada: `FreeGardenAccess=true`, nivel mínimo 55 y equipo mínimo 8000. Sólo admite esos cinco puntos y verifica su zona. Rechaza otros selectores, destinos, parámetros adicionales y la política privada; no interpreta 149 como zoneId ni zoneGroupId.

Los destinos proceden de PortalManager y de los return_points nativos ya convertidos a coordenadas del mundo; no se introducen coordenadas manuales. El traslado delega en Return, que comprueba ZoneLoaded antes de cambiar el personaje y reutiliza el transporte existente dentro de main_world. Las puertas de regreso usan Return/1196 y no requieren esta corrección.

## Validación y entrega

Build Release correcto. Suite completa: 2720 pruebas aprobadas, cero fallos y cero omitidas. Incluye las cinco puertas, rechazo por nivel/equipo/configuración/selector/punto inválido y rechazo sin modificar al personaje cuando faltan hosts 378, 379 o 382. Estos tests no sustituyen la aceptación del cliente retail.

No se modifica game_pak, compact, DB ni configuración. Se conserva la imagen previa con tag `aaemu-world:rollback-garden-interior-20260909`. La imagen y hashes efectivos del despliegue quedan en el manifiesto adjunto. Los logs de build y pruebas se guardan bajo `E:/AAEmu/rama_10/artifacts/garden-interior-*`.

Rollback: etiquetar la imagen de respaldo como `aaemu-world:10.0.2.13-r575-local` y recrear únicamente game con los mismos dos archivos compose. No requiere rollback de datos. El usuario controla el reinicio de los perfiles de Zone tras reiniciar World.

Aceptación pendiente: volver a entrar con Dannia, usar la puerta y verificar traslado a 378/382, entrada del personaje en el host de destino y regreso a 379 sin desconexión. La implementación no cierra todavía la semántica general nativa de ZonePermissionCheck.

Runtime verificado: Game listo a las 01:17:30 UTC, listeners 1239/1240/1250/1280, API World correcta, imagen nueva y DLL comprobadas, cero reinicios automáticos. Tras recrear Game los procesos Zone se cerraron: snapshot 01:17:59 UTC con Zones=[] y PlayerCount=0. Se indicó al usuario relanzar 379/378/382 en Control Center. No se operó lifecycle de Zones en esta corrección.
