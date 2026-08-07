# Protocolo vivo Sorcery -> Archery V1

Fecha: 2026-08-07

## Objetivo y disciplina

Este protocolo convierte la prueba visual del cliente en evidencia
reproducible. Se ejecuta **una sola interaccion por vez**. Despues de cada
interaccion se detiene la prueba, se inspeccionan logs y se registra el
resultado antes de continuar.

Prefijos autoritativos:

- `[AA8SorceryLive]`: ciclo de vida Sorcery;
- `[AA8ArcheryLive]`: ciclo de vida Archery;
- `[AA8SkillDamage]`: efecto de dano y mutacion de HP;
- `[AA8SkillCastRelease]`: porcentaje efectivo al liberar una carga.
- `[AA8ArcheryPassive]`: snapshot servidor antes/despues de una pasiva.

Comando de lectura, ejecutado desde `D:\Proyectos\AAemu\rama_8`:

```powershell
docker compose -f docker-compose.yaml logs --no-color --since 5m game |
  Select-String 'AA8SorceryLive|AA8ArcheryLive|AA8ArcheryPassive|AA8SkillDamage|AA8SkillCastRelease|ERROR|Exception'
```

Resumen JSON/CSV reproducible del mismo intervalo:

```powershell
docker compose -f docker-compose.yaml logs --no-color --since 5m game |
  python reconstruccion_skills_8/summarize_native_skill_live_trace_v1.py `
    --output-json runtime-captures/native-skill-live-summary-v1.json `
    --output-csv runtime-captures/native-skill-live-summary-v1.csv
```

El resumidor agrupa por arbol, skill, `tlId` y caster. Su veredicto
`damage_and_lifecycle_confirmed` exige al menos un dano positivo, reduccion de
HP y fin normal; tambien cuenta lineas de error y arranques del servidor. Sus
regresiones sinteticas pasan 4/4. Ademas agrupa snapshots de pasivas por
personaje/passive/buff y calcula las estadisticas que cambiaron entre cada par
before/after.

Baseline actual previo a las pruebas:
`runtime-captures/native-skill-live-baseline-v5.json`, SHA-256
`31E0D50D31EB7D2A3C1B929028942D7B8697715FE107F9268B8E7D8E941C36C2`.
Contiene un arranque, cero ejecuciones, cero snapshots pasivos y cero errores;
toda traza de skill o pasiva posterior pertenece a la sesion de aceptacion.
El runtime montado es Archery V4, SHA-256
`A8D209F3B30B3DB8DE2B3B0C19B578A6760D68FF2D082B9AC7F5B70616DFFB22`.

V24 propaga la skill originaria por el camino real
`InteractionEffect -> SummonDoodad -> Doodad -> DoodadFuncClout -> AreaTrigger`
cuando `use_origin_source=1`. Asi los buffs y ticks periodicos de Flame
Barrier se atribuyen a la skill interna 41478 sin heuristicas observacionales.
No cambia formulas ni filas AA8; preserva el `EffectSource` autoritativo.

Una prueba de dano pasa solamente si existe una linea
`[AA8SkillDamage]` del arbol correcto con `amount > 0` y
`hpAfter < hpBefore`. La animacion y el texto flotante son evidencia de
presentacion, no sustituyen el cambio de HP.

## Gate S1: Gods' Whip Wave

Preparacion: tres dummies hostiles agrupados dentro del area. Ejecutar una
sola vez Gods' Whip: Wave y no usar otra skill hasta revisar logs.

Debe observarse:

1. `use_result` exitoso para skill 39674;
2. eventos de plot con objetivos cuando los rayos intersectan el grupo;
3. una o mas lineas `tree=sorcery skill=39674` con dano positivo y HP menor;
4. fin normal, cliente conectado y proceso Game sin reinicios;
5. los rayos conservan la altura del terreno.

Si falla, registrar el primer eslabon ausente: resultado, targets, efecto,
dano, HP o paquete. No avanzar a S2.

## Gate S2: Flame Barrier Mist

Preparacion: al menos un dummy hostil que pueda permanecer dentro del campo.
Ejecutar una sola vez Flame Barrier: Mist, esperar el ciclo completo y no usar
otra skill.

La skill visible es 41223 y su camino interno usa 41478. Debe observarse:

1. creacion del campo en el nivel correcto del terreno;
2. aplicacion del slow al entrar;
3. ticks `tree=sorcery` del efecto 76543 / DamageEffect 12209 con dano
   positivo y reduccion de HP;
