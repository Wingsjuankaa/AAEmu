# AA10 r575 — protocolo E2E de misiones Nuia (Fase 6)

## Objetivo y regla de prueba

Demostrar la cadena racial Nuia desde un personaje nuevo usando el cliente
retail 10.0.2.13 r575, sin comandos GM, teletransporte, inserciones SQL de
progreso ni contenido fabricado. El operador humano controla el cliente; el
capturador sólo lee el estado del World, MySQL y los logs.

La puerta de la fase exige:

- inicio nativo por la sphere 2321 y quest 6839;
- aceptación, objetivos, reporte y rewards de la cadena por capítulos;
- cinemas, NPC, doodads, items y cambios de zona observables;
- logout/login con quests, inventario y completadas persistentes;
- repetición desde otro personaje nuevo;
- una captura o log inequívoco por transición, sin intervención GM.

## Estado de referencia del primer recorrido

Personaje: `Dannia`, id 7, raza 1 (Nuia), creado en zone key 179
(`w_solzreed_3`). En el primer login del 20 de agosto de 2026 se verificó:

1. `QuestAreaSphere ENTER ... sphere=2321 zone=179`.
2. Inicio de quest 6839 mediante `QuestActConAcceptSphere(685)`.
3. Inicio y finalización de la cinema 163 mediante
   `QuestActObjCinema(20)` y los paquetes retail de cinema.
4. Ejecución del autocompletado y rewards authored.
5. `SCQuestContextCompletedPacket` y retirada de la quest 6839.

Esto valida la transición de entrada, pero no cierra la cadena. La quest racial
de capítulo 1 que sigue es 330, aceptada en Lucius Quinto (NPC 3597) y reportada
en Parisi (NPC 11541). La prueba manual debe continuar desde ese marcador.

## Incidente trazado: quest 2532 y Marian

El primer recorrido quedó bloqueado en `A Mysterious Visitor` (quest 2532): el
servidor la llevó correctamente a `Ready`, pero Marian no apareció junto al
monolito. El análisis exacto de AA10 r575 estableció:

- el monolito visible es el doodad servidor 4500; su skill 17328 sólo ejecuta
  `FakeUse` y un timer, y no es el objetivo de la quest;
- Marian es el doodad cliente 14074 (`model=npctype://10581`), colocado por
  `game_pak` en `cells/014_014/doodad.g`, aproximadamente 4,5 metros al lado
  del 4500 y en la posición exacta marcada por el cliente;
- `doodad_func_quest_reacts.id=632` cambia 14074 a la fase visible 41496 cuando
  quest 2532 tiene estado 3 (`Ready`); la inferencia inicial de que el cliente
  materializaría por sí solo esta colocación quedó refutada por cuatro pruebas;
- `doodad_func_quests.id=1508` declara 14074 como reporte de 2532 mediante
  `quest_kind_id=2`;
- el handler retail de `SCQuestContextUpdated` busca por template 2532,
  reconoce estado 3 y publica el cambio; su layout coincide con el writer AA10;
- el log de las 18:56:44 confirma dos `SCQuestContextUpdated` en estado
  `Ready`, pero ambos fueron enviados al aceptar 2532, antes de cargar la celda
  de Marian; al llegar después a Bluemist no hubo otra sincronización;
- `ClientDoodad::OnPhaseChanged` registra y elimina callbacks por `quest_id`
  (`FUN_396f1aa0`, `FUN_390f2b80` y `FUN_390f61a0`), por lo que un doodad
  cargado tarde no puede recibir retrospectivamente el cambio ya publicado;
- AAEmu descartaba el reporte porque buscaba el object id local de Marian en
  `World.GetDoodad`, aunque `doodad_almighties.client_doodad=true`.

La corrección nativa carga `client_doodad`, conserva la notificación
`CSDoodadQuestNoti` como observación de un objeto cliente, distingue relaciones
de oferta (`quest_kind_id=1`) y reporte (`quest_kind_id=2`), resuelve el reporte
en la misma Zone sin fabricar un spawn y elimina correctamente el handler
`OnReportDoodad` al finalizar. Además, al recibir el borde nativo
`CSNotifySubZone`, el servidor vuelve a publicar únicamente las quests activas
en `Ready`: una actualización `Ready -> Ready` hace que AA10 despache el
callback recién registrado y seleccione la fase visible authored de Marian.

