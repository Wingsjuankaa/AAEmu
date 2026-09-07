# Checkpoint — merge comunitario AA10 r575 — 2026-09-07

## Resultado de código

Se integró `AAEmu/AAEmu:client_version/zone-10.0.2_r575` hasta
`7babcb3a706c64295b5aaaeec8abe57e4d09b4da` en la rama propia `rama_10`.
Commit de merge: `5e37602d030b2a6e055c6e199206e62c51e3a03f`.
Padre propio: `6c3f7e5ecf9ebc02797fc30326929da884c44902`.
88 commits nuevos de upstream; 74 rutas con conflictos resueltas por contrato y comportamiento.

El detalle de decisiones y sus límites está en
[`Docs/AA10UpstreamIntegration_20260907_es.md`](../../Docs/AA10UpstreamIntegration_20260907_es.md).
Se adopta correo/subasta, gremios/héroes, instancias, streaming, barcos, stacks y regrade
comunitarios, adaptados a las transacciones y representaciones nativas del fork.

## Frontera forense cerrada

Se corrigió la numeración heredada de ItemTaskType contrastándola con el cliente release x64.
SHA-256 de `x2game.dll`:
`405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`.
Tabla construida en RVA `0xB5A010`, stride `0x28`: 186 asignaciones de nombres extraídas.
SkillReagents es 42; SkillEffectGainItem es 44; ItemLock/Unlock/UnlockExcess son 92–94.
El socketing propio sigue emitiendo 42 mediante el nombre correcto.
Se añaden 16 fixtures de bytes del paquete, independientes de la antigua enum.

La evidencia previa de Item Lock sólo acreditaba que AAEmu conservaba 94–96; no demostraba que
esos índices coincidieran con el cliente. La extracción nueva resuelve esa contradicción.
La documentación de lunagem conservaba el byte correcto con nombre simbólico equivocado;
se corrige sin alterar la secuencia nativa de la ventana.

## Validación y preservación

- Restore y build Release correctos.
- Suite con el trabajo local restaurado y la configuración final: **2.682/2.682**, 0 omitidas.
- El merge inicialmente aislado del trabajo pendiente pasó 2.671 pruebas; el ajuste final de
  features añade una regresión para mantener Butler y Smelting desactivados.
- Las 28 migraciones nuevas se validaron en MySQL 8.0.36 sin red, importando un dump local;
  se corrigió la dependencia de orden de la migración de intereses del gremio.
- Los 32 archivos pendientes originales están restaurados. 31 conservan sus bytes originales;
  `SkillObject.cs` combina el contenido del merge con las dos líneas pendientes de `BatchRequest`.
  Los nueve archivos modificados originalmente y los archivos sin seguimiento continúan fuera
  del commit del merge.
- Se conserva la rama de respaldo y el stash de seguridad, además de los archivos y el diff binario.

## Despliegue y rollback

Game/World y Login se reconstruyeron con el trabajo local restaurado. Se aplicaron las 28
migraciones a la base existente después de parar Game/Login y tomar dumps finales consistentes.
No se reinició MySQL. Conteos antes/después: 5 personajes, 386 objetos y 0 gremios.
Se copiaron `Features.json`, `AccessLevels.json` y `StreamAoi.json` al bind mount; sus hashes
deben coincidir en fuente, montaje y contenedor según el manifiesto de este checkpoint.

El catálogo montado de doodads se conserva: ninguna de las 285 posiciones retiradas por
upstream estaba presente en él, comparando template y coordenadas redondeadas a centésimas.
La SQLite autoritativa mantiene su SHA-256:
`85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.
No se modificaron el cliente ni `game_pak`.

Respaldo privado completo:
`E:\AAEmu\rama_10\backups\upstream-sync-20260907-6c3f7e5`.
Incluye dumps anteriores a migraciones, compact, configuración, imágenes etiquetadas,
las 28 migraciones con hashes y los logs de validación/despliegue.
Tags de rollback:
`aaemu-game:rollback-upstream-20260907-6c3f7e5` (imagen World anterior) y
`aaemu-login:rollback-upstream-20260907-6c3f7e5`.
Un rollback completo de este corte requiere coordinar esas imágenes, las configuraciones
respaldadas y los dumps previos; no se ejecutó un rollback sobre el entorno activo.

## Límites de aceptación

Los errores de Smelting 29–32 son preexistentes y su feature permanece OFF.
Butler también queda OFF: sus paquetes parsean requests, pero no implementan los trabajos.
La aceptación visual de las funciones comunitarias queda pendiente de una sesión retail.
Prioridad: correo/subasta, lock/unlock, lunagem/temper consecutivos, Hiram, barcos y costuras,
invitación/entrada/salida de instancias.
Codex no inició, detuvo ni relanzó Zones. El usuario debe levantar su perfil en Control Center
antes de entrar al mundo; luego corresponde comprobar ZoneLoaded y heartbeats de ese perfil.

## Cierre del día: aceptación comunicada por el usuario

Después del despliegue, el usuario confirmó que completó la prueba de entrada al mundo,
movimiento, inventario/equipo y regreso desde selección de personaje sin incidencias.
También confirmó que Lunagem funciona y que pudo publicar un objeto en subasta.
Es aceptación reportada por el usuario; no se infiere de ella una venta completada,
retirada de adjuntos de correo, extracción de gemas, temper, Hiram ni todas las instancias.

Por petición explícita del usuario se incorporan ahora a Git todos los cambios pendientes:
lote Ipnya de un solo casteo, builder/aplicador Lua y sus contratos/fixtures, parches de
Dwarf/Warborn y pelo, reutilización del aplicador español y documentación de esas entregas.
El código de servidor coincide con la versión ya desplegada y validada con 2.682 unit tests.
La comprobación final de scripts da 24 pruebas aprobadas y 3 omitidas por requerir evidencia
retail extraída/configurada; no se aplicaron parches al cliente durante este cierre.
No se cambió el comportamiento del runtime para realizar el commit.
