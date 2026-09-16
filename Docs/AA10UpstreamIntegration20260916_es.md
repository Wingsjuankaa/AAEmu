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

## Verificación y rollback

Solución Release compilada; primera etapa **4.425/4.425 pruebas**, incluidas las nuevas regresiones de frescura y finalización duplicada. Se corrigió una carrera en las pruebas del catálogo ArchePass usando instancias aisladas.

Migración: `Scripts/IntegrateAa10Upstream20260916.py`, plan por defecto y `--apply` con Game detenido. Añade sólo lo necesario, registra su aplicación, conserva esquemas ArchePass/Bless y no reescribe blobs.

Artefactos: `E:/AAEmu/rama_10/artifacts/upstream-integration-20260916`. SQL previo `premerge-runtime.sql`, SHA256 `3a432e1842cc3244be2fd9de56c2dcef3667cd5e609db7b601d977e1fd092723`. Imagen anterior `70cd0c2c1d4076fae3a2e7ee02413ddbd4980cad2d62177050e1b03f3341fa2d`. Configuraciones en `runtime-config-before`. Compact, cliente y ZoneHost conservados. No se opera el lifecycle de Zones.

Checkpoint: primera etapa validada; segunda etapa y despliegue pendientes. Se actualizará antes de la entrega final.
