# Autoridad nativa AA8 para combate

## Resultado de esta fase

Esta carpeta contiene el primer catálogo global de combate construido para las
14 especialidades jugables de ArcheAge 8.0 sin usar filas de gameplay de la
compact 3.0.

El catálogo incluye las 462 habilidades AA8 asociadas a `ability_id` 1–14 y
recorre sus relaciones recuperadas desde `game11`. El runtime generado aplica
una política conservadora:

- Battlerage y Swiftblade tienen todas sus clausuras nativas cerradas.
- Las otras 12 especialidades quedan habilitadas parcialmente: sólo se aísla
  cada habilidad cuya propia clausura alcanza una tabla aún no recuperada.
- Una habilidad en cuarentena conserva su metadato AA8 para inspección, pero no
  recibe relaciones ejecutables ni puede caer silenciosamente a datos 3.0.
- Los dominios ajenos a combate se conservan desde la compact portadora porque
  aún no forman parte de esta migración.

La compact nueva es un artefacto aislado. No se modificó `.env`, no se recreó
el contenedor `game` y no se reemplazó la compact estable.

## Fuentes de autoridad

| Fuente | SHA-256 | Uso |
|---|---|---|
| `D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite` | `4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57` | Metadatos y relaciones visibles del cliente 8.0 |
| `E:\AAEmu-Research\output\compact-8.0-extracted\game11` | `E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031` | Filas nativas recuperadas, strings internados y clausuras |
| `compact-8.0-runtime-phase4-battlerage-v1.sqlite3` | `84990525F520B22BEBB3EAE4A0941B16A5A78C0A900F697E12AF69017D7B7871` | Esquema y dominios fuera del alcance inicial (NPC, ítems y doodads); nunca fallback de combate del jugador |

La compact histórica 3.0 no es argumento de ninguno de los generadores. La
portadora conserva filas fuera del alcance de las 14 especialidades para que
el servidor pueda seguir arrancando durante la migración. Ninguna de ellas es
alcanzable desde el grafo de combate del jugador; retirarlas corresponderá a la
fase posterior de NPC, ítems y doodads.

## Artefactos

| Artefacto | SHA-256 / estado |
|---|---|
| `generated/native-combat-catalog-v1.json` | `F0D27E5173D72C4637E5E1FD4C1471DB872B1F704D360D3C3D91EF50A11475A9` |
| `generated/native-combat-coverage-v1.json` | Matriz de primitivas del backend |
| `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-combat-v1.sqlite3` | `1EA8B11EA0C5167CA6D13688B524FAAF967B7EA5CC1423CD4B288E57BD423E8E` |
| `generated/native-combat-runtime-v1.manifest.json` | Manifiesto de construcción y validación |

La compact pasó `PRAGMA quick_check` e `integrity_check`, ambos con resultado
`ok`. Dos construcciones independientes produjeron el mismo SHA-256.

## Cobertura por especialidad

| ID | Especialidad | Total | Habilitadas | Aisladas | Estado | Primitivas con semántica backend pendiente |
|---:|---|---:|---:|---:|---|---|
| 1 | Battlerage | 37 | 37 | 0 | Completa | — |
| 2 | Witchcraft | 27 | 17 | 10 | Parcial | `ManaBurnEffect`, `SpawnEffect` |
| 3 | Defense | 37 | 33 | 4 | Parcial | `BubbleEffect`, `HealEffect` |
| 4 | Auramancy | 24 | 19 | 5 | Parcial | `HealEffect`, `RestoreManaEffect` |
| 5 | Occultism | 46 | 39 | 7 | Parcial | `HealEffect`, `SpawnEffect` |
| 6 | Archery | 35 | 34 | 1 | Parcial | `BubbleEffect` |
| 7 | Sorcery | 40 | 36 | 4 | Parcial | `ResetAoeDiminishingEffect` |
| 8 | Shadowplay | 28 | 27 | 1 | Parcial | `BubbleEffect` |
| 9 | Songcraft | 30 | 27 | 3 | Parcial | `BubbleEffect`, `HealEffect`, `RestoreManaEffect` |
| 10 | Vitalism | 38 | 11 | 27 | Parcial | `BubbleEffect`, `ExtendChargeEffect`, `HealEffect`, `KillNpcWithoutCorpseEffect`, `RestoreManaEffect` |
| 11 | Malediction | 30 | 17 | 13 | Parcial | `ResetAoeDiminishingEffect` |
| 12 | Swiftblade | 46 | 46 | 0 | Completa | — |
| 13 | Gunslinger | 23 | 4 | 19 | Parcial | `BubbleEffect`, `KillNpcWithoutCorpseEffect`, `ManaBurnEffect`, `ResetAoeDiminishingEffect` |
| 14 | Spelldance | 21 | 8 | 13 | Parcial | `BubbleEffect`, `HealEffect`, `ResetAoeDiminishingEffect` |