Las dos primeras repeticiones desplegadas refutaron los pulsos inmediatos:

- el reenvío al recibir `CSNotifySubZone(id)` ocurrió antes de que la celda
  terminara de cargar y registrar el callback de Marian;
- el reenvío al recibir `CSNotifySubZone(0)` ocurrió cuando el doodad ya había
  retirado ese callback. Además, AA10 puede emitir el sentinel cero muy cerca
  de una entrada válida, por lo que no sirve como barrera de carga;
- el tercer intento fue limpio: la quest 2532 se abandonó y se aceptó otra vez
  desde el NPC inicial. El servidor volvió a llevarla de `Progress` a `Ready`,
  pero Marian continuó oculta. Esto descarta persistencia vieja de la misión.

La decompilación exacta cerró que `SCQuestContextUpdated` no era el defecto:
`FUN_3933e0a0` entrega el contexto a `FUN_396b2850`, y un `Ready -> Ready`
invoca `FUN_390f0330`. Ésta recorre callbacks QuestReact ya registrados y
`FUN_396f2ca0` aplica la fase authored cuando coinciden quest, status y
componente. Por tanto, el pulso es nativo, pero sólo funciona después del
registro del doodad cliente.

La tercera corrección sustituye los dos pulsos inmediatos por una tarea única a
los 3 segundos de cada entrada no-cero. Cada entrada recibe una generación; una
entrada posterior invalida la tarea anterior. El sentinel cero no reenvía ni
cancela, y sólo las quests activas en `Ready` se publican. No se crea un NPC ni
un doodad servidor y no se modifica el compact ni el `game_pak`.

La cuarta prueba manual volvió a abandonar y aceptar 2532 desde cero. El log
demostró la entrada a subzona y la ejecución del pulso diferido exactamente tres
segundos después, con 2532 activa en `Ready`; aun así Marian no apareció y no
llegó `CSDoodadQuestNoti`. Esto descarta definitivamente el orden temporal y el
estado persistido como causa primaria.

La causa siguiente estaba en el contrato inicial del cliente: AA10 r575 define
el bit 90, `fset[11] & 0x04`, como lookup nativo de descriptores de doodad. El
enum autoritativo ya lo clasificaba como `fset_11_2_unknown`, pero ni el baseline
versionado ni el perfil Docker lo activaban. Sin ese lookup el marcador de quest
puede resolverse desde compact mientras el doodad authored de `game_pak` no se
instancia, no registra QuestReact 632 y nunca produce su object id local. Se
habilitó el mismo bit en ambas configuraciones; el byte 11 cambia solamente de
`0x98` a `0x9c`. Se conserva el pulso diferido como reevaluación nativa para el
caso en que la celda se materialice después del primer `Ready`.

El tercer corte quedó desplegado el 2026-08-20 después de restore, build
integral Release con cero errores y 1.455/1.455 pruebas correctas. Se recreó
únicamente `Game`; `db`, `login` y `game` quedaron healthy, el gate estricto
cubrió 43.696 acts sin hallazgos y Game volvió a registrarse en Login. La imagen
activa es
`sha256:f2193b47858fab8bf0b21e50bab55033fd6df658a746e1f2ad8b077dc63873f1`;
`AAEmu.Game.dll` tiene SHA-256
`a03767bf58484698a15a9ea872d03906e9517f669f8895cd4cdaa8071538535f`.
El rollback inmediato es
`aaemu-world:10.0.2.13-r575-local-rollback-20260820-194133`, imagen
`sha256:efa0cfbf65f10f8653721eeeec0bdd42ef0e11950216a2a42fa5661543a5a5fe`.

