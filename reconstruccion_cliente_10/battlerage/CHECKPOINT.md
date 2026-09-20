# Battlerage AA10 — primera auditoría y correcciones

**Herramienta de pruebas: [modo GM sin cooldown](GM_COOLDOWN_20260920.md).**
Reset puntual y continuo limpian grupos compartidos; GCD y cadenas conservados.
Aceptación en el cliente a cargo del usuario.

**Seguimiento actual: [ancestrales de Triple Slash y Frenesí](ANCESTRAL_FRENZY_20260920.md).**
Corrección desplegada y probada con Dannia en Zone 142; 5.511 pruebas correctas.
Rayo/Terremoto completan tres etapas; Frenesí expira y limita las extensiones a
40 s restantes. Pruebas jugables, limpieza de procesos y pendientes detallados
allí. Martillo: impacto con y sin stun en repeticiones, investigar dado; salto:
shape 5047 recurre a 40 m, área pendiente. No declarar Battlerage completo.

**Base de cadencia conservada: [reparación del GCD y respuestas de cadenas](CHAIN_RECOVERY_20260920.md).**
Corrección desplegada; 5.504 pruebas correctas y aceptación del usuario el
2026-09-20: «perfecto, ya funciona como debiese» (`f8af778cf`). El rollback y la
aceptación anterior retirada se conservan como historial.

Seguimiento posterior: [sucesiones de Triple Slash y Whirlwind Slash](COMBOS_20260918.md).
Conserva el diagnóstico y alcance de esta primera auditoría; las pruebas nuevas
se registran en ese seguimiento.

Fecha: 2026-09-18. Target `rama_10`; padre comunitario exacto
`upstream/client_version/zone-10.0.2_r575` (`30837660a75e4beef5a38f37bf95809edf055f53`).
Inicio: `69a3d7f35`. Validación final sobre `cbbd1ebaa6b59bf3b05ee36047ea36e4eaa3c33d`,
que incorpora el arreglo de inventario terminado en paralelo, más los cambios de esta tarea.

Seguimiento de la prueba del usuario: [puntos tras reset de Archery](SKILL_POINTS_20260918.md).
Se detectó contaminación del conjunto aprendido del cliente por siete acciones
temporales de pesca. Tiene una entrega y validación separadas del martillo.

**Esta entrega abre la reconstrucción por ramas; no certifica Battlerage completo.**
Se inventariaron las doce habilidades visibles, doce opciones ancestrales y seis
pasivas. Se corrigieron dos bloqueos del plot del martillo y el ejecutor de
reinicio de cooldown usado por Deflect and Retaliate. Falta aceptación jugable
en el cliente y quedan fronteras de combate indicadas en la matriz.

## Qué cambió

### Martillo 18757 / plot 440

El alcance de 15 m y el stun de 1500 ms ya estaban en los datos r575. No se
añadieron efectos, IDs, duraciones, cooldowns ni excepciones por skill.

1. `28784` crea un destino posicional `BaseUnit`, con `ObjId=uint.MaxValue`.
   `3480` conserva ese destino y exige Visible (`10725`). Una posición nunca
   recibe `Show()` y su `IsVisible` permanece falso: la comprobación anterior
   abortaba el lanzamiento. Ahora los anchors posicionales usan la comprobación
   espacial existente `UnitIsVisible`; las entidades reales conservan sus
   comprobaciones de visibilidad y stealth. Una posición sin región o fuera de
   las regiones visibles sigue siendo rechazada.
2. La fuente de `28786` también es una posición. `PlotEventCondition` la
   convertía a `Unit`, provocando `InvalidCastException`. Los cuatro selectores
   conservan ahora `BaseUnit`, que es el tipo admitido por las condiciones y
   usado también por los efectos.

Recorrido nativo registrado: `3478 → 28784 → 3480 → 25184 → 25939 → 25944 →
25984`; el gate de relación de `25984` distingue el objetivo original del
resto del área. El buff aplicado es `22532`, vía `BuffEffect 24460`. El ramal
alternativo de knockback usa `28786` / controller `11306`.

La prueba usa filas extraídas de la SQLite completa, el actualizador de targets
y los gates de producción. Cubre 3/12/15 m, fuentes posicionales, región ausente
o distante, entidad oculta, objetivo principal/secundario, aplicación única del
buff de 1500 ms y rechazo de un hit fallido. **No simula la selección espacial
completa de NPCs de Zone ni el tiempo de vuelo renderizado.**

