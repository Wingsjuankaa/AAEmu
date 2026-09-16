# Cliente LAN para alpha Nuia — 2026-09-15

## Entrega

Distribución física independiente creada y verificada en:
`E:/AAEmu/rama_10/distributions/AA10-Nuia-Alpha-es_ES-LAN-20260915`.

245 archivos manifestados más el propio manifiesto; 94.284.025.007 bytes
manifestados (**87,81 GiB**). Fuente principal conservada sin cambios.
El usuario copia la carpeta completa al disco del segundo PC y abre
`Jugar en LAN.cmd`. Launcher portable 0.2.1; Login `192.168.100.20:1237`;
es_ES sobre canal interno `en_us`.

## Datos incluidos y excluidos

Conservadas `game/db/compact.sqlite3` (470.106.112 bytes) y
`game/db/game.sqlite3` (552.178.688 bytes). La segunda es el catálogo estático
del cliente con personalización parcheada; no es una DB de cuentas/personajes.
Su entrada efectiva cifrada sigue dentro del PAK. El estado de jugadores reside
en MySQL del servidor.

27 exclusiones, 1.019.601.989 bytes: 13 respaldos/estado de actualizaciones,
2 ejecutables ZoneHost, 6 cachés/logs, 5 manifiestos/accesos editoriales y un
`game/game_decrypted.sqlite3` vacío. Se conservan bibliotecas originales de
Bin64; no se recortan dependencias nativas por conjeturas sobre su nombre.
Sin credenciales, perfiles de usuario, editor de traducción ni Control Center.

## Validaciones realizadas

- Identidad de cliente/launcher/DB fijada contra checkpoints; SQLite quick_check OK.
- Copia física sin hardlinks; identidad de archivos distinta de la fuente.
- Hash calculado durante la copia y repetido leyendo cada archivo del destino.
- PAK completo: `B70AA4AA707E188BA8736D9770F542109377446EABFCA8142A7517B811FC8C22`,
  92.412.641.792 bytes; coincide con Alpha HUD V10.
- Reextracción read-only de 11 entradas: ambas DB, selección racial,
  panel alpha, HUD, reportes, ambos iconos custom, mapa, icono de logro y crafting.
  Todas coinciden con sus identidades aprobadas; compact empaquetada/suelta iguales.
- Inventario final exactamente igual al manifest más el propio manifest;
  sin `.partial`, `BUILD-INCOMPLETE.txt`, `.bak` ni ejecutables ZoneHost.
- Sintaxis de helpers PowerShell comprobada. Comprobador TCP ejecutado:
  1237/1239/1250 accesibles **desde el anfitrión**.
- IP del anfitrión `192.168.100.20/24`; reglas AAEmu10 LAN habilitadas;
  Login anuncia `192.168.100.20:1239`, alta automática habilitada.
- No se modificaron red, firewall, servidor, bases ni procesos ZoneHost.
  No fue necesario reconstruir o desplegar Game/Login.

**Aceptación desde el segundo PC: pendiente.** Ni la conectividad observada desde
el anfitrión ni los hashes prueban aún login/entrada/ventanas en ese equipo.
La copia incluye verificadores de conexión e integridad para hacer esa prueba.
El panel alpha sigue requiriendo autorización del personaje en el servidor.

## Reproducción y evidencia

Herramientas: `Scripts/BuildAa10LanClient.py` (dry-run por defecto),
`Scripts/VerifyAa10LanPackage.py`, `Scripts/ClientDistribution/`.
Guía: `Docs/AA10LanClientDistribution_es.md`.
Evidencia: `E:/AAEmu/rama_10/artifacts/client-distribution/nuia-lan-20260915`.
Manifest hermano: `NUIA_LAN_CLIENT_20260915.manifest.json`.

Target rama_10 HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`;
padre `upstream/client_version/zone-10.0.2_r575`
`d892934591b7a52ee082a5f9a23b277d074d043d`. Cambios ajenos preservados;
sin integración, commit, publicación externa ni carpeta SMB creada.

La reversión consiste en volver a utilizar el cliente de trabajo original;
no se sobrescribió ningún archivo de aquel ni del servidor.
