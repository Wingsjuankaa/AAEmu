# Autoridad y reconstrucción AA10

## Jerarquía

1. `game_decrypted.sqlite3` r575 para catálogo estático completo.
2. compact retail para la proyección que consume el runtime.
3. loaders, consumers, serializers, fórmulas, RTTI y vtables del cliente release.
4. captura/comportamiento repetible del cliente exacto.
5. game_pak, worlds, Lua, XML, assets y localización.
6. Zone/dedicate r575 con identidad de build demostrada para semántica server.
7. upstream padre como baseline de implementación.
8. AA8 como comparador x64/estructural sujeto a confirmación AA10.

## Clausura

Empezar por acción visible y recorrer datos, descriptor, skill/effect/buff,
estado, ownership, transacción, persistencia, packet y observer broadcast. No
declarar completa una mecánica cuando sólo funciona la mutación final.

## Escalación

1. Consultar SQLite/grafo/dossier AA10.
2. Consultar corpus nativo guardado y proyectos Ghidra existentes.
3. Comparar upstream y AA8 para localizar una forma candidata.
4. Volver a pseudocódigo/instrucciones o extraer game_pak sólo para el hecho
   ausente/contradictorio.
5. Instrumentar o capturar dinámicamente sólo si la estática no cierra el
   contrato y registrar artefacto, bytes y condiciones.

Cuando el síntoma sea una UI cacheada aunque el estado servidor persista,
instrumentar ambos extremos en la misma interacción. La traza debe permitir
correlacionar request, flags del controlador, `ItemTaskType`/acciones, packet de
resultado y callback de refresh. Comparar el último estado funcional después de
cada intento y revertir candidatos que degraden inventario, item o casteo.

En AA10 r575 el socketing de Lunagem demostró que un valor semánticamente obvio
puede no ser el gate del cliente: `ItemTaskType.Socketing` (99) aplicaba las
mutaciones, pero `ItemSocketInsert` sólo abría el refresh con el evento de tarea
`0x2A` (42). Este hallazgo es específico de ese consumer; no generalizar 42 a
otras transacciones sin evidencia nativa.

## Protocolo y transacciones

Probar opcode, packet level, body, optional branches, framing, cifrado/counter
y lifecycle por separado. Para items/equipo/crafting/housing usar:

```text
request -> snapshot -> validation -> plan -> mutation -> persistence
        -> task/result packet -> authoritative resync
```

Validar éxito, rechazo, segunda ejecución, concurrencia relevante, relog y
observer visibility. Nunca compensar un dato faltante con un state machine
paralelo o branches por ID sin evidencia nativa.
