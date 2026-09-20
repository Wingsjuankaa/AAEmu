# Panel GM — 20/09/2026

Target `rama_10`, base `2371e385db4047835e478944ed861a9e1c42b99f`.
Padre inspeccionado: `upstream/client_version/zone-10.0.2_r575`,
`7851f67cc0c46fb76b4fafc3414b6754685d96f2`. No se cambia de rama ni se integra upstream.

## Entrega

Catálogo dinámico de comandos autorizados, categorías, búsqueda de nombres/alias/
descripciones, favoritos temporales, ayuda paginada con subcomandos, parámetros,
ejemplos y ejecución por botones. Cuatro accesos rápidos: sin CD, CD normal,
curar objetivo y dummy. Icono propio con transparencia real en la fila HUD.

Manual y límites: [AA10GmPanel_es.md](../../Docs/AA10GmPanel_es.md).
Contrato del cliente: [Aa10GmPanel.contracts.json](../../Scripts/Aa10GmPanel.contracts.json).

El servidor vuelve a comprobar permisos, conserva el dispatcher original y requiere
confirmación para acciones amplias/destructivas. No se ejecutaron comandos mutables
en personajes durante esta tarea. El usuario retomó las pruebas del cliente:
**aceptación visual/jugable pendiente del usuario**. Se conserva este checkpoint
commiteado conforme a su instrucción de dejar el worktree limpio; no se declara
aceptación retail ni reparación de todas las mecánicas que estos comandos invocan.

## Validación automática

- Restore y build Release correctos, con advertencias existentes.
- 5.522 pruebas de servidor correctas, sin fallos ni omitidas.
- Cinco pruebas Lua/builder: autorización/correlación, búsqueda/alias/categorías,
  favoritos, ayuda, dispatch, confirmaciones, timeout, fragmentos perdidos,
  idempotencia del builder y rechazo de ALB desconocido; todas correctas.
- PNG RGBA con alpha 0–255; DDS BGRA8 64×64 con siete mips. Los píxeles RGBA
  de preview y DDS reabierto coinciden. Estados de botón comprobados en harness.
- Ensayo disperso con índice completo: ambos ALB, DDS nuevo, sentinelas y rollback
  exacto correctos. Los offsets de payloads existentes permanecen iguales.
- Control Center: typecheck, 69 pruebas correctas, una omitida y build web/electron
  correctos. Hash del paquete informativo; no existe una allowlist que ampliar.

La prueba de metadata detectó el nombre concreto `AddKit` (archivo `Kit.cs`);
se corrigió el catálogo antes del build y despliegue. La revisión de `/heal`
confirmó que su implementación usa objetivo/nombre, por lo que el acceso dice
Curar y usa `/heal`, sin asumir que `self` cure al emisor.

## Runtime

Game desplegado en imagen
`d83469725007e3b9f15b61c3adc8604d6ba10e6c974008c0841ba786611e0c24`.
DLL Linux en `/app` y `/app/game`:
`414887ba4cdc06d7253424e0b47443554ccf301af0b0d57034a9535cc38bc990`.
Arranque `GameService Server started` a las **18:40:48 UTC**;
GameNetwork y StreamNetwork iniciados. Rollback de imagen:
`aaemu-world:rollback-pre-gm-panel-20260920` (imagen previa `b5abd428...`).
No se iniciaron, detuvieron ni relanzaron Zones ni cliente.

Cliente principal: `ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
Paquete esperado después: `FC386DB43C7C17EB7E5A59348877E14BF2CD1DE58BC54830EEB2C81359028673`;
92.412.664.320 bytes (+22.528). Preserva alpha, reportes, crafting, mapa e icono
de logro. Los detalles de aplicación/segunda ejecución se guardan en el manifiesto
de entrega adjunto y los respaldos por entrada.

Evidencias fuera de Git: `E:/AAEmu/rama_10/artifacts/gm-panel-20260920`.

Instalación confirmada: manifest 183901-277477Z en estado applied.
Segunda ejecución 184446-578982Z: already_patched, mismo SHA completo.
Identidades, sentinelas y respaldo: GM_PANEL_20260920.manifest.json.
