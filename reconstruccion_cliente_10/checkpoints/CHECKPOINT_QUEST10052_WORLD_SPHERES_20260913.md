# Contraatacar 10052: áreas de Delphinad separadas por mundo

Target `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`, HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`.
Padre consultado: `upstream/client_version/zone-10.0.2_r575` (`1017677b40be6508861a8fb74e9d09fa496873c9`). Contiene el mismo cache estático único. Sin cambio de rama, commit ni push; preservados arreglos pendientes.

## Evidencia y causa

El usuario entrega10050 y acepta10052 correctamente; queda junto a Melisara con el objetivo de llegar a la base sin avanzar. Log16:46:06 UTC: `QuestActObjSphere(860).RunAct`, quest10052, sphere3012, todavía sin entrada. Consulta de reportes de quest10052 sin resultados. No se cambia progreso de Dannia.

SQLite r575: act69509, componente43720, objetivo860, sphere3012; entrega mediante doodad14992. Pak original leído exclusivamente en modo rb y MD5 de ambas entradas verificado:

- `game/worlds/instance_phantom_of_delphinad/level_design/zone/384/client/quest_sign_sphere.g`, 3062 bytes, SHA256 `2c2839c4d5101b6a3211fd550718dd0f81393ce00e9ee8c12630399c952f06dd`. Componentes43720/43705 de quest10052, posición local710.143/1075.59/288.282 y radio3.
- `.../384/world_server/quest_area_sphere.g`, 1587 bytes, SHA256 `1032c02131af13fff2b92a8691802a1e978178b7b8328c56d4349e3ceba03c31`. Sphere3012, posición local713.495/1075.36/289.325 y radio10.

`SphereQuestManager.Load` sólo cargaba `_sphereQuests`, `_questAreaSpheres` e índice espacial cuando los campos estáticos eran null. Main los inicializa primero; instancias posteriores reutilizaban exclusivamente la geometría de main. El volumen y el marcador de Delphinad existían en el pak configurado como ClientData, pero no llegaban al gestor de la copia.

## Corrección

Caché concurrente por nombre exacto de WorldTemplate y publicación Lazy atómica de los tres índices. Cada copia referencia su geometría; mantiene locales las colas de triggers y estados de jugadores. Dos copias del mismo template reutilizan una única carga. Las consultas estáticas de áreas seleccionan el mundo solicitado; las de marcadores recorren sólo catálogos ya cargados. Se mantienen parser, coordenadas, radios, requisitos y objetivos nativos.

Es una reparación del aislamiento de la caché del servidor; no requiere contrato AA8, cambio de protocolo, archivos nuevos de cliente ni edición del pak/compact.

## Pruebas y despliegue

Restore y build Release correctos; **2815/2815 tests aprobados**. Nuevas pruebas: main antes de Delphinad con áreas en coordenadas coincidentes, consulta independiente del componente43720/sphere3012, rechazo fuera del radio y carga concurrente de ocho copias con una sola lectura y triggers separados. Se adaptaron las cinco pruebas existentes de items/áreas a la caché por mundo manteniendo todas sus aserciones.

Imagen Game `sha256:ac3263b3af10069ddfcec0edccbdb7b7e06073ec5f8ae68984b6918d46757b7d`, desplegada el13/09 a16:58 UTC. Artefactos en `E:/AAEmu/rama_10/artifacts/delphinad-spheres`. Respaldo y patch en `E:/AAEmu/rama_10/backups/delphinad-spheres-20260913`; rollback de imagen `aaemu-world:rollback-delphinad-spheres-20260913`. Sin escrituras DB/compact; no restaurar progreso antiguo.

Aceptación retail pendiente: el usuario restaura sus Zones desde Control Center si el reinicio las desconectó, entra con Dannia y vuelve al punto de Melisara. El objetivo debe registrar la llegada y habilitar la entrega según los requisitos nativos. No se declara validada la cadena posterior. El lifecycle de ZoneHost permanece a cargo del usuario.

Runtime: Server started y API World a17:00:04 UTC, Game healthy, cero Zones conectadas tras reinicio. Cargadas2632 áreas de main y134 de otro template separado, acreditando carga por mundo. No FATAL ni errores nuevos de áreas; se conservan cuatro diagnósticos preexistentes de Item Smelting29–32, fuera de alcance. La carga de Delphinad se verificará al volver a crear su instancia con el usuario.
