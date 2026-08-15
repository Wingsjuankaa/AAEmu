# Checkpoint AA10 — awakening de equipamiento de misión

Fecha: 2026-08-15

## Síntoma y causa demostrada

El cliente r575 aceptaba Explorer's Nodachi Arcane y el Equipment Awakening Scroll Rank 1,
mostraba 100 %, casteaba skill 42200 y reproducía sonido/animación, pero el arma no cambiaba ni tras
reloguear. El log de World cerró la causa exacta:

```text
EffectTemplate - Unknown special effect: ItemChangeMapping
```

La petición, el target y el skill object ya llegaban al servidor. Faltaba ejecutar el efecto especial
165 y devolver el resultado D4; el consumo genérico sí alcanzó a gastar el scroll del intento fallido.

## Autoridades y revisión comunitaria

- Target: `Wingsjuankaa/AAEmu:rama_10`, base inicial
  `aae593ef6874b2bde5cc1b3fa0d2a0f67c9e6bf0`.
- Padre obligatorio revisado: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`, commit
  `a3c735c658ebe20d10cb50684b4b3e366b7d87e1`.
- Único PR comunitario localizado: `AAEmu/AAEmu#1531`, cerrado y no fusionado, head
  `e092f1fd28c578ff00534cb8ec2c9ac639856f4e`. No existe un PR posterior que lo reemplace.
- Del PR se conservaron el cierre de protocolo r575, las tablas de mapping y el cuerpo del paquete
  resultado. No se copió su orden de transacción: ese código mutaba el arma antes de que el consumo
  genérico confirmara los scrolls.
- Datos activos: `.server_files/AAEmu.Game/Data/compact.sqlite3` r575.

## Contrato nativo fijado

- Skill object 26 transporta el `mapping_id` elegido por el cliente.
- `value1` del special effect selecciona `item_change_mapping_groups`.
- La ruta sólo es válida si coinciden grupo, template fuente y grado fuente; un mapping id enviado por
  el cliente nunca puede escapar de esas condiciones.
- `success` y `fail_bonus` usan basis points sobre escala 10000. `MappingFailBonus` almacena porcentaje
  entero y suma 100 basis points por punto.
- El resultado r575 es `SCItemChangeMappingResultPacket`, opcode `0xD4`, nivel 1:
  item completo antes, item completo después, `u32 mappingId`, `u8 result` (0 éxito, distinto de 0 fallo).
- La herencia de synthesis convierte el grado fuente a EXP total y reproduce ese EXP sobre la escalera
  de la categoría destino; no copia el grado directamente.
- El efecto toma propiedad del consumo. Todos los `consume_item_id/count` se agregan, se validan y se
  descuentan atómicamente entre stacks; luego se desactiva el consumo genérico para impedir doble cobro.
  Si el pago no puede cerrarse, se restaura template, grado, pity y detalle del arma.

## Regresión exacta de la primera captura

- Scroll Rank 1: item 47866 → skill 42200 → effect 78565 → special effect 44600 → grupo 48.
- Ruta 900: Explorer's Nodachi 47784, Arcane grade 4 → Radiant Explorer's Nodachi 47894.
- Categoría fuente 636: 14 + 21 + 28 = 63 EXP base al llegar a Arcane, más el EXP parcial
  almacenado que ya tenga el arma.
- Categoría destino 646: Basic cuesta 63 EXP. Con una fuente Arcane en 0/0, el resultado base es
  Grand grade 2 con 0 EXP; el EXP parcial fuente se conserva sobre ese resultado.
- Grupo 48 tiene `success=10000`, por lo que esta ruta es garantizada.

## Validación

```powershell
dotnet test AAEmu.UnitTests\AAEmu.UnitTests.csproj --no-restore --no-build -- `
  --no-ansi --no-progress
