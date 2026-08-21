# Reactivación AA10: regalos diarios y ArchePass

Fecha de reconstrucción: 2026-08-20
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

El registro nativo de estado ocupa 32 bytes en memoria x64 por alineación y
serializa, en orden, `type:i32`, `point:i64`, `status:u8`, `premium:bool`,
`lastRewardTier:i32`, `lastPremiumRewardTier:i32`. El serializer admite hasta
diez registros por página, no diez en total. 4C usa resincronización completa
paginada porque los valores semánticos de `SCUpdateArchePass.reason` aún no están
demostrados.

La evidencia se obtuvo con
`reconstruccion_cliente_10/scripts/inspect_msvc_rtti_vtable.py`, que resuelve RTTI
MSVC x64 y desensambla serializers sin modificar el binario retail.

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
