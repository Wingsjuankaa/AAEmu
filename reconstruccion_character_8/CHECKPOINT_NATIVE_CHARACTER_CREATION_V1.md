# Checkpoint — Native Character Creation V1

Fecha: 2026-07-25
Cliente: Kakao 8.0.3.12, revisión r558734.

## Resultado

La implementación segura del bootstrap, la persistencia atómica y el protocolo
quedó preparada, pero la restauración visible sigue bloqueada. No se construyó
ni desplegó un runtime porque faltan cuatro datos que no aparecen en ninguna
fuente AA8 barrida. Las creaciones nuevas se rechazan completas si el catálogo
nativo no está listo; los personajes existentes no se reinterpretan.

## Evidencia nativa cerrada

- `characters`: 12 filas, seis razas seleccionables y ambos géneros.
- `login_stage_abilities`: 8 opciones: `1, 6, 7, 10, 11, 12, 13, 14`.
- Matriz completa: 12 plantillas × 8 habilidades = 96 combinaciones.
- Relación de equipo:
  `ability_id → login_stage_abilities.start_equip_pack_id →
  character_equip_packs`.
- `character_equip_packs`: 14; `equip_pack_cloths`: 2389;
  `equip_pack_weapons`: 664.
- `character_supplies`: 4 filas globales; se probaron objeto, cantidad y grado.
- `character_default_skills`: 24; `default_skills`: 146.
- Cierre referencial: 16 objetos y 8 habilidades iniciales; cero referencias
  ausentes en B14.
- `default_action_bar_actions` tiene exactamente cero filas. Se probó mediante
  el límite contiguo de resultados
  `default_skills → default_action_bar_actions → npc_nicknames`.
- Zonas y retornos lógicos:

  | Raza | Zona | Distrito/facción | Return point |
  |---|---:|---|---|
  | Nuian | 179 | 342/101 | 243 `system_nuian_start` |
  | Dwarf | 328 | 191/104 | 239 `dwarf_start` |
  | Elf | 129 | 186/103 | 245 `Gwe_start` |
  | Hariharan | 187 | 182/109 | 240 `rain_system` |
  | Warborn | 157 | 393/187 | 717 `start_warborn` |
  | Ferre | 184 | 184/113 | 241 `start_fp` |

## Barrido exhaustivo del cliente

- Se indexó el `game_pak` completo.
- Se extrajeron y buscaron los 7698 XML indexados, 619.822.805 bytes.
- Hash agregado determinista del árbol XML:
  `21DD148062AD3985A912880898692A721675C85CBC8E94C19EABABFD2DBDE26A`.
- Se verificaron separadamente 1591 `client/entities.xml` y 29
  `mission_mission0.xml`.
- Se extrajo además el mundo `login2` completo: 569 archivos y 29.651.684
  bytes, incluidos 24 DAT y tres CTC. Su hash de árbol es
  `B2BF5918994D5D25B8AF975BB046A6FBE0AC42F0F82A1F05EAD05EAD91EC1864`;
  ninguno contiene los marcadores nativos de retorno o bootstrap.
- Se barrieron los binarios jugables 32/64-bit `archeage`, `crygame`,
  `cryaction`, `cryentitysystem` y `x2game`. Solo ambas variantes de `x2game`
  contienen las cadenas de tablas/acciones ya decompiladas; los seis nombres
  lógicos de retorno no aparecen en ningún binario.
- Ninguno de los seis nombres nativos de retorno aparece en los 7698 XML.
- Solo existen tres marcadores de misión antiguos (`Spawn_Nuian`,
  `Spawn_elf`, `Spawn_andelph`). No cubren las seis entradas AA8 y el de Dwarf
  pertenece a otra zona; quedan excluidos como autoridad.
- Se decompilaron los 1112/1112 scripts ALB de `scriptsbin64`, sin fallos. La
  creación Lua delega a `EndCharacterCreate`/código nativo y no contiene
  XYZ/cuaternión.
- Se extrajeron y decompilaron también los 1112/1112 ALB de 32 bits. La
  comparación por ruta y por byte produjo cero archivos exclusivos y cero
  diferencias; el árbol fuente común tiene SHA-256
  `9122B64B4A16D0B33F85C33E5F60144ED0157E4193E718073F6EBF5D06493CF3`.
- Se hashó y buscó cada archivo desempaquetado fuera del `game_pak`: 363
  archivos y 984.864.203 bytes. Solo `x2game.dll` de 32/64 bits contiene
  consumidores propios del dominio; las coincidencias restantes pertenecen a
  CEF, CryEngine, render, navegación o librerías genéricas.
