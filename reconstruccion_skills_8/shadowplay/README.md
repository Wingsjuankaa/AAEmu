# Reconstrucción nativa de Shadowplay AA8

## Estado actual: V6, Etapa 1 cerrada y validada en cliente

Shadowplay se reconstruye para Kakao `8.0.3.12 r558734` desde la knowledge
SQLite y Stage 15. El runtime final no hereda relaciones ejecutables V1/V2:
parte de la compact Battlerage V5 conocida como buena y reemplaza por cierre
exacto todas las particiones alcanzadas por el grafo V3 y corrige la partición
owner-keyed `unit_reqs` desde el stream AA8 completo.

Artefactos vigentes:

- `build_shadowplay_native_v3_runtime.py`: builder determinista;
- `test_shadowplay_native_v3.py`: integridad, cobertura y evidencia negativa;
- `generated/shadowplay-native-v6-runtime-manifest.json`: procedencia por fila
  y por relación owner-keyed;
- `CHECKPOINT_SHADOWPLAY_STAGE1_CLOSURE_V3.md`: resultado y despliegue;
- `MATRIZ_SHADOWPLAY_NATIVE_V3.md`: cobertura por familia;
- `SHADOWPLAY_DOSSIERS_V3.md`: relaciones y funciones reconstruidas;
- `compact-8.0-runtime-shadowplay-v6.sqlite3`:
  `01088F9835AFD9BA72E2A86504A63909F468154458D36DBAAB08164362C6BAD3`.

El artefacto materializa 31 raíces/etapas/variantes, seis pasivas y cero
raíces Shadowplay en cuarentena. `PRAGMA quick_check`, `integrity_check`, las
siete pruebas estructurales V6, 20 escenarios Mechanics Lab Shadowplay, 25
regresiones Battlerage, cuatro regresiones Archery y 633 pruebas .NET Core 3.1
están verdes.

V4 elimina el requisito histórico de arco de Poisoned Weapons `10481` y
recupera desde `game11` la alternativa nativa de rifle `value1=2` para
Stalker's Mark `12139`, conservando su alternativa de arco dentro del OR.

V5 recupera además seis `unit_reqs` owner-scoped de `PlotCondition` omitidos
en V4. En particular, la condición `9159` admite `TargetOwnerType`
Character/Npc/Mate y abre la rama `TeleportToUnit` de Shadowsmite Lightning
entre 4 y 6 m. El cierre V5 conserva 31 raíces, seis pasivas, cero cuarentenas,
20 escenarios Shadowplay, suites Battlerage/Archery y 633 pruebas .NET verdes.

V6 retira la hipótesis V5 `24093 → 40815`. AA8 materializa la identidad interna
`40815`, pero no contiene una relación ejecutable desde el coating Flame; el tag
378 compartido sólo significa "player skill". Iniciarla manualmente generaba
`SCUnitDamaged(skill=40815, TlId=0)` y el cliente cerraba la sesión al primer
golpe. Flame conserva exclusivamente `24093 → 24095 → 21999`: el coating
persiste para envenenar sucesivos objetivos golpeados durante 3 s, sin
propagación automática al morir ni daño auxiliar servidor.

## Autoridad

- AA8 r558734, la knowledge SQLite y Stage 15 son autoritativos.
- Las observaciones C2S son evidencia de identidad para los tombstones
  `10082`, `10104` y `10189`; cada campo materializado conserva procedencia.
- Modern sólo puede corroborar forma estructural.
- Las relaciones V1/V2 descartadas se conservan como evidencia negativa y no
  son entradas del runtime.

## Historial no promovible

V1 y V2 permanecen para auditoría. No deben usarse como carrier ni copiarse
aditivamente: contienen el scaffold antiguo, el trigger `88000001` y una
lectura incompleta de `BubbleEffect 4766`.
