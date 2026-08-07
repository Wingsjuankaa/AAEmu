# Checkpoint Archery tag closure V3

> Continuidad: este checkpoint es historico. V4 descubrio y corrigio la misma
> frontera en `buffs/tagged_buffs`; ver
> `CHECKPOINT_ARCHERY_PASSIVE_TAG_CLOSURE_V4.md`.

Fecha: 2026-08-07

## Resultado

La clausura ejecutable V2 era correcta para plots, efectos, buffs y requisitos,
pero incompleta para una relacion many-to-many consumida por cache. El runtime
historico tenia `tagged_skills` parciales y duplicados para las 35 entradas de
Archery. En particular, el tag 3750 del modificador nativo del buff 889 no
tenia consumidores, de modo que la pasiva podia aprenderse sin modificar las
skills alcanzadas.

V3 reemplaza deterministicamente todas las relaciones de esas 35 skills por
las filas exactas del conocimiento AA8:

- 356 filas `tagged_skills`;
- 356 pares naturales `(skill_id, tag_id)` distintos;
- 35/35 raices visibles, sucesoras, login-stage e internas cubiertas;
- cero pares duplicados;
- tag 3750 aplicado a 24 skills;
- contrato nativo `buff 889 -> tag 3750 -> skill attribute 10 -> +10%` con
  24 consumidores ejecutables.

No se importaron filas AA10. El crosswalk clasifica las 356 relaciones como
`exact_id_exact_relation`; se uso para reducir el vacio y confirmar identidad,
no como fuente de balance.

## Autoridad y discrepancia de localizacion

La localizacion inglesa montada por el cliente describe algunas pasivas con
semantica de una revision anterior. Las filas nativas Kakao AA8 de `game11`
y sus consumidores actuales son la autoridad runtime. Por ello V3 conserva:

- buff 486: modificador de unidad attribute 10/value 80;
- buff 7564: modificador de unidad attribute 82/value 90;
- buff 889: modificador de skill tag 3750/attribute 10/value 10%;
- buffs 480, 888 y 7565 sin propiedades sintetizadas desde el tooltip.

La prueba viva debe medir las estadisticas servidoras. No se usa el texto UK
para fabricar rango, critico, cooldown o balance que AA8 nativo no demuestre.

## Artefactos

- constructor: `build_archery_runtime_v1.py`;
- runtime:
  `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-archery-v3.sqlite3`;
- bytes: 141.074.432;
- SHA-256:
  `AF234CA0042CFD12393B2ED345B1207F2C1BD7254AFD62F7836831840A956C55`;
- manifiesto: `generated/archery-runtime-v3.manifest.json`, SHA-256
  `73DA82410A0057CC9A2B580DC6A6ADA3CEDC3670A9BD4317C22D9FADE61912E7`;
- contrato canonico `tagged_skills`, SHA-256
  `C21FD1BE7FADC54B2847A3470A1D13752160A64A01DFC44307500F163299B068`;
- filas AA8 materializadas en la capa: 4.995;
- filas runtime AA10: cero;
- `quick_check=ok`, `integrity_check=ok`.

Tres construcciones limpias en destinos separados produjeron exactamente el
mismo SHA-256 del runtime.

## Auditoria corregida

El walker dirigido no puede descubrir por si solo una relacion consultada en
sentido inverso por `SkillManager`: partir del buff/modificador no crea una
arista hacia todas las skills con el tag. El auditor ahora agrega un pase
owner-keyed obligatorio que valida cobertura, unicidad y consumidores de
modificadores por tag.

- auditor: `audit_archery_executable_semantics_v1.py`;
- regresiones: 8/8;
- 35/35 raices y seis pasivas;
- 356 relaciones y 35 raices cubiertas;
- cero duplicados, cero tags de modificador sin consumidores;
- cero blockers del grafo y cero blockers owner-keyed;
- JSON: `generated/archery-executable-semantics-audit-v1.json`, SHA-256
  `BDFA099A5947D95001ED590D3443B472D9BF625004CE1A8287EFCBF3C99A9326`;
- CSV: `generated/archery-executable-semantics-matrix-v1.csv`, SHA-256
  `07D9243A1362F067A9832345FFF5CCC93D8FF5CC409558FAA9146C93430572BD`.

La regresion de runtime permanece 14/14 y la suite completa del servidor pasa
565/565 contra V3.

## Despliegue controlado

- imagen Game:
  `sha256:0a647c2e16376e1ec1bfabe3c182afdb2d69280eb1fd973740242c4012064453`;
- contenedor Game:
  `73984e2582390dfc381f6bc326dda5d59f9b47ee19d4dba23c3da4ab0e9def7c`;
- mount:
  `compact-8.0-runtime-archery-v3.sqlite3 -> /app/Data/compact.sqlite3`;
- Login conservado:
  `72a1b87ae15badcd6fcdf1bdbd99819db84707a980d8fbf47c58bd12b01a8406`;
- MySQL conservado:
  `48ab25a4d483901da9ec9e05a5588eb81dbfb8eee94a56083550a2ddae14d89a`;
- rollback: `aaemu-game:rollback-pre-archery-executable-v2-20260807`;
- registro en Login una vez, puertos 2239/2250 abiertos, cero errores, cero
  fatal y `RestartCount=0`.

Baseline posterior:
`runtime-captures/native-skill-live-baseline-v4.json`, SHA-256
`B852113E9A397403CC0B8D3FD74C199DA20CA3713208F9E812CA912AE62617A6`.
Contiene un arranque y cero ejecuciones, snapshots pasivos o errores. El CSV
equivalente tiene SHA-256
`03710B80A4B03BD134280DD8AD5E5B92D8FFEFEE8DA0840D30C021D792A275C6`.

## Estado

Archery sigue `automatic_verified`. V3 elimina el hueco estatico de tags, pero
la promocion a `live_accepted` requiere A1-A5 y medir cada pasiva con
`[AA8ArcheryPassive]`. Sorcery requiere aun las pruebas vivas S1 y S2; este
checkpoint no convierte animaciones o pruebas automaticas en evidencia viva.
