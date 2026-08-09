# Dossier AA8 — cooldown y temporización Battlerage V5

Fecha: 9 de agosto de 2026. Autoridad: Kakao 8.0.3.12 r558734.

## Contrato de wire cerrado

- `SCSkillCooldownReducePacket`, opcode `0x038`, transporte cifrado AA8 nivel 5.
- Serializer Stage 15 x64:
  `fn:x64:12229b1dc1ea8be3453bc792586ec5a56e948cd8f6424132521f9af7f9a53c4a:00991d60`.
- Equivalente x86:
  `fn:x86:078db1b94236ecb8bbe21dc5c71ce90c178d51b6bf261c4767d32a44809bddc3:00b6ae40`.
- Orden: `BC`, `int32 skill`, `int32 tag`, `uint32 percent`, `uint32 count`,
  `uint32 reduce`, tres booleanos.
- `SCCooldownsPacket`, opcode `0x34D`, transporte cifrado AA8 nivel 5. Serializer x64
  `FUN_39985ee0`: tres buckets de máximo 150 entradas; cada entrada contiene
  `id/duration/remaining` de 32 bits.

Reset (`0x098`) y reducción (`0x038`) permanecen operaciones distintas.

## Relaciones y tiempo

- Behind Enemy Lines: Gale `39661` reduce Charge `11918` en 2000 ms por cada
  objetivo distinto impactado con éxito. Relación `39661001`.
- `SpecialEffect 153`: `value1=skill`, `value2=tag`, `value6=flat ms`,
  `value7=percent`; opera sobre tiempo restante.
- Plots: `animSync + projectile + max(edge, controller)`.
- `combat_sync_event_list.g` se indexa por perfil exacto de raza/género.

## Evidencia ejecutable

- Compact V5 SHA-256:
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`.
- Dos builds idénticos; `quick_check=ok`, `integrity_check=ok`.
- Behind Gale: Charge efectivo `12000 → 10000 → 8000 → 6000 ms`.
- Tiger Lightning: tres daños; primer→tercer impacto `640 ms`.
- Precision `36446`: fase visual en `0 ms`, daño en `642 ms`.
- Tests dirigidos .NET 3.1: `24/24 PASS`; estructurales V5: `11/11 PASS`.
- Mechanics Lab Battlerage: `25/25 PASS` (24 en suite y Triple Slash
  confirmado individualmente tras actualizar su expectativa de tareas agotadas).

La suite completa ejecutó 615 tests: 613 PASS y dos fallos preexistentes del
fixture Sorcery ancestral (`Aa8HeirSorceryProtocolTests`), ajenos a este diff.

## Despliegue V5

- Sólo se recreó el servicio `game`; `login` y `db` conservaron identidad.
- Imagen: `sha256:34936759439268969350882608d953838c64711a390ee3754a97f131bfc7a0f8`.
- `AAEmu.Game.dll` SHA-256:
  `9751783962D7CD50AE27667F9D1D66BACF771A386CBA12DAD6C4E76830FE3DAA`.
- Compact montada SHA-256:
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`.
- Scripts: `0 errors`; puertos `2239/2250`; registro en LoginServer exitoso.
- La captura live del cliente y sus timestamps queda como aceptación manual;
  no se declara sin una sesión AA8 conectada.

## Hotfix de framing de entrada (2026-08-09)

La primera publicación V5 heredó de Modern el transporte nivel 1 para
`0x34D/0x038`. La sesión real de Dannia probó que AA8 r558734 requiere el canal
cifrado nivel 5: tras `SCCooldowns 0x34D` el cliente alcanzaba
`CSNotifyInGame`, pero cerraba ambas conexiones pocos segundos después sin que
el servidor emitiera una expulsión ni excepción. Se restauró nivel 5 tanto
para el snapshot como para la reducción y se añadieron guardrails unitarios
para impedir otra promoción accidental del framing Modern.

## Hotfix de origen temporal de plots (2026-08-09)

La captura live aislada de Charge `11918` cerró un segundo defecto, distinto
del framing y de Behind Enemy Lines. En
`runtime-captures/packet-traces/aa8-game-20260809-214809415-session-361774020.jsonl`
se observaron tres lanzamientos sin impactos ni reducciones:

- `21:50:54.0102373 → 21:50:54.4234540` (`413 ms`);
- `21:51:35.8963759 → 21:51:36.3135187` (`417 ms`);
- `21:51:57.1924943 → 21:51:57.5980885` (`406 ms`).

