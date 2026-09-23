# Cambio de red local — 23 de septiembre de 2026

Target: `rama_10`; padre declarado: `upstream/client_version/zone-10.0.2_r575`.

El cambio de proveedor/router cambió la interfaz activa Ethernet 4 de
`192.168.100.20` a `192.168.1.94/24`, gateway `192.168.1.1`, mediante DHCP.
Se trata de la dirección LAN; no se ha configurado acceso público por Internet.

## Configuración aplicada

- `.server_files/docker-compose.aa10.yaml`: Login anuncia Game en
  `192.168.1.94:1239` y conserva `SkipHostResolve=true`. Login 1237, Game 1239 y
  Stream 1250 se publican en la nueva dirección y en `127.0.0.1`. ZoneAuthority
  1240 se publica únicamente en la nueva dirección LAN.
- `E:\AAEmu\rama_10\zones\retail-zone-server-r575\system.cfg`:
  `world_serveraddr = "192.168.1.94"`; puerto 1240. Este archivo lo consume
  ZoneHost también al iniciarse desde Control Center.
- Perfiles existentes de `%APPDATA%\aaemu-lan-launcher\profiles.json` y
  `%APPDATA%\aaemu-simple-launcher\profiles.json`: destino Login actualizado.
  El perfil de Control Center mantiene `127.0.0.1:1237`, que sigue disponible.
- `Scripts/ClientDistribution/Comprobar-LAN.ps1`: nueva dirección predeterminada;
  acepta `-LanAddress` para comprobar otra dirección sin editar el script.
- `E:\AAEmu\rama_10\runtime\launchers\configure_aa10_lan_firewall.ps1`:
  destino `192.168.1.94`, origen permitido `192.168.1.0/24`.

Se recrearon únicamente Login y Game, sin reconstruir imágenes ni modificar DB,
cliente, mecánicas o estado de personajes. Zones y cliente permanecen bajo
control del usuario. Los paquetes históricos distribuidos y sus manifiestos
conservan sus hashes originales; en otro PC debe cambiarse el host del launcher
a `192.168.1.94`.

## Firewall y validación

Comprobaciones realizadas desde el servidor:

- Compose válido y Login/Game recreados con las mismas imágenes.
- Log de Login: `Game Server 1: AAEmu.Game -> 192.168.1.94:1239`.
- A las 22:15:06 UTC: `GameNetwork - Network started`,
  `StreamNetwork - StreamNetwork started` y
  `GameService - Server started! Took 00:01:45.7553625`.
- TCP 1237/1239/1250 responde en `127.0.0.1` y `192.168.1.94`;
  TCP 1240 responde en `192.168.1.94` y no en loopback, según lo previsto.
- Ambas copias de `AAEmu.Game.dll` en el contenedor conservan SHA-256
  `f5a11c8c3c1513baf726b7b5e39540b4b67fe10393b34ffdc04e46848fbb8136`.
- Los perfiles JSON se parsean y apuntan al destino previsto. No se ha probado
  la entrada con el cliente ni la conexión desde un segundo PC.

La comprobación TCP puntual de 1240 crea una conexión sin protocolo Zone y por
ello registra una desconexión `zoneId=0`; no se inició ningún proceso ZoneHost.

El usuario aplicó las reglas desde PowerShell como administrador. Se comprobó
después que `AAEmu10 LAN Login 1237`, `AAEmu10 LAN Game 1239` y
`AAEmu10 LAN Stream 1250` apuntan a `192.168.1.94` y admiten origen
`192.168.1.0/24`. Para repetirlo incluso cuando Windows PowerShell bloquee la
ejecución de scripts, usar una excepción limitada al proceso:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'E:\AAEmu\rama_10\runtime\launchers\configure_aa10_lan_firewall.ps1'
```

No se deshabilita el firewall ni se cambia el perfil público de Windows.
MySQL permanece publicado únicamente en `127.0.0.1:24306`; no se publican
WebAPI ni administración Docker.

## Respaldo y repetición del despliegue

Respaldo de los cinco archivos modificados y las reglas anteriores:
`E:\AAEmu\rama_10\artifacts\runtime\lan-network\20260923-ip-change`.
Contiene perfiles locales: no compartirlos ni incorporarlos a Git.

Desde `E:\AAEmu\rama_10\server\AAEmu`:

```powershell
docker compose -p aaemu10 -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml config --quiet
docker compose -p aaemu10 -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml up -d --no-deps --no-build login game
& .\Scripts\ClientDistribution\Comprobar-LAN.ps1
```

Para revertir, restaurar cada archivo desde el respaldo a su ruta de origen y
recrear Login/Game con el mismo comando. La IP anterior solo funcionará si vuelve
a estar asignada al equipo. Las imágenes desplegadas se mantienen:

- Login: `sha256:3b5df8db3e83ff45380b4bec5036ab60723d37a9b4e2986805e0cf7062f93c9a`.
- Game: `sha256:7137fd39c3114a35dcec6382859a13afa4e7541ebf389104bf4c99e63e6a3d87`.
