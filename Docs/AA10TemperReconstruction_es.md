# Reconstrucción AA10 r575 — Temper / Refurbishment

Fecha de cierre: 2026-08-16

Target: `Wingsjuankaa/AAEmu:rama_10`

Cliente: ArcheAge Returns `10.0.2.13 r575`

## Resultado

Temper quedó reactivado y reconstruido de extremo a extremo. El cliente muestra la pestaña de
Tempering, ejecuta el casteo de 1.500 ms, consume catalizador/charm y moneda por la transacción
normal, persiste la escala y actualiza DPS/defensa, tooltip e inventario. La aceptación manual
recorrió una Nodachi desde `+0` hasta `+19`, superó el antiguo bloqueo en `+12` y confirmó los charms
de éxito y Anchoring sin degradación.

No se modificó ningún `.alb`: las vistas retail estaban presentes y completas. La reactivación se
hizo enviando el feature bit nativo `itemCapScale` y restaurando en el compact el techo +30 que la
distribución deshabilitada había dejado en +12.

## Reactivación de la feature

La decompilación de `game/ui/enchant/enchant_window.alb` demuestra que el router añade la página
`refurbishment` únicamente cuando `featureSet.itemCapScale` está activo. El servidor ahora:

1. configura `itemCapScale=true` en `AAEmu.Game/Configurations/Features.json`;
2. serializa el bit 54 en el feature set (`byte 6: 0x21 -> 0x61`);
3. exige el mismo bit antes de cobrar, consumir o mutar el special effect 126.

Esto reactiva sólo Temper. Las vistas `itemEvolvingReRoll` (Replace Stat, bit 161) e
`itemSmelting` (bit 178) permanecen apagadas porque sus transacciones de servidor todavía no están
reconstruidas.

Los ALB inspeccionados conservaron su identidad retail:

| Archivo | SHA-256 |
|---|---|
| `enchant_window.alb` | `EB579BCB889A987499D44506C315DE0250209CA54273C25F4BFD68537691CACD` |
| `refurbishment.alb` | `FCD9C75F343B4FC5EFCDB97991233FFEDE8672F36314C4A9B2A636A00D1DFB40` |
| `refurbishment_view.alb` | `1E4249CF5086A40AD5D171D818603C68B222F704E453E918EF7DF03E627C2D0C` |

La extracción, decompilación y evidencia nativa están en:

`E:\AAEmu-Research\output\aa10-client-forensics\temper-frontier`

## Catálogo y restauración del techo +30

AA10 r575 contiene 32 filas `enchant_scale_ratios`, IDs `0..31`: `0` es `none`, `1..30` son los
niveles jugables y `31` funciona como descriptor sin restricción en los supports. El descriptor
`+30` tiene escala `250`, equivalente al multiplicador `1 + 250/1000 = 1,25`.

Los cuatro special effects retail declaran `value4=30`, pero todos los templates temperables
venían con `items.max_enchant_scale_id=12`. La corrección reproducible
`Scripts/PatchAa10TemperScaleCaps.py` valida el catálogo, los cuatro efectos, cobertura exacta,
caps homogéneos, tamaño y `PRAGMA quick_check`; después cambia transaccionalmente sólo `12 -> 30`.

| Proyección | Templates | Armas | Armaduras | Otros |
|---|---:|---:|---:|---:|
| compact cliente retail | 6.461 | 2.355 | 4.106 | 0 |
| compact completo de runtime | 6.534 | 2.384 | 4.142 | 8 |

Comando reproducible:

```powershell
python Scripts/PatchAa10TemperScaleCaps.py `
  '<cliente>\game\db\compact.sqlite3' `
  '.server_files\AAEmu.Game\Data\compact.sqlite3'
```

El cliente prioriza `game/db/compact.sqlite3` dentro de `game_pak`. La copia corregida se reinsertó
con `Tools/PakEntryReplace`, que exige hash previo, tamaño lógico idéntico, recalcula el MD5 interno,
reabre el paquete y vuelve a extraer la entrada para verificarla.

```powershell
dotnet run --project Tools\PakEntryReplace\PakEntryReplace.csproj --configuration Release -- `
  '<cliente>\game_pak' 'game/db/compact.sqlite3' `
  '<cliente>\game\db\compact.sqlite3' `
  '075A661C865E2C9357AB9C9E084100C17C832EFAF6913669D672FCA78632411B'
```

### Identidad desplegada y rollback

| Artefacto | Bytes | SHA-256 anterior | SHA-256 corregido |
|---|---:|---|---|
| compact cliente / entrada de `game_pak` | 440.823.808 | `075A661C865E2C9357AB9C9E084100C17C832EFAF6913669D672FCA78632411B` | `F8C7A0268A26D4EFAEC47A2A2B1B525447BF16C274506CD97BF571839B5E6D29` |
| compact runtime | 552.178.688 | `EDA870B4256C8DACF47823E60422DCC0604923913C76BE9CF285C5E3E79C3BDA` | `FB9273AE82F69FAFCF5FF94E2FF95D7BBCB29A3AD3F6502CAF05713251BAFDAF` |
| `game_pak` completo | 68.963.258.880 | `7BAAAA4AE6C42D7478A6A75F338E0748B18B2871EE6A16D9C12601F68538CF1E` | `32499AC6BF3ED1C1CE24B5A15A151355CB0C5A352A0C2BA727769AEEB3FC89D5` |

Respaldos exactos:

```text
E:\AAEmu-Research\backups\aa10-temper-cap-20260816\
  client-compact-before-temper-cap.sqlite3
  runtime-compact-before-temper-cap.sqlite3
