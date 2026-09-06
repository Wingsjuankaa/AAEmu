# Una prueba de fuerza9245: conservar el banco como objetivo del área

Target `E:/AAEmu/rama_10/server/AAEmu`, branch `rama_10`, HEADbdad11fec1493c43a854369e707de72a20f26f86.
Padre exacto consultado `upstream/client_version/zone-10.0.2_r575`6273a02f0c88f3c48e52252c3e64ae7e71d63945.
El padre conserva el mismo selector AoE. No se cambia de rama ni integra upstream.
Se preserva el diff previo de Skill.cs y los cambios concurrentes.

## Evidencia

El usuario confirma el éxito de la misión9298 y reporta que9245 no avanza al
interactuar con el banco pese a tener el orbe. API confirma item46658, instancia
16777494, Inventory slot133, cantidad1. Posición persistida de Dannia1007:
Zone354, `(21300.4,30380.4,773.815)`.

Los logs19:40:17–19:41:18 UTC prueban tres casteos completos de skill40467 sobre
los bancos101322 y101320: Started, Fired y InteractionEffect Use; no hay ejecución
de Doodad.Use ni evento de progreso. Objective1105 permanece0/1.

`scripts/audit_strength_9245.py` compara14 consultas exactas full/retail/runtime,
con igualdad de contratos y hashes guardados en
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/strength-9245/native-contracts.json`:

- Item46658 Orb of Strength, use_skill_id0. No habilidad propia de doble clic.
- Quest9245, componente40209, act63224/detail1105: Use19 de doodad13571 una vez.
- Doodad13571, fase39797, func37422 -> FakeUse3712, skill40467 -> fase39798.
- Skill40467: casteo5000ms, target_type8 Doodad, selection2 Target, radio20.
- Effect73895 -> InteractionEffect7544/Use19, application_method1 Target.
- UnitReq62187 exige misión9245 activa. La habilidad no tiene skill_reagents ni
  consumo de item en su efecto; no se inventa consumo del orbe.
- Modelo fase39797 `hirama_east.weapon_on`; fase39798 `hirama_weapon_factory_a_off`.

## Causa y arreglo

WorldManager.GetAround pasa el ObjId del centro como exclusión al índice regional.
ApplyEffects sólo reinsertaba el centro cuando selection=Source. Con selection=Target
el banco seleccionado desaparecía de la lista; el efecto Use llegaba a vecinos
no doodad y terminaba sin interacción ni progreso.

Se conserva el centro también cuando selection=Target, target_type=Doodad y el
objeto es Doodad. Sigue pasando por el filtro existente de relación, deduplicación,
límite de objetivos y selección de destino por efecto. No cambia el radio, los
requisitos de misión, la lógica de fases, los objetos ni el consumidor de progreso.
AA8 añade siempre el centro; se usa como comparador de primitiva compartida,
portando únicamente el caso Doodad confirmado por AA10. Clase `server-required`.

## Gates

Restore correcto, build Release0 errores.1821/1821 tests correctos. Cuatro pruebas
nuevas atraviesan ApplyEffects con destino y descriptor capturados: banco seleccionado
recibe una sola aplicación; single-target y Source conservados; Location y tipos
ajenos no reciben un centro nuevo; SourceOnce sigue dirigido al caster.
No hay edición de SQLite ni game_pak y el proceso de traducción queda separado.

Rollback de imagen: `aaemu-world:rollback-pre-strength-9245-20260906`,
SHA01939c55b6af6f64761fc5673078ef7413c78dd7d3fbc8cab8f6a8d73dde807d.
Para revertir sólo código, etiquetar como `aaemu-world:10.0.2.13-r575-local` y recrear
sólo Game sin build. No hay catálogo nuevo que revertir. Evidencias de build,
tests, DB backup y runtime acompañan el manifest de esta frontera.

Imagen Release desplegada:
`42068216132721de2e0843ac68820dd8a14fa47aa6ca7cf19bce99151e05cec6`.
Respaldo MySQL después de detener Game:
`E:/AAEmu/rama_10/backups/strength-9245-20260906/aaemu_game.sql`, SHA256
`6b92f583de32ce8dc2da4a32180d5102229866afe5c54c5d57b19edd0f848430`.
DLLs `/app/AAEmu.Game.dll` y `/app/game/AAEmu.Game.dll` coinciden en
`b8b5d31fa699e2320e99a9d88950c3347146f33a2b3c460d8f5b4d25cbcfb14d`.
Compact montada conserva hash previo
`85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
Gate runtime19:52:30 UTC: `Server started`80.100s, registro Login correcto,
puertos1239/1250 y World1240 activos. API responde, healthy/0 reinicios;
snapshot19:53:26 muestra0 jugadores/0 Zones. DB/Login conservados.

Aceptación pendiente: usuario relanza Zone354 desde Control Center, entra con
Dannia y pulsa F una vez sobre un Banco de trabajo de armas de haradio. Esperado:
casteo5s, banco pasa a fase39798 y objetivo1/1. Mantener la misma misión/orbe;
no abandonar ni otorgar progreso mediante DB. No se inicia/detiene ninguna Zone.
