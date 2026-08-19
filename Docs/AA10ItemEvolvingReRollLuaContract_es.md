# Replace Stat / ItemEvolvingReRoll — reconstrucción AA10 r575

## Estado

Reconstrucción estática e implementación cerradas el 19 de agosto de 2026 para ArcheAge Returns
`10.0.2.13 r575`. Se implementaron la ventana habilitada por feature, el request tipo 9, los modos
aleatorio y seleccionable, las reglas de datos, el consumo atómico, la persistencia del modificador y
el paquete nativo `0xCE`. La aceptación dinámica se registra al final de este documento.

## Identidad de evidencia

- `x2game.dll` SHA-256:
  `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734`;
- SQLite full SHA-256:
  `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`;
- compact retail SHA-256:
  `0ADAA070936F8AFBE0A60307C391CF1C08ECCB98DD48A32024D4F295C140FC86`;
- `evolving_enchant.alb` retail SHA-256:
  `DAB67A1FDFFF00D2CC3384B65B91348676F16DCD88E17A790B2406CBC6710AEC`;
- `evolving_attr_list_select.alb` retail SHA-256:
  `77469FAB2BE72AF38DBB4C3219E7C6D40DB253C59E0FC2732A63B80825AA140F`.

El dossier reproducible está en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\item-evolving-reroll-frontier`.

## Aporte de lua-types

`Inspect-Aa10LuaApi.ps1` encontró 37 sitios de llamada, 28 llamadas nativas únicas, 28/28
declaradas por `lua-types` y los 28 pares namespace/método presentes como strings en el binario
exacto. El artefacto es
`temper-frontier\item-evolving-reroll-lua-api-coverage.json`, SHA-256
`D70F2DBEDB080FF2889505D8E2C9586B3F0BBF6F0FC09BABF6F2B484D51E5631`.

Esto redujo rápidamente el frente a `X2ItemEnchant`; firmas, índices y wire se corroboraron después
en Lua retail y `x2game.dll`. El catálogo sigue siendo un índice estructural, no autoridad ejecutable.

## Ventana y request confirmados

Replace Stat es el submodo `2` de Evolving y se abre con
`X2ItemEnchant:SwitchItemEnchantEvolvingReRollMode()`. La superficie completa depende del feature
`itemEvolvingReRoll` (`161`). La variante garantizada usa
`X2ItemEnchant:IsEvolvingReRollSelect()` y `GetEvolvingRndAttrsInfo(selAttrIndex)` para ofrecer sólo
grupos del mismo group set cuyo atributo todavía no está ocupado.

El consumer ejecuta:

```lua
X2ItemEnchant:Execute(selAttrIndex, false, selectedChangeToGroupType or 0)
```

La vtable `X2::GameClient::ItemEvolvingReRoll` está en `0x39DFC448`. Su `Execute`,
`FUN_39127990`, resta uno al índice Lua antes de llamar a `FUN_391275D0`. Esta última construye:

```text
skill-object type 9
u32 modifierIndex     # índice físico 0-based
u32 changeToGroupId   # 0 aleatorio; group id real en modo seleccionable
```

`GetEvolvingRndAttrsInfo` termina en `FUN_3912B2B0`: `groupSetType` es el ID del group set y
`changeToGroupType` es el ID real de `item_rnd_attr_unit_modifier_groups`, no un enum de UI.

## Resultado nativo

`SCItemReRollEvolvingResultPacket` tiene vtable `0x39E3B140`, functor opcode `0xCE`, lector
`FUN_39AB5C40` y handler `FUN_39354BF0`. El body exacto mide 24 bytes:

```text
u64 itemId
u8  modifierIndex
bool changed
before { u16 unitAttributeId, u8 unitModifierTypeId, i32 value }
after  { u16 unitAttributeId, u8 unitModifierTypeId, i32 value }
```

El handler usa ambos modificadores para la ventana de resultado y refresca el índice afectado.

## Reglas AA10 y reactivos

Full y compact pasan `PRAGMA quick_check=ok` y coinciden en los datasets canónicos consultados:

- 5 `item_sets`: `8F80107AC478E8CC07B7872F7D819441AC89BD08873751E00ADBBD57E1555F81`;
- 13 `item_set_items`: `4737969EB03D1F31571D1996B5B6420BA84135D457F4C25279B1F8C5E2B2FF45`;
- 817 categorías con reroll: `D93754B9298883011E9BFC4AC6E82591A5E1A5CADCD86B19639F770E38CB509B`.

Los sets `230`, `248`, `250` y `252` son de reemplazo y `232` expresa explícitamente que no se
puede reemplazar. Los reactivos aleatorios usan skill `32060`/efecto `136`; los seleccionables usan
skill `46234`/efecto `187`. Las filas activas exigen una unidad. El servidor valida que el reactivo
exacto esté en la bolsa, que su `UseSkillId` corresponda al skill y que pertenezca al
`ReRollItemSetId` de la categoría objetivo.

La resolución sólo sustituye el slot solicitado, permanece en su group set, exige valor para el
grado actual, evita el mismo atributo y atributos ya ocupados, y pondera por `Weight` en modo
aleatorio. En modo seleccionable el ID solicitado debe estar dentro de ese mismo conjunto legal.

## Implementación

- `SkillObjectType.EvolvingRerollOptions = 9`, lectura y eco íntegro en Started/Fired;
- `ItemRandomAttributeResolver.ResolveReroll` para resolución determinista y validable;
- `ItemEvolvingReRoll` para efecto `136` y `ItemEvolvingSelectReRoll` para `187`;
- `SCItemReRollEvolvingResultPacket` en opcode `0xCE`, layer `5`;
- consumo atómico de la piedra seleccionada antes de mutar el equipo;
- actualización inmediata de bonuses si el equipo está puesto;
- feature `itemEvolvingReRoll` habilitado sólo después de cerrar código y pruebas.

## Pruebas

Las pruebas fijan el round-trip del request, el eco de cast, los 24 bytes del resultado, selección
aleatoria ponderada, selección explícita, preservación de slots, índice inválido, group set ajeno y
atributo ya ocupado. El resultado de build, suite completa y aceptación dinámica se añade tras cada
despliegue validado.

Resultado de esta reconstrucción: `dotnet test AAEmu.UnitTests` en Release ejecutó 1.329 pruebas,
con 1.329 correctas, 0 errores y 0 omitidas. Un caso representativo usa los IDs AA10 de categoría
`748`, group set principal `508` y bonus `509`: conserva `3911` y reemplaza únicamente el slot 0 de
`3906` (Strength, atributo 0) a `3908` (Stamina, atributo 2), produciendo `[3908,3911]`. La consulta
al compact operativo confirma que ambos grupos existen en grado 3, tienen peso 1 y valor mínimo 24.

Se construyó y desplegó la imagen
`sha256:bb51d5ef59da56295a0d24145aafde29b0f2f0b8c96776b4bcd5e68b14566375`.
Game arrancó en 80,86 s, quedó healthy, registró `Server started!` y Login confirmó
`Registered GameServer GameServerId 1`. Dentro del contenedor se verificaron el feature 161, el
handler seleccionable y el packet `0xCE`.

## Aceptación dinámica

Aceptación completada el 2026-08-19 con el cliente retail exacto
`10.0.2.13.KX r575`, el personaje `Wingsjuanka` y sólo la partición necesaria para su posición
persistida: `zone_id=351`, perfil `o_hirama_the_west_2`. Se inició directamente
`AAEmu.ZoneHost.exe +zone o_hirama_the_west_2`; no se levantó el agregado ni otra Zone. La prueba
verificó proceso, conexión TCP estable hacia Game `:1240`, `ZWJoin`, `WZJoinResponse`, `ZoneLoaded`
y heartbeats posteriores.

La primera interacción real del cliente reveló un segundo contrato nativo que el corpus estático no
hacía explícito: cuando Hiram dispone de `Change Attempts`, el cliente ejecuta skill `39836` con
`SkillCasterUnit`, target de item y skill-object tipo `9`, sin cargar piedra. El servidor anterior
rechazaba el cast porque exigía siempre `SkillItem`. La implementación acepta ahora los dos pagos,
manteniendo la variante seleccionable restringida a un grupo explícito:

- intento Hiram sin piedra: exige `EvolveChance > 0`, decrementa exactamente una vez y emite el
  detalle actualizado además de `0xCE`;
- Serendipity Stone: valida y consume la pila exacta como antes, sin gastar `EvolveChance`.

Prueba visual y transaccional sobre `Celestial Hiram Guardian Shoes`, item `16777293`, template
`45342`, índice `0`:

1. Sin piedra: `Stamina 60 -> Intelligence 60`, grupo `1234 -> 1235`, Change Attempts `3 -> 2` y
   Bound Serendipity Stone `46682` permaneció en `3`. Log:
   `payment=change-attempt, attempts=2`.
2. Con piedra: `Intelligence 60 -> Strength 60`, grupo `1235 -> 1232`, piedras `3 -> 2` y Change
   Attempts permaneció en `2`. Log: `payment=item:46682, attempts=2`.

La interfaz se refrescó inmediatamente en ambos casos y mostró los diálogos Old Effect/New Effect.
La imagen desplegada fue
`sha256:668f202cf2268194b9154ed80cc3c9c17fcf194aa6ceec667907787c57523e48`; la suite Release
completa terminó con `1329/1329` pruebas correctas, `0` errores y `0` omitidas.
