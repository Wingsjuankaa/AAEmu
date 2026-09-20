# Battlerage: Delirio, Frenesí Oleaje, pasivas y Tigre Rayo

**Continuación:** la espera duplicada de Tigre se corrigió posteriormente en
[TIGER_TIMING_20260920.md](TIGER_TIMING_20260920.md). Este informe conserva el
diagnóstico y descarte del primer candidato; sus pendientes de pasivas/C siguen vigentes.

Fecha: 2026-09-20. Target `rama_10`, base `bde9370739b10e5f444467ce29420dff43ce9b80`.
Padre contrastado: `upstream/client_version/zone-10.0.2_r575`,
`7851f67cc0c46fb76b4fafc3414b6754685d96f2`. Sin integración nueva del padre.
El usuario conserva las pruebas del cliente y el lifecycle de Zones.
La corrección del usuario confirma **6 %**, no 8 %, en Duelista letal.

## Resultado y límites

**Corregida la aplicación de atributos de CombatResource**, incluyendo Delirio.
Las acumulaciones existían, pero ningún loader consumía las filas
`unit_modifiers.owner_type = CombatResource`. `Unit.GetBonuses` tampoco las
incluía. La acumulación no podía aumentar el daño crítico ni la velocidad del
servidor. Clasificación: **server-required**; valores definidos por AA10.

Se cargan las once filas habilitadas de los recursos 1/7/11/17/26/27 y se evalúan
según los puntos actuales. No se introduce un buff de AA8, paquete adicional,
temporizador, cambio del cliente ni persistencia nueva. Ganar/gastar/perder el
recurso afecta el cálculo siguiente; no se mantiene una segunda copia del bonus.

**No se declara corregido Tigre Rayo, el parry a distancia ni el refresco de C.**
El candidato de tiempos se retiró antes del build final: adelantaba también el
primer daño sin cerrar su sincronización nativa. La suite verde de ese candidato
no constituye evidencia de que la transición fuera correcta. No se alteró el
baseline de cadenas/GCD `f8af778cf` aceptado por el usuario.

## Evidencia AA10

Auditoría reproducible, sólo lectura:

```powershell
C:\Python313\python.exe reconstruccion_cliente_10/battlerage/audit_tiger_passives.py `
  --full E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3 `
  --runtime .server_files/AAEmu.Game/Data/compact.sqlite3 `
  --output E:\AAEmu\rama_10\artifacts\battlerage-tiger-passives-20260920\audit.json
