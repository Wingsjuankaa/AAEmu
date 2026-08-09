# Checkpoint AA8 — presentación posicional de skills plot-only V1

Fecha: 2026-08-09
Cliente: ArcheAge Kakao 8.0.3.12 r558734
Estado: **cerrado en Mechanics Lab y cliente AA8 real**

## Problema de referencia

Hammer Toss/Ollo's Hammer `18757` aplicaba correctamente stun y daño, pero el
martillo dejó de ser visible. Una corrección provisional mostró un FX parecido
antes de tiempo y fuera de sincronía. La evidencia histórica aportada durante
la aceptación confirmó que el FX correcto funcionaba antes de reconstruir
Battlerage V2.

## Clausura AA8 confirmada

- skill `18757`: `plot_only=1`, plot `440`, projectile directo `308`;
- evento `3478`: entrada del plot;
- evento `28784`: actualización de target `Area` por método `5`, volumen cero;
- evento `3480`: presentación y continuación autoritativa;
- SpecialEffect `7284`: tipo `36`, `FxGroupAnim 3155`;
- SpecialEffect `7285`: tipo `34`, `Anim 447`;
- SpecialEffect `7742`: tipo `38`, `ProjectileAnim 909`, `value3=20`;
- projectile directo `308`: familia visual distinta, FX group `1195`;
- projectile animado `909`: familia nativa del plot, FX group `3156`.

El método `Area` de volumen cero no selecciona otra unidad. Construye un
objeto posicional sintético con `ObjId=uint.MaxValue`, copia la transformación
y región del target anterior y lo entrega al siguiente evento. El target real
permanece disponible para la resolución autoritativa del daño.

## Regresiones y falsificación

### Battlerage V2

Se añadió una optimización genérica que conservaba la identidad del target
anterior en áreas de volumen cero. El plot siguió aplicando daño y stun, pero
`SCPlotEvent 3480` dejó de transportar una posición y el cliente perdió el
martillo nativo.

### Battlerage V3 — hipótesis falsificada

Se emitió un `SCSkillFired` directo antes del plot usando projectile `308`.
Mechanics Lab confirmó ejecución, pero la prueba viva mostró un efecto
incorrecto, prematuro y desincronizado. El projectile directo no sustituye a
`ProjectileAnim 909` y el paquete adicional duplicaba autoridades de
presentación.

### Battlerage V4 — cierre

Se restauró la semántica posicional anterior a V2 y se retiró por completo la
ruta directa V3. El ledger aprobado es:

`SCPlotEvent(3480, POSITION) -> SCUnitDamaged -> SCBuffCreated -> SCPlotEnded`

No aparece `SCSkillFired` adicional. La prueba visual real confirmó martillo,
sincronización, impacto, stun y daño correctos.

## Reglas para otras ramas

Ante una skill que hace daño pero carece de projectile/FX, o cuyo FX aparece
desincronizado:

1. comprobar si es `plot_only` antes de emitir paquetes directos;
2. recorrer todos los eventos y target updates intermedios, no sólo el evento
   que contiene daño;
3. tratar `POSITION` y `UNIT` como contratos de presentación distintos;
4. separar target visual, target de selección y target autoritativo de daño;
5. auditar `ProjectileAnim`, `Anim` y `FxGroupAnim` antes de buscar otro asset;
6. no deducir equivalencia por compartir nombre, icono o projectile en la fila
   principal de la skill;
7. contrastar contra una ejecución conocida funcional cuando un refactor
   genérico precede la regresión;
8. usar Mechanics Lab para orden, duplicados, daño y cierre; usar el cliente
   real como oráculo final de animación y FX.

Esta regla es aplicable a cualquier árbol y no contiene excepciones por skill
ID en el runtime.

## Validación y artefactos

- compact: `compact-8.0-runtime-battlerage-v4.sqlite3`;
- SHA-256 compact:
  `A244EBEDB2CB58E1E09830650539C97FD77E2EBC077027067563414BC03DA262`;
- dos builds deterministas, `quick_check=ok`, `integrity_check=ok`;
- validador estructural: `10/10 PASS`;
- suite .NET Core 3.1: `602/602 PASS`;
- Mechanics Lab `battlerage_ollos_hammer`: PASS;
- SHA-256 del resultado Lab:
  `9CB3B97A7D5B83AF4D554750EA7F0CB62C440329F0DAD65601C0E5E458ACE358`;
- prueba visual AA8 real: **PASS**;
- desplegado sólo `game`; compact montada con el hash esperado y registro
  exitoso en LoginServer.

## Superficies modificadas y evidencia reproducible

- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotTargetInfo.cs`: se retiró el
  atajo que devolvía la unidad previa para un `Area` de volumen cero; vuelve a
  construir el objeto posicional nativo;
- `AAEmu.Game/Models/Game/Skills/Plots/UpdateTargetMethods/PlotTargetAreaParams.cs`:
  se eliminó `CarriesPreviousTarget`; se conserva la resolución genérica del
  radio AA8 desde `param6` cuando corresponde;
- `AAEmu.Game/Models/Game/Units/BaseUnit.cs`: Mechanics Lab reconoce como
  visible una posición ya resuelta sin registrarla como unidad real;
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotNode.cs`: traza estable del
  tipo de target transportado por `SCPlotEvent`;
- `AAEmu.Tests/MechanicsLabInfrastructureTests.cs` y
  `AAEmu.Tests/PlotAreaTargetSelectionTests.cs`: regresiones de visibilidad y
  semántica posicional;
- `reconstruccion_skills_8/battlerage/build_battlerage_runtime_v2.py` y
  `test_battlerage_runtime_v2.py`: runtime V4 y rechazo explícito de la
  política provisional V3;
- `mechanics-lab/scenarios/battlerage_ollos_hammer.json`: recorrido headless
  permanente;
- `runtime-captures/mechanics-lab/battlerage-v4-hammer-restored-2`: resultado
  aprobado del Lab;
- `runtime-captures/packet-traces/aa8-game-20260809-155239639-session-2791551298.jsonl`:
  control histórico previo sin `SCSkillFired` directo.

La implementación provisional V3 en `Skill`, `SkillManager` y
`SkillTemplate` fue retirada por completo. Esas clases no conservan una
bandera ni un camino especial por `18757`.

## Regresiones permanentes

- `PlotTargetInfo.UpdateAreaTarget` debe conservar el objeto posicional para
  un target `Area`; no debe devolver automáticamente la unidad previa;
- Mechanics Lab debe considerar visible el objeto posicional resuelto sin
  registrarlo como una unidad del mundo;
- el constructor Battlerage debe rechazar la columna provisional
  `server_plot_only_fire_presentation`;
- Hammer Toss debe conservar `plot_only=1`, plot `440` y projectile `308`, sin
  convertir este último en una segunda entrada de ejecución.
