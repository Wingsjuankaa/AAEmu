# Quest 9989 — Enos el Oráculo: combustible y convergencia

## Estado
Corrección server-required en rama_10; aceptación dentro del juego pendiente tras desplegar.
Padre comparado: upstream/client_version/zone-10.0.2_r575 (7babcb3a706c64295b5aaaeec8abe57e4d09b4da).
HEAD previo: fd53b458573572cc354c8564293f274801d9aa3e. Se preservan cambios pendientes de quest9565.

## Contrato y diagnóstico
SQLite completa y compact montada coinciden en todas las filas de la clausura consultada.
Fuente: E:/AAEmu/rama_10/data/sqlite/authoritative/game_decrypted.sqlite3.
Evidencia: E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/quest9989-braziers/native-contract.json.
- 26080 y 26088: Multiple (4), 20.000 ms, máximo cinco cargas; transforman en 26081 y 26089.
- 26081 y 26089: duran 8.000 ms. Sus breakers 3797/3798 requieren respectivamente tags 4616/4615 del otro brasero.
- Triggers 13276/13277, evento breaker (31), efectos 82584/82585 → BuffEffect 32565/32566 → buff26091.
- 26091: 3.000 ms. Started elimina ambos estados listos mediante efectos82587/82588; Timeout13280 ejecuta82603 → SpecialEffect47882, SkillUse33, skill43718.
- Skill43718 aplica efecto82602 (BubbleEffect6564), observado por QuestActObjEffectFire166 del componente43527. Skill.ApplyEffects ya publica EffectFire.
- Sphere3013 → SphereQuest1744 → quest9989, objetivo861; timer256 dura90.000 ms.
- Buff26083 es el bloqueo independiente de calor de3.000 ms: no se altera.

El servidor colapsa Multiple en una instancia con contador. TryGrowStack devolvía antes de refrescar su duración; en el techo OverwriteWith además podía sustituir el contador por1. El padre exacto conserva ese defecto. AA8 usa instancias independientes y no se porta ese modelo.
No existían loader de buff_breakers ni evento31: completar los dos estados no ejecutaba la convergencia. La carga nueva se limita a filas con trigger breaker habilitado (26081,26089,32138 en r575); no activa el resto de las 2478 filas como dispel genérico.

## Implementación
- Multiple temporales administrados por World renuevan la duración efectiva al apilar, conservando índice y contador; un único update publica el nuevo estado. Permanentes y mirrors de Zone conservan su camino anterior.
- La transformación al techo sigue usando el catálogo. No hay IDs de quest/buff codificados en producción.
- DispelTask comprueba el plazo vigente para impedir que una tarea ya despachada expire una renovación. Si aún falta tiempo, vuelve a programarse; los buffs con tick conservan su cadencia.
- Los breakers se evalúan después de crear/transformar sobre snapshot, en ambos órdenes. Cada instancia dispara una vez; callbacks pueden retirar ambas instancias sin invalidar enumeraciones. Excluye expirados y autoridad Zone.
- Cadena SkillUse/EffectFire existente se conserva; no se fuerza la quest ni se cambian materiales, balance, SQLite o game_pak.

## Validación y entrega
Pruebas focales: renovación2→4, índice estable, antiguo vencimiento, transformación5→listo en ambos braseros, techo sin perder cargas, permanentes, convergencia en ambos órdenes, Timeout único, peer expirado y autoridad Zone. Suite Release final: 2694 pruebas correctas, cero fallos.
No se automatizó el cliente ni se afirma todavía que Dannia haya completado9989.
Respaldo DB: E:/AAEmu/rama_10/backups/quest9989-braziers-20260907/aaemu_game.sql (CEBFE23952FE9BFAC5AECD14B155D904191D5415C326EDD298EC82504627EB3C).
Rollback imagen: aaemu-world:rollback-pre-quest9989-braziers-20260907 → sha256:94ba0d7a521bd34baf6a08b3d31c63ccf314eaefc1a354880e2858e46bb25876.
Despliegue sólo Game; no se administra lifecycle Zone. Dannia requiere perfil354 después de reconectar.

Game desplegado y listo el 2026-09-08 00:26:51 UTC. Imagen ecfbb606ab845ec66384154cbd8da7501b73d40c06c2ef8a65621f2135fbe909; ambos ensamblados Game tienen SHA-256 5ea7c380bbfeff4e6b5f6efe2c2a18a54de4d3b4d85bfeb1bd04b4b5a8cefcf1. Se verificaron listeners 1239/1240/1250, conexión Login y Web API interno1280. Aceptación retail pendiente: renovar combustible debe devolver el contador a20 s; llevar ambos a cinco cargas dentro de la ventana de8 s de los estados listos. No hubo cambios a ZoneHost ni game_pak.

Aceptación del usuario confirmada: completó los braseros y avanzó hasta la puerta de Garden.