4. cadencia aproximada de un segundo durante buff 24585;
5. cese de ticks al terminar el estado;
6. cliente conectado y Game sin reinicios.

Prueba adicional separada, solo despues del pase base: repetir contra un
objetivo Electrocute para comprobar el bonus AA8 de 41% del tag 104.

S1 y S2 pasaron el 2026-08-07. La captura final V24 contiene 16 impactos de
Flame Barrier: Mist, 6.625 puntos de delta real de HP, dos objetivos, limpieza
completa y cero errores. Sorcery queda `live_accepted` al 100%.

## Gate A0: preparacion Archery

Usar el mismo personaje estable, reloguear una vez antes de iniciar y equipar
un arco AA8 valido. Para cada fila de la matriz registrar:

- skill visible e ID;
- resultado de aprendizaje/remocion si aplica;
- costo de MP y cooldown;
- targets, impactos, dano y HP;
- buff/debuff, combo o marca observada;
- comportamiento al cancelar por movimiento;
- estabilidad del cliente y del proceso.

## Gate A1: requisitos

1. Con arco equipado, ejecutar una activa que exija `equip_ranged`.
2. Retirar el arco y repetir esa unica skill.
3. Exigir rechazo `UrkEquipRanged` antes de GCD, MP, cooldown o impacto.
4. Repetir con una sucesora ancestral para probar herencia desde la base.
5. Probar por separado la skill 10694 con y sin el buff tag 27; el rechazo
   esperado es `UrkNoBuffTag` cuando el tag esta presente.

## Gate A2: pasivas

Aprender y remover cada una de las seis pasivas por separado. Registrar la
estadistica o estado que cambia y comprobar persistencia despues de reloguear.
No aceptar solamente el icono verde. Para cada operacion exigir el par
`[AA8ArcheryPassive]` correspondiente y revisar `changed_fields` en el JSON;
si una pasiva contractual no cambia ningun campo, queda en fallo aunque el
cliente la muestre aprendida.

La autoridad es la fila y relacion nativa Kakao AA8, no la copia historica del
carrier. V4 aporta las seis filas `buffs` actuales, 21 tags pasivos unicos y
elimina ocho pares duplicados. Para buff 889 exigir que el probe de skill
refleje tag 3750/attribute 10/+10%; existen 24 consumidores y el auditor debe
informar cero `owner_keyed_relation_blockers`.

## Gate A3: activas base

Ejecutar las doce activas base una por una. Para cada una exigir el resultado
que describe AA8: objetivo unico o AoE, numero de impactos, proyectil,
cast/canalizacion, dano, buff/debuff, costo y cooldown. Incluir de forma
explicita Endless Arrows, Missile Rain y Snipe.

## Gate A4: ancestrales

Activar, probar, resetear y reloguear cada una de las doce variantes, una por
vez. Confirmar que la sucesora conserva el requisito de arma de su base. Para
Concussive Arrow: Mist exigir tanto la burbuja localizada como su camino de
dano; una de las dos sin la otra es fallo parcial.

Casos de frontera separados:

1. Concussive Arrow: Flame `36470`: liberar aproximadamente en 10%, 35%, 60%,
   85% y carga completa; la traza debe seleccionar respectivamente las bandas
   0-24, 25-49, 50-74, 75-99 y 100.
2. Snipe: Lightning `41219`: repetir en 10%, 30%, 50%, 70%, 90% y 100% para
   las bandas AA8 de 20%.
3. Snipe: Flame `41221`: probar un objetivo a 29% HP y otro exactamente a 30%;
   kind 26 debe aceptar solo el primero.
4. Deadeye `15073`: observar el bonus quieto y luego un unico movimiento; el
   trigger RemoveOnMove debe ejecutar y retirar el estado.
5. Concussive Arrow: probar sobre una unidad que aterrice; Landing debe aplicar
   su efecto hijo antes de retirar el buff 23961.

## Gate A5: cancelacion y estabilidad

Para cada skill con cast o canalizacion, hacer una prueba separada moviendose
durante el casteo. La cancelacion debe impedir impacto tardio, dano, gasto o
estado residual que AA8 no autorice. Despues de cada candidata revisar
excepciones, desconexion y `RestartCount` de Game.

## Criterio de cierre

Archery pasa de `automatic_verified` a `live_accepted` cuando A1-A5 no dejan
filas sin resultado y las pruebas negativas tampoco mutan estado. Cualquier
particularidad no cubierta por la guia vuelve al flujo forense AA8 y al
crosswalk obligatorio de reduccion de vacios; nunca se completa con balance o
semantica 10.x importada.
