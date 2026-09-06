# Ipnya: activación e implementación en AA10 r575

**Aceptación del usuario — 2026-09-06:** confirma que todo funciona, que los cambios se aplican y que cada nivel de ranura aumenta el nivel de objeto. Quedan aceptados el flujo visible de Ipnya y el casteo corregido. Esta confirmación no equivale a ejecutar todas las combinaciones o pruebas negativas posibles. Los apartados de aceptación pendiente más abajo son históricos y quedan sustituidos por esta confirmación.

Actualizado el 6 de septiembre de 2026 después de la autorización de implementación. **La mecánica está implementada y desplegada en Game; la aceptación visual con el cliente sigue pendiente. No se modificó `game_pak` ni ninguna DLL nativa.** El diagnóstico original se conserva al final como antecedente y sus afirmaciones de soporte ausente describen el estado anterior.

## Corrección posterior de la presentación del casteo

El usuario confirmó la ventana, el consumo y el aumento deEXP. Se detectó y corrigió una omisión en `SkillCastWire.WriteSkillCastExtra`: Started/Fired anunciaban los tipos22/23 sin escribir sus cuerpos de6/2bytes. Eso desplazaba los tiempos y demás campos al leerlos el cliente. El cambio completa esos cuerpos; mantiene el casteo nativo de3,5s y sus animaciones108/100 y grupoFX1291. Cuatro pruebas del paquete completo fallan antes del cambio y pasan después; la suite queda en1838/1838. La presentación visual corregida está pendiente de una nueva prueba real. Detalle y despliegue: [checkpoint de casteo](E:/AAEmu/rama_10/server/AAEmu/reconstruccion_cliente_10/checkpoints/CHECKPOINT_IPNYA_CAST_UX_20260906.md).

## Qué quedó habilitado

`equipSlotEnchantment` (197) se activa tanto en el archivo versionado como en el bind mount de Game, editados por separado para preservar sus diferencias. Requiere nivel de personaje 50. La ventana de personaje debe mostrar el acceso a Ipnya después de volver a entrar; el cliente ya contenía la interfaz y las tablas necesarias.

- Experiencia por ranura, con elección de receta, materiales y coste del catálogo r575. El exceso se descarta tras la confirmación que ofrece el cliente; llenar la barra no aumenta automáticamente el nivel.
- Promoción separada con las runas y cantidades de la fila del nivel actual. Armadura y armas llegan a nivel 10; accesorios de apoyo a nivel 4. No se activaron recetas residuales que exigen nivel 15.
- Efectos de los 38 hitos, selección por los pesos positivos de sus descriptores y sustitución con el objeto 46682. Se excluye el efecto anterior al sustituirlo: `ui_texts` 9256 dice «교체 시 기존 효과는 재적용되지 않습니다.» (al sustituir, el efecto existente no se vuelve a aplicar). Los cinco modificadores sin hito válido quedan fuera del catálogo operativo.
- Mejora del nivel de objeto usado en las fórmulas de combate mediante la fórmula 69 y los tres grupos de bonos acumulativos. La mejora pertenece al personaje y a la ranura; mover el objeto al bolso elimina esa contribución del objeto. Los pesos básicos de fuerza/destreza/etc. mantienen el nivel del template, como exige config359 en el código nativo.
- Persistencia inmediata de las ranuras, sus efectos, el coste y los objetos consumidos en una misma transacción MySQL. El autoguardado y el guardado directo comparten una exclusión con la operación para no sobrescribir su pago. No se guardan copias periódicas obsoletas de las tablas de Ipnya.

## Contratos cerrados durante la implementación

El auditor compara 71 funciones del proyecto Ghidra con los bytes del cliente principal actual; todas coinciden. La identidad sigue siendo x64, DLL SHA-256 `405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`. Direcciones siguientes expresadas como RVA, base `0x39000000`.

