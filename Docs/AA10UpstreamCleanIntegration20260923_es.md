# Integración parcial del padre AA10 — 23 de septiembre de 2026

Target: `Wingsjuankaa/AAEmu:rama_10`. Padre exacto: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`, corte `b73c33aa761dac418472fa85c7e0985dc98abb73`. Base local `f8cae2e71`.

## Alcance y método

Petición del usuario: empezar por todos los commits incorporables sin conflicto. Se simularon las 70 entregas first-parent pendientes: 23 limpias y 47 con conflicto textual. Se aplicaron los cambios en worktrees detached, mediante cherry-pick con `-x` y mainline 1 para los merges. Ningún conflicto se resolvió manualmente. La rama principal conserva su historia; esto es una absorción parcial, no un merge completo del padre.

De las 23 entregas limpias: 16 incorporadas, 4 ya presentes, 2 aplazadas por defectos identificados y 1 por dependencia. Se examinaron además 131 commits individuales de las series restantes: 11 limpios, de los cuales 2 ya estaban presentes. De los 9 con cambio real, se incorporaron 4 y se aplazaron 5 por dependencias o fallos en caminos de error. Total: **20 commits upstream incorporados**.

## Cambios incorporados

| PR / origen | Cambio |
|---|---|
| [#1619](https://github.com/AAEmu/AAEmu/pull/1619) | Persistencia: evita bloqueos recursivos al diferir escrituras de correo y controla el vaciado anidado. |
| [#1616](https://github.com/AAEmu/AAEmu/pull/1616) | Carga los paquetes de equipo de mascotas y las ranuras/equipo permitido de vehículos desde los datos AA10. |
| [#1630](https://github.com/AAEmu/AAEmu/pull/1630) | Pruebas de regresión para deltas de pilas de objetos; la corrección de producción ya estaba en el fork. |
| [#1636](https://github.com/AAEmu/AAEmu/pull/1636) | Scripts comunitarios para construir e iniciar World; no sustituyen los lanzadores Docker/Zone locales. |
| [#1637](https://github.com/AAEmu/AAEmu/pull/1637) | Metadatos de versión 10.0.2.13 y copyright 2026. |
| [#1638](https://github.com/AAEmu/AAEmu/pull/1638) | Actualización de dependencias: OpenTelemetry 1.15.3, SQLitePCLRaw 2.1.13, MessagePack 2.5.301 y SSH.NET 2026.0.0; referencias necesarias de Hosting. |
| [#1642](https://github.com/AAEmu/AAEmu/pull/1642) | Mantiene actualizaciones de posición de unidades suspendidas en el aire, aun estando quietas. |
| [#1644](https://github.com/AAEmu/AAEmu/pull/1644) | Valida la posición inicial propuesta al invocar barcos antes de retirar la embarcación existente. |
| [#1646](https://github.com/AAEmu/AAEmu/pull/1646) | Nieve global y copia de features al construir la configuración inicial, preservando las demás opciones. |
| [#1668](https://github.com/AAEmu/AAEmu/pull/1668) | Carga y ejecuta la función de doodad que abre la interfaz de condiciones de construcción. |
| [#1655](https://github.com/AAEmu/AAEmu/pull/1655) | Límites de alcance de habilidades, selección de mascotas/barcos propios y caché del bando atacante en asedios; conserva las excepciones locales de Zone y plots. |
| `0ad3cf2ce` | README comunitario actualizado. |
| [#1667](https://github.com/AAEmu/AAEmu/pull/1667) | Carga de beneficios de gremio y sus modificadores desde AA10, con distinción del propietario del modificador. |
| [#1681](https://github.com/AAEmu/AAEmu/pull/1681) | Correo: comisiones, pago contra entrega, retención/devolución y reporte de spam, con pruebas de bordes. |
| [#1688](https://github.com/AAEmu/AAEmu/pull/1688) | Tipo de cartel de venta de vivienda obtenido del catálogo en lugar de una constante fija; no incluye el nuevo flujo de compraventa. |
| [#1690](https://github.com/AAEmu/AAEmu/pull/1690) | Instrumentos: catálogo de ítems/doodads, acceso, reproducción/pausa y reanudación de partituras. |

Commits independientes:

- `94ba1034d`: docs: drop provenance notes from the family/guild, chat and synthesis docs.
- `377891b21`: chore(duels): drop provenance comments from duel and team packets.
- `fa2f6b053`: chore(characters): drop provenance comments from character and mail code.
- `fb92e4ec6`: fix(packets): drop the extra byte from SCGamePointInitedPacket.

Los tres commits de limpieza solo modifican comentarios/documentación; la procedencia anterior sigue disponible en Git. `fb92e4ec6` elimina un byte sobrante de `SCGamePointInitedPacket`, que actualmente no tiene emisor de producción.

## Exclusiones comprobadas

- PR #1629, #1634, #1632 y #1633: sin cambios efectivos, ya presentes.
- PR #1651: dos pruebas de `LeadershipPeriod` requieren el evaluador de requisitos de #1656, que tiene conflictos. Esperaban detalle 853 y recibían 0. No se eliminaron ni debilitaron las pruebas; se aplazó el conjunto.
- PR #1693: tienda aleatoria con respuesta nativa incompleta y posibilidad de cobrar la actualización; pendiente según auditoría previa.
- PR #1698: fallo de persistencia ancestral deja una mutación parcial, reproducido en la revisión previa.
- `28dcfc05e`: falla compilación con CS0103 porque falta `QuestAcceptLevelRangeRules`, perteneciente a una serie de quests con conflictos.
- `bb8de1413`: depende de `ChatManager.SyncFactionChannel`, ausente en este fork; queda con la integración de chat.
- `98828fb41`: el comando de honor accede a `args[firstArg]` sin validar que quede un argumento después del nombre del objetivo; aplazado para corregir el caso incompleto.
- `596bcba1e`: el salón retira la pieza anterior antes de crear la nueva; si ese intercambio falla no queda incluido en el undo del llamador. Aplazado hasta cerrar el rollback de la ranura actual.
- `b91923860`: la devolución ante fallo repone propietario/listado/dinero, pero no revierte todos los efectos previos de retirar muebles/desvincular el mayordomo. Requiere revisión transaccional.
- Se volvieron a simular las 47 entregas inicialmente conflictivas contra el resultado final: 46 siguen con conflictos. #1663 pasa a aplicar limpiamente, pero conserva el defecto de rollback del salón descrito arriba y queda aplazada por revisión. No se forzó ninguna resolución.
- Commits individuales ya presentes: `76f6530c2` (autoequipo de mochila limitado a una unidad) y `1720c48f3` (retirada de configuración UCC sin uso).

## Validación

- Restore y build Release de la solución: correctos.
- Suite completa: **5.665 correctas, 0 fallidas, 0 omitidas**.
- Los intentos iniciales detectaron dependencias; se reconstruyó la selección sin ellas antes de promoverla.
- Seis fallos del primer worktree eran del localizador de fixtures, que exige que la carpeta se llame `AAEmu`. Se usó esa ruta para la validación definitiva.
- Otro fallo era la conversión CRLF de un manifiesto verificado por SHA-256. Se conservaron los bytes LF del principal y se añadió una regla específica `eol=lf` en `.gitattributes`; el valor esperado y las pruebas no se alteraron.
- Imagen Linux Release construida con el Dockerfile local de World. No se modifican SQL, compact, game_pak, datos/configuraciones montados ni los lanzadores locales.
- Comparación por blobs: se conservan exactamente `PlotNextEvent`, `Buff`, `BuffLifetimeRules`, `Units/Buffs`, `BuffTriggersHandler`, `CharacterAbilities`, `CSCreateCharacterPacket` y `X2EnterWorldResponsePacket`. `Skill.cs` cambia rangos/objetivos; no se sustituyen la temporización local de cadenas, GCD ni el ownership de plots.
- Esta validación no equivale a aceptación visual de todas las mecánicas en el cliente. El usuario mantiene el control de las Zones y de las pruebas de juego.

## Despliegue y rollback

Despliegue completado. Primero se arrancó la imagen contra `aaemu_cleancheck_20260923`, copia independiente de los datos, sin puertos publicados ni conexión al Login real. Alcanzó Game/Stream y `Server started` en 1 min 27 s. El contenedor de ensayo quedó detenido.

Después se detuvo únicamente Game, se obtuvo un dump consistente de `aaemu_game` (390.500 bytes) y se recreó Game con la imagen validada. Arranque real completo a las 22:55:15 de los logs, en 1 min 30 s; registro en Login confirmado, salud correcta y cero reinicios. Login y MySQL conservaron sus imágenes. Los únicos errores de carga son las cuatro definiciones 29–32 de Item Smelting, ya conocidas y fuera de alcance; no se activó esa función.

- Código desplegado: `ad9b954682dbf214d529bb33e9bf7f6558490dfb`.
- Imagen Game/World: `sha256:296b4eb9d53c082ad627226181b476c56240aca4b071bdc80ad7898f78f483e1`.
- Ambas copias de `AAEmu.Game.dll`: SHA-256 `39e39e4224ea99f9749e29ca3e5f63b2363e4be697fa2ac127b21b1e8cafc121`.
- Config montada: SHA-256 `1200be244daa9be8ae02adc4cf75dfae0ee4c7e58f66b5c0ef95a9391f8681bd`, idéntica al host y al respaldo.
- Se conservaron `192.168.1.94`, Game 1239, Stream 1250 y World 1240; no se publicó la Web API 1280.
- Catálogos nuevos cargados en el ensayo: 43 tipos de doodad, 254 instrumentos de ítem y 41 instrumentos de doodad. La tabla MySQL de miembros de raids de asedio ya existe; no hubo migraciones.
- Las Zones y el cliente no se operaron. **El usuario debe relanzar su perfil de Zones después del reinicio de Game.**

Rollback de código/runtime: existe la referencia `backup/rama_10-before-clean-upstream-20260923-f8cae2e71` y la imagen `aaemu10-game:before-clean-upstream-20260923`. Para volver al runtime anterior, etiquetar esa imagen como `aaemu-world:10.0.2.13-r575-local` y recrear solo Game con el mismo compose, `up -d --no-build --no-deps game`. No restaurar la base de datos por defecto: no cambió el esquema y restaurarla perdería progreso posterior. El dump `private-backup/aaemu_game-predeploy.sql` queda disponible para recuperación explícita si fuera necesaria.

## Evidencia

- Manifiesto versionado: `Docs/AA10UpstreamCleanIntegration20260923.json` (cada SHA de origen, commit aplicado, estado y motivo).
- Auditoría completa anterior: `Docs/AA10UpstreamReview20260923_es.md` y su inventario de commits.
- Artefactos locales: `E:\AAEmu\rama_10\artifacts\upstream-clean-20260923` (matrices, logs de selección, compilación, pruebas y arranque).
- Backups de configuración y SQL bajo `private-backup`, fuera de Git. Nunca publicar su contenido.
