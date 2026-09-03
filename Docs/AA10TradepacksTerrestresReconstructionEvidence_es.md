# Reconstrucción AA10 de tradepacks terrestres — evidencia y checkpoint

**Fecha:** 18 de agosto de 2026

**Target:** `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`

**Caso principal:** pack `31856`, Dewstone Plains (`zone_group_id=3`) → Solzreed Peninsula (`zone_group_id=5`)
**Comprador:** NPC template `17971`, `specialty_bundle_id=10`, pago en oro

## Resultado

El fallo se localizó en la cotización que precede a la venta. El servidor
respondía a `CSSpecialtyRatio 0x070` con un cargo comercial del outlet, no con
el tradepack terrestre equipado. Al cerrar el lote, el cliente buscaba el
template del backpack actual entre los quotes, no lo encontraba y publicaba
`UPDATE_SPECIALTY_RATIO` sin item. El Lua del diálogo cancelaba la ventana,
pero continuaba con `dialog:Init(sellItem)`; el nil resultante podía cerrar el
cliente.

La corrección desplegada genera el quote del pack equipado sólo cuando el
bundle del NPC lo acepta, aplica market ratio y frescura, conserva la fecha de
creación al representar el pack como doodad de vehículo/Zone y ejecuta el
cierre de venta con todas las recompensas preconstruidas antes de consumir el
item.

La prueba jugable posterior descubrió además dos contratos AA10 específicos:

- `SpecialtyQuote.ratio` ya está expresado como porcentaje entero para Lua;
  `130` debe viajar como `130`, no como `1300`;
- `CSSellBackpackGoods 0x06F` envía `characterObjId=0` como sentinel de self.
  El servidor aceptaba sólo el ObjId dinámico y devolvía `Invalid target`.

## Evidencia del incidente

En la reproducción real anterior al cambio, alrededor de las `23:08`:

1. el jugador recuperó el pack y lo equipó;
2. cada interacción con el comprador produjo `CSSpecialtyRatio 0x070`;
3. World respondió `SCSpecialtyRatio 0x0C5`;
4. no apareció `CSSellBackpack 0x06F` ni la ventana utilizable;
5. el jugador pudo volver a depositar el pack y la sesión permaneció activa.

El cierre observado en la prueba previa es coherente con el consumer Lua nil.
Los `CSSaveUIData 0x16E` tardíos y su `NullReferenceException` ocurrían después
de `SCLeaveWorldGranted`; eran ruido de teardown, no la causa de tradepacks.
Se añadió una guarda independiente sobre `ActiveChar`.

## Contratos nativos cerrados