En los tres casos el segundo timestamp corresponde a `SCPlotEnded`. El
runtime iniciaba el cooldown de una skill `plot_only` en ese callback, por lo
que el cliente sustituía su contador optimista por otros `12000 ms`. Se
corrigió transversalmente:

- una skill `plot_only` inicia su cooldown una sola vez al aceptar el
  lanzamiento y con su `TlId` como `castToken`;
- `PlotTree.DoPlotEnd` ya no inicia ni reemplaza cooldowns;
- `SCPlotEnded` no emite snapshots de cooldown: `SCCooldowns 0x34D` queda
  reservado a restauración de estado durante login/reconexión;
- reintentos durante cooldown o GCD no reciben
  `SCSkillStarted(CooldownTime)`, paquete que AA8 puede interpretar como un
  nuevo ciclo visual.

Prueba determinista: tras avanzar el reloj `410 ms`, Charge conserva duración
base `12000` y snapshot restante `11590 ms`. `UnitCooldownsTests`: `13/13`
PASS. Mechanics Lab Behind Gale: PASS (`12000 → 10000 → 8000 → 6000`).
Suite global: `617/619`; los dos fallos son los fixtures Sorcery ancestrales
preexistentes que requieren su compact específico.

Despliegue aislado de `game`:

- imagen `sha256:515dfdca79611cbee82674cc3958dc58e38c317e7e0e0e71b4d2b81145aaa067`;
- `AAEmu.Game.dll` SHA-256
  `D70A54F37DB09C22232CEC4501B4E3AA6092B97C3D37C976E0409EB8DDB1A6D8`;
- compact montada sin cambios:
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- scripts `0 errors`, puertos `2239/2250`, reinicios `0` y registro exitoso
  en LoginServer.

## Corrección de refresco por buffs (2026-08-09)

La captura live
`runtime-captures/packet-traces/aa8-game-20260809-221358742-session-182365033.jsonl`
demostró que Charge crea legítimamente el buff propio `7543` (4000 ms), puede
activar mediante la pasiva el buff `11344` (9000 ms), y que cada eliminación
coincidía con un salto visual del cooldown. En ambos instantes el servidor sólo
emitió `SCBuffRemovedPacket`: no hubo reset, reducción ni un segundo inicio.

El consumidor nativo AA8 `FUN_39a984f0` confirmó que `SCCooldowns 0x34D` carga
el bucket persistente de cooldowns. El snapshot que el hotfix anterior enviaba
después de cada `SCPlotEnded` era, por tanto, un uso fuera de su ciclo nativo:
al refrescar la barra por un cambio de buffs, el cliente volvía a materializar
ese estado masivo. Se retiró esa emisión de fin de plot. El cliente conserva su
ciclo local iniciado por el lanzamiento, el servidor conserva el cooldown
autoritativo iniciado una sola vez con `castToken`, y las reducciones continúan
viajando exclusivamente por `SCSkillCooldownReduce 0x038`.

La aceptación visual requiere comprobar que las expiraciones de `7543` y
`11344` ya no alteran el contador de Charge.

Despliegue candidato de esta corrección:

- imagen `sha256:2fff585d90d919cb270652921bc0f3824e56ecfca4ad736e27eb5b6fe0605328`;
- `AAEmu.Game.dll` SHA-256
  `4E5165948553D79DB9A60EFA6E2FDF9A430D88505B9655E5DA8000FAF31B7022`;
- compact montada, sin cambios:
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- sólo se recreó `game`; arrancó con scripts `0 errors`, registro exitoso en
  LoginServer y `RestartCount=0`.

## Corrección protocolaria de `SCBuffRemoved 0x023` (2026-08-09)

La aceptación viva falsificó el diagnóstico anterior: aun sin el snapshot de
fin de plot, el contador volvía visualmente a 12 segundos exactamente al
expirar `7543` y `11344`. La traza confirmó que esos buffs tienen
`cooldown_skill_id=0`, que el servidor no muta el cooldown en su salida y que
el único evento coincidente es `SCBuffRemoved 0x023`.

La implementación de ese paquete estaba basada en funciones nativas de otro
tipo de mensaje. La resolución correcta desde el factory de opcode prueba:

- x64: `FUN_393362a0` -> `PTR_FUN_39cfa388` -> `FUN_399ab070`;
- x86: `FUN_393266f0` -> `PTR_LAB_3a091ac0` -> `FUN_39b81990`;
- wire AA8: `objId(BC) + buffIndex(uint32)`, sin byte `reason`.

