# Comandos del emulador AAEmu

Guía de los comandos de chat registrados por la rama actual (`develop`) de
AAEmu. Se escriben dentro del juego y siempre empiezan con `/`.

> La fuente de verdad es `AAEmu.Game/Scripts/Commands/` y sus subcomandos en
> `AAEmu.Game/Scripts/SubCommands/`. La disponibilidad depende del nivel de
> acceso de la cuenta configurado en `AAEmu.Game/Configurations/AccessLevels.json`.

## Uso y permisos

- `/help` o `/?`: muestra los comandos disponibles para tu cuenta.
- `/help <comando>`: muestra la sintaxis que expone el servidor para un comando.
- Los parámetros entre `< >` son obligatorios y `[ ]` opcionales.
- Los comandos de creación, borrado, teletransporte y depuración pueden afectar
  al mundo actual. Úsalos en un servidor de pruebas.

En la configuración incluida, `help`, `fly`, `online`, `soloparty` y
`teleport` son de nivel 0; muchos comandos administrativos exigen nivel 50 o
100. Los nombres alternativos se muestran entre paréntesis.

## Jugador, progreso y economía

| Comando | Alias | Función |
| --- | --- | --- |
| `/xp <cantidad>` | `addxp`, `givexp` | Agrega experiencia al personaje. |
| `/level <nivel>` | `setlevel`, `changelevel` | Ajusta el nivel de personaje o mate según el objetivo/parámetros. |
| `/gold add <self\|target\|nombre> <oro> [plata] [cobre]` | `set`, `remove` | Gestiona dinero. Ejemplo: `/gold add self 10 50 25` añade 10 oro, 50 plata y 25 cobre. `remove` lo descuenta; `set` actualmente se comporta igual que `add`. |
| `/labor <cantidad>` | `addlabor` | Agrega puntos de labor. |
| `/vocation <cantidad>` | `vocationpoints`, `add_vp` | Agrega insignias/puntos vocacionales. |
| `/title <id>` | `addtitle`, `appellation` | Otorga una appellation/título. |
| `/buff <id> [tiempo]` | `addbuff`, `buffs` | Aplica un buff. |
| `/kit <id>` | `addkit` | Entrega un kit predefinido. |
| `/inventory` | `showinv`, `show_inventory` | Muestra o inspecciona el inventario. |
| `/item add <templateId> [cantidad]` | — | Crea un ítem desde su template. |
| `/item expire [minutos]` | — | Hace expirar el ítem objetivo; por defecto, pronto. |
| `/item unwrap [minutos]` | — | Ajusta el instante de apertura del ítem objetivo. |
| `/addportal` | `register_portal` | Registra un portal en la posición actual. |
| `/settradepackmaildelay <minutos>` | — | Cambia el retraso del correo de recompensas de trade pack. |
| `/ingamecashshop` | `ics` | Abre o prueba la interfaz de la tienda integrada. |

## Personaje, combate y movimiento

| Comando | Alias | Función |
| --- | --- | --- |
| `/heal [objetivo]` | — | Cura al personaje u objetivo. |
| `/kill [objetivo]` | — | Mata al objetivo. |
| `/revive` | — | Revive al personaje. |
| `/godmode` | — | Alterna invulnerabilidad. |
| `/damage <cantidad|porcentaje>` | — | Inflige daño al objetivo; acepta valores como `9999` o `20%`. |
| `/clearcombat` | `cc` | Limpia el estado de combate. |
| `/fly` | — | Alterna vuelo de depuración. |
| `/run [velocidad]` | — | Ajusta el movimiento de prueba. |
| `/move <x> <y> <z>` | — | Mueve al personaje. |
| `/moveto <jugador|ubicación>` | — | Mueve al personaje a un destino/jugador. |
| `/moveall <ubicación>` | — | Mueve a todos los jugadores. |
| `/teleport <ubicación>` | — | Teletransporta a ubicaciones predefinidas. |
| `/nudge <x> <y> <z>` | — | Aplica un pequeño desplazamiento. |
| `/rotate` | `lookatme` | Hace que el objetivo mire al personaje. |
| `/position` | `pos` | Muestra posición, template y objeto del objetivo/personaje. |
| `/pingpos` | `pingposition` | Envía una marca de posición. |
| `/distance` | `dist` | Muestra distancia al objetivo. |
| `/height` | — | Consulta/depura la altura del terreno. |
| `/getattribute <atributo>` | `getattr`, `attr` | Consulta un atributo del personaje/unidad. |
| `/setfaction <id>` | — | Cambia la facción del objetivo. |
| `/invisible` | — | Alterna invisibilidad administrativa. |
| `/ignoreskillcds` | `ignorecooldowns` | Alterna la omisión de cooldowns. |
| `/resetcd` | `resetskillcooldowns` | Reinicia los cooldowns de habilidades. |
| `/useskill <skillId>` | `testskill` | Ejecuta una habilidad de prueba. |
| `/failskill` | `skillfail` | Fuerza/prueba un fallo de habilidad. |
| `/soloparty` | — | Crea/ajusta grupo para pruebas en solitario. |
| `/online` | `list_online` | Lista personajes conectados. |
| `/kick <personaje>` | `kick_player` | Expulsa a un jugador. |
| `/disconnectme` | — | Desconecta al propio personaje. |

