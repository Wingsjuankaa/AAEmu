# Battlerage V6 — cadencia nativa de cadenas Combo AA8

Fecha: 2026-08-09  
Cliente autoritativo: Kakao `8.0.3.12 r558734`  
Compact activa: `compact-8.0-runtime-battlerage-v5.sqlite3`  
SHA-256: `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`

## Síntoma y reproducción viva

Triple Slash: Lightning (`36401 → 36402 → 36403`) y Whirlwind Slash
(`13282 → 32040 → 32049`) ejecutaban correctamente sus tres golpes, pero cada
continuación pagaba un retraso artificial de aproximadamente 500 ms.

La traza viva `runtime-captures/packet-traces/aa8-game-20260809-232037179-session-1505492601.jsonl`
aisló el patrón:

- Lightning: el cliente pidió `36402` 283 ms después de `36401` y `36403`
  217 ms después de `36402`; ambos primeros intentos fueron rechazados con
  `CooldownTime`, y el reintento aceptado llegó unos 500 ms más tarde;
- Whirlwind: el cliente pidió `32040` a 294 ms y `32049` a 335 ms; ambos
  primeros intentos sufrieron el mismo rechazo y reintento tardío;
- no había demora pendiente en el plot de Whirlwind: cada plot cerraba en
  pocos milisegundos. El bloqueo era el GCD autoritativo.

## Autoridad nativa

El compact AA8 contiene `83` descriptores efectivos `SpecialEffect type 48
(Combo)`. Todos tienen `chance=100` y una ventana explícita de `1000`, `1500`,
`2000`, `3000` o `5000` ms. Las relaciones relevantes son:

| Origen | Siguiente | Ventana |
|---|---:|---:|
| `36401` | `36402` | 1000 ms |
| `36402` | `36403` | 1000 ms |
| `13282` | `32040` | 1500 ms |
| `32040` | `32049` | 1500 ms |

La función nativa AA8 `FUN_39899660` consume estos descriptores para que el
cliente seleccione y solicite el siguiente skill. El servidor no debe lanzar
el hijo: debe admitir esa petición ordinaria como continuación de la cadena.

Los nombres históricos de dos fixtures estaban intercambiados. La autoridad
coreana confirma que `36401–36403` es **Lightning** (`3단 베기: 번개`) y
`36404–36406` es **Quake/Earthquake** (`3단 베기: 지진`). Se conserva por
compatibilidad el filename histórico `battlerage_triple_slash_ancestral_flame`,
pero el builder deja documentado que prueba Lightning.

## Reparación transversal

Cada `Unit` mantiene un conjunto concurrentemente protegido de transiciones
Combo con skill origen, `TlId`, skill siguiente y expiración. Al aceptar un
cast:

1. se evalúan los descriptores type 48 cargados en `SkillTemplate.Effects`;
2. se respetan nivel, relación, frente/espalda y tags de buff de origen y
   objetivo;
3. la nueva skill reemplaza el estado de cadena anterior;
4. sólo la skill siguiente exacta y dentro de ventana puede omitir el GCD;
5. la transición se consume atómicamente; alternativas de la misma fuente se
   invalidan al elegir una.

La excepción Combo conserva el guard de peticiones de 150 ms y omite sólo el
GCD para el ID exacto registrado por la transición nativa. Conserva requisitos,
rango, cooldown propio, mana y validación de objetivo. La continuación
aceptada aplica normalmente su propio GCD y registra su siguiente descriptor.
No existen allow-lists ni excepciones codificadas por ID.

## Regresión determinista

Se añadió `enforce_gcd` al Mechanics Lab. Su valor por defecto conserva los
fixtures anteriores; los escenarios de cadena lo activan para que el Lab ya
no oculte esta clase de error con `bypassGcd=true`.

- Triple Slash Lightning: `36401@0 ms`, `36402@283 ms`, `36403@500 ms`;
  tres resultados `Success`, dos `combo_continuation_admitted`.
- Whirlwind Slash: `13282@0 ms`, `32040@300 ms`, `32049@635 ms`;
  tres resultados `Success`, dos `combo_continuation_admitted`.
- Quake: los tres pasos también pasan con GCD real y su ventana nativa de
  2000 ms.
