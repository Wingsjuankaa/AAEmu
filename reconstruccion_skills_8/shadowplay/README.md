# Reconstrucción nativa de Shadowplay AA8

## Estado actual: runtime V2

V2 conserva íntegro el contrato V1 y añade evidencia de aceptación obtenida
del cliente AA8 en ejecución. Los paquetes `CSLearnSkillPacket` demostraron
que el cliente solicita las IDs `10082`, `10104` y `10189`; por ello sus
raíces ausentes se materializan mediante un scaffold mínimo de la misma ID,
mientras que todas sus aplicaciones y cierres ejecutables proceden de la
SQLite forense AA8. La wiki continúa siendo sólo corroborativa.

`Poisoned Weapons` (`10481`) conserva el buff AA8 `22266` y ahora posee el
puente server-side mínimo hacia el payload Poison nativo
`196 → tick 56 → effect 791 → DamageEffect 210`. Sólo dispara con un impacto
Melee/Ranged de daño positivo y consume el buff preparatorio una vez.

Las seis pasivas no consumen puntos por contrato AA8: tienen
`skill_points=0` y se desbloquean por `req_points=3..8`, calculados a partir de
los puntos activos invertidos. El cuadro del cliente que muestra `Skill
Points: 0` para ellas es, por tanto, el comportamiento correcto.

Artefactos V2 principales:

- `build_shadowplay_specialization_v2_runtime.py`;
- `test_shadowplay_specialization_v2.py`;
- `shadowplay-live-observations-v2.json`;
- `generated/shadowplay-specialization-v2-runtime-manifest.json`;
- `generated/shadowplay-specialization-v2-test-report.json`;
- `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-shadowplay-v2.sqlite3`,
  SHA-256 `AD62A01CF762317CFF49624AB2191B2289B096004C48735B95A2A9156587E5F7`.

Dos construcciones independientes produjeron el mismo SHA-256. V2 ejecuta
los 252 casos originales sin fallos y añade 8 regresiones SQLite y 7 pruebas
.NET específicas.

Esta carpeta materializa la especialidad `ability_id=8` de Kakao 8.0.3.12
r558734 desde el contrato forense
`shadowplay-specialization-graph-v1.sqlite3`. La wiki no participa en ninguna
decisión runtime y sólo puede emplearse como corroboración externa.

## Contrato histórico V1

- Se conservan las 28 raíces AA8 del grafo y sus metadatos nativos.
- Las 27 raíces cuyo cierre está completo reciben sus relaciones ejecutables.
- `36594` permanece en cuarentena y sin `skill_effects`: su cierre alcanza
  `BubbleEffect 4766`, pero `BubbleEffect.Apply` todavía es un no-op y el corpus
  AA8 no prueba la semántica servidor/paquete necesaria.
- `10082` no se materializa como raíz: sólo existe como candidato de wiki y no
  pertenece al contrato nativo.
- Se incorporan las seis pasivas AA8 y sus tags nativos:
  `6→483`, `33→488`, `55→1548`, `259→7570`, `260→7572`, `302→863`.
- No se importan filas históricas de gameplay.

## Artefactos V1

| Artefacto | Estado |
|---|---|
| `build_shadowplay_specialization_v1_runtime.py` | Constructor determinista y verificador del cierre |
| `test_shadowplay_specialization_v1.py` | Ejecutor de los 252 `reconstruction_test_cases` |
| `generated/shadowplay-specialization-v1-runtime-manifest.json` | Manifiesto de fuentes, filas y digests consumidos |
| `generated/shadowplay-specialization-v1-test-report.json` | Resultado individual de cada caso |
| `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-shadowplay-v1.sqlite3` | Runtime, SHA-256 `647E0A65A447595CA547F352E9867869D0650C22B33F1B1207B113D1E34A3029` |

El grafo contractual consumido tiene SHA-256
`40B7BD4F82B0BA86A1E9FEB8CF6A436B94983634284D01C651FAB5C7C7358AE7`.
Dos construcciones independientes del runtime produjeron exactamente el mismo
SHA-256.

## Resultado de pruebas V1

Los 252 casos del grafo se ejecutan, uno por uno:

- 212 `passed`;
- 32 `not_applicable`, demostrados por ausencia de relaciones del tipo exigido;
- 8 `blocked_expected`, todos los casos confirmados de `36594`;
- 0 fallos, 0 errores y 0 casos omitidos.

Además pasan los 12 tests estructurales del catálogo común, el validador del
grafo (`28` raíces, `6` pasivas, cero filas sin clasificar), `quick_check`,
`integrity_check` y los 328 tests de `AAEmu.Tests` bajo .NET Core 3.1.

Los comandos exactos y la matriz por raíz se conservan en
`CHECKPOINT_SHADOWPLAY_NATIVE_RUNTIME_V1.md`.
