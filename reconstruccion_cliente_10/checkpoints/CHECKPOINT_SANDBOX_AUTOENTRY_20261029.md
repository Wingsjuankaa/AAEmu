# Entrada automática del sandbox AA10 — 2026-10-29

Target: `rama_10`, padre `upstream/client_version/zone-10.0.2_r575`.
La implementación es tooling de desarrollo (`diagnostic-only`); no cambia
skills, física, paquetes ni autoridad de Game/World/Zone.

## Contrato cerrado desde el cliente efectivo

Entradas extraídas del `game_pak` del principal español r575:

- `game/scripts/x2ui/loginstage_new/connect/stage_server.lua` y su ALB Bin64.
- `game/scripts/x2ui/loginstage_new/character_select/character_select.lua` y
  su ALB Bin64; `character_list.lua` confirma `GetLoginCharacterName(index)`.

`wnd:SelectServer` utiliza `X2World:EnterWorld(worldIndex, zoneId)`;
`TryToEnterGame` utiliza `X2LoginCharacter:SelectCharacter(index, skipPrologue)`.
Se llaman esas rutas desde el cliente, conservando la validación de entrada,
premium, nombre forzado, borrado, traslado y cola. No se fabrican solicitudes
de selección desde el servidor.

Los Lua originales no igualan los ALB efectivos: el ALB del servidor mueve
`returnToLogin` de Y50 a Y100, y el del selector añade `GetDevMode()` al bloque
de visibilidad del botón de volver a servidores. Se decompilaron exactamente
esas entradas mediante el unluac existente y se reconstruyeron ambos deltas.
La compilación de las fuentes resultantes es semánticamente idéntica a ambos
ALB efectivos, comparando instrucciones, constantes, closures y ABI con
`PatchAa10SpanishUiLayout.semantic_chunk` antes de automatizar nada.

## Comportamiento añadido

El launcher del sandbox usa `+client_default_zone 379` en la copia dedicada.
V1 añadía un gate `X2Debug:GetDevMode()` que resultó inválido: el consumer
release devuelve siempre false. V2 elimina ese gate y conserva el marcador
nativo379 y el destino exacto Sandbox/shard1.
`client_default_zone` es una opción nativa real: el Lua ya la pasa como
`zoneId` a `X2World:EnterWorld`. No es un flag inventado. En este modo se evita
que la lista de Zones del menú dev sustituya el destino379; fuera del modo
permanece el comportamiento anterior.

El selector elige sólo shard1 y nombre exacto `Sandbox`. Espera lista/cola,
comprueba restricciones nativas y primero muestra el personaje si aún no
estaba seleccionado. Luego solicita entrada una sola vez mediante el flujo
normal; `skipPrologue=true` es el mismo parámetro que ofrece el diálogo retail.
Los demás personajes y las ejecuciones sin el marcador mantienen el flujo
normal. No hay fallback al primer personaje.

V2 registra JSON `AA10_SANDBOX` mediante `UIParent:Log`, con `module_loaded`,
`world_request`, `character_request` y estados de espera acotados. La función
`UIParent:DevLog` usada en V1 es no-op en este release y no aportaba evidencia.

## Entrega reproducible

- Builder: `Scripts/PatchAa10SandboxAutoEntry.py`.
- Contratos: `Scripts/Aa10SandboxAutoEntry.contracts.json`.
- Aplicador y rollback: `Scripts/ApplyAa10SandboxAutoEntry.py`.
- Tests: `Scripts/tests/test_patch_aa10_sandbox_autoentry.py`.
- Único destino writable: `E:/AAEmu/rama_10/runtime/sandbox-aa10/client`;
  rechaza el principal, otro cliente, paquete compartido/hardlink y procesos
  de ese mismo sandbox abiertos. No cierra procesos.
- Fuentes, outputs, compilación, temporales y respaldos de esta tarea en E.
  El intérprete para las pruebas se compiló desde las fuentes Lua5.1.5 ya
  existentes en `artifacts/sandbox/lua51`; no se instaló software adicional.

Ambos ALB conservan su tamaño exacto:

| Entrada | Bytes | SHA-256 parcheado |
| --- | ---: | --- |
| stage_server | 13846 | D7D980A0EE5BE76365C7F07140025262E1A81CCE32A76EF7B4BFD063B427DF67 |
| character_select | 26728 | EAD7562CB167E4CB7040480852DD6D0BE17D20AE888D3D8D870A398D9A244A1F |

