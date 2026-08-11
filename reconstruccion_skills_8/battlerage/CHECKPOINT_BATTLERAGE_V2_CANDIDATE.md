# Checkpoint Battlerage V2–V9 — historial del candidato desplegado

Fecha: 9 de agosto de 2026.

## Baseline preservado

- Rama: `client_version/8.0.3.12-kakao-r558734-port`.
- Checkpoint previo: commit `835b42e1`.
- Rollback Docker: `aaemu-game:rollback-pre-aa8-battlerage-v2-20260808`.
- Sorcery, Archery, Mechanics Lab y muerte de NPC permanecen como regresiones
  obligatorias.

## Evidencia y construcción

- Grafo forense Battlerage: SHA-256
  `54736AFC8CDC453C84FFA4C8337C76894FA86D78155E714B1B121B5B640589B5`.
- Crosswalk AA8→10.x consultado obligatoriamente: SHA-256
  `44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71`.
- El crosswalk redujo opacidad de identidad/relación, pero no promovió datos:
  `aa10_runtime_rows=0`.
- Clausura nativa: 42 skills, 37 raíces/variantes jugables, 3 automáticas,
  2 internas obsoletas, 6 pasivas, 115 skill effects, 18 plots y 64 buffs.
- Único controller ausente: `604`, exclusivo de la skill obsoleta oculta
  `11854`; no bloquea contenido jugable.

Constructor reproducible:

```text
reconstruccion_skills_8/battlerage/build_battlerage_runtime_v2.py
```

Compact resultante:

```text
D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-battlerage-v2.sqlite3
SHA-256 54DD8C77556A35C3EECE4009A6FC713179F72054DD4E50A6DBA08B74533ABF3A
size 141148160
quick_check ok
integrity_check ok
```

La copia de verificación produjo exactamente el mismo SHA-256.

## Verificación

- Mechanics Lab Battlerage: `24/24 PASS`.
- Segunda corrida: `24/24` hashes de resultado idénticos.
- Regresiones Archery/muerte: `4/4 PASS`.
- Suite .NET Core 3.1 con esta compact montada: `600/600 PASS`.
- Tests estructurales V2: `9/9 PASS`.
- Tests Phase 4: `6/6 PASS`.
- Certificación determinista versionada: SHA-256
  `C4A5DC628D1645915C0CDC730DC33FA112F958CA54AA04AB45E2428F12B22693`.

Los resultados están en:

```text
runtime-captures/mechanics-lab/battlerage-v2-final/certified-a
runtime-captures/mechanics-lab/battlerage-v2-final/certified-b
runtime-captures/mechanics-lab/battlerage-v2-final/archery-regression
```

El resumen auditable y reproducible está en
`generated/battlerage-v2-mechanics-certification.json`; las capturas completas
permanecen fuera de Git.

## Despliegue

- Imagen: `aaemu-game:0.0.2.0-alpha`.
- Imagen SHA vigente: `sha256:db32fceab464734690770b4b431d2343fbf32908bc94480151062e32057a583d`.
- DLL desplegada SHA-256:
  `0E86C372AC11A86ED5A372562C722442CB08F712CBE96E1E6556AFCEE4CF2139`.
- Compact dentro del contenedor: SHA esperado `54DD8C...ABF3A`.
- Puertos `2239` y `2250`: accesibles.
- Scripts: `0 errors`, 8 warnings heredados.
- LoginServer: `Registered GameServer 1`.
- Sólo se recreó `aaemu8-game-1`; Login y MySQL conservaron sus IDs.

## Estado

Este archivo conserva el historial cronológico del candidato, sus hotfixes y
las hipótesis falsificadas. El cierre vivo de primera etapa fue aceptado al
final de V9 y se resume en
`CHECKPOINT_BATTLERAGE_STAGE1_CLOSURE_V10.md`.

## Bloqueo previo de interacción con NPC (2026-08-09)

