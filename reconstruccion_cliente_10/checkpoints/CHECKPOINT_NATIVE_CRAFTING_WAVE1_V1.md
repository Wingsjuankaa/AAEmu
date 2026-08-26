# Checkpoint nativo: crafting AA10 r575, ola 1

## Estado de promoción

La ola 1 queda **aceptada y cerrada** sobre `rama_10`, baseline de partida
`482bb1118a57bd5c7200fd0bbdda790744674a78`. Game fue desplegado en Release el
2026-08-26 de forma reversible. Codex no inició, reinició ni controló ningún
ZoneHost; el operador reconectó su Zone desde Control Center. Están aprobados
los gates retail de Folio, éxito, persistencia, cancelación/reintento, material
insuficiente, bolsa llena con rechazo pre-cast y múltiples clicks. La ola 2
puede comenzar desde este checkpoint.

El catálogo contiene 9.949 recetas habilitadas en la SQLite full. El manifest
fail-closed promueve 5.282 recetas a `executable_wave1` y mantiene 4.667 en
`blocked`. La cifra preliminar de 5.379 candidatos se reduce porque 282 recetas
full no existen en el compact retail exacto; 97 de ellas no tenían otro bloqueo
de ola 1. No se delega ninguna receta bloqueada al crafting heredado.

## Identidad de las fuentes

