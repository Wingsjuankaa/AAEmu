# Checkpoint Battlerage V2 — candidato desplegado

Fecha: 9 de agosto de 2026.

## Baseline preservado

- Rama: `client_version/8.0.3.12-kakao-r558734-port`.
- Checkpoint previo: commit `835b42e1`.
- Rollback Docker: `aaemu-game:rollback-pre-aa8-battlerage-v2-20260808`.
- Sorcery, Archery, Mechanics Lab y muerte de NPC permanecen como regresiones
  obligatorias.

## Evidencia y construcción

- Grafo forense Battlerage: SHA-256
  `54736AFC8CDC453C84FFA4C8337C76894FA86D78155E714B1B121B5B640589B5`.
- Crosswalk AA8→10.x consultado obligatoriamente: SHA-256
  `44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71`.
- El crosswalk redujo opacidad de identidad/relación, pero no promovió datos:
  `aa10_runtime_rows=0`.
- Clausura nativa: 42 skills, 37 raíces/variantes jugables, 3 automáticas,
  2 internas obsoletas, 6 pasivas, 115 skill effects, 18 plots y 64 buffs.
- Único controller ausente: `604`, exclusivo de la skill obsoleta oculta
  `11854`; no bloquea contenido jugable.

Constructor reproducible:

```text
reconstruccion_skills_8/battlerage/build_battlerage_runtime_v2.py
```

Compact resultante:

```text
D:/Proyectos/AAemu/client_kakao/compact-8.0-runtime-battlerage-v2.sqlite3
SHA-256 54DD8C77556A35C3EECE4009A6FC713179F72054DD4E50A6DBA08B74533ABF3A
size 141148160
quick_check ok
integrity_check ok
```

La copia de verificación produjo exactamente el mismo SHA-256.

## Verificación

- Mechanics Lab Battlerage: `24/24 PASS`.
- Segunda corrida: `24/24` hashes de resultado idénticos.
- Regresiones Archery/muerte: `4/4 PASS`.
- Suite .NET Core 3.1 con esta compact montada: `600/600 PASS`.
- Tests estructurales V2: `9/9 PASS`.
- Tests Phase 4: `6/6 PASS`.
- Certificación determinista versionada: SHA-256
  `C4A5DC628D1645915C0CDC730DC33FA112F958CA54AA04AB45E2428F12B22693`.

Los resultados están en:

```text
runtime-captures/mechanics-lab/battlerage-v2-final/certified-a
runtime-captures/mechanics-lab/battlerage-v2-final/certified-b
runtime-captures/mechanics-lab/battlerage-v2-final/archery-regression
```

El resumen auditable y reproducible está en
`generated/battlerage-v2-mechanics-certification.json`; las capturas completas
permanecen fuera de Git.

## Despliegue

- Imagen: `aaemu-game:0.0.2.0-alpha`.
- Imagen SHA: `sha256:a924aa6d623c5e4837b6821e9b34dc2c0ca528b54163463f291610f022f4d8db`.
- DLL desplegada SHA-256:
  `A2EDD98315960F7AD02D388BA1F9D1A96F9924CF9175308FABA82A3367E2A7D6`.
- Compact dentro del contenedor: SHA esperado `54DD8C...ABF3A`.
- Puertos `2239` y `2250`: accesibles.
- Scripts: `0 errors`, 8 warnings heredados.
- LoginServer: `Registered GameServer 1`.
- Sólo se recreó `aaemu8-game-1`; Login y MySQL conservaron sus IDs.

## Estado

El candidato está listo para validación con el cliente AA8. No se declara
Battlerage cerrado hasta completar el barrido vivo indicado en
`MATRIZ_BATTLERAGE.md`.
