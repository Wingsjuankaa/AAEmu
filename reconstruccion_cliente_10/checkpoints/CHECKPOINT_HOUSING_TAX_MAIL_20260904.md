# Correo fiscal con apóstrofo en el nombre — AA10 r575

Target: `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`.
Padre revisado: `upstream/client_version/zone-10.0.2_r575` (3cc280b14).
El padre y el comparador AA8 conservan la interpolación sin escape.

## Evidencia y causa

El 2026-09-04 a las 22:42:06 UTC, Game recibió CSReadMail para 10003 y
respondió SCMailBody/SCMailStatusUpdated sin excepción. La fila persistida
contenía `body('Miner's Farmhouse', ...)`: el apóstrofo termina el argumento
Lua antes de tiempo. No es un fallo de entrega ni de ownership.

Evidencia focal: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\housing-tax-mail-frontier`.
`read_mail.lua` extraído del game_pak r575, SHA-256
`25703A9441226B09E14989E42463505E9E9CF37413CA8CF38012FC56ABB86213`,
confirma el consumer GetMailText en la ventana de lectura.
`game/scripts/x2ui/mailbox/common.lua`, SHA-256
`8DFC6568E4505968E97781D0097606E1D976FB086BC1ECE55082A586AB5AAC50`,
líneas 21-23 concatena `return locale.mail` + sender + `.` + texto y llama
`loadstring`. Si falla retorna el texto crudo; FillContent espera el resultado
estructurado de la función fiscal. Cierra el vínculo entre el error sintáctico
y el consumer de lectura real.
`before.lua` conserva el cuerpo real: luac51 -p falla con `')' expected near 's'`.
`after.lua` conserva los mismos argumentos escapando el apóstrofo: luac51 -p correcto.

## Corrección

MailForTax escapa apóstrofos, barras inversas y controles en el argumento
del nombre. Los controles usan escapes decimales de tres dígitos compatibles
con Lua 5.1; Unicode se conserva. Se aplica a creación y UpdateTaxInfo.
HousingManager.Load llama UpdateTaxInfo para las casas cargadas y regenera
los correos pendientes existentes mediante el mismo camino, sin migración SQL.
No cambia importes, deadlines, inventario, paquetes ni cliente.

## Validación y entrega

Restore y build Release correctos. Suite: 1812/1812, incluidos seis casos nuevos
que ejecutan los argumentos en Lua y verifican nombre, cantidad, campos vecinos
y ausencia de ejecución de texto incrustado. Verificación adicional de sintaxis
con el compilador Lua 5.1 para el cuerpo real original/corregido.

Respaldo DB: `E:\AAEmu\rama_10\backups\tax-mail-20260904\aaemu_game.sql`.
Imagen rollback: `aaemu-world:rollback-tax-mail-20260904`
(`dd9bab5b6df5beb5d8c949117fb99b4e925fac7a145e284596462ed5efad0aaa`).
Imagen Release construida: `8c01ea32394cdcb4e0a65ce17f0a9b1b266360c832e9fe8e07afd5ce5fb29fb7`.
Despliegue limitado a Game con ambos compose y `--no-deps`.
Zones bajo control del usuario; no se operan sus procesos.
Aceptación visual de abrir el correo y pago: pendiente del usuario.

Runtime verificado: Login/DB/Game saludables; Game/Stream escuchan 1239/1250,
API interna responde. Ambas copias /app/AAEmu.Game.dll y /app/game/AAEmu.Game.dll
tienen SHA-256 `05c137951b2c80a16314b19c0f91dbbcb3e94b6b48a84e99128bdb5f7d6e55e9`.
El guardado normal 22:56:43 UTC actualizó un correo y eliminó cero. Relectura
raw de MySQL confirma 10003 con el apóstrofo escapado y BillingAmount=750000
intacto; `persisted.lua` pasa luac51 -p. Sin escritura SQL manual.
El arranque conserva avisos previos de Item Smelting (fuera de alcance); no
se observaron errores nuevos del correo ni bucles de reinicio.
