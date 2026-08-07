# Checkpoint — Point 0 Shoot Rifle stack V1

Fecha: 2026-07-31  
Autoridad: ArcheAge Kakao 8.0.3.12 r558734  
Estado: reemplazado por V2 después de un retest fallido.

## Fallo reparado

La skill básica `Shoot Rifle` (`46938`) estaba presente, pero define
`plot_only=1` y su plot nativo `5796` no existía en el runtime aceptado P0-A.
Como consecuencia, el servidor no tenía ningún evento que ejecutar.

Se incorporó exclusivamente su clausura AA8 nativa:

- 1 plot y 16 eventos;
- 15 transiciones y 17 efectos;
- 9 condiciones y 5 formas AoE;
- 3 efectos de daño a distancia de multiplicador `0.6`;
- 13 efectos especiales;
- animación `1074` y proyectil `1347`.

No se usó ningún dato histórico 3.0 ni se modificaron otros dominios del
runtime.

## Artefactos

- Dossier: `skill-46938.json`, SHA-256
  `D4F2864A52CD42BCE51A6AAB9A928702A50904DE98047A6D5DD0E0C40A9515FB`.
- Catálogo: `native-basic-rifle-v1.json`, SHA-256
  `DFD8602EBCE097D2A50E50A963F1F0031AC4BBB87326D2EEF8AAE0C515777A73`.
- Runtime: `compact-8.0-runtime-point0-rifle-stack-v1.sqlite3`, SHA-256
  `503BF9639F2005130C9E63A66A443AEA09577C082D7CE8EDC8AB11DA9118B77A`.
- Base preservada: `compact-8.0-runtime-point0-repair-stack-v1.sqlite3`,
  SHA-256
  `444C9A2586468C049C4B68B480724D0D3222F9A1E8091951F520033AA39935DF`.

El catálogo y el runtime se generaron dos veces; ambos conservaron exactamente
el mismo SHA-256.

## Validaciones automatizadas

- `PRAGMA quick_check`: `ok`.
- `PRAGMA integrity_check`: `ok`.
- Pruebas focalizadas Python: 4/4 aprobadas.
- Suite completa .NET en SDK 3.1.409-focal: 305/305 aprobadas.
- Runtime montado dentro del contenedor: SHA-256 confirmado
  `503BF9639F2005130C9E63A66A443AEA09577C082D7CE8EDC8AB11DA9118B77A`.

## Despliegue

Sólo se recreó `aaemu8-game-1`; `db` y `login` permanecieron activos.

- `main_world heightmap loaded` confirmado.
- `Loaded 54/55 heightmaps` confirmado.
- Puertos 2239 y 2250 escuchando.
- `Server started` confirmado.
- Registro en LoginServer confirmado.

Durante la carga paralela inicial apareció una vez el error preexistente de
enumeración de `TransferManager.GetTransfers`; el servidor siguió operativo y
no se repitieron errores, excepciones ni fatales después de finalizar el
arranque. No pertenece a la clausura de Shoot Rifle.

## Próxima prueba manual aislada

Con `Dannia` y un rifle equipado, seleccionar un único mob a no más de 15 m y
hacer un solo clic en `Shoot Rifle`. Registrar por separado:

1. si reproduce la animación de disparo;
2. si aparece el proyectil/impacto;
3. si baja la vida y aparece daño una sola vez.

La repetición manteniendo pulsado y el ataque a varios blancos se probarán como
transiciones separadas después de validar el disparo único.

## Resultado del retest

`Dannia` envió correctamente `CSStartSkill 46938`, pero cada ejecución terminó
inmediatamente con `SCPlotEnded`. La barrera posterior estaba en el evaluador
backend de `WeaponEquipStatus=5`, no en la clausura SQLite. Continuación:
`CHECKPOINT_POINT0_RIFLE_STACK_V2.md`.
