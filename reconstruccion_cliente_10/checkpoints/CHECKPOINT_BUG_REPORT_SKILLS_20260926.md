# Reportes de habilidades AA10 — 2026-09-26

## Alcance y autoridad

- Rama de implementación: `E:\AAEmu\rama_10\server\AAEmu`, `rama_10`; padre `upstream/client_version/zone-10.0.2_r575` (`b73c33…`).
- Cliente r575: SQLite completa `E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3`, compact retail y `x2game.dll` release SHA-256 `2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76` (base `0x39000000`).
- Reportes y su historial: `python Scripts/BugReports.py --category skill`; el texto del jugador es hipótesis, no especificación.
- El usuario autorizó en esta tarea iniciar únicamente Zone 179 para Testxxx y Zone 129 para Noira. Se verificaron las posiciones persistidas, nombres de perfil en `zones` y en `profiles.json` del Control Center, MD5 de ambos `npc_spawners.g`, SHA-256 del ZoneHost instalado y DLL retail r575. Tras el despliegue final se esperó `Server started!` antes de iniciar los workers exactos; ambas Zones tienen `ZoneLoaded`, socket TCP establecido al 1240 y heartbeats. El usuario no puede abrir el juego en este momento; las pruebas de interacción quedan pendientes.

## Diagnóstico y estado

| ID | Habilidad | Evidencia | Estado |
| --- | --- | --- | --- |
| 5 | Disparo de precisión 23592 | QA posterior documentó daño 5570/5548 y 5536 al muñeco en `Docs/AA10LiveQaUpstream20260918_es.md`. | `needs_retest`; confirmar escenario del reportante. |
| 7 | Lente protectora 10153 | SQLite: `ExtendChargeEffect` 1 concede buff de escudo 95. La implementación y pruebas `ExtendChargeEffectTests` son anteriores al reporte (18:18 frente a 22:27 UTC el 16-09); por eso las pruebas aisladas no desmienten el fallo. | `investigating`; capturar casteo, buff y absorción en Zone 129. |
| 8 | Arco de rayos 10670 | SQLite: casteo 3200 ms, cooldown 12000 ms, plot 279. La QA GM anterior no estableció un canal válido. | `investigating`; capturar cancelación por movimiento y segundo intento en Zone 129. |
| 9 | Proyectiles de maná 14810 | Ficha de 14810: `max_range=20`. Mirada de serpiente 39012 aplica buff 22958; `buff_swap_skills` sustituye 39007/39163/39166 por 39013 Onda abisal, de 20 m de radio/alcance. | `investigating`; identificar ID solicitado y objetivo con buff activo en Zone 129. |
| 11 | Bola de fuego 10752 | Log 02:56 UTC: el cliente solicitó 24894 y Game lo rechazó como no aprendido. SQLite: Combo 10752→24894→24895. Game autorizaba solo cadenas sin casteo; 10752 castea 1000 ms. | Corregido en Game y desplegado; `needs_retest` para los tres golpes en Zone 179. |
| 15 | Escapar | El reporte ancla 17610, habilidad de misión con cooldown 30 s. El Escape común es 20297: descripción r575 indica 30 min tras éxito, `cooldown_time=0`, SpecialEffect 74 y cooldown tag 5701. El éxito 49423 comparte tag 5701, tiene cooldown 1800000 ms y es la única habilidad con `MoveToRezPointEffect` 15. El consumidor `Escape.cs` solo envía resurrección, sin secuencia 49423 comprobada. | `investigating`; resolver secuencia nativa antes de cambiar cooldown. |
| 16 | Defiance 39036 | Log 02:55:14 UTC: `SkillReqFail` antes de efecto/cooldown. SQLite: cooldown 360000 ms; vínculos explícitos a filas 58,59,108–111,330, todas `default_result='f'`. El cliente r575 demuestra que esos vínculos eximen a Defiance de restricciones generales; Game los trataba como condiciones que debía satisfacer. | Regla general corregida y desplegada; `needs_retest` para efecto y 6 min de cooldown en Zone 179. |

## Corrección #11

`ClientSkillCombo` registra el enlace de una raíz con tiempo de casteo **al dispararse** (`SCSkillFired`), no al aceptar `Use`. Un casteo interrumpido no abre la ventana para un hijo no aprendido. La autorización sigue limitada al efecto Combo incondicional, chance 100, nivel válido, raíz aprendida y ventana de tiempo del cliente. El test nuevo cubre los dos hijos, el instante de disparo, expiración y sincronización de animación.

