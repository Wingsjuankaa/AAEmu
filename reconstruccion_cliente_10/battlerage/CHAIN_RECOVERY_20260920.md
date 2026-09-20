# Reparación del GCD y de las respuestas de habilidades encadenadas

Fecha: 2026-09-20. Rama `rama_10`; base `76941d5539d9627f6366d7fc40bb2d37e3a781ea`.
Padre inspeccionado: `upstream/client_version/zone-10.0.2_r575`,
`7851f67cc0c46fb76b4fafc3414b6754685d96f2`. Sin integración nueva.
Clasificación: **client-native** para el resultado de SkillStarted;
**server-required** para conservar la autorización de Combo sin saltarse el GCD.

**Implementado, probado y desplegado; pendiente de aceptación visual del usuario.**
Este documento sustituye el estado operativo del rollback descrito en
[CADENCIA_20260920.md](CADENCIA_20260920.md), que se conserva como historial.
No certifica la cadencia completa de todas las habilidades por una suite verde.

## Resultado de la investigación histórica

Hay una referencia positiva anterior: [Neblina, 11 de septiembre](../../Docs/AA10NeblinaReconstruction_es.md)
identifica Flechas incesantes `14835/14836/14837` como funcionamiento aceptado
por el usuario. Su base era `fd53b4585`, con 89 paths ya modificados; no equivale
a una imagen reproducible íntegramente validada. `45bba0ad4` consolidó trabajo
posterior de ese día. El checkpoint Garden del 11 registra también la reparación
del ciclo de vida de sus proyectiles. Esa reparación sigue presente y cubierta
por `ProjectilePlotLifecycleTests`.

| Cambio | Entrada en el fork / efecto comprobado |
|---|---|
| `d216e9da1367a675da98b705427f2cdebf466976` | Merge `c50ffacca`, 16-09 09:52 Chile. Amplió la supresión de `CooldownTime` de ataques básicos 2/3/4 a cualquier skill con `StartAutoAttack` o GCD pequeño. Las familias observadas tienen ese flag, aunque sean habilidades activas. |
| `474f400a4` | Merge `29d68e3f2`, 18-09 12:38 Chile. Exigió habilidad aprendida sin contemplar hijos internos de Combo. Estos no pertenecen al libro aprendido. |
| `b6dff8092` | 18-09 15:25 Chile. Hammer Toss: anchors/visibilidad de plots y reset por tags. No modificó `Skill.cs` ni los tiempos de las cadenas. El blob de `Skill.cs` antes del martillo y en `bd8299f59` es `cec3d2c60b3aa6003b95e75397f678be645c1d9d`. |
| `67e00c1aa` | 18-09 20:35 Chile. Autorizó el siguiente hijo de Combo, pero también le permitió saltarse el GCD compartido. Explica por código la admisión demasiado rápida de las continuaciones. |
| Candidato retirado del 20-09 | Volvió a imponer el GCD pero conservó la supresión del resultado de rechazo. El usuario rechazó las pausas. Revertido antes de esta reparación. |

La referencia histórica no permite fijar el primer instante en que el usuario
experimentó cada síntoma. Sí permite localizar los cambios responsables de los
bloqueos que se reproducen en pruebas y registros. No se atribuye la regresión
del GCD al arreglo espacial del martillo.

## Evidencia del cliente exacto y del fallo

Release x64: SHA-256 `2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76`,
base `0x39000000`. Fuente inmutable leída: `Bin64/x2game.dll.pre_auroria.bak`.
El `x2game.dll` de la carpeta llamada referencia también lleva actualmente el
parche Auroria; su nombre de carpeta no demuestra inmutabilidad.
Cliente español efectivo: `405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`.
Se comprobaron **idénticos los bytes de las cinco funciones** entre backup y cliente efectivo.

| RVA | Consumidor verificado |
|---|---|
| `0xAC68C0` | Deserializa SkillStarted, incluida la tupla de resultado. |
| `0x33BCD0` | Pasa los campos del mensaje al controlador de habilidades. |
| `0x6DEE00` | Antes de separar éxito y error, retira la petición correspondiente del estado pendiente. El error también publica SkillEventParam `0x16`. |
| `0x6D5290` | Localiza y retira la entrada por caster y skill. |
| `0x6D6240` | Procesa el error para el caster local; se llama después de retirar la petición. |

Por tanto, omitir un SkillStarted fallido no equivale a ocultar sólo un mensaje
de UI: elimina una transición del estado de peticiones del cliente.
La prueba de packet usa el `Read` de producción, el `Skill.Use` real y una sesión
que registra los bytes enviados, no sólo la serialización aislada del paquete.

Los registros del vídeo rechazado contienen `14835` aceptada a
`15:12:28.800287 UTC`, `14836` recibida a `28.870406` sin timeline ni respuesta de
fallo y un reintento a `29.359430` aceptado como timeline 201. El intervalo de
489 ms es **observación de logs**, no una nueva constante de animación ni una
prueba del valor exacto del timeout nativo. No se codifica ese intervalo.

La auditoría previa de 145 filas de cadenas conserva igualdad full/runtime y
de las 134 filas compartidas con el compact efectivo. Sus hashes y vídeos siguen
en el [manifiesto anterior](cadence-manifest.json). No se alteraron datos del
cliente, animaciones, plots, SQLite ni persistencia de personajes.

