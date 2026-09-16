# Nuia: reparación de misiones amarillas — 2026-09-15

## Entrega

Implementación, pruebas y despliegue local de Game/World realizados. Aceptación
jugable pendiente: no se declara que las 1.184 misiones regionales estén completas
ni que el síntoma del caballo/bote haya sido reproducido y resuelto en cliente.

Informe: `Docs/AA10NuiaYellowQuestRepair_es.md`.
Manifest: `NUIA_SIDEQUESTS_REPAIR_20260915.manifest.json`.
Evidencia: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/nuia-sidequests-repair-20260915`.

## Reparaciones

1. Overlay con 581 posiciones de 91 plantillas relacionadas con 87 misiones
   regionales en 22 zonas de Nuia. Sector nativo verificado contra world.xml.
   Se conservan las coordenadas, rotación, escala y fase inicial de r575.
2. Cinco barcas 2853 de la misión 2393 reemplazan su grupo heredado mediante una
   regla espacial acotada. No hay plantables añadidos como objetos fijos.
3. `DoodadFuncSpawn` carga los descriptores r575 y publica NPC a través de la ruta
   existente de Zone. Incluye los usados por 1402/1474/2071. Rechaza modos sin
   contrato cerrado; una publicación fallida no avanza fase ni progreso.
4. La colocación consume solo la instancia de item seleccionada y valida el
   resultado antes de notificar `ItemUse`. No consume variantes alternativas ni
   admite un item protegido, incompatible o ya agotado. Cubre el mecanismo usado
   por semilla 23635 y potros 23680/23681/23682.

## Gates y runtime

- Restore correcto; Release 0 errores; última compilación incremental 163 advertencias.
- 2.853 tests correctos, 0 fallidos/omitidos; 13 casos nuevos de esta reparación.
- Generación repetible; comparación del catálogo efectivo fuente/runtime sin
  duplicados para las 581 posiciones y con cinco barcas.
- Imagen desplegada: `sha256:c5b8504e52752800faa14bac053a9e87ecc6bd319d3f0a14e558016e72026a35`.
- SHA256 de las dos copias runtime de AAEmu.Game.dll:
  `57eca9c3940271787e139aba75cc18c42ad247b59adba9d207cf496eeb3788d1`.
- Overlay runtime: `3c46c4fc882315f5815a28a0826902a0cf3a17ee5d2b5a2fa6c1fba4a707de2c`.
- Sustituciones runtime: `c6a8d38a5978045bba25fd6dddf53daf95d8e3b3967057e2ecf23a49a0617e7e`.
- Contenedor inició 2026-09-16 00:03:21 UTC (15 de septiembre local).
  Servidor listo a las 00:05:02 UTC; healthy, sin reinicios/OOM observados.
- Gate de quests Strict: 43.696 actos, 0 hallazgos. Login registrado;
  sockets Game1239/World1240/Stream1250 en escucha.
- main_world: 46.637 doodads cargados; 4.422 entradas heredadas suprimidas por
  las reglas combinadas (incluye Halcyona; solo cuatro son las barcas antiguas).
- Permanecen cuatro errores de definiciones de Item Smelting 29–32, ajenos a
  esta tarea y excluidos por alcance. No se presenta el startup como libre de
  todo error. Hay avisos de contenido sin ZoneLoaded porque no se operaron Zones.

## Respaldo y contexto compartido

HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`, rama `rama_10`.
Padre consultado `upstream/client_version/zone-10.0.2_r575`:
`d892934591b7a52ee082a5f9a23b277d074d043d`. No se integró.

Había 91 archivos modificados/no rastreados registrados al inicio. No se
revirtieron cambios ajenos. `Skill.cs` cambió concurrentemente a las 23:41:43 UTC,
antes de la compilación/pruebas y del build Docker; se preservó. Los otros dos
cambios respecto al inventario son enlaces añadidos a los informes de Nuia.

Rollback de imagen: `aaemu-world:rollback-nuia-sidequests-20260915`,
`sha256:85c064a7e4a57ebffa469e951eee19d1621dd0c93452b3a99ba7f5e35523dc3d`.
Archivos anteriores y script con comprobaciones de imagen/hashes en
`rollback/Restore-Game.ps1`. No se modificó compact, bases ni cliente; no requieren
restauración. El rollback recrea exclusivamente Game y no opera ZoneHost.

## Frontera pendiente

- Aceptación 2393 y 4292→4294→4295, sus tres monturas, recompensa única y relog.
- Invocaciones 1402/1474/2071 con Zone activa y comportamiento completo.
- `FxGroupCallback`, `HideMapIcon`, interfaces de construcción/residencia y las
  fuentes de objetos aún no demostradas en la auditoría anterior.
- Semántica/cierre contra DLL actual del campo final i16 de `CSCreateDoodad`,
  observado en Ghidra pero no modificado ni atribuido como causa del síntoma.

La autorización de esta tarea permitió desplegar Game; no se inició, detuvo ni
relanzó ningún perfil de ZoneHost. Las pruebas jugables se mantienen pendientes.
