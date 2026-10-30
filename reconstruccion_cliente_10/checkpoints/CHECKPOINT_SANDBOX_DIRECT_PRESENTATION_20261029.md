# Presentación directa del sandbox AA10 — 2026-10-29

Objetivo: mostrar al usuario la arena ya preparada, sin splash, selector,
vídeos ni escenas de acceso visibles. Se conserva la autenticación, entrada,
carga del motor/mapa y autoridad real de Game/World/Zone.

## Evidencia nativa acotada

Se reutilizó el proyecto guardado
`forensics/ghidra/ghidra-projects-aa10-client-release/AA10X2GameRelease` en
modo `-readOnly -noanalysis`; no hubo importación ni análisis global nuevo.
El programa guardado corresponde a SHA-256
`2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76`,
base `0x39000000`. Se localizaron referencias a tres cadenas y se decompilaron
sólo sus tres funciones propietarias.

La copia operativa usa `x2game.dll` SHA-256
`405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.
Las tres funciones completas se compararon byte a byte por hash de su tramo
continuo con el PE operativo, y las tres coincidieron exactamente:

| RVA | Bytes | SHA-256 del tramo |
| --- | ---: | --- |
| `0x423BC0` | 94 | 3B42A7F13D18C1D822B3B43AE29CAC75D9F9750BA7E510E626E1F40957F4D36B |
| `0x773E60` | 610 | 7F41F7C223EF92F82183C4BA4E9D5571C298F24BD3D874C1C1C59869ECC7547F |
| `0x772A90` | 279 | 37ABA05FDE93ADA858A3612BD939ECA519A6AE96E4FDD6AF42F2CD8B48FAE6DF |

Evidencia completa local:
`forensics/output/aa10-client-forensics/sandbox-intake-20261029/startup/`:
`native-options-refs.log`, `startup-selected-2.stdout.log`,
`startup-byte-anchors-script.log` y `startup-reanchor.json`.
Ghidra usó home, preferencias, caché y temporales específicos en E.

## Opción nativa `-nosplash`

En RVA `0x423BC0`, la rama de cliente busca `-nosplash` en el comando mediante
`XlFindStringI`. Sólo cuando **no** lo encuentra crea e instala
`StartupSystemUserCallback`, el callback de la presentación de arranque.
Se puede añadir el argumento literal `-nosplash` al launcher de la copia
sandbox. No requiere cambiar ningún byte del binario ni del paquete.

## Dependencia `loginbg4`

`StartLoginPage`, RVA `0x773E60`, inicializa antes de elegir autenticación
automática o ventana de login. Si el flag de inicialización del manager,
offset `+0x48`, está a cero, ejecuta:

1. inicialización de fondo `0x772A90`;
2. inicialización del manager de cámaras `0x309EA0`;
3. selección de cámara de acceso `0x30A110`;
4. marca inicialización completada.

Después toma la rama de autoautenticación; esa rama ya devuelve fade-in cero.
El initializer `0x772A90` comprueba el nivel actual y carga `loginbg4` si no
estaba cargado. Es una dependencia observada del flujo actual, no una simple
duración Lua eliminable. No se ha probado una opción nativa que suprima ese
fondo manteniendo intactos sus consumidores y las cámaras.

Omitir esas llamadas por parche binario modificaría las condiciones de
inicialización del motor. Esta entrega conserva la dependencia y evita mostrar
la ventana hasta que se complete la entrada real y el escenario esté listo.
Ese gate de presentación pertenece al launcher; no falsifica estados de red,
no simula selección desde el servidor y no convierte una carga en instantánea.

## Observación de entrada previa asistida

La sesión llegó al personaje1001 `Sandbox`, sala379, con dummies visibles.
El usuario confirmó después que seleccionó mundo y pulsó Entrar: esta captura
NO demuestra entrada automática. Captura inicial:
`runtime/sandbox-aa10/captures/20261029T225927Z-begin.json`.
El log del cliente se escribió en
`runtime/sandbox-aa10/profile/ArcheAge.log`; registra autoauth a19:59:01–04,
shard1 `AA10 Sandbox` y el personaje correcto. La captura inicial contenía ocho
dummies por la combinación de defaults de colección y ConfigurationBinder;
su corrección se valida por separado en el consumidor del escenario.

El primer intento con `testtoken` no era válido para el handler de autenticación
actual. `CARequestWebAuthPacketHandler` requiere `aaemu-sha256-v1:` seguido de
64 dígitos hexadecimales y pasa por `PasswordAuthFlow`. La credencial exclusiva
del sandbox se guarda como Base64 de esos32 bytes en su DB aislada, conforme
a `PasswordService.HashForStorage`; no se relajó la autenticación global.

La presentación oculta y la aparición de la arena lista necesitan su propia
aceptación visual. El SHA operativo de `x2game.dll` permanece sin modificar.

Punto de parada: el usuario pulsó Escape físico y detuvo Computer Use.
No se modificó el binario ni se aplicó el driver V2 preparado después de ese
evento. La presentación sin pantallas y la entrada sin acciones de usuario
quedan pendientes de una prueba explícitamente reanudada.

## Reanudación: V3 y pantalla negra

V3 completó la entrada sin clics: `world_request`20:35:15,
`character_request`20:35:19 y escenario `ready`20:35:31 con cuatro dummies.
El usuario confirmó pantalla negra; esa sesión NO acredita aceptación visual.
Un reset posterior preservó la conexión y sustituyó los cuatro IDs, pero la
observación visual se interrumpió. No se había realizado la prueba C# aún.

La entrada V3 usa los mismos consumidores retail que el botón Entrar.
`X2Gm nil` ya aparecía en la sesión manual visible anterior; no distingue el
fallo. El log llegó a `StartScreenWorld` y `HideLoadingScreen`. No hay evidencia
para modificar el paquete por este síntoma.

Se retiró del lanzador la repetición de `ShowWindow(SW_HIDE)` cada25ms y la
activación de primer plano. La nueva candidata mantiene la ventana gráfica
visible para Win32, fuera del escritorio durante la carga, y repone su posición
con `SWP_NOACTIVATE`/`SW_SHOWNOACTIVATE`. Tres opciones del perfil sandbox E
se arriendan temporalmente con recuperación tras una interrupción. El perfil
principal no participa. Esto es una hipótesis de reparación de presentación,
pendiente de confirmación visual, no una causa D3D demostrada.

Referencias Win32: [ShowWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindow)
y [SetWindowPos](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowpos).
Pruebas sin ventanas ni entradas reales:7 de presentación; batería Python
completa52/52. El usuario realiza las comprobaciones visuales desde este punto;
no usar Computer Use, capturas ni activación de su escritorio.

El ajuste inicial del runner comprobó un ObjectId nuevo. Se sustituyó después
por la validación de conexión activa y `WorldEntryCompleted` descrita abajo,
porque el ObjectId puede persistir entre conexiones.

## Cierre de la investigación de presentación

El candidato fuera de pantalla también falló visualmente. El mismo cliente,
paquete V3 y servidor funcionaron con la presentación visible normal, según
confirmación del usuario. El usuario confirmó después arena y movimiento tras
dos resets y la modificación/reversión C#; la recarga conserva la sesión real.
Evidencia: `Docs/AA10SandboxHotReload_es.md` y capturas JSON de aceptación.

La variante DWM fue descartada: Windows devuelve `HRESULT 0x80070005` al intentar
ocultar por composición la ventana del otro proceso. No se altera la seguridad
ni se intenta inyección o elevación para eludirlo.

La implementación final conserva el arranque visible normal que funcionó y
presenta un panel Tk propiedad del propio lanzador mientras prepara la escena.
Sólo posiciona ese panel: mantiene las otras aplicaciones por encima si ya
estaban encima del juego, no lo hace topmost y no activa el escritorio. No
modifica posición, visibilidad ni composición de la ventana gráfica nativa.
El código experimental descartado se respaldó en
`runtime/sandbox-aa10/backups/presentation-experiments/`; no es la implementación
que usa el lanzador. Las siete pruebas del panel usan mocks y ninguna ventana
real; batería Python53/53. La aceptación visual final depende del usuario.

Se corrigió además la detección de sesión: el API del sandbox resuelve ahora
`GameConnectionTable`, en lugar de un avatar retenido en la caché de World.
El manager reconoce al nuevo actor al reconectar y retira sólo sus dummies
anteriores. El runner espera el `WorldEntryCompleted` validado por ese API,
no un ObjectId que puede persistir entre conexiones.

## Aceptación visual del panel y cierre de Tcl

El usuario confirmó con el acceso normal: «Sí, carga y puedo jugar en la arena».
Esto acredita la entrada automática y el panel retirado con escena visible,
sin pantalla negra. La prueba fue manual; Codex no manejó su escritorio.

El panel inicial alojaba Tk en un hilo y el cierre de su intérprete produjo
`Tcl_AsyncDelete`, sin cerrar el juego. Se aisló la misma presentación en un
proceso `pythonw`, con Tk exclusivamente en su hilo principal. El lanzador se
comunica mediante una señal y un JSON de error en su directorio temporal E.
Verifica además que el PID gráfico corresponde al ejecutable propio antes de
preparar el panel; el panel sólo modifica su propia ventana. El juego permanece
sin cambios de posición, visibilidad o foco por parte del lanzador.

La batería Python actual pasa 55/55 y contiene un caso de cierre de Tcl en un
proceso principal independiente sin cargar Tk ni crear ventanas de escritorio.
`Comprobar cierre del panel.cmd` verifica adicionalmente el helper real con la
señal de finalización ya creada: su ventana permanece retirada, sin cubrir el
juego, y se comparan proceso y sockets antes/después. Esta comprobación la
inicia el usuario; no requiere relanzar el juego ni perder su sesión.

Resultado final: el usuario ejecutó esa comprobación y confirmó «Sí, muestra OK
y sigo conectado». El helper real terminó con código 0; el cliente 5432 y sus
dos sockets permanecieron iguales. La captura `*-panel-helper-exit.json` registra
la comprobación, y `*-delivery-accepted.json` reúne aceptación visual, escenario
ready con cuatro dummies, runtime World 240 con contador CLR 3 y referencias a
la modificación/reversión C#. Se conservaron el cliente actual y la Zone 59768
abiertos; la Zone habitual 23668 y el stack habitual no se reiniciaron.
