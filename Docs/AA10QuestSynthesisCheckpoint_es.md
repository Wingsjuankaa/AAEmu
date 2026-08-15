# Checkpoint AA10 — síntesis de equipamiento de misión

Fecha: 2026-08-15

## Alcance

Reconstrucción del efecto de síntesis (`ItemEvolving`, efecto especial 123, skill 30666) para el
cliente ArcheAge Returns 10.0.2.13 r575. El objetivo inmediato es que Gear Upgrade acepte las
infusiones de misión, cobre la moneda configurada, consuma exactamente los materiales elegidos y
persista/represente el EXP y el cambio de grado.

Awakening se reconstruyó después y tiene su checkpoint separado en
`Docs/AA10QuestAwakeningCheckpoint_es.md`.

## Autoridades y procedencia

- Target local: `Wingsjuankaa/AAEmu:rama_10`, base `aae593ef6874b2bde5cc1b3fa0d2a0f67c9e6bf0`.
- Padre obligatorio: `AAEmu/AAEmu:client_version/zone-10.0.2_r575`, consultado en
  `a3c735c658ebe20d10cb50684b4b3e366b7d87e1`.
- Comparador comunitario: PR `AAEmu/AAEmu#1531`, commit
  `e092f1fd28c578ff00534cb8ec2c9ac639856f4e`. El PR estaba cerrado y no fusionado. Se reutilizaron
  el cierre de protocolo/datos r575 y se corrigieron sus objeciones de revisión: selección estricta,
  consumo exacto prevalidado, reembolso si el inventario queda obsoleto, RNG calculable y pruebas de
  negocio.
- Comparador AA8: `rama_8/reconstruccion_items_8/phase_b_synthesis_awaken/CHECKPOINT_B13.md` y su
  `ItemSynthesisService`. Se reutilizó la semántica demostrada de bonus en permille y la disciplina de
  preview/transacción; no se copiaron valores de grados AA8.
- Datos activos r575: `.server_files/AAEmu.Game/Data/compact.sqlite3`. Después del parche reproducible
  de caps Hiram su SHA-256 es
  `DF10A47C10D65D6AE64187BE37FE1708646EF5CED284E46ADA3016E112957E0A`.

## Contrato r575 fijado

- Skill object 8: `u16 byteLength`, hasta seis `u64 materialItemId`, `bool autoUseAaPoint`.
- Los payloads con longitud parcial o más de seis slots se consumen completos para no desalinear el
  paquete, pero el efecto los rechaza sin mutar estado.
- `itemEvolving` debe estar habilitado tanto en el archivo versionado como en el override montado por
  Docker: `.server_files/AAEmu.Game/Configurations/Features.json`.
- El target debe ser equipo del personaje; todos los materiales deben ser únicos, existir en la bolsa,
  no ser el target y pertenecer a un grupo de categoría aceptado por el target.
- La progresión usa `item_grades.grade_order`, no el id numérico del grado. Crude (id 1) está antes de
  Basic (id 0).
- `bonus_exp_chance`, `bonus_exp_min` y `bonus_exp_max` son permille; el bonus es un porcentaje del EXP
  aportado, no una cantidad absoluta.
- La petición se rechaza completa si un slot es inválido. El consumo de todos los stacks se preflighta
  antes de cambiar el primero y se publica como una única tarea de inventario.

## Caso de regresión de misión

- Target 48023: categoría de síntesis 651.
- Infusión de rango 1, 48845: categoría 672, grupo de material aceptado, `gain_exp = 50`.
- Valores de categoría 651 en AA10: Basic 12 EXP, Grand 17 EXP, Rare 23 EXP.
- El equipamiento de misión probado nace Grand, no Basic. Resultado observado y fijado desde Grand
  con 0 EXP: Arcane (grade id 4), 10 EXP restante.
- Diferencia deliberada: AA8 resolvía el caso equivalente como Arcane/1. Los valores AA8 no son
  autoridad para r575.

## Validación automatizada

Comando:

```powershell
dotnet test --project AAEmu.UnitTests --configuration Release --no-restore
```

