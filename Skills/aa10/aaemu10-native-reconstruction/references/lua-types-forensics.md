# lua-types.rc como evidencia auxiliar AA10

## Disponibilidad

- Paquete descomprimido: `E:\AAEmu\rama_10\tools\lua-types.rc`.
- Manifest local: `E:\AAEmu\rama_10\tools\lua-types.rc\AA10_TOOL_MANIFEST.json`.
- Inspector reproducible: `E:\AAEmu\rama_10\tools\lua-types.rc\Inspect-Aa10LuaApi.ps1`.
- Configuración de editor: `E:\AAEmu\rama_10\forensics\.luarc.json`.
- Documentación de proyecto:
  `E:\AAEmu\rama_10\server\AAEmu\Docs\AA10LuaTypesForensics_es.md`.
- SHA-256 del ZIP recibido:
  `EB75A6A32AA4DDA653CBC1E671E47044ECEE9D3644994B07D8D4386E8E8ACD74`.

El paquete fue recomendado como correspondiente a r575, pero no incluye una
identidad de build o hash nativo demostrable. Clasificarlo siempre como
`structural_candidate`, no como autoridad de versión.

## Uso reproducible

```powershell
& 'E:\AAEmu\rama_10\tools\lua-types.rc\Inspect-Aa10LuaApi.ps1' `
  -LuaPath '<lua exacto extraído del game_pak>' `
  -X2GamePath 'E:\AAEmu\rama_10\client\ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview\Bin64\x2game.dll' `
  -OutputPath '<salida JSON bajo forensics\output\aa10-client-forensics>'
```

Cruzar cada llamada `X2Namespace:Method` del Lua con `_api_dump.json`, los
stubs `types\*.lua` y las cadenas del `x2game.dll` exacto. Una coincidencia
prueba vocabulario/presencia; no prueba ABI, parámetros, opcode, dirección,
ownership ni comportamiento. Los nombres `sub_*` sólo son pistas para anclar
consumers en el corpus nativo. Las firmas pueden estar incompletas.

## Seguridad

- No ejecutar ni importar los stubs como lógica del juego.
- No copiarlos a `game_pak`, al cliente ni al runtime NLua del servidor.
- Tratar namespaces `Native`, `Test`, debug o GM como posibles superficies de
  harness hasta demostrar que participan en el flujo retail.
- Promover un hallazgo a `confirmed_native` sólo con evidencia AA10 exacta:
  Lua/SQLite/binario/captura o una combinación suficiente de ellas.

## Primera aplicación cerrada

Replace Stat comenzó con 28/28 llamadas `X2ItemEnchant` resueltas por el catálogo y terminó
corroborado en `x2game.dll` como skill-object tipo 9 y resultado `0xCE`. El dossier está en
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\item-evolving-reroll-frontier` y la
implementación se documenta en
`E:\AAEmu\rama_10\server\AAEmu\Docs\AA10ItemEvolvingReRollLuaContract_es.md`. Usar este caso como
patrón: catálogo para reducir superficie, consumer para argumentos, binario exacto para wire y
SQLite exacta para reglas; nunca promover directamente el stub.