| Contrato | Evidencia r575 | Implementación |
|---|---|---|
| Contexto de skill 22 | `AC3780`: u8 ranura, u32 descriptor de material, bool autoUseAAPoint | SkillObjectEquipSlotReinforceMaterials; el byte inputDirection permanece fuera del cuerpo |
| Contexto de skill 23 | `AC3780`, API `192F40`: u8 ranura, i8 nivel de hito | SkillObjectEquipSlotReinforceEffect; no se confunde con índice visual |
| Promoción | CS `0x1D4`, un byte de ranura; `190770` | CSEquipSlotReinforceLevelUpPacket |
| Progreso | SC `0x2C5`, `3D6DB0/AA54E0`: bc3 unidad, u8 ranura, i8 nivel, i32 EXP | SCEquipSlotReinforceUpdatePacket, transporte Game nivel 1 |
| Efecto | SC `0x2C6`, `3D6E90/AA55E0`: bc3 unidad, u8 ranura, i8 hito, u32 modificador | SCEquipSlotReinforceLevelEffectUpdatePacket |
| Eliminación de efecto | SC `0x2C7`, `3D6F70/AA56E0`: bc3 unidad, u8 ranura, i8 hito | Serializer disponible; la progresión actual no necesita eliminar hitos |
| Estado inicial | `A41200/A43710`: u32 cantidad; ranuras i32/u8/i32; u32 cantidad; efectos u8/i8/u32 | SCCharacterState y UnitStateCharacterSerializer, también para el snapshot WZ de entrada |
| Receta por nivel | `B933C0` filtra igualdad exacta de ranura y nivel; `B90540` usa la fila actual para las runas | Planificador puro y catálogo validado |
| Estadísticas | `B90400`, `9774D0`, `BF5510`, `BCED20`; configs359/360 | Fórmula69 sólo en parámetros de combate y bonos de unidad sin duplicación |
| Bonos conjuntos | `B91C60/B91F00`, niveles iniciales1 y todos los umbrales alcanzados | Tres grupos acumulativos; 44 bonos máximos: 38 hitos + 6 valores conjuntos |

Las habilidades 38363 y 38664 llegan a SpecialEffect161/163 al terminar el casteo nativo de 3,5 segundos a través del pipeline existente. No se inventa una habilidad nueva ni un requisito de aprendizaje. El pago publica una transacción de inventario `ConsumeSkillSource` (13) seguida del resultado de progreso/efecto. Este orden usa el mecanismo existente del servidor; su actualización visual completa deberá confirmarse en la aceptación retail, no queda demostrada por pruebas de bytes solamente.

La selección usa los pesos explícitos de los descriptores r575 y excluye la opción anterior, según la regla UI nativa. No se afirma haber recuperado el generador pseudoaleatorio del World comercial ni su semilla; el muestreo del emulador usa Random.Shared sobre esos pesos.

## Game, Zone y estadísticas

`CombatRelay.RelayStartSkill` recibe las peticiones de la IA y ejecuta `Skill.Use` en Game; `DamageEffect` calcula allí daño/mitigación y transmite el resultado a Zone mediante WZUnitDamaged. Por eso las fórmulas y bonos de Ipnya deben integrarse en Game, y ya lo están. Después de confirmar una mejora se sincronizan los puntos HP/MP por el puente WZ existente.

La lista completa de Ipnya viaja también en el snapshot del personaje al entrar o cambiar de Zone. No se envía otro WZUnitState sobre un personaje existente: el consumidor nativo exacto `36B560 -> 36B3C0` rechaza unidades duplicadas. Ambas funciones se anclan al DLL Zone SHA-256 `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`. No se encontró un paquete WZ específico de Ipnya en los símbolos/RTTI inspeccionados. La copia interna de sus listas en Zone se renueva con la entrada; no se atribuye una sincronización incremental de esas listas que el protocolo inspeccionado no ofrece. No se operó el lifecycle de ninguna Zone.

## Validación ejecutada

- Restore y build Release correctos; suite completa: **1.834/1.834**, sin errores ni omitidas. Incluye bytes exactos de contexto, estado inicial y resultados; rechazos, desbordamiento, promoción no repetible, intervalos de peso, exclusión del efecto anterior, bonos y pago sin mutación ante fallo.
- Verificador contra la compact runtime en sólo lectura: 124 niveles, 2.235 recetas catalogadas, **756 recetas aplicables**, 108 promociones y 38 hitos recorridos. Carga 174 modificadores válidos y excluye cinco huérfanos.
- Prueba MySQL con una base temporal exclusiva, eliminada al terminar: utiliza el método Persist y repositorio reales; comprueba guardar un stack aún no autoguardado, cobrar, recuperar 16 ranuras y 38 efectos, revertir una escritura fallida después del cobro SQL, borrar un stack agotado y rechazar un propietario inexistente. No escribe personajes reales.
- Prueba de fórmula69 en ambos tramos (niveles de objeto 20/40/55), equipo frente a bolso, bandera apagada y 44 bonos máximos. Se usa el ParentUnit del contenedor para resolver la ranura incluso antes del registro del personaje en World.
- Las cinco SQLite comparadas pasan quick_check; las tablas mecánicas coinciden. El runtime no recibe una compact nueva. Los avisos ya presentes de análisis de código y NU1903 no se eliminaron como parte de esta tarea.

