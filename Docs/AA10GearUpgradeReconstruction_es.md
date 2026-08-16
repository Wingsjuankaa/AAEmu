# Reconstrucción AA10 — Gear Upgrade, synthesis, awakening y Hiram

Fecha de cierre: 2026-08-15

Target: `Wingsjuankaa/AAEmu:rama_10`

Cliente: ArcheAge Returns `10.0.2.13 r575`

## Resultado

La cadena Gear Upgrade quedó operativa desde equipamiento Explorer de misión hasta Sacred Hiram T6:

- synthesis acepta hasta seis materiales, calcula EXP/coste, cambia grado y persiste el detalle;
- el cliente descuenta inmediatamente todos los stacks usados, sin necesitar relog;
- cada ascenso concede Change Attempts hasta `5/5` y conserva las líneas ya obtenidas;
- awakening ejecuta las rutas del compact, consume scrolls de forma atómica, hereda EXP y efectos,
  aplica probabilidad/pity y devuelve el paquete r575 esperado;
- los límites Hiram son T1 Celestial, T2 Divine, T3 Epic, T4 Mythic y T5/T6 Eternal;
- la prueba manual terminó en `Sacred Hiram Guardian Nodachi`, Eternal, `Max Grade`, cuatro Synthesis
  Effects y cinco Change Attempts.

No se activó `itemEvolvingReRoll`: el menú para cambiar estadísticas sigue siendo una frontera futura.

## Autoridades y comparadores

- Base del target: `aae593ef6874b2bde5cc1b3fa0d2a0f67c9e6bf0`.
- Padre obligatorio revisado: `upstream/client_version/zone-10.0.2_r575`, commit
  `a3c735c658ebe20d10cb50684b4b3e366b7d87e1`.
- PR comunitario estudiado: `AAEmu/AAEmu#1531`, head
  `e092f1fd28c578ff00534cb8ec2c9ac639856f4e`. Estaba cerrado y no fusionado. Se aprovecharon sus
  cierres de datos/wire r575, pero se reemplazó su orden de mutación por transacciones preflightadas.
- AA8 se usó sólo como comparador estructural para bonus en permille, planificación y sincronización;
  ningún ID, opcode, grado ni valor AA8 se trató como autoridad.
- Evidencia AA10: `game_decrypted.sqlite3`, compact retail, `x2game.dll` SHA-256
  `2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76`, capturas y logs de World.

## Síntomas y resolución

### Feature invisible

El cliente tenía datos de synthesis, pero ocultaba tooltip, EXP y panel porque faltaba el bit 141.
Se habilitó `itemEvolving` en `Configurations/Features.json`; `itemEvolvingReRoll` permanece apagado.

### Request mal decodificada

`CSStartSkillPacket` enmascaraba el tipo con cuatro bits. r575 usa los seis bits bajos: synthesis es
skill object 8 y awakening es 26. Se añadieron sus cuerpos exactos y su eco en el wire de cast:

```text
type 8:  u16 byteLength, u64 materialItemId[N], bool autoUseAaPoint
type 26: u32 mappingId
```

Longitudes parciales, más de seis slots, IDs duplicados o materiales ajenos se rechazan sin mutación.

### Datos y persistencia

`ItemManager` carga categorías, propiedades por grado, relaciones de materiales, pools de efectos,
mappings y grupos de awakening desde compact. `EquipItem` expone sobre su bloque PISC persistido:

- `EvolvingExp` en `GemData[3]`;
- hasta cinco IDs de Synthesis Effects en `GemData[13..17]`;
- `EvolveChance` para Change Attempts;
- `MappingFailBonus` para pity de awakening.

Los grados se recorren por `grade_order`, no por ID, porque Poor/Crude y Basic no ordenan
numéricamente. El EXP total de la fuente se reproduce en la escalera destino al despertar.

### Transacción y sincronización del inventario