El cuarto corte quedó desplegado el 2026-08-20 con la imagen
`sha256:463b4795b3b14c435e2462b217f483cb00f1da158e78af0c5a73aa0446162bac`.
El runtime publicó el fset efectivo con byte 11 `0x9c` y listó
`fset_11_2_unknown` entre las features activas. Restore y build integral Release
cerraron sin errores; las suites quedaron en 1.457/1.457 y 6/6, y el gate
runtime en 43.696 acts con cero hallazgos. Se recreó únicamente `Game`; `db`,
`login` y `game` quedaron healthy, Game se registró en Login y los puertos
1239/1240/1250 quedaron escuchando. El rollback inmediato es
`aaemu-world:10.0.2.13-r575-local-rollback-20260820-203851`, imagen
`sha256:f2193b47858fab8bf0b21e50bab55033fd6df658a746e1f2ad8b077dc63873f1`.

### Quinto corte: proxy NPC nativo corroborado por AA8

La distribución AA8 contenía el mismo incidente documentado y resuelto: quest
2532 en `Ready`, marcador presente y Marian invisible/no interactuable. Sus
checkpoints `CHECKPOINT_NATIVE_CLIENT_DOODAD_PROXY_V2.md` y
`CHECKPOINT_NATIVE_QUEST_2532_REWARD_DIALOG_V1.md` demuestran que el actor
lógico no es un NPC autónomo sino el doodad 14074, respaldado por
`npctype://10581`, y que la colocación histórica del NPC 10581 sólo funcionaba
como transportador de transform. La solución AA8 indexa genéricamente doodads
`client_doodad` con modelo `npctype://`, reutiliza la colocación del actor y
elige el grupo funcional que contiene ese modelo.

AA10 confirma la misma estructura con evidencia propia:

- `game_pak/cells/014_014/doodad.g` coloca 14074 en
  `(15036.458, 14739.861, 150.425)`, yaw aproximado 179 grados;
- el full DB relaciona NPC 10581 con `npc_spawner_id=11749`, pero ningún
  `npc_spawners.g` r575 contiene `spawnerType 11749`; Zone nunca crea el
  transportador;
- 14074 tiene `client_doodad=true`; su Start 41495 no aporta el modelo útil y
  su Normal 41496 contiene `npctype://10581`;
- el cargador full-DB de AA10 omitía `doodad_func_groups.model`, aunque el
  modelo runtime ya tenía ese campo, y `Doodad.GetFuncGroupId()` elegía siempre
  Start.

El cierre mantiene la lógica transversal y deja la única especificidad en los
datos authored: el loader conserva `model`; todo `client_doodad` respaldado por
`npctype://` prefiere su grupo Normal y usa Start como fallback; el catálogo
separado `doodad_spawns_aa10_client_quest_proxies.json` publica la colocación
exacta de 14074 extraída de AA10. No se modifica compact, `game_pak`, SQLite ni
el runtime Zone, y no se codifica quest 2532 ni NPC 10581 en la lógica.

Este quinto corte sólo cierra la reconstrucción y sus gates automáticos. La
aparición, interacción y entrega permanecen como prueba manual del operador.

Validación y despliegue del quinto corte, 2026-08-20:

- build integral Release: 0 errores; unitarias 1.461/1.461; integración Login
  6/6; suite del gate Python 8/8;
- Stage 40 full-authority Strict: 43.737/43.737 referencias habilitadas,
  43.696 materializables en runtime y cero hallazgos; las cuatro entradas
  conservaron sus hashes autoritativos;
- imagen activa `sha256:1debea5a952eade6c8fd8b6c673a6d5f3a533bb938040995795194c9fbd77a6e`;
  `AAEmu.Game.dll` dentro del runtime tiene SHA-256
  `ABA3ADD08A3440E92B614CB7B442885ED7C0C9FFD91C6E7B61494E5C4E5B03FE`;
- el catálogo montado tiene SHA-256
  `5AFD7FA7B94CDB88E3C82663468CE6EF476E38CBC0C280D2717F8B23F836B79A`;
  Game cargó 42.611 doodads, incluyendo la única colocación `client_doodad` +
  `npctype://` presente en el catálogo servidor;