```

Resultado: 1252 correctas, 0 errores, 0 omitidas. Las regresiones nuevas fijan selección de ruta,
rechazo de mapping adulterado, escala de chance/pity y la conversión 47784 Arcane → 47894 Grand.

## Prueba manual mínima

1. Confirmar que el arma continúa siendo 47784 Arcane. El intento anterior no la modificó, aunque sí
   consumió un scroll.
2. Si hace falta reponer uno: `/item add self 47866 1`.
3. Abrir Gear Upgrade → Awakening, colocar el arma y un scroll Rank 1, confirmar una sola vez.
4. Deben ocurrir juntas estas tres cosas: bajar el stack exactamente en uno, aparecer Awakening Results
   exitoso y cambiar el mismo item a 47894 Grand.
5. Reloguear y confirmar que template, grado y EXP siguen iguales.

Para Rank 2 y Rank 3, usar después los scrolls 47867 y 47952 respectivamente; no saltar de tier si el
resultado anterior todavía no persiste tras relog.

## Validación manual real — 2026-08-15

El usuario confirmó el primer intento después del despliegue. World registró:

```text
17:42:22 Skill 42200, caster Wingsjuanka
17:42:25 S->C 0D4 SCItemChangeMappingResultPacket
17:42:25 ItemChangeMapping: Wingsjuanka route 900, item 47784->47894, grade 2, result success
```

El cliente mostró `Radiant Explorer's Nodachi`, Grand, `37/139` EXP y el Synthesis Effect
`Agility +25`. El resultado de EXP cierra la herencia real: la fuente conservaba 37 EXP parciales,
por lo que representaba 63 + 37 = 100; el tier destino gastó 63 para subir de Basic a Grand y dejó
37 en la nueva barra. La categoría 646 permite una línea en Grand y su set 325 sortea una entre los
cinco atributos principales; en esta ejecución eligió Agility.

La fila persistida aún mostraba 47784 inmediatamente antes del relog, como corresponde al intervalo
de guardado: la validación final pendiente es salir/reentrar y comprobar que template 47894, grado 2,
37 EXP y la línea sorteada sobreviven. No avanzar a Rank 2 hasta cerrar esa comprobación.

## Herencia de Synthesis Effects — 2026-08-15

Una cadena completa con rifle reveló que el awakening funcional aún regeneraba las líneas:

```text
route 8069: 50799 -> 50801, grade 2
route 8070: 50801 -> 50800, grade 3
route 8071: 50800 -> 50836, grade 4 (Hiram)
```

La primera ruta sorteó Agility correctamente. La segunda sustituyó ese primer stat y añadió otro; la
conversión Hiram volvió a sustituir los stats farmeados. La causa era una llamada incondicional a
`RollRndAttrGroups` después de cambiar de categoría.

La corrección hereda cada línea por su identidad semántica `unit_attribute_id +
unit_modifier_type_id`. Cuando la categoría cambia, busca el grupo equivalente del set destino,
usando `inherit_priority_id` cuando los datos lo declaran. Después completa solamente los slots nuevos:

- Rank 1: añade la primera línea;
- Rank 2: conserva la primera y añade la segunda;
- Hiram: conserva las dos y añade la tercera.

Los mappings que permanecen en la misma categoría conservan sus ids directamente; una categoría
destino con cero slots elimina las líneas porque no puede representarlas. Si una línea no posee un
equivalente inequívoco, el intento se rechaza antes de cobrar el scroll en lugar de aleatorizar el
equipo.

El item usado antes de la corrección ya quedó alterado y no puede reconstruirse automáticamente: sólo
se conoce con certeza que su primera línea original era Agility. La validación debe hacerse con una
nueva arma para observar toda la cadena sin estado contaminado.

Validación automatizada combinada: 1260 pruebas correctas, 0 errores. Hay regresiones específicas para
Rank 2, Hiram y mappings que no cambian de categoría.

## Primera cadena manual completa después de la corrección — 2026-08-15

El usuario completó una cadena limpia de zapatos Explorer hasta Hiram. Los logs de World fijaron la
secuencia del mismo item `16777240`:

```text
ItemEvolving grade 0->4, change attempts +3=3
route 911: 47810 -> 47905, effects [] -> [2615]
ItemEvolving grade 2->3, change attempts +1=4, effects [2615]
ItemEvolving grade 3->5, change attempts +1=5, effects [2615]
route 1012: 47905 -> 47831, effects [2615] -> [2776,2876], added [2876]
ItemEvolving grade 3->6, change attempts +0=5, effects [2776,2876]
route 1050: 47831 -> 45342, effects [2776,2876] -> [1233,1333,1330], added [1330]
```

La captura final mostró `Hiram Guardian Shoes`, Arcane, `91/1085` EXP, cinco Change Attempts y las
tres líneas esperadas: Agility, Received Siege Damage y Received Ranged Damage. La fila MySQL confirmó
el estado persistido, no sólo el tooltip del cliente: template `45342`, grade `4`, `EvolveChance=5`,
`EvolvingExp=91` y grupos `[1233,1333,1330]`.

Resultado de la primera cadena: correcto. Queda una segunda repetición independiente para aumentar la
confianza y una comprobación por relog si se desea cerrar también la recarga desde persistencia.

## Segunda cadena manual y progresión Hiram — 2026-08-15

