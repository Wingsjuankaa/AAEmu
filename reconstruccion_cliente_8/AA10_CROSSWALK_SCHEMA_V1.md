# Esquema del crosswalk relacional AA8 -> 10.x V1

## Autoridad y alcance

`aa8-aa10-crosswalk-v1.sqlite3` es una capa comparativa independiente. El
cliente Kakao 8.0.3.12 r558734 sigue siendo la unica autoridad sobre AA8. La
SQLite 10.x se usa exclusivamente para contrastar identidad, relaciones y
forma estructural; ninguna fila contiene autorizacion de promocion automatica
a Stage 20/30/50/90, la consolidada o el servidor.

Los campos de propiedades se conservan separados de los campos relacionales.
En particular, una coincidencia de ID no confirma balance, probabilidades,
cantidades, formulas, tiempos, IA, paquetes de red ni progreso de quests.

## Vocabulario cerrado

Cada tabla, fila o relacion comparada usa exactamente una de estas clases:

| Clase | Significado |
|---|---|
| `exact_id_exact_relation` | misma identidad y mismas relaciones comparables |
| `stable_id_changed_properties` | ID estable; difieren propiedades no relacionales |
| `renumbered_row_stable_relation` | cambia el ID de fila, pero una clave natural y sus relaciones conservan la entidad |
| `aa8_only` | evidencia presente en AA8 y ausente en la superficie 10.x comparable |
| `aa10_only` | fila o superficie observada solo en 10.x; nunca prueba contenido AA8 |
| `structural_candidate` | forma o relacion compatible sin identidad AA8 confirmada |
| `conflict` | incompatibilidad, ambiguedad o evidencia insuficiente que bloquea promocion |

`evidence_state`, `inference_kind`, `conflict_kind` y
`promotable_to_aa8` mantienen aparte confirmacion, inferencia, conflicto y
ausencia. En V1 `promotable_to_aa8` siempre es `0`.

## Tablas fisicas

| Tabla | Proposito |
|---|---|
| `metadata` | version del esquema, herramienta, autoridad y reglas globales |
| `source_artifacts` | rutas, SHA-256, tamanos, procedencia y checks de las dos fuentes |
| `schema_tables` | inventario determinista de tablas AA8 y 10.x |
| `schema_columns` | orden, tipo, nulabilidad, valor por defecto y PK de cada columna |
| `schema_indexes` | inventario de indices y columnas indexadas |
| `schema_foreign_keys` | relaciones FK declaradas fisicamente por cada fuente |
| `logical_table_crosswalk` | clasificacion por tabla, compatibilidad de columnas, conteos y bloqueos |
| `row_comparisons` | identidad, clave natural, huellas de propiedades/relaciones y clase por fila |
| `relation_comparisons` | comparacion independiente de cada vinculo y su destino |
| `coverage` | metricas cerradas de continuidad para dominios prioritarios |
| `negative_evidence` | ausencias, superficies opacas y relaciones bloqueadas |
| `conflicts` | conflictos accionables con evidencia y resolucion requerida |
| `validation_events` | barreras ejecutadas durante el build y su resultado |

Los BLOB no se incrustan en claves JSON: se representan deterministicamente
por longitud y SHA-256. Booleanos `t/f` se normalizan, y `NULL`/cero se tratan
como ausencia solo en columnas relacionales donde el contrato lo permite.

## Reglas de comparacion

1. Se congela cada fuente mediante ruta normalizada, bytes, SHA-256,
   `quick_check`, `integrity_check` y procedencia declarada.
2. Se inventarian tablas, columnas, claves primarias, indices y FKs antes de
   comparar filas.
3. Los IDs se prueban primero; una clave natural solo puede proponer una
   renumeracion cuando es no ambigua.
4. Las columnas relacionales se comparan aparte de las propiedades.
5. Las filas AA8 sin equivalente se conservan como `aa8_only`; las 10.x sin
   equivalente, como `aa10_only` o candidato estructural.
6. Una superficie opaca o bloqueada nunca se rellena con datos 10.x.
7. Todas las filas de evidencia AA8 deben quedar comparadas o explicitamente
   en cuarentena; la validacion exige cero descartes silenciosos.

## Bloqueos V1

- `tagged_items`: el cache legacy AA8 comparte exactamente el rango de
  `tagged_skills`. Los consumidores nativos distinguen `item_id, tag_id` de
  `skill_id, tag_id`; por ello sus 28.910 filas quedan en cuarentena como
  `blocked_cache_boundary`, con cero filas comparadas. Las 33.226 filas 10.x
  no sustituyen esa evidencia.
- `loot_quest_id`: el loader AA8 exige la columna, pero `loots` 10.x no ofrece
  una relacion equivalente verificable. Permanece bloqueada.
- `npc_spawner` y `npc_group`: la cobertura parcial solo permite candidatos
  por fila, no una importacion masiva.

## Construccion y validacion

Desde `reconstruccion_cliente_8`:

```powershell
python -B -m client_forensics build-aa10-crosswalk
python -B -m client_forensics validate-aa10-crosswalk
```

El builder escribe primero una base temporal, aplica orden estable, omite
timestamps, ejecuta `VACUUM` y publica atomicamente. El validador comprueba
`quick_check`, `integrity_check`, FKs internas, vocabulario, eventos fallidos,
contabilidad AA8, drops silenciosos y los dos bloqueos anteriores.

## Salidas

La base, manifiesto, resumen, CSV generales y CSV por dominio se escriben en:

```text
E:\AAEmu-Research\output\aa8-client-forensics
```

El manifiesto registra los hashes de todas las salidas. El informe
`aa8-aa10-crosswalk-v1-determinism.json` compara dos construcciones limpias en
directorios distintos. Las copias identicas de la SQLite 10.x no se cuentan
como evidencia independiente.
