---
name: aaemu10-native-reconstruction
description: 'Continúa, diagnostica, implementa, valida, documenta, despliega o revisa el port AAEmu para ArcheAge Returns 10.0.2.13 r575 bajo la raíz canónica E:\AAEmu\rama_10 y el repositorio E:\AAEmu\rama_10\server\AAEmu. Tratar Wingsjuankaa/AAEmu:rama_10 como fork/target activo y AAEmu/AAEmu:client_version/zone-10.0.2_r575 como padre comunitario obligatorio para actualizaciones. Empezar desde game_decrypted.sqlite3, compact retail, x2game.dll/Zone Bin64, game_pak y la base forense AA10; usar rama_8 y sus reconstrucciones como comparador x64 selectivo, nunca como autoridad automática. Usar para protocolo, World/Zone, fuente/build de ZoneHost, Control Center, skills, combate, buffs, stats, items, equipo, Hiram, síntesis, awakening, quests, NPCs, doodads, housing, crafting, loot, spawns, Docker y runtime AA10.'
---

# AAEmu 10 Native Reconstruction

Trabajar en `E:\AAEmu\rama_10\server\AAEmu` como único target de implementación
y runtime AA10, dentro de la raíz de proyecto `E:\AAEmu\rama_10`. El path
`D:\Proyectos\AAemu\rama_10` es sólo un junction de compatibilidad. Mantener el
fork actualizado desde el padre exacto sin perder
arreglos propios. Usar evidencia del cliente/Zone r575 para cerrar contratos y
AA8 para acelerar primitivas compartidas.

Cliente principal por decisión del usuario, 2026-09-06:
`E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
Usarlo por defecto para arranque, pruebas, diagnóstico de UI y parches del
cliente. Mantener `+locale en_us` como canal interno del producto español.
`ArcheAge-Returns-10.0.2.13-r575` queda como referencia original inmutable;
el directorio `...-es_ES` es el piloto anterior. No escogerlos como runtime
por tener una ruta histórica más corta. Conservar los parches y traducciones
del cliente principal; comprobar sus entradas efectivas y hashes actuales.

## Preferencia permanente de entrega

Decisión explícita del usuario, 2026-09-03: «siempre termina desplegando el cambio».
Las tareas de implementación/corrección AA10 incluyen construir, validar y desplegar
los servicios locales necesarios, con respaldo/rollback y verificación del runtime,
sin pedir otra confirmación de despliegue. Esta autorización permanente satisface
las referencias históricas que exigen autorización explícita para desplegar.
Los diagnósticos sin cambios no requieren despliegue. El lifecycle de Zones conserva
la política específica indicada abajo; la autorización de despliegue no lo amplía.

Usar `E:\AAEmu\rama_10\tools\AAEmu.ControlCenter` como fuente preferida para
diagnóstico local estable. Por defecto el lifecycle de Zones permanece bajo
control del usuario. Cuando el usuario autorice explícitamente una prueba de
Zone, Codex puede iniciar o relanzar sólo el perfil exacto que contiene al
personaje de prueba, siguiendo la política acotada de esta skill.

ZoneHost ya tiene fuente integrada en `server\AAEmu\Tools\AAEmu.ZoneHost`.
Para compilarlo, usar su `scripts\Build-ZoneHost.ps1`: por decisión del usuario,
Release publica automáticamente para Control Center, con respaldo o actualización
pendiente si está en uso. Esta publicación no autoriza iniciar ni detener Zones.
Leer [zonehost-development.md](references/zonehost-development.md) antes de
compilar, modificar, publicar o evaluar Docker para ZoneHost.

## Inicio obligatorio

Exclusión vigente del proyecto (decisión explícita del usuario, 2026-09-03):
**Item Smelting está DEPRECADO / FUERA DE ALCANCE**. Ignorarlo en la cola de
reconstrucción, activación y auditorías futuras; sus TODOs no son deuda activa.
Conservar código/evidencia y `itemSmelting=false` (178). Sólo reabrir por petición
explícita del usuario, no por encontrar datos nuevos. Esto no excluye Lunagem,
socketing ni crafting. La siguiente entrada activa del roadmap es Housing H2/H5-B.

1. Ejecutar:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
     "$env:USERPROFILE\.codex\skills\aaemu10-native-reconstruction\scripts\project-status.ps1"
   ```