Las pruebas vivas quedaron bloqueadas por una desconexión correlacionada `2/2`
con `CSInteractNPC` sobre Temple Priestess (`template_id=502`). Se restauró el
acuse vacío de interacción al canal DD05/nivel 5 esperado por AA8 sin cambiar
el aggro ordinario de nivel 1. El candidato actualizado supera `601/601`
pruebas y está desplegado. La aceptación viva fue `PASS` el 2026-08-09 y el
bloqueo quedó cerrado, según
`../shared_primitives/CHECKPOINT_AA8_NPC_INTERACTION_CHANNEL_V1.md`.

## Correcciones base posteriores al primer barrido vivo (2026-08-09)

El primer barrido de Battlerage detectó dos regresiones transversales y una
condición de prueba independiente:

- `Buffs.AddBuff` no aplicaba la exclusión nativa por `group_id/group_rank`.
  Las etapas `242/514/515/516/517` de Bleeding (grupo 10, rangos 1..5)
  coexistían, conservaban varios triggers y podían realimentarse. El runtime
  ahora rechaza una etapa inferior y reemplaza los miembros distintos del
  mismo grupo al avanzar; la regla de stack sigue gobernando reaplicaciones
  del mismo `buff_id`.
- Ollo's Hammer `18757` conserva sin diferencias su skill, plot `440`, evento
  visual `3480`, `ProjectileAnim 7742`, projectile `308` y FX `1194/1195`
  respecto de Phase 4. El ledger headless también es idéntico al certificado,
  por lo que no se alteró el wire sin evidencia AA8. Se añadió trazabilidad
  explícita al evento `3480`; la presentación del proyectil sigue requiriendo
  validación visual viva después de eliminar el fan-out de Bleeding.
- Los saltos visuales de cooldown coincidieron exactamente con el modo GM
  temporal `IgnoreSkillCooldowns=true`: la traza registró
  `SCSkillCooldownResetPacket` para cada skill y cada tag de cooldown. No se
  alteró el paquete AA8 ni el balance; al reiniciar únicamente `game` la
  propiedad vuelve a su valor de producción `false`.

La compact continúa inalterada con SHA-256
`54DD8C77556A35C3EECE4009A6FC713179F72054DD4E50A6DBA08B74533ABF3A`.
Las pruebas dirigidas pasan `8/8` y la suite completa, montando la compact
Battlerage V2 como runtime ancestral, pasa `602/602`. Queda pendiente la
confirmación visual del martillo, una única etapa de Bleeding y cooldowns
monótonos con el cliente AA8.

## Enmienda V3: presentación de Hammer Toss (2026-08-09)

La evidencia viva confirmó que la mecánica de Hammer Toss `18757` estaba
cerrada, pero el cliente no materializaba el `ProjectileAnim 909` del evento
`3480`. AA8 declara además el projectile directo `308` en la propia skill. La
compact V3 añade una política server-derived explícita únicamente para la
presentación: el servidor emite `SCSkillFired` antes del plot y mantiene el
plot como única autoridad de daño, stun, buffs, cooldown y finalización. No se
ejecutan ni duplican los `skill_effects` directos.

- Compact: `compact-8.0-runtime-battlerage-v3.sqlite3`.
- SHA-256: `C0CC6BC985C3E8939F74E565AEAE626E33DD0D7BA72EEA5784E820CB276D851D`.
- Dos builds byte a byte idénticos; `quick_check=ok` e `integrity_check=ok`.
- Política activa: `server_plot_only_fire_presentation=1` sólo para `18757`.
- Validador estructural V3: `10/10 PASS`.
- Suite .NET Core 3.1: `604/604 PASS`.
- Mechanics Lab `battlerage_ollos_hammer`: PASS, daño una sola vez,
  `SCSkillFired → SCPlotEvent → SCUnitDamaged → SCBuffCreated → SCPlotEnded`,
  sin excepciones; resultado
  `456517BAB1793526591450D87FBA01ED35AE119629DDE0A936A93A76C7D81FD5`.

