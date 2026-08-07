# Checkpoint Sorcery V12: Chain Lightning (Wave) Snare

Fecha: 2026-08-05

## Resultado

La variante ancestral `36477 Chain Lightning (Wave)` ya recorría correctamente
su rama secundaria AoE, causaba daño y creaba `buff 21449` durante 3000 ms. La
prueba viva con varios enemigos confirmó que el congelado visual aparecía, pero
el objetivo podía seguir desplazándose: el defecto no dependía del número de
objetivos ni estaba en la selección AoE.

## Evidencia de datos

El grafo AA8 exacto es:

- `skill 36477 -> plot 2907`;
- `plot_event 24495` selecciona los secundarios del anillo;
- `plot_event 24259 -> DamageEffect 9843`;
- `plot_event 24122 -> BuffEffect 23282`;
- `BuffEffect 23282 -> buff 21449`, con probabilidad 100%;
- `buff 21449`: `duration=3000`, `root=1`, `impossible_rotate=1`.

El crosswalk AA8→AA10 V1 clasifica skill, plot, eventos, efecto y buff como
identidades o relaciones estables. No se importaron propiedades 10.x: la base
10.x sólo corroboró que el contrato estructural no tenía un hueco de datos.

## Causa raíz

`SkillManager` ya cargaba la columna AA8 `buffs.root`, pero ninguna ruta de
movimiento NPC consultaba esa propiedad. El cliente podía renderizar el estado
Freezing y el servidor podía registrar `SCBuffCreatedPacket buff=21449`, mientras
la IA continuaba ejecutando `Npc.MoveTowards`. Era una omisión transversal del
runtime de crowd control, no una falla específica de Sorcery.

## Corrección

- `Buffs.HasMovementLock()` centraliza los descriptores AA8 que bloquean
  movimiento voluntario: `stun`, `sleep`, `root`, `knockdown` y `fastened`.
- `Npc.MoveTowards` deja de desplazar la IA mientras cualquiera de esos
  descriptores está activo.
- `LeapSkillController` usa el mismo gate para impedir que un controlador de
  salto eluda el crowd control.
- No se modificó la SQLite ni se añadió una excepción por ID de skill/buff.

La misma interpretación está presente en el servidor 10.x y es compatible con
la evidencia estática exacta AA8.

## Validación

- prueba dirigida `Aa8RootDescriptorPreventsVoluntaryMovement`: 1/1;
- suite completa con el runtime activo
  `compact-8.0-runtime-honor-store-v1.sqlite3`: 514/514;
- compilación .NET Core 3.1 correcta;
- aceptación visual/conductual viva pendiente de repetir la variante Wave
  contra un mob que estuviera intentando desplazarse.

