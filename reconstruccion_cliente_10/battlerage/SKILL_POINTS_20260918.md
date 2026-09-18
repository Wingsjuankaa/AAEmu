# Puntos de habilidad tras restablecer Archery

Target `rama_10`, base `b6dff80924ec4a46f1a09d6b3621e7a767acf2fc`.
Padre consultado: `upstream/client_version/zone-10.0.2_r575`,
`bd38a3bd5d7439137c9dbeef7804d599c52b1a30`. El padre conserva la misma
mezcla de habilidades aprendidas y temporales; no se absorbieron commits.

## Síntoma y estado persistido

La captura de Dannia muestra Battlerage 7/12, Archery 0/12, Shadowplay 6/12
y cero puntos disponibles, incluso después de relog. La consulta de sólo lectura
confirma trece activas guardadas, ninguna de Archery, y pasivas 55/260 de coste cero.
`levels.id=55` concede 20 puntos: con este reparto deben quedar **7**.

Los logs del login registran siete grants de pesca:
`21571,38924,21194,21135,21195,21196,21290`. Sus registros AA10 tienen
`ability_id=0` y `skill_points=1`; son acciones temporales de equipo, no compras.
El servidor las mantenía correctamente fuera de MySQL y del cálculo de gasto,
pero las añadía al conjunto aprendido del cliente por dos vías:

- `UnitStateGameplaySerializer` serializaba `LiveSkillIds`, incluyendo temporales.
- `AddTemporarySkill` enviaba `SCSkillLearned`; `ResendLearnedToOwner` las repetía.

Así el cliente calculaba `20 - 13 - 7 = 0`. El reset no perdió puntos guardados:
la lista enviada al cliente volvía a introducir siete cargos falsos en cada login.
No se modificó MySQL, el presupuesto de puntos, las skills, los costes del
catálogo ni la selección de las otras ramas.

## Evidencia nativa

Lua `scripts/x2ui/logic/skill_point.lua` y `skill/tab_combat.lua`:
el contador visible es `total - used`, ambos devueltos por `X2Ability:GetSkillPoint`.

Cliente x64 r575, image base `0x39000000`:

| RVA | Observación |
|---:|---|
| 0x7BE540 | Registra `GetSkillPoint` con el binding 0x7BD8D0. |
| 0x7BD8D0 | Devuelve presupuesto y gasto; el caso global usa 0xB95F30. |
| 0xB95F30 | Recorre el conjunto aprendido y suma el coste de cada descriptor, más pasivas. |
| 0xB95E60 | Variante filtrada por ability; explica que los grants de ability 0 no aparezcan en las tres barras. |
| 0x3EB470 / 0x367FC0 | Enlazan `SCSkillLearned` con el consumer 0x33D4E0. |
| 0x33D4E0 / 0x6BD290 | Consumen el skill id y ejecutan el aprendizaje, seguido del refresco de UI/swaps. |
| 0x2413A0 | Inserta en el contenedor aprendido de la unidad. |
| 0x9A38C0 | Carga las relaciones nativas `buff_skills` habilitadas. |

Ghidra contiene el binario original SHA-256
`2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76`.
Se cotejó **todo el archivo** con el cliente efectivo SHA-256
`405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734`:
únicamente cambian dos bytes en offsets de archivo `0x1336778/0x1336779`,
el parche documentado de Auroria. El código analizado permanece idéntico.
No se atribuye al cliente una decompilación del dedicate.

Extracción: `analyzeHeadless -process x2game.dll -readOnly -noanalysis`, usando
`Aa10FindStringReferences`, `Aa10ListSymbolsMatching`, `Aa10FishingAudit`,
`DecompileVtableEntries` y `DecompileAddressAndXrefs`. Los logs conservan la
cadena de referencias y la comparación binaria en `client-identity.json`.

## Corrección y regresiones

1. El bloque de habilidades de UnitState contiene sólo `Skills.Keys`, también
   cuando un buff reemplaza visualmente una habilidad aprendida.
2. Los grants no emiten aprendizaje permanente. Se conserva su autorización en
   `TemporarySkills`/`HasSkill` y su retirada al expirar o quitar el buff.
3. El reenvío tras cambiar rama conserva las habilidades realmente aprendidas,
   incluidos sus originales; el cliente resuelve grants/swaps con sus buffs.

Pruebas: 19/19 en `BuffGrantedSkillsTests`; se corrigió la expectativa anterior
que exigía `SCSkillLearned` para un grant. Se añadieron los casos del reparto
20→13 con las siete acciones de pesca, reset repetido, snapshot, retirada,
original reemplazado y reenvío. El primer ensayo detectó además dos fallos de
preparación del fixture (Appellations ausente), corregidos antes de aceptar los
resultados. No se presentan esos dos errores como regresiones de producción.

Restore/build Release correctos y suite completa **5460/5460**, sin omitidos.
No se volvió a ejecutar la suite de integración que requiere servicios externos.

## Runtime y aceptación

Evidencia de diagnóstico/build/despliegue:
`E:\AAEmu\rama_10\artifacts\skill-points-20260918`.
El manifiesto de esta entrega registra imagen anterior/nueva y validación.
Game arrancó a las 18:42:49 UTC, healthy y sin reinicios; conexiones TCP a
1239/1250 correctas. Las dos copias publicadas de Game tienen el mismo hash,
la SQLite montada conserva el suyo y las skills guardadas de Dannia coinciden
con la captura de estado anterior. El log conserva avisos de smelting fuera de
alcance. Tras el reinicio no se observaron procesos ZoneHost ni conexiones de
Zone a World; su arranque desde Control Center queda a cargo del usuario.

Para limpiar la lista contaminada del cliente ya conectado hace falta volver al
selector y entrar con el servidor corregido. Con el reparto de la captura debe
mostrar siete puntos libres. Verificar también que equipar/quitar la caña no
altera ese contador, que conserva sus acciones de pesca y que gastar un punto
real reduce el contador en uno. La aceptación visual queda pendiente del usuario;
las pruebas de snapshot no se presentan como una sesión real de pesca.

No se inicia ni se cierra el cliente o las Zones del usuario. La actualización
de Game puede desconectar sus sesiones. Rollback: restaurar el tag de imagen
`aaemu-world:rollback-before-skill-points-20260918` al tag habitual y recrear Game;
no requiere rollback de datos de personajes.
