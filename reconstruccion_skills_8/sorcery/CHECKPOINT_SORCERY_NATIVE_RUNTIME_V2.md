# Checkpoint Sorcery native runtime v2

## Resultado

Esta reconstrucción recupera dos roots activos que el cliente Kakao AA8
solicitó aprender y que el servidor rechazaba por ausencia de plantilla:

- `10151`, Freezing Earth: `CSLearnSkill` observado y rechazado a las
  `2026-08-03T03:13:26-04:00`;
- `10153`, Insulating Lens: `CSLearnSkill` observado y rechazado a las
  `2026-08-03T03:13:25-04:00`.

La observación viva prueba identidad y alcanzabilidad AA8, aunque ambos roots
aparezcan como tombstones en la extracción estática. No prueba por sí sola sus
propiedades de balance.

## Autoridad y cierre

- Los roots `10151/10153` se toman como candidatos de la SQLite 10.x r575. El
  crosswalk los clasifica `aa10_only`; por eso no se presentan como filas AA8
  exactas y quedan sujetos al gate manual.
- Todos los descendientes ejecutables se reponen desde la base consolidada
  AA8: `skill_effects`, descriptores, daño, buffs y el plot `3096`.
- Los cinco descriptores enlazados (`233, 234, 56762, 68337, 87343`) son
  `exact_id_exact_relation` en el crosswalk AA8→10.x.
- No se preserva ningún valor histórico 3.x en las filas reemplazadas.

Freezing Earth queda enlazado a efectos `271, 272, 44888` y a los ocho eventos
AA8 del plot `3096`. Insulating Lens queda enlazado a `53089, 65323`, al
descriptor `ExtendChargeEffect 1` y al buff de absorción AA8 `95`.

## Backend reconstruido

`ExtendChargeEffect` ahora dispone de modelo, loader y un cálculo candidato de
carga. La implementación consume los flags AA8 de valor fijo, nivel, DPS,
armas, porcentaje y salud actual, y entrega la carga calculada al sistema de
absorción existente del buff. Modern y 10.x sólo contienen un `Apply` TODO, por
lo que la fórmula no se considera nativa confirmada hasta cerrar el gate vivo.

Las filas nativas del recurso Sorcery también quedan materializadas:
`combat_resources.id=8` y `combat_resource_groups.id=7`. Esto no habilita un
paquete de sincronización: el opcode/layout AA8 exacto aún no está demostrado y
permanece bloqueado expresamente. No se portó el paquete Modern/10.x.

## Artefactos

- Constructor: `build_sorcery_specialization_v2_runtime.py`.
- Evidencia viva y `game11`: `sorcery-runtime-evidence-v2.json`.
- Runtime: `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v2.sqlite3`.
- SHA-256 runtime: `8D98CE42BC8A8835D012F1FE867D4B19CAF7795C6DB508B6EAF99AC421C173F5`.
- Manifiesto: `generated/sorcery-specialization-v2.manifest.json`.
- SHA-256 manifiesto: `2932DDFE013B577FE23DC89297AEDC78A409D2C1CF09012BCE4697F006A1761D`.

El runtime pasó `quick_check=ok` e `integrity_check=ok`. El catálogo de combate
fue regenerado desde `game11`, y los grafos Sorcery/Swiftblade fueron
reconstruidos y validados contra su nueva identidad en vez de editar hashes.

Despliegue confirmado el 2026-08-04 (America/Santiago):

- imagen activa `sha256:8bbaacec710c1c5faab2356936d9d4f953bd5dfd6050e418ec7d24284f96a72d`;
- rollback `aaemu-game:rollback-pre-sorcery-v2-20260804`, imagen
  `sha256:b9b57c48c2d5b49021ba8985d100eef2ff5dc7391f50e7687941b09222db3a40`;
- sólo se recreó `aaemu8-game-1`; Login y MySQL conservaron sus contenedores;
- la compact v2 quedó montada en `/app/Data/compact.sqlite3`;
- scripts: 0 errores y 8 warnings históricos;
- `GameNetwork` 2239, `StreamNetwork` 2250 y registro en Login confirmados;
- 0 reinicios y ninguna excepción fatal de arranque;
- suite C# completa: 371/371; pruebas estructurales Sorcery: 6/6;
  artefactos nativos: 12/12; grafos de control: 5/5.

## Límites y gate manual

Fire Rain `11939` y sus variantes `36477, 36478, 39674` continúan en
cuarentena por `ResetAoeDiminishingEffect`; este lote no inventa ese estado
backend.

Después del despliegue se debe probar, en sesión limpia y de uno en uno:

1. aprender `10151` y `10153` sin `Rejected unknown skill`;
2. lanzar Freezing Earth y verificar start/fire/end, AoE, daño/buffs y cooldown;
3. lanzar Insulating Lens y verificar buff `95`, absorción y cooldown de 30 s
   al finalizar;
4. salir y volver a entrar para confirmar persistencia;
5. confirmar que no se publica aún una barra/recurso mediante un paquete no
   demostrado.

La aceptación viva es obligatoria antes de declarar correctos los valores
candidatos de los roots, promover la fórmula de `ExtendChargeEffect` o
continuar con Fire Rain.