## Corrección aplicada

1. Una continuación Combo válida vuelve a respetar `GlobalCooldown`.
2. Un rechazo por cooldown vuelve a enviar `SCSkillStarted(CooldownTime)` para
   habilidades de repetición y cadenas, también con `StartAutoAttack` o GCD corto.
3. Se conserva la autorización efímera del hijo exacto, sin aprenderlo ni gastar
   puntos. Un rechazo no consume ni renueva la autorización.
4. Se conserva la excepción existente de ataques básicos 2/3/4; no se amplía.
   También se conserva la omisión del guard genérico de 150 ms para un hijo válido,
   y los controles de cooldown propio, tags, cargas y cuenta.

No hay temporizadores nuevos, autocasts, colas de reintentos ni tiempos por ID.
Los IDs en las pruebas identifican familias que exponen el mismo fallo genérico.
Los fixtures aíslan los gates; no pretenden simular el combate completo ni el
cast inicial de Flamebolt.

## Pruebas y límites de aceptación

- Antes de la corrección: 12 casos de dispatch fallan por ausencia de respuesta
  o por pasar indebidamente al gate de target; el caso de admisión de un hijo con
  GCD activo también falla. Los fallos iniciales de preparación del fixture se
  corrigieron antes de registrar este resultado rojo.
- Después: restore correcto, build Release sin errores, **5.504/5.504** pruebas,
  cero fallos y cero omitidas. Incluye 12 casos del nuevo dispatch, 14 de admisión
  y las regresiones existentes de proyectiles, permisos, puntos y Battlerage.
- Dispatch cubre ambas rutas (`ZoneAuthority` y local), root aprendido,
  continuación y rechazo repetido; exige un único paquete correcto, sin cambiar
  MP, GCD, `SkillLastUsed` ni el permiso pendiente. Familias: Endless Arrows,
  Triple Slash, Whirlwind Slash, Mana Stars, `18125/18126` y etapa corta de Flamebolt.
- Con GCD vencido, el hijo pasa el guard de spam hasta el siguiente gate de target;
  con cooldown propio o por tag, sigue rechazado. No se confunde ese resultado
  con daño o animación probados dentro del juego.
- No se iniciaron/detuvieron Zones ni se manejó el cliente. Prueba visual a cargo
  del usuario, según su última instrucción.

Consulta `BugReports.py --category skill --limit 50`: reportes abiertos 9, 8, 7
y 5. El 9 también refiere a Mana Stars, pero por alcance/sinergia; los otros
describen cancelación, buff o daño. No se cierran como resueltos por este arreglo
de GCD/respuestas ni se amplía su alcance sin investigar sus propios contratos.

Fronteras restantes: escalado de GCD por atributos y equipo, prioridad entre
`default_gcd/custom_gcd`, `GlobalCooldown` Special41 con valor cero y variantes
con tiempo de casteo. El historial incluye cambios en esas áreas; no se presentan
como equivalentes nativos ya cerrados ni se modifican por tanteo en esta entrega.
La corrección elimina dos defectos demostrados; no afirma haber recuperado cada
intervalo original para todas las razas, armas y velocidades.

Primera aceptación manual: mantener Endless Arrows contra un mismo objetivo y
comprobar continuidad y velocidad. Correlacionar después solicitudes, resultados
y timelines de ese intento antes de ampliar la aceptación a Triple/Whirlwind.

## Despliegue y reproducción

Servicio `game`, compose `aaemu10`. Imagen:
`sha256:783ac1533c8437b5a2723d08fce93070e8c4cb1137b0f4f5eb25aa6f73b2be1f`.
Inicio UTC `2026-09-20T15:53:52.553341273Z`.
Ambas copias `/app/AAEmu.Game.dll` y `/app/game/AAEmu.Game.dll`:
`70d124ddb4ea8984ba3d5eaf149eb004eac48ef3180de98418db622944877533`.
Compact runtime sin cambios: `85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
Rollback conservado: `aaemu-world:pre-chain-recovery-20260920`, imagen
`sha256:70afd1893a4aba156881fb4970284a4f4769cfbcc8f967289f98cc5f17752246`;
es el estado anterior conocido como demasiado rápido, no una versión certificada.

Readiness verificada: contenedor `running/healthy`, cero reinicios, API World
responde `[]`, Transfers cargados a `15:56:32 UTC` e IndunManager activo.
El arranque conserva cuatro errores de definiciones Smelting (29–32, área
deprecada y sin cambios) y una conexión/desconexión inicial con `zoneId=0`.
No hubo ZoneLoaded ni proceso ZoneHost observado; no se certifica arranque de Zone.

Evidencia nueva: `E:\AAEmu\rama_10\artifacts\chain-recovery-20260920`.
[Manifiesto](chain-recovery-manifest.json) incluye hashes de artefactos y readiness.
Decompilación reproducible: `Aa10SkillStartedResultAudit.java`, Ghidra con
`-readOnly -noanalysis` sobre `AA10X2GameRelease/x2game.dll`.
Reanclaje: `audit_skill_started_result.py RELEASE EFFECTIVE GHIDRA_LOG`;
falla ante hash, arquitectura, base o bytes diferentes. No modifica los binarios.
