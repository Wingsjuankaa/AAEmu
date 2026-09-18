# Merge adaptado del padre exacto r575 — 2026-09-18

Autorizado por el usuario tras la revisión de los nuevos commits. Base del fork
`86b6d0b46284919ee8ff323cf05f00405e54a1c3`; padre absorbido
`30837660a75e4beef5a38f37bf95809edf055f53`. Backup Git:
`backup/rama_10-before-upstream-20260918-86b6d0b46`.

- [Decisiones, pruebas, migración y despliegue](../../Docs/AA10UpstreamIntegration20260918_es.md).
- [Descripción de los 139 commits](../../Docs/AA10UpstreamReview20260918_es.md).
- Manifiesto: `UPSTREAM_20260918.manifest.json` en este directorio.
- Artefactos privados fuera de Git:
  `E:\AAEmu\rama_10\artifacts\upstream-integration-20260918`.

Se preservan creación de personajes GM, vivienda transaccional, propiedad y
seguridad de objetos, nueve sockets, trabajo de ambos fondos, vida de plots,
propulsión de barcos, pesca y snapshot inicial de buffs. La implementación
combina mejoras compatibles del padre; no hace checkout masivo ours/theirs.

No se incorpora la entrega no atómica de premios de rankings ni las hipótesis
de temporización AoE y movimiento Dash/Wandering/Floating. Segunda contraseña,
protección sensible, Butler e ItemSmelting conservan su estado desactivado.
Los reportes de bugs existentes no se cierran sin reproducirlos en cliente.

Validación: baseline 4638 pruebas; candidato 5414, todas correctas y ninguna
omitida. Migración aditiva repetible probada en clon y aplicada con Game parado,
conservando exactamente los datos previos. Se verifica arranque, redes y mounts
reales. Cliente y SQLite autoritativa sin modificaciones.

Game/World actualizado; Login conserva su imagen. No se operaron procesos
Zone. El usuario debe relanzar su perfil desde Control Center para pruebas
in-game; la creación de personajes puede probarse sin Zones, tras reconectar.
No se ha hecho push. La aceptación visual de creación, vivienda y combate
queda pendiente; las pruebas automáticas no equivalen a esa aceptación.