Reproducción:

```powershell
dotnet restore
dotnet build --configuration Release --no-restore
dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore
dotnet run --project reconstruccion_cliente_10/tools/IpnyaCatalogVerify --configuration Release -- .server_files/AAEmu.Game/Data/compact.sqlite3 --mysql
C:/Python313/python.exe reconstruccion_cliente_10/scripts/audit_ipnya_slot_reinforce.py
```

El argumento `--mysql` es optativo: crea una base con nombre aleatorio, usa las credenciales del Config.json local sin imprimirlas y borra únicamente esa base en finally. Requiere MySQL AA10 en 127.0.0.1:24306. Sin ese argumento sólo lee la SQLite.

## Despliegue, reversión y aceptación

Imagen nueva `14f9dbe048aeaeaa7b0a6a4ae0f7bb5fd59a04285ebb9c772728f03f579fb873`. Migración `SQL/updates/2026-09-06_aaemu_game_equip_slot_reinforce.sql`, reproducida también en el esquema inicial. La migración sólo añade dos tablas InnoDB; no concede progreso ni materiales a jugadores.

Respaldo después de detener Game: `E:/AAEmu/rama_10/backups/ipnya-20260906/aaemu_game.sql`, SHA-256 `de94bf1a7c99dd79b85b72643ab2c8a0812bab007ace5fc1b3958d2d4d3e20c9`. En la misma carpeta están ambos Features.json originales. Imagen anterior conservada como `aaemu-world:rollback-pre-ipnya-20260906` (SHA `42068216132721de2e0843ac68820dd8a14fa47aa6ca7cf19bce99151e05cec6`).

Para deshabilitar sin perder progreso, poner sólo equipSlotEnchantment=false en fuente y bind mount y reiniciar Game. Para volver al código anterior, detener Game, etiquetar la imagen rollback como `aaemu-world:10.0.2.13-r575-local`, restaurar sólo esa bandera/configuración y recrear Game sin build. Conservar las nuevas tablas aunque el código anterior no las lea; restaurar toda la base sólo si se pretende revertir también el progreso posterior, porque eliminaría cambios de otras mecánicas/jugadores desde el respaldo. No ejecutar restauraciones destructivas de manera automática.

Primera aceptación: volver a entrar con personaje de nivel 50 o superior, abrir C y acceder a Ipnya. Después, una operación por vez: alimentar ranura, comprobar coste/EXP, promover con la runa, sustituir efecto distinto y reconectar para comprobar persistencia. Al cambiar equipo, los bonos del objeto deben corresponder a la nueva ranura. Los materiales y sus rutas de adquisición existentes se mantienen; no se inventan recompensas, precios ni drops para hacer la prueba. Si hacen falta materiales de ensayo, usar el canal GM interno autorizado `give-test-items.ps1`, nunca inserts de inventario.

El checkpoint y el manifest de esta frontera conservan las comprobaciones de arranque y hashes finales. **No marcar aceptación visual o combate en cliente como completados hasta recibir y comprobar la prueba real.**

---

# Diagnóstico previo a la implementación (histórico)

Informe del 6 de septiembre de 2026. Alcance: revisión de solo lectura de la mecánica que mejora **las ranuras de equipo del personaje**, conocida como Ipnysh Artifacts / Equipment Slot Enhancement. No es una mejora del objeto equipado ni una misión de los Ipnya. No se activó la función ni se modificaron paquetes, DLL, configuración, base de jugadores o servicios.

**Conclusión: el bloqueo visible actual se controla desde el servidor. No hay una necesidad demostrada de modificar `game_pak` para mostrar Ipnya. Sin embargo, poner el interruptor en `true` no la haría funcional: faltan las transacciones, persistencia, efectos y respuestas de red del servidor.** El camino recomendado es completar ese soporte y activar la bandera al final. El paquete español puede seguir con su proceso de traducción.

El diagnóstico y el plan de trabajo están completos para este alcance. La reconstrucción de los contratos de red y fórmulas indicada más abajo sigue pendiente; este documento no se presenta como una implementación lista para desplegar ni como prueba de aceptación dentro del juego.

## Evidencia y alcance comprobado

