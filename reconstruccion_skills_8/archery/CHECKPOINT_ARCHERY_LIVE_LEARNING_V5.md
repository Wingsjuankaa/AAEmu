# Checkpoint Archery A0: aprendizaje vivo V5

Fecha: 2026-08-07
Cliente: ArcheAge Kakao 8.0.3.12 r558734
Runtime: `compact-8.0-runtime-archery-v4.sqlite3`

## Resultado

El personaje `Dannia` reinicio el set y aprendio las doce activas visibles de
Archery. Entre `21:19:03Z` y `21:19:15Z` el servidor recibio doce
`CSLearnSkillPacket` y respondio doce `SCSkillLearnedPacket`. No se ejecuto
ninguna activa durante esta ventana.

Luego se aprendieron las seis pasivas AA8 correctas:

| Passive | Buff | Resultado inmediato |
|---:|---:|---|
| 7 | 486 | `move: 1.00 -> 1.08` |
| 35 | 888 | sin delta inmediato; contrato condicionado al disparo |
| 2 | 480 | sin delta inmediato; contrato condicionado a distancia |
| 256 | 7565 | sin delta inmediato; contrato condicionado a critico/Feral Mark |
| 300 | 889 | `endlessDamage: 100 -> 110` |
| 255 | 7564 | `rangedCritical: 20.4352 -> 29.4352`, multiplicador 90 |

Cada pasiva produjo el par instrumentado `before_apply/after_apply`. La
ausencia de delta inmediato en 888, 480 y 7565 no es fallo: sus consumidores
se validan en A2/A3 al ejecutar disparos, variar distancia y provocar criticos.

El usuario confirmo que el aprendizaje persiste tras reloguear y solicito no
repetir esa comprobacion. La ejecucion individual de las activas y variantes
sigue pendiente; ninguna fila de la matriz se promueve por el aprendizaje.

## Evidencia

- captura local:
  `runtime-captures/native-skill-live-archery-learning-v1.json`;
- SHA-256 JSON:
  `C2AC131A35E2AD496267C509F1DAE78801A937D6CFC53C01EEC2A90D56C283D5`;
- SHA-256 CSV:
  `03710B80A4B03BD134280DD8AD5E5B92D8FFEFEE8DA0840D30C021D792A275C6`;
- 12 snapshots pasivos, seis transiciones y cero lineas de error;
- `RestartCount=0` y Game activo.

## Siguiente gate

Comenzar A3 con Endless Arrows base `14835` a 12-15 m, mantener tres
segundos y soltar. Exigir la cadena interna `14836/14837`, dano ranged,
finalizacion al soltar y ausencia de impactos tardios. Las pruebas de menos de
8 m y sin arco se ejecutan por separado.
