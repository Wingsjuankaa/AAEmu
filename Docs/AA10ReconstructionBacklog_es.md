# Mapa maestro de reconstrucción AA10 r575

Orden operativo actual: [AA10ReconstructionRoadmap_es.md](AA10ReconstructionRoadmap_es.md).
Primera vertical: [AA10ItemLockReconstruction_es.md](AA10ItemLockReconstruction_es.md).

Fecha de corte: 2026-08-31
Cliente: ArcheAge Returns 10.0.2.13 r575
Servidor: `rama_10`, `39d0489dc0a8c21f81df03861ac89e6f7388d5d1`
Padre nativo exacto: `upstream/client_version/zone-10.0.2_r575`, `3cc280b14d7da0d874121d14ebbf409f5e032d1c`
SQLite completo: 1.374 tablas, `quick_check=ok`, SHA-256 `87531F...3702F`

Este documento responde cuatro preguntas distintas:

1. qué sistemas están reconstruidos y aceptados;
2. qué superficies están visibles pero incompletas;
3. qué funciones existen en el cliente o en sus datos y hoy están apagadas;
4. qué deuda concreta existe en el backend y en qué orden conviene cerrarla.

No se considera una tabla, una clase de paquete o un botón como prueba de una mecánica. Una mecánica sólo está cerrada cuando están demostrados su grafo de datos, autoridad del servidor, persistencia, protocolo, respuesta negativa, reingreso y comportamiento visible en cliente.

## Resumen ejecutivo

- El port ya cerró una porción importante de lo específico de AA10: Gear Upgrade/Hiram, Lunagem, Temper, Replace Stat, flujo principal de Bless Uthstin, asistencia, tienda de vocación, conteos de inventario, Summon Mate, partes sustanciales de Housing, Crafting, quests y Auroria. Son reconstrucciones nuevas del fork, no deuda heredada sin tocar.
- El mayor riesgo actual no son los 904 `TODO` por sí solos: son las funciones **encendidas pero parciales**. Item Lock ya tiene núcleo retail aceptado y Loot Gacha está implementado para gate retail; ahora destacan Event Center/Palos, las misiones de ArchePass y cierres dinámicos de Housing/Crafting/Quest.
- El runtime expone 45 de 136 bits únicos conocidos y deja 91 apagados. No todos los apagados deben encenderse: 22 son bits nativos aún sin contrato, varios son bloqueos administrativos o de plataforma, y otros abren sistemas completos que el servidor todavía no autoriza.
- Hay 904 marcadores de deuda en 699 archivos. La concentración más alta está en protocolo (426 marcadores C2G/G2C), efectos/habilidades (199 entre `SpecialEffect` y `Skill`) y managers/modelos de juego.
- De 477 clases C2G, 401 están registradas. Hay 76 archivos no registrados; descontando `CSOffsets.cs`, quedan 75 candidatos reales. Además, 186 C2G contienen el marcador explícito “nothing acts”; 116 de esos ya están registrados y por ello constituyen superficies especialmente engañosas.
- De 682 clases G2C, 203 declaran “nothing constructs”. No significa que todas sean necesarias, pero sí que ningún cierre de dominio puede basarse sólo en que existe la clase.
- De 149 acciones de efecto especial, 85 tienen un cuerpo explícito `// TODO ...`. Esto afecta el núcleo transversal de combate, movilidad, autoridad, música, portales, proyectiles, mascotas, vehículos, asedios y progresión.
- La base completa contiene datos abundantes para sistemas ausentes: Butler/Farmhand, Craft Orders, Heroes, Siege, Expeditions, Residents, Induns, Gacha, Item Secure, Rankings, Surveys, schedules y ArchePass. Esa presencia sube su reconstruibilidad, pero no demuestra que el flujo servidor-cliente exista.

## Vocabulario de estado y novedad

Estados usados:

- **ACEPTADO**: cierre estático y dinámico con autoridad, persistencia y regresión verificadas.
- **ESTÁTICO CERRADO / DINÁMICO PENDIENTE**: catálogo, protocolo o implementación presentes; falta prueba retail o ciclo completo.
- **PARCIAL EXPUESTO**: el cliente puede entrar o enviar solicitudes, pero la transacción no termina de forma autoritativa.
- **APAGADO RECONSTRUIBLE**: datos y superficies existen, pero el bit debe seguir apagado hasta completar el vertical.
- **BLOQUEADO POR EVIDENCIA**: faltan filas, consumidor, productor o contrato nativo; no se deben inventar valores.
- **APAGADO INTENCIONAL**: bit de bloqueo, entorno, proveedor o política; “activar” no equivale a recuperar contenido.
- **DESCONOCIDO NATIVO**: el cliente C++ consume el bit, pero no está cerrado su contrato.

