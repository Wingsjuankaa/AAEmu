# Catálogo Lua AA10 para análisis forense

## Estado

Disponible desde el 19 de agosto de 2026 como herramienta editor-only para
ArcheAge Returns `10.0.2.13 r575`:

- catálogo: `E:\AAEmu\rama_10\tools\lua-types.rc\types`;
- manifiesto local: `E:\AAEmu\rama_10\tools\lua-types.rc\AA10_TOOL_MANIFEST.json`;
- guía operativa: `E:\AAEmu\rama_10\tools\lua-types.rc\README.md`;
- configuración Lua Language Server:
  `E:\AAEmu\rama_10\forensics\.luarc.json`;
- inspector CLI:
  `E:\AAEmu\rama_10\tools\lua-types.rc\Inspect-Aa10LuaApi.ps1`.

La configuración selecciona Lua 5.1 y añade `lua-types.rc\types` como
`workspace.library`. Para obtener autocompletado y diagnósticos se abre
`E:\AAEmu\rama_10\forensics` como workspace en un editor que tenga Lua
Language Server. El servidor de lenguaje no estaba instalado en la máquina al
incorporar el catálogo; el inspector CLI permite realizar cruces reproducibles
sin esa dependencia.

## Qué aporta

El paquete contiene declaraciones de APIs nativas y de script, widgets,
constantes y eventos del cliente. Sirve para:

- resolver nombres `X2*` usados por un consumer Lua;
- obtener retornos parciales y nombres de parámetros cuando fueron recuperados;
- localizar una implementación candidata indicada como `sub_*`;
- distinguir una llamada conocida de un typo o una API ausente;
- reducir el frente que después debe confirmarse en `x2game.dll`, protocolo o
  captura dinámica.

El directorio descomprimido incluye también `_api_dump.json` y `API_DUMP.md`.
El primero conserva valores y tablas que el generador no siempre proyecta a
los stubs; el segundo facilita la consulta manual. Ambos son archivos extra y
no estaban dentro de `lua-types.rc.zip`.

## Identidad y límites de autoridad

Discord atribuyó el paquete a Returns r575, pero el ZIP no contiene versión del
cliente, SHA-256 ni cadena de custodia. Por ello se clasifica como
`structural_candidate` corroborado:

- ZIP SHA-256:
  `EB75A6A32AA4DDA653CBC1E671E47044ECEE9D3644994B07D8D4386E8E8ACD74`;
- los cinco archivos del ZIP coinciden byte a byte con sus copias extraídas;
- el 96,66 % de los 2.751 nombres únicos de `client_api.lua` y el 99,14 % de
  los 816 nombres de widgets aparecen como strings en el `x2game.dll` r575
  exacto;
- la presencia de un string no prueba firma, RVA, semántica, serializer ni
  lifecycle.

Los namespaces `Native` y `Test`, además de varias funciones debug/GM, pueden
haber sido añadidos por el harness de captura. No son autoridad retail.

Los parámetros están tipados mayoritariamente como `any`; algunas bindings,
incluida `X2ItemEnchant:Execute`, aparecen sin parámetros aunque el Lua retail
sí les pasa argumentos. Para contratos de llamada manda el consumer r575 y
después el binding nativo exacto, no el stub.

## Seguridad

Nunca copiar el catálogo a `game_pak`, cargarlo desde el cliente ni ejecutarlo
mediante NLua del servidor. Los archivos declaran stubs vacíos y asignan
constantes para el analizador; ejecutarlos podría reemplazar APIs globales
reales.

El inspector es de sólo lectura salvo cuando se solicita `-OutputJson`. La
opción `-ClientBinary` comprueba presencia de vocabulario y registra el hash del
binario, pero no promueve automáticamente los RVA del catálogo a evidencia
nativa r575.

## Primera aplicación

La primera prueba se realizó sobre `ItemEvolvingReRoll` y resolvió 28 de 28
llamadas nativas únicas del consumer, además de comprobar los 28 pares de
namespace/método contra el `x2game.dll` exacto. El contrato y las brechas
resultantes están en `Docs/AA10ItemEvolvingReRollLuaContract_es.md`.