La segunda repetición independiente también llegó correctamente a Hiram. World registró el item
`16777237` por las rutas `908`, `1009` y `1047`, preservando y ampliando sus efectos
`[] -> [2603] -> [2764,2854] -> [1221,1311,1312]`. MySQL confirmó template `45339`, grade `4`,
`EvolveChance=5`, `EvolvingExp=13` y los tres grupos finales. Con dos cadenas correctas queda cerrada
la regresión Explorer -> Hiram; la siguiente frontera manual es Hiram T1 -> T6.

El compact retail r575 define para los zapatos de tela la cadena:

| Tier | Item | Grado exigido para despertar | Destino |
|---|---|---|---|
| T1 | 45342 Hiram Guardian Shoes | Celestial (7) | 45655 Radiant |
| T2 | 45655 Radiant Hiram Guardian Shoes | Divine (8) | 45848 Brilliant |
| T3 | 45848 Brilliant Hiram Guardian Shoes | Epic (9) | 46858 Glorious |
| T4 | 46858 Glorious Hiram Guardian Shoes | Mythic (11) | 48382 Exalted |
| T5 | 48382 Exalted Hiram Guardian Shoes | Eternal (12) | 53042 Sacred |

Scrolls de prueba confirmados por la clausura
`items.use_skill_id -> skill_effects.effect_id -> effects.actual_id -> special_effects.value1 ->
item_change_mapping_groups`:

- 47926, grupo 47: T1 -> T2, 100 %;
- 52021, grupo 301: T2 -> T3, 100 %;
- 52022, grupo 302: T3 -> T4, 100 %;
- 54452, grupo 317: T4 -> T5, 100 %;
- 53799, grupo 313: T5 -> T6, 10 %, sin cristalización y +10 puntos porcentuales de pity por fallo.

Materiales Hiram aceptados por la relación de grupos `1 -> 2`: 48841 Eternal Hiram Infusion
(12,500 EXP), 51591 Sacred Hiram Infusion (30,000 EXP) y 54328 Ancestral Hiram Infusion
(500,000 EXP). Para la prueba controlada usar 48841 en T1-T2, 51591 en T3 y 54328 desde T4.

## Límite de grado de synthesis Hiram — corrección final 2026-08-15

La primera prueba T1 reveló que synthesis permitía promover una Hiram Guardian Nodachi desde
Celestial (7) a Divine (8). Eso dejaba el item fuera de la ruta retail: el mapping 857 del grupo 47
exige exactamente template 45325 en grado 7. El rechazo posterior de awakening era correcto; el
mensaje cliente `Not enough $$.` era la localización engañosa de `NotEnoughRequiredItem`, no una
falta real de oro.

`ItemSynthesisCalculator` ahora resuelve el límite por el orden de los grados y, al alcanzarlo,
satura la EXP en el requisito de la barra final sin promover al grado siguiente. La regresión usa los
datos de categoría 496 y prueba una entrada de 500,000 EXP: el resultado obligatorio es Celestial con
`13714/13714`, nunca Divine. Validación automatizada: 1261 pruebas correctas, 0 errores.

La instancia afectada `16777233` se normalizó de Divine a Celestial y de 3572 EXP fuera de rango a
`13714/13714`, conservando los tres grupos de estadísticas `[1194,1267,1269]`, sus cuatro Change
Attempts y el resto del detalle binario. La repetición manual debe usar el scroll 47926: se espera
consumo de una unidad, paso a Radiant, conservación de estadísticas y persistencia después de relog.

La continuación T2 descubrió una segunda parte del problema: el `compact.sqlite3` distribuido por
r575 deja `max_evolving_grade=7` no sólo en T1, sino también en todas las categorías Hiram T2-T6.
Ese valor no puede ser correcto para los tiers posteriores porque las cuarenta rutas de cada grupo
exigen los siguientes grados fuente:

| Categorías | Tier | Límite correcto | Evidencia de awakening |
|---|---|---:|---|
| 494, 496-506 | T1 | Celestial (7) | grupo 47 exige grade 7 |
| 508-519 | T2 | Divine (8) | grupo 301 exige grade 8 |
| 524-535 | T3 | Epic (9) | grupo 302 exige grade 9 |
| 606-617 | T4 | Mythic (11) | grupo 317 exige grade 11 |
| 699-710 | T5 | Eternal (12) | grupo 313 exige grade 12 |
| 826-837 | T6 | Eternal (12) | último `grade_exp` positivo de la categoría |

