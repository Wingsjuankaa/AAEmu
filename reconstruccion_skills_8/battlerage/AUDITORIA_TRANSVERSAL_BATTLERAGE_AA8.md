# Auditoría transversal Battlerage AA8

Generado únicamente desde la clausura nativa AA8 y el backend actual. No consulta ni reutiliza gameplay 3.0.

## Resultado

- Filas Battlerage auditadas: **42**.
- Filas visibles: **15**.
- Animaciones referenciadas ausentes: `[]`.
- Controladores referenciados ausentes: `[604]`.
- Proyectiles referenciados ausentes: `[]`.

Los efectos `Anim`, `FxGroup`, `FxGroupAnim`, `Projectile` y `ProjectileAnim` de un plot son instrucciones de presentación que ejecuta el cliente al recibir `SCPlotEvent`; que su clase servidor sea un no-op no significa que debamos inventar el FX en backend.

## Matriz

| Skill | Visible | Ruta | Animaciones directas | Plot | Presentación del plot | Movimiento/controlador |
|---:|:---:|---|---|---:|---|---|
| `10377` 가벼운 손놀림 | sí | direct_skill_packet | 18 | — | — | — |
| `10385` 반달 베기(폐기 예정) | no | direct_skill_packet | 26, 27 | — | — | — |
| `10455` 폭주 | sí | direct_skill_packet | 18 | — | — | — |
| `10644` 대지 가르기 | sí | direct_skill_packet, plot_event_graph | 412, 413, 414 | 649 | Anim, FxGroup, FxGroupAnim, Projectile | — |
| `11854` 올려치기(폐기 예정) | no | direct_skill_packet, plot_event_graph, skill_controller | 21, 22 | 270 | Anim, FxGroupAnim | controller 604 |
| `11918` 돌격 | sí | direct_skill_packet, plot_event_graph, skill_controller | — | 624 | FxGroup, FxGroupAnim | Detach; controller 6779,8229 |
| `12026` 결정타 | sí | direct_skill_packet | 132, 136 | — | — | — |
| `12028` 돌격 호출기술 | no | direct_skill_packet, skill_controller | — | — | — | controller 5829 |
| `12034` 속박 해제 | sí | direct_skill_packet | 18 | — | — | — |
| `12786` 격투_(로그인스테이지)_회오리베기 | no | direct_skill_packet | 287, 302 | — | — | — |
| `12787` 격투_(로그인스테이지)_올려치기 | no | direct_skill_packet | 21, 22 | — | — | — |
| `12788` 격투_(로그인스테이지)_결정타 | no | direct_skill_packet | 132, 136 | — | — | — |
| `13282` Вихрь ударов | sí | plot_event_graph | — | 133 | Anim, FxGroup, FxGroupAnim | KnockBack |
| `13315` 폭풍 가르기 | sí | plot_event_graph, skill_controller | — | 17 | FxGroup, FxGroupAnim | Detach; controller 2278,2279 |
| `16185` 물리 관통 | no | sin ruta | — | — | — | — |
| `18131` 3단 베기 | no | direct_skill_packet, plot_event_graph | 298, 301, 506 | 2541 | Anim, FxGroup, FxGroupAnim | — |
| `18132` 3단 베기 | sí | direct_skill_packet | 296, 299, 504 | — | — | — |
| `18134` 3단 베기 | no | direct_skill_packet | 297, 300, 505 | — | — | — |
| `18308` 포효 | sí | direct_skill_packet | 18 | — | — | — |
| `18757` 올로의 망치 | sí | direct_skill_packet, plot_event_graph, skill_controller | — | 440 | Anim, FxGroupAnim, ProjectileAnim | controller 11306 |
| `23587` 적진으로 | sí | direct_skill_packet, skill_controller | — | — | — | controller 10258 |
| `32040` 회오리 베기 | no | direct_skill_packet, plot_event_graph | — | 2230 | Anim, FxGroup, FxGroupAnim | KnockBack |
| `32049` 회오리 베기 | no | direct_skill_packet, plot_event_graph | — | 2231 | Anim, FxGroup, FxGroupAnim | KnockBack |
| `34119` 분노 | sí | direct_skill_packet | 18 | — | — | — |
| `34120` 심연의 칼날 | sí | direct_skill_packet, plot_event_graph | — | 8000065 | — | — |
| `34124` 악마의 검 | sí | direct_skill_packet | 847 | — | — | — |
| `36401` 3단 베기: 번개 | no | direct_skill_packet | 296, 299, 504 | — | — | — |
| `36402` <ref:104246> | no | direct_skill_packet | 297, 300, 505 | — | — | — |
| `36403` <ref:104246> | no | direct_skill_packet | 909, 912 | — | — | — |
| `36404` 3단 베기: 지진 | no | direct_skill_packet, plot_event_graph | 296, 299, 504 | 2855 | Anim, FxGroup, FxGroupAnim, Projectile | — |
| `36405` <ref:104248> | no | direct_skill_packet, plot_event_graph | 297, 300, 505 | 2856 | Anim, FxGroup, FxGroupAnim, Projectile | — |
| `36406` <ref:104248> | no | direct_skill_packet, plot_event_graph | 298, 301, 506 | 2857 | Anim, FxGroup, FxGroupAnim, Projectile | — |
| `36446` 결정타: 파도 | no | direct_skill_packet, plot_event_graph | 900, 901 | 2903 | Anim, FxGroupAnim | — |
| `36447` 결정타: 돌풍 | no | direct_skill_packet, plot_event_graph | 907, 908 | 2921 | Anim, FxGroupAnim | — |
| `36448` 폭풍 가르기: 번개 | no | plot_event_graph, skill_controller | — | 2922 | Anim, FxGroup, FxGroupAnim | Detach; controller 11024,11025,11026,11067,11068 |
| `36449` 폭풍 가르기: 생명 | no | plot_event_graph, skill_controller | — | 2923 | FxGroup, FxGroupAnim | Detach; controller 11027,11028 |
| `39661` 적진으로: 돌풍 | no | direct_skill_packet, skill_controller | — | — | — | controller 11525 |
| `39662` 적진으로: 바위 | no | direct_skill_packet, skill_controller | — | — | — | controller 11526 |
| `41217` 대지 가르기: 지진 | no | direct_skill_packet, plot_event_graph | 412, 413, 414 | 4044 | Anim, FxGroup, FxGroupAnim, Projectile | — |
| `41218` 대지 가르기: 안개 | no | direct_skill_packet, plot_event_graph | 412, 413, 414 | 4045 | Anim, FxGroup, FxGroupAnim, Projectile | — |
| `43188` 폭주: 불꽃 | no | direct_skill_packet | 18 | — | — | — |
| `43189` 폭주: 파도 | no | direct_skill_packet | 18 | — | — | — |

## Primitivas servidor pendientes

| Tipo | Clase | Estado |
|---:|---|---|
| `13` | `KnockBack` | `stub` |
| `39` | `ManaCost` | `partial` |
| `40` | `Cooldown` | `partial` |
| `41` | `GlobalCooldown` | `partial` |
| `52` | `StopManaRegen` | `partial` |
| `59` | `CancelStealth` | `stub` |
| `61` | `CancelOngoingBuff` | `stub` |
| `63` | `CombatText` | `stub` |
| `66` | `AutoAttack` | `stub` |
| `67` | `CombatDice` | `stub` |

## Correcciones transversales incluidas

- Selección de `fire_anim_id`, `twohand_fire_anim_id` o `dual_wield_fire_anim_id` según el arma realmente equipada.
- Cálculo de `CombatSyncTime` con la misma variante de animación enviada al cliente.
- Serialización de la lista real y sin duplicados de objetivos AoE en `SCPlotEvent`.
- Conservación del grafo de plot y de sus FX nativos; no se crean animaciones ni desplazamientos artificiales.
