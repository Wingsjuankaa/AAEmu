# Checkpoint AA10 Housing H3 — bindings nativos y Stone Rose Manor

## Frontera y baseline

- Cliente: ArcheAge Returns `10.0.2.13-r575`.
- Rama: `rama_10`.
- Baseline de implementación: `552488e78c1d7fc18f62828ea30f481f325346e3`.
- Referencia upstream exacta: `upstream/client_version/zone-10.0.2_r575` en
  `3cc280b14d7da0d874121d14ebbf409f5e032d1c`.
- Divergencia al abrir H3: `0 behind / 45 ahead`.
- AA8 y `housing_bindings.json`: no usados como fuente de valores.

Los hashes completos de full, compact retail, compact runtime, `x2game.dll` y
`game_pak` se encuentran en
`generated/aa10-housing-h3-manifest.json`. El generador abre las tres bases y el
pak en solo lectura.

## Consultas reproducibles

Las relaciones nativas se comparan, con el mismo orden, en full, compact retail
y compact runtime:

```sql
SELECT housing_id, attach_point_id, doodad_id, force_db_save
FROM housing_binding_doodads
ORDER BY housing_id, attach_point_id, doodad_id;
```

El modelo principal de cada plantilla se compara con:

```sql
SELECT id, main_model_id
FROM housings
ORDER BY id;
```

Los elementos del estado completado de cada `PrefabModel` se obtienen sin el
antiguo `LIMIT 1`:

```sql
SELECT file_path
FROM prefab_elements
WHERE prefab_model_id = @id
  AND state_id = (
      SELECT MIN(state_id)
      FROM prefab_elements
      WHERE prefab_model_id = @id AND state_id > 0
  )
ORDER BY file_path;
```

Para Stone Rose Manor:

```sql
SELECT housing_id, attach_point_id, doodad_id, force_db_save
FROM housing_binding_doodads
WHERE housing_id = 313
ORDER BY attach_point_id;
```

El resultado AA10 es exactamente:

| attach | doodad | helper | función del componente |
|---:|---:|---|---|
| 1 | 4925 | `$driver` | chimenea |
| 36 | 4561 | `$heal_point0` | puerta |
| 37 | 4565 | `$heal_point1` | ventana izquierda |
| 38 | 4565 | `$heal_point2` | ventana derecha |
| 57 | 2392 | `$name_plate01` | placa/administración |

Los cinco tienen `force_db_save=false`.

## Evidencia extraída

La extracción focal se conserva fuera de Git en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\housing-h3-frontier`.

| archivo | SHA-256 |
|---|---|
| `prefabs/housing_big.xml` | `6AA6192DBD0BB1B07AFBB52327C8ACD6687CC5335F31EDF9A8A24B0286BF3BBF` |
| `housing_m_floor01.cgf` | `26CD0BC8D772AE1F118EFD36BF73AA931F80625B6967566CCB544AE80FDD1C9B` |
| `housing_m_roof01_1f.cgf` | `7676B4B304B1B85B9FB2BBE8AA691C03280550D72E053DDD9A5007A43519421F` |
| `housing_m_wall01_1f.cgf` | `8006E81CE4F49469746B3425083069E0B02ACCF27136D05150E729D76AC0F6CD` |
| `housing_m_wall01_in_1f.cgf` | `7630032231B55964F196048A8C86FB00205B0CECED94F03975D46D0FA6DABF7C` |

El prefab completado de modelo 1139 está compuesto por suelo, techo y muro. La
implementación anterior elegía únicamente el primer `prefab_element`; por eso no
podía encontrar los helpers del muro y apilaba los doodads en el origen.

## Catálogo generado

Comando reproducible desde la raíz del repositorio:

```powershell
dotnet run --project reconstruccion_cliente_10\tools\HousingInteractionCatalogBuilder\HousingInteractionCatalogBuilder.csproj -c Release --no-build -- `
  E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3 `
  E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game\db\compact.sqlite3 `
  E:\AAEmu\rama_10\server\AAEmu\.server_files\AAEmu.Game\Data\compact.sqlite3 `
  E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\Bin64\x2game.dll `
  E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575\game_pak `
  AAEmu.Game\Data\model_attach_points_aa10_h3.json `
  AAEmu.Game\Data\housing_interactions_aa10_h3.json `
  reconstruccion_cliente_10\housing_h3\generated\aa10-housing-h3-manifest.json
```

Métricas H3:

- 837 plantillas de housing.
- 4.646 relaciones en 631 plantillas.
- 365 doodads diferentes y 35 attach points.
- 328 conjuntos de helpers reconstruidos.
- 5 bindings ejecutables en H3: los cinco de Stone Rose Manor.
- 4.624 posiciones demostradas pendientes de promoción H4/H5.
- 17 bloqueos forenses: 6 doodads ausentes, 2 modelos ausentes, 5 helpers
  ausentes y 4 transformaciones no uniformes/inválidas.

Dos ejecuciones independientes produjeron exactamente:

- `model_attach_points_aa10_h3.json`:
  `3A252BCEFC00F75F4C626863BEBB4BCEBF7E771600E5B56DCFC07C53B2FCC247`.
- `housing_interactions_aa10_h3.json`:
  `4F522DD30EACFD7B9FFDC3E9E8806E49EDFEF572C5925F21FF945A21E2A9747E`.

## Contrato runtime H3

- La identidad estructural es `(houseId, attachPointId, doodadId)`.
- No existe fallback implícito a `(0,0,0)`.
- El servidor no abre ni escanea `game_pak` al arrancar.
- Padre y bindings se retransmiten a Zone en orden padre→hijos.
- Los bindings estructurales se retiran hijos→padre.
- Sólo `force_db_save=true` puede conservar fase en base de datos; los demás se
  materializan en runtime desde su fase inicial AA10.
- Las filas persistidas por versiones antiguas se conservan para rollback, pero
  no se publican como decoración ni como binding si su definición no fue
  promovida.
- Todo lo no promovido en H3 falla cerrado con un motivo explícito.

## Gate retail H3

Sobre la casa 16, plantilla 313 (`Stone Rose Manor`):

1. La placa muestra F y abre el detalle correcto.
2. Puerta y ambas ventanas abren y cierran y mantienen fase/modelo sincronizados.
3. La chimenea sólo muestra las acciones presentes en AA10.
4. Un relog y una reconexión de Zone no eliminan ni duplican componentes.
5. Ningún componente aparece en el origen o fuera de su helper.

H4 no puede comenzar hasta que este gate sea aceptado.
