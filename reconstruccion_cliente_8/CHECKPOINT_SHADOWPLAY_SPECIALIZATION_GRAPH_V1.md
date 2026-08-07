# Checkpoint Shadowplay Specialization Graph V1

Estado: frontera forense cerrada y reproducible.

Autoridad: cliente Kakao `8.0.3.12 r558734`. La wiki ArcheRage se conserva
como corroboración visible separada. No se modificó AAEmu, ningún compact
runtime, `.env`, MySQL ni Docker.

## Alcance cerrado

- Framework reutilizable para las 14 especializaciones, resoluble por slug,
  nombre o `ability_id`.
- Piloto Shadowplay, `ability_id=8`.
- 28 skills raíz nativas, 9 visibles y 6 passive buffs.
- 31 páginas de skill wiki congeladas y 46 páginas de buff enlazadas.
- 2.928 entidades en clausuras por skill y 3.374 aristas dirigidas.
- 115 aplicaciones de efecto, 57 contratos de buff, 434 condiciones y 314
  outcomes de combo/plot/buff.
- 185 bindings de animación, controller, projectile, AOE, icono y FX.
- 252 casos de prueba: 220 `confirmed` y 32 `not_applicable`.
- Cero filas de clausura sin clasificar y cero entradas en `audit_queue`.

La raíz se deriva sólo de `skills.ability_id=8` y
`passive_buffs.ability_id=8`. El catálogo nativo transversal sólo selecciona
candidatos; cada fila se revalida contra Stage 50, incluida la identidad
compuesta de los effects concretos.

## Wiki y casos de control

`skill 10082` se conserva como `wiki_variant_candidate`, nunca como raíz
nativa. Sus ocho enlaces de rango se preservan como buffs tipados:

```text
599, 600, 601, 5278, 5279, 5280, 8224, 8225
```

Las otras candidatas exclusivamente wiki son `10104` y `10189`. Las 82
relaciones visibles conservan href, label, contexto y hash de respuesta:

- 23 `variant_buff`;
- 36 `visible_buff`;
- 23 `visible_npc`.

La wiki no crea membresía, combo ni relación gameplay nativa.

`skill 36594` permanece entre las 28 raíces. Su comparación downstream es
`quarantined` porque el `BubbleEffect.Apply` observado en el backend continúa
siendo no-op; este estado no altera la evidencia cliente. Las otras 27 skills
figuran `enabled` sólo dentro del namespace comparativo `server_observed`.

## Artefactos finales

```text
Shadowplay SQLite:
E:\AAEmu-Research\output\aa8-client-forensics\shadowplay-specialization-graph-v1.sqlite3
bytes: 3.997.696
SHA-256: 40B7BD4F82B0BA86A1E9FEB8CF6A436B94983634284D01C651FAB5C7C7358AE7

Shadowplay manifest:
SHA-256: 68DD97C381705F0AB2F7F42B83526500403ACA379FB0CFF0C2D0F5327DF449E9

Wiki snapshot manifest:
SHA-256: F9A94AF70B56A53D6A46939AA151B8E66ADD5F047DABB12BBAFF657EFD372706

Stage 70:
SHA-256: 8127A66A5F33AA8B9A13F97AA79C116E60ED89FD48FA6F1342FE788C92C400A9

Stage 90:
SHA-256: F9AE7DBA88C337DA2F5E21A13087F53F8FF0CB73F3678A2D73CAC3F98A9CBA87

Índice semántico lateral:
SHA-256: 983DC318292FF982BB118A209DE2D6E06B8234D30D56BFE49DFF6764F6F19682

Consolidada:
bytes: 8.906.633.216
SHA-256: 92CDF5D1EB16DAF0C4D5ABFCB80B510DFDF827708D4F8087235CCFACE3CE3C4F

Manifest global:
SHA-256: 5448E8DAFD6C1D6AB7573E514EE1499D2510CF224686635CE0C1AF6A6677EE0D
```

## Gates

- Dos builds de Stage 70: SHA idéntico `8127A66A...`.
- Dos builds de Stage 90: SHA idéntico `F9AE7DBA...`.
- Dos consolidaciones estrictas: SHA idéntico `92CDF5D1...`.
- Dos builds Shadowplay: SQLite y cinco derivados con hashes idénticos.
- `quick_check=ok` e `integrity_check=ok` en Shadowplay, Stage 70, Stage 90,
  sidecar y consolidada.
- 116/116 pruebas Python aprobadas.
- Cero referencias huérfanas en Stage 70/90, sidecar y consolidada.
- Cero relaciones consolidadas sin clasificar.
- Ocho de ocho validation events Shadowplay confirmados.

## Comandos reproducibles

```powershell
python -B -m client_forensics freeze-specialization-wiki shadowplay --resume
python -B -m client_forensics build-stage-70
python -B -m client_forensics build-stage-90
python -B -m client_forensics build-native-semantic-index --resume
python -B -m client_forensics consolidate
python -B -m client_forensics finalize
python -B -m client_forensics build-specialization-graph shadowplay
python -B -m client_forensics validate-specialization-graph shadowplay
```

## Continuación

El framework está listo para ejecutar otra especialización con los mismos tres
comandos públicos. La implementación runtime de Shadowplay debe realizarse en
otra tarea con `aaemu8-native-reconstruction`, usando el handoff V1 y sin
promover la wiki a autoridad.
