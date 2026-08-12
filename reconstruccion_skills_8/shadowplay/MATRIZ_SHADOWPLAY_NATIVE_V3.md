# Matriz Shadowplay nativa V3

| Familia | IDs | Cierre V3 | Aceptación automatizada |
|---|---|---|---|
| Stealth | `10082` | Buff 8225, visibilidad, detección, ruptura y lifecycle | activación, ruptura por Leech y cancelación de Shadowsmite |
| Leech | `10104` | BuffSteal type 16, selección ponderada y transferencia de estado | robo elegible sin duplicación |
| Freerunner | `10189,39297,39298` | buff, cooldown y plot 3557 | base verde; variantes presentes y cerradas por grafo |
| Poisoned Weapons | `10481,40787,40788,40815` | cadenas 22266/24093/24235, tres relaciones server-required y cero `unit_reqs` AA8; Flame persiste 3 s y aplica `21999` a cada objetivo válido; `40815` es identidad aislada, no una arista ejecutable | base, Flame en dos objetivos, Wave y rifle verdes; ausencia de daño `40815` validada |
| Shadowsmite | `10496,36593,36594` | plots 3398/3409/3008, posición, stealth y Bubble nativo | base cancelación; Lightning hit y rango inválido |
| Overwhelm | `10648,36588,36589` | controller 10188 y plots ancestrales | desplazamiento e impacto base |
| Wallop | `12029` | plot 3400 | exactamente cuatro impactos calculados |
| Drop Back | `12049,36590,36591` | controller 10265 y cooldown único | desplazamiento base |
| Stalker's Mark | `12139,44288,44289` | marca, projectile/aggro, variantes y `EquipRanged` OR arco/rifle (`value1=0/2`) | buff 7659 validado con arco y rifle |
| Pin Down | `13344` | daño y buffs nativos | un cálculo de daño, sin replay |
| Rapid Strike | `18125,18126,18127` | continuidad C2S; type 41 GCD y type 48 descripción | un root por request, sin máquina servidor |
| Throw Dagger | `23594` | plot 3401, proyectil 16 y rebotes | cuatro daños, cero `SCSkillFired` artificial |
| Internas/login | `11418,19050,19052,19054` | dependencias ocultas | `show=0`, no expuestas en árbol |

## Pasivas

| Pasiva | Buff | `req_points` | `skill_points` |
|---:|---:|---:|---:|
| `260` | `7572` | 3 | 0 |
| `259` | `7570` | 4 | 0 |
| `6` | `483` | 5 | 0 |
| `55` | `1548` | 6 | 0 |
| `302` | `863` | 7 | 0 |
| `33` | `488` | 8 | 0 |

Todas las raíces Shadowplay tienen `native_combat_skill_status=enabled`; no
existe scaffold reservado ni relación ejecutable histórica fuera del cierre
V3.
