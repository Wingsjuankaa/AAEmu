# Ipnya: completar EXP en un solo casteo

Extensión personalizada solicitada por el usuario, corregida el 2026-09-06.
Target `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`, HEAD base
`6c3f7e5ecf9ebc02797fc30326929da884c44902`; padre exacto
`upstream/client_version/zone-10.0.2_r575` (`6273a02f0c88f3c48e52252c3e64ae7e71d63945`).
No es una función nativa de ArcheAge.

## Resultado y corrección

«Completar EXP» conserva las variantes por familia y por combinación disponible.
Calcula lo que falta considerando la EXP actual y los materiales compartidos del
bolso, muestra las cantidades completas, el oro y el excedente inevitable.
**Confirmar envía una sola solicitud y ejecuta un solo casteo de la skill 38363.**
Al finalizar se consumen juntos todos los materiales y todo el oro, y se llena la
barra. La promoción posterior sigue usando la runa y el botón nativos.
Las recetas individuales siguen funcionando como antes.

La implementación anterior encadenaba recetas nativas. El usuario la rechazó:
además de incumplir el casteo único, el segundo intento fue rechazado por Game
con `CooldownTime` (23:03:33 UTC). El cliente esperaba otra actualización de EXP
y mantenía el botón bloqueado. La cola fue eliminada; no se ajustó su demora.

Cancelar, cerrar o cambiar de ranura invalida la operación pendiente. El servidor
comprueba la identidad de la solicitud para no cancelar otro casteo. Si el pago,
el estado o la persistencia fallan, no se consume una parte del lote. Cancelar
después del commit no revierte un pago que ya se completó. La UI observa el
resultado, libera los botones ante interrupción o falta de respuesta y no reintenta.

Las variantes personalizadas pagan **con oro**, indicado en la nota; no usan
puntos AA. El catálogo, precios y EXP por material permanecen intactos. Se
minimizan, en orden, excedente, oro, cantidad de objetos y cantidad de grupos de
receta codificados. Los grupos ×5 compactan la descripción; no son más casteos.

## Cliente y transporte

El único recurso empaquetado modificado es:
`game/scriptsbin64/x2ui/characterinfo/equip_slot_reinforce/info.alb` (36127 bytes).
La ventana usa el preset 510, ampliado a 600 px por la UI española instalada.
No se modifica la DLL, la SQLite del cliente ni el formato nativo de StartSkill.

El Lua nativo acepta sólo un descriptor por `StartReinforceAddExp`; no permite
pasar cantidades. La ruta V2 basada en `Console:ExecuteString` fue descartada:
el usuario mostró un video de 19,65 s donde la UI esperaba y liberaba el botón
sin casteo ni consumo. No llegó ninguna solicitud de lote a Game. El observador
de consola existe, pero eso no demostraba que recibiera las llamadas Lua; no se
utiliza como transporte de esta versión.

V3 usa `X2Chat:JoinUserChatChannel(name, "")`, cuyo binding nativo llama
directamente al emisor de `CSJoinUserChatChannelPacket` (0x096, dos strings y
bool create=false). Se reservan nombres que Game intercepta antes de cualquier
operación de chat. No se crea ni se une a un canal, no se envía contenido a otros
jugadores y no se concede autoridad GM. El cliente no recibe confirmaciones de
unión, por lo que el filtro nativo de canales ya unidos no bloquea los fragmentos.

Contrato ASCII:

```text
payload = requestId,slot0,level,currentExp,gainExp,gold/recipeId:count/...
name    = aa10ip3:requestId:index:total:fragmento
cancel  = aa10ip3cancel:requestId
```

La contraseña va vacía. El constructor nativo copia 48 bytes de nombre y seis
de contraseña; cada fragmento lleva como máximo 23 bytes de payload para respetar
el límite de 48 incluso con IDs de diez dígitos. El presupuesto tiene un máximo
de 233 bytes y once fragmentos. El servidor ensambla por personaje autenticado,
exige el primer fragmento, correlaciona IDs, limita memoria, vence conjuntos
incompletos a los cinco segundos y evita duplicar uno completado. Cancelar
invalida también una petición incompleta. Sólo el presupuesto completo y válido
puede iniciar el casteo; nunca se emite un uso individual como alternativa.

Se aceptan hasta ocho descriptores distintos y cien ejecuciones de receta en
total. El servidor deriva objetos, EXP y oro del catálogo y rechaza IDs desconocidos,
recetas de otra ranura/nivel, costes alterados, copias inútiles y estados obsoletos.

Evidencia AA10 x64, imagen base 0x39000000:

| Consumer | RVA | Evidencia |
| --- | --- | --- |
| Registro X2Chat | 0x7ECEA0 | JoinUserChatChannel(channel, password) |
| Binding de envío | 0x7E9880 | Llama al emisor con create=0 |
| Emisor directo | 0x7228B0 | Sólo excluye nombres ya unidos; construye opcode 0x96 y envía a Game |
| Constructor | 0xA8E8A0 | Copia segura: 0x31 para nombre, 7 para contraseña, bool final |

