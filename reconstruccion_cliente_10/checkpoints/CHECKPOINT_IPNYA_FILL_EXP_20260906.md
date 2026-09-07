# Ipnya: completar EXP en un solo casteo (V3)

Estado: corrección implementada y desplegada. **Flujo positivo retail V3 aceptado por el usuario.**
V1 encadenaba casteos y fallaba por CooldownTime. V2 no enviaba la petición desde
Console.ExecuteString: video del usuario muestra timeout sin casteo ni consumo.
No presentar ninguna de esas versiones como aceptada.

Target rama_10; base 6c3f7e5ecf9ebc02797fc30326929da884c44902.
Padre upstream/client_version/zone-10.0.2_r575, commit 6273a02f0c88f3c48e52252c3e64ae7e71d63945.

V3 usa el emisor directo X2Chat.JoinUserChatChannel (CS 0x96). Nombres reservados
transportan fragmentos ASCII de hasta 23 bytes, sin contraseña y create=false.
El servidor intercepta antes del chat, ensambla por personaje, limita memoria,
vence fragmentos, invalida cancelación y duplicados; sólo una solicitud completa
puede iniciar Skill.Use(38363). No se crean canales ni se comunica con terceros.
La validación, el pago atómico con oro y la promoción separada con runa se conservan.

Informe y reproducción: Docs/AA10IpnyaFillExp_es.md.
Builder/aplicador: Scripts/PatchAa10IpnyaFillExp.py y Scripts/ApplyAa10IpnyaFillExp.py.
Fuente cliente: Scripts/lua/IpnyaFillExp*.lua. Contratos con baseline, V1, V2 y V3 exactos.
Manifiesto actualizado: IPNYA_FILL_EXP_20260906.manifest.json. Evidencia completa:
E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/ipnya-single-cast/v3.

Imagen: 9e731cf67d750344341648191eabb2871ab1990fbebdac92075e0e7eb1c2a9e5.
Ambas AAEmu.Game.dll: 2264a1e478c88fcb83028b70a9aba19561c497b8dbd6e874c71c3cc0942b35ca.
Respaldo con Game detenido: E:/AAEmu/rama_10/backups/ipnya-single-cast-v3-20260906/aaemu_game.sql.
Features/compact conservados. Sin migración SQL. Game listo 2026-09-07 00:06:16 UTC.
No se operaron Zones; las desconectadas necesitan relanzar el perfil correspondiente.

Cliente español full-preview: info.alb 36127 bytes,
SHA256 83C8871E28CA160E070B75A1F8C2B1E24FBDFE97F7CD5BFC52B6CEEF2DF0506F.
Paquete completo 74107641856 bytes, SHA256
723A022888D970D76D2CEF16A4AA65BBD5C4260157EF5D8D75E47CF659E4A0E4.
Dry-run, aplicación, reextracción, mapa/icono/Folio e idempotencia correctos.

Gates: restore/build Release, 1848 pruebas backend (23 focales), 12 Lua/builder,
72 presupuestos cliente/servidor, 65 escenarios con enumerador independiente,
14 regresiones UI. Panel typecheck/build, 52 pruebas y smoke SQLite; una integración
omitida. Cuatro funciones de transporte reancladas byte por byte a la DLL activa.

El usuario pidió a Codex controlar el PC y probar mientras se ausenta.
Computer Use funciona: se observó AAEmu Simple Launcher, juego cerrado y contraseña
vacía (no guardada). Se dejó el lanzador visible y se pidió al usuario iniciar sesión.
No se extrajeron credenciales ni se cambió la cuenta para sortear ese bloqueo.
El usuario realizó la prueba y confirmó: «funciona, fue todo un exito».
Logs del 2026-09-07 UTC confirman tres lotes completos sobre Dannia/slot 17:
00:31:50→00:31:54 nivel 7, 2450 EXP bruta, 5613174 oro, barra 2400;
00:33:57→00:34:01 nivel 8, 2625 EXP bruta, 13878720 oro, barra 2600;
00:34:09→00:34:12 nivel 9, 2800 EXP, 34366368 oro, barra 2800.
Cada solicitud registró un casteo y un commit. La promoción nativa llegó al nivel
10 a las 00:34:15, effect=160. Se cierra la aceptación del flujo positivo.
Cancelación y reconexión no fueron confirmadas individualmente en retail;
conservar esa distinción respecto de las pruebas automatizadas existentes.
