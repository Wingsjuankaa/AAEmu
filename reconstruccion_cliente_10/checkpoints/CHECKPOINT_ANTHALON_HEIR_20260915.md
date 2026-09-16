# Anthalon: nivel ancestral y umbral de huida

Target `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`, HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`. Padre exacto `upstream/client_version/zone-10.0.2_r575`, ref observado al desplegar `d892934591b7a52ee082a5f9a23b277d074d043d`. Conserva el hardcode heir_level=0 para NPCs. Comparación AA8 no aporta una carga ancestral aplicable. Sin merge/commit/push; conservar cambios de otras tareas.

## Evidencia

Usuario confirma que la corrección anterior del lifecycle permite castear, pero quest10101 sigue sin avanzar al50%. `E:/AAEmu/rama_10/artifacts/anthalon-escape/before.log`: Anthalon20019/1047 usa43979,43956 y44313; entre00:38:34 y00:39:46 Game rechaza43979 por UrkTargetHealthMoreThan mientras Zone sigue solicitándola. No44012 ni26463; muerte por daño00:39:54. Es evidencia de selección/validación discordante, no una captura directa del HP interno de Zone.

SQLite completa y compact efectiva tienen el mismo SHA256 `87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f`. NPC20019 tiene level55, heir_level28, template9, kind3, grade3. Las fórmulas nativas dependen de heir_level, incluyendo un cambio de rama al26. El loader/template/spawn ignoraban ese campo y19 evaluaciones NPC forzaban0.

Reproducción con filas nativas, sin buffs/equipo: heir0 produce Sta230, MaxHP1102274 y MaxMP88250; heir28 produce Sta342, MaxHP5555753 y MaxMP130250. Una vida máxima incorrecta cambia el porcentaje que evalúa Game y los puntos/levels publicados. El desajuste es probado; que sea el último bloqueo de la huida requiere aceptación en juego. No se presenta como medición directa del maxHP interno de Zone.

## Corrección

Cargar npcs.heir_level en NpcTemplate, asignarlo en NpcManager.Create antes de inicializar buffs/equipo/puntos, y usar Unit.HeirLevel en las19 fórmulas NPC. El serializador existente ya publica el par nivel/ancestral; no se cambian anchos, opcodes ni estructura. Los NPC con ancestral0 conservan sus cálculos. Los1352 templates con ancestral positivo recuperan sus estadísticas nativas; no hay excepción por Anthalon.

No se fuerza skill44012, buff26463, daño, HP ni crédito de misión. El comportamiento esperado sigue siendo huida44012 con HP1..50%, casteo6s y buff26463 que habilita el objetivo de área. No modifica SQLite, compact, game_pak ni progreso de Dannia.

## Validación y entrega

Build Release y2859/2859 pruebas correctas. Seis casos nuevos usan un extracto nativo embebido: creación completa con ancestral0/28 y HP/MP iniciales, validación del requisito69579 al51/50/49/0%. Fixture confrontado fila por fila con compact efectiva. Los valores esperados proceden de las fórmulas r575; no se sustituye el comportamiento de quest en pruebas.

Game desplegado con imagen192c3b4198dc y rollback `aaemu-world:rollback-anthalon-heir-20260915` (c5b8504e..., imagen que realmente estaba ejecutándose antes de este despliegue). Sólo lifecycle de Game; Zones bajo control del usuario. Manifest y artefactos en `E:/AAEmu/rama_10/artifacts/anthalon-escape`.

Aceptación pendiente: restaurar Zones desde Control Center si corresponde, entrar con Dannia y combatir Anthalon recién creado. Bajar de50%, detener ataques y dejar terminar la huida durante al menos6s. Verificar solicitud44012, buff26463 y progreso10101. Si persiste, capturar HP interno de Zone y comparar selección de skill antes de ampliar cambios. No usar /die para probar la fase.

Arranque confirmado: GameService y WebApi listos01:05:12Z del16/09/2026; contenedor healthy, cero reinicios. API responde,19522 templates cargados, cero Zones registradas tras recrear Game. Los mensajes de navegación posteriores corresponden a carga de fondo.
