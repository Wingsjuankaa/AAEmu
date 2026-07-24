# Fase B3 — Síntesis, atributos aleatorios y awakening AA8

Este catálogo se construye exclusivamente desde resultados SQLite nativos
recuperados de `game11` y layouts confirmados en `x2game.dll`.

Incluye:

- categorías, niveles y propiedades de síntesis;
- grupos y valores de modificadores aleatorios;
- materiales evolutivos;
- grupos y mapeos de awakening/cambio de objeto.

El artefacto es deliberadamente **sólo catálogo**. No habilita mutaciones:
todavía deben confirmarse byte a byte los paquetes, consumos, resultados,
fallos y bonus de AA8. Las referencias a objetos ausentes del subconjunto de
objetos de Fase A quedan registradas como cobertura incompleta; no se sustituyen
por datos 3.0.

Uso:

```powershell
python .\extract_native_synthesis.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b2-temper-v1.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b3-synthesis-v1.sqlite3 `
  --manifest .\manifest.json
```