La comprobación visual posterior demostró que esta enmienda no era nativa: el
`SCSkillFired` directo materializaba el projectile `308` demasiado pronto y
fuera de sincronía con la animación. La evidencia histórica confirmó que el
FX correcto ya funcionaba antes de la reconstrucción Battlerage V2.

## Enmienda V4: restauración del contrato posicional de Hammer Toss (2026-08-09)

La regresión estaba en la semántica del plot, no en los assets. El evento
`28784` (`target_update_method_id=5`) debe producir un `PlotObject` de tipo
posición. Battlerage V2 conservaba en su lugar la identidad de la unidad y
cambiaba el contrato que recibe el `ProjectileAnim 909` del evento `3480`.
V4 restaura la ruta aprobada anterior a Battlerage:

- `SCPlotEvent` es la única autoridad de presentación;
- no se emite un `SCSkillFired` directo para skills `plot_only`;
- el objetivo intermedio vuelve a ser una posición con la transformación del
  objetivo real;
- daño, stun, buffs, cooldown y cierre siguen perteneciendo al plot `440`.

- Compact: `compact-8.0-runtime-battlerage-v4.sqlite3`.
- SHA-256: `A244EBEDB2CB58E1E09830650539C97FD77E2EBC077027067563414BC03DA262`.
- Dos builds byte a byte idénticos; `quick_check=ok` e `integrity_check=ok`.
- Cero filas 10.x promovidas y cero política server-derived por ID.
- Mechanics Lab `battlerage_ollos_hammer`: PASS. El ledger confirmado es
  `SCPlotEvent(3480, POSITION) -> SCUnitDamaged -> SCBuffCreated -> SCPlotEnded`,
  sin `SCSkillFired` directo ni excepciones; resultado SHA-256
  `9CB3B97A7D5B83AF4D554750EA7F0CB62C440329F0DAD65601C0E5E458ACE358`.
- Suite .NET Core 3.1 contra la compact V4: `602/602 PASS`.
- Despliegue: sólo `game`, imagen
  `sha256:2d5da070a62f8367ef033dc80611c708ac790723c94c3c6014cfe78f14b64c9b`,
  DLL SHA-256
  `DCDA7CEFA6550893070305C42637EC8B4783B6D9090997002CB9B98BD96D8A7E`,
  compact montada con el SHA esperado, scripts `0 errors`, puertos
  `2239/2250` y registro exitoso en LoginServer.
- Aceptación visual AA8 real: **PASS**. Hammer Toss volvió a mostrar el
  martillo nativo sincronizado con el gesto, el impacto, el stun y el daño.

## Cierre visual de Hammer Toss y hallazgo reusable (2026-08-09)

La prueba viva cerró la última incertidumbre de Ollo's Hammer/Hammer Toss
`18757`. La presentación correcta no depende del projectile directo `308`:
depende de conservar el objetivo **posicional** que el evento intermedio
`28784` entrega al `SCPlotEvent 3480`, consumidor de `ProjectileAnim 909`.

La secuencia aprobada es:

`plot_only skill -> target Area posicional -> SCPlotEvent(3480, POSITION) -> daño/buff -> SCPlotEnded`

No debe insertarse `SCSkillFired` para “ayudar” al cliente. Esa alternativa
materializa el projectile directo demasiado pronto, usa otra familia de FX y
desincroniza presentación y resultado autoritativo. El descubrimiento queda
promovido al checkpoint compartido
`../shared_primitives/CHECKPOINT_AA8_PLOT_ONLY_POSITIONAL_PRESENTATION_V1.md`
y a la guía transversal de reconstrucción de ramas.

## Enmienda V5: cooldown autoritativo y combat-sync transversal (2026-08-09)

