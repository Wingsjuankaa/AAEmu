# Reactivación aditiva de acciones del inventario AA10 r575

Fecha del corte: 2026-08-19.

## Resultado

La fila de utilidades observada en ArcheRage se reactiva mediante los feature
bits nativos de Returns `10.0.2.13 r575`. No se reemplaza el controlador del
inventario, no se copia bytecode de ArcheRage y no se elimina ninguna acción ya
presente.

El orden que construye el `sort_bag.alb` activo es:

1. Loot Gacha, bit `lootGacha` (160).
2. Enchant, incondicional.
3. Look Convert, bit `itemLookConvertInBag` (148).
4. Repair, bit `itemRepairInBag` (92).
5. Item Lock, bit `itemSecure` (45).
6. Pin/Fix, incondicional y preservado.

`sort_inventory.alb` sólo añade un botón cuando el view-adapter expone su
factory. Por eso los cuatro bits anteriores crean botones nuevos de forma
aditiva; los controles de expansión, ordenado, búsqueda, pestañas, Enchant y
Pin no cambian.

## Evidencia del cliente exacto

- Cliente: ArcheAge Returns `10.0.2.13 r575`, x86-64.
- `sort_bag.alb` activo SHA-256:
  `9535534BA55A92FA98B1F90868FA97F53768DC9F7447B4BDC1FDBADD2FC78D80`.
- Lua fuente del mismo pak SHA-256:
  `CC782126110486CDC3286F93ECC222FBFDBC04E37DC9577E65E9C12CA517F488`.
- La decompilación del ALB activo reproduce los cuatro gates anteriores; no se
  promovió una inferencia desde ArcheRage.
- La captura de ArcheRage se usa sólo como contrato visual comparativo.

Artefactos reproducibles:

```text
E:\AAEmu\rama_10\forensics\output\aa10-client-forensics\
  inventory-action-buttons-frontier\
```

## Configuración y wire

Se habilitan los mismos nombres en:

- `AAEmu.Game/Configurations/Features.json` (baseline versionado);
- `.server_files/AAEmu.Game/Configurations/Features.json` (perfil AA10 montado).

El `SCInitialConfigPacket` serializa el bitmap de 31 bytes. Los cambios exactos
son:

| Byte | Antes | Después | Feature añadido |
|---:|---:|---:|---|
| 5 | `09` | `29` | `itemSecure` (45) |
| 11 | `88` | `98` | `itemRepairInBag` (92) |
| 18 | `0A` | `1A` | `itemLookConvertInBag` (148) |
| 20 | `02` | `03` | `lootGacha` (160) |

La prueba `ConfiguredFlags_ProduceTheExpectedBlob` fija el blob completo y
`ShippedConfig_AdvertisesNativeInventoryUtilityRowAdditively` fija la intención
visible.

## Cobertura y fronteras

- **Enchant:** ya estaba expuesto y conserva las reconstrucciones AA10
  existentes.
- **Pin/Fix:** ya estaba expuesto y se conserva sin cambios.
- **Repair:** Game registra los requests de reparación individual y total y
  ejecuta `Character.DoRepair`.
- **Look Convert:** Game registra `CSConvertItemLookPacket`, carga los mappings
  del compact y emite `SCItemTaskSuccessPacket`.
- **Item Lock:** los cuatro requests r575 están registrados, pero sus handlers
  actuales sólo decodifican y registran la petición. Persistencia/transacción y
  respuesta visible siguen abiertas.
- **Loot Gacha:** el controlador cliente está completo, pero
  `GainGachaLootPackItem` sigue siendo un stub servidor. Catálogo, consumo,
  recompensa, historial y respuesta siguen abiertos.

Por lo anterior, esta entrega cierra la visibilidad aditiva de la fila, no
promueve Item Lock ni Loot Gacha como mecánicas completas. Deben aceptarse por
separado antes de autorizar pruebas con objetos valiosos.