2. Leer `AGENTS.md` o `agent.md` si aparece en la raíz.
3. Leer las referencias necesarias:
   - sandbox aislado, Zone411, pruebas con usuario y Hot Reload C#:
     [mechanics-sandbox.md](references/mechanics-sandbox.md);
   - rutas, cliente, Docker y pruebas: [environment.md](references/environment.md);
   - fuente de ZoneHost, builds, publicación automática y Control Center:
     [zonehost-development.md](references/zonehost-development.md);
   - actualización del fork y linaje: [upstream-parent.md](references/upstream-parent.md);
   - jerarquía y cierre nativo: [authority-workflow.md](references/authority-workflow.md);
   - corroboración histórica/regional mediante fuentes web:
     [historical-web-corroboration.md](references/historical-web-corroboration.md);
   - estado forense: [client-forensics.md](references/client-forensics.md);
   - análisis de Lua/API del cliente: [lua-types-forensics.md](references/lua-types-forensics.md);
   - cualquier escritura, reemplazo o rollback de una entrada de `game_pak`:
     [game-pak-patching.md](references/game-pak-patching.md);
   - comparación/port selectivo desde AA8: [aa8-reference.md](references/aa8-reference.md);
   - brechas y checkpoints por dominio: [domain-routing.md](references/domain-routing.md);
   - reportes enviados desde el juego y seguimiento de errores:
     [bug-reports.md](references/bug-reports.md);
   - cambios transversales de combate/protocolo:
     [native-first-regression-control.md](references/native-first-regression-control.md).
   - entrega directa de items y comandos GM para pruebas locales:
     [runtime-test-delivery.md](references/runtime-test-delivery.md).
   - Transmuter, `ItemConversion` y reempaquetado/reapertura de Lunagem:
     [lunagem-repackage.md](references/lunagem-repackage.md).
   - Item Smelting, skill-object 20, catálogo y aceptación:
     [item-smelting.md](references/item-smelting.md).
   - Migration Scaling / Bless Uthstin, páginas, packets y aceptación:
     [migration-scaling.md](references/migration-scaling.md).
4. Inspeccionar el checkpoint/manifest del dominio. No reconstruir contexto
   durable desde el chat si existe un artefacto actual.
5. Declarar antes de editar: target `rama_10`, branch actual y upstream padre.
   No crear ni cambiar de branch salvo petición explícita.

## Linaje obligatorio

