# Fase B12 — ejecución de socket AA8

## Alcance

Esta fase activa la inserción de la familia moderna de Lunagem asociada al
`item_socket_chance_id = 7` del cliente Kakao 8.0.3.12 r558734.

La cadena confirmada es:

```text
Gear Upgrade
→ skill 23728
→ SkillObjectSocketInstallOptions (tipo 10)
→ casteo nativo de 3000 ms
→ validación de ranura/grado/nivel
→ costo AA8 FormulaKind 38
→ consumo y mutación atómica
→ SCItemTaskSuccessPacket
→ SCSocketingResultPacket
→ SCSkillEnded(tlId)
```

## Resultado y costo

- La prueba local AA8 confirma que esta familia tiene resultado
  determinista. No se importa una probabilidad de 3.0.
- El costo no es fijo: la fórmula AA8 `38` usa `item_level`,
  `socket_item_level`, `item_used_socket` e `item_socketing_cost_mul`.
- Por ello cada Lunagem adicional cuesta más. El nivel/tier del objeto se
  representa mediante el `item_level` nativo de su plantilla.
- El grado se entrega al evaluador general del cliente, pero la expresión
  concreta de la fórmula AA8 `38` no referencia `item_grade`; no se añade un
  multiplicador inventado.

## Protocolo corregido

El primer byte de `SCSocketingResultPacket` es el código de resultado:

- `1`: éxito;
- cualquier otro valor: fallo.

El último booleano sólo decide si el cliente publica/refresca el evento de
instalación o extracción. No representa el éxito de la operación.

## Refresco de Gear Upgrade

El cliente AA8 mantiene una copia seleccionada del objeto dentro de
`X2ItemEnchant`. La ventana sólo la vuelve a leer cuando procesa
`UPDATE_ENCHANT_ITEM_MODE`.

Una inserción debe persistirse y notificarse como una única transacción
`SCItemTaskSuccessPacket(Socketing)` con este orden interno:

1. cambio de dinero;
2. consumo o eliminación del reactivo;
3. actualización de detalles del equipamiento.

Enviar esas mutaciones como transacciones `Socketing` independientes rompe la
atomicidad visible del inventario y permite refrescos parciales.

La inspección completa del cliente corrigió la hipótesis inicial sobre el
orden. `FUN_39a56560` aplica `ItemAction.UpdateDetail` de forma síncrona sobre
el objeto vivo. Por ello la secuencia nativa es:

1. `SCItemTaskSuccessPacket(Socketing)` aplica dinero, reactivo y detalle.
2. `SCSocketingResultPacket` publica el resultado mediante el evento `0x5A`;
   el modo Lunagem reconstruye entonces el objetivo ya actualizado.
3. `SCSkillEndedPacket` cierra la operación y provoca el refresco final.

Corrección posterior de dirección de protocolo: `FUN_399952d0` describe un
mensaje booleano del sentido opuesto y no el payload `SC` que consume el
handler entrante de `0x345`. El registro nativo `FUN_393676c0` enlaza ese
opcode con `FUN_392f96c0`, que entrega el identificador a
`FUN_396197c0`. Esta última función busca y elimina la transacción de skill y
publica su cierre visual. Por ello el servidor debe enviar el `UInt16 tlId`;
reducirlo a `true=01` deja activa cualquier transacción cuyo id no sea `1`.

## Frontera conocida

`x2game.dll` contiene dos loaders para `item_socket_chances`:

- cliente público: `id`, `fail_break`, `cost_ratio`;
- datos de servidor: además `socket0..socket9`.

Los `game0..game11` públicos sólo contienen la variante corta. Por eso los
grupos probabilísticos históricos continúan bloqueados: esta fase no fabrica
porcentajes ni reutiliza la compact 3.0.

## Generación

```powershell
python .\build_native_socket_execution_b12.py `
  --base-runtime D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b11-selective-lunagem-v2.sqlite3 `
  --output D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-native-equipment-phase-b12-socket-execution-v1.sqlite3 `
  --manifest ..\generated\native-socket-execution-phase-b12-v1.json
```