- se recreó únicamente Game. `db`, `login` y `game` quedaron healthy, el gate
  runtime cerró 43.696/0, el fset conservó byte 11 `0x9c`, Game se registró en
  Login y 1239/1240/1250 quedaron escuchando;
- rollback inmediato:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260820-214806` ->
  `sha256:463b4795b3b14c435e2462b217f483cb00f1da158e78af0c5a73aa0446162bac`.

No se inició, detuvo ni reinició ningún Zone ni se controló el cliente.

La aparición visual y la entrega quedaron demostradas por el operador en el
sexto corte descrito a continuación.

### Sexto corte: entrega 2532 y selección de la siguiente quest

La captura manual demuestra a Marian visible como proxy 14074/10581 y con
marcador de entrega. Su SHA-256 es
`BC62874C5E10B55B1331DF6DD9F754CF5B7E9776C6832B22BA83A19DE27AF624`.
La entrega de 2532 se persistió correctamente: el bit de `completed_quests`
quedó activo, 2532 salió de las quests activas y 2255 todavía no estaba activa
ni completada. Por tanto, no hubo pérdida ni corrupción de progreso.

La siguiente interacción volvió a abrir el diálogo de 2532 en vez de ofrecer
2255. La captura del fallo tiene SHA-256
`F59E90BECAFFA7DCBFBB45CEEF886D0832B9FF863FB195EC1C7E541783737FB0`.
El log reprodujo skill 11006 sobre doodad 14074/grupo 41496 y envío de
`SCDoodadQuestAcceptPacket` para 2532.

La causa fue transversal: el grupo 41496 contiene cuatro wrappers
`DoodadFuncQuest` sin skill propia —reportar 2532, ofrecer/reportar 2255 y
ofrecer 2256—, pero `GiveQuest` y `CompleteQuest` llamaban al selector genérico
de doodad. Éste escogía siempre el primer wrapper con `SkillId=0`;
`DoodadFuncQuest.Use` tampoco distinguía `quest_kind_id` y convertía cualquier
quest no activa en oferta, incluso si era no repetible y ya estaba completada.

Se implementó `Doodad.UseQuest`: filtra todos los wrappers de la fase por tipo
de interacción, estado activo/completado y repetibilidad; `GiveQuest` solicita
kind 1 y `CompleteQuest` kind 2. `DoodadFuncQuest` aplica la misma elegibilidad
como defensa en profundidad. En este estado authored, descarta 2532 y selecciona
2255 (`The Golden Mark`). La primitiva coincide con el cierre validado de AA8,
pero los IDs, fase, orden y estado usados para decidir provienen de AA10.

Validación y despliegue del sexto corte, 2026-08-21:

- build integral Release: 0 errores; unitarias 1.466/1.466; integración Login
  6/6; gate Stage 40 Python 8/8;
- runtime Strict: 43.696 actos habilitados, cero hallazgos; 8.901 quests;
- imagen activa:
  `sha256:67faf05dce381d331658927836f71c6949d5df52bb1ca562e018a4b699c6da20`;
  `AAEmu.Game.dll` SHA-256
  `91A84F95FC9D946E113D899C8C31FD3737925F187EE486E5DE0EFDAD5986E356`;
- rollback inmediato:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260821-064835` ->
  `sha256:1debea5a952eade6c8fd8b6c673a6d5f3a533bb938040995795194c9fbd77a6e`;
- `db`, `login` y `game` quedaron healthy; Game escucha 1239/1240/1250 y se
  registró correctamente en Login;
- un primer recreate omitió por error el override AA10 y arrancó la imagen
  base sin client worlds. Se detectó antes de servir, no mutó datos y fue
  reemplazado por la topología integrada `aaemu-world` correcta.

No se inició, detuvo ni reinició Zone ni se controló el cliente. El operador
debe relanzar Zone 179 y el cliente; con 2532 ya completada, el siguiente clic
en Marian debe mostrar la oferta 2255. La Fase 6 continúa abierta hasta probar
la cadena racial restante, persistencia y repetición.

### Séptimo corte: 2256 sin opción Aceptar y auditoría de suministros