Eje de novedad:

- **LEGACY**: mecánica fundamental del ArcheAge original.
- **POST-LANZAMIENTO**: añadida por actualizaciones históricas, pero ya parte de la experiencia AA10.
- **NUEVA EN AA10/RETURNS**: superficie o contrato de la rama 10 que no debe copiarse ciegamente desde AA8.
- **LIVE-OPS/REGIONAL**: depende de campañas, calendarios, webs o políticas de publicación.
- **INFRAESTRUCTURA**: seguridad, plataforma, monetización o administración, no contenido jugable en sí.

## Clasificación por dominio

| Dominio o mecánica | Estado actual | Qué falta para cierre | Novedad / prioridad |
|---|---|---|---|
| Combate base, skills, buffs y proc | Parcial transversal | Cerrar 85 SpecialEffects vacíos; proc side, daño de arma/NPC/asedio, bonus por buffs, chances, recursos y cargas; regresión PvE/PvP | LEGACY, P0 porque bloquea todo lo demás |
| Proyectiles, targeting, channeling y controladores | Parcial | `Projectile`, `RetrieveProjectile`, `ClearProjectile`, `Track`, `LoseTargetingTheTarget`, `StopChanneling`, animaciones y autoridad de movimiento | LEGACY, P0 |
| Resurrección, retorno y teleports | Parcial | `Resurrection`, `Return`, `TeleportToUnit`, `TeleportToSiegeHq`, tipos adicionales de libro/portal, cooldowns y errores retail | LEGACY, P0/P1 |
| Quests | Cobertura estática cerrada; dinámico no exhaustivo | El manifiesto v8 resuelve 43.737/43.737 referencias habilitadas y Phase 4 1.397/1.397; faltan recorridos retail de capítulos, repetición, persistencia, actores y portales restantes | LEGACY + contenido AA10, P1 |
| Crafting general | Estático muy avanzado; dinámico parcial | 7.320/9.949 recetas promovidas; 2.629 bloqueadas. Cerrar gates dinámicos de recetas sin materiales, ArchePaper, consumers faltantes y separar eventos/regionales/unused | LEGACY/LIVE-OPS, P1 |
| Gear Upgrade / Hiram synthesis & awakening | ACEPTADO | Mantener regresión y ampliar matriz sólo con evidencia nativa | POST-LANZAMIENTO, reconstrucción AA10 ya cerrada |
| Replace Stat / reroll de síntesis | ACEPTADO | Mantener pruebas de objeto tipo 9 y respuestas 0xCE | POST-LANZAMIENTO, reconstrucción AA10 ya cerrada |
| Lunagem instalar/remover/extraer | ACEPTADO | Regresión por slots y costes; no reabrir por documentación histórica vieja | POST-LANZAMIENTO, reconstrucción AA10 ya cerrada |
| Temper / Refurbishment | Flujo principal aceptado; borde parcial | Resolver resultado destructivo de Temper que aún aparece como TODO y probar matriz de catalizadores | POST-LANZAMIENTO, P1 |
| Erenor | Parcial avanzado | Bow progression aceptado; completar matriz de slots. Mantener T3→T4 de accesorios bloqueado mientras no exista ruta nativa | POST-LANZAMIENTO, P1 |
| Bless Uthstin | Principal aceptado; subfunciones parciales | Reset, extensión de tope, copiar/expandir páginas y aceptación dinámica de reemplazo; hoy fallan explícitamente sin mutar | POST-LANZAMIENTO, P1 |
| Item Smelting | Estático cerrado, bit apagado | Mantener recetas 29–32 bloqueadas por outputs ausentes; cerrar gate dinámico de receta 5 y confirmar ruta real antes de poner bit 178 en `true` | NUEVA EN AA10, P1 |
| Item Lock / Secure | NÚCLEO RETAIL ACEPTADO | Lock visible, relog y venta bloqueada confirmados; conservar unlock temporizado y bulk como regresión ampliada | POST-LANZAMIENTO, reconstrucción AA10 cerrada en su núcleo |
| Loot Gacha | IMPLEMENTADO; RETAIL PENDIENTE | Tipo 16, lote 1-10, catálogo 11/24/30, consume/reward, pity persistente y respuestas 0x2E2-0x2E4; falta aceptación cliente | POST-LANZAMIENTO/LIVE-OPS, P0 hasta gate retail |
| Item counts / stack-limit UX | Conteos aceptados; cambio de stack en trabajo local | Conservar cambios locales actuales y validar el ciclo del parche game_pak sin mezclarlo con este backlog | NUEVA EN AA10, fuera del alcance de esta auditoría |
| Housing placement H1 | ACEPTADO | Regresión de relog y colisiones | LEGACY, cerrado |
| Housing sale/permissions H2 | Parcial avanzado | Gate retail cruzado entre cuentas para Private/Public y visibilidad de venta | LEGACY, P1 |
| Housing tax/prepay/dates H3 | ACEPTADO | Mantener Stone Rose, fiscalidad y formato de fechas | LEGACY, cerrado |
| Housing construction H4/H5/H5-B | Estático avanzado; retail parcial | 3.990 rutas ejecutables y 656 bloqueadas en H5-B; completar ola pendiente, territorial/consumers, ciclo de persistencia y gates retail | LEGACY + catálogos AA10, P1 |
| Housing rebuilding | Núcleo aceptado, bloqueos explícitos | 223 definiciones/177 packs; 219 ejecutables y 4 bloqueadas; reconciliar checkpoint antiguo con aceptación H5-B y mantener fail-closed | POST-LANZAMIENTO, P1 |
| Housing decoration recovery | ACEPTADO | Regresión owner/recover; aún faltan demoliciones complejas, correo/cofres y full-kit | LEGACY/POST-LANZAMIENTO, P2 |
| Tradepacks, specialties y commerce | Activo y en reconstrucción avanzada | No pisar cambios locales actuales; cerrar eventos, ratios, caducidad/turn-in, marítimo/cargo y matriz regional | LEGACY, P1 |
| Community Centers y residents | Catálogo presente; backend parcial | Ciclos de desarrollo, service points, contribuciones, rewards, tradepacks comunitarios y permisos de residente | POST-LANZAMIENTO, P2 |
| Craft Orders / Requests | APAGADO RECONSTRUIBLE | Cupones (4 filas), request station, escrow de materiales/pago, aceptación, expiración, mail y recuperación idempotente | POST-LANZAMIENTO, P2; gran sinergia con Community Center |
| Summon Mate | ACEPTADO | 478/552 promovidos; conservar 74 bloqueados por datos retail ausentes | LEGACY + catálogo AA10, cerrado |
| Summon Slave / vehículos / barcos | Parcial | Grafo item→template→components, equipo/reparación, destrucción/respawn, simulación de zona y física; `DestroyAndSpawnSlave`, `EscapeMySlave`, `HealSlave` vacíos | LEGACY, P1/P2 |
| Navegación, combate naval y pesca | Parcial/no cuantificado como vertical | Radar de shipyards, autoridad de barcos, pesca deportiva, capturas/turn-in, física y eventos marítimos | LEGACY, P2; la wiki confirma que es eje central, no accesorio |
| Instances / Indun | Parcial | Botón de salida implementado con validación cliente pendiente; portales, límites diarios, eventos/acciones (263/357 filas) y ciclo entrar/salir/reingresar | LEGACY/POST-LANZAMIENTO, P1 |
| Auroria / Western Hiram | Map + Western Hiram aceptados | Validar cada región restante, teleports, quests, NPC/doodad y dependencias; “Auroria habilitada” no prueba todas sus zonas | POST-LANZAMIENTO, P1 |
| Family | Núcleo upstream parcial | Niveles (3), buffs, misiones, ownership, cross-faction y property access; varios paquetes existen pero requieren E2E | LEGACY/POST-LANZAMIENTO, P2 |
| Expedition/Guild base | Parcial | Niveles (100.000 filas), buffs (14), recruiting, authority, summon, rename-by-item, war/dominion y persistencia | LEGACY/POST-LANZAMIENTO, P2 |
| Hero system | APAGADO RECONSTRUIBLE | Elección/candidatura, schedules (25), 120 registros, leadership, rewards, statue/skills, bonus y season rollover | POST-LANZAMIENTO, P3 por dependencia política/PvP |
| Siege, Dominion, castles y territory | Parcial | Tickets, plan/auction, HQ teleport, guard towers, taxes in kind, declare independence, schedules, victory/ownership y recovery | LEGACY/POST-LANZAMIENTO, P3 después de combate y guild |
| Crime, prison y jury | Parcial | Evidence lifecycle, fases, offline actors, Z/floor, sentencia, audiencia, appeals/cancel y recompensas; paquetes de trial existen pero no equivalen a cierre | LEGACY, P2/P3 |
| Rankings, Elo y competition | Ranking base encendido; sistemas parciales | Rewards (140), rollover, Elo, arenas/faction competitions, anti-abuse y temporalidad | POST-LANZAMIENTO, P2/P3 |
| Butler / Farmhand | APAGADO RECONSTRUIBLE | Aunque hay 1 butler, 41 niveles, 159 harvests y 163 specialty trades, sólo existen paquetes/scalar; faltan estado, nivel, labor, órdenes, vivienda, timers y recovery | POST-LANZAMIENTO, P3 |
| ArchePass | Core 4C reconstruido; missions apagadas | Catálogo/pass/tiers, compra, start/drop, expiry, points/rewards y persistencia están; faltan misiones de cuenta, reroll, contadores/configs 277–280 y aceptación retail | POST-LANZAMIENTO/LIVE-OPS, P0/P1 |
| Attendance | ACEPTADO | Campaña mensual, ledger por cuenta y una claim/día UTC; mantener calendario y pruebas de rollover | LIVE-OPS, cerrado |
| Event Center: info/schedule/today | Expuesto con madurez desigual | Schedule tiene catálogo; Today Assignment tiene manager pendiente de validación manual; Event Info/web content exige fuente/configuración y respuestas vacías seguras | LIVE-OPS, P0 por exposición |
| Palos shop | Expuesto; backend no demostrado | Cerrar catálogo, moneda, compra, límites, refresh y entrega o apagar hasta disponer de vertical | LIVE-OPS/REGIONAL, P0 |
| Survey forms | APAGADO RECONSTRUIBLE | 6 forms/26 questions; eligibility, respuestas únicas, rewards, privacidad y cierre temporal | LIVE-OPS, P3 |
| Auction / market price / partial buy | Subasta base parcial; bits avanzados apagados | Autoridad de post, buffs, partial buy, price history, mail/settlement, expiración y duplicación | LEGACY/POST-LANZAMIENTO, P1/P2 |
| Mail | Parcial | Expired return, Mia, attachments/fees, recovery e idempotencia; report spam separado | LEGACY, P1 |
| UCC, appearance, beautyshop y music | Parcial/apagado | Upload/moderation, housing UCC, cosplay slot drift, beautyshop/gender/tail, notas/música, storage y playback; varios efectos están vacíos | POST-LANZAMIENTO, P3 |
| Factions, nations y migration | Parcial | Player nation cleanup, independence, migration limits, diplomacy, leadership y chat/faction competition | LEGACY/POST-LANZAMIENTO, P3 |
| Bot/spam/bad-user reporting | Mayormente apagado y stub | Evidence, rate limits, case lifecycle, penalties, privacy/audit; no activar botones sin backend operativo | INFRAESTRUCTURA, P2 de seguridad |
| Return Account y páginas de lista | Contrato movido/parcial | `returnAccount` ya no es fset en AA10; validar system-feature table, rewards/eligibility y paginación de personajes | POST-LANZAMIENTO, P2 |