El servidor enviaba un cero terminal adicional en cada retirada. Se retiró
ese byte, se fijó la longitud nativa en la prueba de serialización y se marcó
como falsificado el checkpoint Archery que había asociado por error
`FUN_399ad0f0/FUN_39b83420` con `0x023`.

Despliegue del candidato:

- prueba focal `BuffRemovedPacketSerializationTests`: PASS;
- Mechanics Lab Behind Gale: PASS (`12000 -> 10000 -> 8000 -> 6000`), SHA
  `FBC24E1DEAB2E8E05F09061A52A5BFC16C26323659CC91BC0963104B905168B7`;
- imagen `sha256:25f26b51f11fbbf7bcdddcc3bfc91501d219656bf99439158b50dfc683d5dfe4`;
- `AAEmu.Game.dll` SHA-256
  `DA9B7357F3214E81CD0CA164581C966E052FC64C1751728FB8E25F5D0B2F5E1C`;
- compact montada sin cambios:
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- sólo se recreó `game`; scripts `0 errors`, puertos `2239/2250`, registro
  correcto en LoginServer y `RestartCount=0`.

Queda como gate vivo comprobar una sesión posterior al despliegue: cada
`SCBuffRemoved 0x023` debe perder exactamente el byte terminal previo y la
expiración de `7543/11344` no debe alterar el contador visual de Charge.

La sesión posterior confirmó el layout corregido pero falsificó que éste fuera
la causa del salto visual: Charge todavía volvía a 12 segundos.

## Causa raíz: vínculo toggle incorrecto en `SCBuffCreated 0x36C` (2026-08-09)

La comparación de regresiones localizó el cambio exacto en `835b42e1`. Antes
de ese checkpoint, el campo compacto `s` de `SCBuffCreated` sólo contenía una
skill cuando el buff era el `toggle_buff_id` de esa skill. El checkpoint lo
cambió para enviar la skill origen en todos los buffs.

La captura viva posterior al hotfix protocolario probó el patrón completo:

- Charge `11918` tiene `toggle_buff_id=0` en la compact AA8;
- sus buffs `7543`, `11344` y `22627` se publicaban con `skillId=11918`;
- al retirar cada buff, el cliente reactivaba visualmente el cooldown de la
  skill enlazada y volvía a mostrar su duración base de 12 segundos;
- no existía en esos instantes un segundo `CSStartSkill`, reset, reducción,
  snapshot ni mutación de `UnitCooldowns`.

Se restauró la semántica anterior y conservada también por el comparador
Modern: `s = originSkillId` únicamente cuando
`originSkill.toggle_buff_id == buff.id`; en cualquier otro buff, `s = 0`. El
campo continúa transportándose con la anchura AA8 probada y el `stack` nativo
permanece intacto. La procedencia real sólo se conserva en el trace del
servidor (`originSkill`), separada del vínculo funcional (`toggleSkill`).

Validación previa al despliegue:

- regresiones focales .NET 3.1: `9/9 PASS`;
- suite completa .NET 3.1 con la compact Sorcery requerida: `619/619 PASS`;
- Mechanics Lab Charge: PASS, `originSkill=11918`, `toggleSkill=0`, SHA-256
  `09EE2A88924E9369F0E4F71DF98D86ED15C21D7E35AC0AB2F5A46B112871B622`;
- Mechanics Lab Behind Gale: PASS, `12000 -> 10000 -> 8000 -> 6000`, SHA-256
  `75A1FCAB81D08F2D72969797C4BD1E338952D117A6AC6100404EE11CBFA409EE`.

Despliegue aislado de `game`:

- rollback preservado como
  `aaemu-game:rollback-pre-aa8-buff-toggle-link-20260809`;
- imagen `sha256:6e7f05407ff5b76670960c03b5217686917fa185bb9761738e3b198621548a71`;
- `AAEmu.Game.dll` SHA-256
  `C350439F3D0877946E9216A4AB1C559E70AA589755EF1B5AC688E1F82C6111B8`;
- compact montada SHA-256
  `BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58`;
- scripts `0 errors`, puertos `2239/2250`, registro correcto en LoginServer
  y `RestartCount=0`; `login` y `db` no fueron recreados.

Aceptación viva: **PASS**. El usuario lanzó sólo Charge y esperó las salidas
de `7543` y `11344`; ninguna volvió a materializar los 12 segundos. El hallazgo
queda promovido como regla transversal en
`../shared_primitives/CHECKPOINT_AA8_BUFF_CREATED_TOGGLE_LINK_V1.md`.
