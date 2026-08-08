# Checkpoint Archery Deadeye Multiple Stack V7

Fecha: 2026-08-07
Cliente: ArcheAge Kakao 8.0.3.12 r558734
Rama: `client_version/8.0.3.12-kakao-r558734-port`
Runtime: `compact-8.0-runtime-archery-v5.sqlite3` (sin cambios de datos)

## Sintoma

Deadeye `15073` retiraba correctamente el icono y el bonus al dejar de
moverse, pero el efecto visual rosa/verde permanecia unido al personaje. El
relogueo ocultaba el residuo, confirmando una desincronizacion de presentacion
y no un buff servidor aun activo.

## Cadena AA8

- `skill 15073 -> effect 12118 -> buff_effect 3886 -> buff 27702`;
- el tick `87300 -> buff_effect 35385 -> buff 27705` detecta movimiento;
- `effect 87301 -> buff_effect 35386 -> buff 27704` crea las cargas;
- `buff 27704`: `StackRule.Multiple`, `max_stack=10`, duracion indefinida,
  `fx_group_id=1140`, requiere `27702`;
- al quedar quieto, el timeout de `27705` ejecuta el dispel por tag y retira
  hasta diez instancias de `27704`.

El dossier forense `skill-15073.json` quedo `profile_complete`, sin frontera
dura. El crosswalk clasifica skill/buffs por ID estable, los efectos y
`buff_effects` como `exact_id_exact_relation`, y conserva las relaciones de
esta cadena. No se importaron propiedades ni balance r575.

## Hipotesis V7 y resultado vivo

`Buffs.AddBuff` habia perdido el caso explicito
`BuffStackRule.Multiple` introducido historicamente por AAEmu en `a676144c`.
Por ello todas las instancias independientes se enviaban con `stack=1`. La
restauracion era necesaria y la prueba viva confirmo que las altas pasaron a
profundidades 1..N. Sin embargo, la aceptacion del 2026-08-07 falsifico que
este defecto explicara por si solo el residuo visual: todos los indices de
`27704` fueron retirados y el FX rosa/verde siguio visible.

AA8 x2game.dll `FUN_399aa9a0` confirma que `SCBuffUpdated` transporta
`buffId/index`, `stack`, `charged`, `elapsedTime` y `reason`; el alta AA8 ya
serializa `Buff.Stack`. Esta reparacion corrige la identidad Multiple, pero no
cierra el incidente visual. La continuacion autoritativa queda en V8.

## Reparacion

- `Buffs.AddBuff`: restaura profundidad 1..N para instancias Multiple antes
  de `SCBuffCreatedPacket`;
- `SCBuffRemovedPacket.Verbose`: registra `owner/index` para observar la
  retirada;
- `BuffMultipleStackTests`: prueba que tres instancias se publiquen como
  stacks 1, 2 y 3 y mantengan tres indices/instancias servidor.

## Gate vivo

1. activar Deadeye;
2. moverse hasta acumular varias cargas;
3. quedarse quieto hasta que desaparezca el icono;
4. confirmar que desaparecen tambien el FX rosa/verde y el bonus, sin
   relogueo;
5. verificar en log stacks 1..N, retiros por indices distintos, cero errores
   y `RestartCount=0`.

## Verificacion y despliegue

- prueba focal `BuffMultipleStackTests`: 1/1;
- suite completa SDK .NET 3.1.409: 568/568;
- build Docker Game: correcto;
- solo Game fue recreado; Login y MySQL conservaron sus contenedores;
- contenedor Game:
  `eb0c1eb06391b1955348f1f35545ac90e13e40ecac18879501099081e5507ff5`;
- `RestartCount=0`, puertos `2239/2250` activos;
- compact montada SHA-256:
  `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`;
- scripts: cero errores de compilacion;
- `Server started!` y registro exitoso en Login.

Estado: contrato Multiple confirmado, pero candidata visual rechazada por
prueba viva. Sustituida por
`CHECKPOINT_ARCHERY_DEADEYE_BUFF_REMOVED_REASON_V8.md`.