V5 separa inicio, reducción y reset de cooldown; reconstruye los paquetes AA8
`0x038/0x34D`; materializa Behind Gale `39661 → 11918 -2000 ms/objetivo`;
elimina el doble conteo arista/controlador; y resuelve combat-sync por perfil.
Bleeding conserva el proc nativo de 5 %, ahora trazable, y sus rangos siguen
siendo mutuamente excluyentes.

- Compact: `compact-8.0-runtime-battlerage-v5.sqlite3`.
- SHA-256: `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`.
- Builds A/B idénticos; SQLite `quick_check=ok`, `integrity_check=ok`.
- Behind Gale: Charge efectivo `12→10→8→6 s` con tres objetivos.
- Tiger Lightning: tres impactos; primero→tercero `640 ms`.
- Precision `36446`: visual a `0 ms`, daño tras combat-sync a `642 ms`.
- Dossier: `BATTLERAGE_COOLDOWN_TIMING_V5_AA8.md`.
- Pruebas: `24/24` dirigidas .NET 3.1, `11/11` estructurales y `25/25`
  escenarios Battlerage efectivos del Mechanics Lab.
- Despliegue: sólo `game`, imagen
  `sha256:34936759439268969350882608d953838c64711a390ee3754a97f131bfc7a0f8`,
  DLL SHA-256
  `9751783962D7CD50AE27667F9D1D66BACF771A386CBA12DAD6C4E76830FE3DAA`,
  compact montada con el SHA esperado, scripts `0 errors`, puertos
  `2239/2250` y registro exitoso en LoginServer.
- Pendiente de aceptación manual: captura live del cliente AA8 con paquetes y
  timestamps; no se atribuye evidencia visual sin una sesión conectada.
- Hotfix live: la desconexión al entrar fue causada por promover desde Modern
  el transporte nivel 1 de `SCCooldowns 0x34D`. AA8 exige nivel cifrado 5. El
  mismo guardrail se aplicó preventivamente a `SCSkillCooldownReduce 0x038`.
- Hotfix live de Charge `11918`: tres capturas aisladas demostraron que el
  contador se reiniciaba al recibir `SCPlotEnded`, entre `406` y `417 ms`
  después del lanzamiento. Las skills `plot_only` ahora inician cooldown al
  aceptar el cast; el cierre del plot no lo reinicia ni emite un snapshot
  masivo. Los rechazos transitorios de cooldown/GCD se
  silencian para no abrir otro ciclo visual. Imagen desplegada
  `sha256:515dfdca79611cbee82674cc3958dc58e38c317e7e0e0e71b4d2b81145aaa067`,
  DLL `D70A54F37DB09C22232CEC4501B4E3AA6092B97C3D37C976E0409EB8DDB1A6D8`;
  pendiente confirmación visual final del cliente.
- Regresión final localizada en `835b42e1`: `SCBuffCreated 0x36C` promovió el
  campo `s` desde vínculo de toggle a skill origen universal. Como Charge no
  es toggle, sus buffs `7543/11344/22627` deben enviar `s=0`; vincularlos a
  `11918` hace que el cliente vuelva a materializar 12 segundos cuando salen.
  Se restauró `s=skillId` sólo si `skill.toggle_buff_id == buff.id`, sin perder
  el `stack` AA8. Suite .NET 3.1 `619/619`; Mechanics Lab Charge y Behind Gale
  PASS. Despliegue sólo de `game`: imagen
  `sha256:6e7f05407ff5b76670960c03b5217686917fa185bb9761738e3b198621548a71`,
  DLL `C350439F3D0877946E9216A4AB1C559E70AA589755EF1B5AC688E1F82C6111B8`,
  compact V5 con SHA esperado y `RestartCount=0`. Aceptación visual AA8:
  **PASS**; las expiraciones de `7543/11344` ya no alteran Charge. Antecedente
  transversal:
  `../shared_primitives/CHECKPOINT_AA8_BUFF_CREATED_TOGGLE_LINK_V1.md`.

## Enmienda V6: admisión nativa de continuaciones Combo (2026-08-09)

