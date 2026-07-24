# Reconstrucción nativa AA8 de objetos y equipamiento

El estado completo al cierre del 24 de julio de 2026, incluida la activación
de Fase A, los catálogos B1–B6 y Temper B7, está en
[`CHECKPOINT_2026-07-24.md`](CHECKPOINT_2026-07-24.md).

Este directorio contiene la Fase A del catálogo de objetos de **ArcheAge
8.0.3.12 Kakao r558734**. Ninguna fila de gameplay de la compact 3.0 se
considera autoridad.

## Autoridad

1. `compact-client-8.0-decrypted.sqlite`
2. resultados nativos recuperados desde `game11`
3. layouts y loaders confirmados en `x2game.dll`
4. protocolo observado con el cliente local
5. `game_pak` para recursos visuales y localización

La compact 3.0 sólo sirve para detectar diferencias históricas.

## Construcción reproducible

```powershell
python .\reconstruccion_items_8\extract_native_equipment.py `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-combat-passives-v1.sqlite3 `
  --unit-modifiers .\reconstruccion_skills_8\native_combat_stats\generated\native-unit-modifiers-v1.json `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-v1.sqlite3 `
  --manifest .\reconstruccion_items_8\generated\native-equipment-v1.manifest.json
```

La segunda construcción de verificación produjo el mismo SHA-256:

```text
566236160A50A5B77CE9640EF40D492BF925A8132591717FDE61E6692F2A8C98
```

`PRAGMA quick_check` e `integrity_check` devuelven `ok`.

Las fórmulas nativas de `holdables` y `wearable_formulas` se reconstruyen
reproduciendo la caché de cadenas de `game11`, cuyo primer índice confirmado
para este bloque es `157353`. La construcción falla si una fórmula conserva
una referencia `<ref:...>` sin resolver; no se sustituyen fórmulas con valores
de la compact 3.0.

## Cobertura recuperada

- 21.419 objetos activos del cliente AA8.
- 1.879 armas, 4.446 armaduras y 399 accesorios.
- 850 mochilas y 718 partes corporales nativas.
- 32 holdables, 71 wearables, 16 ranuras y 47 grupos de ranuras.
- 13 grados, 495 conjuntos de equipamiento, 247 item sets y 938 bonos.
- 2.127 modificadores de unidad alcanzables.
- Cero referencias huérfanas dentro de la clausura habilitada.

Las filas nativas de tipos concretos cuyo `item_id` ya no existe en el
catálogo AA8 se excluyen de forma explícita y quedan contadas en el
manifiesto. El ID firmado anómalo se registra sin convertirlo a `uint`.

La excepción son los `item_body_parts`: AA8 carga este resultado de forma
independiente y 405 rostros, cuerpos y cabellos válidos no poseen una fila en
el resultado general `items`. `ItemManager` construye directamente sus
`BodyPartTemplate`; filtrarlos deja personajes invisibles. Se conservan las
718 filas de `game11` y la ausencia de fila general se registra como
información, no como referencia huérfana.

## Estado de despliegue

Desde el 23 de julio de 2026 la compact candidata está activa en una ventana
controlada de **staging** y conserva `deployable=false`: todavía no es una
promoción definitiva. El detalle reproducible, respaldo y procedimiento de
rollback están en
`generated/ACTIVACION_STAGING_EQUIPMENT_2026-07-23.md`.

Las definiciones de armas, armaduras, accesorios, mochilas, partes corporales
y objetos cuyo tipo nativo es `impl_id=0` están marcadas como
`phase_a_candidate`, no como `complete`, hasta superar las pruebas dentro del
cliente. Las otras 4.948 definiciones permanecen `catalog_only` y no pueden
crearse mediante un fallback genérico.

`impl_id=0` es la implementación genérica nativa de AA8 y no una definición
concreta faltante. Objetos como Coinpurses y contenedores de equipo no
identificado pertenecen deliberadamente a esa clase y ejecutan su conducta
mediante `items.use_skill_id`; se habilitan como candidatas sin inventar un
subtipo.

La auditoría de MySQL encontró 59 instancias persistidas. La activación retuvo
dos candidatas de Fase A y movió 57 instancias a `quarantined_items` dentro de
una transacción validada. Ninguna instancia fue reemplazada por un objeto
parecido.

## Migración segura

1. Detener `game` y obtener un respaldo completo de MySQL.
2. Instalar `SQL/updates/2026-07-23-aa8-item-quarantine.sql`.
3. Exportar `items` como TSV con cabecera y las 17 columnas originales.
4. Generar, sin ejecutar, la transacción revisable:

```powershell
python .\reconstruccion_items_8\build_quarantine_transaction.py `
  --runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-v1.sqlite3 `
  --inventory-tsv E:\AAEmu-Research\migration\items-before-aa8.tsv `
  --output-sql E:\AAEmu-Research\migration\quarantine-aa8.sql `
  --report E:\AAEmu-Research\migration\quarantine-aa8.json
```

El generador nunca se conecta a MySQL. La SQL generada falla si una instancia
revisada desapareció entre la exportación y la ejecución, copia todas sus
columnas a `quarantined_items` y sólo después elimina la original.

En una ventana de staging se puede añadir `--allow-phase-a-candidates`. Este
modo conserva exclusivamente las instancias con clausura concreta candidata
para poder validarlas dentro del cliente, pero no cambia su cobertura a
`complete`. Sin el argumento, el comportamiento sigue siendo estricto.

El compose de staging define
`AAEMU_ITEM8_STAGING_ALLOW_CANDIDATES=1` únicamente en `game`. Esto permite que
NPCs, loot y comandos construyan tipos concretos candidatos durante la
validación. `catalog_only` continúa bloqueado. La variable debe eliminarse al
promover la compact definitiva.

## Comandos de prueba

```text
/item8 search <texto> [all|weapon|armor|accessory|consumable] [nivel]
/item8 info <itemId>
/item8 coverage <itemId>
/item8 quarantine list [owner]
/equipment audit [self|target]
/equipment resync [self|target]
```

`/additem` rechaza IDs no nativos, grados inexistentes y definiciones
incompletas cuando está activo un catálogo AA8 con cobertura. Durante staging,
un GM puede crear una definición `phase_a_candidate`; la excepción queda
limitada a esa ejecución del comando, se anuncia en chat y no habilita loot ni
otros creadores del servidor.

## Fase B

Sockets, lunagems, temper, síntesis, awakening, evolución, reroll, apariencia
y salvaging permanecen fuera de esta entrega. Cada subsistema se habilitará
solamente después de reconstruir su clausura nativa y probar su protocolo.
