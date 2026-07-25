# B13 — Síntesis y awakening nativos AA8

Esta fase reconstruye el catálogo dirigido de armas Hiram y Erenor desde los
resultados nativos de `game11` y los layouts confirmados en `x2game.dll`.

## Decisiones de autoridad

- B12 se usa sólo como contenedor de los dominios ya restaurados.
- Todas las tablas de evolución se eliminan y se recrean con filas AA8.
- `item_rnd_attr_category_materials` se elimina: las 777 filas presentes en
  B12 son históricas y no existe un loader equivalente en el cliente AA8.
- La síntesis inicia la skill `30666`; usa el material como `SkillItem`, el
  equipo como `SkillCastItemTarget`, el objeto auxiliar de tipo `6` y la
  cantidad elegida en `SkillItem.Type2`.
- Los campos sin consumidor confirmado en `x2game.dll` permanecen bloqueados.

## Construcción B13a

```powershell
python .\build_native_evolution_runtime.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b12-socket-execution-v1.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b13a-evolution-catalog.sqlite3 `
  --manifest .\manifest-b13a.json
```

El generador realiza dos construcciones, exige SHA-256 idéntico, ejecuta
`quick_check` e `integrity_check` y rechaza referencias huérfanas.

## Resultado de síntesis B13b

La mutación usa `ItemTask` razón `100` y luego el paquete nativo AA8
`SCEvolvingResultPacket` (`0x0C6`). El cliente consume este segundo paquete
para presentar la XP base/bonus, el cambio de grado y mantener actualizado
Gear Upgrade.

Las probabilidades y rangos de bonus se expresan en milésimas. Esta escala
está confirmada por el consumidor `FUN_39301ec0` de `x2game.dll`; no procede
de la compact histórica.

## Construcción B13c

```powershell
python .\build_phase_b13c_runtime.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b13b-hiram-evolution.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b13c-hiram-erenor-evolution.sqlite3 `
  --manifest .\manifest-b13c.json
```

B13c incorpora sólo clausuras confirmadas por AA8:

- reroll aleatorio `32060 → 52963 → 21462/type 136`;
- reroll selectivo `46234 → 88704 → 56777/type 187`;
- descristalización `39040 → 70715 → 35710/type 156`.

El runtime generado activa el catálogo de armas Hiram y Erenor sobre el mismo
motor genérico. No introduce datos de evolución provenientes de 3.0.

## Construcción B13d: envoltorios de infusión Hiram

B13d restaura la diferencia nativa entre el objeto apilable sin identificar
y el material evolutivo resultante, no apilable:

| Envoltorio | Skill | Loot pack | Distribución | Resultado |
|---|---:|---:|---:|---|
| `45731` Unidentified Hiram Infusion | `39052` | `12470` | `17` | `48825`, Grand/Rare/Arcane |
| `46023` Mysterious Hiram Infusion | `39346` | `12532` | `23` | `48825`, Rare/Arcane/Heroic |
| `47052` Radiant Hiram Infusion | `40772` | `12759` | `47` | `48825`, Heroic/Unique/Celestial |

Las tres distribuciones se recuperaron de la tabla nativa
`item_grade_distributions` de `game11` y usan pesos `60/30/10`. Se importan
las 50 distribuciones AA8 completas, incluidos los grados `0..12`. El vínculo
entre cada loot pack y su distribución se registra como `server_derived`
porque no lo conserva la compact del cliente; se obtiene por correspondencia
única entre el rango visible nativo del envoltorio y las distribuciones
nativas de `game11`.

```powershell
python .\build_phase_b13d_runtime.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b13c-hiram-erenor-evolution.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b13d-hiram-infusion-wrappers.sqlite3 `
  --manifest .\manifest-b13d.json
```

El selector del backend consume el total real de pesos y usa intervalos
semiabiertos. Esto elimina el error histórico por el que una tirada `0`
podía seleccionar un grado con peso cero.

Runtime:

```text
compact-8.0-runtime-native-equipment-phase-b13d-hiram-infusion-wrappers.sqlite3
SHA-256 A1E8370FCA25502124CFFE0F383916BCCDFABBDD449F1477399282DC2442F245
```

Validación:

- dos builds deterministas;
- `quick_check = ok`;
- `integrity_check = ok`;
- 50 distribuciones AA8 con suma 100;
- clausura completa de 3 skills, 6 relaciones y 6 efectos;
- 175 pruebas automatizadas aprobadas en .NET Core 3.1;
- cero filas de gameplay tomadas de la compact 3.0.
