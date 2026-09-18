# Consumer de reset de cooldown r575

Fuente: programa Ghidra `AA10ZoneServer/x2game-dev_dedicate.dll`, x86-64,
SHA-256 `8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a`,
image base `0x39000000`. Es el consumer cliente embarcado en este binario;
no se atribuyen estos RVA al `x2game.dll` release.

Extracción en modo `-readOnly -noanalysis`. Scripts versionados:
`FindBattlerageConsumers.java`, `DecompileVtableEntries.java`,
`DecompileAddressAndXrefs.java`, `Aa10FishingAudit.java`.
Logs con prefijo `native-cooldown-` bajo el directorio forense de esta entrega.

| RVA | Papel observado |
|---:|---|
| 0xC25430 | Serializer de SCSkillCooldownReset: objeto BC; dos int32; gc/rstc/rtsc/rtstc. |
| 0x56A8C0 | Registro del functor del paquete; caller lo enlaza con 0x4C8E00. |
| 0x4C8E00 | Consumer: resetea skill y tag seleccionados, y ejecuta los tres flags adicionales de forma separada. |
| 0xBF9120 | Elimina clave skill del contenedor en +0x40. |
| 0xBF91E0 | Elimina clave tag del contenedor en +0x20. |
| 0xBF93B0 | Resuelve la skill y recorre su conjunto de tags para eliminarlos. Sólo lo llama rstc. |
| 0xBF9BB0 | Resuelve los miembros de la etiqueta y aplica 0xBF9290 a cada descriptor. Sólo lo llama rtsc. |
| 0xBF9290 | Elimina cooldown de la skill; si rtstc está activo elimina además sus tags. |

Por tanto las dos banderas antes denominadas `resetToggleSkill*` en C# estaban
mal nombradas: el consumer recorre **skills etiquetadas**, no una colección de
toggles. El cambio mantiene el orden y tamaño del body.

Conexión con datos completos AA10: buff2610 → combat_buff23 → buff2611 →
timeout trigger1374 → effect15008 → special4636 (tipo43), con valores
`0,415,1,0,1,1,0`. Se enlazan los valores4/5/6 con las tres opciones adicionales
del reset y se conserva la selección1/2 y GCD3. Las pruebas cubren combinaciones
positivas y negativas, skill/tag con el mismo número y consumidores fuera de
la etiqueta. No se crean temporizadores de supresión ni se cambian cargas.

Frontera independiente: la búsqueda de símbolos/strings de Visible localizó
los loaders de plot_conditions y plot_event_conditions, pero no cerró su
consumer dinámico. La corrección de anchors se apoya en el grafo completo r575
y en el contrato BaseUnit ya existente; no se presenta como decompilación de
ConditionVisible ni como prueba de línea de visión/obstáculos del cliente.