```

Para rollback: cerrar el cliente, reinsertar el respaldo cliente con `PakEntryReplace` usando como
hash esperado `F8C7...6D29`, restaurar el respaldo runtime en
`.server_files\AAEmu.Game\Data\compact.sqlite3`, y reiniciar Game y las Zones. No se versionan las
SQLite, respaldos ni el paquete de ~69 GB; Git conserva el parche, hashes y procedimiento.

## Catalizadores, casteo y protocolo

| Item | Skill | Destino | Shining | Techo (`value4`) |
|---:|---:|---|---|---:|
| 45914 | 37723 | arma | no | 30 |
| 45915 | 37724 | armadura | no | 30 |
| 45916 | 39267 | arma | sí | 30 |
| 45917 | 39268 | armadura | sí | 30 |

Los cuatro skills declaran `casting_time=1500`, `start_anim_id=59`, `fire_anim_id=48` y
`fx_group_id=1257`. El casteo inicialmente esperaba el tiempo correcto en World pero era invisible:
r575 enviaba skill-object type 6 con `u64 supportItemId`, `bool autoUseAaPoint` e
`inputDirection`, mientras el servidor lo trataba como un string desconocido y colocaba el support
en type 7. Se corrigieron enum, parser y eco de `SCSkillStarted`; type 7 queda fail-closed.

El resultado nativo es `SCItemRefurbishmentResult`, opcode `0x00CC`, packet level 5:

1. `byte result` (`Break=0`, `Downgrade=1`, `Fail=2`, `Disable=3`, `Success=4`,
   `GreatSuccess=5`);
2. `ItemLink`;
3. `uint32` reservado;
4. `uint16 beforeScaleId`;
5. `uint16 afterScaleId`.

El detalle de equipo en offset `0x3C` es `ScaledA`, no un template de runa. La tarea nativa 127
(`Refurbishment`/`ScaleCap`) publica el detalle actualizado y libera la UI para el siguiente intento.

## Transacción de servidor

La reconstrucción implementa:

- carga fail-closed de 32 ratios, 3.047 forbids, caps por template y supports;
- validación de propietario, tipo arma/armadura, rango, tags, cap, forbid, catalizador y charm;
- costo mediante fórmula 59, costo del slot y atributo 259 `enchant_scale_cost_mul`;
- resolución normalizada de Success, Great Success, Fail y Downgrade;
- persistencia de `ScaledA` y multiplicador `1 + scale/1000` sobre daño y defensa;
- recálculo al equipar, task 127, detalle y resultado `0xCC`;
- consumo atómico y reembolso si un support desaparece entre validación y consumo;
- rechazo fail-closed de Break/Disable si datos futuros los vuelven alcanzables.

No se añadió instrumentación al chat. Game conserva una línea estructurada por intento con item,
catalizador, support, transición, resultado, costo y probabilidades normalizadas.

## Charms

Los supports AA10 usados en aceptación fueron `48858..48865` (arma/armadura): variantes ×1,5, ×2,
Anchoring y Resplendent Anchoring. Sus campos `*_mul` son porcentajes, no unidades sobre 10.000:

- `50` significa ×1,5;
- `100` significa ×2;
- `-100` elimina esa salida.

El servidor anterior aplicaba `multiplier * 0.0001`, por lo que la UI podía mostrar 50,6% y
Downgrade con `X`, mientras Game aún conservaba el 99% del riesgo de degradación. Se corrigió a
`multiplier * 0.01`, en concordancia con la localización retail y `GradeEnchant.GetCharmChance`.
El usuario confirmó que Resplendent Weapon Anchoring conserva el ×2 y ya no degrada en fallos.

## Validación

Validación automática final del 2026-08-16:

- `dotnet restore AAEmu.slnx`: correcto;
- `dotnet build AAEmu.slnx --configuration Release --no-restore`: 0 errores;
- `dotnet test AAEmu.UnitTests/AAEmu.UnitTests.csproj --configuration Release --no-build --no-restore`:
  1.290 correctas, 0 fallidas.

Las pruebas dedicadas cubren catálogo/cap/forbid, `none -> +1`, +12 todavía temperable, Great
Success con clamp en +30, multiplicador por mil, charms ×1,5/×2/Anchoring, opcode y cuerpo exacto,
task 127, feature bit y skill-object type 6 antes de los tiempos de casteo.

Validación manual aceptada por el usuario:

- pestaña Temper visible desde el Gear Upgrade retail;
- casteo y animación de 1.500 ms visibles;
- secuencia real desde +0 hasta +19, con DPS, tooltip y resultado actualizados;
- superación del antiguo techo +12;
- probabilidades y degradación normales desde +18;
- Resplendent Anchoring ×2 sin degradación.

Evidencia durable:

| Captura | SHA-256 | Propósito |
|---|---|---|
| `manual-evidence-20260816-plus12-cap.png` | `88F6E8058CE12E148F0ED661CDFC0EDD7C4112BABAE2989A9AE688800FA964BC` | reproduce el bloqueo previo en +12 |
| `manual-evidence-20260816-plus19-and-charm-ui.png` | `4B5C16BD578D9A7324315B6081D5A91A839B2F042590E163D37B4726499B227C` | +19, rates y slot de charm activos |
| `manual-evidence-20260816-anchoring-pre-server-fix.png` | `70C56E46AFFF198546BF0073CD666E02D1C3B31A3BEE546B717D781A32CC364B` | divergencia UI/Game que llevó al arreglo de `-100` |

## Fronteras deliberadamente pendientes

- Replace Stat: `itemEvolvingReRoll` (bit 161), vista presente, backend pendiente.
- Smelting: `itemSmelting` (bit 178), vista presente, backend pendiente.
- La página `gem` está hard-disabled en el router del ALB; no forma parte de Temper ni de la
  instalación de Lunagem ya reconstruida.