Las trazas vivas de Triple Slash: Lightning `36401→36402→36403` y Whirlwind
Slash `13282→32040→32049` demostraron que el cliente solicitaba cada
continuación a tiempo, pero el servidor rechazaba el primer intento por el GCD
activo. El reintento del cliente unos 500 ms después producía la lentitud.

El runtime ahora consume transversalmente los descriptores AA8
`SpecialEffect type 48 (Combo)`: registra la skill siguiente y su ventana al
aceptar el origen, y permite que sólo esa continuación omita el GCD. La
enmienda live de Endless Arrows que omitía también el guard fue falsificada
por cadencia excesiva; el guard de 150 ms vuelve a aplicar a todos. Cooldown propio,
requisitos, rango y consumo permanecen intactos. No
se introdujeron excepciones por ID ni se alteró la compact V5.

- catálogo AA8 activo: 83 descriptores type 48, todos deterministas;
- Lightning: admisiones a `0/283/500 ms`, tres `Success`;
- Whirlwind: admisiones a `0/300/635 ms`, tres `Success`;
- Quake `36404→36405→36406`: PASS con GCD real;
- dossier: `BATTLERAGE_COMBO_CADENCE_V6_AA8.md`.
- suite .NET 3.1 `623/623`, Mechanics Lab Battlerage `25/25`, validadores
  estructurales `17/17`, SQLite `quick_check/integrity_check=ok`;
- despliegue sólo de `game`: imagen
  `sha256:756dfb8b2045abdf5a51ea957de30717a822d45c8edef12ac3032f6d108bde64`,
  DLL `4C3A65B058C23E07463B19A7CDED6096189100EA4D0CE9D602749AA207B5E528`,
  compact V5 con SHA esperado, scripts `0 errors`, puertos `2239/2250`,
  registro exitoso y `RestartCount=0`.

## Enmienda V7 falsificada: guard y Endless Arrows (2026-08-09)

Endless Arrows reveló requests type 48 anteriores a 150 ms. Interpretarlos
como velocidad autorizada fue incorrecto: la sesión posterior aceptó impactos
cada 47–103 ms aunque las filas declaran `custom_gcd=220`. Se restaura la
baseline V6: guard de 150 ms para toda solicitud y bypass sólo del GCD para la
transición exacta. La cadencia AA8 definitiva y el coalescing de requests
tempranos quedan separados de esta comparación visual.

- suite .NET 3.1 `624/624`;
- Mechanics Lab Endless PASS y Battlerage `25/25`;
- validadores Battlerage `11/11 + 6/6`, Archery `17/17`;
- compact V5 sin cambios, SHA-256
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- rollback previo: `aaemu-game:rollback-pre-endless-combo-20260809`.
- despliegue sólo de `game`: imagen
  `sha256:1cb54e2db695dbc3f4bb8d9d4756437c5c839e73e7ee98c02b918f2049e66915`,
  DLL
  `976F118961D017AC555013C67C4493C6C8C45BA23D72B2720EFCA0D2FC66D267`;
- scripts `0 errors`, puertos `2239/2250`, registro exitoso y
  `RestartCount=0`.

Baseline restaurada para comparación visual:

- suite .NET 3.1 `624/624`, Endless PASS, Battlerage `25/25`;
- imagen `sha256:4a21782cdeae17a359fecca7d04f41767f7701fad2f46bdf4d86fb93a054d55f`;
- DLL `4E9B8E0656DEE6A38B7D21157A9DDCA353BC02AEE519BBC3141FCF44DD6ADC84`;
- compact V5 sin cambios; sólo se recreó `game`.

## Enmienda V8 falsificada: coalescing de Endless Arrows (2026-08-09)

La baseline restaurada fue aprobada visualmente para Triple Slash, pero V8
intentó reparar Endless reservando y reejecutando la petición anticipada desde
el servidor. El cliente mantuvo su propio `auto_fire`; ambas autoridades se
intercalaron y generaron saltos de TlId (`3844→3847`, `3871→3887`) y cadencia
errática. El resultado vivo invalida el diseño aunque todas las pruebas fueran
verdes.