## Mundo, tasas y configuración en tiempo real

| Comando | Función |
| --- | --- |
| `/world set exprate <1..1000>` | Modifica el multiplicador global de experiencia sin reiniciar. Ej.: `/world set exprate 5`. |
| `/world set growthrate <valor>` | Ajusta la tasa de crecimiento. |
| `/world set lootrate <valor>` | Ajusta la tasa de botín. |
| `/world set vocationrate <valor>` | Ajusta la tasa vocacional. |
| `/world set honorrate <valor>` | Ajusta la tasa de honor. |
| `/world set autosaveinterval <valor>` | Cambia el intervalo de guardado automático. |
| `/world set logoutmessage <texto>` | Cambia el mensaje de desconexión. |
| `/world set motd <texto>` | Cambia el mensaje del día. |
| `/world set geodatamode <modo>` | Ajusta el modo de geodata. |
| `/time set <hora>` | Establece la hora del mundo. |
| `/feature check <nombre>` | Consulta el estado de una feature. |
| `/feature set <nombre> <true|false>` | Activa/desactiva una feature en tiempo de ejecución. |
| `/reloadconfig` | `reload_configs` | Recarga configuraciones JSON. |
| `/reloadauction` | `reloadah` | Recarga datos de subasta. |
| `/snow` | — | Alterna nieve/efecto relacionado. |
| `/zonestate ...` | — | Prueba o cambia el estado de una zona. |
| `/towerdef ...` | — | Herramientas de Tower Defense. |
| `/sphere ...` | — | Herramientas de Sphere Quest. |

Los cambios de tasa son de memoria y normalmente vuelven a los valores de
`Configurations/World.json` tras reiniciar Game.

## NPC, doodads y objetos de mundo

| Comando | Función |
| --- | --- |
| `/npc spawn <templateId> [yaw]` | Crea un NPC frente al personaje. |
| `/npc info [objId]` | Muestra datos del NPC objetivo o indicado. |
| `/npc position [x y z yaw]` | Reubica/rota un NPC. |
| `/npc remove [objId]` | Elimina un NPC. |
| `/npc save ...` | Guarda spawns de NPC para el mundo actual. |
| `/doodad spawn <templateId> [yaw]` | Crea un doodad frente al personaje. |
| `/doodad info/chain` | Muestra información y propiedades enlazadas de un doodad. |
| `/doodad position [x y z yaw]` | Reubica/rota un doodad. |
| `/doodad remove [objId]` | Elimina un doodad; `0` usa el más cercano. |
| `/doodad removes <radio>` | Elimina doodads cercanos dentro del radio. |
| `/doodad phase list` | Lista fases de un doodad. |
| `/doodad phase change <fase>` | Cambia la fase de un doodad. |
| `/doodad save ...` | Guarda el estado de un doodad en los archivos del mundo. |
| `/doodad_location` | `dloc` | Consulta/localiza un doodad. |
| `/setpos ...` | `npcpos`, `doodadpos` | Cambia la posición de un objeto. |
| `/setrot ...` | `npcrot`, `doodadrot` | Cambia la rotación de un objeto. |
| `/spawn <tipo> <templateId> ...` | Spawn genérico de objetos del mundo. |
| `/spawngrid <tipo> <templateId> <ancho> <alto> <separación>` | Crea una cuadrícula de spawns. |
| `/despawn <objId|templateId> [radio]` | Elimina NPC/doodad por objeto o template. |
| `/despawnall` | Elimina todos los objetos del mundo actual. |
| `/findobject <tipo> ...` | `findobj` | Busca objetos cercanos por tipo. |
| `/around <tipo> [radio]` | `near` | Lista doodads, NPC, personajes, spawners u objetos cercanos. |
| `/build <templateId>` | `build_house` | Construye una casa/estructura de prueba. |
| `/housebindingmove ...` | — | Mueve bindings de vivienda. |
| `/tickdoodad [objId]` | Fuerza un tick de un doodad. |
| `/coffer ...` | `chest` | Acciones de cofres. |
| `/gimmick spawn <templateId> [yaw]` | Crea un gimmick frente al personaje. |

