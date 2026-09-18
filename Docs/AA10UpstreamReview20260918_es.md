> Informe de revisión previo a la integración. Para el resultado del merge autorizado después, consultar [la entrega](AA10UpstreamIntegration20260918_es.md).

# Revisión del padre AAEmu r575 — 18 de septiembre de 2026

**Conclusión: sí podemos incorporar sus mejoras, mediante una integración adaptada; esta punta no está lista para fusionar y desplegar sin correcciones.** La revisión detectó conflictos con cierres propios, rutas duplicadas que Git uniría sin advertir y problemas de implementación en el padre. No se efectuó merge, commit, push, migración ni despliegue.

## Alcance y corte exacto

| Dato | Valor |
|---|---|
| Target | `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10` |
| Fork | `Wingsjuankaa/AAEmu:rama_10` |
| HEAD local revisado | `86b6d0b46284919ee8ff323cf05f00405e54a1c3` |
| Padre exclusivo | `AAEmu/AAEmu:client_version/zone-10.0.2_r575` |
| Base común | `b439e1cc0d4bb96647d11dcb76da61b0246a53e1` |
| Punta padre revisada | `30837660a75e4beef5a38f37bf95809edf055f53` |
| Pendientes desde la base | **139 commits: 116 no merge + 23 merges** |
| Commits exclusivos del fork | **92**, incluidos merges e historial propio |
| Diff neto del padre | **387 archivos; +31.147 / −1.231 líneas** |
| Archivos de pruebas modificados o añadidos | **119**; no equivale al número de pruebas |
| Solapamiento con cambios propios desde la base | **47 archivos** |
| Simulación `git merge-tree --write-tree` | **20 archivos con conflictos**, 17 de contenido y 3 add/add |

