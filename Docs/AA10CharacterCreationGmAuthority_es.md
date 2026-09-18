# Creación de personajes: bloqueo de cuentas GM — 2026-09-16

## Rectificación de la solución — 2026-09-18

La propuesta original de enviar autoridad `1` también a cuentas GM fue retirada.
El diagnóstico del bloqueo era correcto, pero esa solución quitaba la autorización
GM nativa. El servidor conserva `gmFlag`, pero el cliente no lo consulta para
reemplazar su bit `0x04`. Se restaura el comportamiento del padre: autoridad `101`
para cuentas con acceso >= 100 y `1` para el resto. Se mantienen los valores del
padre sin atribuir significado no demostrado a los bits `0x20` y `0x40`.

La comprobación GM de `x2game-dev.dll`, RVA `0x4C0520`, rechaza con
`you are not gm.` cuando no hay bit `0x04` ni se cumplen las excepciones del motor.
Los gates de creación descritos abajo usan ese mismo bit. Por tanto, enviar `5`
conservaría GM, pero tampoco permitiría crear fuera del editor. Las cuentas GM
deben conservar esta restricción; la creación ordinaria corresponde a una cuenta
sin permisos GM. Esta corrección no modifica cuentas ni personajes existentes.

Se verificaron los bytes de los tres rangos contra los binarios actuales:
GM dev (140 bytes), creación dev (726) y creación release (672). Todos coinciden
con las extracciones Ghidra aunque difieren los hashes de archivo completo de sus
importaciones. SHA-256 dev: `81dfabe826125d5ad4914439815af62fdee550dcc98b6f29c65d4228fa9f2b80`;
release: `405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`.

[Análisis y solicitud de cierre del PR #1627](https://github.com/AAEmu/AAEmu/pull/1627#issuecomment-5736900438).
Evidencia local: `E:\AAEmu\rama_10\artifacts\pr1627-review-20260918`.
No se presenta esta revisión estática como una prueba nueva de consola o idle kick,
ni como evidencia independiente de la política operativa de GM en retail.
Las secciones siguientes conservan el diagnóstico y la entrega históricos;
la corrección de autoridad `1` descrita allí queda reemplazada por esta rectificación.

Al confirmar el nombre, el diálogo se cerraba y el cliente permanecía en apariencia.
El siguiente intento recuperaba el nombre, pero no enviaba `CSCreateCharacter`.
El caso local fue Rahenis; los registros de otro usuario, mencionados en el
checkpoint de perfil local, mostraban un síntoma similar, sin probar su causa.

## Causa confirmada

La integración `e533e88b6` cambió la autoridad de `X2EnterWorldResponsePacket`
de `1` a `gm ? 101 : 1`. El nivel de acceso AAEmu 100 es numérico, mientras que
ese campo nativo es una máscara: 101 (`0x65`) activa el bit `0x04`.

El cliente r575 comprueba ese bit antes de enviar la solicitud. Cuando está
activo, exige que el motor esté en modo editor; si no, retorna sin solicitud
ni aviso. Ejecutar el cliente con `-devmode` no satisface por sí solo ese requisito.

Se leyó el cliente abierto sin modificar su memoria: autoridad 101, byte de
editor del motor 0, permisos de creación habilitados, congestión de todas las
razas 0 y ninguna plantilla de personaje bloqueada por contenido. La plantilla
de elfa y el descriptor del cabello seleccionado eran válidos. El cliente
registró `creating character`; Game no recibió `CSCreateCharacter`.

Evidencia del consumidor:

- `x2game-dev.dll` ejecutado: SHA-256
  `81dfabe826125d5ad4914439815af62fdee550dcc98b6f29c65d4228fa9f2b80`, x64.
- `NewCharacter`: RVA `0x9A66C0`; validación/envío: RVA `0x4F18B0`.
- El consumidor release equivalente tiene la misma condición en RVA `0x356D20`.
- La lectura de autoridad usa el objeto de conexión y su método virtual `+0x18`;
  en el proceso inspeccionado devuelve el campo `+0x48` de CryNetwork.
- El método de motor exigido consulta `+0x9D1` y el bit 2 de `+0x984`;
  los valores observados fueron 0 y 3 respectivamente, por lo que devuelve falso.

## Corrección original y alcance (retirada)

Restaurar autoridad de conexión `1` para cuentas normales y GM. El constructor
del paquete deja de recibir un booleano GM para evitar volver a convertir ese
permiso en indicadores nativos. Se conserva la asignación de `gmFlag` en
EnterWorldManager, el control de acceso de comandos y los niveles de cuenta y
personaje. No se cambian MySQL, apariencia, nombres, SQLite, traducciones ni cliente.

La cuenta debe volver a iniciar sesión: una conexión ya abierta conserva el valor
anterior. Crear un personaje no necesita iniciar Zones; para entrar al mundo,
el usuario debe tener su perfil de Zones conectado desde Control Center.

## Validación y entrega históricas (2026-09-16)

- Restore y build Release completos: cero errores.
- Dos pruebas nuevas verifican el paquete completo, longitudes de clave RSA,
  autoridad `1`, ausencia del bit de editor y conservación del atributo GM.
- Suite completa: 4.619 aprobadas, cero fallos y cero omitidas.
- Imagen anterior: `sha256:a2410c071173c066a9eb7127298d994d684815961b92f7d076a33fd0a454a204`.
- Imagen corregida: `sha256:b1e2a1fa0ec5eb22fe7c4d810c98b8d2ec6dd1f60e082ea86dd5f78aa4a761a9`.
- Respaldo: `aaemu-world:rollback-character-create-20260916`.
- Despliegue de Game/World: 2026-09-16 22:05:40 UTC; lifecycle de Zones no operado.
- Aceptación de creación en el cliente después de reconectar: pendiente.

Artefactos de diagnóstico/build/pruebas en
`E:\AAEmu\rama_10\artifacts\character-create-20260916`.
Los cambios ajenos de tax/trade, fishspots y perfil local se conservaron.
