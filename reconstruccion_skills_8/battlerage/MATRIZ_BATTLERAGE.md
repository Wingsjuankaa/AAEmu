# Matriz Battlerage V5 — ArcheAge Kakao 8.0.3.12 r558734

Estado del candidato desplegado el 9 de agosto de 2026. `AA8` es la autoridad;
Modern sólo se usó como comparador de implementación y el crosswalk 10.x sólo
para orientar relaciones que luego fueron corroboradas en AA8.

## Artefacto activo

- Compact: `compact-8.0-runtime-battlerage-v5.sqlite3`.
- SHA-256: `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`.
- Clausura: `battlerage-v2-native-closure.json`.
- SHA-256 de clausura: `9B29046271D67802F9D3986AFFFB54640DC1292544FFB34B0A2AD7AEB44D10A8`.
- Dos builds limpios idénticos; `quick_check=ok`, `integrity_check=ok` y cero
  dependencias jugables huérfanas.
- Cero filas 10.x promovidas al runtime.

## Activas visibles

| Habilidad | IDs cubiertos | Datos AA8 | Mechanics Lab | Cliente AA8 |
|---|---|:---:|:---:|:---:|
| Triple Slash | `18132/18134/18131`, `36401–36406` | cerrado | PASS raíz; Lightning `36401→36402→36403` completa la admisión en 500 ms con GCD real; Quake también PASS | **PASS etapa 1: base y variantes con cadencia/animación correctas** |
| Charge | `11918`, auxiliar `12028` | cerrado | PASS daño/carga/knockback; cooldown nace al aceptar cast; buffs no-toggle publican `toggleSkill=0` | **PASS etapa 1: expiraciones no reinician cooldown** |
| Battle Focus | `10377` | cerrado | PASS buff propio | **PASS etapa 1** |
| Whirlwind Slash | `13282`, internas `32040/32049` | cerrado | PASS plot/AoE; tres etapas y dos continuaciones admitidas en 635 ms con GCD real | **PASS etapa 1: tres etapas fluidas** |
| Sunder Earth | `10644`, `41217/41218` | cerrado | PASS raíz, Flame y Quake | **PASS etapa 1** |
| Frenzy | `10455`, `43188/43189` | cerrado | PASS raíz, Flame y Wave | **PASS etapa 1: buff/lifecycle funcional** |
| Precision Strike | `12026`, `36446/36447` | cerrado | PASS; `36446` daño tras combat-sync 642 ms | **PASS etapa 1: daño sincronizado** |
| Tiger Strike | `13315`, `36448/36449` | cerrado | PASS; Lightning 3 impactos en 640 ms | **PASS etapa 1: tres impactos fluidos** |
| Bondbreaker | `12034` | cerrado | PASS liberación | **PASS etapa 1** |
| Terrifying Roar | `18308` | cerrado | PASS control | **PASS etapa 1** |
| Ollo's Hammer | `18757`, plot `440` | cerrado | PASS target/plot/daño; V4 `SCPlotEvent(3480, POSITION)` sin fire directo | **PASS etapa 1: martillo correcto y sincronizado** |
| Behind Enemy Lines | `23587`, `39661/39662` | cerrado | PASS; Gale reduce Charge 2 s por objetivo distinto | **PASS etapa 1** |

## Automáticas y pasivas

Las automáticas `34124`, `34119` y `34120` están presentes como skills
visibles de costo cero, con sus consumidores y relaciones nativas. Las seis
pasivas tienen identidad exacta y buffs alcanzables:

| Pasiva | Buff AA8 | Puntos | Contrato de datos |
|---:|---:|---:|:---:|
| `32` | `2610` | 3 | PASS |
| `245` | `7542` | 4 | PASS |
| `92` | `2621` | 5 | PASS |
| `29` | `811` | 6 | PASS; partición histórica incompatible retirada |
| `295` | `831` | 7 | PASS; modificador nativo retenido |
| `244` | `7544` | 8 | PASS |

Las tres automáticas y seis pasivas quedan aceptadas en el alcance funcional
de primera etapa. Una futura etapa de robustecimiento puede ampliar la matriz
de persistencia/relog, combinaciones de arma y observación desde otro cliente;
esa frontera no invalida los efectos principales ya aceptados.

## Matriz headless permanente

Se ejecutaron 24 escenarios Battlerage en dos directorios limpios. Resultado:
`24/24 PASS` y `24/24 ResultSha256` idénticos entre ambas corridas. Cubren:

- cadena de tres golpes, variantes ancestrales y retrasos de plot;
- daño melee, AoE, buffs propios, controles, liberación y knockback;
- selección AA8 de target `Area` y `RandomUnit`;
- cargas y desplazamiento de caster/target;
- cooldown, mana, GCD, reloj y scheduler deterministas;
- orden plaintext/wire, contador DD05 y ausencia de excepciones.

Regresiones cruzadas sobre la misma compact:

- cuatro escenarios Archery/muerte de NPC: `4/4 PASS`;
- wrap DD05, wrap concurrente y 15 segundos de tareas tardías: PASS;
- suite .NET Core 3.1: `600/600 PASS`;
- validador estructural Battlerage V2: `9/9 PASS`;
- regresión de artefactos Phase 4: `6/6 PASS`.

La certificación versionada
`generated/battlerage-v2-mechanics-certification.json` resume los 24 hashes
idénticos con SHA-256
`C4A5DC628D1645915C0CDC730DC33FA112F958CA54AA04AB45E2428F12B22693`.

## Primitives cerradas durante V2

- `Cooldown`, `ManaCost`, `GlobalCooldown`, `StopManaRegen` y
  `CancelStealth` usan el reloj/estado genérico y no hacks por skill ID.
- `KnockBack` y selección de área funcionan tanto en producción como en el
  contexto manual del Lab.
- `PlotTargetRandomUnit` consume las columnas nativas AA8 `param7/8/9` para
  `hit_once`, relación y flags de unidad.
- un target `Area` de volumen cero materializa una posición sintética con la
  transformación del target anterior; este contrato de presentación nativo
  repara Ollo's Hammer sin una excepción por ID.
- las esferas AA8 de radio cero pueden resolver el radio específico del evento
  desde `param6`, sin mutar el catálogo compartido.
- visibilidad y mundo en memoria sólo se sustituyen cuando existe un contexto
  `MechanicsRuntime`; producción conserva regiones, Quartz y sockets reales.
- el Lab registra selección/aplicación de efectos y cálculo/descartes de daño,
  de modo que un `PASS` no dependa sólo de que el cast haya sido aceptado.
- los tiempos de fase de doodads usan `MechanicsRuntime.UtcNow`; producción
  conserva el reloj real y el Lab serializa `TimeLeft` de forma determinista.

## Cierre vivo de primera etapa

El usuario confirmó el cierre funcional y visual de primera etapa para toda la
rama. El detalle, la comparación con Sorcery/Archery y los hallazgos promovidos
están en `CHECKPOINT_BATTLERAGE_STAGE1_CLOSURE_V10.md`.

Una etapa posterior de robustecimiento, si se abre, debe ampliar sin borrar
esta evidencia:

1. persistencia/relog y cambio de especialización repetidos;
2. combinaciones de arma, latencia y targets no cubiertas en etapa 1;
3. observación desde segundo cliente;
4. soak prolongado con muerte y cambio de zona.
