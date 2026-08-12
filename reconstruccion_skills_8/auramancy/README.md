# Auramancy AA8 — Runtime nativo V1

Estado: **candidato de Etapa 1 desplegado para aceptación viva**.

Este cierre reconstruye Auramancy para Kakao `8.0.3.12 r558734` sobre el
runtime validado de Sorcery, Archery, Battlerage y Shadowplay.

## Alcance materializado

- 25 raíces: 12 visibles y 13 ancestrales.
- Seis pasivas nativas: `13, 21, 98, 251, 252, 298`.
- Cero raíces en cuarentena.
- Teleportation `10152` recuperada como tombstone AA8 confirmado.
- Conversion Shield base y ancestrales habilitados mediante el consumidor
  acotado `DamagedSpell -> HealEffect fixed per-mille` probado por datos AA8.
- Ninguna rama custom por ID ni relación hipotética ejecutable.

## Descubrimientos nuevos

### Teleportation es una raíz AA8 tombstone

El resultado estático completo de `skills` no contiene `10152`, pero:

- el cliente vivo envía `CSLearnSkill(10152)`;
- la knowledge SQLite conserva nueve relaciones `client_native` confirmadas;
- AA8 aporta exactamente `skill_effects 273/20536`, `SpecialEffect 27`
  (`Blink 15m`), `DispelEffect 631`, seis tags, modifier `Buff 5319` y las
  ancestrales `39293/39294`;
- la localización AA8 confirma uso durante GCD, ausencia de GCD propio y
  bloqueo estando Snared.

Sólo la fila padre faltante usa el candidato estructural AA10 después del gate
del crosswalk (`aa10_only`, relación estable). Balance, relaciones y ejecución
permanecen gobernados por AA8.

### La cuarentena genérica de HealEffect era demasiado amplia

Conversion Shield no necesita reconstruir todas las semánticas de HealEffect.
Su cierre AA8 es estrecho y verificable:

- evento `9 = DamagedSpell`;
- `use_damage_amount=1`;
- valores fijos `170..333` en escala por mil;
- el handler aplica ese porcentaje al daño mágico recibido.

El runtime sólo promueve ese subconjunto y conserva fuera de alcance cualquier
otra variante HealEffect no probada.

## Artefactos

- Builder: `build_auramancy_native_v1_runtime.py`.
- Manifest: `generated/auramancy-native-v1.manifest.json`.
- Runtime: `compact-8.0-runtime-auramancy-v1.sqlite3`.
- SHA-256: `7F4D3038A03D82DEDF06DD9C5B232218ECCABB15A7137FAF586EFE3082E1469D`.
- Dos builds deterministas byte a byte.
- Tests estructurales: `6/6 PASS`.
- Suite .NET Core 3.1 con el compact Auramancy: `633/633 PASS`.
- Mechanics Lab: Teleportation, Vicious Implosion (contrato plot), Conversion
  Shield, Charge, Behind Enemy Lines Gale y Poisoned Weapons: PASS.

## Validación viva pendiente

La aceptación visual se ejecuta por lotes: doce bases, pasivas, variantes
ancestrales y una regresión final de las cuatro ramas ya cerradas. Un fallo
detiene el cierre; no se compensa con excepciones por skill.

## Corrección V2: preservación de campos del carrier

El primer candidato mezclaba la fila padre estructural de Teleportation `10152`
con 24 filas nativas AA8 en una misma llamada de upsert. Como la fila moderna
tenía columnas adicionales, el lote escribió `NULL` en 16 campos que sólo
existen en el esquema runtime para parte de las filas AA8. Entre ellos estaba
`need_learn`, por lo que el servidor rechazaba once habilidades visibles como
no aprendibles aunque el árbol y sus costes fueran correctos.

V2 separa ambos shapes: primero importa las 24 filas AA8 conservando los campos
del carrier Shadowplay V6 y después materializa aisladamente el padre tombstone.
Un gate nuevo exige `need_learn=1` en las doce raíces visibles y compara los 16
campos carrier-only de las 24 raíces AA8. Resultado: cero diferencias.

- Runtime V2: `compact-8.0-runtime-auramancy-v2.sqlite3`.
- SHA-256: `A47153649ABAFC3F8DE0397F5B6192AD0ADE885A1FE77615B5CA211B23BAD84E`.
- Manifest: `generated/auramancy-native-v2.manifest.json`.
- Tests estructurales: `7/7 PASS`.