| Fuente | Bytes | SHA-256 | quick/integrity |
|---|---:|---|---|
| `E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3` | 552.178.688 | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` | `ok/ok` |
| `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game\db\compact.sqlite3` | 440.827.904 | `8B1619B11702892AEE02008DECCD70D6A2A206E2DEA57482BF52201C19CE9849` | `ok/ok` |
| `E:\AAEmu\rama_10\server\AAEmu\.server_files\AAEmu.Game\Data\compact.sqlite3` | 552.178.688 | `DA36AB24D439EAF7AEF8E638A2797194276BBC7C8AA8DD4E787847E286ECFACD` | `ok/ok` |
| `x2game.dll` r575 | — | `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734` | — |

La línea padre exacta es
`AAEmu/AAEmu:client_version/zone-10.0.2_r575` en
`3cc280b14d7da0d874121d14ebbf409f5e032d1c`. AA8 se utilizó sólo como
`structural_candidate`; no se copiaron IDs, packets, fórmulas, rates ni timings.

## Frontera forense reproducible

`reconstruccion_cliente_10/scripts/audit_aa10_crafting.py` abre las tres SQLite
en modo read-only y `query_only`, verifica integridad, congela schemas y SQL,
calcula hashes y emite el catálogo completo en
`reconstruccion_cliente_10/generated/aa10-crafting-wave1-manifest.json`.

El manifest no contiene timestamps ni entradas dependientes del orden del
runtime. Dos generaciones consecutivas deben producir el mismo SHA-256. Su
hash en este checkpoint es
`D86079198C11CAE752F13AC198851923EEE9C886772BF67D30D287D2D7D612C4`.
La allowlist compacta que consume Game está en
`AAEmu.Game/Data/aa10-crafting-wave1-policy.json`, contiene exactamente los
5.282 IDs promovidos, referencia ese hash y tiene SHA-256
`24E61D81A33ACB9306612A3A41884EBFD7C32C3D52C2C65C0D0BEBD8D47276F5`.
El auditor emite la misma política también en
`.server_files/AAEmu.Game/Data/aa10-crafting-wave1-policy.json`, porque ese
directorio se monta sobre `/app/game/Data` en Docker y oculta el contenido de
la imagen. La copia montada conservó exactamente el mismo hash.
Si la política falta, está vacía o incluye IDs desconocidos/deshabilitados, el
loader falla cerrado y Game no arranca con un fallback implícito.

Bloqueos del catálogo (una receta puede tener más de uno):

| Bloqueo | Recetas |
|---|---:|
| coste diferido | 2.950 |
| grado de producto diferido | 1.413 |
| actability diferida | 1.334 |
| materiales ausentes | 702 |
| backpack/tradepack diferido | 389 |
| ausente del compact retail | 282 |
| productos ausentes | 180 |
| grado de material diferido | 93 |
| rate de producto diferido | 91 |
| skill ausente | 87 |
| item de material ausente | 13 |
| `CraftEffect` ausente | 4 |
| item de producto ausente | 1 |

La fuente full contiene además 243 filas huérfanas de `craft_materials` y cero
de `craft_products`. Esas filas no se incorporan silenciosamente a ninguna
receta.

## Contratos cerrados en la ola 1

- Loader AA10 exacto para `enable`, `cost`, `products_pack_id`, categorías,
  `orderable`, `use_only_actability`, `require_grade` y `upper_grade`.
- `craft_pack_crafts` se conserva como membresía de catálogo. Un producto se
  considera autoequipable sólo por su `BackpackTemplate` runtime.
- `TryGetCraft` rechaza IDs desconocidos y recetas deshabilitadas sin lanzar.
- `TryValidateContract` cierra el contrato inmutable antes de abrir la sesión.
  El planner transaccional es puro e inmutable; agrega materiales/productos repetidos con
  overflow comprobado, consume múltiples stacks y simula la capacidad liberada
  por el consumo antes de producir.
- La transacción vuelve a comprobar materiales, destruibilidad y capacidad bajo
  el mismo lock de la bolsa. Sólo después publica las tareas de consumo y
  producto.
- `CharacterCraft` admite una sola sesión activa y exactamente `count=1`.
  Antes de iniciar la skill valida receta, skill/`CraftEffect`, estación,
  permiso, labor, materiales y capacidad. `CraftEffect` revalida el estado
  mutable y confirma bajo lock para cerrar carreras ocurridas durante el cast.
- Las estaciones requeridas deben existir y coincidir exactamente. Los doodads
  no públicos fallan cerrados hasta que cada modo de ownership/permisos tenga
  evidencia AA10. El rango continúa siendo validado por los requisitos nativos
  de la skill.
- Quest, shipyard, housing e interacción sólo avanzan después del commit. Un
  rechazo cancela la skill para impedir labor, vocation o progreso parcial.
- Cancelación, desconexión y salida del mundo limpian la sesión activa.
- `SCCraftFailedPacket` (`0x22D`) lee un `int32`, un contador `int32` y hasta 20
  IDs `int32`. `FUN_3933fb20` llama a `FUN_398b2150`, que publica el evento UI
  `CRAFT_FAILED` (`0x72`) con links de item. El Lua sólo muestra
  `failed_craft_alert`: no resetea `CraftManagerImpl` ni genera
  `CRAFT_ENDED`, así que no se usa como cierre de batch.
- El manager cliente r575 considera que trabaja cuando `count > 0` y su flag
  `+0x14` está activo. `ExecuteBatchCraftByType` registra los eventos de skill
  `0x16`–`0x19`. En `FUN_398b52d0`, la rama `0x16` con resultado no exitoso
  llama a `FUN_398b1390`, resetea el batch y publica `CRAFT_ENDED` (`0x22F`)
  antes de `CRAFT_STARTED`. Los rechazos pre-cast usan por ello
  `SCSkillStarted` fallido con `tl=0`, cast real/base cero y el `SkillResult`
  nativo; la revalidación tardía continúa cancelando mediante `SCSkillEnded`.
  El decompilado reproducible está en
  `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\craft-failure-frontier\ghidra-craft-manager-lifecycle.log`.

## Exclusiones deliberadas

Repetición, costes, actability especial, grados, rates y backpacks/tradepacks
permanecen bloqueados para sus olas respectivas. `Craft Orders` no forma parte
de esta reconstrucción. `cast_delay` se preserva en el modelo y manifest; la
ola 1 usa el lifecycle de la skill de una sola unidad y no introduce un
scheduler propio.

## Verificación estática

- `dotnet restore AAEmu.slnx`: correcto.
- build `Release` de la solución: correcto, sin errores.
- `AAEmu.UnitTests`: 1.543/1.543 pruebas correctas.
- pruebas focales: loader AA10, planner, agregación/overflow, stacks múltiples,
  capacidad liberada, bolsa llena, item no destruible y transacción sin mutación
  en rechazos; separación contrato/lifecycle frente a estado mutable; wire
  exacto del rechazo `BagFull` pre-cast; 2/2 pruebas de cancelación y
  aislamiento de sesiones correctas.
- auditoría Python del manifest y paridad exacta de su allowlist runtime: 5/5
  pruebas correctas.
- `PRAGMA quick_check` e `integrity_check`: `ok` en las tres fuentes.

## Despliegue reversible de la ola 1

- servicio recreado: sólo `game`; `db` y `login` permanecieron sanos y no se
  recrearon;
- imagen Release activa: `sha256:fde1982008e1822e835fad98128b5c8a67bc3f6941bcad9bbd9e8c0b7fc22d6b`;
- rollback inmediato anterior a la validación `BagFull` pre-cast:
  `aaemu-world:rollback-pre-crafting-wave1-precast-bagfull-fix-20260826`,
  imagen `sha256:8d5ed64b71492a04e699f8d0af8b58d8c04703ed6a04cc6cdd60ba783861f6dc`;
- rollback inmediato anterior a la reparación del lifecycle de bolsa llena:
  `aaemu-world:rollback-pre-crafting-wave1-fullbag-lifecycle-fix-20260826`,
  imagen `sha256:679a0b38e6f12f30b94a9f57380aaa3b6495a685c8d9c13f11936bf88efb81a9`;
- rollback inmediato anterior a la reparación de cancelación preservado como
  `aaemu-world:rollback-pre-crafting-wave1-cancel-fix-20260826`, imagen
  `sha256:5d4f26e6d62b92df36074f5d4c733d5695321009842226d229b911fe7e36f34a`;
- rollback preservado como
  `aaemu-world:rollback-pre-crafting-wave1-20260826`, imagen
  `sha256:ead6131af1213c50f5d0dbdf9a280bb2434985c59bdd91ecda0ecdb0100fa9a3`;
- contenedor `aaemu10-game-1`: `healthy`, cero reinicios;
- hash dentro del contenedor: política
  `24e61d81a33acb9306612a3a41884ebfd7c32c3d52c2c65c0d0bebd8d47276f5`
  y compact runtime
  `da36ab24d439eaf7aef8e638a2797194276bbc7c8aa8dd4e787847e286ecfacd`;
- loader runtime: 12.402 recetas, 9.949 habilitadas y 5.282 promovidas;
- Game `1239`, Zone ingress `1240`, Stream `1250` y WebApi `1280` arrancaron;
  Game registró su sesión con Login;
- no se observaron fallos fatales, excepciones no controladas ni bucle de
  reinicios durante el arranque.

El recreado de Game desconectó la Zone que estaba enlazada. Codex no la inició
ni manipuló; el operador la reconectó desde Control Center y realizó la prueba
retail con `Dannia`.

## Aceptación retail

Con la Zone elegida por el operador, probar una receta `executable_wave1` con
materiales entregados por el canal GM:

1. abrir el Folio y confirmar que el producto aparece como `Finished Product`
   con categoría, workbench, recursos, coste y labor completos;
2. buscar cada ingrediente bajo `Materials`; exigir también `Finished Product`
   sólo si el item posee una receta productora habilitada;
3. capturar inventario, labor y dinero antes del craft;
4. ejecutar una unidad en la estación correcta;
5. confirmar consumo y producto exactos, labor una sola vez y dinero sin cambio;
6. cancelar una ejecución durante el cast y comprobar cero mutación;
7. probar material insuficiente, bolsa llena, estación equivocada y doble
   petición, todos sin progreso de quest ni mutación parcial;
8. reloguear y verificar persistencia;
9. conservar logs y comparación antes/después.

La receta de aceptación es `craft_id=12176`, localizada como
`Hiram Awakening Scroll`. Debe ejecutarse en un `Proven Warrior Workbench`
estático y público, sin línea `Owner`; no se aceptan estaciones colocadas en
propiedades porque mezclarían esta prueba con permisos de housing. Consume
exactamente un `Radiant Hiram Awakening Scroll` (45908) y un
`Onyx Archeum Essence` (32103), produce un `Hiram Awakening Scroll` (45729),
cuesta 0 cobre, consume 5 labor, tarda 1000 ms y tiene rate 100. El manifest la
clasifica `executable_wave1` sin blockers. Existen once spawns estáticos del
workbench en `main_world`, frente a cero spawns estáticos de la
`Specialty Workbench` usada en la propuesta anterior.

Como smoke test opcional en una estación pública más común puede usarse
`craft_id=10697`, `Farm Cart Chroma`, en un `Carpentry Workbench`: consume un
`Scroll: Farm Cart` (36293) y produce un `Scroll: Farm Cart Chroma` (46111).
No reemplaza la aceptación decisiva porque su skill consume 0 labor.

Este smoke test fue aprobado dinámicamente el 2026-08-26 con `Dannia`:
`CSExecuteCraft` recibió `craftId=10697`, `objId=128449`, `count=1`; la skill
34492 completó su lifecycle y Game registró un único commit con
`materials=1`, `products=1`, `labor=0`, sin `SCErrorMsgPacket`. El snapshot vivo
posterior no contenía el material 36293 y contenía exactamente una unidad del
producto 46111. Esto acepta el intercambio base y la estación pública, pero no
promueve la ola: siguen pendientes el caso con cobro de labor y los rechazos
dinámicos sin mutación.

El caso positivo decisivo también fue aprobado dinámicamente el 2026-08-26 con
`Dannia`. Tras entregar 1000 unidades de cada material, `CSExecuteCraft`
recibió `craftId=12176`, `objId=119164`, `count=1` contra el template de
estación 7088. La skill 40812 completó su lifecycle y Game registró un único
commit con `materials=2`, `products=1`, `labor=5`, seguido de
`SCCharacterLaborPowerChangedPacket` y sin `SCErrorMsgPacket`. El snapshot vivo
posterior conservó 999 unidades de 45908 y 32103 y añadió exactamente una
unidad de 45729. En ese momento quedaron pendientes la persistencia tras relog
y los rechazos dinámicos sin mutación.

La persistencia tras relog quedó aprobada el 2026-08-26. Game registró la
desconexión y una nueva entrada completa de `Dannia`, incluyendo
`SCCharacterInvenInitPacket`, contenidos de inventario y
`CSSpawnCharacterPacket`. El snapshot vivo posterior mantuvo 999 unidades de
45908, 999 de 32103, una de 45729 y una de 46111. No hubo reversión ni
duplicación de los commits de crafting.

La primera prueba dinámica de cancelación demostró cero mutación, pero descubrió
un bloqueo de lifecycle: a las `13:32:05`, `CSStopCasting` canceló la skill
40812 y terminó la timeline 720 sin ejecutar ningún commit; al reintentar a las
`13:32:17`, Game rechazó la misma receta con `failure=Busy`. La causa era que el
stop limpiaba `SkillTask`, pero dejaba `_currentCraft` activo en la sesión
separada de `CharacterCraft`.

La reparación enlaza `CSStopCasting` con `CharacterCraft.Cancel(sourceSkill)`.
Sólo una skill cuyo template coincide con el `SkillId` de la receta activa puede
liberar la sesión; además queda marcada como cancelada y sin consumo automático.
Dos pruebas focales cubren tanto la liberación correcta como la preservación
frente a una skill ajena. Restore, build Release y las 1.541 pruebas completas
pasaron antes de desplegar la imagen reparada. Game arrancó en 74 segundos,
abrió 1239/1240/1250/1280, se registró con Login y permanece `healthy` con cero
reinicios.

El gate reparado quedó aprobado dinámicamente el 2026-08-26. Entre `13:43:51`
y `13:44:16`, Game recibió cinco `CSExecuteCraft` consecutivos para la receta
12176. Cuatro se cancelaron y registraron
`StopCasting ... skill=40812 ... craftSession=True`; cada cancelación fue
seguida por otro inicio válido, con nuevas timelines 720–724. No apareció
`failure=Busy` ni `SCErrorMsgPacket`. Sólo la timeline 723 completó y produjo un
único `AA10 craft committed` con `materials=2`, `products=1`, `labor=5` y el
packet de cambio de labor. El snapshot runtime posterior de `Dannia` mostró
998 unidades de 45908, 998 de 32103 y 2 de 45729, exactamente una transacción
adicional sobre el estado persistido anterior 999/999/1. Las cuatro
cancelaciones no produjeron mutación observable.

El gate retail de material insuficiente quedó aprobado a continuación. Con 998
unidades de 45908 y cero de 32103, el Folio mostró `0/1` para el ingrediente
ausente y mantuvo `Confirm` deshabilitado. El click no produjo ningún
`CSExecuteCraft` en Game: el consumer r575 cerró la petición antes de la red y
el inventario no mutó. La defensa servidor equivalente permanece cubierta por
las pruebas focales del planner y la transacción; el cliente retail normal no
permite alcanzar esa rama con materiales ya ausentes.

La atomicidad del rechazo por bolsa llena quedó aprobada dinámicamente. Para eliminar la
posibilidad de apilar el resultado, el operador completó primero una unidad
adicional a las `13:49:41`, destruyó las tres unidades existentes de 45729 y
llenó los 100 slots de la bolsa dividiendo 32103. A las `13:50:12`, Game recibió
`CSExecuteCraft` para 12176, emitió un único `SCErrorMsgPacket` y registró
`failure=BagFull`; no creó skill ni timeline. Después del rechazo no apareció
ningún commit ni packet de cambio de labor. El snapshot vivo mostró 100/100
filas, 997 unidades totales de 32103 en 34 stacks, 997 de 45908 y cero de 45729:
los materiales y el producto permanecieron exactamente en el estado preparado.

Esa prueba descubrió un segundo defecto de lifecycle: como `BagFull` se
rechazaba antes de crear la skill, el cliente ya había dejado
`IsWorkingCraft=true`, pero nunca recibía un evento terminal. `crafting.lua`
sólo reactiva Confirm en `CRAFT_ENDED`; su handler de `BAG_UPDATE` está
comentado. Por eso liberar un slot dejaba 99/100 pero no enviaba un nuevo
`CSExecuteCraft`.

La segunda reparación liberó correctamente el batch mediante `SCSkillEnded`,
pero la alerta `BagFull` sólo aparecía al terminar el casteo. El decompilado
r575 del callback `FUN_398b52d0` cerró una ruta anterior y más precisa: un
evento de inicio de skill con resultado fallido resetea el batch, publica
`CRAFT_ENDED` y retorna antes de `CRAFT_STARTED`. La implementación actual hace
preflight de estación, permiso, labor, materiales y capacidad antes de abrir la
sesión; ante `BagFull` envía `SCSkillStarted` con timeline/cast cero y resultado
`0x2E`. Conserva la revalidación atómica en `CraftEffect` para carreras reales.
Restore, build Release, 1.543/1.543 pruebas, auditoría 5/5 y `diff --check`
pasaron. Se recreó únicamente Game con la imagen `fde1982008e...`; completó el
arranque en 70 segundos, abrió 1239/1240/1250/1280, cargó 5.282 recetas
promovidas, se registró con Login y permanece healthy con cero reinicios. DB y
Login continuaron sanos. Zone no fue iniciada ni manipulada por Codex y debe
reconectarse desde Control Center.

El gate final quedó aprobado dinámicamente el 2026-08-26. A las `19:24:58`,
Game recibió `CSExecuteCraft` para 12176 y registró
`Rejected AA10 craft before skill start ... failure=BagFull ... result=BagFull`;
no creó timeline, no emitió `SCErrorMsgPacket` y no hubo commit. Tras liberar
espacio sin cerrar el Folio, una petición a las `19:25:03` creó la timeline 718
y su cancelación a las `19:25:07` liberó la sesión. El reintento de las
`19:25:10` creó la timeline 719 y produjo a las `19:25:18` exactamente un commit
con dos materiales, un producto y cinco de labor.

El operador probó después múltiples clicks. A las `19:26:43` el cliente emitió
una sola petición `CSExecuteCraft`, Game creó únicamente la timeline 721 y a
las `19:26:51` publicó un solo commit y un solo cambio de labor. En toda la
ventana hubo cuatro peticiones —rechazo, cancelación, reintento y prueba
múltiple—, un `BagFull`, dos commits válidos, cero `Busy` y cero
`SCErrorMsgPacket`. El snapshot vivo y MySQL coincidieron después de la prueba:
995 unidades de 45908, 995 de 32103 y dos de 45729, exactamente el estado
esperado tras los dos commits sobre la preparación 997/997/0. La validación de
estación ausente/equivocada y permisos no públicos permanece fail-closed y
cubierta por las pruebas focales.

El operador aceptó explícitamente el checkpoint y autorizó cerrar la ola 1.
