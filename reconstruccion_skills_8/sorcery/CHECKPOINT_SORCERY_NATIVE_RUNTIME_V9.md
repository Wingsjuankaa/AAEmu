# Checkpoint Sorcery V9: cierre ejecutable y frontera nativa exhaustiva

Fecha: 2026-08-04  
Cliente autoridad: ArcheAge Kakao `8.0.3.12 r558734`  
Rama: `client_version/8.0.3.12-kakao-r558734-port`

## Resultado

Sorcery queda cerrada en el plano estructural y automatizado para sus doce
activas base, doce sucesores Heir, seis entrypoints internos y seis pasivas.
La auditoría V3 recorre 30 entrypoints hasta sus plots, efectos, buffs,
triggers, recursos y skills hijas y no encuentra filas ausentes ni primitivas
bloqueantes.

El cierre visual/conductual continúa siendo un gate separado: sólo el cliente
puede certificar animación, FX, física, limpieza de doodads, repetición y
persistencia después de relog. La matriz exacta está en
`SORCERY_LIVE_ACCEPTANCE_PROTOCOL_V2.md`.

## Autoridad y fuentes congeladas

| Fuente | Rol | SHA-256 |
|---|---|---|
| Runtime Sorcery V9 | runtime desplegable AA8 | `33C0268086CCF7E6914B33CCF75B3BF935F6481CE18C9006E18B76446085C6CF` |
| Stage 50 skills AA8 | filas nativas/caché directa | `B15853F5E1D24FC9FAF77C9F4F1697262F32525E6CCDE4EC96D943DD938E9E07` |
| Crosswalk AA8→10.x V1 | reducción obligatoria de vacíos e identidad | `44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71` |
| SQLite 10.x r575 | corroboración de esquema/relación, nunca balance AA8 | `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F` |
| Manifiesto V9 | receta y cierre de Insulating Lens | `FCE225F0633CCD56C21BDF1E54A349173BE7C346946569C48EEE643498948DEC` |

La jerarquía aplicada fue: fila/relación exacta AA8, crosswalk clasificado,
10.x estable sólo para cerrar identidad o schema, corpus/binario nativo y,
finalmente, aceptación manual. No se promovieron propiedades de balance desde
10.x.

## Cobertura ejecutable V3 reconciliada

- 24/24 raíces públicas: 12 base y 12 Heir.
- 6/6 entrypoints internos: `12789/12790/12791` de login-stage y
  `42012/43464/43465` de retorno contextual de Magic Circle.
- 6/6 pasivas.
- `blocked_root_count=0`.
- cero raíces con filas ausentes.
- cero special effects bloqueantes.
- 23 triggers únicos alcanzables: 18 `Started`, 4 `Timeout` y 1
  `Absorption`.
- 43 skills en el cierre ejecutable; las 40 raíces nativas Sorcery del grafo
  forense están cubiertas y no queda ningún ID sin clasificar.

Los parents `10151/10153` continúan explícitamente como candidatos tombstone:
el cliente AA8 solicitó aprenderlos, pero no existe fila raíz en Stage 50 y el
crosswalk los clasifica `aa10_only`. El runtime los conserva para aceptación
manual sin convertir sus propiedades en evidencia AA8 exacta. La skill
`15317`, en cambio, es una hija AA8 exacta `ability_id=0` alcanzada por Meteor.

El informe reproducible es
`generated/sorcery-executable-semantics-audit-v3.json`; la matriz humana está
en `generated/sorcery-executable-semantics-matrix-v3.csv` y la reconciliación
en `generated/sorcery-forensic-runtime-reconciliation-v1.json`.

## Semánticas reconstruidas

### Ejecución de plots y skills hijas

- El estado de casting/channeling se conserva a través de los nodos de plot;
  ya no se pierde entre `start`, `fire` y `end`.
- `SkillUse` valida template, probabilidad exacta, delay no negativo y agente
  de destino. Para skills posicionales crea un target desde la posición del
  ancla efectiva, evitando reutilizar un cursor heredado obsoleto.
- El test de Fire Wall: Mist (`41223`) prueba que la hija `41478` queda
  anclada a la pared temporizada.
- Las comprobaciones de alcance son borde-a-borde: consideran radios físicos
  de fuente y objetivo en vez de medir sólo centro-a-centro.

### Recursos, fórmulas y concurrencia

- `HighAbilityResourceEffect` consume los tipos corroborados por el crosswalk
  y emite el protocolo AA8 de recurso, transformación y actualización.
- `ExtendCharge` materializa el contrato de Insulating Lens: a nivel 50,
  `792 + 225% Magic Attack + 5% Max Mana`. La espina AA8 permanece autoridad;
  10.x sólo resolvió el enum estable `max_mana` y las columnas que faltaban en
  la proyección AA8.
- Los snapshots de colecciones de buffs evitan mutación concurrente durante
  triggers/ticks.
- La identidad interna de Quartz es monótona e independiente del task id
  reciclable; un tick recién programado ya no colisiona con un job terminado.

### Insulating Lens y evento Absorption

V9 restaura la cadena exacta ausente:

`buff 95 → trigger 9738 (event 29) → effect 67353 → SpecialEffect 31561 → SkillUse 37837 → effect 67349 → buff 94`.

`Absorption=29` se incorporó al router de triggers. `ConsumeCharge` calcula el
overflow bajo lock, emite el evento una sola vez cuando la carga cruza a cero
y luego termina el buff. El cierre ejecuta Ice Shard y aplica el cooldown
diferido de 30 segundos de la skill `10153`; no se dispara dos veces por daño
concurrente ni por un segundo intento sobre carga agotada.