Se ejecutó fetch del padre exacto y se repitió después del aviso del usuario. Los tres merges recién publicados ya están incluidos: [asedios #1617](https://github.com/AAEmu/AAEmu/pull/1617), [protección sensible #1621](https://github.com/AAEmu/AAEmu/pull/1621) y [remodelación #1618](https://github.com/AAEmu/AAEmu/pull/1618). La hora de la comprobación final se registra al pie y en `verification.json`.

`git merge-tree` creó únicamente objetos de simulación en Git; no cambió HEAD, índice ni archivos de trabajo. Se guardaron copias de fuentes relevantes y evidencia bajo este directorio de artefactos. Las skills aplicadas fueron [aaemu10-native-reconstruction](C:/Users/juank/.codex/skills/aaemu10-native-reconstruction/SKILL.md) y [aa10-es-es-localization](C:/Users/juank/.codex/skills/aa10-es-es-localization/SKILL.md).

## Decisión por bloque

| Bloque | Qué ganamos | Recomendación para nuestro fork |
|---|---|---|
| Puntuación de equipo | Escala correcta de armas, armaduras y accesorios; gates de equipo más fiables | Prioritario. La SQLite local confirma 220/78/1/2 y fórmulas que esperan 2,2/0,78/0,01/0,02. Mantener `NativeSocketItemIds`. |
| Eventos y residencia | Respuestas a ventanas antes vacías; correcciones de longitud y operación de paquetes | Incorporable con verificación del wire. Eventos solo cubre el caso sin eventos. |
| Filtro de contenido | Generación desde `world_contents`, categorías y serialización corregidas | Incorporar los tres commits juntos. Validar categorías habilitadas contra nuestro catálogo; no traducir los identificadores del protocolo. |
| Música | Conjuntos de hasta cinco músicos y flujo de invitación/partituras/interpretación | Incorporable con prueba de entrada, salida y desconexión del director. |
| Asedios | Inscripciones, equipos, miembros y equipo offline | Incorporar la cadena completa, incluidas exclusión de borrados y lectura de contenedores sin creación. Aún no elige comandante. |
| Rankings | Tablas persistentes, equipo, gremios, contadores, pesca, apariencia y temporadas | Incorporable tras corregir liquidación. El pago corre desde el refresco; no asumir que puede desplegarse la UI sin activar ese camino. |
| Bloqueo de objetos | Replay tras entrada y ajustes de desbloqueo | Adaptar sobre nuestro servicio único. Nuestro núcleo ya está implementado y tiene aceptación retail de lock/relog/venta. |
| Segunda contraseña y protección | Persistencia, límite de intentos y guardas de operaciones | Importar código conservando `secondpass=false` y `sensitiveOpeartion=false` hasta cerrar aceptación. Mantener nuestro arreglo contra falsa protección al entrar. |
| Habilidades/daño/buffs/plots | Gran expansión de requisitos, fórmulas, escudos, áreas, cargas y efectos | Integración transversal de riesgo alto. Conservar correcciones finales, liquidación propia y contratos de Zone; corregir discrepancia angular y revisar hipótesis temporales. |
| Controladores de movimiento | Saltos, dash, wandering y floating para jugadores | No promover velocidades/curvas inferidas como comportamiento nativo validado. Probar interacción con Zone y vehículos. |
| Viviendas | Datos y flujo comunitario de remodelación, alcance desde parcela y comando de prueba | Adaptar mejoras sobre nuestro `TryRebuildHouse`; no reemplazar la transacción, los impuestos ni la identidad de vivienda. |
| Vehículos/antibot | Nuevos catálogos y estado interno | Beneficio parcial: faltan consumidores o pregunta/validación. No declarar sistemas completos. |

## Hallazgos que impiden una integración directa

### 1. Premios de rankings: la transacción no engloba la entrega

En el código final, `PayEndedWindows` llama a `Grant` para cada ganador **antes** de `MarkPayout`. Aunque recibe `connection` y `transaction`, las comprobaciones y el marcado de `MySqlRankScoreStore` abren conexiones propias; la entrega usa correo/estado del personaje. El comentario y el mensaje original del commit dicen que se marca antes, pero el código no hace eso.

Si se interrumpe el proceso entre entregas y marcado, la siguiente pasada puede volver a pagar las entregas ya efectuadas. Dos pasadas concurrentes también pueden superar la comprobación previa. Una clave única con `ON DUPLICATE KEY UPDATE` al final no revierte esos efectos. Es un defecto estático de atomicidad/idempotencia, no un fallo reproducido en el runtime del usuario.

La corrección debe usar un registro durable por destinatario/premio y entrega recuperable e idempotente, con reclamación y transición transaccionales. Adelantar simplemente la marca al inicio cambiaría el riesgo por premios perdidos.

Evidencia: [RankScoreManager.cs](upstream/AAEmu.Game/Core/Managers/RankScoreManager.cs), líneas 306–338; [MySqlRankScoreStore.cs](upstream/AAEmu.Game/Core/Managers/MySqlRankScoreStore.cs), líneas 284–307; commit [5a6c1c5aa](https://github.com/AAEmu/AAEmu/commit/5a6c1c5aa970867f66ce1984cca9c2a3f424fd52).

Además, `Grant` omite moneda cuando `holder == null` y posteriormente marca el período pagado. Es una limitación real del código, pero **el impacto actual debe acotarse**: en nuestra SQLite las cinco filas con moneda son contribución del ranking de gremios 41, de un tipo todavía sin productor de puntuaciones en esta serie. No se ha demostrado pérdida de moneda de jugadores en el runtime actual. Antes de ampliar esas tablas habrá que resolver también el destinatario `HolderKind.Expedition`, que `Grant` no distingue al buscar un personaje.

### 2. Viviendas: dos implementaciones incompatibles y pérdida de validaciones

Git une `HousingGameData.cs` sin conflicto, pero deja activos **`LoadHousingRebuildings` y `LoadRebuildTables`** con dos catálogos del mismo sistema. También une `HousingManager.cs` dejando nuestro `TryRebuildHouse` y el nuevo `Rebuild`, además de dos vías para cotizar. No basta con resolver los archivos marcados por Git.

El nuevo `Rebuild` suma materiales, llama a `ConsumeItem` sin comprobar cuánto retiró y cambia la vivienda; valida solo `LaborPower`, mientras nuestra ruta contempla ambos saldos y una liquidación propia. En nuestra integración, los materiales bloqueados o un consumo rechazado/parcial pueden hacer divergir la comprobación previa de la mutación efectiva. Nuestro camino incluye impuestos/certificados, estado de construcción/venta, decoración, habilidad y restauración de bindings; esas garantías no deben perderse.

La respuesta comunitaria de cotización envía `[]` en la punta revisada, aunque el mensaje del commit habla de filas de cotización. El paquete añadido usa `ulong Pd`; nuestro contrato y pruebas usan **`double PaidDuration`**. Ambos ocupan ocho bytes, pero codifican distinto un valor no nulo: no son intercambiables por coincidir en tamaño.

Conservar el catálogo/planificador propios y trasladar únicamente los ajustes confirmados de alcance, selección del objetivo, actualización visual y herramientas que aporten valor.

Evidencia: [HousingManager upstream](upstream/AAEmu.Game/Core/Managers/HousingManager.cs), líneas 709–712 y 1834–1914; [HousingGameData simulado](simulation/AAEmu.Game/GameData/HousingGameData.cs), llamadas en líneas 261 y 328; [paquete simulado en conflicto](simulation/AAEmu.Game/Core/Packets/G2C/SCRebuildHouseTaxInfoPacket.cs). Nuestra referencia está en [HousingManager local](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Core/Managers/HousingManager.cs).

### 3. Los conos siguen usando dos convenciones

`AreaShape` divide `Value3` entre dos, como apertura completa. En cambio, `SkillAreaRules.ConeHalfAngle(120, 0)` devuelve 120 y `Skill.FilterAoeShape` compara directamente el rumbo contra ese valor: admite ±120°, mientras la documentación final dice que debería ser ±60°. Sus pruebas todavía afirman que el ángulo de skill es un semiángulo.

La discrepancia código/documentación y entre rutas está comprobada por lectura; determinar si ambas columnas nativas comparten exactamente la misma semántica exige corroboración. No se debe aceptar la afirmación documental de que ya están unificadas.

Evidencia: [SkillAreaRules.cs](upstream/AAEmu.Game/Models/Game/Skills/SkillAreaRules.cs), líneas 45–64; [Skill.cs](upstream/AAEmu.Game/Models/Game/Skills/Skill.cs), líneas 1366–1377; [AreaShape.cs](upstream/AAEmu.Game/Models/Game/World/AreaShape.cs), líneas 34–42; [pruebas de ángulos](upstream/AAEmu.UnitTests/Game/Models/Game/Skills/SkillAreaRulesTests.cs).

### 4. El bloqueo de objetos ya existe y está más integrado en nuestro fork

Nuestro `ItemSecurityService` valida propietario, contenedor, ranura/ID, categoría y excepciones; usa `ItemLock`, `ItemUnlock` y `ItemUnlockExcess`, y tiene guardas centrales para operaciones irreversibles. La implementación entrante introduce otra máquina de estado y publica `ItemLock` en `SendSecurityUpdate` para todas las transiciones. Los cuatro handlers entran en conflicto porque ambos lados dejaron de ser stubs de formas diferentes.

Incorporar mejoras demostrables, como el replay si hiciera falta, a una sola autoridad. No sustituir el servicio ni dar por nueva una función que el usuario ya probó. En nuestra configuración `itemSecure=true`, así que sus riesgos no quedan ocultos por el valor apagado de upstream.

Referencia: [checkpoint Item Lock](E:/AAEmu/rama_10/server/AAEmu/reconstruccion_cliente_10/checkpoints/CHECKPOINT_NATIVE_ITEM_LOCK_V1.md) y [ItemManager upstream](upstream/AAEmu.Game/Core/Managers/ItemManager.cs), líneas 3047–3051.

### 5. Una segunda guarda bloquea las habilidades de liberación

`Skill.Use` evalúa primero `SkillUseConditionRules` con los bits de permiso de la habilidad. A continuación, para jugadores y mascotas, llama a `CrowdControlRules.RejectCast(state)` sin esos permisos. Esa sobrecarga rechaza siempre bajo stun/sleep/silence, incluso cuando la primera guarda dejó pasar una habilidad diseñada para usarse en ese estado. Existe otra sobrecarga que acepta los permisos y tiene pruebas, pero este caller no la usa.

La resolución del merge `da75d765a` conservó ambas guardas sin conectarlas correctamente. Antes de integrar hay que conectar los permisos al camino real y probar una habilidad de liberación a través de `Skill.Use`, no solo sus reglas aisladas.

Evidencia: [Skill.cs](upstream/AAEmu.Game/Models/Game/Skills/Skill.cs), líneas 215–241; [CrowdControlRules.cs](upstream/AAEmu.Game/Models/Game/Skills/CrowdControlRules.cs), líneas 72–115. Defecto estático confirmado; no se ensayó en el cliente del usuario.

### 6. El merge de daño perdió su tipo al aplicar la reducción de vida

`8ada199e5` hizo que `DamageEffect` pasara su `DamageType` a `ReduceCurrentHp` para que reflexión/escudos distinguieran golpes. El merge `93525fd09`, al combinar daño de maná y de vida, conservó `trg.ReduceCurrentHp(caster, value)` sin el tipo. Esa llamada sigue así en `30837660a`, y el parámetro por defecto de `Unit.ReduceCurrentHp` es `DamageType.Melee`.

Por tanto, los golpes mágicos y a distancia que recorren ese punto se presentan a esa lógica como cuerpo a cuerpo: pueden activar o evitar reflejos del tipo equivocado. Hay que pasar el tipo correcto y comprobar las familias de daño en la ruta integrada.

Evidencia: [DamageEffect.cs](upstream/AAEmu.Game/Models/Game/Skills/Effects/DamageEffect.cs), línea 609; [Unit.cs](upstream/AAEmu.Game/Models/Game/Units/Unit.cs), línea 757. `upstream-merge-resolutions.patch` conserva la resolución que eliminó el argumento.

### 7. Combate y movimiento necesitan preservar nuestros contratos

Los conflictos alcanzan casteo, `SkillObject`, buffs, plots, unidades y `ZoneAuthorityCombat`. Se deben conservar especialmente el arreglo de contexto vacío `410d36871`, la propulsión naval `f4d8767f5`, los límites de casco `d2b3dbf1c`, la pesca/snapshots `398c43ba9` y la liquidación de labor propia. Git conserva automáticamente varios de sus textos, pero eso no demuestra compatibilidad de comportamiento.

La serie también declara decisiones todavía inferidas: ventana de diez segundos en reducción AoE, 4 m/s para dash sin duración, interpretación de wandering/floating y `ray_off_set`. `skill_reqs` usa cuatro IDs excepcionales por diseño cuya aceptación en juego no está completada. La procedencia comunitaria no reemplaza evidencia nativa; estos puntos necesitan resolución focal, sin añadir compensaciones arbitrarias.

## Base de datos y despliegue futuro

Se añaden seis scripts:

| Script | Efecto |
|---|---|
| `2026-09-17_aaemu_game_rank_scores.sql` | Crea `character_rank_scores`. |
| `2026-09-17_aaemu_game_rank_game_points.sql` | Crea `character_game_point_totals`. |
| `2026-09-17_aaemu_game_rank_payouts.sql` | Crea `rank_period_payouts`. |
| `2026-09-17_aaemu_game_second_passwords.sql` | Crea `account_second_passwords`. |
| `2026-09-18_aaemu_game_rank_records.sql` | Crea `character_rank_records`. |
| `2026-09-18_aaemu_game_rank_scores_sub_data.sql` | Añade `sub_data VARBINARY(24)` a `character_rank_scores`. |

Los cinco CREATE usan `IF NOT EXISTS`. El ALTER no lo usa: requiere inspección del esquema o un ledger de migraciones para ser reejecutable. No se consultó ni cambió el esquema MySQL vivo en esta revisión; no se afirma que esas tablas estén ausentes allí. Antes de un despliegue deberán prepararse respaldo, migrador idempotente, pruebas de reinicio y rollback. Esta revisión no requiere reiniciar Docker ni operar Zones.

## Impacto en es_ES

El diff del padre no sustituye `game_pak`, compact, ALB, JSONL de traducción ni los parches UI del cliente principal. La distribución sigue usando `+locale en_us`; importar estos commits no requiere habilitar un locale español binario.

Sí hay nueva superficie visible generada por el servidor: correo `Ranking reward`/`Rankings`/`Rank ... on board ...`, rechazo de cuenta protegida y salidas de `/houserebuild`, `/siegewindow`, `/rankrefresh` y `/sensitive`. Debe inventariarse y traducirse conservando parámetros. Los mensajes enviados como IDs nativos dependen de las unidades ya localizadas del cliente: comprobar la pantalla no equivale a traducir otra vez el ID.

La nueva ruta comunitaria de remodelación reemplaza el nombre de la vivienda por el nombre localizado de plantilla; nuestra `HousingRebuildNamePolicy` conserva nombres personalizados y normaliza nombres anteriores. Esa política también debe sobrevivir. Los nombres técnicos de `WorldContentFilterPack` son claves de protocolo y no deben traducirse.

Consulta SQLite realizada en modo de solo lectura: desbloqueo 4320 minutos; 223 destinos de remodelación; multiplicadores de equipo en centésimas. Nuestra `world_contents` autoritativa tiene **7.405 filas**, frente a las 7.408 citadas por el autor: no usar su recuento como validación de nuestro contenido. Las pruebas editoriales y de UI no se ejecutaron porque no se generó ni aplicó una traducción.

## Ruta recomendada de integración

1. Fijar el SHA padre aprobado y crear respaldo local de `rama_10` antes de integrar. Usar merge normal para conservar linaje.
2. Resolver los 20 conflictos y revisar los otros 27 archivos solapados que Git uniría automáticamente. Unificar catálogos, servicios y estado; no aceptar `ours`/`theirs` de forma masiva.
3. Corregir liquidación de rankings, permisos de liberación y propagación del tipo de daño; resolver semántica angular. Conservar transacciones propias de objetos/vivienda y los arreglos de casteo/Zone. Mantener apagadas las features actualmente apagadas, incluido Item Smelting fuera de alcance.
4. Incorporar los textos nuevos al flujo de localización y preparar las seis migraciones con comprobaciones idempotentes.
5. Ejecutar restore, build Release y suite unitaria sobre la combinación real. Añadir regresiones de fallos de consumo, reintentos/reinicio de pagos, bloqueo/relog, pasivas/cargas, conos y autoridad Zone.
6. Preparar y verificar despliegue local con respaldo y rollback, conforme a la autorización permanente de la skill cuando exista tarea de implementación. La aceptación cliente debe cubrir monturas/pociones, combate, barcos, pesca, remodelación y rankings. La operación de Zones conserva su autorización específica.

## Qué se verificó y qué queda pendiente

Verificado: referencia remota exacta mediante fetch y ls-remote; base/divergencia; los 139 commits inventariados sin omisiones; diff neto, simulación de merge y archivos solapados; mensajes originales; revisión de fuentes finales en puntos de riesgo; comparación con implementaciones/checkpoints propios; consultas focales a SQLite en solo lectura; configuración de features versionada.

No realizado: integración, resolución efectiva, compilación o ejecución de pruebas del candidato, migración, despliegue y aceptación en el cliente. Los resultados de pruebas citados por los autores son antecedentes, **no pruebas locales de esta revisión**. La revisión es de viabilidad y riesgos, no una certificación exhaustiva de todas las rutas de las 31.147 líneas añadidas.

## Detalle de todos los commits

Las secciones siguientes cubren los **116 commits no merge**, con explicación en español y enlace al SHA completo. Se describe el cambio y, cuando corresponde, la corrección posterior que lo sustituye. Después se listan los **23 merges**, que integran esos mismos bloques y sus resoluciones; no son 23 funcionalidades adicionales.
<!-- GENERATED COMMIT DETAILS -->

### Eventos y residencia — 4 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [f264b17b1](https://github.com/AAEmu/AAEmu/commit/f264b17b1d91e2be3ede0b7cb26e74eae42d0578) | Responde al recuento de eventos y añade la respuesta vacía. El panel deja de esperar indefinidamente; sigue sin implementar las entradas de eventos reales (SC 0x2DE). | 7 |
| [9616bb38c](https://github.com/AAEmu/AAEmu/commit/9616bb38c44c150af3313ee3e0484b2d615bcee5) | Responde la lista de regiones de residencia; añade el byte de operación al mapa de residentes y corrige el cuerpo de protección sensible. Añade paquetes de URL/verificación, sin implementar balances de residencia. | 9 |
| [fa4bbcb37](https://github.com/AAEmu/AAEmu/commit/fa4bbcb3726a435c8e2d3d2adf998f8c37674ec2) | Usa Add=1 en el mapa de residentes: el valor inicial cero era ignorado por el cliente. Sigue pendiente retirar automáticamente una región al vender la última casa, sin relog. | 2 |
| [2405f6682](https://github.com/AAEmu/AAEmu/commit/2405f6682f689b1a43821f4adc919beac8ebd282) | Documenta el constructor nativo del opcode 0x3B, fija anchos y limita la lista de residentes a 100 filas para no desbordar la capacidad del lector. | 4 |

### Vehículos — 3 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [e864bf727](https://github.com/AAEmu/AAEmu/commit/e864bf7276651da9fa8a624ecb5d7ff6d7631ca5) | Intento inicial de ofrecer interacciones desde slave_interaction_skills en mascotas. Queda corregido por f1e32e3c5: esas filas describen vehículos, no NPC de mascotas; no integrar aisladamente. | 4 |
| [6053e5bfe](https://github.com/AAEmu/AAEmu/commit/6053e5bfe02a87492bd36ffd68779661f6803d55) | Carga slave_equip_kind_id y condiciona interacciones al equipo instalado. La interpretación de ranura/mascota se corrige después; el resultado útil es el catálogo y sus reglas. | 4 |
| [f1e32e3c5](https://github.com/AAEmu/AAEmu/commit/f1e32e3c58a2b2b4a39ea78c80bf337d6a1ebb9c) | Corrige la confusión entre mates y slaves: las interacciones son asientos de vehículos y el requisito identifica un punto de anclaje. Restaura la interacción anterior de mascotas; queda pendiente conectar el consumidor correcto. | 4 |

### Buffs — 7 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [aea000cab](https://github.com/AAEmu/AAEmu/commit/aea000cabe148246444890ab96ba5141cab50b91) | Implementa pulsos de auras: aplica el buff asociado a unidades dentro del radio y relación permitidos, lo retira al salir o terminar y evita crear tareas duplicadas al refrescar. | 7 |
| [a1b51dbd0](https://github.com/AAEmu/AAEmu/commit/a1b51dbd0842577009753f889a04cff2c4b3ddab) | Implementa provocación de NPC mediante el relay de objetivo y amenaza hacia Zone. La variante de máxima amenaza usa la mayor amenaza conocida más uno; al terminar se libera la provocación simple. | 4 |
| [8ada199e5](https://github.com/AAEmu/AAEmu/commit/8ada199e50ab2b06d8260531ee07edc396725ca9) | Añade reflexión de daño y escudo de maná en la reducción de vida, según probabilidad, proporciones y tipos de daño. Amplía firmas de métodos compartidos; requiere comprobar autoridad y sincronización Game/Zone. | 9 |
| [3225f8282](https://github.com/AAEmu/AAEmu/commit/3225f8282108e338b93b0b116d8db58caef84830) | Distingue escudos que absorben por golpe, por número de impactos o gastando una reserva. Consume cargas según damage_absorption_type_id y damage_absorption_per_hit. | 5 |
| [99acc010a](https://github.com/AAEmu/AAEmu/commit/99acc010ac73b91a9fd82fe07109d86d89dc3877) | Generaliza el coste de maná periódico más allá de Dash y filtra el área de cada tick por ángulo, orientación y número máximo de objetivos. Dos campos de tick siguen sin consumidor por semántica no resuelta. | 7 |
| [a8a1ec17d](https://github.com/AAEmu/AAEmu/commit/a8a1ec17dcffada97ce5a3be7cc38f7d760d740f) | Impide movimiento por inmovilización, sueño o aturdimiento y lanzamiento por silencio/sueño/aturdimiento. Añade soporte de permisos de liberación, pero la integración final llama a la variante estricta y no usa esos permisos; corregir el caller. | 4 |
| [7e384e538](https://github.com/AAEmu/AAEmu/commit/7e384e538a52c7031eefd5b2c6ddfeb2fba9bf7b) | Aplica max_life_time como techo a duración y refrescos, incluyendo buffs de duración cero que antes quedaban permanentes. La documentación posterior corrige el recuento de filas afectadas. | 6 |

### Carga, fórmulas y mantenimiento — 13 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [eabc0abb7](https://github.com/AAEmu/AAEmu/commit/eabc0abb76d1be2aad8f49e245c992843d58c2a8) | Respeta enable en reactivos y modificadores; contabiliza filas omitidas, duplicadas o con referencias ausentes en skills y plots, evitando que ciertas referencias rotas derriben toda la carga. | 6 |
| [614d660d8](https://github.com/AAEmu/AAEmu/commit/614d660d8cc4484fb7ed184ca94089b5866fb7ee) | Retira avisos y mensajes de depuración por cada buff, condición y búsqueda de efecto. Reduce consultas de diagnóstico de área cuando Trace está apagado y corrige el nombre de un mensaje de log. | 5 |
| [40898454b](https://github.com/AAEmu/AAEmu/commit/40898454b03c2229514b562b62204a253ecc5d6f) | Carga 16 campos de física de planeo y seis animaciones de instrumentos. No añade comportamiento que los consuma: es preparación de datos, no una implementación nueva del vuelo. | 2 |
| [7366e1260](https://github.com/AAEmu/AAEmu/commit/7366e126084e92fc74793acef7ffcc54ae16f9fa) | Corrige documentación: source_crippled corresponde a bloqueo de habilidades físicas, no simplemente a inmovilización. Sigue sin aplicarse una prohibición indiscriminada que también bloquearía magia. | 1 |
| [8b62d99a0](https://github.com/AAEmu/AAEmu/commit/8b62d99a02357fff89f54c0a38f8adcea2fa5805) | Completa enumeraciones de fórmulas y propietarios, y usa filas de fórmulas para resistencia de combate, flexibilidad y precisión. Cargar filas de Butler no significa activar Butler. | 11 |
| [a81f7caa8](https://github.com/AAEmu/AAEmu/commit/a81f7caa8b38ef0719b11d7184332a0ac4715528) | Calcula estadísticas de combate de NPC desde sus fórmulas, incluidas tasas/bonos críticos, defensa y normalización por facets. Deja sin activar otros valores cuyo cambio general no se justificó en este bloque. | 2 |
| [82b2c82d1](https://github.com/AAEmu/AAEmu/commit/82b2c82d1d18279432c815a45b4001511bb641e9) | Separa modificadores por owner_type para que un ID de objeto no se interprete como buff. Conecta modificadores de equipo y gemas y consume atributos de curación, radio, GCD y canalización; algunos propietarios siguen solo catalogados. | 12 |
| [a8f9eaf8c](https://github.com/AAEmu/AAEmu/commit/a8f9eaf8c3513ef60aaf8d43547484b83f331204) | Carga propietarios Buffs, BuffUnitModifier y HealEffect de unit_modifiers. Aplica modificadores condicionados por etiqueta/buff y ajustes de crítico de curación; otros propietarios quedan fuera. | 7 |
| [fd0a4428c](https://github.com/AAEmu/AAEmu/commit/fd0a4428c5d06fc24c52cb58e70f859e92a4bb8a) | Ajusta pruebas y comentarios de ticks a la apertura completa del cono. Corrige expectativas antiguas de 120 y 180 grados; no añade otra mecánica. | 2 |
| [d6458636a](https://github.com/AAEmu/AAEmu/commit/d6458636af614f2d14c16b97d7ac11abd039a702) | Elimina UnitCharges y ChargeSkillRules duplicados y conserva la reserva UnitCooldowns que realmente usa el lanzamiento. Evita dos autoridades independientes para las cargas. | 5 |
| [e329d27fc](https://github.com/AAEmu/AAEmu/commit/e329d27fc726b1fadd41fc5fe316ae6b8911a6ca) | Corrige recuentos y afirmaciones de documentación sobre duración de buffs, requisitos, GCD, ángulos y recursos porcentuales. No cambia comportamiento; su afirmación de que la ruta de skills divide el ángulo no coincide con el código final observado. | 5 |
| [6c5e1891e](https://github.com/AAEmu/AAEmu/commit/6c5e1891eb6877101d246eb3feba0a65ffd1374d) | Refina el recuento de mensajes coreanos de prohibición, considerando dos grafías. Mantiene explícito que la redacción por sí sola no determina la polaridad del requisito. | 1 |
| [7aa3f8afd](https://github.com/AAEmu/AAEmu/commit/7aa3f8afd9bd8f78378b233733b3cea4c56bfc95) | Registra pruebas de invocación de montura en estados de guerra y paz. Declara que los cuatro requisitos excepcionales no se probaron en juego; no presentarlos como aceptación completa. | 1 |

### Habilidades: lanzamiento — 12 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [7b3032029](https://github.com/AAEmu/AAEmu/commit/7b303202905aefce7f0ae3a0074a603b72617f8b) | Exige el nivel de las pasivas, reevalúa las aprendidas al subir de nivel y aprende las automáticas cuando corresponda. Ajusta el nivel usado al aplicar sus bonificaciones. | 6 |
| [2ad4c229f](https://github.com/AAEmu/AAEmu/commit/2ad4c229f2385ae1a981a7c42ea05794d86b7a07) | Añade cooldown compartido por hasta tres etiquetas, cooldown por cuenta y selección del GCD desde custom_gcd, clase de arma o valor por defecto. Los encadenamientos no borran el cooldown de la familia. | 11 |
| [9bbeff224](https://github.com/AAEmu/AAEmu/commit/9bbeff2240959470e4dab1afb42b194198c97186) | Implementa reservas de cargas y recarga diferida; añade efectos para cambiar cargas e intervalos. El servidor controla el uso, pero no emite todavía una actualización de cargas cuya semántica de paquete no está cerrada. | 7 |
| [474f400a4](https://github.com/AAEmu/AAEmu/commit/474f400a4a487a07d9569373684c03954ad088ae) | Valida estados del lanzador, habilidad aprendida, alcance también en plot_only, estado vivo/muerto del objetivo y pertenencia real al grupo. Resuelve el objeto objetivo. Debe conservar excepciones legítimas de objetos, vivienda y habilidades concedidas. | 5 |
| [b1f85d53c](https://github.com/AAEmu/AAEmu/commit/b1f85d53cee06776e8686284245f8c7475d31bdc) | Usa combat_dice_id para decidir fallos, evasión y ataques indefendibles; respeta always_hit por efecto e incluye resistencia/fallo mágico entre resultados que impiden aplicar daño. | 3 |
| [6112d45ae](https://github.com/AAEmu/AAEmu/commit/6112d45ae98c17054672167f039fab954f68bae0) | Rechaza antes de lanzar una habilidad si falta labor, con límites y suma de ambos saldos seguros. Mantiene el débito al finalizar; combinar con nuestra liquidación idempotente y atómica. | 3 |
| [246d05126](https://github.com/AAEmu/AAEmu/commit/246d051263ee592c97027daf11947a363c5d2dad) | Aplica los efectos al terminar naturalmente una canalización, drena maná por intervalo y cancela las tareas al interrumpir. Corrige permisos de objetivos vivos/muertos; reconoce pendiente validar la doble notificación SCSkillFired. | 7 |
| [8d8119a72](https://github.com/AAEmu/AAEmu/commit/8d8119a72b92b82a454313f4fbe7940a2cabd88c) | Los golpes pueden cancelar o retrasar un lanzamiento y terminar una canalización; usa fórmulas de tolerancia y daño porcentual. El umbral de golpe grande y límites temporales necesitan corroboración nativa antes de promoverse. | 5 |
| [3ae030b32](https://github.com/AAEmu/AAEmu/commit/3ae030b32f32e51263fda9b72d67145eb467a0e6) | Carga requisitos de habilidades y enlaces por etiqueta, y activa daño de sinergia según buffs del objetivo. Su lectura inicial de default_result provocó rechazos; debe acompañarse de 658d3e21b y sus comprobaciones posteriores. | 7 |
| [11b0636d0](https://github.com/AAEmu/AAEmu/commit/11b0636d0e0c427d258170d62f414685fd8199c5) | Valida bandas de recursos de combate y requisitos por efecto: acumulaciones de buffs, etiquetas del lanzador/objetivo y probabilidad. Algunas probabilidades de progreso se aproximan al extremo final; no equivalen a una simulación por fotograma. | 7 |
| [e23e7834f](https://github.com/AAEmu/AAEmu/commit/e23e7834fc959445e9bc739834215347c5db5216) | Añade filtros de cono y corredor a la selección de área. Carga obstáculos y proyectiles, pero no implementa raycast ni vuelo de proyectiles. En la punta revisada persiste una discrepancia entre el semiángulo usado por esta ruta y la apertura completa usada por AreaShape. | 5 |
| [658d3e21b](https://github.com/AAEmu/AAEmu/commit/658d3e21b633108fd86d56c9652edf8d1cc64d5b) | Corrige la polaridad de skill_reqs que bloqueaba monturas y consumibles. Trata las filas como prohibiciones salvo cuatro requisitos explícitos por ID (15,37,58,59); conservar la corrección junto con la serie D7. | 3 |

### Autoridad de Zone — 3 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [7965ad8f2](https://github.com/AAEmu/AAEmu/commit/7965ad8f238bc27d1fb49d44677274868cac2121) | Elimina rutas de daño de NPC y MeleeCastTask que upstream considera sin uso, y actualiza comentarios del reparto World/Zone. En nuestro fork hay cambios en ese archivo: comprobar referencias antes de aceptar las eliminaciones. | 6 |
| [eaab1e8f4](https://github.com/AAEmu/AAEmu/commit/eaab1e8f4cb502baaf0a2923930b79191f5167cd) | Sustituye el bloqueo fijo de 1500 ms de ataques básicos de NPC por GetAttackDelay y permite que almighty omita esa guarda. Afecta la cadencia de NPC gestionados por Zone. | 4 |
| [f897b672c](https://github.com/AAEmu/AAEmu/commit/f897b672cc7255b24d4428ca62f96a0137895f14) | Pasa los buffs recibidos de Zone por reglas que evitan duplicarlos y comprueban requisitos. Debe combinarse con nuestro seguimiento de buffs procedentes de snapshots y la propulsión naval. | 3 |

### Equipo — 1 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [a08eda769](https://github.com/AAEmu/AAEmu/commit/a08eda769927940b1dd68d5208d43370cc75b6b6) | Divide por 100 los multiplicadores de puntuación de armas, armaduras y accesorios: 220 pasa a 2,2 y 78 a 0,78. Corrige puntuaciones y requisitos de acceso; conservar nuestros nueve sockets nativos. | 2 |

### Efectos de habilidades — 8 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [85c016b01](https://github.com/AAEmu/AAEmu/commit/85c016b017c81a328676f51807809e7a0ee621bb) | Implementa curación y restauración de maná porcentuales, multiplicador de autocuración y exclusión de amenaza al curar. Debe incluir 7fcb304a0, que corrige dónde se calcula el porcentaje. | 10 |
| [a0b0811c5](https://github.com/AAEmu/AAEmu/commit/a0b0811c59e9633836cc4eb6d4ad4908a2f6eff1) | Implementa ExtendChargeEffect: calcula absorción desde valores fijos, nivel, estadísticas y porcentaje de un recurso, crea el buff de escudo o amplía su carga respetando el límite. | 4 |
| [e38d6141d](https://github.com/AAEmu/AAEmu/commit/e38d6141d0d9718b681354020e09f5849b3fb7c4) | Activa la creación de gimmicks y su anuncio a Zone; carga intervalos de ángulo/distancia para repartir invocaciones y orientación. ray_off_set se aplica mediante una interpretación declarada como inferencia; revisar con nuestros límites del casco de barcos. | 7 |
| [dbce09faa](https://github.com/AAEmu/AAEmu/commit/dbce09faaa7d91b9880662c531ca31ed05a12f9b) | Completa varios efectos: amenaza desde cualquier Unit, quema de maná y daño asociado, disipación por acumulaciones, XP al retirar NPC sin cadáver, facción del invocador en la ruta local, detener seguimiento y filtros de mensajes de mundo. Persisten límites en Signal, drenaje y ruta Zone. | 14 |
| [a90d0b525](https://github.com/AAEmu/AAEmu/commit/a90d0b525441c9c8b3d50da40de5248bdfcb9f2a) | Aplica reducción progresiva a impactos de área según aoe_diminishings, del 100 % al 50 %, con contador por unidad/habilidad y efecto de reinicio. La ventana de diez segundos es una elección de implementación, no un valor confirmado del catálogo. | 7 |
| [2b5d7fe8f](https://github.com/AAEmu/AAEmu/commit/2b5d7fe8fb078fb8a4981b52a9da95a4e2c5a110) | Añade tipos especiales ausentes: cambios de cargas, tolerancia a control, regreso a posición guardada por un buff y cambios de estado de conflicto. Su segunda reserva de cargas se elimina después; la duración solicitada del conflicto sigue sin aplicarse. | 24 |
| [c78b3a659](https://github.com/AAEmu/AAEmu/commit/c78b3a6591985465b89088315a87a49a056c436f) | Implementa efectos antes vacíos: robar/cancelar/explotar buffs, interrumpir casteo, consumir labor/maná, curar mascota, perder objetivo, bajar al suelo, retirar doodads y teletransportar a sede de asedio, sujetos a sus reglas. | 32 |
| [7fcb304a0](https://github.com/AAEmu/AAEmu/commit/7fcb304a09624d1c1fd5227e0110777ad1ca457f) | Corrige la curación porcentual para que reciba reducción de curación y multiplicador crítico. Antes podía anunciar un crítico sin aumentar la cantidad curada. | 2 |

### Daño y combate — 6 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [6e830ae48](https://github.com/AAEmu/AAEmu/commit/6e830ae48bc97724512b726401b44c2eb8526611) | Añade daño porcentual sobre vida actual/máxima del objetivo o lanzador y escalado condicional por salud del objetivo. El porcentaje se suma a la composición, sin multiplicarlo otra vez por el multiplicador general. | 5 |
| [f3df48ddd](https://github.com/AAEmu/AAEmu/commit/f3df48dddca91d544f3e9dfe6f10734ae457addd) | Evalúa las fórmulas de altura y distancia óptima para ajustar daño; distingue distancia horizontal y diferencia vertical y mantiene factor neutro cuando faltan datos evaluables. | 6 |
| [4d3378dda](https://github.com/AAEmu/AAEmu/commit/4d3378dda741e9dbc8336764d69a3fec81aafa36) | Permite que un efecto dañe maná en vez de vida, habilita los recursos de maná en porcentajes y consume cancel_protection para decidir si la inmunidad detiene el golpe. | 3 |
| [884e7ddcc](https://github.com/AAEmu/AAEmu/commit/884e7ddcc03e357a82d55e73ebbcffb5b2399eed) | Respeta multiplicador de amenaza, entrada en combate y activación de procs por efecto. El multiplicador de amenaza se aplica a la ruta local; el relay Zone continúa transportando el daño bruto. | 4 |
| [360527adc](https://github.com/AAEmu/AAEmu/commit/360527adcd15937f4401e6c4422ba7724d455ac8) | Aplica bonificación crítica del efecto y suma plana condicionada por etiquetas del objetivo. Carga campos elementales y fixed_type, pero no implementa su efecto sin una fuente de atributos confirmada. | 5 |
| [de63b4c08](https://github.com/AAEmu/AAEmu/commit/de63b4c086cd1db4e996fb2275f27bf8675ab8d4) | Usa DPS del arma equipada para los términos que piden arma y añade contribuciones del recurso de combate. Completa columnas del cargador; las unidades sin arma conservan el fallback sobre estadísticas compuestas. | 5 |

### Plots — 6 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [bcc072f3d](https://github.com/AAEmu/AAEmu/commit/bcc072f3d58811996197d81214dc6cdc1056a47a) | Selecciona una sola rama entre hijos con peso positivo, conservando los hijos sin peso que deben ejecutarse siempre. Evita ejecutar simultáneamente todas las alternativas ponderadas. | 5 |
| [04807972d](https://github.com/AAEmu/AAEmu/commit/04807972d65720ea22f85167df137699d519689f) | Ordena la ejecución de nodos por su vencimiento y ajusta el estado activo y su liberación. Debe mantener nuestros contratos de timeline, finalización y limpieza. | 6 |
| [a59eea6ef](https://github.com/AAEmu/AAEmu/commit/a59eea6ef23c15f5215e83da2f35e1c3d57b010b) | Amplía evaluación de condiciones de plots: relaciones, acumulaciones, progreso del lanzamiento y recursos, entre otras. Documenta las condiciones todavía permisivas; no cierra todos los tipos. | 6 |
| [4009c60e6](https://github.com/AAEmu/AAEmu/commit/4009c60e676307c4154cf27a6df5de8e4668b029) | Interpreta value3 de SphereCone como apertura completa y filtra con la mitad del ángulo. Modifica el selector compartido de áreas y las llamadas de WorldManager. | 3 |
| [294d067eb](https://github.com/AAEmu/AAEmu/commit/294d067eb6420a34b38eb37ce28a3c338294b2b5) | Aplica filtros de eventos sobre muertos, mascota propia, propietario y otros selectores, y deja que la relación solicitada decida sobre objetivos neutrales. | 7 |
| [428c1435d](https://github.com/AAEmu/AAEmu/commit/428c1435d40311c445ae475b4bd1c4591b1f186b) | Añade TargetHistoryClearEffect y el manejo del historial del plot, permitiendo que los nodos que lo ordenan borren objetivos anteriores. | 4 |

### Movimiento por habilidades — 3 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [4e2f192d7](https://github.com/AAEmu/AAEmu/commit/4e2f192d742d621ab4a355cfd46f91b76b16429c) | Permite controladores de movimiento para jugadores sobre unidades controladas, extrae el desplazamiento lineal y completa limpieza del salto. Revisar que no compita con la autoridad de movimiento de Zone. | 8 |
| [cd5da6037](https://github.com/AAEmu/AAEmu/commit/cd5da6037a24bfa790dbad307dde66568f5cb68a) | Implementa dash (kind 4), distancias con signo y movimientos cortos. Cuando falta duración usa una velocidad de 4 m/s deducida de otras filas; necesita evidencia específica antes de adoptarla como contrato nativo. | 4 |
| [878c8a6e3](https://github.com/AAEmu/AAEmu/commit/878c8a6e3d7b5e9c679c5b996a9a49b473a1a0ce) | Añade wandering y floating y activa controladores desde plots. La interpretación temporal, velocidad y curva de elevación requiere validación; rope_ready/crawl y skill_controller_at_end siguen incompletos. | 5 |

### Asedios — 10 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [6d0b04d23](https://github.com/AAEmu/AAEmu/commit/6d0b04d230a1dcea4d11ac6a05071ad971e12f61) | Responde las inscripciones de equipos por zona con nombres e identificadores de personajes. Deja campos sin semántica conocida a cero y prepara el recorrido completado por commits posteriores. | 6 |
| [5b6e8880c](https://github.com/AAEmu/AAEmu/commit/5b6e8880cdc501cbc63c037a072ea41e8058474d) | Responde la lista de equipos por facción, separa defensa según propietario del dominio y limita a las tres posiciones de la ventana. No elige comandante. | 8 |
| [563be26a9](https://github.com/AAEmu/AAEmu/commit/563be26a9ddfbf11129e4810e2b75cf0d403f115) | Añade /siegewindow teams para inspeccionar/enviar la lista sin esperar a una fase de asedio activa. | 1 |
| [d906e1111](https://github.com/AAEmu/AAEmu/commit/d906e111107167521723a105b7bc65d0cfe4f6fd) | Responde el detalle de miembros con niveles, habilidades y equipo, y añade /siegewindow members. La resolución de equipo offline se corrige en la cadena siguiente. | 7 |
| [d89add368](https://github.com/AAEmu/AAEmu/commit/d89add3689736e6e3efeadcdb86c10bed84d9ef4) | Retira la lectura obsoleta que devolvía inventario vacío para personajes offline y registra temporalmente su puntuación como desconocida en vez de un cero silencioso. | 1 |
| [20696022e](https://github.com/AAEmu/AAEmu/commit/20696022e227013a835e0669a2f1437d41d67bf0) | Introduce el cálculo de equipo offline mediante contenedor persistente. Su accessor podía crear contenedores vacíos; debe incluir 3b997cce4. | 1 |
| [a2545d825](https://github.com/AAEmu/AAEmu/commit/a2545d825b9295299b2a26461b0181ac6f89cc6b) | Registra cuando se recorta una lista mayor que las tres posiciones de la UI y aclara que ese límite proviene de la ventana, no de un máximo probado del serializador. | 2 |
| [68e8fe3a2](https://github.com/AAEmu/AAEmu/commit/68e8fe3a26480ab6eef11af6a9c34442889b423f) | Excluye personajes marcados como borrados del recuento de equipos y del listado de miembros; centraliza y prueba las consultas. | 3 |
| [3b997cce4](https://github.com/AAEmu/AAEmu/commit/3b997cce4e1bf67c6f9e69910437e2c098f10036) | Usa FindItemContainerFor para leer el equipo offline ya cargado, sin crear ni registrar contenedores durante una consulta de ranking de asedio. | 2 |
| [a57b0a281](https://github.com/AAEmu/AAEmu/commit/a57b0a28107778c23c7e9a245171189d8eab8d0f) | Excluye personajes borrados también de inscripciones. Conserva registros huérfanos sin fila de personaje, que aparecen sin nombre. | 3 |

### Bloqueo de objetos — 4 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [7ddcbc639](https://github.com/AAEmu/AAEmu/commit/7ddcbc639ea61396be98fea716ebb85d43c17aae) | Implementa handlers de bloqueo individual y de equipo, excepciones y desbloqueo diferido. Se solapa con nuestro ItemSecurityService ya aceptado; su uso general de ItemLock no debe sustituir nuestros tasks diferenciados. | 8 |
| [77126aa94](https://github.com/AAEmu/AAEmu/commit/77126aa9415ea791178119a55fbd3302063be83c) | Reenvía el estado de bloqueo tras completar la entrada al mundo, permite cancelar un desbloqueo pendiente y evita prolongar el plazo al repetirlo. Revisar convivencia con nuestra política y persistencia. | 5 |
| [e6c69b1d1](https://github.com/AAEmu/AAEmu/commit/e6c69b1d1188566d1fd74bace821708936230716) | Lee el retraso desde item_secure_unlock_delay_time y conserva 4320 minutos como fallback. Nuestro catálogo ya conoce ese contrato; unificar sin mantener dos fuentes de estado. | 2 |
| [45b6b4e8c](https://github.com/AAEmu/AAEmu/commit/45b6b4e8c002431e753765dc239e466373cf6458) | Marca las pruebas del tiempo de desbloqueo como no paralelas porque modifican un singleton de configuración compartido. | 1 |

### Contenido del mundo — 3 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [262b46c17](https://github.com/AAEmu/AAEmu/commit/262b46c17760c418b2a1a9ab69fd253b48354b11) | Construye el filtro de contenido desde world_contents, evitando depender de un binario ausente. Su primer formato se corrige después; no incorporar sin deb427e32. | 4 |
| [b98259961](https://github.com/AAEmu/AAEmu/commit/b98259961fbe3f90a05dc7fdeedb0bba18734113) | Normaliza nombres de categorías para reconocer variantes como QuestContext y GameSchedule, y deja fuera tipos sin equivalente conocido. | 2 |
| [deb427e32](https://github.com/AAEmu/AAEmu/commit/deb427e3279c773526630c122d2eece1af236c59) | Corrige el paquete: cada grupo lleva nombre y cantidad, sin ID de categoría, y usa los nombres que reconoce el cliente. El formato anterior desplazaba el lector y producía errores de buffer. | 3 |

### Música — 2 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [a5f2ae606](https://github.com/AAEmu/AAEmu/commit/a5f2ae606eeabf4548d0e0a743fe00b51709e19e) | Añade sesión de conjunto con director, invitados, aceptados y partituras recibidas, y los paquetes de invitación, rechazo, inicio, cancelación y retirada de sonido. Límite de cinco miembros. | 9 |
| [4949f8b66](https://github.com/AAEmu/AAEmu/commit/4949f8b661827070511963a5ebf6cc5d9704817d) | Conecta invitación, aceptación, rechazo, recepción de partes y ejecución conjunta. Gestiona salida de miembros, pérdida del director y limpieza de sesiones abandonadas. | 7 |

### Rankings — 12 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [7f1fade58](https://github.com/AAEmu/AAEmu/commit/7f1fade58b4091bcfe78006893c723f26cd96c4a) | Añade la respuesta de estadísticas personales y las primeras tablas basadas en puntuación de equipo. Su identificación inicial se corrige en f5afe7560; no integrar sola. | 6 |
| [3fdcef3c2](https://github.com/AAEmu/AAEmu/commit/3fdcef3c2a4387fa117e1a8b599b7dcfc15ae912) | Obtiene rankings de armas de una mano, dos manos y distancia a partir de las piezas equipadas y sus puntuaciones; omite la fila cuando no existe pieza elegible. | 4 |
| [5064b7371](https://github.com/AAEmu/AAEmu/commit/5064b737172cf5d3667be38825462d97f4559238) | Responde las pestañas del ranking, ordena posiciones y respeta mínimos de puntuación, nivel y grado. Corrige la señal que indica si una fila incluye datos adicionales. | 8 |
| [ce69e5d2c](https://github.com/AAEmu/AAEmu/commit/ce69e5d2cc360f09c11c8b284cc9a59db04184dd) | Corrige la identidad del titular de cada fila y responde la consulta de apariencia/equipo; emplea el ID de servidor adecuado. Las listas de refuerzo de ranuras todavía se envían vacías. | 7 |
| [8ae149592](https://github.com/AAEmu/AAEmu/commit/8ae149592f9dfc603dcc302433f42c6b9d50b829) | Persiste puntuaciones por titular y período para incluir jugadores desconectados; añade ciclos semanales/mensuales y reglas de empate. Requiere character_rank_scores. | 16 |
| [2c4dc2a3b](https://github.com/AAEmu/AAEmu/commit/2c4dc2a3b3b9f53d676f74c1f9e9d513f5bb30c8) | Cuenta experiencia, honor, puntos de vida profesional y labor ganados/gastados por período. Integra su guardado con el personaje y añade character_game_point_totals. | 8 |
| [2476a6654](https://github.com/AAEmu/AAEmu/commit/2476a6654efa6e0a762cc534ca9bc3512b7291ef) | Actualiza tablas cada hora y hace el primer refresco al minuto del arranque. Conserva el guardado frecuente de contadores; el refresco incorpora liquidación de premios al integrarse la serie. | 7 |
| [5a6c1c5aa](https://github.com/AAEmu/AAEmu/commit/5a6c1c5aa970867f66ce1984cca9c2a3f424fd52) | Añade premios por posición de la temporada anterior y rank_period_payouts. El código final entrega antes de marcar el pago y omite monedas de titulares desconectados; la atomicidad debe corregirse antes de habilitarlo. | 7 |
| [e10c86397](https://github.com/AAEmu/AAEmu/commit/e10c86397bdbc05cfa47c5291b6e8286ed01d7c6) | Añade datos específicos de cada fila (objeto/gremio), tabla de nivel de gremios, columna sub_data y comando /rankrefresh. No todos los tipos de ranking tienen productor de datos. | 13 |
| [f5cbc0585](https://github.com/AAEmu/AAEmu/commit/f5cbc0585629639b41a81902f3175425af4fffa6) | Registra longitud y peso de peces al adquirirlos, persiste récords y alimenta las dos tablas de pesca. Revisar contra nuestro arreglo que conserva las medidas del pez y evita adquisiciones repetidas. | 9 |
| [03577ebec](https://github.com/AAEmu/AAEmu/commit/03577ebec27025e7d129090ea7106a12eca111a6) | Responde la vista de temporada anterior con el mismo período usado para premios; respeta el cuerpo observado sin timestamp final adicional. | 8 |
| [f5afe7560](https://github.com/AAEmu/AAEmu/commit/f5afe7560abc41c423b1326b1e318d10cc5ab53f) | Corrige la cabecera de datos personales para identificar al personaje, no al ranking, y agrupa todas sus tablas en una respuesta. Las respuestas anteriores eran descartadas por el cliente. | 2 |

### Antibot — 2 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [cf3f3632b](https://github.com/AAEmu/AAEmu/commit/cf3f3632ba06e2b8dc93829bcd8722203955aae6) | Introduce estado por personaje, refresca contadores y conecta el efecto bot-trial. No identifica todavía el paquete de la pregunta ni valida respuestas: no es un sistema antibot terminado. | 7 |
| [3617ff1d2](https://github.com/AAEmu/AAEmu/commit/3617ff1d27520a4d47aca115e394e43b8bc32a56) | Baja a Debug el caso de responder sin comprobación pendiente, que es el único estado posible mientras no exista el flujo de preguntas. | 1 |

### Seguridad de cuenta — 8 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [5e5b02dda](https://github.com/AAEmu/AAEmu/commit/5e5b02dda7dc2c47c1159563d80e18fb60596f56) | Responde al teclado de segunda contraseña con cuatro permutaciones de 62 caracteres, asociadas a la cuenta y ventana solicitante. | 5 |
| [921d42536](https://github.com/AAEmu/AAEmu/commit/921d42536cfca58e5d5bfc62bf8e7ffb0ab87f7e) | Implementa crear, verificar, cambiar y borrar la segunda contraseña y lee la contraseña nueva que se ignoraba. La persistencia y limitación de intentos llegan en c0ae976e6. | 7 |
| [c0ae976e6](https://github.com/AAEmu/AAEmu/commit/c0ae976e6c2efe001c394e5f2cd9e96692380a44) | Persiste sal/hash y fallos en account_second_passwords, limita a cinco intentos por minuto, usa aleatoriedad criptográfica para teclados y renueva la sal al cambiar contraseña. El límite temporal es una política del servidor, no un contrato retail confirmado. | 12 |
| [e062c05ee](https://github.com/AAEmu/AAEmu/commit/e062c05ee2748115c81292282684e07c6f343d4e) | Añade ventana temporal de protección por cuenta y bloqueos de destrucción, confirmación de intercambio y envío de correo. Queda tras feature 56 apagada; usa segunda contraseña como verificación, no una web retail. | 10 |
| [58d16e5d0](https://github.com/AAEmu/AAEmu/commit/58d16e5d0de60e80ce9607d656b3b67b0ea4e0a8) | Impide desactivar protección mediante un byte enviado al consultar estado; la consulta solo consulta. No prolonga el plazo al rechazar acciones y exige segunda contraseña verificada o comando GM para levantarla. | 7 |
| [957bd66ad](https://github.com/AAEmu/AAEmu/commit/957bd66ad1f43ec01cce6cb77013b4360926aa18) | Retira identificadores numéricos de cuenta de tres logs del guard para resolver alertas de CodeQL; conserva nombre y acción. | 1 |
| [e5c1f7426](https://github.com/AAEmu/AAEmu/commit/e5c1f74261641acbb79a889c1c7aa0f31b4e22d8) | Convierte el contador de protección a milisegundos al serializarlo. Una ventana de diez minutos se envía como 600000, sin alterar el formato del paquete. | 3 |
| [64920501d](https://github.com/AAEmu/AAEmu/commit/64920501d1f176d5031d85831ae50e810c2ef208) | Elimina comentarios de procedencia del layout de correo. No modifica sus campos, tamaños ni comportamiento. | 1 |

### Viviendas — 9 commits

| Commit | Aporte y límites | Archivos del commit |
|---|---|---:|
| [f01c28c20](https://github.com/AAEmu/AAEmu/commit/f01c28c20dbe6564498700a7e22eabebded8d001) | Carga destinos, paquetes, enlaces y materiales de remodelación y añade reglas de propietario, ruta, materiales y labor. Se solapa con nuestro catálogo y planificador ya existentes. | 4 |
| [91887a906](https://github.com/AAEmu/AAEmu/commit/91887a906763fd16269f316059c94d5c91a5b820) | Ejecuta la remodelación desde su habilidad, cobra y cambia el modelo/estado de vivienda con avisos al cliente y Zone. El camino final no verifica cantidades realmente consumidas ni conserva todas nuestras validaciones; adaptar sobre TryRebuildHouse. | 2 |
| [5db1cd010](https://github.com/AAEmu/AAEmu/commit/5db1cd0103b83f56da916cc9bc735f959484f415) | Añade /houserebuild create para preparar pruebas, pero inicialmente llama a una cotización que no construye. La corrección dace5d0f1 es obligatoria. | 1 |
| [00156087b](https://github.com/AAEmu/AAEmu/commit/00156087bb8fd08c200d0b41d8cdf7a0b9a11397) | Resuelve la vivienda abierta para CS 0x1AB, contesta SC 0x2BA y concede habilidades de remodelación. En la punta revisada envía una lista de cotizaciones vacía; el campo pd también difiere de nuestro double nativo. | 8 |
| [a4a884e23](https://github.com/AAEmu/AAEmu/commit/a4a884e23ccc98a72b0d452ff22f4f5c35d93497) | Obtiene el destino de remodelación del extra u32 del lanzamiento con flag 7 y lo resuelve por paquete/habilidad/vivienda. Evita interpretar ese extra como un encantamiento normal. | 8 |
| [4370ec2bb](https://github.com/AAEmu/AAEmu/commit/4370ec2bbddb356d7be18a06e75c721d88302041) | Mide el alcance desde el borde de la parcela usando GardenRadius, evitando rechazar a quien está dentro de una vivienda grande por distancia a su centro. | 1 |
| [901799b47](https://github.com/AAEmu/AAEmu/commit/901799b47ac89931b56ab5a51fca9a45960c3be3) | Indexa solo habilidades de destinos alcanzables desde paquetes. Excluye seis filas de prueba/huérfanas, incluida una que usaba la habilidad de ataque básico 2 y podía secuestrar ese lanzamiento. | 3 |
| [dace5d0f1](https://github.com/AAEmu/AAEmu/commit/dace5d0f1e55e8cf9433efef838c811c64539a70) | Corrige /houserebuild create para pasar por Build, consumir el diseño existente y anunciar éxito solo si aparece realmente una casa del diseño para el propietario. | 2 |
| [199b58086](https://github.com/AAEmu/AAEmu/commit/199b58086542cb110b2a07171ff3bbad76cc43f6) | Elimina una búsqueda por habilidad que devolvía un destino arbitrario cuando varios compartían habilidad; mantiene la resolución completa por paquete y extra del casteo. | 1 |

### Los 23 commits de merge

| Merge | Integración y resoluciones |
|---|---|
| [83576f61a](https://github.com/AAEmu/AAEmu/commit/83576f61a917e03caebf60a712d57217e7f3cad4) | Integra PR #1611: respuestas del panel de eventos. |
| [dd4b1ceef](https://github.com/AAEmu/AAEmu/commit/dd4b1ceef1b10ecf4327591a6052a6f2961ff568) | Integra PR #1604: catálogos y reglas de interacción de vehículos, con la corrección que restaura mascotas. |
| [00c2b4054](https://github.com/AAEmu/AAEmu/commit/00c2b40547e6a77800f02a10f420a3b07a2423e9) | Integra PR #1609: auras, provocación, reflexión, escudo de maná y absorción. |
| [ff217a08c](https://github.com/AAEmu/AAEmu/commit/ff217a08c702ad1d76386602760211187c715233) | Integra PR #1614: ticks, diagnósticos de carga, pasivas y mantenimiento del reparto World/Zone. |
| [ab01c6ca3](https://github.com/AAEmu/AAEmu/commit/ab01c6ca3e82b5fbf9f5c248b24115b6ee4a0e36) | Integra PR #1613: escala de multiplicadores de puntuación de equipo. |
| [c6a6dff41](https://github.com/AAEmu/AAEmu/commit/c6a6dff419b8018049bb0ed76ef76b6aeee99a6a) | Integra cast-pipeline-gates: cooldowns, cargas, validaciones, canalización, requisitos y áreas. |
| [d4d97dee0](https://github.com/AAEmu/AAEmu/commit/d4d97dee0d6e9543fbcc3bce699cb8ed14baccc1) | Integra effect-gaps y resuelve el cruce en ResetAoeDiminishingEffect conservando la ejecución del reinicio. |
| [93525fd09](https://github.com/AAEmu/AAEmu/commit/93525fd0935bb8e410b6fae31d1fcb02cef12b78) | Integra damage-effect-fields con los efectos anteriores: combina salud y reducción AoE. Su resolución pierde el DamageType al llamar a ReduceCurrentHp; requiere corrección. |
| [b29ff1167](https://github.com/AAEmu/AAEmu/commit/b29ff116731da4172227eb39536bce866430f286) | Integra special-effects-and-plots: resuelve PlotManager, condiciones y Skill, y prefiere la ruta de cargas de UnitCooldowns frente a la implementación alternativa. |
| [da75d765a](https://github.com/AAEmu/AAEmu/commit/da75d765a2f1aa44dfdf9da7821ae62df8f89c85) | Integra buff-restrictions conservando las dos guardas de casteo. La segunda usa la variante estricta sin permisos de liberación; requiere corrección. |
| [caec2eae5](https://github.com/AAEmu/AAEmu/commit/caec2eae5750d299adde115838c5e344e42afe4d) | Integra formulas-stats-controllers: combina filtros de enable y owner_type, coste de tick, críticos y reglas de curación. Incluye resoluciones en cuatro archivos. |
| [5044b7892](https://github.com/AAEmu/AAEmu/commit/5044b7892abb4f372276944fb82010bc1e9ae09b) | Integra PR #1615: reúne las series de habilidades y sus correcciones de integración, curación porcentual, cargas y documentación. |
| [8b678d2f1](https://github.com/AAEmu/AAEmu/commit/8b678d2f1446df4872a293b4da8d7e228ffbbc76) | Integra PR #1591: residencia, cuerpos de paquetes de protección e inscripciones de asedio. |
| [0bf80779f](https://github.com/AAEmu/AAEmu/commit/0bf80779fb266bf6a7ea61eac03469aa500779d3) | Integra PR #1596: bloqueo de objetos, persistencia visual y retraso de desbloqueo. |
| [f75ca7c3f](https://github.com/AAEmu/AAEmu/commit/f75ca7c3fe6a8ba367d40b0d0c0bde54f4cdb738) | Integra PR #1597: filtro de contenido generado desde tablas con el formato final corregido. |
| [63cf2e52d](https://github.com/AAEmu/AAEmu/commit/63cf2e52d9feb4f0e8c3acbfca8dab1507ee531c) | Integra PR #1598: sesión musical de conjunto y flujo de interpretación. |
| [a376a85b9](https://github.com/AAEmu/AAEmu/commit/a376a85b97ebe05ea221cc5ced2720a2cf86e54b) | Integra PR #1602: serie de rankings, persistencia, premios, gremios y pesca, incluidas correcciones de identidad. |
| [12323bad5](https://github.com/AAEmu/AAEmu/commit/12323bad57e9a460c6bbc9810838cbe04e5e3275) | Integra PR #1603: estado y refresco antibot, aún sin preguntas ni validación. |
| [b63cd07f2](https://github.com/AAEmu/AAEmu/commit/b63cd07f2c732857dc1c8dd1903f01ec79e003ad) | Integra PR #1606: teclado de segunda contraseña, operaciones, persistencia y limitación de intentos. |
| [4b31d751b](https://github.com/AAEmu/AAEmu/commit/4b31d751b7b29fa23e74090a2953e5d56e656982) | Integra PR #1620: corrección de polaridad de requisitos y documentación de la prueba con monturas. |
| [b1eca397d](https://github.com/AAEmu/AAEmu/commit/b1eca397d9df70ecfaf1b415f17ee6bd5e8f4429) | Integra PR #1617: equipos y miembros de asedio, equipo offline y exclusión de personajes borrados. Uno de los tres merges más recientes. |
| [6c6b6484e](https://github.com/AAEmu/AAEmu/commit/6c6b6484e08769a547a39b298dc5437fce651947) | Integra PR #1621: protección de operaciones sensibles y correcciones de consulta, logs y milisegundos. Uno de los tres merges más recientes. |
| [30837660a](https://github.com/AAEmu/AAEmu/commit/30837660a75e4beef5a38f37bf95809edf055f53) | Integra PR #1618: reconstrucción comunitaria de remodelación, alcance de parcela y comando de construcción. Punta padre fijada en esta revisión. |

## Anexo: los 20 archivos con conflictos

- `AAEmu.Game/Core/Managers/ItemManager.cs` — contenido.
- `AAEmu.Game/Core/Packets/C2G/CSEquipmentsSecurePacket.cs` — contenido.
- `AAEmu.Game/Core/Packets/C2G/CSEquipmentsUnsecurePacket.cs` — contenido.
- `AAEmu.Game/Core/Packets/C2G/CSItemSecurePacket.cs` — contenido.
- `AAEmu.Game/Core/Packets/C2G/CSItemUnsecurePacket.cs` — contenido.
- `AAEmu.Game/Core/Packets/C2G/CSRebuildHouseTaxInfoPacket.cs` — contenido.
- `AAEmu.Game/Core/Packets/C2G/CSStartSkillPacket.cs` — contenido.
- `AAEmu.Game/Core/Packets/G2C/SCOffsets.cs` — contenido.
- `AAEmu.Game/Core/Packets/G2C/SCRebuildHouseTaxInfoPacket.cs` — add/add.
- `AAEmu.Game/Models/Game/Char/Character.cs` — contenido.
- `AAEmu.Game/Models/Game/Skills/Buff.cs` — contenido.
- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/RebuildHousing.cs` — contenido.
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotTree.cs` — contenido.
- `AAEmu.Game/Models/Game/Skills/Skill.cs` — contenido.
- `AAEmu.Game/Models/Game/Skills/SkillObject.cs` — contenido.
- `AAEmu.Game/Models/Game/Skills/ZoneAuthorityCombat.cs` — contenido.
- `AAEmu.Game/Models/Game/Units/BaseUnit.cs` — contenido.
- `AAEmu.Game/Models/Game/Units/Unit.cs` — contenido.
- `AAEmu.UnitTests/Game/Core/Packets/G2C/SCHouseTaxInfoPacketTests.cs` — add/add.
- `AAEmu.UnitTests/Game/Core/Packets/G2C/SCRebuildHouseTaxInfoPacketTests.cs` — add/add.

## Anexo: los 27 archivos solapados que Git combina automáticamente

- `AAEmu.Game/Core/Managers/HousingManager.cs`.
- `AAEmu.Game/Core/Managers/SaveManager.cs`.
- `AAEmu.Game/Core/Managers/SkillManager.cs`.
- `AAEmu.Game/Core/Managers/World/WorldManager.cs`.
- `AAEmu.Game/Core/Packets/C2G/CSNotifyInGameCompletedPacket.cs`.
- `AAEmu.Game/Core/Packets/C2G/CSNotifyInGamePacket.cs`.
- `AAEmu.Game/Core/Packets/G2C/SCCharacterStatePacket.cs`.
- `AAEmu.Game/GameData/HousingGameData.cs`.
- `AAEmu.Game/GameData/SlaveGameData.cs`.
- `AAEmu.Game/Models/Game/Char/GearScoreCalculator.cs`.
- `AAEmu.Game/Models/Game/Char/Inventory.cs`.
- `AAEmu.Game/Models/Game/Items/Containers/LootingContainer.cs`.
- `AAEmu.Game/Models/Game/NPChar/Npc.cs`.
- `AAEmu.Game/Models/Game/Skills/Effects/BuffEffect.cs`.
- `AAEmu.Game/Models/Game/Skills/Effects/SpawnEffect.cs`.
- `AAEmu.Game/Models/Game/Skills/Plots/PlotCondition.cs`.
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotNode.cs`.
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotState.cs`.
- `AAEmu.Game/Models/Game/Skills/Plots/Tree/PlotTargetInfo.cs`.
- `AAEmu.Game/Models/Game/Skills/SkillCastWire.cs`.
- `AAEmu.Game/Models/Game/Skills/Templates/BuffTemplate.cs`.
- `AAEmu.Game/Models/Game/Units/Buffs.cs`.
- `AAEmu.Game/Models/Game/Units/UnitEvents.cs`.
- `AAEmu.Game/Program.cs`.
- `AAEmu.Game/WorldIntegration.cs`.
- `AAEmu.UnitTests/Game/Models/Game/Skills/BuffToleranceAddBuffTests.cs`.
- `AAEmu.WorldServer/AAEmu.World/Core/Relay/CombatRelay.cs`.

## Artefactos y trazabilidad

- [Inventario completo](inventory.json): hashes, padres, fechas, autores, mensajes y archivos de los 139 commits; solapamientos y conflictos.
- [Inventario explicado en español](reviewed-commits.json): 139 entradas con explicación, grupo y enlace al commit.
- [Mensajes originales](commit-messages.txt): texto completo de los commits, incluidas sus limitaciones y pruebas declaradas por los autores.
- [Diff neto](upstream.patch): cambios del padre respecto de la base común.
- [Resoluciones de merges upstream](upstream-merge-resolutions.patch): remerge-diff, incluidas las regresiones de permisos y tipo de daño.
- [Simulación de nuestra fusión](merge-tree.txt): resultado completo de Git; `simulation/` contiene los archivos solapados simulados.
- [Commits propios](local-commits.txt): inventario de los 92 commits del fork que se deben preservar.
- [Evidencia de contenido](content-evidence.json): consultas SQLite focales en solo lectura.
- [Verificación del informe](verification.json): cobertura 139/139 y comprobación final de HEAD, limpieza y punta remota.

Las copias `upstream/` son evidencia fijada al SHA revisado; `simulation/` contiene conflictos y no es una versión ejecutable. No utilizar esas carpetas como runtime.

Comprobación remota final: **2026-09-18T15:07:30.023185+00:00**; punta `30837660a75e4beef5a38f37bf95809edf055f53`. HEAD local intacto y repositorio limpio.
