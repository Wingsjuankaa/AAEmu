# Reactivación AA10: regalos diarios y ArchePass

Fecha de reconstrucción: 2026-08-20
Última validación incremental: 2026-09-03
Cliente objetivo: ArcheAge Returns 10.0.2.13 r575
Servidor objetivo: `Wingsjuankaa/AAEmu:rama_10`

## Resultado y alcance

Se reactivaron aditivamente los bits `account_attendance` (144) y `arche_pass`
(98). No se retiró ningún flag ni controlador de inventario ya habilitado.

Account Attendance queda funcional de extremo a extremo:

- carga el catálogo retail `account_attendance_rewards`;
- muestra la cuadrícula nativa de 28 posiciones mensuales (4x7);
- persiste por cuenta, año, mes y día acumulado;
- permite un reclamo por día calendario UTC;
- impide duplicados también entre dos personajes/sesiones de una cuenta;
- pre-valida que todas las recompensas entren en la bolsa;
- entrega el premio normal y el hito adicional de los días 7, 14, 21 y 28;
- si la bolsa no tiene capacidad, rechaza sin consumir el reclamo.

La Fase 4C completa el núcleo de ArchePass en el código objetivo: carga categorías,
pases y tiers retail; persiste por personaje; aplica buy/start/drop/expiry/
complete; cobra la moneda configurada; consume el upgrade item; mantiene fronteras
normal/premium; reclama tiers en orden con preflight de bolsa; y acredita los 325
actos `QuestActSupplyArchePassPoint` sólo cuando existe un pase persistido en
progress. El estado y el cierre del ledger de recompensa se confirman en la misma
transacción de guardado del personaje.

La mecánica de misiones del ArchePass sigue separada: no se habilitó
`archePassMissionAccount` ni el cambio/reroll. Las claves retail 277–280 existen en
`enum_content_configs`, pero no tienen filas de valor en `content_configs`; por
eso no se inventaron contadores, límites, coste ni item de inicialización. Este
corte dejó la migración preparada, sin aplicarla ni desplegar/reiniciar el runtime.

## Contrato nativo cerrado

### Account Attendance

| Dirección | Opcode | Cuerpo |
|---|---:|---|
| C2G | `0x1B0` | `u64 type`, `u32 dayOffset` |
| C2G | `0x1B1` | sin cuerpo |
| G2C | `0x2C9` | 31 entradas fijas `{i64 unixTime, bool archelife}` |
| G2C | `0x2CA` | `bool result`, `i64 unixTime`, `bool archelife` |
| G2C | `0x2CC` | `i32 type`, `bool byMail` |

El servidor no confía en `type` ni `dayOffset` para decidir qué premio entregar:
calcula el siguiente índice desde su ledger persistente y el mes UTC vigente.

### ArchePass

El bloque G2C r575 consecutivo quedó declarado:

| Opcode | Packet |
|---:|---|
| `0x33D` | `SCArchePassesPacket` |
| `0x33E` | `SCCompletedArchePassesPacket` |
| `0x33F` | `SCUpdateArchePassPacket` |
| `0x340` | `SCCompletedArchePassPacket` |
| `0x341` | `SCArchePassMissionCountPacket` |
| `0x342` | `SCArchePassChangeMissionPacket` |

El registro nativo de estado ocupa 32 bytes en memoria x64 por alineación, pero
ese layout no es su contrato de red. `FUN_39a3d7e0` (RVA `0xA3D7E0`) serializa,
en orden, `type:i32`, `lastRewardTier:i32`, `lastPremiumRewardTier:i32`,
`point:i64`, `premium:bool`, `status:u8`. El serializer admite hasta diez
registros por página, no diez en total. La carga/reconexión usa resincronización
completa paginada.

La reconstrucción binaria posterior cerró además los diez valores nativos de
`SCUpdateArchePass.reason`. El callback retail en RVA `0x0BD290` los transforma en
los eventos Lua consecutivos `ARCHE_PASS_UPDATE_POINT` a `ARCHE_PASS_RESETED`:

| Reason | Evento retail |
|---:|---|
| 1 | `ARCHE_PASS_UPDATE_POINT` |
| 2 | `ARCHE_PASS_UPDATE_REWARD_ITEM` |
| 3 | `ARCHE_PASS_DROPPED` |
| 4 | `ARCHE_PASS_STARTED` |
| 5 | `ARCHE_PASS_OWNED` |
| 6 | `ARCHE_PASS_BUY` |
| 7 | `ARCHE_PASS_UPGRADE_PREMIUM` |
| 8 | `ARCHE_PASS_EXPIRED` |
| 9 | `ARCHE_PASS_COMPLETED` |
| 10 | `ARCHE_PASS_RESETED` |