## Hallazgo nuevo: `SkillUse.value4`

La única fila alcanzable de Sorcery con `value4 != 0` es:

- raíz Heir `41223` Fire Wall: Mist;
- special effect `42478`;
- skill hija `41478`;
- `delay=0`, `chance=0`, `value4=1`.

Se compararon exhaustivamente las 14 filas AA8 y las 64 filas r575 de
`SkillUse` con `value4=1`. Los contraejemplos descartan que el campo seleccione
la skill hija, delay, probabilidad, tipo de target, source/target agent,
plot-vs-buff, evento, GCD o validación. `game_pak`, Lua/XML y el historial de
AAEmu tampoco contienen un consumidor semántico.

La frontera binaria se extendió a las tres variantes r575 disponibles:

- `x2game-dev_dedicate.dll`, SHA
  `8936CE897D7610D2D4E0A27BE9CC97708930C33E4CB910C03D17F23088A4891A`;
- `x2game-dev.dll`, SHA
  `DBE4D32ECC3573B7E68393B8484187BA7D30F321E5F9B4A40B5E5E6363419D07`;
- `x2game.dll` release, SHA
  `2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76`.

En release, `FUN_39a82e40` carga exactamente `id,type,value1..value7` y
`FUN_39b1c1a0` busca el descriptor de skill. Sus 301 callers producen sólo dos
consumidores del patrón special-desc→skill: `FUN_396df870`, encargado de
presentación/FireSkill, y `FUN_396eb830`, un validador de requisitos de items y
shipyards. Ninguno evalúa special type 33. El RTTI
`SkillResult(SpecialEffectDesc const*, SkillSource const&, SkillTarget const&,
SkillParams const*, SkillValidationContext const*)` conduce a cuatro
validadores de enchant/socket/refurbishment/awakening, no a un dispatcher
genérico de efectos. Las búsquedas de dispatch por tipo produjeron parsers y
decodificadores sin relación con skills.

Conclusión precisa: `value4` se preserva como evidencia, pero no se le inventa
un significado. Las DLL suministradas son consumidores de presentación y
protocolo, no contienen el evaluador autoritativo del servidor original. La
conducta observable de esta ruta queda definida por la hija, el target
posicional, el delay, la probabilidad y los agentes, y se cierra en vivo con
Fire Wall: Mist. Esto es evidencia negativa de la colección disponible, no
una afirmación de que el servidor retail nunca usara el campo.

La evidencia estructurada queda congelada en
`generated/sorcery-skilluse-value4-native-frontier-v1.json`.

## Validación automatizada

- 67/67 pruebas C# dirigidas a Sorcery, plots, recursos, buffs, scheduler y
  protocolo Heir, más 38/38 del gate enfocado de movimiento y efectos
  especiales que incluye los dos contratos de retorno de Magic Circle.
- 492/492 pruebas C# de la suite completa con
  `AAEMU8_SORCERY_RUNTIME=/workspace/client_kakao/compact-8.0-runtime-transversal-sorcery-v9.sqlite3`.
- 51/51 pruebas Python Sorcery, incluidas construcción V2→V9, auditoría V3,
  traza viva, snapshot persistente y
  aceptación del runtime.
- 127/127 pruebas Python del framework forense completo.
- Runtime V9: `PRAGMA quick_check=ok` e `integrity_check=ok`.
- Auditoría V3: 30 entrypoints, 43 skills ejecutables, cero bloqueos y cero
  filas ausentes.

Una primera invocación de la suite completa sin la variable anterior produjo
un falso negativo Heir (`MaxLevel=0`): dentro de Linux, la ruta Windows por
defecto abrió una base vacía. Al montar el directorio padre y fijar la ruta V9
Linux, el mismo gate pasó 492/492; no hubo cambio de código para ocultarlo.

## Despliegue reproducible

- `.env` apunta a
  `D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-transversal-sorcery-v9.sqlite3`.
- El contenedor monta esa ruta read-only como `/app/Data/compact.sqlite3` y el
  SHA dentro del contenedor coincide con V9.
- Imagen desplegada: `sha256:36d1869f93706c3f135d0ad20e35bd468109377dc280090db57394e62b3c9e08`.
- Rollback conservado: `aaemu-game:rollback-pre-sorcery-v9-20260804`.
- Game abrió `2239/2250`, inició Network/StreamNetwork, se registró ante Login
  y completó `Server started` sin reinicio.

## Gate restante

No queda una frontera estática conocida de Sorcery. Queda ejecutar la matriz
V2 en el cliente para certificar las doce activas, los doce sucesores, las seis
pasivas, los retornos de Magic Circle, Insulating Lens bajo daño real, Fire
Wall: Mist y persistencia. Un
fallo visual o conductual reabre sólo la familia y el closure exactos que lo
produzcan; no autoriza importar balance 10.x.

La sesión siguiente queda instrumentada mediante `[AA8SorceryLive]`, el
resumidor determinista y el snapshot MySQL read-only descritos en
`CHECKPOINT_SORCERY_LIVE_TRACE_V1.md`. Esta traza separa explícitamente
lifecycle servidor de aceptación visual y no modifica gameplay.

La comprobación externa posterior está aislada en
`SORCERY_EXTERNAL_CORROBORATION_V1.md`: corrobora 42/43 IDs públicos, refuerza
que `15317` es un hijo interno de Meteor y no aporta propiedades promovibles.
