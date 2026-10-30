---
name: aa10-client-forensics
description: "Investiga de forma exhaustiva el cliente ArcheAge Returns 10.0.2.13 r575 y construye SQLite relacionales, grafos, cobertura, evidencia negativa, corpus nativo y visor estático desde game_decrypted.sqlite3, compact.sqlite3, x2game.dll Bin64, game_pak, DLL, Lua, XML, worlds, capturas y fuentes comparativas AA8. Usar para inventariar o relacionar items, NPCs, modelos, skills, buffs, quests, doodads, crafting, loot, spawns, protocolo, localización y assets de AA10. Esta skill es sólo forense: nunca implementa mecánicas, modifica el runtime AAEmu, toca .env/MySQL ni despliega servidores."
---

# AA10 Client Forensics

Construir una representación consultable, reproducible y con procedencia de
todo lo que conoce el cliente Returns `10.0.2.13`, revisión `r575`. Mantener la
implementación del servidor como consumidor posterior y separado.

Desde la decisión del usuario del 2026-09-06, el cliente principal es
`E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
Diagnosticar el comportamiento observado a partir de sus entradas efectivas.
Conservar `...\ArcheAge-Returns-10.0.2.13-r575` como referencia original
inmutable y `...-es_ES` como piloto histórico. Separar en la evidencia el
baseline nativo y los parches/traducciones del principal; sus hashes no son
intercambiables. Esta elección no habilita escrituras desde la skill forense.

## Contrato estricto

Existe un sandbox privado aceptado, Zone411 `aa10_sandbox_lab`, útil para que
el consumidor AAEmu pruebe hallazgos con cliente español y recarga C# en vivo.
Leer [sandbox-evidence.md](references/sandbox-evidence.md) al investigar una
captura o catálogo de ese entorno. Sus recursos custom y aceptaciones no son
fuente retail: esta skill conserva su modo read-only y deriva operaciones,
arreglos y Hot Reload a `aaemu10-native-reconstruction`.

- Trabajar sólo en extractores, decodificadores, manifests, SQLite forenses,
  corpus nativo, reportes y visor.
- No editar `AAEmu.Game`, `AAEmu.Login`, `AAEmu.WorldServer`, SQL de runtime,
  `.env`, MySQL, Docker ni compacts desplegados.
- Si se pide implementación o despliegue, derivar esa parte a
  `aaemu10-native-reconstruction`.
- Conservar lo incierto como `unknown`, `blocked`, `opaque` o `conflict`; no
  rellenar huecos con AA8, upstream, nombres, wiki ni intuición.
- Registrar procedencia, hash, locator, consumer y estado por campo y arista.
- Tratar AAEmu Control Center sólo como consumidor/visor de salidas forenses.
  No iniciar Docker, ZoneHost, cliente ni acciones administrativas desde esta
  skill; derivar esa operación a `aaemu10-native-reconstruction`.

## Inicio obligatorio

1. Ejecutar `scripts/status.ps1`.
2. Leer siempre [current-forensic-state.md](references/current-forensic-state.md)
   y continuar desde su siguiente entregable.
3. Leer [environment.md](references/environment.md),
   [evidence-and-schema.md](references/evidence-and-schema.md) y
   [staged-workflow.md](references/staged-workflow.md).
4. Leer [lua-types-forensics.md](references/lua-types-forensics.md) cuando la
   frontera incluya Lua, widgets, eventos o bindings `X2*`.
5. Leer [aa8-crosswalk.md](references/aa8-crosswalk.md) antes de comparar o
   importar identidad, relaciones o estructuras de AA8.
6. Leer [upstream-lineage.md](references/upstream-lineage.md) cuando se compare
   evidencia con código del fork o del padre comunitario.
7. Leer [item-smelting-frontier.md](references/item-smelting-frontier.md) cuando
   la frontera sea Smelting o el skill-object tipo 20.
8. Leer [migration-scaling-frontier.md](references/migration-scaling-frontier.md)
   cuando la frontera sea Bless Uthstin o Migration Scaling.
9. Revisar el checkpoint y manifest de la última etapa. No repetir inventarios
   ni extracciones si inputs, hashes y decodificadores no cambiaron.

## Autoridad

Aplicar este orden, preservando el rol de cada artefacto:

1. `game_decrypted.sqlite3` r575: autoridad estática completa;
2. `compact.sqlite3` retail: proyección cargable por el cliente/runtime;
3. loaders, RTTI, vtables, consumers, serializers y fórmulas del
   `x2game.dll` release Bin64 con hash confirmado;
4. `game_pak`: Lua, XML, worlds, modelos, texturas, FX, audio y localización;
5. restantes DLL/EXE y superficies de caché del mismo cliente;
6. capturas y comportamiento repetible del cliente exacto;
7. binario Zone/dedicate r575 con identidad demostrada, sólo para semántica de
   servidor y nunca como sustituto del cliente;
8. `AAEmu/AAEmu:client_version/zone-10.0.2_r575` como implementación
   comunitaria padre, no como evidencia nativa;
9. AA8 como crosswalk estructural y de continuidad, nunca autoridad AA10.

La coincidencia x64 entre AA8 y AA10 reduce el costo de comparar ABI, layouts,
punteros, RTTI y patrones de compilación. No prueba opcodes, anchos, esquemas,
IDs, fórmulas, timings, ownership ni comportamiento. Confirmar cada hecho en
AA10 y anclar funciones por `SHA-256 + arquitectura + RVA`, no por RVA sola.

## Flujo

1. Definir la entidad o frontera y su clausura esperada.
2. Congelar hashes de inputs y versión del decoder.
3. Consultar primero las SQLite y corpus ya indexados.
4. Extraer filas, layouts, loaders, consumers y relaciones sin descartar
   nulos, duplicados, tombstones ni diferencias full/compact.
5. Recorrer referencias hasta entidad, dependencia externa, tombstone o región
   opaca documentada.
6. Generar la etapa y reconstruir la consolidada; nunca editarla a mano.
7. Regenerar cobertura, opacos, CSV, dossiers y visor.
8. Construir dos veces y exigir hashes idénticos.
9. Actualizar manifest, checkpoint y estado durable.

## Regla de clausura

Seguir relaciones entrantes y salientes, no sólo el dominio inicial:

```text
item -> descriptor -> skill/effect -> buff/loot/craft/quest
     -> modelo/icono/localización/UI -> serializer/consumer