- suite .NET 3.1 `627/627`, tests dirigidos Combo `8/8`;
- Mechanics Lab Endless PASS y Battlerage `25/25`;
- validadores Battlerage `11/11 + 6/6`, Archery `17/17`;
- SQLite `quick_check/integrity_check=ok` y compact V5 sin cambios;
- rollback `aaemu-game:rollback-pre-endless-cadence-v8-20260809`;
- imagen desplegada
  `sha256:87308ec296565aee563ab1aeefb269ac95f61abcdc28c8789ad32026e64681ad`;
- DLL `B8918096E56F23D6E9A8E668F1EC8A34CEB9278135042E2816110A1796FD1C34`;
- sólo se recreó `game`; scripts `0 errors`, puertos `2239/2250`, registro
  exitoso en LoginServer y `RestartCount=0`.

La imagen queda etiquetada
`aaemu-game:failed-endless-cadence-v8-20260809`. Se restauró la baseline
`sha256:4a21782cdeae17a359fecca7d04f41767f7701fad2f46bdf4d86fb93a054d55f`
y se eliminó del árbol toda cola, callback y replay de Combo.

## Candidato V9: feedback nativo sin segunda autoridad (2026-08-09)

La corrección de Charge había suprimido globalmente las respuestas
`SCSkillStarted(CooldownTime)`. Las capturas antiguas de Endless demostraron que
su loop cliente sí dependía de esos rechazos transitorios. V9 restaura el
feedback sólo si coinciden transición type 48 exacta, `auto_fire=1`,
`effect_repeat_tick>0` y cooldown propio igual a cero. El servidor nunca vuelve
a crear el cast.

- Triple Slash y Whirlwind: excluidos por `effect_repeat_tick=0`;
- Charge y demás timers reales: excluidos por cooldown autoritativo;
- tests dirigidos Combo `8/8`, suite .NET 3.1 `627/627`;
- Mechanics Lab Endless PASS, hash
  `4C3FABEF40F81A6BE2AED2343BADE273BE2A01B916CDC738C77D7F3F1806A4D1`;
- despliegue sólo de `game`: imagen
  `sha256:8dd98d44d5d814e95509a297e007dbccf0073fc969a3b2898f174420cc8119ac`,
  DLL `B8C90AB0374D4CC56F495FAE8CBE30A6D25DEEA931E985F8F77CE6BF41CD3B3C`;
- rollback `aaemu-game:rollback-pre-endless-feedback-v9-20260809`;
- compact V5 SHA
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`,
  scripts `0 errors`, puertos `2239/2250`, registro exitoso y
  `RestartCount=0`;
- gate visual aceptado por el usuario; la traza viva confirma respuestas
  `clientOwnedRepeat=True` seguidas por casts `Success` con TlId monotónico y
  ausencia total de `[AA8ComboCadence] Deferred/Executing`. V9 queda promovida
  como contrato transversal estable.

## Promoción documental V10: cierre de primera etapa

El usuario confirmó que toda la rama Battlerage cumple el alcance funcional y
visual requerido para la primera etapa. La matriz deja de ser candidata y
marca las doce familias activas, automáticas y pasivas como aceptadas dentro de
ese alcance.

El cierre no repite como nuevos los contratos heredados de Sorcery/Archery.
Promueve únicamente las primitivas descubiertas aquí:

- autoridad y wire de cooldown;
- temporización controller/arista y combat-sync por perfil;
- target posicional de presentación;
- procedencia versus vínculo toggle;
- agentes/condiciones de triggers, group/rank y stack `Extend`;
- admisión Combo durante GCD sin replay servidor;
- Mechanics Lab como certificación determinista de rama.

Punto de entrada:
`CHECKPOINT_BATTLERAGE_STAGE1_CLOSURE_V10.md`.
