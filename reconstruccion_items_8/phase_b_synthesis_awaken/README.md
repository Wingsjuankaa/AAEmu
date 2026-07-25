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