En total hay 355 habilidades habilitadas y 107 aisladas. Cada cierre sigue las
habilidades internas solicitadas por `SpecialEffect` tipo 48 antes de decidir
el estado, por lo que una cadena incompleta se aísla completa sin afectar las
otras habilidades de su especialidad.

El recorrido de buffs y efectos se ejecuta hasta alcanzar un punto fijo. Esto
evita marcar una habilidad como cerrada cuando un `buff_trigger` agrega un
efecto que, a su vez, agrega otro buff todavía no recorrido.

La matriz `native-combat-coverage-v1.json` distingue ahora tres estados:

- `native_implemented`: modelo/loader disponible y sin bloqueo semántico
  conocido en esta fase;
- `native_semantics_pending`: datos y layout nativos recuperados, pero la
  implementación actual es parcial o vacía;
- `native_not_implemented`: no existe modelo/loader de backend.

Actualmente hay 10 primitivas implementadas, 7 con semántica pendiente y una
sin implementación (`ExtendChargeEffect`).

## Tablas concretas recuperadas desde game11

Los siguientes layouts se confirmaron directamente en `x2game.dll` mediante
los loaders de Ghidra guardados en
`E:\AAEmu-Research\output\ghidra-static`. Sus filas ya forman parte del
catálogo y conservan procedencia `game11_native`; no habilitan automáticamente
una skill si el backend aún no reproduce su semántica AA8.

| Tabla | Inicio game11 | Filas | Loader x2game |
|---|---:|---:|---|
| `bubble_effects` | `0xDEBADB` | 5811 | `FUN_399710a0` |
| `heal_effects` | `0xB45F23` | 916 | `FUN_3996c3c0` |
| `restore_mana_effects` | `0xB5EFE9` | 256 | `FUN_3996d140` |
| `spawn_effects` | `0xD5AC76` | 2447 | `FUN_3996e5a0` |
| `mana_burn_effects` | `0xD9F951` | 89 | `FUN_3996f3e0` |
| `kill_npc_without_corpse_effects` | `0xDD0ECA` | 1613 | `FUN_399708e0` |
| `reset_aoe_diminishing_effects` | `0xE52AB1` | 191 | `FUN_39973660` |
| `extend_charge_effects` | `0xE57331` | 23 | `FUN_39974f20` |

El bloqueo semántico se mantiene porque, por ejemplo, `BubbleEffect` y
`ResetAoeDiminishingEffect` son no-op, `ExtendChargeEffect` no existe en el
backend y los modelos de heal, mana, spawn y kill todavía omiten campos o
comportamientos AA8 confirmados.

### Caché nativa de strings de animación

La tabla `anims` usa el caché de strings del resultado SQLite de `game11`.
Los valores con marcador `0xffffffff` se internan en secuencia y los campos
posteriores pueden referenciarlos por ID. El rango de animaciones comienza en
`18722`, confirmado sin consultar 3.0 por dos autorreferencias inmediatas de
las primeras filas (`18724` y `18725`).