## Barcos, vehículos y físicas

| Comando | Función |
| --- | --- |
| `/slave spawn <templateId> [yaw]` | Crea un vehículo/slave frente al personaje. En agua: `52` Clipper, `14` Harpoon Clipper, `76` Adventure Clipper, `75` Merchant Schooner. |
| `/slave info [objId]` | Muestra información del vehículo objetivo/indicado. |
| `/slave position [objId] [x y z roll pitch yaw]` | Ajusta posición y orientación del vehículo. |
| `/slave remove [objId]` | Elimina un vehículo. |
| `/slave save ...` | Guarda posiciones de slaves del mundo. |
| `/shipbarrier status` | Muestra el estado de las barreras de barco. |
| `/shipbarrier reset world ingest` | Reinicia la ingesta de barreras del mundo. |
| `/shipbarrier reset cell ingest` | Reinicia la ingesta por celda. |
| `/waterdebug reload` | Reconstruye las áreas de agua cargadas. |
| `/waterdebug info [x y z]` | Muestra datos de agua en la posición. |
| `/waterdebug reloadinfo [x y z]` | Recarga e informa datos de agua. |
| `/waterdebug setprobe <x y z>` | Activa log de sondeo de agua. |
| `/waterdebug probeoff` | Desactiva el sondeo de agua. |
| `/testslave` | Crea el slave de prueba usado por los desarrolladores. |

## Crimen, misiones y sistemas sociales

| Comando | Función |
| --- | --- |
| `/crime create <templateId>` | Crea evidencia de crimen en la posición actual. |
| `/crime points ...` | Ajusta puntos de crimen, infamia o jurado del objetivo. |
| `/crime jury_invite` | `ji` | Envía invitación de jurado. |
| `/crime ask_guilty` | `ag` | Pregunta declaración de culpabilidad. |
| `/crime court` | Inicia/solicita flujo de corte. |
| `/crime trial_state <estado>` | `ts` | Cambia estado de juicio. |
| `/crime fake` | Ejecuta un juicio falso de prueba. |
| `/quest ...` | Herramientas de misiones. |
| `/testmail` | Herramientas de correo de prueba. |
| `/testchatchannel` | `testchat` | Prueba canales de chat. |

## Depuración, red y desarrollo

| Comando | Función |
| --- | --- |
| `/announce ...` | Envía un anuncio formateado/global. |
| `/echo <texto>` | Repite texto para probar chat. |
| `/nwrite <texto>` | `nw` | Envía escritura/notificación de prueba. |
| `/packet ...` | Envía un paquete de prueba. |
| `/pathfind ...` | `pf` | Grupo de comandos A*: `start`, `goal`, `find`, `view`. |
| `/fishfinder set ...` | Configura Fish Finder. |
| `/scripts ...` | Herramientas de scripts; útil para recarga y diagnóstico. |
| `/testai` | `ai` | Herramientas de IA. |
| `/testcombat` | Pruebas de combate. |
| `/testnavmesh` | Pruebas de navegación/NavMesh. |
| `/testtracker` | `track`, `tt` | Pruebas de tracker. |
| `/testtransfer` | Prueba transfers; deshabilitado por configuración por defecto. |
| `/testfsets` | Prueba feature sets. |
| `/testheightvisualizer` | Visualizador de altura para depuración. |
| `/testhouse` | `house` | Crea/prueba vivienda. |

## Notas de mantenimiento

- Algunos nombres del código histórico se solapan (por ejemplo, `gold` tiene
  implementación raíz y subcomandos); `/help gold` muestra la variante que se
  cargó en tu ejecución.
- Para nuevos comandos, sigue el patrón de `AAEmu.Game/Scripts/Commands/` y
  registra el nombre en `AccessLevels.json` si debe tener un permiso concreto.
- Después de modificar scripts, recompila Game y reinícialo, o utiliza las
  herramientas de `/scripts` si corresponde a la carga actual.
