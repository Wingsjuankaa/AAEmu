# Checkpoint — Shadowplay native runtime v1

## Alcance cerrado

Se leyó íntegramente `HANDOFF_SHADOWPLAY_SPECIALIZATION_GRAPH_V1.md` y se trató
la SQLite especializada como contrato forense. La cadena de autoridad fue:

1. grafo Shadowplay y catálogo nativo AA8;
2. corpus nativo/consumidores consolidados ya expresados por esos artefactos;
3. runtime portador sólo para esquema y dominios fuera del alcance;
4. wiki únicamente como corroboración, nunca como fuente de filas runtime.

No se usó fallback histórico de combate.

## Fuentes congeladas

| Fuente | SHA-256 |
|---|---|
| `shadowplay-specialization-graph-v1.sqlite3` | `40B7BD4F82B0BA86A1E9FEB8CF6A436B94983634284D01C651FAB5C7C7358AE7` |
| `native-combat-catalog-v1.json` | `83A03859A039A5D217D822B89D889D0CD124F8EC40BDC9C238EE3093F2AD3D66` |
| runtime portador `compact-8.0-runtime-nuia-story-v2-chapter11.sqlite3` | `E7A889EEE77E643C8F4EB51BF066DC192551C2F904ACEB78C9A59C2FA1F0DDDB` |
| runtime Shadowplay v1 | `647E0A65A447595CA547F352E9867869D0650C22B33F1B1207B113D1E34A3029` |

## Matriz raíz por raíz

Cada raíz tiene nueve casos contractuales.

| Skill | Resultado de sus 9 casos | Runtime |
|---:|---|---|
| 10481 | 8 pass, 1 N/A | enabled |
| 10496 | 8 pass, 1 N/A | enabled |
| 10648 | 8 pass, 1 N/A | enabled |
| 11418 | 7 pass, 2 N/A | enabled |
| 12029 | 8 pass, 1 N/A | enabled |
| 12049 | 8 pass, 1 N/A | enabled |
| 12139 | 8 pass, 1 N/A | enabled |
| 13344 | 8 pass, 1 N/A | enabled |
| 18125 | 9 pass | enabled |
| 18126 | 9 pass | enabled |
| 18127 | 9 pass | enabled |
| 19050 | 7 pass, 2 N/A | enabled |
| 19052 | 8 pass, 1 N/A | enabled |
| 19054 | 8 pass, 1 N/A | enabled |
| 23594 | 7 pass, 2 N/A | enabled |
| 36588 | 8 pass, 1 N/A | enabled |
| 36589 | 8 pass, 1 N/A | enabled |
| 36590 | 8 pass, 1 N/A | enabled |
| 36591 | 8 pass, 1 N/A | enabled |
| 36593 | 8 pass, 1 N/A | enabled |
| 36594 | 8 bloqueados esperados, 1 N/A | quarantined |
| 39297 | 7 pass, 2 N/A | enabled |
| 39298 | 7 pass, 2 N/A | enabled |
| 40787 | 8 pass, 1 N/A | enabled |
| 40788 | 8 pass, 1 N/A | enabled |
| 40815 | 6 pass, 3 N/A | enabled |
| 44288 | 8 pass, 1 N/A | enabled |
| 44289 | 8 pass, 1 N/A | enabled |

Totales exactos: `212 passed + 32 not_applicable + 8 blocked_expected = 252`.
El JSON de reporte conserva el resultado y la evidencia de cada fila de
`reconstruction_test_cases`.

## Pasivas materializadas

| Passive ID | Buff AA8 | Tagged buffs nativos alcanzados |
|---:|---:|---|
| 6 | 483 | 19563, 53749, 67360 |
| 33 | 488 | 19565, 53751, 67363 |
| 55 | 1548 | 531, 19702, 53782, 67361 |
| 259 | 7570 | 19903, 53809, 67359 |
| 260 | 7572 | 19905, 53810, 67358 |
| 302 | 863 | 19665, 53771, 67362 |

## Bloqueador preservado

`36594` es una raíz nativa real, pero su ruta alcanza `plot_effect 35005` y
`BubbleEffect 4766` (`kind_id=3`). El loader nativo demuestra los campos
`id`, `kind_id` y `speech`, pero no demuestra la conducta servidor ni el
paquete de burbuja. La implementación actual de `BubbleEffect.Apply` sólo
registra un trace. Por ello la raíz conserva metadatos AA8, queda marcada como
`quarantined` y no recibe relaciones ejecutables. Esto evita tanto inventar
semántica como caer silenciosamente a 3.0.

## Validaciones ejecutadas

```powershell
python -B -m client_forensics validate-specialization-graph shadowplay
python -B reconstruccion_skills_8\shadowplay\test_shadowplay_specialization_v1.py `
  --graph E:\AAEmu-Research\output\aa8-client-forensics\shadowplay-specialization-graph-v1.sqlite3 `
  --catalog reconstruccion_skills_8\native_combat\generated\native-combat-catalog-v1.json `
  --runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-shadowplay-v1.sqlite3 `
  --report reconstruccion_skills_8\shadowplay\generated\shadowplay-specialization-v1-test-report.json
python -B reconstruccion_skills_8\native_combat\test_native_combat_artifacts.py `
  --catalog reconstruccion_skills_8\native_combat\generated\native-combat-catalog-v1.json `
  --runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-shadowplay-v1.sqlite3 -v
docker run --rm -v "D:\Proyectos\AAemu\rama_8:/src" -w /src `
  mcr.microsoft.com/dotnet/sdk:3.1.409-focal bash -lc `
  "dotnet restore AAEmu.Tests/AAEmu.Tests.csproj && dotnet test AAEmu.Tests/AAEmu.Tests.csproj --no-restore --verbosity minimal"
```

Resultados: grafo `confirmed`; 5/5 tests especializados; 12/12 tests del
catálogo; 328/328 tests .NET; SQLite `quick_check=ok` e
`integrity_check=ok`; dos builds con hash binario idéntico.

## Despliegue local

Se actualizó únicamente `COMPACT_DB` y se reconstruyó/recreó el servicio
`game`; Login y MySQL no fueron recreados. La imagen resultante es
`sha256:07b5359459bda0efd0fc6626e703dd95e7d2a0e76ab7c178c3ce2a56e5803c5e`.
Dentro del contenedor, `/app/Data/compact.sqlite3` tiene el mismo SHA-256
`647E0A65A447595CA547F352E9867869D0650C22B33F1B1207B113D1E34A3029`.

El arranque terminó con `Application started`, listeners en `2239` y `2250`,
compilación dinámica de scripts con cero errores y registro de `GameServer 1`
en Login. La compact anterior permanece disponible y permite rollback mediante
el valor previo de `COMPACT_DB`.
