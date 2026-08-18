# Checkpoint AA10 — reactivación de ArchPass, asistencia y Event Center

Fecha del corte: 2026-08-18.

Estado: checkpoint forense y plan de reconstrucción. Este trabajo no activa
features ni modifica el runtime, las SQLite o los clientes.

## Objetivo

Conservar la evidencia y la ruta de trabajo necesarias para reactivar las
funcionalidades de live-ops que el cliente ArcheAge Returns `10.0.2.13 r575`
incluye, pero que el servidor AAEmu todavía no expone o no implementa por
completo:

- ArchPass;
- calendario mensual de asistencia y recompensas;
- Today Assignment;
- Event Info y calendario de contenidos;
- Survey Form y otras pestañas relacionadas de Event Center.

Este checkpoint separa cuatro fronteras que no deben confundirse:

```text
feature bit -> Lua/UI -> datos estáticos -> protocolo/estado autoritativo
```

Mostrar una ventana sólo prueba las dos primeras fronteras. Una funcionalidad
no está reconstruida hasta cerrar además validación, transacción, persistencia,
respuesta al cliente, relog, reset calendario y rechazo sin mutación parcial.

## Conclusión ejecutiva

No es necesario importar la interfaz de ArchPass o Today Assignment desde un
cliente Unchained ni desde ArcheRage. Returns r575 ya contiene sus scripts,
assets, APIs nativas y tablas estáticas.

La comparación con el ArcheRage `10.0.2.9` instalado demuestra que:

- los cinco `.alb` de ArchPass se decompilan a Lua idéntico en ambos clientes;
- `today_assignment.alb` también se decompila idéntico;
- ambos `toc.g` cargan los módulos de ArchPass y asistencia;
- ArcheRage conserva los mismos gates `featureSet.arche_pass` y
  `featureSet.account_attendance`;
- su `eventcenter.alb` no agrega ArchPass: elimina Voyage y FollowMe;
- el Lua de asistencia de ArcheRage tiene diferencias de comportamiento, pero
  no elimina el gate ni reemplaza el contrato `X2EventCenter`.

La explicación más consistente es que ArcheRage activa las features mediante
el `fset`, mantiene datos vigentes y responde desde su servidor. El cliente por
sí solo no permite demostrar de dónde procede la implementación privada de ese
servidor.

Descifrar su `compact.sqlite` sigue siendo útil para recuperar campañas,
recompensas y fechas actuales. No recuperará la lógica de compra, progreso,
reclamación, persistencia o resets. Para esa frontera tiene más valor capturar
el `SCInitialConfig` y el ciclo de paquetes de una interacción real.

## Identidad y autoridad de las fuentes

### Cliente target

- Cliente: ArcheAge Returns `10.0.2.13 r575`, x86-64.
- Raíz: `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575`.
- `game_pak` SHA-256:
  `32499AC6BF3ED1C1CE24B5A15A151355CB0C5A352A0C2BA727769AEEB3FC89D5`.
- `x2game.dll` SHA-256:
  `2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76`.
- SQLite completa SHA-256:
  `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`.
- Compact retail SHA-256:
  `F8C7A0268A26D4EFAEC47A2A2B1B525447BF16C274506CD97BF571839B5E6D29`.

La SQLite completa es la autoridad de catálogo. El compact retail es la
proyección que consume el cliente. El consumer Lua y el `x2game.dll` exacto son
autoridad para gates, llamadas y layouts. Una captura del cliente exacto será
autoridad para el lifecycle que la evidencia estática todavía no cierre.

### Comparador ArcheRage

- Instalación: `E:\Rage\ArcheRage.to NA`.
- Versión: `10.0.2.9`.
- `game_pak` SHA-256:
  `6CCB24F55B0D59BD8CDD9EEAC3A0E73727654545DD3837B3D7AF99D8F2B9EAFB`.
- El compact vivo extraído continúa cifrado y no se usó como autoridad de
  filas.

ArcheRage es un comparador semántico y un posible oráculo dinámico. No es
autoridad automática para opcodes, layouts o reglas de Returns r575.

### Código consumidor

- Target: `Wingsjuankaa/AAEmu:rama_10`.
- HEAD del corte: `666b7ca0844977430c984c37f6c695019c8f38cf`.
- Padre obligatorio:
  `upstream/client_version/zone-10.0.2_r575`.
- HEAD padre observado:
  `a3c735c658ebe20d10cb50684b4b3e366b7d87e1`.