npc -> template/model -> equipo/skills/buffs -> AI/faction/spawn
    -> quests/loot/doodads -> worlds/assets
```

## Cobertura y cierre

Medir por separado identidad, schema, propiedades, relaciones, consumer,
serialización, assets/localización, lifecycle, evidencia negativa y diferencias
`game_decrypted`/`compact`. `100%` significa clasificado, no necesariamente
comprendido. Un opaco bien inventariado sigue siendo blocker.

No cerrar una etapa sin:

- `PRAGMA quick_check=ok` e `integrity_check=ok`;
- cero descartes silenciosos y huérfanos explicados;
- dos builds deterministas;
- inputs, hashes y versiones congelados;
- manifest, checkpoint, visor y
  [current-forensic-state.md](references/current-forensic-state.md) actualizados.

## Salidas

Mantener código y checkpoints bajo
`E:\AAEmu\rama_10\server\AAEmu\reconstruccion_cliente_10` cuando se cree el
pipeline. Escribir artefactos grandes fuera de Git en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics`.

Producir SQLite por etapa, `aa10-client-knowledge.sqlite`, manifests, dossiers,
`opaque-regions.json`, CSV de brechas, corpus nativo y visor HTML. Validar una
base consolidada con:

```powershell
python scripts/validate_forensics_db.py <ruta.sqlite>
```

No borrar artefactos históricos: marcarlos `superseded` y conservar linaje.

Si se preparan mapas o iconos para Control Center, escribir únicamente assets
derivados y manifests bajo su caché de `%LOCALAPPDATA%`. Mantener `game_pak`,
SQLite retail y compact inmutables, congelar sus hashes y documentar cada ruta
interna extraída.
