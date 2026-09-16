# Alpha Nuia — barrido racial y despliegue del 2026-09-15

## Alcance

Petición: planificar alpha limitada a Nuia por RAM, maximizar actividades útiles
de prueba y barrer/reparar elfos y enanos a partir de la evidencia nuiana.
Plan operativo: `Docs/AA10NuiaAlphaPlan_es.md`.
Identidades, hashes y validaciones: `NUIA_ALPHA_20260915.manifest.json`.

Target canónico `E:/AAEmu/rama_10/server/AAEmu`, branch `rama_10`, HEAD
`45bba0ad49fee55ab30a80168b4d6caefbb9ac87`. Se consultó por fetch el padre exacto
`upstream/client_version/zone-10.0.2_r575`; no se integró ni cambió de rama.
El árbol tenía 61 entradas modificadas/no versionadas antes de esta tarea.
Los cambios de misiones, combate y portales previos se preservan.

## Diagnóstico y corrección

54 misiones élficas y 68 enanas; se inventarían además 76 de continuación
compartida. Los 1.154 actos habilitados tienen clases/loaders y detalle r575.
La frontera era espacial y de datos desplegados: 120 posiciones ausentes en
fuente/runtime, 143 solo presentes en fuente y siete solo en runtime.

El nuevo overlay contiene 270 posiciones/43 templates, con coordenadas, rotación,
escala y único grupo Start probados en game_pak/full/compact. Reutiliza el loader
AA10 y su deduplicación; no altera protocolo, paquetes, estado persistente ni
fases del motor. El padre no aporta este overlay. AA8 se consultó como índice de
historia racial; no se portó código ni se tomaron coordenadas de AA8.

El postbarrido arroja cero posiciones nativas observadas pendientes en elfos y
enanos. Se preservan seis referencias sin placement demostrado para investigación,
en vez de inventar spawns. Dos gaps compartidos posteriores al corte siguen fuera
de la reparación. El detalle está en la planificación y `audit.json`.

Se corrigió el auditor de proveedores para incluir recompensas selectivas:
139/139 objetos con metadatos de suministro. 223/224 NPC del barrido ampliado
aparecen en spawners nativos verificados; NPC14750/quest6584 sigue sin demostrar.

El índice TM estaba obsoleto respecto de los JSONL contextuales. El nuevo auditor
respeta estos últimos: 2.053/2.053 textos auditados aprobados coinciden con la
compact suelta española. No se tradujo, aprobó ni modificó texto automáticamente.

## Validación y despliegue

- `dotnet restore`: correcto; advertencias de dependencias existentes.
- Build Release: cero errores, 163 advertencias.
- Suite: 2.832 correctas, cero fallidas/omitidas.
- Nueva prueba de catálogo contra fixture extraída: posición, Euler, escala,
  fase, unicidad y deserialización `InitialFuncGroupId`.
- Overlay fuente y bind mount con SHA-256
  `18082656bf3d112806c284b6a5a4447d86f243a84bf6e061b7ed0e7ce198b370`,
  confirmado también dentro de `aaemu10-game-1`.
- Spawners129/150/154/192/193/328 preparados en la raíz Zone canónica,
  con MD5 exacto de sus entradas del game_pak nativo. No se operó ZoneHost.
- Se reinició únicamente `aaemu10-game-1`, conservando la imagen existente.
  Es un despliegue de datos montados; no incluye los cambios C# ajenos del worktree.
- Arranque: 23:02:17 UTC, gate Strict de 43.696 actos/0 findings y 8.901 quests;
  23:02:45, puertos1239/1250 y registro en Login; 23:02:47, 46.076 doodads en
  main_world. Contenedor healthy, sin reinicios automáticos.
- El log conserva avisos de SubZone/catálogos y TowerDef sin zonas disponibles.
  No se declara arranque sin warnings ni aceptación retail de las zonas raciales.

No se modificaron DB, compact, game_pak ni cliente. No se publicó commit/push.
Rollback acotado en
`E:/AAEmu/rama_10/backups/nuia-alpha/20260915-230048/manifest.json`:
verificar hashes y retirar únicamente archivos nuevos; reiniciar Game para
retirar el overlay. No hace falta restaurar bases de datos ni imagen.

## Siguiente aceptación concreta

El usuario inicia en Control Center el perfil129 para un elfo nuevo o328 para un
enano nuevo, según la posición persistida/plantilla. Verificar ZoneLoaded,
conexión World y heartbeat antes de entrar. No reactivar perfiles adicionales
por inferencia ni usar el lanzador agregado.

Primera prueba: creación/introducción y quest2385 (elfo) o3484 (enano), con
recompensas selectivas y sin saltos GM. Continuar según la matriz de capítulos.
La hoja `acceptance-racial.csv` contiene 122 filas pendientes para registrar
resultado, personaje, evidencia y reporte. La aceptación nuiana previa sigue
siendo referencia, no aceptación implícita de estas razas.

La continuación sale de Nuia en7139 según catálogo; revisar el viaje de7137 antes
de fijar el límite efectivo. Falta implementar/probar el cierre geográfico de
la alpha y medir RAM bajo jugadores. La alpha aún no se declara lista para abrir.
