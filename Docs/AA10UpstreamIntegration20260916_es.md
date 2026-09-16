# Integración del padre AA10 — 16 de septiembre de 2026

Fork `Wingsjuankaa/AAEmu:rama_10`; padre exclusivo `AAEmu/AAEmu:client_version/zone-10.0.2_r575`.
Base local `e564181b6`, primera revisión padre `8e71a37aa`: 180 commits y 120 archivos con conflictos. Respaldo `backup/rama_10-before-upstream-20260916-e564181b6`. La última comprobación detectó otros 20 commits hasta `b439e1cc0` (segunda etapa).

## Resoluciones definitivas de la primera etapa

El JSON adjunto conserva el inventario de resoluciones iniciales. Esta sección prevalece sobre decisiones provisionales anteriores a las pruebas.

- Barcos/pesca: se conservan orilla, SL10, equipo, escuelas de pesca y ZoneHost. Aceptación en juego pendiente.
- ArchePass/Bless: se conserva una única implementación nativa activa, ledger atómico, consumo al previsualizar, cancelación y reinicio diario. DTO comunitarios adaptados al mismo estado. No se reemplazan las tablas. CharacterArchePass y sus dos suites de estado, más CharacterBlessUthstinTests, se sustituyen por las suites nativas del runtime retenido; originales recuperables del padre y archivados en los artefactos externos. Pruebas puras compatibles conservadas.
- Objetos: Seize comunitario de 11 bytes confirmado en cliente release RVA B510A0; la dirección comunitaria 39CDDC20 era incorrecta. ItemCountUpdate firmado, action 5, confirmado en RVA B50AB0. Se conservan blobs persistentes y nueve sockets nativos.
- Crafting: planificador atómico propio más estación/fase, recetas, cancelación y origen de frescura comunitarios. Pruebas nuevas: origen válido produce pack; origen ausente rechaza sin consumir. Conversión mantiene grados y selección exacta con relaciones/exclusiones comunitarias.
- Misiones/buffs: ledger propio, EffectFire, requisitos y Breaker combinados con agentes/temporización comunitarios. QuestReact se publica después del contexto y no duplica la fase personal. Sort-6 no se acepta como misión personal, evitando duplicar premios públicos.
- Familias/gremios: los premios del ledger usan los agregados persistentes comunitarios. Las tablas auxiliares antiguas permanecen archivadas; la migración exige conversión explícita si contienen progreso. Ambas están vacías en este runtime.
- Asistencia: calendario exacto, 31 entradas de 9 bytes, exclusión mutua por cuenta y migración de las dos asistencias previas. No se reutiliza implícitamente una campaña caducada.
- Housing: mismo layout en Game y Zone; callbacks de conflictos/torres restaurados fuera del bloqueo de estado.
- Labor: publicación del débito ya confirmado con deltas exactos de ambos saldos; finalización duplicada no cobra dos veces.
- Configuración: Patron máximo, Jardín y reparación desde inventario conservados; Butler e Item Smelting desactivados. Override runtime ActabilityRate=100.0 preservado. Cliente español sin modificaciones.

## Segunda etapa y cierre conjunto

Se integran los 20 commits siguientes hasta `b439e1cc0d4bb96647d11dcb76da61b0246a53e1`: 200 commits comunitarios en total. Se fija esa revisión comprobada para que el avance concurrente del padre no impida terminar una versión validada.

- Buffs: apilado por invocador y expiraciones independientes comunitarias; se conservan el refresco de braseros, las transformaciones válidas y la autoridad de Zone. Se elimina una segunda retirada que habría borrado la instancia de otro invocador.
- Breaker: retirada comunitaria para buffs ordinarios; los que tienen efectos Breaker propios esperan a que ambas etiquetas estén presentes. La prueba de convergencia instala los dos índices reales del cargador y verifica ambos órdenes.
- Monturas: retirada de poses al invocar y filtro por asiento al desmontar combinados con la persistencia propia de mascotas y barcos.
- Combate: absorbidas las mejoras de máscaras de impactos, velocidad, asedio, precisión y recursos. Corregido el límite cero de un recurso conocido: debe impedir acumular, no convertirse en ilimitado.
- Arranque: se elimina la carga duplicada de `doodad_func_quest_reacts` introducida por la combinación de ambas implementaciones. Los arranques de comprobación detectaron también doce cargadores de objetivos/recompensas duplicados. Se retienen los cargadores nativos de fases 3/4 y se unifica el índice de grupos. Prueba nueva: ambos consumidores ven los mismos grupos y recargar no duplica miembros. Estos solapamientos no eran conflictos textuales de Git.

## Verificación y rollback

Solución Release compilada; primera etapa **4.425/4.425 pruebas**, incluidas las nuevas regresiones de frescura y finalización duplicada. Se corrigió una carrera en las pruebas del catálogo ArchePass usando instancias aisladas.

Migración: `Scripts/IntegrateAa10Upstream20260916.py`, plan por defecto y `--apply` con Game detenido. Añade sólo lo necesario, registra su aplicación, conserva esquemas ArchePass/Bless y no reescribe blobs.

Artefactos: `E:/AAEmu/rama_10/artifacts/upstream-integration-20260916`. SQL previo `premerge-runtime.sql`, SHA256 `3a432e1842cc3244be2fd9de56c2dcef3667cd5e609db7b601d977e1fd092723`. Imagen anterior `70cd0c2c1d4076fae3a2e7ee02413ddbd4980cad2d62177050e1b03f3341fa2d`. Configuraciones en `runtime-config-before`. Compact, cliente y ZoneHost conservados. No se opera el lifecycle de Zones.

Checkpoint: ambas etapas compiladas en Release y **4.592/4.592 pruebas aprobadas, cero omitidas**. La migración aplicó 64 sentencias y la segunda ejecución confirmó idempotencia. Verificados los 448 blobs de objetos sin cambios y las dos asistencias migradas. Respaldo final con Game detenido: `predeploy-runtime.sql`, SHA256 `6c66a5d4b68eaba9ef794cf8724172b829193a7ed368131c7f8158a4de172c56`. Despliegue final verificado: Login, Game, World y Stream operativos; API responde, cero reinicios. Imagen Game `sha256:b5c72b6362259317be72951cbcc7dd7aa09e220d30e3eb566bcbf9ea206dc41a`; Login `sha256:3b5df8db3e83ff45380b4bec5036ab60723d37a9b4e2986805e0cf7062f93c9a`. Compact r575 y ZoneHost mantienen sus hashes. Los cuatro mensajes de error residuales corresponden a las definiciones previas de Smelting desactivado; no hubo excepciones de arranque en la imagen final. Aceptación en el cliente pendiente; el usuario administra las Zones.
