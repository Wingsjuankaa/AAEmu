# Impuestos y aviso de disolución al entrar — AA10 r575

Target `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`, HEAD inicial
`ed64286c69b932490703a9aa7420189499ea4e82`. Padre exacto revisado mediante fetch:
`upstream/client_version/zone-10.0.2_r575`, `b439e1cc0d4bb96647d11dcb76da61b0246a53e1`.
El padre conserva tanto feature107 activada como la disolución incondicional al login.
AA8 no aporta autoridad a este contrato; sólo contiene el opcode de otra versión.

## Causa cerrada

La captura muestra `MAIL_FAIL_RESTRICT_OWNER_CHANGE`, error nativo **839**,
confirmado en `enum_error_messages`. No es `WORLD_RESTRICT_OWNER_CHANGE` (843)
ni prueba de estar en Garden. La identidad de localización es
`(ui_texts, text, 6792)`, fila localized_texts349864. En la compact del cliente
principal, `en_us` contiene exactamente «Estás en un periodo de protección de
intercambios.»; coincide con el significado de las fuentes. No se cambia texto,
Lua, ALB, compact ni game_pak para ocultar el error.

Cliente principal x64 SHA256:
`405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`.
El proyecto Ghidra histórico SHA2735819 fue reanclado contra el ejecutable
405242e verificando **todos los bytes de ambas funciones**:

- `RVA 0x730FF0`, 623 bytes, hash
  `5cfca4d3c83ea124692f65bf7aa1aa148f78e6f13f88211fd6e61e8e2b66107a`:
  antes de emitir CSPayChargeMoney0xE2, comprueba bit0x800 de ctx+0x34
  (`fset[13]&0x08`, feature107). Si el temporizador no venció, muestra839.
- `RVA 0x345A50`, 100 bytes, hash
  `c13434ae35f95ecbb60cd50ceb19488b068c44f7abcd38b73ff36dfbc46363b2`:
  con bit107 apagado retorna permitido inmediatamente. Encendido, compara el
  tiempo transcurrido desde ctx+0x3590 contra el umbral nativo. No depende del
  grupo ni de la zona. La duración exacta y el nombre exportado siguen sin
  promoverse; no se inventa una duración en la UI.

Por separado, `SyncClientSquadAfterLogin` enviaba SCDisbandSquad0x30D cuando
NO existía squad del personaje. Logs de Dannia1007 a13:58:41UTC confirman el
envío. Ese evento explica el aviso rojo; no demuestra pertenencia a instancia.

## Cambio

- Feature107 desactivada en configuración versionada y bind mount. Se conserva
  el nombre `fset_13_3_unknown` por compatibilidad, con semántica documentada.
- Login sin squad conserva la limpieza de cola, pero no emite una disolución
  inexistente. Las disoluciones reales y la salida de instancia conservan sus
  paquetes. No cambia membresías, matchmaking, permisos ni pagos.
- La prueba de configuración verifica el bitmap y los flags vecinos de
  instancias/housing; la prueba de login captura el transporte en dos ingresos
  consecutivos y descarta el aviso de disolución.

## Evidencia dinámica anterior al cambio

El usuario confirmó que /soloparty, disolver y pagar funcionaron antes de editar
el runtime. Logs14:09:51/14:09:54UTC muestran CSPayChargeMoney para10004/10003
y SCChargeMoneyPaid0x163 para ambos. La secuencia no prueba que el grupo quite
la protección: el consumer nativo sólo consulta tiempo/feature107.
Después del guardado/reinicio ambas filas ya no existen en `mails`.
No se ejecutaron pagos, reintegros ni modificaciones SQL manuales.
Cola BugReports consultada (hasta100 activos): sin reporte relacionado.

## Validación y despliegue

Restore y build Release correctos; **4601/4601 tests**, cero omitidos.
`git diff --check` correcto. Evidencia y logs:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\tax-trade-protection-20260916`.

Respaldo `E:\AAEmu\rama_10\backups\tax-trade-protection-20260916`:
dump transaccional aaemu_game, Features.before.json, identidad de imagen.
Rollback: `aaemu-world:rollback-tax-trade-protection-20260916`, imagen
`b5b521fab2dbeb8e692a041b16e7847ee4af77aa70d92aa3cfd6c7ba86fd2033`.
Imagen Release desplegada sólo en Game, ambos compose, `--no-deps`:
`cf3a3afee847ca4b7741715e7293f950b7f5b29f57dc01072e9472d5b0afa295`.
Ambas copias AAEmu.Game.dll del contenedor:
`a980537c95d270c5fd2e4622d33ec7082487c643913eca12431a35cea132e20c`.

Verificación del runtime: DB/Login/Game saludables, cero reinicios, /status
responde y puertos1240/1239/1250 escuchan. FeaturesManager14:18:25UTC publica
`5f 37 00 00 f4 2f 61 02 32 4e 00 fe bf c7 2d 00 00 ff bf f5 7f 9e b3 00 6c bf 28 90 79 f2 02`;
byte13=0xC7 deja bit0x08 apagado y mantiene vecinos. Es la misma FeatureSet que
SCInitialConfig.Write serializa (prueba de wire verde). La configuración
versionada y el bind mount sólo difieren en una línea final vacía; el archivo
visible en el contenedor coincide por SHA256 con el mount
`95eba7cc1bf2a288547b610a2a82c31b59224d4d7e1101b81607e613b22e2f1c`.
Persisten los avisos preexistentes de Smelting29–32 (excluido del alcance) y
Zones no cargadas; no se atribuyen a este cambio.

Zones no operadas. Dannia persiste en zone179 (`w_solzreed_3`). El usuario
administra ese perfil en Control Center. Pendiente aceptación posterior al
despliegue: ingreso sin aviso falso y acceso inmediato al correo; el pago
anterior está aceptado, pero no sustituye la prueba con feature107 apagada.