La prueba manual confirmó que 2255 se aceptó, suministró el item 16280, se
completó y entregó su recompensa 18792. Inmediatamente después Marian abrió los
diálogos de 2256 (`Divine Intervention`), pero la UI sólo permitió avanzar o
cerrar la conversación: nunca envió `CSStartQuestContextPacket` para 2256. La
captura tiene SHA-256
`9298FFA041AD1E29FCF802C336475C4F931830849D1B1B4CF10161763D8C975D`.

No era un fallo al materializar un item al aceptar. La fuente AA10 demuestra
que 2256 sólo tiene `QuestActSupplyItem(8874)` para item 18791 x5 en su
componente reward 10366. Su componente start 10362 exige
`CompleteQuestContext(2255)`. El servidor persistió el bit de 2255 y emitió
`SCQuestContextCompletedPacket`, pero el runtime enviaba siempre componente 0.
AA10 r575 serializa ese paquete como dos `i32` —quest y componente—; AA8
corrobora que el segundo valor era el componente de reward realmente
completado. Para 2255 es 9946.

Se conserva el `ComponentId` antes de finalizar/eliminar la quest y se emite
`SCQuestContextCompletedPacket(2255, 9946)`. Esto cierra de forma transversal
las condiciones sucesivas que deben habilitarse sin relog. El cero se conserva
únicamente para quests que realmente no tengan componente reward authored.

La revisión de suministros se ejecutó contra toda la SQLite AA10 autoritativa,
no sólo contra la cadena Nuia. Resultado: 6.434 referencias enabled; 5.852
`SupplyItem`, 546 `SupplySelectiveItem`, 23 `SupplyRankedItem` y 13
`SupplyResultRankedItem`. Todas las referencias selectivas/rankeadas cierran
item y count. Sólo hay dos items inexistentes, ambos rewards de quests de prueba
category 55 (6763 y 7468), y un count cero authored en quest 3782. El runtime
ahora trata count cero o una cantidad ya satisfecha como no-op exitoso y no
encola una creación de item cero.

El dossier reproducible está en
`forensics/output/aa10-client-forensics/quest-phase6-item-supply-cut7/`; el
script fuente es
`reconstruccion_cliente_10/scripts/audit_quest_item_supply.py`. Los cuatro usos
enabled de `try_equip`/`check_exist` quedan inventariados aparte: son rewards de
quests 8462, 8463, 144 y 11138, no bloqueos de aceptación, por lo que no se les
inventó una semántica sin prueba nativa.

Validación y despliegue del séptimo corte, 2026-08-21:

- build integral Release: cero errores; unitarias 1.471/1.471; integración
  Login 6/6; gate Stage 40 Python 8/8;
- runtime Strict: 43.696 actos habilitados, cero hallazgos; 8.901 quests;
- imagen integrada activa:
  `sha256:df6b9af8078e693f36d001e4f735c3215cfde545a826f3fa1e9b1862a63ff8b5`;
  `AAEmu.Game.dll` SHA-256
  `750B52298F5CC4D395C15536DB22CB6D046221C1EB13DD4DDB1E861A667213D8`;