El código del fork o del padre describe el estado de implementación. No
reemplaza la evidencia nativa del cliente.

## Mapa de features

`SCInitialConfigPacket`, opcode `0x007`, entrega un `fset` fijo de 31 bytes. Los
bits relevantes están definidos en
`AAEmu.Game/Models/Game/Features/Feature.cs`.

| Funcionalidad | Nombre del feature | Bit | Gate adicional | Estado en `Features.json` |
|---|---|---:|---|---|
| ArchPass | `arche_pass` | 98 | ninguno en la pestaña | no listado, apagado |
| Asistencia mensual | `account_attendance` | 144 | debe haber recompensas del período | no listado, apagado |
| Event Info | `event_center_event_info` | 145 | datos recibidos desde servidor | encendido |
| Calendario de contenidos | `event_center_content_schedule` | 194 | UI principalmente estática | encendido |
| Today Assignment | `event_center_today_assignment` | 204 | catálogo y estado de quests | encendido |
| Misiones ArchPass por cuenta | `archePassMissionAccount` | 222 | consumer nativo pendiente de cerrar | no listado, apagado |
| Encuestas | `survey_form` | 223 | formulario/campaña activa | no listado, apagado |

El consumer de `eventcenter.alb` construye sus pestañas así:

```lua
return featureSet.account_attendance and #rewardInfos > 0
return featureSet.event_center_today_assignment
return featureSet.arche_pass
return featureSet.event_center_event_info
return featureSet.event_center_content_schedule
return featureSet.survey_form
```

Por tanto, cambiar un bit no equivale a terminar la funcionalidad. En
particular, asistencia tiene un segundo gate dependiente de datos vigentes.

## Evidencia del game_pak

### ArchPass

Los siguientes módulos Bin64 fueron extraídos de Returns y ArcheRage,
normalizados como bytecode Lua 5.1 y decompilados con `unluac`:

- `arche_pass/arche_pass_info.alb`;
- `arche_pass/arche_pass_list_info.alb`;
- `arche_pass/arche_pass_list_view.alb`;
- `arche_pass/arche_pass_view.alb`;
- `arche_pass/reward_item_listctrl.alb`.

Los cinco producen Lua idéntico. La diferencia binaria original es de 33 bytes
por archivo, pero no produce ninguna diferencia lógica en la decompilación;
por sí sola no es evidencia de un parche funcional de ArcheRage.

El Lua utiliza las APIs nativas siguientes:

- `X2ArchePass:GetCategories`;
- `GetArchePassInfo`, `GetArchePassRewards`, `GetStatus` e `IsFull`;
- `StartPass`, `BuyPass`, `RemovePass` y `UpgradePremium`;
- `GetMyArchePassInfo` y `GetMyArchePassRewards`;
- `GetMyArchePassReward` y `NormalComplete`;
- `GetMissionCompleteCount` y `GetMissionChangeCount`.

También espera eventos como `ARCHE_PASS_LOADED`, `ARCHE_PASS_STARTED`,
`ARCHE_PASS_UPDATE_POINT`, `ARCHE_PASS_UPDATE_TIER`,
`ARCHE_PASS_UPDATE_REWARD_ITEM`, `ARCHE_PASS_MISSION_COMPLETED` y
`ARCHE_PASS_MISSION_CHANGED`.

Esto confirma que el cliente ya contiene la presentación y el adaptador nativo
completo. No confirma cómo debe construir AAEmu el estado que alimenta esas
APIs.

### Asistencia

La pestaña llama a:

- `X2EventCenter:GetAttendanceRewardInfos()` para datos estáticos;
- `X2EventCenter:GetAttendedDayCount()` para estado autoritativo;
- `X2EventCenter:CheckAttendable()` para habilitar la acción;
- `X2EventCenter:AddAttendance()` para reclamar/registrar el día.

Returns además escucha `ACCOUNT_ATTENDANCE_LOADED` y
`ACCOUNT_ATTENDANCE_ADDED` para refrescar la ventana. ArcheRage conserva el
mismo contrato general, aunque su `attendance.alb` distribuye de otra forma el
contador ArcheLife y omite un handler local duplicado. Esa diferencia no
reactiva la función por sí sola.

### Today Assignment y Event Center

