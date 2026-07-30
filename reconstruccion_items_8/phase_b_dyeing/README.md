# AA8 native dyeing — B15

> Superseded forensic experiment. Do not build or deploy this runtime from the
> client-decoding workflow. Preserve extracted rows, layouts and relations as
> evidence for `aa8-client-forensics`; server implementation belongs to a
> separate future process.

This phase closes the Kakao 8.0 dyeing path without importing historical
`item_dyeings` or `dyeing_colors`.

Build the isolated candidate from the active validated runtime:

```powershell
python .\reconstruccion_items_8\phase_b_dyeing\build_native_dyeing_runtime.py `
  --game11 E:\AAEmu-Research\output\compact-8.0-extracted\game11 `
  --client-compact D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-nuian-green-arc-v5.sqlite3 `
  --forensics-dir E:\AAEmu-Research\output\aa8-item-forensics `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-nuian-green-arc-v6-dyeing.sqlite3 `
  --manifest .\reconstruccion_items_8\phase_b_dyeing\manifest-b15.json
```

The builder:

- imports all 292 native `dyeable_items(item_id,color)` rows;
- marks the 26 dye consumables, wrapper 45632 and ticket 48965 as
  review-only `phase_a_candidate` closure members;
- restores skills `39137`, `43874`, and `22727` dependency closure;
- adds the two server-derived loot bindings explicitly identified in the
  manifest;
- drops the incompatible historical 3.0 dyeing tables;
- builds twice and rejects differing hashes, integrity failures, or orphan
  dependencies.

The candidate remains non-deployable until manual client acceptance is
completed.
