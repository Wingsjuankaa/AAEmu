# Dwarf/Warborn y pelo de enana — 2026-09-07 UTC

Estado: **desplegado; aceptación visual pendiente**. Implementación y guía en
`Docs/AA10DwarfWarborn_es.md`. Sin cambios ni reinicios de servidor.

Se reprodujo exactamente el ALB comunitario del usuario (dos constantes de
GetSortedRaces) y se restauró la fila 486/item 407 del catálogo de personalización.
La comparación semántica demuestra que no cambia otro código Lua. El Lua fuente
incluido en el paquete difiere del ALB efectivo y no se recompiló.

Cliente: `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
Tamaño de game_pak antes/después: **74107641856** bytes.

| Identidad | SHA-256 |
| --- | --- |
| game_pak antes (Ipnya V3 aceptado) | `723A022888D970D76D2CEF16A4AA65BBD5C4260157EF5D8D75E47CF659E4A0E4` |
| game_pak después | `B46859E855131495BF36C26FD4EF8010A362A2C29010EB8C855582276B70495C` |
| selector ALB después, 26785 bytes | `545FA08321F3159AEC4D4B4927FA6880330C8AB8CCDECD7293A9A9EFB79C1EA6` |
| game.sqlite3 cifrada después, 552178688 bytes | `1387EC6535270F99D9469F7F895306673827AFB0861E1B4E5F7BAAA503F605EB` |
| game.sqlite3 suelta descifrada después | `ED288C43AA1D459BCFC56D5433A6E52D1EECF42E2D3F1C25D8BC9BF4F13860B3` |

Manifiesto de instalación y rollback:
`E:\AAEmu\rama_10\backups\client-patches\aa10-dwarf-warborn-20260907-005403-042659Z\manifest.json`.
Dry-run previo:
`E:\AAEmu\rama_10\backups\client-patches\aa10-dwarf-warborn-20260907-005236-067609Z\manifest.json`.

Evidencia local de entradas originales, comparación comunitaria y runtime:
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\dwarf-warborn-activation`.
El manifiesto JSON de este checkpoint incorpora el estado final de idempotencia.

Validación: 11 pruebas focales aprobadas (incluye datos retail reales), integridad
SQLite y roundtrip AES, reextracción exacta de ambas entradas, verificación de la
copia suelta. Mapa, icono, crafting, Ipnya V3 y asset del peinado conservan hashes.
Control Center: typecheck aprobado; 52 tests aprobados y 1 omitido; smoke SQLite
y build electron-vite aprobados. No hay allowlist de hash completo en MapAssetService;
la caché se invalida por ruta/tamaño/mtime y registra SHA-256 informativo.

Backend ya listo: config versionada y montada true; fset del proceso activo con
byte 9 = 0x0c (bit 74 activo, alias itemChangeMapping), plantillas 3/8 y cuatro
combinaciones de raza/género creatable confirmadas en compact montada.
No se probaron ni se afirman como resueltas las quests, spawns o transformaciones
raciales. No se crearon personajes de prueba ni se inició ninguna Zone.

Siguiente prueba: abrir Crear personaje en el cliente español, comprobar Dwarf
y Warborn con ambos géneros, y el peinado de dos coletas de enana; verificar que
las otras cuatro razas mantienen sus opciones. Registrar aceptación visual antes
de declarar este checkpoint aceptado.
