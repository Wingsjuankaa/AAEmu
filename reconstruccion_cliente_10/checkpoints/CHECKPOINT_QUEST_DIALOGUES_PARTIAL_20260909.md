# Diálogos de misión — corte aplicado, familia pendiente

Por petición del usuario se cierra el avance tras el lote 037 y se priorizan
los nombres y cargos de NPC. No se declara terminada la familia de diálogos.

- Alcance original: 26.920 identidades.
- Candidatos examinados directamente: 3.700 en 37 lotes.
- Nuevas aprobaciones: 3.547; aprobaciones previas conservadas: 9.
- TEST excluidos y documentados: 150.
- Fuentes aplazadas: 3.
- Candidatos sin examinar: 23.211, conservados sin cambios.
- Correcciones de cierre verificadas: 3.

Aplicado el 2026-09-09T22:43:38.628334+00:00, parche `1211cf946c31433e8b4637bdbf09777c`.
Se verificaron los 3.556 textos aprobados del corte en el cliente español
principal; 3.530 produjeron cambios efectivos. Pendientes globales: 0.
La comprobación visual dentro del juego queda para el usuario.

El cierre comprueba texto, estado y fuente de los revisados, y conserva la
revisión, fuente y texto de los no examinados y de las aprobaciones previas.
La cola fija, los recibos y las tres correcciones oficiales quedan en
`work/quest-dialogues-20260909` para reanudar sin repetir el trabajo.

[Textos del corte](texts.csv). [Excepciones](exceptions.csv).
[Auditoría](summary.json). [Verificación de instalación](application-verification.json).
[Inventario y prioridad de NPC](../npc-inventory-20260909/README.md).

Decisión: `decisions/0019-npc-priority-dialogue-cutoff-20260909.md`.

Reanudar diálogos únicamente por indicación del usuario; el objetivo anterior de completar toda la familia quedó sustituido por este corte. Próxima prioridad: NPC interlocutores, conservando nombres propios.

Verificación del panel: typecheck correcto; 65 pruebas aprobadas, 1 omitida, 20 archivos; build electron-vite correcto. Fecha 2026-09-09.

Datos del parche para reproducción y rollback:

```json
{
  "id": "1211cf946c31433e8b4637bdbf09777c",
  "before": {
    "pak_sha256": "500F85287EF0E1CE64E336F504D38EFCA794E426BE6C57BFB9FB632B3E8794C3",
    "pak_size": 84894211584,
    "compact_sha256": "19DFF300B838484A1465DF861B199B37FBA7CD7FBF2AB63825270850C528B842",
    "patch": "6fad08b683204f4ba1e46529c2ef5064",
    "resource_probes": {
      "game/ui/map/map_resources/w_white_forest/line.dds": "5E7B547AA9AF46B38B8633A4853CEF3F38F7652CD72A8D6B7F255A90F3C04B36",
      "game/ui/icon/icon_item_shotgun_0024.dds": "A162E6CAD29E95453228493EBAD54F71E6534C49545E4266A336117B1D18F0AC",
      "game/scriptsbin64/x2ui/crafting/crafting_view.alb": "067B69FA6664CACC3D0239F31405A743D958C0BD7811D6B604F8AA93B35756F7",
      "game/scriptsbin64/x2ui/components/tooltip/tooltip.alb": "F688859D8FC8A9492A8C993B7C7F777D1D477493FF655343DFE7AF082D2B49A9",
      "game/scriptsbin64/x2ui/baselib/func_prefix_size.alb": "9812B0C2791B416FD8382A1DEF91391BEE0ECFD9089D72BAE8AA002CA4041E56",
      "game/scriptsbin64/x2ui/baselib/baselib.alb": "1A75DE90888AB4998EE583722EF07157CAD7AC3E0C6E7E469687B9D7AF219265",
      "game/scriptsbin64/x2ui/components/tooltip/tooltip_view.alb": "FDC03747AC35C14BF99A2E7000EB7ACF9ED8307DFB2E2BA049538410E68638A7",
      "game/scriptsbin64/x2ui/option/option.alb": "88E4F298EB4BECD4650E8D434CE011475331217ABC9301D9368FA786CA6566EC",
      "game/scriptsbin64/x2ui/skill/locale/layout_set.alb": "4EA9924FF43DE38095531819C37BCE658878BB590721F8E76AC484B3FE15AC78",
      "game/scriptsbin64/x2ui/store/common.alb": "D932A2E84BF386E10FDCE476D5F171B53F0BA7C0FE82AE3C47DD4FF0CB775BF1",
      "game/scriptsbin64/x2ui/questcontext/locale/ko.alb": "808D0F309E649298BA6194E7C9833D240CDE609B45368AD372418C522D60A7EC"
    },
    "external_patches": [
      {
        "patch_id": "aa10-spanish-ui-layout-v2-r575",
        "manifest_sha256": "B3CD83C909E00D966C6AF92CCF3CC65E6AF9E5818606158DEB58482A1D382498",
        "pak_sha256": "F3D915B210C29521FD1581E8042B1E7132E432D17D3010113D3AECF98577672F"
      }
    ]
  },
  "after": {
    "changed": 3530,
    "selected": 3530,
    "sha256": "FD931C4F8B971EED6B27E616045BE629CBD6D51FEE722A7AE2BF1A7630D90C67",
    "size": 469516288
  },
  "backup": "E:\\AAEmu\\rama_10\\backups\\client-patches\\contextual-1211cf946c31433e8b4637bdbf09777c",
  "pak_before": null,
  "pak_after": null,
  "verification": {
    "tables_verified": 1003,
    "identities_verified": 3530
  },
  "applied_at": "2026-09-09T22:43:38.628334+00:00"
}
```
