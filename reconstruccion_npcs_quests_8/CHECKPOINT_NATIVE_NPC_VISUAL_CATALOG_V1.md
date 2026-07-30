# Checkpoint: catálogo visual nativo de NPC AA8 v1

Fecha: 2026-07-30
Cliente: ArcheAge Kakao `8.0.3.12 r558734`

## Resultado

Se reconstruyó el cierre de presentación de los NPC que ya existen en el
runtime sin promover objetos para gameplay de jugador:

```text
NPC
-> model
-> ActorModel / PrefabModel / VehicleModel
-> total_character_custom
-> rostro, cabello y piezas corporales
-> equip_pack_cloths / equip_pack_weapons
-> item_armors / item_weapons
-> item_armor_assets / item_assets
```

El runtime candidato es:

```text
D:\Proyectos\AAemu\client_kakao\
compact-8.0-runtime-native-npc-visual-v1.sqlite3

SHA-256
A97D4162020F02AA579D2F95AA41B02F90302EC708E3ADD30A0156467281F5F7
```

Dos builds independientes desde la misma base produjeron el mismo archivo,
con el mismo tamaño `140525568` y el mismo SHA-256.

## Evidencia usada

Raíz de control:

```text
npc:3597 (Lucius)
dossier profile=generic
forensic readiness=profile_complete
reconstruction readiness=runtime_audit_required
JSON SHA-256
ECCC638F6DC1042F3ACD764729B8B1B4D0B326DB04F5A0DF38DB8AFB4285E319
```

SQLite consolidada:

```text
E:\AAEmu-Research\output\aa8-client-forensics\
aa8-client-knowledge.sqlite

SHA-256
807BDABAC73BEDE4D5477BDF6A953C709B8D7007BAFB5286EB3C36575D9D36EC
```

SQLite forense de items:

```text
E:\AAEmu-Research\output\aa8-item-forensics\
aa8-item-forensics.sqlite

SHA-256
36C2A49F90E1B4CE0C1BD3B83A0D6A0261E6222F8A093BEE5087F55DBA3293B8
```

Runtime base:

```text
compact-8.0-runtime-native-nuian-green-arc-v5.sqlite3
SHA-256
11E4D8FD9D28DBA23E25934A5A27CCAD7E4CE4C7B15DF3EEE09C0797622D953B
```

## Diagnóstico probado

El problema visible no procedía sólo de NPC o modelos ausentes.

```text
NPC nativos ya presentes en runtime             14921
modelos usados                                   940
ActorModels usados                               895
total_character_customs nativos                 1546
packs de ropa usados                            1686
packs de armas usados                            480
```

Los packs alcanzables referencian:

```text
armaduras/ropa distintas                        1552
armas distintas                                  448
piezas corporales reales                         717
total IDs visuales                              2717
```

Todas esas referencias tienen descriptor nativo confirmado. El runtime base
sólo contenía una fracción de los descriptores y, cuando existía la fila,
`ItemManager.Create` rechazaba casi todos los candidatos por la cobertura
funcional de gameplay. `NpcManager` terminaba serializando slots vacíos.

Además, `NpcManager` cargaba el `grade_id` de cada pack pero lo descartaba al
crear el equipo.

## Implementación

### Catálogo de presentación aislado

El builder crea:

```text
aaemu_npc_visual_items
```

Contiene exactamente `2717` IDs con descriptor nativo. La fila centinela
`item_id=0` de `item_body_parts` se conserva fuera del catálogo de objetos:

```text
armor      1552
weapon      448
body_part   717
```

`ItemManager.CreateNpcVisual` puede crear esos objetos únicamente para
presentación NPC. No cambia:

- `items`;
- `aaemu_item_definition_coverage`;
- inventario de jugador;
- ItemTask;
- loot, craft o recompensas;
- persistencia o equipamiento de personajes.

El digest canónico de `items` y el de
`aaemu_item_definition_coverage` son idénticos antes y después del build.

### Proyección NPC acotada

Para los `14921` NPC ya existentes se actualizaron sólo:

