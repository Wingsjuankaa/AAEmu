# Checkpoint B10 — contexto nativo de Lunascale/Lunagem AA8

## Diagnóstico cerrado

La prueba anterior mezclaba la inserción de socket con el uso ordinario del
reactivo. El cliente AA8 distingue ambos casos mediante el contexto de
`CSStartSkill`:

- clic derecho sobre Lunascale: skill `37186`, objetivo normal, desarma la
  pieza y entrega 3000 honor;
- Gear Upgrade > Lunagem > Equip: el mismo skill sobre un objetivo de objeto
  con `SkillObject` tipo `10`, instala la gema;
- el tipo `11` transporta índice y operación global para cambios/retiros.

La compact 3.0 no participó en el diagnóstico ni en el runtime.

## Cambios

- Se implementaron los layouts AA8:
  - tipo `10`: `bool autoUseAaPoint`, `uint count`, `bool continuous`;
  - tipo `11`: `uint index`, `bool isAll`.
- `Skill.ApplyEffects` reconoce el contexto nativo de instalación y lo separa
  de la acción de desarme.
- La instalación garantizada admite la cantidad solicitada, valida capacidad,
  reactivos y costo completo antes de mutar, consume las Lunascales y actualiza
  inmediatamente el equipo.
- El generador incorpora la clausura nativa de desarme de la skill `37186`,
  conservando el comportamiento AA8 de clic derecho.

## Runtime

```text
compact-8.0-runtime-native-equipment-phase-b10-socket-context-v1.sqlite3
SHA-256 AD485098675808EFD9E26AEB78F777A52E927B67A357F65F7BDA96059ADEC762
```

Validación:

- `PRAGMA quick_check`: `ok`
- `PRAGMA integrity_check`: `ok`
- dos construcciones deterministas: mismo SHA-256
- `skill_effects`: relación `51508`
- `effects`: efecto `65940`
- `special_effects`: acción `30634 / GiveHonorPoint(3000)`

## Prueba recomendada

Usar un equipo permanente AA8, no el objeto temporal `38244`:

```text
/additem 45633 1
/additem 39064 7
```

Luego:

1. abrir Gear Upgrade;
2. entrar en Lunagem > Equip;
3. colocar `45633` como equipo;
4. colocar `39064` en el recuadro Lunagem;
5. confirmar una inserción;
6. repetir o seleccionar una cantidad mayor;
7. verificar que el socket, el consumo y el costo se actualicen sin relog.

El clic derecho sobre `39064` prueba la ruta distinta de desarme por honor.
