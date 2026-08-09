# Checkpoint de baseline para Battlerage V2

Fecha local: 2026-08-08

Este checkpoint congela el runtime aprobado antes de reconstruir Battlerage.
La autoridad activa es AA8 y el port desplegado en `rama_8`; Modern sólo puede
usarse como comparador selectivo.

## Código y pruebas

- Rama: `client_version/8.0.3.12-kakao-r558734-port`.
- HEAD previo al commit de checkpoint: `1758760b`.
- Suite ejecutada dentro de .NET Core SDK 3.1.409: `595/595` aprobadas.
- Árbol funcional preservado: Sorcery, Archery, Mechanics Lab y cierre de
  muerte de NPC sin desconexión.

## Runtime aprobado

- Compact montada: `compact-8.0-runtime-archery-v5.sqlite3`.
- SHA-256 compact host/mount:
  `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`.
- Imagen Game activa:
  `sha256:850817a6fe0961e8fe2a18005eb5694e7e68a6af012a091e8a9c853d491ee073`.
- SHA-256 `AAEmu.Game.dll` desplegada:
  `F326F33D1332338B5D55AC7BDA05BF0A93AA6B28FE3B6E72643BA6A65BDE781A`.
- Puertos: Login `2237`, Game `2239`, Stream `2250`.

La compact Battlerage V2 deberá derivarse de esta Archery V5. El artefacto
histórico `compact-8.0-runtime-phase4-battlerage-v1.sqlite3` no es una base de
runtime válida para este ciclo.

## Exclusiones del checkpoint

No se versionan `.env`, compacts, capturas de runtime, binarios, `bin/obj`,
logs, secretos ni configuraciones locales del IDE. Los slots adicionales, la
actualización de .NET y otros árboles de especialización quedan fuera del
cierre Battlerage.
