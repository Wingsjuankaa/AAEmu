# Hayden: entrega10050 bloqueada por fase inicial incorrecta

Target `E:/AAEmu/rama_10/server/AAEmu`, rama `rama_10`.
HEAD45bba0ad49fee55ab30a80168b4d6caefbb9ac87; padre
`upstream/client_version/zone-10.0.2_r575`1017677b40be6508861a8fb74e9d09fa496873c9.
No cambio de rama, commit ni push. Conservados todos los arreglos pendientes.

## Evidencia

El usuario confirma que los NPC y el actor de misión aparecen tras restaurar
Delphinad. La entrega a Hayden responde «No puedes usar esto».
Log `E:/AAEmu/rama_10/artifacts/hayden-interaction.log`:
-16:01:01, doodad15086/obj148195 inicia en44632.
-16:01:14,16:01:17,16:01:19, skill11008 solicita QuestKind2: sharedPhase44632,
characterPhase44632, candidates0. Quest10050 Ready, sin reportes BugReports relacionados.

SQLite r575 completa y compact coinciden:15086 Start44622 tiene funciones40487 y40493:
DoodadFuncQuest2108 entrega10050;2109 inicia10052. Normal44632 contiene únicamente
Use44135/11543 y corresponde a la progresión de10053.
QuestReact1954 mueve44622→44632 cuando10053 está Progress; no corresponde a Dannia.
Ambas fases tienen npctype20050: por eso el actor se veía correctamente.

`Doodad.GetFuncGroupId` conserva un fallback genérico que prefiere modelos npctype
en fases Normal para otros actores cuyo Start es invisible. El catálogo anterior
emitía FuncGroupId0 y por ello seleccionaba ese fallback en Hayden.
La infraestructura existente `DoodadSpawner.ResolveInitialFuncGroupId` ya admite
fases explícitas validadas. No hace falta alterar el resolver transversal ni AA8.

## Cambio y validación

El builder `Scripts/RestoreAa10DelphinadContent.py` ahora emite la única fase Start
de cada plantilla r575, en las mismas68 ubicaciones originales. Hayden recibe44622.
No altera progreso, requisitos, coordenadas, modelos, DB, compact ni cliente.
Upgrade permitido únicamente desde el hash anterior conocido1e065fa4…; respalda
antes de cambiar y rechaza cualquier otro catálogo diferente. Reejecución sin cambios.
Validado contra exports y lectura rb del game_pak original.

Regresión `DelphinadCatalog_HaydenStartsInReportPhaseInsteadOfLaterQuestPhase` carga
el catálogo real como recurso, lo deserializa con Newtonsoft igual que el loader y
comprueba fase inicial44622 frente al fallback44632, y fases explícitas en68 entradas.
Restore/build Release correctos;2813/2813 pruebas pasan.
Nuevo catálogo fuente/bind SHA256:
`81429821831637e1448ec551346c181530f05f0517e741452825a51c01175688`.

## Entrega y rollback

Despliegue Game autorizado permanentemente. Manifest adjunto registra imagen,
hashes y startup. Respaldos: `E:/AAEmu/rama_10/backups/hayden-phase-20260913`.
Rollback: imagen `aaemu-world:rollback-hayden-phase-20260913` más restaurar
`runtime-doodads.json` al bind original. DB/compact no cambiaron; no restaurar
el dump sobre progreso nuevo. Fuente anterior en`source-doodads.json`.

Aceptación cliente pendiente: el usuario inicia384 si el reinicio desconectó su
host, vuelve con Dannia e intenta entregar10050 a Hayden. Esperado: diálogo y
entrega disponibles; continuación10052 ofrecida según sus requisitos nativos.
No se afirma validada toda la cadena futura de Delphinad.
