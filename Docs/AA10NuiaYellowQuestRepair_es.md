# Reparación de misiones amarillas de Nuia — 2026-09-15

## Resultado y alcance

Se repararon tres mecanismos con evidencia disponible: posiciones de objetos,
invocación de NPC desde objetos y consumo del objeto usado para plantar.
**La validación automatizada no equivale a completar las misiones en el cliente.**
La reproducción del bloqueo original del caballo/bote y su aceptación jugable
siguen pendientes. No se declara reparado todo el catálogo de 1.184 misiones
regionales ni se activa contenido por el mero hecho de estar catalogado.

| Reparación | Alcance comprobado | Validación pendiente |
|---|---|---|
| Posiciones nativas | 581 posiciones, 91 plantillas, dependencias de 87 misiones regionales, 22 zonas de Nuia | Oferta, interacción, recompensa y persistencia de cada recorrido |
| Bote, misión 2393 | Cinco barcas 2853, fase inicial 6378, transformaciones y escala r575; sustitución acotada del grupo antiguo | Interactuar con skill 14006, recibir item 17863 una vez y entregar |
| `DoodadFuncSpawn` | Cargador y consumidor de NPC para descriptores de rango fijo; misiones regionales 1402/1474/2071 | Invocación, interacción/combate, expiración y entrega en Zone |
| Plantación, incluida crianza | Consume exactamente la instancia seleccionada; rechaza fuente incompatible, protegida, agotada o desplazada; evento de misión solo tras consumo correcto | Cadena 4292→4294→4295, cosecha, agua, crianza y las tres variantes de montura |

El mapa por misión está en `quest-repair-status.csv` dentro de la evidencia de
esta reparación. Todos sus recorridos permanecen `pending_retail_client`.

Quedan fuera los consumidores cuya función nativa no está cerrada, entre ellos
`FxGroupCallback` (objetos 2422/16621, misión 1933), `HideMapIcon` y aperturas de
interfaz de construcción/residencia. Las 152 plantillas sin fuente estática ni
item identificada en el análisis siguen siendo una frontera de investigación,
no una lista autorizada de objetos que crear artificialmente.

## Evidencia y decisiones

- Autoridad mecánica: SQLite completa r575 y compact original/montada;
  la auditoría anterior verificó 18.898 filas mecánicas sin divergencia de servidor.
- Posiciones: entradas del game_pak r575. La pertenencia a Nuia se comprueba por
  sectores nativos de `main_world/world.xml`, no por una caja rectangular ni por
  el nombre del objeto. MD5 del XML contra índice del paquete:
  `44f5ea385afd79bf710c0d2f327b9f05`.
- El overlay solo admite objetos regionales con plantilla, fase inicial inequívoca
  y funciones atendidas. Excluye objetos plantables, del cliente, contratos sin
  consumidor resuelto y posiciones fuera de Nuia. Los redondeos heredados entre
  0,01 y 0,05 unidades quedan fuera para no crear dobles casi coincidentes.
- El grupo del bote se reemplaza entero mediante la regla existente de sustitución:
  X `[15217,15228)`, Y `[13616,13617)`. Contenía cinco barcas en fuente y cuatro en
  runtime; ningún otro objeto. No se copia el catálogo genérico completo.
- `DoodadFuncSpawn` es infraestructura **server-required**, basada en los
  descriptores r575 y la ruta existente Game→World→Zone de `SpawnEffect`.
  AA8 se utilizó como comparador estructural, sin importar su IA ejecutada en Game.
  Solo se aceptan NPC y rangos fijos soportados. Si no se publica la invocación,
  no se avanza la fase ni se concede progreso de interacción.
- `item_spawn_doodads` enumera fuentes alternativas, no ingredientes acumulativos.
  El código anterior recorría todas las fuentes, notificaba `ItemUse` antes de
  consumir e ignoraba el resultado. Ahora usa la transacción existente de consumo
  exacto. Se conserva el camino interno sin item para evidencias de delitos.