```text
model_id
equip_cloths_id
equip_weapons_id
total_custom_id
char_race_id
scale
opacity
```

Todos los demás campos de esos NPC permanecen idénticos a la base. Los modelos,
ActorModels, customs, packs y descriptores alcanzables se reemplazaron por sus
filas AA8 exactas.

`Race.None` ya no recibe por error una customización Nuian aleatoria.
Customs sin nombre no sobrescriben el nombre localizado del NPC y el loader
acepta el `NULL` nativo como ausencia de override.

### Grados de equipo

Cada slot usa ahora el `*_grade_id` exacto del pack nativo, incluida ropa,
armas, cosplay y stabilizer.

## Frontera preservada

Los archivos históricos de mundo contienen `285` template IDs con fila NPC
AA8 positiva que no están en el runtime base. No se habilitaron:

```text
37 requieren npc_ai_params ausentes
14 requieren npc_interaction_sets ausentes
```

La SQLite consolidada todavía no contiene esos catálogos. Insertar los NPC
habría creado actores alcanzables con comportamiento parcial.

Otros `46` IDs de spawn no existen ni en el runtime ni en el catálogo positivo
Kakao AA8. Tampoco se sintetizaron. Ambos conjuntos exactos están registrados
en el manifest como evidencia negativa/bloqueo de una fase posterior.

## Validación automática

Auditorías SQLite:

```text
quick_check                                      ok
integrity_check                                  ok
target_npc_missing_model                          0
target_npc_missing_total_custom                   0
target_npc_missing_cloth_pack                     0
target_npc_missing_weapon_pack                    0
target_model_missing_actor_model                  0
visual_item_missing_descriptor                    0
```

Regresiones:

```text
tests Python del dominio NPC/quests              52/52
test C# dirigido                                  2/2
suite AAEmu.Tests .NET Core 3.1 Docker          274/274
```

Advertencias de restore `NU1701` para `Ionic.Zlib` y `JitterPhysics` siguen
siendo las advertencias históricas; no aparecieron errores de compilación.

## Despliegue verificado

Se reconstruyó y recreó exclusivamente el servicio `game` con la imagen:

```text
aaemu-game:0.0.2.0-alpha
image sha256
d5ebb6b5f57e1c58dcaf2f8ec3d897a9d7d0dd3ca3cc370c78a6e9f83ea09176
```

Verificación activa:

```text
compact montado SHA-256                         A97D4162020F02AA579D2F95AA41B02F90302EC708E3ADD30A0156467281F5F7
IDs visuales AA8 cargados                       2717
plantillas NPC cargadas                        15688
scripts compilados                         0 errores
puerto game                                     2239
puerto stream                                   2250
reinicios del contenedor                           0
Login                                      GameServer 1 registrado
```

El arranque deja en cuarentena cuatro piezas (`31573`–`31576`) usadas sólo
por el NPC legado `16829`. Ni ese NPC ni esas piezas tienen entidad positiva
en los catálogos Kakao consultados; no se promovieron como autoridad AA8.

## Archivos reproducibles

```text
build_native_npc_visual_catalog_runtime.py
test_native_npc_visual_catalog.py
generated\native-npc-visual-v1-runtime-manifest.json
generated\native-npc-visual-v1-runtime-verify-manifest.json
AAEmu.Tests\NpcVisualItemCatalogServiceTests.cs
```

## Aceptación manual pendiente

Después de desplegar sólo `game`, cerrar y abrir el cliente y comprobar:

1. Lucius `3597`: rostro, cabello, ropa/cosplay y tocado conocidos.
2. Un NPC humano con ropa por piezas: cabeza, pecho, pantalón, guantes y
   zapatos.
3. Un NPC con arma principal y secundaria.
4. Un NPC con `total_custom_id=0` y raza real, para verificar la custom
   determinista.
5. Un NPC no humano con `char_race_id=0`, que debe conservar su modelo Skin y
   no recibir una cara Nuian.
6. Alejarse hasta descargar la entidad, volver, cambiar de zona y reloguear.

La fase no se considera aceptada visualmente hasta completar esa prueba dentro
del cliente.
