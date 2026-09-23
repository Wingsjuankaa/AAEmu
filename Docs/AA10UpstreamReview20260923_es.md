# Revisión del padre r575 — 23 de septiembre de 2026

Sí conviene incorporar mejoras de la comunidad, mediante una integración adaptada.
El padre compila y pasa sus 5.778 pruebas, pero tiene funciones todavía incompletas
y un fallo ancestral reproducido durante esta revisión. No recomiendo fusionarlo
y desplegarlo sin resolver esos puntos y preservar nuestros cierres nativos.

## Estado publicado y alcance

- Target: `E:\AAEmu\rama_10\server\AAEmu`, rama `rama_10`.
- Fork: `Wingsjuankaa/AAEmu:rama_10`.
- Se publicó el trabajo local pendiente de push y la corrección documental del
  firewall. SHA publicado antes de la revisión: `96ebd8ab620e232f6281ddfb2425d152e0334112`.
  Se verificó con `git ls-remote`; no hubo force-push.
- Padre exclusivo: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`.
- Corte auditado: `b73c33aa761dac418472fa85c7e0985dc98abb73`, PR #1698.
- Última referencia leída: `7851f67cc`; último padre integrado por linaje/base
  común: `30837660a75e4beef5a38f37bf95809edf055f53`. Son cortes distintos.
- Hay **168 commits nuevos desde la última lectura** y **255 pendientes por
  linaje** desde nuestro HEAD: **181 cambios y 74 merges**. No son 255 funciones.
- Diff neto desde la base común: **794 archivos, +54.167 / −2.596 líneas**.
  Desde la última lectura: **633 archivos, +45.360 / −2.171 líneas**.
- **146 archivos solapados**, **58 conflictos** en la simulación de merge.
  Las 70 entradas de primer padre comprenden entregas y un cambio de README;
  los merges internos explican que el total de merges sea mayor.

Se revisaron historial, archivos afectados, cambios netos, conflictos y rutas
centrales de habilidades, entrada, recompensas y persistencia. Se compiló y probó
el padre en un worktree separado, sin configuración de producción. Esta es una
revisión de integración, no una certificación visual de cada función nueva ni una
auditoría línea por línea de los 794 archivos.

No se realizó merge en `rama_10`, no se aplicaron migraciones, no se cambió la
imagen de producción y no se operaron Zones ni cliente. El inventario íntegro está
en [commits](AA10UpstreamReview20260923_commits.md); el
[JSON](AA10UpstreamReview20260923.json) conserva SHAs, archivos, conflictos y gates.

## Qué trae y qué incorporar

“Incorporar” significa candidato recomendado sujeto a los gates de integración,
no garantía de que pueda copiarse sin adaptación. Las series deben tomarse en su
estado final, incluyendo sus correcciones posteriores.

| Bloque / PR del padre | Qué aporta | Decisión para nuestro fork |
|---|---|---|
| Aportes propios #1628–#1634 | Escape de correo fiscal, recarga de scripts, deltas de stacks, pesca, snapshot de buffs, avisos de squad y retirada de NPC | Converger con los aportes aceptados. Ya tenemos el origen de estas soluciones; inspeccionar las diferencias posteriores, sin duplicar callbacks o persistencia. |
| Persistencia #1619 | Corrección del gate de persistencia con operaciones diferidas anidadas | Prioritario para las nuevas transacciones; revisar interacción con nuestros scopes de inventario. |
| Operación #1626, #1635–#1638 y README | Limpieza, importación SQL, launcher World, versión de Zone y dependencias NuGet | Incorporar selectivamente. Conservar Docker, bind mounts y red local propios. Una actualización de dependencias requiere nuevo build, no sustituir el despliegue por los scripts genéricos. |
| Vendedores y puntos #1640 | Compras con monedas distintas de oro; formatos de puntos y comandos de honor/vocación | Recomendado, adaptando conflictos de `CSBuyItems`/`SCGamePointChanged` y el catálogo de nuestro menú GM. Probar saldo, coste y serialización. |
| Personalización #1663, #1677 | Edición de apariencia en salón/lobby, validación de partes, rango de cicatrices y tolerancia a filas nulas | Incorporar la serie final. Probar creación y edición de todas las razas/sexos, y que editar en lobby preserve buffs guardados. |
| Equipo de mascotas #1616 | Equipamiento/packs de mates | Incorporable con pruebas de equipar, retirar, invocar y relog. |
| Refuerzo de ranuras #1601 | Progresión persistida, experiencia, efectos y aporte al nivel del equipo | Adaptación obligatoria: ya tenemos loader y efectos con los mismos nombres. Hay conflictos add/add; debe quedar una única autoridad de progresión y costes. |
| Gear score #1647 | Separación de puntuación total/base, gemas, refuerzo, truncado y coherencia del caché/ranking/asedio offline | Útil, pero comparar contra la pantalla C y nuestro caso validado de equipo. Mantener nueve sockets nativos y el bloqueo local de pagos inseguros de rankings. |
| Ancestrales #1698 | Elegir una ancestral puede aprender automáticamente la base después de resetear el árbol | Incorporar después de corregir el fallo de atomicidad reproducido abajo. No equivale a arreglar todas las ancestrales. |
| Objetivos y resultados de skills #1651, #1655, #1656, #1665 | Códigos de error, rango mínimo/máximo, mascotas/barcos propios, operadores `unit_reqs`, objetivos de plots y Reversal con inmunidad por tags | Combinar con admisión/GCD/cadenas/Zone del fork. No sustituir íntegramente `Skill.cs` ni `UnitReqs.cs`. |
| Efectos de equipo #1649 | Eventos de golpe, crítico, daño recibido, curación y lanzamiento; selección de objetivo, probabilidades, CD y prevención de recursión | Recomendado con adaptación del ownership de plots. Su protección `FromItemProc` no representa automáticamente nuestro `IsBackgroundProc`. |
| Efectos especiales #1652 | Clasifica efectos ejecutados por servidor, visuales del cliente y no implementados; evita ciertos cobros de casts sin implementación | Revisar la clasificación contra los consumidores propios. Mantener ItemSmelting fuera de alcance y no confundir clasificación con implementación completa. |
| Actos de misiones #1657, #1662, #1664 | Nuevas condiciones de inicio/progreso/recompensa, grupos de objetos con grado, efectos, nivel y avisos de rechazo | Incorporable tras combinar cinco archivos movidos desde `UnusedActs` y los tres actos add/add. Conservar la evidencia de cadenas iniciales de nuestro fork. |
| Actores iniciales #1661 | Posiciones de entrega de cadenas iniciales y auditoría de actores | Recomendado con comparación del contenido de Zone y nuestras correcciones de spawn. |
| Interacciones y doodads #1645, #1666–#1671 | Conjuntos de interacción NPC, progresión FakeUse, condiciones de construcción/UI, spawns soportados, dificultad/salida de instancia y beneficios de gremio | Incorporar por consumidores completos. Se solapa con nuestros handlers y autoridad nativa; no crear doble spawn ni abrir UI sin permisos. |
| Craft orders #1641, #1653 | Tablón de encargos, completar instantáneo, lista propia, tarifas, devolución de hoja y limpieza con reembolsos | Incorporable como bloque económico con sus followups. Validar rollback, expiración y migraciones sobre copia de DB. |
| Barcos y movimiento #1642, #1644 | Posición inicial solicitada al invocar barcos y reposo/streaming de unidades suspendidas | Comparar con propulsión, colisiones y control de Zone propios. No introducir una segunda autoridad de movimiento. |
| Movilización #1643 | Aceptación junto a la bandera, elección del pad/instancia y persistencia de tiempos | Incorporable junto con sus dos columnas de estado; comprobar teleports y límites de invitación. |
| PvP y mundo #1650, #1672, #1674 | Muertes que escalan conflicto, ventanas diarias de guerra y persistencia/reintento de estado de zona | Recomendado con reinicio y horarios probados; no reemplazar estados persistidos por valores predeterminados. |
| Clima #1646, #1682 | Nieve nativa y fases de lluvia/viento según horarios, preservando nieve ajena al ciclo | Incorporar con inspección de flags efectivos montados y sincronización al entrar. |
| Diplomacia, raid y chat #1658, #1660, #1676 | Relaciones de facción e historial, reclutamiento de raid y autorización de canales de facción/juicio | Incorporable con pruebas de permisos, desconexión, pertenencia y transición a pirata. |
| Instancias #1625, #1654, #1675, #1684 | Selección de canal, acciones/eventos/rondas, horarios de acceso, tags de buff, reentrada, permisos y dificultad | Adaptar a nuestra admisión y carga real de Zones. Probar rechazo sin mutación y reentrada con puerta cerrada. |
| Radar #1673 | Ciclo de vida de NPC monitor y telescopio de jefes | Incorporable preservando nuestro radar y alta/baja de buffs. |
| Mentoría #1648 | Restauración de misiones de mentor/aprendiz en mazmorras | Candidato de contenido, condicionado a la integración de quests/instancias. |
| Viviendas #1678, #1688 | Publicación, cancelación, compra y persistencia de venta; cartel correcto y correcciones de locks | Adaptar sobre nuestra transacción de vivienda. Verificar propietario, dinero, impuestos, decoraciones y fallo de guardado. |
| UCC/parcela #1680, #1687 | Integridad al aplicar emblemas, consumo del sello correcto, slots UCC persistidos y geometría rotada de parcelas | Recomendado tras integrar vivienda. Necesita comparación retail de geometría, broadcast y propiedad. |
| Correo #1681 | Spam, pago de correo contra reembolso, devolución, vencimiento y notificación del pago | Incorporable como serie completa; probar dinero/adjuntos y fallo de DB, conservando correo fiscal propio. |
| Logros #1622–#1624 | Registros/progreso, premios, títulos y crédito por acciones anteriores | Incorporar seguimiento; corregir entrega y recuperación de premios antes de habilitarla masivamente. Hallazgo específico abajo. |
| Colecciones #1679 | Descubrimiento, enciclopedia, grado de objetos y sincronización aplazada hasta cargar progreso | Depende de logros; aplazar premios hasta resolver su liquidación. |
| Música #1690 | Instrumentos de doodad/slave, propiedad y reanudación de partituras | Incorporable con pruebas de dueño, distancia, detener y reanudar. |
| Residencia #1692 | Puntos y cobros por zona, agregados y persistencia; gates de paquetes de desarrollo | Incorporación parcial. El propio padre rechaza semánticas `type2` no resueltas; no presentar como residencia/tributos completamente terminados. |
| Sagas #1683 | Desbloqueo de grupos, progreso, sincronización y ledger de hitos | Seguimiento útil, recompensa todavía parcial: registrar un grant no demuestra entrega al jugador. Conservar el revert final de la serie. |
| Tiendas aleatorias #1693 | Catálogo, rotación por personaje, contadores, stock y protección de compra repetida interna | Aplazar exposición al jugador. Faltan listado y compra completos en wire; el refresco pagado ya puede cobrar. |

## Hallazgos que condicionan el merge

### 1. Activación ancestral deja una mutación parcial si falla DB — reproducido

En [CharacterHeirSkills.cs](https://github.com/AAEmu/AAEmu/blob/b73c33aa761dac418472fa85c7e0985dc98abb73/AAEmu.Game/Models/Game/Char/CharacterHeirSkills.cs#L49),
`TryActivate` aprende la base mediante `AddSkill` antes de `TryPersistSelection`.
Si este último devuelve `false`, retorna error sin deshacer la habilidad aprendida
ni el paquete de aprendizaje. `GetUsedSkillPoints` contará después esa base según
su coste. No es una pérdida reproducida en nuestro runtime: es un defecto del
candidato nuevo bajo fallo de persistencia.

Se añadió temporalmente una prueba a `HeirSkillActivateTests` en la copia del padre:
base ausente, `PersistForTest = (_, _) => false`; se espera rechazo sin aprenderla.
Resultado: **2 pruebas originales aprobadas y 1 prueba diagnóstica fallida**,
`Expected to be false but found True` al comprobar si la base quedó aprendida.
El fixture usa coste cero; prueba la mutación parcial, no una cantidad concreta
de puntos. El código de aprendizaje demuestra la consecuencia para bases de pago.

Antes de integrar: planificar aprendizaje/selección, persistir coherentemente,
publicar ambos resultados solo al confirmar, y cubrir rollback con base ausente,
base existente y falta de puntos. Preservar nuestro reset y admisión ancestral.

### 2. Tiendas aleatorias todavía no ofrecen un circuito jugable completo — estático

[CSRandomShopInfoPacket](https://github.com/AAEmu/AAEmu/blob/b73c33aa761dac418472fa85c7e0985dc98abb73/AAEmu.Game/Core/Packets/C2G/CSRandomShopInfoPacket.cs)
carga una ventana pero retiene la respuesta porque `shopDisplayInfo` no está
decodificado. [CSRandomShopGoodsBuyPacket](https://github.com/AAEmu/AAEmu/blob/b73c33aa761dac418472fa85c7e0985dc98abb73/AAEmu.Game/Core/Packets/C2G/CSRandomShopGoodsBuyPacket.cs)
lee campos iniciales y rechaza toda compra por desconocer la lista de ofertas.
En cambio, `CSRandomShopInfoRefreshPacket.HandleRefresh` llama a `TryRefresh` y
puede cobrar objetos, vocación u oro. Integrar ese conjunto como tienda terminada
permitiría un refresco con coste sin un flujo completo de visualización/compra.

Además, la exclusión de stock del gestor no es una transacción durable de compra:
`TryClaimOffer` guarda `sold=1` en su propia conexión antes del callback de pago.
La entrega no forma parte de esa operación. Los tests de compra concurrente
demuestran exclusión dentro de su modelo, no recuperación de cobro/entrega ante
caída de proceso. No exponerlo hasta cerrar wire y liquidación.

### 3. Logros pueden quedar completados sin premio — estático

[AchievementManager.Refresh](https://github.com/AAEmu/AAEmu/blob/b73c33aa761dac418472fa85c7e0985dc98abb73/AAEmu.Game/Core/Managers/AchievementManager.cs#L211)
marca completado y emite su aviso antes de `PayReward`. Si falla `TryPayItem`,
solo registra un aviso. La siguiente evaluación retorna porque `Complete` ya no
produce transición. No existe en ese camino un estado pendiente de entrega o
reintento. Debe separarse progreso de liquidación y persistir un grant recuperable,
incluidos el caso de bolsa llena/correo y los premios retroactivos.

### 4. Procs de equipo y plots del jugador necesitan combinación — riesgo de integración

El padre crea los procs con `FromItemProc=true`; nuestro fork protege el cast
principal con `IsBackgroundProc`, derivado de `IsBuffTriggered` y flags nativos.
Son propósitos distintos: antirrecursión frente a ownership del plot. Resolver
el conflicto escogiendo solamente una versión de `Plot.cs` perdería una de las
protecciones. Debe probarse la interacción, no equiparar los flags sin evidencia.

La SQLite autoritativa AA10, consultada en solo lectura, contiene tres procs con
plots: `63 → skill 19148 / plot 699`, `104 → 27436 / 1609`,
`112 → 27896 / 1692`, todos `plot_only`. Por ello el cruce no es meramente un caso
hipotético de plantilla inexistente. No se afirma que los tres fallen visualmente:
la cancelación depende del plot activo y sus flags.

### 5. El arreglo de tempo de Tiger Strike sigue siendo propio

El padre conserva en `PlotNextEvent.GetDelay` la suma de espera de controlador
y espera de arista. Nuestro commit `db98de647` compone ambas con `Math.Max` y
conserva animación/proyectil aparte. La simulación mantiene **idéntico nuestro
archivo**, porque el nuevo rango no lo modifica. Aun así, hay conflictos en
`Skill.cs`, `Plot.cs` y `PlotNode.cs` que pueden alterar su ciclo de vida.

El nuevo `CastTlId` capturado para plots asíncronos sí es una mejora candidata.
Debe viajar por inicio, eventos, fin y cancelación sin duplicar liberación ni
invalidar nuestros casts de fondo. No sustituir tiempos por constantes nuevas.

### 6. Sagas: ledger de finalización no equivale a premio entregado

`SagaProgressState` registra `(grupo, milestone)` y devuelve `RewardGranted`;
`CharacterSagaProgress.ReportChange` registra un log. Ese recorrido no entrega
objetos o moneda. Es una base para hitos posteriores, no prueba de recompensa
funcional. La consulta local no encontró grupos con `currency_value > 0` o
`item_set_id > 0`; el rechazo de compras con coste no bloquea por sí solo el
catálogo actual, aunque queda como límite explícito del handler.

## Protecciones locales que deben sobrevivir

La simulación conserva byte por byte estos archivos respecto del fork publicado:

- `X2EnterWorldResponsePacket.cs` y `CSCreateCharacterPacket.cs`: handshake y
  creación. La autoridad GM del servidor no debe convertir el byte de entrada
  en un modo de cliente incompatible.
- `CombatResourceGameData.cs`: modificadores nativos de recursos de combate.
- `PlotNextEvent.cs`: composición temporal de Tiger Strike.
- `SkillComboRules.cs` y `SkillCooldownGateRules.cs`: reglas auxiliares de cadenas/CD.

Esto no certifica el conjunto: consumidores de esas reglas tienen conflictos.
También conservar admisión de sucesores, devolución de puntos, respuesta a casts
repetidos rechazados, expiración/extensión de Frenesí, stats de pasivas, reset GM
de CD, panel GM, sockets, propulsión y snapshots de Zone. Los aportes comunitarios
al salón amplían CharacterManager aunque no cambien el handler de creación.

El diff simulado de RankScoreManager mantiene el bloqueo local de liquidación
automática; solo adapta el cálculo de puntuación. No reactivar los pagos pendientes
de transacción segura durante la resolución.

## Migraciones y despliegue futuro

El rango añade **13 scripts SQL**: refuerzo de ranuras; logros; craft orders;
estadísticas de tarifas; dos tiempos de movilización; diplomacia; colecciones;
sagas; estado de conflicto; UCC de vivienda; tienda aleatoria; residencia.
La lista exacta está en el JSON. `SQL/aaemu_game.sql` tiene conflicto y no debe
importarse encima de la base viva para resolverlo.

Los dos ALTER de movilización no usan `IF NOT EXISTS`. Varios scripts incluyen
`USE aaemu_game`: ejecutarlos sin adaptar sobre una conexión destinada a una base
de ensayo podría cambiar el destino. Preparar migrador con comprobación de
esquema y destino explícito, aplicar dos veces sobre una copia aislada y comparar
datos de personajes/objetos antes del despliegue. Esta revisión no consultó ni
modificó el esquema vivo, por lo que “script nuevo” no significa “tabla ausente”.

Los cambios no requieren reemplazar el cliente traducido ni su `game_pak`.
Mantener `en_us` como canal interno del producto español y localizar los nuevos
mensajes propios, correos y ayudas de comandos al integrar. Los IDs de protocolo
y las claves técnicas no se traducen.

## Orden recomendado

1. Crear respaldo de HEAD, imágenes, DB y configuración efectiva. Integrar el
   padre mediante merge normal conservando linaje; resolver por dominio, no con
   selección global de ours/theirs. Separar la revisión de cada dominio en commits
   posteriores cuando sea posible, sin desplegar estados intermedios incompletos.
2. Converger aportes propios, operación/dependencias y correcciones acotadas de
   vendedores, personalización, puntos y avisos.
3. Combinar skills/plots/procs con los cierres locales, corregir atomicidad ancestral
   y validar primero creación, reset de puntos, cadenas y buffs.
4. Incorporar quests, instancias, clima, PvP, raid/diplomacia y contenido dependiente.
5. Adaptar vivienda/UCC, correo, encargos y refuerzo con migraciones probadas.
6. Habilitar premios de logros/colecciones solo tras cerrar entrega durable.
   Mantener tiendas aleatorias y premios de saga como parciales hasta cerrar
   sus contratos; ItemSmelting permanece excluido.

Gates mínimos del candidato combinado: restore/build Release, suites del fork y
padre, pruebas de fallo de persistencia, migración idempotente y arranque aislado.
Luego aceptación en cliente de creación, Triple Slash y ancestrales, Whirlwind,
Endless Arrows, Tiger Strike Rayo, Frenesí/Delirio, parry y reset de CD. Para
funciones económicas: reintento, doble petición, bolsa llena, relog y reinicio.
Las 5.778 pruebas del padre por sí solas no certifican ninguna de estas combinaciones.

## Evidencia y reproducibilidad

Artefactos locales: `E:\AAEmu\rama_10\artifacts\upstream-review-20260923`.

- `merge-tree.txt`: simulación `git merge-tree --write-tree HEAD <padre>`, salida 1
  por 58 conflictos, árbol `5686073040d1ec66d1f82ea7e8d1379cb5746578`.
- `restore-parent.log` y `test-parent.log`: padre original, 5.778 aprobadas,
  cero fallos/omitidas, compilación Release con advertencias.
- `heir-persist-failure-reproducer.patch` y `heir-persist-failure-test.log`:
  prueba diagnóstica añadida temporalmente, 2 aprobadas/1 fallida. La modificación
  se retiró del worktree; no se incorpora el test fallido a `rama_10`.
- `build-parent`: worktree detached usado para compilar/probar, sin despliegue.
- `parent`: snapshot de fuentes para revisión; `generate_inventory.py` genera
  el inventario a partir del historial Git.

Comandos de validación ejecutados en la copia del padre:

```powershell
dotnet restore AAEmu.UnitTests/AAEmu.UnitTests.csproj
dotnet run --project AAEmu.UnitTests/AAEmu.UnitTests.csproj -c Release --no-restore -- --report-trx
# Tras aplicar exclusivamente el reproducer temporal:
dotnet run --project AAEmu.UnitTests/AAEmu.UnitTests.csproj -c Release --no-restore -- --treenode-filter '/*/*/HeirSkillActivateTests/*' --report-trx
```
