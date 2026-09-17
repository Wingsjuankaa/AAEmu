# Fishspots GM — 2026-09-16

Entregado `/fishspots [on|off]`: bancos de pesca presentes del mundo e instancia actuales, sin límite de distancia en modo GM. Nivel efectivo requerido 100. Estado temporal, independiente del radar de barco. No cambia cliente, SQLite, spawns ni lifecycle de Zones.

Implementación y aceptación pendiente: [AA10FishSpotsCommand_es.md](../../Docs/AA10FishSpotsCommand_es.md).

## Gates y runtime

- Restore/build Release correctos; 4.617 tests correctos, 0 fallos, 0 omitidos. Siete casos nuevos.
- Game desplegado desde la rama `rama_10` y el árbol local existente, preservando trabajo ajeno de Squad/Features.
- Imagen `sha256:a2410c071173c066a9eb7127298d994d684815961b92f7d076a33fd0a454a204`.
- Contenedor iniciado `2026-09-16T20:56:27.985252884Z`; health healthy. Game iniciado y registrado en Login a las 20:57:41 UTC.
- Listeners internos 1239/1240/1250/1280 verificados; API de personajes online responde.
- Quest gate Strict: 43.696 actos habilitados, findings=0.
- 102 bancos cargados en `main_world(0)`; 0 en `arche_mall_world(14)`.
- Solo cuatro errores conocidos de Item Smelting 29–32, deprecado. Sin nuevos errores de scripts.
- AccessLevels source/mount/container SHA256 `2A6BBFF970E5025DF61366C03703780BCA49BA4DF2851E2A909BA74AB946C17E`.
- Ambas copias de AAEmu.Game.dll en el contenedor SHA256 `064106ea794266704a77bb94d4aaa3f29f1696fc467db352edf3cdcd77b84dd0`.
- No había personajes online ni Zones registradas al finalizar. No se han operado Zones ni reiniciado Login/DB.

## Evidencia y rollback

`E:/AAEmu/rama_10/artifacts/fishspots/20260916/manifest.json`, logs restore/build/tests/Docker/startup y respaldos de los archivos previos. Imagen anterior `sha256:63166f4afdc9fc02937774c31c2975d28952002f639bb7667c956d6f65a66fb3`, tag `aaemu-world:before-fishspots-20260916`.

Pendiente exclusivamente aceptación visual retail de `/fishspots` y `/fishspots off`. Las pruebas de paquetes no prueban por sí solas el dibujo de los marcadores ni su eliminación en la UI nativa.
