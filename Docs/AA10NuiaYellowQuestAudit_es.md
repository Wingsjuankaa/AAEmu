# Misiones amarillas de Nuia: auditoría y reparación por mecanismos

> Diagnóstico inicial conservado. La implementación posterior y sus límites están
> en [Reparación de misiones amarillas de Nuia](AA10NuiaYellowQuestRepair_es.md).

## Conclusión

Es viable reparar familias completas de misiones cuando comparten una causa
demostrada: interacción con objetos, creación desde inventario, cambios de fase,
entrega de objetos o invocación de NPC. El color amarillo no identifica una sola
mecánica. La historia nuiana validada sirve como regresión del motor de misiones,
pero no valida automáticamente cosecha, crianza, barcos ni todas las funciones de
los objetos.

Este trabajo entrega **diagnóstico estático, matriz y plan de reparación**. No se
reprodujo en el cliente el bloqueo del caballo/bote y no se declara reparado.
No hay cambios de gameplay ni despliegue derivados de esta auditoría. El cliente,
las traducciones, las bases y los procesos Zone permanecen sin modificaciones.

## Alcance medido

Target `rama_10`, HEAD `45bba0ad49fee55ab30a80168b4d6caefbb9ac87`.
Padre consultado: `upstream/client_version/zone-10.0.2_r575`,
`67b51f17db333988f24daf86d219a7c6932a66a2`. No se integró ni cambió la rama.

Selección reproducible: `detail_id=1`, máscara occidental `(race & 13)!=0`,
zona cuyo grupo tiene `target_id=3`, excluyendo categorías raciales
`3,8,93,131,45,174`. Es una selección del catálogo, no de ofertas activas.

| Medida | Resultado | Interpretación |
|---|---:|---|
| Misiones normales seleccionadas | 2.567 | No equivale a 2.567 misiones disponibles |
| Asignadas a una zona distinta de la genérica 1 | 1.184 | Candidatas regionales; revisar requisitos y disponibilidad |
| Asignadas a la zona genérica 1 | 1.383 | Separadas de la cola regional; incluye contenido de prueba |
| Acciones habilitadas / tipos | 11.070 / 72 | Detalles presentes, iguales entre full y compact original; clases/cargadores de actos presentes |
| Plantillas de objetos referenciadas | 689 | Incluye proveedores compartidos y objetos dinámicos |
| Con una fuente `item_spawn_doodads` | 74 | No restaurar como objetos fijos por ausencia espacial |
| Sin posición nativa ni fuente de item identificada | 152 | Frontera de investigación, no 152 objetos demostrados como ausentes |
| Posiciones nativas en main_world | 7.405 | Las referencias compartidas también pueden tener posiciones fuera de Nuia |
| Discrepancias de presencia fuente/runtime | 4.571 posiciones / 353 plantillas | No autoriza a añadirlas en bloque |
| Filas mecánicas distintas comparadas | 18.898 | Incluye plantillas, fases, funciones, skills y enlaces de efectos |
| Diferencias de esas filas entre full y compact montada en Game | 0 | El servidor tiene los datos revisados |

Las 4.571 discrepancias se descomponen en 2.079 ausentes en ambos catálogos,
2.100 presentes solo en fuente y 392 solo en runtime. La comparación espacial
usa tolerancia de 0,01 unidades: parte de los hallazgos son redondeos. Tampoco
prueba rotación, fase, accesibilidad, carga geográfica ni interacción.

## Casos iniciales identificados

Los nombres se leen del compact español instalado; no se modificaron textos ni
estados de aprobación. El usuario no recuerda los nombres: estos son los
candidatos iniciales de Solzreed, no una identificación confirmada por captura.

| Misión | Flujo confirmado en datos | Estado de diagnóstico |
|---|---|---|
| 2393 — Una embarcación apta para el mar | NPC 7661; objeto 2853; skill 14006; entrega item 17863 | Cinco botes nativos, cinco en fuente y cuatro en runtime; discrepancia geométrica demostrada, causalidad del bloqueo pendiente |
| 4292 — Cuidado de animales | NPC 3636 → 10666; suministro 23608; recompensa semilla 23635 | Datos presentes; aceptación, suministro y entrega pendientes en cliente |
| 4294 — Alimentar a tu potro | Usar semilla 23635 → planta 4594; cosechar 21850; elegir potro 23680/23681/23682 | Plantación y cosecha pendientes de reproducción |
| 4295 — Un compañero veloz | Criar la variante elegida y obtener montura 8159/8160/8161 | Revisar cada variante y la condición de finalización en cliente |

### Bote: qué está demostrado