El servidor ya persistía todos los consumos, pero un lote con varios `Take` actualizaba sólo el primer
stack en r575; los demás desaparecían visualmente recién al relog. La mutación sigue siendo atómica
bajo el lock del contenedor, pero cada tarea confirmada se publica en su propio
`SCItemTaskSuccessPacket`. Se añadieron preflights para:

- consumir una unidad de cada stack seleccionado por synthesis;
- consumir cantidades agregadas por template para scrolls/reagentes de awakening;
- restaurar el plan completo si un stack queda obsoleto antes del commit.

`SCItemDetailUpdatedPacket` publica el snapshot compacto de cambios PISC. `ItemAction.UpdateDetail`
usa otra representación: una unión interna fija de 128 bytes reconstruida desde `FUN_39a3ccd0`; enviar
allí el snapshot compacto deja icono/tooltip rotos. Los paquetes de resultado reconstruidos son `0xCD`
para synthesis y `0xD4` para awakening.

### Change Attempts y efectos

Cada promoción efectiva concede un intento hasta cinco. Los atributos existentes se preservan por la
identidad semántica `unit_attribute_id + unit_modifier_type_id`; al cambiar de categoría se busca el
grupo equivalente, respetando `inherit_priority_id`. Sólo se sortean los slots nuevos desbloqueados.
Los bonuses de equipo usan el valor del grupo correspondiente al grado actual.

### Awakening

El special effect `ItemChangeMapping` valida grupo, template, grado y mapping solicitado. Calcula
`success` y `fail_bonus` en basis points, consume el reactivo antes de comprometer el resultado,
restaura snapshot ante fallo transaccional y evita el doble consumo genérico. En un fallo legítimo se
preserva el item y aumenta pity; en éxito se cambian template/categoría y se heredan EXP/efectos.

### Caps Hiram y precedencia de `game_pak`

La proyección r575 distribuida dejó `max_evolving_grade=7` en todas las categorías Hiram. Las cuarenta
rutas por tier demuestran que T2/T3/T4/T5 deben llegar respectivamente a 8/9/11/12; T6 conserva 12.
La función nativa AA10 `0x3978C940` lee ese byte directamente, por lo que no corresponde introducir
una excepción exclusiva del servidor.

`Scripts/PatchAa10HiramGradeCaps.py` corrige transaccionalmente estas categorías:

| Categorías | Tier | Cap |
|---|---|---:|
| 494, 496-506 | T1 | 7 |
| 508-519 | T2 | 8 |
| 524-535 | T3 | 9 |
| 606-617 | T4 | 11 |
| 699-710 | T5 | 12 |
| 826-837 | T6 | 12 |

El cliente da prioridad a `game/db/compact.sqlite3` dentro de `game_pak`, incluso con `-devmode`.
Por eso hay que parchear la SQLite suelta, el compact de World y reinsertar la copia cliente. La
herramienta versionada `Tools/PakEntryReplace` exige hash previo, reemplazo del mismo tamaño y verifica
el SHA-256 reabriendo el paquete.

```powershell
python Scripts/PatchAa10HiramGradeCaps.py `
  '<cliente>\game\db\compact.sqlite3' `
  '.server_files\AAEmu.Game\Data\compact.sqlite3'

dotnet run --project Tools\PakEntryReplace\PakEntryReplace.csproj --configuration Release -- `
  '<cliente>\game_pak' 'game/db/compact.sqlite3' `
  '<cliente>\game\db\compact.sqlite3' `
  '68919695CDD12C7B9CB4AC9BEA3828132B83C95D7DCCF46AA3E113CEA756507F'
