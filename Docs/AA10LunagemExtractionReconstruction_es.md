# Reconstrucción AA10 de extracción de Lunagem

## Resultado

`rama_10` implementa los tres modos del efecto retail `ItemSocketing` para Returns 10.0.2.13 r575:

| Modo | `special_effects.value1` | Consumible | Resultado |
|---|---:|---:|---|
| Retirada destructiva | 0 | item 327 / skill 23729 | elimina todas las Lunagem |
| Instalación | 1 | la Lunagem elegida / skill 23728 | instala en el primer socket libre |
| Extracción | 2 | item 38568 / skill 30673 | devuelve la Lunagem extraíble a la bolsa |

La extracción individual usa el índice físico base cero enviado por el cliente. La extracción total
usa `value=0, isAll=true`, procesa todos los sockets ocupados y consume una piedra y 500 de labor por
socket. Las filas `item_sockets.extractable=false` se eliminan sin producto, exactamente como advierte
el diálogo retail.

El contexto CS nativo de extracción no es el tipo 10 de instalación. La captura dinámica r575 cerró
un tipo 11 distinto, con cuerpo exacto `u32 socketIndex, bool extractAll`; después viene el
`inputDirection` común. El servidor lo parsea y lo vuelve a emitir completo en Started/Fired.

## Evidencia AA10

- Base autoritativa SHA-256:
  `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`.
- `x2game.dll` SHA-256:
  `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`.
- Compact efectiva SHA-256:
  `23FEC0E7CD7F362125CDDE3CF32F0D60D3EDC3C5BCEFF60DFE7244B67B68373B`.
- `items.id=38568` usa `skills.id=30673`; la skill tiene `consume_lp=500` y su efecto es
  `ItemSocketing(106), value1=2`.
- El catálogo contiene 783 Lunagem: 528 extraíbles y 255 no extraíbles, tanto en full como en la
  compact desplegable.
- `socket_enchant.lua` llama `Execute(selectIndex - 1, false)` para una gema y `Execute(0, true)` para
  todas. El coste visual de “todas” es el número de sockets usados.
- `FUN_3912AF60` de `x2game.dll` asigna operación `0/1/2` a Remove/Insert/Extract. El resultado usa el
  packet r575 `SCItemSocketingResult` `0xCA` con `operation=2` para extracción.
- La vista retail sólo publica la pestaña Extract cuando `Feature.socketExtract=169` está activa. El
  runtime y la configuración versionada mantienen `socketExtract=true`; el servidor falla cerrado si
  el bit falta aunque se falsifique una petición.

El dossier reproducible vive en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\lunagem-extraction-frontier`.

## Transacción del servidor

1. valida que target, consumible y use-skill pertenezcan a la misma solicitud;
2. resuelve el índice o todos los sockets y vuelve a consultar `item_sockets.extractable`;
3. preflighta cantidad de piedras, labor total y espacio agregado de bolsa, incluyendo el slot que
   puede liberar la última piedra consumida;
4. bajo el lock de bolsa consume exactamente las piedras y crea los productos retornables;
5. limpia sólo los sockets planificados, recalcula bonuses si el objeto está equipado y marca detalle
   persistente;
6. publica primero el cambio del equipo y consumible, cada producto en su propio límite de packet,
   luego `SCItemDetailUpdated` y finalmente `SCItemSocketingResult(operation=2)`.

Los rechazos por socket vacío, índice inválido, catálogo desconocido, consumible insuficiente, labor
insuficiente o bolsa llena no cambian gems, inventario ni labor.

## Archivos principales

- `AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/ItemSocketing.cs`
- `AAEmu.Game/Models/Game/Items/Services/ItemSocketRuleService.cs`
- `AAEmu.Game/Models/Game/Items/Containers/ItemContainer.cs`
- `AAEmu.Game/Models/Game/Skills/Skill.cs`
- `AAEmu.Game/Models/Game/Skills/SkillObject.cs`
- `AAEmu.Game/Models/Game/Skills/SkillCastWire.cs`
- `AAEmu.Game/Core/Managers/ItemManager.cs`
- `AAEmu.UnitTests/Game/Models/Game/Items/ItemSocketRuleServiceTests.cs`
- `AAEmu.UnitTests/Game/Models/Game/Skills/SkillObjectSocketExtractOptionsTests.cs`

## Aceptación dinámica r575 — 2026-08-19

Se reconstruyó únicamente la imagen Game (`sha256:f894924aa87cfad537830b37905a2c803d4f3faf66a9b07d155123a1224a2630`),
se recreó sólo `aaemu10-game-1` y se inició exclusivamente la Zone persistida del personaje:
`o_hirama_the_west_2`, `zoneId=351`, PID 21784. Login y base de datos no se reiniciaron. El cliente
retail fue `10.0.2.13.KX r575` y el personaje `Wingsjuanka`.

La primera petición aportó la evidencia de protocolo que faltaba: `StartSkill 30673`, flag/tipo 11 y
cinco bytes de cuerpo. Tras implementar `SocketExtractOptions`, la prueba individual obtuvo:

- target `16777289` / template `53038`, socket físico 0 = item `44684`;
- Mornstone `38568`: `2 -> 1`;
- socket 0: `44684 -> vacío`;
- producto nuevo `16777336` / template `44684`, bolsa slot 65;
- log: `returned=44684x1, destroyed=, labor=400, all=False`;
- UI: `Acquired: [Glorious Fireglow Lunagem: Healing]` y `Used 400 Labor Point(s)`.

Los 400 son correctos: la skill declara 500 base y Alquimia 70.000 aplica la reducción visible de
20%. Para dejar intacto el equipo del usuario, la misma `44684` se reinstaló con éxito en el primer
socket libre y luego el casco se reequipó. Snapshot final:

- casco `16777289` en `Equipment/Head`;
- datos completos restaurados:
  `[29381,44684,44683,44681,44682,44706,44707,44709,44708,4461,4548,4547,4611]`;
- no queda ninguna `44684` suelta; Mornstone `38568` queda en 1;
- sólo continúa activa Zone 351.

La persistencia se verificó además fuera de la caché viva: se salió normalmente a selección de
personaje y MySQL confirmó `16777289` en `slot_type=1, slot=0`, la Mornstone `16777335` con
`count=1` y ausencia de la fila temporal `16777336`. Un segundo ingreso de `Wingsjuanka` reconstruyó
el personaje en Western Hiram Mountains con el casco equipado, sin pérdida ni duplicación de items.

## Estado de validación

- Build/imagen Docker: 0 errores.
- TUnit: 1338/1338 correctas.
- Extracción, retorno a bolsa, reinstalación, reequipado y persistencia observada por API, MySQL y
  segundo ingreso: aceptados dentro del cliente retail r575.
