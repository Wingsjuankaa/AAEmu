# AA10 r575 — Migration Scaling / Bless Uthstin

## Resultado

La sustitución aleatoria de estadísticas de personaje quedó reconstruida para
ArcheAge Returns `10.0.2.13 r575`. El servidor carga el catálogo y los límites
desde la SQLite exacta, publica las páginas en `CharacterState`/`UnitState`,
consume el talismán seleccionado, decide el resultado aleatorio y sólo acepta
una confirmación que coincida campo por campo con el preview pendiente.

El feature `bless_uthstin` (bit 176) está habilitado. Reset de estadísticas,
extensión del máximo y administración de páginas están fuera de este primer
cierre: sus seis contratos wire están registrados, pero esas operaciones
secundarias responden fracaso explícito y nunca mutan estado.

## Autoridad y herramientas

- SQLite completa: `E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3`
  (`SHA-256 87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`).
- Lua retail extraído y guía visual:
  `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\migration-scaling-frontier`.
- Zone r575 analizado:
  `E:\AAEmu\rama_10\zones\retail-zone-server-r575\Bin64\x2game-dev_dedicate.dll`
  (`SHA-256 8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A`).
- Ghidra reutilizado, sin instalar otra copia:
  `E:\AAEmu-Research\tools\ghidra\ghidra_12.1.2_PUBLIC`, con
  `E:\AAEmu-Research\tools\jdk\jdk-21.0.11+10`.
- Proyecto Ghidra:
  `E:\AAEmu\rama_10\forensics\ghidra\ghidra-projects-aa10-server\AA10ZoneServer.gpr`.
- `tools\lua-types.rc` sólo se usó como índice estructural. Lua, SQLite y el
  binario exacto promovieron los hechos al contrato r575.

## Datos exactos

`item_bless_uthstins` contiene 45 filas, todas con `items.impl_id=35`:

- item `42822`: función normal, `+1/-1`, pesos iguales para los cinco stats;
- item `42325`: función especial, `+3/-3`, pesos iguales para los cinco stats.

La build r575 no vende esos dos items mediante General Merchant. Sus rutas
retail están ligadas a contenido de battlefield. Para una aceptación local se
deben entregar por el comando GM normal, sin inventar una fila de merchant.

Configuración `kind_id=35` confirmada:

| Config | Valor |
|---|---:|
| `bless_uthstin_base_stats` | 200 |
| `bless_uthstin_max_stats_limit` | 300 |
| `bless_uthstin_max_stats_extend_per_point` | 20 |
| `bless_uthstin_apply_limit_count` | 1 |
| item de reset/extensión | 47084 |
| item de expansión de página | 39559 |

La cantidad requerida después del primer uso sigue la fórmula 44:
`bless_uthstin_apply_count ^ 2 + 1` (1, 2, 5, 10...).

## Contrato de estado y wire

Cada página ocupa 28 bytes nativos:

```text
STR i32 | DEX i32 | STA i32 | INT i32 | SPI i32
normalApplyCount i32 | specialApplyCount i32
```

Hay hasta tres páginas. El índice de página y los stats viajan base cero. Los
opcodes usados por el flujo principal son:

```text
C2G 0x1BF: itemInstanceId i64, pageIndex i32
G2C 0x2EC: bc, result, itemTemplateId, incKind, decKind, incPoint, decPoint
C2G 0x1C0: apply, itemTemplateId, incKind, decKind, incPoint, decPoint, pageIndex
G2C 0x2ED: bc, result, cinco stats i32, pageIndex, normalCount, specialCount, login
```

El `type` de preview/confirmación es el template del item, no la función
normal/especial. El servidor conserva un único preview pendiente y compara los
siete campos del C2G antes de persistir. Cancelar consume el item, igual que el
flujo nativo: sólo descarta el preview.

## Persistencia

La migración `SQL/updates/2026-08-19_aaemu_game_character_bless_uthstin.sql`
crea:

- `character_bless_uthstin`: página activa, cantidad de páginas, extensión y
  fecha de reset;
- `character_bless_uthstin_pages`: cinco deltas firmados y los dos contadores.

Al cambiar una estadística se persiste primero un snapshot completo de las
páginas y luego se publica `0x2ED`. Al relog, los descriptores iniciales y los
paquetes `0x2ED` con `login=true` llevan los registros guardados. El cambio de
día también se evalúa antes de cada nuevo consumo, por lo que no exige relog.
Como inferencia `server-required`, los contadores
normal y especial se reinician al día UTC siguiente porque ambos aparecen bajo
`Daily Usage Count` en el Lua exacto. La hora/boundary comercial de ese reset no
quedó decompilada; validar el cambio de día en una aceptación posterior.

## Validación ejecutada

```text
dotnet restore AAEmu.slnx: OK
dotnet build AAEmu.slnx -c Release --no-restore: OK, 0 errores
dotnet test AAEmu.UnitTests/AAEmu.UnitTests.csproj -c Release --no-build --no-restore:
1362/1362, 0 omitidas
```

Las pruebas nuevas cubren límites de stats, intercambio en el máximo, exclusión
de aumento/decremento sobre el mismo stat, fórmula de consumo y cuerpos exactos
de `0x2EC`, `0x2ED`, Copy, Abox e Init.

## Aceptación ejecutada en cliente — 2026-08-19

La aceptación dinámica se completó con `Wingsjuanka` (owner `1`) en la única
Zone autorizada, `351 / o_hirama_the_west_2`:

- Game desplegado desde la imagen
  `sha256:f0da9b9bfcac950032d994e3194ac91c1e7d77b3eb07d4ec5aabba3120ad6eb0`;
