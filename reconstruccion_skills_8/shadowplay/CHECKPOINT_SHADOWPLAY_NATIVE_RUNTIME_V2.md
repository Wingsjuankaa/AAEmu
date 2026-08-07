# Checkpoint — Shadowplay native runtime V2

## Resultado

Shadowplay V2 corrige los dos defectos runtime observados y documenta el caso
de las pasivas:

- `10082`, `10104` y `10189` ya existen como skills aprendibles de
  `ability_id=8`, cuestan un punto activo y conservan las aplicaciones de
  efecto exactas recuperadas de AA8.
- `10481` aplica el buff preparatorio `22266`; el primer impacto Melee/Ranged
  con daño positivo aplica Poison `196` al objetivo y consume el preparatorio.
- Las pasivas conservan `skill_points=0` y `req_points=3..8`. No gastar puntos
  al adquirirlas es el contrato AA8, no un error contable.

## Autoridad y excepción mínima

La autoridad runtime sigue siendo la SQLite forense de Kakao 8.0.3.12
r558734. La evidencia en vivo procede de paquetes y logs del mismo cliente.
La wiki sólo corrobora nombres o presentación.

Las raíces de `10082`, `10104` y `10189` están ausentes del resultado positivo
completo de `skills`, pero sobreviven sus relaciones nativas y el cliente AA8
envía esas IDs exactas al servidor. Se materializó únicamente el scaffold de
raíz de la misma ID desde la compact histórica; `10104` sólo cambia
`ability_id` a `8`. Sus `skill_effects`, `effects`, `buff_effects`,
`special_effects` y buffs son filas AA8 exactas de los dossiers congelados.

Poisoned Weapons conserva exacta la fila nativa de buff `22266`. AA8 omite su
trigger server-side, aunque conserva el tag familiar `3567`, el texto de
“next successful Melee or Ranged attack”, y todo el payload Poison nativo. El
puente reservado `buff_trigger 88000001` resuelve:

`22266 → effect 720 → BuffEffect 256 → buff 196 → tick 56 → effect 791 → DamageEffect 210`

Sólo `effect 720` y `BuffEffect 256` son scaffold mínimo de enlace de la misma
identidad histórica; `buff 196`, el tick, el efecto de daño y sus tags son
filas AA8 nativas.

## Artefactos y digests

| Artefacto | SHA-256 |
|---|---|
| Runtime V2 | `AD62A01CF762317CFF49624AB2191B2289B096004C48735B95A2A9156587E5F7` |
| Manifest V2 | `D81385BE13CAE6C993207DADB1D44FB2A0ECE50809133255EEFDEF578FCD4FB8` |
| Reporte V2 | `4E859C8D1C5DE4A7FD5DD762C898BFE49AB4D170AE9E8C35FA09D4EA8F35BA4C` |
| Dossier 10082 | `9A641DF00571E413AD49F606BD888EE5EE7C6727954FFBDC5BB3EE26EA50909F` |
| Dossier 10104 | `AE5DEF418465D6A8594681B30CC6B2960041ABC16EF543590E1536E776444EAC` |
| Dossier 10189 | `6C839F21A5C176982F91CCC99CF2AC3DB054EE82B6F618BDF45B629B3348FD76` |

Dos builds independientes del runtime produjeron exactamente el SHA-256
`AD62A01...E5F7`.

## Validación

- 252/252 filas de `reconstruction_test_cases` ejecutadas:
  `212 passed`, `32 not_applicable`, `8 blocked_expected` y cero fallos.
- 8/8 regresiones V2 SQLite.
- 7/7 tests .NET de clasificación del impacto Poisoned Weapons.
- 12/12 tests estructurales del catálogo nativo y 337/337 tests .NET del
  proyecto completo.
- `PRAGMA quick_check=ok` e `integrity_check=ok`.
- `10104` alcanza cuatro `SpecialEffect` con `special_effect_type_id=16`
  (`BuffSteal`).
- La segunda generación binaria es idéntica a la primera.

## Despliegue

`.env` apunta a `compact-8.0-runtime-shadowplay-v2.sqlite3`. Sólo se reconstruyó
y recreó `game`; MySQL y Login permanecieron activos. El contenedor monta la
SQLite en modo read-only y su `/app/Data/compact.sqlite3` reporta el mismo hash
`AD62A01CF762317CFF49624AB2191B2289B096004C48735B95A2A9156587E5F7`.
La imagen desplegada es
`sha256:0dba9b75fb682ad64390f88439ceb410f118e1151ebf5140ebacecdd9b0c0d3c`.

Rollback: restaurar `COMPACT_DB` a
`compact-8.0-runtime-shadowplay-v1.sqlite3` y recrear únicamente `game`.
