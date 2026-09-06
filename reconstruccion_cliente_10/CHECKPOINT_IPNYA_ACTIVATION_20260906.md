# Ipnya r575 — implementación desplegada, aceptación retail pendiente

**Aceptación del usuario — 2026-09-06:** confirma que todo funciona, que los cambios se aplican y que cada nivel de ranura aumenta el nivel de objeto. Quedan aceptados el flujo visible de Ipnya y el casteo corregido. Esta confirmación no equivale a ejecutar todas las combinaciones o pruebas negativas posibles. Los apartados de aceptación pendiente más abajo son históricos y quedan sustituidos por esta confirmación.

Seguimiento: el usuario confirmó ventana/consumo/progresión; se corrigió después el contexto omitido en Started/Fired. Estado y despliegue más recientes en [CHECKPOINT_IPNYA_CAST_UX_20260906.md](E:/AAEmu/rama_10/server/AAEmu/reconstruccion_cliente_10/checkpoints/CHECKPOINT_IPNYA_CAST_UX_20260906.md). Los hashes de imagen siguientes describen el despliegue inicial.

Fecha: 2026-09-06. Target canónico `E:/AAEmu/rama_10/server/AAEmu`, branch `rama_10`, HEAD `bdad11fec1493c43a854369e707de72a20f26f86`. Padre exacto consultado `upstream/client_version/zone-10.0.2_r575` / `6273a02f0c88f3c48e52252c3e64ae7e71d63945`; conserva los stubs, no se integra ni cambia de rama. Preservados los cambios previos/concurrentes.