El aplicador extrae entradas efectivas, valida SHA del cliente y compilador,
guarda rollback antes de escribir, aplica con `PakEntryReplace`, reextrae y
verifica entradas más mapa/icono/UI de crafting. Registra hash/tamaño completo
del paquete y tiene compensación inversa ante fallo multientrada. Conserva
FILETIME a precisión de100ns: `PakEntryReplace` transmite el mtime del archivo
de reemplazo al FAT. Los extractores no lo conservan por sí solos. El aplicador
lee los registros WIBO efectivos, fija el mtime determinista de cada output y
restaura el del respaldo; la verificación revisa contenido y FILETIME.

```powershell
python -B Scripts/ApplyAa10SandboxAutoEntry.py
python -B Scripts/ApplyAa10SandboxAutoEntry.py --apply
python -B Scripts/ApplyAa10SandboxAutoEntry.py --rollback-manifest E:\ruta\manifest.json --apply
```

## Validación

14 pruebas correctas, ninguna omitida. Ejecutan con Lua5.1 real el
`SelectCharacter`/`TryToEnterGame` retail parcheado y los controladores:
gating desactivado, marcador incorrecto, personaje ausente, cola, ubicación,
borrado, renombrado, traslado, selección previa y ausencia de doble envío.
Dos builds producen exactamente los mismos hashes; corrupción de ALB y
fuentes desconocidas se rechazan; outputs ya instalados se reconocen.
Las pruebas adicionales comprueban conversión FILETIME/mtime_ns sin pérdida
y lectura de registros WIBO sin interpretar nombres ajenos como UTF-8.

Evidencia local inicial:
`forensics/output/aa10-client-forensics/sandbox-intake-20261029/autoentry`.

La aceptación retail de entrada y el roundtrip real de paquete se registran
en los manifiestos de despliegue. Esta prueba de Lua no demuestra por sí sola
que una sesión retail haya entrado y que la Zone procese el escenario.

Roundtrip del paquete real realizado en la copia dedicada: tras apply y
rollback por entrada, el SHA-256 completo volvió exactamente a
`FC386DB43C7C17EB7E5A59348877E14BF2CD1DE58BC54830EEB2C81359028673`,
igual al original observado en dry-run. Tamaño `92,412,664,320` bytes,
mapa/icono/UI de crafting sin cambios. Manifiesto inicial aplicado:
`backups/client-patches/aa10-sandbox-autoentry-v1-20261029-223957-215264Z/manifest.json`.
Su subdirectorio `rollback-*` conserva la verificación completa.

Reaplicación final con FILETIME determinista instalada en la copia dedicada:
SHA-256 completo
`FC13C158A10FAE014A0C979B9CCABBE4DD1304CC73FFC4E619C8EEB30D20ADCA`,
mismo tamaño. Manifiesto:
`backups/client-patches/aa10-sandbox-autoentry-v1-20261029-224643-223293Z/manifest.json`.
La segunda extracción/construcción produjo `before == after` para ambas
entradas, y el consumidor transaccional no intentó escribir. Se verificaron
de nuevo FILETIME, mapa, icono y crafting, manteniendo inode/tamaño/mtime del
paquete antes y después. Se reutilizó el hash completo de la aplicación
acabada; no se volvió a leer92GB sin mutaciones nuevas.

El marcador `runtime/sandbox-aa10/autoentry-applied.json` enlaza ese manifiesto,
SHA completo, identidad del paquete, perfil `Sandbox`/shard1/zone379 y evidencia
de idempotencia. `package_mtime_ns` usa época Unix a precisión nanosegundos;
debe leerse como entero de64bits. El launcher valida ese vínculo antes de
abrir la copia del cliente. Aceptación retail de entrada aún independiente.

Observación retail inicial asistida: personaje1001 `Sandbox` en sala379.
El usuario aclaró que tuvo que seleccionar mundo y pulsar Entrar; por tanto
esa sesión NO acepta entrada automática. Evidencia de estado online en
`runtime/sandbox-aa10/captures/20261029T225927Z-begin.json` y
`runtime/sandbox-aa10/profile/ArcheAge.log`. Los ocho dummies del primer begin
evidenciaron un problema de binding de la colección, independiente de la
preparación del escenario, que se corrige en su consumidor. Ver también
`CHECKPOINT_SANDBOX_DIRECT_PRESENTATION_20261029.md` para el arranque invisible
y el argumento nativo `-nosplash`, sin cambiar `x2game.dll`.

## Corrección V2 del driver

