# Integración del padre AA10 — 2026-10-29

## Linaje y conservación

Target canónico: `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10` del fork
`Wingsjuankaa/AAEmu`. Padre exacto: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`,
corte `78533663d9ca93dc4aa610c088359312f91f4293`.

Antes de integrar se validaron y publicaron cuatro commits propios:
`14dce1670`, `b1276a86d`, `557201cb5` y `6c77f7c57`. El último conserva
el informe de validación previa. El padre aportaba 385 commits aún no presentes
por ascendencia: 306 sin merge y 79 merges. La integración usa merge completo,
sin rebase, reset ni force-push; retiene la ascendencia y los commits del fork.

Respaldo local: `E:/AAEmu/rama_10/artifacts/pre-upstream-validation-20261029`.
Incluye patch previo, inventario de conflictos, decisiones por archivo, logs de
build/pruebas, configuraciones anteriores e imágenes etiquetadas para rollback.
Existe además `refs/backup/rama_10-pre-upstream-20261029-6c77f7c57`.

## Contratos conciliados

Se conservan los requisitos y exenciones nativos r575, la autorización de los
hijos de Bola de fuego al disparar, los nueve sockets físicos independientes de
Lunafrost, las transacciones de transformación de equipo, el refuerzo nativo de
slots, la política cerrada de crafting, los portales con distrito/subzona y las
recompensas/progreso durable de quests. El adaptador de refuerzo comunitario lee
el estado nativo y no escribe en su esquema alternativo.

La integración añade el catálogo comunitario y sus consumidores compatibles,
conservando los campos `enable`, producto-pack y grado de materiales de crafting.
La ruta pública de carga y las rutas de pruebas comparten esos contratos. Se
eliminan cargas repetidas de spawn de doodads y de actos de quests; no se ocultan
las colisiones de claves. La inicialización de atributos de objetos otorgados
usa el resolvedor nativo de síntesis.

Los plots capturan el timeline al nacer, mantienen las condiciones de rango
autorizadas y separan los marcadores de posición de unidades visibles. La
serialización de vivienda se comparte entre Game y Zone, incluye categoría y
UCC, y conserva co-owner/owner distintos. Las gemas usan los contextos 10/11 y
la respuesta completa de extracción; los lotes probabilísticos se rechazan sin
gasto parcial y se comprueba el Labor del lote antes de modificar objetos.

Los tests comunitarios que asumían esquemas anteriores se adaptan a esos
contratos: no sustituyen el ledger nativo de recompensas por stubs ni vuelven a
persistir habilidades ancestrales como habilidades aprendidas. Las pruebas que
mutan el singleton de content_configs se aíslan para evitar carreras.

`vehicleZoneSimulation=false` y `factionMigrateLimit=true` se incorporan del
padre con su golden de features actualizado. Se conservan reparación, buffs y
las demás decisiones locales. Item Smelting continúa fuera de alcance y con
su feature desactivada; sus mensajes diagnósticos no lo reactivan.

## Validación

- Restore y build Release de la solución: correctos, cero errores.
- Suite .NET: **8830 correctas, cero fallidas, cero omitidas**.
- `python Scripts/tests/test_local_profile.py -v`: **10 correctas**, incluyendo
  sandbox de DLL r575, Apply/Rollback, repetición y manifiestos autorizados.
- Launcher existente: typecheck correcto y **31 tests correctos, 1 omitido**;
  conserva el canal interno `en_us` y el cliente español principal.
- `git diff --check`: correcto.

La suite incluye cobertura adicional del adaptador de refuerzo y del campo
`enable` en el cargador comunitario. La aceptación de gameplay de una sesión
retail sigue requiriendo las Zones iniciadas por el usuario.

## Base de datos y despliegue local

Se respalda `aaemu_game` y `aaemu_login` antes del cambio. Dump:
`database-pre-merge.sql`, SHA-256
`901dad3b98992bf06e209120c4240d15d95c24a85a298b633408387eaaeeca17`.
Se aplican 46 adiciones de tablas/columnas necesarias y se permiten NULL en
HP/MP de mascotas sin convertir ceros ya grabados. Se eliminan del bootstrap
las definiciones alternativas duplicadas de ArchePass y refuerzo: el esquema
nativo existente permanece como autoridad. No se ejecutan los DROP/TRUNCATE
históricos ni se reinicializan las bases o sus volúmenes.

Las imágenes anteriores quedan como `aaemu-rollback:aaemu10-game-1-20261029`
y `aaemu-rollback:aaemu10-login-1-20261029`. El rollback con datos posteriores
al respaldo exige preservar primero esos datos; no restaurar el dump a ciegas.
El contexto Docker excluye .env, runtime montado, Git y productos de build.

Compose activo: `docker-compose.yaml` más `.server_files/docker-compose.aa10.yaml`.
Se retira Playit de la selección activa del panel, conservando su archivo y
perfil para volver a elegirlo. Se sincronizan Features/Weather al bind mount;
World recibe los nuevos multiplicadores de durabilidad y mantiene el
`ActabilityRate=100` local.

## IP y arranque del usuario

IP confirmada en Ethernet 4: `192.168.1.94`. Login usa `1237`, Game `1239`,
ZoneAuthority `1240` y Stream `1250`. MySQL sigue en loopback y el API interno
no se publica. El perfil local anuncia la IP LAN y mantiene los puertos nativos.

Control Center queda con la IP y el cliente español principal, conservando
íntegro el perfil de Zones. Ambos launchers seleccionan `aa10-ip-local`,
un perfil explícito que evita que la migración histórica `aa10-lan` vuelva a
Internet. Se preservan los perfiles anteriores y se respaldan los JSON de
AppData fuera de Git; no se publican credenciales.

Cliente principal: `E:/AAEmu/rama_10/client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`;
locale `en_us`. El cliente original, game_pak y el corpus de localización no
se modifican. Los fuentes pendientes del repositorio independiente del launcher
se validan pero no se incorporan al merge del servidor.

El usuario abre Control Center portable 0.1.9, selecciona las Zones que quiere
usar y pulsa **Iniciar** en el panel **Zones**. Esta integración no inicia,
detiene ni relanza ZoneHost. Tras su acción se deben verificar ZoneLoaded y
heartbeats antes de entrar con el cliente.