El extractor reconstruye ahora esa secuencia y rechaza el catálogo si queda
algún nombre, variante o referencia `<ref:N>` sin resolver. El loader del
servidor admite `NULL` solamente en variantes opcionales; una animación sin
nombre nativo se omite con un aviso en vez de provocar una excepción.

## Triple Slash como piloto transversal

El runtime valida la cadena AA8 del tercer golpe:

- skill `18131`;
- plot `2541`, con 19 eventos;
- evento AoE `20729`;
- forma `10110`;
- relación hostil `4`;
- máscara de unidades `111`;
- máximo nativo de 20 objetivos;
- transición por objetivo `23962 → 23026`.

Además se corrigió el ejecutor genérico de áreas:

- ahora aplica `plot_aoe_conditions`, que antes se cargaban pero se ignoraban;
- deja la relación neutral/hostil en manos del filtro nativo en vez de excluir
  neutrales antes de evaluar la relación solicitada;
- elimina duplicados antes de aplicar el límite;
- conserva al objetivo principal una sola vez y ordena de forma determinista;
- aplica el límite de objetivos después del filtrado y ordenamiento;
- evita seleccionar un índice aleatorio sobre una colección vacía.

Estas correcciones son genéricas y no introducen radios, FX o daños inventados
para Triple Slash.

## Reproducibilidad

Desde `D:\Proyectos\AAemu\rama_8`:

```powershell
python reconstruccion_skills_8\native_combat\extract_native_combat_catalog.py `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --client-game-stream E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --source-root D:\Proyectos\AAemu\rama_8 `
  --output reconstruccion_skills_8\native_combat\generated\native-combat-catalog-v1.json `
  --coverage reconstruccion_skills_8\native_combat\generated\native-combat-coverage-v1.json `
  --verify

python reconstruccion_skills_8\native_combat\build_native_combat_runtime.py `
  --runtime-carrier D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-phase4-battlerage-v1.sqlite3 `
  --catalog reconstruccion_skills_8\native_combat\generated\native-combat-catalog-v1.json `
  --schema reconstruccion_skills_8\native_combat\native_combat_schema.sql `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-combat-v1.sqlite3 `
  --manifest reconstruccion_skills_8\native_combat\generated\native-combat-runtime-v1.manifest.json `
  --verify

python reconstruccion_skills_8\native_combat\test_native_combat_artifacts.py `
  --catalog reconstruccion_skills_8\native_combat\generated\native-combat-catalog-v1.json `
  --runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-combat-v1.sqlite3 `
  -v
```

Las pruebas C# deben ejecutarse con el runtime 3.1 usado por el proyecto. El
host actual no lo tiene instalado; la validación reproducible usada fue:

```powershell
docker run --rm `
  -v 'D:\Proyectos\AAemu\rama_8:/src' `
  -w /src `
  mcr.microsoft.com/dotnet/sdk:3.1.409-focal `
  bash -lc 'dotnet restore AAEmu.Tests/AAEmu.Tests.csproj && dotnet test AAEmu.Tests/AAEmu.Tests.csproj --no-restore'
```

Resultado actual: 12/12 pruebas estructurales y 52/52 pruebas C# aprobadas.

## Activación segura pendiente

Antes de apuntar Docker a esta compact se requiere:

1. respaldo de MySQL y de la compact activa;
2. una imagen limpia de `game` con estos cambios;
3. iniciar una instancia aislada;
4. probar Triple Slash con 1, 2, 3, 5, 20 y más de 20 enemigos;
5. verificar que Sunder Earth no pierda zona, FX ni reducción de daño;
6. ejecutar login, barras, aprendizaje, cambio de especialidad, relog, loot y
   consumibles;
7. probar con un segundo cliente la visibilidad de animaciones e impactos;
8. observar memoria del cliente, servidor y MySQL.

No se debe habilitar una especialidad en cuarentena modificando el manifiesto a
mano. Primero se recupera la tabla nativa faltante desde `game11`, se confirma
su layout en `x2game.dll`, se vuelve a generar la clausura y recién entonces se
quita la cuarentena de forma automática.
