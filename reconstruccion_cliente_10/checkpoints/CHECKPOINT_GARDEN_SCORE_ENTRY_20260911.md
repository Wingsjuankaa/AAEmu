# Garden: entrada, eventos de muerte y puntos

Estado: implementado y desplegado; 2754 pruebas pasan. Buff/HUD/puntos pendientes de aceptación retail. El usuario confirmó expresamente que el daño ya funciona: preservar el arreglo de proyectiles anterior.

Target `E:/AAEmu/rama_10/server/AAEmu`, branch `rama_10`, HEAD `fd53b458573572cc354c8564293f274801d9aa3e`. Padre exacto `upstream/client_version/zone-10.0.2_r575`, `7babcb3a706c64295b5aaaeec8abe57e4d09b4da`. Cambios clasificados `server-required` y requisitos `client-native`; no cambios de game_pak, migración de DB ni lifecycle de Zones.

## Causas y evidencia

- El log del intento más reciente contiene `12:59:37 Not relaying buff 26390 to zone: owner ObjId 0 is not a zone unit id`, antes de `SCCharacterList`. Cargar el Transform del personaje en el lobby ejecutaba Unit.OnZoneChange y arrancaba el buff ambiental con ID0 y Quests sin cargar. El buff periódico evalúa requisitos de misión que precisan ese estado. La cola de notificaciones ZW del arreglo previo no resuelve este origen: no hubo ningún `ZWCreateBuff player=`. La reconciliación de zona sólo debe aplicar efectos al personaje seleccionado, con ID y misiones inicializados. CSSelectCharacter ya hace esa reconciliación explícita después de Load.
- La baja de Primark NPC19979 está registrada en `artifacts/garden-review-20260911/trace.log`, líneas3232–3275: buff26574, trigger13590 (Death), SkillUse44464/plot4909 se ejecutaban con source=target=NPC863. La tabla indica source_agent=1 (killer), target_agent=0 (propietario muerto). BuffTrigger.Execute ignoraba OnDeathArgs. Death se suscribía además al caster original, no al propietario.
- El buff25655 tiene KillAny/trigger13463, source_agent=0, target_agent=2 y requisito de misión10056 en Progress. El handler no suscribía este evento. La notificación antigua previa a DoDie no contiene víctima: no es un evento de baja utilizable. DoDie emite después Killer/Victim; sólo ese evento debe activar el efecto.
- Tick4479 de25655 concede 5 puntos/10000ms y exige ZoneScoreLevel(3,1,5), misión activa y salud positiva. El evaluador sólo soportaba igualdad (modo2), rechazando este tick. La decompilación r575 cierra modo0 >=, modo1 <= y modo2 ==, con límites inclusivos. No se extrapola otro enum.
- Plot4909 distingue paz de otros estados mediante UnitReq129/ConflictZoneState. Este requisito también estaba sin implementar y tomaba siempre la rama de fallo, alterando el valor concedido. Se implementan los predicados exactos del nativo.

## Contrato nativo

Binario x64 `zones/retail-zone-server-r575/Bin64/x2game-dev_dedicate.dll`, SHA256 `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`, base0x39000000.

- RVA0x770EA0: dispatch UnitReq; 0x82→0x770CB0, 0x81→0x76FD60.
- RVA0x770CB0: lee kind/value2/value3; calcula rango con umbrales acumulativos; resultado no cero significa fallo. Comparaciones >= / <= / ==.
- RVA0x76FD60: requiere zona de conflicto; modo0 devuelve state in {6,7}, modo1 state!=7, modo2 state!=6; compara el booleano con value2. Estado6=War,7=Peace.
- Artefactos `E:/AAEmu/rama_10/artifacts/garden-unitreq-{dispatch,score-level,conflict}.log`, producidos por DecompileAddressAndXrefs.java en proyecto read-only AA10ZoneServer.
- Clausura completa/runtime idéntica: `artifacts/garden-score-contract.json`, SHA256 `4f8bd10e3db79451b9663231130c3b986c7aa6c3d8dcc30cfe1e5ae8f054e64b`. Incluye zona133, score3, niveles, buffs, requisitos, NPC19979 y plots4848/4909.

## Implementación y validación

Unit.ReconcileZoneBuffs omite personajes de lobby sin ObjId/Quests. Al seleccionar, la ruta existente aplica el buff ambiental con el caster correcto. Cambiar378↔382 conserva el buff de la misma región; salir elimina los buffs dependientes.

BuffTrigger resuelve los agentes de OnDeathArgs y OnKillArgs; Death/KillAny se suscriben al propietario y se desuscriben simétricamente. Se cargan y evalúan requisitos AND/OR de esas dos clases de evento, usando al propietario y la víctima. No cambia el cálculo de daño, GCD ni el ciclo de los proyectiles.

BuffTickRequirementsTests recorre el callback real DispelTask: entrada diferida, misión activa, preservación dentro de Garden y retirada al salir; +5 puntos en rango0 y5, sin ganancia pasiva en6, muerto o sin misión. BuffDeathEventTests prueba source=killer, target=NPC, original caster sin efectos, desuscripción y KillAny sin duplicar el aviso incompleto. GardenScoreTests cubre las fronteras de paz/guerra y zona ausente. Suite Release2754/2754, cero fallos; `git diff --check` limpio para la corrección.

## Despliegue y rollback

Respaldo `E:/AAEmu/rama_10/backups/garden-score-20260911-132502`: DB transaccional, log y snapshot World anteriores. Imagen rollback `aaemu-world:rollback-garden-score-20260911-132502` apunta a3a59fbe3. La DB conservaba score0 para Dannia antes del cambio; no se inventan puntos por bajas históricas.

Imagen desplegada `sha256:d20e139bcdd9d5495957c5fa61967e575efb002e3751eb316fa4acec5c0a0411`, inicio2026-09-11T13:26:27Z. GameDLL `82ae5b8ad5211f2030db8b57795063c360da8b11d13c7cb181de48866ae5c17c`; WorldDLL `b7f6c3a72d25b2d021aecc16cb5cfd81a33a394235595c83dee090294b0280fb`. Manifest adjunto registra comprobación de servicios.

Aceptación pendiente: iniciar desde Control Center el perfil que contiene a Dannia y entrar. Con misión10056 en Progress, verificar rango0 estable y +5 puntos a los10s; matar un monstruo y correlacionar trigger13590 con caster=Dannia y logs Garden score. Relog debe conservar puntuación. El valor de cada baja depende de los datos nativos, estado de conflicto, buffs y reparto de objetivos; no se fija un valor único artificial. No declarar aceptada la prueba retail a partir de la suite ni ampliar esta corrección a todos los modos PvP de ChangeZoneScore.

Runtime verificado: health healthy; World API responde; puertos1239/1240/1250/1280 en LISTEN. Snapshot 2026-09-11T13:29:44.7127062Z: 0 jugadores, 0 Zones registradas. No hubo prueba retail automatizada. AA8 conserva Death sobre caster y aporta KillBuffTrigger, pero no se copiaron sus agentes ni protocolo: el contrato implementado está cerrado por r575.

Seguimiento: el usuario confirma HUD nivel1 y el log registra ganancias pasivas y bajas. El icono permanecio en0; continuacion en CHECKPOINT_GARDEN_RANK_GROUP_RATE_20260911.md.
