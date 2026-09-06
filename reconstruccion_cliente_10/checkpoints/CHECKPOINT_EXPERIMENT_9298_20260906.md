# Un experimento 9298: usar el espécimen desde el borde de la fuente

Target `E:/AAEmu/rama_10/server/AAEmu`, branch `rama_10`, HEAD
`bdad11fec1493c43a854369e707de72a20f26f86`. Padre exacto consultado mediante
fetch: `upstream/client_version/zone-10.0.2_r575`, `6273a02f0`.
No se integra ni cambia de rama. El padre no modifica SphereGameData ni
SphereQuestManager desde el baseline3cc280b14. Se preservan cambios concurrentes.

## Evidencia

El usuario no puede llegar a la posición elevada del marcador por la colisión
de la fuente. `/fly` permite acercarse, pero impide usar el objeto durante vuelo.
No se ha inspeccionado/reparado la colisión ni atribuido su causa a un modelo.

Full, compact retail y compact servidor coinciden en las consultas de
`scripts/audit_experiment_9298.py`. Resultado completo y hashes en
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/experiment-9298/native-contracts.json`.

- Item46685 -> skill40653 (casteo2s, self, sin efectos adicionales).
- UnitReq62055: kind32, misión9298 activa. UnitReq62105: kind35, esfera2836.
- Componente40452/act62927/detail964: usar item46685 una vez.
- Sphere2836 -> SphereQuest1637 -> evento de misión9242.
- Zone354, `quest_area_sphere.g`, stype2836: centro local
  `(1594.94,2329.86,875.591)`, radio12m.
- `quest_sign_sphere.g`, qtype9298/ctype40452: marcador local
  `(1596,2327.37,880.163)`, radio8m, elevado4.572m frente al centro nativo.
- Logs previos prueban ENTER2836 para Dannia en Zone354. Posición persistida
  observada `(21055.5,31002.4,877.233)`; dentro del radio nativo.

Las dos entradas geométricas se extrajeron read-only de la referencia original.
No se abre/escribe el game_pak del cliente español ocupado por traducción.
No se cambia SQLite, cliente, geometría ni ciclo de vida de Zones.

## Causa y corrección

`IsInsideAreaSphere` resolvía el evento de sphere2836 a los marcadores de9242,
y `CanUseSkill` exigía el componente40452 de9298. Ningún marcador podía cumplir
ambas condiciones. Aumentar solamente el radio de un marcador no arregla ese
rechazo del servidor.

La validación resuelve ahora el volumen nativo por `spheres.id`/`stype` y mundo.
Usa el radio12 y centro nativos, sin filtrar por componente de una misión que
comparte el mismo espacio. Si hay geometría nativa, salir de ella rechaza el uso
sin probar marcadores alternativos. Si falta geometría, se mantiene el fallback
legacy y su filtro de componente, ahora limitado al mundo del personaje.
Los requisitos de misión activa, inventario, consumo y progreso no se omiten.

Es una corrección del resolvedor compartido de AreaSphere, no un radio global
ni una excepción codificada por quest/skill ID. Las demás áreas conservan sus
datos nativos. AA8 se inspeccionó como comparador estructural; su catálogo no
contiene este método y no se porta ningún contrato desde esa versión.

## Verificación y despliegue

Restore correcto, build Release0 errores/174 advertencias.1817/1817 pruebas
unitarias correctas, incluidas5 regresiones nuevas: esfera compartida por
misiones, borde12m y rechazo exterior/vertical, marcador del NPC fuera del área,
otro mundo/ID desconocido y fallback legacy con componente conservado.
El audit compara full/retail/runtime sin modificaciones y `git diff --check` pasa.

Imagen Release construida y desplegada recreando sólo Game:
`01939c55b6af6f64761fc5673078ef7413c78dd7d3fbc8cab8f6a8d73dde807d`.
Rollback: `aaemu-world:rollback-pre-experiment-9298-20260906`, imagen anterior
`8c01ea32394cdcb4e0a65ce17f0a9b1b266360c832e9fe8e07afd5ce5fb29fb7`.
Para revertir código, etiquetar esa imagen como `aaemu-world:10.0.2.13-r575-local`
y recrear únicamente Game sin build. No hay datos de contenido nuevos que revertir.

Respaldo después de detener Game:
`E:/AAEmu/rama_10/backups/experiment-9298-20260906/aaemu_game-stopped.sql`, SHA256
`9e399b961437f06b2642253cf79338eebe8360c87dd08aa011daaf05368d978a`.
También se conserva respaldo previo con Game activo; no restaurarlos sobre
progreso posterior sin analizarlo. DB/Login no se recrean.

Gate runtime: `Server started`19:33:16 UTC,80.411s; registro Login correcto,
puertos1239/1250 y World1240 escuchando, API responde, Game healthy/0 reinicios.
Cargó2632 áreas de103 Zones. DLLs `/app` y `/app/game` coinciden en SHA256
`250de0f443a46cc7d35633567b62cea2889147f664160ad073e515f29252e1e4`.
Compact montada conserva SHA256 anterior
`85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
Snapshot final:0 jugadores/0 Zones; no se opera ninguna Zone desde esta tarea.

Aceptación retail pendiente: usuario relanza Zone354 desde Control Center,
entra con Dannia, desactiva vuelo y usa una vez el espécimen de pie en el borde
accesible. Esperado: casteo2s y objetivo1/1. Si el cliente rechaza antes de emitir
CSUseSkill, capturar el intento: este despliegue sólo corrige el servidor y no
se declara resuelta una comprobación local del cliente sin aceptación.

Aceptado por el usuario el2026-09-06: pudo avanzar. Logs19:38:03/19:38:05 UTC
confirman skill40653 y objetivo item46685 en1/1, seguido del reporte al doodad13567.
