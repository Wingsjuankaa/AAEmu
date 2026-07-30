# Checkpoint: observación controlada y conocimiento transversal de quests V1

Fecha: 2026-07-30
Cliente: ArcheAge Kakao `8.0.3.12 r558734`
Rama: `client_version/8.0.3.12-kakao-r558734-port`

## Resultado

El catálogo estricto V2 está desplegado en `game`:

```text
quest_contexts activos                       561
catálogo nativo clasificado                7.826
native_safe + validated_override             561
cuarentena recuperable                     7.265
SHA-256 del compact
D8FBD65AC8906ACC876D31A10F31293CA4A8E1DD40BF3712FF2DFBEC696A2744
```

Las quests activas de MySQL cuya plantilla quedó en cuarentena no se eliminan.
El cargador las omite en memoria y conserva sus filas para una recuperación
posterior.

Antes del despliegue se creó el respaldo:

```text
D:\Proyectos\AAemu\backups\quest-observer-v1\
  aaemu8-before-quest-observer-20260730-120749.sql.gz

SHA-256
96624E24550EF52E664AF30B5C9656CCDB98D5909FA3A1AF7AC0083D47ADEF04
```

## Recorder runtime

`AA8ObservationService` sólo captura durante una sesión GM explícita. Sin una
sesión activa no copia buffers de red, no calcula hashes de paquetes y no
agrega filas de observación.

El almacenamiento es una SQLite separada:

```text
host:
D:\Proyectos\AAemu\client_kakao\runtime_observations\
  aa8-runtime-observations.sqlite3

contenedor:
/app/Observations/aa8-runtime-observations.sqlite3
```

El escritor usa una cola acotada no bloqueante, un único consumidor, WAL,
`synchronous=NORMAL`, transacciones por lote y barreras de flush para stop,
disconnect y apagado.

Tablas V1:

```text
observation_sessions
observation_interactions
observation_events
observation_packets
observation_snapshots
```

Cada interacción puede registrar:

```text
expected -> attempted -> blocked/executed -> client_seen -> persisted
```

Los paquetes correlacionados guardan opcode, nivel, dirección, tamaño y
SHA-256. No se conserva el payload de paquetes conocidos. Un opcode desconocido
puede guardar como máximo los primeros 256 bytes en hexadecimal.

## Comando GM y punto de parada

```text
/aa8observe start <etiqueta>
/aa8observe status
/aa8observe mark <ok|fail> <nota>
/aa8observe continue [nota]
/aa8observe stop [nota]
/aa8observe resume <session-id>
```

La primera mutación de quest se ejecuta y cierra la compuerta. Toda mutación
posterior queda bloqueada hasta `continue`. Movimiento, chat e inspección no se
bloquean.

Primer test manual autorizado:

1. entrar con un personaje GM y usar `/aa8observe start supply-item-smoke`;
2. aceptar **una sola** quest natural;
3. detenerse sin avanzar otro objetivo;
4. usar `/aa8observe mark ok|fail <observación>`;
5. usar `/aa8observe stop first-accept`;
6. cerrar limpiamente el cliente antes de analizar.

No usar `/quest force` como aceptación.

## Analizador transversal

Builder:

```text
reconstruccion_npcs_quests_8/build_runtime_quest_knowledge.py
```

Uso:

```powershell
python reconstruccion_npcs_quests_8\build_runtime_quest_knowledge.py `
  --observations <aa8-runtime-observations.sqlite3> `
  --compact <compact-v2.sqlite3> `
  --forensic-graph <aa8-client-knowledge.sqlite> `
  --output <directorio>
```

El juego debe estar detenido o la SQLite debe tener WAL vacío. El analizador
falla cerrado si hay un WAL pendiente.

Outputs:

```text
aa8-runtime-knowledge-v1.sqlite3
aa8-runtime-knowledge-v1-manifest.json
aa8-runtime-knowledge-v1-summary.json
aa8-runtime-knowledge-v1-report.md
```

La primera ejecución real, todavía sin sesiones GM, clasificó correctamente:

```text
eventos observados                          0
familias derivadas                          0
quests del catálogo                     7.826
relaciones nativas quest-act-item        6.192
SHA-256 knowledge SQLite
1E9CCF4EA640EF8C113EED4B8C7BFD6FAE37E18A3CDB8EEE6AB1F9DDB389618D
```

Dos builds consecutivos fueron idénticos. Las relaciones item se reconstruyen
desde filas `confirmed` de `native_rows`:

```text
quest_components
-> quest_acts
-> quest_act_supply_items /
   quest_act_supply_selective_items
-> item_id
```

El resultado distingue `client_native`, `observed_runtime_only` y
`visible_corroboration_only`. Nunca modifica el compact, el grafo forense, la
cobertura de items ni el servidor.

## Validación

```text
catálogo/analyzer Python                   9/9
suite completa AAEmu.Tests              284/284
build AAEmu.Game .NET Core 3.1                ok
observation SQLite quick_check                ok
scripts runtime                                0 errores
puertos Game/Stream                         2239/2250
LoginServer registrado                         sí
compact montado con SHA esperado                sí
```

El runtime inicial sin sesión contiene cero sessions, interactions, events,
packets y snapshots, confirmando que la captura es opt-in.

## Frontera de autoridad

Una observación puede priorizar o proponer una reparación, pero no habilita
contenido. Toda promoción debe:

1. cerrar la relación nativa AA8;
2. implementar una primitiva genérica;
3. reconstruir dos runtimes idénticos;
4. pasar auditorías y pruebas;
5. validarse con una interacción real y relog.
