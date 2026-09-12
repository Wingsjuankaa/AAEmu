# Gatekeeper Hall 379 — carga nativa sin spawner estático

El usuario autorizó iniciar únicamente la 379 para observar su comportamiento. Runtime canónico r575, host 1A2F91A758E08D2597ED8A6DC8C23B4C65A6C69A2EDE782DA4D9A5E2079F1E03 y DLL 8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A. Se usó el helper ConPTY del Control Center, argumento `+zone gatekeeper_hall`, log/save `zone-379`. No se fabricó npc_spawners.g ni se alteró el paquete.

Resultado: ZoneLoaded 2026-09-09T00:46:17.0288256Z, ZoneId 379, InstanceId 0, cero spawners/unidades y heartbeats continuos. La advertencia de NpcManager por archivo ausente es recuperable. Hay advertencias de material, textura de terreno y quest_area.xml; no impidieron cargar. La sala tiene una área de misión cargada. La prueba no demuestra todavía interacción/combate/misiones ni cruce del cliente.

Host PID 54228, helper PID 44916. Se deja únicamente la 379 activa conforme a la autorización para probarla. Evidencia en `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/garden-gate/zone379-probe-20260908` (`native.log`, `host-status.log`, `world-loaded.json`, `process.json`, `runtime-hashes.json`).

Corrección en repositorio separado `tools/AAEmu.ControlCenter`, rama main, versión 0.1.8: excepción estricta 379/gatekeeper_hall/main_world con SHA de DLL verificado. Se comparte en preparación y diagnóstico, conserva MD5 exigidos por perfiles y no exime otras zonas. El panel ofrece Preparar zona y describe la ausencia de NPCs estáticos. Se incorporó 379 al perfil `aa10-local-solzreed` mediante el servicio existente, con respaldo previo; sin reiniciar Game ni operar otras Zones.

Validación: 65 pruebas, una omitida preexistente, typecheck y smoke SQLite/Electron. Preparación real aprobada; entrega portable/instalador 0.1.8. Consulte `tools/AAEmu.ControlCenter/docs/releases/0.1.8-GATEKEEPER_ES.md` para pipeline, helper ocupado y recuperación.

Se cierra la duda del checkpoint GARDEN_RETURN_AND_TEXTS_20260907 sobre la carga sin archivo de NPCs. Queda pendiente que Dannia cruce y compruebe la interacción en la sala.