Clausura nativa: registro de `GetDevMode` en RVA0x803780 enlaza el wrapper
RVA0x803520 (75bytes). Este construye un boolean false y lo devuelve, sin
consultar la línea de comandos. Registro UIParent enlaza `DevLog` con
RVA0x4D0BC0 (151bytes), que extrae el argumento y retorna sin log; `Log`
enlaza RVA0x4D0AD0 (225bytes), que sí llama a `X2Log(2,"%s",text)`.
Los tramos completos están reanclados exactamente del corpus2735819 al
binario405242. El catálogo auxiliar lua-types tenía direcciones distintas y
no se utilizó como autoridad para las llamadas.

V2 incorpora polling real en `wnd:SetHandler("OnUpdate", ...)` para la lista
de mundos tardía. Las pruebas ejecutan ambos Lua retail completos y sus
handlers con GetDevMode=false, lista vacía en OnShow y aparición posterior del
shard correcto. Prueban el defecto que V1 no cubría; la aceptación sin clics
permanece pendiente hasta repetir el cliente real sin ayuda del usuario.

Los dos ALB V1 son entradas de upgrade explícitamente aceptadas; la transacción
guarda su estado actual para revertir V2 a V1 sin perder los cambios españoles.
Los outputs V2 fijos son A16180E20C5C946EC559DACF289E1902BC571E18B1595B0406BF3D31D4D6A482
y C02AE49D7B291F2FAD97A4E9ED3F632995F4F251D814107E3EBAEA5695E57C3E.

## Punto de parada solicitado por el usuario

El usuario pulsó Escape físico durante Computer Use; se detuvo la interacción
con el cliente y no se aplicó V2. Estado al terminar esta pasada:

- Código, contratos V2, polling, logging nativo y14 pruebas están preparados;
  las14 pruebas pasaron sin omisiones.
- Dry-run de upgrade V1→V2 correcto, sin mutar el paquete:
  `backups/client-patches/aa10-sandbox-autoentry-v2-20261029-230806-450974Z/manifest.json`.
- El `game_pak` operativo de la copia continúa en V1, SHA completo
  `FC13C158A10FAE014A0C979B9CCABBE4DD1304CC73FFC4E619C8EEB30D20ADCA`.
  El marcador `autoentry-applied.json` aún describe V1, no V2.
- El cliente del usuario permanece abierto; esta pasada no lo cerró ni cambió
  sus archivos después de la interrupción.
- La sesión observada fue asistida por el usuario y contenía ocho dummies.
  No hay aceptación de entrada sin clics ni de la herramienta de recarga en vivo.
- Para continuar se requiere la reanudación explícita del usuario. Antes de
  escribir el paquete, coordinar el cierre exclusivo de la copia sandbox,
  aplicar V2 con respaldo, reextraer/verificar y actualizar su marcador.
  La aceptación debe repetir el arranque con cero entradas de UI y comprobar
  los eventos JSON nativos junto con entrada completa y escenario listo.

No se programa continuación automática ni se efectúan operaciones del runtime
desde este punto de parada.

## Reanudación explícita y aplicación V2

El usuario reanudó explícitamente la tarea y autorizó cerrar/relanzar sólo la
copia sandbox. El agente principal confirmó que no quedaban procesos de ese
cliente antes de escribir. Se aplicó V2 al paquete dedicado; el principal y
su proceso no se tocaron.

Manifiesto final:
`backups/client-patches/aa10-sandbox-autoentry-v2-20261029-231655-673585Z/manifest.json`.
SHA-256 completo después de las mutaciones:
`CC69C39764C77501EA3C8B421B994854748F5CB0B9FE36DB719860929823073B`.
Tamaño `92,412,664,320` bytes; `x2game.dll` conserva405242.
El hash anterior se reutilizó sólo porque el marcador previo seguía ligado
al mismo inode/tamaño/mtime; después de escribir se realizó una lectura
SHA-256 completa nueva. No se repitieron lecturas completas sin mutaciones.

La segunda extracción/construcción verificó idempotencia sin escribir, ambos
ALB, FILETIME, mapa/icono/UI de crafting e identidad del paquete intactos.
El subdirectorio `idempotence/manifest.json` guarda la prueba.
`runtime/sandbox-aa10/autoentry-applied.json` ya enlaza esta V2 verificada.

La aceptación verdaderamente sin clics y la prueba de recarga en vivo aún
requieren el nuevo arranque real coordinado por el agente principal. No se
reutiliza como aceptación la sesión asistida de V1.

## V3: evidencia negativa del marcador y alcance por realm

