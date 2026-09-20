# Tiger Strike: Lightning — composición de tiempos AA10

Continuación del 20/09/2026 sobre `16f50e1d9`, rama `rama_10`.
Skill36448, plot2922. Sustituye el estado pendiente de temporización de
[TIGER_PASSIVES_20260920.md](TIGER_PASSIVES_20260920.md).

## Causa y corrección

El servidor sumaba dos esperas que parten del mismo evento: el plazo de la
arista siguiente y la duración del controlador de desplazamiento. En Tigre,
400+400 pasaba a800 ms y300+300 a600 ms. La terminación nativa del Leap ya se
mide desde su inicio; no empieza a contar después de la espera de la arista.

Se cambia únicamente la composición de `PlotNextEvent.GetDelay`:

```text
antes: animationSync + projectileTravel + edgeDelay + controllerCompletion
ahora: animationSync + projectileTravel + max(edgeDelay, controllerCompletion)
```

Esto conserva la espera del controlador cuando la arista vale0 y evita sumarla
dos veces cuando ambas describen la misma fase. Sigue aplicándose el ajuste de
casting sólo a aristas de casting. El cálculo usa long antes de limitar a int.
Clasificación: **server-required**, composición de los plazos AA10; primitiva
AA8 contrastada con descriptores y reloj de Leap AA10.

No se usa el candidato anterior basado en `UseExeTime`, que hacía desaparecer
la espera del primer daño. Tampoco se añade el marcador308 de StartAnim175:
ese dato pertenece a la animación del controller, mientras el evento declara
Anim46. Confundir ambas referencias habría introducido otra espera no probada.
La investigación de animación fue útil para descartar esa alternativa; no se
modifica el selector de animaciones, su velocidad ni el cliente.

## Secuencia programada

Tiempos relativos al inicio del plot, sin latencia de red ni sobrecarga del
scheduler. Son resultados del grafo/delay de producción, no una captura del
cliente de esta sesión.

| Acción | Antes | Después |
|---|---:|---:|
| Primer desplazamiento24143 | 1 ms | 1 ms |
| Primer daño27709 | 401 ms | 401 ms |
| Segundo desplazamiento24145 | 821 ms | 421 ms |
| Segundo daño24146 | 1421 ms | 721 ms |
| Tercer desplazamiento24152 | 1441 ms | 741 ms |
| Tercer daño24146 | 2041 ms | 1041 ms |

Los giros mantienen sus20 ms. Primer→tercer impacto: **640 ms**, con320 ms
entre impactos consecutivos. El mismo objetivo se conserva en el grafo; no
hay un cuarto nodo de daño. No se cambian selectors, montos, condiciones,
cooldown/GCD, auto_fire, Combo, orden intranodo ni publicación SC/WZ.

## Procedencia y contraste

Hashes de full/runtime/client/Zone: informe anterior. El nuevo
`timing-audit.json` compara quince selecciones completas AA10: todas iguales
entre full y compact. El fixture embebido contiene17 eventos,19 aristas,
34 efectos,5 controllers y19 SpecialEffects de la SQLite full.

Se consultó después el comparador AA8
`D:\Proyectos\AAemu\rama_8\reconstruccion_skills_8\shared_primitives\CHECKPOINT_AA8_PLOT_TIMING_COMBAT_SYNC_V1.md`.
Ya documentaba la composición por máximo, sus tres impactos en640 ms y la
aceptación visual AA8. **Esa aceptación no se presenta como una prueba AA10.**
Se cotejaron las19 aristas por IDs/plazos/flags y los cinco controllers por
kind/value2–5/start_anim_id. Sin diferencias de esos valores, salvo NULL frente
a0 en start_anim_id de los dos giros (ambos ausencia de animación).

AA10 dedicate x64, SHA
`8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`,
base39000000, RVAs:

- `26EDA0`: construcción del controller desde el descriptor; value3 pasa como
  duración. IDs11024/11025/11026 declaran400/300/300 ms.
