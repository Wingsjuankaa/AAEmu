# Fase B14 — Explorer → Hiram T1 nativo AA8

Esta fase parte del runtime B13d y añade exclusivamente el cierre dirigido
confirmado por el cliente Kakao 8.0.3.12: equipo Explorer/Radiant/Brilliant,
grupos de awakening 48–50, infusiones y wrappers de historia, cofres,
vendedores y las recompensas/tutoriales necesarios para llegar a Hiram T1.

El generador no importa gameplay 3.0. Los únicos enlaces derivados del
servidor se registran en el manifiesto: contenido de `loots` (tabla ausente
del cliente) y la caja ranged `51185`, cuyo `skill_id` colisiona pero cuya
descripción AA8 y categoría nativa 638 cierran de forma única arco y rifle.

```powershell
python .\build_phase_b14_runtime.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b13d-hiram-infusion-wrappers.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b14-explorer-hiram-t1.sqlite3 `
  --manifest .\manifest-b14.json
```

El proceso construye dos copias, exige SHA-256 idéntico, ejecuta
`quick_check`/`integrity_check` y valida cantidades, referencias, stocks y
recompensas antes de publicar el artefacto.
