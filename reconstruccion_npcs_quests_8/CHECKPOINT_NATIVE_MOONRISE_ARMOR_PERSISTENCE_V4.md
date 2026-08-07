# Checkpoint — cajas Moonrise y persistencia directa V4

Fecha local: 2026-07-31  
Autoridad: ArcheAge Kakao 8.0.3.12 r558734

## Fallos demostrados

Las cajas de armadura `47982–47984` conservaban cobertura
`phase_a_candidate` y no tenían en el runtime sus aplicaciones de efecto,
detalles `GainLootPackItemEffect` ni los loot packs del servidor. La caja
Leather `47983` no podía abrirse.

El intercambio `48507 -> 48845` sí se ejecutaba correctamente en memoria. Un
relog rápido volvía a presentar ese estado porque `ItemManager` es global al
proceso, pero `Character.SaveDirectlyToDatabase`, usado en desconexión, sólo
guardaba el personaje. MySQL continuó temporalmente con `48507 x2` y sin
`48845`; el autosave posterior terminó persistiendo `48507 x1 + 48845 x1`.
Por tanto, el fallo era una descarga inmediata ausente, no una pérdida ni una
relación nativa incorrecta.

## Cierre AA8 reconstruido

```text
47982 Moonrise Cloth Armor Crate
  skill 42225 -> effect 78589 -> detail 4215 -> loot pack 12950
  48015, 48016, 48017, 48019 x1

47983 Moonrise Leather Armor Crate
  skill 42227 -> effect 78591 -> detail 4217 -> loot pack 12952
  48022, 48023, 48024, 48026 x1

47984 Moonrise Plate Armor Crate
  skill 42229 -> effect 78593 -> detail 4219 -> loot pack 12954
  48029, 48030, 48031, 48033 x1

48507 Unidentified Story Quest Infusion: Rank 1
  skill reagent 43013: 48507 x1
  skill product 43013: 48845 x1
```

Las doce filas `loots` son `server_derived`: la tabla no existe en el cliente,
pero las descripciones AA8 enumeran exhaustivamente cuatro resultados por
caja. No se habilitó ningún dato de gameplay 3.0.

`Character.SaveDirectlyToDatabase` ahora llama a `ItemManager.Save` antes de
guardar el personaje y confirma ambas mutaciones dentro de la misma
transacción MySQL.

## Evidencia

```text
client compact
sha256=4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57

game11
sha256=E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031

item-47982.json
sha256=FBF297FB764CD259708FB1FD74823427D263DAC6546FE623E3C7D66E1C8CE1B6

item-47983.json
sha256=AAE7FB7ABEEA8A6486A21260F4821588954E440F862E98E002A88BEEA55C36D2

item-47984.json
sha256=525A9E96C411E79C0E2E5B76AD780DF287E0FC45607ECBE9123BE1FBE4E8A062
```

Las páginas `https://wiki.archerage.to/na-en/db/items/{id}` para `47982`,
`47983`, `47984` y `48507` se usaron sólo como corroboración visible.

## Artefactos y validación

```text
compact-8.0-runtime-point0-moonrise-armor-persistence-v4.sqlite3
sha256=84A2E6AF2B890A3FE066129F80F041DDE2FF6B071B151AD0D05E2FB509073E0F
bytes=140046336

dos builds deterministas: hash idéntico
quick_check=ok
integrity_check=ok
orphan_loot_items=0
regresiones Python del stack=33/33
suite AAEmu.Tests .NET Core 3.1=311/311
ScriptCompiler=0 errores, 8 advertencias históricas
git diff --check=ok
```

Builder:
`build_native_moonrise_armor_persistence_v4_runtime.py`

Regresión:
`test_native_moonrise_armor_persistence_v4.py`

Manifiesto:
`generated/native-moonrise-armor-persistence-v4-runtime-manifest.json`

Backup MySQL previo:

```text
D:\Proyectos\AAemu\backups\moonrise-armor-persistence-v4-20260731-2247\mysql-all.sql
sha256=52E48690BB93A168A2A1A3C8805E54B26FD81B3D64B4F7E6CEDDE7051BDDD774
```

Despliegue:

```text
servicio recreado: game solamente
imagen game=sha256:452c36400804508a2bc7ba41a43dec94ef9d622aaefff979bda6d6b5c371a8f6
compact montado sha256=84A2E6AF2B890A3FE066129F80F041DDE2FF6B071B151AD0D05E2FB509073E0F
restart_count=0
Game 2239 y Stream 2250 escuchando
registro en LoginServer exitoso
tiempo de arranque=00:01:49.4795068
```

## Estado persistido previo a aceptación manual

```text
Dannia id=1
47983 x1, grade 0, Inventory slot 10
48507 x1, grade 2, Inventory slot 12
48845 x1, grade 2, Inventory slot 9
sin resultados 48022, 48023, 48024 ni 48026
```

## Aceptación manual controlada

1. Abrir únicamente la última `48507`.
2. Salir inmediatamente a selección de personaje y volver a entrar, sin
   esperar el autosave.
3. Verificar en MySQL `48507 1 -> 0` y `48845 1 -> 2`.
4. Sólo entonces abrir `47983`, detenerse y comprobar exactamente
   `48022`, `48023`, `48024`, `48026` antes de otro relog.

Estado: `desplegado`; aceptación manual V4 pendiente por etapas.