- rollback inmediato:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260821-075742` ->
  `sha256:67faf05dce381d331658927836f71c6949d5df52bb1ca562e018a4b699c6da20`;
- `db`, `login` y `game` quedaron healthy; World escucha 1240, Game 1239,
  Stream 1250 y Game se registró correctamente en Login.

Se recreó únicamente `game` con ambos compose, base + override AA10. Esto cerró
la conexión TCP del Zone que el operador mantenía abierto, pero no se inició,
detuvo ni relanzó ningún proceso Zone y no se controló el cliente.

### Octavo corte: 2256 bloqueada por el hard cap de apertura del mundo

La siguiente prueba manual mostró durante un instante la acción de completar
en `G`, reemplazada inmediatamente por `Kick Immediately`. La captura tiene
SHA-256
`66D8780B6FBC3DBFBD0B56010E70498D3EC2FEDE1AA566A13289060DC29AB264`.
El cliente sí recibió la oferta 2256 —Game registró
`SCDoodadQuestAcceptPacket`—, pero nunca emitió
`CSStartQuestContextPacket`. Esto descartó tanto el reward 18791 x5 como la
sincronización de 2255 como causa inmediata.

La etiqueta no describe una expulsión. En el corpus retail AA10,
`ui_texts.id=12213`, clave `world_level_hard_cap`, tiene como texto original
"alcanzado el nivel límite; no se puede aceptar la misión principal", mientras
su localización inglesa defectuosa es `Kick Immediately`. Dannia estaba en
nivel 28 y acababa de recibir la experiencia de 2255. La tabla nativa
`world_level_hard_caps` impide obtener quests durante los días 0–1 al llegar a
nivel 28 (`get_quest=false`); sólo desde el día 9 usa nivel 55 y
`get_quest=true`.

La reconstrucción en `x2game.dll` confirmó la ruta completa:
`GetWorldLevelHardCapInfo`/`FUN_39850220` resta el tiempo de apertura del mundo
guardado en `ClientPlayer+16000` al tiempo actual, selecciona la fila por días
y devuelve hard cap, modificador de experiencia y `get_quest`.
`GetServerOpenTime`/`FUN_3984afb0` lee ese mismo campo y
`IsWorldLevelEnabled`/`FUN_3984adf0` gobierna la mecánica.

El servidor enviaba `Helpers.UnixTimeNow()` en cada
`SCServerInfoPacket`, reiniciando para cada conexión la edad visible del mundo
a día cero. Ahora el paquete usa un tiempo de apertura estable y configurable:
`InitialConfig.ServerOpenTimeUnixSeconds=1782403200`
(`2026-06-25 16:00:00 UTC`), valor exacto de la captura original preservada en
el código. El wire test fija la serialización little-endian
`80503D6A00000000` y otro test verifica el valor de la configuración
distribuida y montada.

Validación y despliegue del octavo corte, 2026-08-21:

- build integral Release: cero errores; unitarias 1.473/1.473; integración
  Login 6/6; gate Stage 40 sin hallazgos;
- runtime Strict: 43.696 actos habilitados, cero hallazgos; 8.901 quests;
- imagen integrada activa:
  `sha256:c2effa60a1de6b5e9a87c5705fad6225f31a8dbbf205501d63de24d50cd45487`;
  `AAEmu.Game.dll` SHA-256
  `6460E91FBC45F38679872BFD7268C8DF69C6E8EE6647AED2788384E9D3AB0548`;
- rollback inmediato:
  `aaemu-world:10.0.2.13-r575-local-rollback-20260821-082340` ->
  `sha256:df6b9af8078e693f36d001e4f735c3215cfde545a826f3fa1e9b1862a63ff8b5`;
- `db`, `login` y `game` quedaron healthy; World escucha 1240, Game 1239,
  Stream 1250 y Game se registró correctamente en Login.

Se recreó únicamente `game` con ambos compose. El cambio de
`SCServerInfoPacket` se recibe al entrar de nuevo desde lobby; una conversación
ya abierta conserva el estado anterior. El recreate desconectó el Zone abierto,
pero no se inició, detuvo ni relanzó Zone ni se controló el cliente.

## Perfiles Zone exactos

El campo `quest_contexts.zone_id` no es el `zone_key` del protocolo. Usar este
crosswalk AA10 exacto:

| Capítulo / zona lógica | World nativo | zone key |
|---|---|---:|
| 1, `125` | `w_solzreed_3` | 179 |
| 1–2, `9` | `w_solzreed_1` | 142 |
| 2, `124` | `w_solzreed_2` | 178 |
| 3, `11` | `w_lilyut_hills_1` | 144 |
| 3–4, `141` | `w_lilyut_hills_2` | 195 |
| 4, `7` | `w_dewstone_plains_1` | 140 |
| 4, `131` | `w_dewstone_plains_2` | 185 |
| 5, `10` | `w_white_forest_1` | 143 |
| 6, `2` | `w_marianople_1` | 133 |
| 6, `15` | `w_two_crowns_1` | 149 |

Las particiones 133 y 149 sí existen en el `game_pak` r575. Sus spawners
nativos fueron extraídos sin modificar el paquete fuente y tienen SHA-256:

- 133: `4F62007259FB048A634EEA0592AF0622CE7D24D8AB32031EA47905F565428D15`
- 149: `6F7260065DA02DB971E0D88498116CB109CB446695D0BA52494453D1CF77ADF8`

Antes de cruzar un borde, el operador del servidor debe levantar la partición
destino y verificar `ZWJoin`, `WZJoinResponse`, `ZoneLoaded` y heartbeats. No se
debe detener la partición origen mientras el personaje esté en tránsito.

## Captura no interactiva

Desde PowerShell, en la raíz del repositorio:

```powershell
.\Scripts\CaptureAa10QuestPhase6Evidence.ps1 -Action Begin -CharacterName Dannia -Label baseline
```

Si el cliente ya había iniciado antes de abrir la sesión de evidencia, se puede
fijar el comienzo UTC sin alterar el runtime:

```powershell
.\Scripts\CaptureAa10QuestPhase6Evidence.ps1 -Action Begin -CharacterName Dannia -Label baseline -SinceUtc "2026-08-20T18:24:30Z"
```

Después de cada quest racial (o al final de cada capítulo):

```powershell
.\Scripts\CaptureAa10QuestPhase6Evidence.ps1 -Action Snapshot -CharacterName Dannia -Label chapter1-q330
```

Tras logout, nuevo login y comprobación visual de persistencia:

```powershell
.\Scripts\CaptureAa10QuestPhase6Evidence.ps1 -Action Finish -CharacterName Dannia -Label relog
```

Cada snapshot conserva:

- estado vivo del World y Zone Manager;
- fila del personaje, quests activas/completadas, inventario y ledger durable;
- logs filtrados de quests, spheres, cinemas, doodads y Zone;
- identidad/estado de contenedores y procesos Zone;
- manifest SHA-256 al finalizar.

La salida queda en `runtime/evidence/quest-phase6/`. No altera progreso ni
controla el cliente.

El parser de `session.json` acepta tanto el ISO-8601 original como el objeto
`DateTime` materializado por `ConvertFrom-Json`; esto evita que `Snapshot` falle
por la cultura `es-CL` al convertir fechas con mes/día.

## Secuencia racial mínima a marcar

Registrar el ID visible en logs al aceptar y al completar. El orden authored es:

- Capítulo 1: 330, 2531, 2532, 2255, 2256, 2257.
- Capítulo 2: 2258, 2259, 2260, 1525, 2263, 2261, 3503, 2262, 2264,
  2265, 2266.
- Capítulo 3: 2485, 4393, 2486, 3573, 2488, 2489, 4394, 4396.
- Capítulo 4: 2490, 2491, 1424, 2492, 4397, 2494, 2495, 2496, 4398.
- Capítulo 5: 2498, 3985, 3986, 4399, 4400, 3987.
- Capítulo 6: 4402, 4403, 4404, 3988, 3989, 4405, 4406, 4407, 3990,
  3991, 4409, 4410, 3993, 4411.

Las quests raciales con `chapter_idx=0`, tutoriales genéricos y la quest 7115
posterior al capítulo 6 no sustituyen esta secuencia. Si una quest no aparece,
registrar el último ID completado, el marcador/NPC esperado, zone key, posición
y hora; no adelantar el estado con GM.

## Checklist de relog y repetición

1. Tomar snapshot con una quest de objetivo parcialmente avanzada.
2. Salir mediante la UI y esperar que el personaje desaparezca de
   `/api/world/logged-characters`.
3. Volver a entrar con el mismo personaje.
4. Confirmar el mismo objetivo, contador, items y siguiente marcador.
5. Completar la quest y tomar otro snapshot.
6. Al cerrar toda la cadena, repetir 6839 y al menos un capítulo desde un Nuia
   nuevo para demostrar ausencia de estado residual de cuenta/personaje.

La Fase 6 sólo puede marcarse cerrada cuando los artefactos demuestren todos los
capítulos y la persistencia. Hasta entonces el estado correcto es
`E2E manual en curso`.