El arranque real V2 oculto registró el módulo a20:25:37 con `marker:-1` y
`dev_mode:false`; la autenticación terminó correctamente a20:26:04 pero no
hubo selección automática. Evidencia negativa conservada por el coordinador:
`runtime/sandbox-aa10/captures/client-v2-marker-negative.log`. La presencia
del registro CVar y los argumentos separados no probaron un valor efectivo379.
V2 tampoco constituye aceptación de entrada sin clics.

V3 retira esa dependencia. La instalación está limitada a la copia física
sandbox que el runner enlaza al perfil E y al hash completo del paquete.
El polling sólo solicita mundo cuando la lista contiene simultáneamente
id1 y nombre exacto `AA10 Sandbox`; sólo esa solicitud automática suministra
zone379 al consumidor nativo. El flujo manual conserva su CVar/combo y el
valor nativo-1. La selección y omisión del diálogo inicial sólo se activan
si `X2World:GetCurrentWorldName()` es exactamente `AA10 Sandbox` y el nombre
del personaje es exactamente `Sandbox`. Colas y restricciones retail siguen
siendo comprobadas. Se usa `EnterWorld`/`SelectCharacter`, sin saltar protocolo.
El valor CVar se registra sólo como diagnóstico.

Quince pruebas pasan: ambos archivos retail completos ejecutan sus handlers
con marker-1 y devmodefalse; realm incorrecto con id1 queda inerte; lista
correcta tardía se acepta una sola vez; personaje/realm incorrectos no se
seleccionan; entrada manual conserva zone-1; se mantienen todas las demás
restricciones y contratos reproducibles. ALB V1 y V2 son orígenes de upgrade
aceptados explícitamente y quedan respaldados sin alterar los parches previos.
La aceptación nativa sin interacción aún depende del lanzamiento V3 real,
coordinado por el agente principal; ninguna prueba Lua sustituye ese paso.

Aplicacion V3 final autorizada tras confirmacion de cierre exclusivo de la
copia sandbox: `backups/client-patches/aa10-sandbox-autoentry-v3-20261029-232829-651761Z/manifest.json`.
SHA-256 completo nuevo despues de escribir ambas entradas:
`C734AB98C089E55C08A5729F3C1916D7ADAF0CFF93F164077B8CFF66AFA622A7`.
Se conserva tamano `92,412,664,320`, inode281474978774392 y mtime_ns
`1793316541796565500`. El original espanol y `x2game.dll`405242 no se tocaron.

Segunda extraccion/construccion idempotente en `idempotence/manifest.json`:
ambos ALB `before==after`, transaccion sin intento de escribir, FILETIMEs
originales exactos, sentinelas de mapa/icono/crafting intactos e identidad del
paquete estable. El marcador `runtime/sandbox-aa10/autoentry-applied.json`
publicado atomicamente enlaza V3, ese manifiesto, hash completo y realm exacto.
No hubo mutaciones del paquete tras el hash; no se repitio el escaneo completo.
La aceptacion sin clics permanece pendiente del lanzamiento real V3 del
coordinador en este punto de comprobacion.

## Prueba real V3 sin entradas de UI; visual pendiente

El coordinador confirmo entrada real sin seleccion manual: `world_request`
a20:35:15 y `character_request` a20:35:19, seguida del primer intento de
escenario listo con cuatro dummies. Cliente70392, Game240 y Zone59768.
`profile/ArcheAge.log` muestra carga de gatekeeper_hall terminada20:35:26,
OnLoadingWorldComplete terminada20:35:27, HideLoadingScreen/StartScreenWorld
20:35:29 y segundo HideLoadingScreen20:35:33 tras el reset/teleport.
Esto acepta el driver de entrada automatica, pero el usuario observo pantalla
negra despues de presentar/enfocar la ventana. La aceptacion visual sigue
pendiente y el coordinador investiga el ciclo de presentacion D3D.

Comparacion solo lectura: el error X2Gm nil en gm_console.lua:655 tambien
aparece en el log de la sesion V1 manual visible a19:59:26 (archivo de backup
Time(19 58 20).log, linea1464); no distingue el fallo visual de V3.
El Lua automatico llama al mismo SelectCharacter que startBtn:OnClick y al
mismo TryToEnterGame: premium check, native SelectCharacter(index,true),
background Enable(false,true) y sonido normal. True es el valor de la rama
retail OkProc del dialogo de omitir prologo. No modifica ni invoca fader o
SelectPrologue. El flujo nativo llega a ocultar loading antes y despues del
reset. Sin evidencia de una causa en esos consumidores no se modifica el
paquete; la presentacion y el renderer se diagnostican de forma independiente.
