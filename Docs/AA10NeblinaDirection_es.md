# Neblina: corrección de altura y revisión del seguimiento

2026-09-11, segunda entrega. Continúa `AA10NeblinaReconstruction_es.md`.
Target `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`, padre exacto
`upstream/client_version/zone-10.0.2_r575` (`7babcb3a706c64295b5aaaeec8abe57e4d09b4da`).
Se preservaron los 102 paths sucios al iniciar esta revisión.

## Evidencia del usuario

Videos originales en `C:\Users\juank\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings`:

- `20260911-1812-15.0045878.mp4`, 4,27 s: flechas visibles durante la habilidad;
  trayectoria ascendente, especialmente clara al bajar la cámara entre1,5 y2 s.
- `20260911-1813-29.0641809.mp4`, 8,06 s: salvas contra varias unidades con daño
  visible y proyectiles orientados hacia ellas. El usuario rechaza su aparente
  seguimiento como comportamiento original.

Se extrajeron contact sheets a2 fps para revisión, sin modificar los videos.
Evidencia y hashes: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\archery-mist-direction-20260911`.
La primera entrega queda aceptada sólo respecto a la reaparición de flechas;
no equivale a aceptación de trayectorias, cadencia exacta ni daño.

## Causa de la elevación y corrección

La rama posicional de AA10 encadena:

| Evento | Datos | Resultado anterior en suelo plano, lanzador Z100 |
|---|---|---|
|24565, Area|distancia20000, altura0|destino20 m delante, Z100|
|24854, RandomArea|p3=6000,p4=8000,p5=0|dispersión horizontal6 m y elevación injustificada a Z108|
|24575, Area|altura explícita p5=1000|destino final Z109|

`PlotTargetRandomAreaParams` había etiquetado p4 como HeightOffset con el
comentario «This is not confirmed». Los datos de prueba AA10 también distinguen
1118 «임의 지역 수평» (área aleatoria horizontal), p3=10000/p4=0/p5=0, de1122
«임의 지역 수직» (área aleatoria vertical), p3=0/p4=0/p5=5000. Esto no cierra toda
la semántica de p4, pero tampoco justifica tratarlo como una altura aditiva.

La corrección elimina la suma de p4 a la altura del ancla. Conserva el valor
como `Param4`, sin asignarle una semántica nativa no probada. Mantiene la política
existente de suelo, agua y portales, incluido su tratamiento previo de sondeos
grandes; no introduce el límite de terreno8 m propuesto por AA8. Mantiene también
el offset **explícito** de1 m en Area24575 y los offsets de otros eventos Area.
En el caso plano probado, el destino final queda en Z101, delante del lanzador.

Clasificación: `server-required`, retirada de una compensación sin contrato
nativo, respaldada por filas AA10 y el resultado visual del usuario. La
semántica completa de RandomArea.p4 y su comportamiento en pendientes permanece
abierta; no se declara reconstrucción completa de RandomArea.

## Qué sabemos sobre las flechas dirigidas

AA10 contiene dos rutas diferentes:

- 24566→24567, enlace28159 `per_target=true`, proyectil840 y selector Target4.
- Relleno24575, proyectil840 y selector Location5.

El handler nativo ya analizado, RVA0x6CB250, crea destino de unidad para
PlotObj1 y destino de posición para PlotObj2. Por eso enviar unidades a la
primera rama produce proyectiles dirigidos por el propio cliente. El servidor
no implementa una simulación adicional de persecución en SpecialEffect.Projectile.
Esto demuestra el camino de ejecución actual; **no prueba por sí solo que toda
la persecución observada, su selección o su continuidad durante el vuelo sean
idénticas al servidor original**. Esa aceptación continúa abierta. No se ha
eliminado ni convertido la rama Target a Location por intuición.

La nueva decompilación release descarta otra interpretación incorrecta:
RVA0x752060 mapea el valor8 del efecto Projectile a `item_hand_l`; RVA0x759910
configura la unión al hueso. No es un bit que active/desactive homing. RVA0x7597B0
copia la estructura de destino al proyectil. Las tres funciones fueron
reancladas byte a byte contra x2game.dll x64 del cliente principal:
`405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`.

La [nota oficial rusa del18-05-2017](https://archeage.ru/updates/18052017/)
ya describe la variante ancestral con diez salvas de seis flechas contra un
oponente y penalización cercana. Es corroboración histórica regional; no
demuestra trayectorias ni permite afirmar que el seguimiento sea una novedad
de10.x. Los indicios de cambios posteriores para disparar sin objetivo tampoco
constituyen prueba de que se eliminara la ruta por unidad.

## Verificación y entrega

- Restore/build Release correctos; cero errores de compilación.
- Suite completa: **2767/2767**.
- Prueba con eventos nativos24565/24854/24575 en cuatro orientaciones, veinte
  muestras por orientación: altura100/100/101 y proyección frontal entre13,9
  y26,1 m, respetando distancia20 m y dispersión6 m existentes.
- Regresiones de terreno ausente, suelo, portal aéreo y agua; los tests de
  offsets Area y ciclo de vida de Incesantes permanecen verdes.
- Imagen anterior: `aaemu-world:before-neblina-direction-20260911`.
  Respaldo consistente nuevo de DB y compact en `rollback`, fuera de Git.
- Sólo se reemplaza el servicio Game/World; sin cambios de datos, cliente ni
  operación del lifecycle de Zones. Hashes y arranque en el manifest de entrega.

Primera prueba retail del nuevo build: arco, sin objetivo, cámara lateral y una
sola Neblina hacia terreno despejado. Debe desaparecer la elevación artificial
de8 m. La comparación con objetivos debe registrar orientación del lanzador,
posición de cada unidad al disparar y si una flecha cambia de trayectoria
después de salir. Siguen abiertos la sexta flecha y la fórmula de daño cercano.