Usuario autorizó activar la mecánica completa sin tocar game_pak. Sustituye el estado anterior report-only. Informe vigente: [AA10IpnyaActivationReport_es.md](E:/AAEmu/rama_10/server/AAEmu/Docs/AA10IpnyaActivationReport_es.md). Manifest reproducible: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/ipnya-slot-reinforce-frontier/manifest.json`.

## Entrega

Feature197 `equipSlotEnchantment=true` en fuente y bind mount, editados separadamente. Config237 nivel mínimo50, config236 objeto de reemplazo46682, configs359/360 activas. Implementados loader, contextos22/23, SpecialEffect161/163, CS1D4, SC2C5/2C6/2C7, listas de SCCharacterState y UnitState, transacciones de materiales/moneda/progreso, guardado y recuperación, fórmula69 y bonos individuales/conjuntos. El registro de fuente y bind mount conserva todas las demás opciones.

Catálogo actual: 16 ranuras, 124 niveles, 756 recetas aplicables de2235, 108 promociones, 38 hitos,174 modificadores válidos;5 huérfanos excluidos. Las1479 recetas residuales que exigen nivel15 no se pueden ejecutar. EXP se limita a la barra, sin promoción automática; runa de nivel actual. Reroll excluye el modificador existente según UI9256, y muestrea los pesos de los restantes. No se afirma reproducir la semilla/generador del World comercial.

Los niveles pertenecen a ranuras, no a UIDs. ParentUnit del contenedor resuelve el equipo antes de registrar al personaje en World. Objetos en bolso y feature apagada no reciben el aumento. Config359 exige conservar los pesos primarios por template; sólo cambia item_level en fórmulas de combate. Todos los bonos conjuntos alcanzados son acumulativos.

Game calcula el daño/defensa también para ZWStartSkill de IA; WZUnitDamaged transmite el resultado. Tras la mejora se sincronizan puntos por el puente WZ existente. El snapshot de entrada/handoff lleva la lista Ipnya. No hay reenvío de WZUnitState a una unidad existente: Zone36B3C0 lo rechaza como duplicado. No se encontró paquete WZ incremental de Ipnya; la copia interna de esas listas en Zone cambia en entrada/handoff, no se afirma actualización incremental de esa copia. No se cambia ni opera ZoneHost ni ninguna Zone.

## Gates

Restore y Release0 errores. **1834/1834 pruebas**; tests de bytes nativos, promoción, desbordamiento, rechazos, pesos/exclusión de reroll, pago y estado inmutable. Verificador real de catálogo:756 feeds,108 promociones,38 hitos. Smoke MySQL real con esquema temporal eliminado: stack no guardado previamente, cobro, relog16/38, rollback por fallo SQL posterior al cobro, consumo total, propietario inexistente; fórmulas20/40/55, equipo/bolso/feature apagada y44 bonos. No escribe filas de jugadores reales. Logs restore/build/tests/persistence-tests en la frontera.

Auditor cincoSQLite quick_check correcto, igualdad mecánica,71 funciones cliente reancladas sin diferencias y2 funciones consumidor Zone. Cliente principal DLL SHA405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734; Zone8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a. Auditor ampliado SHA3780c32ccbc3b28193c92a0c576847c90f6474b06a41b82abfe00d599f13f90b. Ver manifest para hashes de scripts y artefactos.

## Runtime y rollback

Imagen Game `14f9dbe048aeaeaa7b0a6a4ae0f7bb5fd59a04285ebb9c772728f03f579fb873`. Contenedor `aaemu10-game-1`, healthy,0 reinicios; arranque21:35:46UTC en101.492s, API interna responde, cero personajes online al verificar. Fset efectivo: `13 37 00 00 d0 29 61 00 32 0c 00 dc 2c 80 00 00 00 a0 1b 10 03 82 91 00 24 34 00 00 01 e0 00`; byte24=24h incluye20h deIpnya. Log Enabled Features incluye equipSlotEnchantment; catálogo cargado. Esto verifica el estado que serializa SCInitialConfig, no es una captura de red nueva al cliente.

DLLs `/app/AAEmu.Game.dll` y `/app/game/AAEmu.Game.dll`: `a98475a8e8d2cac69642b872b2dae7896b6f2d0af31b10090aeffb3dacaad866`.
Features fuenteSHA `c0936b6e6d88322cdca31cc701e5f95de74594536d596acf2f8c1b15d602a807`; montadoSHA `e4d5cb1f49c71e6ea8aa25946fa9adf92145dc371e49e23910662a10d3cce6d2` coincide con el interior del contenedor.
Compact permanece `85024f044f2a0b119776012ee516f90fdd9db28b4e5581403d40526b1b7d8c65`.

Migración `SQL/updates/2026-09-06_aaemu_game_equip_slot_reinforce.sql` aplicada; ambas tablasInnoDB presentes y vacías, sin progreso concedido. Backup después de detener Game en `E:/AAEmu/rama_10/backups/ipnya-20260906/aaemu_game.sql`, SHAde94bf1a7c99dd79b85b72643ab2c8a0812bab007ace5fc1b3958d2d4d3e20c9. Configs originales en esa carpeta. Imagen anterior `aaemu-world:rollback-pre-ipnya-20260906`, SHA42068216132721de2e0843ac68820dd8a14fa47aa6ca7cf19bce99151e05cec6.

Reversión preferida: apagar sólo el flag y reiniciar Game, conservando progreso. Si se vuelve a la imagen anterior, mantener las tablas nuevas sin borrarlas. Una restauración completa del backup perdería también cambios posteriores de otras mecánicas; no hacerla automáticamente. No hay compact, game_pak ni DLL nativa que revertir.

## Próxima interacción

Usuario vuelve a entrar con nivel>=50 y abre C→Ipnya. Sólo después de confirmar la ventana: alimentar una ranura, subir nivel cuando la barra esté llena, cambiar efecto y reconectar. Verificar logs de commits y filas antes/después; si necesita kit, entregar con scriptGM interno cuando esté online, sin insertsSQL. La aceptación visual, consumo en el cliente y combate/relog de personaje real permanecen pendientes; no declararlos probados por el smoke automático. Si su Zone quedó desconectada tras Game, su lifecycle sigue bajo control del usuario mediante Control Center.