```

Las catorce selecciones son idénticas entre full y runtime: 128 registros,
incluyendo 19 edges, 34 efectos y las seis pasivas. Esto prueba igualdad de esos
datos; no prueba la implementación ni el funcionamiento completo en cliente.

| Fuente | SHA-256 |
|---|---|
| Full AA10 | `87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f` |
| Compact runtime | `85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65` |
| Cliente release original, referencia de Ghidra x64 | `2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76` |
| Zone dedicate x64, referencia de Ghidra | `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a` |
| Entrada efectiva `game/combat_sync_event_list.g` | `9467bfbc2dc0d18af45fe33c891f691685238af18a506859f618bf0100a301f4` |

Ghidra usa image base `0x39000000`; direcciones siguientes expresadas como RVA.
Exportaciones y captura de logs en
`E:\AAEmu\rama_10\artifacts\battlerage-tiger-passives-20260920`.
El script `scripts/ghidra/FindBattlerageFlow.java` indexa símbolos/referencias
en modo sólo lectura; no modifica el binario.

## Delirio: cadena y valores

Pasiva29 → buff811 → combat_buff51 (máscara101, skill tag4749) → buff22277
(1000 ms, inmunidad a su tag3714) → Started14546 → efecto87395 →
CombatResourceEffect494 → recurso1. AA10 no usa el buff11344 de AA8.

Recurso1: máximo5, recovery_cycle9000 ms, recuperación -6; buff_id0.
Modificadores80244/80245: atributos17/218, linear_level_bonus5000/3000.
Cada punto produce **+5 puntos porcentuales de daño crítico cuerpo a cuerpo y
+30 de velocidad de ataque**; cinco puntos producen +25/+150. Los valores se
convierten con la misma escala centesimal de los modificadores existentes.
Los logs anteriores registran incrementos reales del recurso en Dannia.

Pruebas cubren lectura de filas habilitadas, descarte de otro owner/recurso
desconocido, ganancia, límite5, gasto, retirada hasta cero y aislamiento por unidad.
No se afirma haber probado visualmente la barra/icono ni C después del despliegue.

## Frenesí Oleaje y seis pasivas

Frenesí43189 → buff25650; Damaged13086 → BuffEffect32318 → buff25987.
Su modificador63237 aporta40000 unidades internas: **+40 de ataque por daño
recibido**, no por activar Frenesí. Stack múltiple hasta10. La prueba activa el
trigger real y verifica +40 por evento, límite +400 y retirada. No se modificó
esa cadena porque ya funciona en la prueba de servidor. Queda pendiente verificar
que el daño de la sesión real alcanza ese trigger y que C refleja la acumulación.

| Pasiva / buff | Auditoría y validación | Frontera pendiente |
|---|---|---|
| Parar y contraatacar /2610 | CombatBuff23 acepta MeleeParry/RangedParry; aplica2611; timeout100 ms dispara ResetCooldown4636/tag415. Dos pruebas recorren dispatcher, buff, tarea y reset real: resetean ataque, conservan Frenesí; dodge no activa. | Producción del parry real y supresión nativa de12 s. |
| Carga temeraria /7542 | Tag1476 habilita7543; atributos143/145=-150 durante4 s. | Aceptación de los desplazamientos, aplicación y retirada en combate. |
| Penetración física /2621 | CombatBuff24 crítico melee →2622 → timeout1390 → SkillUse4670 →16185. | Destinatario y supresión. No cerrar por mera presencia de datos. |
| Entrenamiento de velocidad /811 | Recurso1 ahora aporta sus atributos; pruebas de cálculo y limpieza. | Aceptación visual, cadencia real y duración con golpes. |
| Maestría de armas /831 | SkillModifier1842, tag415, Damage/Percent10. | Comparación de daño con/sin pasiva y control fuera del tag. |
| Duelista letal /7544 | UnitModifier56117, atributo77, valor60 = +6 puntos de crítico. Prueba de PassiveBuff.Apply y retirada; no hay gate de equipo en este modifier. | Cláusula separada del parry ranged con dual/2H y visualización en C. |

Defecto sospechoso, **sin parche especulativo**: `Skill.RollCombatDice` consulta
4899+831 para el parry ranged procedente del melee rate, excluye2H y devuelve
MeleeParry. AA10 tiene const_tag `ranged_parry`/4270 con equipos4899/8227.
Eso no prueba por sí solo si el consumidor debe exigir7544; no se sustituyó el
ID a ciegas. `SpecialEffects.CombatDice` y el nuevo sorteo de
`ConditionCombatDiceResult` siguen siendo fronteras transversales anteriores.

Cliente release: SCBuffLearned, RVA33D520 →6BEC10 →BD78F0, registra la pasiva;
BD6FF0 reconstruye sus buffs/tags y BCBBF0 invalida los290 atributos. Existe
una vía nativa de refresco: no se añadieron paquetes de buffs por tanteo para C.
Esto no demuestra que el cliente de la sesión haya recibido cada evento.

## Tigre Rayo: diagnóstico conservado, arreglo pendiente

Skill36448/plot2922, tres controllers Leap11024/11025/11026. Los descriptores
declaran duraciones400/300/300 ms; los edges hacia status/daño declaran400/300 ms,
`use_exe_time=false`. El servidor suma además la duración del controller sin
consultar ese flag. Esto explica una espera adicional en el código actual,
pero falta cerrar cómo el scheduler nativo combina ejecución y sincronización.

Zone dedicate: RVA26EDA0 carga el descriptor de Leap; RVA231780/231AB0 preparan
target/posición; RVA241890 usa inicio+duración en su tick. Zone ya posee el
movimiento del jugador. No se activó un segundo controlador de movimiento C#.

Un candidato condicionaba la suma a UseExeTime. Cuatro pruebas pasaban, pero
la arista32042 hacia el primer daño tiene delay0/AddAnimCsTime: su evento incluye
Anim46 `all_co_sk_stop`, ausente de `combat_sync_event_list.g`. El controller
usa StartAnim175 `all_co_sk_dashattack_2`. El loader actual sólo toma la sync
de SpecialType.Anim y del modelo nuian_male; no está demostrada la selección
nativa correcta aquí. El candidato habría adelantado el primer daño de unos
401 ms a1 ms. **No desplegado ni integrado**; patch y fixture conservados fuera
de Git como diagnóstico, no como implementación válida.

Siguiente frontera concreta: seguir el consumidor nativo de sincronización
controller/animación y `use_exe_time`, correlacionar WZPlotEvent/daño con la
presentación del cliente; sólo entonces cambiar la espera. No usar repeatTick300
ni el texto del tooltip como sustituto de ese contrato.

## Validación y entrega

- Restore y build Release: correctos; build sin errores,382 advertencias.
- Suite final: **5529/5529**,0 fallos,0 omitidos. Baseline5522 +7 pruebas nuevas.
- Antes del cambio, dos pruebas de atributos del recurso fallaban; después pasan.
- La suite5533 pertenece al candidato de Tigre retirado y no es la entrega final.
- No se operó el cliente ni las Zones; no hubo aceptación jugable en esta sesión.
- Sin cambios en SQLite, game_pak, configuración de red o datos de personajes.
- Rollback de imagen: `aaemu-world:rollback-before-delirium-20260920`,
  imagen `d83469725007e3b9f15b61c3adc8604d6ba10e6c974008c0841ba786611e0c24`.
- Imagen nueva: `4d607c6cd3bcf692ab046de139f729988b299ae665d744173391810154217067`.
- Desplegada a las20:56:44 UTC; Game/Stream listos y TCP1239/1240/1250
  accesibles a las20:58 UTC. Contenedor healthy,0 reinicios. Las copias de
  `/app/AAEmu.Game.dll` y `/app/game/AAEmu.Game.dll` coinciden:
  `012f976bf5b2db9517cbe59b3813e877e892c17632dad7f6ed3aec6cd41b4cb2`.
  Compact montada conserva el SHA indicado. No hubo cambios en Login/DB.
- Arranque conserva avisos previos de experiencia y definiciones smelting29–32
  fuera de alcance. La desconexión Zone durante el reinicio se registra sin
  operar su lifecycle; no se declara sesión jugable validada por el healthcheck.

Para aceptación del cambio confirmado: relanzar Zones/relog tras el reinicio de
Game, golpear con Battlerage y comprobar los aumentos de Delirio hasta5 y su
retirada tras9 s sin renovar. Registrar C antes/después. No presentar este ensayo
como aceptación de Tigre, parry o todas las pasivas.

Rollback local:

```powershell
docker tag aaemu-world:rollback-before-delirium-20260920 aaemu-world:10.0.2.13-r575-local
docker compose -p aaemu10 -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml up -d --no-deps --no-build game
```
