# Sandbox AA10 y pruebas en caliente

Estado aceptado el 29 de octubre de 2026. Consultar los scripts/documentos del
repositorio y el estado vivo en cada tarea; no fijar PIDs de sesiones antiguas.

## Entorno y uso

- Código: `E:\AAEmu\rama_10\server\AAEmu`.
- Runtime: `E:\AAEmu\rama_10\runtime\sandbox-aa10`.
- Escena actual: Zone411 `aa10_sandbox_lab`, World0/Instance0. Hall379 fue el
  escenario anterior y sigue siendo el bootstrap histórico, no el mapa actual.
- Acceso: `Iniciar sandbox AA10.cmd` dentro del runtime. Pedir al usuario que
  lo abra si no ha autorizado abrirlo tú. El usuario pidió realizar las pruebas
  personalmente: no controlar su escritorio, teclado, ratón ni foco.
- `Herramienta de desarrollo.cmd`: controles de reset, posiciones y distribución
  en vivo, contador CLR y PID World. Puede iniciar watch; no abrirla sólo para
  inspeccionar un runtime saludable.
- `Estado sandbox.cmd`, `Reiniciar escenario.cmd` y
  `Aplicar laboratorio de entrenamiento.cmd` reutilizan el runner versionado.

El español usa +locale en_us. Mundo y personaje entran solos y un panel propio
cubre la carga sin alterar la ventana gráfica normal. No reintroducir
ocultación/offscreen, minimización, DWM ni elevación: causaron pantalla negra o
acceso denegado. Una sesión online se reutiliza.

Sandbox1001/cuenta1 es un clon privado. Dummies7512 y servicios reales:
18870/Toosten especializaciones,1023/Tiri banco,1497/Vigdia armas y1498/Giyolla
armaduras. Menús y costes normales. Reset conserva las especializaciones,
restablece la tentativa y recrea actores; no revierte inventario, XP, quests
ni todos los objetos/invocaciones producidos por mecánicas. CombatProfile
excluye únicamente el pasivo369 del clon para evitar su cadena de tesoros al
restaurar. No desactivarlo globalmente ni forzar callbacks/buffs rechazados.

## Aislamiento y autorización

Compose aaemu10-sandbox tiene DB/Login/Game propios. Login3237, Game3239,
Stream3250; Native conecta a World3240 en la IP LAN configurada. DB/API1280
no se publican. Cliente, Native, catálogos y perfiles son copias privadas.
Todo nuevo output, temporal, caché, backup y captura va en E. No imprimir
.env, Game.json, credenciales, tokens ni la línea de comando del cliente.

No ejecutar prepare/seed ni recrear el stack para diagnosticar una sesión viva.
Leer sandbox.json, watch-mode.json, zone411-installed.json y captures.
La autorización de una prueba anterior no se extiende a una nueva tarea:
respetar la política de Zones del SKILL principal y el alcance actual. Cuando
esté autorizado, usar sólo el launcher/perfil sandbox, validando ownership,
ruta, PID y creación. No tocar el Native habitual ni reiniciar una Zone sana
para editar cuerpos C# compatibles.

## Observar sin tocar la pantalla

Desde el repo, TEMP/TMP en runtime\sandbox-aa10\temp, Python -B. El API se
consulta mediante docker exec interno, sin publicar puertos:

```python
import sys
sys.path.insert(0, 'Scripts')
import aa10_sandbox as s
root = s.DEFAULT_ROOT
runtime = s.api(root, '/api/mechanics-sandbox/runtime')
world = s.api(root, '/api/world/zone-manager-status')
scenario = s.command(root, 'status')
```

World puede conservar un avatar desconectado; el controller tipado resuelve la
conexión Game activa y valida WorldEntryCompleted. Usar s.capture para guardar
respuestas y aceptación. Leer logs filtrados: logs/launcher-start.log,
profile/ArcheAge.log y zone-save/sandbox-411. Evitar dumps con tokens.

## Hot Reload real

1. Confirmar runningUnderWatch, hotReloadSupported, actor conectado y Zone411
   ZoneLoaded con heartbeat. Registrar PID World, updateCount, sesión Native,
   personaje/objeto e identidades de cliente/Native.
2. Respaldar fuentes en E. Cerrar el contrato AA10 y pruebas focales; editar
   consumidores reales bajo AAEmu.Game/AAEmu.Commons. No crear otra simulación.
3. Preferir cuerpos de métodos compatibles. Estructura, inicialización, paquetes
   o DLL nativa pueden exigir reinicio. **El watch usa --non-interactive y
   reinicia ante rude edits**: no significa que descarte esos cambios. Valorar
   compatibilidad antes de guardar una edición que pueda cortar la sesión y
   respetar la autorización de lifecycle.
4. Exigir aumento del contador CLR, mismo PID, mismos cliente/Native y sesión
   online; comprobar efectos reales en logs. Si se necesita una tentativa limpia,
   s.command(root,'reset') y esperar s.ready_result(root). No resetear por rutina
   mientras el usuario esté probando un lanzamiento.
5. Pedir una interacción concreta, comprobar resultado/log antes del siguiente
   caso, compilar y probar. Una compilación verde o hotReloadSupported=true por
   sí solos no prueban que se aplicó código ni que una mecánica funciona.

Caso aceptado:23592/Disparo de precisión, área lineal corregida, contador0→2,
misma sesión y daño a30 y44–45 m confirmado. La imagen Game habitual no se
recreó. No presentar un arreglo del sandbox como desplegado al servidor normal.

## Escena y errores ya resueltos

Zone411 es custom de la herramienta, reutiliza terreno/modelos de la arena
retail406 y no es un hallazgo retail. Sólo main_world privado se redujo a2×2
celdas; el continente original permanece intacto. Origen575/506/256.25 y
offsets por actor en Scripts/aa10_sandbox_training_hub_zone411.json. No volver
aZ260 del spawn donante: dejaba dummies flotando y NPCs saltando.

InitialConfig.LobbyLevel privado debe ser aa10_sandbox_lab. Con w_hanuimaru_1
se detenía en selección de servidor porque falta en el mundo reducido.
Geometría, catálogos, ALB y Native no son Hot Reload C#: usar builders,
contratos, manifests y rollback. No forzar marcadores ni omitir hashes.

## Referencias mantenidas del repositorio

- Docs/AA10MechanicsSandbox_es.md y AA10MechanicsSandboxResetContract_es.md.
- Docs/AA10SandboxHotReload_es.md: montaje SDK y evidencia de sesión.
- Docs/AA10SandboxSeparateZone_es.md: escena411, paquetes, catálogo y rollback.
- Docs/AA10SandboxTrainingHub_es.md y AA10SandboxProfile_es.md.
- Docs/AA10PrecisionShotRange_es.md: arreglo real en caliente.
- reconstruccion_cliente_10/checkpoints/CHECKPOINT_SANDBOX_SEPARATE_ZONE_20261029.md.

Runner: Scripts/aa10_sandbox*.py y Start-AA10Sandbox.ps1. Skills mantenidas en
Skills/aa10 del repo, enlazadas desde Codex mediante Scripts/Install-AA10Skills.ps1.