- `231780`/`231AB0`: preparación posición/unidad; duración en+74, inicio en+94.
- `241890`: el tick compara inicio+duración con el reloj; confirma que es un
  plazo del desplazamiento en curso, no una pausa posterior a la arista.
- `227E10`: sólo escala velocidad/duración si se activa el flag recibido de
  value12; los tres Leap de Tigre tienen value12=0. No acelerar con attack speed.

Cliente release x64, SHA
`2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76`:
PlayEvent6CE380 → PlayEffect6CDC70 → controller6CD950 / Anim6CC9C0.
La animación sigue siendo nativa. Las funciones2F8210/2FA860 extraen su marcador
combat_sync; no constituyen por sí solas el scheduler de World y no se usaron
para inventar un tiempo de daño nuevo. `use_exe_time` sigue cargado sin promover
una semántica nueva a partir únicamente del nombre.

## Alcance y regresiones

La primitiva compartida afecta539 aristas con delay positivo y controller
value3 positivo/value5=1, en371 plots:537 aristas Leap y2 Rotate. El inventario
completo queda en `affected-controller-edges.json`. No cambia las aristas sin
controller ni las esperas0 que ya dependen sólo de él. No se restringe por
skill ID ni se sustituye ningún valor del catálogo.

Cinco pruebas nuevas:

- El grafo AA10 completo recorre el scheduler y `GetDelay` reales: exactamente
  tres nodos de daño, primer impacto401 ms, último1041 ms y separación640 ms.
  Se modela el camino exitoso; no se simulan inmunidades, animación o fórmula de daño.
- Aristas0/400/650 junto al controller400: esperan400/400/650 respectivamente.
- Una arista sin controller conserva su espera735 ms.

Antes:3 fallos/5; después:5/5. Restore/build Release correctos. Suite completa:
**5534/5534**,0 fallos,0 omitidos, incluyendo Hammer, combos, lifecycle y
scheduler existentes. La prueba de tiempos no sustituye la aceptación visual.

Recrear evidencia y fixture:

```powershell
C:\Python313\python.exe reconstruccion_cliente_10/battlerage/audit_tiger_passives.py `
  --full E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3 `
  --runtime .server_files/AAEmu.Game/Data/compact.sqlite3 `
  --output E:\AAEmu\rama_10\artifacts\battlerage-tiger-passives-20260920\timing-audit.json `
  --timing-fixture E:\AAEmu\rama_10\artifacts\battlerage-tiger-passives-20260920\timing-fixture.json
```

Artefactos de esta continuación: prefijo `tiger-phase-*`, `tiger-final-tests`,
`tiger-build`, `tiger-docker-build`, `native-plot-*`, `native-sync-*`,
`native-controller-*`, `native-leap-clock-scale` en el directorio citado.
No se operó el cliente ni el lifecycle de Zones; el usuario conserva las pruebas.

Rollback de imagen: `aaemu-world:rollback-before-tiger-tempo-20260920`,
imagen previa `4d607c6cd3bcf692ab046de139f729988b299ae665d744173391810154217067`.
Sin escrituras de SQLite/game_pak/MySQL/configuración de red.

Desplegado en la imagen
`7137fd39c3114a35dcec6382859a13afa4e7541ebf389104bf4c99e63e6a3d87`.
Las dos copias de AAEmu.Game.dll (`/app` y `/app/game`) coinciden en
`f5a11c8c3c1513baf726b7b5e39540b4b67fe10393b34ffdc04e46848fbb8136`.
Compact conserva el hash previo. Arranque confirmado por `GameService - Server
started!` a las **21:22:00 UTC**; Game/Stream iniciados, TCP1239/1240/1250
accesibles, contenedor healthy y0 reinicios. Los avisos de experiencia y BAI20
omitido son previos; no se atribuyen a esta modificación.

El usuario debe relanzar sus Zones/relog tras el reinicio de Game y comprobar
un cast de Tigre Rayo contra el mismo dummy. El parche está implementado y
desplegado; no se afirma una aceptación visual AA10 que no se ha ejecutado.