- El caballo usa objetos dinámicos: semilla 23635→4594 y potros
  23680/23681/23682→4725/4727/4743. No se añadieron como spawns fijos.
  Esto corrige un defecto verificable del flujo compartido; **no demuestra que
  fuera la causa concreta del bloqueo observado por el usuario**.
- No se alteraron los tiempos de crecimiento: las 313 diferencias de proyección
  del cliente corresponden al rate100 existente. No se tocaron textos, traducciones,
  compact, bases de personajes ni el cliente original/español.

La inspección de `CSCreateDoodad` en los proyectos Ghidra identificó un campo
final firmado de 16 bits que el lector actual no consume. Su semántica y la
equivalencia completa con la DLL de cliente hoy instalada no están cerradas;
no se modificó el protocolo ni se atribuye el síntoma a ese campo. Los logs se
conservan como frontera forense, separados de las reparaciones verificadas.

## Comprobaciones

- `dotnet restore`: correcto.
- Build Release: 0 errores.
- Suite completa: **2.853 correctas, 0 fallidas, 0 omitidas**.
- Trece casos nuevos cubren datos nativos de invocación, entrega fallida/reintento,
  posiciones/fases/rotaciones, grupo de barcas y consumo/eventos de semilla/potros.
- Generador repetido: mismo hash de overlay
  `3c46c4fc882315f5815a28a0826902a0cf3a17ee5d2b5a2fa6c1fba4a707de2c`.
- Verificador del catálogo efectivo: reproduce orden, sustitución y deduplicación
  espacial del cargador sobre fuente y runtime; exige una instancia por cada
  posición restaurada y exactamente cinco barcas, con fase/escala/posición nativas.

Comandos reproducibles desde la raíz del repositorio:

```powershell
python reconstruccion_cliente_10/scripts/build_nuia_sidequest_placements.py
python reconstruccion_cliente_10/scripts/verify_nuia_sidequest_repair.py
dotnet restore
dotnet build --configuration Release --no-restore
dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore
```

El generador exige los hashes de las fuentes congeladas de la auditoría anterior.
No volver a ejecutar esa auditoría sobre la carpeta congelada para comparar el
resultado reparado: el verificador produce una evidencia separada.

## Despliegue, rollback y aceptación

Servicio afectado: Game/World en `aaemu10-game-1`. Se construye Release, se
sincronizan únicamente el overlay y su manifiesto de sustitución y se recrea Game.
La imagen previa y los dos archivos de destino quedan registrados en
`rollback/before.json`; tag de imagen anterior:
`aaemu-world:rollback-nuia-sidequests-20260915`.

El checkpoint y manifest enlazados abajo contienen imagen, hashes y resultado
de arranque. El árbol compartido ya incluía otros cambios; se preservaron y se
guardó su inventario inicial. Esta reparación no integra el padre comunitario
ni crea un commit de cambios ajenos.

La aceptación se realiza con el cliente español principal. Probar primero el
bote 2393 y la crianza 4292/4294/4295: aceptar normalmente, interactuar, comprobar
consumo/recompensa una vez, continuar la cadena y repetir comprobación tras relog.
Después probar 1402/1474/2071 con su NPC invocado. Conservar la historia nuiana
ya validada como regresión. Las tres variantes de potro necesitan recorridos
separados. Las posiciones restauradas no requieren levantar otras zonas a la vez.

No se operó el lifecycle de ZoneHost. El usuario conserva ese control; la
aceptación jugable se registra separadamente de compilación y salud del contenedor.

## Artefactos

- Diagnóstico previo: [AA10NuiaYellowQuestAudit_es.md](AA10NuiaYellowQuestAudit_es.md).
- Checkpoint: [CHECKPOINT_NUIA_SIDEQUESTS_REPAIR_20260915.md](../reconstruccion_cliente_10/checkpoints/CHECKPOINT_NUIA_SIDEQUESTS_REPAIR_20260915.md).
- Evidencia: `E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/nuia-sidequests-repair-20260915`.
