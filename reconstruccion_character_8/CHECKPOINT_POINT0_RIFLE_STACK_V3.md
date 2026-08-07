# Checkpoint — Point 0 Shoot Rifle stack V3

Fecha: 2026-07-31  
Autoridad: ArcheAge Kakao 8.0.3.12 r558734  
Estado: validado manualmente con `Dannia`.

## Evidencia del segundo retest

El usuario confirmó que Shoot Rifle `46938` todavía sólo activaba el GCD, sin
animación ni daño. Los logs mostraron que la skill entraba al plot `5796` y que
la reparación V2 ya permitía superar `WeaponEquipStatus=5`.

La siguiente rama nativa es enteramente de retraso cero:

- `52251`: selecciona hasta tres hostiles y ejecuta `A = Targets`;
- `52260`: comprueba inmediatamente `A == 0`;
- rama de fallo: continúa a `52239`, animación de rifle `1074`;
- luego `52262` selecciona objetivos y `52252` inicia el proyectil `1347` y el
  camino de daño.

El planificador del servidor almacenaba el efecto de `52251` en una cola, pero
evaluaba `52260` antes de vaciarla. Por ello `A` conservaba su cero inicial y el
plot se detenía aun cuando la selección hubiera encontrado al objetivo.

## Reparación

`PlotTree` ahora vacía la ejecución del evento actual inmediatamente después
de aprobar sus condiciones y antes de recorrer sus hijos. Esto restablece el
orden causal nativo para variables, buffs y cualquier otro estado consumido
por una transición sin retraso. No se agregó ningún hardcode de Shoot Rifle.

Se agregó la regresión del camino nativo `Targets -> A -> A == 0`, verificando
que un objetivo hace falsa la guarda de cero y abre la rama de disparo.

## Validación

- Pruebas focalizadas de plots, variables y arma a distancia: 16/16.
- Suite completa .NET SDK 3.1.409-focal: 311/311.
- Compilación Docker: correcta.
- Imagen desplegada:
  `sha256:8c8aeb894caedc06b4c050dda9c6adb8f170c45f4f2479a0c0f7b53012a142d3`.
- Runtime AA8 preservado:
  `503BF9639F2005130C9E63A66A443AEA09577C082D7CE8EDC8AB11DA9118B77A`.
- `main_world` y 54/55 heightmaps cargados.
- Script compiler: 0 errores.
- Puertos 2239/2250 y registro en LoginServer confirmados.
- Arranque sin nuevos errores, excepciones ni fatales.

## Resultado del tercer retest

El usuario confirmó que Shoot Rifle funciona y que la animación del ataque
quedó reparada. Con esto se cierra P0-0004 para el punto 0.

Este cierre queda como antecedente reutilizable para Gunslinger, pero no como
prueba automática de todas sus skills. Las piezas reutilizables demostradas son
`WeaponEquipStatus=5`, la ranura física ranged, el orden causal de eventos de
retraso cero, la selección de objetivos, la animación, el proyectil y el camino
de daño. Cada skill Gunslinger deberá cerrar además su propio plot, efectos,
buffs, condiciones, recursos y protocolo AA8.