`today_assignment.alb` es lógicamente idéntico entre ambos clientes.
`eventcenter.alb` de ArcheRage es un subconjunto del de Returns: quitó Voyage y
FollowMe. Esto es evidencia negativa contra la hipótesis de que ArcheRage haya
añadido ArchPass mediante un módulo UI externo.

## Evidencia SQLite

Las tablas siguientes existen tanto en la SQLite completa como en el compact
retail de Returns:

| Tabla | Filas | Función |
|---|---:|---|
| `account_attendance_rewards` | 2.700 | premios por año, mes y día acumulado |
| `arche_pass_categories` | 14 | categorías y flag `enable` |
| `arche_passes` | 97 | definición, vencimiento, costo, icono y máximo tier |
| `arche_pass_tiers` | 3.028 | puntos y premios normal/premium por tier |
| `quest_act_supply_arche_pass_points` | 325 | puntos otorgados por acts de quest |

El catálogo contiene explícitamente categorías históricas de Unchained:

| ID | Nombre lógico | `enable` observado |
|---:|---|---|
| 10 | Unchained ArchePass normal | false |
| 11 | Unchained ArchePass avanzado | false |
| 12 | Unchained ArchePass premium | false |
| 13 | Unchained ArchePass nuevo comienzo | false |

Esto demuestra herencia de contenido Unchained en el propio cliente Returns.
No prueba que activar esas filas produzca un sistema jugable.

### Vigencia observada

- Los ArchPass con fecha de cuatro dígitos más recientes terminan en 2023.
- El pase `id=102`, categoría 5, no tiene fecha de expiración y posee 60 tiers;
  es el mejor candidato estático inicial para una prueba controlada.
- `account_attendance_rewards` contiene campañas hasta julio de 2026.
- No hay filas para agosto de 2026 en el corte actual.

Como el consumer exige `#rewardInfos > 0`, encender hoy solamente
`account_attendance` no basta para mostrar la pestaña. Antes de una prueba se
debe definir una campaña vigente y mantener consistente el dato que consulta
el cliente con el catálogo que valida el servidor. Nunca editar el compact
retail autoritativo sin respaldo, hash y rollback.

### Consultas de reproducción

```sql
SELECT COUNT(*) FROM account_attendance_rewards;
SELECT COUNT(*) FROM arche_pass_categories;
SELECT COUNT(*) FROM arche_passes;
SELECT COUNT(*) FROM arche_pass_tiers;
SELECT COUNT(*) FROM quest_act_supply_arche_pass_points;

SELECT id, name, order_index, enable
FROM arche_pass_categories
ORDER BY id;

SELECT id, arche_pass_category_id, name,
       ed_year, ed_month, ed_day, currency_value, upgrade_item_id, max_tier
FROM arche_passes
ORDER BY ed_year DESC, ed_month DESC, ed_day DESC;

SELECT year, month, COUNT(*), MIN(day_count), MAX(day_count)
FROM account_attendance_rewards
GROUP BY year, month
ORDER BY year DESC, month DESC;
```

Ejecutar siempre contra una conexión SQLite `mode=ro`/`query_only` al producir
evidencia. Las campañas de runtime modificadas deben etiquetarse
`server_observed`, no reemplazar el baseline retail.

## Brecha actual del servidor

### ArchPass

AAEmu ya define estos C2G con layouts derivados del cliente r575:

| Packet | Opcode |
|---|---:|
| `CSArchePassGetRewardItemPacket` | `0x1F8` |
| `CSArchePassRemovePacket` | `0x1F9` |
| `CSArchePassStartPacket` | `0x1FA` |
| `CSArchePassBuyPacket` | `0x1FB` |
| `CSArchePassUpgradePacket` | `0x1FC` |
| `CSArchePassChangeMissionPacket` | `0x1FD` |
| `CSArchePassNormalCompletePacket` | `0x1FE` |

En el corte actual sólo `CSArchePassUpgradePacket` está registrado en
`GameNetwork`. Los siete tipos continúan sin una implementación de negocio;
sus clases están marcadas `TODO` o tienen cuerpo vacío. No existe un
`ArchePassManager`, loader de las tablas, estado persistente, transacción de
premios ni construcciones de los G2C definidos.

G2C localizados hasta ahora:

| Packet | Opcode | Estado |
|---|---:|---|
| `SCCompletedArchePassPacket` | `0x340` | definido, sin productor |
| `SCArchePassMissionCountPacket` | `0x341` | definido, sin productor |
| `SCArchePassChangeMissionPacket` | `0x342` | definido, sin productor |