- `SkillComboTransitionTests`: bypass limitado al GCD para el siguiente ID
  exacto, guard de 150 ms para todas las solicitudes,
  expiración, skill no relacionada, reemplazo y consumo de alternativas.

El compact no cambia: la relación ya estaba reconstruida correctamente. La
corrección pertenece exclusivamente a la admisión transversal del runtime.
El patrón queda promovido para reparaciones futuras en
`../shared_primitives/CHECKPOINT_AA8_COMBO_GCD_ADMISSION_V1.md`.

## Cierre automatizado y despliegue candidato

- suite .NET 3.1: `624/624 PASS`;
- Mechanics Lab Battlerage: `25/25 PASS`, `suite_failed=0`;
- validadores Battlerage: `11/11 + 6/6 PASS`;
- documentación y primitivas compartidas: `4/4 + 4/4 PASS`;
- SQLite: `quick_check=ok`, `integrity_check=ok`;
- rollback: `aaemu-game:rollback-pre-aa8-combo-cadence-20260809`;
- imagen desplegada: `sha256:756dfb8b2045abdf5a51ea957de30717a822d45c8edef12ac3032f6d108bde64`;
- `AAEmu.Game.dll` SHA-256:
  `4C3A65B058C23E07463B19A7CDED6096189100EA4D0CE9D602749AA207B5E528`;
- sólo se recreó `game`; `login` y `db` conservaron sus contenedores;
- compact V5 montada read-only con el SHA esperado;
- scripts `0 errors`, puertos `2239/2250`, registro exitoso en LoginServer y
  `RestartCount=0`.

El gate visual posterior confirmó Lightning subsegundo y Whirlwind sin la
pausa del retry. Las iteraciones V7–V9 de este mismo dossier preservan además
la regresión cruzada y el contrato final de `auto_fire`.

## Enmienda V7 falsificada y baseline restaurada (2026-08-09)

La captura de Endless mostró requests exactos a 50–148 ms. Permitir que Combo
omitiera también el guard eliminó los rechazos, pero la prueba visual posterior
mostró que aceleraba todas las cadenas. Los logs confirmaron impactos Endless
aceptados cada 47–103 ms pese a `custom_gcd=220`.

Se restaura la baseline V6 solicitada: guard de 150 ms primero y excepción
Combo sólo para el GCD. Cooldown propio, requisitos, rango, recursos y
validación del objetivo permanecen sin bypass.

- evidencia live: rechazos reproducidos a `50/52/100/101/148 ms`;
- fixture permanente: preserva la cadena completa sin declarar 50 ms como
  cadencia nativa;
