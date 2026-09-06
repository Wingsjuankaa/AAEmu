# Patron activo para todos por defecto — 2026-09-04

Petición explícita del usuario: activar el buff Patron por defecto para todos.
Target: `E:\AAEmu\rama_10\server\AAEmu`, branch `rama_10`; padre exacto
`upstream/client_version/zone-10.0.2_r575`.

## Cambio

Se activa la política existente `Account.ForceMaxPremiumGrade=true` en
`AAEmu.Game/Configurations/CharacterSettings.json` y en el archivo runtime
`.server_files/AAEmu.Game/Configurations/CharacterSettings.json` montado sobre
`/app/game/Configurations/CharacterSettings.json`. El runtime no tenía la clave;
el source y el default de código estaban en false.

Se utiliza la implementación existente, también presente en el padre comunitario:

- `PremiumGameData.MaxGradeId` resuelve grado 6 en el catálogo r575.
- `Character.PremiumGrade` y `AccountManager.GetAccountPremium` aplican el grado
  a cualquier cuenta/personaje, incluidos nuevos y sin puntos acumulados.
- `CSSpawnCharacterPacket` invoca `ApplyPremiumGradeBuff` después de `SCUnitState`:
  aplica buff 7153 (grado 5 en el nombre interno; no es la numeración del lobby), elimina otros grados
  incompatibles y no duplica el buff si ya está presente.
- El modo existente incluye membresías Ancient/Advanced (1001/1002), sincronizadas
  en atributos de cuenta y en el cálculo de labor. No se inventaron valores nuevos.
- Los puntos persistidos no se sobrescriben; la política se evalúa al entrar y
  para las ganancias futuras. Las membresías forzadas son de sesión.

Evidencia de catálogo: SQLite autoritativa SHA-256
`87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`;
`premium_grades`: grade_id=6, point=400, buff_id=7153. No se modificaron SQLite,
ALB o game_pak; World Level continúa desactivado.

## Despliegue y rollback

Respaldo de ambos archivos y manifest:
`E:\AAEmu\rama_10\backups\patron-default-20260904-171430`.
Se conserva la imagen Docker existente: cambia exclusivamente una configuración
montada. Se reinicia solo `aaemu10-game-1` para recargarla. No se opera lifecycle
de Zones. Al preparar la operación no había personajes online ni procesos ZoneHost.

Rollback: restaurar `CharacterSettings.source.before.json` y
`CharacterSettings.runtime.before.json` a sus rutas originales y reiniciar Game.
Si se ha editado posteriormente la configuración, revertir solo esta clave,
preservando los cambios posteriores. No requiere revertir DB de personajes.

## Validación

Restore y build Release correctos; suite 1804/1804, 0 fallos. Ver logs
`E:\AAEmu\rama_10\forensics\output\patron-*-20260904.log`.
La clave true se verificó en el archivo visible dentro del contenedor y no hay
override de entorno `Account__ForceMaxPremiumGrade`. El manifiesto local registra
identidades y estado del contenedor tras reiniciar.

Arranque confirmado a las 17:16:56 UTC: `GameService - Server started`, registro
correcto en Login y listeners 1239/1250. `/status` responde con 0 jugadores y
contenedor running/healthy. SHA-256 runtime montado (host y contenedor):
`FAC909FC51F9B59B8866A9047F5228EF482FF65AF568ED82314BCC53E62E7DF4`.
No existe `/app/game/Config.Local.json` que reemplace la opción. Durante el inicio
se registró una conexión Zone de id=0 que se desconectó, sin personaje afectado;
no se operó una Zone para corregir ese evento.

## Aceptación del usuario y corrección de la etiqueta

El usuario confirma el nuevo buff y adjunta captura del lobby con `Patron 3`.
Logs 17:42:57 y 17:44:31 UTC confirman `premiumGrade=6`; los mensajes premium
reportan point=400/grade=6/forceMaxGrade=True. La predicción inicial de `Patron 5`
era incorrecta: mezclaba el nombre interno del buff con otro consumidor nativo.

El ALB efectivo `loginstage_new/character_select/account_info.alb` SHA-256
`9766596C557D1024988E2904144DE52FBF8A379F8237C7AA6804A3E79ED2B022` usa
`GetLoginCharacterPremiumGrade(1) - 1`. El wrapper nativo RVA `0x82D350` llama
RVA `0x3571D0`, que consulta los atributos AccountBuff 1001 y 1002 y devuelve:

| Membresías activas | Retorno nativo | Texto del lobby |
|---|---|---|
| Ninguna | 1 | Patron 0 |
| Solo 1001 (Ancient) | 2 | Patron 1 |
| Solo 1002 (Life/Advanced) | 3 | Patron 2 |
| Ambas | 4 | Patron 3 |

Por tanto, `Patron 3` es correcto para la política instalada: ambas membresías
están activas. No indica que el grado interno haya bajado de 6 a 4, ni requiere
forzar visualmente un 5. No se cambia configuración o runtime por este diagnóstico.
Ambas funciones se compararon byte a byte con x2game x64 efectivo SHA-256
`405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.
Evidencia: `forensics/output/aa10-client-forensics/patron-display-20260904`.