### Reinicio de cooldown por etiqueta

La pasiva `2610` registra `combat_buffs 23`, aplica `2611` y al expirar dispara
`special_effects 4636`: `(0,415,1,0,1,1,0)`. El ejecutor anterior enviaba un
paquete con sus flags finales a cero y no modificaba los cooldowns de las
habilidades etiquetadas en el servidor.

Ahora se consumen los siete valores del efecto. Se distinguen la clave de una
habilidad, la clave de un grupo y el conjunto de habilidades etiquetadas.
Los flags determinan si se eliminan también los grupos compartidos. El GCD se
reinicia sólo cuando lo indica el efecto. Cliente y servidor reciben la misma
selección, en un paquete. No se modificaron los resets GM ni se añadió una lista
especial de habilidades Battlerage.

La decompilación r575 confirma que `rtsc`/`rtstc` significan **tagged skill**,
no toggle skill. Ver [evidencia nativa](NATIVE_RESET_COOLDOWN.md).

## Lo que dice la comparación AA8

- En las columnas compartidas de los doce registros visibles `skills`, once
  coinciden tras normalizar booleanos y referencias nulas. Rugido `18308`
  tiene `check_obstacle=true` en AA10 frente a false en el catálogo AA8.
- Triple Slash Terremoto `36404/36405/36406` cuesta **20** de maná en AA10
  frente a **12** en AA8. Se conserva AA10.
- Attack Speed Training `811` es una cadena distinta: `combat_buffs 51`, tag
  `4749`, buff `22277`, trigger `14546`, efecto `87395`, recurso `1`.
  El recurso tiene máximo 5 y recuperación de 9000 ms. El buff intermedio de
  1000 ms tiene inmunidad a su propio tag `3714`. No se portó el proc AA8
  `11344` ni su tabla derivada `passive_procs`.
- Las automáticas AA8 `34119/34120/34124` no existen en `skills` de la SQLite
  completa AA10. No se crearon sustitutos por coincidencia de nombre.
- Estos resultados comparan datos; no prueban equivalencia de fórmulas,
  selección de víctimas, movimiento ni cadencia.

## Cobertura reproducible

`audit_skill_branch.py` abre las tres SQLite en modo sólo lectura. Extrae
42 registros de habilidad de ability 1, seis pasivas y sus referencias
explícitas: **3803 filas / 39 tablas**, 18 plots, 338 eventos, 262 condiciones,
38 buff triggers y tres combat buffs. Incluye opciones ancestrales, efectos,
buffs, modificadores, requisitos, controllers y el recurso de combate.

Dentro de ese grafo no hay filas ausentes ni diferencias funcionales entre
full y SQLite montada en Game. Los cuatro `skill_controller_id` textuales
`--- :null` en buffs 127/143/182/183 se registran como referencias inválidas,
no se convierten en IDs ni se ocultan. No se expanden todos los miembros de un
tag genérico; no se incluyen automáticamente herramientas de ítems ni skills
de otras abilities sólo porque compartan etiquetas.

Dos generaciones independientes (`accepted-a`, `accepted-b`) producen
`catalog.json` SHA-256:
`405E938B819DE27413EC43F0FAE1E2441C2EBD7E2D0E01C3152C7AACA5B6B3ED`.
Las tres fuentes pasan `quick_check` e `integrity_check`.

El [manifiesto](manifest.json) conserva hashes de las fuentes, los nueve archivos
de código/fixture comprobados contra la copia compilada y el despliegue. Las
65 filas del fixture del martillo se cotejaron íntegramente con la SQLite full.
El [inventario generado](inventory.md) permite recorrer los 42 registros.

Reproducción desde la raíz del repositorio (salida separada de las fuentes):

```powershell
C:\Python313\python.exe reconstruccion_cliente_10/battlerage/audit_skill_branch.py `
  --full E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3 `
  --runtime .server_files\AAEmu.Game\Data\compact.sqlite3 `
  --client E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview\game\db\compact.sqlite3 `
  --aa8 D:\Proyectos\AAemu\rama_8\reconstruccion_skills_8\battlerage\generated\battlerage-v2-native-closure.json `
  --output E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\battlerage-recheck
```

Artefactos extensos, fuera de Git:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\battlerage-20260918`.
Pruebas/build/despliegue:
`E:\AAEmu\rama_10\artifacts\battlerage-20260918`.

