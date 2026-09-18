# QA real de la integración upstream — 18 septiembre 2026

Base: merge `29d68e3f2d60d615fa892dfeed037ddff4fa2010` (139 commits del padre).
Inventario completo de commits: [AA10UpstreamReview20260918_es.md](AA10UpstreamReview20260918_es.md).
Decisiones del merge: [AA10UpstreamIntegration20260918_es.md](AA10UpstreamIntegration20260918_es.md).

Pruebas autorizadas por el usuario con Dannia, cuenta de pruebas, cliente principal
es_ES-full-preview r575 y Zone `w_solzreed_1`/142. La contraseña no se registra.
API exclusivamente mediante `docker exec` al puerto interno 1280. Sin publicar ese puerto.
Respaldo transaccional antes de comenzar; sin SQL de modificación sobre personajes online.

## Evidencia local

`E:\AAEmu\rama_10\artifacts\upstream-live-qa-20260918` contiene el diario API
con UTC, capturas, logs de cada sesión, inventario inicial, respaldo SQL privado,
logs de compilación/pruebas y desensamblado Ghidra. El respaldo y las configuraciones
privadas no se incorporan a Git.

## Resultados observados

| Caso | Resultado / límite de la prueba |
|---|---|
| Inicio de sesión y Dannia | Entrada real, ZoneLoaded y heartbeats; varias sesiones sin bloqueo de carga. |
| Creación de personajes | Creado `Qamerge`, Firran masculino Spelldance nivel 1, mostrado en selector. Eliminado desde UI con su nombre exacto y espera de un minuto; consulta final confirma ausencia en DB. Captura `04-character-created.png`. No se entró al mundo con este personaje. |
| Disparo de precisión 23592 | Dos lanzamientos en sesión 1: 5570 y 5548 de daño. Sesión 2, tecla 6 del cliente: vida del muñeco 1036179 → 1030643, daño 5536, un PlotEnded y un SkillEnded, ActivePlot=false. Distancia aproximada 2–3 m. No certifica otros rangos, sinergias o todas las habilidades. |
| Arco de rayos 10670 | La invocación GM terminó inmediatamente sin daño en este escenario. No se reproduce una canalización válida; cancelación/reutilización del reporte previo sigue pendiente. |
| Eventos | Calendario abre; información de eventos vacía, coherente con backend todavía incompleto. No se certifica ejecución de eventos. Capturas 01 y 02. |
| Housing | `/houserebuild 1` devuelve catálogo (destino 328, skill 28828, materiales 8318×100 y 23633×10). No se ejecutó reconstrucción sobre vivienda de jugador. |
| Asedios | `/siegewindow teams` responde correctamente con roster vacío del grupo 5. No se realizó un asedio multijugador. |
| Rankings | `/rankrefresh now` procesa dos tablas. Tras corregir GearScore, cliente, servidor y tabla 23 guardada en DB coinciden en **8093**. Tabla 26: 2008. Premios automáticos continúan desactivados. |
| Protección de objetos | Gorro temporal template 53045, item 16777695, grado 0, slot Inventory/14. Candado conservado tras reconectar. Unlock desde UI cambia a candado rojo y programa **72 h**; `CanDestroy=False` durante espera. Retirado administrativamente al terminar. No se certifica vencimiento natural de 72 h. Equipo original sin cambios. Capturas 05, 07, 08. |
| Recarga de scripts | Fallo inicial: faltaba ensamblado de Parallel y se vaciaba el registro antes de compilar. Corregido. Recarga correcta; error `#error` intencional conservó `/gearscore`; retirado el archivo y recarga correcta. |
| Retirar NPC temporal | Hallado NullReferenceException con `/npc remove`: NPC creado por GM carece de Spawner. Corregido y probado tras reconstruir imagen: template 7511, obj 1067 desaparece de UI sin excepción. Se conserva semántica Hide del comando, no se certifica eliminación persistente de un spawn normal. La recarga dinámica reutiliza subcomandos del ensamblado principal. |

## Correcciones derivadas de la prueba

### Puntuación de equipo r575

Antes: cliente **8093**, servidor **10218**, mismo equipo (captura 03).
Se corrige el contrato, sin compensaciones específicas para Dannia:

- `x2game.dll` FUN_39b4cc60: fórmula 30 arma, 56 armadura, 57 accesorio;
  nivel efectivo incorpora mejora de ranura (Ipnya).
- Detalle nativo +0x08 = `GemData[1]`: una Lunafrost, fórmula 32, nivel de SU template.
- +0x18..+0x38 = `GemData[4..12]`: nueve Lunagem, fórmula 31 por template válido,
  cada una con SU nivel. No sumar fórmula 32 por Lunagem.
- FUN_39b4c250: templado usa `(1000 + enchant_scale_ratios.scale) * 0.001f`;
  una fila desconocida devuelve cero. Multiplicadores de holdable/wearable siguen en centésimas.
- FUN_39979340/39979460/39979530: cálculo float, `floor(resultado * 10) / 10`.
  Constantes verificadas: 39e347dc=1f, 39e19200=10f, 39f71938=1000f,
  39df4608=0.001f, 39f71940=0.01 double.