No se resolvió con una excepción exclusiva del servidor. En `x2game.dll` r575 SHA-256
`2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76`, la función `0x3978C940`
lee directamente el byte `maxEvolvingGrade` en el offset `+0x18`
de la categoría y lo compara con el grado actual; también consulta `gradeExp` para `canEvolve`. Por
eso hay que corregir la proyección que consume cada runtime. El parche SQLite reproducible es
`Scripts/PatchAa10HiramGradeCaps.py`.

En la prueba real de la Nodachi Radiant, World registró un inicio Heroic con 5632 EXP y consumo de
una infusión de 12500 más dos de 30000 EXP. Esos materiales tienen cero probabilidad de bonus en
r575. El tope obsoleto dejó la instancia `16777233` en Celestial `38433/38433`; el resultado correcto
es exactamente Divine con 9326 EXP. La instancia se reparó a ese estado preservando template 45637,
cinco Change Attempts y los efectos `[1355,1428,1430]`.

Hashes después del parche: cliente `90839A7FBF260979C401FC4563F4DCCACD62E8A6F4ED25EA9C2ECA9E0DA2A2B0`;
servidor `DF10A47C10D65D6AE64187BE37FE1708646EF5CED284E46ADA3016E112957E0A`.
Ambos devolvieron `PRAGMA quick_check = ok`. La regresión automatizada combinada terminó con 1262
pruebas correctas y cero errores.

### Corrección de precedencia del cliente

La primera aplicación sólo cambió `<cliente>/game/db/compact.sqlite3` y el compact de World. El
awakening T2 -> T3 funcionó en servidor, pero el tooltip de Brilliant Hiram siguió mostrando
`Synthesis Available (~Celestial)`. La captura aportó una prueba especialmente útil: el denominador
`9326/40964` demostraba que el cliente había seleccionado la categoría T3 525, pero su límite seguía
siendo 7. No era caché ni otra categoría.

`game_pak` contiene su propia entrada `game/db/compact.sqlite3`, SHA-256 original
`68919695CDD12C7B9CB4AC9BEA3828132B83C95D7DCCF46AA3E113CEA756507F`, y tiene prioridad sobre la
copia suelta incluso con este arranque `-devmode`. Se añadió la herramienta versionada
`Tools/PakEntryReplace`, que exige hash previo y el mismo tamaño, recalcula el MD5 interno, reabre el
paquete y compara SHA-256:

```powershell
dotnet run --project Tools/PakEntryReplace/PakEntryReplace.csproj --configuration Release -- `
  <cliente>/game_pak game/db/compact.sqlite3 <compact-corregido> `
  68919695CDD12C7B9CB4AC9BEA3828132B83C95D7DCCF46AA3E113CEA756507F
```

La entrada reextraída después del reemplazo mide 440823808 bytes, tiene SHA-256
`90839A7FBF260979C401FC4563F4DCCACD62E8A6F4ED25EA9C2ECA9E0DA2A2B0`, pasa `quick_check` y devuelve
los caps 7/8/9/11/12/12. El `game_pak` conserva sus 68963162112 bytes. Rollback completo:
`E:/AAEmu-Research/backups/aa10-hiram-grade-caps-20260815/game_pak-before-hiram-caps`.

## Cierre manual T1 -> T6 — 2026-08-15

Después de corregir la entrada efectiva de `game_pak`, la Nodachi `16777233` completó toda la cadena:

```text
route 857:  45325 -> 45637, efectos [1194,1267,1269] -> [1355,1428,1430]
route 8450: 45637 -> 45830, efectos [1355,1428,1430] -> [1631,1704,1706]
route 8490: 45830 -> 46840, efectos [1631,1704,1706] -> [2205,2278,2280]
route 9159: 46840 -> 48364, efectos [2205,2278,2280] -> [3104,3177,3179]
route 8639: 48364 -> 53022, efectos [3104,3177,3179] -> [4442,4515,4517,4698]
```

T2 llegó a Divine, T3 a Epic, T4 a Mythic y T5 a Eternal antes de aceptar su scroll. La ruta final
falló tres veces sin mutar template ni stats y tuvo éxito al cuarto intento, cubriendo pity
10/20/30/40 %. T6 añadió exclusivamente el cuarto slot permitido. MySQL persistió template 53022,
grade 12, `EvolveChance=5`, `EvolvingExp=2800034` y los cuatro grupos. La captura final mostró
`Sacred Hiram Guardian Nodachi`, Eternal y `Max Grade`.

Con esto queda cerrada la progresión manual Explorer -> Hiram -> Sacred T6. El índice técnico y los
pasos reproducibles de despliegue están en `Docs/AA10GearUpgradeReconstruction_es.md`.
