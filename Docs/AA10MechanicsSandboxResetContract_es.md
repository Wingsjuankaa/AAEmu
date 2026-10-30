# Contrato del escenario de desarrollo AA10 r575

Target: `rama_10`, padre exacto
`upstream/client_version/zone-10.0.2_r575` (corte `78533663d`).
El árbol del padre no contiene sandbox ni MechanicsLab. Se reutilizan sus
primitivas de NPC, buffs, skills y teletransporte. Estos controles son herramientas
de desarrollo autorizadas, no una reconstrucción de una mecánica retail.

Ampliación del laboratorio (2026-10-29): los resets nuevos reconstruyen los
pasivos desde el libro actual y excluyen sus hijos BuffEffect del snapshot.
Así se respeta el cambio de especialización realizado en el NPC retail.
Se rechazan productores no cerrados antes de retirar estado. Detalles,
servicios y aceptación en `Docs/AA10SandboxTrainingHub_es.md`; el baseline V1
se conserva sólo para retirar una sesión anterior a esta actualización.

## Activación y API

`Configurations/MechanicsSandbox.json` está desactivado por defecto. El entorno
aislado debe habilitarlo y fijar **nombre, ID de personaje, ID de cuenta, mundo,
instancia y zoneKey**. El comando rechaza cualquier identidad diferente, una
entrada al mundo incompleta, la Zone nativa ausente o posiciones fuera de ella.

Los slots de dummies proceden exclusivamente del JSON. Se verificó con el binder
real que preinicializar una lista con cuatro entradas duplicaba las cuatro del
JSON (ocho); la lista empieza vacía y la recarga reemplaza el perfil sandbox
antes de enlazarlo, conservando exactamente cuatro slots en cada recarga.

Comando GM: `/sandbox begin|status|reset|clear`, acceso efectivo mínimo 100.
El comando manual presenta una frase breve en español. La automatización usa
`POST /api/mechanics-sandbox/{begin|status|reset|clear}` con cuerpo
`{"character":"Sandbox"}` (nombre exacto configurado). El API permanece en el
puerto interno1280 y valida cuenta, ID, nombre y acceso GM100 antes de ejecutar.
Devuelve el snapshot directamente sin usar `CommandManager` ni enviar mensajes
al chat del cliente; no sondear mediante `/api/commands/sandbox`.

La respuesta del API contiene un objeto JSON camelCase:

```json
{"success":true,"state":"ready","message":"…","characterId":1001,"character":"Sandbox","zoneKey":379,"attempt":1,"dummies":[123,124],"hp":100,"mp":100}
```

- `begin`: crea la sesión y la primera tentativa; repetirlo estando `ready` no
  añade más NPCs ni cambia el número de tentativa.
- `reset`: solicita la siguiente tentativa; devuelve `resetting` antes de que
  termine. Consultar `status` hasta `ready` o `faulted`.
- `clear`: retira únicamente los NPCs y la sesión propios. Devuelve `clearing`;
  esperar `status=idle` para confirmar limpieza.
- Un fallo de preparación deja `faulted`, `success=false`, sin declarar lista
  una restauración parcial. La barrera de ejecución permanece cerrada hasta
  reintento o cierre explícito.

## Ajustar la arena con la sesión abierta

`POST /api/mechanics-sandbox/reconfigure` aplica un nuevo origen y una lista
de entre 1 y 16 posiciones relativas, sin recargar la configuración global ni
reiniciar Game/World, Zone o cliente:

```json
{"character":"Sandbox","origin":{"X":500.295,"Y":38373.5,"Z":129.948,"Rotation":0},"dummies":[{"Forward":7,"Right":0,"Up":0},{"Forward":12,"Right":2,"Up":0}]}
```

No admite cambios de personaje, cuenta, mundo, instancia, Zone, template o
balance. Rechaza campos ajenos a las posiciones, valores no finitos y offsets
fuera de los límites de desarrollo (60 m en planta y 10 m en altura). Todos los
puntos deben pertenecer a la misma Zone nativa cargada. Requiere una sesión
`ready`; monturas, invocaciones pendientes, duelo y buffs de autoridad nativa
quedan fuera de esta operación V1.

La validación termina antes de retirar la tentativa: un rechazo deja intactos
el perfil activo, la tentativa y los dummies. Un ajuste aceptado usa la misma
barrera de reset y devuelve `resetting`; esperar `status=ready`. El snapshot
incluye `origin` y `layout` efectivos, además de los IDs propios. Un fallo
posterior del consumidor nativo conserva la configuración previa y queda
`faulted` con limpieza parcial, nunca se presenta como un commit distribuido
aceptado. La API cambia la sesión en memoria; el editor/launcher debe guardar
su JSON de perfil si quiere conservar el ajuste para el siguiente arranque.

