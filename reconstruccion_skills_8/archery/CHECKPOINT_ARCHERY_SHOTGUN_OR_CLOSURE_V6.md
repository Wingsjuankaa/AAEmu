# Checkpoint Archery shotgun OR closure V6

Fecha: 2026-08-07
Cliente: ArcheAge Kakao 8.0.3.12 r558734
Runtime: `compact-8.0-runtime-archery-v5.sqlite3`

## Resultado

El barrido vivo de Archery con el rifle AA8 `item 50799`, equipado en el slot
ranged 17 y con `holdable_id=31`, rechazo todas las activas ranged antes de
crear timeline. Las trazas registraron `UrkEquipRanged` (`result=95`), por lo
que no habia animacion, consumo, plot ni dano. El texto rojo "No corpses
nearby" observado con Missile Rain era la presentacion cliente de ese mismo
rechazo, no una relacion de corpse reagent en la skill.

La causa fue una frontera de string cache en `unit_reqs`. El decoder comenzaba
su captura en la referencia 69882; 4.405 filas conservaban el owner como
`<ref:69872>`. Para nueve skills Archery esas filas son las alternativas
`equip_ranged kind 29/value1 2` que autorizan shotgun/rifle dentro de un grupo
`or_unit_reqs=true`. El runtime V4 solo tenia `value1 0` (bow).

## Evidencia y crosswalk

- fuente AA8: `game11`, SHA-256
  `E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031`;
- cached result `unit_reqs`: offsets `0x828B2C..0x87EC3C`, 13.053 filas;
- owner reference recuperada: `69872 -> Skill`;
- r575 identifica 4.383/4.405 claves naturales exactas de esa referencia como
  `Skill`; las nueve filas Archery coinciden campo por campo;
- corroboracion AA8 independiente: owners presentes en `skills`,
  `or_unit_reqs=true`, animaciones `shot_gun_*` y holdable 31;
- el raw r575 se consulta solo como candidato estructural, SHA-256
  `87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F`;
- filas r575 materializadas: **cero**.

Las alternativas AA8 recuperadas pertenecen a `11933, 13281, 14835, 14836,
14837, 15073, 15096, 16210, 23592`. Los requisitos de arco existentes se
conservan; el evaluador OR acepta cualquiera de los dos holdables y sigue
rechazando un slot ranged vacio.

## Artefactos

- decoder: `shared_primitives/extract_native_unit_requirements.py`;
- constructor: `archery/build_archery_runtime_v1.py`;
- runtime: `D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-archery-v5.sqlite3`;
- bytes: 141.082.624;
- SHA-256 runtime:
  `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`;
- manifiesto: `generated/archery-runtime-v5.manifest.json`;
- SHA-256 manifiesto:
  `B084A6AABF143A26D6E5F48FF1157A955AA465405B967A0EC5FFB9993EF0B191`;
- auditoria semantica: 35/35 roots, cero blockers;
- filas materializadas por la capa: 5.043;
- `quick_check=ok`, `integrity_check=ok`.

Dos builds limpios produjeron el mismo SHA-256. Al eliminar solo el path de
destino, sus manifiestos tambien son identicos con hash semantico
`5794720F05857DCEA198640611A6D098DB48B78A20B7E9155A2A3B2DDA0B40C8`.

## Verificacion automatica

- extractor AA8: 2/2;
- runtime Archery: 16/16;
- auditor ejecutable: 35/35 roots, cero blockers;
- Sorcery heredado: 4/4;
- documentacion: 4/4;
- suite completa AAEmu SDK 3.1.409: 567/567.

## Gate vivo

Endless Arrows queda `live_accepted_with_rifle` en V5. La ejecucion controlada
del 2026-08-07 produjo la cadena interna `14835 -> 14836/14837`, 16 timelines
aceptados, 13 impactos autoritativos, consumo de MP y HP decreciente. No
aparecio `UrkEquipRanged`; los rechazos intermedios fueron exclusivamente
`CooldownTime` durante la repeticion sostenida.

Artefactos locales de evidencia:

- `runtime-captures/archery-endless-arrows-rifle-v6.json`, SHA-256
  `7A183F7056D47C7F23BB5002E3218029A8DBFEC973221DA3A4513B3DB4F510A8`;
- `runtime-captures/archery-endless-arrows-rifle-v6.csv`, SHA-256
  `C3E588565222A84F9B7BDDC5986180E1ED06F39D7CEA299A0B92A5E1A689DA5F`;
- 174 eventos parseados, 18 grupos de ejecucion, 13 con dano autoritativo y
  cero lineas de error.

La matriz viva puede continuar una skill por vez con Charged Bolt.

## Barrido transversal posterior

El usuario ejecuto las 12 activas base con el rifle AA8. La traza agrupada
registra 92 ejecuciones, 1.187 eventos parseados, 65 ejecuciones con dano
autoritativo, cero lineas de error y `RestartCount=0`. Todas las activas base
aparecen aceptadas; las ofensivas reducen HP y las habilidades sin dano
completan su timeline. No reaparece `UrkEquipRanged`.

- `runtime-captures/archery-transversal-rifle-v6.json`, SHA-256
  `347DA027B88536CBFD521EF3C51346E161B22004F4A1C51210D6C23DEC223FA2`;
- `runtime-captures/archery-transversal-rifle-v6.csv`, SHA-256
  `9DEE6869D66785DEC81530EF7247DCE7977D9A63F121222F6D78CE2D690188F2`.

Este barrido cierra la frontera transversal de requisito ranged y ejecucion
base. No sustituye los gates de efectos secundarios, pasivas ni variantes
ancestrales.

## Despliegue de prueba

La V5 fue montada recreando exclusivamente Game; Login y MySQL conservaron
sus contenedores y datos. Evidencia del arranque:

- Game: `e665c40cab909f32c483f0b6440c312084071cc4c6852be761c1cbe9d42d6a56`;
- `RestartCount=0`;
- runtime montado SHA-256:
  `4AA3CD82175C7DE10A64D29E4C184782A5AECDD34E2D81CCFE6DE624AA29F7E2`;
- `Loaded 6700 skill unit requirements (841 supported AA8 kinds 29/30)`;
- scripts: cero errores de compilacion;
- listeners activos: `2239` y `2250`;
- Game registrado con exito en Login;
- arranque completo: `Server started!`.
