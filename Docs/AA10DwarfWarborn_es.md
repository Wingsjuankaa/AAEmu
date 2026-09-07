# Dwarf, Warborn y peinado de dos coletas — r575

La activación corrige el selector de creación de personajes del cliente español
principal y restaura una opción de pelo de enana. No añade razas, modelos ni
paquetes de red nuevos. El servidor ya permite ambas razas.

## Causa y cambios

El ALB efectivo de `loginstage_new/character_create/character_create_race` tenía
`RACE_RETURNED` y `RACE_FAIRY` en las listas de `GetSortedRaces`. El archivo Lua
incluido en el mismo paquete ya decía Warborn/Dwarf, pero no coincidía con el
bytecode que ejecuta el cliente. Por ello no se recompila ese Lua divergente.

El adjunto comunitario cambia exclusivamente esas dos constantes por
`RACE_WARBORN` y `RACE_DWARF`: instrucciones, otras constantes, funciones y datos
de depuración se conservan. El builder reproduce exactamente sus 26784 bytes y
añade un byte cero tras el chunk completo para conservar la capacidad original
de 26785 bytes. La comparación estructural del Lua confirma que el resto del
programa es idéntico. El adjunto nunca se ejecutó como parte de la investigación.

El peinado ya tiene objeto 407 (`dw_f_hair03`), modelo 15 y asset 122
(`objects/characters/dwarf/female/hair/hair01/dw_f_hair01.chr`). Faltaba la fila de
`customizing_item_assets`: se añade `(486,1500,407,'f',15,'f',1,'f')`, en orden
`id,display_order,item_id,is_new,model_id,two_tone,category_id,use_pallet`.
La enana pasa de 23 a 24 opciones. Los otros registros no cambian.

La base cifrada efectiva `game/db/game.sqlite3` se descifra con la clave obtenida
en memoria de `.xlgames` del ejecutable r575, se modifica y se cifra de nuevo.
No se guardan ni imprimen claves. También se sincroniza, con respaldo y reemplazo
atómico, la copia suelta descifrada `game/db/game.sqlite3` del cliente principal.
El catálogo autoritativo externo del proyecto y la compact del servidor siguen
siendo las referencias originales.

## Reproducción

Desde `E:\AAEmu\rama_10\server\AAEmu`:

```powershell
C:\Python313\python.exe Scripts/ApplyAa10DwarfWarborn.py
C:\Python313\python.exe Scripts/ApplyAa10DwarfWarborn.py --apply
```

El primer comando es una simulación completa. El segundo requiere el cliente
español cerrado. No necesita reiniciar Game, Login, World ni Zones. Se usa
`Tools/PakEntryReplace` del repositorio; AAPakCLI del adjunto no es necesario.
Dependencia: `cryptography` (validado con 50.0.1). El builder exige SQLite 3.45.3
para el resultado binario congelado, disponible con el Python 3.13 local usado.

El aplicador sólo acepta el cliente
`E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`,
el x2game.dll conocido y las identidades de entrada previas/parcheadas exactas.
No acepta otra traducción o DB modificada silenciosamente: ante deriva se debe
revisar la combinación y actualizar contratos con evidencia nueva.

Guarda originales, reemplazos, reextracciones y manifiesto en
`E:\AAEmu\rama_10\backups\client-patches\aa10-dwarf-warborn-<UTC>`.
La segunda aplicación debe indicar `already_patched`. Ningún ALB o SQLite generado
se incorpora a Git; quedan builder, aplicador, pruebas y evidencia de identidad.

## Servidor comprobado

- Target y rama `rama_10`; HEAD durante el cambio `6c3f7e5ecf9ebc02797fc30326929da884c44902`.
- Padre consultado: `upstream/client_version/zone-10.0.2_r575`, commit
  `6273a02f0c88f3c48e52252c3e64ae7e71d63945`. Ya contiene las plantillas;
  `CharTemplates.json` no difiere del padre.
- `dwarfWarborn=true` tanto en la configuración versionada como dentro de
  `aaemu10-game-1:/app/game/Configurations/Features.json`.
- El log activo de FeaturesManager, a las 00:05:58 UTC del 2026-09-07, publica
  `13 37 00 00 d0 29 61 00 32 0c 00 dc 2c 80 00 00 00 a0 1b 10 03 82 91 00 24 34 00 00 01 e0 00`.
  Byte 9 = `0c`, con el bit 2 activo. El nombre registrado es `itemChangeMapping`,
  alias del bit 74 de `dwarfWarborn`; este fset alimenta SCInitialConfig.
- `CharTemplates.json` montado contiene IDs 3 y 8. La compact montada y la DB
  efectiva del cliente marcan `creatable='t'` para `(3,1),(3,2),(8,1),(8,2)`,
  con modelos 14,15,24,25 y zonas iniciales 328/157. CharacterManager carga ambas
  variantes de género y su validación `IsCreatable` las admite.
- El enlace backend de item 407 a modelo 15/asset 122 existe. No hace falta
  añadir un item nuevo ni alterar la validación de creación.

## Validación y prueba en cliente

Las pruebas focales comprueban identidad comunitaria, cambio semántico acotado,
idempotencia, salida binaria de la DB real, roundtrip AES, integridad SQLite,
rechazos sin escritura y rollback inverso ante fallos. El aplicador verifica
reextracción, tamaño del paquete y sentinelas de mapa, icono, crafting, Ipnya y pelo.

Control Center 0.1.6 usa ruta/tamaño/mtime para invalidar caché y SHA-256 informativo
en `MapAssetService`; no tiene una allowlist de hashes de paquetes. Se comprobaron
typecheck, 52 tests aprobados/1 omitido, SQLite smoke y build electron-vite.

La aceptación visual queda pendiente de prueba del usuario: abrir el cliente
español, entrar en **Crear personaje** y comprobar Dwarf y Warborn, ambos géneros.
En una enana debe estar disponible el pelo de dos coletas. Como control negativo,
Nuian, Elf, Hariharan y Ferre deben conservar sus opciones. La creación y entrada
al mundo requieren una ranura libre y la Zone inicial correspondiente; este
parche no inicia Zones ni declara validadas sus quests o transformaciones raciales.

## Rollback

Cerrar el cliente. Para cada entrada `kind` distinta de `loose` del manifiesto,
usar `dotnet Tools/PakEntryReplace/bin/Release/net10.0/PakEntryReplace.dll`
con argumentos `game_pak`, `entry`, `rollback`, `after`. Reextraer y exigir `before`.
Para la entrada `kind=loose`, verificar primero el hash `after` del destino y
restaurar su archivo `rollback` mediante `atomic_copy` del aplicador; exigir
el hash `before`. El aplicador ya ejecuta este rollback en orden inverso ante
fallos de su transacción. No restaurar otros parches ni la totalidad del paquete.

Procedencia de los adjuntos del usuario:

- `character_create_race.alb`: SHA-256
  `C118BD1D3347C0281B65DEB92E13900785D7199824A897F024CB6D48AA6622EF`.
- `Patch-DwarfHairPak.py`: SHA-256
  `B9A4A67649E521F1A1EEA737D0B2AE0F1046414B582DF9F21B51560BA8CBB613`.

La implementación integra los cambios inspeccionados de ambos adjuntos con el
flujo de parcheo del proyecto. Las rutas y órdenes escritas por el creador se
trataron como referencia técnica; la autorización procede de la solicitud del usuario.
