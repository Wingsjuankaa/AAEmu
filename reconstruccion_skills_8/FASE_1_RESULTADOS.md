# Fase 1 — catálogo y procedencia de Battlerage

## Estado

La primera tarea de la Fase 1 está implementada. El extractor trabaja en modo
solo lectura y genera de forma determinista los cinco entregables definidos en
el plan.

No se modificó la compact usada por Docker, MySQL, el runtime ni el personaje.
No es necesario reiniciar el servidor para regenerar estos informes.

## Ejecución

```powershell
python .\extract_battlerage_manifest.py `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --client-game-stream E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --runtime-compact D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-loot-hybrid.sqlite3 `
  --server-reference D:\Proyectos\AAemu\client_kakao\compact.sqlite3 `
  --source-root D:\Proyectos\AAemu\rama_8 `
  --output .\generated `
  --verify
```

El modo `--verify` exige los cinco archivos, valida ambos casos manuales y
vuelve a leer los JSON generados.

## Fuentes verificadas

| Fuente | SHA-256 |
|---|---|
| Vista SQLite cliente 8.0 | `4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57` |
| Compact runtime híbrida | `80D28843A4380FAF93C16117477DBDCA184106D6F3CD2B686195E316BA635550` |
| Compact servidor 3.0 de referencia | `9FB1838113820D4F5BAC93BB7E79A3E51613CF7B2828B28545B59F506B4F4397` |

El hash de `game11` queda registrado automáticamente en el manifiesto para no
depender de una ruta o copia sin identificar.

## Recuperación nativa desde `game11`

La SQLite de investigación solo contiene seis tablas, pero `game11` conserva
resultados de consultas serializados. El extractor ya reconstruye en memoria:

| Resultado 8.0 | Filas |
|---|---:|
| `skill_effects` | 46.088 |
| `passive_buffs` | 278 |
| `buff_effects` | 24.914 |
| `conversion_effects` | 68 |
| `damage_effects` | 10.291 |
| `physical_explosion_effects` | 130 |
| `special_effects` | 41.013 |
| `buffs` | 27.031 |
| `buff_tick_effects` | 2.962 |
| `buff_triggers` | 10.084 |
| `buff_unit_modifiers` | 159 |
| `tagged_buffs` | 49.526 |

Las estructuras se aceptan únicamente cuando un ancla conocida es única y el
resultado completo termina en `SQLITE_DONE`. El layout de `damage_effects` se
confirmó contra las llamadas de acceso por columna de
`x2game.dll/FUN_3996b1d0`. La consulta y los 230 tipos de columna de `buffs` se
confirmaron en `FUN_39a2ae70`; las relaciones se confirmaron en
`FUN_39a2a190`, `FUN_39a29860`, `FUN_39978e50` y `FUN_39a29620`.

Los valores `<ref:N>` de `effects.actual_type` se resolvieron construyendo un
mapa de referencias. Una referencia solo se acepta cuando todos los pares
compartidos `effect.id + actual_id` producen un único tipo histórico. El mapa,
su evidencia y cualquier conflicto quedan dentro del manifiesto.

## Resultado Battlerage

- 19 filas 8.0 con `ability_id = 1`.
- 27 filas en la referencia histórica.
- IDs compartidos: `23587`, `32040`, `32049`.
- 14 de las 19 filas 8.0 tienen relaciones de efectos nativas en `game11`.
- 50 relaciones nativas de efectos alcanzan esas filas Battlerage.
- 6 pasivas Battlerage se recuperaron directamente de `game11`.
- Los tipos alcanzados son `DamageEffect`, `BuffEffect`, `SpecialEffect`,
  `PhysicalExplosionEffect` y `ConversionEffect`; los tipos históricos de las
  filas no presentes en 8.0 quedan separados en el informe.
- AAEmu ya posee clase y registro de loader para los tipos alcanzados.

La lista de `skills` 8.0 contiene principalmente variantes internas o
ancestrales y solo `23587` aparece con `show = 1`. Esto demuestra que filtrar
`skills.ability_id` no basta por sí solo para reconstruir la pantalla completa
de aprendizaje. La procedencia de la selección de habilidades base debe
confirmarse en la Fase 2 mediante los datos auxiliares o el protocolo 8.0.

## Validación manual del extractor

### Cadena simple: `32040` — Whirlwind Slash

- Existe en cliente 8.0 y referencia histórica.
- Tiene una relación nativa: efecto `55076`.
- El tipo se resuelve como `SpecialEffect`.
- El efecto concreto nativo está presente.

### Cadena compleja: `23587` — Behind Enemy Lines

- Existe en cliente 8.0 y referencia histórica.
- Tiene ocho relaciones nativas 8.0:
  `33809`, `33811`, `34131`, `62489`, `67233`, `67234`, `67750`, `86728`.
- Sus tipos son un `DamageEffect`, cinco `BuffEffect`, un
  `PhysicalExplosionEffect` y un `SpecialEffect`.
- Todos los efectos concretos están recuperados del stream 8.0.
- El daño nativo demuestra diferencias reales frente a 3.0, por ejemplo
  `dps_multiplier = 1.1`, `level_va_start = 0`, `level_va_end = 0` y
  `weapon_slot_id = 15`.
- Los cinco buffs referenciados (`828`, `7543`, `26932`, `27631` y `27632`)
  están recuperados directamente desde `game11`.
- Los buffs nuevos `27631`, `26932` y `27632` no existen en la compact
  histórica, pero ahora cuentan con plantilla 8.0 completa y relaciones
  nativas. Sus nombres localizados son `Tripped`, `Slow` y `Tripped`.
- La validación exige que no quede ningún `buff_id` nativo sin plantilla 8.0.

Las consultas SQL independientes devolvieron exactamente los mismos IDs que el
manifiesto. Una segunda ejecución produjo hashes idénticos para todos los
entregables.

## Primer corte vertical seleccionado

Se selecciona `23587` — Behind Enemy Lines — como primer objetivo visible. Es
la única fila Battlerage mostrada por la vista 8.0 cuyo ID también existe en el
runtime histórico, y ahora dispone de relaciones y efectos concretos 8.0.

La dependencia de plantillas y relaciones de buff quedó cerrada. `23587` ya
tiene cadena nativa hasta `buffs`, y `32040` permanece como prueba técnica
pequeña para validar cualquier adaptación del loader antes de activar el corte
vertical completo.

## Siguiente paso

1. Entrar a la Fase 2 para confirmar qué estructura define las habilidades
   base visibles.
2. Estabilizar aprendizaje, puntos, cambio de rama, guardado y carga antes de
   activar efectos individuales.
3. Usar `23587` como primer corte vertical una vez que el núcleo de
   especializaciones supere las pruebas de relog y persistencia.

El procedimiento reutilizable para catalogar la siguiente especialización se
encuentra en `GUIA_REPETIR_FASE_1_ESPECIALIZACIONES.md`. La guía documenta cómo
recuperar nuevas tablas de `game11`, confirmar layouts en `x2game.dll`, resolver
referencias sin inferir y cerrar cada especialización con pruebas deterministas.

## Cierre de reconstrucción de buffs

- Resultado `buffs`: bytes `44.378.464..64.403.064` de `game11`, 27.031 filas.
- Los cuatro resultados relacionales tienen límites propios y terminan en
  `SQLITE_DONE`.
- La cobertura de `BuffEffect` cambió a
  `backend_present_native_source_confirmed`: las 22 relaciones nativas
  Battlerage encuentran tanto su `buff_effect` como su plantilla `buffs` 8.0.
- Para `23587`, `missing_client_8_buff_ids` es una lista vacía.
- Dos ejecuciones consecutivas generaron hashes idénticos para los cinco
  entregables.
- Esta etapa solo leyó `game11`, las compact y el código; no modificó Docker,
  MySQL ni el personaje.
