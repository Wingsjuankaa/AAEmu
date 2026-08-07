# Checkpoint Sorcery V7: catálogo ancestral y protocolo AA8 exactos

Fecha: 2026-08-04

Cliente autoridad: ArcheAge Kakao `8.0.3.12 r558734`

## Resultado

V7 conserva sin cambios el cierre ejecutable de las doce activas y las seis
pasivas de V6 y agrega la progresión Heir completa, el grafo de sucesores y el
protocolo necesario para seleccionar variantes ancestrales. La SQLite 10.x no
es autoridad de progresión ni de protocolo: sólo confirmó de manera
independiente identidades recuperadas directamente de AA8.

La aceptación estática está cerrada. La aceptación visual/conductual continúa
pendiente porque animaciones, FX, físicas del cliente y limpieza visual final
no pueden certificarse con una prueba de servidor.

## Nueva evidencia directa en `game11`

`FUN_3993b660` carga `id, level, req_item_count, req_item_id, req_total_exp,
step` desde `heir_levels`. El resultado cacheado completo comienza en
`113965013`, termina en `113967072`, usa layout `i32,i32,i32,i32,i64,i32` y
contiene 71 niveles (`0..70`) y pasos `0..12`. El umbral final es
`178230921286`; la primera fila exige un objeto (`1 x 40491`).

`FUN_399d1530` carga 159 `heir_skill_details` entre `143882320..143887105`.
`FUN_399d1850` carga 78 `heir_skills WHERE enable='t'` entre
`143887111..143888125`. Las 308 filas exactas quedan preservadas en la tabla
de evidencia V7.

## Grafo ancestral de Sorcery

| Heir ID | Base | Paso | Sucesores AA8 `(skill,pos)` |
|---:|---:|---:|---|
| 19 | 10752 Flamebolt | 1 | `(36474,1)`, `(36475,8)` |
| 20 | 11967 Chain Lightning | 2 | `(36476,1)`, `(36477,5)` |
| 21 | 10664 Meteor Strike | 3 | `(36478,5)`, `(36479,8)` |
| 40 | 23593 Gods' Whip | 4 | `(39669,8)`, `(39674,5)` |
| 52 | 14774 Flame Barrier | 5 | `(41222,5)`, `(41223,6)` |
| 58 | 12796 Magic Circle | 6 | `(43068,3)`, `(43185,1)` |

Las doce filas declaran `skill_active_type_id=1` (`Active`).

## Protocolo recuperado de `x2game.dll`

- C2G activación `0x08F`: `i32 heir`, `i32 successor`, `u8 isChange`
  (`FUN_39101160/FUN_3997b4f0`).
- C2G reset `0x076`: `u32 kind`, `i8 ability`, `i32 successor`
  (`FUN_391015b0/FUN_39101860`).
- G2C lista Heir `0x02D`: `u32 count` (máximo 128), luego `i32 heir`,
  `i32 base`, `i32 successor`, `u32 skillLevel`, `i8 ability`, `i8 activeType`
  (`FUN_399a6650/FUN_399210e0`).
- G2C activado `0x18C`: `i32 heir`, `i32 successor`, `u8 isChange`.
- G2C reset `0x341`: `u32 kind`, `i32 successor`, `i8 ability`.
- G2C active types `0x236`: `u32 count` (máximo 200) y entradas
  `i32 heir`, `i32 skill`, `u8 activeType` (`FUN_39981860/FUN_399236b0`).
- G2C actualización active type `0x1F2`: una entrada con el mismo layout.

Esto corrige dos defectos legados: la actualización omitía el Heir ID y el
spawn enviaba siempre una lista vacía.

## Implementación

- `HeirGameData` carga y valida niveles, pasos, familias y sucesores AA8.
- `CharacterHeirSkills` valida base aprendida, paso y sucesor seleccionado.
- `CharacterSkillActiveTypes` restaura el registro nativo completo.
- `ChangeSkillActiveType` dejó de ser un no-op.
- `heir_level`, `heir_exp`, selecciones y active types se persisten mediante
  `SQL/updates/2026-08-04_aa8_heir_sorcery.sql`.
- Al salir una especialización se eliminan sus sucesores ancestrales.

## Artefactos y gates

- Runtime V7 SHA-256:
  `6680B69159285BC817732DAD24707BB1A4B2625C77718FEA9A02E72BD8E17159`.
- Manifiesto SHA-256:
  `0CACA13258617C1AA6DEB9C9DC71D2EBA81A0737C9CEA6902FFC1D9EAC5277B6`.
- Aceptación V7 SHA-256:
  `BD22B186E2483345CDD0217364046C5F01FB76FB5795239A96383F833C508CA7`.
- SQLite `quick_check=ok`, `integrity_check=ok`.
- 308/308 filas vuelven a decodificarse desde `game11` campo por campo.
- 5/5 pruebas C# específicas; 415/415 C# totales; 3/3 Python V7 y 25/25
  pruebas Python Sorcery encadenadas V2→V7.
- Docker monta el mismo SHA; `HeirGameData` completa Load/PostLoad y Game se
  registra en LoginServer.

## Frontera restante

Las doce activas base están cerradas estructuralmente, pero deben ejecutarse
según `SORCERY_LIVE_ACCEPTANCE_PROTOCOL_V1.md`. Las seis familias ancestrales
requieren además seleccionar ambas variantes, lanzar, cambiar, reloguear y
resetear. Hasta completar esa matriz no debe declararse Sorcery aceptada
completamente en vivo.
