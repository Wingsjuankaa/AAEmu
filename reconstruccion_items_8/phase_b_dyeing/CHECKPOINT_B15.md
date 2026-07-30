# Checkpoint B15 — native AA8 dyeing

## Estado corregido

Este entregable queda preservado como experimento forense superseded. El
runtime v6 fue retirado y el servidor volvió a v5. No se realizará aceptación
de gameplay ni promoción a `Complete` dentro del trabajo de descifrado.

Los layouts, IDs, filas y relaciones recuperados siguen siendo evidencia
válida y deben migrarse a las SQLite por etapa y al grafo consolidado de
`aa8-client-forensics`. El builder/runtime no forma parte del producto final.

Fecha: 2026-07-27
Cliente autoridad: Kakao 8.0.3.12 r558734

## Resultado

La familia `dyeing` quedó cerrada hasta la compuerta de aceptación manual:

- 26 consumibles `impl_id=27` clasificados;
- `SkillObject` nativo tipo `27` confirmado en x86 y x64;
- campo `color` serializado como `uint32`, seguido por `inputDirection`;
- catálogo `dyeable_items(item_id,color)` recuperado con 292 filas;
- 267 objetivos físicos y 25 tombstones nativos conservados;
- cadena de skills, effects, gain-loot-pack effects y dos salidas de loot
  cerrada;
- mutación AAEmu implementada sobre `EquipItem.GemIds[2]`;
- consumo de un solo ticket y `ItemTaskType.Dyeing=102`;
- persistencia reutiliza el detalle de equipo AA8 en offset `+0x14`;
- tablas históricas `item_dyeings` y `dyeing_colors` eliminadas del
  candidato.

El color del catálogo es el color visual por defecto del template. No se
escribe como override al crear el item: `DyeColor=0` conserva el default del
cliente y dyeing sólo persiste un override explícito.

## Cadena nativa

```text
25 dye items -> skill 39137 -> effect 70986
  -> GainLootPackItemEffect 3802 -> pack 12508 -> item 45632

item 45632 -> skill 43874 -> effect 83102
  -> GainLootPackItemEffect 4360 -> pack 13114 -> item 48965

item 48965 -> skill 22727 -> effect 31866
  -> SpecialEffect 12678 -> special type 98 Dyeing

item 43161 -> skill 22727
```

Las relaciones pack→item son datos derivados del servidor: el cliente
identifica inequívocamente los packs 12508/13114, mientras que la base
visible compatible corrobora las salidas 45632/48965. No se atribuyen a la
compact cliente.

## Artefactos

```text
runtime candidato v6:
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-nuian-green-arc-v6-dyeing.sqlite3
SHA-256 46C3507966B5C75EC0F6D51ACE15FB4A5D7F03E7CF31D98B569FCBFC27AF4AA7

manifest B15:
reconstruccion_items_8/phase_b_dyeing/manifest-b15.json
SHA-256 2D74F0B9A1A04315FEAC320A14255E68D25FA9A428B82206701518BCED351139

SQLite forense consolidada:
E:\AAEmu-Research\output\aa8-item-forensics\aa8-item-forensics.sqlite
SHA-256 697D9D9BEA2D9A18BB04003170D06B984AFA947C7369D462F7BC24EB576C7595

manifest forense:
E:\AAEmu-Research\output\aa8-item-forensics\manifest.json
SHA-256 9D4A5E219A18CD940E100DD100327C4A73B6990AB415CA11F5763F0E0955706F
```

El manifest B15 está registrado dentro de `review_manifests` en la SQLite
consolidada como `native_family_runtime_candidate`. La auditoría funcional
compara contra el runtime de prueba v6 activo. Los 26 consumibles, el wrapper
45632 y el ticket 48965 están en `phase_a_candidate`: backend, protocolo y
clausura confirmados; persistencia y validación continúan pendientes de
aceptación manual.

## Validación automática

- builder B15 ejecutado dos veces con SQLite idéntica;
- `PRAGMA quick_check=ok`;
- `PRAGMA integrity_check=ok`;
- cero dependencias huérfanas de skill/effect/gain/loot;
- 25/25 tombstones exactos;
- 27/27 pruebas Python;
- `compileall` correcto;
- 5/5 pruebas C# dirigidas de dyeing;
- 277/277 pruebas C# completas en Docker SDK 3.1;
- dos `run-all --deep` con SQLite forense idéntica;
- build Docker `game` correcto.

## Estado de despliegue

El runtime de prueba v6 está activo y el servidor carga las 292 reglas sin
errores. B15 permanece `deployable=false` y no es `Complete` hasta completar:

1. abrir y usar un Dye Ticket sobre un objetivo físico del catálogo;
2. confirmar consumo exacto de un ticket y cambio visual;
3. repetir rápidamente varias veces;
4. reloguear y confirmar persistencia;
5. confirmar la apariencia desde un segundo cliente cuando aplique.

No promover la familia a `Complete` antes de esa aceptación.

Rollback inmediato:

```text
runtime v5:
D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-nuian-green-arc-v5.sqlite3

backup MySQL:
E:\AAEmu-Research\output\aa8-item-forensics\backups\aaemu_b15_predeploy.sql
SHA-256 DE4F731E8EAD441E8E20757A86095BAE139A33709C79A9E360572A7BCCEEDC5E
```

La sección histórica de despliegue anterior queda anulada por “Estado
corregido”. No ejecutar pruebas manuales ni implementar dyeing durante el
descifrado del cliente.