## Mecánicas confirmadas por fuentes históricas y wiki

El contraste externo evita que el inventario quede sesgado hacia lo que ya tiene una clase C#:

- El resumen histórico de [ArcheAge](https://en.wikipedia.org/wiki/ArcheAge) identifica crafting, housing/farming, trade routes, combate naval, PvP/crimen/jurado y castle sieges como pilares. Por eso navegación/pesca, crime/jury y siege no pueden clasificarse como “extras” sólo porque sus verticales estén incompletos.
- [Family](https://archeage.fandom.com/wiki/Family) confirma que Family es paralelo a guild, admite composición cross-faction y afecta acceso a propiedades. Los handlers sociales existentes no cubren por sí solos ese contrato.
- [Community Center](https://archeage.fandom.com/wiki/Community_Center) documenta ciclos de resident contribution/rewards, tradepacks comunitarios y Crafting Request Stations. Coincide con las tablas `resident_*` y `craft_order_*` del cliente, y justifica tratarlos como un único programa de reconstrucción económica.
- [Hiram Equipment](https://archeage.fandom.com/wiki/Hiram_Equipment) y [Enhancements](https://archeage.fandom.com/wiki/Enhancements) sitúan Hiram, awakening, synthesis, Lunagem, Temper y otras mejoras como sistemas post-lanzamiento. En el fork no son “nuevos diseños”: son mecánicas retail reconstruidas para AA10.
- [Trade Packages](https://archeage.fandom.com/wiki/Trade_Packages), [Commerce](https://archeage.fandom.com/wiki/Commerce), [Crafting](https://archeage.fandom.com/wiki/Crafting) y [Labor](https://archeage.fandom.com/wiki/Labor) muestran que trade, crafting, labor y propiedad forman una economía acoplada. Deben probarse juntos para impedir exploits de coste, duplicación y profit share.
- El historial de [Updates](https://archeage.fandom.com/wiki/Updates?cookieSetup=true) ubica Hero, guild levels/recruitment/dominion y upgrades de housing como añadidos posteriores. Sirve para separar mecánica histórica de reconstrucción reciente del fork.
- La guía histórica de [Farmhand/Butler](https://archeage.ru/news/315275.html) confirma la dependencia con vivienda, nivel, labor y órdenes temporizadas. Las 364 filas de catálogo encontradas no bastan para encender el bit 47.
- [Crime and Punishment](https://archeage-archive.fandom.com/wiki/Crime_and_Punishment) corrobora que evidence, crime points, prison y jury son un ciclo completo y no sólo un conjunto de ventanas/paquetes.

Las wikis sirven para descubrir y delimitar mecánicas; no son autoridad para IDs, opcodes, fórmulas o valores de r575. Esos deben proceder del cliente nativo, SQLite, Lua/ALB y trazas de red de la misma versión.

## Opciones apagadas: qué podría activarse y qué no

El runtime real lee `.server_files/AAEmu.Game/Configurations/Features.json` (SHA-256 `466A9...3FF0`). El archivo versionado `AAEmu.Game/Configurations/Features.json` (SHA-256 `0E403...413C`) no es el usado por el proceso. Hay una deriva: `useCosplayLooksSlot` está `true` sólo en la copia versionada y ausente/apagado en runtime.

### Candidatos de UI o presentación

No implican que sean “seguros” automáticamente. Requieren traza del consumidor Lua/nativo y una prueba de que no habilitan una mutación sin servidor:

- `2 use_slash_open_chat`
- `89 useUrlLink`
- `100 fastQuestChatBubble`
- `103 target_equipment_wnd`
- `146 ui_avi`
- `171 useCharacterListPage`
- `198 loadingTipOfDay`
- `220 useCosplayLooksSlot` — además debe resolverse la deriva source/runtime
- `225 chatLanguageFilter`
- `227 use_character_privacy`
- `228 show_premium_hud`
- `229 specialty_trade_info_ui`

Orden sugerido: trazar consumidor → capturar UI con bit aislado → comprobar packets nuevos → si no hay mutación, activar primero en entorno de aceptación y luego en runtime.

### Sistemas jugables que sí son reconstruibles, pero no deben activarse todavía

- Progresión/combate: `6 combatResource`, `44 aaPoint`, `52 pvpModifiySet`, `93 petOnlyEnchantStone`, `139 freeResurrectionInPlace`, `157 socketChange`, `170 itemlookExtract`, `178 itemSmelting`, `181 useForceAttack`, `197 equipSlotEnchantment`, `200 itemGradeEnchant`, `207 mateAggressive`.
- Social/política: `47 butler`, `63 banishPlayer`, `114 hero`, `138 expeditionWar`, `140 expeditionLevel`, `149 squad`, `151 expeditionSummon`, `152 heroBonus`, `159 permissionZone`, `163 eloRating`, `164 chronicle_info`, `167 reportBadUser`, `172 renameExpeditionByItem`, `206 factionMigrateLimit`, `223 survey_form`, `236 useCraftOrder`.
- Housing/vehículos/instances: `73 housingUcc`, `106 indunPortal`, `110 indunDailyLimit`, `158 mate_type_summon`, `166 packageDemolish`, `177 vehicleZoneSimulation`.
- Mercado/live-ops/seguridad: `61 reportSpamMail`, `113 reportSpammer`, `115 marketPrice`, `182 reportBadWordUser`, `196 auctionPartialBuy`, `222 archePassMissionAccount`.
- Apariencia: `57 tailCustomizing` requiere contrato de datos, persistencia y compatibilidad de creación/edición.

Cada bit de esta lista necesita un paquete de trabajo vertical. El criterio de salida no es “la ventana abre”, sino “la operación válida persiste y la inválida no cobra, no consume, no duplica y devuelve el error nativo”.

### Bits de entorno, política o bloqueo: no son contenido para “reactivar”

- Plataforma/proveedor: `34 nexonPcRoom`, `46 secondpass`, `56 sensitiveOpeartion`, `117 buyPremiuminSelChar`, `142 premiumUserServer`.
- Restricciones o bloqueos: `102 forbidTransferChar`, `168 restrictFollow`, `179 protectPvp`, `221 uccUploadBlock`, `226 blockRename`, `231 block_trade_by_nft`, `232 block_joint_raid`, `234 blockSpendableGamePoint`, `235 blockFamilyContents`, `241 freeDemolishHouse`, `242 notGainLeaderShipPoint`.

Su valor correcto depende de política de servidor. En los bits cuyo nombre expresa bloqueo, ponerlos en `true` normalmente deshabilita contenido en vez de habilitarlo.

### Bits nativos desconocidos: mantener apagados

- `37 fset_4_5_unknown`
- `41 fset_5_1_unknown`
- `42 fset_5_2_unknown`
- `58 fset_7_2_unknown`
- `78 fset_9_6_unknown`
- `96 fset_12_0_unknown`
- `97 fset_12_1_unknown`
- `104 fset_13_0_unknown`
- `105 fset_13_1_unknown`
- `107 fset_13_3_unknown`
- `112 fset_14_0_unknown`
- `136 fset_17_0_unknown`
- `137 fset_17_1_unknown`
- `154 fset_19_2_unknown`
- `162 fset_20_2_unknown`
- `165 fset_20_5_unknown`
- `195 fset_24_3_unknown`
- `199 fset_24_7_unknown`
- `201 fset_25_1_unknown`
- `203 fset_25_3_unknown`
- `230 fset_28_6_unknown`
- `233 fset_29_1_unknown`

Algunos comentarios de `Feature.cs` ya asocian estos bits a un consumidor aproximado, pero eso no basta para activarlos. Se exige dirección/función nativa, condición exacta, payload o estado que modifica y una prueba A/B con un único bit.

## Inventario completo de deuda del backend

El inventario se genera con:

```powershell
python Scripts/AuditAa10ReconstructionBacklog.py --summary
python Scripts/AuditAa10ReconstructionBacklog.py > aa10-reconstruction-backlog.json
```

El segundo comando produce las 15.871 líneas del inventario exhaustivo: cada marcador con archivo/línea/texto/categoría, todos los paquetes C2G/G2C, registro/no-op, todos los efectos y todos los bits. Se mantiene como generador para que no quede obsoleto cada vez que cambia una línea.

Distribución actual de los 904 marcadores:

| Área | Marcadores |
|---|---:|
| G2C | 222 |
| C2G | 204 |
| SpecialEffect | 106 |
| Skill | 93 |
| GameModel | 76 |
| Manager | 66 |
| AAEmu.Game restante | 54 |
| Character | 24 |
| World | 16 |
| Quest | 13 |
| Unit | 13 |
| Commons | 9 |
| Tests e integración | 8 |

### Los 85 efectos especiales con cuerpo vacío

`ActivateSavedAbilitySet`, `AddCharacterSlot`, `AddExpeditionExp`, `AddFamilyExp`, `AddFxToProjectile`, `AddPStat`, `ApplyBotTrial`, `ArrestBot`, `AuctionPostAuthority`, `BuffSteal`, `ClearProjectile`, `CombatDice`, `CombatText`, `DeclareIndependence`, `DestroyAndSpawnSlave`, `DominionTaxInKind`, `EngraveOnGuardTower`, `EnterBeautyshop`, `EscapeMySlave`, `ExpandDecoLimit`, `ExpeditionLevelChange`, `ExpeditionSummon`, `ExplodeBuff`, `ExpToItem`, `FxGroup`, `FxGroupAnim`, `GainGachaLootPackItem`, `GainItemWithPosImprint`, `GenderTransfer`, `GetSiegeTicket`, `HealPet`, `HealSlave`, `HudAuctionAuthority`, `HudBattlefieldAuthority`, `IncreaseFavoritePortalLimit`, `Interaction`, `ItemCapScale`, `ItemCapScaleReset`, `ItemGradeEnchanting`, `ItemSmelting`, `LearnSpecialAbility`, `LoseTargetingTheTarget`, `ManaCost`, `MateMakeGetUp`, `MoveToGround`, `NotifyQuest`, `OpacityControl`, `OpenPortal`, `PauseUserMusic`, `PhysicalEnchantArmor`, `PhysicalEnchantWeapon`, `PlayAttachmentAnim`, `PlaySkillControllerAttachmentAnim`, `PlayUserMusic`, `Projectile`, `ProjectileAnim`, `ProtectionForExpedition`, `ReceiveLuluLeaflet`, `RechargeItemRndAttrUnitModifier`, `RechargeItemSkill`, `RedeemBuff`, `RemoveAllDoodad`, `RenewEquipment`, `RepairAuthorityInBag`, `ReportBot`, `ReportBotArrested`, `ReportBotExpired`, `ResetCooldown`, `ResidentServicePoint`, `Resurrection`, `RetrieveProjectile`, `Return`, `RevertItemLook`, `SavePortal`, `SextantPos`, `SkillUse`, `SpawnBomb`, `StartDominionNonPvpDuration`, `StopChanneling`, `StopManaRegen`, `TeleportToSiegeHq`, `TeleportToUnit`, `Track`, `UserMusicSaveNotes`, `WeaponDisplay`.

No todos tienen la misma prioridad. `Projectile`, `Resurrection`, `ManaCost`, `SkillUse`, `ResetCooldown`, `OpenPortal` y `TeleportToUnit` son primitives transversales; `UserMusicSaveNotes` o `OpacityControl` son hojas. La estrategia debe cerrar primitives antes que hojas.

### TODO críticos que no son cuerpos vacíos

- `DamageEffect`: lado correcto de procs, DPS sólo de arma, NPC, siege damage, bonus por buff y tipos de chance.
- `BuffEffect`: caso de quest 2488.
- Combat resource, charges, skill maps y char transforms: hay carga de datos, pero falta conducta.
- Temper: outcome destructivo pendiente.
- `PlayUserMusic`: parte del flujo existe, pero falta conducta del instrumento.
- Housing managers: impuestos de dominion/castle, demolition/recovery mail/chest/full-kit, broadcasts y world checks.
- Crime: evidence, fases, offline y coordenada de suelo.
- Gimmick: física.
- Mail: expired return y Mia.
- Portal: tipos de teleport book, cooldown y error retail.
- Radar: shipyards.
- Borrado de personaje: player nation y leadership cleanup.
- World/instances: selección de channel.

### Paquetes que merecen auditoría prioritaria

Los 75 C2G no registrados reales y los 186 no-op contienen familias de Residents, Craft Orders, Butler jobs, Hero, Expedition recruitment/buffs/level, faction relations, Plot Auction, squads/raid recruitment, sailing activity, Housing UCC/trade list, Return Account y equipment slot reinforcement.

La lista exhaustiva y verificable está en la salida JSON del script. No se copian manualmente aquí para evitar dos fuentes de verdad.

## Qué es realmente “mecánica nueva”

Hay tres conceptos que conviene no mezclar:

1. **Nueva para el fork**: implementación creada en los 56 commits locales sobre el padre r575. Hiram/Gear Upgrade, Lunagem, Temper, tradepacks AA10, Auroria, reroll, Uthstin, LiveOps, crafting waves, Summon Mate, Housing waves y Erenor entran aquí.
2. **Nueva respecto al ArcheAge original**: Hero, Hiram, ArchePass, Ancestral/Heir, Farmhand, Community Centers/Craft Orders, Equipment Slot Reinforcement, modern Housing Rebuilding, Palos y otras capas post-lanzamiento. Deben reconstruirse como retail AA10, no diseñarse desde cero.
3. **Nueva o específica de Returns/r575**: contratos, bits, layouts, system-feature states y catálogos que difieren de AA8. AA8 puede aportar forma y semántica, pero nunca IDs/opcodes/valores sin demostrar equivalencia.

La etiqueta “nuevo” no debe basarse en la fecha del archivo C#. El criterio es la genealogía de la mecánica y si existe o no en el padre exacto de la rama.

## Estrategia de reconstrucción

### Fase 0 — hacer auditable el universo

1. Ejecutar y versionar por checkpoint el resumen del script de backlog.
2. Completar Stage 00/10 de `aa10-client-forensics`: hoy existe evidencia estática útil, pero falta la base forense agregada canónica. Sin ella no es defendible afirmar que se agotaron todos los consumidores Lua/native.
3. Resolver deriva entre Features source y runtime y declarar una única fuente de despliegue.
4. Mantener tres listas separadas: `advertised`, `implemented`, `accepted`. Nunca derivar una de otra.

### Fase 1 — reducir riesgo de superficies ya expuestas

1. Item Lock: núcleo retail aceptado; mantener unlock/bulk en regresión ampliada.
2. Loot Gacha: implementación desplegada; ejecutar gate retail de consume/RNG/reward/relog.
3. ArchePass: missions/reroll/counters y aceptación retail; mientras tanto mantener `archePassMissionAccount=false`.
4. Event Center y Palos: demostrar backend por ventana o retirar sólo el bit que expone la ventana incompleta.
5. Completar bordes de Bless Uthstin y Temper que hoy fallan explícitamente o quedan pendientes.

### Fase 2 — cerrar verticales con evidencia abundante

1. Item Smelting receta 5 y verificación de las 29–32 bloqueadas.
2. Housing H2/H4/H5/H5-B retail gates y persistencia.
3. Crafting: recipes sin materiales, ArchePaper y consumers faltantes.
4. Erenor: matriz restante de slots.
5. Quest Phase 6: recorridos, relog, repetición y persistencia.
6. Indun: entrada/salida/límite/eventos y reingreso.

### Fase 3 — reconstruir economía social como programa único

1. Community/Resident state machine.
2. Craft Orders con escrow e idempotencia.
3. Family levels/buffs/property access.
4. Expedition levels/buffs/recruitment.
5. Mail/Auction settlement y recuperación.

El orden evita implementar Craft Orders sobre Mail o Community incompletos.

### Fase 4 — autoridad competitiva y política

1. Primitives de combate/proyectiles/resurrección/teleport.
2. Crime/Jury/Prison.
3. Rankings/Elo/competitions.
4. Expedition War/Dominion.
5. Hero seasons y liderazgo.
6. Siege/castle/territory.

Hero y Siege deben ir después de combate, guild y schedules; hacerlos antes generaría una UI convincente sobre una autoridad incompleta.

### Fase 5 — contenido tardío y plataforma

Butler/Farmhand, Surveys, UCC/music/beauty, Return Account, privacy/reporting y bits de plataforma. Son reconstruibles, pero tienen menos capacidad de desbloquear otros dominios o más dependencia externa.

## Priorización cuantitativa sugerida

Para cada paquete de trabajo, puntuar de 0 a 5:

- evidencia nativa disponible;
- impacto visible para jugadores;
- cuántos dominios desbloquea;
- riesgo de exploit si queda parcial;
- coste/protocolo desconocido;
- dependencia de LiveOps o servicios externos.

Prioridad orientativa:

`(evidencia + impacto + desbloqueo + riesgo_expuesto) - (coste_desconocido + dependencia_externa)`

Un sistema encendido y no autoritativo recibe además un multiplicador de urgencia. Esto pone Item Lock/Loot Gacha por encima de una ventana apagada aunque el segundo sistema sea más atractivo.

## Gate de aceptación obligatorio por mecánica

1. **Source-of-truth**: tabla/filas, Lua/ALB, consumidor nativo y protocolo identificados.
2. **Cobertura**: manifest de productores/consumidores y razones explícitas para filas bloqueadas.
3. **Autoridad**: el cliente nunca decide coste, RNG, reward, ownership ni resultado.
4. **Negativos**: request forjada, repetida, fuera de estado, sin coste, sin permiso y fuera de rango.
5. **Persistencia**: relog/restart, expiración, rollover y recovery.
6. **Economía**: consume/cobra/entrega exactamente una vez; no hay duplicación ni pérdida silenciosa.
7. **Protocolo**: payload y respuestas retail, incluido error visible.
8. **Cliente**: UI abre, actualiza y cierra sin error Lua/native.
9. **Regresión**: tests del dominio y primitives compartidas.
10. **Live runtime**: sólo después de los nueve gates anteriores se cambia el bit de `.server_files`.

## Próximos diez paquetes concretos

1. Ejecutar gate retail de Loot Gacha y registrar aceptación o defecto reproducible.
2. Reconciliar Features source/runtime y añadir test que impida drift silencioso.
3. Auditar Palos/Event Center por productor y dejar cada ventana fail-closed.
4. Terminar ArchePass missions/reroll/counters.
5. Completar Item Smelting recipe 5 y revalidar bloqueos 29–32.
6. Cerrar Housing H2 cross-account y H5-B persistence gate.
7. Ejecutar campaña Quest Phase 6 E2E con relog/repetición.
8. Construir primitives `Projectile`/`Resurrection`/`TeleportToUnit` antes de Hero/Siege.
9. Iniciar Community Center + Craft Orders como un solo vertical con Mail escrow.
10. Mantener Item Lock visible/relog/venta como regresión y ampliar unlock/bulk.

## Límites de esta auditoría

- Es exhaustiva respecto de los marcadores, paquetes, efectos y fset observables en este checkout en la fecha de corte.
- Es amplia respecto de mecánicas conocidas por cliente, base de datos, checkpoints y fuentes históricas, pero no puede demostrar evidencia negativa total mientras la base forense agregada no exista y Stage 00/10 no se haya completado.
- “Sin TODO” no significa terminado; “con TODO” no significa prioritario. Los checkpoints, pruebas y gates dinámicos prevalecen sobre comentarios antiguos.
- No se ejecutó Zone ni se mutó estado de juego durante esta auditoría. La lectura de contenedor fue limitada a configuración, mounts y logs.
