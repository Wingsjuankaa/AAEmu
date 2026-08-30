# CHECKPOINT_NATIVE_ERENOR_CATALOG_V1

Estado: reconstrucción v1 implementada, empaquetada y desplegada; fabricación
y progresión completa de arco aceptadas dinámicamente, matriz restante pendiente.

## Frontera

- Build: ArcheAge Returns `10.0.2.13 r575` x64.
- Rama/HEAD: `rama_10` / `2ecce32fd709b59c534c19d5dde2de02694a1186`.
- Objetivo: Folio, enciclopedia, síntesis y despertar Erenor T1–T4.
- No objetivo: inventar la ruta T3 → T4 de accesorios ausente en r575.

## Diagnóstico nativo

- Las 42 recetas base ya existían: 42 crafts, 42 productos, 210 materiales,
  pack `206`, doodad `9351` y política Wave 5 ejecutable.
- `item_recipes` representa objetos de receta/diseño, no productos terminados;
  sus 0 filas Erenor son nativas y se preservaron.
- El Folio filtraba 39 categorías D y tres categorías C de accesorios con
  `use_only_doodad='t'`.
- Las guías de equipo `619/873/922/994` tenían `0/0/1/1` piezas.
- Los mappings `23/275/311` aportan cadenas exactas `42/42/39`; el grupo 311
  no contiene accesorios Brilliant.
- Las categorías activas tenían tope 7 aunque los mappings exigen grados
  `10/11/12`.

## Transformación

- 42 categorías Folio: `use_only_doodad='f'`.
- Guías T1/T2/T3/T4: `42/42/42/39` piezas.
- Shield T3 obsoleto `48595` retirado; shield efectivo `50398` agregado.
- Seis relaciones de guía agregadas: `48836`, `48853`, `54329`, `52913`,
  `53793`, `53794`.
- 78 topes de síntesis corregidos según el tier nativo.
- Los scrolls normales ahora aplican el piso/rango `value2/value3/value4` al
  temper tras éxito; Holy/Blessed/Refined lo conservan.
- Cero recetas, `item_recipes`, `craft_line_components` o mappings inventados.

## Empaquetado y rollback

- `game_pak`: `2F751B...ABD3` → `8CD6A1...EFF4`, tamaño preservado en
  `68.963.258.880` bytes.
- Compact empaquetado final: `FFEE421E...6E5`.
- Compact suelto final: `F61B6B6E...65B`.
- Compact runtime final: `85024F04...C65`.
- Backup y manifiesto de rollback:
  `E:\AAEmu\rama_10\backups\client-patches\aa10-erenor-catalog-20260830-214032Z`.
- Dos entradas binarias ajenas al parche conservaron sus hashes: icono de
  shotgun y modelo buffalo.

## Gates ejecutados

- Builder en estado final: dry-run idempotente, 0 cambios pendientes.
- SQLite runtime: `PRAGMA quick_check = ok`.
- Guías: `42/42/42/39`; seis progresiones presentes; shield T3 correcto.
- Pruebas Python: 16/16 pass.
- Pruebas focales C# de despertar: 4/4 pass.
- Suite C#: 1.681/1.682 pass; el único fallo fue el `MailTests.MoneyTest`
  preexistente por `UnableToFindRecipient`; ejecutado aisladamente pasa 2/2.
- Build del servicio Game: 0 errores.
- Game recreado y saludable, restart 0; 12.402 crafts cargados, 9.949
  habilitados y 7.320 promovidos por Wave 5.
- Login y DB permanecieron saludables y no fueron recreados.
- El usuario fabricó un `43044 Erenor Bow` desde el workbench reconstruido.
- La progresión real terminó en un `53095 Refined Erenor Bow`, Eternal `12`;
  la Web API confirmó el item equipado y sus datos de síntesis. Esto acepta de
  extremo a extremo para arco los grupos `23`, `275` y `311`.

## Gates retail pendientes

- Buscar `Erenor Cuirass` y una muestra de cada ranura distinta del arco en Folio.
- Confirmar y fabricar la matriz restante por ranura; el arco ya está aceptado.
- Abrir enciclopedia y confirmar T1/T2/T3/T4 e infusiones/scrolls.
- Repetir síntesis hasta grados 10, 11 y 12 en armadura, armas de una mano y capa.
- Comparar scroll normal contra Holy/Blessed/Refined con temper superior a 20.
- Confirmar que T3 → T4 de Necklace/Earring/Ring queda bloqueado, sin destino
  inventado, hasta disponer de evidencia nativa adicional.
