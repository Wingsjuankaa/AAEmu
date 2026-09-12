# Garden: impactos en vuelo y entrada de buffs — 2026-09-11

Estado: corrección server-required, pruebas 2740/2740, aceptación retail pendiente. El usuario confirmó que el arreglo anterior de BuffTickEffect NO resolvió el daño y que el buff de rango ya no aparecía.

## Evidencia
Target E:/AAEmu/rama_10/server/AAEmu; branch rama_10; padre upstream/client_version/zone-10.0.2_r575. Se preservan los cambios pendientes de otras tareas.

Video 20260911-1239-49.2649148.mp4, creación UTC12:39:53, duración9.13s. Dannia ataca Primark (NPC19979,Obj863) a20.1m. En el log, skill14835/timeline138 dispara eventos51690/51697/51691/51692 y termina al entrar14836/timeline139, sin ejecutar el impacto51693. A partir de12:39:57, cuando disminuye la distancia, timeline153 sí llega a51693 en136ms y aplica3910 de daño (absorción2152). Esto distingue el fallo de impacto de los rechazos CooldownTime por pulsaciones repetidas: existen ataques aceptados y lanzados que nunca alcanzan su efecto de daño.

Clausura full/compact idéntica: skills14835/14836/14837 usan plot5733. Edge71617, 61611→51693, speed50, casting=false, channeling=false. Los60056/60057/etc. tampoco canalizan. PlotNode.Execute marcaba IsChanneling=true en todo nodo sin una arista entrante de canalización. Plot.BindState cancela el anterior si IsCasting||IsChanneling. A20m la flecha requiere400ms de vuelo; otro disparo aceptado antes del impacto cancela la cola. Es una confusión de estado, no una razón para aumentar el GCD o eliminar la duración del proyectil. El padre exacto conserva la misma asignación defectuosa.

## Cambios
- PlotNode inicia IsChanneling sólo cuando uno de sus hijos tiene una arista Channeling. Mantiene la canalización existente durante eventos hermanos y la termina al recorrer su arista final. No toca velocidad/GCD/daño ni modifica game_pak.
- CombatRelay conservaba buffs sólo si IsStreamedUnitForAnyClient era true; el cliente propio también se excluye hasta NotifyInGameCompleted. Las creaciones que llegan al entrar se perdían sin reenvío posterior. La misión10056 de Dannia sigue en Progress(4), pero no hay registro SCBuffCreated26390 para Dannia en esta entrada; sí existe paraNPCs. El nuevo log ZWCreateBuff player/template/loadComplete permite confirmar ese orden al repetir la entrada.
- PendingZoneBuffs retiene las notificaciones nativas Create/Remove del personaje, manteniendo orden, hasta NotifyInGameCompleted. Se limpia al seleccionar otra sesión. Los NPCs conservan su filtro de interés. No se añade un buff artificial por ID ni se da por recibida una notificación ausente.

## Pruebas y límites
2740 pruebas pasan. ProjectilePlotLifecycleTests ejecuta PlotNode y Plot.BindState: una flecha ya lanzada no adquiere canalización ni se cancela con el disparo siguiente; una canalización real sigue activa en eventos hermanos, admite interrupción y se apaga en su final. La cola de entrada conserva create/remove, evita reenvío doble, aplica posteriores avisos y descarta la sesión anterior. Las pruebas de BuffTickEffect, Hiram, pesca y resto de combate pasan.

Se conserva el arreglo anterior de requisitos BuffTickEffect: sin él Garden quita/reaplica el buff cada segundo incluso en NPCs. Este cambio no completa los operadores restantes de ZoneScoreLevel ni KillAny. La puntuación total y la IA no se declaran aceptadas por una suite verde. El origen temporal de la ausencia de26390 debe confirmarse con los avisos nuevos; si la Zone no lo emite, la cola no fabrica estado.

Respaldo e imagen previa: E:/AAEmu/rama_10/backups/garden-projectiles-20260911, tag aaemu-world:rollback-garden-projectiles-20260911. No hubo migraciónDB ni cambios de cliente. Game se despliega según autorización permanente; no se opera el lifecycle deZones.

Aceptación: entrar desde ControlCenter con la Zone de Dannia iniciada; comprobar registro/estabilidad de26390→25655→26196 y disparar varias flechas desde20m. Correlacionar cada timeline aceptado con impacto51693 y descartar que el cast siguiente lo retire. Revisar combate después sin prometer arreglado el contador de Garden.

Desplegado y verificado: imagen3a59fbe306fb78bea74989f319670158b9d4a1b3c6f302a149cae5c15d1ae7fc, Game95e173ce2f3e385e5cf6ceafc4d78794b536dcec7350c2be8eaede49a43a27a6, Worlde0bf67746fb08c9a229b58c1b3fe5cd2095db162248b405983783e36f2cdaf17. Arranque12:54:18 UTC, WorldAPI responde, puertos1239/1240/1250/1280 escuchando. Cero jugadores/Zone activas al verificar; aceptación retail pendiente.

Actualizacion 2026-09-11: el usuario confirma que el daño funciona. Buff/puntaje seguían fallando; continuación y corrección en CHECKPOINT_GARDEN_SCORE_ENTRY_20260911.md. Esta aceptación no incluye la cola de entrada como solución del buff.