En `game/worlds/main_world/level_design/cells/014_013/doodad.g` existen cinco
instancias de 2853, con inclinación de aproximadamente 53 grados y escala 1.
El catálogo runtime tiene cuatro y usa 45 grados. Las coordenadas de fuente
también tienen pequeños redondeos. `boat-placements.json` conserva todos los
valores, sin sobrescribir el catálogo existente.

Contrato: Start **6378**, `DoodadFuncFakeUse` 1096 con `fake_skill_id=14006`
→ fase **6379**, `LootItem` 1672 entrega **17863** → fase **6380**, final y
respawn. El requisito de skill 19674 exige la misión **2393**. Un intento sin
la misión no es una prueba positiva válida.

`DoodadManager.GetFunc` ya consulta `DoodadFuncIncomingSkill.TemplateAccepts`,
que reconoce `FakeSkillId`; `InteractionEffect`/`Use` ya llegan a `Doodad.Use`.
No se justifica duplicar ese arreglo ni eliminar el requisito de misión.
La diferencia de geometría o un bote faltante **no demuestra por sí sola** por
qué otro bote visible no permitía interactuar.

### Caballo: qué está demostrado

La semilla 23635 usa la skill 13139 y `item_spawn_doodads` 234 apunta a 4594.
La planta inicia en **11305**, pasa mediante crecimiento a **11307**, acepta
la skill **17752**, entra a **11308** y entrega **21850**. Los tres potros
23680/23681/23682 producen **4725/4727/4743**. No tienen posiciones fijas en
las celdas nativas inspeccionadas: deben crearse con el item del jugador.

La ruta de servidor para plantación está en `CSCreateDoodadPacket` →
`CreatePlayerDoodad`, con permisos, consumo, inicialización, spawn y persistencia.
La skill 13139 también referencia `SummonDoodad` con doodad nulo; no basta esa
fila para declarar un fallo: hay que registrar cuál de las rutas usa el cliente.
No se agregaron plantas ni potros estáticos para eludir el proceso.

Las interacciones de crianza referencian fruto 21850 y agua 15694 como reactivos.
Hay que distinguir: item sin acción, colocación rechazada, objeto colocado pero
sin interacción, casteo rechazado, fase que no avanza y objetivo que no cuenta.
Cada uno exige una corrección diferente.

### Crecimiento: diferencia explicada por la configuración

Hay 313 filas de crecimiento de estos contratos cuyo `delay` en ambos compact
de cliente es cien veces menor que en full/servidor. **Las 313 coinciden con
full dividido por el `GrowthRate=100` montado**, antes del modificador de clima
que aplica `DoodadFuncGrowth`. Por ejemplo, la planta 4594 pasa de 30.000 ms
en full a 300 ms base con la configuración actual, igual al compact cliente.
Esto no es evidencia de un error de traducción o de una espera de 30 segundos.
No se cambiaron tiempos. El contador visual y la transición real siguen
requiriendo aceptación con cliente.

## Fronteras compartidas encontradas

De 47 tipos de función de objetos usados por las referencias, seis no tienen
clase/cargador local. No son los 72 tipos de acciones de misión, que sí existen.
La ausencia local requiere clasificar primero si ejecuta el cliente, Game o Zone.

El padre upstream consultado tampoco contiene `DoodadFuncSpawn` (sí las clases
distintas `SpawnGimmick` y `SpawnMgmt`). AA8 sí tiene una implementación que crea
NPC desde Game: se clasifica como **`structural_candidate`**, porque esa autoridad
de NPC no se puede trasladar automáticamente a AA10 con Zone nativa. El receptor
AA10 usa `template?.Use`; una plantilla no cargada no ejecuta la función en Game.

| Función | Dependencias identificadas | Prioridad |
|---|---|---|
| `DoodadFuncSpawn` | Objetos 1365, 2936, 11651; misiones regionales 1402, 1474, 2071 | P1: cerrar creación/ownership/lifetime de NPC con Zone antes de implementar |
| `DoodadFuncFxGroupCallback` | Objetos 2422 y 16621; misión regional 1933 | P1: comprobar callback visual y efecto necesario para progreso |
| `DoodadFuncHideMapIcon` | Grupo de objetos relacionado con misión regional 9872 | P2: determinar consumidor cliente; no asumir bloqueo de objetivo |
| `DoodadFuncBuildConditionUiOpen` y `DoodadFuncBuildConditionInfo` | Objeto 12870; referencias de zona genérica | P2: vivienda/construcción, fuera del piloto inicial |
| `DoodadFuncResidentTownhallUiOpen` | Objeto 13133; referencias de zona genérica | P2: cerrar consumidor antes de ampliar la alpha |