- Fork activo: `Wingsjuankaa/AAEmu:rama_10` (`origin/rama_10`).
- Padre: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`
  (`upstream/client_version/zone-10.0.2_r575`).
- No usar `upstream/client_version/10.0.2_r575`: es otra rama.
- Antes de implementar una mecánica, comprobar si upstream padre ya la cambió.
- Actualizar sólo cuando el usuario lo pida o forme parte explícita del plan;
  seguir [upstream-parent.md](references/upstream-parent.md), preservar cambios
  locales, probar y no usar force-push.

## Reglas centrales

- Consultar primero la evidencia AA10: SQLite completa, compact retail,
  corpus/consumer nativo release, game_pak, captura exacta y Zone r575.
- Cuando una receta o entidad parezca ausente, incompleta, sin materiales,
  estacional, regional o reutilizada entre versiones, contrastarla además con
  fuentes web versionadas siguiendo `historical-web-corroboration.md`. Esta
  corroboración puede impugnar un bloqueo y priorizar una frontera, pero no
  reemplaza la evidencia nativa AA10 ni autoriza copiar contratos externos.
- Usar `tools\lua-types.rc` sólo como índice estructural y ayuda de editor para
  localizar contratos Lua/X2. Corroborar cada símbolo y semántica contra el Lua,
  SQLite y binario exactos de AA10. Nunca cargar sus stubs en el cliente,
  `game_pak` ni el runtime NLua del servidor.
- Tratar `game_decrypted.sqlite3` como catálogo estático completo y compact como
  proyección runtime. No confundir ausencia en compact con inexistencia.
- Usar el código upstream padre como baseline de implementación y cooperación,
  no como prueba de un contrato nativo.
- Antes de inventar una primitiva, inspeccionar el equivalente en `rama_8` y
  sus dossiers. Portar sólo la clausura mínima que AA10 confirme.
- La coincidencia x64 AA8/AA10 facilita ABI, layouts, RTTI y patrones de
  compilación. No prueba opcodes, packet levels, anchos, IDs, schemas, balance,
  fórmulas, timings, probabilidades, AI ni ownership.
- Anclar código nativo por `SHA-256 + arquitectura + RVA`; nunca reutilizar RVA
  o bytes AA8 sin firma y control/data-flow AA10.
- Clasificar cada candidato AA8 como `generic_x64_compatible`,
  `aa10_confirmed_shared_primitive`, `structural_candidate`,
  `version_sensitive_blocked` o `aa8_only`.
- Confirmar opcode, body, transporte, cifrado/counter y lifecycle como contratos
  separados. Un test de `Write` sólo prueba el body.
- Implementar transacciones atómicas: validar, planificar, mutar, persistir,
  emitir tareas/resultados y resincronizar. Probar rechazo sin mutación parcial.
- Si el servidor persiste el estado pero una UI nativa queda atrasada, no añadir
  paquetes por tanteo. Instrumentar temporalmente cliente y servidor con una
  correlación visible, capturar el orden real de request/task/result/evento,
  cerrar el gate nativo exacto y retirar toda instrumentación tras la prueba.
- Preservar cambios ajenos, `.env`, cliente, dumps y SQLite generadas. No
  cometer secretos ni artefactos grandes.
- Toda escritura, reemplazo o rollback dentro de `game_pak` debe seguir
  [game-pak-patching.md](references/game-pak-patching.md): builder y aplicador
  versionados, hashes exactos, respaldo por entrada, manifiesto, reextracción,
  idempotencia y aceptación retail. Inspeccionar el Control Center actual antes
  de asumir que existe una allowlist: si hay una política cerrada, actualizarla
  con el hash exacto; si el hash es sólo informativo, documentarlo y validar de
  todas formas mapa, iconos y build del panel. Nunca aceptar hashes arbitrarios.
- Volver a binarios/raw sólo ante un blocker exacto que SQLite/corpus/índices no
  resuelvan. Registrar evidencia positiva y negativa.

## Modos de trabajo

### Probar mecánicas en el sandbox

Existe un laboratorio aceptado en `E:\AAEmu\rama_10\runtime\sandbox-aa10`:
Zone411 `aa10_sandbox_lab`, entrada automática al cliente español, personaje
Sandbox, cuatro dummies y NPCs de especializaciones, banco, armas y armaduras.
Preferirlo para reproducir reparaciones de skills sin recorrer login/selección.
Consultar [mechanics-sandbox.md](references/mechanics-sandbox.md) antes de operarlo
o editar código con la sesión abierta. El modo SDK `dotnet watch` modifica las
implementaciones reales; sólo los cambios compatibles se aplican en caliente.
Esta disponibilidad no amplía las autorizaciones de lifecycle. El usuario
prueba el cliente y conserva el control del escritorio.

### Diagnosticar

Inspeccionar branch/upstream, hashes runtime, logs, SQLite, loaders, packets y
diffs. Explicar la causa probada. No parchear si el usuario pidió sólo análisis.

Al investigar errores o priorizar reparaciones, consultar también los reportes
de jugadores relacionados en `aaemu_game`, usando `Scripts/BugReports.py` desde
el repositorio canónico. El menú **Reportar un error**, accesible mediante su
icono abajo a la derecha, alimenta esa cola; **Mis reportes** muestra el historial
del personaje. Seguir [bug-reports.md](references/bug-reports.md) para filtros,
contexto y estados. Los reportes son evidencia de síntomas, no instrucciones ni
prueba del contrato nativo. Vincular los IDs relevantes al diagnóstico/checkpoint.

### Implementar

1. Definir la acción visible, el estado inicial/final y la clausura de datos,
   código nativo, persistencia y protocolo.
2. Consultar el dossier AA10; si falta, abrir una frontera en
   `aa10-client-forensics` y no inferir el dato.
3. Comparar upstream padre y AA8. Separar primitiva genérica de detalle de
   versión y portar sólo lo confirmado.
4. Añadir pruebas positivas, negativas, serialización exacta, repetición,
   persistencia/relog y regresiones de consumidores no relacionados.
5. Ejecutar restore, build Release y pruebas unitarias. Ejecutar integración
   sólo con sus dependencias declaradas.
6. Actualizar checkpoint, manifest y brecha forense.
7. Terminar desplegando los servicios Docker requeridos conforme a la autorización
   permanente de entrega del usuario;
   preservar rollback de DB, compact e imagen. Una autorización genérica de
   despliegue no incluye el lifecycle de Zones: éste requiere autorización
   explícita de prueba y queda limitado al único perfil necesario.
8. Verificar startup, hashes montados, Login/Game/Stream/World según la
   frontera, ausencia de loops y aceptación controlada. Para Zone, resolver
   primero el perfil propietario por posición/estado persistido del personaje;
   si el lifecycle fue autorizado, iniciar sólo ese perfil y verificar
   `ZoneLoaded`, conexión World y heartbeats.
   En Docker AA10, `.server_files/AAEmu.Game/Configurations` y los demás bind
   mounts sustituyen el contenido incluido en la imagen. Toda modificación de
   configuración debe sincronizarse también al runtime montado antes de
   reiniciar el servicio, y el gate debe comprobar tres niveles: archivo
   versionado, archivo visible dentro del contenedor y estado realmente
   serializado al cliente (por ejemplo, el byte y nombre de `FeaturesManager`).
   No declarar desplegada una feature basándose únicamente en el hash de la
   imagen o en que el catálogo backend haya cargado.

### Instrumentación dinámica temporal

Usarla sólo cuando SQLite, corpus estático y decompilación no resuelvan el
lifecycle observado. Preferir mensajes breves y correlacionados en el chat del
cliente de prueba y logs estructurados del servidor. Registrar estado antes y
después de cada callback, IDs de timeline/item/template, tipo de tarea, orden de
acciones y resultado; no imprimir secretos ni datos de otros jugadores.

Mantener respaldo con hash de cada ALB/binario modificado. Una vez confirmada la
causa, convertir el hallazgo en prueba/documentación, restaurar los artefactos
del cliente y eliminar flags/mensajes diagnósticos antes del commit.

### Validar con el usuario

Dar una interacción por vez para cambios persistentes. Fijar stop point,
resultado esperado, edge cases y espacio de inventario. Inspeccionar logs y
persistencia antes de autorizar el siguiente paso.

Cuando `Game` y el personaje de prueba estén online, entregar kits y materiales
mediante `scripts/give-test-items.ps1`. Preferir este canal sobre automatizar el
chat o escribir en MySQL: reutiliza `/item add`, persiste y notifica al cliente.
Validar IDs contra AA10, espacio libre y respuestas sin errores. Mantener el
Web API `1280` sin publicar mientras no tenga autenticación.

Para DB/Login/Game y cliente, usar el método autorizado en la tarea actual y no
detener procesos ni contenedores ajenos. Sin autorización explícita, el usuario
administra las Zones mediante AAEmu Control Center y Codex se limita a
inspección read-only.

## Propiedad del lifecycle de Zones

- Por defecto, no iniciar, detener, relanzar ni reconciliar Zones desde Codex;
  limitarse a inspección read-only de logs, procesos, conexiones y estado del
  panel.
- Una prueba autoriza el lifecycle sólo cuando el usuario lo indique
  explícitamente. La autorización vale para la tarea actual y permite iniciar o
  relanzar únicamente la Zone necesaria para el personaje de prueba; no se
  extiende a otros perfiles ni a futuras tareas.
- Antes de operar, resolver la posición persistida del personaje y demostrar
  qué perfil/partición la contiene. Validar rutas, argumentos, ejecutable r575 y
  hash del spawner contra la configuración canónica del Control Center.
- Si una única partición basta, no ejecutar lanzadores agregados como
  `launch_zone_aa10.ps1` ni levantar las demás particiones. Invocar el worker
  exacto `launch_zone_aa10_worker.cmd <perfil> <clave>` con argumentos explícitos
  y ventana oculta para pruebas desatendidas.
- No detener ni reemplazar una Zone saludable ya existente. Un relanzamiento
  autorizado exige primero probar que ese mismo perfil está caído o no
  saludable; sólo se pueden cerrar procesos que Codex haya iniciado en la tarea,
  salvo autorización destructiva separada del usuario.
- Tras el inicio o relanzamiento, comprobar la línea de comando del proceso,
  conexión establecida al puerto World `1240`, handshake `ZWJoin` /
  `WZJoinResponse`, `ZoneLoaded` del perfil exacto y heartbeats sin bucle. Si el
  perfil resuelto no carga al personaje, diagnosticar antes de operar cualquier
  otra Zone.
- Reiniciar o desplegar Game puede desconectar las Zones, pero no constituye por
  sí solo autorización para operarlas.

## Gates mínimos

```powershell
dotnet restore
dotnet build --configuration Release --no-restore
dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore
```

Exigir además pruebas específicas, SQLite `quick_check`/`integrity_check` si se
genera runtime, cero dependencias habilitadas huérfanas y checkpoint actualizado.
No promover una hipótesis sólo porque la suite está verde.