- `dotnet build` Release: correcto, 0 errores.
- `dotnet test` focal: 8/8; suite completa: 5668/5668.
- Imagen de rollback inicial `aaemu-world:pre-bug-report-skills-20260926` (`sha256:8c8e0968…`). Imagen intermedia de #11 `sha256:0448a47d7607465347633856b64ca71b5f2515670c06be3650b8e7e85ba28070`, conservada en `aaemu-world:pre-skillreq-native-20260926`.

## Corrección #16 y evidencia nativa

`Aa10SkillReqStringRefs.java` localiza la carga de `skill_reqs` en `0x39a89240` (RVA `0x00a89240`). `Aa10SkillReqEvalAudit.java` y la cadena de xrefs revelan:

- `FUN_39b96780` (RVA `0x00b96780`) devuelve si el SkillDesc está nombrado por `skill_req_skills` o por sus etiquetas en `skill_req_skill_tags`.
- `FUN_39689570` (RVA `0x00689570`) selecciona cada fila cuando `linked == default_result`: las 102 filas `f` rigen por defecto y el vínculo las exime; las 236 filas `t` rigen solo cuando hay vínculo. Después, si el objetivo/caster tiene el buff o tag de una fila aplicable, retorna `SkillReqFail` (0x32). No existe una excepción de polaridad por cuatro IDs.
- `FUN_39b941f0` (RVA `0x00b941f0`) excluye restricciones de target para los tipos de objetivo no unitarios 6,7,8,9,11–15,18,23. El servidor refleja ese gate usando `SkillTargetType`.

La corrección elimina `RequireRowsByDesign` y aplica el selector nativo a toda la tabla, cacheando las filas por skill en `SkillManager`. El test cubre exención de Defiance, restricción general, fila `t`, unión de vínculos, mensaje y target no unitario. Build Release: 0 errores; pruebas focales 6/6 y suite completa 5664/5664. Imagen final desplegada `aaemu-world:10.0.2.13-r575-local` (`sha256:35932e775655d0876bf55d660ab33eaa1e0e04d06a6e5fe8ff3ac40c069952df`); Game saludable, 0 reinicios. Ghidra logs: `E:\AAEmu\rama_10\artifacts\bug-report-skills-20260926\native-skill-req-*.log`.

En el primer reenganche tras el despliegue final, Zone 179 se conectó durante la carga de `ZoneManager` y World lanzó `NullReferenceException` en `ZoneManager.GetZoneByKey`; la Zone salió. Se esperó el marcador de aplicación `Server started!` y se reinició solamente esa Zone propia, seguida de 129. Ambas quedaron estables. Este incidente de arranque no es una regresión de habilidades.

La auditoría posterior del perfil activo del Control Center mostró que también incluye `.server_files/docker-compose.playit.yaml`. El primer `compose up` del despliegue final omitió ese override y eliminó del contenedor Game los bind de 127.0.0.1:12371/12372 y `StreamNetwork__AdvertisedPort=49174`. Se recreó Game con los tres archivos del perfil activo, restaurando esos puertos y el valor anunciado. Ese segundo reinicio desconectó las Zones; se esperó otra vez `Server started!` antes de enlazar los dos perfiles autorizados. Esta comprobación forma parte del gate final de runtime.

Para #15, `Aa10ZoneEscapeStringRefs.java` sobre Zone DLL r575 SHA-256 `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a` localizó referencias a `MoveToRezPointEffect`, pero las funciones `0x39ad0220` y `0x39c825b0` son el loader/dispatcher de efectos, no prueban quién inicia 49423. La búsqueda de inmediatos `49423` en el código nativo no encontró funciones. El tag compartido de SQLite es evidencia positiva de asociación de cooldown, pero no basta para implementar el evento de éxito.

## Siguiente prueba acotada

Con Zones 179 y 129 disponibles, repetir #11 (secuencia de tres golpes), #16 (con estados de control verificados), #15 (ID realmente lanzado y transición a 49423), y luego #7–#9. Correlacionar petición del cliente, decisión de Game, ejecución Zone, buff/cooldown y resultado visual. No aplicar compensaciones por ID ni importar comportamiento de otra versión.