Target: `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`; HEAD `bdad11fec1493c43a854369e707de72a20f26f86`. Padre consultado: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`, commit `6273a02f0c88f3c48e52252c3e64ae7e71d63945`. El árbol tenía cambios previos de otras tareas, que se conservaron. No se hizo merge ni cambio de rama.

Cliente principal: `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`, Bin64, canal interno `en_us`. Se comparó con el paquete de referencia local `ArcheAge-Returns-10.0.2.13-r575`; «referencia» aquí identifica ese archivo local, no certifica que todos sus contenidos sean una distribución virgen.

Se extrajeron **21 entradas por paquete**: 20 Lua/ALB relacionadas con la pantalla de personaje e Ipnya, más `game/db/compact.sqlite3`. Las 20 entradas de interfaz coinciden byte por byte entre ambos paquetes. Esto incluye los nueve ALB de `scriptsbin64`, no solo fuentes Lua que podrían no ejecutarse. Los archivos sueltos españoles y la compact extraída del paquete tienen el mismo SHA-256. No se alteró ninguna entrada; tamaño y fecha de modificación de cada paquete permanecieron constantes durante la extracción. No se calculó el hash de los aproximadamente 74 GB del paquete español: la identidad de esta revisión se fija por entrada.

Los siete catálogos se auditaron en cinco bases: completa, compact del paquete de referencia, compact del paquete español, compact española suelta y compact del servidor. Las **seis tablas operativas coinciden en todos sus campos mecánicos** en las cinco bases. El enum de atributos está en la completa y en el servidor; su ausencia en compact retail es una proyección, no falta de contenido. Las cinco bases devuelven `ok` en `PRAGMA quick_check`.

Evidencia íntegra: [carpeta forense](E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/ipnya-slot-reinforce-frontier), [catálogo y comparaciones](E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/ipnya-slot-reinforce-frontier/catalog-audit.json), [auditor reproducible](E:/AAEmu/rama_10/server/AAEmu/reconstruccion_cliente_10/scripts/audit_ipnya_slot_reinforce.py).

## Qué la mantiene oculta y cómo se habilitará

La bandera es **`equipSlotEnchantment = 197`** en [Feature.cs](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Models/Game/Features/Feature.cs:179). [FeaturesManager](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Core/Managers/FeaturesManager.cs) parte de un conjunto vacío; los flags no declarados quedan apagados. La clave no estaba declarada ni en el archivo de fuente ni en el montado durante esta inspección.

El registro de inicio del Game activo confirma que el byte 24, contando desde cero, vale `04`. La máscara de Ipnya es `20` hexadecimal: `04 & 20 = 00`. La función está apagada en el estado calculado por el servidor, no simplemente escondida por una traducción. `SCInitialConfig` serializa ese `fset` de 31 bytes. Este informe no tomó una captura nueva del tráfico al cliente.

La interfaz extraída hace lo siguiente:

1. `equipped_item_view.lua` crea los botones solo si `X2Player:GetFeatureSet().equipSlotEnchantment` está activo.
2. `equipped_item.lua` crea `CreateEquipSlotReinforceWindow` bajo la misma condición.
3. `equip_slot_reinforce/logic.lua` vuelve a comprobar la bandera y consulta `SuitableLevelForEquipSlotReinforce()` para mostrar el botón según el nivel.
4. La API nativa compara el nivel con `content_configs[237]`, cuyo valor es **50**. No hace falta inventar una misión de desbloqueo: no se encontró tal requisito en este recorrido.

Una vez implementado y validado el soporte, el cambio de configuración previsto es añadir **dentro del objeto existente `Features.Flags`**:

```json
"equipSlotEnchantment": true
```

Debe aplicarse tanto a [configuración fuente](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Configurations/Features.json) como a [configuración montada](E:/AAEmu/rama_10/server/AAEmu/.server_files/AAEmu.Game/Configurations/Features.json), preservando las demás claves. Sus hashes actuales difieren: no conviene copiar uno entero sobre el otro. El archivo visto dentro del contenedor coincide con el montado. No añadir flags con nombres inventados ni sustituir todo el `fset` por bytes fijos.

Después del despliegue, reiniciar únicamente el servicio Game necesario y reconectar el cliente para recibir la configuración inicial. Comprobar archivo fuente, archivo montado, bit calculado y recepción/UI. Con la instantánea actual, el byte sería `24` en lugar de `04`; el criterio duradero es `(byte24 & 0x20) != 0`, pues otras funciones pueden cambiar.

**Esto es la fase final de activación, no una instrucción para encenderla ahora.** Para una prueba inicial aislada de interfaz también habría que rechazar todas las operaciones sin consumir recursos mientras el backend siga incompleto.

## Comprobación nativa de los controles

Se consultó el proyecto Ghidra release en modo `-readOnly -noanalysis`. Su DLL de análisis tiene SHA-256 `2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76`. La DLL principal actual tiene SHA-256 **`405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`**, arquitectura x64. No se asumió que fueran iguales: **los bytes de las ocho funciones exportadas coinciden íntegramente por RVA con la DLL actual**. Resultado en `catalog-audit.json/native_reanchor`.

| RVA, base de análisis `0x39000000` | Hallazgo observado |
|---|---|
| `0x8457B0` | Construye la tabla de features Lua. `equipSlotEnchantment` usa máscara `0x20`; `equipSlotFormulaItemLevel` consulta índice `0x167` (359); `equipSlotBundleEffect` consulta `0x168` (360), ambos activos si el resultado es mayor que cero. |
| `0x1948A0` | Registro de las APIs `X2EquipSlotReinforce`, incluidos sus nombres y argumentos. |
| `0x191F70` → `0xB903E0` | `SuitableLevelForEquipSlotReinforce`; compara nivel con la configuración `0xED` (237). |
| `0x98A660` | Getter de configuración indexada usado por los controles anteriores. |
| `0x192550` | `StartReinforceLevelup`: resta uno al índice visual y crea una tarea de confirmación. |
| `0x193DB0` | `StartReinforceAddExp`: resta uno al índice visual, construye contexto interno con discriminante `0x16` (22), ranura y material; contempla confirmación por exceso de experiencia. |
| `0x192F40` | `ChangeLevelEffect`: construye contexto interno con discriminante `0x17` (23); convierte la ranura visual y resuelve el efecto antes de lanzar la acción. |

Los discriminantes 22/23 son evidencia del contexto interno; **todavía hay que seguir sus serializadores para certificar anchos, orden y cola de `CSStartSkill` en wire**. No convertir el layout de memoria directamente en formato de paquete.

Hay un comentario engañoso en la cabecera de `Feature.cs` que asocia 359/360 a `SCSystemFeatureStateListPacket`. Para Ipnya, la evidencia de esta revisión muestra getters de configuración indexada y filas homónimas en `content_configs`; no se debe implementar agregando arbitrariamente entradas 359/360 a aquel paquete. La corrección del comentario queda propuesta, no aplicada.

## Catálogo y reglas que deben conservarse

| Tabla | Filas | Uso previsto |
|---|---:|---|
| `equip_slot_reinforces` | 124 | Niveles por ranura, experiencia, atributo, contribución al nivel de objeto, ítem/cantidad para subir nivel. |
| `equip_slot_reinforce_materials` | 2.235 | Opciones de alimentación: nivel requerido, experiencia, moneda, costo y conjunto de materiales. |
| `equip_slot_reinforce_level_effects` | 38 | Niveles que desbloquean efectos por ranura. |
| `equip_slot_reinforce_unit_modifiers` | 179 | Atributos, tipo de modificador, valor y peso de las opciones de efecto. |
| `equip_slot_reinforce_set_effects` | 6 | Variante de efectos de conjunto por atributo. |
| `equip_slot_reinforce_bundle_effects` | 3 | Variante de bonos conjuntos por umbrales de ataque, defensa y soporte. |
| `enum_equip_slot_reinforce_attributes` | 3 | Ataque, defensa y soporte. |

Son **16 ranuras**: siete de armadura y tres de armas con niveles catalogados 1–10; seis de accesorios/instrumento con niveles 1–4. Los índices presentes son `0,1,2,3,4,5,6,7,9,10,11,12,15,16,17,18`, compatibles con el enum de ranuras cero-based. No confundirlos con las claves de `enum_equip_slot_types`, ni con los índices visuales Lua que las funciones convierten restando uno. Se debe cerrar el mapping en el servicio y sus pruebas.

Los efectos aparecen en 5/10 para las ranuras de diez niveles y en 2/3/4 para las de cuatro. Los umbrales de los tres bundles son respectivamente ataque/defensa/soporte `12/28/12`, `21/49/18` y `30/70/24`. Las descripciones mencionan vida/maná, defensas y reducciones PvP/críticas; su traducción no sustituye la fórmula o unidad nativa del atributo.

Configuración de este cliente:

| ID | Nombre | Valor |
|---:|---|---:|
| 236 | `equip_slot_reinforce_change_level_effect_item` | 46682 |
| 237 | `equip_slot_reinforce_enable_min_level` | 50 |
| 359 | `equip_slot_reinforce_item_level_formula` | 1 |
| 360 | `equip_slot_reinforce_bundle_effect` | 1 |

Materiales principales, con nombre inglés del catálogo runtime para identificar los IDs independientemente de la traducción:

| Ítem | Nombre | Papel catalogado |
|---:|---|---|
| 51594 | Gedlon's Strength | Material de experiencia. |
| 51595 | Herstan's Resilience | Material de experiencia. |
| 51596 | Yordan's Wisdom | Material de experiencia. |
| 51602 | Demigod Essence | Parte de conjuntos de materiales adicionales. |
| 51597 / 51598 / 51599 | Ewan's Rune Rank 1 / 2 / 3 | Requisitos de subida de nivel según fila. |
| 46682 | Bound Serendipity Stone | Cambio de efecto, configuración 236. |

Los tres materiales base tienen cuatro referencias de producto de crafting y dos de mercancía cada uno; las runas tienen 4/2/1 referencias de crafting respectivamente, y la esencia cuatro. Esto prueba referencias de catálogo, **no que los NPC, recetas, drops o tiendas necesarios estén disponibles y habilitados en el mundo actual**. Se guardaron las filas de crafting y mercancía en el auditor; queda una prueba de adquisición real por ruta elegida. La cobertura de loot no se cerró en este informe.

Hay datos residuales que requieren selección nativa, no una carga indiscriminada:

- **1.479 de las 2.235 opciones de material requieren nivel 15**, mientras el catálogo de niveles actual llega a 10 o 4. Incluyen materiales antiguos y de prueba. No son 2.235 opciones necesariamente utilizables. El filtro exacto de selección debe seguir el consumidor nativo.
- Los modificadores **170–174 apuntan a `equip_slot_reinforce_level_effect_id=40`, inexistente** en la tabla de efectos. Es igual en las bases comparadas: no es daño producido por la traducción. Deben registrarse como residuos no enlazables y nunca sortearse como opciones válidas.
- El efecto especial 34807 de tipo 161 existe pero no está enlazado por `skill_effects`; no asignarlo por conjetura.
- No hay conjuntos de materiales huérfanos ni IDs de ítem ausentes entre las referencias auditadas. Esto no prueba el resto de las relaciones del juego.
- El peso de una opción y las descripciones no bastan para decidir distribución aleatoria, exclusiones de reroll, redondeos, consumo o desbordamiento de experiencia.

## Qué falta en el servidor

| Capa | Situación observada | Trabajo necesario |
|---|---|---|
| Entrada de subida | [CSEquipSlotReinforceLevelUpPacket](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Core/Packets/C2G/CSEquipSlotReinforceLevelUpPacket.cs) solo lee un `sbyte`. Está registrado en nivel de transporte 1, opcode actual `0x1D4`. | Verificar contrato r575 completo y conectar una transacción autoritativa. El opcode indicado es el del código, no una captura nueva. |
| Alimentación | Skill 38363 → skill_effect 53325 → effect 68799 → special_effect 33820 → tipo 161. | Implementar `EquipSlotReinforceAddExp`, contexto 22 tras cierre wire, validación de materiales, costo y experiencia. |
| Cambio de efecto | Skill 38664 → skill_effect 54017 → effect 69959 → special_effect 34629 → tipo 163. | Implementar `EquipSlotReinforceChangeLevelEffect`, contexto 23 tras cierre wire, selección/sorteo y consumo del ítem configurado. |
| Ejecución de efectos | [SpecialEffect.cs](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Models/Game/Skills/Effects/SpecialEffect.cs) busca clases por nombre; no hay implementaciones para esos dos tipos. | Evitar retornos silenciosos o consumo parcial. El enum por sí solo no implementa la mecánica. |
| Contextos de skill | [SkillObject.cs](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Models/Game/Skills/SkillObject.cs) no implementa tipos 22/23. | Parsers/serializadores exactos y manejo de mensajes inválidos sin desalinear el paquete. |
| Estado inicial | [SCCharacterStatePacket](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Core/Packets/G2C/SCCharacterStatePacket.cs:101) escribe cero en las listas de ranuras y efectos. | Cargar y serializar estado persistido con el layout r575 confirmado. |
| Estado de unidad | [UnitStateCharacterSerializer](E:/AAEmu/rama_10/server/AAEmu/AAEmu.Game/Core/Packets/G2C/UnitState/UnitStateCharacterSerializer.cs:56) también escribe dos listas vacías. | Mantener el mismo contrato para entrada al mundo, visibilidad y resincronización. |
| Actualizaciones | No se encontraron clases `SCEquipSlotReinforce*` en AA10. | Cerrar opcodes, bodies, owners, orden de task/result/event y actualización/borrado de efectos. |
| Persistencia | No se encontró un modelo/repositorio/migración de progreso de Ipnya en el alcance de fuente y SQL revisado. | Estado por personaje y ranura; efectos elegidos estables; transacciones con inventario/moneda y carga al relog. |
| Estadísticas | No hay integración específica de este progreso. | Aplicar modificadores, fórmula de item level y bundles una sola vez; recalcular al cambiar equipo/estado y emitir stats. |

Las skills de alimentación y cambio tienen `casting_time=3500`, sin LP en sus filas; el cambio tiene cooldown 1000. Respetar el ciclo de casteo/interrupción en lugar de entregar experiencia al recibir el primer paquete. Que estas filas no cobren LP no elimina el costo en moneda/materiales del catálogo.

El catálogo `equip_slot_enchanting_costs` que ya carga ItemManager pertenece al circuito de temper/refurbishment. **No es un backend reutilizable de Ipnya por parecido del nombre.**

El padre comunitario consultado conserva el handler sin acción y las listas vacías: no hay una implementación terminada que baste traer por merge. AA8 contiene nombres de respuestas y offsets útiles como índice de búsqueda, pero tampoco ofrece aquí un backend completo; sus opcodes son sensibles a versión y no se proponen para AA10.

## Secuencia de implementación propuesta

1. **Cerrar contratos nativos r575.** Seguir los contextos 22/23 hasta sus serializers; confirmar request de level-up, respuestas de progreso/efectos, listas iniciales, tamaños, signos, cantidades, transporte y lifecycle. Partir de las RVAs verificadas de este informe. Determinar si los efectos se transmiten como fila de modificador, atributo o estructura propia. Documentar casos vacíos y máximos. No ensayar opcodes AA8.
2. **Cerrar reglas y cargar catálogo.** Servicio/manager específico `EquipSlotReinforce` —nombre propuesto, todavía inexistente— con tablas tipadas, índices por ranura/nivel y opciones válidas. Seguir consumidores de material, overflow, promoción, pesos, fórmula 359 y bundles 360. Registrar los cinco modificadores huérfanos y los materiales fuera del rango vigente. No modificar la compact para hacer utilizables datos residuales.
3. **Diseñar persistencia.** Clave `(character_id, equip_slot)` para nivel/experiencia y una colección de efectos seleccionados por su posición nativa. No atarla al UID del ítem equipado. Definir restricciones, revisión de concurrencia y migración reversible. No fijar anchos SQL antes de cerrar máximos y representación. Persistir el resultado del sorteo, no repetirlo al entrar al juego.
4. **Implementar operaciones atómicas.** Bajo bloqueo por personaje: validar bandera/nivel/ranura/opción, preparar costo y resultado, revalidar al finalizar casteo, consumir recursos y guardar progreso en una unidad de trabajo compatible con el inventario; publicar resultados tras commit. Un fallo, repetición, desconexión o carrera no debe duplicar progreso ni consumir recursos sin otorgarlo. Mantener el cambio de objeto equipado independiente del progreso de la ranura.
5. **Conectar stats y sincronización.** Reemplazar las dos listas vacías, añadir respuestas exactas y actualizar modificadores/item level/bundles. La UI escucha `EQUIP_SLOT_REINFORCE_UPDATE` y `EQUIP_SLOT_REINFORCE_MSG_CHAGNE_LEVEL_EFFECT` —la errata `CHAGNE` es el nombre real—. Comprobar actualización de inventario y estados de casting. Revisar integración de `CharRecordKind.EquipSlotReinforceAttribute=84` cuando corresponda, sin conceder logros solo por abrir la ventana.
6. **Validar antes de mostrar.** Pruebas de dominio, persistencia y fixtures de bytes procedentes de la evidencia nativa; build Release y suite de regresión AA10. Preparar imagen y respaldo de datos con flag apagado. Comprobar fuente frente a bind mounts. Habilitar solo tras cerrar los puntos anteriores y ejecutar aceptación con personaje de prueba.
7. **Activación final.** Aplicar el flag en las dos configuraciones, desplegar Game, reconectar y verificar bit/UI/operación/relog. El informe no requiere iniciar o detener Zones. Cualquier prueba posterior que lo necesitase debe respetar el perfil y la autorización de lifecycle del proyecto.

## Criterios de aceptación y rollback

| Prueba | Resultado que debe observarse |
|---|---|
| Flag apagado / personaje bajo nivel 50 | UI y servidor respetan el bloqueo; una petición manual tampoco muta recursos. |
| Nivel 50+, flag activo | Botón y ventana disponibles; listado correcto de las 16 ranuras. |
| Una alimentación válida | Casteo, consumo exacto y aumento único de experiencia; UI refleja el resultado sin reabrirse. |
| EXP llena, overflow y nivel máximo | Regla nativa confirmada, confirmación cuando aplique y ausencia de sobrepasos o cobros inútiles. |
| Subida de nivel | Requisitos de experiencia y runa comprobados; nuevo nivel, efecto y stats coherentes. |
| Cambio de efecto | Consumo correcto de 46682, opción válida persistida, mensaje de cambio y stats actualizados. |
| Cruce de umbral de bundle | Bono exacto, aplicado una vez y visible; sin sumar variante legacy accidentalmente. |
| Ítem retirado, dinero insuficiente, solicitud duplicada, interrupción | Rechazo o cancelación coherente, sin mutación parcial. |
| Cambio de equipo, relog y reinicio Game | La ranura conserva progreso y efectos; stats no se acumulan ni desaparecen. |
| Regresión | Temper, síntesis, reroll de objetos, sockets y otras skills conservan su protocolo y consumo. |

Antes de desplegar una implementación: conservar imagen anterior, configuraciones y respaldo consistente de las nuevas tablas y recursos afectados. Si falla la aceptación, apagar el flag en fuente/montaje y revertir imagen si procede, manteniendo el esquema y progreso para diagnóstico. **No borrar progreso ni restaurar solo el inventario o solo las ranuras**: produciría duplicaciones o pérdidas. Retirar el esquema únicamente después de exportar estado y verificar compatibilidad. Ningún rollback de cliente es necesario para el plan principal porque no contempla modificarlo.

Solo se justificaría un parche de `game_pak` si una prueba con backend correcto demuestra un fallo concreto adicional del cliente. En tal caso: coordinarse con la traducción, fijar hashes nuevos, respaldar por entrada, usar el builder/aplicador versionado y reextraer para comprobar. No tocar el modelo de la fuente de la misión anterior ni reutilizar parches de esas quests para Ipnya.

## Reproducción y límites de la entrega

El archivo `entries.txt` de la frontera contiene la selección exacta. `PakBatchExtract` se abrió con `openAsReadOnly: true`; sus CSV guardan tamaño/hash por entrada y los JSON de snapshot el estado exterior de cada paquete. El auditor usa conexiones SQLite `mode=ro`, conserva filas y proyecciones mecánicas, calcula hashes y valida las funciones contra el binario actual.

```powershell
Set-Location E:\AAEmu\rama_10\server\AAEmu
C:\Python313\python.exe reconstruccion_cliente_10/scripts/audit_ipnya_slot_reinforce.py
```

Dos ejecuciones consecutivas produjeron el mismo SHA-256 del resultado: `189150c7899f6c515a0ca69aa4d12e303fc165f9a0123cbf3b23d1a2e8b0e34e`. El script requiere Python con `pefile` y las extracciones existentes; no extrae ni modifica el paquete por sí mismo. Las consultas nativas reproducibles están en `Aa10IpnyaNativeAudit.java` y el extractor existente `Aa10WorldLevelNativeAudit.java`, invocados contra Ghidra en modo de solo lectura.

No se ejecutaron pruebas de gameplay ni se encendió el flag; no corresponde declarar aceptación retail, consumos correctos, economía disponible o persistencia operativa. Las coincidencias de catálogo y código nativo demuestran que el cliente conserva el sistema y localizan el bloqueo; las brechas de protocolo/fórmula son tareas concretas previas a una activación funcional.

Como corroboración histórica del nombre, el anuncio oficial de ArcheAge publicado en Steam en diciembre de 2021 denomina la función Equipment Slot Enhancement / Ipnysh Artifacts. Esa referencia no se utilizó para importar balance ni contratos de otra versión: [anuncios oficiales de Steam](https://store.steampowered.com/news/posts/?enddate=1638472340&feed=steam_community_announcements).