- Se catalogó todo el SQL ASCII embebido: 1016 sentencias en `x2game` de
  32 bits, 1015 en 64 bits y 1014 comunes. Las tres diferencias son
  sentencias internas/ruido de SQLite, no tablas jugables. Los loaders de
  creación relevantes son idénticos entre arquitecturas.
- Se hashó y buscó cada byte de los 12 streams descifrados `game*`,
  266.826.408 bytes. Los únicos ocho marcadores exactos aparecen en `game11`
  y son los nombres de retorno lógico ya cerrados; ningún otro stream aporta
  una relación inicial.
- El cierre global del `game_pak` extrajo 121.380 contenedores
  estructurados/textuales o DAT/CTC de mundo, 5.428.511.353 bytes, más 24
  formatos poco comunes revisables, 8.825.732 bytes. Las dos extracciones
  terminaron con cero fallos, ausencias, diferencias de tamaño o MD5.
- Las 377.295 entradas del paquete permanecen ancladas por el índice completo.
  Raster, geometría, animación compilada, audio y navegación se contabilizan,
  pero se excluyen como autoridad independiente de estado del servidor.
- El escaneo de contenido cubre 121.404 archivos y 5.437.337.085 bytes.
  Registró 89 coincidencias de barra, cuatro de capacidad, 49 de creación y 81
  de transformación/spawn; cero nombres de retorno inicial y cero marcadores
  de suministros iniciales. Las coincidencias se reducen a bindings/UI,
  tutoriales, capas/cinemáticas de `login2`, animación/efectos y
  `Player_Spawn` de misiones antiguas en zonas 140/142/144.
- Veintiséis entradas del índice no publican digest (MD5 cero) y se verifican
  por tamaño exacto. Los dos JSON de launcher EAC publican un MD5 desfasado;
  dos extracciones independientes produjeron los mismos bytes y SHA-256. Se
  documentan como diferencias de salida decodificada y no tienen relación con
  creación.
- El loader nativo de `return_points` conserva solo id, nombre y
  `use_additional`; no carga transformación.
- Manifiesto:
  `generated/gamepak-full-xml-world-evidence-v1-manifest.json`.
- Manifiesto binario:
  `generated/client-binary-creation-evidence-v1-manifest.json`, SHA-256
  `511D6548C700CABAED04A79C237D5008B0E29D8BB1BA8597B8235DD8525A8E87`.
- Cierre global:
  `generated/global-client-creation-sweep-v1-manifest.json`, SHA-256
  `BC66A656598792DFD5D4A7E23996C639C21450C285F40A6EE6044438B96E4C3B`.
  Consolida 11 manifiestos y nueve artefactos de decompilación; su integridad
  es `clean`.
- Escaneo global de contenido:
  `generated/gamepak-global-content-scan-v1-manifest.json`, SHA-256
  `F594E9FB3EBB785405781EF7359741C92EC54F7192B651E5D60B2DAFFC23A458`.

## Protocolo cerrado

- C2G creación (`FUN_3997d1b0` + `FUN_399a70b0`): nombre, raza, género,
  7 `uint32` corporales, modelo de 0x128 bytes, 3 bytes de habilidad,
  `level=1`, `introZoneId=-1`.
- El cliente construye explícitamente `introZoneId=-1`; una zona enviada por
  cliente no es autoridad.
- G2C éxito, opcode `0x2DD`: `FUN_3997b180 → FUN_399228b0`, exactamente el
  serializador de personaje usado por la lista.
- `SCActionSlots`: 217 entradas; byte tipo, sin payload para 0, `uint32` para
  1/2/5/6 y `uint64` para 4.
- Actualización individual: mismo layout de acción, precedido por byte de
  índice.
- C2G `0xAE` es ordenar inventario (`FUN_397d3980`), no barra.
- `BaseActionBarEmptySlotCount` termina en telemetría HTTP; no registra
  acciones.
- La ruta de registro automático probada es
  `SCSkillLearned/FUN_392fa740 → FUN_395fb5a0 → FUN_39690860 →
  FUN_39690340`: bajo nivel 21 busca la habilidad ya presente o la primera
  ranura base vacía y emite `ACTION_BAR_AUTO_REGISTERED`. No prueba que el
  servidor auténtico envíe `SCSkillLearned` durante la creación ni define el
  snapshot inicial completo.