- .NET 3.1: `624/624 PASS`;
- Mechanics Lab: Endless PASS y Battlerage `25/25 PASS`;
- validadores estructurales: Battlerage `11/11 + 6/6`, Archery `17/17`;
- compact sin cambios, SHA-256
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`.
- despliegue sólo de `game`: imagen
  `sha256:1cb54e2db695dbc3f4bb8d9d4756437c5c839e73e7ee98c02b918f2049e66915`,
  DLL
  `976F118961D017AC555013C67C4493C6C8C45BA23D72B2720EFCA0D2FC66D267`;
- scripts `0 errors`, puertos `2239/2250`, registro exitoso en LoginServer y
  `RestartCount=0`.

### Estado actual: baseline restaurada para comparación visual

- suite .NET 3.1 `624/624`, Endless PASS, Battlerage `25/25`;
- imagen `sha256:4a21782cdeae17a359fecca7d04f41767f7701fad2f46bdf4d86fb93a054d55f`;
- DLL `4E9B8E0656DEE6A38B7D21157A9DDCA353BC02AEE519BBC3141FCF44DD6ADC84`;
- compact V5 sin cambios; sólo se recreó `game`.

## Enmienda V8 falsificada: replay diferido de Endless

V8 reservó requests tempranos y los ejecutó desde un callback del servidor. La
suite fue verde, pero la prueba viva demostró que el cliente continuaba enviando
su propio `auto_fire`. Los dos productores se adelantaban mutuamente: aparecen
callbacks `[AA8ComboCadence] Executing` intercalados con requests del socket y
saltos de TlId `3844→3847` y `3871→3887`. La cadencia resultante fue errática.

Esta versión queda preservada sólo como evidencia negativa:

- suite .NET 3.1 `627/627` y tests dirigidos de admisión `8/8`;
- Mechanics Lab Endless PASS y Battlerage `25/25`, `suite_failed=0`;
- validadores Battlerage `11/11 + 6/6`, Archery `17/17`;
- SQLite `quick_check=ok`, `integrity_check=ok`;
- rollback: `aaemu-game:rollback-pre-endless-cadence-v8-20260809`;
- despliegue sólo de `game`: imagen
  `sha256:87308ec296565aee563ab1aeefb269ac95f61abcdc28c8789ad32026e64681ad`,
  DLL `B8918096E56F23D6E9A8E668F1EC8A34CEB9278135042E2816110A1796FD1C34`;
- compact V5 montada con SHA esperado, scripts `0 errors`, puertos
  `2239/2250`, registro exitoso en LoginServer y `RestartCount=0`.

La imagen fue etiquetada
`aaemu-game:failed-endless-cadence-v8-20260809` y se restauró inmediatamente
`sha256:4a21782cdeae17a359fecca7d04f41767f7701fad2f46bdf4d86fb93a054d55f`.
Regla promovida: un loop `auto_fire` del cliente no puede tener un replay
paralelo en el servidor aunque el timer use datos AA8 correctos.

## Candidato V9: feedback nativo con autoridad única

La regresión histórica estaba en la supresión global de
`SCSkillStarted(CooldownTime)` añadida para impedir que Charge reiniciara su
timer visual. Las capturas Endless anteriores a esa supresión mostraban esos
rechazos intercalados con una continuidad visual aceptada.

V9 mantiene el cast exclusivamente en el cliente. Sólo devuelve el rechazo
nativo cuando hay transición type 48 exacta y viva, `auto_fire=1`,
`effect_repeat_tick>0` y cero cooldown propio. Triple Slash/Whirlwind quedan
fuera por `effect_repeat_tick=0`; Charge y cualquier timer real quedan fuera por
la comprobación autoritativa de cooldown. No existe callback, cola ni cast
sintético.

- tests dirigidos `8/8`;
- suite .NET 3.1 `627/627`;
- Mechanics Lab Endless PASS, hash
  `4C3FABEF40F81A6BE2AED2343BADE273BE2A01B916CDC738C77D7F3F1806A4D1`;
- imagen candidata
  `sha256:8dd98d44d5d814e95509a297e007dbccf0073fc969a3b2898f174420cc8119ac`,
  DLL `B8C90AB0374D4CC56F495FAE8CBE30A6D25DEEA931E985F8F77CE6BF41CD3B3C`;
- rollback `aaemu-game:rollback-pre-endless-feedback-v9-20260809`;
- sólo se recreó `game`, compact V5 con SHA esperado, scripts `0 errors`,
  puertos `2239/2250`, registro en LoginServer y `RestartCount=0`;
- gate visual aceptado por el usuario: Endless Arrows recuperó continuidad
  fluida; la traza viva alterna `clientOwnedRepeat=True` con casts `Success`
  monotónicos (`tlId 756→757→758→759…`) y no contiene callbacks
  `[AA8ComboCadence]`.

## Cierre posterior: V6-V9 retiradas del runtime

Este dossier se conserva como evidencia negativa e historial de la regresión,
pero su sistema de admisión no es ya arquitectura activa. Al incorporar
Battlerage se había invertido globalmente el orden de `PlotNode`; los bypasses
Combo y clasificadores `auto_fire` sólo compensaban parcialmente esa mutación y
terminaron dañando Endless Arrows y Flamebolt de manera alternada.

La resolución final restaura el orden del control positivo `835b42e1` y elimina
del runtime las transiciones Combo de servidor, el feedback especializado, el
guard variable, `auto_fire` como propiedad ejecutable y el batch global de
plots. También se retiró `enforce_gcd` de Mechanics Lab y se restauraron los
fixtures Battlerage previos a esa instrumentación. Los timings nativos del
motor de plots y la autoridad real de cooldown permanecen separados y activos.

Para futuras ramas, no promover una mejora visual de una cadena a regla global
sin ejecutar primero los controles vivos de Sorcery, Archery y Battlerage. En
particular, un fixture que invoca manualmente cada ID no demuestra que el
cliente vaya a seleccionar ni solicitar la continuación.
