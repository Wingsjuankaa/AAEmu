# Fase B1 — sockets y lunagems nativos AA8

Esta carpeta reconstruye la primera parte de la Fase B del sistema de objetos
sin usar filas de gameplay de la compact 3.0.

Fuentes de autoridad:

1. `compact-client-8.0-decrypted.sqlite`;
2. resultados nativos de `game11`;
3. layouts y protocolo confirmados en `x2game.dll`.

## Hallazgos confirmados

- `item_enchanting_gems`: 484 definiciones nativas.
- `item_sockets`: 783 definiciones nativas.
- `item_socket_level_limits`: 762 límites.
- `item_socket_num_limits`: 403 combinaciones de ranura y grado.
- `gem_visual_effects`: 26 referencias visuales.
- `item_socket_changes`: 27 conversiones nativas.
- El cliente cargó 8 filas mediante la consulta corta de
  `item_socket_chances`, que sólo contiene `id`, `fail_break` y `cost_ratio`.
- Las probabilidades `socket0` a `socket9` existen en el loader alternativo de
  `x2game.dll`, pero no están presentes en el resultado cacheado de este
  cliente. No se completan con valores históricos ni se asume éxito.
- AA8 usa `SCSocketingResultPacket` (`0x279`) con:
  `byte result`, `uint64 itemId`, `uint32 itemTemplateId`,
  `byte operation`, `bool success`.
- El handler `FUN_39301ac0` confirma `operation=0` para retirar y
  `operation=1` para instalar.
- El enchanting mágico usa un paquete distinto,
  `SCEnchantMagicalResultPacket` (`0x2ED`), con:
  `bool result`, `uint64 itemId`, `uint32 itemTemplateId`.

El runtime generado es candidato y permanece bloqueado hasta que el backend
implemente las reglas nativas y se confirme la fuente autoritativa de las
probabilidades que el cliente no almacena.

## Generación

```powershell
python .\extract_native_sockets.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-v1.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b1-sockets-v1.sqlite3 `
  --manifest ..\generated\native-sockets-phase-b1-v1.json
```

El script construye dos veces el artefacto y exige el mismo SHA-256, además de
ejecutar `quick_check` e `integrity_check`.
