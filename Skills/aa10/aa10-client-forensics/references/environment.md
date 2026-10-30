# Entorno forense AA10

## Identidad del cliente

- Build: ArcheAge Returns `10.0.2.13`, revisión `r575`.
- Arquitectura: x86-64.
- Raíz de proyecto: `E:\AAEmu\rama_10`.
- Cliente principal (decisión 2026-09-06): `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview`.
- Referencia original inmutable: `E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575`.
- Piloto español histórico: `...\ArcheAge-Returns-10.0.2.13-r575-es_ES`.
- Repositorio consumidor: `E:\AAEmu\rama_10\server\AAEmu`.

El principal usa `+locale en_us` y contiene traducciones y parches propios de
UI. Sus entradas efectivas son la primera referencia para un fallo observado.
Registrar hashes actuales con `scripts/status.ps1`; no reutilizar los hashes
históricos de abajo para su compact o game_pak. La autoridad estática completa
sigue siendo `game_decrypted.sqlite3`. Contrastar con el original cuando se
necesite separar comportamiento nativo de una modificación local.

## Fuentes confirmadas del baseline histórico (2026-08-15)

| Artefacto | Ruta | SHA-256 |
|---|---|---|
| SQLite completa | `E:\AAEmu\rama_10\data\sqlite\authoritative\game_decrypted.sqlite3` | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` |
| SQLite retail equivalente | `...\game\db\game.sqlite3` | mismo hash |
| Compact retail | `...\game\db\compact.sqlite3` | `F8C7A0268A26D4EFAEC47A2A2B1B525447BF16C274506CD97BF571839B5E6D29` |
| x2game release | `...\Bin64\x2game.dll` | `2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76` |
| game_pak | `...\game_pak` | 68,963,258,880 bytes; `32499AC6BF3ED1C1CE24B5A15A151355CB0C5A352A0C2BA727769AEEB3FC89D5` |

Las tres copias conocidas de la SQLite completa de 552,178,688 bytes tienen
el mismo SHA-256. La completa posee 1,374 tablas; compact posee 1,003 y todas
están contenidas en la completa. Hay 371 tablas sólo en la completa. Ambas
pasaron `PRAGMA quick_check=ok` el 2026-08-15.

## Snapshot operacional posterior

El cliente retail observado el 2026-08-19 conserva la SQLite completa con el
hash del baseline, pero presenta otros artefactos operacionales:

| Artefacto | SHA-256 operacional 2026-08-19 |
|---|---|
| Compact retail | `0ADAA070936F8AFBE0A60307C391CF1C08ECCB98DD48A32024D4F295C140FC86` |
| x2game release | `405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734` |

Mantener ambos snapshots separados. No transferir RVAs del x2game baseline al
operacional sin reanclaje por símbolos, cadenas y consumers.

## Proyectos nativos existentes

- Cliente release: `E:\AAEmu\rama_10\forensics\ghidra\ghidra-projects-aa10-client-release\AA10X2GameRelease.gpr`.
- Cliente dev: `E:\AAEmu\rama_10\forensics\ghidra\ghidra-projects-aa10-client\AA10X2GameDev.gpr`.
- Zone server: `E:\AAEmu\rama_10\forensics\ghidra\ghidra-projects-aa10-server\AA10ZoneServer.gpr`.
- Análisis de daño dedicate: `E:\AAEmu\rama_10\forensics\output\aa10-dedicate-ghidra`.

Reutilizar estos proyectos. No asumir que `x2game-dev_dedicate.dll` o un
binario dev corresponde exactamente al release sin congelar hash/build.

## Salidas

- Objetivo: `E:\AAEmu\rama_10\forensics\output\aa10-client-forensics`.
- Código/checkpoints futuros: `E:\AAEmu\rama_10\server\AAEmu\reconstruccion_cliente_10`.
- Crosswalk AA8 existente: `E:\AAEmu-Research\output\aa8-client-forensics`.
- Consumidor/visor local: `E:\AAEmu\rama_10\tools\AAEmu.ControlCenter`.

AAEmu Control Center abre la SQLite autoritativa con `readonly`,
`fileMustExist` y `PRAGMA query_only`. Puede consumir manifests forenses y una
caché derivada en `%LOCALAPPDATA%\AAEmu Control Center\cache`, pero nunca debe
usarse como destino de evidencia autoritativa. Mantener extractores,
procedencia y resultados reproducibles bajo el namespace forense.

No leer una compact runtime modificada como autoridad del cliente. Etiquetarla
`server_observed` y conservarla fuera del namespace retail.