Los cuatro rangos completos se contrastaron byte por byte con la DLL activa
SHA-256 `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.
La evidencia y el video están referenciados bajo
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/ipnya-single-cast`.
La recepción, el casteo y el commit de tres lotes V3 quedaron corroborados en Game
y el usuario confirmó el éxito del flujo en retail.

## Backend y atomicidad

`EquipSlotReinforceBatchRequest` parsea y recalcula el presupuesto.
`CharacterEquipSlotReinforce.Batch` verifica feature, nivel mínimo, vida, estado,
recursos y ausencia de otro casteo antes de llamar una vez a `Skill.Use`.
Se conservan requisitos, cooldown, cast time, eventos y efectos de la skill.
El contexto de lote vive sólo en memoria: el cuerpo nativo tipo 22 no cambia.

El efecto `EquipSlotReinforceAddExp` consume la autorización una sola vez,
revalida la EXP y el nivel, y utiliza el pago Ipnya existente bajo los locks de
persistencia, estado, monedero e inventario. Objetos, oro y progresión se guardan
en una transacción MySQL; luego se publica una transacción de inventario y una
actualización de ranura. No hay migración SQL ni edición manual de personajes.

## Reproducción y rollback

Todo el código fuente necesario queda en el backend:

- `Scripts/lua/IpnyaFillExp.lua` y `IpnyaFillExpUi.lua`.
- `Scripts/PatchAa10IpnyaFillExp.py`: builder determinista desde el Lua efectivo.
- `Scripts/Aa10IpnyaFillExp.contracts.json`: hashes exactos de fuente, compilador,
  ALB original, cola anterior, V2 fallido y ALB V3 de casteo único.
- `Scripts/ApplyAa10IpnyaFillExp.py`: extracción, dry-run, respaldo, aplicación,
  reextracción, sentinelas e idempotencia.
- Código C# de lote, pruebas y fixtures compartidos cliente/servidor.

Primero compilar/desplegar Game de esta revisión. Cerrar el cliente español y,
desde `E:/AAEmu/rama_10/server/AAEmu`, ejecutar:

```powershell
python Scripts/ApplyAa10IpnyaFillExp.py
python Scripts/ApplyAa10IpnyaFillExp.py --apply
```

Para reconstruir tras perder game_pak se necesita una copia base compatible del
cliente español; el script reconstruye el parche, no los 74 GB de recursos del
juego. Rechaza fuentes o hashes desconocidos. Conserva las traducciones y parches
ajenos; el original inglés permanece inmutable. Los respaldos están en
`E:/AAEmu/rama_10/backups/client-patches/aa10-ipnya-fill-exp-*`.

Rollback del cliente: reinsertar su entrada de respaldo con `PakEntryReplace`,
exigiendo el hash actual exacto, y reextraer. Para volver a recetas normales es
preferible el ALB nativo original; el respaldo inmediatamente anterior contiene
la cola que el usuario rechazó. Rollback del servidor: imagen etiquetada
`aaemu-world:rollback-pre-ipnya-v3-20260906`, recreando sólo Game. Esa imagen
contiene V2; para volver al comportamiento nativo sin extensión usar
`aaemu-world:rollback-pre-ipnya-single-cast-20260906`.
La base no necesita restaurarse para revertir código: hacerlo perdería progreso.
El respaldo consistente anterior al despliegue está en
`E:/AAEmu/rama_10/backups/ipnya-single-cast-v3-20260906/aaemu_game.sql`.

## Validación y aceptación

Restore/build Release: cero errores. 1848 pruebas backend aprobadas, incluidas
validación del lote, pago conjunto, persistencia fallida, cancelación correlacionada,
replay y preservación del wire nativo. 12 pruebas Lua/builder pasan, con 65 casos
contra un enumerador independiente y 72 presupuestos compartidos con C#.
14 regresiones de UI pasan. Control Center: typecheck, build, 52 pruebas y smoke
SQLite correctos; una integración real omitida. El hash del paquete es informativo:
el caché de mapa se invalida por ruta/tamaño/mtime, no hay allowlist que modificar.

El usuario confirmó el éxito en retail. Los registros del 2026-09-07 muestran
un casteo y un commit por solicitud en tres lotes de la ranura 17: nivel 7
(00:31:50→00:31:54), nivel 8 (00:33:57→00:34:01) y nivel 9
(00:34:09→00:34:12). Las barras quedaron en 2400, 2600 y 2800 EXP y se
registró la promoción nativa al nivel 10 a las 00:34:15. El flujo positivo queda
aceptado por el usuario y corroborado por el servidor.

Cancelación y reconexión no fueron confirmadas individualmente en la prueba
retail; no atribuirles esa aceptación específica. Mantienen la cobertura
automatizada descrita arriba.