```

Identidad validada de la entrada parcheada: 440823808 bytes, SHA-256
`90839A7FBF260979C401FC4563F4DCCACD62E8A6F4ED25EA9C2ECA9E0DA2A2B0`, `PRAGMA quick_check=ok`.
No se versionan el cliente, `game_pak`, SQLite ni respaldos.

## Mapa de cambios versionados

- `Configurations/Features.json`: feature gate.
- `Core/Managers/ItemManager.cs` e interfaz: carga y consultas de datos Gear Upgrade.
- `Core/Packets/C2G/CSStartSkillPacket.cs`, `SkillObject.cs`, `SkillCastWire.cs`: requests/wire.
- `SCItemEvolvingResultPacket`, `SCItemChangeMappingResultPacket`,
  `SCItemDetailUpdatedPacket` y offsets: respuestas r575.
- `EquipItem.cs`, `EquipItemTemplate.cs`, `ItemRndAttrCategory.cs`, servicios de cálculo: estado,
  progresión, RNG y herencia.
- `ItemEvolving.cs`, `ItemChangeMapping.cs`, `Skill.cs`: efectos y ownership de consumo.
- `ItemContainer.cs`, acciones de item, `Inventory.cs`: commit atómico y sincronización inmediata.
- `Unit.cs`: aplicación de Synthesis Effects al equipar.
- `Scripts/PatchAa10HiramGradeCaps.py` y `Tools/PakEntryReplace`: parche reproducible de datos.
- `AAEmu.UnitTests`: wire, cálculo, atributos, consumo, feature gate y regresiones.

## Validación automática

Gates de cierre:

```powershell
dotnet restore
dotnet build --configuration Release --no-restore
dotnet test --project AAEmu.UnitTests --configuration Release --no-build --no-restore
```

Último resultado antes de publicar: 1262 pruebas correctas, 0 errores, 0 omitidas. Ambos compacts y la
entrada reextraída de `game_pak` devolvieron `PRAGMA quick_check=ok`.

## Validación manual completa

La Nodachi `16777233` recorrió estas rutas en World:

```text
857:  45325 Hiram -> 45637 Radiant
8450: 45637 Radiant -> 45830 Brilliant
8490: 45830 Brilliant -> 46840 Glorious
9159: 46840 Glorious -> 48364 Exalted
8639: 48364 Exalted -> 53022 Sacred
```

Se verificaron los caps Celestial/Divine/Epic/Mythic/Eternal, consumo inmediato multi-stack,
persistencia de cinco Change Attempts y herencia de efectos. La última ruta falló legítimamente tres
veces y tuvo éxito al cuarto intento, ejercitando el pity 10/20/30/40 %. El resultado persistido fue
template 53022, grado 12 Eternal, EXP 2800034 y grupos `[4442,4515,4517,4698]`; el cliente mostró
`Sacred Hiram Guardian Nodachi`, `Max Grade` y cuatro líneas.

## Operación y rollback

- Runbook de Zone/cliente y parche de parpadeo: `Docs/AA10NativeZoneRunbook_es.md`.
- Comandos de prueba: `Docs/AA10HiramProgressionTestCommands_es.md`.
- Detalle de synthesis: `Docs/AA10QuestSynthesisCheckpoint_es.md`.
- Cap Eternal de undergarments: `Docs/AA10UndergarmentSynthesisGradeCap_es.md`.
- Detalle de awakening: `Docs/AA10QuestAwakeningCheckpoint_es.md`.
- Respaldo local validado del `game_pak` anterior al parche:
  `E:\AAEmu-Research\backups\aa10-hiram-grade-caps-20260815\game_pak-before-hiram-caps`.

Para rollback, cerrar cliente, restaurar el `game_pak` completo y las SQLite desde sus respaldos,
reiniciar World y volver a levantar las Zones nativas. No mezclar compacts AA8/Kakao con r575.

## Fronteras pendientes

- `itemEvolvingReRoll` y su menú/coste/packet/transacción.
- Instalación de Lunagem reconstruida posteriormente; véase
  `Docs/AA10LunagemSocketingReconstruction_es.md`. Reemplazo/extracción sigue pendiente.
- Pruebas dedicadas de cristalización y scrolls no Hiram.
- Bugs individuales de skills, fuera del alcance de Gear Upgrade.