## Qué restablece

Se captura el estado inicial de buffs con sus plantillas, caster, duración
efectiva, AbLevel, stacks, cargas y bandera pasiva. El restore interno no vuelve
a aplicar modificadores de duración a un valor ya efectivo y conserva el nivel
que escala sus modificadores. V1 rechaza un baseline o una restauración con
buffs administrados por Zone: no promueve su procedencia a autoridad World.
Cada reset cancela las skills rastreadas,
incluidos plots superpuestos, solicita el final por el consumidor existente y
espera hasta 15 s su cierre. Se detienen autoataque, craft y controlador activo.

El commit de restauración se serializa frente a las ejecuciones del sandbox:

1. Retira las referencias de NPC propias mediante `WorldIntegration.RemoveNpcNow`.
   No busca NPCs ajenos por plantilla o radio. El relay conserva su política
   normal de retiro y liberación diferida de IDs.
2. Restablece los buffs iniciales, incluidos pasivos y sus temporizadores,
   mediante su salida y el consumidor real de `Buffs`; la variante interna de
   snapshot conserva la duración efectiva sin calcularla dos veces.
3. Revive si corresponde, usa `GmTeleportHelper` hacia el origen, limpia target,
   combate y aggro mediante sus consumidores y relays normales.
4. Restaura HP/MP, cooldowns/cargas y recursos de combate. Los cooldowns durante
   la prueba siguen siendo los normales: no activa `IgnoreSkillCooldowns`.
5. Crea los dummies con `NpcManager`, el modelo del catálogo, `IsZoneMirror` y
   publicación a la Zone propietaria. Si falla una publicación se retira el lote
   parcial y la sesión no pasa a `ready`.

El reset no revierte inventario, consumo de objetos, experiencia, misiones,
economía ni persistencia completa. El entorno debe usar una copia de DB y un
personaje exclusivo. Las invocaciones/estructuras producidas por otras mecánicas
no se incluyen automáticamente en el lote de dummies propio.

## Barrera de ejecución por tentativa

Sólo los objetos explícitamente registrados por la sesión tienen barrera.
Para el resto de actores, los hooks toman el camino de ejecución normal.
No se sustituyen relojes, scheduler, fórmulas, requisitos o resultados de skills.

Cada callback pendiente conserva una identidad inmutable de sesión/tentativa.
Al iniciar reset se retira la tentativa anterior. Esto protege también un objeto
`Skill` reutilizado por autoataques: sus campos actuales `Cancelled` y `TlId`
no bastan para identificar el callback antiguo.

Se protegen Use/ApplyEffects, startup y ejecución de plots, y los tasks de cast,
fin/tick de canal, autoataque, aplicación de proyectil, SkillUse diferido, triggers
de buffs, pulsos periódicos/aura, continuación de craft, despawn propio y repetición
de efectos especiales. Se auditó toda la carpeta `Models/Tasks/Skills`: su clase
abstracta `SkillTask` no ejecuta callbacks y cada implementación concreta está
cubierta. Las únicas llamadas periódicas a `Buff.ScheduleEffect` y `Buff.PulseAura`
vienen de `DispelTask` y `AuraTask`; las demás llamadas `ScheduleEffect` son
transiciones síncronas de aplicación/retirada del mismo buff. Los efectos ya ejecutándose terminan
su sección serializada antes de retirar la tentativa. Los callbacks antiguos no
se vuelven válidos al cerrar/recrear la sesión.

Los triggers síncronos también conservan la tentativa de su buff. Durante la
restauración sólo el hilo del commit puede ejecutar callbacks de la nueva
tentativa; los de instancias retiradas siguen rechazados. Al cerrar se reconstruye
el baseline tras desligar al actor, para que sus nuevos callbacks vuelvan al
flujo ordinario sin revivir los del escenario. El factory de dummies registra
su propiedad antes de `InitializeSpawnBuffs`, usando el mismo `NpcManager`.

Las pruebas permanentes cubren el proyectil antiguo con `Skill` reutilizado,
cast/canal/descendiente antiguos, plot diferido, timeout/repetición, exclusión de
una ejecución concurrente, reapertura de sesión, actores ajenos y rechazo de
identidad/configuración inválidas. La aceptación nativa visual es una puerta
independiente de estas pruebas.
