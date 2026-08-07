# Checkpoint — Point 0 repair stack v1

Fecha de construcción y despliegue: 2026-07-31.

Estado final: `validado satisfactoriamente` por el operador.

## Autoridad y alcance

- Cliente: ArcheAge Kakao 8.0.3.12 r558734.
- Base runtime: `compact-8.0-runtime-native-quest-repair-stack-v1.sqlite3`.
- SHA-256 base: `7C0100208A4846058F62377203DE48E237D332CFB77E926F90D96B5397C5DB25`.
- Runtime producido: `compact-8.0-runtime-point0-repair-stack-v1.sqlite3`.
- SHA-256 producido: `444C9A2586468C049C4B68B480724D0D3222F9A1E8091951F520033AA39935DF`.
- Única tabla runtime mutada: `native_character_creation_action_slots`.
- Código servidor: selección de animación nativa por holdable y política de
  altura de spawn terrestre compatible con AA8.

## Evidencia de reproducción

`build_point0_repair_stack_v1_runtime.py` se ejecutó dos veces desde la misma
base hacia archivos diferentes. Ambos resultados tuvieron exactamente el mismo
SHA-256 `444C9A…935DF`.

Validaciones SQLite:

- `PRAGMA quick_check`: `ok`.
- `PRAGMA integrity_check`: `ok`.
- 20.832 filas de acción: 12 plantillas × 8 habilidades iniciales × 217 slots.
- 96 combinaciones completas.
- Cero acciones que referencien una skill ausente.
- Pruebas Python: 4/4.

## Validación de código

- Compilación local de `AAEmu.Game` y `AAEmu.Tests`: correcta.
- Pruebas específicas de animación y altura: 10/10.
- Suite C# completa: 305/305.
- Build Docker del servicio `game`: correcto.

## Despliegue

- Sólo se reconstruyó y recreó `game`; `login` y `db` no fueron reiniciados.
- Runtime montado de sólo lectura en `/app/Data/compact.sqlite3`.
- SHA-256 verificado dentro del contenedor: `444C9A…935DF`.
- `HeightMapsEnable=true` y `PreferClientHeightMap=true`.
- `main_world heightmap loaded` confirmado.
- Resultado global: `Loaded 54/55 heightmaps`.
- Puertos 2239 y 2250 accesibles.
- Servidor iniciado sin líneas `ERROR`, `FATAL` ni excepciones durante la
  verificación; tiempo de arranque observado: 2 minutos 25 segundos.

## Aceptación manual final

El operador validó el lote completo en juego:

- Melee Attack reproduce su animación y mantiene el daño.
- Los mobs terrestres observados apoyan correctamente sobre el terreno.
- Shoot Rifle funciona con animación; su cierre ampliado se registra en
  `CHECKPOINT_POINT0_RIFLE_STACK_V3.md`.
- El personaje nuevo `Wingsjuanka`, Nuian masculino Battlerage, recibió
  automáticamente las 14 acciones esperadas en sus posiciones AA8.
- Tras salida limpia y reconexión, la barra reapareció correctamente.
- MySQL conserva exactamente 217 ranuras en un blob de 329 bytes, con SHA-256
  `7E3BD7C0373BC0E189D58657D24F7CEB4F12D2C4A521363E7AA45D4C5278CA49`.
- `Dannia`, creada antes del arreglo, conservó su barra previa; el bootstrap
  nuevo no sobrescribe el estado persistido de personajes existentes.

El cierre acumulativo se realizó con el runtime activo
`compact-8.0-runtime-point0-rifle-stack-v1.sqlite3`, SHA-256
`503BF9639F2005130C9E63A66A443AEA09577C082D7CE8EDC8AB11DA9118B77A`,
y la imagen `game`
`sha256:8c8aeb894caedc06b4c050dda9c6adb8f170c45f4f2479a0c0f7b53012a142d3`.

El manifiesto de aceptación final está en
`generated/point0-repair-stack-v1-acceptance-manifest.json`.