- ZoneHost r575 PID `5820`, iniciado como
  `AAEmu.ZoneHost.exe +zone o_hirama_the_west_2`;
- ejecutable ZoneHost SHA-256
  `86C935A4C91C028DCB6AC99F6E2C710E4CEA692C6C1E8E398BC310257AEC457F`;
- feature `bless_uthstin=true` y migración SQL aplicada antes del login;
- entrega GM mínima: una unidad de `42822` y dos unidades de `42325`.

La aceptación inicial demostró la ventana mediante
`Escape -> Characters -> Stat Migration` y el uso de talismanes compatibles.
Esa evidencia no demostraba el acceso histórico dentro de `C`: el cliente r575
conservaba la ventana moderna y dos fuentes antiguas de Character Info, pero el
`character_info.alb` activo ya no creaba el botón.

## Corrección de acceso en Character Info — 2026-08-19

Se restauró el acceso dentro de `C` sin duplicar la mecánica ni cargar el panel
legacy huérfano. El parche añade al `character_info.alb` activo un botón de 20 ×
20 en el anclaje nativo de la cuarta estadística base y llama
`ADDON:ToggleContent(UIC_BLESS_UTHSTIN)`. Por tanto abre la misma ventana AA10
moderna ya registrada por `x2ui/bless_uthstin`, con sus permisos, eventos y
contratos r575 actuales.

Artefactos reproducibles:

- constructor: `Scripts/PatchAa10CharacterInfoStatMigration.py`;
- fuente retail validada: `D33E3B0843585D03A12343EDCABB12DACF5DF8F0123D81AA84D5197C70B4CAEA`;
- ALB retail: `598B7C84E5E383FAF447501B1873D9BEF419DA8638E1BBDB647C67AEAFB370E5`;
- ALB parcheado: `5D795CE92E8D6B92A73B1338E752108930EBA3D07FCDD7A0B7E0ACD113385E96`;
- tamaño preservado: `54.793` bytes;
- `game_pak` final: `A696E303162AD2054918F5B9AE2ED71CFCD71A3C53C7EE6ACE677D38300407C9`.

El bytecode recompilado se validó con Lua 5.1 después de normalizar el marcador
de cabecera ArcheAge `0x08`; la entrada se reextrajo del paquete y coincidió
exactamente con el artefacto parcheado. Falta únicamente la aceptación visual
en cliente: abrir `C`, comprobar el nuevo botón junto a las estadísticas y
confirmar que muestra Stat Migration.

El General Merchant no es una fuente válida para los talismanes en los datos
exactos r575, por lo que la entrega GM sólo corresponde al fixture de prueba.

Resultados observados:

1. `42822` produjo el preview `Stamina +1 / Spirit -1`; al confirmar consumió
   una unidad y dejó el uso normal en `1/1`.
2. El primer `42325` produjo `Agility +3 / Strength -3`. Se canceló el preview,
   se aceptó la advertencia de no reembolso y el item quedó consumido sin
   modificar stats ni el contador especial.
3. El segundo `42325` produjo `Strength +3 / Agility -3`; al confirmar quedó
   aplicado y el contador especial pasó a `1`.
4. El panel final mostró `4/200`: Strength `161 (158+3)`, Agility
   `155 (158-3)`, Stamina `159 (158+1)`, Intelligence `158 (158+0)` y Spirit
   `157 (158-1)`.
5. Se volvió a selección de personaje, se ingresó nuevamente a Zone 351 y el
   panel conservó exactamente los mismos deltas y contadores.

MySQL después del relog:

```text
character_bless_uthstin:
owner active_page page_count extended_max_stats extend_count reset_date
1     0           1          0                  0            2026-08-19

character_bless_uthstin_pages:
owner page STR DEX STA INT SPI normal special
1     0    3   -3  1   0   -1  1      1
```

El log de Game registró el flujo normal y ambos especiales con
`0x1BF -> 0x2EC -> 0x1C0 -> 0x2ED`. En el relog publicó `0x2ED` y `0x2EF` sin
excepción de Bless Uthstin. Las advertencias de TowerDef/Buff y el opcode
desconocido `0x080` observados alrededor del login son preexistentes y ajenos a
esta mecánica.

Evidencia visual reproducible:

- [disponibilidad en el menú](evidence/migration-scaling-2026-08-19/01-menu-availability.jpg);
- [panel inicial](evidence/migration-scaling-2026-08-19/02-initial-panel.jpg);
- [preview normal](evidence/migration-scaling-2026-08-19/03-normal-preview-stamina-plus1-spirit-minus1.jpg);
- [aplicación normal](evidence/migration-scaling-2026-08-19/04-normal-applied.jpg);
- [preview especial cancelado](evidence/migration-scaling-2026-08-19/05-special-cancel-preview-agility-plus3-strength-minus3.jpg);
- [advertencia de cancelación](evidence/migration-scaling-2026-08-19/06-cancel-warning.jpg);
- [preview especial confirmado](evidence/migration-scaling-2026-08-19/07-special-preview-strength-plus3-agility-minus3.jpg);
- [resultado final](evidence/migration-scaling-2026-08-19/08-final-applied.jpg);
- [selección de personaje](evidence/migration-scaling-2026-08-19/09-character-select-relog.jpg);
- [persistencia después del relog](evidence/migration-scaling-2026-08-19/10-persisted-after-relog.jpg).

La defensa contra confirmaciones alteradas o stale permanece cubierta en las
pruebas unitarias del handler: el cliente retail no ofrece una vía legítima para
forjar ese paquete. Reset, Copy/Activate, expansión de página y extensión del
máximo siguen fuera del cierre y responden fracaso explícito.
