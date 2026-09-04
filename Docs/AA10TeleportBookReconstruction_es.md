# Teleport Book: auditoría y reparación de descubrimiento

Fecha: 2026-09-04 UTC (2026-09-03 Chile). Target: Returns 10.0.2.13 r575.
Branch `rama_10`, HEAD de partida `ac4f3ecb2b3d2b996e74e75509055cc3e593a3c7`.
Padre exacto consultado/fetch: `upstream/client_version/zone-10.0.2_r575`,
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. AA8 se utilizó sólo como comparador estructural.

## Resultado

**Hiram Cave no faltaba en el catálogo. Faltaba conectar su descubrimiento nativo al libro.**
La carga desde `recalls.json` ya se ampliaba con SQLite y `game_pak`; por eso añadir otra
coordenada al JSON no corregía el disparador. Se reparó el puente Zone → Game para distritos
de Memory Tomes, válido para todo el catálogo y no sólo para Hiram.

Clasificación: reparación de mecánica nativa, no contenido nuevo. Implementación y pruebas
automatizadas completadas; registro de Hiram Cave aceptado por el usuario. No se declara probado el viaje
a los 190 destinos ni se concede el libro completo a ningún personaje.

Catálogo visible de cada entrada: [AA10TeleportBookCatalog_es.md](AA10TeleportBookCatalog_es.md).

## Cobertura y excepciones

La relación `doodad_funcs → doodad_func_bindings → district_return_points → return_points`
identifica **192 destinos, 187 distritos y 1452 relaciones por facción**. Los datos coinciden
en SQLite completa, compact retail y compact runtime. Se excluyen bindings a Zone explícita,
portales privados, cementerios y efectos de retorno de quests sin relación con Memory Tomes.

| Clasificación | Cantidad | Tratamiento |
|---|---:|---|
| Destinos con colocación `return_point.g` y áreas de distrito nativas | 185 | Catálogo automático y nuevo aviso de entrada a distrito |
| Jardines conservados por JSON histórico | 5 | Compatibilidad por subzona, sin inventar polígonos |
| Entradas sin colocación demostrada | 2 | No activadas con coordenadas inventadas; evidencia pendiente |

Los cinco jardines son 520, 521, 522, 523 y 565. No se encontró su área estática en los
`district.xml` extraídos; conservarlos no equivale a validar la colocación histórica como retail.

Las dos excepciones son:

- **858 / distrito455 / Player Nation Defense Base**: sólo facción166. Existe área nativa,
  pero no colocación exacta `whale_song_c`. `gv_whale_song_c` es otro destino (cementerio)
  y no se utiliza como sustituto.
- **1076 / distrito503 / Golden Ruins Community Center**: nombre coreano de base avanzada,
  editor `o_ruins_of_gold_02`. Sin colocación ni área estática encontradas. No se ha demostrado
  si requiere un spawn condicionado, datos adicionales o es una entrada retirada.

`return_points.use_additional` no se interpreta como prueba de spawn dinámico. No existe
una columna `dynamic` en esa tabla. La ausencia estática no acredita por sí sola obsolescencia.

## Contrato nativo y causa

Zone DLL r575 SHA256 `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`.
Ghidra sobre esa misma DLL, sólo lectura:

- `FUN_3932b1b0`: callback de entrada a área y emisión de `ZWEnterAreaPacket` / opcode0x23.
- `FUN_3932b120`: grupos permitidos 16, 19, 20, 21 y **22**.
- `FUN_39362a50`: asigna unit, grupo y dos valores al paquete.
- `FUN_393691c0`: serializa **unit Bc(3), groupId u8, value1 i32, value2 i32**.

No confundir el byte `groupId` con un ID de subzona o de quest. En `district.xml`,
`Group=22`, `value1=district_id`; `Area.Id` suele ser cero. El puente previo llamaba
únicamente a quests y descartaba el distrito para el libro.

También se estaban insertando distritos en el diccionario indexado por subzonas. Sus
números coincidentes no significan la misma región; podían registrar destinos equivocados.
Ahora son catálogos separados. Se conserva la interpretación histórica sólo al leer visitas
anteriores, para no quitar destinos guardados por versiones previas.

### Hiram Cave

- Return point933 `rp_hirama_cave`, distrito473, Memory Tome13136, binding215.
- Zone351, `return_point.g`: local `(2667.62,1045,368.722)`, rotación `-0.383973` rad.
- Mundo: `(20075.62,29717,368.722)`.
- `district.xml`: `LevelDesignShape_351_gahee_2`, Group22/value1=473, altura150.
- El área de cliente1267 pertenece a **Group18** y no es el distrito473.
- La posición de retorno no cae en una subzona cliente del catálogo; eso no invalida su
  área de registro nativa. El warning anterior exponía esa diferencia geométrica.

## Implementación y persistencia

- `ZoneQuestAreaBridge` envía entradas Group22/value1 válido a `CharacterPortals.NotifyDistrict`.
- El registro sólo admite un destino colocado y asociado a un Memory Tome del distrito,
  con mapping para la facción del personaje o su facción madre. No concede destinos de otra facción.
