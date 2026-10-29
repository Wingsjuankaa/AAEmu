# Acceso al alfa por Playit — 2026-09-25

## Configuración aplicada

Túnel `AA10 Alpha - Login Game Stream`, ID `9300a2e7-2d0d-4aea-af85-d51d01fa3155`, región Brasil, TCP x3. Agente Windows 0.17.1 `from-key-78a4`, conectado a la red Playit en Chile. Proxy Protocol desactivado: AA10 recibe su protocolo nativo sin cabeceras adicionales.

| Canal | Endpoint público | Destino del agente | Puerto en contenedor |
|---|---|---|---|
| Login | laurel-filmed.tun.ply.gg:49172 | 127.0.0.1:12370 | 1237 |
| Game | laurel-filmed.tun.ply.gg:49173 | 127.0.0.1:12371 | 1239 |
| Stream | laurel-filmed.tun.ply.gg:49174 | 127.0.0.1:12372 | 1250 |

DNS verificado: `198.22.204.17`. Login anuncia esa IPv4 y Game 49173. Stream anuncia 49174 manteniendo el listener interno 1250 mediante la nueva propiedad opcional `StreamNetwork.AdvertisedPort` (0 conserva el puerto de escucha).

El paquete X2EnterWorldResponse no cambia de formato: utiliza el puerto anunciado en sus dos campos de puerto. La IP común evita cambiar la selección nativa `cl_serveraddr`. No se modifica game_pak ni el protocolo del cliente.

La configuración pública está en `.server_files/docker-compose.playit.yaml`, aplicada después de `docker-compose.yaml` y `.server_files/docker-compose.aa10.yaml`. El perfil activo de Control Center también incluye este override. Se preservan las conexiones locales existentes y solo se añaden los tres destinos loopback del agente. World 1240, Web API 1280, DB y administración no tienen túneles.

Los clientes deben utilizar el endpoint público de Login incluso desde este PC para mantener el mismo recorrido de red que el Stream anunciado.

## Cliente

Entrega simplificada vigente (25/09):
`E:/AAEmu/rama_10/distributions/AA10-Nuia-Alpha-es_ES-Internet`.
Copiar completa y abrir **Jugar ArcheAge.exe**; consultar `README.txt` para
las instrucciones. El portable 0.2.3 incorpora el perfil Internet y prepara
el español, por lo que ya no hacen falta los scripts/ZIP descritos debajo.
La distribución LAN se renombró y sus helpers quedaron fuera del cliente en
`artifacts/client-distribution/internet-clean-20260925/retirados`.

Configuración histórica previa al launcher 0.2.3:

El perfil activo del Simple Launcher local es `AA10 Alpha Internet`. El perfil LAN permanece guardado. Canal español interno: en_us.

Para el otro PC, extraer `E:/AAEmu/rama_10/artifacts/playit/20260925/AA10-Conexion-Internet.zip` junto al launcher y game_pak; cerrar el launcher y ejecutar `Jugar por Internet.cmd`. El script detecta el cliente en esa carpeta, respalda los perfiles y crea/actualiza únicamente `aa10-playit`, sin incluir credenciales. Los dos archivos también están añadidos a la distribución LAN original.

Playit debe permanecer ejecutándose en el anfitrión. No se compró ningún plan ni se cambiaron suscripciones. La cuenta ya tenía Premium activo. El usuario autorizó expresamente la declaración de uso requerida por el asistente.

## Verificación

- Restore y build Release correctos. 5.667 tests correctos, 0 fallos, 0 omitidos.
- Pruebas del paquete cubren puerto local por defecto y puertos anunciados distintos para autoridad normal y GM; el listener no cambia.
- Imagen desplegada `sha256:8c8e09683108d90b54da9940f5b26d482203f8768a7e309f9c9c78c92af366d3`; ambas copias de Game.dll: `b173340ab8a2bf8efec7c3627688716ec8a5cfa6cad0e97962518935e6a71d8d`.
- Login y Game saludables. Game arrancó y se registró en Login a las 00:34:17 UTC del 26/09. Quest Strict findings=0.
- A las 00:34:50–51 UTC las conexiones TCP al hostname público, puertos 49172/49173/49174, llegaron respectivamente a LoginConnectionHandler, GameProtocolHandler y StreamProtocolHandler. No se acepta solo la conexión al borde de Playit como prueba: los logs del backend corroboran el recorrido.
- Esas pruebas salieron desde el propio anfitrión hacia el endpoint público. **Pendiente** una sesión completa del cliente desde otra red: autenticación, selección de world/personaje, Stream y entrada al mundo.
- Sin jugadores ni Zones registradas al finalizar; no se inició/detuvo ninguna Zone. Su lifecycle queda en manos del usuario.
- El startup registra los cuatro errores de Smelting deprecado 29–32 y dos mensajes de desconexión Zone desconocida (zoneId=0) a las 00:32:58 UTC, antes de cargar Game. No atribuirlos al túnel ni afirmar un startup sin errores.

## Respaldo y rollback

Evidencia, ZIP, capturas y perfiles previos en `E:/AAEmu/rama_10/artifacts/playit/20260925`. Imagen anterior: tag `aaemu-world:before-playit-20260925`. Para regresar a LAN: retirar solamente el override Playit del perfil de Control Center, recrear Login/Game con los dos Compose anteriores, seleccionar el perfil LAN del launcher y desactivar el túnel. La imagen nueva admite LAN sin configurar AdvertisedPort. No restaurar un perfil completo si contiene cambios posteriores; retirar únicamente las entradas de esta tarea. Mantener DB y volúmenes.
