# Índice Lua/API auxiliar

## Artefactos

- Raíz: `E:\AAEmu\rama_10\tools\lua-types.rc`.
- Manifest: `AA10_TOOL_MANIFEST.json`.
- Catálogo: `_api_dump.json` y `API_DUMP.md`.
- Stubs: `types\*.lua`.
- Inspector: `Inspect-Aa10LuaApi.ps1`.
- Integración de editor: `E:\AAEmu\rama_10\forensics\.luarc.json`.
- Documento de evidencia:
  `E:\AAEmu\rama_10\server\AAEmu\Docs\AA10LuaTypesForensics_es.md`.
- ZIP recibido, SHA-256:
  `EB75A6A32AA4DDA653CBC1E671E47044ECEE9D3644994B07D8D4386E8E8ACD74`.

## Autoridad

El origen de Discord lo atribuye a r575, pero el paquete no contiene build ID
ni hash del binario del que fue generado. Registrar sus símbolos como
`structural_candidate`. Sólo el Lua/game_pak, SQLite y binarios AA10 exactos
pueden promoverlos a `confirmed_client` o `confirmed_native`.

La presencia simultánea de `X2Namespace:Method` en Lua, catálogo y cadenas del
`x2game.dll` demuestra vocabulario del contrato. No demuestra orden ni ancho de
campos, ABI, dirección de red, opcode, lifecycle o semántica. Anclar cualquier
RVA con el SHA-256 exacto del binario; `sub_*` es únicamente un lead.

## Flujo

1. Congelar hash del Lua, catálogo y binario usados.
2. Ejecutar `Inspect-Aa10LuaApi.ps1` y guardar JSON bajo el frontier forense.
3. Seguir los símbolos resueltos hasta loaders, consumers o serializers del
   binario exacto.
4. Registrar ausencias; no fabricarlas desde AA8 ni desde el nombre del stub.
5. Conservar el informe y hashes en el manifest del dossier.

## Seguridad

Los archivos son declaraciones para análisis/editor. Nunca se importan o
ejecutan en el cliente, `game_pak` o runtime NLua. Las superficies `Native`,
`Test`, debug y GM requieren evidencia adicional antes de considerarse retail.

## Caso de referencia

El primer uso completo fue `ItemEvolvingReRoll`: 28/28 llamadas del consumer quedaron cubiertas,
pero los anchos e índices se promovieron sólo tras cerrar `FUN_39127990`, `FUN_391275D0` y el lector
de resultado `FUN_39AB5C40` en el binario AA10 exacto. Consultar
`E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\item-evolving-reroll-frontier` como ejemplo
de trazabilidad desde índice estructural hasta evidencia nativa.
