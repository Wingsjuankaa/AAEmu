# Ipnya — corregir casteo invisible en Started/Fired

**Aceptación del usuario — 2026-09-06:** confirma que todo funciona, que los cambios se aplican y que cada nivel de ranura aumenta el nivel de objeto. Quedan aceptados el flujo visible de Ipnya y el casteo corregido. Esta confirmación no equivale a ejecutar todas las combinaciones o pruebas negativas posibles. Los apartados de aceptación pendiente más abajo son históricos y quedan sustituidos por esta confirmación.

Target E:/AAEmu/rama_10/server/AAEmu, rama_10, HEADbdad11fec1493c43a854369e707de72a20f26f86; padre upstream/client_version/zone-10.0.2_r575 (6273a02f0c88f3c48e52252c3e64ae7e71d63945). No cambio de rama ni merge. Clase client-native.

El usuario confirma que la ventana funciona y que consume el material después de unos segundos, pero sin casteo/efectos. Screenshot codex-clipboard-4aab6f65-e8d6-43a8-925b-61de4efa1891.png muestra Dannia con ranura17 y EXP100. Logs21:44:09–13UTC prueban skill38363/context22/timeline5061/casteo3500ms y commitowner1007 slot17 level1 exp100. Segundo commit21:44:20 exp200. Lectura posterior DB muestra slot17 level2 exp500; no se modifica ni reinicia su progreso.

Causa: SkillObject implementaba la lectura y Write propio de los contextos22/23, pero SCSkillStartedPacket y SCSkillFiredPacket usan SkillCastWire.WriteSkillCastExtra, que tenía un switch independiente sin esos casos. Enviaba el tipo22/23 seguido inmediatamente de inputDirection, omitiendo6/2 bytes. El cliente AC3780 consume esos bytes obligatorios y lee los tiempos/campos siguientes desplazados. Esto explica la ausencia de casteo mientras Game sigue programando el efecto y cobrando correctamente.

Cambio mínimo: añadir los dos cuerpos al serializer común de salida. Tipo22: u8 ranura,u32 descriptor,bool autoUseAAPoint. Tipo23: u8 ranura,i8 hito. Se mantiene inputDirection posterior, tiempos, timelines, costes y tipos de paquete. No se cambia WriteWzSkillObject: es otro contrato.

Evidencia: AC3780 ya anclado a DLLcliente x64 SHA405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734, base39000000; cases22/23. Consulta actual full/runtime/loose principal confirma igualdad de todas las columnas mecánicas de skills38363/38664: casting_time3500,start_anim108,fire_anim100,fx_group1291. La compact principal cambió por la traducción concurrente; se verifica su fila actual sin escribirla. Padre exacto sin casos22/23; AA8 sólo ofrece otra versión de packets, no se copian opcodes.

Gates: cuatro pruebas construyen los cuerpos completos Started/Fired para ambos contextos. Las4 fallan con el código anterior y pasan con el cambio. Comprueban bytes de inicio, contexto, dirección, tiempos y campos finales para detectar corrimientos. Restore correcto, Release0errores, suite1838/1838 correcta. Evidencia en E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/ipnya-slot-reinforce-frontier/cast-ux. No se precisó añadir paquetes ni instrumentación al cliente: el cuerpo omitido queda probado por el serializer exacto y las pruebas de regresión.

Despliegue y hashes: ver cast-ux/manifest.json. Rollback de imagen aaemu-world:rollback-pre-ipnya-cast-20260906 (14f9dbe048aeaeaa7b0a6a4ae0f7bb5fd59a04285ebb9c772728f03f579fb873). No hay migración ni edición de Features, compact, game_pak o DLLnativa en esta corrección. Se respalda MySQL después de detener Game para conservar los avances reales de Ipnya. Las Zones siguen bajo control del usuario.

Aceptación: la apertura de la ventana, consumo y progresión están confirmados; la presentación del casteo después de esta corrección requiere una nueva prueba del cliente. Una sola operación: volver a entrar, elegir una ranura con espacio deEXP y confirmar un material. Esperado casteo/animación nativos durante3,5s, seguido del consumo y aumento deEXP. No repetir pulsaciones mientras el casteo esté activo. Los efectos especiales estadísticos de la ranura17 se desbloquean en niveles5/10; son distintos de los efectos visuales de alimentar la ranura.

## Identidad desplegada

Imagen nueva `e64b33d51b347a6c7a473132931c7b89fb8726228780a6af65111eb571f1bfb2`. Ambas copias de AAEmu.Game.dll montadas: SHA256 `81375f1d4bbf9ec21cf5f91e71508bb81085540395fa6285654f0be9eb0da2c5`. Features conserva `e4d5cb1f49c71e6ea8aa25946fa9adf92145dc371e49e23910662a10d3cce6d2`; compact conserva `85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`. Backup posterior a detener Game: E:/AAEmu/rama_10/backups/ipnya-cast-20260906/aaemu_game.sql, SHA256 `5cc1e3a429c65c246421a8b3086a730f800fe3d972abb60ec2e067a0817f957c`. El rollback sólo requiere reetiquetar la imagen previa y recrear Game; no restaurar DB para revertir un serializer, porque perdería progreso posterior.

Gate runtime: Server started21:52:07UTC en100.090s; registrado enLogin, API1280 responde[], healthy/0reinicios. Ipnya catalog y Feature197 cargados. Presentación visual postcorrección pendiente de prueba del usuario.
