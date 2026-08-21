# Launcher simple y autenticación de cuentas AA10

## Objetivo

El launcher de usuario final solicita únicamente el endpoint Login, nombre de
usuario y contraseña. Si `AutoAccount` está habilitado y el usuario no existe,
Login crea la cuenta con la credencial del primer inicio. Los intentos siguientes
deben presentar la misma contraseña.

## Contrato

El launcher convierte la contraseña UTF-8 a SHA-256 y construye el token:

```text
aaemu-sha256-v1:<64 dígitos hexadecimales en mayúsculas>
```

El cliente r575 incorpora `StrUserName` y `strUserToken` en el passport JSON de
`CARequestWebAuthPacket`. `CARequestWebAuthPacketHandler` exige ambos campos y el
prefijo versionado. Un JSON malformado, un hash de longitud incorrecta o un token
legacy arbitrario se rechazan con `BadAccount`.

Los tokens válidos se entregan a `PasswordAuthFlow` como
`PasswordKind.Sha256Hex`. Esto reutiliza `LoginController.Login`, incluido el
control de ban, la verificación en tiempo constante y la creación condicionada
por `AutoAccount`. El antiguo camino `TokenAuthFlow` ya no es alcanzable desde el
packet de launcher, por lo que conocer sólo el nombre de una cuenta no permite
suplantarla con `testtoken`.

## Persistencia y exposición

- El perfil local conserva endpoint y ruta del cliente, no la contraseña.
- El renderer puede recordar sólo el último nombre de usuario.
- La contraseña en texto claro existe únicamente en memoria durante el click de
  lanzamiento.
- La línea de comandos contiene el derivado SHA-256, no el texto claro.
- Los logs ya redactan cualquier argumento `strUserToken`.
- Los diagnósticos exportados no contienen credenciales.

El derivado presente en la línea de comandos debe tratarse como secreto mientras
el proceso está vivo. Es suficiente para repetir la autenticación y no debe
publicarse en capturas o reportes.

## Aceptación estática

- Launcher: typecheck, 13 pruebas y build Electron de producción.
- El portable 0.2.1 detecta en cada inicio `Bin64/archeage.exe` junto a su
  carpeta, valida los hashes retail r575 y sólo solicita una ruta manual si no
  encuentra un cliente válido.
- La vista principal expone únicamente usuario y contraseña; endpoint, puerto y
  ruta quedan en el panel de configuración accesible desde la tuerca.
- Login: build Release de la solución y 1.399 pruebas unitarias.
- Pruebas específicas: token versionado usa `PasswordAuthFlow`; tokens legacy o
  malformados devuelven `BadAccount`.

## Despliegue pendiente

El launcher 0.2.1 necesita una imagen Login que contenga este handler. Reiniciar
o recrear Login es un paso de despliegue separado; no requiere operar Zones.