Fuente autoritativa: `x2game.dll` del cliente Returns 10.0.2.13 r575 y
`sell_tradegood.lua` extraído a
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\tradepacks-terrestrial-frontier\sell_tradegood.lua`.

| Contrato | Evidencia r575 |
|---|---|
| `SCSpecialtyRatio` | vtable `0x39e627a0`, serializer `FUN_39ab56a0` |
| `SCSpecialtyGoods` | vtable `0x39e627c8`, serializer `FUN_39a9c2e0` |
| `SpecialtyQuote` | serializer `FUN_39b62390` |
| handler ratio | registro `0x3933b2a0` → `FUN_398f2fe0` |
| handler goods | registro `0x3933b2f0` → `FUN_398f0c20` |
| frescura UI | `FUN_398ee280`, resolver `FUN_3998fdf0` |

`SCSpecialtyRatio` serializa `zoneGroup:u16`, `npcTemplate:u32`,
`count:u32`, `eventCount:u32`, flags begin/end, hasta 20 quotes y hasta 50
event ids. Cada quote contiene `item:u32`, `refund:u64`,
`noEventRefund:u64`, `ratio:u32`, `stock:u32`, `canProduce:bool`,
`currency:u8` y `type:i8`. Las clases wire existentes ya respetaban este
layout; el defecto estaba en la selección semántica del quote.

Al recibir el último packet de ratio, el handler nativo busca explícitamente
el template del backpack equipado en el acumulado. Por esto un lote vacío o un
cargo ajeno no es una respuesta segura para la interacción de venta.

## Datos autoritativos del caso

- `31856` pertenece al bundle `10`, usa `backpack_type_id=3` y
  `freshness_group_id=5`.
- El valor base del mapping es `33.263`; su ratio observado en datos es
  `2.488` y el wire neutral de frescura es `1.000`.
- Los tramos del grupo 5 se resuelven con límite inclusivo, igual que el
  nativo: 900 s → 115%, 3.600 s → 105%, 10.800 s → 90%, 86.400 s → 85% y
  172.800 s → 65%. Después del último límite permanece la última etapa.
- El `seller_share` del tramo se expresa en décimas de porcentaje en cliente;
  el servidor lo transforma dividiendo por diez cuando existe.
- El NPC alternativo `15087` usa bundle `26` y otra moneda. No se mezcló con
  el comprador de oro del caso principal.

## Cambios implementados

- `BackpackTemplate` e `ItemManager` cargan `freshness_group_id`.
- `SpecialtyManager` carga y ordena `freshness_group_items`.
- `SendBuyList` emite el quote del backpack equipado aceptado por el bundle;
  conserva la ruta separada de compra de cargo cuando no hay pack.
- Un pack no aceptado produce error explícito sin enviar un lote final vacío
  que vuelva a activar el defecto Lua del cliente.
- El quote publica la demanda en porcentaje directo; la captura real confirmó
  que la UI cambió de `1300%` a `130%`.
- La validación del target de venta acepta únicamente el sentinel self `0` o
  el ObjId del personaje activo; NPC, distancia y zone group siguen validados.
- Quote y payout usan la misma etapa de frescura y el mismo market ratio.
- La fecha del item se transmite como Unix time en `WZCreateDoodadPacket`, en
  lugar del cero anterior.
- Los correos de vendedor/crafter se finalizan antes de registrarse. Un fallo
  de registro o consumo revierte los correos registrados en memoria.
- Tras el éxito se registra template, destino, ratio, frescura, payouts y
  moneda para auditoría de la prueba real.
- `CSSaveUIDataPacket` tolera paquetes tardíos después de limpiar
  `ActiveChar`.
- `/delivertradepackmails [jugador]` libera sólo recompensas
  `SysSellBackpack` ya creadas y todavía futuras. Actualiza el mismo mail,
  notifica al jugador conectado y no puede duplicar payout ni adjuntos al
  repetirse.

La persistencia actual de items/correos no ofrece una transacción MySQL única.
El rollback añadido cierra la ventana de mutación parcial dentro de la
arquitectura existente, pero no debe describirse como atomicidad durable ante
caída abrupta del proceso.

## Validación automatizada

- `dotnet build AAEmu.slnx --no-restore --nologo --verbosity:minimal`:
  correcto, 0 errores.
- `dotnet test AAEmu.UnitTests\AAEmu.UnitTests.csproj --no-restore`:
  1.322 correctas, 0 fallos, 0 omitidas.
- Cobertura nueva: límites inclusivos de las cinco etapas y post-límite,
  grupo inexistente, aceptación/rechazo de bundle, roundtrip exacto del packet
  ratio, rechazo de más de 20 quotes, sentinel self de venta, filtrado e
  idempotencia de liberación de mails y conversión nativa de `/speed 1..1000`.
- `git diff --check`: limpio.

Las advertencias NuGet y de análisis ya existentes continúan visibles; no
están causadas por este dominio.

## Despliegue del checkpoint

Se reconstruyó `aaemu-world:10.0.2.13-r575-local` y se recreó únicamente el
servicio `game`. DB y Login permanecieron saludables. En la validación inicial
las Zones nativas se levantaron secuencialmente para evitar la carrera conocida:

| Zone | Hora `ZoneLoaded` | Estado |
|---|---:|---|
| 142 | 23:34:23 | `loadedCount=1` |
| 178 | 23:35:56 | `loadedCount=2` |
| 179 | 23:36:38 | `loadedCount=3` |

Desde el cierre de este checkpoint, el lifecycle de `AAEmu.ZoneHost.exe` queda
bajo control exclusivo del usuario mediante el panel. Codex puede comprobar
logs, conexiones y `ZoneLoaded`, pero no iniciar, detener ni reconciliar Zones.

## Aceptación jugable de la ruta principal

Las entregas reales posteriores al último build completaron el recorrido. La
primera venta quedó así:

- `00:03:10`: quote de NPC `17971`, item `31856`, demanda `130`;
- `00:03:12`: `CSSellBackpackGoods` con `npcObjId=712`,
  `characterObjId=0`, sin bytes sobrantes;
- `SCItemTaskSuccess` con tarea `SellBackpack`;
- payout: `107.622` cobre (`10g 76s 22c`), frescura `850` = 85%,
  market ratio `130`, sin reparto a un crafter distinto;
- autosave `00:07:10`: un mail actualizado y el item vendido eliminado.

El autosave de las pruebas confirmó cinco filas tipo `19`
(`SysSellBackpack`) para `Wingsjuanka`:

| Mail | `received_date` UTC | Ratio | Dinero adjunto |
|---:|---|---:|---:|
| 10000 | 2026-08-19 08:03:13 | 130% | 107622 |
| 10001 | 2026-08-19 08:08:55 | 129% | 106795 |
| 10002 | 2026-08-19 08:09:13 | 128% | 105967 |
| 10003 | 2026-08-19 08:09:24 | 128% | 105967 |
| 10004 | 2026-08-19 08:09:37 | 128% | 105967 |

Cada fecha era exactamente ocho horas posterior a su venta. La API ordinaria
de listado no mostraba esos mails antes de su hora porque filtra
`RecvDate <= DateTime.UtcNow`; esto era entrega diferida, no pérdida. A las
`00:36:14`, `/delivertradepackmails Wingsjuanka` liberó las cinco filas
existentes y notificó los cinco correos al cliente conectado. Después de
cobrarlos, `aaemu_game.mails` quedó con cero filas y no apareció ningún mail ni
adjunto duplicado.

El item concreto `16777339` ya no existe en `aaemu_game.items`. El estado de
labor persistido después de la operación es 4.021 global y 135 local.

## Incidencia de zona descubierta durante la certificación

La zona `140` es `w_garangdol_plains_1` (Dewstone Plains) y la `272` es
`e_hasla_2` (Hasla). La aparición real en Hasla al iniciar la Zone `272`
demostró que `PlayerEnterService` resolvía correctamente la fila persistida;
el personaje se había guardado de forma incorrecta en `272`.

La causa estaba en los teletransportes GM anteriores. `/teleport` y `/move`
enviaban `SCTeleportUnit` y movían el cliente, pero no actualizaban el
`Transform` autoritativo de Game ni ejecutaban el handoff
`WZUnitRemoved -> WZUnitState`. Además, `CSTeleportEndedPacket` ignoraba las
coordenadas confirmadas por el cliente. El movimiento posterior podía seguir
enrutándose a la Zone de origen mientras la posición visible y la persistida se
separaban.

El build `sha256:7df1ede2f7c8ced5f237d4ebdb8085084227de9a1e7a9a8f7ad2459b9410a5d6`
corrige ambas rutas:

- el comando resuelve y exige una Zone destino cargada, desmonta, actualiza
  primero Game y ejecuta el handoff antes de mover el cliente;
- `CSTeleportEndedPacket` aplica la posición reconocida como red de seguridad;
- una coordenada fuera del mundo o una Zone no cargada se rechaza y devuelve
  al personaje a su transformación autoritativa anterior.

La aceptación jugable requiere comprobar `142 -> 140 -> 142`, observar los dos
handoffs en el log y confirmar que `characters.zone_id` coincide después de
cada guardado. Hasla `272` queda como control negativo: no debe recibir al
personaje en ese recorrido.

## Reparación auxiliar del baúl del Strada

Durante las pruebas de transporte, el Strada template `1198` quedó con la tapa
visualmente cerrada mientras el action bar ofrecía `Close Chest` (`41725`). La
traza de cinco pulsaciones seguidas probó que todas llegaban a
`CSStartSkill -> WZSkillStarted/Fired/Ended`, pero sólo tres alcanzaban el
efecto final. No era un fallo de input ni de ZoneAuthority.

La SQLite AA10 autoritativa cierra el grafo nativo:

- `slave_bindings` adjunta al Strada el slave `865`, `Strada Rear Cover`, en
  attach point `21`;
- el hijo nace con buff `25385`, tag `5008` (`Strada Trunk`);
- `Open Chest` (`41719`, plot `4242`) y `Close Chest` (`41725`, plot `4245`)
  hacen una búsqueda esférica de 4 m, `UnitTypeFlag.Slave`, máximo un target y
  condición `BuffTag=5008`;
- el modelo padre `2845` no resuelve su helper `$sail0` desde el pak/cache y
  registra `has no attach point information`; el hijo sigue existiendo en el
  grafo de transforms, pero su selección dependía exclusivamente del índice
  regional durante movimiento dedicado;
- el buff de cierre `24729` tiene dos triggers `Started`: agent `0 -> 0`
  limpia el tag `4266` en la tapa y agent `3 -> 3` lo limpia en el original
  source, el Strada. La segunda limpieza retira `24887` (`chest open`), que es
  el buff usado por `buff_mount_skills` para habilitar `Close Chest`.

AA10 cargaba sólo los filtros de target de `buff_triggers` e ignoraba
`source_agent_id`, `target_agent_id` y los filtros owner/source. En ejecución
trataba ambos triggers como `owner -> owner`: la animación del hijo podía
cerrar, pero el padre conservaba `24887`, dejando el action bar desincronizado.

La reparación es genérica y guiada por datos, sin IDs hardcodeados:

1. los plots esféricos incorporan los slaves directamente adjuntos a sus
   candidatos cuando el índice regional no los devuelve, conservando radio,
   cono, relación, type flag y condiciones AoE;
2. `buff_triggers` carga y resuelve los agentes nativos r575:
   `0=owner`, `1=event source`, `2=event target`, `3=original source`, además
   de los filtros de tags owner/source/target;
3. se añadieron cuatro tests de regresión para resolución de agentes,
   inclusión del hijo adjunto, límite de radio y deduplicación.

El comparador AA8 se usó sólo para corroborar el significado de los cuatro
agent ids; la autoridad de skills, plots, tags y bindings fue la SQLite AA10.
El build completo y las 1.322 pruebas quedaron verdes. Se desplegó únicamente
Game con la imagen
`sha256:cdc40c764c4c49a9e51c7c93ea7b457f4f5a0524c4e304abae1a9e94648e6d35`;
DB y Login no se recrearon y el usuario mantiene control exclusivo de las
Zones desde el panel.

Aceptación jugable del Strada:

1. invocar el vehículo y alternar abrir/cerrar cinco veces detenido;
2. moverlo varios metros y repetir cinco veces;
3. comprobar que tapa e iconos `Open Chest`/`Close Chest` cambian juntos;
4. depositar y retirar un pack de cada uno de los cuatro slots;
5. confirmar en logs que cada pulsación alcanza el efecto final y que al cerrar
   se elimina el estado abierto del Strada padre.

Aceptación completada por el usuario el 18 de agosto de 2026: el baúl del
Strada alternó correctamente y permaneció funcional durante la prueba de
transporte. La ruta terrestre Dewstone funcionó de extremo a extremo y el oro
observado aumentó con la proficiency comercial del personaje. Con esta prueba
quedan aceptados el vehículo auxiliar, la entrega, el correo diferido y la
progresión visible del payout para el caso Dewstone.

## Certificación ampliada pendiente

Para cerrar la matriz completa del plan debe ejecutarse con el build desplegado:

1. repetir `/delivertradepackmails Wingsjuanka` y verificar que libere cero;
2. certificar el handoff de teletransporte `142 -> 140 -> 142` con el nuevo
   build y comprobar `/speed 1000` seguido de `/speed reset`;
3. repetir con un pack recién fabricado para validar 115% y la conservación de
   timestamp al subir/bajar del vehículo bajo el build nuevo;
4. ejecutar los rechazos del plan y comprobar cero mutaciones parciales.

Checkpoint demostrado en cliente: la ventana abre sin cierre,
selecciona el template `31856`, muestra demanda `130%` y el botón Confirm envía
`CSSellBackpackGoods 0x06F`. La traza exacta fue `npcObjId=711`,
`characterObjId=0`, `unreadBytes=0` antes del fix; la venta final usó el nuevo
ObjId de NPC `712` y el mismo sentinel self.

Rollback del runtime: reconstruir la imagen desde el commit anterior y recrear
sólo `game`; después el usuario relanza desde su panel el perfil de Zones que
corresponda. No requiere modificar la SQLite retail, `game_pak`, MySQL ni los
binarios Zone.

## Auditoría reproducible del payout r575 — 30 de agosto de 2026

La full autoritativa y la compact retail coinciden para el pack `31856`:

- `item_prices.refund=10000`;
- `specialty_bundle_items.profit=33263`, `ratio=2488` para bundle `10`;
- `item_backpacks.freshness_group_id=5`;
- etapas inclusivas `900/1150`, `3600/1050`, `10800/900`, `86400/850` y
  `172800/650`.

El precio base resultante es `92758` cobre. Con demanda `130%` e interés de
correo `5%`, la matriz golden conectada al mismo helper usado por
`SellSpecialty` es:

| Antigüedad | Frescura | Payout |
|---:|---:|---:|
| `0..900 s` | 115% | `145607` (`14g 56s 07c`) |
| `901..3600 s` | 105% | `132945` (`13g 29s 45c`) |
| `3601..10800 s` | 90% | `113953` (`11g 39s 53c`) |
| `10801..86400 s` | 85% | `107622` (`10g 76s 22c`) |
| `>=86401 s` | 65% | `82300` (`8g 23s 00c`) |

Las pruebas demuestran también que un `CreateTime` UTC de craft y el mismo
valor recuperado por MySQL como `DateTimeKind.Unspecified`, vendido diez
minutos después, seleccionan ambos la etapa 115%. Por tanto, una venta inmediata
que produzca `107622` no es compatible con los inputs nominales: el runtime
recibió una antigüedad mayor de `10800 s`, una fecha de creación distinta, o no
estaba ejecutando el build esperado. Una aceptación posterior debe registrar
item instance id, `created_at`, hora de venta y edad calculada en la misma línea
de log.

La fórmula `formulas.id=49` del cliente r575 es:

```text
((item_refund + (ratio * profits)) * specialty_gold * merchant_price_ratio
 * extra_buff * freshness * specialty_ratio)
```

El simulador cubre los tres multiplicadores explícitos y confirma su orden antes
del interés del correo. El runtime los conserva por ahora en `1.0`: todavía no
se han cerrado sus providers/escalas nativos. En particular, la observación
histórica de que el payout aumentó con proficiency no puede atribuirse a la
implementación actual, porque Comercio sólo modifica el coste de labor. Queda
como evidencia dinámica por reconciliar, no como cierre de
`merchant_price_ratio`.

Resultado automatizado: `SpecialtyManagerTests`, 30/30 verdes. La suite completa
ejecutó 1.698 casos: 1.697 pasaron y falló únicamente `MoneyTest` por
`UnableToFindRecipient`, fuera del dominio specialty; los 30 casos specialty
constan verdes en el reporte del mismo run.