- Registro idempotente, reconstrucción del panel y envío del `SCCharacterReturnDistrictsPacket`
  existente; wire conserva `id=distrito`, `type=return_point` y ReturnDistrictId sin alterarlo.
- El índice directo por return point ya no depende de encontrar una subzona cliente.
- Se conserva el descubrimiento previo por subzonas físicas, separado de los distritos.
- `portal_visited_district.subzone` es INT firmado. Nuevas visitas de distrito usan bit30;
  nuevas subzonas bit29; ambos caben en INT. Es almacenamiento interno, no se envía ese tag
  al cliente. Filas antiguas sin tag conservan su lectura anterior, sin migración masiva.
- Guardado, carga y nuevos registros comparten sincronización; se mantiene autosave/logout
  y apagado limpio existentes. No se promete durabilidad ante kill antes de guardar.
- Sin cambios de cliente, esquema SQL, feature bits ni coordenadas del JSON.

Un rollback de binarios conserva las filas nuevas, pero la versión antigua no interpreta
sus tags; restaurar el build nuevo vuelve a interpretarlas. No borrar visitas para hacer rollback.

## Corroboración externa

Fuentes consultadas el 2026-09-04; corroboran comportamiento/identidad, no sustituyen datos r575:

- [The Hereafter's Energy, quest6518](https://archeagecodex.com/us/quest/6518/): el diálogo
  describe registro automático al pasar por Memory Tomes, distinto de registrar casas con Memory Ink.
- [Teleport Book — ArcheAge Wiki](https://archeage.fandom.com/wiki/Teleport_Book): registro de
  lugares visitados. No se importan límites ni costes de otra versión.
- [Hiram Cave Memory Tome13136 — ArcheRage](https://wiki.archerage.to/ru-en/db/maps/zone-107/doodad-13136):
  corroboración de identidad y Western Hiram Mountains obtenida en búsqueda; la reapertura directa
  de la página falló. La identidad exacta está además demostrada por SQLite r575.

## Evidencia reproducible y pruebas

Script: `reconstruccion_cliente_10/scripts/audit_teleport_book.py`.
Salida: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/teleport-book-frontier`.
Incluye catálogo JSON, extracción de áreas/colocaciones de todos los worlds presentes en el
índice, manifest SHA256 por entrada y logs de decompilación. No se modificó `game_pak`.

SHA256 de las bases consultadas:

- Completa: `87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f`.
- Retail: `f61b6b6ed23ad83403d0e45f7d72f7cdf33553bcde03535e800acbb84639165b`.
- Runtime: `85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.

Build Release World/Game correcto. Suite **1780/1780**, cero omitidas: 8 pruebas nuevas
de dominio y una fixture binaria nativa de 12 bytes para distrito473. Incluye separación
de namespaces, mapping de facción/madre, repetición, destino inexistente, recarga de filas y
30 solicitudes concurrentes. La recarga es prueba de dominio, no simula una caída real de servidor.
Persisten advertencias preexistentes, incluida NU1903 de SQLitePCLRaw; no se ocultaron.

## Despliegue y aceptación

Game detenido limpiamente a 01:10:18 UTC, salida0, sin jugadores conectados.
Backup SQL posterior: `E:/AAEmu/rama_10/backups/teleport-book-20260904/aaemu_game.sql`,
SHA256 `5F943843D59FE2748F02BC636D4299B58A037DEF50E1FAB7E805F764E8C84666`.

- Imagen candidata desplegada: `aaemu-world:teleport-book-20260904`,
  `967f4a614fabd00f82dca88002fd65c9d6f627e071bf2fac8ad7acbdef771608`.
- Rollback: `aaemu-world:rollback-pre-teleport-book-20260904`,
  `b8992f44d6b1d3ae26a19aca94a247c9520e7760d884ee3eb489c33d1ab34c35`.
- Inicio Game01:10:35 UTC; mismo networking y mounts. Login/DB no recreados.
- Ambas DLL Game (`/app` y `/app/game`):
  `58844b1ca40e50ebe9d37348ec564d316478ae9688c61cd7f71ff02d67aa957f`.
- Ningún lifecycle de Zone operado por Codex.
- Startup confirmado01:11:50 UTC; catálogo190/192 a01:11:31, healthy, restart0 y API interna
  responde. Advertencias esperadas858/1076, errores preexistentes Smelting29–32 (OFF) y
  una desconexión de Zone durante el arranque; no se operó ese proceso ni hubo bucle de Game.

Aceptación del 2026-09-04 UTC: el usuario levantó la Zone351 y solicitó llevar a Dannia
desde Lacton. El comando GM de movimiento efectuó el handoff142→351 sin conceder visitas
directamente. A01:19:43 se observó `ZWEnterArea unit=1074 area=22 v1=473 v2=0` y
`Teleport-book discovery char=Dannia district=473 returnPoint=933`.

El usuario confirmó visualmente Hiram Cave en Western Hiram Mountains/Auroria (44/160
lugares registrados) y después confirmó el arreglo y solicitó commit/push tras la indicación
de comprobar relog. MySQL confirma la fila persistida id52, owner1007,
subzone1073742297 (=bit30|473). Se cierra el arreglo de registro de Hiram Cave con aceptación
del usuario; no se atribuye una prueba de viaje de retorno ni de los 190 destinos completos.