- `FUN_3991e9f0` serializa posición, tres ángulos, zona, `invenSlots` y
  `bankSlots` desde el estado de personaje suministrado por servidor.
  `FUN_39926040`/`FUN_3997dfa0` consumen además
  `numInvenSlots`/`numBankSlots` en el estado completo.

## Implementación de servidor preparada

- `NativeCharacterCreationCatalog` y `CharacterBootstrapPlan` resuelven antes
  de asignar IDs: plantilla, transformación, capacidad, equipo, suministros,
  habilidades y las 217 acciones.
- El catálogo exige tablas derivadas con procedencia cerrada para spawn,
  capacidad, slots de suministros y barra. Si falta una, no utiliza fallback y
  bloquea toda creación.
- Valida matriz, apariencia por modelo/slot, referencias, cantidades, grados,
  espacio, colisiones de slot y conflicto dos manos/mano secundaria.
- `CharacterManager` conserva el lock/política de cuenta, reserva el nombre de
  forma atómica y solo materializa después del plan.
- El cargador legado de creación ya no consume `ability_id` desde
  `character_equip_packs`/`character_supplies`; el runtime nativo puede
  reemplazar ambas tablas sin heredar su esquema histórico.
- La habilidad inicial se selecciona sobre el catálogo completo con los cinco
  predicados AA8 probados (`ability_id`, `ability_level<=1`, `auto_learn`,
  `need_learn`, `show`) y se materializan también las habilidades
  predeterminadas relacionadas con la plantilla.
- La creación guarda personaje, habilidades, blob de 217 acciones y únicamente
  sus objetos dentro de una transacción MySQL.
- `ItemManager.SaveCreatedItems` reutiliza el serializador central. Los flags
  dirty se limpian únicamente después del commit.
- Un fallo revierte MySQL, nombre, ID de personaje, objetos e IDs de objeto sin
  encolar borrados de objetos que nunca existieron.
- Una acción inválida o con bytes sobrantes no muta el personaje y provoca
  resincronización autoritativa de las 217 posiciones.
- Equipo, apariencia y suministros se crean como filas individuales en sus
  ranuras exactas; cada ID queda registrado antes de insertar el objeto en su
  contenedor. La orientación se guarda y recarga en orden `roll/pitch/yaw`.
- El serializador de modelo conserva `model_id` en la respuesta/lista, en vez
  de emitir el cero histórico.

## Puertas de autoridad aún abiertas

1. `spawn_transform_unproven`: no hay XYZ ni rotación de servidor para las seis
   razas; el cliente confirma que esos campos llegan con el estado del
   personaje, pero no sus valores iniciales.
2. `action_bar_bootstrap_unproven`: no se observó la posición inicial de la
   habilidad seleccionada ni un snapshot nativo completo. El auto-registro
   posterior a `SCSkillLearned` no demuestra el flujo de creación.
3. `supply_inventory_slots_unproven`: la tabla nativa no contiene ranura de
   mochila; el cliente la recibe en los paquetes de inventario y los cuatro
   suministros tienen desactivado `auto_register_to_actionbar`.
4. `initial_inventory_capacity_unproven`: la tabla nativa no contiene capacidad
   inicial de mochila/banco; el cliente consume ambas capacidades desde el
   servidor.

Resolverlas requiere protocolo observado contra un servidor AA8 auténtico,
otra fuente binaria de servidor o nueva evidencia inequívoca. No se completarán
con `CharTemplates.json`, orden de filas, primera ranura libre ni nombres.

## Validación

- Extractor ejecutado dos veces con resultados idénticos:
  - datos:
    `B5749F84DB3993A4BB70CCF77E6F3A16CC5E1581312653BE5D8BF341D5A0BFBE`;
  - manifiesto:
    `17CB722F3A6E2328DC14774E8C66844E2DB19E2C500AE3018ED6C8C2579AD250`.
- Builder: salida 2, `built=false`, sin crear SQLite.
- El manifiesto global se construyó dos veces con SHA-256 idéntico:
  `BC66A656598792DFD5D4A7E23996C639C21450C285F40A6EE6044438B96E4C3B`.
- Build Docker .NET Core 3.1 del proyecto `game`: correcto.
- Suite Docker .NET Core 3.1: 209/209 pruebas aprobadas. El dominio aporta 13
  pruebas de protocolo para petición de creación, modelo de respuesta,
  snapshot de 217 acciones, actualización individual y exclusión documentada
  de `0xAE`.
- No se cambió MySQL, no se reinició `game`, no se desplegó una imagen y no se
  migraron personajes.
- Este checkpoint no declara cumplido el criterio visible.