`CSArchePassBuy` debe responder con el estado nuevo `Owned` y `reason=6`. La
respuesta anterior enviaba sólo `SCArchePassesPacket`: cobraba y persistía el pase,
pero no disparaba el evento incremental con el que la UI inserta y selecciona el
pase recién registrado. Desde 2026-09-03 la compra usa el paquete incremental
exacto; el listado completo queda reservado para carga, reconexión y rechazo.

El registro no es una ranura única. `X2ArchePass:IsFull()` enlaza con la rutina
retail que cuenta estados `Owned` y `Progress` y sólo devuelve lleno cuando el
conteo alcanza seis. La UI lo confirma con «You can have up to 6 registered
passes». El servidor conserva por separado el invariante de un único estado
`Progress`. El primer corte mantenía erróneamente una sola entrada abierta: si el
personaje ya poseía un pase persistido, rechazaba en silencio cualquier compra
adicional antes de cobrarla. La política y la validación de persistencia usan
ahora capacidad seis.

La evidencia se obtuvo con
`reconstruccion_cliente_10/scripts/inspect_msvc_rtti_vtable.py`, que resuelve RTTI
MSVC x64 y desensambla serializers sin modificar el binario retail, y con la
decompilación reproducible de `FUN_393416c0` → `FUN_390bd290` sobre el
`x2game.dll` SHA-256 `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.

## Persistencia

La migración `SQL/updates/2026-08-19_aaemu_game_account_attendance_claims.sql`
crea `account_attendance_claims` con:

- PK `(account_id, campaign_year, campaign_month, day_count)`;
- unique `(account_id, claim_day)`;
- `claimed_at`, `claimed_by` e `is_archelife` auditables.

La misma tabla está incluida en `SQL/aaemu_game.sql` para instalaciones nuevas.

La Fase 4C añade, sin aplicarla al MySQL activo, la migración
`SQL/updates/2026-08-20_aaemu_game_arche_pass_states.sql`. La tabla
`character_arche_passes` conserva punto, status, premium y las fronteras de claim
normal/premium por `(character_id, arche_pass_id)`. Si la tabla no existe, el
manager falla cerrado: muestra estado seguro y rechaza mutaciones/puntos positivos.

## Campaña operacional agosto 2026

El corte retail no contenía agosto de 2026. Se usó
`Scripts/PatchAa10AccountAttendanceCampaign.py` para proyectar julio de 2026 como
agosto: 28 premios visibles y cuatro hitos adicionales. Los días 29–31 no se
publican porque `attendance.alb` fija `attendMax` a `ATTENDANCE_VER_COUNT *
ATTENDANCE_HORI_COUNT`, una cuadrícula 4x7. El script:

- exige el nombre `compact.sqlite3`;
- valida el esquema y el origen 31+4;
- proyecta el layout nativo 28+4;
- rehúsa sobreescribir un mes existente;
- crea respaldo antes de escribir;
- usa IDs nuevos y una transacción;
- permite recortar de forma explícita un target 31+4 ya creado;
- ofrece `--move-source` para producir un SQLite de igual tamaño para `game_pak`;
- ejecuta `PRAGMA quick_check` y comprueba 32 filas al final.

Artefactos operacionales, no versionados:

| Destino | SHA-256 antes | SHA-256 después | Respaldo |
|---|---|---|---|
| Game `.server_files/AAEmu.Game/Data/compact.sqlite3` | `2a16e2dfa373b628a929d5c3b7234fff42ad8afdcb0c94f2584c2d954400c7be` | `da36ab24d439eaf7aef8e638a2797194276bbc7c8aa8dd4e787847e286ecfacd` | `compact.sqlite3.pre-attendance-native28-202608.bak` |
| cliente suelto `game/db/compact.sqlite3` | `b363b717bc33b40ff93566abc3ee951c7b0b97cfcd1f2fc1fad1ff89ae25be62` | `8b1619b11702892aee02008deccd70d6a2a206e2dea57482bf52201c19ce9849` | `compact.sqlite3.pre-attendance-native28-202608.bak` |

## Proyección efectiva dentro de `game_pak`

El diagnóstico manual demostró que r575 sigue resolviendo
`game/db/compact.sqlite3` desde `game_pak` aun con `-devmode`; por eso la primera
copia suelta no alcanzaba a crear la pestaña. Se hicieron dos reemplazos exactos
con `Tools/PakEntryReplace`, que exige SHA-256 previo, conserva el tamaño y vuelve
a exportar la entrada para verificarla:

| Entrada | Bytes | SHA-256 antes | SHA-256 después |
|---|---:|---|---|
| `game/db/compact.sqlite3` | 440.823.808 | `4B2771E24BE56CD3B2223F7EF5EE1B0C0D8A5002A95227E38B0A33EEEB96839D` | `026A40B71824ED341B8F6981C895BA2BFE53B5F6B3687B7A2F2325E9FE9A829F` |
| `game/scriptsbin64/x2ui/eventcenter/eventcenter.alb` | 18.813 | `C88D59E1423885C3DE0609A303932C6E3439FCD11A16BDC2090F9E8187035603` | `E9C037CBAAFCF6D1806BAB9071A7D20AE5CDE1F522DEAC2BE9494691998FE6FF` |

El segundo cambio modifica únicamente el `LOADBOOL true` del closure de
validación de `CreateFollowMeWnd` (offset decimal 3616) a `false`. Así desaparece
la pestaña china `关注有礼` sin reemplazar el Event Center por el de ArcheRage ni
retirar ninguna pestaña de Returns.

`game_pak` conservó 68.963.258.880 bytes y cambió de
`A696E303162AD2054918F5B9AE2ED71CFCD71A3C53C7EE6ACE677D38300407C9` a
`AB3B86E694CFC0141453AD9B734BABEE67019C58D8E0B52498036ABC0DCBCBF0`.
Los reemplazos y originales exactos quedaron en
`artifacts/client-patches/eventcenter-attendance-20260819`.

No se modificó `data/sqlite/authoritative/game_decrypted.sqlite3` ni otro baseline
forense.

## Validación automática

Comandos ejecutados:

```powershell
dotnet build AAEmu.Game/AAEmu.Game.csproj --no-restore
dotnet test AAEmu.UnitTests/AAEmu.UnitTests.csproj --no-restore -- --maximum-parallel-tests 8 --no-progress
python -m py_compile Scripts/PatchAa10AccountAttendanceCampaign.py
python -m py_compile Scripts/PatchAa10EventCenterFollowMe.py
```

Resultado actual de Fase 4C: compilación integral Release correcta y `1437/1437`
pruebas correctas. Las pruebas de ArchePass fijan umbrales, saturación, claims
secuenciales, salto de tiers vacíos, cierre normal/premium y límite wire de diez
registros por página. Stage 40 v6 reproduce 1.318/1.397 referencias Fase 4
implementadas y 79 bloqueadas; las 325 de ArchePassPoint quedan cerradas.

## Despliegue observado

Se reconstruyó y recreó exclusivamente el servicio Compose `aaemu10-game-1`; Login,
DB y los procesos Zone no fueron reiniciados. La migración fue aplicada y la tabla
quedó vacía antes de la primera prueba (`0` claims).

El arranque confirmó:

```text
Loaded 96 Account Attendance campaigns (2732 reward rows)
fset: ... byte12=2c ... byte18=1b ...
Enabled Features: ... arche_pass ... account_attendance ...
TCP server listening start on 0.0.0.0:1239
GameNetwork - Network started
```

La Zone que estaba abierta se desconectó al recrear Game y no volvió a registrarse
automáticamente. Debe arrancarla el operador después de que Game esté listo; no se
intervino su ciclo de vida desde este cambio.

## Prueba manual

1. Cerrar completamente el cliente para que reabra el `game_pak` actualizado.
2. Entrar con una cuenta sin reclamo de asistencia para el día UTC vigente.
3. Abrir Event Center y comprobar la pestaña/calendario de regalos diarios.
4. Reclamar el día 1: debe aparecer el item `44283 x1` y marcarse una sola casilla.
5. Intentar reclamar otra vez el mismo día: debe rechazarse y conservar el estado.
6. Reloguear con otro personaje de la misma cuenta: debe verse la misma casilla.
7. Tras aplicar la migración y desplegar en una sesión E2E autorizada, abrir
   ArchePass y comprar/iniciar un pase retail disponible.
8. Completar una quest con `QuestActSupplyArchePassPoint`, verificar el aumento y
   reloguear para confirmar persistencia.
9. Reclamar el siguiente tier normal, subir a premium con su item y comprobar que
   ambos tracks conservan fronteras independientes.
10. Verificar que ChangeMission continúa rechazado y en cero: su configuración
    retail no tiene valores demostrados.

## Rollback operacional

Para desactivar la UI sin borrar datos, poner `account_attendance` y `arche_pass` en
`false` dentro de `Configurations/Features.json` y recrear Game. Los reclamos quedan
conservados.

Para revertir la proyección del cliente, cerrar el cliente y usar
`Tools/PakEntryReplace` con los originales exactos del directorio de artefactos:
el compact de SHA `4B2771...` y el `eventcenter.alb` forense de SHA `C88D59...`.
El reemplazador verifica hash y tamaño antes y después. Para revertir el catálogo
del Game, detener Game y restaurar el respaldo operacional correspondiente. No
borrar ni reemplazar el baseline forense. La tabla MySQL puede permanecer: es
inerte con el flag apagado.

La tabla `character_arche_passes` también es inerte con el flag apagado. Para
activar 4C debe aplicarse primero su migración y luego desplegar Game; esta sesión
no realizó ninguna de las dos acciones.

## Despliegue incremental 2026-09-03

La corrección del registro visible se compiló en Release y pasó `1724/1724`
pruebas. Se reconstruyó y recreó únicamente `aaemu10-game-1` con la imagen
`sha256:472f1457dfdfed9dc36c102b46e454479fcef0e63b97a385ea6e44aa55b608e0`.
El rollback inmediato es
`aaemu-world:rollback-pre-archepass-buy-ui-20260903-132900`.

El nuevo Game quedó healthy, cargó 97 pases y 3.028 tiers, mantuvo el feature
`arche_pass`, abrió GameNetwork y se registró correctamente en Login. Los
contenedores Login y DB no fueron recreados. Codex no inició ni relanzó Zone.

La prueba manual posterior reveló un rechazo al registrar un segundo pase. La base
confirmó que `Dannia` ya conservaba el pase 48 como `Owned`; no se descontó oro en
el nuevo intento. La causa fue la política servidor de una sola ranura, no el
serializer de `SCArchePassesPacket`. La corrección siguiente eleva el límite a seis
estados registrados y añade regresiones para 5/6/7 entradas, estados terminales y
el invariante de un solo pase activo.

La corrección de capacidad pasó el build integral Release y `1730/1730` pruebas.
Se desplegó exclusivamente Game con la imagen
`sha256:452cc81cd99700314677793da6f19c9cccfce2c08bc74f73bcf01cfdf1d9705d`;
rollback inmediato
`aaemu-world:rollback-pre-archepass-capacity-fix-20260903-112653`. Game cargó
97 pases/3.028 tiers, abrió la red, quedó healthy y registró GameServer 1 en Login.
Login y DB conservaron sus contenedores. La recreación desconectó la Zone enlazada
y Codex no la inició ni relanzó.

El segundo gate manual volvió a dejar `Adventurer Growth` en `Register`. La traza
servidor demostró dos `CSArchePassBuy` con `type=88`, ambos rechazados antes del
cobro y antes de cualquier `SCUpdateArchePass`; la tabla seguía conteniendo sólo
el pase 48. El bloqueo ya no era capacidad ni protocolo de respuesta, sino
`IsAvailableAt`: type 88 es la única fila de las 97 cuyo `ed_year` es `23` en vez
de un año de cuatro dígitos, y el loader la convertía sin evidencia a 2023.

En el `x2game.dll` r575 SHA-256
`405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`,
`GetStatus` (`FUN_390bcb90`, RVA `0x0BCB90`) resuelve la fecha mediante
`FUN_39a39da0` (RVA `0xA39DA0`) y no contiene una conversión de año corto a
2000. La observación retail es decisiva: la UI muestra literalmente `23.03.30`,
lo considera comprable y emite type 88, mientras las filas vencidas con año
completo muestran el estado expirado. El loader conserva ahora los años de
cuatro dígitos y trata el único año corto inválido como timestamp ausente, sin
modificar compact ni cliente. La compra registra además una traza de commit con
tipo, estado y ocupación 1–6 para correlacionar el siguiente gate.

Este tercer corte pasó build integral Release y `1731/1731` pruebas. Se desplegó
únicamente Game con imagen
`sha256:053337a5d35b5a503b758fb7a8c59fe8e803bca2cf8bd8035f1276539d0df8c7`;
rollback `aaemu-world:rollback-pre-archepass-type88-date-fix-20260903-114605`.
El startup confirmó el cambio específico de 28 a 29 pases comprables, mantuvo
97 pases/3.028 tiers, `arche_pass` activo, Game healthy y GameServer 1 registrado.
Login y DB fueron preservados. Zone se desconectó al recrear Game y no fue
iniciada ni relanzada por Codex.

El tercer gate alcanzó por primera vez la transacción exitosa: a las `15:57:32`
Game recibió `CSArchePassBuy(type=88)`, persistió `Owned`, registró ocupación
`2/6` y emitió `SCUpdateArchePass 0x33F`. A las `15:57:35` rechazó correctamente
el segundo clic porque el pase ya estaba `Owned`; MySQL confirmó los pases 48 y
88. La UI, sin embargo, siguió mostrando `Register`, incluso tras resincronizar.

La decompilación directa del `x2game.dll` r575 cerró el último error: el servidor
había confundido el layout alineado en memoria con el wire de `FUN_39a3d7e0`.
El estado salía como `type, point, status, premium, lastRewardTier,
lastPremiumRewardTier`, pero el cliente espera `type, lastRewardTier,
lastPremiumRewardTier, point, premium, status`. `FUN_39aba690`
(RVA `0xABA690`) confirmó además que `SCUpdateArchePass` agrega después
`reason:u8`, `diffPoint:i32`, `allDone:bool`. Se corrigió el serializer compartido
por `0x33D` y `0x33F` y se fijaron fixtures binarios no nulos para impedir que el
orden vuelva a confundirse.

El cuarto corte pasó build Release y la suite completa `1731/1731`. Se desplegó
únicamente Game con imagen
`sha256:fdf9a0a20225cdf09f783b5699e8be72c09a734ef077869f1f53d39f16e16330`;
rollback inmediato
`aaemu-world:rollback-pre-archepass-wire-order-20260903-120528`. El arranque
cargó 97 pases/3.028 tiers, mantuvo 29 comprables, quedó healthy y registró
GameServer en Login. Login y DB conservaron sus contenedores y MySQL mantuvo
intactos los pases 48 y 88 de Dannia. Zone no fue iniciada ni relanzada por Codex.

El cuarto gate confirmó que el registro visible ya estaba reparado: type 88
apareció con la marca amarilla `Owned`. Al pulsar el botón, `16:46:25` registró
`CSArchePassStart 0x1FA` y MySQL avanzó type 88 a `Progress` (`status=2`), pero el
panel principal permaneció vacío. La causa fue una respuesta semánticamente
incompleta: `TryStart` enviaba la página de carga `SCArchePasses 0x33D`, que no
dispara un evento Lua. El consumer r575 exige el incremental
`SCUpdateArchePass 0x33F` con `reason=4`, que emite `ARCHE_PASS_STARTED` y ejecuta
`parent:Update()` en `arche_pass_info.alb.lua`. El éxito de Start usa ahora ese
contrato; la página completa queda para carga/relogin y rechazos.

El quinto corte pasó el build integral Release y `1732/1732` pruebas. Se desplegó
únicamente Game con imagen
`sha256:2df0ca029159bee06870eac1434e98d2ed9f65d137668cff4665a3834db8bc51`;
rollback inmediato
`aaemu-world:rollback-pre-archepass-start-event-20260903-124946`. El arranque
cargó 97 pases/3.028 tiers (29 comprables), abrió GameNetwork, quedó healthy y se
registró correctamente en Login. Login y DB conservaron sus contenedores. MySQL
confirmó que Dannia mantiene type 48 como `Owned` y type 88 como `Progress`, por
lo que la prueba visual no debe volver a comprar ni iniciar el pase. La recreación
de Game desconectó la Zone enlazada y Codex no la inició ni relanzó.

El gate siguiente registró `Hellwraith Kirin` (type 19) a las `18:09:59`: Game
cobró, persistió `Owned` como tercera entrada y envió `SCUpdateArchePass`
`reason=6`. La estrella amarilla probó que la compra y su actualización visual
sí llegaron. El panel principal conservó correctamente type 88 porque registrar
no equivale a iniciar; el Lua usa el mismo botón para ambas fases y sólo envía
`StartPass(type)` en el segundo clic, cuando `GetStatus(type) == APS_OWNED`.

La frontera real estaba en `TryStart`: el servidor rechazaba empezar un pase si
ya existía otro en `Progress`, pese a que la propia UI r575 promete que el pase
activo será pausado. El sexto corte implementa la transición atómica
`Progress → Owned` para el anterior y `Owned → Progress` para el nuevo,
conservando puntos, premium y fronteras cobradas. Envía primero el anterior con
`reason=5` (`ARCHE_PASS_OWNED`) y después el nuevo con `reason=4`
(`ARCHE_PASS_STARTED`), ya que el consumer nativo sólo sobrescribe el registro
del type recibido antes de emitir cada evento.

El sexto corte pasó build Release y `1736/1736` pruebas. Se desplegó únicamente
Game con imagen
`sha256:f8a698878264e1eee4db6effc17f5aca2a057163a0d09ac02e1877a9bb155284`;
rollback inmediato
`aaemu-world:rollback-pre-archepass-switch-20260903-141820`. El arranque cargó
97 pases/3.028 tiers (29 comprables), abrió GameNetwork, quedó healthy y se
registró en Login. Login y DB conservaron sus contenedores. Antes del gate,
MySQL mantiene type 19 y 48 `Owned`, y type 88 `Progress` con 3.500 puntos.
Codex no inició ni relanzó Zone.

## Comando GM de puntos (2026-09-03)

El usuario confirmó el cambio visible de ArchePass y pidió una herramienta para
probar XP. Se añadió `/archepass addpoints self <cantidad>`: sólo el personaje
ejecutor, acceso efectivo GM >= 100, entero positivo <= 2147483647 y pase válido
en `Progress`. No compra, inicia, mejora a premium ni cobra recompensas. Es
infraestructura de pruebas del servidor, no una mecánica retail nueva.

Reutiliza la progresión central bajo el lock del personaje y el límite del último
tier. La respuesta informa cantidad aplicada (puede ser menor que la solicitada),
total y tier; el log registra personaje/cuenta/pase, solicitud y delta real.
Persiste con el autosave/logout normal de `Character.Save`, conservando su
transacción conjunta con el ledger de quests; no se ejecuta SQL separado.

El éxito de suma de puntos, también para quests, emite `SCUpdateArchePass 0x33F`
con `reason=1`, delta aplicado y `allDone=false`. Autoridad: consumer r575
`FUN_390bd290` (RVA `0x0BD290`), que actualiza el registro antes de emitir
`ARCHE_PASS_UPDATE_POINT` y, al cruzar umbral, `ARCHE_PASS_UPDATE_TIER`.
No se usa una página inicial para refrescar un panel ya abierto.

Validación: build integral Release sin errores y suite `1742/1742`, sin omitidos.
Los nuevos tests cubren parser, límites numéricos, destino self, ausencia de
personaje, acceso GM predeterminado, saturación/delta y fixture binario exacto
del incremento. Permanecen advertencias de dependencias y analizadores previas.

Gate manual: entrar con un pase iniciado, abrir ArchePass, ejecutar
`/archepass addpoints self 1000` y comprobar mensaje, barra/tier inmediato y
persistencia después de relog. Las recompensas deben seguir pendientes de
reclamo manual. Codex no ejecutó el comando sobre el personaje durante el despliegue.

Despliegue exclusivo de Game completado con imagen
`sha256:a31c65c8e3405e9c30aa1d501b9062be5ce8ccdd6cbbd7b386e64e83a0c2eadc`;
rollback `aaemu-world:rollback-pre-archepass-gm-points-20260903-151015`.
Arranque `19:12:18 UTC`: GameNetwork abierto, `Server started`, registro en Login
y health healthy; 97 pases/3028 tiers, 29 comprables. Scripts usa Reflection por
defecto, sin errores de ScriptReflector; ArchePassCmd está en ambos ensamblados
Game desplegados y su fuente tiene SHA256 idéntico en host y contenedor.
Login/DB conservaron sus contenedores. Zone quedó desconectada durante la
recreación de Game y no fue iniciada ni relanzada por Codex. Siguen los errores
preexistentes de definiciones Smelting 29–32, fuera del alcance de este corte.

## Refresco de recompensas cobradas — 2026-09-03

La prueba del usuario confirmó puntos y tier en tiempo real, pero la recompensa
1 seguía habilitada después de cobrar y la 2 permanecía deshabilitada. Correlación
del intento: `19:18:34 UTC`, `CSArchePassGetRewardItem 0x1F8` →
`SCItemTaskSuccess 0x0BC/TodReward` → página `SCArchePasses 0x33D`, sin incremental
de recompensa. MySQL confirmó para Dannia/type 19: `point=7000`, `status=2`,
`last_reward_tier=1`, `last_premium_reward_tier=0`. Los clics repetidos a tier 1
fueron rechazados por frontera secuencial; no entregaron premios adicionales.

Causa cerrada en corpus r575: `FUN_390bd290`, RVA `0x0BD290`, case 2,
actualiza el estado local y emite evento `0x334/ARCHE_PASS_UPDATE_REWARD_ITEM`.
`arche_pass_info.alb.lua:234` llama `UpdateMyRewards`; `arche_pass_view.alb.lua`
aplica check, alpha 0.2 y deshabilita lo cobrado, habilitando únicamente
`nextRewardTier`. La página inicial no ejecuta ese callback. Se conserva el
wire existente y se reemplaza sólo la respuesta de éxito por
`SCUpdateArchePass 0x33F/reason=2/diffPoint=0/allDone=false`, después del item task.
Sin paquete adicional por tanteo, sin modificar Lua/game_pak ni reiniciar claims.

SQLite completa r575, pase 19: tier 1 = 0 puntos, item 23633 x10;
tier 2 = 5745 puntos, item 46250 x1; tier 3 = 11490 puntos, item 49000 x1.
A 7000 puntos, después del claim 1 corresponde habilitar el 2, nunca el 3.
Fixtures nuevos: bodies exactos de actualización normal/premium y regresión de
la frontera 1 → 2 → ninguna alcanzada con 7000 puntos. Se mantiene la separación
de ambos tracks. El log de éxito identifica personaje/cuenta/type/tier/fronteras.

Gate manual pendiente: conservar los 7000 puntos y el primer claim, entrar,
verificar tier 1 marcado y tier 2 disponible; cobrar sólo el tier 2 y comprobar
su marcado inmediato sin cerrar el panel. No otorgar más puntos ni reclamar
premium durante esta interacción. El tercer tier seguirá bloqueado por puntos.

Entrega: restore/build integral Release sin errores, suite `1745/1745` sin
omitidos (persisten advertencias previas). Game desplegado como
`sha256:b8ea6d75fa3e89e977e62499215664297a7cc4e9c1bcfc2b44a78c24d3abdc54`;
rollback `aaemu-world:rollback-pre-archepass-reward-refresh-20260903-152338`.
Los ensamblados `/app/AAEmu.Game.dll` y `/app/game/AAEmu.Game.dll` coinciden en
SHA256 `dd3a93bef9704f6eb7bfca9bd31c9e3f9b990e860418f97ddf9cf27e5e4c8f5e`.
Arranque 19:26:26 UTC: Game/Stream abiertos, Server started, registrado en Login,
healthy, 97 pases/3028 tiers/29 comprables. Login y DB no fueron recreados.
MySQL después del despliegue conserva type 19/7000/Progress/claim normal 1,
premium 0. Zone se desconectó al recrear Game y no fue operada por Codex.

El usuario aceptó el refresco de claims; los logs posteriores registraron tier 2
y luego tiers 3–14 tras subir a 77000 puntos. Reportó pérdida de misiones pagadas
al reiniciar. Causa transversal confirmada: faltaban las tres tablas TodayAssignment,
no un problema de UI ni un reset calendario. Ver
[persistencia compartida y recuperación autorizada](AA10TodayAssignmentPersistence_es.md).

## Premium: actualización en tiempo real — 2026-09-03

El usuario probó los 33 premios normales de Hellwraith Kirin y consumió el ticket
premium. A 20:00:28 UTC la traza fue `CSArchePassUpgrade 0x1FC` →
`SCItemTaskSuccess 0x0BC/QuestComplete` → `SCArchePasses 0x33D`, sin incremental.
MySQL confirmó type19/183840 puntos/Progress/premium1/normal33/premium0.
El usuario confirmó que al reloguear el camino premium sí aparecía: persistencia
correcta, refresco del panel abierto ausente.

SQLite r575 fija `upgrade_item_id=50633` y `max_tier=33` para type19. El consumer
`FUN_390bd290` RVA 0x0BD290 de x2game x64
SHA256 405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734
sobrescribe el estado y, para reason7, emite evento 0x339
`ARCHE_PASS_UPGRADE_PREMIUM`. El Lua `arche_pass_info.alb.lua:263` responde con
`parent:Update()`: cabecera, recompensas y misiones. El padre upstream sólo
contiene el request vacío sin ejecución; AA8 no aporta implementación.

El éxito de TryUpgradePremium ahora usa 0x33F/reason7/diffPoint0/allDonefalse
después del consumo existente. No se cambian coste, validación, inventario,
fronteras ni persistencia; una segunda solicitud sigue rechazada antes de cobrar.
Se agrega log de upgrade y fixture binario exacto con normal33/premium0, además
de una regresión de upgrade tardío que habilita el primer premio premium sin
reabrir premios normales ni completar el pase prematuramente.

No se revirtió premium ni se entregó/consumió otro ticket. Gate visual pendiente
para un próximo upgrade de un pase no premium: panel abierto, un ticket del
catálogo, refresco inmediato sin relog. El pase actual conserva su upgrade
aceptado por el usuario tras relog. La finalización del pase es un gate separado.

Validación y despliegue: build Release sin errores; suite completa 1750/1750,
sin fallos ni omitidos. Game recreado con imagen
`sha256:6bc2b55a27b4b706d7eba97da266d66a9a2035fd1eaeb98cd98abea121f90a8f`.
Rollback: `aaemu-world:rollback-pre-archepass-premium-refresh-20260903-160330`.
SHA256 coincidente en `/app/AAEmu.Game.dll` y `/app/game/AAEmu.Game.dll`:
`ef05c2cd4d342fbd7e4ae24c44a0a50493d37da995247efd7073ddad3614e59f`.
Login/DB conservan sus contenedores; lectura MySQL posterior confirma
type19/183840/Progress/premium1/normal33/premium0. Sin escrituras de recuperación.
Catálogo cargado: 97 pases, 3028 tiers y 29 comprables. Persisten diagnósticos
previos de smelting29–32 y avisos de zonas; Zone no fue operada.
Arranque confirmado a 20:07:24 UTC: Game/Stream abiertos, Server started y
registro en LoginServer; healthcheck healthy. Gate visual incremental pendiente.

## Cuarta misión premium: requisito pendiente — 2026-09-03

El usuario aceptó el refresco premium con ArcheRacer. La traza de 20:13:42 UTC
confirma type18, ticket50634, premium y 0x33F. A 20:13:44, 47 y 53, 20:14:28 y
20:15:05, `CSRequestTodayAssignment 0x120` llega con realStep53/request1 y se
rechaza antes del desbloqueo: `Unsupported UnitReq ... id=68641 ... PremiumArchePass`.
No se trata de UI cacheada ni se consumió moneda por esos intentos.

SQLite completa r575: el único requisito kind121 es 68641, owner
TodayQuestStep39, values0/0/0, enable=true. Step39 corresponde a realStep53,
sin item de coste ni cantidad, con grupos118/156/167/168 y quests de catálogo.
El cliente exacto pasa esa ranura de bloqueada a interactiva tras mejorar el
pase activo, como confirmó el usuario. Upstream padre y AA8 no implementan el
requisito; no se copia un contrato externo. Clasificación: client-native en la
elegibilidad observada, server-required en su consulta al libro persistido.

`UnitReqs.PremiumArchePass` ahora consulta `ArchePassManager.HasActivePremiumPass`
bajo el lock del personaje, con carga persistida, reconciliación de expiración,
pase Progress, premium y catálogo disponible. No confundir con Patron ni con
un pase premium pausado. Se mantiene fail-closed ante almacenamiento no listo,
estado ausente o catálogo inválido. Las solicitudes individuales y AcceptAll
usan el mismo requisito; permanecen sin cambios coste, selección de quest,
persistencia TodayAssignment y respuesta 0x285. No se modificó SQL ni cliente.

Seis regresiones cubren premium activo/repetición sin mutación, no premium,
estados no activos, almacenamiento/catálogo ausentes, expiración, cambio de pase
y rechazo de UnitReq sin personaje. La compilación inicial detectó una escritura
incorrecta en un campo init-only del fixture; se corrigió antes de la suite.

Antes del despliegue, MySQL Dannia1007 conserva pase18/210000/Progress/premium1,
pase19/183840/Owned/premium1/normal33/premium15; slots50/51 Done y52 Progress,
sin fila53 ni desbloqueo pagado53. No se otorgaron tickets, quests ni desbloqueos.
Gate manual: en el pase18 premium, confirmar una vez la cuarta ranura; debe
quedar Ready sin coste. Detenerse para revisar 0x120 → 0x285 y persistencia53.
Luego aceptar la misión será una interacción separada. Relog/restart y negativos
en cliente siguen pendientes; no se declara cerrada toda la mecánica de misiones.

Entrega: restore y build Release correctos (advertencias preexistentes), suite
1756/1756 sin omitidos. Game desplegado con imagen
`sha256:fd6330cdbd072e1a9fbde4091e2f1a7c0407306688641fab01aca8712c20adf5`;
rollback `aaemu-world:rollback-pre-premium-mission-20260903`.
DLL en /app y /app/game idénticas:
`66fcb9b8cd0188231e44a98be79cb3144844f80d6f625bdc2255e1dce36eada7`.
Arranque20:23:19 UTC: Game/Stream, Server started, registro Login y healthy;
catálogo97/3028/29. Login/DB no recreados. Consulta posterior conserva puntos,
premium, claims y slots50/51/52 anteriores, sin fila53 aún. Zone no operada;
su desconexión al recrear Game y los errores previos smelting29–32 quedan fuera
de este cambio. Manifest/consultas en arche-pass-phase4c-frontier.

### Aceptación y cierre del ciclo — 2026-09-03

Usuario confirma que funciona y autoriza commit/push y pasar a Item Smelting.
Logs20:25:54 UTC: realStep53/request1 → Ready sin coste;20:25:55: request2 →
Progress, group168/quest10120. Se cierra el ciclo probado de registro, cambio,
puntos, claims, premium y cuarta misión. Reroll/rollover, completado final y
negativos E2E no ejercitados siguen pendientes; no confundir aceptación del
usuario con cobertura completa. CSArchePassChangeMission sigue rechazado.
