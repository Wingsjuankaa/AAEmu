# Checkpoint — Teleport Book / Hiram Cave

Estado: reparación desplegada y aceptada por el usuario; registro de Hiram Cave confirmado.

- Dossier: [AA10TeleportBookReconstruction_es.md](../../Docs/AA10TeleportBookReconstruction_es.md).
- Catálogo: [AA10TeleportBookCatalog_es.md](../../Docs/AA10TeleportBookCatalog_es.md).
- Branchrama_10; partidaac4f3ecb2; padre r5753cc280b14.
- Catálogo idéntico full/retail/runtime:192returnpoints,187districts,1452relations;
  185 colocaciones nativas,5JSONhistóricas,2no colocadas (858/1076).
- Causa: Group22/value1 de ZWEnterArea no llegaba al libro. Distritos y subzonas
  compartían equivocadamente el diccionario. Hiram933/distrito473/Zone351 sí existía.
- Contrato decompilado en Zone r575 de igual hash; sin alterar cliente o Zone.
- Nuevos tags internos bit30distrito/bit29subzona, compatibles con INT firmado.
  Visitas históricas preservadas; sin migración de esquema ni concesión masiva de destinos.
- Build Release y1780/1780pruebas. Fixturewire12bytes, recarga, facciones y concurrencia.
- Game imagen967f4a614fabd00f82dca88002fd65c9d6f627e071bf2fac8ad7acbdef771608.
- DLLGame58844b1ca40e50ebe9d37348ec564d316478ae9688c61cd7f71ff02d67aa957f, ambas copias.
- Rollbackb8992f44d6b1d3ae26a19aca94a247c9520e7760d884ee3eb489c33d1ab34c35.
- BackupSQL213462bytes, SHA2565F943843D59FE2748F02BC636D4299B58A037DEF50E1FAB7E805F764E8C84666.
- Apagado limpio01:10:18UTC, recreaciónGame01:10:35, Server started01:11:50,
  healthy/restart0. Login/DB y networking preservados. Zones bajo control del usuario.

Aceptación: traslado GM solicitado por el usuario desde Lacton a Hiram Cave, sin conceder
visitas. A01:19:43UTC, ZWEnterArea group22/value1473 y registro distrito473/returnpoint933.
El usuario muestra Hiram Cave en el libro y confirma el arreglo tras solicitarle comprobar
relog; autoriza commit/push. MySQL: id52/subzone1073742297/owner1007, visita persistida.
No se declara probado el viaje de retorno ni todo el catálogo;858/1076 siguen pendientes.