## Validación y despliegue

- Martillo: baseline corregido del fixture **8 fallos / 9** antes del cambio;
  **10/10** después, incluyendo la prueba adicional de aplicación del buff.
- Cooldowns: **4 fallos / 7** antes; **8/8** después, incluido body con cuatro flags.
- Restore y build Release de la solución: correctos.
- Suite final aislada sobre `cbbd1ebaa` + estos cambios: **5446/5446**, sin omitidos.
- La primera ejecución aislada tuvo siete fallos de preparación: seis tests
  exigen que la carpeta se llame `AAEmu`, y uno verifica bytes de un manifiesto
  alterados por autocrlf. Se corrigió la disposición de la copia y se copiaron
  los bytes canónicos del manifiesto; no se relajaron tests ni hashes.
- Imagen preparada y desplegada:
  `sha256:83a131be4133377e72f2c716286020846b3bf7874b892deb5cee2cb26464da2e`.
  Docker build usa una copia aislada bajo
  `E:\AAEmu\rama_10\validation\battlerage-20260918-run\AAEmu`.
  El tag habitual `aaemu-world:10.0.2.13-r575-local` queda actualizado.
- Arranque confirmado a las 18:05:35 UTC: Game/Stream escuchan en 1239/1250;
  ambas conexiones TCP comprobadas. Contenedor healthy, cero reinicios. Las dos
  copias publicadas de `AAEmu.Game.dll` coinciden y la SQLite montada conserva
  su hash. Esto comprueba arranque, no combate en cliente.
- El log de arranque registra desconexión Zone 0, datos de experiencia no usados
  por encima de nivel 56, definiciones de smelting 29–32 inválidas y un Areas BAI
  versión 20 omitido. Quedan registrados en `deployed-startup.log`; no se
  resolvieron ni se atribuyen a este cambio. Smelting queda fuera de alcance.
- Rollback conservado como `aaemu-world:rollback-before-battlerage-20260918`
  (imagen previa `87b849094c8ded2c2e184c6b85e1c42f873a3ec6f3c637a45016b354e338aadb`).
  No hay migraciones ni escrituras de SQLite/clientes/game_pak en esta entrega.
- No se inició ningún cliente ni Zone. No se crearon ventanas CMD.
  **No hay aceptación en vivo del stun, de la pasiva ni del árbol completo.**

Rollback local, sin revertir datos de personajes:

```powershell
docker tag aaemu-world:rollback-before-battlerage-20260918 aaemu-world:10.0.2.13-r575-local
docker compose -p aaemu10 -f docker-compose.yaml -f .server_files/docker-compose.aa10.yaml up -d --no-deps --no-build game
```

## Continuación

Seguir [MATRIZ_BATTLERAGE.md](MATRIZ_BATTLERAGE.md). La siguiente frontera
transversal es el resultado de impacto: `ConditionCombatDiceResult` todavía
vuelve a tirar y no interpreta su máscara nativa. AA10 conserva
`enum_combat_dice_results` (hit/critical/miss/dodge/block/parry/resist/immune);
hay un candidato AA8, pero `DamageEffect` de AA10 debe integrarse y probarse
como un conjunto para que daño y combos compartan el mismo resultado. No se
portó parcialmente durante esta corrección de targets/cooldowns.

También falta verificar la supresión de 12 s de las pasivas de parry/crítico,
el destinatario de la skill automática `16185` y el parry ranged de Weapon Training.
La bonificación del recurso 1 quedó corregida en la revisión siguiente; la
aceptación visual sigue pendiente.

## Revisión del 20/09: Tigre, Frenesí y pasivas

Ver [TIGER_PASSIVES_20260920.md](TIGER_PASSIVES_20260920.md): carga y aplicación
de modificadores CombatResource corregidas, siete pruebas nuevas y suite final
5529/5529. Frenesí Oleaje/+6 %/reset tras parry tienen pruebas de servidor,
con límites explícitos para la sesión real y C. El candidato de timings de
Tigre se retiró por no cerrar la sincronización del primer daño; no se desplegó.

Continuación: [TIGER_TIMING_20260920.md](TIGER_TIMING_20260920.md) corrige la
composición arista/controller por máximo, conservando el primer impacto401 ms.
Tres daños a401/721/1041 ms en el grafo probado; suite5534/5534. No se reutiliza
el candidato UseExeTime. Aceptación visual AA10 a cargo del usuario.