- FUN_39b4e1c0 y predicados 39985880/B0/D0: suma float en orden de slots
  0..18,26,27,29,30,32 y truncamiento final a entero.

Evidencia: `gearscore-*-native.log`, `gearscore-instructions.log`.
Binario x64 SHA-256 `405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`,
ImageBase `0x39000000`: los símbolos anteriores son VA; RVAs principales
`0xB4CC60` (pieza), `0xB4E1C0` (total), `0xB4C250` (templado),
`0x979340/0x979460/0x979530` (fórmulas), `0x985880/0x9858B0/0x9858D0` (slots).
Pruebas añadidas: niveles propios, Lunafrost independiente, novena ranura,
templates inexistentes, exclusión de datos de síntesis/apariencia, truncamiento decimal y slots.
Aceptación final: `/gearscore self` devuelve 8093 y panel C muestra 8093;
captura `06-gearscore-corrected.png`. La igualdad se demuestra para el equipo real
de Dannia; tipos especiales no representados por Weapon/Armor/Accessory no quedan certificados.

### Herramientas de diagnóstico

`/qainspect self|target|gear` es de lectura: HP/MP, buffs, estado de plot y
desglose de equipo. Requiere los permisos GM habituales. No modifica estadísticas.
La recarga ahora incluye explícitamente System.Threading.Tasks.Parallel, conserva
comandos cuando la compilación falla y omite tipos generados por el compilador.

## Límites y observaciones

No presentar esta sesión como certificación integral del juego. Quedan fuera de esta
prueba real las carreras multijugador, asedios con participantes, reconstrucción de una
vivienda propia y todos los casos de absorción/reflejo/CC. Las pruebas automatizadas
complementan la sesión pero no sustituyen esos escenarios.

Se observaron textos ingleses y una cadena de menú de protección incorrecta:
`(ui_texts, text, 5351)`, fuente en_us "1 minute", también traducida como un minuto.
La fuente coreana y `content_configs.id=43` coinciden en 4320 minutos (72 horas).
La confirmación y el backend son correctos: petición 2026-09-18 16:30:18.9658173 UTC,
vencimiento 2026-09-21 16:30:18.9658173 UTC. No se cambió el paquete de localización;
la cadena 5351 queda identificada para corrección mediante el pipeline reproducible.
El opcode 0x080 al entrar y referencias de EquipmentSlave a ítems ausentes ya estaban
documentados antes de este merge. Se registran sin atribuirlos a los nuevos commits.

Un acceso a las 16:22:54 UTC cerró Game antes de completar CTJoin; Stream rechazó
correctamente el token ya retirado. La causa del cierre inicial no quedó demostrada.
Reintento 16:25:22 con la Zone cargada: selector, entrada y sesión final correctos.
No se debilitó la autenticación ni se atribuye el incidente al merge sin evidencia.
La ausencia de recurrencia en ese reintento no demuestra que la causa esté resuelta.

## Validación final y limpieza

- Build Release correcto. Suite: **5418/5418**, cero fallos/omitidos. Después de la
  guardia de Spawner se repitió build y se comprobó su caso real en cliente.
- Imagen final desplegada: `sha256:f6c6bac0fab9e457a273a834cf24bbbeada5d2218f67e155b215e74750b8545e`.
  Tag `aaemu-world:live-qa-20260918`; Game reiniciado 16:20:07 UTC. Login sin cambios.
- Rollback previo a QA: `aaemu-world:rollback-before-live-qa-20260918`.
- Recarga final: cero errores de compilación/carga, cinco advertencias CS1701 de
  referencias MySql.Data/System.Data.Common. Un error en el script temporal de limpieza
  se corrigió antes de ejecutarlo; durante ese fallo los comandos anteriores siguieron disponibles.
- Limpieza administrativa usó un comando efímero limitado a personaje 1007, item
  16777695/template 53045/slot 14/cantidad 1/owner verificado, bajo mutation lease.
  Se retiró del contenedor y del registro mediante una recarga posterior. Su fuente
  queda sólo en artefactos locales como evidencia, nunca en la imagen ni Git.
- `inventory-before.json` frente a `inventory-after.json`: arrays Equipment y Backpack
  idénticos, **20 equipados y 121 entradas de mochila**. Se retiró exclusivamente el objeto
  añadido. `persistence-final.json` confirma Qamerge y item 16777695 ausentes y los campos
  originales de Dannia (posición, nivel, dinero, especializaciones) idénticos.
  Labor creció por regeneración online normal; no se fuerza a su valor anterior.
- Cliente cerrado por salida normal y launcher cerrado. Los tres workers usados en
  sesiones sucesivas cerraron su árbol completo CMD/ZoneHost/conhost. Último árbol:
  28472/59120/50028; comprobación final sin procesos cliente/Zone ni esos PID.
- 16:34:49 UTC: API indica PlayerCount=0, Zones=[], sin reservas. Game/Login/DB saludables.
  Sólo se operó `w_solzreed_1`/142; no se abrieron las demás Zones.
- Sin modificaciones de game_pak/SQLite autoritativa, sin SQL de escritura sobre el
  personaje online y sin push remoto. Permanecen los límites expresamente descritos arriba.