Esta lista no debe declararse completa hasta cerrar en `x2game.dll` todos los
serializers y consumers que alimentan los eventos Lua observados.

### Asistencia

C2G conocidos:

| Packet | Opcode | Registro/handler |
|---|---:|---|
| `CSAddAccountAttendancePacket` | `0x1B0` | no registrado; sólo parsea |
| `CSLoadAccountAttendancePacket` | `0x1B1` | registrado; no actúa |

G2C conocidos:

| Packet | Opcode | Estado |
|---|---:|---|
| `SCAccountAttendancePacket` | `0x2C9` | layout fijo de 31 días; sin productor |
| `SCAccountAttendanceAddedPacket` | `0x2CA` | definido; sin productor |
| `SCAccountAttendanceRewardedPacket` | `0x2CC` | definido; sin productor |

Falta decidir con evidencia el ownership por cuenta/personaje, persistencia,
clave calendario, elegibilidad ArcheLife, entrega directa/correo, idempotencia
y reset mensual.

### Today Assignment

No debe clasificarse junto a los esqueletos anteriores. El fork ya posee
`TodayAssignmentManager` con:

- carga y persistencia diaria;
- estados Locked/Ready/Progress/Done;
- aceptación individual y masiva;
- reroll con límites;
- desbloqueos y costos;
- integración con quests;
- reset UTC, relog y resincronización;
- C2G registrados y G2C producidos.

Debe validarse manualmente de extremo a extremo, pero su brecha es de cierre y
regresión, no de implementación desde cero.

### Event Info y calendario de contenidos

`CSRequestEventInfoCountPacket` y `CSRequestEventMainInfoPacket` están
registrados, pero no actúan. Al entrar al mundo el servidor envía un
`SCEventInfoCountPacket` con cero eventos para inicializar de forma segura la
lista y evitar que la ventana dereferencie estado no inicializado. No existe
aún un catálogo/manager de eventos activos ni respuesta de detalle.

El calendario de contenidos es principalmente una presentación estática de
Lua, texturas y localización. No debe confundirse con el calendario de
asistencia ni con el scheduler autoritativo de NPCs/quests.

## Plan recomendado de reactivación

### Fase 0 — congelar evidencia y evitar falsas activaciones

1. Mantener `arche_pass`, `account_attendance`, `archePassMissionAccount` y
   `survey_form` apagados mientras sus requests no tengan handlers seguros.
2. Congelar hashes del cliente Returns, ArcheRage y cada captura utilizada.
3. Mantener toda extracción/decompilación fuera del runtime y del Git salvo
   reportes/manifests pequeños.
4. No copiar `x2game.dll`, `.alb`, SQLite ni `game_pak` completos desde otro
   build.

### Fase 1 — captura dinámica de ArcheRage

Obtener, como mínimo:

1. los 31 bytes de `fset` enviados por `SCInitialConfig`;
2. apertura de Event Center sin interacción;
3. carga y reclamación de un día de asistencia;
4. apertura de lista y detalle de ArchPass;
5. activar/comprar un pass si existe una cuenta de prueba autorizada;
6. completar una misión, sumar puntos, subir tier y reclamar recompensa;
7. repetir tras relog y, cuando sea posible, tras un cambio de día.

Cada traza debe registrar orden, dirección, opcode, packet level, body,
resultado visible, estado antes/después y condición de la cuenta. Si el canal
está cifrado, instrumentar el borde cliente después del descifrado en vez de
inferir el contrato desde tráfico opaco.

### Fase 2 — calendario de asistencia como primer vertical

1. Cerrar serializers C2G/G2C en el `x2game.dll` r575.
2. Confirmar si el estado es por cuenta, región o personaje.
3. Definir campaña vigente en una fuente de runtime reproducible, sin mutar el
   baseline retail.
4. Implementar loader server-side de `account_attendance_rewards`.
5. Añadir persistencia con clave de calendario explícita y restricción única
   para impedir doble reclamación.
6. Implementar carga de los 31 días y conteos normal/ArcheLife.
7. Implementar `AddAttendance` con validación de fecha, offset y elegibilidad.
8. Entregar la recompensa de forma transaccional; confirmar correo cuando el
   inventario esté lleno.
9. Emitir Added/Rewarded sólo después de persistir y otorgar correctamente.
10. Activar `account_attendance` únicamente al cerrar pruebas automáticas y
    manuales.