Adicionalmente, tres IDs referenciados no tienen plantilla en full
(1659, 2430, 12798); ocho referencias de NPC y dos de item tampoco tienen
plantilla. Solo el NPC 1706/misión 645 pertenece a una zona regional en esta
selección; los demás NPC y los dos items están en la zona genérica.
No se crearon plantillas sustitutas. `audit.json` conserva los vínculos exactos.

Otros 18 objetos y cinco skills existen en full pero no en los compact de
cliente consultados. No incluyen bote, planta o potros del piloto. Son diferencias
de proyección que requieren cerrar el consumidor antes de copiar datos al cliente.

## Plan de reparación para la alpha

1. **P0: bote y caballo, con captura de la primera interacción fallida.**
   Registrar personaje, misión/fase, template/objId, posición, skill, request,
   error, fase posterior y cambio de inventario. En ausencia de request, revisar
   oferta de interacción/modelo/fase del cliente; si hay request, seguir el
   rechazo o ejecución de Game y Zone. No inferir ambas situaciones de un clic.
2. **P1: propagar la causa demostrada a su familia.** Corregir en la ruta común
   correspondiente y enumerar las misiones afectadas desde la matriz. Añadir
   pruebas de rechazo sin consumo, inventario lleno, repetición, propietario
   distinto, recompensa única y relog. Mantener la racial nuiana como regresión.
3. **P1: restauración espacial acotada.** Revisar los objetos fijos de las
   misiones regionales activas dentro de perfiles Nuia confirmados. Usar las
   posiciones y fases nativas; comparar fuente/runtime, reemplazar sin duplicar
   y medir el incremento de objetos/memoria. Resolver primero los cinco botes
   y su catálogo efectivo. No importar los 4.571 hallazgos en bloque.
4. **P1: funciones faltantes con impacto en objetivos.** Empezar por
   `DoodadFuncSpawn` y sus tres objetos; contrastar consumer r575, upstream y
   AA8 antes de implementar. La lista de funciones faltantes por sí sola no
   autoriza inventar spawn, ownership o callbacks.
5. **P2: ampliar oferta jugable.** Cosecha/crianza, recolección de objetos,
   uso de item sobre objetivo, crafting y entrega. Promover una familia solo
   tras una misión completa y una regresión en otra misión de la misma familia.
   Revisar por separado las referencias genéricas y la localización contextual.

Los perfiles candidatos son `w_solzreed_1`/142 para la cadena del caballo y
`w_solzreed_2`/178 para la del bote según la zona catalogada. Antes de cada
prueba se verifica la posición real y el perfil propietario; no se arrancan
ambos perfiles solo por pertenecer a Solzreed. Su lifecycle sigue en Control
Center bajo control del usuario. Este análisis no arrancó ninguna Zone.

**Gate de aceptación:** aceptar normalmente, completar el objetivo, recibir
la recompensa una vez, enlazar la siguiente misión y conservar el estado tras
relog. Para la crianza: probar las tres variantes en recorridos separados,
consumo exacto de semilla/potro/reactivos y ausencia de duplicación.

## Validación y reproducción

- `dotnet restore`: correcto.
- `dotnet build --configuration Release --no-restore`: 0 errores, 28 advertencias.
- `dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore`:
  **2.836 correctas, 0 fallidas, 0 omitidas**. Validan el árbol local actual;
  no son una prueba de completar estas misiones en el cliente.
- Auditor y clasificador ejecutados contra bases abiertas read-only.
- Reportes pendientes de categoría quest consultados: reporte 3, misión 10029
  de Garden; no sirve como evidencia de los dos síntomas de Solzreed.

Herramientas versionadas:

- `reconstruccion_cliente_10/scripts/audit_nuia_sidequests.py`.
- `reconstruccion_cliente_10/scripts/classify_nuia_sidequests.py`.

Ejecutar primero el auditor para obtener `requested-ids.txt`. Escanear el
game_pak original con `PakDoodadScan` y `--all-worlds`; guardar
`all-world-placements.csv`, filtrar main_world a `placements.csv` y ejecutar
nuevamente el auditor. Finalmente ejecutar el clasificador. El modo tolerante
del auditor **registra divergencias**; el generador común sigue rechazando
contratos divergentes y conserva el modo estricto por defecto.

Evidencia:
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/nuia-sidequests-20260915`.
Incluye `quest-matrix.csv`, `interaction-contracts.json`,
`projection-differences.json`, `growth-rate-alignment.json`,
`missing-consumer-impacts.json`, `boat-placements.json`, `sources.json`,
`classification.json`, aceptación pendiente y logs de los tres gates.

El resultado del scanner sin posiciones para un ID conserva evidencia negativa;
no cambia la clasificación de objeto dinámico a objeto roto. La ausencia de
clase local tampoco equivale a ausencia de implementación en el cliente/Zone.