Resultado combinado tras añadir awakening: 1252 correctas, 0 errores, 0 omitidas. Incluye captura real de CSStartSkill, round-trip de
seis slots, rechazo de longitudes malformadas/sobredimensionadas, progresión r575, overflow, bonus en
permille y feature gate `itemEvolving`.

## Prueba manual mínima tras desplegar

1. Entrar con un equipo de misión Grand sin EXP y una sola infusión 48845.
2. Abrir Bag → Gear Upgrade → Synthesis.
3. Colocar el target y exactamente una infusión; confirmar una sola vez.
4. Verificar que desaparece una unidad de la infusión, se aplica el costo mostrado y el resultado queda
   en Arcane con 10 EXP.
5. Reloguear y comprobar que grado/EXP persisten antes de probar múltiples infusiones o awakening.

## Corrección de sincronización multi-material — 2026-08-15

Prueba real: al sintetizar con cuatro infusiones situadas en cuatro slots, World otorgó la EXP de las
cuatro y el estado persistido descontó las cuatro, pero la bolsa sólo mostró un descuento inmediato.
Tras relog aparecieron los tres consumos restantes. Esto demuestra una divergencia de presentación,
no una duplicación de EXP ni un fallo de persistencia.

La causa fue el lote r575: la transacción atómica emitía varios `ItemCountUpdate`, implementados como
`Take` (acción 6, cuerpo completo y variable), dentro del mismo `SCItemTaskSuccessPacket`. El cliente
aplicó sólo el primer cuerpo del lote. No se portó `AddStack` desde AA8 porque su layout/delta no es
compatible con AA10 y ya se había demostrado que el cliente r575 ignora el decremento.

La corrección conserva el commit atómico del servidor, pero publica cada stack confirmado en su propio
`SCItemTaskSuccessPacket`. Las eliminaciones llevan su `forceRemove` únicamente en el paquete de ese
item. La misma primitiva cubre síntesis y awakening con reactivos repartidos entre varios stacks.

Prueba manual de cierre:

1. Usar exactamente cuatro infusiones desde cuatro slots sobre un equipo que aún pueda recibir EXP.
2. Confirmar una sola vez.
3. Verificar sin relog que los cuatro stacks bajan una unidad, o desaparecen si tenían una sola.
4. Confirmar que el resultado suma exactamente cuatro aportes de EXP.
5. Reloguear y verificar que los conteos no cambian nuevamente.

## Change Attempts y preservación de efectos — 2026-08-15

La prueba real con el rifle de misión mostró dos divergencias adicionales:

- el preview Rare → Unique calculó `0 + 3/5` Change Attempts, pero el resultado permaneció en cero;
- cada cambio de grado volvía a sortear todas las líneas de Synthesis Effects en vez de conservar las
  existentes y añadir únicamente los slots desbloqueados.

La primera causa estaba cerrada por el propio contrato r575. `EquipItem.EvolveChance` es el contador
persistido y `SCItemEvolvingResultPacket` contiene `addChance`; el runtime no modificaba el primero y
siempre enviaba cero en el segundo. Ahora cada ascenso efectivo en `grade_order` concede un intento,
con el máximo de cinco mostrado por el cliente. Rare → Unique concede exactamente tres. El detalle y
el resultado se emiten con el mismo valor.

La segunda causa era el uso de `RollRndAttrGroups` sobre el item completo. Ahora el resolver valida y
preserva los grupos existentes, respeta la cuota `pick_num` de cada set, evita atributos duplicados y
sortea sólo las líneas que faltan hasta `max_unit_modifier_num`. El paquete resultado enumera sólo las
líneas recién añadidas.

Validación automatizada combinada: 1260 pruebas correctas, 0 errores. Incluye tope `3/5`, wire exacto
de `addChance=3`, preservación de una línea y adición exclusiva de la siguiente.

La primera cadena manual completa posterior al despliegue confirmó el contador: el item `16777240`
recibió `+3`, luego `+1`, luego `+1` hasta el máximo de cinco; una promoción posterior anunció `+0=5`.
MySQL persistió `EvolveChance=5`. El detalle completo de rutas y efectos quedó registrado en
`Docs/AA10QuestAwakeningCheckpoint_es.md`.

El cierre integrado y el mapa completo de archivos están en
`Docs/AA10GearUpgradeReconstruction_es.md`.