Criterios mínimos: primer claim, claim duplicado, día inválido, mes sin
campaña, inventario lleno, desconexión/reintento, dos sesiones concurrentes,
relog y rollover mensual.

### Fase 3 — ArchPass

1. Completar el corpus nativo de `X2ArchePass`: serializers, consumers,
   eventos y estado inicial.
2. Determinar cómo se transmite el pass activo, status, tier, puntos,
   reclamaciones y premium; no asumir que los tres G2C ya definidos bastan.
3. Crear loaders relacionales para categorías, pases, tiers y acts que otorgan
   puntos.
4. Diseñar persistencia por ownership confirmado: pass activo, compra,
   premium, tier, puntos, claims normal/premium, contadores y misiones.
5. Implementar Start/Buy/Remove/Upgrade con costos atómicos e idempotencia.
6. Integrar puntos con quests/Today Assignment usando IDs r575 confirmados.
7. Implementar cambio de misión, límites diarios y reset UTC observado.
8. Implementar avance de tier y reclamaciones, incluyendo último premio,
   inventario lleno y correo si corresponde.
9. Probar expiración y cambio de campaña sin perder ni duplicar rewards.
10. Activar `arche_pass` y, sólo si el consumer lo exige y el backend lo
    soporta, `archePassMissionAccount`.

El pass `id=102` sin expiración es candidato para la primera prueba de catálogo,
pero no debe recibir excepciones hardcodeadas. Toda regla debe provenir del
modelo general confirmado.

### Fase 4 — Event Info, calendario y Survey Form

1. Separar contenido estático, datos SQLite, estado servidor y posibles URLs
   externas.
2. Reconstruir Event Info desde sus requests/serializers antes de devolver
   registros no vacíos.
3. Validar `TodayAssignmentManager` con el cliente y corregir el comentario
   genérico de `Features.json` cuando la prueba cierre.
4. Mantener Survey Form apagado hasta identificar campaña, respuestas,
   milestone/recompensa, persistencia e idempotencia.
5. Tratar cualquier panel web como dependencia externa explícita; abrir una
   ventana sin su host/API no constituye reactivación.

## Matriz de aceptación

Antes de marcar una feature como completa debe existir evidencia para todas
estas columnas:

| Frontera | Evidencia requerida |
|---|---|
| Gate | bit exacto y `SCInitialConfig` observado |
| UI | ALB consumer, APIs y eventos esperados |
| Datos | tablas, filas vigentes, relaciones y loader |
| Request | opcode, level, body, rechazo malformed |
| Estado | ownership, lifecycle, resets y concurrencia |
| Transacción | costo/recompensa atómicos e idempotentes |
| Persistencia | relog, restart y migración SQL |
| Respuesta | G2C/evento exacto y refresh visible |
| Edge cases | inventario lleno, expiración, duplicado y rollover |
| Regresión | feature apagada, sistemas no relacionados y suite completa |

## Evidencia reproducible conservada

Comparación y decompilación de live-ops:

```text
E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\
  liveops-ui-compare-20260818\
    returns\
    rage\
```

Índices de los paks:

```text
E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\
  returns-10.0.2.13-r575\pak-index.tsv
E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\
  archerage-10.0.2.9\pak-index.tsv
```

Herramienta de extracción:

```text
reconstruccion_cliente_10/tools/PakEntryExtract
```

Informe general de comparación:

- [AA10ArcheRageClientComparison_es.md](AA10ArcheRageClientComparison_es.md)

## Fronteras abiertas

- `opaque`: compact vivo de ArcheRage cifrado por su protección privada.
- `unknown`: `fset` real enviado actualmente por el servidor ArcheRage.
- `unknown`: lifecycle completo y todos los G2C que alimentan `X2ArchePass`.
- `unknown`: ownership exacto de asistencia y ArchPass en r575.
- `unknown`: semántica confirmada de `archePassMissionAccount` bit 222.
- `missing`: manager, loaders y persistencia ArchPass en AAEmu.
- `missing`: backend de asistencia mensual en AAEmu.
- `partial`: Event Info inicializa de forma segura una lista vacía.
- `partial`: Today Assignment implementado, pendiente de cierre manual y
  regresión integral.

No promover ninguna de estas fronteras por semejanza con AA8, Unchained,
ArcheRage u otro emulador. Los comparadores reducen búsqueda; Returns r575 y su
captura exacta cierran el contrato.
