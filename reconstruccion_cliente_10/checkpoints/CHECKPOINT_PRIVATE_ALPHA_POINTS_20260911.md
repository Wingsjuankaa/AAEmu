# Alpha privada V9: Honor y Vocación — 2026-09-11

Target `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`, HEAD
`fd53b458573572cc354c8564293f274801d9aa3e`, padre
`upstream/client_version/zone-10.0.2_r575`. Extiende V8 sin cambiar su búsqueda
automática bilingüe. Estado de instalación y hashes en
`PRIVATE_ALPHA_POINTS_20260911.manifest.json`; aceptación nativa pendiente del usuario.

## Acción visible y persistencia

La llave 900001 abre dos controles adicionales: Honor y Vocación, con cantidad
inicial 1000 y botón explícito Obtener. Cada entrega admite 1–100000 enteros.
Los controles requieren ACK autorizado y se bloquean durante solicitudes.
No se repite una entrega tras timeout ni al pulsar dos veces mientras espera.
La búsqueda automática continúa mostrando diez filas, ahora de 34 px.

`AlphaService` acepta `honor/<cantidad>` y `vocation/<cantidad>` por el transporte
custom ya validado. Conserva autorización por personaje, posesión de llave,
deduplicación y throttle. El ACK de apertura conserva sus tres campos anteriores.
Sólo Dannia/1007 está autorizada; no se crean accesos ni se conceden puntos durante
la instalación.

`GrantAlphaPoints` valida tipo, cantidad, saldo no negativo y ausencia de overflow;
actualiza una sola columna SQL y sólo tras éxito actualiza memoria y notifica.
Rechaza completa una operación que no cabe; no recorta la entrega. Honor usa
`characters.honor_point`, Vocación `vocation_point`. No aplica buffs de ganancia
ni dispara objetivos de misiones con estas concesiones artificiales. El método
normal `ChangeGamePoints` conserva sus bonificaciones y eventos; su mutación
comparte ahora `GamePersistence.Sync` con la concesión alpha y el guardado general.

## Autoridad

Reutiliza los consumidores AA10 cerrados en `Docs/AA10CharacterPanelVocationStoreReconstruction_es.md`,
`Docs/AA10LaborProficiencyRegression_es.md` y el dossier
`forensics/output/aa10-client-forensics/vocation-shop-frontier/README.md`.
`SCCharacterGamePointsPacket` publica la tabla de 14 i32 (Honor slot 0, Vocación
slot 1); `SCGamePointChangedPacket` usa count u8=1, kind u8, delta i32.
Honor kind=0; Vocación kind=1. No se cambian opcodes, transporte ni serializadores.
Las pruebas retail históricas de Vocación no sustituyen la prueba de estos botones.
La inspección del padre conserva el flujo existente de puntos. AA8 se consultó
como comparador estructural (`structural_candidate`); no se portan sus opcodes.

## Gates y reversión

Restore y build Release correctos, 2773 pruebas de servidor, 9 del parche/Lua.
Control Center: typecheck/build correctos, 65 pruebas correctas y 1 omitida.
Su caché usa ruta/tamaño/mtime y el SHA es informativo: no tiene allowlist cerrada.
El aplicador valida hashes exactos, respaldo, tamaño fijo del ALB (30761 bytes),
reextracción, sentinelas de mapa/icono/Folio y SHA completo del paquete.
La compact, catálogo y configuración de acceso no cambian en V9.

Imagen de rollback `aaemu10-private-alpha-v9-rollback:20260911` (V8), DB en
`E:\AAEmu\rama_10\backups\private-alpha-v9-20260911\aaemu_game.sql`.
Los respaldos por entrada y hashes están en el manifest de aplicación enlazado.
Restaurar sólo la entrada ALB usando el hash previo V9 exacto y la imagen V8;
no restaurar toda la DB sobre progresos del usuario. No hubo migración SQL V9.

## Prueba nativa pendiente

El usuario retomó expresamente el control de Zones y pruebas. Codex no inicia,
detiene ni relanza Zones ni opera el personaje para esta entrega.
Base previa: Dannia Honor=16100, Vocación=1681, money=11748369695,
199 filas de ítems / 189873 unidades; único acceso 1007.

Primero abrir el cliente actualizado y la llave; solicitar 1 Honor y comprobar
16101 en UI y SQL si no hubo otra ganancia/gasto. Tras correlacionar esta entrega,
solicitar 1 Vocación (1682 bajo la misma condición), comprobar rechazo de 0,
ausencia de duplicado al doble clic y conservación al volver a entrar.
La suite automatizada no acredita actualización visual ni persistencia tras relog.
No se etiqueta como aceptado ni se hace commit/push en este estado.
