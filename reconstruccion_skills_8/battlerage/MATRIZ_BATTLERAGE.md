# Matriz de cierre de Battlerage — AA 8.0

Fuente de esta revisión: `battlerage-phase4-closure.json`, SHA-256
`541CAF080C2C05EA9EC142F27AF9000EEF868DB88C4B0B8CE6F754878D59F096`.

## Habilidades visibles aprendibles

| Orden | Familia raíz | ID raíz | Nivel | Dependencias 8.0 principales | Estado |
|---:|---|---:|---:|---|---|
| 1 | Triple Slash | 18132 | 1 | 18134, 18131; ancestrales 36401–36406; plots 2541, 2855–2857 | Datos cerrados; prueba funcional pendiente |
| 2 | Charge | 11918 | 3 | auxiliar 12028; plot 624; controller 8229 | Catalogada |
| 3 | Battle Focus | 10377 | 10 | efectos y buffs nativos | Catalogada |
| 4 | Whirlwind Slash | 13282 | 15 | 32040, 32049; plots 133, 2230, 2231 | Catalogada |
| 5 | Sunder Earth | 10644 | 20 | 41217, 41218; plots 649, 4044, 4045 | Funcional en prueba local; pendiente segundo cliente |
| 6 | Frenzy | 10455 | 25 | 43188, 43189; habilidad automática 34119 | Catalogada |
| 7 | Precision Strike | 12026 | 30 | 36446, 36447; plots 2903, 2921 | Catalogada |
| 8 | Tiger Strike | 13315 | 35 | 36448, 36449; plots 17, 2922, 2923 | Catalogada |
| 9 | Bondbreaker | 12034 | 40 | efectos nativos de liberación/buff | Catalogada |
| 10 | Terrifying Roar | 18308 | 45 | 14 relaciones nativas directas | Catalogada |
| 11 | `올로의 망치` | 18757 | 50 | plot 440 | Catalogada; nombre no reinterpretado |
| 12 | Behind Enemy Lines | 23587 | 55 | 39661, 39662; controllers 10258, 11525, 11526 | Catalogada |

## Habilidades automáticas visibles de costo cero

| ID | Nombre recuperado | Nivel | Estado |
|---:|---|---:|---|
| 34124 | Soulbound Edge | 10 | Incluida en la clausura |
| 34119 | Fury | 25 | Incluida en la clausura |
| 34120 | Bladefall | 55 | Incluida; plot 8000065 |

## Pasivas nativas

| ID | Buff | Requisito de puntos | Estado |
|---:|---:|---:|---|
| 32 | 2610 | 3 | Datos cerrados; prueba pendiente |
| 245 | 7542 | 4 | Datos cerrados; prueba pendiente |
| 92 | 2621 | 5 | Datos cerrados; prueba pendiente |
| 29 | 811 | 6 | Datos cerrados; prueba pendiente |
| 295 | 831 | 7 | Datos cerrados; prueba pendiente |
| 244 | 7544 | 8 | Datos cerrados; prueba pendiente |

## Resultado del primer corte de datos

- 42 filas de skills Battlerage.
- 115 relaciones `skill_effects` nativas.
- 152 efectos y todas sus filas concretas alcanzables.
- 55 buffs con sus relaciones alcanzables.
- 18 plots, 338 eventos y 395 transiciones.
- 35 animaciones, 16 controladores y 3 proyectiles alcanzados.
- Cero dependencias de efectos o tipos de plot sin resolver.
- Cero animaciones, proyectiles, formas AoE o controladores jugables faltantes.
- El controller `604` sólo pertenece a la skill oculta `11854`, marcada como
  obsoleta por el catálogo nativo; se conserva como evidencia fuera del cierre
  jugable.

## Triple Slash: estado inicial

La compact runtime anterior mezclaba relaciones históricas y omitía las
modernas:

- `18132` conservaba una relación histórica adicional que no figura en el
  resultado nativo 8.0.
- `18131` no contenía la quinta relación nativa 8.0.
- `36401–36406` no tenían relaciones de efectos en runtime.
- los plots `2855–2857` no tenían eventos.

El artefacto `compact-8.0-runtime-phase4-battlerage-v1.sqlite3` corrige esa
clausura sin tocar la compact estable anterior. Pasó `quick_check`,
`integrity_check`, validación de huérfanos y cadenas doradas. Su SHA-256 es
`84990525F520B22BEBB3EAE4A0941B16A5A78C0A900F697E12AF69017D7B7871`.

El siguiente estado sólo puede cambiar a **completa** después de desplegar este
artefacto y validar en cliente los tres golpes, daño, debuffs, transición de
icono/skill, repetición, GCD, animación/FX/sonido y relog.
